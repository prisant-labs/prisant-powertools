#!/usr/bin/env python3
"""Fixture tests for lib/session-logs.py, the session-log rules shared by
plab-wrap-session and plab-continue-session (W-07). No test framework required.

Run: python lib/test-session-logs.py

Every case builds its own store in a temporary directory, and the store-root
cases build real git repositories and a real linked worktree, so nothing here
touches a real checkout or a real session-log store.

Each case is a function that returns its checks instead of printing them, so a
canary can run the same case against a mutated module and prove that the case
notices. A canary patches the loaded module in this process only. It never
edits a tracked file, because a canary that edits reconcile.py once left it
modified in the working tree.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent / "session-logs.py"

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 11, 12, 0, tzinfo=UTC)  # a Wednesday

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def load_module():
    spec = importlib.util.spec_from_file_location("plab_session_logs_under_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-b", "main")
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "initial commit")
    return path


def write_log(store: Path, name: str, *, branch: str = "main", date: str | None = None,
              session_id: str | None = None, session_start: str | None = None,
              resumed: str | None = None, carried: str | None = None, waiting: int = 0) -> Path:
    """Write a fixture log. `date` defaults to the file name's time as UTC."""
    store.mkdir(parents=True, exist_ok=True)
    if date is None:
        date = f"{name[0:10]}T{name[11:13]}:{name[14:16]}:00+00:00"
    lines = ["---", f"date: {date}", "type: session-log", f"branch: {branch}"]
    if session_id:
        lines.append(f"session-id: {session_id}")
    if session_start:
        lines.append(f'session-start: "{session_start}"')
    if resumed:
        lines.append(f"resumed-from: {resumed}")
    if carried:
        lines.append(f"carried-from: {carried}")
    lines += ["---", "", "# Session log", "", "## Waiting on You", ""]
    lines += [f"- **Item {i}** (blocked since 2026-11-01). Detail." for i in range(waiting)]
    lines += ["  - an indented sub-bullet that is not an item", "", "## What's Next", "", "1. Next."]
    path = store / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def names(items) -> list[str]:
    return [i["name"] for i in items]


# ---------------------------------------------------------------------------
# Cases. Each takes the module and a fresh temp dir, and returns its checks.
# ---------------------------------------------------------------------------

def case_pool(m, tmp: Path):
    root = tmp / "proj"
    store = root / "_local" / "_session-logs"
    write_log(store, "2026-11-10_09-00_claude_top.md")
    write_log(store / "2026-10", "2026-10-03_09-00_claude_month.md")
    write_log(store / "_superseded", "2026-11-10_10-00_claude_superseded.md")
    write_log(store / "_capture", "2026-11-10_11-00_claude_capture.md")
    (store / "notes.md").write_text("not a log\n", encoding="utf-8")
    write_log(root / "AGENTS" / "session-log", "2026-06-01_09-00_claude_legacy.md")
    got = [p.name for p in m.pool_logs(store, root)]
    want = ["2026-11-10_09-00_claude_top.md", "2026-10-03_09-00_claude_month.md",
            "2026-06-01_09-00_claude_legacy.md"]
    return [("pool: top level, month folder and legacy store, newest first; nothing else",
             got == want, f"got {got}")]


def case_frontmatter(m, tmp: Path):
    store = tmp / "s"
    p = write_log(store, "2026-11-10_09-00_claude_fm.md", branch="feat/x", session_id="abc",
                  session_start="2026-11-09T08:00:00.000Z", resumed="r.md", carried="c.md", waiting=2)
    fm = m.read_frontmatter(p)
    out = [("frontmatter: every W-07 field read, quotes stripped",
            (fm.get("branch"), fm.get("session-id"), fm.get("session-start"), fm.get("resumed-from"),
             fm.get("carried-from"), fm.get("malformed")) ==
            ("feat/x", "abc", "2026-11-09T08:00:00.000Z", "r.md", "c.md", False), f"got {fm}")]
    bad = store / "2026-11-10_10-00_claude_bad.md"
    bad.write_text("no frontmatter here\n", encoding="utf-8")
    fm2 = m.read_frontmatter(bad)
    out.append(("frontmatter: a log without frontmatter is malformed, not an exception",
                fm2.get("malformed") is True and fm2.get("branch") is None, f"got {fm2}"))
    info = m.describe(p)
    out.append(("describe: waiting count counts top-level items only", info["waiting"] == 2,
                f"got {info['waiting']}"))
    return out


