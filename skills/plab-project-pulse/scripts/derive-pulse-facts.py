#!/usr/bin/env python3
"""Derive every deterministic `plab-project-pulse` fact in one call.

PP-01 (project pulse): Requirements 1 to 13 of
docs/internal/release-plans/_unassigned/PP-01_project-pulse/spec.md, and the
exact output shape in
skills/plab-project-pulse/references/pulse-schema.md (`pulse-facts.json`).
Discovery (C1) and the sweep (C2) are imported as modules, never
re-implemented here; this script's own job is settings, enrichment,
classification, carry-forward and snapshot reading.

USAGE
-----
  derive-pulse-facts.py --config <settings.local.md> [--mode quick|week]
                        [--state state.json] --out pulse-facts.json
                        [--root PATH ...] [--tz ZONE] [--author-pattern REGEX]
                        [--start YYYY-MM-DD] [--end YYYY-MM-DD]
                        [--max-depth N] [--no-gh] [--unprotected-glob GLOB ...]

A value given as an explicit flag always overrides the same value read from
`--config`. Neither is required to be given alone: `--config` alone, flags
alone, or both together (flags filling in what the file does not set) all
work, which is why every field below has a documented default.

EXIT-CODE CONTRACT
------------------
  0  the facts were written; every expected missing source (no `gh`, no
     state file, no snapshot, a root that does not exist) is a `gaps` entry
  2  BROKEN   not one configured root is a readable directory, so there is
             nothing to discover; nothing is written to `--out`

THE SETTINGS FILE SUBSET
-------------------------
`--config` points at a Markdown file whose YAML frontmatter carries this
plugin's settings (the `.claude/<skill>.local.md` pattern the
`plugin-settings` skill documents). The standard library has no YAML
parser, so this script reads a small, documented subset by hand rather than
vendoring one:

  - a scalar:            `key: value`              (quotes optional)
  - a quoted scalar:     `key: "a value: with a colon"`
  - a block list of scalars:
        key:
          - value one
          - value two
  - a block list of one-level mappings (used for `roots`, so that each root
    carries its own `folder` label alongside its `path`):
        roots:
          - path: /abs/one
            folder: team-a
          - path: /abs/two
            folder: team-b

Comments (`#` at the start of a trimmed line) and blank lines are skipped.
Nothing deeper than one level of mapping is supported, and nothing else in
this plugin needs it.

RECOGNISED FIELDS, THEIR FLAG, AND THEIR DEFAULT
--------------------------------------------------
  roots              --root (repeatable; replaces the file's list wholesale
                      when given)                   no default; see below
  max_depth           --max-depth                   2
  timezone            --tz                           UTC (a `gaps` entry
                                                       is added when neither
                                                       supplies one, because
                                                       Requirement 3 forbids
                                                       guessing an offset)
  author_pattern      --author-pattern               ".*" (a `gaps` entry
                                                       is added: matching
                                                       every author is not
                                                       the same as the
                                                       owner's own commits)
  exclude             (discovery excludes; no flag, config only)
  unprotected_globs   --unprotected-glob (repeatable, additive to config)
  state               --state                        None (no carry-forward)
  gh                  --no-gh forces false            true
  gh_timeout          (config only)                   8

With neither `--root` nor a config `roots` list, there is nothing to
discover and the run exits 2.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import discover  # noqa: E402
import sweep  # noqa: E402

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SNAPSHOT_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_([a-z0-9]+(?:-[a-z0-9]+)*)_([a-z0-9]+(?:-[a-z0-9]+){1,5})\.md$"
)
NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.*)$")
WHY_HERE_RE = re.compile(r"\s*Why here:.*$")
SINCE_RE = re.compile(r"\bsince\s+(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
ID_RE = re.compile(r"\b[A-Z]{1,3}-?\d+\b")
BOLD_RE = re.compile(r"\*\*(.*?)\*\*")
PAREN_RE = re.compile(r"\(([^)]*)\)")
PATH_RE = re.compile(r"`([^`]+)`")
SECTION_RE_TMPL = r"^##\s+%s\s*$"
HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)

STATUS_PROTECTED = {"_session-logs", "_status"}

GH_CALL_FIELDS = {
    "visibility": ["repo", "view", "--json", "visibility"],
    "releases": ["release", "list", "--json", "tagName,publishedAt"],
    "prs": ["pr", "list", "--json", "number", "--state", "open"],
}

GIT_ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")


# ---------------------------------------------------------------------------
# The settings-file subset
# ---------------------------------------------------------------------------


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _strip_comment(s: str) -> str:
    """Drop an inline comment: a `#` preceded by whitespace and outside quotes."""
    quote = None
    for idx, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (idx == 0 or s[idx - 1] in " \t"):
            return s[:idx].rstrip()
    return s


def _value(s: str):
    """One value: a one-line flow list `[a, "b"]` of scalars, else a scalar with quotes
    stripped. Inline comments are dropped first. This matches plab-usage-audit's
    settings subset, so one settings syntax serves both skills."""
    s = _strip_comment(s.strip())
    if s.startswith("[") and s.endswith("]"):
        items, buf, quote = [], "", None
        for ch in s[1:-1]:
            if quote:
                buf += ch
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
                buf += ch
            elif ch == ",":
                items.append(buf)
                buf = ""
            else:
                buf += ch
        if buf.strip():
            items.append(buf)
        return [_strip_quotes(i) for i in items if i.strip()]
    return _strip_quotes(s)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_blank_or_comment(line: str) -> bool:
    s = line.strip()
    return s == "" or s.startswith("#")


def _parse_list(lines, start, indent):
    items = []
    i = start
    while i < len(lines):
        raw = lines[i]
        if _is_blank_or_comment(raw):
            i += 1
            continue
        if _indent(raw) < indent:
            break
        stripped = raw.strip()
        if not stripped.startswith("- "):
            break
        item_text = stripped[2:]
        if ":" in item_text:
            key, _, rest = item_text.partition(":")
            key, rest = key.strip(), rest.strip()
            mapping = {key: _value(rest) if _strip_comment(rest) else None}
            item_col = _indent(raw) + 2
            j = i + 1
            while j < len(lines):
                if _is_blank_or_comment(lines[j]):
                    j += 1
                    continue
                if _indent(lines[j]) != item_col or ":" not in lines[j].strip() \
                        or lines[j].strip().startswith("- "):
                    break
                k2, _, r2 = lines[j].strip().partition(":")
                mapping[k2.strip()] = _value(r2.strip())
                j += 1
            items.append(mapping)
            i = j
        else:
            items.append(_value(item_text))
            i += 1
    return items, i


def _parse_mapping(lines, start, indent):
    result = {}
    i = start
    while i < len(lines):
        raw = lines[i]
        if _is_blank_or_comment(raw):
            i += 1
            continue
        cur = _indent(raw)
        if cur < indent:
            break
        stripped = raw.strip()
        if stripped.startswith("- ") or ":" not in stripped:
            i += 1
            continue
        key, _, rest = stripped.partition(":")
        key, rest = key.strip(), _strip_comment(rest.strip())
        if rest != "":
            result[key] = _value(rest)
            i += 1
            continue
        # a nested block follows: find its indent, then whether it is a
        # list or a (one-level) mapping.
        j = i + 1
        block_indent = None
        while j < len(lines) and (_is_blank_or_comment(lines[j]) or _indent(lines[j]) > cur):
            if not _is_blank_or_comment(lines[j]) and block_indent is None:
                block_indent = _indent(lines[j])
            j += 1
        if block_indent is None:
            result[key] = None
            i += 1
            continue
        sub = lines[i + 1:j]
        if sub and next(s for s in sub if not _is_blank_or_comment(s)).strip().startswith("- "):
            value, _ = _parse_list(sub, 0, block_indent)
        else:
            value, _ = _parse_mapping(sub, 0, block_indent)
        result[key] = value
        i = j
    return result, i


def parse_settings(text: str) -> dict:
    """The frontmatter block of a settings.local.md file, as the subset
    documented in this script's module docstring. `{}` for no frontmatter
    at all, which is a legitimate "use every default" file."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    lines = m.group(1).splitlines()
    value, _ = _parse_mapping(lines, 0, 0)
    return value


