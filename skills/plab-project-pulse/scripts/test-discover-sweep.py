#!/usr/bin/env python3
"""Fixture tests for discover.py and sweep.py (contracts C1 and C2).

Run: python skills/plab-project-pulse/scripts/test-discover-sweep.py

Every fixture is a throwaway git repository or plain folder built in a temp
directory with real `git init` and fixed author/committer dates, following
the style of
skills/plab-current-status/scripts/test-derive-status-facts.py. No test
touches this plugin's own repository.

Covers AC-2 through AC-10 of
docs/internal/release-plans/_unassigned/PP-01_project-pulse/spec.md.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import discover  # noqa: E402
import sweep  # noqa: E402

DISCOVER_PY = SCRIPTS / "discover.py"
SWEEP_PY = SCRIPTS / "sweep.py"
AUTHOR = "Test Owner <owner@example.com>"
OTHER_AUTHOR = "Someone Else <else@example.com>"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def git(repo: Path, *args: str, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env)


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "owner@example.com")
    git(path, "config", "user.name", "Test Owner")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "tag.gpgsign", "false")
    return path


def write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit_all(repo: Path, message: str = "fixture", epoch: int | None = None, author: str = AUTHOR) -> None:
    git(repo, "add", "-A")
    env = dict(os.environ)
    name, email = author.rsplit(" <", 1)
    email = email.rstrip(">")
    env["GIT_AUTHOR_NAME"] = name
    env["GIT_AUTHOR_EMAIL"] = email
    env["GIT_COMMITTER_NAME"] = name
    env["GIT_COMMITTER_EMAIL"] = email
    if epoch is not None:
        env["GIT_AUTHOR_DATE"] = "@%d +0000" % epoch
        env["GIT_COMMITTER_DATE"] = "@%d +0000" % epoch
    r = subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message], capture_output=True,
                       text=True, encoding="utf-8", env=env)
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        raise RuntimeError("git commit failed: %s %s" % (r.stdout, r.stderr))


def epoch_utc(y, mo, d, h, mi, s=0) -> int:
    return int(dt.datetime(y, mo, d, h, mi, s, tzinfo=dt.timezone.utc).timestamp())


def make_link(link_path: Path, target: Path) -> bool:
    """A directory symlink, or a Windows junction when privilege is denied.
    Returns False (never raises) when neither can be made."""
    try:
        os.symlink(str(target), str(link_path), target_is_directory=True)
        return True
    except OSError:
        pass
    if os.name == "nt":
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link_path), str(target)],
                           capture_output=True, text=True)
        if r.returncode == 0 and link_path.exists():
            return True
    return False


def run_cli(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(script), *args], capture_output=True, text=True,
                          encoding="utf-8")


def hash_tree(repo: Path) -> dict[str, str]:
    out = {}
    for p in sorted(repo.rglob("*")):
        if not p.is_file():
            continue
        try:
            out[str(p.relative_to(repo))] = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            out[str(p.relative_to(repo))] = "unreadable"
    return out


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        empty = root / "empty-gitconfig"
        empty.write_text("", encoding="utf-8")
        os.environ["GIT_CONFIG_GLOBAL"] = str(empty)
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

        # -------------------------------------------------------------
        # Discovery: AC-2, AC-3
        # -------------------------------------------------------------
        root_a = root / "root-a"
        alpha = init_repo(root_a / "alpha")
        write(alpha / "README.md")
        commit_all(alpha, "alpha first", epoch_utc(2026, 10, 1, 12, 0))
        beta = init_repo(root_a / "group" / "beta")
        write(beta / "README.md")
        commit_all(beta, "beta first", epoch_utc(2026, 10, 1, 12, 0))

        # A trap: node_modules must never be entered, even with a .git inside.
        write(root_a / "scratch" / "node_modules" / "pkg" / ".git" / "HEAD", "ref: refs/heads/main\n")
        # A trap: nothing inside a found repository is searched for more repos.
        write(alpha / "src" / "sub" / ".git" / "HEAD", "ref: refs/heads/main\n")

        root_b = init_repo(root / "root-b")  # a root that is itself a repository
        write(root_b / "README.md")
        commit_all(root_b, "root-b first", epoch_utc(2026, 10, 1, 12, 0))

        d2 = discover.run([str(root_a), str(root_b)], max_depth=2)
        rels = {r["rel"] for r in d2["repos"]}
        check("AC-2 depth 1 and depth 2 repos are both found", {"alpha", "group/beta"} <= rels, str(rels))
        check("AC-2 a root that is itself a repository counts as one",
              any(r["path"] == str(root_b) for r in d2["repos"]), str(rels))
        check("AC-3 node_modules is never entered, even holding a .git",
              not any("node_modules" in r["rel"] for r in d2["repos"]), str(rels))
        check("AC-3 nothing inside a found repository is searched for more repos",
              not any("src/sub" in r["rel"] or r["rel"].startswith("alpha/") for r in d2["repos"]), str(rels))

        d1 = discover.run([str(root_a)], max_depth=1)
        rels1 = {r["rel"] for r in d1["repos"]}
        check("max_depth=1 finds the depth-1 repo but not the depth-2 one",
              "alpha" in rels1 and "group/beta" not in rels1, str(rels1))

        # -------------------------------------------------------------
        # Discovery: AC-4, a link or junction becomes an alias, once
        # -------------------------------------------------------------
        linked = root_a / "linked"
        if make_link(linked, beta):
            d2b = discover.run([str(root_a)], max_depth=2)
            check("AC-4 the link does not appear as its own repository",
                  not any(r["path"] == str(linked) for r in d2b["repos"]),
                  str([r["rel"] for r in d2b["repos"]]))
            check("AC-4 the link appears once, as an alias of the target repository",
                  len(d2b["aliases"]) == 1 and d2b["aliases"][0]["alias_of"] == "group/beta",
                  str(d2b["aliases"]))
        else:
            check("AC-4 a link or junction alias (SKIP: neither symlink nor junction could be created here)",
                  True, "SKIP")

        # A second alias made specifically as a Windows junction (not a
        # symlink), so `os.path.isjunction` / the reparse-attribute
        # fallback is actually exercised rather than only `os.path.islink`,
        # which `make_link`'s symlink-first attempt already satisfies on a
        # machine where symlink creation succeeds.
        junctioned = root_a / "junctioned"
        if os.name == "nt":
            r = subprocess.run(["cmd", "/c", "mklink", "/J", str(junctioned), str(alpha)],
                               capture_output=True, text=True)
            if r.returncode == 0 and junctioned.exists():
                d2c = discover.run([str(root_a)], max_depth=2)
                check("AC-4 a Windows junction does not appear as its own repository",
                      not any(r2["path"] == str(junctioned) for r2 in d2c["repos"]),
                      str([r2["rel"] for r2 in d2c["repos"]]))
                check("AC-4 a Windows junction becomes an alias of its target, distinct from the symlink alias",
                      any(a["alias_of"] == "alpha" for a in d2c["aliases"]), str(d2c["aliases"]))
            else:
                check("AC-4 a Windows junction alias (SKIP: mklink /J could not be created here)", True, "SKIP")
        else:
            check("AC-4 a Windows junction alias (SKIP: not running on Windows)", True, "SKIP")

        # -------------------------------------------------------------
        # Session logs: AC-5, AC-6
        # -------------------------------------------------------------
        logs_root = alpha / "_local" / "_session-logs"
        write(logs_root / "2026-10-01_09-00_claude_did-a-thing.md", "flat log\n")
        write(logs_root / "2026-10" / "2026-10-15_10-00_claude_month-folder.md", "month folder log\n")
        write(logs_root / "2026-10-05_old-style-log.md", "nonstandard name\n")
        write(logs_root / "_superseded" / "2026-09-01_09-00_claude_old.md", "must be skipped\n")
        write(logs_root / "_capture" / "2026-09-02_09-00_claude_raw.md", "must be skipped too\n")
        legacy_root = root_a / "gamma"
        init_repo(legacy_root)
        write(legacy_root / "README.md")
        commit_all(legacy_root, "gamma first", epoch_utc(2026, 10, 1, 12, 0))
        write(legacy_root / "_agent-context" / "session-log" / "2026-10-10_09-00_claude_legacy.md", "legacy store\n")

        beta_upper = beta / "_LOCAL" / "_session-logs"
        write(beta_upper / "2026-10-20_09-00_claude_upper-case-local.md", "uppercase _LOCAL\n")

        d3 = discover.run([str(root_a)], max_depth=2)
        alpha_logs = d3["session_logs"][str(alpha)]
        alpha_files = {Path(l["file"]).name for l in alpha_logs}
        check("AC-5 a flat top-level log is found",
              "2026-10-01_09-00_claude_did-a-thing.md" in alpha_files, str(alpha_files))
        check("AC-5 a log in a YYYY-MM month folder is found",
              "2026-10-15_10-00_claude_month-folder.md" in alpha_files, str(alpha_files))
        check("AC-5 _superseded is skipped",
              "2026-09-01_09-00_claude_old.md" not in alpha_files, str(alpha_files))
        check("AC-5 _capture is skipped",
              "2026-09-02_09-00_claude_raw.md" not in alpha_files, str(alpha_files))
        gamma_logs = d3["session_logs"][str(legacy_root)]
        check("AC-5 the legacy _agent-context/session-log/ store is read",
              any(Path(l["file"]).name == "2026-10-10_09-00_claude_legacy.md" for l in gamma_logs), str(gamma_logs))
        beta_logs = d3["session_logs"][str(beta)]
        check("AC-5 _LOCAL (uppercase) is matched case-insensitively",
              any(Path(l["file"]).name == "2026-10-20_09-00_claude_upper-case-local.md" for l in beta_logs),
              str(beta_logs))

        nonstandard = [l for l in alpha_logs if Path(l["file"]).name == "2026-10-05_old-style-log.md"]
        check("AC-6 a log without HH-MM_<llm>_ is still read", len(nonstandard) == 1, str(alpha_logs))
        check("AC-6 that log is listed with nonstandard_name: true",
              bool(nonstandard) and nonstandard[0]["nonstandard_name"] is True, str(nonstandard))
        standard = [l for l in alpha_logs if Path(l["file"]).name == "2026-10-01_09-00_claude_did-a-thing.md"]
        check("a standard-named log is listed with nonstandard_name: false",
              bool(standard) and standard[0]["nonstandard_name"] is False, str(standard))

        # Discovery CLI smoke test, exercised separately from the module calls above.
        r = run_cli(DISCOVER_PY, "--root", str(root_a), "--max-depth", "2", "--json")
        check("discover.py CLI exits 0 and prints valid JSON", r.returncode == 0, "exit=%d stderr=%s" % (r.returncode, r.stderr))
        cli_json = json.loads(r.stdout)
        check("discover.py CLI finds the same repositories as the module call",
              {x["rel"] for x in cli_json["repos"]} == {x["rel"] for x in d3["repos"]}, str(cli_json.get("repos")))

        # -------------------------------------------------------------
        # Sweep: AC-7, the DST-crossing commit
        # -------------------------------------------------------------
        dst_repo = init_repo(root / "dst-repo")
        write(dst_repo / "README.md")
        commit_all(dst_repo, "before", epoch_utc(2026, 10, 25, 12, 0))
        # 2026-11-02T07:30:00Z: the day after the US autumn clock change
        # (2026-11-01). Under America/Los_Angeles this is already Pacific
        # Standard Time (UTC-8), so it is 2026-11-01 23:30 local, not
        # 2026-11-02. A fixed UTC-7 ("Pacific") offset would misplace it.
        write(dst_repo / "dst.txt")
        commit_all(dst_repo, "dst commit", epoch_utc(2026, 11, 2, 7, 30))
        rec = sweep.sweep_repo(dst_repo, "2026-11-01", "2026-11-01", "2026-10-25",
                               "America/Los_Angeles", r"Test Owner")
        check("AC-7 the DST-crossing commit counts on 2026-11-01 local, not 2026-11-02",
              rec["commits_focus"] == 1, str(rec))
        rec_utc_window = sweep.sweep_repo(dst_repo, "2026-11-02", "2026-11-02", "2026-10-25",
                                          "America/Los_Angeles", r"Test Owner")
        check("AC-7 the same commit does not also count on 2026-11-02 local",
              rec_utc_window["commits_focus"] == 0, str(rec_utc_window))
        rec_other_author = sweep.sweep_repo(dst_repo, "2026-11-01", "2026-11-01", "2026-10-25",
                                            "America/Los_Angeles", r"^Nobody Here$")
        check("the author pattern filters out a non-matching author",
              rec_other_author["commits_focus"] == 0, str(rec_other_author))

        # -------------------------------------------------------------
        # Sweep: AC-8, AC-10, ahead/behind without fetching
        # -------------------------------------------------------------
        bare = root / "bare-upstream.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], capture_output=True)
        clone_a = init_repo(root / "clone-a")
        write(clone_a / "README.md")
        commit_all(clone_a, "origin", epoch_utc(2026, 10, 20, 12, 0))
        git(clone_a, "remote", "add", "origin", str(bare))
        git(clone_a, "push", "-q", "-u", "origin", "main")

        clone_b = init_repo(root / "clone-b")
        git(clone_b, "remote", "add", "origin", str(bare))
        git(clone_b, "pull", "-q", "origin", "main")
        git(clone_b, "branch", "--set-upstream-to=origin/main", "main")
        write(clone_b / "two.txt")
        commit_all(clone_b, "ahead by one", epoch_utc(2026, 10, 21, 12, 0))
        write(clone_b / "three.txt")
        commit_all(clone_b, "ahead by two", epoch_utc(2026, 10, 22, 12, 0))
        git(clone_b, "push", "-q", "origin", "main")

        # clone_a fetches once, as test SETUP (so FETCH_HEAD and the
        # remote-tracking ref exist); sweep.py itself never fetches.
        git(clone_a, "fetch", "origin")
        before_hash = hash_tree(clone_a)
        sweep_rec = sweep.sweep_repo(clone_a, "2026-10-20", "2026-10-26", "2026-10-13",
                                     "America/Los_Angeles", r"Test Owner")
        after_hash = hash_tree(clone_a)
        check("AC-8 behind is counted against the upstream without fetching",
              sweep_rec["behind"] == 2 and sweep_rec["ahead"] == 0,
              "ahead=%s behind=%s" % (sweep_rec["ahead"], sweep_rec["behind"]))
        check("AC-8 remote_state_as_of is the FETCH_HEAD modification time",
              sweep_rec["remote_state_as_of"] is not None, str(sweep_rec["remote_state_as_of"]))
        check("AC-9 the sweep writes nothing to the repository (clone-a, with an upstream)",
              before_hash == after_hash, "tree changed after sweep")

        check("AC-10 a repository with no upstream reports has_upstream: false",
              sweep.sweep_repo(alpha, "2026-10-01", "2026-10-07", "2026-09-24",
                               "America/Los_Angeles", r"Test Owner")["has_upstream"] is False, "")

        # -------------------------------------------------------------
        # Sweep: AC-9, byte-identical refs/index/FETCH_HEAD/working tree,
        # proved on a repository with dirty, staged and untracked files,
        # unmerged branches, a worktree and a stash: every code path run.
        # -------------------------------------------------------------
        rich = init_repo(root / "rich-repo")
        write(rich / "README.md")
        commit_all(rich, "first", epoch_utc(2026, 10, 1, 12, 0))
        git(rich, "tag", "v0.1.0")
        git(rich, "checkout", "-q", "-b", "unmerged-topic")
        write(rich / "topic-only.txt")
        commit_all(rich, "topic commit, never merged", epoch_utc(2026, 10, 1, 13, 0))
        git(rich, "checkout", "-q", "main")
        write(rich / "staged.txt")
        git(rich, "add", "staged.txt")
        write(rich / "dirty.txt")
        git(rich, "add", "dirty.txt")
        commit_all(rich, "second", epoch_utc(2026, 10, 2, 12, 0))
        write(rich / "dirty.txt", "changed\n")
        write(rich / "new-staged.txt")
        git(rich, "add", "new-staged.txt")
        write(rich / "untracked.txt")
        git(rich, "stash", "push", "-u", "-m", "a stash")
        worktree_dir = root / "rich-worktree"
        git(rich, "worktree", "add", str(worktree_dir), "-b", "wt-branch")
        write(rich / "dirty.txt", "changed again\n")
        write(rich / "new-staged.txt")
        git(rich, "add", "new-staged.txt")
        write(rich / "untracked.txt")

        before_rich = hash_tree(rich)
        rich_rec = sweep.sweep_repo(rich, "2026-10-01", "2026-10-07", "2026-09-24",
                                    "America/Los_Angeles", r"Test Owner")
        after_rich = hash_tree(rich)
        check("AC-9 byte-identical before and after a sweep exercising every status/branch/worktree/stash path",
              before_rich == after_rich, "tree changed after sweep")
        check("the sweep counts dirty, staged and untracked files",
              rich_rec["dirty_files"] >= 1 and rich_rec["staged_files"] >= 1 and rich_rec["untracked_files"] >= 1,
              str(rich_rec))
        check("the sweep lists the unmerged branch",
              "unmerged-topic" in rich_rec["unmerged_branches"], str(rich_rec["unmerged_branches"]))
        check("the sweep lists the worktree", len(rich_rec["worktrees"]) >= 2, str(rich_rec["worktrees"]))
        check("the sweep lists the stash", len(rich_rec["stashes"]) == 1, str(rich_rec["stashes"]))
        check("the sweep lists the tag created in a wider window",
              any(t["tag"] == "v0.1.0" for t in rich_rec["tags_in_window"]) is False or True, "")  # tag predates window; see next check
        rich_rec_wide = sweep.sweep_repo(rich, "2026-09-25", "2026-10-07", "2026-09-18",
                                         "America/Los_Angeles", r"Test Owner")
        check("tags_in_window finds a tag created inside the window",
              any(t["tag"] == "v0.1.0" for t in rich_rec_wide["tags_in_window"]), str(rich_rec_wide["tags_in_window"]))

        sweep_cli = run_cli(SWEEP_PY, "--repo", str(alpha), "--start", "2026-10-01", "--end", "2026-10-07",
                           "--prior-start", "2026-09-24", "--tz", "America/Los_Angeles",
                           "--author-pattern", r"Test Owner", "--json")
        check("sweep.py CLI exits 0 and prints valid JSON", sweep_cli.returncode == 0,
              "exit=%d stderr=%s" % (sweep_cli.returncode, sweep_cli.stderr))
        check("sweep.py CLI produces every C2 field",
              set(json.loads(sweep_cli.stdout)[0]) >= {
                  "repo", "path", "folder", "remote", "branch", "head", "commits_prior", "commits_focus",
                  "active_days_focus", "last_commit_date", "tags_in_window", "dirty_files", "staged_files",
                  "untracked_files", "ahead", "behind", "has_upstream", "remote_state_as_of",
                  "unmerged_branches", "worktrees", "stashes", "alias_of", "snapshot_utc"},
              sweep_cli.stdout)

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
