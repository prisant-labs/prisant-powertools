#!/usr/bin/env python3
"""Fixture tests for derive-log-facts.py. No test framework required.

Run: python skills/plab-wrap-session/scripts/test-derive-log-facts.py

Every case builds a throwaway git fixture in a temp directory, so these tests never
touch a real git checkout or a real session-log store, matching the precedent set by
test-organize-logs.py in this same directory.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "derive-log-facts.py"

# Never the literal glyph in a committed file: U+274C, the cross mark, built
# from chr() so this file does not itself become a canary for anything.
CROSS = chr(0x274C)

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def run_script(
    *args: str,
    timeout: float = 20,
    no_session_env: bool = False,
    python_args: list[str] | None = None,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if no_session_env:
        env.pop("CLAUDE_CODE_SESSION_ID", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, *(python_args or []), str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )


def git(repo: Path, *args: str, check_rc: bool = True, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    if check_rc and proc.returncode != 0:
        raise RuntimeError(f"git {args} failed in {repo}: {proc.stderr}")
    return proc


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-b", "main")
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "initial commit")
    return path


def hash_tree(root: Path) -> dict[str, str]:
    """sha256 of every file under root, keyed by relative path."""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def make_log(store: Path, name: str, body: str) -> Path:
    store.mkdir(parents=True, exist_ok=True)
    path = store / name
    path.write_text(body, encoding="utf-8")
    return path


BASIC_LOG_BODY = """---
date: 2026-08-18T09:09:00-07:00
type: session-log
---

# Session log

## Decisions Made

1. **Decision one.** Reasoning for the first decision.
2. **Decision two.** Reasoning for the second decision.
3. **Decision three.** Reasoning for the third decision.

## Waiting on You

Intro sentence, not a bullet, should be excluded.

- **Item one** (blocked since 2026-08-01). Some detail about item one.
- **Item two** (blocked since 2026-09-15). Some detail about item two.

## What's Next

