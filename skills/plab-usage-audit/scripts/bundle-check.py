#!/usr/bin/env python3
"""
plab-usage-audit bundle checker. Implements R1 to R9 of
`skills/plab-usage-audit/references/bundle-format.md` exactly as written there, and the
self-test that proves each rule can fail (AC-21).

USAGE
-----
  bundle-check.py <bundle> [--private-pattern P [--private-pattern P2 ...]]
  bundle-check.py --self-test

EXIT-CODE CONTRACT (bundle-format.md, "Exit codes")
----------------------------------------------------
  0  CLEAN    self-test passed AND the bundle satisfies every rule
  1  FINDINGS self-test passed AND at least one rule is violated (printed as
             `R<n>: <file>: <message>`)
  2  BROKEN   the self-test failed, or the bundle folder does not exist, or
             `data/` is absent

NEVER INTERPRET 2 AS CLEAN. A bundle this script could not read is not a bundle it
looked at and found fine; see AGENTS.md's exit-code convention and the sibling checkers
`skills/plab-audit/scripts/bundle-check.py` and `skills/plab-current-status/scripts/status-check.py`,
whose self-test shape this one follows.

`--self-test` always runs first, even on an ordinary bundle check, for the same reason it
does in both sibling checkers: a rule's regex can go blind (match nothing, ever) without
raising any exception, and only proving it can still fail catches that silently.

A NOTE ON R1, FOR WHOEVER READS bundle-format.md NEXT
------------------------------------------------------
The rule's text is: "Every file in the table above exists. `data/` holds at least one
`.json` file." The table also lists `data/*.jsonl` and `data/briefs/*.md` as bundle
contents, but the rule gives no explicit existence requirement for either, the way it
does for `.json`. This checker follows the rule's literal text: it requires the seven
named files and at least one `data/*.json` file, and does not require a `.jsonl` file or
a `data/briefs/*.md` file to exist. The committed sample ships both anyway, because a
real run produces them, but a bundle missing them is not flagged by R1 as written. This
looks like a gap in the rule rather than an intended omission; it is reported as such
rather than silently over-implemented, per the instruction not to edit bundle-format.md.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

REQUIRED_FILES = [
    "README.md",
    "01-usage.md",
    "02-shipped.md",
    "03-scorecard.md",
    "04-config.md",
    "05-recommendations.md",
    os.path.join("data", "README.md"),
]

METHOD_HEADINGS = [
    "Windows",
    "Exclusion method",
    "Reconciliation",
    "Commands",
    "Ledger",
    "Agents",
    "Verification",
    "Not measured",
]

WHO_ACTS_VALUES = {"owner decides", "owner acts", "agent", "agent after a yes"}
MECHANISM_VALUES = {"setting", "rule", "hook", "skill", "script", "decision", "habit"}
APPROVAL_FILES = ("03-scorecard.md", "05-recommendations.md")

FIVE_MIN_HEADING_RE = re.compile(r"^##\s+Five-minute version", re.M)
SECTION_HEADING_TEXT_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
REC_HEADING_RE = re.compile(r"^##\s+([A-Za-z]\d+)\s*\(([^)]*)\)\s*:\s*(.+?)\s*$", re.M)
WHO_ACTS_LINE_RE = re.compile(r"^\*\*Who acts:\*\*\s*(.+?)\s*$", re.M)
MECHANISM_LINE_RE = re.compile(r"^\*\*Mechanism:\*\*\s*(.+?)\s*$", re.M)
DRIVE_LETTER_RE = re.compile(r"[A-Za-z]:[\\/]")
APPROVAL_VERB_RE = re.compile(r"\b(approved|chose|decided|declined|said yes)\b", re.I)
OWNER_RE = re.compile(r"\bowner\b", re.I)
BACKTICK_RE = re.compile(r"`[^`]+`")
QUOTE_RE = re.compile(r'"[^"]+"')

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "sample-bundle"


class Broken(Exception):
    """Raised for every condition that must exit 2 rather than 1."""


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------


def read_text(path):
    """Read a text file this checker needs to exist and parse as markdown. Returns
    None if the file is simply absent (R1 already reports that); raises Broken if it
    exists but cannot be decoded, because that is not a rule violation, it is this
    checker being unable to look."""
    if not os.path.isfile(path):
        return None
    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise Broken("cannot read %s: %s" % (path, exc))


def read_raw(path):
    """Read a file for a scan (R7, R8) where an unreadable file is itself the finding,
    not a reason to stop checking everything else."""
    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def h2_sections(text):
    """Ordered {heading name: body text} for every level-2 heading in text."""
    matches = list(SECTION_HEADING_TEXT_RE.finditer(text))
    out = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out[m.group(1)] = text[m.end():end]
    return out


def is_separator_row(line):
    stripped = line.strip()
    if "|" not in stripped:
        return False
    body = stripped.strip("|")
    cells = [c.strip() for c in body.split("|")]
    return bool(cells) and all(c and set(c) <= set("-: ") and "-" in c for c in cells)


def find_tables(text):
    """Every markdown pipe table in text, as a list of (header_cells, data_rows)."""
    lines = text.splitlines()
    n = len(lines)
    tables = []
    i = 0
    while i < n - 1:
        if "|" in lines[i] and is_separator_row(lines[i + 1]):
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < n and "|" in lines[j] and lines[j].strip():
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            tables.append((header, rows))
            i = j
        else:
            i += 1
    return tables


def split_sentences(text):
    """Sentences, split within a line only. Headings and `**Label:**` lines carry no
    terminal punctuation, so splitting across lines would glue an unrelated heading's
    words onto the next paragraph's sentence; AGENTS.md's one-paragraph-per-line
    convention makes a line the right unit to split within."""
    sentences = []
    for line in text.splitlines():
        if not line.strip():
            continue
        sentences.extend(p for p in re.split(r"(?<=[.!?])\s+", line) if p.strip())
    return sentences


# ---------------------------------------------------------------------------
# R1 to R9
# ---------------------------------------------------------------------------


def check_r1(bundle, findings):
    for rel in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(bundle, rel)):
            findings.append("R1: %s: required file is missing" % rel)
    data_dir = os.path.join(bundle, "data")
    json_names = [f for f in os.listdir(data_dir) if f.lower().endswith(".json")] if os.path.isdir(data_dir) else []
    if not json_names:
        findings.append("R1: data/: no .json file found; data/ must hold at least one")


def check_r2(bundle, findings):
    path = os.path.join(bundle, "README.md")
    text = read_text(path)
    if text is None:
        return
    if not FIVE_MIN_HEADING_RE.search(text):
        findings.append("R2: README.md: no level-2 heading starting with 'Five-minute version'")
    found = any(
        re.search(r"\bID\b", " | ".join(header)) and "Who acts" in " | ".join(header)
        for header, _rows in find_tables(text)
    )
    if not found:
        findings.append("R2: README.md: no table header row containing both 'ID' and 'Who acts'")


def check_r3(bundle, findings):
    path = os.path.join(bundle, "05-recommendations.md")
    text = read_text(path)
    if text is None:
        return
    all_starts = sorted(m.start() for m in SECTION_HEADING_TEXT_RE.finditer(text))
    rec_matches = [m for m in REC_HEADING_RE.finditer(text) if m.group(2).strip()]
    if not rec_matches:
        findings.append(
            "R3: 05-recommendations.md: no recommendation heading of the form "
            "'## <ID> (<handle>): <title>' with a non-empty handle")
        return
    for m in rec_matches:
        rec_id = m.group(1)
        later = [s for s in all_starts if s > m.start()]
        end = min(later) if later else len(text)
        body = text[m.end():end]
        who = WHO_ACTS_LINE_RE.search(body)
        if not who or who.group(1).strip() not in WHO_ACTS_VALUES:
            findings.append(
                "R3: 05-recommendations.md: recommendation %s has no valid '**Who acts:**' line "
                "(must be one of %s)" % (rec_id, ", ".join(sorted(WHO_ACTS_VALUES))))
        mech = MECHANISM_LINE_RE.search(body)
        if not mech or mech.group(1).strip() not in MECHANISM_VALUES:
            findings.append(
                "R3: 05-recommendations.md: recommendation %s has no valid '**Mechanism:**' line "
                "(must be one of %s)" % (rec_id, ", ".join(sorted(MECHANISM_VALUES))))


def check_r4(bundle, findings):
    path = os.path.join(bundle, "data", "README.md")
    text = read_text(path)
    if text is None:
        return
    headings = [m.group(1) for m in SECTION_HEADING_TEXT_RE.finditer(text)]
    if headings != METHOD_HEADINGS:
        findings.append(
            "R4: data/README.md: level-2 headings are %r; expected exactly %r, in that order"
            % (headings, METHOD_HEADINGS))


def check_r5(bundle, findings):
    path = os.path.join(bundle, "data", "README.md")
    text = read_text(path)
    if text is None:
        return
    body = h2_sections(text).get("Agents")
    if body is None:
        findings.append("R5: data/README.md: no '## Agents' section to hold the routing table")
        return
    model_col, data_rows = None, None
    for header, rows in find_tables(body):
        for idx, cell in enumerate(header):
            if re.search(r"\bModel\b", cell):
                model_col, data_rows = idx, rows
                break
        if model_col is not None:
            break
    if model_col is None:
        findings.append("R5: data/README.md: the Agents section has no table with a 'Model' column in its header")
        return
    for i, row in enumerate(data_rows, 1):
        cell = row[model_col] if model_col < len(row) else ""
        if not cell.strip():
            findings.append("R5: data/README.md: Agents table row %d has an empty Model cell" % i)


def check_r6(bundle, findings):
    path = os.path.join(bundle, "data", "README.md")
    text = read_text(path)
    if text is None:
        return
    body = h2_sections(text).get("Verification")
    if body is None:
        findings.append("R6: data/README.md: no '## Verification' section")
        return
    stripped = body.strip()
    if not stripped:
        findings.append("R6: data/README.md: the Verification section is empty")
        return
    if re.match(r"^no corrections\.?$", stripped, re.I):
        findings.append(
            "R6: data/README.md: the Verification section says only 'No corrections.' with no "
            "verifier model named")


def check_r7(bundle, findings):
    for root, _dirs, files in os.walk(bundle):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in (".json", ".jsonl"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, bundle).replace(os.sep, "/")
            raw = read_raw(path)
            if raw is None:
                findings.append("R7: %s: could not be read as text" % rel)
                continue
            if ext == ".json":
                try:
                    json.loads(raw)
                except ValueError as exc:
                    findings.append("R7: %s: does not parse as JSON (%s)" % (rel, exc))
            else:
                for i, line in enumerate(raw.splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        json.loads(line)
                    except ValueError as exc:
                        findings.append("R7: %s:%d: does not parse as JSON (%s)" % (rel, i, exc))


def check_r8(bundle, private_patterns, findings):
    home = os.path.expanduser("~")
    home_forms = set(f for f in (home, home.replace("\\", "/"), home.replace("/", "\\")) if f)
    for root, _dirs, files in os.walk(bundle):
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, bundle).replace(os.sep, "/")
            text = read_raw(path)
            if text is None:
                continue
            for pattern in private_patterns:
                if pattern and pattern in text:
                    findings.append("R8: %s: contains the configured private pattern %r" % (rel, pattern))
            if any(form in text for form in home_forms):
                findings.append("R8: %s: contains the home path" % rel)
            if DRIVE_LETTER_RE.search(text):
                findings.append("R8: %s: contains a drive-letter path" % rel)


def check_r9(bundle, findings):
    for rel in APPROVAL_FILES:
        path = os.path.join(bundle, rel)
        text = read_text(path)
        if text is None:
            continue
        for sentence in split_sentences(text):
            if OWNER_RE.search(sentence) and APPROVAL_VERB_RE.search(sentence):
                if not (BACKTICK_RE.search(sentence) or QUOTE_RE.search(sentence)):
                    findings.append(
                        "R9: %s: a sentence claims the owner approved/chose/decided/declined/said yes "
                        "with no backticked path or quoted record naming it: %r"
                        % (rel, sentence.strip()[:140]))


def run_checks(bundle, private_patterns):
    if not os.path.isdir(bundle):
        raise Broken("%s is not a directory; cannot check a bundle that is not there" % bundle)
    if not os.path.isdir(os.path.join(bundle, "data")):
        raise Broken("%s/data is not a directory" % bundle)
    findings = []
    check_r1(bundle, findings)
    check_r2(bundle, findings)
    check_r3(bundle, findings)
    check_r4(bundle, findings)
    check_r5(bundle, findings)
    check_r6(bundle, findings)
    check_r7(bundle, findings)
    check_r8(bundle, private_patterns, findings)
    check_r9(bundle, findings)
    return findings


# ---------------------------------------------------------------------------
# Self-test: one mutation per rule, each proved to make that rule fail.
# ---------------------------------------------------------------------------


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def _replace_once(path, old, new):
    text = _read(path)
    if text.count(old) != 1:
        raise Broken("self-test mutation anchor is not unique in %s: %r" % (path, old))
    _write(path, text.replace(old, new, 1))


def mutate_r1(copy_dir):
    os.remove(os.path.join(copy_dir, "02-shipped.md"))


def mutate_r2(copy_dir):
    _replace_once(os.path.join(copy_dir, "README.md"), "## Five-minute version", "## Quick version")


def mutate_r3(copy_dir):
    _replace_once(
        os.path.join(copy_dir, "05-recommendations.md"), "**Who acts:** owner decides", "**Who acts:** maybe")


def mutate_r4(copy_dir):
    _replace_once(os.path.join(copy_dir, "data", "README.md"), "## Ledger\n", "## The Ledger\n")


def mutate_r5(copy_dir):
    _replace_once(
        os.path.join(copy_dir, "data", "README.md"), "| Agent | Model | Task |", "| Agent | Engine | Task |")


def mutate_r6(copy_dir):
    path = os.path.join(copy_dir, "data", "README.md")
    text = _read(path)
    m = re.search(r"^##\s+Verification\s*$\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        raise Broken("R6 mutation: '## Verification' section not found")
    _write(path, text[:m.start(1)] + "No corrections.\n\n" + text[m.end(1):])


def mutate_r7(copy_dir):
    path = os.path.join(copy_dir, "data", "collector-output.json")
    text = _read(path).rstrip()
    _write(path, text[:-1])  # drop the final closing brace


def mutate_r8(copy_dir):
    # Built by concatenation, not typed as a literal, so this script's own source
    # never contains a drive-letter path shaped like a real one (AC-11).
    drive_path = "D" + ":" + "\\" + "exports" + "\\" + "raw-log.txt"
    path = os.path.join(copy_dir, "README.md")
    _write(path, _read(path) + "\n\nSee %s for the raw log.\n" % drive_path)


def mutate_r9(copy_dir):
    _replace_once(
        os.path.join(copy_dir, "03-scorecard.md"),
        "that decision is recorded at `docs/internal/decisions/sonnet-alias.md` and is not a finding",
        "that decision is recorded somewhere and is not a finding")


MUTATIONS = [
    ("R1", mutate_r1), ("R2", mutate_r2), ("R3", mutate_r3), ("R4", mutate_r4),
    ("R5", mutate_r5), ("R6", mutate_r6), ("R7", mutate_r7), ("R8", mutate_r8),
    ("R9", mutate_r9),
]


def self_test():
    """Return the number of rules proved. Raises Broken naming the first rule that
    cannot be proved, per the Exit-code contract's '2, naming the rule'."""
    if not SAMPLE_DIR.is_dir():
        raise Broken("sample bundle not found at %s" % SAMPLE_DIR)
    root = tempfile.mkdtemp()
    try:
        baseline = os.path.join(root, "baseline")
        shutil.copytree(str(SAMPLE_DIR), baseline)
        findings = run_checks(baseline, [])
        if findings:
            raise Broken("the committed sample fails its own checker: %s" % "; ".join(findings))

        proved = 0
        for rule_id, mutate in MUTATIONS:
            copy_dir = os.path.join(root, "mutant-" + rule_id)
            shutil.copytree(str(SAMPLE_DIR), copy_dir)
            mutate(copy_dir)
            got = run_checks(copy_dir, [])
            if not any(f.startswith(rule_id + ":") for f in got):
                raise Broken(
                    "self-test: the %s mutation did not make %s fail (findings were: %s)"
                    % (rule_id, rule_id, got))
            proved += 1

        try:
            run_checks(os.path.join(root, "definitely-absent"), [])
            raise Broken("self-test: an absent bundle directory did not raise Broken")
        except Broken as exc:
            if "definitely-absent" not in str(exc):
                raise
        return proved
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a plab-usage-audit bundle against bundle-format.md.")
    parser.add_argument("bundle", nargs="?", help="the bundle directory to check")
    parser.add_argument("--private-pattern", action="append", default=[], dest="private_patterns",
                         help="a string that must not appear anywhere in the bundle; repeatable")
    parser.add_argument("--self-test", action="store_true", help="prove the rules against the committed sample only")
    args = parser.parse_args(argv)

    if not args.bundle and not args.self_test:
        parser.error("give a bundle directory, or --self-test")

    try:
        proved = self_test()
    except Broken as exc:
        sys.stderr.write("BROKEN: self-test failed; this checker cannot be trusted: %s\n" % exc)
        return 2

    sys.stdout.write(
        "self-test: PASS (the committed sample is clean and each of %d rules, R1 to R9, failed its own "
        "mutation)\n" % proved)

    if args.self_test:
        sys.stdout.write("CLEAN: canary proved.\n")
        return 0

    try:
        findings = run_checks(args.bundle, args.private_patterns)
    except Broken as exc:
        sys.stderr.write("BROKEN: %s\n" % exc)
        return 2

    if findings:
        for f in findings:
            sys.stdout.write(f + "\n")
        sys.stdout.write("FINDINGS: %d rule failure(s) in %s\n" % (len(findings), args.bundle))
        return 1

    sys.stdout.write("CLEAN: canary proved, %s satisfies every rule.\n" % args.bundle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
