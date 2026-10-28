#!/usr/bin/env python3
"""Check a plab-current-status snapshot against its format, after proving every rule can fail.

USAGE
-----
  status-check.py <snapshot.md> [--facts <facts.json>]
  status-check.py --self-test

EXIT-CODE CONTRACT
------------------
  0  CLEAN     the self-test passed AND the snapshot satisfies every rule
  1  FINDINGS  the self-test passed AND at least one rule failed; each is named
  2  BROKEN    the self-test failed, or the snapshot or facts could not be read

NEVER INTERPRET 2 AS CLEAN. Every run proves the rules first, against the
committed sample and one mutation per rule, so a rule that has gone blind
stops the run instead of passing everything. This is the contract of
`skills/plab-audit/scripts/bundle-check.py` and the repository's other gates.

THE RULES (CS-01, current status skill, Requirements 6 and 8 to 13)
--------------------------------------------------------------------
  R1  the file is `_local/_status/YYYY-MM-DD_<model>_<byline>.md`, the byline
      two to six kebab-case words
  R2  frontmatter carries type: status-snapshot, date and model matching the
      filename, repo, branch, head, a known level, previous (a snapshot
      filename or `none`), and integer waiting, pending-decisions and next
  R3  an "As of" paragraph precedes the first section, and the level-2
      sections are exactly SECTIONS, in order
  R4  every numbered item in the ranked sections carries `Why here:`
  R5  each ranked section holds min(its frontmatter count, CAP) numbered items
  R6  every list item under Pending Decisions and Recent Decisions carries a
      backticked path to its home document
  R7  Changed Since Last Status names the previous snapshot, or says there is
      no previous snapshot when `previous` is `none`
  R8  with --facts, What I Don't Know mentions every gap the facts list

THE SAMPLE
----------
`examples/sample-status/` holds a sample snapshot and its facts. It cannot
live under a `_local/` folder, because `.gitignore` ignores `_local/` at every
depth, so the self-test checks it under the logical path
`_local/_status/<its filename>`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SECTIONS = [
    "The Answer",
    "Changed Since Last Status",
    "Waiting on You",
    "What's Next",
    "Pending Decisions",
    "Recent Decisions",
    "Accomplished",
    "Where the Project Is",
    "What I Don't Know",
]
RANKED = {"Waiting on You": "waiting", "What's Next": "next", "Pending Decisions": "pending-decisions"}
DECISION_SECTIONS = ("Pending Decisions", "Recent Decisions")
LEVELS = {"git-only", "logs", "decisions"}
CAP = 10
SNAPSHOT_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})_([a-z0-9]+(?:-[a-z0-9]+)*)_([a-z0-9]+(?:-[a-z0-9]+){1,5})\.md$"
)
REQUIRED_FIELDS = ("type", "date", "model", "repo", "branch", "head", "level", "previous",
                   "waiting", "pending-decisions", "next")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
NUMBERED_RE = re.compile(r"^\d+\.\s")
BULLET_RE = re.compile(r"^(?:\d+\.|[-*])\s")
PATH_RE = re.compile(r"`[^`\s]*[/.][^`\s]*`")

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "sample-status"


class Broken(Exception):
    pass


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def split_frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, lines
    for j in range(1, len(lines)):
        if lines[j].strip() == "---":
            fm = {}
            for line in lines[1:j]:
                m = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
                if m:
                    fm[m.group(1)] = m.group(2).strip().strip("\"'")
            return fm, lines[j + 1:]
    return None, lines


def sections(body):
    """Ordered (heading, lines) pairs for each level-2 section, plus the preamble."""
    out, preamble, current = [], [], None
    for line in body:
        m = H2_RE.match(line)
        if m and not line.startswith("###"):
            current = (m.group(1), [])
            out.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current[1].append(line)
    return preamble, out


def items(lines, pattern):
    """List items matching pattern, each joined with its indented continuation lines."""
    found, current = [], None
    for line in lines:
        if pattern.match(line):
            current = [line]
            found.append(current)
        elif current is not None and line.startswith((" ", "\t")) and line.strip():
            current.append(line)
        else:
            current = None
    return [" ".join(x) for x in found]


# ---------------------------------------------------------------------------
# Rules. Each takes (logical_path, text, facts) and returns a list of findings.
# ---------------------------------------------------------------------------


def r1_path(path, text, facts):
    p = Path(path)
    out = []
    if [x.lower() for x in p.parent.parts[-2:]] != ["_local", "_status"]:
        out.append("R1: the file is not in a `_local/_status/` folder: %s" % path)
    if not SNAPSHOT_RE.match(p.name):
        out.append("R1: the filename is not YYYY-MM-DD_<model>_<byline>.md with a two-to-six-word byline: %s" % p.name)
    return out


def r2_frontmatter(path, text, facts):
    fm, _ = split_frontmatter(text)
    if fm is None:
        return ["R2: no frontmatter"]
    out = ["R2: frontmatter has no `%s`" % f for f in REQUIRED_FIELDS if not fm.get(f)]
    if fm.get("type") and fm["type"] != "status-snapshot":
        out.append("R2: type is `%s`, not `status-snapshot`" % fm["type"])
    if fm.get("level") and fm["level"] not in LEVELS:
        out.append("R2: level `%s` is not one of %s" % (fm["level"], ", ".join(sorted(LEVELS))))
    for f in ("waiting", "pending-decisions", "next"):
        if fm.get(f) and not fm[f].isdigit():
            out.append("R2: `%s` is not a non-negative integer: %s" % (f, fm[f]))
    m = SNAPSHOT_RE.match(Path(path).name)
    if m:
        if fm.get("date") and fm["date"] != m.group(1):
            out.append("R2: date %s does not match the filename's %s" % (fm["date"], m.group(1)))
        if fm.get("model") and fm["model"] != m.group(2):
            out.append("R2: model %s does not match the filename's %s" % (fm["model"], m.group(2)))
    prev = fm.get("previous")
    if prev and prev != "none" and not SNAPSHOT_RE.match(prev):
        out.append("R2: previous `%s` is neither `none` nor a snapshot filename" % prev)
    return out


def r3_sections(path, text, facts):
    _, body = split_frontmatter(text)
    preamble, secs = sections(body)
    out = []
    if not any(line.lstrip().startswith("**As of") for line in preamble):
        out.append("R3: no `**As of` paragraph before the first section")
    names = [name for name, _ in secs]
    if names != SECTIONS:
        out.append("R3: sections are %s; expected exactly %s, in that order" % (names, SECTIONS))
    return out


def section_map(text):
    _, body = split_frontmatter(text)
    return {name: lines for name, lines in sections(body)[1]}


def r4_why_here(path, text, facts):
    out = []
    secs = section_map(text)
    for name in RANKED:
        for i, item in enumerate(items(secs.get(name, []), NUMBERED_RE), 1):
            if "Why here:" not in item:
                out.append("R4: item %d under %s has no `Why here:` clause" % (i, name))
    return out


def r5_counts(path, text, facts):
    fm, _ = split_frontmatter(text)
    fm = fm or {}
    secs = section_map(text)
    out = []
    for name, field in RANKED.items():
        value = fm.get(field, "")
        if not value.isdigit():
            continue  # R2 reports it
        shown = len(items(secs.get(name, []), NUMBERED_RE))
        expected = min(int(value), CAP)
        if shown != expected:
            out.append("R5: %s shows %d numbered item(s); `%s: %s` requires %d" % (name, shown, field, value, expected))
    return out


def r6_paths(path, text, facts):
    secs = section_map(text)
    out = []
    for name in DECISION_SECTIONS:
        for i, item in enumerate(items(secs.get(name, []), BULLET_RE), 1):
            if not PATH_RE.search(item):
                out.append("R6: item %d under %s names no home document as a backticked path" % (i, name))
    return out


def r7_previous(path, text, facts):
    fm, _ = split_frontmatter(text)
    prev = (fm or {}).get("previous", "")
    body = "\n".join(section_map(text).get("Changed Since Last Status", []))
    if prev and prev != "none":
        if prev not in body:
            return ["R7: Changed Since Last Status does not name the previous snapshot `%s`" % prev]
    elif "no previous" not in body.lower():
        return ["R7: `previous` is none, but Changed Since Last Status does not say there is no previous snapshot"]
    return []


def r8_gaps(path, text, facts):
    if facts is None:
        return []
    body = "\n".join(section_map(text).get("What I Don't Know", [])).lower()
    return ["R8: What I Don't Know does not mention the gap `%s`" % g["source"]
            for g in facts.get("gaps", []) if g["source"].lower() not in body]


RULES = [r1_path, r2_frontmatter, r3_sections, r4_why_here, r5_counts, r6_paths, r7_previous, r8_gaps]


def check(path, text, facts):
    findings = []
    for rule in RULES:
        findings.extend(rule(path, text, facts))
    return findings


# ---------------------------------------------------------------------------
# Self-test: the sample passes, and each mutation fails its own rule
# ---------------------------------------------------------------------------


def _replace_once(text, old, new):
    if text.count(old) < 1:
        raise Broken("self-test mutation anchor not found in the sample: %r" % old)
    return text.replace(old, new, 1)


def _strip_section_backticks(text, name):
    lines = text.splitlines()
    out, inside = [], False
    for line in lines:
        m = H2_RE.match(line)
        if m:
            inside = m.group(1) == name
        out.append(line.replace("`", "") if inside and BULLET_RE.match(line) else line)
    return "\n".join(out) + "\n"


def self_test():
    samples = sorted(p for p in SAMPLE_DIR.glob("*.md") if SNAPSHOT_RE.match(p.name)) if SAMPLE_DIR.is_dir() else []
    if len(samples) != 1:
        raise Broken("expected exactly one sample snapshot in %s, found %d" % (SAMPLE_DIR, len(samples)))
    sample = samples[0]
    text = sample.read_text(encoding="utf-8")
    facts = json.loads((SAMPLE_DIR / "facts.json").read_text(encoding="utf-8"))
    logical = "_local/_status/" + sample.name
    fm, _ = split_frontmatter(text)
    if not fm or fm.get("previous") in (None, "none"):
        raise Broken("the sample must name a previous snapshot, so R7's named branch is proved")

    findings = check(logical, text, facts)
    if findings:
        raise Broken("the committed sample fails its own checker: %s" % "; ".join(findings))

    waiting = fm["waiting"]
    mutations = [
        ("R1", "_local/_status/notes.md", text, facts),
        ("R2", logical, _replace_once(text, "\nlevel: ", "\nlevels: "), facts),
        ("R3", logical, _replace_once(_replace_once(text, "## Accomplished", "## @@SWAP@@"),
                                      "## Recent Decisions", "## Accomplished").replace("## @@SWAP@@", "## Recent Decisions"), facts),
        ("R4", logical, _replace_once(text, "Why here:", "Because:"), facts),
        ("R5", logical, _replace_once(text, "\nwaiting: %s" % waiting, "\nwaiting: %d" % (int(waiting) + 1)), facts),
        ("R6", logical, _strip_section_backticks(text, "Pending Decisions"), facts),
        ("R7", logical, text.replace(fm["previous"], "an-earlier-file.md").replace(
            "previous: an-earlier-file.md", "previous: %s" % fm["previous"]), facts),
        ("R8", logical, text, dict(facts, gaps=facts["gaps"] + [{"source": "a source never mentioned", "reason": "x"}])),
    ]
    for rule_id, path, mutated, mfacts in mutations:
        hits = [f for f in check(path, mutated, mfacts) if f.startswith(rule_id + ":")]
        if not hits:
            raise Broken("self-test: rule %s did not fail its mutation, so it cannot be trusted" % rule_id)
    return len(mutations)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Check a plab-current-status snapshot.")
    parser.add_argument("snapshot", nargs="?", help="the snapshot file to check")
    parser.add_argument("--facts", help="the derive-status-facts.py JSON the snapshot was written from")
    parser.add_argument("--self-test", action="store_true", help="prove the rules against the committed sample only")
    args = parser.parse_args(argv)
    if not args.snapshot and not args.self_test:
        parser.error("give a snapshot file, or --self-test")

    try:
        proved = self_test()
    except (Broken, OSError, ValueError, KeyError) as exc:
        print("BROKEN: %s" % exc)
        return 2
    print("self-test: PASS (the sample is clean and each of %d rules failed its own mutation)" % proved)
    if args.self_test:
        print("CLEAN: canary proved.")
        return 0

    try:
        text = Path(args.snapshot).read_text(encoding="utf-8-sig")
        facts = json.loads(Path(args.facts).read_text(encoding="utf-8")) if args.facts else None
    except (OSError, ValueError) as exc:
        print("BROKEN: %s" % exc)
        return 2
    logical = Path(args.snapshot).resolve().as_posix()
    findings = check(logical, text, facts)
    if findings:
        for f in findings:
            print(f)
        print("FINDINGS: %d rule failure(s) in %s" % (len(findings), args.snapshot))
        return 1
    print("CLEAN: canary proved, %s satisfies every rule%s." % (
        args.snapshot, "" if facts is not None else " (R8 skipped: no --facts given)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