1. Do the next thing.
"""


def main() -> int:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)

        # ------------------------------------------------------------------
        # 1. Basic derivation: machine/repo/branch/files-changed/commit-range/tag
        # ------------------------------------------------------------------
        repo = init_repo(root / "basic")
        git(repo, "tag", "v1.0.0")
        (repo / "a.txt").write_text("changed\n", encoding="utf-8")
        git(repo, "add", "a.txt")
        git(repo, "commit", "-m", "add a.txt")

        proc = run_script(str(repo), "--base", "v1.0.0", "--json")
        check("basic run exits 0", proc.returncode == 0, proc.stderr)
        data = json.loads(proc.stdout)
        check("machine is a non-empty string", bool(data.get("machine")))
        check("branch is main", data.get("branch") == "main", str(data.get("branch")))
        check("files-changed matches git diff --name-only",
              data.get("files-changed") == ["a.txt"], str(data.get("files-changed")))
        check("latest-tag is v1.0.0", data.get("latest-tag") == "v1.0.0", str(data.get("latest-tag")))
        rc, head_short, _ = (0, None, None)
        head_proc = git(repo, "rev-parse", "--short", "HEAD")
        base_proc = git(repo, "rev-parse", "--short", "v1.0.0")
        expected_range = f"{base_proc.stdout.strip()}..{head_proc.stdout.strip()}"
        check("commit-range matches manual rev-parse",
              data.get("commit-range") == expected_range,
              f"{data.get('commit-range')} != {expected_range}")

        # ------------------------------------------------------------------
        # 2. Base resolution order: explicit > upstream > latest-tag > none
        # ------------------------------------------------------------------
        no_remote = init_repo(root / "no-remote-no-tag")
        proc = run_script(str(no_remote), "--json")
        data = json.loads(proc.stdout)
        check("no remote, no tag: base resolution is none",
              data["base"]["resolution"] == "none", str(data["base"]))
        check("no base: files-changed is empty", data["files-changed"] == [])
        check("no base: commit-range is null", data["commit-range"] is None)

        tagged_only = init_repo(root / "tagged-only")
        git(tagged_only, "tag", "v0.1.0")
        (tagged_only / "b.txt").write_text("x\n", encoding="utf-8")
        git(tagged_only, "add", "b.txt")
        git(tagged_only, "commit", "-m", "add b.txt")
        proc = run_script(str(tagged_only), "--json")
        data = json.loads(proc.stdout)
        check("tag but no upstream: base resolution is latest-tag",
              data["base"]["resolution"] == "latest-tag", str(data["base"]))

        # Session-start resolution (spec D7, revised 2026-10-15): when a transcript
        # gives a start timestamp, the default base is the commit on HEAD just
        # before it, even when an upstream tracking ref exists and points at HEAD
        # itself (the exact case that made files-changed empty for a pushed session).
        session_start_repo = init_repo(root / "session-start")
        d0 = "2026-10-12T09:00:00+00:00"
        git(session_start_repo, "commit", "--amend", "--date", d0,
            extra_env={"GIT_AUTHOR_DATE": d0, "GIT_COMMITTER_DATE": d0})
        # Push to a bare remote so an upstream tracking ref exists and, after the
        # second commit below, points at HEAD itself - the exact shape that made
        # Option B (upstream-only) resolve to an empty files-changed.
        bare = root / "session-start-bare.git"
        git(root, "init", "--bare", str(bare))
        git(session_start_repo, "remote", "add", "origin", str(bare))
        git(session_start_repo, "push", "-u", "origin", "main")

        # The session's own work: a second commit, after the transcript's start
        # timestamp, also pushed - so the upstream tracking ref points at it too.
        (session_start_repo / "work.txt").write_text("session work\n", encoding="utf-8")
        git(session_start_repo, "add", "work.txt")
        d1 = "2026-10-12T20:00:00+00:00"
        git(session_start_repo, "commit", "-m", "session work",
            extra_env={"GIT_AUTHOR_DATE": d1, "GIT_COMMITTER_DATE": d1})
        git(session_start_repo, "push", "origin", "main")

        ss_transcripts = root / "ss-transcripts" / "proj"
        ss_transcripts.mkdir(parents=True)
        ss_transcript_path = ss_transcripts / "ss-session.jsonl"
        ss_transcript_path.write_text(
            json.dumps({"type": "attachment", "timestamp": "2026-10-12T17:00:00.000Z"}) + "\n",
            encoding="utf-8",
        )

        proc = run_script(str(session_start_repo), "--json", "--session-id", "ss-session",
                           "--transcript-dir", str(ss_transcripts.parent))
        data = json.loads(proc.stdout)
        check("session-start: base resolution is session-start, not upstream",
              data["base"]["resolution"] == "session-start", str(data["base"]))
        check("session-start: files-changed shows the session's own pushed work",
              data["files-changed"] == ["work.txt"], str(data["files-changed"]))

        # ------------------------------------------------------------------
        # 3. decisions-count: mechanical count of '## Decisions Made' entries
        # ------------------------------------------------------------------
        log_dir = root / "logs-1"
        log_path = make_log(log_dir, "x.md", BASIC_LOG_BODY)
        proc = run_script("--count-decisions", str(log_path), "--json")
        check("decisions-count exits 0", proc.returncode == 0, proc.stderr)
        parsed = json.loads(proc.stdout)
        check("decisions-count is 3", parsed.get("decisions-count") == 3, proc.stdout)

        proc = run_script("--count-decisions", str(root / "does-not-exist.md"))
        check("decisions-count on missing file exits non-zero", proc.returncode != 0)

        bullet_log = make_log(log_dir, "bullets.md", (
            "## Decisions Made\n\n"
            "- **Decision one.** Reasoning.\n"
            "- **Decision two.** Reasoning.\n\n"
            "## Files Changed\n"
        ))
        proc = run_script("--count-decisions", str(bullet_log), "--json")
        parsed = json.loads(proc.stdout)
        check("decisions-count counts '-' bullets: 2",
              parsed.get("decisions-count") == 2, proc.stdout)

        star_log = make_log(log_dir, "stars.md", (
            "## Decisions Made\n\n"
            "* Decision one.\n"
            "* Decision two.\n"
            "* Decision three.\n\n"
            "## Files Changed\n"
        ))
        proc = run_script("--count-decisions", str(star_log), "--json")
        parsed = json.loads(proc.stdout)
        check("decisions-count counts '*' bullets: 3",
              parsed.get("decisions-count") == 3, proc.stdout)

        nested_log = make_log(log_dir, "nested.md", (
            "## Decisions Made\n\n"
            "1. **Decision one.** Top-level reasoning.\n"
            "   - A nested sub-bullet elaborating, not a decision of its own.\n"
            "   - Another nested sub-bullet.\n"
            "2. **Decision two.**\n\n"
            "## Files Changed\n"
        ))
        proc = run_script("--count-decisions", str(nested_log), "--json")
        parsed = json.loads(proc.stdout)
        check("decisions-count excludes indented nested sub-bullets: 2, not 4",
              parsed.get("decisions-count") == 2, proc.stdout)

        h3_log = make_log(log_dir, "h3.md", (
            "## Decisions Made\n\n"
            "### Chose option B over option A\n\n"
            "Full alternatives-considered analysis for an architectural decision.\n\n"
            "### Kept the existing retry policy\n\n"
            "More analysis.\n\n"
            "## Files Changed\n"
        ))
        proc = run_script("--count-decisions", str(h3_log), "--json")
        parsed = json.loads(proc.stdout)
        check("decisions-count falls back to '### ' subheadings when no list items: 2",
              parsed.get("decisions-count") == 2, proc.stdout)

        # ------------------------------------------------------------------
        # 4. Waiting on You extraction preserves blocked-since dates verbatim
        # ------------------------------------------------------------------
        woy_project = root / "woy-project"
        woy_project.mkdir()
        make_log(woy_project / "_local" / "_session-logs", "2026-10-01_09-00_claude_x.md", BASIC_LOG_BODY)
        init_repo(woy_project)
        proc = run_script(str(woy_project), "--json")
        data = json.loads(proc.stdout)
        woy = data["evidence-gathering"]["waiting-on-you"]
        check("waiting-on-you has exactly 2 bullets", woy is not None and len(woy) == 2, str(woy))
        check("waiting-on-you excludes the intro paragraph",
              woy is not None and all(line.lstrip().startswith("- ") for line in woy), str(woy))
        check("waiting-on-you preserves (blocked since ...) verbatim",
              woy is not None
              and "(blocked since 2026-08-01)" in woy[0]
              and "(blocked since 2026-09-15)" in woy[1],
              str(woy))

        # 4b. An indented sub-bullet under a top-level item is not its own item
        # (found on the real 2026-10-07 log: "Approve starting the layout
        # effort" carried 6 indented sub-bullets explaining what it would do,
        # and all 6 were being counted as separate, undated Waiting on You
        # items). Top-level only, no leading indentation, matching
        # count_decisions()'s own rule, '-' or '*'.
        subbullet_log = (
            "---\ndate: 2026-10-07T15:56:00-07:00\ntype: session-log\n---\n\n"
            "# Session log\n\n"
            "## Waiting on You\n\n"
            "- **Approve starting the layout effort** (blocked since 2026-10-07). It would:\n"
            "  - unify the ADR criteria in one place;\n"
            "  - write ADR-0001 for decision 21.\n"
            "- **Removed since the 18:04 log** (no date marker, top-level, still flagged).\n"
        )
        subbullet_project = root / "subbullet-project"
        subbullet_project.mkdir()
        make_log(subbullet_project / "_local" / "_session-logs", "2026-10-07_15-56_claude_x.md", subbullet_log)
        init_repo(subbullet_project)
        proc = run_script(str(subbullet_project), "--json")
        data = json.loads(proc.stdout)
        woy2 = data["evidence-gathering"]["waiting-on-you"]
        check(
            "waiting-on-you excludes indented sub-bullets: 2 top-level items, not 4",
            woy2 is not None and len(woy2) == 2,
            str(woy2),
        )

        # ------------------------------------------------------------------
        # 5. Log-store discovery: flat, YYYY-MM, legacy; newest wins by filename
        # ------------------------------------------------------------------
        disc_project = root / "discovery-project"
        disc_project.mkdir()
        init_repo(disc_project)
        store = disc_project / "_local" / "_session-logs"
        make_log(store, "2026-07-01_08-00_claude_flat-old.md", "---\ntype: session-log\n---\n# x\n")
        make_log(store / "2026-09", "2026-09-30_23-00_claude_archived-newer.md", "---\ntype: session-log\n---\n# x\n")
        make_log(disc_project / "_agent-context" / "session-log", "2026-05-01_08-00_claude_legacy.md",
                  "---\ntype: session-log\n---\n# x\n")
        proc = run_script(str(disc_project), "--json")
        data = json.loads(proc.stdout)
        check("newest-wins: archived log outranks older flat and legacy logs",
              data["evidence-gathering"]["newest-log"] == "2026-09-30_23-00_claude_archived-newer.md",
              str(data["evidence-gathering"]["newest-log"]))

        no_log_project = root / "no-log-project"
        no_log_project.mkdir()
        init_repo(no_log_project)
        proc = run_script(str(no_log_project), "--json")
        data = json.loads(proc.stdout)
        check("no logs anywhere: newest-log is null and waiting-on-you is null",
              data["evidence-gathering"]["newest-log"] is None
              and data["evidence-gathering"]["waiting-on-you"] is None)

        # ------------------------------------------------------------------
        # 6. Capture-record cutoff, with the timezone-conversion canary
        # ------------------------------------------------------------------
        cap_project = root / "capture-project"
        cap_project.mkdir()
        init_repo(cap_project)
        make_log(cap_project / "_local" / "_session-logs", "2026-08-18_09-09_claude_x.md", BASIC_LOG_BODY)
        capture_dir = cap_project / "_local" / "_session-logs" / "_capture"
        capture_dir.mkdir(parents=True)
        # Log's frontmatter date is 2026-08-18T09:09:00-07:00 == 16:09:00Z.
        # Record X (09:15Z) is well BEFORE the true UTC cutoff: a naive comparison
        # that treated the filename's bare "09-09" as if it were already UTC would
        # wrongly call 09:15 > 09:09 and include it. Record Y (16:15Z) is genuinely
        # after the cutoff and must be included.
        records = [
            {"ts": "2026-08-18T09:15:00+00:00", "session_id": "s1", "head": "aaaaaaa"},
            {"ts": "2026-08-18T16:15:00+00:00", "session_id": "s2", "head": "bbbbbbb"},
            {"ts": "2026-08-18T16:20:00+00:00", "session_id": None, "head": "ccccccc"},
        ]
        (capture_dir / "2026-08.jsonl").write_text(
            "\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8"
        )
        proc = run_script(str(cap_project), "--json")
        data = json.loads(proc.stdout)
        cap = data["evidence-gathering"]["capture-records"]
        check("tz-correct cutoff: exactly 1 qualifying record",
              cap.get("available") is True and cap.get("count") == 1, str(cap))
        check("tz-correct cutoff: the qualifying record is the one after the true UTC cutoff",
              cap.get("latest-head") == "bbbbbbb", str(cap))
        check("null session_id record never counted",
              cap.get("count") != 3, str(cap))

        # Filename-fallback path: no frontmatter date line at all. Compute the
        # expected cutoff the same way the script does, on this same machine, so
        # the assertion is timezone-independent.
        fallback_project = root / "capture-fallback-project"
        fallback_project.mkdir()
        init_repo(fallback_project)
        make_log(fallback_project / "_local" / "_session-logs", "2026-08-18_09-09_claude_x.md",
                  "# Session log with no frontmatter date\n")
        fb_capture = fallback_project / "_local" / "_session-logs" / "_capture"
        fb_capture.mkdir(parents=True)
        expected_cutoff = dt.datetime.strptime("2026-08-18 09:09", "%Y-%m-%d %H:%M").astimezone(dt.timezone.utc)
        before = (expected_cutoff - dt.timedelta(minutes=1)).isoformat()
        after = (expected_cutoff + dt.timedelta(minutes=1)).isoformat()
        (fb_capture / "x.jsonl").write_text(
            "\n".join(
                json.dumps(r)
                for r in [
                    {"ts": before, "session_id": "s1", "head": "before"},
                    {"ts": after, "session_id": "s2", "head": "after"},
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        proc = run_script(str(fallback_project), "--json")
        data = json.loads(proc.stdout)
        cap = data["evidence-gathering"]["capture-records"]
        check("filename-fallback cutoff: exactly 1 qualifying record",
              cap.get("available") is True and cap.get("count") == 1, str(cap))
        check("filename-fallback cutoff: the qualifying record is the later one",
              cap.get("latest-head") == "after", str(cap))

        # No capture dir at all.
        no_cap_project = root / "no-capture-project"
        no_cap_project.mkdir()
        init_repo(no_cap_project)
        proc = run_script(str(no_cap_project), "--json")
        data = json.loads(proc.stdout)
        check("no capture dir: available is false",
              data["evidence-gathering"]["capture-records"] == {"available": False, "reason": "no-capture-dir"})

        # ------------------------------------------------------------------
        # 7. Verification derivation: no session id / no transcript / real transcript
        # ------------------------------------------------------------------
        ver_project = root / "ver-project"
        ver_project.mkdir()
        init_repo(ver_project)

        proc = run_script(str(ver_project), "--json", no_session_env=True)
        data = json.loads(proc.stdout)
        check("no session id: verification unavailable, reason no-session-id",
              data["verification"] == {"available": False, "reason": "no-session-id"},
              str(data["verification"]))

        empty_transcripts = root / "empty-transcripts"
        empty_transcripts.mkdir()
        proc = run_script(str(ver_project), "--json", "--session-id", "nope",
                           "--transcript-dir", str(empty_transcripts))
        data = json.loads(proc.stdout)
        check("no matching transcript file: reason no-transcript-file",
              data["verification"] == {"available": False, "reason": "no-transcript-file"},
              str(data["verification"]))

        transcripts = root / "transcripts" / "proj"
        transcripts.mkdir(parents=True)
        transcript_lines = [
            {"message": {"content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "python scripts/check-dashes.py"}}
            ]}},
            {"message": {"content": [
                {"type": "tool_result", "tool_use_id": "t1", "is_error": False}
            ]}},
            {"message": {"content": [
                {"type": "tool_use", "id": "t2", "name": "Bash",
                 "input": {"command": "python scripts/gate-that-fails.py"}}
            ]}},
            {"message": {"content": [
                {"type": "tool_result", "tool_use_id": "t2", "is_error": True}
            ]}},
            {"message": {"content": [
                {"type": "tool_use", "id": "t3", "name": "Bash",
                 "input": {"command": "ls -la"}}
            ]}},
            {"message": {"content": [
                {"type": "tool_result", "tool_use_id": "t3", "is_error": False}
            ]}},
            "not even valid json {{{",
        ]
        transcript_path = transcripts / "sess-1.jsonl"
        with transcript_path.open("w", encoding="utf-8") as fh:
            for entry in transcript_lines:
                fh.write(entry if isinstance(entry, str) else json.dumps(entry))
                fh.write("\n")

        proc = run_script(str(ver_project), "--json", "--session-id", "sess-1",
                           "--transcript-dir", str(transcripts.parent))
        data = json.loads(proc.stdout)
        ver = data["verification"]
        check("real transcript: available is true", ver.get("available") is True, str(ver))
        facts = ver.get("facts", [])
        check("real transcript: 2 verification-relevant facts captured (check-dashes, gate-that-fails)",
              len(facts) == 2, str(facts))
        check("real transcript: non-matching 'ls -la' excluded", all("ls -la" not in f["command"] for f in facts))
        check("real transcript: the failing gate is captured with is_error true",
              any(f["is_error"] for f in facts), str(facts))
        check("real transcript: malformed line counted, not fatal", ver.get("malformed-lines") == 1, str(ver))

        # Overflow keeps the most recent facts, not the first ones (the orchestrator's
        # review finding): build 60 matching Bash calls, numbered in order, and assert
        # the kept 50 are calls 11 through 60, the latest, not 1 through 50.
        overflow_transcripts = root / "overflow-transcripts" / "proj"
        overflow_transcripts.mkdir(parents=True)
        overflow_lines = []
        for i in range(60):
            overflow_lines.append({"message": {"content": [
                {"type": "tool_use", "id": f"o{i}", "name": "Bash",
                 "input": {"command": f"python scripts/check-dashes.py --call {i}"}}
            ]}})
            overflow_lines.append({"message": {"content": [
                {"type": "tool_result", "tool_use_id": f"o{i}", "is_error": False}
            ]}})
        overflow_path = overflow_transcripts / "overflow-session.jsonl"
        with overflow_path.open("w", encoding="utf-8") as fh:
            for entry in overflow_lines:
                fh.write(json.dumps(entry))
                fh.write("\n")
        proc = run_script(str(ver_project), "--json", "--session-id", "overflow-session",
                           "--transcript-dir", str(overflow_transcripts.parent))
        data = json.loads(proc.stdout)
        ver = data["verification"]
        overflow_facts = ver.get("facts", [])
        check("overflow: exactly 50 facts kept", len(overflow_facts) == 50, str(len(overflow_facts)))
        check("overflow: fact-overflow counts the 10 dropped earlier calls",
              ver.get("fact-overflow") == 10, str(ver.get("fact-overflow")))
        check("overflow: the kept facts are the most recent (calls 10 through 59), not the earliest",
              overflow_facts[0]["command"].endswith("--call 10")
              and overflow_facts[-1]["command"].endswith("--call 59"),
              str(overflow_facts[0]) + " / " + str(overflow_facts[-1]))

        # Capture-lite present, but no transcript at all: must still be unavailable.
        # D3 (spec Open Questions / Decisions): capture-lite never grounds the
        # CURRENT session's verification, because it describes prior closed sessions.
        capture_only_project = root / "capture-only-project"
        capture_only_project.mkdir()
        init_repo(capture_only_project)
        cl_capture = capture_only_project / "_local" / "_session-logs" / "_capture"
        cl_capture.mkdir(parents=True)
        (cl_capture / "x.jsonl").write_text(
            json.dumps({"ts": "2026-08-18T16:15:00+00:00", "session_id": "s1", "head": "x"}) + "\n",
            encoding="utf-8",
        )
        proc = run_script(str(capture_only_project), "--json", "--session-id", "no-such-session",
                           "--transcript-dir", str(empty_transcripts))
        data = json.loads(proc.stdout)
        check("capture-lite present, no transcript: verification stays unavailable",
              data["verification"]["available"] is False, str(data["verification"]))

        # ------------------------------------------------------------------
        # 8. No-write guarantee: without --fetch, nothing under the fixture changes
        # ------------------------------------------------------------------
        write_project = init_repo(root / "no-write-project")
        before_hash = hash_tree(write_project)
        proc = run_script(str(write_project), "--json")
        check("no-write run exits 0", proc.returncode == 0, proc.stderr)
        after_hash = hash_tree(write_project)
        check("no --fetch: the fixture tree is byte-for-byte unchanged",
              before_hash == after_hash,
              f"added/removed/changed: {set(before_hash) ^ set(after_hash)}")

        # ------------------------------------------------------------------
        # 9. No-prune guarantee: a stale remote-tracking ref survives --fetch
        #    even when fetch.prune is set, because the script passes --no-prune.
        #    Canary: temporarily strip --no-prune from the script and confirm
        #    this exact case fails. Performed as a separate, manual verification
        #    step outside this automated run (see the implementation report).
        # ------------------------------------------------------------------
        upstream = init_repo(root / "upstream")
        git(upstream, "branch", "feature-to-prune")
        clone = root / "clone"
        git(root, "clone", str(upstream), str(clone))
        git(clone, "config", "fetch.prune", "true")
        git(upstream, "branch", "-D", "feature-to-prune")

        before_refs = git(clone, "for-each-ref", "--format=%(refname)", "refs/remotes/origin").stdout
        check("clone initially has the stale-to-be ref",
              "refs/remotes/origin/feature-to-prune" in before_refs, before_refs)

        proc = run_script(str(clone), "--fetch", "--json")
        check("--fetch run exits 0", proc.returncode == 0, proc.stderr)
        after_refs = git(clone, "for-each-ref", "--format=%(refname)", "refs/remotes/origin").stdout
        check("no-prune: the stale remote-tracking ref survives --fetch with fetch.prune=true",
              "refs/remotes/origin/feature-to-prune" in after_refs, after_refs)

        # ------------------------------------------------------------------
        # 10. Encoding robustness: a non-UTF-8-safe byte in git's own output
        #     must not crash run_git()'s reader thread. A real wrap crashed
        #     on this exact shape: an unpushed commit's message containing a
        #     non-ASCII character, read by check1_remote()'s
        #     `git log --oneline @{u}..HEAD`, decoded with no explicit
        #     encoding, which on this machine (and under a forced non-UTF-8
        #     mode, which is what makes this reproducible on any machine)
        #     is not UTF-8 and cannot represent some of the bytes the UTF-8
        #     commit message actually contains.
        #     -X utf8=0, PYTHONUTF8=0 and LC_ALL=C force Python out of UTF-8
        #     mode (PEP 540) so the test does not depend on ambient locale
        #     state; without the explicit -X flag, PEP 538's locale
        #     coercion can turn UTF-8 mode back on under a C locale and hide
        #     the bug.
        # ------------------------------------------------------------------
        enc_bare = root / "encoding-upstream.git"
        git(root, "init", "--bare", str(enc_bare))
        enc_repo = init_repo(root / "encoding-repo")
        git(enc_repo, "remote", "add", "origin", str(enc_bare))
        git(enc_repo, "push", "-u", "origin", "main")
        (enc_repo / "b.txt").write_text("world\n", encoding="utf-8")
        git(enc_repo, "add", "b.txt")
        git(enc_repo, "commit", "-m", f"fix: broke things {CROSS} badly")

        proc = run_script(
            str(enc_repo), "--json",
            python_args=["-X", "utf8=0"],
            extra_env={"PYTHONUTF8": "0", "LC_ALL": "C"},
        )
        check(
            "a non-ASCII byte in an unpushed commit message does not crash the reader thread",
            proc.returncode == 0,
            (proc.stdout[-300:] + "\n" + proc.stderr[-1200:]),
        )
        if proc.returncode == 0:
            data = json.loads(proc.stdout)
            unpushed = data["hygiene-sweep"]["check1-remote"].get("unpushed-commits", [])
            check(
                "the unpushed commit's message, cross mark included, is captured intact",
                any(CROSS in line for line in unpushed),
                str(unpushed),
            )

        # ------------------------------------------------------------------
        # 11. check4_doc_drift: a change to only HISTORY.md is not drift.
        #     Found on this repository's own main branch: plab-resolve-open-
        #     items changed only its HISTORY.md since v0.8.0 (verified with
        #     `git diff --name-only v0.8.0..HEAD -- skills/`), and the old
        #     `git diff --quiet <tag> HEAD -- <skill>` call, with no pathspec
        #     exclusion, counted that alone as "this skill changed" and then
        #     flagged a stale metadata.version that was never actually stale.
        #     An anti-canary alongside it proves the fix does not blind the
        #     check entirely: a real SKILL.md change with a genuinely unbumped
        #     version must still be flagged.
        # ------------------------------------------------------------------
        drift_project = root / "drift-project"
        drift_repo = init_repo(drift_project)

        def write_skill(name: str, version: str, history_rows: str) -> Path:
            skill_dir = drift_repo / "skills" / name
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                f'---\nmetadata:\n  version: "{version}"\n---\n# {name}\n', encoding="utf-8"
            )
            (skill_dir / "HISTORY.md").write_text(
                f"| Version |\n|---|\n{history_rows}", encoding="utf-8"
            )
            return skill_dir

        history_only_dir = write_skill("plab-history-only", "1.0.0", "| 1.0.0 |\n")
        real_drift_dir = write_skill("plab-real-drift", "1.0.0", "| 1.0.0 |\n")
        git(drift_repo, "add", "skills")
        git(drift_repo, "commit", "-m", "add two skills")
        git(drift_repo, "tag", "v1.0.0")

        # plab-history-only: HISTORY.md gets an annotation, SKILL.md untouched.
        (history_only_dir / "HISTORY.md").write_text(
            "| Version |\n|---|\n| 1.0.0 |\n| (clarifying note added later) |\n", encoding="utf-8"
        )
        # plab-real-drift: SKILL.md itself changes, version left unbumped on purpose.
        (real_drift_dir / "SKILL.md").write_text(
            '---\nmetadata:\n  version: "1.0.0"\n---\n# plab-real-drift\n\nNew content.\n',
            encoding="utf-8",
        )
        git(drift_repo, "add", "skills")
        git(drift_repo, "commit", "-m", "annotate history; also change real-drift content")

        proc = run_script(str(drift_repo), "--json")
        data = json.loads(proc.stdout)
        findings = data["hygiene-sweep"]["check4-doc-drift"]["findings"]
        check(
            "a HISTORY.md-only change is not reported as drift",
            not any("plab-history-only" in f for f in findings),
            str(findings),
        )
        check(
            "a genuine SKILL.md change with an unbumped version is still flagged",
            any("plab-real-drift" in f and "metadata.version" in f for f in findings),
            str(findings),
        )

        # ------------------------------------------------------------------
        # 12. The text digest (no --json) stays under the 20,000-character
        #     budget on a large fixture, and every field the Frontmatter
        #     block and the five sweep checks need is still present. Two
        #     real wraps that ran long (14 and 15 assistant calls, against a
        #     12-call baseline) both redirected --json to a file and sliced
        #     it, because the old text mode (6,384 chars on this repo) left
        #     out the Waiting on You text, the gitignored paths, and the
        #     verification facts, and rendered check3/check4 as Python dict
        #     reprs. This fixture is deliberately larger than any real wrap
        #     on this repository: every list capable of growing without
        #     bound (unpushed commits, remote branches, dirty files,
        #     gitignored-modified paths) is pushed past the render cap of
        #     40, to prove the cap engages with an explicit "N more, see
        #     --json" line rather than either silently dropping entries or
        #     letting the digest grow unbounded. The two fields a log
        #     copies verbatim (files-changed, waiting-on-you) are pushed
        #     past that same cap too, to prove they are never capped even
        #     once a list is larger than every other list here allows.
        #     Ground truth for every assertion comes from this fixture's
        #     own --json run, never a hand-derived count, so a change to
        #     how any one list is built cannot desync the test from what
        #     the script actually produced.
        # ------------------------------------------------------------------
        stress_repo = init_repo(root / "stress-project")
        stress_bare = root / "stress-upstream.git"
        git(root, "init", "--bare", str(stress_bare))
        git(stress_repo, "remote", "add", "origin", str(stress_bare))
        git(stress_repo, "push", "-u", "origin", "main")
        git(stress_repo, "tag", "v1.0.0")

        (stress_repo / ".gitignore").write_text("ignored_dir/\n", encoding="utf-8")
        WAITING_COUNT = 45
        log_body = "---\ndate: 2020-01-01T08:00:00-07:00\ntype: session-log\n---\n\n# Session log\n\n## Waiting on You\n\n"
        for i in range(WAITING_COUNT):
            log_body += (
                f"- **Decide on stress item {i:03d}.** Blocked since 2026-0{1 + i % 9}-1{i % 9}, "
                f"needs a maintainer call on fixture scenario number {i:03d} before the wrap can close.\n"
            )
        log_dir = stress_repo / "_local" / "_session-logs"
        log_dir.mkdir(parents=True)
        (log_dir / "2020-01-01_08-00_claude_stress-fixture.md").write_text(log_body, encoding="utf-8")
        # -f: this machine's global excludesfile also ignores _local/ (the
        # convention this repo's own AGENTS.md documents), so a plain `git
        # add` on the fixture's own _local path is refused as already
        # ignored; the fixture needs this file tracked, not ignored.
        git(stress_repo, "add", "-f", ".gitignore", "_local")

        STRESS_FILES = 80
        for i in range(STRESS_FILES):
            (stress_repo / f"stress_file_{i:03d}.txt").write_text(f"stress file {i}\n", encoding="utf-8")
        git(stress_repo, "add", *(f"stress_file_{i:03d}.txt" for i in range(STRESS_FILES)))
        git(stress_repo, "commit", "-m", "add gitignore, the fixture log, and 80 stress files")
        git(stress_repo, "push", "origin", "main")

        UNPUSHED = 45  # local-only commits ahead of the pushed upstream, never pushed by this fixture
        for i in range(UNPUSHED):
            (stress_repo / "counter.txt").write_text(f"{i}\n", encoding="utf-8")
            git(stress_repo, "add", "counter.txt")
            git(stress_repo, "commit", "-m", f"chore: bump counter to {i:03d}")

        FAKE_BRANCHES = 44  # + the real refs/remotes/origin/main the push above created = 45 total
        for i in range(FAKE_BRANCHES):
            git(stress_repo, "update-ref", f"refs/remotes/origin/branch-{i:03d}", "HEAD")

        UNTRACKED = 45
        for i in range(UNTRACKED):
            (stress_repo / f"untracked_{i:03d}.txt").write_text(f"untracked {i}\n", encoding="utf-8")

        IGNORED = 45
        ignored_dir = stress_repo / "ignored_dir"
        ignored_dir.mkdir()
        for i in range(IGNORED):
            (ignored_dir / f"ignored_{i:03d}.txt").write_text(f"ignored {i}\n", encoding="utf-8")

        proc_json = run_script(str(stress_repo), "--base", "v1.0.0", "--json", no_session_env=True, timeout=30)
        check("stress fixture: --json run exits 0", proc_json.returncode == 0, proc_json.stderr)
        data = json.loads(proc_json.stdout)

        proc_text = run_script(str(stress_repo), "--base", "v1.0.0", no_session_env=True, timeout=30)
        check("stress fixture: text run exits 0", proc_text.returncode == 0, proc_text.stderr)
        text = proc_text.stdout

        check(
            f"text digest stays under the 20,000-character budget ({len(text)} chars)",
            len(text) < 20000,
            f"{len(text)} chars",
        )

        files = data["files-changed"]
        check(f"fixture exceeds the render cap on files-changed ({len(files)} > 40)", len(files) > 40)
        missing_files = [f for f in files if f not in text]
        check(
            "every files-changed entry appears verbatim in the text digest, never capped",
            not missing_files,
            f"missing {len(missing_files)}: {missing_files[:5]}",
        )
        check(
            "files-changed count header matches the --json count",
            f"files-changed ({len(files)})" in text,
            f"files-changed ({len(files)}) not found",
        )

        woy = data["evidence-gathering"]["waiting-on-you"]
        check(f"fixture exceeds the render cap on waiting-on-you ({len(woy)} > 40)", len(woy) > 40)
        missing_woy = [w for w in woy if w not in text]
        check(
            "every waiting-on-you item appears verbatim with its date, never capped",
            not missing_woy,
            f"missing {len(missing_woy)}: {missing_woy[:2]}",
        )

        unpushed = data["hygiene-sweep"]["check1-remote"]["unpushed-commits"]
        remote_branches = data["hygiene-sweep"]["check1-remote"]["remote-branches"]
        dirty = data["hygiene-sweep"]["check2-worktree"]["dirty"]
        gitignored = data["evidence-gathering"]["gitignored-modified"]["files"]
        for label, items in (
            ("unpushed-commits", unpushed),
            ("remote-branches", remote_branches),
            ("dirty", dirty),
            ("gitignored-modified", gitignored),
        ):
            check(f"fixture exceeds the render cap on {label} ({len(items)} > 40)", len(items) > 40)
            overflow = len(items) - 40
            check(
                f"{label} is capped with an explicit overflow line ('{overflow} more, see --json')",
                f"... {overflow} more, see --json" in text,
                text,
            )

        for needed in (
            "Frontmatter fields", "Evidence Gathering", "Hygiene Sweep", "Verification",
            "Check 1, remote reconciliation", "Check 2, working tree", "Check 3, release and repo hygiene",
            "Check 4, documentation drift", "Check 5, session-log store",
            "commit-range:", "latest-tag:", "fetch:",
        ):
            check(f"text digest includes the {needed!r} section", needed in text, text[:2000])

        check(
            "check3's version-vs-tag renders as readable prose, not a Python dict repr",
            "version-vs-tag: latest-tag=" in text,
            text,
        )
        check(
            "no raw Python dict repr leaks into the text digest",
            "{'" not in text,
            text,
        )

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
