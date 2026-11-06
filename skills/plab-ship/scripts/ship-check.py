#!/usr/bin/env python3
"""Check a plab-ship run record against its format and the real changes, after proving every rule can fail.

USAGE
-----
  ship-check.py <record.md> [--repo <root>]
  ship-check.py --self-test

EXIT-CODE CONTRACT
------------------
  0  CLEAN     the self-test passed AND the record satisfies every rule
  1  FINDINGS  the self-test passed AND at least one rule failed; each is named
  2  BROKEN    the self-test failed, or the record could not be read

NEVER INTERPRET 2 AS CLEAN. Every run proves the rules first, against the
committed sample and one mutation per rule, so a rule that has gone blind stops
the run instead of passing everything.

THE RULES (SH-01, the ship skill)
---------------------------------
  R1  the file is `_local/_shipped/YYYY-MM-DD_<byline>.md`, the byline two to
      six kebab-case words
  R2  frontmatter carries type: ship-record, a date matching the filename, repo,
      release (`approved` or `not approved`), and version (`none`, or a version
      only when release is approved)
  R3  the level-2 sections are exactly SECTIONS, in order
  R4  every row under Merged names a branch, a commit and an undo point
  R5  every merged branch has a level-3 block under Documents holding all twelve
      layer and depth cells; `updated` and `correct` name a backticked path, and
      `n/a` gives a reason of at least three words
  R6  every Documents block has a `**Cold reader:**` line and a
      `**New surface:**` line
  R7  a version other than `none` appears in the Release section with a `Why:`
      clause; `not approved` says so there
  With --repo, for each merged row, reading the commits themselves:
  R8  every `updated` path changed between the undo point and the commit, and
      every changed document is listed as `updated`
  R9  every new-surface token, declared or detected in the diff, appears in a
      file the record names in its Human layer. This is the mechanical half of
      the documentation standard: it proves presence, not quality
  R10 a version other than `none` exists as a tag
  Always, because the rule reads only the record:
  R11 In Plain English carries `**End-user value:**` and `**Technical value:**`,
      each at least eight words, and neither holds a backtick, a reference id, a
      commit hash, a flag or a file name. This is a proxy: it rejects the common
      ways a summary stops being plain, and cannot prove a person understands it

WHAT THIS DOES NOT PROVE
------------------------
That a document is good. R8 and R9 prove a document changed and that it mentions
each new thing. The cold reader, which is an agent and not this script, is what
tests quality.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path

SECTIONS = ["In Plain English", "Merged", "Left Open", "Needs Your Decision", "Documents", "Release", "Cleanup", "Unverified"]
LAYERS = ["Human", "Technical", "Agentic"]
DEPTHS = ["Discover", "Use", "Understand", "Trust"]
STATES = {"updated", "correct", "n/a"}
RECORD_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_([a-z0-9]+(?:-[a-z0-9]+){1,5})\.md$")
VERSION_RE = re.compile(r"^v?\d+(?:\.\d+)+$")
REQUIRED_FIELDS = ("type", "date", "repo", "release", "version")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
TICK_RE = re.compile(r"`([^`]+)`")
DOC_SUFFIXES = (".md", ".mdx", ".rst", ".adoc", ".txt")
NOT_DOCS = ("evals/*", "tests/*", "test/*", "fixtures/*", "*/examples/*", "*/fixtures/*", "_local/*")
NOT_CODE = ("evals/*", "tests/*", "test/*", "fixtures/*", "*/examples/*", "*/fixtures/*", "*/test-*", "test-*", "*/test_*")
# Anchored to the start of the statement, so a flag quoted inside a string is not a definition.
FLAG_DEF_RE = re.compile(r"""^\s*[\w.]*add_argument\(\s*["'](--[\w-]+)["']""")
ARG_HINT_RE = re.compile(r"^argument-hint:\s*(.*)$")
FLAG_RE = re.compile(r"--[a-z][\w-]*")
NOT_PLAIN = [
    ("a backtick", re.compile(r"`")),
    ("a reference id", re.compile(r"(?<![\w-])(?:#\d+|[A-Z]{1,3}-\d+|AC-\d+)\b")),
    ("a commit hash", re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")),
    ("a flag", re.compile(r"(?<![\w-])--[a-z]")),
    ("a file name", re.compile(r"\b[\w./-]+\.(?:md|py|json|ya?ml|js|mjs|ts|toml|sh)\b")),
]
GIT_ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "sample-run"


class Broken(Exception):
    pass


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


def section_map(text):
    _, body = split_frontmatter(text)
    names, out, current = [], {}, None
    for line in body:
        m = H2_RE.match(line)
        if m and not line.startswith("###"):
            current = m.group(1)
            names.append(current)
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return names, out


def table_rows(lines):
    """Data rows of every pipe table in lines, as lists of stripped cells."""
    rows, seen_rule = [], False
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            seen_rule = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c or "x") for c in cells):
            seen_rule = True
        elif seen_rule:
            rows.append(cells)
    return rows


def merged_rows(text):
    _, secs = section_map(text)
    out = []
    for cells in table_rows(secs.get("Merged", [])):
        cells = cells + [""] * (4 - len(cells))
        out.append({"branch": cells[0].strip("`"), "pr": cells[1], "commit": cells[2].strip("`"),
                    "undo": cells[3].strip("`")})
    return out


def doc_blocks(text):
    _, secs = section_map(text)
    blocks, current = {}, None
    for line in secs.get("Documents", []):
        m = H3_RE.match(line)
        if m:
            current = m.group(1).strip("`")
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return blocks


def cells_of(block):
    """{(layer, depth): (state, detail)} for one Documents block."""
    out = {}
    for cells in table_rows(block):
        if len(cells) >= 4:
            out[(cells[0], cells[1])] = (cells[2].lower(), cells[3])
    return out


def marked_line(block, label):
    for line in block:
        if line.strip().startswith("**%s:**" % label):
            return line.strip()[len(label) + 5:].strip()
    return None


# ---------------------------------------------------------------------------
# Rules. Each takes (logical_path, text, repo) and returns a list of findings.
# ---------------------------------------------------------------------------


def r1_path(path, text, repo):
    p = Path(path)
    out = []
    if [x.lower() for x in p.parent.parts[-2:]] != ["_local", "_shipped"]:
        out.append("R1: the file is not in a `_local/_shipped/` folder: %s" % path)
    if not RECORD_RE.match(p.name):
        out.append("R1: the filename is not YYYY-MM-DD_<byline>.md with a two-to-six-word byline: %s" % p.name)
    return out


def r2_frontmatter(path, text, repo):
    fm, _ = split_frontmatter(text)
    if fm is None:
        return ["R2: no frontmatter"]
    out = ["R2: frontmatter has no `%s`" % f for f in REQUIRED_FIELDS if not fm.get(f)]
    if fm.get("type") and fm["type"] != "ship-record":
        out.append("R2: type is `%s`, not `ship-record`" % fm["type"])
    m = RECORD_RE.match(Path(path).name)
    if m and fm.get("date") and fm["date"] != m.group(1):
        out.append("R2: date %s does not match the filename's %s" % (fm["date"], m.group(1)))
    release, version = fm.get("release"), fm.get("version")
    if release and release not in ("approved", "not approved"):
        out.append("R2: release is `%s`, not `approved` or `not approved`" % release)
    if version and version != "none":
        if not VERSION_RE.match(version):
            out.append("R2: version `%s` is neither `none` nor a version" % version)
        if release == "not approved":
            out.append("R2: version is `%s` but release is `not approved`" % version)
    return out


def r3_sections(path, text, repo):
    names, _ = section_map(text)
    if names != SECTIONS:
        return ["R3: sections are %s; expected exactly %s, in that order" % (names, SECTIONS)]
    return []


def r4_merged(path, text, repo):
    out = []
    for i, row in enumerate(merged_rows(text), 1):
        if not row["branch"]:
            out.append("R4: Merged row %d names no branch" % i)
        if not re.fullmatch(r"[0-9a-f]{7,40}", row["commit"]):
            out.append("R4: Merged row %d has no commit hash: `%s`" % (i, row["commit"]))
        if not row["undo"]:
            out.append("R4: Merged row %d has no undo point" % i)
    return out


def r5_cells(path, text, repo):
    out = []
    blocks = doc_blocks(text)
    for row in merged_rows(text):
        name = row["branch"]
        if name not in blocks:
            out.append("R5: merged branch `%s` has no block under Documents" % name)
            continue
        cells = cells_of(blocks[name])
        for layer in LAYERS:
            for depth in DEPTHS:
                cell = cells.get((layer, depth))
                if cell is None:
                    out.append("R5: `%s` has no %s / %s cell" % (name, layer, depth))
                    continue
                state, detail = cell
                if state not in STATES:
                    out.append("R5: `%s` %s / %s has state `%s`, not updated, correct or n/a" % (name, layer, depth, state))
                elif state == "n/a":
                    if len(detail.split()) < 3:
                        out.append("R5: `%s` %s / %s is n/a with no reason of at least three words" % (name, layer, depth))
                elif not TICK_RE.search(detail):
                    out.append("R5: `%s` %s / %s is %s but names no backticked path" % (name, layer, depth, state))
    return out


def r6_lines(path, text, repo):
    out = []
    for name, block in doc_blocks(text).items():
        for label in ("Cold reader", "New surface"):
            if not marked_line(block, label):
                out.append("R6: `%s` has no `**%s:**` line" % (name, label))
    return out


def r7_release(path, text, repo):
    fm, _ = split_frontmatter(text)
    fm = fm or {}
    _, secs = section_map(text)
    body = "\n".join(secs.get("Release", []))
    version = fm.get("version")
    if version and version != "none":
        out = []
        if version not in body:
            out.append("R7: version `%s` does not appear in the Release section" % version)
        if "Why:" not in body:
            out.append("R7: the Release section has no `Why:` clause for `%s`" % version)
        return out
    if fm.get("release") == "not approved" and "not approved" not in body.lower():
        return ["R7: release is `not approved` but the Release section does not say so"]
    return []


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, env=GIT_ENV)
    return r.returncode, r.stdout


