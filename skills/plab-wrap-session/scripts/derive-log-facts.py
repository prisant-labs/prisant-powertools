#!/usr/bin/env python3
"""Derive session-log facts from git and the environment, instead of model recall.

W-02 (derived log facts): replaces model-recalled frontmatter fields, the Evidence
Gathering inputs, and the hygiene sweep's detection results with values this script
reads directly from git, the filesystem, and (when available) the current session's
own transcript. See docs/internal/release-plans/_unassigned/W-02_derived-log-facts/
for the spec and implementation plan this script fulfils.

WRITE CONTRACT
--------------
By default this script writes nothing anywhere. Its one write path is `--fetch`,
which runs exactly `git fetch --no-prune origin --tags` and nothing else. `--no-prune`
is explicit rather than relied-upon-by-default, because a plain `git fetch` prunes
whenever `fetch.prune` or `remote.<name>.prune` is set in git configuration, and the
explicit flag overrides that setting. On 2026-09-25 a by-hand `git fetch --prune`
deleted a remote-tracking ref without the confirmation the hygiene sweep requires;
this script must never repeat that. Every git subprocess call sets
`GIT_OPTIONAL_LOCKS=0`, because `git status` and `git diff` opportunistically refresh
`.git/index` as a side effect even on a read; without that flag, a "no write" test
that hashes files under `.git` across a run would fail even though nothing meant to
write anything. `GIT_TERMINAL_PROMPT=0` stops a missing-credential prompt from
hanging a call that touches the network.

PATH RESOLUTION
---------------
This script resolves its own location relative to its own installed directory
(`Path(__file__).resolve().parent`), matching the precedent already shipped in
`organize-logs.py` in this same directory: a plugin can be installed anywhere, so a
script must never assume it shares a root with the project it inspects. The project
to inspect is a separate, explicit argument (`project_root`, default `.`), never
assumed to be the plugin's own install location.

NEWEST-LOG DISCOVERY MIRRORS log-discovery.md, DOES NOT REDEFINE IT
---------------------------------------------------------------------
`skills/plab-continue-session/references/log-discovery.md` is the one named owner of
the newest-wins sort across the flat session-log store, its `YYYY-MM/` folders, and
the two legacy paths. This script needs the same answer to find the newest log for
Evidence Gathering, so it reimplements the same rule in Python rather than inventing
a second one; consolidating the two copies into one is a later effort's job (D-10),
not this one's.

VERIFICATION DERIVATION, AND WHY CAPTURE-LITE NEVER GROUNDS IT
-----------------------------------------------------------------
A `SessionEnd`-triggered capture-lite record (`_local/_session-logs/_capture/*.jsonl`)
describes a prior, already-closed session; it cannot describe the still-open session
that is being wrapped right now (D-4's finding, cited by this effort's spec as D3).
So verification-relevant facts are derived only from a live transcript: the current
`CLAUDE_CODE_SESSION_ID`, read from the environment unless `--session-id` overrides
it for testing, resolved to `~/.claude/projects/*/<id>.jsonl` (or `--transcript-dir`
for testing). When no session id, no transcript file, or no matching tool-call
appears, the script reports an explicit "no record" signal. It never fabricates a
verification entry and never reports an empty success as though it had looked and
found nothing, because those two states are not the same fact.

The transcript is streamed line by line, because it can be very large. Malformed
JSON lines are skipped and counted, not fatal.

EXIT CODES
----------
0  Always, once the project root exists. This script reports; it has no pass/fail
   verdict of its own to signal through its exit code (that is what the sweep's
   per-finding proposals and the Log Self-Check gates are for).
2  The given project_root is not a directory, or --count-decisions was given a path
   that does not exist. Both are caller errors, not findings about the project.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

LOG_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}_[^_]+_.+\.md$")
MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")
LEGACY_LOG_DIRS = ("_agent-context/session-log", "AGENTS/session-log")
DECISION_LIST_ITEM_RE = re.compile(r"^(?:\d+\.|[-*])\s")
DECISION_SUBHEADING_RE = re.compile(r"^### \S")
VERIFICATION_COMMAND_RE = re.compile(r"\b(test|check|gate|lint|verify)\b", re.IGNORECASE)
MAX_VERIFICATION_FACTS = 50


# ---------------------------------------------------------------------------
# git plumbing
# ---------------------------------------------------------------------------

def run_git(args: list[str], cwd: Path, timeout: float = 10) -> tuple[int, str, str]:
    """Run one git command. Never raises; a failure is a (returncode, "", stderr).

    `encoding="utf-8", errors="replace"` is explicit, not left to `text=True`'s
    default. Without it, `subprocess.run` decodes git's UTF-8 stdout and stderr
    using `locale.getpreferredencoding(False)`, which is cp1252 on this
    maintainer's Windows machine. A commit message (or any other git output)
    containing a UTF-8 byte sequence that lands on one of cp1252's undefined
    code points (0x81, 0x8D, 0x8F, 0x90, 0x9D) crashes the background reader
    thread `capture_output=True` spawns with an uncaught `UnicodeDecodeError`,
    which this function's own `try/except` around `subprocess.run` cannot
    catch, because the exception happens in a different thread. Reproduced
    live during a real wrap on 2026-10-16.

    Returns `.rstrip()`, not `.strip()`. `git status --short` (and porcelain
    formats generally) use a fixed two-column status code where a literal
    leading space is meaningful (" M" is an unstaged modify, "M " is a
    staged one); `.strip()` trims leading whitespace from the START of the
    whole string, which silently ate that first line's leading space and
    turned " M path" into "M path". Found live in a real wrap's digest on
    `pm-skills` on 2026-10-16, where the first dirty entry rendered
    misaligned. `.rstrip()` only trims the trailing newline every git
    command leaves, never a character git itself put first."""
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout.rstrip(), proc.stderr.rstrip()
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"
    except FileNotFoundError:
        return 127, "", "git not found on PATH"


# ---------------------------------------------------------------------------
# Environment fields (AC-1)
# ---------------------------------------------------------------------------

def get_machine() -> str:
    return socket.gethostname()


def parse_remote_url(url: str) -> str:
    url = url.strip()
    if url.endswith(".git"):
        url = url[:-4]
    match = re.search(r"[:/]([^/:]+/[^/:]+)$", url)
    return match.group(1) if match else url


def get_repo(project_root: Path) -> str:
    rc, out, _ = run_git(["remote", "get-url", "origin"], project_root)
    if rc == 0 and out:
        return parse_remote_url(out)
    return project_root.resolve().name


def get_branch(project_root: Path) -> str | None:
    rc, out, _ = run_git(["branch", "--show-current"], project_root)
    if rc == 0 and out:
        return out
    rc, sha, _ = run_git(["rev-parse", "--short", "HEAD"], project_root)
    if rc == 0 and sha:
        return f"(detached@{sha})"
    return None


def get_date() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Base ref, files-changed, commit-range, latest-tag (AC-2, AC-3)
# ---------------------------------------------------------------------------

def resolve_base(
    project_root: Path, base_arg: str | None, session_start_ts: str | None = None
) -> tuple[str | None, str]:
    """Open decision D7 (spec Open Questions / Decisions): default base order when
    the caller does not supply --base. Explicit argument wins outright. Otherwise,
    when the current session's transcript gives a start timestamp, the commit on
    HEAD immediately before that moment - this is what makes files-changed show a
    session's own work rather than nothing, for the common case of a session that
    already committed and pushed before wrapping, where the upstream tracking ref
    points at HEAD itself. Falls back to the upstream tracking ref, then the latest
    reachable tag, then no base at all."""
    if base_arg:
        rc, _, _ = run_git(["rev-parse", "--verify", base_arg], project_root)
        return (base_arg, "explicit") if rc == 0 else (None, "explicit-unresolved")
    if session_start_ts:
        rc, out, _ = run_git(["rev-list", "-1", f"--before={session_start_ts}", "HEAD"], project_root)
        if rc == 0 and out:
            return out, "session-start"
    rc, out, _ = run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], project_root
    )
    if rc == 0 and out:
        return out, "upstream"
    rc, out, _ = run_git(["describe", "--tags", "--abbrev=0"], project_root)
    if rc == 0 and out:
        return out, "latest-tag"
    return None, "none"


def get_files_changed(project_root: Path, base: str | None) -> tuple[list[str], dict[str, list[str]]]:
    """Open decision D6 (spec Open Questions / Decisions): `git diff --name-only
    <base>` (base vs. the current working tree, AC-2's literal wording) rather than
    `<base>..HEAD` (committed only, what the implementation plan's Phase 1 step 3
    text says). A wrap's files-changed must reflect the session's actual current
    state, including staged and unstaged tracked edits not yet committed; `..HEAD`
    would miss exactly that for a mid-session or final-mode wrap."""
    if not base:
        return [], {}
    rc, out, _ = run_git(["diff", "--name-only", base], project_root)
    flat = [line for line in out.splitlines() if line.strip()] if rc == 0 else []
    grouped: dict[str, list[str]] = {}
    for f in flat:
        key = f.split("/")[0] if "/" in f else "(root)"
        grouped.setdefault(key, []).append(f)
    return flat, grouped


def get_commit_range(project_root: Path, base: str | None) -> str | None:
    if not base:
        return None
    rc1, b, _ = run_git(["rev-parse", "--short", base], project_root)
    rc2, h, _ = run_git(["rev-parse", "--short", "HEAD"], project_root)
    return f"{b}..{h}" if rc1 == 0 and rc2 == 0 and b and h else None


def get_latest_tag(project_root: Path) -> str | None:
    rc, out, _ = run_git(["describe", "--tags", "--abbrev=0"], project_root)
    return out if rc == 0 and out else None


def do_fetch(project_root: Path) -> dict:
    rc, out, err = run_git(["fetch", "--no-prune", "origin", "--tags"], project_root, timeout=30)
    return {"ran": True, "ok": rc == 0, "stdout": out, "stderr": err}


# ---------------------------------------------------------------------------
# Newest-log discovery, mirroring log-discovery.md (Requirement 10)
# ---------------------------------------------------------------------------

def pool_logs(project_root: Path) -> list[Path]:
    candidates: list[Path] = []
    store = project_root / "_local" / "_session-logs"
    if store.is_dir():
        for entry in store.iterdir():
            if entry.is_file() and LOG_NAME_RE.match(entry.name):
                candidates.append(entry)
            elif entry.is_dir() and MONTH_DIR_RE.match(entry.name):
                for sub in entry.iterdir():
                    if sub.is_file() and LOG_NAME_RE.match(sub.name):
                        candidates.append(sub)
    for legacy in LEGACY_LOG_DIRS:
        legacy_dir = project_root / legacy
        if legacy_dir.is_dir():
            for entry in legacy_dir.iterdir():
                if entry.is_file() and LOG_NAME_RE.match(entry.name):
                    candidates.append(entry)
    candidates.sort(key=lambda p: p.name, reverse=True)
    return candidates


def newest_log(project_root: Path) -> Path | None:
    pooled = pool_logs(project_root)
    return pooled[0] if pooled else None


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


WAITING_ON_YOU_ITEM_RE = re.compile(r"^[-*]\s")


def extract_waiting_on_you(text: str) -> list[str] | None:
    """Top-level list items only, '-' or '*', with no leading indentation,
    the same rule DECISION_LIST_ITEM_RE already applies to Decisions Made. A
    real log ('Approve starting the layout effort', 2026-10-07) carried six
    indented sub-bullets explaining what one item would do; matching on
    `line.lstrip().startswith("- ")` counted each of those as its own,
    undated Waiting on You item, which this script then handed to the next
    wrap's carry-forward as six separate stale items."""
    body = extract_section(text, "Waiting on You")
    if body is None:
        return None
    return [line.rstrip() for line in body if WAITING_ON_YOU_ITEM_RE.match(line)]


def count_decisions(text: str) -> int:
    """Mechanical count of the Decisions Made section's own entries (AC-4). Top-level
    list items, numbered or bulleted (`-` or `*`), with no leading indentation, so a
    nested sub-bullet elaborating on a decision is never counted as its own decision.
    If the section has no top-level list items at all, falls back to counting
    `### ` subheadings, since an architectural decision is sometimes written that
    way instead of as a list (spec Example 2)."""
    body = extract_section(text, "Decisions Made")
    if body is None:
        return 0
    items = sum(1 for line in body if DECISION_LIST_ITEM_RE.match(line))
    if items:
        return items
    return sum(1 for line in body if DECISION_SUBHEADING_RE.match(line))


def log_cutoff_utc(log_path: Path | None) -> dt.datetime | None:
    """The newest log's moment, in UTC, for comparing against capture-record and
    gitignored-file timestamps. Prefers the frontmatter `date:` field, which carries
    an explicit UTC offset; falls back to the filename's date/time, which is naive
    local time and is converted using this machine's current offset."""
    if log_path is None:
        return None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^date:\s*(\S+)", text, re.MULTILINE)
    if match:
        try:
            parsed = dt.datetime.fromisoformat(match.group(1))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            return parsed.astimezone(dt.timezone.utc)
        except ValueError:
            pass
    name_match = re.match(r"^(\d{4}-\d{2}-\d{2})_(\d{2})-(\d{2})_", log_path.name)
    if name_match:
        naive = dt.datetime.strptime(
            f"{name_match.group(1)} {name_match.group(2)}:{name_match.group(3)}",
            "%Y-%m-%d %H:%M",
        )
        return naive.astimezone(dt.timezone.utc)
    return None


# ---------------------------------------------------------------------------
# Evidence Gathering inputs (Requirement 10)
# ---------------------------------------------------------------------------

def capture_records(project_root: Path, cutoff_utc: dt.datetime | None) -> dict:
    capture_dir = project_root / "_local" / "_session-logs" / "_capture"
    if not capture_dir.is_dir():
        return {"available": False, "reason": "no-capture-dir"}
    records = []
    for jsonl_file in sorted(capture_dir.glob("*.jsonl")):
        try:
            lines = jsonl_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("session_id") is None:
                continue
            ts = rec.get("ts")
            if not ts:
                continue
            try:
                ts_dt = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if cutoff_utc is not None and ts_dt <= cutoff_utc:
                continue
            records.append(rec)
    if not records:
        return {"available": False, "reason": "none-qualifying"}
    records.sort(key=lambda r: r["ts"])
    return {
        "available": True,
        "count": len(records),
        "earliest-ts": records[0]["ts"],
        "earliest-head": records[0].get("head"),
        "latest-ts": records[-1]["ts"],
        "latest-head": records[-1].get("head"),
    }


def gitignored_modified(project_root: Path, cutoff_utc: dt.datetime | None, limit: int) -> dict:
    rc, out, _ = run_git(
        ["ls-files", "--others", "--ignored", "--exclude-standard"], project_root, timeout=20
    )
    if rc != 0:
        return {"files": [], "overflow": 0, "error": "git-ls-files-failed"}
    matched: list[str] = []
    overflow = 0
    for rel in out.splitlines():
        if not rel.strip():
            continue
        full = project_root / rel
        try:
            mtime = dt.datetime.fromtimestamp(full.stat().st_mtime, tz=dt.timezone.utc)
        except OSError:
            continue
        if cutoff_utc is not None and mtime <= cutoff_utc:
            continue
        if len(matched) < limit:
            matched.append(rel)
        else:
            overflow += 1
    return {"files": matched, "overflow": overflow}


# ---------------------------------------------------------------------------
# Hygiene sweep detection (Requirement 10; commands ported from hygiene-sweep.md)
# ---------------------------------------------------------------------------

def check1_remote(project_root: Path, fetched: bool) -> dict:
    result: dict = {"as-of": "this-run-fetch" if fetched else "last-fetch"}
    rc, out, _ = run_git(["rev-list", "--left-right", "--count", "HEAD...@{u}"], project_root)
    if rc == 0 and out:
        parts = out.split()
        if len(parts) == 2:
            result["ahead"], result["behind"] = int(parts[0]), int(parts[1])
    rc, out, _ = run_git(["log", "--oneline", "@{u}..HEAD"], project_root)
    result["unpushed-commits"] = out.splitlines() if rc == 0 and out else []
    rc, out, _ = run_git(["log", "--oneline", "HEAD..@{u}"], project_root)
    result["commits-behind"] = out.splitlines() if rc == 0 and out else []
    if fetched:
        rc, out, _ = run_git(["ls-remote", "--heads", "origin"], project_root, timeout=20)
        result["remote-branches"] = (
            [line.split("refs/heads/")[-1] for line in out.splitlines()] if rc == 0 else []
        )
    else:
        rc, out, _ = run_git(
            ["for-each-ref", "--format=%(refname)", "refs/remotes/origin"], project_root
        )
        result["remote-branches"] = (
            [
                line[len("refs/remotes/origin/"):]
                for line in out.splitlines()
                if line and line != "refs/remotes/origin/HEAD"
            ]
            if rc == 0
            else []
        )
    rc, out, _ = run_git(["tag", "-l"], project_root)
    result["tags-tail"] = out.splitlines()[-5:] if rc == 0 else []
    return result


def check2_worktree(project_root: Path) -> dict:
    rc, out, _ = run_git(["status", "--short"], project_root)
    dirty = out.splitlines() if rc == 0 else []
    rc, out, _ = run_git(["stash", "list"], project_root)
    stashes = out.splitlines() if rc == 0 else []
    rc, out, _ = run_git(["worktree", "list"], project_root)
    worktrees = out.splitlines() if rc == 0 else []
    return {"dirty": dirty, "stashes": stashes, "worktrees": worktrees}


def check3_release(project_root: Path) -> dict:
    result: dict = {}
    changelog = project_root / "CHANGELOG.md"
    if not changelog.is_file():
        result["changelog"] = {"available": False, "reason": "missing"}
    else:
        text = changelog.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^## \[Unreleased\]\s*$", text, re.MULTILINE)
        if not match:
            result["changelog"] = {"available": True, "has-unreleased-heading": False}
        else:
            rest = text[match.end():]
            next_heading = re.search(r"^## \[", rest, re.MULTILINE)
            body = rest[: next_heading.start()] if next_heading else rest
            has_content = any(line.strip() for line in body.splitlines())
            result["changelog"] = {
                "available": True,
                "has-unreleased-heading": True,
                "has-content": has_content,
            }
    latest_tag = get_latest_tag(project_root)
    plugin_version = None
    lib_json = project_root / "library.json"
    if lib_json.is_file():
        try:
            plugin_version = json.loads(lib_json.read_text(encoding="utf-8")).get("version")
        except (json.JSONDecodeError, OSError):
            pass
    result["version-vs-tag"] = {
        "latest-tag": latest_tag,
        "library-json-version": plugin_version,
        "consistent": bool(
            latest_tag and plugin_version and latest_tag.lstrip("v") == plugin_version
        ),
    }
    return result


def check4_doc_drift(project_root: Path) -> dict:
    last_tag = get_latest_tag(project_root)
    if not last_tag:
        return {"available": False, "reason": "no-tags"}
    skills_dir = project_root / "skills"
    if not skills_dir.is_dir():
        return {"available": False, "reason": "no-skills-dir"}
    findings: list[str] = []
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill = skill_dir.name
        skill_path = f"skills/{skill}"
        skill_file = skill_dir / "SKILL.md"
        history_file = skill_dir / "HISTORY.md"
        rc, _, _ = run_git(["cat-file", "-e", f"{last_tag}:{skill_path}/SKILL.md"], project_root)
        if rc != 0:
            continue  # new since last tag
        # HISTORY.md is excluded from this diff via pathspec, matching the
        # CI gate scripts/skill-drift-check.py (PR #41). Without the
        # exclusion, a skill whose only change since the tag is its own
        # HISTORY.md (adding a row, annotating one, fixing a typo) counted
        # as "this skill changed", which then compared an unmoved
        # metadata.version against itself and flagged a false "changed but
        # not bumped" finding. Found live on this repository's own main
        # branch: plab-resolve-open-items changed only HISTORY.md since
        # v0.8.0 and was flagged on 2026-10-16.
        rc, _, _ = run_git(
            ["diff", "--quiet", last_tag, "HEAD", "--", skill_path, f":(exclude){skill_path}/HISTORY.md"],
            project_root,
        )
        if rc == 0:
            continue  # unchanged since last tag, HISTORY.md aside
        head_version = None
        if skill_file.is_file():
            m = re.search(r'version:\s*"([^"]+)"', skill_file.read_text(encoding="utf-8", errors="replace"))
            head_version = m.group(1) if m else None
        rc, out, _ = run_git(["show", f"{last_tag}:{skill_path}/SKILL.md"], project_root)
        tag_version = None
        if rc == 0:
            m = re.search(r'version:\s*"([^"]+)"', out)
            tag_version = m.group(1) if m else None
        if head_version and head_version == tag_version:
            findings.append(f"{skill} changed since {last_tag} but metadata.version is still {head_version}")
        if head_version and history_file.is_file():
            hist_text = history_file.read_text(encoding="utf-8", errors="replace")
            if not re.search(rf"^\|\s*{re.escape(head_version)}\s*\|", hist_text, re.MULTILINE):
                findings.append(f"{skill}/HISTORY.md has no entry for version {head_version}")
    return {"available": True, "last-tag": last_tag, "findings": findings}


def check5_log_store(project_root: Path) -> dict:
    organize_script = SCRIPT_DIR / "organize-logs.py"
    store = project_root / "_local" / "_session-logs"
    if not organize_script.is_file():
        return {"available": False, "reason": "organize-logs.py not found"}
    try:
        proc = subprocess.run(
            [sys.executable, str(organize_script), str(store), "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return {"available": False, "reason": "timed out"}
    try:
        return {"available": True, "plan": json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"available": False, "reason": "unparseable output", "returncode": proc.returncode}


# ---------------------------------------------------------------------------
# Verification derivation (AC-5), from the current session's own transcript only
# ---------------------------------------------------------------------------

def locate_transcript(session_id: str | None, transcript_dir: Path | None) -> tuple[Path | None, str | None]:
    """Resolve CLAUDE_CODE_SESSION_ID (or an override) to its transcript file.
    Returns (path, None) on success, or (None, reason) naming why there is none -
    shared by verification derivation and the session-start base resolution so
    both agree on what "this session's transcript" means."""
    session_id = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not session_id:
        return None, "no-session-id"
    base_dir = transcript_dir or (Path.home() / ".claude" / "projects")
    if not base_dir.is_dir():
        return None, "no-transcript-dir"
    matches = sorted(base_dir.glob(f"*/{session_id}.jsonl"))
    if not matches:
        return None, "no-transcript-file"
    return matches[0], None


def get_session_start_ts(transcript_path: Path | None) -> str | None:
    """The transcript's first `timestamp` field (ISO 8601, UTC), used as the
    session-start default base (spec Open Questions item D7). Not every line
    carries one (metadata-only lines do not), so this scans forward to the first
    that does rather than assuming line 1."""
    if transcript_path is None:
        return None
    try:
        with transcript_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = entry.get("timestamp")
                if ts:
                    return ts
    except OSError:
        return None
    return None


def derive_verification(transcript_path: Path | None, unavailable_reason: str | None) -> dict:
    if transcript_path is None:
        return {"available": False, "reason": unavailable_reason or "no-transcript-file"}

    tool_uses: dict[str, tuple[str, str]] = {}
    facts: "collections.deque[dict]" = collections.deque(maxlen=MAX_VERIFICATION_FACTS)
    malformed = 0
    total_matches = 0

    try:
        with transcript_path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    malformed += 1
                    continue
                content = entry.get("message", {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        name = block.get("name", "")
                        command = ""
                        if isinstance(block.get("input"), dict):
                            command = block["input"].get("command", "")
                        tool_uses[block.get("id", "")] = (name, command)
                    elif block.get("type") == "tool_result":
                        tool_use_id = block.get("tool_use_id", "")
                        name, command = tool_uses.get(tool_use_id, ("", ""))
                        if name != "Bash" or not VERIFICATION_COMMAND_RE.search(command):
                            continue
                        total_matches += 1
                        # deque(maxlen=...) keeps the most recent entries: the ones
                        # that matter at wrap time are the latest commands, not the
                        # earliest, which are stale by the time a long session wraps.
                        # Kept full and untruncated here, even though a Bash
                        # command can embed many newlines (a heredoc, a
                        # multi-line script) and run to thousands of
                        # characters: `--json` is this field's one promise of
                        # completeness, and the text digest's 200-character,
                        # single-line cap (render_verification) is a display
                        # choice, not a data-loss one. Truncating here instead
                        # would apply to both and silently cost --json the
                        # same information the text digest only ever meant to
                        # summarize.
                        facts.append(
                            {
                                "command": command,
                                "is_error": bool(block.get("is_error", False)),
                            }
                        )
    except OSError as exc:
        return {"available": False, "reason": f"transcript unreadable: {exc}"}

    return {
        "available": True,
        "source": "claude-code-transcript",
        "transcript": str(transcript_path),
        "facts": list(facts),
        "facts-are": "most recent" if total_matches else "none",
        "fact-overflow": max(0, total_matches - len(facts)),
        "malformed-lines": malformed,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
# The text digest (the default, non-`--json` output) is read once and used
# for everything it returns, per SKILL.md's Evidence Gathering: no
# redirecting it to a file, no re-reading it in pieces, no re-running git or
# re-inventorying `_local/` for anything it already reports. Two real wraps
# measured on 2026-10-16 (14 and 15 assistant API calls, against a baseline
# of 12 and AC-11's target of 6) redirected this output to a file and sliced
# it with `python -c`, because the old text digest was a set of one-line
# counts with no actual content, and the full `--json` output is 34,320
# characters on this repository, over Claude Code's shell output limit.
# This digest instead carries everything the Frontmatter block and the five
# sweep checks need, readably rendered rather than as Python dict reprs, and
# holds the whole thing under a stated budget by capping only the lists a
# session log does not copy verbatim.
#
# NEVER CAPPED: `files-changed` (copied verbatim into the frontmatter's own
# `files-changed:` list) and `waiting-on-you` (copied verbatim into the new
# log's carried-forward Waiting on You section, with its dates). Capping
# either would hand the agent a frontmatter field or a blocked-since date
# that silently disagrees with the real log.
#
# CAPPED, WITH AN EXPLICIT OVERFLOW LINE: everything else that can grow
# without bound on a large or long-lived repository (gitignored-modified
# paths, check1's commit and branch lists, check2's dirty/stash/worktree
# lists, check4's findings, check5's planned moves, verification facts).
# None of these are copied into the log verbatim; the agent reads them,
# judges, and writes its own prose or proposal. A capped list never goes
# silent about what it dropped: `TEXT_LIST_CAP` lines, then one line naming
# how many more exist and that `--json` has them all.
#
# `TEXT_LIST_CAP` was 40 in this digest's first build, measured only against
# this repository's own fixtures. A live run against two real repositories
# on 2026-10-16 (prisant-utilities itself, 20,304 characters; `pm-skills`,
# 43,782) blew the 20,000-character budget: `pm-skills` carries 45 dirty
# entries at roughly 100 characters each, and a verification fact can embed
# a multi-line Bash command (one ran 19 lines and 3,782 characters, because
# the facts kept their embedded newlines). 40 lines of real-repository-sized
# text is not the same size as 40 lines of this repository's short fixture
# paths; the cap is now 10, and verification facts get their own stricter
# rule below rather than sharing this one.

TEXT_LIST_CAP = 10


def render_verbatim(items: list[str]) -> list[str]:
    """One line per item, never capped. Only for a field the log itself
    reproduces verbatim (files-changed, waiting-on-you)."""
    if not items:
        return ["    (none)"]
    return [f"    {item}" for item in items]


def render_capped(items: list[str], cap: int = TEXT_LIST_CAP) -> list[str]:
    """One line per item, capped at `cap` with an explicit overflow line.
    For every list the log does not reproduce verbatim."""
    if not items:
        return ["    (none)"]
    lines = [f"    {item}" for item in items[:cap]]
    if len(items) > cap:
        lines.append(f"    ... {len(items) - cap} more, see --json")
    return lines


def render_check3(check3: dict) -> list[str]:
    lines = []
    changelog = check3.get("changelog", {})
    if not changelog.get("available"):
        lines.append(f"    CHANGELOG.md: {changelog.get('reason', 'unavailable')}")
    elif not changelog.get("has-unreleased-heading"):
        lines.append("    CHANGELOG.md: no [Unreleased] heading")
    else:
        lines.append(f"    CHANGELOG.md: [Unreleased] heading present, has-content={changelog.get('has-content')}")
    vvt = check3.get("version-vs-tag", {})
    lines.append(
        f"    version-vs-tag: latest-tag={vvt.get('latest-tag')} "
        f"library.json={vvt.get('library-json-version')} consistent={vvt.get('consistent')}"
    )
    return lines


def render_check4(check4: dict) -> list[str]:
    if not check4.get("available"):
        return [f"    {check4.get('reason', 'unavailable')}"]
    findings = check4.get("findings", [])
    lines = [f"    last-tag: {check4.get('last-tag')}"]
    lines.append(f"    findings ({len(findings)}):")
    lines.extend(render_capped(findings))
    return lines


def render_check5(check5: dict) -> list[str]:
    if not check5.get("available"):
        return [f"    {check5.get('reason', 'unavailable')}"]
    plan = check5.get("plan", {})
    moves = plan.get("moves", [])
    collisions = plan.get("collisions", [])
    lines = [f"    moves: {len(moves)}  collisions: {len(collisions)}"]
    if moves:
        lines.append("    would file:")
        lines.extend(render_capped([f"{m['from']} -> {m['to']}" for m in moves]))
    if collisions:
        lines.append("    collisions (anomaly, not a routine proposal):")
        lines.extend(render_capped(collisions))
    return lines


# A verification fact's `command` is kept full and untruncated in the data
# (see derive_verification), because a Bash tool call can be a heredoc or a
# multi-line script running to thousands of characters with dozens of
# embedded newlines. The text digest cannot afford that per fact: one such
# fact alone cost 3,782 characters and printed as 19 lines on a real
# `pm-skills` run on 2026-10-16, which is what blew that digest's budget.
# So the text digest, and only the text digest, collapses every fact to one
# line and caps it at FACT_CHAR_CAP characters, and shows at most the
# FACT_WINDOW newest (facts are appended oldest-first, so the newest are the
# tail of the list); `--json` still carries every fact the script kept, up
# to the 50 `MAX_VERIFICATION_FACTS` allows, full text and embedded newlines
# included.
FACT_CHAR_CAP = 200
FACT_WINDOW = 20


def render_verification(ver: dict) -> list[str]:
    if not ver.get("available"):
        return [f"    available: false ({ver.get('reason')})"]
    lines = [f"    available: true (source: {ver.get('source')})"]
    facts = ver.get("facts", [])
    newest = facts[-FACT_WINDOW:] if len(facts) > FACT_WINDOW else facts
    older_not_shown = len(facts) - len(newest)
    lines.append(
        f"    facts ({len(facts)} total, {ver.get('facts-are')}, showing the {len(newest)} newest, "
        f"one line each collapsed and capped at {FACT_CHAR_CAP} chars, "
        f"{ver.get('fact-overflow', 0)} dropped beyond the 50 the script itself keeps):"
    )
    fact_lines = []
    for f in newest:
        collapsed = " ".join(f.get("command", "").split())
        if len(collapsed) > FACT_CHAR_CAP:
            collapsed = collapsed[: FACT_CHAR_CAP - 15] + " ...(truncated)"
        fact_lines.append(f"[{'ERROR' if f.get('is_error') else 'ok'}] {collapsed}")
    lines.extend(render_verbatim(fact_lines))
    if older_not_shown:
        lines.append(f"    ... {older_not_shown} more, see --json")
    lines.append(f"    malformed-lines: {ver.get('malformed-lines', 0)}")
    return lines


def render(data: dict) -> str:
    lines = ["Frontmatter fields"]
    lines.append(f"  machine: {data['machine']}")
    lines.append(f"  repo: {data['repo']}")
    lines.append(f"  branch: {data['branch']}")
    lines.append(f"  date: {data['date']}")
    lines.append(f"  commit-range: {data['commit-range']}")
    lines.append(f"  latest-tag: {data['latest-tag']}")
    lines.append(f"  base: {data['base']['ref']} (resolution: {data['base']['resolution']})")
    files = data["files-changed"]
    lines.append(f"  files-changed ({len(files)}), copy verbatim into the frontmatter, never capped:")
    lines.extend(render_verbatim(files))

    eg = data["evidence-gathering"]
    lines.append("")
    lines.append("Evidence Gathering")
    lines.append(f"  newest-log: {eg['newest-log']}")
    cap_rec = eg["capture-records"]
    if cap_rec.get("available"):
        lines.append(f"  capture-records: {cap_rec['count']} ({cap_rec['earliest-head']} .. {cap_rec['latest-head']})")
    else:
        lines.append(f"  capture-records: none ({cap_rec.get('reason')})")
    woy = eg["waiting-on-you"]
    if woy is None:
        lines.append("  waiting-on-you: n/a (no existing log to carry forward)")
    else:
        lines.append(f"  waiting-on-you ({len(woy)} item(s), verbatim with their dates, never capped):")
        lines.extend(render_verbatim(woy))
    gm = eg["gitignored-modified"]
    lines.append(
        f"  gitignored-modified ({len(gm['files'])} file(s), "
        f"{gm['overflow']} beyond the script's own --gitignored-limit):"
    )
    lines.extend(render_capped(gm["files"]))

    hs = data["hygiene-sweep"]
    lines.append("")
    lines.append("Hygiene Sweep")
    c1 = hs["check1-remote"]
    lines.append(f"  Check 1, remote reconciliation ({c1.get('as-of')}): ahead={c1.get('ahead')} behind={c1.get('behind')}")
    lines.append(f"    unpushed-commits ({len(c1.get('unpushed-commits', []))}):")
    lines.extend(render_capped(c1.get("unpushed-commits", [])))
    lines.append(f"    commits-behind ({len(c1.get('commits-behind', []))}):")
    lines.extend(render_capped(c1.get("commits-behind", [])))
    lines.append(f"    remote-branches ({len(c1.get('remote-branches', []))}):")
    lines.extend(render_capped(c1.get("remote-branches", [])))
    lines.append(f"    tags-tail: {', '.join(c1.get('tags-tail', [])) or '(none)'}")

    c2 = hs["check2-worktree"]
    lines.append(
        f"  Check 2, working tree and worktrees: dirty={len(c2['dirty'])} "
        f"stashes={len(c2['stashes'])} worktrees={len(c2['worktrees'])}"
    )
    lines.append("    dirty:")
    lines.extend(render_capped(c2["dirty"]))
    lines.append("    stashes:")
    lines.extend(render_capped(c2["stashes"]))
    lines.append("    worktrees:")
    lines.extend(render_capped(c2["worktrees"]))

    lines.append("  Check 3, release and repo hygiene:")
    lines.extend(render_check3(hs["check3-release"]))

    lines.append("  Check 4, documentation drift:")
    lines.extend(render_check4(hs["check4-doc-drift"]))

    lines.append("  Check 5, session-log store:")
    lines.extend(render_check5(hs["check5-log-store"]))

    lines.append("")
    lines.append("Verification")
    lines.extend(render_verification(data["verification"]))

    lines.append("")
    fetch = data["fetch"]
    if not fetch.get("ran"):
        lines.append("fetch: not run (pass --fetch in deep and final modes for current remote state)")
    else:
        suffix = f" ({fetch['stderr']})" if fetch.get("stderr") else ""
        lines.append(f"fetch: ran, ok={fetch.get('ok')}{suffix}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive session-log facts from git and the environment."
    )
    parser.add_argument(
        "project_root", nargs="?", default=".",
        help="project to inspect (default: current directory); never the plugin's own install location",
    )
    parser.add_argument(
        "--base",
        help="diff base ref (default: the current session's start commit from its transcript, "
        "then upstream, then latest tag, then none)",
    )
    parser.add_argument(
        "--fetch", action="store_true",
        help="run 'git fetch --no-prune origin --tags' first; the script's only write path",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a text summary")
    parser.add_argument(
        "--count-decisions", metavar="PATH",
        help="second, small invocation: count '## Decisions Made' entries in a drafted log (PATH or '-' for stdin)",
    )
    parser.add_argument("--gitignored-limit", type=int, default=200, help="cap on gitignored-modified entries")
    parser.add_argument("--session-id", help="override CLAUDE_CODE_SESSION_ID (testing)")
    parser.add_argument("--transcript-dir", help="override ~/.claude/projects (testing)")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Write-side guard, mirroring the read-side fix above: a commit message,
    # file path, or Waiting on You item can carry a character this
    # interpreter's default stdout/stderr encoding cannot represent (the
    # same cp1252-on-Windows gap `run_git()` now guards on the read side).
    # Without this, printing such a character raises UnicodeEncodeError
    # instead of reporting the fact it was trying to print.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.count_decisions:
        if args.count_decisions == "-":
            text = sys.stdin.read()
        else:
            path = Path(args.count_decisions)
            if not path.is_file():
                print(f"error: {path} does not exist", file=sys.stderr)
                return 2
            text = path.read_text(encoding="utf-8", errors="replace")
        count = count_decisions(text)
        print(json.dumps({"decisions-count": count}) if args.json else str(count))
        return 0

    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"error: {project_root} is not a directory", file=sys.stderr)
        return 2

    fetch_info = do_fetch(project_root) if args.fetch else {"ran": False}

    transcript_dir = Path(args.transcript_dir) if args.transcript_dir else None
    transcript_path, transcript_unavailable_reason = locate_transcript(args.session_id, transcript_dir)
    session_start_ts = get_session_start_ts(transcript_path)

    base, base_resolution = resolve_base(project_root, args.base, session_start_ts)
    files_flat, files_grouped = get_files_changed(project_root, base)
    log_path = newest_log(project_root)
    cutoff = log_cutoff_utc(log_path)
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path else None

    data = {
        "machine": get_machine(),
        "repo": get_repo(project_root),
        "branch": get_branch(project_root),
        "date": get_date(),
        "base": {"ref": base, "resolution": base_resolution},
        "files-changed": files_flat,
        "files-changed-grouped": files_grouped,
        "commit-range": get_commit_range(project_root, base),
        "latest-tag": get_latest_tag(project_root),
        "fetch": fetch_info,
        "evidence-gathering": {
            "capture-records": capture_records(project_root, cutoff),
            "newest-log": log_path.name if log_path else None,
            "waiting-on-you": extract_waiting_on_you(log_text) if log_text is not None else None,
            "gitignored-modified": gitignored_modified(project_root, cutoff, args.gitignored_limit),
        },
        "hygiene-sweep": {
            "check1-remote": check1_remote(project_root, args.fetch),
            "check2-worktree": check2_worktree(project_root),
            "check3-release": check3_release(project_root),
            "check4-doc-drift": check4_doc_drift(project_root),
            "check5-log-store": check5_log_store(project_root),
        },
        "verification": derive_verification(transcript_path, transcript_unavailable_reason),
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
