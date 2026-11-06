#!/usr/bin/env python3
"""Gather the facts one /plab-ship run needs, in one call, without writing to the working tree.

USAGE
-----
  derive-ship-facts.py --repo <root> --json [--out <file>] [--no-fetch] [--gh <exe>]

EXIT-CODE CONTRACT
------------------
  0  the facts were gathered; every source that could not be read is a named gap
  2  BROKEN: the target is not a git repository, or a required step failed

NEVER INTERPRET 2 AS AN EMPTY RESULT. A `git fetch` may update remote-tracking
refs, which changes no tracked or untracked file. Nothing else here writes,
except the `--out` file, which belongs outside the repository.

WHY THE LATEST VERSION TAG IS NOT `git describe`
------------------------------------------------
`tools/merge-check.py --tag` in the maintainer's configuration writes backup
tags named `pre-merge/<date>-<branch>` before each merge. `git describe` returns
the nearest tag of any name, so it returns a backup. Measured in one repository
on 2026-11-05: a check starting from that answer saw 8 changed files where the
true range since the last release held 1,149. This script therefore lists tags,
keeps only those shaped like a version, and sorts them numerically. `v1`, a
floating major-version tag, is deliberately not a version here.

THE DOCUMENTATION MAP
---------------------
`.claude/plab-ship.local.md` may carry `human:`, `technical:`, `agentic:` and
`not-docs:` frontmatter lines, each a comma-separated list of globs. Without it
the script detects a map from the tracked files, and reports `source: detected`
so the skill can propose the map in its record.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
GATHER = Path(__file__).resolve().parents[2] / "plab-resolve-open-items" / "scripts" / "gather-backlog.py"
VERSION_TAG_RE = re.compile(r"^(v?)(\d+(?:\.\d+)+)$")
RECORD_DIR = "_local/_shipped"
SETTINGS = ".claude/plab-ship.local.md"
COMMIT_CAP = 200

DEFAULT_MAP = {
    "human": ["README*", "CHANGELOG*", "FAQ*", "GUIDE*", "CONTRIBUTING*", "docs/*"],
    "technical": ["docs/internal/*", "docs/adr/*", "docs/decisions/*", "ARCHITECTURE*", "DESIGN*", "*.schema.json"],
    "agentic": ["AGENTS.md", "CLAUDE.md", "GEMINI.md", "skills/*/SKILL.md", "skills/*/references/*",
                ".claude/rules/*", ".claude/agents/*", "agents/*"],
    "not-docs": ["evals/*", "tests/*", "test/*", "fixtures/*", "*/examples/*", "*/fixtures/*"],
}
VERSION_FILES = ("library.json", "package.json", "pyproject.toml", "Cargo.toml", "plugin.json",
                 ".claude-plugin/plugin.json", ".codex-plugin/plugin.json", "manifest.json")
OPEN_ITEM_FILES = ("OPEN.md", "docs/OPEN.md", "TODO.md", "BACKLOG.md")
RELEASE_DOCS = ("docs/internal/release-plans/release-checklist.yaml", "RELEASING.md", "docs/RELEASING.md",
                "docs/releasing.md")

PR_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: OPEN, first: 50) {
      nodes {
        number title headRefName baseRefName isDraft
        author { login }
        reviewThreads(first: 100) { nodes { isResolved } }
      }
    }
  }
}
"""


class Broken(Exception):
    pass


def run(cmd, cwd, timeout=30, env=None):
    try:
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env or GIT_ENV)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timed out after %ss" % timeout
    except OSError as exc:
        return 127, "", str(exc)


def git(repo, *args, timeout=30):
    return run(["git", "-C", str(repo), *args], repo, timeout=timeout)


def first_line(text):
    text = (text or "").strip()
    return text.splitlines()[0] if text else ""


def lines_of(text):
    return [line for line in (text or "").splitlines() if line.strip()]


def slug_of(url):
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?/?$", (url or "").strip())
    return m.group(1) if m else None


