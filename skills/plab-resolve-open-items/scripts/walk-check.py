#!/usr/bin/env python3
"""
plab-resolve-open-items self-check. Invoked by the skill after each write-back
and after writing each walk record, and by CI against the committed sample.

USAGE
-----
  walk-check.py record <walk-record.md>
  walk-check.py writeback <before.md> <after.md>

EXIT-CODE CONTRACT
------------------
  0  CLEAN    self-test passed AND the input satisfies every rule of its mode
  1  FINDINGS self-test passed AND at least one rule is violated
  2  BROKEN   a file is absent, unreadable or not UTF-8, a write-back pair has
              no decisions section in the documented format, the arguments
              are wrong, or the self-test could not prove this checker works

NEVER INTERPRET 2 AS CLEAN. "I could not look" is not "I looked and it was
fine". This is the same contract as `skills/plab-audit/scripts/bundle-check.py`
and the repository's own gates.

RECORD MODE: WHAT IT CHECKS, AND WHICH ACCEPTANCE CRITERION EACH RULE CARRIES
------------------------------------------------------------------------------
The format is `references/walk-record.md`. The criteria are WD-01's.

  R1  frontmatter: type walk-record, a YYYY-MM-DD date, a repo,     AC-10
      an integer rounds of at least 1, and a non-empty handle and   WD-01
      handle-source (references/write-back.md's one-handle rule)    finding 2
  R2  an items table with exactly the seven documented columns,     AC-10
      and at least one row
  R3  every Walk ID is Q, D or T plus a number, and is unique       AC-2
  R4  every Home is "none" or ends in the item's own id             AC-3
  R5  every State belongs to its series' vocabulary                 AC-4, AC-6
  R6  every decided or provisional row names its Follow-up          AC-19
  R7  T rows land in the walk record only; unanswered D rows are    AC-20, AC-6
      "not written"; assumed Q rows answer "default: ..."
  R8  one "## Round N" section per round; no Round cell beyond      AC-18
      them; every provisional row quotes the maintainer's words

WRITEBACK MODE: WHAT IT CHECKS
------------------------------
It compares one document before and after a walk wrote to it. The format is
`references/decisions-section.md` at the plugin root: a summary table, one
"### <ID>: <Title> (<Status>)" subsection per item, and a maintainer block
after a "---" rule. A walk may change three surfaces and nothing else (AC-8).
SECTION_RE accepts the heading `## Open Questions / Decisions` plus exactly
the variants `references/walk-format.md` says this skill gathers from: an
optional numbered prefix ("## 7. ...") and "&" or "and" standing in for the
slash. No other heading, punctuation or word order is a decisions section.

  W1  everything outside the "## Open Questions / Decisions"        AC-8
      section is identical, and so is the section's own text
      outside its table and its items
  W2  each item's body, from its header to the rule before its       AC-8
      maintainer block, is identical; only the header's trailing
      status may change. No item is added, removed or renamed
  W3  in the summary table only Resolution, Status and Updated       AC-8
      may change; no row is added, removed or reordered
  W4  for every changed item, the table status, the header status    AC-8
      and the block's Status line agree
  W5  every changed block whose status is Decided or Provisional     AC-19
      carries a Follow-up line, except a pointer block, whose
      Choice begins "Recorded in" (the follow-up lives in the home)

Line endings are normalized before comparing, because a Windows checkout
rewrites them and that is not a change a walk made.

WHAT THIS DELIBERATELY DOES NOT CHECK
-------------------------------------
Whether an answer was parsed correctly, whether a Follow-up names the right
action, whether an item's home was chosen well, and whether the walk gathered
the right items. Those are judgments the skill makes and a live walk proves.
A green result here means the record is complete and the write-back stayed in
bounds, not that the walk was right.
"""

import io
import os
import re
import shutil
import sys
import tempfile

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class Broken(Exception):
    """Raised for every condition that must exit 2 rather than 1."""


def read(path):
    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            return fh.read().replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise Broken("%s is not valid UTF-8: %s" % (path, exc))
    except OSError as exc:
        raise Broken("cannot read %s: %s" % (path, exc))


