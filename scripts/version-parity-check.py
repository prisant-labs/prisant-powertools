#!/usr/bin/env python3
"""
Version-parity gate: every version a tracked document CLAIMS must equal the version the repository DECLARES.

EXIT-CODE CONTRACT
------------------
  0  CLEAN    self-test passed AND every claimed version matched its authoritative source
  1  FINDINGS self-test passed AND at least one document claims a version that disagrees with the source
  2  BROKEN   the detector could not prove itself, a file could not be parsed, a location this script is supposed to read yielded no claims at all, or any other exception reached the top level

NEVER INTERPRET 2 AS CLEAN. `scripts/doc-lifecycle-check.py` and `scripts/check-dashes.py` carry the same contract; this script applies it to the one thing neither of them can see, which is whether the prose agrees with `library.json` and with each `skills/*/SKILL.md`.

WHY THIS SCRIPT EXISTS
----------------------
v0.5.3 shipped with six stale version references in `README.md` and `docs/status-skills.md`. They were found by hand during the release and fixed there, but nothing mechanical had flagged them and nothing mechanical would have.

The gap was wider than the session log that recorded it suggested. The "bidirectional drift check" that was believed to cover this (`skills/plab-wrap-session/references/hygiene-sweep.md`, Check 4, delivered by D-03) is a bash recipe inside a skill reference document, run by an agent during a session wrap. Two consequences follow, and both matter more than the missing file coverage:

  1. **CI had never run it, until `scripts/skill-drift-check.py` mechanized it.** Before that script existed, Check 4 was not a committed script and no workflow invoked it, so a version reference could stay stale on `main` indefinitely, through any number of green pull requests, until someone happened to wrap a session. `scripts/skill-drift-check.py` now closes that gap by running Check 4's own recipe in CI.
  2. **It checks a different thing.** Check 4 compares each skill's own `metadata.version` at HEAD against its value at the last tag, and looks for a `HISTORY.md` row. It never reads the version numbers written in the documentation at all. The usage-README comparison in that reference is under "Stale docs, caught by reading", which is a human instruction, not a check.

So this script does not extend Check 4; it covers what Check 4 was mistakenly believed to cover, mechanically and in CI. Check 4, and `scripts/skill-drift-check.py` which now mechanizes it, remain useful and unchanged by this script: they answer "should this version have been bumped", a question about git history that this script deliberately does not ask.

WHY THIS IS A STRUCTURAL CHECK AND NOT A VERSION-STRING SWEEP
------------------------------------------------------------
The obvious implementation, "find every `\\d+\\.\\d+\\.\\d+` in the tracked docs and compare it to something", is the implementation this repository already knows not to write. D-12's path-citation rule scored 13 flags with 11 false positives when a prose rule was mechanized literally (`docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-12_path-citation-precision/spec.md`), and the lesson kept from it is "mechanize the structure, never the prose". Version-shaped strings in these documents are overwhelmingly historical: HISTORY tables, "carried through 1.2.1", changelog entries. Every one of those is correct precisely because it does NOT match the current version.

This script therefore reads exactly six structured locations, each of which is a claim about what a version IS RIGHT NOW, and ignores every other version-shaped string in the repository:

  L1  `README.md`, the Skills table. A row whose first cell links a `plab-*` skill claims that skill's current version.
  L2  `docs/status-skills.md`, the At a glance table. Same row shape, same claim.
  L3  `docs/skills/<skill>/README.md`, the `**Version:**` line near the top. One per usage README.
  L4  `docs/status-skills.md`, the `**Plugin version:**` line. A claim about `library.json`'s version, not a skill's.
  L5  `docs/status-skills.md`, the per-skill section headings in Per-skill detail (a line reading
      "### " then a backtick-quoted skill name then a version, optionally followed by a comma and
      a note such as ", explicit only"). One per skill.
  L6  `library.json`'s `components.skills[].version`. One entry per skill, a claim carried by the same manifest the toolkit's manifest generators read.

Authoritative sources, never the other way round: a skill's version is whatever `skills/<name>/SKILL.md` says in `metadata.version`, and the library's version is whatever `library.json` says in its top-level `version`. This script never edits either, and never edits the documents; CI reports, it does not fix (`AGENTS.md`, Build and validate).

WHY AN UNPARSEABLE LOCATION IS BROKEN, NOT CLEAN
------------------------------------------------
Each of L1, L2, L3, L5 and L6 is matched by a shape. If someone reformats the Skills table, renames the `**Version:**` label, changes the section-heading format, or empties `components.skills`, the matcher stops finding claims and this gate goes quiet while the documents drift freely. A gate that reports CLEAN because it has gone blind is worse than no gate, and this repository has been bitten by that exact failure twice: the empty `git tag -l` in v0.5.2, and `AGENTS.md` never loading in the superpowers experiment.

So a location that yields ZERO claims when the repository has skills to claim is BROKEN, not clean. A location that yields SOME claims but is missing a particular skill is a FINDING, because that is real drift: a skill exists and the documentation does not list it.

WHAT THIS SCRIPT DELIBERATELY DOES NOT CHECK
--------------------------------------------
Whether a version SHOULD have been bumped (Check 4's question, and one that needs git history). Whether `HISTORY.md` has a row for the current version (also Check 4). Whether the generated manifests agree with `library.json`, which is the toolkit's `gen-manifest.mjs` and its own parity gate. Whether a version number is semantically the right increment. And any version-shaped string outside the four locations above, all of which are presumed historical and correct.
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile

SKILL_NAME = re.compile(r'`(plab-[a-z0-9-]+)`')
SEMVER = re.compile(r'^\d+\.\d+\.\d+$')
USAGE_VERSION_LINE = re.compile(r'^\*\*Version:\*\*\s*(\d+\.\d+\.\d+)\s*$', re.MULTILINE)
PLUGIN_VERSION_LINE = re.compile(r'\*\*Plugin version:\*\*\s*(\d+\.\d+\.\d+)')
# L5. The trailing ", explicit only" (or any other comma-introduced note) is optional, because
# docs/status-skills.md writes it on the two manual-only skills and nothing else.
SECTION_HEADING = re.compile(r'^### `(plab-[a-z0-9-]+)` (\d+\.\d+\.\d+)(?:,.*)?$', re.MULTILINE)

README_REL = "README.md"
STATUS_REL = "docs/status-skills.md"
LIBRARY_REL = "library.json"


class Broken(Exception):
    """Raised for anything that means this detector cannot prove what it claims to prove. Always becomes exit 2, never exit 1."""


def read_text(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise Broken("expected file is missing: %s" % path)
    except UnicodeDecodeError as exc:
        raise Broken("%s is not valid UTF-8: %s" % (path, exc))


def declared_skill_versions(repo_root):
    """The authoritative per-skill versions: `metadata.version` inside each skills/<name>/SKILL.md frontmatter block.

    Read from the `metadata:` block specifically rather than by grepping the first `version:` line anywhere in the file, which is what the Check 4 recipe does. A SKILL.md whose body happened to contain the word `version:` before its metadata block would give that recipe the wrong answer silently."""
    skills_dir = os.path.join(repo_root, "skills")
    if not os.path.isdir(skills_dir):
        raise Broken("no skills/ directory under %s; this script cannot establish any authoritative version" % repo_root)
    versions = {}
    for name in sorted(os.listdir(skills_dir)):
        skill_file = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(skill_file):
            continue
        text = read_text(skill_file)
        lines = text.split("\n")
        if not lines or lines[0].strip() != "---":
            raise Broken("%s does not open with a frontmatter fence" % skill_file)
        in_metadata = False
        found = None
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if re.match(r'^metadata:\s*$', line):
                in_metadata = True
                continue
            if in_metadata:
                if line and not line[0].isspace():
                    in_metadata = False
                    continue
                m = re.match(r'^\s+version:\s*"?(\d+\.\d+\.\d+)"?\s*$', line)
                if m:
                    found = m.group(1)
                    break
        if found is None:
            raise Broken("%s has no metadata.version line this script can read" % skill_file)
        versions[name] = found
    if not versions:
        raise Broken("skills/ contains no readable SKILL.md; nothing to check parity against")
    return versions


def _load_library_json(repo_root):
    path = os.path.join(repo_root, LIBRARY_REL)
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Broken("%s is not valid JSON: %s" % (path, exc))


def declared_library_version(repo_root):
    data = _load_library_json(repo_root)
    version = data.get("version")
    if not isinstance(version, str) or not SEMVER.match(version):
        raise Broken("%s has no usable top-level 'version' string, got %r"
                     % (os.path.join(repo_root, LIBRARY_REL), version))
    return version


def declared_library_components(repo_root):
    """L6's claim source within the same manifest: `components.skills[]`, read separately from the
    top-level `version` field `declared_library_version()` reads. Returns {} if the array is
    missing, empty, or carries no usable {name, version} entries; the caller (`check_library_components()`)
    is the one that decides whether an empty result means BROKEN."""
    data = _load_library_json(repo_root)
    comps = data.get("components")
    skills = comps.get("skills") if isinstance(comps, dict) else None
    out = {}
    if isinstance(skills, list):
        for entry in skills:
            if (isinstance(entry, dict) and isinstance(entry.get("name"), str)
                   and isinstance(entry.get("version"), str)):
                out[entry["name"]] = entry["version"]
    return out


def table_claims(text, rel_path):
    """Every table row whose FIRST cell names exactly one `plab-*` skill contributes that row's version cells as claims about that skill.

    Deliberately position-independent: README.md puts the version in the last cell and docs/status-skills.md puts it in the second, and hard-coding either would make this function silently wrong the first time a column moved. A row carrying two DIFFERENT version-shaped cells is ambiguous, so it is reported rather than resolved by guessing which column was meant."""
    claims = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        names = SKILL_NAME.findall(cells[0])
        if len(names) != 1:
            continue
        versions = {c for c in cells[1:] if SEMVER.match(c)}
        if not versions:
            continue
        if len(versions) > 1:
            raise Broken("%s line %d: row for %s carries more than one version-shaped cell (%s); "
                         "this script will not guess which one is the claim"
                         % (rel_path, lineno, names[0], ", ".join(sorted(versions))))
        claims.append((names[0], versions.pop(), lineno))
    return claims


def check_table_location(repo_root, rel_path, declared, label):
    """L1 and L2. Zero claims from a file that should carry one per skill is BROKEN (the matcher went blind); a claim that disagrees, or a skill with no claim at all, is a FINDING."""
    text = read_text(os.path.join(repo_root, rel_path))
    claims = table_claims(text, rel_path)
    if not claims:
        raise Broken("%s (%s) yielded no version claims at all, but %d skill(s) exist. The table shape "
                     "this script matches has probably changed, and a silent pass here would let every "
                     "version in that file drift unchecked."
                     % (rel_path, label, len(declared)))
    findings = []
    claimed_for = {}
    for name, version, lineno in claims:
        claimed_for.setdefault(name, []).append((version, lineno))
        if name not in declared:
            findings.append("%s line %d: %s lists skill %r, which has no skills/%s/SKILL.md"
                            % (rel_path, lineno, label, name, name))
        elif version != declared[name]:
            findings.append("%s line %d: %s claims %s is %s, but skills/%s/SKILL.md declares %s"
                            % (rel_path, lineno, label, name, version, name, declared[name]))
    for name in sorted(declared):
        if name not in claimed_for:
            findings.append("%s: %s has no row for skill %r, which exists at skills/%s/SKILL.md"
                            % (rel_path, label, name, name))
    return findings


def check_usage_readmes(repo_root, declared):
    """L3. Every skill must have a usage README carrying exactly one `**Version:**` line, and it must agree."""
    findings = []
    seen_any = False
    for name in sorted(declared):
        rel = "docs/skills/%s/README.md" % name
        path = os.path.join(repo_root, rel)
        if not os.path.isfile(path):
            findings.append("%s: no usage README for skill %r, which exists at skills/%s/SKILL.md"
                            % (rel, name, name))
            continue
        matches = USAGE_VERSION_LINE.findall(read_text(path))
        if len(matches) != 1:
            findings.append("%s: expected exactly one '**Version:** X.Y.Z' line, found %d"
                            % (rel, len(matches)))
            continue
        seen_any = True
        if matches[0] != declared[name]:
            findings.append("%s: claims version %s, but skills/%s/SKILL.md declares %s"
                            % (rel, matches[0], name, declared[name]))
    if declared and not seen_any:
        raise Broken("no usage README under docs/skills/ yielded a '**Version:**' line, but %d skill(s) "
                     "exist. The label this script matches has probably changed, and a silent pass here "
                     "would let every usage README drift unchecked." % len(declared))
    return findings


def check_plugin_version(repo_root, library_version):
    """L4. The `**Plugin version:**` line in docs/status-skills.md against library.json."""
    rel = STATUS_REL
    matches = PLUGIN_VERSION_LINE.findall(read_text(os.path.join(repo_root, rel)))
    if not matches:
        raise Broken("%s carries no '**Plugin version:** X.Y.Z' line. Either the label changed or the "
                     "claim was removed; either way this script can no longer verify it." % rel)
    findings = []
    for claimed in matches:
        if claimed != library_version:
            findings.append("%s: claims plugin version %s, but library.json declares %s"
                            % (rel, claimed, library_version))
    return findings


def check_section_headings(repo_root, declared):
    """L5. Every skill must have a '### `plab-x` X.Y.Z' heading in docs/status-skills.md's
    Per-skill detail section, optionally followed by a comma-introduced note (", explicit only")."""
    rel = STATUS_REL
    text = read_text(os.path.join(repo_root, rel))
    matches = SECTION_HEADING.findall(text)
    if not matches:
        raise Broken("%s yielded no per-skill section headings at all, but %d skill(s) exist. The "
                     "heading shape this script matches ('### `plab-x` X.Y.Z') has probably "
                     "changed, and a silent pass here would let every heading drift unchecked."
                     % (rel, len(declared)))
    findings = []
    seen = set()
    for name, version in matches:
        seen.add(name)
        if name not in declared:
            findings.append("%s: section heading lists skill %r, which has no skills/%s/SKILL.md"
                            % (rel, name, name))
        elif version != declared[name]:
            findings.append("%s: section heading claims %s is %s, but skills/%s/SKILL.md declares %s"
                            % (rel, name, version, name, declared[name]))
    for name in sorted(declared):
        if name not in seen:
            findings.append("%s: no per-skill section heading for %r, which exists at skills/%s/SKILL.md"
                            % (rel, name, name))
    return findings


def check_library_components(repo_root, declared):
    """L6. library.json's components.skills[].version, one entry expected per skill."""
    rel = LIBRARY_REL
    claimed = declared_library_components(repo_root)
    if not claimed:
        raise Broken("%s's components.skills array yielded no usable {name, version} entries, but "
                     "%d skill(s) exist. The manifest shape this script reads has probably "
                     "changed, and a silent pass here would let every component version drift "
                     "unchecked." % (rel, len(declared)))
    findings = []
    for name, version in sorted(claimed.items()):
        if name not in declared:
            findings.append("%s: components.skills lists skill %r, which has no skills/%s/SKILL.md"
                            % (rel, name, name))
        elif version != declared[name]:
            findings.append("%s: components.skills claims %s is %s, but skills/%s/SKILL.md declares %s"
                            % (rel, name, version, name, declared[name]))
    for name in sorted(declared):
        if name not in claimed:
            findings.append("%s: components.skills has no entry for %r, which exists at skills/%s/SKILL.md"
                            % (rel, name, name))
    return findings


