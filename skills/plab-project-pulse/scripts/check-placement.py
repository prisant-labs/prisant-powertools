#!/usr/bin/env python3
"""
check-placement.py - refuse to let a usage-audit bundle land somewhere a plain `git add`
could pick it up, before anything is written (Requirement 29, AC-22).

USAGE
-----
  check-placement.py <output-dir> [--allow-tracked]

This never creates `<output-dir>`. It only asks whether writing there would be safe, so
it can run before the skill writes a single file.

EXIT CODES
----------
  0  the folder is safe to write to: it is outside any git repository, or inside one
     that already ignores it (`git check-ignore`), or `--allow-tracked` was given
  1  the folder is inside a git repository that does NOT ignore it, and
     `--allow-tracked` was not given; the message names the two ways out
  2  the folder is inside a tree that contains a `.git` entry, but the `git` executable
     could not be run, so placement cannot be determined safely

NEVER INTERPRET 2 AS CLEAN. "git is not available" is not "the folder is fine"; it is
this check being unable to look, which is exactly the state this script exists to catch
before a write rather than after one.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys


def find_git_root(path):
    """Walk upward from `path` (which need not exist) for the nearest ancestor-or-self
    directory containing a `.git` entry. Returns that directory, or None."""
    cur = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def check_ignore(repo_root, path):
    """True if `git check-ignore` says `path` is ignored inside the repo at `repo_root`.
    Raises RuntimeError on anything other than git's own documented 0 (ignored) or
    1 (not ignored) exit codes."""
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", os.path.abspath(path)],
            cwd=repo_root,
            capture_output=True,
        )
    except OSError as exc:
        raise RuntimeError("could not run git check-ignore: %s" % exc)
    if result.returncode in (0, 1):
        return result.returncode == 0
    raise RuntimeError(
        "git check-ignore exited %d: %s"
        % (result.returncode, result.stderr.decode("utf-8", "replace").strip()))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check whether an output folder is a safe place to write a usage-audit bundle.")
    parser.add_argument("output_dir", help="the folder the bundle would be written into")
    parser.add_argument("--allow-tracked", action="store_true",
                         help="skip the check; the caller has already opted in")
    args = parser.parse_args(argv)
    path = args.output_dir

    if args.allow_tracked:
        print("CLEAN: --allow-tracked given; placement check skipped for %s" % path)
        return 0

    root = find_git_root(path)
    if root is None:
        print("CLEAN: %s is outside any git repository" % path)
        return 0

    if shutil.which("git") is None:
        print(
            "BROKEN: %s is inside a tree containing .git (%s), but the git executable is not "
            "available, so placement cannot be determined safely" % (path, root))
        return 2

    try:
        ignored = check_ignore(root, path)
    except RuntimeError as exc:
        print("BROKEN: %s" % exc)
        return 2

    if ignored:
        print("CLEAN: %s is inside a git repository (%s) that already ignores it" % (path, root))
        return 0

    print(
        "FINDINGS: %s is inside a git repository (%s) that does not ignore it. "
        "Pass --out to write somewhere else, or set `allow_tracked_output: true` in the settings "
        "file to write here on purpose." % (path, root))
    return 1


if __name__ == "__main__":
    sys.exit(main())