def split_row(line):
    """Split a markdown table row into stripped cells, honouring escaped pipes."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", inner)]


def is_separator(cells):
    return bool(cells) and all(re.match(r"^:?-{3,}:?$", c) for c in cells)


def tables_in(lines):
    """Yield (start_index, [rows of cells]) for each contiguous block of table lines."""
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            start = i
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            yield start, rows
        else:
            i += 1


# ---------------------------------------------------------------------------
# Record mode
# ---------------------------------------------------------------------------

COLUMNS = ["Walk ID", "Home", "Answer", "State", "Round", "Follow-up", "Landed"]
STATES = {
    "D": {"decided", "provisional", "deferred", "canceled", "unanswered"},
    "Q": {"decided", "provisional", "assumed"},
    "T": {"done", "later", "drop", "open"},
}
WALK_ID_RE = re.compile(r"^([QDT])\d+$")
HOME_ID_RE = re.compile(r"(?:^|\s)[A-Z]{1,3}-?\d+[a-z]?$")
ROUND_RE = re.compile(r"^##\s+Round\s+(\d+)\s*$", re.M)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
QUOTE_CHARS = ('"', "“", "”")
EMPTY = ("", "-")


def frontmatter(text):
    """Return the flat key: value frontmatter as a dict, or None when there is none."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fm = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z][\w-]*):\s*(.*?)\s*$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip("\"'")
    return fm


def check_frontmatter(text, findings):
    """R1. Return the declared round count, or None when it is unusable."""
    fm = frontmatter(text)
    if fm is None:
        findings.append("the record has no frontmatter block (R1, AC-10)")
        return None
    if fm.get("type") != "walk-record":
        findings.append("frontmatter type is %r, not 'walk-record' (R1, AC-10)" % fm.get("type"))
    if not DATE_RE.match(fm.get("date", "")):
        findings.append("frontmatter date %r is not YYYY-MM-DD (R1, AC-10)" % fm.get("date"))
    if not fm.get("repo"):
        findings.append("frontmatter names no repo (R1, AC-10)")
    if not fm.get("handle"):
        findings.append("frontmatter names no handle (R1, WD-01 finding 2)")
    if not fm.get("handle-source"):
        findings.append("frontmatter names no handle-source (R1, WD-01 finding 2)")
    rounds = fm.get("rounds", "")
    if not rounds.isdigit() or int(rounds) < 1:
        findings.append("frontmatter rounds %r is not an integer of at least 1 (R1, AC-18)" % rounds)
        return None
    return int(rounds)


def find_items_table(text, findings):
    """R2. Return the data rows of the items table, or None when there is no usable one."""
    lines = text.splitlines()
    seen = []
    for _, rows in tables_in(lines):
        if rows and rows[0] == COLUMNS:
            data = [r for r in rows[1:] if not is_separator(r)]
            if not data:
                findings.append("the items table has no rows (R2, AC-10)")
                return None
            return data
        if rows:
            seen.append(rows[0])
    if seen:
        findings.append(
            "no items table with the seven columns %s; the nearest has %s (R2, AC-10)"
            % (" | ".join(COLUMNS), " | ".join(seen[0])))
    else:
        findings.append("the record has no items table (R2, AC-10)")
    return None