def run_all_checks(repo_root):
    """The one top-level entry point the real run and the wiring self-test both drive. A check dropped from this list is a check that never runs in production."""
    declared = declared_skill_versions(repo_root)
    library_version = declared_library_version(repo_root)
    findings = []
    findings += check_table_location(repo_root, README_REL, declared, "the root README Skills table")
    findings += check_table_location(repo_root, STATUS_REL, declared, "the status page At a glance table")
    findings += check_usage_readmes(repo_root, declared)
    findings += check_plugin_version(repo_root, library_version)
    findings += check_section_headings(repo_root, declared)
    findings += check_library_components(repo_root, declared)
    return declared, findings


# ---------------------------------------------------------------------------
# Self-test. Every fixture is built in its own tempfile.TemporaryDirectory():
# self_test() never reads this repository, so the gate's trustworthiness does
# not depend on what the real docs happen to look like on the machine it runs
# on. Same discipline as doc-lifecycle-check.py and path-citation-check.py.
# ---------------------------------------------------------------------------

def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _skill_md(name, version):
    return ("---\nname: %s\ndescription: \"Test skill %s\"\nlicense: MIT\nmetadata:\n"
            "  version: \"%s\"\n  updated: 2026-01-01\n---\n\n# %s\n" % (name, name, version, name))