def version_tags(repo):
    """Every tag on the current history shaped like a version, newest first by number."""
    rc, out, err = git(repo, "tag", "--merged", "HEAD")
    if rc != 0:
        raise Broken("`git tag --merged HEAD` failed: %s" % first_line(err))
    all_tags = lines_of(out)
    shaped = []
    for tag in all_tags:
        m = VERSION_TAG_RE.match(tag)
        if m:
            shaped.append((tuple(int(p) for p in m.group(2).split(".")), tag, m.group(1)))
    shaped.sort(reverse=True)
    return shaped, len(all_tags) - len(shaped)


def default_branch(repo):
    rc, out, _ = git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if rc == 0 and out.strip():
        return out.strip().rsplit("/", 1)[-1]
    for name in ("main", "master"):
        rc, _, _ = git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/%s" % name)
        if rc == 0:
            return name
    return None


def commits_since(repo, tag):
    rev = "%s..HEAD" % tag if tag else "HEAD"
    rc, out, _ = git(repo, "log", "--format=%h%x09%s", "-n", str(COMMIT_CAP + 1), rev)
    if rc != 0:
        return [], False
    rows = [dict(zip(("sha", "subject"), line.split("\t", 1))) for line in lines_of(out) if "\t" in line]
    return rows[:COMMIT_CAP], len(rows) > COMMIT_CAP


def unreleased(repo):
    path = repo / "CHANGELOG.md"
    if not path.is_file():
        return {"path": None, "unreleased_lines": 0}
    count, inside = 0, False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("## "):
            inside = line.lower().startswith("## [unreleased]") or line.lower().startswith("## unreleased")
        elif inside and line.strip():
            count += 1
    return {"path": "CHANGELOG.md", "unreleased_lines": count}


def tag_workflows(repo):
    """Workflows that fire on a pushed tag: pushing a version tag publishes through these."""
    found = []
    folder = repo / ".github" / "workflows"
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if path.suffix in (".yml", ".yaml"):
                text = path.read_text(encoding="utf-8", errors="replace")
                if re.search(r"^\s*tags\s*:", text, re.M):
                    found.append(path.relative_to(repo).as_posix())
    return found


def worktrees(repo):
    rc, out, _ = git(repo, "worktree", "list", "--porcelain")
    rows, current = [], {}
    if rc != 0:
        return rows
    for line in out.splitlines() + [""]:
        if line.startswith("worktree "):
            current = {"path": line[9:]}
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")
        elif not line and current:
            rows.append(current)
            current = {}
    return rows


def local_branches(repo, base):
    if not base:
        return []
    rc, out, _ = git(repo, "for-each-ref", "--format=%(refname:short)%09%(upstream:track)", "refs/heads")
    if rc != 0:
        return []
    rows = []
    for line in lines_of(out):
        name, _, track = line.partition("\t")
        if name == base:
            continue
        rc, ahead, _ = git(repo, "rev-list", "--count", "%s..%s" % (base, name))
        rows.append({"name": name, "ahead_of_base": int(ahead.strip() or 0) if rc == 0 else None,
                     "upstream_gone": "[gone]" in track})
    return rows


def check_state(rollup):
    failing, pending, total = [], 0, 0
    for check in rollup or []:
        total += 1
        conclusion = (check.get("conclusion") or check.get("state") or "").upper()
        status = (check.get("status") or "").upper()
        if conclusion in ("FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"):
            failing.append(check.get("name") or check.get("context") or "unnamed")
        elif status and status != "COMPLETED" or conclusion in ("PENDING", "EXPECTED"):
            pending += 1
    state = "failing" if failing else "pending" if pending else "passing" if total else "none"
    return {"state": state, "failing": failing, "pending": pending, "total": total}


