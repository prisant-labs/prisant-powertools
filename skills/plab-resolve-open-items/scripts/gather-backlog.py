#!/usr/bin/env python3
"""Gather every pending backlog item across a repository, in one call.

USAGE
-----
  gather-backlog.py --repo <root> [--json] [--today YYYY-MM-DD]

EXIT-CODE CONTRACT
------------------
  0  the sweep completed, whether it found items or none
  2  BROKEN   a source this sweep should have read could not be read or
             parsed; nothing is printed to stdout

NEVER INTERPRET 2 AS CLEAN. An empty JSON array and a BROKEN exit look
different on stdout/stderr, but a caller must still branch on the exit code,
not on whether stdout parses: this is the same contract as
`scripts/walk-check.py` and the repository's other gates.

WHAT THIS GATHERS
------------------
Two kinds of source, both read-only.

1. The "## Open Questions / Decisions" section (or a heading variant
   `references/walk-format.md` names) of every git-tracked Markdown file
   whose frontmatter `type` is `spec`, `implementation-plan` or
   `release-plan`. Only rows whose `Status` is `Open`, `Needs info` or the
   legacy `Proposed` are kept.
2. The "## Waiting on You" section of the newest session log, found by the
   newest-wins rule in `skills/plab-continue-session/references/log-discovery.md`
   (mirrored here, not imported, since that reference is prose, not code).

WHY THE HEADING RULE IS IMPORTED, NOT RE-DECLARED
--------------------------------------------------
`scripts/walk-check.py` already defines `SECTION_RE`, `LEVEL2_RE`,
`tables_in`, `is_separator` and `TABLE_COLUMNS` for the identical decisions-
section format. Re-declaring them here would give this plugin two
definitions of the same heading that could silently drift apart. This
script loads that module by file path (`importlib`, not a dotted import,
because the filename is not a valid identifier) and reuses its constants
and helpers directly.

WHAT COUNTS AS BROKEN, AND WHAT COUNTS AS EMPTY
------------------------------------------------
A typed document with no decisions-section heading at all (most
implementation plans) contributes nothing: that is its correct, empty
state, not a defect. A decisions section whose body is prose with no table
("None at this time.", or an older document whose items were all written
before the maintainer-block format existed) also contributes nothing, for
the same reason: there is no row to misread, so there is nothing to get
wrong. BROKEN is reserved for a source this sweep positively tried to read
and could not: a frontmatter fence that never closes, a decisions table
that exists but is missing a required column, or a data row whose cell
count does not match its header. On the first such source, gathering stops
and prints nothing to stdout, naming that one source on stderr, rather than
returning a shorter list that looks complete.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing walk-check.py below must not write __pycache__

TYPED_KINDS = ("spec", "implementation-plan", "release-plan")

# The one named constant the status filter hangs off, so the P1 canary
# (delete this filter, rerun the tests, see them fail naming "status") is a
# single-line edit rather than a scavenger hunt through the module.
PENDING_STATUSES = {"Open", "Needs info", "Proposed"}

FRONTMATTER_LINE_RE = re.compile(r"^([A-Za-z][\w-]*):\s?(.*)$")
WAITING_HEADING_RE = re.compile(r"^##\s+Waiting on You\s*$")
LEVEL2_GENERIC_RE = re.compile(r"^##\s")
BULLET_RE = re.compile(r"^-\s+\*\*(.+?)\*\*\s*(?:\(blocked since (\d{4}-\d{2}-\d{2})\))?\.?\s*(.*)$")
LOG_NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_.*\.md$")
MONTH_DIR_RE = re.compile(r"^\d{4}-\d{2}$")


class Broken(Exception):
    """Raised for every source this sweep should have read but could not."""


# ---------------------------------------------------------------------------
# scripts/walk-check.py's heading rule, loaded rather than re-declared
# ---------------------------------------------------------------------------


def load_walk_check():
    path = Path(__file__).resolve().parent / "walk-check.py"
    spec = importlib.util.spec_from_file_location("plab_walk_check_for_gather", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def read_frontmatter(text, label):
    """Return the flat frontmatter dict, or None when the file has none.

    Raises Broken when an opening fence is found but never closes.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return None
    start = i + 1
    end = None
    for j in range(start, len(lines)):
        if lines[j].strip() == "---":
            end = j
            break
    if end is None:
        raise Broken("%s: frontmatter fence never closes" % label)
    fm = {}
    for line in lines[start:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = FRONTMATTER_LINE_RE.match(line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip("\"'")
    return fm


def read_text(path, label):
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise Broken("%s: cannot be read (%s)" % (label, exc))
    except UnicodeDecodeError as exc:
        raise Broken("%s: not valid UTF-8 (%s)" % (label, exc))


# ---------------------------------------------------------------------------
# Age
# ---------------------------------------------------------------------------


def _parse_date(value):
    if not value:
        return None
    value = value.strip()
    if value in ("", "(none)", "none", "None", "-"):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def compute_age(today, *candidates):
    """The first parseable date among candidates, in priority order, as an
    age in days against today. The literal string "unknown" when none of
    them parse. Never an invented age."""
    for value in candidates:
        parsed = _parse_date(value)
        if parsed is not None:
            return (today - parsed).days
    return "unknown"


# ---------------------------------------------------------------------------
# Source 1: decisions sections in typed planning documents
# ---------------------------------------------------------------------------


def list_tracked_markdown(repo_root):
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", "*.md"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        raise Broken("git ls-files failed: %s" % (result.stderr or "").strip())
    return [line for line in result.stdout.splitlines() if line]


def gather_decisions_items(repo_root, rel_paths, today, wc):
    items = []
    for rel in rel_paths:
        path = repo_root / rel
        text = read_text(path, rel)
        fm = read_frontmatter(text, rel)
        if fm is None:
            continue
        if fm.get("type") not in TYPED_KINDS:
            continue
        doc_status = fm.get("status")
        doc_created = fm.get("created")

        lines = text.splitlines()
        starts = [i for i, ln in enumerate(lines) if wc.SECTION_RE.match(ln)]
        if not starts:
            continue  # no decisions section at all: contributes nothing
        s = starts[0]
        e = next((i for i in range(s + 1, len(lines)) if wc.LEVEL2_RE.match(lines[i])), len(lines))
        section = lines[s + 1:e]

        tables = list(wc.tables_in(section))
        if not tables:
            continue  # "None at this time." or an unstructured section: contributes nothing
        _, rows = tables[0]
        header = rows[0]
        missing = [c for c in ("ID", "Status") if c not in header]
        if missing:
            raise Broken("%s: decisions table has no %s column" % (rel, missing[0]))
        col = {name: header.index(name) for name in header}
        # A document written before references/decisions-section.md's five-column
        # standard existed often carries a differently named second column
        # ("Question", "Item") doing the same job as "Title". Only ID and Status
        # are load-bearing for this script (identity and the pending filter), so
        # a missing Title is tolerated: fall back to whatever other column is
        # not ID or Status, and only then to a literal placeholder.
        title_col = "Title" if "Title" in col else next(
            (name for name in header if name not in ("ID", "Status")), None
        )
        data_rows = [r for r in rows[1:] if not wc.is_separator(r)]

        for r in data_rows:
            if len(r) != len(header):
                raise Broken(
                    "%s: a decisions-table row has %d cell(s) against a %d-column header"
                    % (rel, len(r), len(header))
                )
            status = r[col["Status"]].strip()
            if status not in PENDING_STATUSES:
                continue
            updated = r[col["Updated"]] if "Updated" in col else None
            title = r[col[title_col]].strip() if title_col else "(untitled)"
            items.append({
                "home": rel.replace(os.sep, "/"),
                "id": r[col["ID"]].strip(),
                "title": title,
                "status": status,
                "age_days": compute_age(today, updated, doc_created),
                "source_kind": "decisions-section",
                "home_status": doc_status,
            })
    return items


# ---------------------------------------------------------------------------
# Source 2: the newest session log's Waiting on You section
# ---------------------------------------------------------------------------


def find_newest_log(repo_root):
    """Mirror skills/plab-continue-session/references/log-discovery.md's
    newest-wins rule: pool the flat store, its YYYY-MM month folders and the
    two legacy stores, then take the newest by filename. A store that does
    not exist contributes nothing; it is not broken."""
    stores = []
    current = repo_root / "_local" / "_session-logs"
    if current.is_dir():
        stores.append(current)
        for entry in sorted(current.iterdir()):
            if entry.is_dir() and MONTH_DIR_RE.match(entry.name):
                stores.append(entry)
    for legacy in (repo_root / "_agent-context" / "session-log", repo_root / "AGENTS" / "session-log"):
        if legacy.is_dir():
            stores.append(legacy)

    candidates = []
    for store in stores:
        for p in store.glob("*.md"):
            if LOG_NAME_RE.match(p.name):
                candidates.append(p)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.name, reverse=True)
    return candidates[0]


def gather_waiting_on_items(repo_root, today):
    log_path = find_newest_log(repo_root)
    if log_path is None:
        return []
    rel_log = os.path.relpath(log_path, repo_root).replace(os.sep, "/")
    text = read_text(log_path, rel_log)
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if WAITING_HEADING_RE.match(ln)]
    if not starts:
        return []
    s = starts[0]
    e = next((i for i in range(s + 1, len(lines)) if LEVEL2_GENERIC_RE.match(lines[i])), len(lines))
    section = lines[s + 1:e]

    items = []
    n = 0
    for ln in section:
        m = BULLET_RE.match(ln.strip())
        if not m:
            continue
        title, blocked_since, _rest = m.groups()
        n += 1
        items.append({
            "home": rel_log,
            "id": "W%d" % n,
            "title": title.strip(),
            "status": "Open",
            "age_days": compute_age(today, blocked_since),
            "source_kind": "waiting-on",
        })
    return items


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def gather(repo_root, today):
    wc = load_walk_check()
    rel_paths = list_tracked_markdown(repo_root)
    decisions_items = gather_decisions_items(repo_root, rel_paths, today, wc)
    waiting_items = gather_waiting_on_items(repo_root, today)
    return decisions_items + waiting_items


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Gather every pending backlog item across the repository in one call."
    )
    parser.add_argument("--repo", default=".", help="repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="emit the gathered items as a JSON array")
    parser.add_argument("--today", help="override today's date as YYYY-MM-DD (for testing)")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo).resolve()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    try:
        items = gather(repo_root, today)
    except Broken as exc:
        sys.stderr.write("BROKEN: %s\n" % exc)
        return 2

    if args.json:
        print(json.dumps(items, indent=2))
    else:
        print("%d item(s) gathered across the repository." % len(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