def is_doc(path):
    return path.lower().endswith(DOC_SUFFIXES) and not any(fnmatch(path, g) for g in NOT_DOCS)


def is_code(path):
    return not path.lower().endswith(DOC_SUFFIXES) and not any(fnmatch(path, g) for g in NOT_CODE)


def changed_files(repo, row):
    rc, out = git(repo, "diff", "--name-only", "--diff-filter=d", row["undo"], row["commit"])
    return (out.splitlines() if rc == 0 else None)


def r8_diff(path, text, repo):
    if repo is None:
        return []
    out = []
    blocks = doc_blocks(text)
    for row in merged_rows(text):
        changed = changed_files(repo, row)
        if changed is None:
            out.append("R8: `%s` cannot be diffed from undo point `%s` to commit `%s`" % (row["branch"], row["undo"], row["commit"]))
            continue
        listed = set()
        for (layer, depth), (state, detail) in cells_of(blocks.get(row["branch"], [])).items():
            for token in TICK_RE.findall(detail):
                if state == "updated":
                    listed.add(token)
                    if token not in changed:
                        out.append("R8: `%s` lists `%s` as updated, but it did not change in that merge" % (row["branch"], token))
                elif state == "correct" and git(repo, "cat-file", "-e", "%s:%s" % (row["commit"], token))[0] != 0:
                    out.append("R8: `%s` lists `%s` as already correct, but it does not exist at that commit" % (row["branch"], token))
        for doc in changed:
            if is_doc(doc) and doc not in listed:
                out.append("R8: `%s` changed the document `%s`, and the record does not list it as updated" % (row["branch"], doc))
    return out