def _fixture(tmp, skills, readme_versions=None, status_versions=None,
             usage_versions=None, plugin_version="1.0.0", library_version="1.0.0",
             readme_table=True, usage_label="**Version:**",
             heading_versions=None, library_skill_versions=None,
             write_headings=True, library_has_components=True):
    """Build a miniature repository. Each *_versions dict may override what a location CLAIMS, so a canary is one dict entry away from an anti-canary."""
    readme_versions = dict(skills if readme_versions is None else readme_versions)
    status_versions = dict(skills if status_versions is None else status_versions)
    usage_versions = dict(skills if usage_versions is None else usage_versions)
    heading_versions = dict(skills if heading_versions is None else heading_versions)
    library_skill_versions = dict(skills if library_skill_versions is None else library_skill_versions)

    for name, version in skills.items():
        _write(os.path.join(tmp, "skills", name, "SKILL.md"), _skill_md(name, version))

    library_obj = {"name": "t", "version": library_version}
    if library_has_components:
        library_obj["components"] = {
            "skills": [{"name": name, "version": version}
                      for name, version in sorted(library_skill_versions.items())]
        }
    _write(os.path.join(tmp, LIBRARY_REL), json.dumps(library_obj))

    rows = ["# Test\n\n## Skills\n", "| Skill | What it does | Version |", "|---|---|---|"]
    for name, version in sorted(readme_versions.items()):
        if readme_table:
            rows.append("| [`%s`](docs/skills/%s/README.md) | Does a thing | %s |" % (name, name, version))
        else:
            rows.append("- `%s` is at %s" % (name, version))
    _write(os.path.join(tmp, README_REL), "\n".join(rows) + "\n")

    status = ["# Skill Status\n",
              "**Plugin version:** %s **Skills:** %d" % (plugin_version, len(skills)),
              "\n## At a glance\n", "| Skill | Version | Invocation |", "|---|---|---|"]
    for name, version in sorted(status_versions.items()):
        status.append("| `%s` | %s | Auto |" % (name, version))
    status.append("\n## Per-skill detail\n")
    if write_headings:
        for name, version in sorted(heading_versions.items()):
            status.append("### `%s` %s\n" % (name, version))
            status.append("Some body text about %s.\n" % name)
    _write(os.path.join(tmp, STATUS_REL), "\n".join(status) + "\n")

    for name, version in usage_versions.items():
        _write(os.path.join(tmp, "docs", "skills", name, "README.md"),
               "# %s\n\n%s %s\n**Source:** somewhere\n\n| Ver | Note |\n|---|---|\n| 0.9.0 | history, must be ignored |\n"
               % (name, usage_label, version))
    return tmp