def case_wrapped_at(m, tmp: Path):
    store = tmp / "s"
    p = write_log(store, "2026-11-10_09-00_claude_offset.md", date="2026-11-10T09:00:00-08:00")
    got = m.wrapped_at_utc(p, m.read_frontmatter(p))
    out = [("wrapped_at: frontmatter date with offset wins", got == dt.datetime(2026, 11, 10, 17, 0, tzinfo=UTC),
            f"got {got}")]
    q = store / "2026-11-10_09-00_claude_nodate.md"
    q.write_text("---\ntype: session-log\n---\n", encoding="utf-8")
    got2 = m.wrapped_at_utc(q, m.read_frontmatter(q))
    want2 = dt.datetime(2026, 11, 10, 9, 0).astimezone(UTC)
    out.append(("wrapped_at: falls back to the file name as local time", got2 == want2, f"got {got2}"))
    return out


def case_store_root(m, tmp: Path):
    main = init_repo(tmp / "main")
    wt = tmp / "wt"
    git(main, "worktree", "add", str(wt), "-b", "feat/x")
    plain = tmp / "plain"
    plain.mkdir()
    s_main, how_main = m.store_root(main)
    s_wt, how_wt = m.store_root(wt)
    s_plain, how_plain = m.store_root(plain)
    want = (main / "_local" / "_session-logs").resolve()
    return [
        ("store_root: a normal checkout uses its own store",
         (s_main.resolve(), how_main) == (want, "checkout"), f"got {s_main}, {how_main}"),
        ("store_root: a linked worktree uses the main checkout's store (AC-9)",
         (s_wt.resolve(), how_wt) == (want, "main-checkout"), f"got {s_wt}, {how_wt}"),
        ("store_root: a directory outside git falls back to its own store and says why",
         s_plain.resolve() == (plain / "_local" / "_session-logs").resolve()
         and how_plain.startswith("checkout-fallback:"), f"got {s_plain}, {how_plain}"),
    ]


def ac4_store(m, tmp: Path):
    store = tmp / "s"
    write_log(store, "2026-11-09_10-00_claude_a.md", branch="x", session_id="sa",
              session_start="2026-11-09T08:00:00Z")
    write_log(store, "2026-11-10_10-00_claude_b.md", branch="y", session_id="sb",
              session_start="2026-11-10T08:00:00Z")
    return [m.describe(p) for p in m.pool_logs(store, None)]


def case_carry_forward(m, tmp: Path):
    infos = ac4_store(m, tmp)
    log, rule, note = m.carry_forward_source(infos, None)
    out = [("carry: with no resumed-from, the newest log overall, whatever its branch (AC-4)",
            (log and log["name"], rule) == ("2026-11-10_10-00_claude_b.md", "newest-overall"),
            f"got {log and log['name']}, {rule}")]
    log, rule, note = m.carry_forward_source(infos, "2026-11-09_10-00_claude_a.md")
    out.append(("carry: resumed-from wins over a newer log (AC-4)",
                (log and log["name"], rule) == ("2026-11-09_10-00_claude_a.md", "resumed-from"),
                f"got {log and log['name']}, {rule}"))
    log, rule, note = m.carry_forward_source(infos, "2026-01-01_00-00_claude_gone.md")
    out.append(("carry: a resumed-from the store lacks falls through and is reported",
                (log and log["name"], rule) == ("2026-11-10_10-00_claude_b.md", "newest-overall")
                and note == "resumed-from-not-found", f"got {log and log['name']}, {rule}, {note}"))
    log, rule, note = m.carry_forward_source([], None)
    out.append(("carry: an empty store gives rule none", (log, rule) == (None, "none"), f"got {log}, {rule}"))
    return out


def case_concurrent(m, tmp: Path):
    store = tmp / "s"
    write_log(store, "2026-11-09_07-00_claude_c.md", session_id="sc", session_start="2026-11-09T06:00:00Z")
    write_log(store, "2026-11-09_17-00_claude_d.md", session_id="sd", session_start="2026-11-09T09:30:00Z")
    infos = [m.describe(p) for p in m.pool_logs(store, None)]
    start = dt.datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
    conc, reason = m.concurrent_logs(infos, "me", start)
    log, rule, _ = m.carry_forward_source(infos, None)
    out = [
        ("concurrent: a log another session wrote after this session started is listed (AC-4)",
         names(conc) == ["2026-11-09_17-00_claude_d.md"] and reason is None, f"got {names(conc)}, {reason}"),
        ("carry: D7 option C carries from the concurrent newest log anyway (AC-4)",
         (log and log["name"], rule) == ("2026-11-09_17-00_claude_d.md", "newest-overall"),
         f"got {log and log['name']}, {rule}"),
    ]
    conc2, _ = m.concurrent_logs(infos, "sd", start)
    out.append(("concurrent: this session's own earlier log is never concurrent", names(conc2) == [],
                f"got {names(conc2)}"))
    conc3, reason3 = m.concurrent_logs(infos, "me", None)
    out.append(("concurrent: with no session start the list is empty and says why",
                conc3 == [] and reason3 == "no-session-start", f"got {names(conc3)}, {reason3}"))
    return out