# ---------------------------------------------------------------------------
# Snapshot reading (Requirements 9, 10, 11)
# ---------------------------------------------------------------------------


def read_frontmatter(text: str) -> dict:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        line = line.split(" #", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        fm[k.strip()] = _strip_quotes(v)
    return fm


def _section_body(text: str, heading: str):
    pattern = re.compile(SECTION_RE_TMPL % re.escape(heading), re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None
    start = m.end()
    nxt = HEADING_RE.search(text, start)
    return text[start: nxt.start() if nxt else len(text)]


def _strip_numbered(line: str) -> str | None:
    m = NUMBERED_RE.match(line)
    if not m:
        return None
    return WHY_HERE_RE.sub("", m.group(1)).strip()


def _plain_items(body, source):
    if body is None:
        return []
    out = []
    for line in body.splitlines():
        text = _strip_numbered(line)
        if text:
            out.append({"text": text, "source": source})
    return out


def _decision_items(body, source):
    if body is None:
        return []
    out = []
    for line in body.splitlines():
        text = _strip_numbered(line)
        if not text:
            continue
        id_m = ID_RE.search(text)
        item_id = id_m.group(0) if id_m else None
        paren_m = PAREN_RE.search(text)
        bold_m = BOLD_RE.search(text)
        if paren_m:
            handle = paren_m.group(1).strip() or None
        elif bold_m:
            handle = bold_m.group(1)
            if item_id:
                handle = handle.replace(item_id, "")
            handle = handle.strip(" -") or None
        else:
            handle = None
        path_m = PATH_RE.search(text)
        home = path_m.group(1) if path_m else None
        out.append({"id": item_id, "handle": handle, "home": home, "source": source})
    return out


def find_snapshot(repo_path: str):
    """R9, R10: the newest file matching the snapshot pattern in
    `_local/_status/`, or None. A file that does not match the pattern
    (a hand-kept register, for example) is never considered, even if it is
    the newest file in the folder by name or by time (AC-13)."""
    local_dir = discover._find_child_ci(repo_path, "_local")
    if not local_dir:
        return None
    status_dir = discover._find_child_ci(local_dir, "_status")
    if not status_dir:
        return None
    try:
        with os.scandir(status_dir) as it:
            candidates = sorted(e.name for e in it if e.is_file(follow_symlinks=False) and SNAPSHOT_RE.match(e.name))
    except OSError:
        return None
    if not candidates:
        return None
    name = candidates[-1]  # YYYY-MM-DD prefix sorts correctly; ties broken by name
    path = os.path.join(status_dir, name)
    try:
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    fm = read_frontmatter(text)
    rel_source = str(Path(path).relative_to(repo_path).as_posix())
    waiting = _plain_items(_section_body(text, "Waiting on You"), rel_source)
    whats_next = _plain_items(_section_body(text, "What's Next"), rel_source)
    pending_decisions = _decision_items(_section_body(text, "Pending Decisions"), rel_source)
    return {
        "path": rel_source,
        "date": fm.get("date"),
        "head": fm.get("head"),
        "waiting": _int_or(fm.get("waiting"), len(waiting)),
        "pending_decisions_count": _int_or(fm.get("pending-decisions"), len(pending_decisions)),
        "next": _int_or(fm.get("next"), len(whats_next)),
        "waiting_on_you": waiting,
        "whats_next": whats_next,
        "pending_decisions": pending_decisions,
    }


def _int_or(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def snapshot_is_fresh(snapshot, sweep_rec) -> bool:
    """R9: fresh when the snapshot's head equals the repository's head
    commit, or its date is on or after the newest own commit's date."""
    if snapshot is None or sweep_rec is None:
        return False
    head = sweep_rec.get("head")
    if snapshot.get("head") and head and (snapshot["head"] == head or head.startswith(snapshot["head"])):
        return True
    snap_date, last_commit = snapshot.get("date"), sweep_rec.get("last_commit_date")
    if snap_date and (not last_commit or snap_date >= last_commit):
        return True
    return False


# ---------------------------------------------------------------------------
# Waiting-item ages (Requirement 11)
# ---------------------------------------------------------------------------


def normalize_text(text: str) -> str:
    t = text.lower()
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[^\w]+", "", t)
    t = re.sub(r"[^\w]+$", "", t)
    return t


def age_waiting_items(items, repo_name, state, window_end: dt.date):
    out = []
    first_seen_store = (state or {}).get("first_seen", {})
    for item in items:
        since = None
        m = SINCE_RE.search(item.get("text", ""))
        if m:
            since = m.group(1)
        key = "%s::%s" % (repo_name, normalize_text(item.get("text", "")))
        first_seen = since or first_seen_store.get(key) or window_end.isoformat()
        try:
            age_days = max(0, (window_end - dt.date.fromisoformat(first_seen)).days)
        except ValueError:
            age_days, first_seen = 0, window_end.isoformat()
        out.append({**item, "since": since, "first_seen": first_seen, "age_days": age_days})
    return out


# ---------------------------------------------------------------------------
# Unprotected work (Requirement 12)
# ---------------------------------------------------------------------------


def _git_check_ignore(repo_path, rel_paths):
    """Which of `rel_paths` (repo-relative, posix) `git check-ignore`
    confirms are gitignored. Read-only; one call for the whole batch.

    NUL-separated bytes, not text: on Windows, text mode turns each newline
    into CRLF, git then reads every path but the last with a trailing CR,
    and only the last path ever matched. `-z` also stops git quoting paths
    that hold unusual characters."""
    if not rel_paths:
        return set()
    try:
        r = subprocess.run(
            ["git", "-c", "core.fsmonitor=false", "--no-optional-locks", "-C", str(repo_path),
             "check-ignore", "-z", "--stdin"],
            input=("\0".join(rel_paths) + "\0").encode("utf-8"), capture_output=True,
            timeout=20, env=GIT_ENV,
        )
    except (subprocess.TimeoutExpired, OSError):
        return set()
    return {x for x in r.stdout.decode("utf-8", errors="replace").split("\0") if x}


def _changed_in_window(path: str, start: dt.date, end: dt.date, tz: ZoneInfo) -> bool:
    try:
        mtime_utc = dt.datetime.fromtimestamp(os.path.getmtime(path), tz=dt.timezone.utc)
    except OSError:
        return False
    return start <= mtime_utc.astimezone(tz).date() <= end


def unprotected_work(repo_path: str, start: dt.date, end: dt.date, extra_globs, tz: ZoneInfo):
    """R12: files changed in the window, under gitignored `_local/`
    subfolders other than `_session-logs/` and `_status/`, plus the
    configured globs. Scoped to `_local/` and the configured globs only,
    never a full walk of the repository."""
    local_dir = discover._find_child_ci(repo_path, "_local")
    candidates = []  # (abs_path, group_key)
    if local_dir:
        try:
            with os.scandir(local_dir) as it:
                subfolders = [e for e in it if e.is_dir(follow_symlinks=False)
                              and e.name not in STATUS_PROTECTED and e.name.lower() not in
                              {s.lower() for s in STATUS_PROTECTED}]
        except OSError:
            subfolders = []
        local_name = Path(local_dir).name
        for sub in subfolders:
            group = "%s/%s" % (local_name, sub.name)
            for dirpath, dirnames, filenames in os.walk(sub.path):
                dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git")]
                for fn in filenames:
                    fp = os.path.join(dirpath, fn)
                    if _changed_in_window(fp, start, end, tz):
                        candidates.append((fp, group))
    for pattern in extra_globs or []:
        for match in Path(repo_path).glob(pattern):
            if match.is_file() and _changed_in_window(str(match), start, end, tz):
                candidates.append((str(match), pattern))

    rel_map = {}
    for abs_path, group in candidates:
        try:
            rel = Path(abs_path).resolve().relative_to(Path(repo_path).resolve()).as_posix()
        except ValueError:
            continue
        rel_map[rel] = (abs_path, group)
    ignored = _git_check_ignore(repo_path, list(rel_map))

    by_group = {}
    for rel, (abs_path, group) in rel_map.items():
        if rel not in ignored:
            continue
        try:
            mtime_utc = dt.datetime.fromtimestamp(os.path.getmtime(abs_path), tz=dt.timezone.utc)
        except OSError:
            continue
        local_date = mtime_utc.astimezone(tz).date()  # the window is local dates, R3
        if not (start <= local_date <= end):
            continue
        g = by_group.setdefault(group, {"folder": group, "files_changed": 0, "newest_mtime": None})
        g["files_changed"] += 1
        iso = mtime_utc.isoformat().replace("+00:00", "Z")
        if g["newest_mtime"] is None or iso > g["newest_mtime"]:
            g["newest_mtime"] = iso
    return sorted(by_group.values(), key=lambda g: g["folder"])


# ---------------------------------------------------------------------------
# gh enrichment (Requirement 4)
# ---------------------------------------------------------------------------


def gh_enrich(repo_path, gh_exe, timeout, start: dt.date, end: dt.date, gaps, repo_label):
    exe = shutil.which(gh_exe)
    if exe is None:
        gaps.append({"source": "gh", "detail": "`%s` is not on PATH" % gh_exe, "repo": repo_label})
        return None
    out = {"visibility": None, "releases_in_window": [], "open_prs": None}
    for key, args in GH_CALL_FIELDS.items():
        try:
            r = subprocess.run([exe, *args], cwd=str(repo_path), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            gaps.append({"source": "gh", "detail": "`gh %s` timed out after %ss" % (" ".join(args), timeout),
                        "repo": repo_label})
            continue
        except OSError as exc:
            gaps.append({"source": "gh", "detail": "`gh %s` failed: %s" % (" ".join(args), exc), "repo": repo_label})
            continue
        if r.returncode != 0:
            gaps.append({"source": "gh", "detail": "`gh %s` exited %d: %s" % (
                " ".join(args), r.returncode, (r.stderr or "").splitlines()[:1]), "repo": repo_label})
            continue
        try:
            data = json.loads(r.stdout or ("[]" if key != "visibility" else "{}"))
        except json.JSONDecodeError:
            gaps.append({"source": "gh", "detail": "`gh %s` returned unparseable JSON" % " ".join(args),
                        "repo": repo_label})
            continue
        if key == "visibility":
            # `gh repo view --json visibility` returns PRIVATE/PUBLIC/INTERNAL;
            # pulse-schema.md's example shows lowercase ("private").
            visibility = data.get("visibility")
            out["visibility"] = visibility.lower() if visibility else None
        elif key == "releases":
            for rel in data:
                published = (rel.get("publishedAt") or "")[:10]
                if published and start.isoformat() <= published <= end.isoformat():
                    out["releases_in_window"].append({"tag": rel.get("tagName"), "date": published})
        elif key == "prs":
            out["open_prs"] = len(data)
    return out


# ---------------------------------------------------------------------------
# Settings assembly
# ---------------------------------------------------------------------------


def build_settings(args) -> tuple[dict, list]:
    gaps = []
    cfg = {}
    if args.config:
        p = Path(args.config)
        if p.is_file():
            cfg = parse_settings(p.read_text(encoding="utf-8-sig", errors="replace"))
        else:
            gaps.append({"source": "settings", "detail": "config file not found: %s" % args.config})

    roots_cfg = cfg.get("roots") or []
    if args.root:
        roots = [{"path": r, "folder": Path(r).resolve().name} for r in args.root]
    elif roots_cfg:
        # A root is a plain path (references/settings-example.md) or a {path, folder} mapping.
        roots = []
        for r in roots_cfg:
            if isinstance(r, str) and r.strip():
                path = os.path.expanduser(r.strip())
                roots.append({"path": path, "folder": Path(path).resolve().name})
            elif isinstance(r, dict) and r.get("path"):
                path = os.path.expanduser(r["path"])
                roots.append({"path": path, "folder": r.get("folder") or Path(path).resolve().name})
    else:
        roots = []

    max_depth = args.max_depth if args.max_depth is not None else _int_or(cfg.get("max_depth"), 2)

    tz = args.tz or cfg.get("timezone")
    if not tz:
        gaps.append({"source": "timezone", "detail": "no --tz and no `timezone` in settings; defaulting to UTC"})
        tz = "UTC"

    author_pattern = args.author_pattern or cfg.get("author_pattern")
    if not author_pattern:
        gaps.append({"source": "author_pattern", "detail": "no --author-pattern and no `author_pattern` in "
                                                            "settings; matching every author"})
        author_pattern = ".*"

    # C5: 2 ("could not run") on a setting that exists but is invalid, not
    # a gaps entry (which is for an expected absence) and not an
    # uncaught traceback.
    try:
        ZoneInfo(tz)
    except Exception as exc:  # ZoneInfoNotFoundError, or a malformed name
        raise Broken("not a valid IANA time zone: %r (%s)" % (tz, exc))
    try:
        re.compile(author_pattern)
    except re.error as exc:
        raise Broken("not a valid author_pattern regex: %r (%s)" % (author_pattern, exc))

    excludes = list(cfg.get("exclude") or [])
    unprotected_globs = list(cfg.get("unprotected_globs") or []) + list(args.unprotected_glob or [])
    state_path = args.state or cfg.get("state_path") or cfg.get("state")
    if state_path:
        state_path = os.path.expanduser(state_path)
    # `gh` is a mapping {enabled, timeout_seconds} as documented, or a bare true/false.
    gh_cfg = cfg.get("gh", True)
    if isinstance(gh_cfg, dict):
        gh_on = str(gh_cfg.get("enabled", "true")).strip().lower() not in ("false", "no", "0", "off")
        gh_timeout = _int_or(gh_cfg.get("timeout_seconds"), _int_or(cfg.get("gh_timeout"), 8))
    else:
        gh_on = str(gh_cfg).strip().lower() not in ("false", "no", "0", "off")
        gh_timeout = _int_or(cfg.get("gh_timeout"), 8)
    gh_enabled = False if args.no_gh else gh_on

    return {
        "roots": roots, "max_depth": max_depth, "timezone": tz, "author_pattern": author_pattern,
        "excludes": excludes, "unprotected_globs": unprotected_globs, "state_path": state_path,
        "gh_enabled": gh_enabled, "gh_timeout": gh_timeout,
    }, gaps


def load_state(state_path, gaps):
    if not state_path:
        gaps.append({"source": "state", "detail": "no --state given; nothing carries forward"})
        return {}
    p = Path(state_path)
    if not p.is_file():
        gaps.append({"source": "state", "detail": "state file not found: %s" % state_path})
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        gaps.append({"source": "state", "detail": "state file could not be read: %s" % exc})
        return {}


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def derive(args) -> dict:
    gaps = []
    settings, settings_gaps = build_settings(args)
    gaps.extend(settings_gaps)

    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(
        ZoneInfo(settings["timezone"])).date()
    end = dt.date.fromisoformat(args.end) if args.end else today
    start = dt.date.fromisoformat(args.start) if args.start else end - dt.timedelta(days=6)
    prior_start = dt.date.fromisoformat(args.prior_start) if args.prior_start else start - dt.timedelta(days=7)

    readable_roots = []
    for r in settings["roots"]:
        if os.path.isdir(r["path"]):
            readable_roots.append(r)
        else:
            gaps.append({"source": "roots", "detail": "root does not exist, skipped: %s" % r["path"]})
    if not readable_roots:
        raise Broken("no configured root is a readable directory")

    t0 = time.monotonic()
    repos, links = discover.discover([r["path"] for r in readable_roots], settings["max_depth"], settings["excludes"])
    aliases = discover.resolve_aliases(repos, links)
    discover_seconds = time.monotonic() - t0

    folder_by_root = {str(Path(r["path"]).resolve()): r["folder"] for r in readable_roots}
    for r in repos:
        r["folder"] = folder_by_root.get(r["root"], Path(r["root"]).name)
    for a in aliases:
        a["folder"] = folder_by_root.get(a["root"], Path(a["root"]).name)

    state = load_state(settings["state_path"], gaps)
    state_repos = (state or {}).get("repos", {})

    t1 = time.monotonic()
    sweeps = {}

    def _sweep_one(r):
        return sweep.sweep_repo(r["path"], start.isoformat(), end.isoformat(),
                                prior_start.isoformat(), settings["timezone"],
                                settings["author_pattern"], repo_name=r["rel"], folder=r["folder"])

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_sweep_one, r): r for r in repos}
        for fut in concurrent.futures.as_completed(futures):
            r = futures[fut]
            try:
                sweeps[r["path"]] = fut.result()
            except sweep.Broken as exc:
                gaps.append({"source": "sweep", "detail": str(exc), "repo": r["rel"]})
                sweeps[r["path"]] = None
    gaps.sort(key=lambda g: (g.get("source", ""), g.get("repo", ""), g.get("detail", "")))
    sweep_seconds = time.monotonic() - t1

    logs_top = []
    out_repos = []
    for r in repos:
        rec = sweeps.get(r["path"])
        repo_logs = discover.find_session_logs(r["path"])
        logs_in_window = [l for l in repo_logs if l["date"] and start.isoformat() <= l["date"] <= end.isoformat()]
        for l in logs_in_window:
            logs_top.append({"file": l["file"], "repo": r["rel"], "date": l["date"], "time": l["time"],
                             "nonstandard_name": l["nonstandard_name"]})

        gh_rec = None
        if settings["gh_enabled"] and rec and rec.get("remote"):
            gh_rec = gh_enrich(r["path"], "gh", settings["gh_timeout"], start, end, gaps, r["rel"])

        snapshot = find_snapshot(r["path"])
        fresh = snapshot_is_fresh(snapshot, rec)
        has_own_commit = bool(rec and rec.get("commits_focus", 0) > 0)
        activity = "active" if (has_own_commit or logs_in_window) else "dormant"

        prior_state = state_repos.get(r["rel"])
        carried = None
        if fresh:
            status_source = "snapshot"
        elif activity == "active":
            status_source = "scout"
        elif prior_state:
            status_source = "carried"
            carried = dict(prior_state.get("status") or {})
            carried["carried_from"] = prior_state.get("refreshed")
        else:
            status_source = "sweep-only"

        if snapshot:
            snapshot["fresh"] = fresh
            snapshot["waiting_on_you"] = age_waiting_items(snapshot["waiting_on_you"], r["rel"], state, end)

        to_scout = status_source == "scout"
        current_status_candidate = activity == "active" and not fresh

        out_repos.append({
            "repo": r["rel"], "path": r["path"], "folder": r["folder"], "alias_of": None,
            "sweep": rec, "gh": gh_rec, "activity": activity, "logs_in_window": [l["file"] for l in logs_in_window],
            "snapshot": snapshot, "status_source": status_source, "carried": carried,
            "unprotected_work": unprotected_work(r["path"], start, end, settings["unprotected_globs"],
                                                 ZoneInfo(settings["timezone"])),
            "to_scout": to_scout, "current_status_candidate": current_status_candidate,
        })

    for a in aliases:
        out_repos.append({
            "repo": a["rel"], "path": a["path"], "folder": a["folder"], "alias_of": a["alias_of"],
            "sweep": None, "gh": None, "activity": "dormant", "logs_in_window": [], "snapshot": None,
            "status_source": "sweep-only", "carried": None, "unprotected_work": [], "to_scout": False,
            "current_status_candidate": False,
        })

    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": args.mode,
        "window": {"start": start.isoformat(), "end": end.isoformat(), "prior_start": prior_start.isoformat(),
                  "timezone": settings["timezone"]},
        "roots": [r["path"] for r in readable_roots],
        "repos": out_repos,
        "logs": logs_top,
        "gaps": gaps,
        "timings": {"discover_seconds": round(discover_seconds, 3), "sweep_seconds": round(sweep_seconds, 3)},
    }


class Broken(Exception):
    pass


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Derive every deterministic project-pulse fact in one call.")
    parser.add_argument("--config", help="a settings.local.md file")
    parser.add_argument("--mode", choices=["quick", "week"], default="week")
    parser.add_argument("--state", help="an existing state.json, for carry-forward")
    parser.add_argument("--out", required=True, help="where to write pulse-facts.json")
    parser.add_argument("--root", action="append", help="a root to discover; repeatable; overrides the config's roots")
    parser.add_argument("--tz", help="the IANA zone; overrides the config's timezone")
    parser.add_argument("--author-pattern", dest="author_pattern", help="a Python regex; overrides the config")
    parser.add_argument("--start", help="YYYY-MM-DD; default is 6 days before --end")
    parser.add_argument("--end", help="YYYY-MM-DD; default is today in --tz")
    parser.add_argument("--prior-start", dest="prior_start", help="YYYY-MM-DD; default is 7 days before --start")
    parser.add_argument("--max-depth", type=int, dest="max_depth")
    parser.add_argument("--no-gh", action="store_true", dest="no_gh")
    parser.add_argument("--unprotected-glob", action="append", dest="unprotected_glob", default=[])
    parser.add_argument("--today", help="override today's date (for testing)")
    args = parser.parse_args(argv)

    try:
        facts = derive(args)
    except Broken as exc:
        sys.stderr.write("BROKEN: %s\n" % exc)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    print("%d repo(s), %d gap(s) -> %s" % (len(facts["repos"]), len(facts["gaps"]), out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