def check_rows(rows, rounds, findings):
    """R3 to R8's per-row halves."""
    seen = set()
    for cells in rows:
        if len(cells) != len(COLUMNS):
            findings.append("row %r has %d cells, not %d (R2, AC-10)" % (" | ".join(cells), len(cells), len(COLUMNS)))
            continue
        row = dict(zip(COLUMNS, cells))
        wid = row["Walk ID"]
        m = WALK_ID_RE.match(wid)
        if not m:
            findings.append("Walk ID %r is not Q, D or T followed by a number (R3, AC-2)" % wid)
            continue
        if wid in seen:
            findings.append("Walk ID %s appears more than once (R3, AC-2)" % wid)
        seen.add(wid)
        series = m.group(1)
        state = row["State"].lower()

        home = row["Home"]
        if not (home.lower().startswith("none") or HOME_ID_RE.search(home.rstrip(".,;"))):
            findings.append("%s: Home %r is neither 'none' nor a document followed by the item's own id (R4, AC-3)" % (wid, home))

        if state not in STATES[series]:
            findings.append("%s: State %r is not one of %s for a %s item (R5, AC-4/AC-6)"
                            % (wid, row["State"], ", ".join(sorted(STATES[series])), series))

        if state in ("decided", "provisional") and row["Follow-up"] in EMPTY:
            findings.append("%s is %s but names no Follow-up (R6, AC-19)" % (wid, state))

        landed = row["Landed"].lower()
        if series == "T" and landed != "walk record only":
            findings.append("%s is a T item but landed %r; a T answer stays in the walk record (R7, AC-20)" % (wid, row["Landed"]))
        if series == "D" and state == "unanswered" and not landed.startswith("not written"):
            findings.append("%s is unanswered but landed %r; a skipped decision is not written (R7, AC-6)" % (wid, row["Landed"]))
        if series == "Q" and state == "assumed" and not row["Answer"].lower().startswith("default:"):
            findings.append("%s is assumed but its Answer does not begin 'default:' (R7, AC-6)" % wid)

        rnd = row["Round"]
        if rnd not in EMPTY:
            if not rnd.isdigit():
                findings.append("%s: Round %r is neither a number nor '-' (R8, AC-18)" % (wid, rnd))
            elif rounds is not None and not 1 <= int(rnd) <= rounds:
                findings.append("%s: Round %s is outside the record's %d round(s) (R8, AC-18)" % (wid, rnd, rounds))
        if state == "provisional" and not any(q in row["Answer"] for q in QUOTE_CHARS):
            findings.append("%s is provisional but its Answer quotes no words of the maintainer's (R8, AC-18)" % wid)


def check_rounds(text, rounds, findings):
    """R8's document half."""
    found = [int(n) for n in ROUND_RE.findall(text)]
    if rounds is None:
        return
    if sorted(found) != list(range(1, rounds + 1)):
        findings.append("frontmatter declares %d round(s) but the record has '## Round' sections %s (R8, AC-18)"
                        % (rounds, found or "none"))


def run_record_checks(text):
    findings = []
    rounds = check_frontmatter(text, findings)
    rows = find_items_table(text, findings)
    if rows is not None:
        check_rows(rows, rounds, findings)
    check_rounds(text, rounds, findings)
    return findings


# ---------------------------------------------------------------------------
# Writeback mode
# ---------------------------------------------------------------------------

SECTION_RE = re.compile(r"^##\s+(?:\d+\.\s+)?Open Questions\s*(?:/|&|and)\s*Decisions\s*$")
LEVEL2_RE = re.compile(r"^##\s")
ITEM_RE = re.compile(r"^###\s+([A-Z]+\d+):\s+(.*?)\s*\(([^()]*)\)\s*$")
BLOCK_START_RE = re.compile(r"^>\s*\*\*Maintainer decision:\*\*")
STATUS_LINE_RE = re.compile(r"^>\s*\*\s*\*\*Status:\*\*\s*(.*?)\s*$", re.M)
CHOICE_LINE_RE = re.compile(r"^>\s*\*\s*\*\*Choice:\*\*\s*(.*?)\s*$", re.M)
FOLLOWUP_LINE_RE = re.compile(r"^>\s*\*\s*\*\*Follow-up:\*\*\s*\S", re.M)
TABLE_COLUMNS = ("ID", "Title", "Resolution", "Status", "Updated")
MUTABLE_COLUMNS = ("Resolution", "Status", "Updated")


