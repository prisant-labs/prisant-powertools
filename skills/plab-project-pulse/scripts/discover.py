#!/usr/bin/env python3
"""Discover repositories and their session logs, fast, read-only.

PP-01 (project pulse): contract C1 in
docs/internal/release-plans/_unassigned/PP-01_project-pulse/spec.md. Both
`plab-project-pulse` and the usage-audit skill (UA-01) use this contract, so
its shape is kept generic rather than tailored to either skill's output.

USAGE
-----
  discover.py --root R [--root R2 ...] --max-depth N [--exclude GLOB ...]
             [--json] [--out FILE]

C1 rules this implements
-------------------------
  1. Walk each root to --max-depth. Stop descending once a directory holds
     `.git` (a repository never has its own subdirectories searched for
     more repositories; it does get its session-log stores read, by name,
     not by recursive search).
  2. A root that is itself a repository counts as one. Repositories
     directly under a root (depth 1) count.
  3. Never enter `node_modules`, `.git`, or any directory link or Windows
     junction. A link's target is read as a path (`os.path.realpath`,
     metadata only) without listing the link's own contents, so a link to
     a non-repository, a link to a repository found elsewhere, and a link
     whose target is never found are all handled without ever entering it.
     A link whose target matches another discovered repository is reported
     once, as that repository's alias, after every root has been walked
     (a link can be seen before its target is discovered).
  4. Session logs live in `_local/_session-logs/` (matched case-insensitively
     on `_local` only), at the top level and in `YYYY-MM/` month folders.
     `_superseded/` and `_capture/` are skipped. The older stores
     `_agent-context/session-log/` and `AGENTS/session-log/` are read flat
     (no month folders) when present.
  5. A log's date comes from its file name. A name that does not carry the
     `HH-MM_<llm>_` segment right after the date is still read, is listed
     with `nonstandard_name: true`, and is ordered by modification time
     within its day rather than by a time segment it does not have.

WHY `os.scandir`, NEVER `rglob`
--------------------------------
An unbounded recursive search timed out at five minutes on the maintainer's
own tree (spec.md C1 commentary, sourced from the hand-run reviews). Every
directory this module visits is visited through one `os.scandir` call per
level, stopped at `--max-depth` and at every repository root, so the cost is
bounded by the number of folders above and including each repository, never
by what is inside one.

JUNCTION DETECTION
-------------------
`os.path.islink` returns `False` for a Windows junction. From Python 3.12,
`os.path.isjunction` exists and is used first; the fallback checks
`os.stat(path, follow_symlinks=False).st_file_attributes` for
`FILE_ATTRIBUTE_REPARSE_POINT`, which is set for both a junction and a
symlink and is the attribute Windows itself uses to mark a reparse point.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import stat
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True

SKIP_DIR_NAMES = {"node_modules", ".git"}
SKIP_LOG_FOLDERS = {"_superseded", "_capture"}
MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")
STANDARD_LOG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2})_[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*_.+\.md$"
)
DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_.+\.md$")
LEGACY_LOG_STORES = (("_agent-context", "session-log"), ("AGENTS", "session-log"))


def is_reparse_point(path: str) -> bool:
    """True for a symlink or a Windows junction, without entering it."""
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is not None and isjunction(path):
        return True
    if os.path.islink(path):
        return True
    attr = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", None)
    if attr is None:
        return False
    try:
        st = os.stat(path, follow_symlinks=False)
    except OSError:
        return False
    return bool(getattr(st, "st_file_attributes", 0) & attr)


def is_repo_dir(path: str) -> bool:
    """A directory that holds `.git`, as a directory (ordinary clone) or a
    file (a linked worktree, which is what this very worktree is)."""
    return os.path.exists(os.path.join(path, ".git"))


def scandir_dirs(path):
    """Directory entries only, skipping anything scandir itself cannot stat
    (a dangling link, a permission error on one child) rather than failing
    the whole walk."""
    try:
        with os.scandir(path) as it:
            entries = list(it)
    except OSError:
        return []
    out = []
    for e in entries:
        try:
            if e.is_dir(follow_symlinks=False) or is_reparse_point(e.path):
                out.append(e)
        except OSError:
            continue
    return out


# ---------------------------------------------------------------------------
# Session logs
# ---------------------------------------------------------------------------


def _find_child_ci(path: str, name: str):
    """The first immediate child of `path` whose name matches `name`
    case-insensitively, or None. One scandir call, not a recursive search."""
    target = name.lower()
    try:
        with os.scandir(path) as it:
            for e in it:
                if e.name.lower() == target and e.is_dir(follow_symlinks=False):
                    return e.path
    except OSError:
        pass
    return None


def _classify_log_name(name: str):
    m = STANDARD_LOG_RE.match(name)
    if m:
        return m.group(1), m.group(2), False
    m = DATE_PREFIX_RE.match(name)
    if m:
        return m.group(1), None, True
    return None  # not a log at all


def _logs_in_folder(folder: str):
    """Non-recursive: the .md files directly inside `folder`."""
    out = []
    try:
        with os.scandir(folder) as it:
            entries = list(it)
    except OSError:
        return out
    for e in entries:
        if not e.is_file(follow_symlinks=False) or not e.name.lower().endswith(".md"):
            continue
        classified = _classify_log_name(e.name)
        if classified is None:
            continue
        date, time_part, nonstandard = classified
        try:
            mtime = dt.datetime.fromtimestamp(e.stat(follow_symlinks=False).st_mtime, tz=dt.timezone.utc)
        except OSError:
            mtime = None
        out.append({
            "file": Path(e.path).as_posix(),
            "date": date,
            "time": time_part,
            "nonstandard_name": nonstandard,
            "mtime": mtime.isoformat().replace("+00:00", "Z") if mtime else None,
        })
    return out


def find_session_logs(repo_path: str):
    """C1 rules 4 and 5. Returns a list of log records, newest first within
    each day by (time when standard, else mtime)."""
    logs = []
    local_dir = _find_child_ci(repo_path, "_local")
    if local_dir:
        store = _find_child_ci(local_dir, "_session-logs")
        if store:
            logs.extend(_logs_in_folder(store))
            try:
                with os.scandir(store) as it:
                    month_dirs = [e for e in it if e.is_dir(follow_symlinks=False)]
            except OSError:
                month_dirs = []
            for e in month_dirs:
                if e.name in SKIP_LOG_FOLDERS or e.name.lower() in {s.lower() for s in SKIP_LOG_FOLDERS}:
                    continue
                if MONTH_DIR_RE.match(e.name):
                    logs.extend(_logs_in_folder(e.path))
    for first, second in LEGACY_LOG_STORES:
        p = os.path.join(repo_path, first, second)
        if os.path.isdir(p):
            logs.extend(_logs_in_folder(p))
    logs.sort(key=lambda r: (r["date"] or "", r["time"] or r["mtime"] or ""), reverse=True)
    return logs


# ---------------------------------------------------------------------------
# Repository discovery
# ---------------------------------------------------------------------------


def _excluded(rel_posix: str, name: str, excludes):
    return any(fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(rel_posix, pat) for pat in excludes)


def _rel_name(repo_path: str, root: str) -> str:
    if os.path.normcase(os.path.abspath(repo_path)) == os.path.normcase(os.path.abspath(root)):
        return Path(root).name
    return Path(repo_path).resolve().relative_to(Path(root).resolve()).as_posix()


def discover(roots, max_depth, excludes=None):
    """Return (repos, link_records). `repos` carries every real repository
    found, each with `alias_of: None`; `link_records` carries every link or
    junction seen, for the caller (or `resolve_aliases`) to match against
    `repos` after every root has been walked."""
    excludes = excludes or []
    repos = []
    links = []

    def walk(root, current, depth):
        if depth > max_depth:
            return
        for e in scandir_dirs(current):
            if e.name in SKIP_DIR_NAMES:
                continue
            child_abs = str(Path(current).resolve() / e.name)
            rel_posix = Path(child_abs).relative_to(Path(root).resolve()).as_posix()
            if _excluded(rel_posix, e.name, excludes):
                continue
            if is_reparse_point(e.path):
                try:
                    target = os.path.realpath(e.path)
                except OSError:
                    target = None
                links.append({
                    "path": child_abs,
                    "root": str(Path(root).resolve()),
                    "rel": rel_posix,
                    "depth": depth,
                    "target_realpath": target,
                })
                continue  # never enter a link or junction
            if is_repo_dir(e.path):
                repos.append({
                    "path": child_abs,
                    "root": str(Path(root).resolve()),
                    "rel": rel_posix,
                    "depth": depth,
                    "alias_of": None,
                })
                continue  # never search inside a repository for more repos
            if depth < max_depth:
                walk(root, e.path, depth + 1)

    for root in roots:
        root_abs = str(Path(root).resolve())
        if is_repo_dir(root_abs):
            repos.append({
                "path": root_abs,
                "root": root_abs,
                "rel": Path(root_abs).name,
                "depth": 0,
                "alias_of": None,
            })
        else:
            walk(root_abs, root_abs, 1)

    return repos, links


def resolve_aliases(repos, links):
    """A link whose target resolves to a discovered repository becomes that
    repository's alias, reported once. Matching is by realpath, so a link
    seen before its target is irrelevant: this runs only after every root
    has been walked."""
    by_realpath = {}
    for r in repos:
        try:
            by_realpath[os.path.normcase(os.path.realpath(r["path"]))] = r
        except OSError:
            continue
    aliases = []
    seen_targets = set()
    for link in links:
        target = link.get("target_realpath")
        if not target:
            continue
        key = os.path.normcase(target)
        target_repo = by_realpath.get(key)
        if target_repo is None:
            continue
        if key in seen_targets:
            continue  # the same target aliased by more than one link: report once
        seen_targets.add(key)
        aliases.append({
            "path": link["path"],
            "root": link["root"],
            "rel": link["rel"],
            "depth": link["depth"],
            "alias_of": target_repo["rel"] if target_repo["root"] == link["root"] else target_repo["path"],
            "alias_of_path": target_repo["path"],
        })
    return aliases


def run(roots, max_depth, excludes=None):
    t0 = time.monotonic()
    repos, links = discover(roots, max_depth, excludes)
    aliases = resolve_aliases(repos, links)
    session_logs = {}
    for r in repos:
        session_logs[r["path"]] = find_session_logs(r["path"])
    elapsed = time.monotonic() - t0
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "roots": [str(Path(r).resolve()) for r in roots],
        "max_depth": max_depth,
        "excludes": excludes or [],
        "repos": repos,
        "aliases": aliases,
        "session_logs": session_logs,
        "timings": {"seconds": round(elapsed, 3)},
    }


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Discover repositories and their session logs (C1).")
    parser.add_argument("--root", action="append", required=True, help="a root to walk; repeatable")
    parser.add_argument("--max-depth", type=int, required=True, dest="max_depth")
    parser.add_argument("--exclude", action="append", default=[], help="a glob to skip; repeatable")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="also write the JSON to this file")
    args = parser.parse_args(argv)

    missing = [r for r in args.root if not os.path.isdir(r)]
    for m in missing:
        sys.stderr.write("discover.py: root does not exist, skipped: %s\n" % m)
    roots = [r for r in args.root if r not in missing]
    if not roots:
        sys.stderr.write("discover.py: no readable root\n")
        return 2

    result = run(roots, args.max_depth, args.exclude)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("%d repo(s), %d alias(es), %.2fs" % (len(result["repos"]), len(result["aliases"]), result["timings"]["seconds"]))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