def detected_surface(repo, row):
    """Flags defined and skills added by the diff, read from the added lines of code and of SKILL.md."""
    tokens = set()
    rc, added = git(repo, "diff", "--name-only", "--diff-filter=A", row["undo"], row["commit"])
    for path in added.splitlines() if rc == 0 else []:
        m = re.fullmatch(r"skills/([\w-]+)/SKILL\.md", path)
        if m:
            tokens.add(m.group(1))
    rc, diff = git(repo, "diff", "--unified=0", "--no-color", row["undo"], row["commit"])
    current = None
    for line in diff.splitlines() if rc == 0 else []:
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and current:
            if current.endswith("SKILL.md"):
                hint = ARG_HINT_RE.match(line[1:])
                if hint:
                    tokens.update(FLAG_RE.findall(hint.group(1)))
            elif is_code(current):
                tokens.update(FLAG_DEF_RE.findall(line[1:]))
    return tokens


def r9_surface(path, text, repo):
    if repo is None:
        return []
    out = []
    blocks = doc_blocks(text)
    for row in merged_rows(text):
        block = blocks.get(row["branch"], [])
        human = set()
        for (layer, depth), (state, detail) in cells_of(block).items():
            if layer == "Human" and state in ("updated", "correct"):
                human.update(TICK_RE.findall(detail))
        declared = set(TICK_RE.findall(marked_line(block, "New surface") or ""))
        for token in sorted(declared | detected_surface(repo, row)):
            found = False
            for doc in sorted(human):
                rc, content = git(repo, "show", "%s:%s" % (row["commit"], doc))
                if rc == 0 and token in content:
                    found = True
                    break
            if not found:
                out.append("R9: `%s` adds `%s`, and no Human-layer file in the record mentions it" % (row["branch"], token))
    return out


