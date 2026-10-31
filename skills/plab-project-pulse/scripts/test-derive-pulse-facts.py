#!/usr/bin/env python3
"""Fixture tests for derive-pulse-facts.py.

Run: python skills/plab-project-pulse/scripts/test-derive-pulse-facts.py

Covers the settings-file subset parser, and AC-11 through AC-15 of
docs/internal/release-plans/_unassigned/PP-01_project-pulse/spec.md. Every
fixture is a throwaway repository built in a temp directory with real
`git init` and fixed author/committer dates, in the style of
skills/plab-current-status/scripts/test-derive-status-facts.py.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
SCRIPT = SCRIPTS / "derive-pulse-facts.py"

# The file name has hyphens, so it cannot be a normal `import` target; it is
# loaded by path instead, exactly as it runs when invoked as a script.
_spec = importlib.util.spec_from_file_location("derive_pulse_facts", SCRIPT)
dpf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dpf)
WINDOW_END = "2026-10-30"
WINDOW_START = "2026-10-24"
PRIOR_START = "2026-10-17"
TZ = "America/Los_Angeles"

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
    git(path, "config", "user.email", "owner@example.com")
    git(path, "config", "user.name", "Test Owner")
    git(path, "config", "commit.gpgsign", "false")
    return path


def write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def epoch_utc(y, mo, d, h=12, mi=0) -> int:
    return int(dt.datetime(y, mo, d, h, mi, 0, tzinfo=dt.timezone.utc).timestamp())


def commit_all(repo: Path, message: str, epoch: int) -> None:
    git(repo, "add", "-A")
    env = dict(os.environ, GIT_AUTHOR_NAME="Test Owner", GIT_AUTHOR_EMAIL="owner@example.com",
              GIT_COMMITTER_NAME="Test Owner", GIT_COMMITTER_EMAIL="owner@example.com",
              GIT_AUTHOR_DATE="@%d +0000" % epoch, GIT_COMMITTER_DATE="@%d +0000" % epoch)
    r = subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", message], capture_output=True,
                       text=True, encoding="utf-8", env=env)
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        raise RuntimeError("git commit failed: %s %s" % (r.stdout, r.stderr))


def head_short(repo: Path) -> str:
    r = git(repo, "rev-parse", "--short=7", "HEAD")
    return r.stdout.strip()


def run_derive(root: Path, out: Path, state=None, extra=()):
    args = [sys.executable, "-B", str(SCRIPT), "--root", str(root), "--max-depth", "2",
           "--tz", TZ, "--author-pattern", "Test Owner", "--start", WINDOW_START, "--end", WINDOW_END,
           "--prior-start", PRIOR_START, "--no-gh", "--out", str(out), "--today", WINDOW_END, *extra]
    if state:
        args += ["--state", str(state)]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
    if r.returncode not in (0, 2):
        raise AssertionError("derive-pulse-facts.py exited %d: %s" % (r.returncode, r.stderr))
    return r


def repos_by_name(facts):
    return {r["repo"]: r for r in facts["repos"]}


SNAPSHOT_TMPL = """---
type: status-snapshot
date: {date}
model: opus-5-5
repo: {name}
branch: main
head: {head}
level: decisions
waiting: {waiting}
pending-decisions: {decisions}
next: {next}
---

# Status: {name}, {date}

**As of {date}.** Fixture.

## The Answer

Fixture.

## Changed Since Last Status

Fixture.

## Waiting on You

{waiting_lines}

## What's Next

{next_lines}

## Pending Decisions

{decision_lines}

## Recent Decisions

None in the window.

## Accomplished

- Fixture.

## Where the Project Is

- Fixture.

## What I Don't Know

- Nothing.
"""


def make_snapshot(repo: Path, date: str, head: str, waiting_lines, next_lines, decision_lines, name="fixture",
                  waiting_count=None):
    # `waiting_count`, when given, decouples the frontmatter's `waiting:`
    # total from the number of numbered lines below the cap of ten, which
    # is the real-world case the frontmatter counts exist for.
    text = SNAPSHOT_TMPL.format(
        date=date, head=head, name=name,
        waiting=waiting_count if waiting_count is not None else len(waiting_lines),
        decisions=len(decision_lines), next=len(next_lines),
        waiting_lines="\n".join(waiting_lines), next_lines="\n".join(next_lines),
        decision_lines="\n".join(decision_lines),
    )
    write(repo / "_local" / "_status" / ("%s_opus-5-5_fixture-status.md" % date), text)


def test_settings_parser():
    doc = """---
max_depth: 3
timezone: "America/Los_Angeles"
author_pattern: 'Test Owner <owner@example\\.com>'
exclude:
  - "*.cache"
  - node_modules
