#!/usr/bin/env python3
"""
Reconcile a session log's claims against the repository's current state, at resume time.

EXIT-CODE CONTRACT
------------------
  0  OK        every check completed and found no drift
  1  FINDINGS  every check completed and at least one found drift (commits landed, a tag
                cut, a branch gone, a cited file missing or renamed, a possible overlap
                between recent commits and the next action)
  2  BROKEN    at least one check could not complete (network unavailable, a fetch that
                timed out, the log could not be read, or anything else unanticipated)

NEVER INTERPRET 2 AS CLEAN. This mirrors the contract `skills/plab-wrap-session/scripts/
path-citation-check.py`, `scripts/doc-lifecycle-check.py` and `scripts/version-parity-check.py`
already use: exit 1 means a check ran to completion and found something real, never an
unanticipated failure, and no "no changes found" result may ever be printed in place of a
check that did not actually run. A per-check state follows the same three names (ok /
finding / broken) so one broken check can never be averaged into an overall clean result;
the worst state of any single check decides the whole run's exit code.

WHY THIS IS A SCRIPT, NOT A DOCUMENTED CONVENTION (design change from the original plan)
------------------------------------------------------------------------------------------
The implementation plan this effort started from argued that `plab-continue-session` "has
no independent execution runtime ... so there is no standalone script for a canary to test
against," and made the reconciliation mechanism a rung-3 documented convention instead.
That reasoning no longer holds: `plab-wrap-session` already ships agent-run scripts
(`organize-logs.py`, `path-citation-check.py`, `dash-check.py`), each with a committed test
file the agent is expected to run. This file follows that same pattern. It stays out of CI,
exactly like `test-organize-logs.py`; see `test-reconcile.py` for the fixture suite and
canary.

INVOCATION
----------
This script's own path resolves against this skill's own directory, wherever the plugin is
installed, exactly the same convention `organize-logs.py` documents in
`skills/plab-wrap-session/SKILL.md`: "the script path resolves against this skill's own
directory ... the store argument is relative to the project being wrapped." Here, both the
project root and the log path are given explicitly as arguments rather than assumed, because
unlike the wrap skill's session-log store, `plab-continue-session` does not have one fixed,
skill-relative path to resolve a log against.

    python scripts/reconcile.py <project_root> <log_path> [--json] [--fetch-timeout SECONDS]

THE THREE-WAY PATH-CITATION SCOPING RULE (AC-6) COMES FROM D-12, MIRRORED HERE
--------------------------------------------------------------------------------
`skills/plab-wrap-session/scripts/path-citation-check.py` is the canonical implementation of
the rule `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-12_path-citation-
precision/spec.md` defines: (a) a citation with a path separator is checked for existence and
flagged when missing; (b) a backtick-wrapped citation with no separator is resolved against
the repo root and produces no finding either way; (c) a bare word with neither signal is
prose, never evaluated. This file mirrors a minimal subset of that classifier (the regexes
and the `is_path_claim` / `clean_token` / `extract_citations` logic) rather than importing
across skill directories, because plugin skills are installed independently and must not
depend on each other's internal script modules at runtime. Any change to the D-12 rule itself
belongs in `path-citation-check.py`; a change here should only ever be "catch up to a fix made
there."

WHY EVERY SUBPROCESS CALL PINS encoding="utf-8" AND SETS GIT_TERMINAL_PROMPT=0
----------------------------------------------------------------------------------
`path-citation-check.py`'s docstring records the failure an unpinned text-mode read guards
against (a non-UTF-8 byte crashing the read). The same risk exists here for subprocess output,
so every `run_git` call pins `encoding="utf-8"` with `errors="replace"`. Separately,
`GIT_TERMINAL_PROMPT=0` is set on every subprocess so that an https remote with no cached
credential fails fast instead of blocking on a credential prompt that no `timeout=` argument
can interrupt from the outside; a bare timeout alone was proven insufficient for this shape of
hang.

WHY THE FETCH IS --no-prune (fixing a stale assumption in the original spec)
---------------------------------------------------------------------------------
`skills/plab-wrap-session/references/hygiene-sweep.md` Check 1 uses a plain
`git fetch origin --tags`. A plain fetch prunes whenever `fetch.prune` is set in git config,
and on 2026-09-25 a pruning fetch deleted a remote-tracking ref without confirmation (recorded
in the sibling spec W-02 (derived log facts), decision D4, tested 2026-10-05). This script therefore fetches with
`git fetch --no-prune origin --tags` and documents the one-word deviation from Check 1's exact
command text rather than reusing it verbatim.

NO COMMAND HERE MUTATES REPOSITORY STATE (AC-9)
---------------------------------------------------
Every subprocess call in this file is one of: `fetch` (updates remote-tracking refs and the
local tag list, never the working tree, the index, or HEAD), `status`, `log`, `diff`,
`branch --list`, `ls-remote`, `tag -l`, `for-each-ref`, and `rev-list` / `rev-parse` in
read-only form. None of `pull`, `merge`, `checkout`, `reset`, or `push` appears anywhere in
this file as a command to run; `test-reconcile.py` asserts this at runtime against the actual
recorded argv list, not just by reading the source.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

MUTATING_VERBS = ("pull", "merge", "checkout", "reset", "push")

# ---------------------------------------------------------------------------
# git subprocess helper
# ---------------------------------------------------------------------------


def run_git(args, cwd, commands_run, timeout=None):
    """Run one read-only git command, recording it in commands_run regardless of outcome.

    Returns (returncode_or_None, stdout, stderr, timed_out). returncode is None only when
    the process never produced one (a timeout, or the git executable could not be started),
    which callers must treat as distinct from a normal non-zero exit.
    """
    argv = ["git", *args]
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    record = {"argv": argv, "returncode": None, "timed_out": False}
    commands_run.append(record)
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
        )
        record["returncode"] = proc.returncode
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired:
        record["timed_out"] = True
        return None, "", "timed out after %ss" % timeout, True
    except OSError as exc:
        record["returncode"] = None
        return None, "", str(exc), False


# ---------------------------------------------------------------------------
# Log reading: frontmatter scalars and the Continuation Prompt section
# ---------------------------------------------------------------------------

FRONTMATTER_SCALAR = re.compile(
    r'^(date|branch|repo|commit-sha):\s*(.*)$'
)


def strip_scalar(val):
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        val = val[1:-1]
    return val


def read_log(log_path):
    """Read the log file. Raises OSError / UnicodeDecodeError on failure; callers convert
    that into a whole-run BROKEN result, since nothing downstream can run without the log.
    """
    with open(log_path, encoding="utf-8-sig") as fh:
        return fh.read()


def extract_frontmatter(text):
    """Pull only the four scalar fields this script needs (date, branch, repo, commit-sha)
    out of the log's frontmatter block.

    Deliberately NOT a general YAML parser: a real wrap-session log's frontmatter carries
    `files-changed:` as a YAML block list (one `- item` per line), and a parser that refuses
    block sequences (as `scripts/doc-lifecycle-check.py`'s does, by design, for its own
    different job) would report every real log as BROKEN. Scanning line-by-line for these
    four known scalar key names simply never matches a `- item` continuation line, so the
    block list is silently and correctly ignored rather than tripping a parse error.
    """
    fm = {}
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return fm, text
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end = i
            break
    if end is None:
        return fm, text
    for line in lines[1:end]:
        m = FRONTMATTER_SCALAR.match(line)
        if m:
            fm[m.group(1)] = strip_scalar(m.group(2))
    body = "\n".join(lines[end + 1:])
    return fm, body


CONTINUATION_HEADING = re.compile(r'^##\s+Continuation Prompt\s*$', re.MULTILINE)
NEXT_HEADING = re.compile(r'^##\s+\S')


def extract_continuation_prompt(body):
    """Return the text of the '## Continuation Prompt' section, or None if absent."""
    m = CONTINUATION_HEADING.search(body)
    if not m:
        return None
    rest = body[m.end():]
    lines = rest.split("\n")
    out = []
    for line in lines:
        if NEXT_HEADING.match(line):
            break
        out.append(line)
    return "\n".join(out)


def parse_log_date(raw):
    """Parse the frontmatter 'date' field (ISO 8601, e.g. 2026-10-01T14:30:00-07:00)."""
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# D-12 path-citation classifier, mirrored minimally from
# skills/plab-wrap-session/scripts/path-citation-check.py. See that file for the full
# rationale and canary history; only the pieces AC-6 needs are reproduced here.
# ---------------------------------------------------------------------------

URI_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.]*://")
WINDOWS_ABS = re.compile(r"^[A-Za-z]:[\\/]")
STRIP_CHARS = ".,;:!?()[]{}\"'<>"
LEADING_STRIP_CHARS = STRIP_CHARS.replace(".", "")
POSSESSIVE_SUFFIX = re.compile("(?:'s|" + chr(0x2019) + "s)$")
FILE_EXTENSION = re.compile(r"^[A-Za-z0-9]{1,10}$")
VERSION_NUMBER = re.compile(
    r"^v?\d+(\.\d+){1,}"
    r"(?:(?:-[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)*|[A-Za-z]+\d*)$"
)
LINE_ANCHOR = re.compile(r":\d+(-\d+)?$")
ELLIPSIS_PREFIX = re.compile(r"^\.{3,}")
BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")


def has_separator(cite):
    return "/" in cite or "\\" in cite


def strip_line_anchor(cite):
    return LINE_ANCHOR.sub("", cite)


def strip_ellipsis_prefix(cite):
    return ELLIPSIS_PREFIX.sub("", cite)


def is_path_claim(cite):
    """Does this citation assert where a file lives? Mirrors path-citation-check.py's
    function of the same name; see that file for the canary-proved edge cases."""
    if URI_SCHEME.match(cite):
        return False
    if WINDOWS_ABS.match(cite):
        return False
    if "*" in cite or "?" in cite:
        return False
    if "<" in cite or ">" in cite:
        return False
    if cite.startswith("/") and cite.count("/") == 1:
        return False
    if not has_separator(cite):
        return False
    if cite.endswith("/") or cite.endswith("\\"):
        return True
    base = os.path.basename(cite.rstrip("/\\").replace("\\", "/"))
    if "." not in base:
        return False
    if VERSION_NUMBER.match(base):
        return False
    ext = base.rsplit(".", 1)[1]
    if not FILE_EXTENSION.match(ext):
        return False
    return True


def clean_token(tok):
    c = tok.rstrip(STRIP_CHARS)
    c = strip_line_anchor(c)
    c = POSSESSIVE_SUFFIX.sub("", c)
    c = strip_line_anchor(c)
    c = c.lstrip(LEADING_STRIP_CHARS)
    c = strip_ellipsis_prefix(c)
    return c


def extract_path_claims(text):
    """Return the deduplicated, order-preserving list of citations in text that assert a
    file location per the D-12 rule (branch (a) only; branch (b) and (c) never produce a
    citation this script needs to check, since AC-6 only checks separator-bearing claims)."""
    seen = []
    cites = []
    for m in BACKTICK_SPAN.finditer(text):
        c = m.group(1).strip()
        if not c:
            continue
        c = strip_line_anchor(c)
        c = strip_ellipsis_prefix(c)
        cites.append(c)
    outside = BACKTICK_SPAN.sub(" ", text)
    for tok in outside.split():
        c = clean_token(tok)
        if c and has_separator(c):
            cites.append(c)
    out = []
    for c in cites:
        if is_path_claim(c) and c not in seen:
            seen.append(c)
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_remote_fetch(cwd, timeout, commands_run):
    """AC-2 (minus the one documented --no-prune deviation): fetch tags and refs from
    origin. Feeds check_release_cut and check_branch_remote; its own state reports whether
    that feed is fresh."""
    rc, _out, err, timed_out = run_git(
        ["fetch", "--no-prune", "origin", "--tags"], cwd, commands_run, timeout=timeout
    )
    if timed_out:
        return {"state": "broken", "detail": "git fetch --no-prune origin --tags timed out after %ss" % timeout}
    if rc is None:
        return {"state": "broken", "detail": "git fetch --no-prune origin --tags could not run: %s" % err}
    if rc != 0:
        return {"state": "broken", "detail": "git fetch --no-prune origin --tags failed: %s" % err.strip()}
    return {"state": "ok", "detail": "fetched origin"}


def check_ahead_behind(cwd, fetch_state, commands_run):
    """Informational half of AC-2: ahead/behind counts against the upstream, when one is
    configured, reusing hygiene-sweep.md Check 1's `git status -sb` in addition to the
    HEAD..@{u} / @{u}..HEAD log pair it also specifies. No upstream is reported as a
    finding-free 'not applicable', not broken, since many branches legitimately have none.

    When the fetch (check_remote_fetch) did not succeed, @{u} reflects whatever was fetched
    last time, which may be stale. Reporting 'up to date' off stale data in that case would
    be exactly the fail-open AC-8 forbids, so this check goes broken instead, the same
    cascading pattern check_release_cut uses."""
    rc, _out, _err, _ = run_git(
        ["rev-parse", "--abbrev-ref", "@{u}"], cwd, commands_run
    )
    if rc != 0:
        return {"state": "ok", "detail": "no upstream configured for the current branch"}
    rc_s, out_status, _err_s, _ = run_git(["status", "-sb"], cwd, commands_run)
    status_line = out_status.splitlines()[0].strip() if rc_s == 0 and out_status.strip() else None
    if fetch_state != "ok":
        detail = "fetch did not succeed; @{u} may be stale, so ahead/behind cannot be trusted"
        if status_line:
            detail += " (last known: %s)" % status_line
        return {"state": "broken", "detail": detail}
    rc_b, out_behind, err_b, _ = run_git(["log", "--oneline", "HEAD..@{u}"], cwd, commands_run)
    rc_a, out_ahead, err_a, _ = run_git(["log", "--oneline", "@{u}..HEAD"], cwd, commands_run)
    if rc_b != 0 or rc_a != 0:
        return {"state": "broken", "detail": "git log against @{u} failed: %s" % ((err_b or err_a).strip())}
    behind = len([l for l in out_behind.splitlines() if l.strip()])
    ahead = len([l for l in out_ahead.splitlines() if l.strip()])
    if behind == 0 and ahead == 0:
        detail = "up to date with upstream"
        if status_line:
            detail += " (%s)" % status_line
        return {"state": "ok", "detail": detail}
    return {"state": "finding", "detail": "%d commit(s) behind, %d ahead of upstream" % (behind, ahead),
            "behind": behind, "ahead": ahead}


def check_remote_branches_without_local(cwd, timeout, commands_run):
    """AC-2's remaining literal reuse of hygiene-sweep.md Check 1: `git ls-remote --heads
    origin` (unscoped, unlike AC-5's branch_remote check, which is scoped to the log's own
    branch) and `git tag -l` (the plain listing Check 1 pipes to `tail -5`; the last five
    are taken in Python here since there is no shell pipe at this call site). Flags remote
    branches with no local counterpart, exactly the flag Check 1 itself defines; a
    one-maintainer repo with many short-lived feature branches should expect this to be a
    finding often, the same as it is at wrap time."""
    rc, out, err, timed_out = run_git(["ls-remote", "--heads", "origin"], cwd, commands_run, timeout=timeout)
    if timed_out:
        return {"state": "broken", "detail": "git ls-remote --heads origin timed out after %ss" % timeout}
    if rc is None:
        return {"state": "broken", "detail": "git ls-remote --heads origin could not run: %s" % err}
    if rc != 0:
        return {"state": "broken", "detail": "git ls-remote --heads origin failed: %s" % err.strip()}
    remote_branches = []
    for line in out.splitlines():
        parts = line.strip().split("\t")
        if len(parts) == 2 and parts[1].startswith("refs/heads/"):
            remote_branches.append(parts[1][len("refs/heads/"):])
    rc_b, out_b, err_b, _ = run_git(["branch", "--list"], cwd, commands_run)
    if rc_b != 0:
        return {"state": "broken", "detail": "git branch --list failed: %s" % err_b.strip()}
    local_branches = {l.strip().lstrip("* ").strip() for l in out_b.splitlines() if l.strip()}

    rc_t, out_t, _err_t, _ = run_git(["tag", "-l"], cwd, commands_run)
    tail_tags = [t for t in out_t.splitlines() if t.strip()][-5:] if rc_t == 0 else []
    tag_note = (" Recent tags: %s." % ", ".join(tail_tags)) if tail_tags else ""

    missing_locally = sorted(b for b in remote_branches if b not in local_branches)
    if not missing_locally:
        return {"state": "ok",
                "detail": "every remote branch has a local counterpart (%d checked)." % len(remote_branches) + tag_note}
    shown = missing_locally[:10]
    more = ", ..." if len(missing_locally) > 10 else ""
    return {"state": "finding",
            "detail": "%d remote branch(es) with no local counterpart: %s%s." % (len(missing_locally), ", ".join(shown), more) + tag_note,
            "branches": missing_locally}


def _commits_and_touched_by_sha(cwd, sha, ref, commands_run):
    """Count commits and collect touched files in sha..ref. Returns (count, touched,
    error_or_None); error is set (and the other two meaningless) when the git commands
    themselves fail, never raised, so a caller can report a named broken reason."""
    rc, out, err, _ = run_git(["rev-list", "--count", sha + ".." + ref], cwd, commands_run)
    if rc != 0:
        return None, None, "git rev-list --count %s..%s failed: %s" % (sha, ref, err.strip())
    count = int(out.strip() or "0")
    rc2, out2, err2, _ = run_git(["diff", "--name-only", sha + ".." + ref], cwd, commands_run)
    if rc2 != 0:
        return None, None, "git diff --name-only %s..%s failed: %s" % (sha, ref, err2.strip())
    touched = [l.strip() for l in out2.splitlines() if l.strip()]
    return count, touched, None


def _commits_and_touched_by_date(cwd, log_date, ref, commands_run):
    """Count commits on ref strictly after log_date, and collect their touched files.
    Deliberately not `git log --since=<date>`: --since's boundary is inclusive in
    practice, which double-counts the exact commit a wrap session logs against when the
    log's date and that commit's date coincide to the second (the common case, since a
    wrap is typically written immediately after the last commit). Each commit's own date
    is compared to the log's date in Python instead, strictly greater-than, so the
    boundary commit itself is correctly excluded. Returns (count, touched, error_or_None)."""
    rc, out, err, _ = run_git(["log", "--pretty=format:%H %cI", ref], cwd, commands_run)
    if rc != 0:
        return None, None, "git log --pretty=format:%%H %%cI %s failed: %s" % (ref, err.strip())
    since_shas = []
    for line in out.splitlines():
        line = line.strip()
        if not line or " " not in line:
            continue
        commit_sha, iso = line.split(" ", 1)
        commit_date = parse_log_date(iso)
        if commit_date is not None and _comparable(commit_date, log_date) and commit_date > log_date:
            since_shas.append(commit_sha)
    touched_set = set()
    for commit_sha in since_shas:
        rc2, out2, _err2, _ = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha], cwd, commands_run)
        if rc2 == 0:
            touched_set.update(l.strip() for l in out2.splitlines() if l.strip())
    return len(since_shas), sorted(touched_set), None


def check_commits_since(cwd, fm, fetch_state, commands_run):
    """AC-3: count commits landed since the log, via commit-sha when present, via the date
    fallback otherwise, measured separately against the log's branch LOCALLY and against
    `origin/<branch>` REMOTELY, because this skill never pulls or merges (AC-9): a resuming
    checkout's local branch can sit stale behind origin indefinitely, and commits that
    landed there (another checkout's push, a PR merged through GitHub) would otherwise be
    invisible. Verified against a fixture (test-reconcile.py) that reading only the local
    ref reports a false-clean 'no commits landed' in exactly this shape; a live run against
    the maintainer's real checkout hit it the same way (two PRs merged on origin/main while
    the checkout sat on another branch).

    Returns a combined report: 'count' and 'touched_files' cover the LOCAL half only (kept
    for callers and tests written against the pre-remote-aware shape); 'remote_count' and
    'remote_touched_files' cover the remote half when it could be verified. The state and
    the detail string fold both halves together. When the remote half cannot be verified
    (the fetch did not succeed, or the log names no branch, or no matching remote-tracking
    ref exists), the whole check reports broken rather than a clean or finding result that
    implicitly asserts a remote it never actually checked, mirroring check_release_cut's
    fetch-state cascade."""
    sha = fm.get("commit-sha")
    branch = fm.get("branch")

    local_ref = "HEAD"
    local_note = ""
    if branch:
        rc_b, out_b, _err_b, _ = run_git(["branch", "--list", branch], cwd, commands_run)
        if rc_b == 0 and out_b.strip():
            local_ref = branch
        else:
            local_note = " (the log's branch `%s` no longer exists locally; counted against HEAD instead)" % branch

    log_date = None
    if not sha:
        log_date = parse_log_date(fm.get("date"))
        if log_date is None:
            return {"state": "broken", "detail": "log has neither commit-sha nor a parseable date field; cannot count commits since"}

    if sha:
        rc, _out, err, _ = run_git(["rev-parse", "--verify", sha + "^{commit}"], cwd, commands_run)
        if rc != 0:
            return {"state": "broken",
                    "detail": "commit-sha %s from the log was not found in this repository "
                              "(a different checkout, or history was rewritten): %s" % (sha, err.strip())}
        local_count, local_touched, local_err = _commits_and_touched_by_sha(cwd, sha, local_ref, commands_run)
        local_desc = "commit-sha `%s` on `%s`%s" % (sha, local_ref, local_note)
    else:
        local_count, local_touched, local_err = _commits_and_touched_by_date(cwd, log_date, local_ref, commands_run)
        local_desc = "the log's date (%s) on `%s`%s" % (fm.get("date"), local_ref, local_note)
    if local_err:
        return {"state": "broken", "detail": local_err}

    remote_ref = None
    remote_broken_reason = None
    if fetch_state != "ok":
        remote_broken_reason = "the fetch did not succeed, so commits on origin/%s cannot be verified" % (branch or "<branch>")
    elif not branch:
        remote_broken_reason = "log has no branch field; cannot determine which remote-tracking ref to check"
    else:
        candidate = "origin/" + branch
        rc_r, _out_r, _err_r, _ = run_git(["rev-parse", "--verify", candidate], cwd, commands_run)
        if rc_r == 0:
            remote_ref = candidate
        else:
            remote_broken_reason = "no remote-tracking ref `%s` exists; cannot verify commits on the remote" % candidate

    remote_count, remote_touched = None, []
    if remote_ref is not None:
        if sha:
            remote_count, remote_touched, remote_err = _commits_and_touched_by_sha(cwd, sha, remote_ref, commands_run)
        else:
            remote_count, remote_touched, remote_err = _commits_and_touched_by_date(cwd, log_date, remote_ref, commands_run)
        if remote_err:
            remote_broken_reason = remote_err
            remote_count, remote_touched = None, []

    behind = None
    if remote_ref is not None and remote_broken_reason is None:
        rc_bh, out_bh, _err_bh, _ = run_git(["rev-list", "--count", local_ref + ".." + remote_ref], cwd, commands_run)
        if rc_bh == 0:
            behind = int(out_bh.strip() or "0")

    touched = sorted(set(local_touched) | set(remote_touched))

    parts = []
    if local_count == 0:
        parts.append("no commits landed on the local branch since %s" % local_desc)
    else:
        parts.append("%d commit(s) landed on the local branch since %s" % (local_count, local_desc))
    if remote_broken_reason:
        parts.append("remote commits could not be verified: %s" % remote_broken_reason)
    elif remote_count == 0:
        parts.append("no additional commits on %s" % remote_ref)
    else:
        parts.append("%d commit(s) on %s not yet reflected in the local branch" % (remote_count, remote_ref))
    if behind:
        parts.append("local `%s` is %d commit(s) behind %s" % (local_ref, behind, remote_ref))
    detail = "; ".join(parts) + "."

    result = {"count": local_count, "touched_files": touched,
              "remote_count": remote_count, "remote_touched_files": remote_touched}
    if remote_broken_reason:
        result["state"] = "broken"
    elif local_count > 0 or (remote_count or 0) > 0:
        result["state"] = "finding"
    else:
        result["state"] = "ok"
    result["detail"] = detail
    return result


def check_release_cut(cwd, fm, fetch_state, commands_run):
    """AC-4: compare each tag's creation date against the log's date field. Uses
    creatordate:iso-strict rather than Check 1's plain tail-5 listing, because a date-only
    comparison would false-positive a tag cut earlier the same calendar day as the log."""
    log_date = parse_log_date(fm.get("date"))
    if log_date is None:
        return {"state": "broken", "detail": "log has no parseable date field; cannot compare tag creation dates"}
    rc, out, err, _ = run_git(
        ["for-each-ref", "refs/tags", "--sort=-creatordate",
         "--format=%(refname:short) %(creatordate:iso-strict)"],
        cwd, commands_run,
    )
    if rc != 0:
        return {"state": "broken", "detail": "git for-each-ref refs/tags failed: %s" % err.strip()}
    new_tags = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rsplit(" ", 1)
        if len(parts) != 2:
            continue
        tag, iso = parts
        try:
            tag_date = dt.datetime.fromisoformat(iso)
        except ValueError:
            continue
        if _comparable(tag_date, log_date) and tag_date > log_date:
            new_tags.append(tag)
    prefix = "" if fetch_state == "ok" else "(fetch did not succeed; checked against locally cached tags only) "
    if not new_tags:
        return {"state": "broken" if fetch_state != "ok" else "ok",
                "detail": prefix + "no tag cut since the log's date"}
    state = "broken" if fetch_state != "ok" else "finding"
    return {"state": state, "detail": prefix + "tag(s) cut since the log: %s" % ", ".join(new_tags),
            "new_tags": new_tags}


def _comparable(a, b):
    """Both datetimes must be naive or both aware to compare; treat a mismatch as
    incomparable rather than raising."""
    return (a.tzinfo is None) == (b.tzinfo is None)


def check_branch_local(cwd, fm, commands_run):
    """AC-5, local half."""
    branch = fm.get("branch")
    if not branch:
        return {"state": "broken", "detail": "log has no branch field; cannot check local branch existence"}
    rc, out, err, _ = run_git(["branch", "--list", branch], cwd, commands_run)
    if rc != 0:
        return {"state": "broken", "detail": "git branch --list %s failed: %s" % (branch, err.strip())}
    if out.strip():
        return {"state": "ok", "detail": "branch `%s` still exists locally" % branch}
    return {"state": "finding", "detail": "branch `%s` no longer exists locally" % branch}


def check_branch_remote(cwd, fm, timeout, commands_run):
    """AC-5, remote half."""
    branch = fm.get("branch")
    if not branch:
        return {"state": "broken", "detail": "log has no branch field; cannot check remote branch existence"}
    rc, out, err, timed_out = run_git(["ls-remote", "--heads", "origin", branch], cwd, commands_run, timeout=timeout)
    if timed_out:
        return {"state": "broken", "detail": "git ls-remote --heads origin %s timed out after %ss" % (branch, timeout)}
    if rc is None:
        return {"state": "broken", "detail": "git ls-remote --heads origin %s could not run: %s" % (branch, err)}
    if rc != 0:
        return {"state": "broken", "detail": "git ls-remote --heads origin %s failed: %s" % (branch, err.strip())}
    if out.strip():
        return {"state": "ok", "detail": "branch `%s` still exists on origin" % branch}
    return {"state": "finding", "detail": "branch `%s` no longer exists on origin" % branch}


def rename_hint(cwd, path, timeout, commands_run):
    """Attempt AC-6's rename-hint recovery for a missing citation. Returns the new path
    name, or None if no rename was found (never broken on its own; a missing hint is not a
    failed check, just an unanswered one).

    DEVIATION FROM THE SPEC'S LITERAL COMMAND TEXT: the spec names
    `git log --follow --diff-filter=R -- <path>`. Verified empirically against a fixture
    (test-reconcile.py) that this does not work for the case AC-6 actually needs: `--follow`
    tracks a path that exists at the tip of history backward through renames, but a citation
    to a path that is MISSING at HEAD because it was renamed away is the opposite direction,
    and `--follow` finds nothing for it, with or without the pathspec restricted to the old
    name. Restricting by pathspec at all turns out to be the problem, not `--follow`
    specifically: git's history-simplification path limiting drops the rename commit itself
    once the pathspec no longer matches the post-rename tree. The fix is to scan every
    rename record in history with no pathspec at all (`git log --diff-filter=R --name-status
    --format=%H`) and match the old name against this process's own citation in Python. This
    is more work per call than a pathspec-scoped query would be, but it only runs once per
    missing citation, and only when a citation is already missing.
    """
    rc, out, _err, timed_out = run_git(
        ["log", "--diff-filter=R", "--name-status", "--format=%H"],
        cwd, commands_run, timeout=timeout,
    )
    if timed_out or rc != 0:
        return None
    normalized = path.replace("\\", "/")
    for line in out.splitlines():
        line = line.strip()
        if not line or not line.startswith("R"):
            continue
        parts = line.split("\t")
        if len(parts) >= 3 and parts[1].replace("\\", "/") == normalized:
            return parts[-1]
    return None


def check_path_existence(cwd, citations, timeout, commands_run):
    """AC-6: existence-check every path-claim citation found in the Continuation Prompt
    section, with a rename-hint attempt on a miss."""
    if citations is None:
        return {"state": "broken", "detail": "no '## Continuation Prompt' section found in the log; "
                                              "cannot check cited paths", "missing": []}
    missing = []
    for cite in citations:
        if os.path.exists(os.path.join(cwd, cite)):
            continue
        hint = rename_hint(cwd, cite, timeout, commands_run)
        missing.append({"cite": cite, "rename_hint": hint})
    if not missing:
        return {"state": "ok", "detail": "every cited path in the continuation prompt resolves (%d checked)" % len(citations),
                "missing": []}
    return {"state": "finding",
            "detail": "%d of %d cited path(s) do not resolve" % (len(missing), len(citations)),
            "missing": missing}


def check_next_action_overlap(commits_check, citations):
    """AC-7: advisory only. Overlap between files touched since the log and paths the
    continuation prompt cites. Never asserts completion as fact."""
    if citations is None:
        return {"state": "broken", "detail": "no '## Continuation Prompt' section found in the log; "
                                              "cannot check for next-action overlap"}
    if commits_check["state"] == "broken":
        return {"state": "broken", "detail": "commit history since the log could not be determined; "
                                              "cannot check for next-action overlap"}
    touched = set(t.replace("\\", "/") for t in commits_check.get("touched_files", []))
    cited = set(c.replace("\\", "/") for c in citations)
    overlap = sorted(touched & cited)
    if not overlap:
        return {"state": "ok", "detail": "no overlap between recently touched files and the continuation prompt"}
    return {"state": "finding",
            "detail": "the named next action may already be complete: recent commits touch %s; verify before proceeding"
                       % ", ".join("`%s`" % f for f in overlap),
            "overlap": overlap}


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------

STATE_RANK = {"ok": 0, "finding": 1, "broken": 2}


def build_report(project_root, log_path, fetch_timeout):
    commands_run = []
    try:
        text = read_log(log_path)
    except (OSError, UnicodeDecodeError) as exc:
        return {
            "overall": "broken",
            "detail": "could not read log %s: %s: %s" % (log_path, type(exc).__name__, exc),
            "checks": {},
            "commands_run": commands_run,
        }

    fm, body = extract_frontmatter(text)
    continuation = extract_continuation_prompt(body)
    citations = extract_path_claims(continuation) if continuation is not None else None

    checks = {}
    checks["remote_fetch"] = check_remote_fetch(project_root, fetch_timeout, commands_run)
    checks["ahead_behind"] = check_ahead_behind(project_root, checks["remote_fetch"]["state"], commands_run)
    checks["remote_branches"] = check_remote_branches_without_local(project_root, fetch_timeout, commands_run)
    checks["commits_since"] = check_commits_since(project_root, fm, checks["remote_fetch"]["state"], commands_run)
    checks["release_cut"] = check_release_cut(project_root, fm, checks["remote_fetch"]["state"], commands_run)
    checks["branch_local"] = check_branch_local(project_root, fm, commands_run)
    checks["branch_remote"] = check_branch_remote(project_root, fm, fetch_timeout, commands_run)
    checks["path_existence"] = check_path_existence(project_root, citations, fetch_timeout, commands_run)
    checks["next_action_overlap"] = check_next_action_overlap(checks["commits_since"], citations)

    overall_rank = max(STATE_RANK[c["state"]] for c in checks.values())
    overall = [k for k, v in STATE_RANK.items() if v == overall_rank][0]

    return {
        "overall": overall,
        "detail": None,
        "checks": checks,
        "commands_run": commands_run,
        "frontmatter": fm,
    }


def render_markdown(report):
    lines = []
    if report.get("detail"):
        lines.append("Reconciliation incomplete: %s" % report["detail"])
        return "\n".join(lines)

    checks = report["checks"]
    order = ["remote_fetch", "ahead_behind", "remote_branches", "commits_since", "release_cut",
             "branch_local", "branch_remote", "path_existence", "next_action_overlap"]
    label = {
        "remote_fetch": "Remote fetch",
        "ahead_behind": "Ahead/behind upstream",
        "remote_branches": "Remote branches without a local counterpart",
        "commits_since": "Commits since the log",
        "release_cut": "Release cut since the log",
        "branch_local": "Log's branch, locally",
        "branch_remote": "Log's branch, on origin",
        "path_existence": "Continuation-prompt file paths",
        "next_action_overlap": "Next action vs. recent commits",
    }
    any_broken = any(c["state"] == "broken" for c in checks.values())
    if any_broken:
        lines.append("Reconciliation incomplete; one or more checks could not complete.")
    for key in order:
        c = checks[key]
        tag = {"ok": "ok", "finding": "FINDING", "broken": "BROKEN"}[c["state"]]
        lines.append("- %s: [%s] %s" % (label[key], tag, c["detail"]))
        if key == "path_existence":
            for miss in c.get("missing", []):
                if miss["rename_hint"]:
                    lines.append("  - `%s` is missing; possibly renamed to `%s`" % (miss["cite"], miss["rename_hint"]))
                else:
                    lines.append("  - `%s` is missing; no rename found" % miss["cite"])
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Reconcile a plab-wrap-session log's claims against current repository state."
    )
    ap.add_argument("project_root", help="the project being resumed in (not this skill's install location)")
    ap.add_argument("log_path", help="path to the session log being resumed from")
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    ap.add_argument("--fetch-timeout", type=float, default=20.0,
                     help="seconds before a network git command is treated as broken (default: 20)")
    args = ap.parse_args(argv)

    report = build_report(args.project_root, args.log_path, args.fetch_timeout)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))

    return {"ok": 0, "finding": 1, "broken": 2}[report["overall"]]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - backstop, matches path-citation-check.py
        print("BROKEN: unexpected %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(2)