def parse_document(text, label):
    """Split a document into the parts the write-back rules compare."""
    lines = text.splitlines()
    starts = [i for i, ln in enumerate(lines) if SECTION_RE.match(ln)]
    if not starts:
        raise Broken("%s has no '## Open Questions / Decisions' section; it is not in the decisions format" % label)
    s = starts[0]
    e = next((i for i in range(s + 1, len(lines)) if LEVEL2_RE.match(lines[i])), len(lines))
    outside = lines[:s] + ["<section>"] + lines[e:]
    section = lines[s + 1:e]

    tables = list(tables_in(section))
    if not tables:
        raise Broken("%s's decisions section has no summary table" % label)
    tstart, rows = tables[0]
    header = rows[0]
    missing = [c for c in TABLE_COLUMNS if c not in header]
    if missing:
        raise Broken("%s's summary table lacks the column(s) %s" % (label, ", ".join(missing)))
    col = {name: header.index(name) for name in header}
    data = [r for r in rows[1:] if not is_separator(r)]
    table = []
    for r in data:
        if len(r) != len(header):
            raise Broken("%s's summary table has a row with %d cells against a %d-column header: %r"
                         % (label, len(r), len(header), " | ".join(r)))
        table.append(r)

    item_idx = [i for i, ln in enumerate(section) if ITEM_RE.match(ln)]
    tend = tstart + len(rows)
    first_item = item_idx[0] if item_idx else len(section)
    preamble = section[:tstart] + ["<table>"] + section[tend:first_item]

    items = []
    for n, i in enumerate(item_idx):
        j = item_idx[n + 1] if n + 1 < len(item_idx) else len(section)
        m = ITEM_RE.match(section[i])
        body_lines = section[i + 1:j]
        block_at = next((k for k, ln in enumerate(body_lines) if BLOCK_START_RE.match(ln)), None)
        if block_at is None:
            body, block = body_lines, []
        else:
            rule = next((k for k in range(block_at - 1, -1, -1) if body_lines[k].strip() == "---"), block_at)
            body, block = body_lines[:rule], body_lines[rule:]
        items.append({
            "id": m.group(1), "title": m.group(2), "status": m.group(3).strip(),
            "body": body, "block": "\n".join(block),
        })
    return {"outside": outside, "preamble": preamble, "header": header, "col": col,
            "table": table, "items": items}


def block_status(block):
    m = STATUS_LINE_RE.search(block)
    return m.group(1).strip() if m else None


def run_writeback_checks(before_text, after_text):
    before = parse_document(before_text, "before")
    after = parse_document(after_text, "after")
    findings = []

    # W1
    if before["outside"] != after["outside"]:
        findings.append("text outside the decisions section changed (W1, AC-8)")
    if before["preamble"] != after["preamble"]:
        findings.append("the decisions section's own text, outside its table and items, changed (W1, AC-8)")

    # W3
    if before["header"] != after["header"]:
        findings.append("the summary table's header row changed (W3, AC-8)")
    b_ids = [r[before["col"]["ID"]] for r in before["table"]]
    a_ids = [r[after["col"]["ID"]] for r in after["table"]]
    rows_changed = set()
    if b_ids != a_ids:
        findings.append("summary-table rows were added, removed or reordered: %s became %s (W3, AC-8)" % (b_ids, a_ids))
    elif before["header"] != after["header"]:
        rows_changed.update(a_ids)  # Already a W3 finding; treat every row as changed so W4 and W5 still run.
    else:
        for br, ar in zip(before["table"], after["table"]):
            rid = br[before["col"]["ID"]]
            for name in before["header"]:
                b, a = br[before["col"][name]], ar[after["col"][name]]
                if b != a:
                    rows_changed.add(rid)
                    if name not in MUTABLE_COLUMNS:
                        findings.append("%s: the table's %s cell changed from %r to %r; only Resolution, Status "
                                        "and Updated may change (W3, AC-8)" % (rid, name, b, a))

    # W2
    b_items = [(it["id"], it["title"]) for it in before["items"]]
    a_items = [(it["id"], it["title"]) for it in after["items"]]
    if b_items != a_items:
        findings.append("item subsections were added, removed, renamed or reordered: %s became %s (W2, AC-8)"
                        % (b_items, a_items))
        return findings
    a_table = {r[after["col"]["ID"]]: r for r in after["table"]}
    for bi, ai in zip(before["items"], after["items"]):
        iid = ai["id"]
        if bi["body"] != ai["body"]:
            findings.append("%s: the item's body changed; only its header status and maintainer block may "
                            "change (W2, AC-8)" % iid)
        changed = (bi["status"] != ai["status"] or bi["block"] != ai["block"] or iid in rows_changed)
        if not changed:
            continue

        # W4
        surfaces = {"header": ai["status"], "block": block_status(ai["block"])}
        row = a_table.get(iid)
        if row is not None:
            surfaces["table"] = row[after["col"]["Status"]]
        values = {k: (v or "").strip().lower() for k, v in surfaces.items()}
        if len(set(values.values())) != 1:
            findings.append("%s: the three surfaces disagree on its status: %s (W4, AC-8)"
                            % (iid, ", ".join("%s %r" % (k, surfaces[k]) for k in sorted(surfaces))))

        # W5
        status = (surfaces["block"] or "").strip().lower()
        if status in ("decided", "provisional"):
            choice = CHOICE_LINE_RE.search(ai["block"])
            pointer = bool(choice) and choice.group(1).startswith("Recorded in")
            if not pointer and not FOLLOWUP_LINE_RE.search(ai["block"]):
                findings.append("%s is %s but its maintainer block has no Follow-up line (W5, AC-19)"
                                % (iid, surfaces["block"]))
    return findings


