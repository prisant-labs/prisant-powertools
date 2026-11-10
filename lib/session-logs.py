#!/usr/bin/env python3
"""Session-log rules shared by plab-wrap-session and plab-continue-session.

W-07 (session-aware wrap and continue). Both skills answer the same questions
about the session-log store, and this module is the one place the answers
live, so the two skills cannot drift apart:

- where the store is, including from a linked git worktree (spec D3);
- which logs exist, by the newest-wins discovery rule;
- what each log's frontmatter says about its session;
- which logs another session wrote while this one ran;
- which log a wrap carries Waiting on You and Parked items from (spec D7);
- which logs continue should offer, because no later log took them up (spec D2).

Stdlib only. Reads, never writes. Loaded by file path through importlib,
because a hyphenated file name cannot be imported by name; check-log.py loads
derive-log-facts.py the same way.

THE CARRY-FORWARD RULE (spec Requirement 4, D7 Option C)

The wrap carries from the log this session resumed from, and otherwise from
the newest log overall, whichever session wrote it. Waiting on You items are
the maintainer's obligations across the whole project, so the newest log is
their best record. A replay of 44 real logs found that a lineage-and-branch
rule would have carried from a log 17 days older than this one picks. Whether
a log is concurrent plays no part in the choice; it decides only consumption
and the same-arc archive.

THE CONSUMPTION RULE (spec Requirement 7)

A newer log consumes an older one when it names it in `resumed-from`, or names
it in `carried-from` and its own session started after the older log was
written. A carry by a session that was already running when the older log was
written does not consume it, so a parallel session's handoff stays visible to
continue. A newer log without `session-start` consumes through `carried-from`
as before, because nothing says it ran in parallel. A log without a
`session-id`, the shape of every log written before W-07, is also consumed by
any newer log on its branch, which keeps today's newest-wins behavior for
those logs.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
from pathlib import Path

LOG_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}_[^_]+_.+\.md$")
MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")
LEGACY_LOG_DIRS = ("_agent-context/session-log", "AGENTS/session-log")
STORE_RELATIVE = Path("_local") / "_session-logs"
WAITING_ITEM_RE = re.compile(r"^[-*]\s")
FIELDS = ("date", "branch", "session-id", "session-start", "resumed-from", "carried-from")
WINDOW_DAYS = 7


def run_git(args: list[str], cwd: Path, timeout: float = 10) -> tuple[int, str]:
    """One git command. Never raises. `GIT_OPTIONAL_LOCKS=0` keeps a read from
    refreshing `.git/index`, as in derive-log-facts.py."""
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return proc.returncode, proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return 124, ""
    except (FileNotFoundError, NotADirectoryError):
        return 127, ""


# ---------------------------------------------------------------------------
# Where the store is
# ---------------------------------------------------------------------------

def store_root(project_root: Path) -> tuple[Path, str]:
    """The session-log store for a checkout, and how it was found.

    In a linked worktree, `--git-dir` is `.git/worktrees/<name>` inside the main
    checkout while `--git-common-dir` is the main checkout's `.git`, so the two
    differ, and the main checkout is the common directory's parent. Every
    session then writes to and reads from one store, which survives the
    worktree's removal (spec D3).

    Returns `(path, how)`, where `how` is `checkout`, `main-checkout`, or
    `checkout-fallback: <reason>`."""
    root = Path(project_root).resolve()
    own = root / STORE_RELATIVE
    rc1, git_dir = run_git(["rev-parse", "--git-dir"], root)
    rc2, common_dir = run_git(["rev-parse", "--git-common-dir"], root)
    if rc1 != 0 or rc2 != 0 or not git_dir or not common_dir:
        return own, "checkout-fallback: not a git checkout"
    git_dir_p = (root / git_dir).resolve()
    common_p = (root / common_dir).resolve()
    if git_dir_p == common_p:
        return own, "checkout"
    if common_p.name != ".git":
        return own, "checkout-fallback: the common git directory is not named .git"
    return common_p.parent / STORE_RELATIVE, "main-checkout"


# ---------------------------------------------------------------------------
# Which logs exist
# ---------------------------------------------------------------------------

def pool_logs(store: Path, project_root: Path | None = None) -> list[Path]:
    """Every log, newest file name first: the store's top level, its `YYYY-MM/`
    folders, and, when `project_root` is given, the two frozen legacy stores.

    Discovery is an allowlist one level deep, so `_superseded/`, `_capture/`
    and any other subfolder stay outside the corpus, and a non-log file such as
    `notes.md` is skipped. The sort is on the file name, never the path, so a
    log in a month folder orders correctly against one at the top level."""
    found: list[Path] = []
    store = Path(store)
    if store.is_dir():
        for entry in store.iterdir():
            if entry.is_file() and LOG_NAME_RE.match(entry.name):
                found.append(entry)
            elif entry.is_dir() and MONTH_DIR_RE.match(entry.name):
                found.extend(sub for sub in entry.iterdir()
                             if sub.is_file() and LOG_NAME_RE.match(sub.name))
    if project_root is not None:
        for legacy in LEGACY_LOG_DIRS:
            legacy_dir = Path(project_root) / legacy
            if legacy_dir.is_dir():
                found.extend(e for e in legacy_dir.iterdir()
                             if e.is_file() and LOG_NAME_RE.match(e.name))
    found.sort(key=lambda p: p.name, reverse=True)
    return found


# ---------------------------------------------------------------------------
# What each log says
# ---------------------------------------------------------------------------

def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict:
    """A flat `key: value` read of the opening `---` block, for the W-07 fields.
    A missing field is None. Never raises: a log without frontmatter comes back
    with `malformed: True` and every field None."""
    out: dict = {f: None for f in FIELDS}
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        out["malformed"] = True
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            out["malformed"] = False
            return out
        match = re.match(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*)$", line)
        if match and match.group(1) in FIELDS:
            value = _unquote(match.group(2))
            out[match.group(1)] = value or None
    out["malformed"] = True
    return out


def read_frontmatter(path: Path) -> dict:
    return parse_frontmatter(Path(path).read_text(encoding="utf-8", errors="replace"))


def parse_utc(value: str | None) -> dt.datetime | None:
    """An ISO 8601 timestamp as an aware UTC datetime. A naive value is read as
    this machine's local time. None when absent or unparseable."""
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(dt.timezone.utc)


