#!/usr/bin/env python3
"""Read-only git sweep of one or more repositories.

PP-01 (project pulse): contract C2 in
docs/internal/release-plans/_unassigned/PP-01_project-pulse/spec.md. Both
`plab-project-pulse` and the usage-audit skill (UA-01) use this contract.

USAGE
-----
  sweep.py --repo PATH [--repo PATH2 ...] --start D --end D
           --prior-start D --tz ZONE --author-pattern REGEX [--json]

Dates (`--start`, `--end`, `--prior-start`) are `YYYY-MM-DD` local dates in
`--tz`. The focus window is `[start, end]` inclusive; the prior window is
`[prior_start, start)`, the day before `start` back to `prior_start`
inclusive. `--author-pattern` is a Python regex matched with `re.search`
against `"<name> <email>"` for each commit, in Python, not passed to
`git log --author`, so there is exactly one regex dialect in play.

READ-ONLY, NEVER FETCH
------------------------
Every git call here is one of: `log`, `status --porcelain`,
`rev-list --left-right --count`, `rev-parse`, `for-each-ref`,
`worktree list --porcelain`, `stash list`, `branch --no-merged`. No call
writes, prunes, packs, or fetches. Every call carries
`-c core.fsmonitor=false --no-optional-locks` and the environment sets
`GIT_OPTIONAL_LOCKS=0`, so `git status` does not refresh and rewrite the
index's stat cache (AC-9): the working tree, refs, index and `FETCH_HEAD`
are byte-identical before and after a sweep.

COMMIT DATES USE THE COMMITTER DATE, IN THE CONFIGURED ZONE
-------------------------------------------------------------
"Commit date" in contract C2 is read as the committer date (`%ct`), the
field git itself reports for `git log --date=local` and the one that cannot
be rewritten by rebasing without `--committer-date-is-author-date`. It is
converted with `zoneinfo`, never a fixed UTC offset: a fixed `-07:00`
("Pacific time") is wrong half the year, which is exactly what AC-7's
2026-11-02T07:30Z fixture (the day after the US autumn clock change) is
built to catch.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True

GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
UNIT_SEP = "\x1f"


class Broken(Exception):
    """A repository could not be read at all. The caller decides how to
    report it; `main()` turns it into one sweep record with `error` set,
    never a crash, so one bad repository does not stop the others."""


def _run(args, cwd, timeout=20):
    try:
        r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=GIT_ENV)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ss" % timeout
    except OSError as exc:
        return 127, "", str(exc)


def git(repo, *args, timeout=20):
    return _run(["git", "-c", "core.fsmonitor=false", "--no-optional-locks", "-C", str(repo), *args], repo, timeout)


def first_line(text):
    text = (text or "").strip()
    return text.splitlines()[0] if text else ""


def _local_date(epoch_seconds: int, tz: ZoneInfo) -> dt.date:
    return dt.datetime.fromtimestamp(epoch_seconds, tz=tz).date()


def _git_common_dir(repo) -> str | None:
    rc, out, _ = git(repo, "rev-parse", "--git-common-dir")
    if rc != 0:
        return None
    p = out.strip()
    return p if os.path.isabs(p) else str(Path(repo) / p)


def own_commits(repo, author_re, tz: ZoneInfo):
    """Every commit on every ref, author-matched, as (local_date, sha).
    `--all` per C2 ("own commits on all branches"); duplicates cannot occur
    because each commit is listed once regardless of how many refs reach it."""
    rc, out, err = git(repo, "log", "--all", "--format=%H" + UNIT_SEP + "%ct" + UNIT_SEP + "%an <%ae>")
    if rc != 0:
        raise Broken("git log --all failed: %s" % (first_line(err) or "exit %d" % rc))
    rows = []
    for line in out.splitlines():
        parts = line.split(UNIT_SEP)
        if len(parts) != 3:
            continue
        sha, ct, author = parts
        if not author_re.search(author):
            continue
        try:
            local_date = _local_date(int(ct), tz)
        except ValueError:
            continue
        rows.append((local_date, sha))
    return rows


def tags_in_window(repo, start: dt.date, end: dt.date, tz: ZoneInfo):
    rc, out, err = git(repo, "for-each-ref", "refs/tags",
                       "--format=%(refname:short)" + UNIT_SEP + "%(creatordate:unix)")
    if rc != 0:
        raise Broken("git for-each-ref failed: %s" % (first_line(err) or "exit %d" % rc))
    found = []
    for line in out.splitlines():
        parts = line.split(UNIT_SEP)
        if len(parts) != 2 or not parts[1]:
            continue
        name, epoch = parts
        d = _local_date(int(epoch), tz)
        if start <= d <= end:
            found.append({"tag": name, "date": d.isoformat()})
    found.sort(key=lambda t: t["date"])
    return found


def status_counts(repo):
    rc, out, err = git(repo, "status", "--porcelain")
    if rc != 0:
        raise Broken("git status failed: %s" % (first_line(err) or "exit %d" % rc))
    dirty = staged = untracked = 0
    for line in out.splitlines():
        if not line:
            continue
        x, y = (line[0], line[1]) if len(line) > 1 else (line[0], " ")
        if x == "?" and y == "?":
            untracked += 1
            continue
        if x not in (" ", "?"):
            staged += 1
        if y not in (" ", "?"):
            dirty += 1
    return dirty, staged, untracked


def ahead_behind(repo):
    rc, out, _ = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if rc != 0:
        return None, None, None, False
    upstream = out.strip()
    rc, out, _ = git(repo, "rev-list", "--left-right", "--count", "@{u}...HEAD")
    if rc != 0 or len(out.split()) != 2:
        return upstream, None, None, True
    behind, ahead = out.split()
    return upstream, int(ahead), int(behind), True


def remote_state_as_of(repo):
    common_dir = _git_common_dir(repo)
    if not common_dir:
        return None
    fetch_head = Path(common_dir) / "FETCH_HEAD"
    if not fetch_head.is_file():
        return None
    ts = fetch_head.stat().st_mtime
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def unmerged_branches(repo):
    # --format must come before --no-merged: git otherwise reads the
    # --format value as --no-merged's optional [<commit>] argument and
    # fails with "malformed object name".
    rc, out, _ = git(repo, "branch", "--format=%(refname:short)", "--no-merged")
    return [ln for ln in out.splitlines() if ln.strip()] if rc == 0 else []


def worktrees(repo):
    rc, out, _ = git(repo, "worktree", "list", "--porcelain")
    if rc != 0:
        return []
    found, current = [], {}
    for line in out.splitlines():
        if not line.strip():
            if current:
                found.append(current)
            current = {}
            continue
        if line.startswith("worktree "):
            current["path"] = line[len("worktree "):]
        elif line.startswith("branch "):
            current["branch"] = line[len("branch "):]
        elif line == "bare":
            current["bare"] = True
    if current:
        found.append(current)
    return found


def stashes(repo):
    rc, out, _ = git(repo, "stash", "list")
    return [ln for ln in out.splitlines() if ln.strip()] if rc == 0 else []


def remote_url(repo):
    rc, out, _ = git(repo, "remote", "get-url", "origin")
    return out.strip() if rc == 0 and out.strip() else None


def sweep_repo(path, start: str, end: str, prior_start: str, tz: str, author_pattern: str,
               repo_name=None, folder=None):
    repo = Path(path).resolve()
    zone = ZoneInfo(tz)
    start_d, end_d = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    prior_start_d = dt.date.fromisoformat(prior_start)
    prior_end_d = start_d - dt.timedelta(days=1)
    author_re = re.compile(author_pattern)

    rc, out, err = git(repo, "rev-parse", "HEAD")
    head = out.strip() if rc == 0 else None
    if head is None and "unknown revision" not in (err or "") and "ambiguous argument" not in (err or ""):
        # a path that is not a git repository at all; anything else (no
        # commits yet) is a legitimate, reportable state, not a break.
        rc2, _, _ = git(repo, "rev-parse", "--is-inside-work-tree")
        if rc2 != 0:
            raise Broken("not a git repository: %s" % repo)

    rc, out, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    branch = out.strip() if rc == 0 else None

    commits = own_commits(repo, author_re, zone) if head else []
    focus_dates = {d for d, _ in commits if start_d <= d <= end_d}
    all_own_dates = [d for d, _ in commits]

    dirty, staged, untracked = status_counts(repo)
    upstream, ahead, behind, has_upstream = ahead_behind(repo)

    return {
        "repo": repo_name or repo.name,
        "path": Path(repo).as_posix(),
        "folder": folder,
        "remote": remote_url(repo),
        "branch": branch,
        "head": (head or "")[:7] or None,
        "commits_prior": sum(1 for d in all_own_dates if prior_start_d <= d <= prior_end_d),
        "commits_focus": sum(1 for d in all_own_dates if start_d <= d <= end_d),
        "active_days_focus": len(focus_dates),
        "last_commit_date": max(all_own_dates).isoformat() if all_own_dates else None,
        "tags_in_window": tags_in_window(repo, start_d, end_d, zone),
        "dirty_files": dirty,
        "staged_files": staged,
        "untracked_files": untracked,
        "ahead": ahead,
        "behind": behind,
        "has_upstream": has_upstream,
        "remote_state_as_of": remote_state_as_of(repo),
        "unmerged_branches": unmerged_branches(repo),
        "worktrees": worktrees(repo),
        "stashes": stashes(repo),
        "alias_of": None,
        "snapshot_utc": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Read-only git sweep of one or more repositories (C2).")
    parser.add_argument("--repo", action="append", required=True, dest="repos")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--prior-start", required=True, dest="prior_start")
    parser.add_argument("--tz", required=True)
    parser.add_argument("--author-pattern", required=True, dest="author_pattern")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="also write the JSON to this file")
    args = parser.parse_args(argv)

    records = []
    broken = 0
    for path in args.repos:
        try:
            records.append(sweep_repo(path, args.start, args.end, args.prior_start, args.tz, args.author_pattern))
        except Broken as exc:
            broken += 1
            records.append({"repo": Path(path).name, "path": str(Path(path).resolve()), "error": str(exc)})

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(records, indent=2))
    else:
        for r in records:
            if "error" in r:
                print("%s: BROKEN: %s" % (r["repo"], r["error"]))
            else:
                print("%s: head=%s focus=%d prior=%d ahead=%s behind=%s" % (
                    r["repo"], r["head"], r["commits_focus"], r["commits_prior"], r["ahead"], r["behind"]))
    if broken == len(records):
        return 2
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