def _self_test_all_agree(failures):
    """Anti-canary for the whole pipeline: a tree where everything matches must produce zero findings. Without this, a check that flagged everything unconditionally would still pass every canary below."""
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.2.3", "plab-b": "2.0.0"}, plugin_version="1.0.0", library_version="1.0.0")
        try:
            _, findings = run_all_checks(tmp)
        except Broken as exc:
            failures.append("all-agree fixture must not be BROKEN, got %r" % exc)
            return
        if findings:
            failures.append("all-agree fixture is an anti-canary and must produce zero findings, got %r" % findings)


def _self_test_each_location_canary(failures):
    """One canary per claim location, each proving that location is actually read. A single shared canary would let three of the four checks be deleted with the self-test still passing."""
    cases = (
        ("L1 root README table", dict(readme_versions={"plab-a": "9.9.9"}), "the root README Skills table"),
        ("L2 status page table", dict(status_versions={"plab-a": "9.9.9"}), "the status page At a glance table"),
        ("L3 usage README", dict(usage_versions={"plab-a": "9.9.9"}), "docs/skills/plab-a/README.md"),
        ("L4 plugin version", dict(plugin_version="9.9.9"), "claims plugin version 9.9.9"),
        ("L5 status page heading", dict(heading_versions={"plab-a": "9.9.9"}), "section heading claims"),
        ("L6 library components", dict(library_skill_versions={"plab-a": "9.9.9"}), "components.skills claims"),
    )
    for label, override, marker in cases:
        with tempfile.TemporaryDirectory() as tmp:
            _fixture(tmp, {"plab-a": "1.2.3"}, **override)
            try:
                _, findings = run_all_checks(tmp)
            except Broken as exc:
                failures.append("%s canary raised Broken instead of reporting a finding: %r" % (label, exc))
                continue
            hits = [f for f in findings if marker in f]
            if len(hits) != 1:
                failures.append("%s: expected exactly one finding mentioning %r, got %r"
                                % (label, marker, findings))