unprotected_globs:
  - "_local/notes/**"
roots:
  - path: /abs/one
    folder: team-a
  - path: /abs/two
    folder: team-b
gh: false
---

body text, not parsed
"""
    cfg = dpf.parse_settings(doc)
    check("settings: a plain scalar", cfg.get("max_depth") == "3", str(cfg.get("max_depth")))
    check("settings: a double-quoted scalar", cfg.get("timezone") == "America/Los_Angeles", str(cfg.get("timezone")))
    check("settings: a single-quoted scalar with an escaped-looking dot",
          cfg.get("author_pattern") == "Test Owner <owner@example\\.com>", str(cfg.get("author_pattern")))
    check("settings: a block list of scalars", cfg.get("exclude") == ["*.cache", "node_modules"], str(cfg.get("exclude")))
    check("settings: a one-item block list under a different key",
          cfg.get("unprotected_globs") == ["_local/notes/**"], str(cfg.get("unprotected_globs")))
    roots = cfg.get("roots") or []
    check("settings: a block list of one-level mappings has the right length", len(roots) == 2, str(roots))
    check("settings: each mapping item carries both its keys",
          roots == [{"path": "/abs/one", "folder": "team-a"}, {"path": "/abs/two", "folder": "team-b"}], str(roots))
    check("settings: a bare false scalar round-trips as the string 'false'", cfg.get("gh") == "false", str(cfg.get("gh")))

    empty = dpf.parse_settings("no frontmatter here\n")
    check("settings: a file with no frontmatter block returns {}", empty == {}, str(empty))


def main() -> int:
    test_settings_parser()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "projects"
        empty_cfg = Path(tmp) / "empty-gitconfig"
        empty_cfg.write_text("", encoding="utf-8")
        os.environ["GIT_CONFIG_GLOBAL"] = str(empty_cfg)
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

        # active-no-snapshot: a commit inside the window, no snapshot at all.
        active = init_repo(root / "active-no-snapshot")
        write(active / "README.md")
        commit_all(active, "first", epoch_utc(2026, 9, 1))
        write(active / "work.txt")
        commit_all(active, "work in the window", epoch_utc(2026, 10, 26))

        # dormant-with-prior-state: nothing in the window, a prior state entry.
        carried_repo = init_repo(root / "dormant-with-prior-state")
        write(carried_repo / "README.md")
        commit_all(carried_repo, "old work", epoch_utc(2026, 9, 1))

        # dormant-no-state: nothing in the window, no prior entry anywhere.
        bare_dormant = init_repo(root / "dormant-no-state")
        write(bare_dormant / "README.md")
        commit_all(bare_dormant, "old work", epoch_utc(2026, 9, 1))

        # fresh-snapshot: the snapshot's head matches the repository's head.
        fresh = init_repo(root / "fresh-snapshot")
        write(fresh / "README.md")
        commit_all(fresh, "first", epoch_utc(2026, 9, 1))
        fresh_head = head_short(fresh)
        # waiting_count=12 deliberately differs from the single numbered
        # line below the cap of ten, so AC-12 proves the frontmatter total
        # is read, not merely however many items happen to be listed.
        make_snapshot(fresh, "2026-10-29", fresh_head,
                      ["1. **A waiting item (since 2026-10-20).** Text. Why here: first."],
                      ["1. **Next thing.** Text. Why here: first."],
                      ["1. **EX-01 D1 (do the thing)** in `docs/spec.md`. Why here: first."],
                      waiting_count=12)

        # stale-snapshot: the snapshot predates the last commit and its head is stale.
        stale = init_repo(root / "stale-snapshot")
        write(stale / "README.md")
        commit_all(stale, "first", epoch_utc(2026, 9, 1))
        stale_old_head = head_short(stale)
        make_snapshot(stale, "2026-09-05", stale_old_head, ["1. **Old waiting item.** Text. Why here: x."], [], [])
        write(stale / "later.txt")
        commit_all(stale, "later work, after the snapshot, inside the window", epoch_utc(2026, 10, 27))

        # decision-register: a hand-kept file in _local/_status/ that must
        # never be read as a snapshot (AC-13), even though its name sorts
        # after a real snapshot's name.
        register = init_repo(root / "decision-register-repo")
        write(register / "README.md")
        commit_all(register, "first", epoch_utc(2026, 9, 1))
        write(register / "_local" / "_status" / "decision-register.md", "a hand-kept register, not a snapshot\n")

        # unprotected work: three changed files under gitignored _local/notes/
        # counts; one under _local/_session-logs/ (always excluded) does not.
        unprotected = init_repo(root / "unprotected-work")
        write(unprotected / ".gitignore", "_local/\n")
        write(unprotected / "README.md")
        commit_all(unprotected, "first", epoch_utc(2026, 9, 1))
        write(unprotected / "_local" / "notes" / "idea.md", "an idea\n")
        # Three files, not one: on Windows a text-mode pipe to `git check-ignore` once dropped every
        # path but the last, so a single-file fixture could not see the bug.
        write(unprotected / "_local" / "notes" / "second.md", "a second\n")
        write(unprotected / "_local" / "notes" / "deeper" / "third.md", "a third\n")
        write(unprotected / "_local" / "_session-logs" / "2026-10-26_09-00_claude_x.md", "a log\n")

        state_path = Path(tmp) / "state.json"
        state_path.write_text(json.dumps({
            "schema_version": 1,
            "repos": {
                "dormant-with-prior-state": {
                    "status": {"summary": "carried forward from last week", "whats_next": [], "waiting_on_you": [],
                              "pending_decisions": [], "risks": []},
                    "refreshed": "2026-10-23", "head": "0000000",
                },
                # AC-11's last clause: a repository carried as dormant last
                # time, now active, must be scouted, not carried again.
                "active-no-snapshot": {
                    "status": {"summary": "was dormant last week", "whats_next": [], "waiting_on_you": [],
                              "pending_decisions": [], "risks": []},
                    "refreshed": "2026-10-23", "head": "0000000",
                },
            },
            "first_seen": {
                "fresh-snapshot::a waiting item": "2026-10-23",  # overridden by the stated since date
                "active-no-snapshot::an item seven days old": "2026-10-23",
            },
        }, indent=2), encoding="utf-8")

        out = Path(tmp) / "pulse-facts.json"
        run_derive(root, out, state=state_path)
        facts = json.loads(out.read_text(encoding="utf-8"))
        by_name = repos_by_name(facts)

        # AC-11
        check("AC-11 a repo with an own commit in the window is active",
              by_name["active-no-snapshot"]["activity"] == "active", by_name["active-no-snapshot"]["activity"])
        check("AC-11 a dormant repo with a previous state entry carries it, stamped carried_from",
              by_name["dormant-with-prior-state"]["status_source"] == "carried"
              and by_name["dormant-with-prior-state"]["carried"]["carried_from"] == "2026-10-23",
              json.dumps(by_name["dormant-with-prior-state"]))
        check("AC-11 a dormant repo with no previous entry is sweep-only",
              by_name["dormant-no-state"]["status_source"] == "sweep-only", by_name["dormant-no-state"]["status_source"])
        check("AC-11 an active repo with no fresh snapshot is listed to scout",
              by_name["active-no-snapshot"]["to_scout"] is True, str(by_name["active-no-snapshot"]))
        check("AC-11 a repository carried as dormant last time, now active, is scouted, not carried again",
              by_name["active-no-snapshot"]["status_source"] == "scout"
              and by_name["active-no-snapshot"]["carried"] is None,
              json.dumps(by_name["active-no-snapshot"]))

        # AC-12
        check("AC-12 a snapshot whose head equals the repository's head is status_source: snapshot",
              by_name["fresh-snapshot"]["status_source"] == "snapshot", by_name["fresh-snapshot"]["status_source"])
        check("AC-12 that repo takes its waiting count from the snapshot's waiting field, not the item count",
              by_name["fresh-snapshot"]["snapshot"]["waiting"] == 12, json.dumps(by_name["fresh-snapshot"]["snapshot"]))
        check("AC-12 a fresh-snapshot repo is not listed to scout",
              by_name["fresh-snapshot"]["to_scout"] is False, "")
        check("AC-12 a stale snapshot (older than the last commit) is listed to scout",
              by_name["stale-snapshot"]["to_scout"] is True and by_name["stale-snapshot"]["status_source"] == "scout",
              json.dumps(by_name["stale-snapshot"]))
        check("AC-12 a stale-snapshot repo is a /plab-current-status candidate",
              by_name["stale-snapshot"]["current_status_candidate"] is True, "")

        # AC-13
        check("AC-13 a hand-kept _local/_status/ file is never read as a snapshot",
              by_name["decision-register-repo"]["snapshot"] is None, json.dumps(by_name["decision-register-repo"]))

        # AC-14
        fresh_waiting = by_name["fresh-snapshot"]["snapshot"]["waiting_on_you"]
        check("AC-14 a waiting item with a stated since date reports its age from that date",
              fresh_waiting[0]["since"] == "2026-10-20" and fresh_waiting[0]["age_days"] == 10,
              json.dumps(fresh_waiting))

        # Second run: an item with no stated since date, present in the state
        # file from a run seven days before the window end, ages to 7 days.
        make_snapshot(active, "2026-10-26", "0000000",
                     ["1. **An item seven days old.** Why here: x."], [], [])
        out2 = Path(tmp) / "pulse-facts-2.json"
        run_derive(root, out2, state=state_path)
        facts2 = json.loads(out2.read_text(encoding="utf-8"))
        active2 = repos_by_name(facts2)["active-no-snapshot"]
        item = active2["snapshot"]["waiting_on_you"][0]
        check("AC-14 an item with no since date, first seen seven days before the window end, ages to 7",
              item["since"] is None and item["first_seen"] == "2026-10-23" and item["age_days"] == 7,
              json.dumps(item))

        # AC-15
        unp = by_name["unprotected-work"]["unprotected_work"]
        check("AC-15 a file changed in the window under gitignored _local/notes/ is reported, once",
              len(unp) == 1 and unp[0]["files_changed"] == 3 and unp[0]["folder"] == "_local/notes",
              json.dumps(unp))
        check("AC-15 a change under _local/_session-logs/ is never reported as unprotected work",
              not any(g["folder"].endswith("_session-logs") for g in unp), json.dumps(unp))

        # A sanity check outside the numbered ACs: exit 2 when no root is readable.
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(Path(tmp) / "does-not-exist"),
                           "--tz", TZ, "--author-pattern", "x", "--out", str(Path(tmp) / "never.json"),
                           "--today", WINDOW_END], capture_output=True, text=True, encoding="utf-8")
        check("no readable root exits 2 and writes nothing", r.returncode == 2 and not (Path(tmp) / "never.json").exists(),
              "exit=%d" % r.returncode)

        # An invalid setting is a named break (exit 2), never an uncaught
        # traceback: the un-caught ZoneInfoNotFoundError / re.error this
        # test would otherwise exercise.
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(active), "--tz", "Not/AZone",
                           "--author-pattern", "x", "--out", str(Path(tmp) / "never2.json"), "--today", WINDOW_END],
                           capture_output=True, text=True, encoding="utf-8")
        check("an invalid --tz exits 2, named, not a traceback",
              r.returncode == 2 and "Traceback" not in r.stderr and "not a valid IANA time zone" in r.stderr,
              "exit=%d stderr=%s" % (r.returncode, r.stderr))
        r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(active), "--tz", TZ,
                           "--author-pattern", "(unterminated", "--out", str(Path(tmp) / "never3.json"),
                           "--today", WINDOW_END], capture_output=True, text=True, encoding="utf-8")
        check("an invalid --author-pattern regex exits 2, named, not a traceback",
              r.returncode == 2 and "Traceback" not in r.stderr and "not a valid author_pattern" in r.stderr,
              "exit=%d stderr=%s" % (r.returncode, r.stderr))

        # --no-gh makes no gh call at all: every gh field stays null.
        check("--no-gh leaves every repo's gh field null", all(r["gh"] is None for r in facts["repos"]), "")

    # A `gh`-enabled smoke run against this very plugin's own worktree
    # (read-only; a root that is itself a repository, whose `.git` is a
    # file, not a directory, since this is a linked worktree). Exercises
    # gh_enrich end to end rather than only the --no-gh path above. `gh`
    # may be absent, unauthenticated, or rate-limited in CI, so this does
    # not assert success, only that nothing crashes and that visibility,
    # when present, is lowercase per pulse-schema.md's example.
    plugin_root = SCRIPTS.parents[2]
    gh_out = Path(tempfile.gettempdir()) / "pp-facts-gh-smoke.json"
    r = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(plugin_root), "--max-depth", "0",
                       "--tz", TZ, "--author-pattern", ".", "--out", str(gh_out), "--today", WINDOW_END],
                       capture_output=True, text=True, encoding="utf-8")
    check("a gh-enabled run against the plugin's own worktree exits cleanly, no traceback",
          r.returncode in (0, 2) and "Traceback" not in r.stderr, "exit=%d stderr=%s" % (r.returncode, r.stderr))
    if r.returncode == 0 and gh_out.exists():
        gh_facts = json.loads(gh_out.read_text(encoding="utf-8"))
        visibilities = [rec["gh"]["visibility"] for rec in gh_facts["repos"] if rec.get("gh") and rec["gh"].get("visibility")]
        check("gh visibility, when gh succeeded, is lowercase",
              all(v == v.lower() for v in visibilities), str(visibilities))
        gh_out.unlink(missing_ok=True)

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