def pull_requests(repo, gh, slug, gaps):
    exe = shutil.which(gh)
    if exe is None:
        gaps.append({"source": "pull requests", "reason": "`%s` is not on PATH, so pull requests and their review threads were not read" % gh})
        return []
    if not slug or "/" not in slug:
        gaps.append({"source": "pull requests", "reason": "the repository has no GitHub remote to read"})
        return []
    env = os.environ.copy()
    owner, name = slug.split("/", 1)
    rc, out, err = run([exe, "api", "graphql", "-f", "query=%s" % PR_QUERY, "-F", "owner=%s" % owner,
                        "-F", "name=%s" % name], repo, env=env)
    if rc != 0:
        gaps.append({"source": "pull requests", "reason": "`gh api graphql` failed (%s)" % (first_line(err) or "exit %d" % rc)})
        return []
    nodes = json.loads(out)["data"]["repository"]["pullRequests"]["nodes"]
    prs = {}
    for node in nodes:
        threads = (node.get("reviewThreads") or {}).get("nodes") or []
        prs[node["number"]] = {
            "number": node["number"], "title": node["title"], "head": node["headRefName"],
            "base": node["baseRefName"], "draft": node["isDraft"],
            "author": (node.get("author") or {}).get("login"),
            "unresolved_threads": sum(1 for t in threads if not t.get("isResolved")),
            "checks": {"state": "unknown", "failing": [], "pending": 0, "total": 0},
        }
    rc, out, err = run([exe, "pr", "list", "--state", "open", "--json", "number,statusCheckRollup", "--limit", "50"],
                       repo, env=env)
    if rc == 0:
        for row in json.loads(out or "[]"):
            if row["number"] in prs:
                prs[row["number"]]["checks"] = check_state(row.get("statusCheckRollup"))
    else:
        gaps.append({"source": "pull request checks", "reason": "`gh pr list` failed (%s)" % (first_line(err) or "exit %d" % rc)})
    return [prs[n] for n in sorted(prs)]


def pending_decisions(repo, gaps):
    if not GATHER.is_file():
        gaps.append({"source": "pending decisions", "reason": "the decisions sweep is missing from the plugin: %s" % GATHER.name})
        return []
    rc, out, err = run([sys.executable, "-B", str(GATHER), "--repo", str(repo), "--json"], repo, timeout=60)
    if rc != 0:
        gaps.append({"source": "pending decisions", "reason": "the decisions sweep exited %d (%s)" % (rc, first_line(err))})
        return []
    return [{k: item.get(k) for k in ("id", "title", "home", "status", "age_days") if k in item}
            for item in json.loads(out or "[]") if item.get("kind", "pending") == "pending"]


def settings_map(repo):
    path = repo / SETTINGS
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    found = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^(human|technical|agentic|not-docs):\s*(.*)$", line)
        if m:
            found[m.group(1)] = [g.strip() for g in m.group(2).split(",") if g.strip()]
    return found or None