# ---------------------------------------------------------------------------
# Self-test. Every rule is proved against a canary that must fail, and each
# mode against anti-canaries that must pass. A checker with no proof that it
# can fail is not a check; this block is what makes exit 0 mean something.
# ---------------------------------------------------------------------------

GOOD_RECORD = """---
type: walk-record
date: 2026-11-02
repo: example/repo
rounds: 2
handle: jp
handle-source: docs/spec.md D2's maintainer block
---

# Walk record: sample

## Items, answers, and where each landed

| Walk ID | Home | Answer | State | Round | Follow-up | Landed |
|---|---|---|---|---|---|---|
| D1 | docs/spec.md D2 | "A, but I'm not sure" | provisional | 1 | Build A in phase 2 of the plan | docs/spec.md (three surfaces) |
| D2 | docs/spec.md D3 | "B" | decided | 2 | None needed | docs/spec.md (three surfaces); docs/brief.md (pointer) |
| D3 | docs/spec.md D4 | (no answer) | unanswered | - | - | not written |
| D4 | none (merge PR #9) | "A" | decided | 1 | None needed | walk record only |
| Q1 | none | default: staging | assumed | - | - | not written |
| T1 | none | "later" | later | 1 | - | walk record only |

## Round 1

> D1 A, but I'm not sure. D2: expand this. D4 A. T1 later

## Round 2

> D2 B
"""

PENDING = """---

> **Maintainer decision:** _(pending)_
>
> * **Status:** {status}
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
"""

GOOD_BEFORE = """# A document

Intro text that a walk never touches.

## Open Questions / Decisions

These items are open.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Sync authority | (none) | Open | (none) |
| D2 | Record location | (none) | Open | (none) |
| Q1 | Deploy target | (none) | Needs info | (none) |

### D1: Sync authority (Open)

**Summary.** Which side wins a sync conflict.

**Options / approaches.**

* **Option A:** The local copy wins.
* **Option B:** The remote copy wins.

**Recommendation.** Option A.

""" + PENDING.format(status="Open") + """
### D2: Record location (Open)

**Summary.** Where the record is kept.

* **Option A:** Local.
* **Option B:** Tracked.

**Recommendation.** Option A.

""" + PENDING.format(status="Open") + """
### Q1: Deploy target (Needs info)

**Summary.** Where the first deploy goes.

**Default if skipped.** Staging.

""" + PENDING.format(status="Needs info") + """
## Sources

- S1, a source.
"""

D1_DECIDED = """---

> **Maintainer decision:** Decided 2026-11-02 by jp
>
> * **Status:** Decided
> * **Choice:** Option A
> * **Reasoning:** "A". The local copy is the one being edited.
> * **Follow-up:** Build option A in phase 2 of the sync plan.
> * **Decided by / date:** jp / 2026-11-02
"""

D2_POINTER = """---

> **Maintainer decision:** Decided 2026-11-02 by jp
>
> * **Status:** Decided
> * **Choice:** Recorded in docs/spec.md D3
> * **Reasoning:** Answered in the home document.
> * **Decided by / date:** jp / 2026-11-02
"""


def _decide_d1(text, block=D1_DECIDED, header="Decided", table_status="Decided"):
    text = text.replace("| D1 | Sync authority | (none) | Open | (none) |",
                        "| D1 | Sync authority | Option A | %s | 2026-11-02 |" % table_status)
    text = text.replace("### D1: Sync authority (Open)", "### D1: Sync authority (%s)" % header)
    head, tail = text.split("### D2:", 1)
    head = head.replace(PENDING.format(status="Open"), block)
    return head + "### D2:" + tail