def r10_tag(path, text, repo):
    if repo is None:
        return []
    fm, _ = split_frontmatter(text)
    version = (fm or {}).get("version")
    if version and version != "none":
        if git(repo, "rev-parse", "--verify", "--quiet", "refs/tags/%s" % version)[0] != 0:
            return ["R10: version `%s` is recorded, but no such tag exists" % version]
    return []


def r11_plain(path, text, repo):
    _, secs = section_map(text)
    lines = secs.get("In Plain English", [])
    out = []
    for label in ("End-user value", "Technical value"):
        value = marked_line(lines, label)
        if value is None:
            out.append("R11: In Plain English has no `**%s:**` line" % label)
        elif len(value.split()) < 8:
            out.append("R11: `**%s:**` holds fewer than eight words" % label)
    body = "\n".join(lines)
    for name, pattern in NOT_PLAIN:
        if pattern.search(body):
            out.append("R11: In Plain English holds %s; say what the thing does instead" % name)
    return out


RULES = [r1_path, r2_frontmatter, r3_sections, r4_merged, r5_cells, r6_lines, r7_release, r8_diff, r9_surface, r10_tag, r11_plain]


def check(path, text, repo):
    findings = []
    for rule in RULES:
        findings.extend(rule(path, text, repo))
    return findings


# ---------------------------------------------------------------------------
# Self-test: the sample passes, and each mutation fails its own rule. R8 to R10
# read real commits, so the self-test builds a throwaway repository that holds
# exactly what the sample claims, then one merge with the human mention removed.
# ---------------------------------------------------------------------------


def _replace_once(text, old, new):
    if old not in text:
        raise Broken("self-test mutation anchor not found in the sample: %r" % old)
    return text.replace(old, new, 1)


def _fixture_git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=self-test", "-c", "user.email=self-test@example.invalid",
                        "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, env=GIT_ENV)
    if r.returncode != 0:
        raise Broken("self-test fixture: git %s failed: %s" % (args[0], r.stderr.strip()))
    return r.stdout.strip()


def _write(repo, files):
    for rel, content in files.items():
        p = Path(repo) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def _build_fixture(repo):
    _fixture_git(repo, "init", "-q")
    _write(repo, {"README.md": "# Example\n", "CHANGELOG.md": "# Changelog\n", "AGENTS.md": "# Agents\n",
                  "docs/index.md": "# Docs\n", "docs/internal/spec.md": "# Spec\n", "tool.py": "print('x')\n"})
    _fixture_git(repo, "add", "-A")
    _fixture_git(repo, "commit", "-q", "-m", "base")
    undo = _fixture_git(repo, "rev-parse", "HEAD")
    _write(repo, {"README.md": "# Example\n\nRun `tool.py --example-flag`.\n",
                  "CHANGELOG.md": "# Changelog\n\n- Added `--example-flag`.\n",
                  "AGENTS.md": "# Agents\n\nThe tool takes `--example-flag`.\n",
                  "docs/guide.md": "# Guide\n\nUse `--example-flag`.\n",
                  "docs/internal/spec.md": "# Spec\n\nThe flag.\n",
                  # The second line is an anti-canary: a flag quoted in a string defines nothing,
                  # and ship-check.py's own fixture is exactly that case.
                  "tool.py": "parser.add_argument('--example-flag')\nTEXT = \"parser.add_argument('--quoted-flag')\"\n",
                  "evals/case/prompt.md": "An eval prompt is not a document.\n"})
    _fixture_git(repo, "add", "-A")
    _fixture_git(repo, "commit", "-q", "-m", "feat: add the flag")
    good = _fixture_git(repo, "rev-parse", "HEAD")
    _fixture_git(repo, "tag", "v1.1.0")
    # The canary commit: the same change with the flag's human-facing mentions removed.
    _write(repo, {"README.md": "# Example\n\nA line.\n", "CHANGELOG.md": "# Changelog\n\n- A line.\n",
                  "docs/guide.md": "# Guide\n\nA line.\n"})
    _fixture_git(repo, "add", "-A")
    _fixture_git(repo, "commit", "-q", "-m", "docs: drop the mentions")
    return undo, good, _fixture_git(repo, "rev-parse", "HEAD")