def _self_test_missing_skill_is_a_finding(failures):
    """A skill that exists but is absent from a table is real drift, so it is a FINDING. Distinct from the blind-matcher case below, which is BROKEN."""
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0", "plab-b": "2.0.0"},
                 readme_versions={"plab-a": "1.0.0"})
        try:
            _, findings = run_all_checks(tmp)
        except Broken as exc:
            failures.append("a table missing ONE skill must be a finding, not BROKEN, got %r" % exc)
            return
        hits = [f for f in findings if "has no row for skill 'plab-b'" in f]
        if len(hits) != 1:
            failures.append("expected exactly one 'no row for plab-b' finding, got %r" % findings)


def _self_test_blind_matcher_is_broken(failures):
    """The load-bearing test. If the table shape changes so nothing matches, the gate must refuse to report CLEAN. This is the empty-`git tag -l` lesson applied to a prose matcher: a detector that has gone blind must say so rather than pass."""
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0"}, readme_table=False)
        try:
            _, findings = run_all_checks(tmp)
        except Broken:
            pass
        else:
            failures.append("a README whose Skills table no longer matches must raise Broken (exit 2), "
                            "not report %r" % findings)

    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0"}, usage_label="**Ver:**")
        try:
            _, findings = run_all_checks(tmp)
        except Broken:
            pass
        else:
            failures.append("usage READMEs whose '**Version:**' label changed must raise Broken (exit 2), "
                            "not report %r" % findings)

    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0"}, write_headings=False)
        try:
            _, findings = run_all_checks(tmp)
        except Broken:
            pass
        else:
            failures.append("docs/status-skills.md with no per-skill section headings at all must "
                            "raise Broken (exit 2), not report %r" % findings)

    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0"}, library_has_components=False)
        try:
            _, findings = run_all_checks(tmp)
        except Broken:
            pass
        else:
            failures.append("library.json with no components.skills array at all must raise Broken "
                            "(exit 2), not report %r" % findings)


