#!/usr/bin/env python3
"""Fixture tests for list-candidates.py (W-07 phase 5). No test framework required.

Run: python skills/plab-continue-session/scripts/test-list-candidates.py

Every case builds a throwaway git repository with its own session-log store.
The canary loads the script in this process and swaps the shared module's
candidate rule, so it never edits a tracked file.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "list-candidates.py"
TODAY = dt.date.today()

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def git(repo: Path, *args: str) -> None:
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
        "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
    })
    proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"git {args} failed in {repo}: {proc.stderr}")


def init_repo(path: Path, branch: str = "main") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-b", branch)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "initial commit")
    return path


def day(offset: int) -> str:
    """A date `offset` days before today, so the 7-day window is real."""
    return (TODAY - dt.timedelta(days=offset)).isoformat()


def log(store: Path, days_ago: int, hhmm: str, title: str, *, branch: str = "main",
        session_id: str | None = None, start_days_ago: int | None = None, start_hhmm: str = "08:00",
        resumed: str | None = None, carried: str | None = None, waiting: int = 0) -> str:
    name = f"{day(days_ago)}_{hhmm}_claude_{title}.md"
    store.mkdir(parents=True, exist_ok=True)
    head = ["---", f"date: {day(days_ago)}T{hhmm.replace('-', ':')}:00+00:00", "type: session-log",
            f"branch: {branch}"]
    if session_id:
        head.append(f"session-id: {session_id}")
    if start_days_ago is not None:
        head.append(f'session-start: "{day(start_days_ago)}T{start_hhmm}:00Z"')
    if resumed:
        head.append(f"resumed-from: {resumed}")
    if carried:
        head.append(f"carried-from: {carried}")
    body = head + ["---", "", "# Log", "", "## Waiting on You", ""]
    body += [f"- **Item {i}** (blocked since 2026-11-01). Detail." for i in range(waiting)]
    (store / name).write_text("\n".join(body) + "\n", encoding="utf-8")
    return name


def run(project: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(project), *extra], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)


def run_json(project: Path) -> dict:
    proc = run(project, "--json")
    return json.loads(proc.stdout)


def build_ac7(root: Path) -> tuple[Path, list[str]]:
    """Three logs in the window: two of session s1 on x, one of s2 on y, plus a
    log consumed by resumed-from, one consumed by a sequential carried-from, and
    one in _superseded/. Expect y1 and x2."""
    repo = init_repo(root / "ac7", branch="y")
    store = repo / "_local" / "_session-logs"
    w = log(store, 5, "10-00", "w", session_id="s9", start_days_ago=5)
    z = log(store, 3, "10-00", "z", session_id="s0", start_days_ago=4, carried=w)
    x1 = log(store, 2, "10-00", "x1", branch="x", session_id="s1", start_days_ago=2, resumed=z)
    x2 = log(store, 2, "15-00", "x2", branch="x", session_id="s1", start_days_ago=2, carried=x1, waiting=2)
    y1 = log(store, 1, "09-00", "y1", branch="y", session_id="s2", start_days_ago=2, start_hhmm="09:00",
             carried=x2, waiting=1)
    log(store / "_superseded", 1, "10-00", "old", session_id="s3", start_days_ago=1)
    return repo, [y1, x2]


def cases(root: Path) -> None:
    repo, want = build_ac7(root)
    data = run_json(repo)
    got = [c["name"] for c in data.get("candidates", [])]
    check("AC-7: two sessions in the window give mode choose with exactly two candidates",
          data.get("mode") == "choose" and got == want, f"mode {data.get('mode')}, {got}")
    check("AC-7: the one candidate on the current branch is the default",
          data.get("default") == want[0], str(data.get("default")))
    text = run(repo).stdout
    check("AC-7: the text list shows branch, span and waiting count, and asks",
          "Which session should I resume?" in text and "x2" in text and "2 waiting" in text
          and "  x  " in text, text[:500])

    repo = init_repo(root / "one")
    store = repo / "_local" / "_session-logs"
    t = log(store, 2, "17-00", "t", session_id="st", start_days_ago=2)
    u = log(store, 1, "12-00", "u", session_id="su", start_days_ago=1, carried=t)
    data = run_json(repo)
    check("AC-8: a sequential pair gives mode one with the newest log",
          data.get("mode") == "one" and [c["name"] for c in data["candidates"]] == [u],
          f"{data.get('mode')}, {data.get('candidates')}")

    repo = init_repo(root / "legacy")
    store = repo / "_local" / "_session-logs"
    for i, title in enumerate(("l1", "l2", "l3")):
        newest = log(store, 3 - i, "10-00", title)
    data = run_json(repo)
    check("AC-8: logs from before W-07 on one branch give mode one, the newest",
          data.get("mode") == "one" and [c["name"] for c in data["candidates"]] == [newest],
          f"{data.get('mode')}, {data.get('candidates')}")

    repo = init_repo(root / "stale")
    old = log(repo / "_local" / "_session-logs", 20, "10-00", "old", session_id="s1", start_days_ago=20)
    data = run_json(repo)
    check("AC-8: nothing in the window gives mode fallback with the newest log and its age",
          data.get("mode") == "fallback" and (data.get("newest") or {}).get("name") == old
          and (data.get("newest") or {}).get("age-days") == 20, str(data))

    repo = init_repo(root / "empty")
    data = run_json(repo)
    check("no logs at all gives mode none", data.get("mode") == "none", str(data))

    main = init_repo(root / "wt-main")
    m = log(main / "_local" / "_session-logs", 1, "10-00", "main-log")
    wt = root / "wt"
    git(main, "worktree", "add", str(wt), "-b", "feat/x")
    data = run_json(wt)
    check("AC-9: a worktree reads the main checkout's store",
          data["store"]["how"] == "main-checkout" and [c["name"] for c in data["candidates"]] == [m],
          str(data.get("store")))

    # The install guard.
    lone = root / "lone" / "a" / "b" / "c"
    lone.mkdir(parents=True)
    (lone / "list-candidates.py").write_bytes(SCRIPT.read_bytes())
    proc = subprocess.run([sys.executable, str(lone / "list-candidates.py"), str(main)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=60)
    check("a missing lib/session-logs.py exits 2 and names the path",
          proc.returncode == 2 and "session-logs.py" in proc.stderr, f"rc {proc.returncode}: {proc.stderr[:200]}")

    # Canary, in process: a candidate rule that returns every log in the window
    # unfiltered must be caught by the AC-7 case.
    spec = importlib.util.spec_from_file_location("list_candidates_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    original = mod.SL.candidates

    def unfiltered(infos, now=None, window_days=7):
        now = now or dt.datetime.now(dt.timezone.utc)
        keep = [i for i in infos if mod.SL.in_window(i["name"], now, window_days)]
        return [{"name": i["name"], "path": str(i["path"]), "branch": i["branch"], "title": i["title"],
                 "session-id": i["session-id"], "session-start": None, "wrapped": None,
                 "waiting": i["waiting"]} for i in keep]

    ac7_repo, ac7_want = build_ac7(root / "canary")
    mod.SL.candidates = unfiltered
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            mod.main([str(ac7_repo), "--json"])
        mutated = json.loads(buf.getvalue())
    finally:
        mod.SL.candidates = original
    check("canary: an unfiltered candidate rule is caught by the AC-7 case",
          [c["name"] for c in mutated["candidates"]] != ac7_want, str([c["name"] for c in mutated["candidates"]]))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            cases(Path(tmp))
        except Exception as exc:
            check(f"suite raised {type(exc).__name__}", False, str(exc))
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
