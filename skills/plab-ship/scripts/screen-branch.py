#!/usr/bin/env python3
"""Screen one branch before it merges: nothing under _local/, and no credential in what it adds.

USAGE
-----
  screen-branch.py --repo <root> --range <base>..<head>

EXIT-CODE CONTRACT
------------------
  0  CLEAN     nothing was found
  1  FINDINGS  each is named by file and pattern; a value is never printed
  2  BROKEN    the range could not be read

NEVER INTERPRET 2 AS CLEAN.

WHY THIS RUNS BEFORE THE MERGE, AND WHAT IT DOES NOT PROVE
----------------------------------------------------------
The prompt this skill replaced checked for secrets after merging, when a secret
has already reached `main`. A session measurement of 2026-11-05 found that a
secret scanner ran in 0 of 8 past runs and a `_local/` check in 1 of 8, so the
check is a script here rather than a line of advice.

This is a pattern screen over added lines, not a full secret scanner. It finds
the common credential shapes and the common credential file names. A clean
result means none of those matched, never that the branch holds no secret. The
skill reports that limit in its record.

THE VALUE IS NEVER PRINTED
--------------------------
Output names the file, the pattern and how many lines matched. A transcript or
log that quotes this script's output therefore cannot leak what it found.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys

GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")

PATTERNS = [
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-style-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{20,}")),
    ("private-key-block", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("assigned-secret", re.compile(
        r"""(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b["']?\s*[:=]\s*["'][A-Za-z0-9+/_.-]{16,}["']""")),
]
SENSITIVE_NAMES = (".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa", "id_ed25519",
                   "credentials.json", ".credentials.json", "credentials.yml", ".npmrc", ".pypirc")
HARMLESS_NAMES = (".env.example", ".env.sample", ".env.template")


class Broken(Exception):
    pass


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, env=GIT_ENV)
    if r.returncode != 0:
        raise Broken("`git %s` failed: %s" % (" ".join(args[:2]), (r.stderr or "").strip().splitlines()[:1]))
    return r.stdout


def screen(repo, rng):
    if ".." not in rng:
        raise Broken("the range must read <base>..<head>: %s" % rng)
    head = rng.split("..")[-1] or "HEAD"
    findings = []

    tree = git(repo, "ls-tree", "-r", "--name-only", head)
    for path in tree.splitlines():
        if path.lower().startswith("_local/"):
            findings.append("tracked-local: %s is tracked under _local/" % path)

    for path in git(repo, "diff", "--name-only", "--diff-filter=AMR", rng).splitlines():
        name = path.rsplit("/", 1)[-1]
        if name not in HARMLESS_NAMES and any(fnmatch.fnmatch(name, p) for p in SENSITIVE_NAMES):
            findings.append("sensitive-name: %s has a name that usually holds a credential" % path)

    hits, current = {}, None
    for line in git(repo, "diff", "--unified=0", "--no-color", rng).splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and current:
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    hits[(current, name)] = hits.get((current, name), 0) + 1
    for (path, name), count in sorted(hits.items()):
        findings.append("credential-pattern: %s matched %s on %d added line(s)" % (path, name, count))
    return findings


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Screen one branch before it merges.")
    parser.add_argument("--repo", default=".", help="the repository root (default: the current folder)")
    parser.add_argument("--range", required=True, dest="rng", help="the branch's commits, as <base>..<head>")
    args = parser.parse_args(argv)
    try:
        findings = screen(args.repo, args.rng)
    except (Broken, OSError, subprocess.TimeoutExpired) as exc:
        print("BROKEN: %s" % exc)
        return 2
    for finding in findings:
        print(finding)
    if findings:
        print("FINDINGS: %d in %s. Do not merge; report these to the maintainer." % (len(findings), args.rng))
        return 1
    print("CLEAN: nothing under _local/ and no known credential shape in %s. This is a pattern screen, not proof that no secret exists." % args.rng)
    return 0


if __name__ == "__main__":
    sys.exit(main())