def _self_test_heading_and_component_missing_skill_is_a_finding(failures):
    """L5 and L6's version of the 'a skill exists but is absent from a location' case the README
    and status-table locations already prove (`_self_test_missing_skill_is_a_finding`)."""
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0", "plab-b": "2.0.0"},
                 heading_versions={"plab-a": "1.0.0"},
                 library_skill_versions={"plab-a": "1.0.0"})
        try:
            _, findings = run_all_checks(tmp)
        except Broken as exc:
            failures.append("a heading/components location missing ONE skill must be a finding, "
                            "not BROKEN, got %r" % exc)
            return
        heading_hits = [f for f in findings if "no per-skill section heading for 'plab-b'" in f]
        comp_hits = [f for f in findings if "components.skills has no entry for 'plab-b'" in f]
        if len(heading_hits) != 1:
            failures.append("expected exactly one missing-heading finding for plab-b, got %r" % findings)
        if len(comp_hits) != 1:
            failures.append("expected exactly one missing-components-entry finding for plab-b, got %r" % findings)


def _self_test_history_versions_ignored(failures):
    """The D-12 lesson, as a fixture. Every usage README in the all-agree tree carries a 0.9.0 in a history table, and no fixture above expects a finding for it. This test states that intent explicitly so a future change to a blanket version sweep fails here instead of in review."""
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0"})
        try:
            _, findings = run_all_checks(tmp)
        except Broken as exc:
            failures.append("history-versions fixture must not be BROKEN, got %r" % exc)
            return
        if any("0.9.0" in f for f in findings):
            failures.append("a version-shaped string inside a history table must be ignored, not flagged: %r"
                            % findings)