def matches(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def doc_map(repo):
    configured = settings_map(repo)
    globs = dict(DEFAULT_MAP, **(configured or {}))
    rc, out, _ = git(repo, "ls-files")
    tracked = lines_of(out) if rc == 0 else []
    counts = {}
    for layer in ("technical", "agentic", "human"):
        counts[layer] = 0
    for path in tracked:
        if matches(path, globs["not-docs"]):
            continue
        # Order matters: docs/internal/* also matches the human docs/* glob.
        for layer in ("technical", "agentic", "human"):
            if matches(path, globs[layer]):
                counts[layer] += 1
                break
    return {"source": "settings" if configured else "detected", "settings_file": SETTINGS,
            "globs": globs, "tracked_counts": counts}


def derive(repo_arg, do_fetch, gh):
    rc, out, err = run(["git", "-C", str(repo_arg), "rev-parse", "--show-toplevel"], repo_arg)
    if rc != 0:
        raise Broken("not a git repository: %s (%s)" % (repo_arg, first_line(err)))
    repo = Path(out.strip()).resolve()
    gaps = []

    rc, url, _ = git(repo, "remote", "get-url", "origin")
    has_remote = rc == 0 and bool(url.strip())
    slug = slug_of(url) if has_remote else None
    if not has_remote:
        gaps.append({"source": "remote", "reason": "the repository has no `origin` remote"})
    elif do_fetch:
        rc, _, err = git(repo, "fetch", "--quiet", "--prune", "origin", timeout=60)
        if rc != 0:
            gaps.append({"source": "fetch", "reason": "`git fetch` failed, so the remote comparison is as of the last fetch (%s)" % first_line(err)})
    else:
        gaps.append({"source": "fetch", "reason": "--no-fetch was passed, so the remote comparison is as of the last fetch"})

    rc, head, err = git(repo, "rev-parse", "--short", "HEAD")
    if rc != 0:
        raise Broken("the repository has no commits: %s" % first_line(err))
    _, branch, _ = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    _, status, _ = git(repo, "status", "--porcelain")
    base = default_branch(repo)
    upstream = None
    rc, counts, _ = git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    if rc == 0 and counts.split():
        ahead, behind = counts.split()
        upstream = {"ahead": int(ahead), "behind": int(behind)}

    ignored = git(repo, "check-ignore", "-q", "%s/probe.md" % RECORD_DIR)[0] == 0
    _, tracked_local, _ = git(repo, "ls-files", "_local", "_LOCAL")

    tags, other_tags = version_tags(repo)
    latest = tags[0] if tags else None
    rows, truncated = commits_since(repo, latest[1] if latest else None)

    version_files = [f for f in VERSION_FILES if (repo / f).is_file()]
    return {
        "repo": slug or repo.name,
        "root": repo.as_posix(),
        "branch": branch.strip(),
        "default_branch": base,
        "head": head.strip(),
        "tree_clean": not status.strip(),
        "dirty_files": [line[3:] for line in lines_of(status)],
        "upstream": upstream,
        "record_dir": RECORD_DIR,
        "record_dir_ignored": ignored,
        "tracked_local_files": lines_of(tracked_local),
        "release": {
            "latest_version_tag": latest[1] if latest else None,
            "tag_prefix": latest[2] if latest else None,
            "tag_parts": len(latest[0]) if latest else None,
            "other_tags_ignored": other_tags,
            "commits_since_tag": rows,
            "commits_truncated": truncated,
            "changelog": unreleased(repo),
            "version_files": version_files,
            "tag_workflows": tag_workflows(repo),
            "release_docs": [f for f in RELEASE_DOCS if (repo / f).is_file()],
            "plugin_repo": (repo / "library.json").is_file(),
        },
        "open_item_files": [f for f in OPEN_ITEM_FILES if (repo / f).is_file()],
        "worktrees": worktrees(repo),
        "local_branches": local_branches(repo, base),
        "pull_requests": pull_requests(repo, gh, slug, gaps),
        "pending_decisions": pending_decisions(repo, gaps),
        "doc_map": doc_map(repo),
        "gaps": gaps,
    }


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Gather the facts one /plab-ship run needs.")
    parser.add_argument("--repo", default=".", help="the repository root (default: the current folder)")
    parser.add_argument("--json", action="store_true", help="print the facts as JSON (the only output format)")
    parser.add_argument("--out", help="write the JSON to this file, which belongs outside the repository, and print one summary line")
    parser.add_argument("--no-fetch", action="store_true", help="skip `git fetch`; the remote comparison then becomes a named gap")
    parser.add_argument("--gh", default="gh", help="the GitHub CLI executable (default: gh)")
    args = parser.parse_args(argv)
    try:
        facts = derive(args.repo, not args.no_fetch, args.gh)
    except (Broken, OSError, ValueError, KeyError) as exc:
        print("BROKEN: %s" % exc)
        return 2
    text = json.dumps(facts, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print("facts: %s on %s, latest version tag %s, %d open pull request(s), %d gap(s); wrote %s" % (
            facts["repo"], facts["branch"], facts["release"]["latest_version_tag"],
            len(facts["pull_requests"]), len(facts["gaps"]), args.out))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