def case_example1(m, tmp: Path):
    """Two parallel sessions, P on feat/a and Q on feat/b; Q carries from P."""
    store = tmp / "s"
    write_log(store, "2026-11-05_12-00_claude_o.md", session_id="so", session_start="2026-11-05T08:00:00Z")
    write_log(store, "2026-11-10_17-00_claude_a-work.md", branch="feat/a", session_id="sp",
              session_start="2026-11-10T09:00:00Z", carried="2026-11-05_12-00_claude_o.md", waiting=2)
    write_log(store, "2026-11-11_11-00_claude_b-work.md", branch="feat/b", session_id="sq",
              session_start="2026-11-10T10:00:00Z", carried="2026-11-10_17-00_claude_a-work.md")
    infos = [m.describe(p) for p in m.pool_logs(store, None)]
    got = names(m.candidates(infos, NOW))
    return [("candidates: a parallel handoff stays listed after a concurrent carry (Example 1, D7)",
             got == ["2026-11-11_11-00_claude_b-work.md", "2026-11-10_17-00_claude_a-work.md"], f"got {got}")]


def case_example1b(m, tmp: Path):
    """Sequential sessions T then U on main; U carries from T, so T is consumed."""
    store = tmp / "s"
    write_log(store, "2026-11-09_17-00_claude_t.md", session_id="st", session_start="2026-11-09T08:00:00Z")
    write_log(store, "2026-11-10_12-00_claude_u.md", session_id="su", session_start="2026-11-10T09:00:00Z",
              carried="2026-11-09_17-00_claude_t.md")
    infos = [m.describe(p) for p in m.pool_logs(store, None)]
    got = names(m.candidates(infos, NOW))
    return [("candidates: a sequential carry consumes, so one candidate (Example 1b)",
             got == ["2026-11-10_12-00_claude_u.md"], f"got {got}")]


def case_example3(m, tmp: Path):
    store = tmp / "s"
    write_log(store, "2026-11-10_12-00_claude_s1.md", session_id="ss", session_start="2026-11-10T09:00:00Z")
    write_log(store, "2026-11-10_18-00_claude_s2.md", session_id="ss", session_start="2026-11-10T09:00:00Z",
              carried="2026-11-10_12-00_claude_s1.md")
    infos = [m.describe(p) for p in m.pool_logs(store, None)]
    got = names(m.candidates(infos, NOW))
    return [("candidates: two wraps of one session collapse to the newer (Example 3)",
             got == ["2026-11-10_18-00_claude_s2.md"], f"got {got}")]


def case_ac7(m, tmp: Path):
    store = tmp / "s"
    write_log(store, "2026-11-06_10-00_claude_w.md", session_id="s9", session_start="2026-11-06T08:00:00Z")
    write_log(store, "2026-11-08_10-00_claude_z.md", session_id="s0", session_start="2026-11-07T08:00:00Z",
              carried="2026-11-06_10-00_claude_w.md")
    write_log(store, "2026-11-09_10-00_claude_x1.md", branch="x", session_id="s1",
              session_start="2026-11-09T08:00:00Z", resumed="2026-11-08_10-00_claude_z.md")
    write_log(store, "2026-11-09_15-00_claude_x2.md", branch="x", session_id="s1",
              session_start="2026-11-09T08:00:00Z", carried="2026-11-09_10-00_claude_x1.md")
    write_log(store, "2026-11-10_09-00_claude_y1.md", branch="y", session_id="s2",
              session_start="2026-11-09T09:00:00Z", carried="2026-11-09_15-00_claude_x2.md")
    write_log(store / "_superseded", "2026-11-10_10-00_claude_old.md", session_id="s3",
              session_start="2026-11-10T09:30:00Z")
    infos = [m.describe(p) for p in m.pool_logs(store, None)]
    got = m.candidates(infos, NOW)
    want = ["2026-11-10_09-00_claude_y1.md", "2026-11-09_15-00_claude_x2.md"]
    out = [("candidates: AC-7's store gives exactly two, newest first", names(got) == want, f"got {names(got)}")]
    if names(got) == want:
        y = got[0]
        out.append(("candidates: each carries branch, span, title and waiting count",
                    (y["branch"], y["title"], y["waiting"], y["session-start"] is not None, y["wrapped"] is not None)
                    == ("y", "y1", 0, True, True), f"got {y}"))
    return out


