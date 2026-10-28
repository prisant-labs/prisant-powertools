#!/usr/bin/env python3
"""Fixture tests for derive-status-facts.py. No test framework required.

Run: python skills/plab-current-status/scripts/test-derive-status-facts.py

Every case builds a throwaway git repository in a temp directory, so the
tests never touch this plugin's own repository. `--today` pins the clock and
`--gh` names an executable that does not exist, so no case reads GitHub.

The canary for the level rule is not automated here, because it edits the
script under test rather than its input: per the implementation plan's
Phase 2 Verification, make the level always `git-only`, rerun this file, and
confirm the failure names "level"; then restore it.
"""

from __future__ import annotations

import hashlib
import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "derive-status-facts.py"
TODAY = "2026-02-01"
NO_GH = "plab-no-such-gh-executable"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "test@example.com")
    git(path, "config", "user.name", "Test")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "tag.gpgsign", "false")
    return path


def commit_all(repo: Path, message: str = "fixture", date: str = "2026-01-10T12:00:00") -> None:
    git(repo, "add", "-A")
    env_date = {"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    r = subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, **env_date})
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        raise RuntimeError("git commit failed: %s %s" % (r.stdout, r.stderr))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(repo: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--json", "--today", TODAY, "--gh", NO_GH, *extra],
        capture_output=True, text=True, encoding="utf-8",
    )


def facts(repo: Path, *extra: str) -> dict:
    r = run(repo, *extra)
    if r.returncode != 0:
        raise AssertionError("derive-status-facts.py exited %d: %s" % (r.returncode, r.stderr))
    return json.loads(r.stdout)


def gap_sources(f: dict) -> set[str]:
    return {g["source"] for g in f["gaps"]}


def hash_tree(repo: Path) -> dict[str, str]:
    out = {}
    for p in sorted(repo.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        out[str(p.relative_to(repo))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


SPEC = """---
id: X-01
type: spec
status: draft
created: 2026-01-05
---

# Spec

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|---|---|---|---|---|
| D1 | Still open | (none) | Open | (none) |
| D2 | Decided recently | Option A | Decided | 2026-01-28 |
| D3 | Decided long ago | Option B | Decided | 2026-01-02 |
"""

LOG = "---\ntype: session-log\n---\n\n## Waiting on You\n\n- **A task** (blocked since 2026-01-20). Pending.\n"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Isolate every git call, here and in the script under test, from the
        # machine's own configuration: a global excludes file that ignores
        # `_local/` (the maintainer's does) would make case 6 pass or fail by
        # machine rather than by fixture.
        empty = root / "empty-gitconfig"
        empty.write_text("", encoding="utf-8")
        os.environ["GIT_CONFIG_GLOBAL"] = str(empty)
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

        # 1. Not a repository: exit 2, named, nothing on stdout.
        plain = root / "not-a-repo"
        plain.mkdir()
        r = run(plain)
        check("a non-repository exits 2", r.returncode == 2, "exit=%d" % r.returncode)
        check("the broken exit names the cause", "not a git repository" in r.stderr, r.stderr)
        check("the broken exit prints nothing to stdout", r.stdout == "", repr(r.stdout))

        # 2. Git only: level, gaps, tag, commits, and gh unavailable is a gap, not a break.
        repo = init_repo(root / "git-only")
        write(repo / "README.md", "# A project\n")
        commit_all(repo, "first", "2026-01-10T12:00:00")
        git(repo, "tag", "v0.1.0")
        write(repo / "src.txt", "code\n")
        commit_all(repo, "second", "2026-01-12T12:00:00")
        f = facts(repo)
        check("level is git-only with neither logs nor typed documents", f["level"] == "git-only", f["level"])
        check("git-only gaps name the session logs and the decision documents",
              {"session logs", "decision documents"} <= gap_sources(f), str(gap_sources(f)))
        check("gh unavailable is a named gap and exit 0", "pull requests" in gap_sources(f), str(gap_sources(f)))
        check("no remote is a named gap", "remote" in gap_sources(f), str(gap_sources(f)))
        check("the latest tag is found", (f["git"]["latest_tag"] or {}).get("name") == "v0.1.0", str(f["git"]["latest_tag"]))
        check("one commit since the tag", f["git"]["commits_since_tag_count"] == 1, str(f["git"]["commits_since_tag"]))
        check("the tree is clean", f["git"]["dirty_count"] == 0, str(f["git"]["dirty_sample"]))
        check("every fact the spec names is present",
              all(k in f for k in ("repo", "level", "git", "pull_requests", "previous_status", "status_dir_ignored",
                                   "window", "session_logs", "decisions", "gaps"))
              and all(k in f["git"] for k in ("branch", "head", "dirty_count", "upstream", "ahead", "behind",
                                              "latest_tag", "commits_since_tag", "commits_since_window")),
              str(sorted(f)))
        check("with no previous snapshot, accomplishments run from the latest tag",
              f["window"]["accomplished_basis"] == "latest-tag" and f["window"]["accomplished_since"] == "2026-01-10",
              str(f["window"]))
        check("with no previous snapshot, decisions run from fourteen days back",
              f["window"]["decisions_since"] == "2026-01-18", str(f["window"]))

        # 3. Logs: a session log raises the level.
        repo = init_repo(root / "logs")
        write(repo / "README.md", "# A project\n")
        commit_all(repo)
        write(repo / "_local" / "_session-logs" / "2026-01-30_09-00_claude_work.md", LOG)
        f = facts(repo)
        check("level is logs with a session log and no typed documents", f["level"] == "logs", f["level"])
        check("the newest log is named", (f["session_logs"]["newest"] or "").endswith("2026-01-30_09-00_claude_work.md"),
              str(f["session_logs"]))
        check("the log's Waiting on You item arrives as pending",
              any(i.get("source_kind") == "waiting-on" for i in f["decisions"]["pending"]), str(f["decisions"]))

        # 4. Decisions: a typed spec raises the level, and the window splits answers.
        repo = init_repo(root / "decisions")
        write(repo / "docs" / "spec.md", SPEC)
        commit_all(repo)
        f = facts(repo)
        check("level is decisions with a typed spec", f["level"] == "decisions", f["level"])
        check("the open item is pending", [i["id"] for i in f["decisions"]["pending"]] == ["D1"], str(f["decisions"]["pending"]))
        check("only the answer inside the window is recent",
              [i["id"] for i in f["decisions"]["answered"]] == ["D2"], str(f["decisions"]["answered"]))
        check("decision documents are not a gap when a spec exists", "decision documents" not in gap_sources(f),
              str(gap_sources(f)))

        # 5. Previous snapshot: only the pattern counts, and it sets the windows.
        repo = init_repo(root / "previous")
        write(repo / "README.md", "# A project\n")
        commit_all(repo)
        status = repo / "_local" / "_status"
        write(status / "2026-01-20_opus-5-5_first-status-snapshot.md", "x\n")
        write(status / "2026-01-25_threads-consolidated.md", "hand-written, not a snapshot\n")
        write(status / "open-decisions.md", "a register, not a snapshot\n")
        logs = repo / "_local" / "_session-logs"
        write(logs / "2026-01-15_09-00_claude_before.md", LOG)
        write(logs / "2026-01" / "2026-01-22_09-00_claude_after.md", LOG)
        f = facts(repo)
        prev = f["previous_status"] or {}
        check("the previous snapshot is the newest matching file, not a hand-written one",
              prev.get("path") == "_local/_status/2026-01-20_opus-5-5_first-status-snapshot.md", str(prev))
        check("the snapshot's model and byline are parsed",
              prev.get("model") == "opus-5-5" and prev.get("byline") == "first-status-snapshot", str(prev))
        check("both windows start at the previous snapshot",
              f["window"]["accomplished_since"] == "2026-01-20" and f["window"]["decisions_since"] == "2026-01-20",
              str(f["window"]))
        check("logs since the previous snapshot include a month folder and exclude older logs",
              f["session_logs"]["since_previous"] == ["_local/_session-logs/2026-01/2026-01-22_09-00_claude_after.md"],
              str(f["session_logs"]))

        # 6. Whether _local/_status/ is ignored.
        check("an unignored status folder is reported as not ignored", f["status_dir_ignored"] is False, str(f["status_dir_ignored"]))
        write(repo / ".gitignore", "_local/\n")
        f = facts(repo)
        check("a status folder under an ignored _local/ is reported as ignored", f["status_dir_ignored"] is True,
              str(f["status_dir_ignored"]))

        # 7. A remote: fetch, upstream, ahead.
        remote = root / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], capture_output=True)
        repo = init_repo(root / "with-remote")
        write(repo / "README.md", "# A project\n")
        commit_all(repo)
        git(repo, "remote", "add", "origin", str(remote))
        git(repo, "push", "-q", "-u", "origin", "main")
        write(repo / "more.txt", "more\n")
        commit_all(repo, "ahead by one", "2026-01-11T12:00:00")
        f = facts(repo)
        check("the fetch succeeds against a reachable remote", f["git"]["fetch"] == "ok", str(f["git"]["fetch"]))
        check("ahead and behind are counted against the upstream",
              f["git"]["upstream"] == "origin/main" and f["git"]["ahead"] == 1 and f["git"]["behind"] == 0,
              "upstream=%s ahead=%s behind=%s" % (f["git"]["upstream"], f["git"]["ahead"], f["git"]["behind"]))
        f = facts(repo, "--no-fetch")
        check("--no-fetch skips the fetch and names the gap", f["git"]["fetch"] == "skipped" and "fetch" in gap_sources(f),
              str(f["git"]["fetch"]))

        # 8. No write in the working tree, and an uncommitted change is counted.
        repo = root / "previous"
        write(repo / "untracked.txt", "dirty\n")
        before = hash_tree(repo)
        f = facts(repo)
        after = hash_tree(repo)
        check("the facts script writes nothing in the working tree", before == after, "changed")
        check("an untracked file counts as a change", f["git"]["dirty_count"] >= 1, str(f["git"]["dirty_sample"]))

    failed = [name for name, ok, _ in results if not ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed.")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
