#!/usr/bin/env python3
"""Fixture tests for reconcile.py. No test framework required.

Run: python skills/plab-continue-session/scripts/test-reconcile.py

Every case builds a throwaway git repository (and, where needed, a throwaway bare "origin")
in a temp directory, so these tests never touch a real checkout. Commit and tag dates are
pinned with GIT_AUTHOR_DATE / GIT_COMMITTER_DATE so the date-fallback and tag-date cases are
deterministic regardless of when the suite runs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "reconcile.py"
RECONCILE_SOURCE = SCRIPT.read_text(encoding="utf-8")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def git(cwd, *args, env_extra=None):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError("git %s failed in %s: %s" % (" ".join(args), cwd, proc.stderr))
    return proc.stdout


def commit(cwd, message, date, files=None):
    """Write/update files, stage, and commit with a pinned author/committer date."""
    for name, content in (files or {}).items():
        path = Path(cwd) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(cwd, "add", "-A")
    git(cwd, "-c", "user.name=Test", "-c", "user.email=test@example.com",
        "commit", "-m", message,
        env_extra={"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
    return git(cwd, "rev-parse", "HEAD").strip()


def init_repo(root):
    repo = Path(root) / "repo"
    repo.mkdir(parents=True)
    git(repo, "init", "-b", "main")
    return repo


def init_bare_origin(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    origin = root / "origin.git"
    git(root, "init", "--bare", "-b", "main", str(origin))
    return origin


def run_reconcile(project_root, log_path, *extra_args):
    proc = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(project_root), str(log_path), *extra_args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc


def log_text(date, branch, repo="prisant-labs/prisant-utilities", commit_sha=None, prompt_body=""):
    fm = ["---", "date: %s" % date, "repo: %s" % repo, "branch: %s" % branch,
          "summary: test log", "status: completed",
          "files-changed:", "  - some/file.md", "  - other/file.md"]
    if commit_sha:
        fm.append("commit-sha: %s" % commit_sha)
    fm.append("---")
    body = "\n\n## Continuation Prompt\n\n" + prompt_body + "\n\n## Waiting on You\n\nNothing pending.\n"
    return "\n".join(fm) + body


def write_log(path, *args, **kwargs):
    Path(path).write_text(log_text(*args, **kwargs), encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)

        # ---------------------------------------------------------------
        # Shared fixture: a repo with a bare origin, an initial commit at
        # a pinned date, a rename, two more commits, and a tag cut after
        # the log date.
        # ---------------------------------------------------------------
        origin = init_bare_origin(tmp / "shared")
        repo = init_repo(tmp / "shared")
        git(repo, "remote", "add", "origin", str(origin))

        log_date = "2026-10-01T09:00:00-07:00"
        c0 = commit(repo, "initial", "2026-10-01T09:00:00-07:00", files={
            "real/fileA.md": "a\n",
            "docs/old-name.md": "renamed later\n",
        })
        git(repo, "push", "-u", "origin", "main")

        # A rename, landing after the log date: docs/old-name.md -> docs/new-name.md.
        git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "mv", "docs/old-name.md", "docs/new-name.md")
        git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "commit", "-m", "rename",
            env_extra={"GIT_AUTHOR_DATE": "2026-10-02T09:00:00-07:00",
                       "GIT_COMMITTER_DATE": "2026-10-02T09:00:00-07:00"})

        # A commit touching src/touched.md, used by the overlap test.
        c2 = commit(repo, "touch overlap file", "2026-10-03T09:00:00-07:00",
                     files={"src/touched.md": "content\n"})
        git(repo, "push", "origin", "main")

        # A tag cut after the log date.
        git(repo, "-c", "user.name=Test", "-c", "user.email=test@example.com",
            "tag", "-a", "v1.0.0", "-m", "release",
            env_extra={"GIT_COMMITTER_DATE": "2026-10-04T09:00:00-07:00"})
        git(repo, "push", "origin", "--tags")

        log_with_sha = tmp / "shared" / "log_with_sha.md"
        write_log(log_with_sha, log_date, "main", commit_sha=c0,
                  prompt_body="Finish the work. See `real/fileA.md` and `docs/old-name.md`. "
                              "Also touch `src/touched.md` and `docs/never-existed.md`.")

        log_date_only = tmp / "shared" / "log_date_only.md"
        write_log(log_date_only, log_date, "main",
                  prompt_body="Finish the work. See `real/fileA.md`.")

        # 1. Commit count via commit-sha.
        proc = run_reconcile(repo, log_with_sha, "--json")
        check("commit-sha path exits non-fatally", proc.returncode in (0, 1), proc.stderr)
        report = json.loads(proc.stdout)
        check("commit-sha: commits_since is a finding", report["checks"]["commits_since"]["state"] == "finding",
              report["checks"]["commits_since"])
        check("commit-sha: counts exactly 2 commits since c0",
              report["checks"]["commits_since"]["count"] == 2, report["checks"]["commits_since"])

        # 2. Commit count via date fallback (no commit-sha field).
        proc2 = run_reconcile(repo, log_date_only, "--json")
        report2 = json.loads(proc2.stdout)
        check("date-fallback: commits_since is a finding", report2["checks"]["commits_since"]["state"] == "finding",
              report2["checks"]["commits_since"])
        check("date-fallback agrees with commit-sha path on count",
              report2["checks"]["commits_since"]["count"] == report["checks"]["commits_since"]["count"],
              (report2["checks"]["commits_since"], report["checks"]["commits_since"]))

        # 3. Tag created after the log date.
        check("release_cut: v1.0.0 flagged as cut since the log",
              report["checks"]["release_cut"]["state"] == "finding"
              and "v1.0.0" in report["checks"]["release_cut"].get("new_tags", []),
              report["checks"]["release_cut"])

        # 4. Renamed file gets a rename hint; missing-with-no-hint stays a plain miss.
        missing = {m["cite"]: m["rename_hint"] for m in report["checks"]["path_existence"]["missing"]}
        check("path_existence: old-name.md flagged missing", "docs/old-name.md" in missing, missing)
        check("path_existence: rename hint points at new-name.md",
              missing.get("docs/old-name.md") == "docs/new-name.md", missing)
        check("path_existence: never-existed.md flagged missing with no hint",
              "docs/never-existed.md" in missing and missing["docs/never-existed.md"] is None, missing)
        check("path_existence: fileA.md (exists) not flagged", "real/fileA.md" not in missing, missing)

        # 5. File-overlap advisory.
        check("next_action_overlap: src/touched.md flagged",
              report["checks"]["next_action_overlap"]["state"] == "finding"
              and "src/touched.md" in report["checks"]["next_action_overlap"].get("overlap", []),
              report["checks"]["next_action_overlap"])

        # 6. No-mutation: HEAD, index and working tree are unchanged by either run above, and no
        # forbidden verb was ever invoked.
        head_after = git(repo, "rev-parse", "HEAD").strip()
        check("no-mutation: HEAD unchanged", head_after == c2, (head_after, c2))
        status_after = git(repo, "status", "--short")
        check("no-mutation: working tree clean", status_after.strip() == "", status_after)
        forbidden = {"pull", "merge", "checkout", "reset", "push"}
        bad_calls = [c for c in report["commands_run"] if len(c["argv"]) > 1 and c["argv"][1] in forbidden]
        check("no-mutation: no forbidden verb in commands_run", not bad_calls, bad_calls)
        check("no-mutation: fetch recorded as --no-prune",
              any(c["argv"][:2] == ["git", "fetch"] and "--no-prune" in c["argv"] for c in report["commands_run"]),
              report["commands_run"])

        # 6b. AC-2: every one of hygiene-sweep.md Check 1's six commands actually ran
        # (with the documented --no-prune deviation on the fetch), not just a subset.
        argvs = [c["argv"] for c in report["commands_run"]]
        check1_commands = [
            ["git", "fetch", "--no-prune", "origin", "--tags"],
            ["git", "status", "-sb"],
            ["git", "log", "--oneline", "HEAD..@{u}"],
            ["git", "log", "--oneline", "@{u}..HEAD"],
            ["git", "ls-remote", "--heads", "origin"],
            ["git", "tag", "-l"],
        ]
        missing_check1 = [cmd for cmd in check1_commands if cmd not in argvs]
        check("AC-2: all six hygiene-sweep Check 1 commands ran (--no-prune deviation aside)",
              not missing_check1, missing_check1)

        # 7. Markdown rendering is non-empty and names the broken/finding checks.
        proc_md = run_reconcile(repo, log_with_sha)
        check("markdown output exits matching json overall",
              proc_md.returncode == proc.returncode, (proc_md.returncode, proc.returncode))
        check("markdown mentions release cut", "v1.0.0" in proc_md.stdout, proc_md.stdout)

        # ---------------------------------------------------------------
        # 8. Branch deleted locally and on the remote.
        # ---------------------------------------------------------------
        git(repo, "branch", "feature/gone")
        git(repo, "push", "origin", "feature/gone")
        log_branch = tmp / "shared" / "log_branch.md"
        write_log(log_branch, log_date, "feature/gone", prompt_body="n/a")
        git(repo, "branch", "-D", "feature/gone")
        git(repo, "push", "origin", "--delete", "feature/gone")
        proc_branch = run_reconcile(repo, log_branch, "--json")
        report_branch = json.loads(proc_branch.stdout)
        check("branch_local: reports gone", report_branch["checks"]["branch_local"]["state"] == "finding",
              report_branch["checks"]["branch_local"])
        check("branch_remote: reports gone", report_branch["checks"]["branch_remote"]["state"] == "finding",
              report_branch["checks"]["branch_remote"])

        # ---------------------------------------------------------------
        # 9. Fetch failure: origin points at a path that does not exist. Must be BROKEN,
        # never silently clean.
        # ---------------------------------------------------------------
        broken_repo = init_repo(tmp / "broken-origin")
        commit(broken_repo, "initial", log_date, files={"a.md": "x\n"})
        git(broken_repo, "remote", "add", "origin", str(tmp / "does-not-exist.git"))
        log_broken = tmp / "broken-origin" / "log.md"
        write_log(log_broken, log_date, "main", prompt_body="n/a")
        proc_broken = run_reconcile(broken_repo, log_broken, "--json", "--fetch-timeout", "5")
        report_broken = json.loads(proc_broken.stdout)
        check("fetch failure: remote_fetch is broken",
              report_broken["checks"]["remote_fetch"]["state"] == "broken", report_broken["checks"]["remote_fetch"])
        check("fetch failure: overall exit is 2 (broken), never 0",
              proc_broken.returncode == 2, proc_broken.returncode)
        check("fetch failure: release_cut does not claim a clean result",
              report_broken["checks"]["release_cut"]["state"] == "broken", report_broken["checks"]["release_cut"])

        # ---------------------------------------------------------------
        # 9b. ahead_behind must not fail open on a dead remote once an upstream exists.
        # A repo with no upstream reports "no upstream configured" regardless of the
        # remote's reachability (fixture 9 above), which cannot exercise this branch; this
        # fixture pushes first so @{u} is real, then breaks the remote URL.
        # ---------------------------------------------------------------
        ab_origin = init_bare_origin(tmp / "ahead-behind")
        ab_repo = init_repo(tmp / "ahead-behind")
        git(ab_repo, "remote", "add", "origin", str(ab_origin))
        commit(ab_repo, "initial", log_date, files={"a.md": "x\n"})
        git(ab_repo, "push", "-u", "origin", "main")
        git(ab_repo, "remote", "set-url", "origin", str(tmp / "does-not-exist-2.git"))
        log_ab = tmp / "ahead-behind" / "log.md"
        write_log(log_ab, log_date, "main", prompt_body="n/a")
        proc_ab = run_reconcile(ab_repo, log_ab, "--json", "--fetch-timeout", "5")
        report_ab = json.loads(proc_ab.stdout)
        check("ahead_behind: broken on a dead remote with a real upstream (never fail-open)",
              report_ab["checks"]["ahead_behind"]["state"] == "broken", report_ab["checks"]["ahead_behind"])

        # ---------------------------------------------------------------
        # 10. Timeout path: an unreasonably small --fetch-timeout against a real origin.
        # ---------------------------------------------------------------
        proc_timeout = run_reconcile(repo, log_with_sha, "--json", "--fetch-timeout", "0.0001")
        report_timeout = json.loads(proc_timeout.stdout)
        check("timeout: remote_fetch is broken, not clean",
              report_timeout["checks"]["remote_fetch"]["state"] == "broken", report_timeout["checks"]["remote_fetch"])
        check("timeout: overall exit is 2, never 0",
              proc_timeout.returncode == 2, proc_timeout.returncode)

        # ---------------------------------------------------------------
        # 11. Canary: disable the rename-hint rule in the actual script file, prove the
        # rename-hint test above would now fail, then restore the file.
        # ---------------------------------------------------------------
        mutated = RECONCILE_SOURCE.replace(
            "def rename_hint(cwd, path, timeout, commands_run):",
            "def rename_hint(cwd, path, timeout, commands_run):\n"
            "    return None  # CANARY: rule disabled\n"
            "    # unreachable:",
            1,
        )
        if mutated == RECONCILE_SOURCE:
            check("canary: mutation target found in source", False, "rename_hint() signature not found")
        else:
            try:
                SCRIPT.write_text(mutated, encoding="utf-8")
                proc_canary = run_reconcile(repo, log_with_sha, "--json")
                report_canary = json.loads(proc_canary.stdout)
                canary_missing = {m["cite"]: m["rename_hint"]
                                   for m in report_canary["checks"]["path_existence"]["missing"]}
                check("canary: with the rule disabled, the rename-hint assertion now fails",
                      canary_missing.get("docs/old-name.md") != "docs/new-name.md", canary_missing)
            finally:
                SCRIPT.write_text(RECONCILE_SOURCE, encoding="utf-8")
            proc_restored = run_reconcile(repo, log_with_sha, "--json")
            report_restored = json.loads(proc_restored.stdout)
            restored_missing = {m["cite"]: m["rename_hint"]
                                 for m in report_restored["checks"]["path_existence"]["missing"]}
            check("canary: restored script passes the rename-hint assertion again",
                  restored_missing.get("docs/old-name.md") == "docs/new-name.md", restored_missing)

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