GOOD_AFTER = _decide_d1(GOOD_BEFORE)


def self_test():
    """Return a list of self-test failures. Empty means the checker is proved."""
    bad = []

    def expect_record(label, text, should_fail, needle=None):
        got = run_record_checks(text)
        _judge(label, got, should_fail, needle)

    def expect_writeback(label, before, after, should_fail, needle=None):
        try:
            got = run_writeback_checks(before, after)
        except Broken as exc:
            bad.append("  %s: unexpected Broken: %s" % (label, exc))
            return
        _judge(label, got, should_fail, needle)

    def _judge(label, got, should_fail, needle):
        if should_fail and not got:
            bad.append("  %s: expected a finding, got none" % label)
        elif not should_fail and got:
            bad.append("  %s: expected clean, got %r" % (label, got))
        elif should_fail and needle and not any(needle in g for g in got):
            bad.append("  %s: findings %r contain no %r" % (label, got, needle))

    # Anti-canaries: well-formed inputs must pass, or every canary is meaningless.
    expect_record("anti-canary, well-formed record", GOOD_RECORD, False)
    # A Windows checkout rewrites line endings; read() must normalize them, so a
    # CRLF copy of a good record, read from disk, still passes.
    crlf_dir = tempfile.mkdtemp()
    try:
        crlf_path = os.path.join(crlf_dir, "record.md")
        with io.open(crlf_path, "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write(GOOD_RECORD)
        expect_record("anti-canary, CRLF record read from disk", read(crlf_path), False)
    finally:
        shutil.rmtree(crlf_dir, ignore_errors=True)
    expect_writeback("anti-canary, untouched document", GOOD_BEFORE, GOOD_BEFORE, False)
    expect_writeback("anti-canary, one decision written back", GOOD_BEFORE, GOOD_AFTER, False)
    pointer_after = GOOD_AFTER.replace("| D2 | Record location | (none) | Open | (none) |",
                                       "| D2 | Record location | See docs/spec.md D3 | Decided | 2026-11-02 |")
    pointer_after = pointer_after.replace("### D2: Record location (Open)", "### D2: Record location (Decided)")
    # After D1 is decided, the only pending block still marked Open is D2's.
    pointer_after = pointer_after.replace(PENDING.format(status="Open"), D2_POINTER, 1)
    expect_writeback("anti-canary, a pointer block needs no Follow-up (W5 exemption)", GOOD_BEFORE, pointer_after, False)
    provisional_block = (D1_DECIDED
                         .replace("**Maintainer decision:** Decided", "**Maintainer decision:** Provisional")
                         .replace("* **Status:** Decided", "* **Status:** Provisional")
                         .replace('"A". The local copy', '"A, but I\'m not sure." The local copy'))
    provisional = _decide_d1(GOOD_BEFORE, provisional_block, "Provisional", "Provisional")
    expect_writeback("anti-canary, a provisional answer", GOOD_BEFORE, provisional, False)
    # WD-01 finding 1: the live trial's brief was headed "## 7. Open Questions & Decisions",
    # a heading the skill gathers from (references/walk-format.md) that the checker used to
    # reject with Broken. Both the numbered "&" form and the unnumbered "and" form must be
    # accepted, because walk-format.md names both as gathered variants.
    numbered_before = GOOD_BEFORE.replace("## Open Questions / Decisions", "## 7. Open Questions & Decisions")
    numbered_after = GOOD_AFTER.replace("## Open Questions / Decisions", "## 7. Open Questions & Decisions")
    expect_writeback("anti-canary, a numbered '&' heading (WD-01 finding 1)", numbered_before, numbered_after, False)
    and_before = GOOD_BEFORE.replace("## Open Questions / Decisions", "## Open Questions and Decisions")
    and_after = GOOD_AFTER.replace("## Open Questions / Decisions", "## Open Questions and Decisions")
    expect_writeback("anti-canary, an unnumbered 'and' heading", and_before, and_after, False)

    # R1 to R8
    expect_record("R1 wrong type", GOOD_RECORD.replace("type: walk-record", "type: session-log"), True, "R1")
    expect_record("R1 rounds missing", GOOD_RECORD.replace("rounds: 2\n", ""), True, "R1")
    expect_record("R1 handle missing", GOOD_RECORD.replace("handle: jp\n", ""), True, "R1")
    expect_record("R1 handle-source missing",
                  GOOD_RECORD.replace("handle-source: docs/spec.md D2's maintainer block\n", ""), True, "R1")
    expect_record("R2 a column missing", GOOD_RECORD.replace("| Walk ID | Home | Answer | State | Round | Follow-up | Landed |",
                                                             "| Walk ID | Home | Answer | Round | Landed |"), True, "R2")
    expect_record("R3 a bad Walk ID", GOOD_RECORD.replace("| Q1 | none |", "| X1 | none |"), True, "R3")
    expect_record("R3 a duplicate Walk ID", GOOD_RECORD.replace("| D3 | docs/spec.md D4 |", "| D1 | docs/spec.md D4 |"), True, "R3")
    expect_record("R4 a Home with no item id", GOOD_RECORD.replace("| D2 | docs/spec.md D3 |", "| D2 | docs/spec.md |"), True, "R4")
    expect_record("R5 a state outside the series", GOOD_RECORD.replace("| assumed |", "| unanswered |"), True, "R5")
    expect_record("R6 a decision with no Follow-up",
                  GOOD_RECORD.replace("| decided | 2 | None needed |", "| decided | 2 | - |"), True, "R6")
    expect_record("R7 a T item landed in a document",
                  GOOD_RECORD.replace("| later | 1 | - | walk record only |", "| later | 1 | - | docs/spec.md (three surfaces) |"),
                  True, "R7")
    expect_record("R7 an unanswered D was written",
                  GOOD_RECORD.replace("| unanswered | - | - | not written |", "| unanswered | - | - | docs/spec.md (three surfaces) |"),
                  True, "R7")
    expect_record("R7 an assumed Q with no default", GOOD_RECORD.replace("| default: staging |", "| staging |"), True, "R7")
    expect_record("R8 a round section missing", GOOD_RECORD.replace("## Round 2\n\n> D2 B\n", ""), True, "R8")
    expect_record("R8 a Round cell beyond the rounds", GOOD_RECORD.replace("| decided | 2 |", "| decided | 5 |"), True, "R8")
    expect_record("R8 a provisional answer with no quoted words",
                  GOOD_RECORD.replace("| \"A, but I'm not sure\" | provisional |", "| A | provisional |"), True, "R8")

    # W1 to W5
    expect_writeback("W1 text outside the section changed", GOOD_BEFORE,
                     GOOD_AFTER.replace("Intro text that a walk never touches.", "Intro text, edited."), True, "W1")
    expect_writeback("W1 the section's own text changed", GOOD_BEFORE,
                     GOOD_AFTER.replace("These items are open.", "These items were open."), True, "W1")
    expect_writeback("W2 an Options line changed", GOOD_BEFORE,
                     GOOD_AFTER.replace("The local copy wins.", "The local copy always wins."), True, "W2")
    expect_writeback("W2 an item removed", GOOD_BEFORE,
                     GOOD_AFTER.split("### Q1:")[0] + "## Sources\n\n- S1, a source.\n", True, "W2")
    expect_writeback("W3 a Title cell changed", GOOD_BEFORE,
                     GOOD_AFTER.replace("| D2 | Record location |", "| D2 | Where records live |"), True, "W3")
    expect_writeback("W3 a row removed", GOOD_BEFORE,
                     GOOD_AFTER.replace("| Q1 | Deploy target | (none) | Needs info | (none) |\n", ""), True, "W3")
    expect_writeback("W4 the header kept its old status", GOOD_BEFORE,
                     _decide_d1(GOOD_BEFORE, header="Open"), True, "W4")
    expect_writeback("W4 the table kept its old status", GOOD_BEFORE,
                     _decide_d1(GOOD_BEFORE, table_status="Open"), True, "W4")
    expect_writeback("W5 a decision with no Follow-up line", GOOD_BEFORE,
                     _decide_d1(GOOD_BEFORE, D1_DECIDED.replace(
                         "> * **Follow-up:** Build option A in phase 2 of the sync plan.\n", "")), True, "W5")

    # BROKEN, not FINDINGS.
    # A heading this skill does NOT gather from, per walk-format.md, must still be
    # rejected: a colon instead of a period after the number is outside the
    # documented variants, so the checker must not widen past what the skill reads.
    unsupported_heading = GOOD_BEFORE.replace("## Open Questions / Decisions", "## 7: Open Questions & Decisions")
    for label, text in (("no decisions section", "# A document\n\nNo section here.\n"),
                        ("no summary table", "# A\n\n## Open Questions / Decisions\n\nNone at this time.\n"),
                        ("a heading variant the skill does not gather from", unsupported_heading)):
        try:
            run_writeback_checks(text, text)
            bad.append("  %s: expected Broken, got a normal return" % label)
        except Broken:
            pass
    try:
        read(os.path.join(tempfile.gettempdir(), "walk-check-definitely-absent.md"))
        bad.append("  absent file: expected Broken, got a normal return")
    except Broken:
        pass

    # The shipped entry points must reach every rule, not only the check functions
    # in isolation: one fixture breaking R1 to R8 at once must report all eight.
    everything = (GOOD_RECORD.replace("type: walk-record", "type: x")
                  .replace("| Q1 | none | default: staging | assumed |", "| Q1 | none | staging | assumed |")
                  .replace("| D3 | docs/spec.md D4 |", "| D1 | docs/spec.md |")
                  .replace("| decided | 2 | None needed |", "| unknown | 2 | - |")
                  .replace("| later | 1 | - | walk record only |", "| later | 1 | - | docs/x.md (three surfaces) |")
                  .replace("| \"A, but I'm not sure\" | provisional | 1 | Build A in phase 2 of the plan |",
                           "| A | provisional | 1 | - |")
                  .replace("| \"A\" | decided | 1 | None needed | walk record only |",
                           "| \"A\" | decided | 9 | None needed | walk record only |"))
    got = " ".join(run_record_checks(everything))
    for rule in ("R1", "R3", "R4", "R5", "R6", "R7", "R8"):
        if "(%s" % rule not in got:
            bad.append("  pipeline: a record breaking every rule did not report %s; got %r" % (rule, got))
    if "(R2" not in " ".join(run_record_checks(GOOD_RECORD.replace("| Walk ID |", "| Walk |"))):
        bad.append("  pipeline: a record with a broken header did not report R2")
    return bad


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

USAGE = "usage: walk-check.py record <walk-record.md> | walk-check.py writeback <before.md> <after.md>\n"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help") or argv[0] not in ("record", "writeback") \
            or (argv[0] == "record" and len(argv) != 2) or (argv[0] == "writeback" and len(argv) != 3):
        sys.stderr.write(USAGE)
        sys.exit(2)

    failures = self_test()
    if failures:
        sys.stderr.write("BROKEN: self-test failed; this checker cannot be trusted:\n")
        sys.stderr.write("\n".join(failures) + "\n")
        sys.exit(2)
    sys.stdout.write(
        "gate self-test: PASS (8 record rules and 5 write-back rules proved against 25 canaries, "
        "8 anti-canaries including a CRLF record, a pointer block, a provisional answer and two "
        "accepted heading variants, 4 BROKEN cases, and two pipeline fixtures that must reach "
        "every record rule)\n")

    mode = argv[0]
    try:
        if mode == "record":
            target = argv[1]
            findings = run_record_checks(read(target))
        else:
            target = "%s -> %s" % (argv[1], argv[2])
            findings = run_writeback_checks(read(argv[1]), read(argv[2]))
    except Broken as exc:
        sys.stderr.write("BROKEN: %s\n" % exc)
        sys.exit(2)

    if findings:
        sys.stdout.write("FINDINGS: %d rule(s) violated in %s\n" % (len(findings), target))
        for f in findings:
            sys.stdout.write("  - %s\n" % f)
        sys.exit(1)
    sys.stdout.write("CLEAN: canary proved, %s satisfies every %s rule.\n" % (target, mode))
    sys.exit(0)


if __name__ == "__main__":
    main()