def self_test():
    samples = sorted(p for p in SAMPLE_DIR.glob("*.md") if RECORD_RE.match(p.name)) if SAMPLE_DIR.is_dir() else []
    if len(samples) != 1:
        raise Broken("expected exactly one sample record in %s, found %d" % (SAMPLE_DIR, len(samples)))
    text = samples[0].read_text(encoding="utf-8")
    logical = "_local/_shipped/" + samples[0].name
    findings = check(logical, text, None)
    if findings:
        raise Broken("the committed sample fails its own checker: %s" % "; ".join(findings))

    mutations = [
        ("R1", "_local/_shipped/notes.md", text),
        ("R2", logical, _replace_once(text, "\nversion: v1.1.0", "\nversions: v1.1.0")),
        ("R3", logical, _replace_once(text, "## Left Open", "## Still Open")),
        ("R4", logical, _replace_once(text, "| 0123abc |", "| not-a-hash |")),
        ("R5", logical, _replace_once(text, "| Human | Use | updated |", "| Human | Use | skipped |")),
        ("R6", logical, _replace_once(text, "**Cold reader:**", "**Reader:**")),
        ("R7", logical, _replace_once(text, "**Why:**", "**Because:**").replace("Why:", "Because:")),
        ("R11", logical, _replace_once(text, "**Technical value:**", "**Technical:**")),
        ("R11", logical, _replace_once(text, "**End-user value:** ", "**End-user value:** See the `README.md` file. ")),
    ]
    for rule_id, path, mutated in mutations:
        if not [f for f in check(path, mutated, None) if f.startswith(rule_id + ":")]:
            raise Broken("self-test: rule %s did not fail its mutation, so it cannot be trusted" % rule_id)

    with tempfile.TemporaryDirectory() as tmp:
        undo, good, stripped = _build_fixture(tmp)
        real = text.replace("pre-merge/2026-11-05-feat-example-flag", undo).replace("| 0123abc |", "| %s |" % good)
        findings = check(logical, real, tmp)
        if findings:
            raise Broken("the sample does not match its fixture repository: %s" % "; ".join(findings))
        repo_mutations = [
            ("R8", _replace_once(real, "| Human | Use | updated | `docs/guide.md` |", "| Human | Use | updated | `docs/index.md` |")),
            ("R9", real.replace("| %s |" % good, "| %s |" % stripped)),
            ("R10", _replace_once(_replace_once(real, "\nversion: v1.1.0", "\nversion: v9.9.9"),
                                  "Released v1.1.0", "Released v9.9.9")),
        ]
        for rule_id, mutated in repo_mutations:
            if not [f for f in check(logical, mutated, tmp) if f.startswith(rule_id + ":")]:
                raise Broken("self-test: rule %s did not fail its mutation, so it cannot be trusted" % rule_id)
    return len({m[0] for m in mutations} | {m[0] for m in repo_mutations})


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Check a plab-ship run record.")
    parser.add_argument("record", nargs="?", help="the run record to check")
    parser.add_argument("--repo", help="the repository, so the record can be compared with the real commits (R8 to R10)")
    parser.add_argument("--self-test", action="store_true", help="prove the rules against the committed sample only")
    args = parser.parse_args(argv)
    if not args.record and not args.self_test:
        parser.error("give a record file, or --self-test")

    try:
        proved = self_test()
    except (Broken, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print("BROKEN: %s" % exc)
        return 2
    print("self-test: PASS (the sample is clean and each of %d rules failed its own mutation)" % proved)
    if args.self_test:
        print("CLEAN: canary proved.")
        return 0

    try:
        text = Path(args.record).read_text(encoding="utf-8-sig")
    except OSError as exc:
        print("BROKEN: %s" % exc)
        return 2
    logical = Path(args.record).resolve().as_posix()
    findings = check(logical, text, args.repo)
    if findings:
        for f in findings:
            print(f)
        print("FINDINGS: %d rule failure(s) in %s" % (len(findings), args.record))
        return 1
    print("CLEAN: canary proved, %s satisfies every rule%s." % (
        args.record, "" if args.repo else " (R8 to R10 skipped: no --repo given)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