def wrapped_at_utc(path: Path, fm: dict | None = None) -> dt.datetime | None:
    """When the log was wrapped, in UTC. The frontmatter `date:` wins, because it
    carries an explicit offset. Otherwise the file name's date and time are
    read as this machine's local time, which is how the wrap names the file."""
    fm = fm if fm is not None else read_frontmatter(path)
    from_date = parse_utc(fm.get("date"))
    if from_date is not None:
        return from_date
    match = re.match(r"^(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})_", Path(path).name)
    if not match:
        return None
    naive = dt.datetime.strptime(f"{match.group(1)} {match.group(2)}:{match.group(3)}", "%Y-%m-%d %H:%M")
    return naive.astimezone(dt.timezone.utc)


def extract_section(text: str, heading: str) -> list[str] | None:
    """Lines between `## {heading}` and the next `## ` heading, exclusive of both."""
    lines = text.splitlines()
    target = f"## {heading}"
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == target)
    except StopIteration:
        return None
    body = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def extract_waiting_on_you(text: str) -> list[str] | None:
    """Top-level list items of `## Waiting on You`, `-` or `*` with no leading
    indentation, so an indented sub-bullet is never its own item."""
    body = extract_section(text, "Waiting on You")
    if body is None:
        return None
    return [line.rstrip() for line in body if WAITING_ITEM_RE.match(line)]


def title_of(name: str) -> str:
    """The file name's title slug: what follows `YYYY-MM-DD_HH-MM_<llm>_`."""
    stem = name[:-3] if name.endswith(".md") else name
    parts = stem.split("_", 3)
    return parts[3] if len(parts) == 4 else stem


