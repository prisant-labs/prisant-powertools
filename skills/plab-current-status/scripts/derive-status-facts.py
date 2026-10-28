#!/usr/bin/env python3
"""Derive a repository's status facts in one call, instead of model recall.

CS-01 (current status skill): every fact `plab-current-status` states about
repository state comes from this script. See
docs/internal/release-plans/_unassigned/CS-01_current-status/ for the spec and
implementation plan this script fulfils.

USAGE
-----
  derive-status-facts.py [--repo <path>] [--json] [--out <file>] [--no-fetch]
                         [--gh <exe>] [--today YYYY-MM-DD]

EXIT-CODE CONTRACT
------------------
  0  the facts were gathered; every source that was missing for an expected
     reason (no remote, no `gh`, no session logs) is listed in `gaps`
  2  BROKEN   the target is not a git repository, or the decisions sweep
             could not read a source it should have read; nothing is printed
             to stdout

NEVER INTERPRET 2 AS CLEAN. A gap is an expected absence and is reported; a
break is a failure to read something that exists and is not.

WRITE CONTRACT
--------------
This script writes no file in the working tree. `--out` writes the JSON to a
path the caller names, which the skill places in a temp folder. Its one write
to the repository is the fetch,
`git fetch --no-prune origin --tags`, which updates remote-tracking refs under
`.git` only (CS-01's D2, whether to fetch). `--no-prune` is explicit because a
plain fetch prunes whenever `fetch.prune` is set, the same reason
`skills/plab-wrap-session/scripts/derive-log-facts.py` gives. `--no-fetch`
skips it. Every git call sets `GIT_OPTIONAL_LOCKS=0`, so a read never refreshes
`.git/index`, and `GIT_TERMINAL_PROMPT=0`, so a missing credential cannot hang
the fetch.

THE LEVEL
---------
  git-only    neither session logs nor typed planning documents exist
  logs        session logs exist, typed planning documents do not
  decisions   tracked documents whose frontmatter `type` is `spec`,
              `implementation-plan` or `release-plan` exist

The level tells the skill which sections it can fill from evidence. Each
missing source is also a named gap, so the snapshot's What I Don't Know can
list it.

THE DECISIONS SWEEP IS CALLED, NOT RE-DECLARED
-----------------------------------------------
Pending, recently answered and unrecognised decision items come from
`skills/plab-resolve-open-items/scripts/gather-backlog.py --answered-since`,
run as a subprocess by its path inside the plugin (CS-01's D1, where the
decisions sweep lives). Its exit 2 is this script's exit 2. Newest-log
discovery mirrors `skills/plab-continue-session/references/log-discovery.md`,
as `gather-backlog.py` and `derive-log-facts.py` already do.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

GATHER = Path(__file__).resolve().parents[2] / "plab-resolve-open-items" / "scripts" / "gather-backlog.py"

TYPED_KINDS = ("spec", "implementation-plan", "release-plan")
STATUS_DIR = "_local/_status"
# YYYY-MM-DD_<model>_<byline>.md: model and byline are lowercase kebab-case,
# the byline two to six words. Hand-written files such as
# 2026-10-25_threads-consolidated.md carry one underscore and never match.
SNAPSHOT_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_([a-z0-9]+(?:-[a-z0-9]+)*)_([a-z0-9]+(?:-[a-z0-9]+){1,5})\.md$"
)
LOG_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_.*\.md$")
MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")
TYPE_LINE_RE = re.compile(r"^type:\s*['\"]?([\w-]+)")

COMMIT_CAP = 50
DECISIONS_DEFAULT_DAYS = 14
GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")


class Broken(Exception):
    """A source that exists could not be read. Always exit 2."""


def run(cmd, cwd, timeout=20, env=None):
    try:
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env or GIT_ENV)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ss" % timeout
    except OSError as exc:
        return 127, "", str(exc)


def git(repo, *args, timeout=20):
    return run(["git", "-C", str(repo), *args], repo, timeout=timeout)


def first_line(text):
    text = (text or "").strip()
    return text.splitlines()[0] if text else ""


def commits(repo, *rev_args):
    rc, out, _ = git(repo, "log", "--format=%h%x09%ad%x09%s", "--date=short", *rev_args)
    if rc != 0:
        return None
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
    return rows


# ---------------------------------------------------------------------------
# Git state
# ---------------------------------------------------------------------------


def git_facts(repo, do_fetch, gaps):
    facts = {}
    rc, out, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    facts["branch"] = out.strip() if rc == 0 else None
    facts["detached"] = facts["branch"] == "HEAD"
    rc, out, _ = git(repo, "rev-parse", "HEAD")
    facts["head"] = out.strip() if rc == 0 else None
    if facts["head"] is None:
        gaps.append({"source": "commits", "reason": "the repository has no commits yet"})

    rc, out, _ = git(repo, "status", "--porcelain")
    changed = [ln for ln in out.splitlines() if ln.strip()] if rc == 0 else []
    facts["dirty_count"] = len(changed)
    facts["dirty_sample"] = changed[:10]

    rc, out, _ = git(repo, "remote")
    remotes = out.split() if rc == 0 else []
    if "origin" not in remotes:
        facts["fetch"] = "no-remote"
        gaps.append({"source": "remote", "reason": "no `origin` remote, so nothing is compared with a remote"})
    elif not do_fetch:
        facts["fetch"] = "skipped"
        gaps.append({"source": "fetch", "reason": "run with --no-fetch, so the remote comparison is as of the last fetch"})
    else:
        rc, _, err = git(repo, "fetch", "--no-prune", "origin", "--tags", timeout=30)
        facts["fetch"] = "ok" if rc == 0 else "failed"
        if rc != 0:
            gaps.append({"source": "fetch", "reason": "`git fetch` failed (%s), so the remote comparison is as of the last fetch"
                         % (first_line(err) or "exit %d" % rc)})

    facts["upstream"] = facts["ahead"] = facts["behind"] = None
    if "origin" in remotes and facts["head"]:
        rc, out, _ = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if rc == 0:
            facts["upstream"] = out.strip()
            rc, out, _ = git(repo, "rev-list", "--left-right", "--count", "@{u}...HEAD")
            if rc == 0 and len(out.split()) == 2:
                behind, ahead = out.split()
                facts["behind"], facts["ahead"] = int(behind), int(ahead)
        else:
            gaps.append({"source": "upstream", "reason": "branch `%s` tracks no upstream" % facts["branch"]})

    facts["latest_tag"] = None
    if facts["head"]:
        rc, out, _ = git(repo, "describe", "--tags", "--abbrev=0")
        if rc == 0 and out.strip():
            tag = out.strip()
            _, date_out, _ = git(repo, "log", "-1", "--format=%ad", "--date=short", tag)
            facts["latest_tag"] = {"name": tag, "date": date_out.strip() or None}
        else:
            gaps.append({"source": "tags", "reason": "no tag is reachable from HEAD"})
    return facts


# ---------------------------------------------------------------------------
# Previous snapshot, session logs, typed documents
# ---------------------------------------------------------------------------


def previous_snapshot(repo):
    folder = repo / STATUS_DIR
    if not folder.is_dir():
        return None
    found = sorted((p for p in folder.glob("*.md") if SNAPSHOT_RE.match(p.name)), key=lambda p: p.name)
    if not found:
        return None
    p = found[-1]
    date, model, byline = SNAPSHOT_RE.match(p.name).groups()
    return {"path": "%s/%s" % (STATUS_DIR, p.name), "date": date, "model": model, "byline": byline}


def session_logs(repo):
    """Every log in the pooled stores of log-discovery.md, newest first."""
    stores = []
    current = repo / "_local" / "_session-logs"
    if current.is_dir():
        stores.append(current)
        stores.extend(e for e in sorted(current.iterdir()) if e.is_dir() and MONTH_DIR_RE.match(e.name))
    for legacy in (repo / "_agent-context" / "session-log", repo / "AGENTS" / "session-log"):
        if legacy.is_dir():
            stores.append(legacy)
    logs = [p for s in stores for p in s.glob("*.md") if LOG_NAME_RE.match(p.name)]
    logs.sort(key=lambda p: p.name, reverse=True)
    return [p.relative_to(repo).as_posix() for p in logs]


def typed_documents(repo):
    rc, out, err = git(repo, "ls-files", "--", "*.md")
    if rc != 0:
        raise Broken("git ls-files failed: %s" % first_line(err))
    found = []
    for rel in out.splitlines():
        try:
            with open(repo / rel, encoding="utf-8-sig", errors="replace") as fh:
                head = [fh.readline() for _ in range(30)]
        except OSError:
            continue  # a tracked file deleted in the working tree
        if not head or head[0].strip() != "---":
            continue
        for line in head[1:]:
            if line.strip() == "---":
                break
            m = TYPE_LINE_RE.match(line)
            if m and m.group(1) in TYPED_KINDS:
                found.append(rel)
                break
    return found


def status_dir_ignored(repo):
    rc, _, _ = git(repo, "check-ignore", "-q", "%s/probe.md" % STATUS_DIR)
    return rc == 0


# ---------------------------------------------------------------------------
# Pull requests and decisions
# ---------------------------------------------------------------------------


def pull_requests(repo, gh, since, gaps):
    exe = shutil.which(gh)
    if exe is None:
        gaps.append({"source": "pull requests", "reason": "`%s` is not on PATH, so pull requests were not read" % gh})
        return {"available": False, "open": [], "merged_since": []}
    rc, out, err = run([exe, "pr", "list", "--state", "open", "--json", "number,title,headRefName,isDraft"],
                       repo, timeout=30, env=os.environ.copy())
    if rc != 0:
        gaps.append({"source": "pull requests", "reason": "`gh pr list` failed (%s)" % (first_line(err) or "exit %d" % rc)})
        return {"available": False, "open": [], "merged_since": []}
    open_prs = json.loads(out or "[]")
    merged = []
    if since:
        rc, out, err = run([exe, "pr", "list", "--state", "merged", "--search", "merged:>=%s" % since,
                            "--json", "number,title,mergedAt", "--limit", "50"],
                           repo, timeout=30, env=os.environ.copy())
        if rc == 0:
            merged = json.loads(out or "[]")
        else:
            gaps.append({"source": "merged pull requests", "reason": "`gh pr list --state merged` failed (%s)"
                         % (first_line(err) or "exit %d" % rc)})
    return {"available": True, "open": open_prs, "merged_since": merged}


def decisions(repo, since, today):
    if not GATHER.is_file():
        raise Broken("the decisions sweep is missing from the plugin: %s" % GATHER)
    rc, out, err = run([sys.executable, "-B", str(GATHER), "--repo", str(repo), "--json",
                        "--answered-since", since, "--today", today], repo, timeout=60)
    if rc != 0:
        raise Broken("the decisions sweep exited %d: %s" % (rc, first_line(err)))
    items = json.loads(out or "[]")
    return {
        "pending": [i for i in items if i.get("kind") == "pending"],
        "answered": [i for i in items if i.get("kind") == "answered"],
        "unrecognised": [i for i in items if i.get("kind") == "unrecognised"],
    }


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def derive(repo_arg, do_fetch, gh, today):
    rc, out, err = run(["git", "-C", str(repo_arg), "rev-parse", "--show-toplevel"], repo_arg)
    if rc != 0:
        raise Broken("not a git repository: %s (%s)" % (repo_arg, first_line(err)))
    repo = Path(out.strip()).resolve()
    gaps = []

    g = git_facts(repo, do_fetch, gaps)
    prev = previous_snapshot(repo)
    if prev is None:
        gaps.append({"source": "previous status", "reason": "no earlier snapshot matches %s/YYYY-MM-DD_<model>_<byline>.md" % STATUS_DIR})

    # CS-01's D3, the look-back window: since the previous snapshot; with none,
    # since the latest tag for accomplishments and fourteen days for decisions.
    if prev:
        accomplished_since, accomplished_basis = prev["date"], "previous-status"
        decisions_since, decisions_basis = prev["date"], "previous-status"
    else:
        tag_date = g["latest_tag"]["date"] if g["latest_tag"] else None
        accomplished_since = tag_date
        accomplished_basis = "latest-tag" if tag_date else "none"
        decisions_since = (dt.date.fromisoformat(today) - dt.timedelta(days=DECISIONS_DEFAULT_DAYS)).isoformat()
        decisions_basis = "%d-days" % DECISIONS_DEFAULT_DAYS

    if g["head"] is None:
        since_tag = since_window = []
    else:
        since_tag = commits(repo, "%s..HEAD" % g["latest_tag"]["name"]) if g["latest_tag"] else commits(repo, "-n", str(COMMIT_CAP))
        since_window = commits(repo, "--since=%s 00:00" % accomplished_since) if accomplished_since else since_tag
    g["commits_since_tag_count"] = len(since_tag or [])
    g["commits_since_tag"] = (since_tag or [])[:COMMIT_CAP]
    g["commits_since_window_count"] = len(since_window or [])
    g["commits_since_window"] = (since_window or [])[:COMMIT_CAP]

    logs = session_logs(repo)
    if not logs:
        gaps.append({"source": "session logs", "reason": "none in _local/_session-logs/ or the legacy stores"})
    newest_log = logs[0] if logs else None
    if prev:
        logs_since = [p for p in logs if LOG_NAME_RE.match(p.rsplit("/", 1)[-1]).group(1) >= prev["date"]]
    else:
        logs_since = logs[:1]

    typed = typed_documents(repo)
    if not typed:
        gaps.append({"source": "decision documents", "reason": "no tracked spec, implementation-plan or release-plan"})
    level = "decisions" if typed else ("logs" if logs else "git-only")

    dec = decisions(repo, decisions_since, today)
    if dec["unrecognised"]:
        gaps.append({"source": "unrecognised statuses",
                     "reason": "%d decision row(s) carry a status outside the vocabulary of references/decisions-section.md"
                               % len(dec["unrecognised"])})

    prs = pull_requests(repo, gh, accomplished_since, gaps)
    ignored = status_dir_ignored(repo)

    return {
        "schema": 1,
        "today": today,
        "repo": {"root": repo.as_posix(), "name": repo.name},
        "level": level,
        "git": g,
        "pull_requests": prs,
        "previous_status": prev,
        "status_dir": STATUS_DIR,
        "status_dir_ignored": ignored,
        "window": {
            "accomplished_since": accomplished_since, "accomplished_basis": accomplished_basis,
            "decisions_since": decisions_since, "decisions_basis": decisions_basis,
        },
        "session_logs": {"newest": newest_log, "since_previous": logs_since, "total": len(logs)},
        "typed_documents": len(typed),
        "decisions": dec,
        "gaps": gaps,
    }


def summary(f):
    g = f["git"]
    lines = [
        "%s: level %s, branch %s at %s" % (f["repo"]["name"], f["level"], g["branch"], (g["head"] or "none")[:7]),
        "tag %s, %d commit(s) since it; tree %s" % (
            g["latest_tag"]["name"] if g["latest_tag"] else "none", g["commits_since_tag_count"],
            "clean" if g["dirty_count"] == 0 else "%d change(s)" % g["dirty_count"]),
        "decisions: %d pending, %d answered since %s, %d unrecognised" % (
            len(f["decisions"]["pending"]), len(f["decisions"]["answered"]), f["window"]["decisions_since"],
            len(f["decisions"]["unrecognised"])),
        "previous status: %s" % (f["previous_status"]["path"] if f["previous_status"] else "none"),
        "gaps: %s" % (", ".join(x["source"] for x in f["gaps"]) or "none"),
    ]
    return "\n".join(lines)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Derive a repository's status facts in one call.")
    parser.add_argument("--repo", default=".", help="repository to inspect (default: current directory)")
    parser.add_argument("--json", action="store_true", help="emit the facts as JSON")
    parser.add_argument("--no-fetch", action="store_true", help="do not fetch from origin first")
    parser.add_argument("--gh", default="gh", help="the GitHub CLI executable (default: gh)")
    parser.add_argument("--today", help="override today's date as YYYY-MM-DD (for testing)")
    parser.add_argument("--out", help="also write the JSON to this file, for `status-check.py --facts`; "
                                      "give a path outside the working tree")
    args = parser.parse_args(argv)
    today = args.today or dt.date.today().isoformat()
    try:
        facts = derive(Path(args.repo).resolve(), not args.no_fetch, args.gh, today)
    except Broken as exc:
        sys.stderr.write("BROKEN: %s\n" % exc)
        return 2
    if args.out:
        # Written by Python rather than by shell redirection, because `>` in
        # Windows PowerShell 5.1 writes UTF-16, which the checker cannot read.
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(facts, indent=2) if args.json else summary(facts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