def _self_test_ambiguous_row_is_broken(failures):
    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp, {"plab-a": "1.0.0"})
        path = os.path.join(tmp, README_REL)
        text = read_text(path)
        _write(path, text.replace("| Does a thing | 1.0.0 |", "| 2.0.0 | 1.0.0 |"))
        try:
            run_all_checks(tmp)
        except Broken:
            pass
        else:
            failures.append("a table row carrying two different version cells is ambiguous and must raise "
                            "Broken rather than guess which is the claim")


def self_test():
    failures = []
    _self_test_all_agree(failures)
    _self_test_each_location_canary(failures)
    _self_test_missing_skill_is_a_finding(failures)
    _self_test_heading_and_component_missing_skill_is_a_finding(failures)
    _self_test_blind_matcher_is_broken(failures)
    _self_test_history_versions_ignored(failures)
    _self_test_ambiguous_row_is_broken(failures)
    if failures:
        print("BROKEN: gate self-test failed, the detector is not trustworthy.", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        return False
    print("gate self-test: PASS (6 claim locations each proved against their own canary, an all-agree "
          "anti-canary, a missing-skill finding for the README/status tables plus one for the "
          "section headings and the manifest components, four blind-matcher BROKEN cases, a "
          "history-version false-positive guard, and an ambiguous-row BROKEN case)")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--self-test-only", action="store_true")
    args = parser.parse_args()

    if not self_test():
        sys.exit(2)
    if args.self_test_only:
        sys.exit(0)

    repo_root = os.path.abspath(args.repo_root)
    try:
        declared, findings = run_all_checks(repo_root)
    except Broken as exc:
        print("BROKEN: %s" % exc, file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:                                    # noqa: BLE001
        print("BROKEN: unanticipated %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        sys.exit(2)

    if findings:
        print("FINDINGS: %d version claim(s) disagree with what the repository declares.\n" % len(findings))
        for f in findings:
            print("  " + f)
        print("\nAuthoritative sources: skills/<name>/SKILL.md metadata.version, and library.json version.")
        sys.exit(1)

    print("CLEAN: canary proved, %d skill(s) checked across 6 claim locations, every claimed version "
          "matches what the repository declares." % len(declared))
    sys.exit(0)


if __name__ == "__main__":
    main()