def describe(path: Path) -> dict:
    """Everything the rules below need about one log, read once."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text)
    waiting = extract_waiting_on_you(text)
    return {
        "path": path,
        "name": path.name,
        "title": title_of(path.name),
        "branch": fm["branch"],
        "session-id": fm["session-id"],
        "session-start": parse_utc(fm["session-start"]),
        "resumed-from": fm["resumed-from"],
        "carried-from": fm["carried-from"],
        "wrapped": wrapped_at_utc(path, fm),
        "waiting": len(waiting) if waiting is not None else 0,
        "malformed": fm["malformed"],
    }


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------

def concurrent_logs(infos: list[dict], session_id: str | None,
                    session_start: dt.datetime | None) -> tuple[list[dict], str | None]:
    """Logs another session wrote after this session started (Requirement 5),
    newest first. A log with no `session-id` counts as another session's. With
    no session start there is nothing to compare, so the list is empty and the
    reason is `no-session-start`, which leaves a Codex or transcript-less wrap
    behaving as it does today (spec D5)."""
    if session_start is None:
        return [], "no-session-start"
    out = [i for i in infos
           if i["wrapped"] is not None and i["wrapped"] > session_start
           and (session_id is None or i["session-id"] != session_id)]
    return out, None


def carry_forward_source(infos: list[dict], resumed_from: str | None) -> tuple[dict | None, str, str | None]:
    """The log a wrap carries Waiting on You and Parked items from (Requirement 4,
    D7 Option C), as `(log, rule, note)`. `infos` is newest first.

    `resumed-from` wins whatever the log's age or session. Otherwise the newest
    log overall, under `newest-overall`. A `resumed_from` the store does not hold
    falls through to the newest log, with the note `resumed-from-not-found`,
    rather than failing the wrap."""
    note = None
    if resumed_from:
        for info in infos:
            if info["name"] == resumed_from:
                return info, "resumed-from", None
        note = "resumed-from-not-found"
    if infos:
        return infos[0], "newest-overall", note
    return None, "none", note


def consumes(later: dict, earlier: dict) -> bool:
    """Whether the newer log `later` took up the older log `earlier`'s handoff.
    See THE CONSUMPTION RULE in the module docstring."""
    if later["resumed-from"] == earlier["name"]:
        return True
    if later["carried-from"] == earlier["name"]:
        if later["session-start"] is None or earlier["wrapped"] is None:
            return True
        if later["session-start"] > earlier["wrapped"]:
            return True
    if earlier["session-id"] is None and earlier["branch"] is not None \
            and later["branch"] == earlier["branch"]:
        return True
    return False


def in_window(name: str, now: dt.datetime, window_days: int = WINDOW_DAYS) -> bool:
    """Whether the file name's date is at most `window_days` before today's local
    date. This is the same arithmetic as continue's age warning, which fires only
    when a log is more than seven days old (Requirement 11)."""
    try:
        logged = dt.date.fromisoformat(name[:10])
    except ValueError:
        return False
    today = now.astimezone().date() if now.tzinfo else now.date()
    return (today - logged).days <= window_days


def candidates(infos: list[dict], now: dt.datetime | None = None,
               window_days: int = WINDOW_DAYS) -> list[dict]:
    """The logs continue should offer (Requirement 7), newest first.

    Two wraps of one session collapse to the newer, then a log is offered when
    it is in the window and no newer pooled log consumes it. `infos` must be
    every pooled log, newest first, not only the window, because a consuming
    log is always newer and so is always in the list."""
    now = now or dt.datetime.now(dt.timezone.utc)
    out = []
    for idx, info in enumerate(infos):
        newer = infos[:idx]
        if info["session-id"] and any(n["session-id"] == info["session-id"] for n in newer):
            continue
        if not in_window(info["name"], now, window_days):
            continue
        if any(consumes(n, info) for n in newer):
            continue
        out.append({
            "name": info["name"],
            "path": str(info["path"]),
            "branch": info["branch"],
            "title": info["title"],
            "session-id": info["session-id"],
            "session-start": info["session-start"].isoformat() if info["session-start"] else None,
            "wrapped": info["wrapped"].isoformat() if info["wrapped"] else None,
            "waiting": info["waiting"],
        })
    return out