def case_legacy(m, tmp: Path):
    store = tmp / "s"
    for n in ("2026-11-08_10-00_claude_l1.md", "2026-11-09_10-00_claude_l2.md", "2026-11-10_10-00_claude_l3.md"):
        write_log(store, n)
    infos = [m.describe(p) for p in m.pool_logs(store, None)]
    got = names(m.candidates(infos, NOW))
    out = [("candidates: logs without session fields on one branch give the newest alone",
            got == ["2026-11-10_10-00_claude_l3.md"], f"got {got}")]
    store2 = tmp / "s2"
    write_log(store2, "2026-11-09_10-00_claude_m.md", branch="main")
    write_log(store2, "2026-11-10_10-00_claude_f.md", branch="feat/x")
    infos2 = [m.describe(p) for p in m.pool_logs(store2, None)]
    got2 = names(m.candidates(infos2, NOW))
    out.append(("candidates: legacy logs on two branches are two candidates, as Requirement 7 says",
                got2 == ["2026-11-10_10-00_claude_f.md", "2026-11-09_10-00_claude_m.md"], f"got {got2}"))
    return out


def case_window(m, tmp: Path):
    store = tmp / "s"
    write_log(store, "2026-10-20_10-00_claude_old.md", session_id="s1", session_start="2026-10-20T08:00:00Z")
    infos = [m.describe(p) for p in m.pool_logs(store, None)]
    got = names(m.candidates(infos, NOW))
    store2 = tmp / "s2"
    write_log(store2, "2026-11-04_10-00_claude_edge.md", session_id="s1", session_start="2026-11-04T08:00:00Z")
    got2 = names(m.candidates([m.describe(p) for p in m.pool_logs(store2, None)], NOW))
    return [("candidates: nothing in the 7-day window gives none", got == [], f"got {got}"),
            ("candidates: a log exactly 7 days old is still in the window, as the age warning counts",
             got2 == ["2026-11-04_10-00_claude_edge.md"], f"got {got2}")]


CASES = [case_pool, case_frontmatter, case_wrapped_at, case_store_root, case_carry_forward,
         case_concurrent, case_example1, case_example1b, case_example3, case_ac7, case_legacy, case_window]


def run_case(case, m) -> list[tuple[str, bool, str]]:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            return case(m, Path(tmp))
        except Exception as exc:  # a crash is a failure, named
            return [(f"{case.__name__} raised {type(exc).__name__}", False, str(exc))]


# ---------------------------------------------------------------------------
# Canaries: each mutant must make its named case fail.
# ---------------------------------------------------------------------------

def canaries(m):
    orig_carry = m.carry_forward_source
    orig_consumes = m.consumes
    orig_store_root = m.store_root

    def carry_ignoring_resumed(infos, resumed_from):
        return orig_carry(infos, None)

    def consumes_without_carried(later, earlier):
        if later.get("resumed-from") == earlier["name"]:
            return True
        return earlier.get("session-id") is None and later.get("branch") == earlier.get("branch")

    def consumes_every_carried(later, earlier):
        if later.get("carried-from") == earlier["name"]:
            return True
        return orig_consumes(later, earlier)

    def store_root_own(project_root):
        return Path(project_root) / "_local" / "_session-logs", "checkout"

    return [
        ("canary: ignoring resumed-from is caught (AC-4)", "carry_forward_source",
         carry_ignoring_resumed, case_carry_forward),
        ("canary: dropping carried-from from consumption is caught (the S11 defect)", "consumes",
         consumes_without_carried, case_example1b),
        ("canary: letting every carried-from consume is caught (AC-7, D7)", "consumes",
         consumes_every_carried, case_example1),
        ("canary: letting every carried-from consume is caught on AC-7's store", "consumes",
         consumes_every_carried, case_ac7),
        ("canary: a worktree reading its own store is caught (AC-9)", "store_root",
         store_root_own, case_store_root),
    ]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        m = load_module()
    except Exception as exc:
        check("module loads", False, f"{type(exc).__name__}: {exc}")
        print(f"\n0/1 passed: {MODULE_PATH} could not be loaded")
        return 1

    for case in CASES:
        for name, ok, detail in run_case(case, m):
            check(name, ok, detail)

    for label, attr, mutant, case in canaries(m):
        original = getattr(m, attr)
        setattr(m, attr, mutant)
        try:
            outcome = run_case(case, m)
        finally:
            setattr(m, attr, original)
        caught = any(not ok for _, ok, _ in outcome)
        check(label, caught, "the mutant passed every check in its case" if not caught else "")

    # Anti-canary: the harness must not flag an unchanged function, or every
    # canary above would pass for a reason unrelated to its mutant.
    original = m.consumes
    m.consumes = lambda later, earlier: original(later, earlier)
    try:
        outcome = run_case(case_ac7, m)
    finally:
        m.consumes = original
    check("anti-canary: an unchanged function swapped in is not flagged",
          all(ok for _, ok, _ in outcome), f"flagged: {[n for n, ok, _ in outcome if not ok]}")

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
