#!/usr/bin/env python3
"""
Cross-file document lifecycle gate for docs/internal/release-plans/.

EXIT-CODE CONTRACT
------------------
  0  CLEAN    self-test passed AND no cross-file invariant was violated
  1  FINDINGS self-test passed AND at least one invariant was violated
  2  BROKEN   the detector could not prove itself, a doc could not be parsed, git tag -l failed, git tag -l returned no tags without an explicit opt-in, or any other exception this script did not anticipate reached the top level

NEVER INTERPRET 2 AS CLEAN. See `scripts/check-dashes.py` and `skills/plab-wrap-session/scripts/path-citation-check.py` for the same contract applied to a repo-wide grep and a single-log scan; this script applies it to the relationships between the twenty spec/implementation-plan pairs and the five release plans that no single file's own frontmatter can see.

Also see `scripts/skill-drift-check.py`, which carries the same contract applied to a different relationship (a skill's own folder against its content at the latest tag). That script does not read `docs/internal/release-plans/` at all, and this one reads only whether a tag exists (`git tag -l`), never a file's content at a past commit, so neither one's silence substitutes for the other's.

Exit 1 means, and only means, that the detector proved itself and then found a real cross-file problem. No unexpected exception may ever surface as exit 1: `main()` wraps the whole run in a single top-level handler, so any exception this script did not specifically anticipate and convert to a sys.exit(2) of its own is still reported as BROKEN and still exits 2, never falls through to Python's default uncaught-exception behavior (which exits 1 and would be indistinguishable from a real finding).

WHY THIS SCRIPT EXISTS, AND WHY IT IS NOT A JSON SCHEMA
---------------------------------------------------------
A JSON Schema, or any per-file validator, checks a document against itself: does this file's frontmatter have the right keys, the right types, a status from the right enum. It cannot see that another file claims to supersede this one and this one has never heard of it, that two release plans both claim the same target version, or that a spec still reads `draft` for a release that has already shipped and been tagged. Those are relationships between files, or between a file and git state, and the maintainer was bitten by exactly one of them: a supersession declared in only one direction, found by hand during the 2026-08-25 `_local` documentation review (`_local/hygiene/2026-08-25_local-docs-review.md`, Section 1, "A live supersession asymmetry"). This script exists to catch that class mechanically instead of by a full manual read every few weeks.

WHY EVERY CHECK HERE IS MECHANICAL, WITH NO JUDGMENT CALLS
-------------------------------------------------------------
The same review (Section 5) measured what happens when a judgment rule gets mechanized anyway: D-12's path-citation rule, which reads fine as prose because a human applies sense to it, scored 13 flags with 11 false positives once written as a literal script (`docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-12_path-citation-precision/spec.md`). The lesson kept here is "mechanize the lifecycle fields, never the content judgment": every check below compares a field to another field, a field to a filesystem fact, or a field to git state, and none of them read prose for meaning. The acceptance-criteria count check was nearly dropped for the same reason; it shipped only after an empirical sweep of all sixteen real specs AND the spec-template.md / example specs under skills/plab-spec/references/ found that exactly two checklist forms cover every one of them with zero exceptions (the bare `- [ ] AC-N:` form the sixteen real specs use, and the `- [ ] **AC-N** -` form the template and its examples document as what the generator itself produces), while both forms are read only outside fenced code blocks so a spec that quotes AC syntax as a documentation example is not double-counted.

WHY EVERY SUBPROCESS BOUNDARY PINS encoding="utf-8"
-----------------------------------------------------
`scripts/check-dashes.py`'s docstring records the failure this guards against: Python's subprocess text mode defaults to the locale encoding, which is cp1252 on this maintainer's machine, and cp1252 cannot represent the same bytes UTF-8 can, so an unpinned subprocess call can silently see nothing to match and report a clean result that is really a broken one. The `git tag -l` call below pins `encoding="utf-8"` for the same reason, and so does every `open()` call in this file. A file that is not valid UTF-8 is reported as a named, path-specific BROKEN finding rather than an uncaught traceback.

WHY AN EMPTY `git tag -l` IS BROKEN, NOT CLEAN
---------------------------------------------------
Invariant 4 (released-but-unfulfilled) can only fire against tags that are actually present. A default GitHub Actions checkout (`actions/checkout`) fetches no tags at all unless `fetch-tags: true` is set or a later step runs `git fetch --tags`, so an empty tag list is far more often a starved checkout than a repository that has genuinely never tagged a release. If an empty tag list were treated as "no violations found," invariant 4 would pass CLEAN on every CI run by construction, proving nothing, silently. So an empty tag list is BROKEN unless `--allow-no-tags` is passed explicitly, for the one genuine case: a repository that really has never tagged.

WHY EACH INVARIANT'S FIXTURE IS BUILT IN ITS OWN tempfile.TemporaryDirectory()
---------------------------------------------------------------------------------
`self_test()` below never touches this repository. Each of the ten invariants gets its own small, throwaway fixture tree containing exactly one seeded violation (a canary, which must be flagged) alongside at least one correctly-shaped sibling (an anti-canary, which must not be). That keeps this gate's trustworthiness independent of whatever `docs/internal/release-plans/` happens to look like on the machine it runs on, which is the same discipline `path-citation-check.py` documents under "The self-test never touches --repo-root." On top of the ten per-check fixtures, one more fixture drives the checks through `run_all_checks()` itself, the same top-level entry point the real run uses, seeded with one violation of every invariant at once, so a check silently missing from the shipped pipeline is caught even though each check function still passes its own isolated test. The invariant-4/10 tag-availability gate is proved separately, as a pure decision function with no git and no filesystem, against all three of its branches (tags present, tags absent without the opt-in, tags absent with the opt-in); both invariants share one tag list and one gate, so one proof covers both. And invariant 10's dated baseline is proved both ways: a release plan named in it produces zero findings (the anti-canary), and the same release plan with its entry removed from the baseline produces a finding (the canary), by passing a smaller `baseline` dict directly to `check_released_but_prerelease_release_plans()` rather than mutating the module-level constant.

THE TEN INVARIANTS
----------------------
  1. Supersession symmetry, both directions: if a document declares `superseded-by: X`, a document with `id: X` must exist and must declare `supersedes:` back naming this document's own id; if a document declares `supersedes: Y`, a document with `id: Y` must exist and must declare `superseded-by:` back naming this document's own id. Checked across specs, implementation plans, AND release plans, not just the first two: this is a field-to-field comparison, not a per-file-type rule, so a release plan carrying either field is checked exactly like a spec.
  2. No two release plans may declare the same `target-version`.
  3. No two release plans may declare the same `sequence`.
  4. A spec whose `target-release` is already an existing git tag must be `fulfilled` or `superseded`, never still `draft` or `committed`. This invariant is only as trustworthy as the tag list it is checked against; see "WHY AN EMPTY git tag -l IS BROKEN, NOT CLEAN" above.
  5. Every `linked-spec`, `linked-plan` and `linked-release` value must resolve to a real FILE (not a directory), tried first relative to the citing file's own directory and then relative to the repo root, since this repository stores some of these paths one way and some the other. A non-string value (for example a list) is itself a finding, not a silently skipped field. Checked across specs, implementation plans, AND release plans. `linked-effort` is deliberately never checked here: the schema allows it to be a plain-language description of an untracked source rather than a path, and a tracked document is not permitted to cite an untracked one (`skills/plab-spec/references/frontmatter-schema.md`, `linked-effort` row).
  6. An effort folder named like `D-07_waiting-on-blocker-contract` must contain a `spec.md` whose `id` is `D-07`, and the `implementation-plan.md` beside it must carry the same `id`.
  7. A release plan's `spec-count` and `plan-count` must equal the number of `spec.md` and `implementation-plan.md` files present in that release plan's effort folders, and its `includes` list must name exactly the effort ids whose folders are present there. "Effort folder" has exactly one definition in this script, used for both halves of this invariant and for invariant 6: an immediate subdirectory of the release plan's own folder, matching the `ID_slug` naming convention (`effort_dirs_of()`). Nothing deeper than that is counted, matching the documented convention that effort subfolders are peers of `plan.md`, not an arbitrarily deep tree.
  8. A spec's `ac-count` must equal the number of AC checklist lines in its body, outside fenced code blocks, counting either of two forms: `- [ ] AC-N: <text>` (17 of the 20 real specs in this repository use this form) or `- [ ] **AC-N** - <text>` (the other 3 real specs use this form, alongside `skills/plab-spec/references/spec-template.md` and its example specs, which document it as the generator's own output).
  9. A spec's `status` and its acceptance-criteria checkboxes must agree: a `fulfilled` spec must have every AC checkbox ticked, and a `draft` spec must have none ticked. `committed` and `superseded` are deliberately not checked, for a reason that is empirical rather than an oversight; see `check_ac_status_agreement()`. Invariants 8 and 9 read the same checkbox lines through the same regex and therefore cannot disagree about what an acceptance criterion is: 8 counts them, 9 reads their state.
  10. A release plan whose `status` is still pre-release (`draft` or `in-progress`, per `docs/internal/schemas/release-plan.schema.json`'s status enum, which also allows `complete`) and whose `target-version` is already an existing git tag is a finding, unless it is named in the dated baseline below (`BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS`). Baselined 2026-10-16: `plan_05_reconcile-at-resume` (target-version v0.6.0), `plan_06_derived-facts` (v0.7.0) and `plan_07_aggregation` (v0.8.0); v0.6.0, v0.7.0 and v0.8.0 each shipped other content than what these three plans describe. Retiring or renumbering these version-named plans is the deferred "plan half" of decision 21 in the maintainer's private decision register (versions are assigned only at ship time), which is the maintainer's call, not this gate's. The baseline is keyed on `(sequence, target-version)`, so a plan whose frontmatter later changes either field drops out of the baseline on its own and must be re-added deliberately if the deferral still applies; a plan removed from the baseline, or any release plan newly meeting this shape, is a finding. Checked like invariant 4: this invariant is only as trustworthy as the tag list it is checked against.

WHAT THIS SCRIPT DELIBERATELY DOES NOT CHECK
------------------------------------------------
Per-file frontmatter shape (required keys, enum membership, type correctness) is a JSON Schema's job, not this script's; a file this script cannot even locate a frontmatter block in, or cannot decode as UTF-8, is treated as BROKEN rather than silently skipped, because a parser that returns an empty result for a malformed file and calls that clean is the exact failure the three-state contract exists to rule out. Whether a roadmap's reasoning still holds, whether a status change was the right call, and whether a document should exist at all are judgment calls the 2026-08-25 review names explicitly as things a gate must never try to answer; this script answers none of them.

This script's flat-frontmatter parser deliberately supports only 'key: value' lines, an inline '[a, b]' list, a quoted or bare scalar, and a trailing '# comment' stripped the way real YAML strips one (only when the '#' is preceded by whitespace or starts the value, and never inside quotes). A YAML block sequence (a 'key:' line followed by '- item' lines, indented or not) is NOT supported: rather than silently parsing to an empty value and producing a false "missing from includes" finding, this script fails loud, reporting the document as BROKEN with a named line and a rewrite-as-inline remedy.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

RELEASE_PLANS_REL = "docs/internal/release-plans"

KEY_LINE = re.compile(r'^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$')
BLOCK_LIST_ITEM = re.compile(r'^\s*-\s')
# The capture group holds the checkbox state character, which invariant 9 reads and invariant 8
# ignores. Deliberately ONE regex rather than two: findall() with a single group returns the group
# instead of the whole match, so len() is unchanged and invariant 8 counts exactly what it counted
# before, while invariant 9 becomes structurally incapable of disagreeing with invariant 8 about
# what an AC line is. Two regexes kept in sync by hand would eventually drift, and the failure mode
# would be invariant 9 silently not seeing lines invariant 8 counts.
AC_CHECKBOX = re.compile(r'^- \[([ xX])\] (?:AC-\d+:|\*\*AC-\d+\*\*)', re.MULTILINE)
EFFORT_FOLDER = re.compile(r'^([A-Z]{1,2}-\d{2,4})_')
FENCE_LINE = re.compile(r'^\s*```')

LINK_FIELDS = ("linked-spec", "linked-plan", "linked-release")
TERMINAL_SPEC_STATUSES = ("fulfilled", "superseded")

# Invariant 9's three-way split of the spec status enum in docs/internal/schemas/spec.schema.json.
# The union of these three tuples must equal that enum. A status in none of them is reported as a
# finding rather than skipped, so widening the schema without widening this invariant cannot make
# the invariant pass silently.
AC_TICK_ALL_REQUIRED = ("fulfilled",)
AC_TICK_NONE_ALLOWED = ("draft",)
AC_TICK_UNCHECKED = ("committed", "superseded")

# Invariant 10's two-way split of the release-plan status enum in
# docs/internal/schemas/release-plan.schema.json: "draft" and "in-progress" are pre-release,
# "complete" is the one terminal status and is never checked here.
PRERELEASE_RELEASE_STATUSES = ("draft", "in-progress")

# Dated baseline for invariant 10, added 2026-10-16. Each entry is a release plan already in a
# pre-release status whose target-version is already tagged, deliberately NOT fixed by retiring or
# renumbering the plan: that is the deferred "plan half" of decision 21 in the maintainer's private
# decision register (versions are assigned only at ship time), which is the maintainer's call, not
# this gate's. v0.6.0, v0.7.0 and v0.8.0 each shipped other content than what these three plans
# describe. Keyed on (sequence, target-version), not on folder name: a plan whose frontmatter later
# changes either field drops out of this baseline on its own, so continuing to defer it after that
# requires a deliberate re-add rather than silently continuing to pass.
BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS = {
    ("05", "v0.6.0"),  # plan_05_reconcile-at-resume
    ("06", "v0.7.0"),  # plan_06_derived-facts
    ("07", "v0.8.0"),  # plan_07_aggregation
}


class FrontmatterError(Exception):
    """Raised when a doc's frontmatter block cannot be located, cannot be bounded, cannot be decoded as UTF-8, or uses YAML this flat parser does not support. Treated as BROKEN, never as an absence of findings."""


def strip_quotes(s):
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def strip_inline_comment(raw_value):
    """Strip a trailing ' # comment' from a raw (still-quoted) YAML value, the way a real YAML parser does: a '#' starts a comment only when it is preceded by whitespace or begins the value, and never while inside a quoted string. Without this, a value copied from a template that ships an inline comment (docs/internal/release-plans ships none, but skills/plab-release-plan/references/plan-template.md does, on spec-count, plan-count and includes) is treated as part of the value and produces a false finding."""
    in_quote = None
    for i, ch in enumerate(raw_value):
        if in_quote:
            if ch == in_quote:
                in_quote = None
        elif ch in ('"', "'"):
            in_quote = ch
        elif ch == "#" and (i == 0 or raw_value[i - 1].isspace()):
            return raw_value[:i].rstrip()
    return raw_value


def parse_scalar_or_list(val):
    """Parse one flat 'key: value' right-hand side: an inline [a, b] list, a quoted or bare string, or the literal null."""
    if val == "" or val == "null":
        return None if val == "null" else ""
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [strip_quotes(item.strip()) for item in inner.split(",")]
    return strip_quotes(val)


def parse_flat_yaml(fm_lines):
    """Parse this repo's flat frontmatter: 'key: value' lines, occasional inline lists, occasional quoted strings, occasional trailing '# comment's. No nesting, no multiline values, no anchors: a YAML block sequence is refused with a ValueError rather than silently parsed as an empty value."""
    result = {}
    for raw in fm_lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        m = KEY_LINE.match(raw)
        if not m:
            if BLOCK_LIST_ITEM.match(raw):
                raise ValueError(
                    "line %r looks like a YAML block-sequence item, which this flat parser does not "
                    "support (inline '[a, b]' lists only); rewrite the preceding key as a single-line "
                    "inline list" % raw)
            continue
        key = m.group(1)
        value = strip_inline_comment(m.group(2)).strip()
        result[key] = parse_scalar_or_list(value)
    return result


def read_doc(abs_path, repo_root):
    """Read one spec.md / implementation-plan.md / plan.md: its frontmatter dict and the body text after the closing '---'."""
    try:
        with open(abs_path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
    except UnicodeDecodeError as exc:
        raise FrontmatterError("%s: not valid UTF-8 (%s)" % (abs_path, exc))
    if not lines or lines[0].rstrip() != "---":
        raise FrontmatterError("%s: does not open with a '---' frontmatter delimiter" % abs_path)
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end = i
            break
    if end is None:
        raise FrontmatterError("%s: frontmatter block opens but never closes with '---'" % abs_path)
    try:
        fm = parse_flat_yaml(lines[1:end])
    except ValueError as exc:
        raise FrontmatterError("%s: %s" % (abs_path, exc))
    body = "\n".join(lines[end + 1:])
    rel_path = os.path.relpath(abs_path, repo_root).replace(os.sep, "/")
    return {
        "path": rel_path,
        "abs_dir": os.path.dirname(abs_path),
        "fm": fm,
        "body": body,
    }


def discover(repo_root):
    """Walk docs/internal/release-plans/ and return (specs, plans, releases, parse_errors)."""
    root = os.path.join(repo_root, *RELEASE_PLANS_REL.split("/"))
    specs, plans, releases, errors = [], [], [], []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fname, bucket in (("spec.md", specs), ("implementation-plan.md", plans), ("plan.md", releases)):
            if fname in filenames:
                abs_path = os.path.join(dirpath, fname)
                try:
                    bucket.append(read_doc(abs_path, repo_root))
                except FrontmatterError as exc:
                    errors.append(str(exc))
    return specs, plans, releases, errors


def find_release_plan_dirs(repo_root):
    root = os.path.join(repo_root, *RELEASE_PLANS_REL.split("/"))
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        if "plan.md" in filenames:
            out.append(dirpath)
    return out


def effort_dirs_of(release_plan_dir):
    """The one definition of 'effort folder' this script uses, for invariants 6 and 7 alike: an immediate subdirectory of a release-plan folder whose name matches the ID_slug convention, e.g. D-07_waiting-on-blocker-contract. Nothing nested deeper than this is an effort folder."""
    out = []
    for name in sorted(os.listdir(release_plan_dir)):
        full = os.path.join(release_plan_dir, name)
        if os.path.isdir(full):
            m = EFFORT_FOLDER.match(name)
            if m:
                out.append((m.group(1), full))
    return out


def build_id_registry(specs, plans, releases):
    """Every document carrying an 'id', regardless of type: specs, implementation plans, and release plans alike, since supersession symmetry (invariant 1) is a field-to-field comparison that does not care what kind of document is on either end."""
    reg = {}
    for d in specs + plans + releases:
        i = d["fm"].get("id")
        if i:
            reg.setdefault(i, []).append(d)
    return reg


def check_supersession_symmetry(specs, plans, releases):
    """Invariant 1: true bidirectional supersession. If A declares superseded-by: X, a document with id X must exist and must declare supersedes: A back. If A declares supersedes: Y, a document with id Y must exist and must declare superseded-by: A back. Both fields are read; a document that only ever set one half of the pair (the real maintainer historical shape: a new document declares supersedes: Y and Y says nothing back) is caught either way, from whichever side is scanned first."""
    docs = specs + plans + releases
    reg = build_id_registry(specs, plans, releases)
    findings = []
    for d in docs:
        my_id = d["fm"].get("id")
        target = d["fm"].get("superseded-by")
        if target:
            if not isinstance(target, str):
                findings.append("%s: superseded-by %r is not a single document id (must be a plain string)"
                                 % (d["path"], target))
            elif target not in reg:
                findings.append("%s: declares superseded-by: %s, but no document carries id %s"
                                 % (d["path"], target, target))
            elif not any(t["fm"].get("supersedes") == my_id for t in reg[target]):
                findings.append("%s: declares superseded-by: %s, but %s does not declare supersedes: %s back"
                                 % (d["path"], target, target, my_id))
        source = d["fm"].get("supersedes")
        if source:
            if not isinstance(source, str):
                findings.append("%s: supersedes %r is not a single document id (must be a plain string)"
                                 % (d["path"], source))
            elif source not in reg:
                findings.append("%s: declares supersedes: %s, but no document carries id %s"
                                 % (d["path"], source, source))
            elif not any(s["fm"].get("superseded-by") == my_id for s in reg[source]):
                findings.append("%s: declares supersedes: %s, but %s does not declare superseded-by: %s back"
                                 % (d["path"], source, source, my_id))
    return findings


def check_unique_release_field(releases, field, label):
    """Invariants 2 and 3: no two release plans may share a target-version, or a sequence."""
    groups = {}
    for r in releases:
        val = r["fm"].get(field)
        if val is None or val == "":
            continue
        groups.setdefault(val, []).append(r["path"])
    findings = []
    for val, paths in sorted(groups.items()):
        if len(paths) > 1:
            findings.append("%s %r is declared by %d release plans: %s"
                             % (label, val, len(paths), ", ".join(sorted(paths))))
    return findings


def check_released_but_unfulfilled(specs, tags):
    """Invariant 4: a spec targeting an already-tagged release must be fulfilled or superseded."""
    findings = []
    for s in specs:
        target = s["fm"].get("target-release")
        if not target or target not in tags:
            continue
        status = s["fm"].get("status")
        if status not in TERMINAL_SPEC_STATUSES:
            findings.append("%s: target-release %s is already tagged, but status is %r (must be fulfilled or superseded)"
                             % (s["path"], target, status))
    return findings


def check_link_resolution(docs, repo_root):
    """Invariant 5: linked-spec / linked-plan / linked-release must resolve to a real FILE, either relative to the citing file's directory or relative to the repo root. A value that resolves only to a directory is not accepted: these fields cite a document, not a folder. A non-string value is itself a finding rather than a silently skipped field."""
    findings = []
    for d in docs:
        for field in LINK_FIELDS:
            if field not in d["fm"]:
                continue
            val = d["fm"][field]
            if val is None or val == "":
                continue
            if not isinstance(val, str):
                findings.append("%s: %s: %r is not a single path string, cannot resolve"
                                 % (d["path"], field, val))
                continue
            resolves_from_dir = os.path.isfile(os.path.join(d["abs_dir"], val))
            resolves_from_root = os.path.isfile(os.path.join(repo_root, val))
            if resolves_from_dir or resolves_from_root:
                continue
            findings.append("%s: %s: %r does not resolve to a file relative to its own directory or to the repo root"
                             % (d["path"], field, val))
    return findings


def check_folder_id_agreement(repo_root, specs, plans):
    """Invariant 6: an effort folder's id-prefixed name must match the id its spec.md and implementation-plan.md carry."""
    specs_by_dir = {d["abs_dir"]: d for d in specs}
    plans_by_dir = {d["abs_dir"]: d for d in plans}
    findings = []
    for rp_dir in find_release_plan_dirs(repo_root):
        for expected_id, eff_abs in effort_dirs_of(rp_dir):
            spec = specs_by_dir.get(eff_abs)
            if spec is not None and spec["fm"].get("id") != expected_id:
                findings.append("%s: folder name claims id %s but spec.md carries id %r"
                                 % (spec["path"], expected_id, spec["fm"].get("id")))
            plan = plans_by_dir.get(eff_abs)
            if plan is not None and plan["fm"].get("id") != expected_id:
                findings.append("%s: folder name claims id %s but implementation-plan.md carries id %r"
                                 % (plan["path"], expected_id, plan["fm"].get("id")))
    return findings


def _as_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def check_counts(repo_root, releases):
    """Invariant 7: spec-count, plan-count and includes must match what is actually present in the release plan's effort folders, using the one definition of 'effort folder' this script has (effort_dirs_of(): immediate ID_slug-named subdirectories, the same definition invariant 6 uses). Nothing nested deeper than that is counted."""
    findings = []
    for r in releases:
        rp_dir = r["abs_dir"]
        efforts = effort_dirs_of(rp_dir)
        spec_actual = sum(1 for _eid, eff_dir in efforts if os.path.isfile(os.path.join(eff_dir, "spec.md")))
        plan_actual = sum(1 for _eid, eff_dir in efforts if os.path.isfile(os.path.join(eff_dir, "implementation-plan.md")))
        declared_spec = _as_int(r["fm"].get("spec-count"))
        declared_plan = _as_int(r["fm"].get("plan-count"))
        if declared_spec != spec_actual:
            findings.append("%s: spec-count declares %r but %d spec.md files exist in this release plan's effort folders"
                             % (r["path"], r["fm"].get("spec-count"), spec_actual))
        if declared_plan != plan_actual:
            findings.append("%s: plan-count declares %r but %d implementation-plan.md files exist in this release plan's effort folders"
                             % (r["path"], r["fm"].get("plan-count"), plan_actual))
        declared_includes = r["fm"].get("includes")
        if isinstance(declared_includes, list):
            declared_set = set(declared_includes)
        elif declared_includes:
            declared_set = {declared_includes}
        else:
            declared_set = set()
        actual_ids = {eid for eid, _abs in efforts}
        missing = actual_ids - declared_set
        extra = declared_set - actual_ids
        if missing or extra:
            parts = []
            if missing:
                parts.append("missing from includes: %s" % ", ".join(sorted(missing)))
            if extra:
                parts.append("in includes but no such effort folder: %s" % ", ".join(sorted(extra)))
            findings.append("%s: includes disagrees with the effort folders present (%s)"
                             % (r["path"], "; ".join(parts)))
    return findings


def strip_fenced_code(body):
    """Remove the content of fenced code blocks (lines delimited by a ``` line) before counting AC checklist lines, so a spec that quotes AC checklist syntax as a documentation example inside a fence is not counted as if the example were real acceptance criteria."""
    out = []
    in_fence = False
    for line in body.split("\n"):
        if FENCE_LINE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def check_ac_count(specs):
    """Invariant 8: ac-count must equal the number of AC checklist lines in the body, outside fenced code blocks, counting either supported form: '- [ ] AC-N: ...' (17 of the 20 real specs) or '- [ ] **AC-N** - ...' (the other 3 real specs, plus skills/plab-spec/references/spec-template.md and its example specs). See the module docstring for the empirical sweep that justified both forms."""
    findings = []
    for s in specs:
        declared = _as_int(s["fm"].get("ac-count"))
        actual = len(AC_CHECKBOX.findall(strip_fenced_code(s["body"])))
        if declared is None:
            findings.append("%s: ac-count %r is not an integer" % (s["path"], s["fm"].get("ac-count")))
        elif declared != actual:
            findings.append("%s: ac-count declares %d but the body has %d AC checklist line(s) outside fenced code blocks"
                             % (s["path"], declared, actual))
    return findings


def check_ac_status_agreement(specs):
    """Invariant 9: a spec's status and its acceptance-criteria checkboxes must agree. A `fulfilled` spec asserts that every criterion was delivered, so every AC checkbox must be ticked; a `draft` spec has not had its contract agreed yet, so none may be. Both directions are real defect shapes rather than tidiness: a fulfilled spec with an unticked criterion claims delivery it never verified, and a draft spec with a ticked one claims delivery before anyone agreed what delivery meant.

    `committed` and `superseded` are deliberately NOT checked, and that is empirical rather than an oversight. `committed` is the one status a spec legitimately holds while its implementation plan is mid-execution, so a partial tick count there is the correct state and not a defect; checking it would false-flag exactly the window this repository is about to spend building A-02, whose spec is currently the only committed spec in the tree. `superseded` is a dead end whose ticks no longer assert anything about a live contract. A status this function does not recognise is reported rather than skipped, so widening the schema enum without widening this invariant cannot make it pass silently.

    A spec with zero AC lines passes vacuously. Whether a spec should carry criteria at all is invariant 8's business (`ac-count` against the body) and, before that, the JSON Schema's; this invariant only compares state that exists.

    Measured across the whole corpus on 2026-09-04, before the rule was written: 8 fulfilled specs at 52 of 52 ticked, 8 draft specs at 0 of 61, and 1 committed spec at 0 of 9. The record was already perfect and enforced by nothing, which is the reason to build the fixture while it still is."""
    findings = []
    for s in specs:
        status = s["fm"].get("status")
        if isinstance(status, str):
            status = status.strip().strip('"').strip("'")
        if status in AC_TICK_UNCHECKED:
            continue
        states = AC_CHECKBOX.findall(strip_fenced_code(s["body"]))
        total = len(states)
        ticked = sum(1 for c in states if c.lower() == "x")
        if status in AC_TICK_ALL_REQUIRED:
            if total and ticked != total:
                findings.append("%s: status is %r but %d of %d acceptance criteria are still unticked"
                                 % (s["path"], status, total - ticked, total))
        elif status in AC_TICK_NONE_ALLOWED:
            if ticked:
                findings.append("%s: status is %r but %d of %d acceptance criteria are already ticked"
                                 % (s["path"], status, ticked, total))
        else:
            known = ", ".join(AC_TICK_ALL_REQUIRED + AC_TICK_NONE_ALLOWED + AC_TICK_UNCHECKED)
            findings.append("%s: status %r is not one of the statuses invariant 9 knows (%s), so it "
                             "cannot decide whether the acceptance criteria agree, and is refusing to "
                             "skip silently" % (s["path"], status, known))
    return findings


def check_released_but_prerelease_release_plans(releases, tags, baseline=None):
    """Invariant 10: a release plan whose target-version is already tagged must not still be
    pre-release (PRERELEASE_RELEASE_STATUSES), unless it is named in the dated baseline. `baseline`
    is an injectable parameter, defaulting to the module-level BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS,
    so the self-test can prove removing an entry makes the run fail without mutating module state."""
    if baseline is None:
        baseline = BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS
    findings = []
    for r in releases:
        target = r["fm"].get("target-version")
        if not target or target not in tags:
            continue
        status = r["fm"].get("status")
        if status not in PRERELEASE_RELEASE_STATUSES:
            continue
        seq = r["fm"].get("sequence")
        if (seq, target) in baseline:
            continue
        findings.append(
            "%s: status is %r but target-version %s is already tagged, and this release plan is "
            "not in the dated baseline (decision 21 deferred, versions assigned at ship time)"
            % (r["path"], status, target))
    return findings


def baselined_prerelease_release_plan_notes(releases, tags, baseline=None):
    """Visible reporting for invariant 10's dated baseline, so a known violation is 'reported as
    known', not simply absent from the findings list. For each release plan that currently matches
    the pre-release-but-tagged shape AND is named in the baseline, returns a note string. A plan
    whose status or target-version later changes so it no longer matches the shape produces no
    note, so this never claims a plan is still a known violation once it has moved on."""
    if baseline is None:
        baseline = BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS
    notes = []
    for r in releases:
        target = r["fm"].get("target-version")
        status = r["fm"].get("status")
        seq = r["fm"].get("sequence")
        if not target or target not in tags or status not in PRERELEASE_RELEASE_STATUSES:
            continue
        if (seq, target) in baseline:
            notes.append(
                "%s: status %r with already-tagged target-version %s is a known baselined "
                "violation (decision 21 deferred, versions assigned at ship time)"
                % (r["path"], status, target))
    return notes


def run_all_checks(repo_root, specs, plans, releases, tags):
    """The one top-level entry point both the real run and the wiring self-test (_self_test_wiring) drive. A check silently dropped from this list is a check that never runs in production; the wiring self-test exists specifically to catch that, by asserting every invariant is represented in the findings from a single fixture seeded with one violation of each."""
    findings = []
    findings += check_supersession_symmetry(specs, plans, releases)
    findings += check_unique_release_field(releases, "target-version", "target-version")
    findings += check_unique_release_field(releases, "sequence", "sequence")
    findings += check_released_but_unfulfilled(specs, tags)
    findings += check_link_resolution(specs + plans + releases, repo_root)
    findings += check_folder_id_agreement(repo_root, specs, plans)
    findings += check_counts(repo_root, releases)
    findings += check_ac_count(specs)
    findings += check_ac_status_agreement(specs)
    findings += check_released_but_prerelease_release_plans(releases, tags)
    return findings


# ---------------------------------------------------------------------------
# Self-test fixtures. Each invariant gets its own throwaway tree with one
# seeded violation (the canary) and at least one correctly-shaped sibling
# (the anti-canary), built fresh in a tempfile.TemporaryDirectory() so this
# gate's trustworthiness never depends on the repository under the cursor.
# ---------------------------------------------------------------------------

def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _fm(pairs):
    lines = ["---"]
    for k, v in pairs:
        lines.append("%s: %s" % (k, v))
    lines.append("---")
    return "\n".join(lines) + "\n"


def _spec_doc(id_, ac_lines=2, ac_count=None, status="draft", target_release=None,
              linked_plan="implementation-plan.md", linked_release=None, superseded_by=None,
              supersedes=None, ac_form="colon", ac_ticked=0):
    if ac_count is None:
        ac_count = ac_lines
    pairs = [
        ("id", id_),
        ("title", '"Test spec %s"' % id_),
        ("type", "spec"),
        ("status", status),
        ("created", "2026-01-01"),
        ("updated", "2026-01-01"),
        ("linked-effort", '"a plain-language description, not a path"'),
        ("linked-plan", linked_plan if linked_plan is not None else "null"),
        ("ac-count", ac_count),
    ]
    if target_release:
        pairs.append(("target-release", target_release))
    if linked_release:
        pairs.append(("linked-release", linked_release))
    if superseded_by:
        pairs.append(("superseded-by", superseded_by))
    if supersedes:
        pairs.append(("supersedes", supersedes))
    body_lines = ["", "## Acceptance Criteria", ""]
    for i in range(1, ac_lines + 1):
        box = "x" if i <= ac_ticked else " "
        if ac_form == "colon":
            body_lines.append("- [%s] AC-%d: something true" % (box, i))
        else:
            body_lines.append("- [%s] **AC-%d** - something true" % (box, i))
    return _fm(pairs) + "\n".join(body_lines) + "\n"


def _plan_doc(id_, linked_spec="spec.md", linked_release=None):
    pairs = [
        ("id", id_),
        ("title", '"Implementation plan: %s"' % id_),
        ("type", "implementation-plan"),
        ("status", "draft"),
        ("created", "2026-01-01"),
        ("updated", "2026-01-01"),
        ("linked-spec", linked_spec),
        ("ac-coverage", "complete"),
        ("phase-count", 1),
    ]
    if linked_release:
        pairs.append(("linked-release", linked_release))
    return _fm(pairs) + "\nBody.\n"


def _release_doc(sequence, target_version, includes, spec_count, plan_count,
                  superseded_by=None, supersedes=None, linked_spec=None, includes_comment=None):
    includes_val = "[" + ", ".join(includes) + "]"
    if includes_comment:
        includes_val += "  " + includes_comment
    pairs = [
        ("sequence", sequence),
        ("target-version", target_version),
        ("title", '"Release plan %s"' % sequence),
        ("type", "release-plan"),
        ("status", "in-progress"),
        ("created", "2026-01-01"),
        ("updated", "2026-01-01"),
        ("theme", '"Test theme"'),
        ("includes", includes_val),
        ("spec-count", spec_count),
        ("plan-count", plan_count),
        ("checklist-complete", "false"),
    ]
    if superseded_by:
        pairs.append(("superseded-by", superseded_by))
    if supersedes:
        pairs.append(("supersedes", supersedes))
    if linked_spec:
        pairs.append(("linked-spec", linked_spec))
    return _fm(pairs) + "\nBody.\n"


def _rp(root, sequence):
    return os.path.join(root, "docs", "internal", "release-plans", "plan_%s_test" % sequence)


def _self_test_parser(failures):
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "spec.md")
        _write(p, _fm([
            ("id", "Z-01"),
            ("title", '"A title: with a colon inside quotes"'),
            ("type", "spec"),
            ("includes", "[A-01, B-02, C-03]"),
            ("linked-plan", "null"),
        ]) + "\nbody\n")
        doc = read_doc(p, tmp)
        if doc["fm"].get("title") != "A title: with a colon inside quotes":
            failures.append("parser: quoted title with an inner colon was not preserved: %r" % doc["fm"].get("title"))
        if doc["fm"].get("includes") != ["A-01", "B-02", "C-03"]:
            failures.append("parser: inline list was not parsed correctly: %r" % doc["fm"].get("includes"))
        if doc["fm"].get("linked-plan") is not None:
            failures.append("parser: literal null was not parsed as None: %r" % doc["fm"].get("linked-plan"))


def _self_test_parser_comments_and_block_sequence(failures):
    # Defect D (part 1): a trailing '# comment' on a scalar or inline-list value, exactly the shape
    # skills/plab-release-plan/references/plan-template.md ships on spec-count, plan-count and
    # includes, must be stripped rather than treated as part of the value.
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "plan.md")
        _write(p, _fm([
            ("sequence", "NN"),
            ("spec-count", "0                    # computed by --update"),
            ("includes", "[]                     # list of effort ids (e.g., [S-07, S-05]); grows on promote"),
            ("title", '"A #4 title with a hash inside quotes"'),
        ]) + "\nBody.\n")
        doc = read_doc(p, tmp)
        if doc["fm"].get("spec-count") != "0":
            failures.append("parser: trailing comment on spec-count was not stripped: %r" % doc["fm"].get("spec-count"))
        if doc["fm"].get("includes") != []:
            failures.append("parser: trailing comment on an inline list was not stripped: %r" % doc["fm"].get("includes"))
        if doc["fm"].get("title") != "A #4 title with a hash inside quotes":
            failures.append("parser: a '#' inside quotes was wrongly treated as a comment: %r" % doc["fm"].get("title"))

    # Defect E: a YAML block sequence must fail loud (BROKEN), not parse to an empty value.
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "plan.md")
        _write(p, "---\nsequence: NN\nincludes:\n  - A-01\n  - B-02\n---\nBody.\n")
        try:
            read_doc(p, tmp)
            failures.append("parser: a YAML block sequence for includes was silently accepted instead of raising FrontmatterError")
        except FrontmatterError:
            pass


def _self_test_supersession(failures):
    with tempfile.TemporaryDirectory() as tmp:
        d = os.path.join(tmp, "efforts")
        # A-02 -> Z-99: Z-99 does not exist anywhere. Still caught.
        _write(os.path.join(d, "A-02_missing", "spec.md"), _spec_doc("A-02", superseded_by="Z-99"))
        _write(os.path.join(d, "A-02_missing", "implementation-plan.md"), _plan_doc("A-02"))
        # A-01 <-> A-03: a fully symmetric pair. True anti-canary: must produce zero findings.
        _write(os.path.join(d, "A-01_old", "spec.md"), _spec_doc("A-01", superseded_by="A-03"))
        _write(os.path.join(d, "A-01_old", "implementation-plan.md"), _plan_doc("A-01"))
        _write(os.path.join(d, "A-03_new", "spec.md"), _spec_doc("A-03", supersedes="A-01"))
        _write(os.path.join(d, "A-03_new", "implementation-plan.md"), _plan_doc("A-03"))
        # A-05 -> A-06, one-directional: the real 2026-08-25 historical shape. A-06 says nothing back.
        _write(os.path.join(d, "A-05_new", "spec.md"), _spec_doc("A-05", supersedes="A-06"))
        _write(os.path.join(d, "A-05_new", "implementation-plan.md"), _plan_doc("A-05"))
        _write(os.path.join(d, "A-06_old", "spec.md"), _spec_doc("A-06"))
        _write(os.path.join(d, "A-06_old", "implementation-plan.md"), _plan_doc("A-06"))
        # A-07: a non-string superseded-by (e.g. a list) is a finding, not a crash.
        _write(os.path.join(d, "A-07_listvalue", "spec.md"), _spec_doc("A-07", superseded_by="[A-01, A-03]"))
        _write(os.path.join(d, "A-07_listvalue", "implementation-plan.md"), _plan_doc("A-07"))
        # A-08 -> A-09, the RECIPROCITY branch: superseded-by names a target that EXISTS and simply
        # does not point back. Without this fixture the branch is unproven, because A-02's target is
        # missing entirely and therefore exits through the dangling-target branch instead. Adversarial
        # review found exactly this gap: deleting the reciprocity test left the self-test reporting
        # PASS while the gate silently stopped catching half of what invariant 1 claims to cover.
        _write(os.path.join(d, "A-08_old", "spec.md"), _spec_doc("A-08", superseded_by="A-09"))
        _write(os.path.join(d, "A-08_old", "implementation-plan.md"), _plan_doc("A-08"))
        _write(os.path.join(d, "A-09_new", "spec.md"), _spec_doc("A-09"))
        _write(os.path.join(d, "A-09_new", "implementation-plan.md"), _plan_doc("A-09"))

        subdirs = ("A-01_old", "A-02_missing", "A-03_new", "A-05_new", "A-06_old", "A-07_listvalue",
                   "A-08_old", "A-09_new")
        specs = [read_doc(os.path.join(d, sub, "spec.md"), tmp) for sub in subdirs]
        plans = [read_doc(os.path.join(d, sub, "implementation-plan.md"), tmp) for sub in subdirs]
        findings = check_supersession_symmetry(specs, plans, [])

        missing = [f for f in findings if "A-02" in f and "Z-99" in f]
        asymmetric = [f for f in findings if "A-05" in f and "A-06" in f]
        listvalue = [f for f in findings if "A-07" in f]
        symmetric_pair_noise = [f for f in findings if ("A-01" in f or "A-03" in f) and "A-02" not in f and "A-05" not in f and "A-07" not in f]

        if not missing:
            failures.append("check 1 (supersession symmetry): expected a finding for A-02's dangling superseded-by: Z-99, got %r" % findings)
        if not asymmetric:
            failures.append("check 1 (supersession symmetry): expected a finding for A-05's one-directional supersedes: A-06 "
                             "(the real 2026-08-25 historical shape), got %r" % findings)
        if not listvalue:
            failures.append("check 1 (supersession symmetry): expected a finding (not a crash) for A-07's list-valued "
                             "superseded-by, got %r" % findings)
        reciprocity = [f for f in findings if "A-08" in f and "A-09" in f]
        if not reciprocity:
            failures.append("check 1 (supersession symmetry): expected a finding for A-08's superseded-by: A-09 where "
                             "A-09 exists but does not declare supersedes back. This is the reciprocity branch; A-02 "
                             "cannot prove it because its target is missing entirely and exits elsewhere, got %r" % findings)
        if symmetric_pair_noise:
            failures.append("check 1 (supersession symmetry): the fully symmetric A-01/A-03 pair must produce zero "
                             "findings (anti-canary), got %r" % symmetric_pair_noise)
        if len(findings) != 4:
            failures.append("check 1 (supersession symmetry): expected exactly 4 findings (A-02, A-05, A-07, A-08), got %r" % findings)


def _self_test_target_version_uniqueness(failures):
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(_rp(tmp, "01"), "plan.md"), _release_doc("01", "v1.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "02"), "plan.md"), _release_doc("02", "v1.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "03"), "plan.md"), _release_doc("03", "v3.0.0", [], 0, 0))
        releases = [read_doc(os.path.join(_rp(tmp, s), "plan.md"), tmp) for s in ("01", "02", "03")]
        findings = check_unique_release_field(releases, "target-version", "target-version")
        if len(findings) != 1 or "v1.0.0" not in findings[0] or "v3.0.0" in findings[0]:
            failures.append("check 2 (target-version uniqueness): expected exactly one v1.0.0 collision, got %r" % findings)


def _self_test_sequence_uniqueness(failures):
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(_rp(tmp, "01"), "plan.md"), _release_doc("01", "vA.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "02"), "plan.md"), _release_doc("01", "vB.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "03"), "plan.md"), _release_doc("03", "vC.0.0", [], 0, 0))
        releases = [read_doc(os.path.join(_rp(tmp, s), "plan.md"), tmp) for s in ("01", "02", "03")]
        findings = check_unique_release_field(releases, "sequence", "sequence")
        matching = [f for f in findings if "'01'" in f]
        if len(findings) != 1 or not matching:
            failures.append("check 3 (sequence uniqueness): expected exactly one sequence '01' collision, got %r" % findings)


def _self_test_released_but_unfulfilled(failures):
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "shipped_bad", "spec.md"), _spec_doc("R-01", status="draft", target_release="v9.9.9"))
        _write(os.path.join(tmp, "shipped_good", "spec.md"), _spec_doc("R-02", status="fulfilled", target_release="v9.9.9"))
        _write(os.path.join(tmp, "unshipped", "spec.md"), _spec_doc("R-03", status="draft", target_release="v8.8.8"))
        specs = [read_doc(os.path.join(tmp, sub, "spec.md"), tmp) for sub in ("shipped_bad", "shipped_good", "unshipped")]
        tags = {"v9.9.9"}
        findings = check_released_but_unfulfilled(specs, tags)
        if len(findings) != 1 or "shipped_bad" not in findings[0]:
            failures.append("check 4 (released but unfulfilled): expected exactly one R-01 finding, got %r" % findings)


def _self_test_link_resolution(failures):
    with tempfile.TemporaryDirectory() as tmp:
        rp = _rp(tmp, "05")
        _write(os.path.join(rp, "plan.md"), _release_doc("05", "v5.0.0", ["E-01"], 1, 1))
        rel_release_path = "docs/internal/release-plans/plan_05_test/plan.md"
        eff = os.path.join(rp, "E-01_effort")
        _write(os.path.join(eff, "spec.md"),
               _spec_doc("E-01", linked_plan="missing-impl.md", linked_release=rel_release_path))
        _write(os.path.join(eff, "implementation-plan.md"),
               _plan_doc("E-01", linked_spec="spec.md", linked_release=rel_release_path))
        # Defect E: a link that resolves only to a DIRECTORY (the effort folder itself) must not be
        # accepted as a resolved document.
        dir_only_rel = os.path.relpath(eff, tmp).replace(os.sep, "/")
        _write(os.path.join(tmp, "dirlink_holder", "spec.md"),
               _spec_doc("E-02", linked_plan=None, linked_release=dir_only_rel))
        # Defect E: a NON-STRING link value (a list) must be a finding in its own right, never a
        # silently skipped field. The invariant-5 docstring claims this explicitly, and adversarial
        # review found the claim unguarded: reverting to a bare `continue` left the self-test
        # reporting PASS while a list-valued link stopped being reported at all.
        _write(os.path.join(tmp, "listlink_holder", "spec.md"),
               _spec_doc("E-03", linked_plan="[a.md, b.md]", linked_release=rel_release_path))
        specs = [read_doc(os.path.join(eff, "spec.md"), tmp),
                 read_doc(os.path.join(tmp, "dirlink_holder", "spec.md"), tmp),
                 read_doc(os.path.join(tmp, "listlink_holder", "spec.md"), tmp)]
        plans = [read_doc(os.path.join(eff, "implementation-plan.md"), tmp)]
        findings = check_link_resolution(specs + plans, tmp)
        bad = [f for f in findings if "linked-plan" in f and "missing-impl.md" in f]
        dirbad = [f for f in findings if "linked-release" in f and dir_only_rel in f]
        listbad = [f for f in findings if "linked-plan" in f and "is not a single path string" in f]
        stray = [f for f in findings if f not in bad and f not in dirbad and f not in listbad]
        if len(findings) != 3 or not bad or not dirbad or not listbad or stray:
            failures.append("check 5 (link resolution): expected exactly one linked-plan finding, one "
                             "directory-only linked-release finding, one non-string linked-plan finding, "
                             "and none for the repo-root-relative linked-release or the "
                             "directory-relative linked-spec, got %r" % findings)


def _self_test_folder_id_agreement(failures):
    with tempfile.TemporaryDirectory() as tmp:
        rp = _rp(tmp, "06")
        _write(os.path.join(rp, "plan.md"), _release_doc("06", "v6.0.0", ["F-01", "F-02"], 2, 2))
        _write(os.path.join(rp, "F-01_effort", "spec.md"), _spec_doc("F-02"))
        _write(os.path.join(rp, "F-01_effort", "implementation-plan.md"), _plan_doc("F-01"))
        _write(os.path.join(rp, "F-02_effort", "spec.md"), _spec_doc("F-02"))
        _write(os.path.join(rp, "F-02_effort", "implementation-plan.md"), _plan_doc("F-02"))
        specs, plans, _releases, errors = discover(tmp)
        if errors:
            failures.append("check 6 fixture failed to parse: %r" % errors)
            return
        findings = check_folder_id_agreement(tmp, specs, plans)
        if len(findings) != 1 or "spec.md" not in findings[0]:
            failures.append("check 6 (folder/id agreement): expected exactly one F-01 spec.md mismatch, got %r" % findings)


def _self_test_counts(failures):
    with tempfile.TemporaryDirectory() as tmp:
        bad_rp = _rp(tmp, "07")
        _write(os.path.join(bad_rp, "plan.md"), _release_doc("07", "v7.0.0", ["G-99"], 5, 5))
        _write(os.path.join(bad_rp, "G-01_effort", "spec.md"), _spec_doc("G-01"))
        _write(os.path.join(bad_rp, "G-01_effort", "implementation-plan.md"), _plan_doc("G-01"))

        good_rp = _rp(tmp, "07b")
        _write(os.path.join(good_rp, "plan.md"), _release_doc("07b", "v7.1.0", ["H-01"], 1, 1))
        _write(os.path.join(good_rp, "H-01_effort", "spec.md"), _spec_doc("H-01"))
        _write(os.path.join(good_rp, "H-01_effort", "implementation-plan.md"), _plan_doc("H-01"))

        _specs, _plans, releases, errors = discover(tmp)
        if errors:
            failures.append("check 7 fixture failed to parse: %r" % errors)
            return
        findings = check_counts(tmp, releases)
        bad_findings = [f for f in findings if "plan_07_test" in f.replace("\\", "/")]
        good_findings = [f for f in findings if "plan_07b_test" in f.replace("\\", "/")]
        if len(bad_findings) != 3 or good_findings:
            failures.append("check 7 (counts): expected 3 findings on the bad release plan and none on the good "
                             "one, got %r" % findings)


def _self_test_ac_count(failures):
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "spec_bad", "spec.md"), _spec_doc("X-01", ac_lines=2, ac_count=5))
        _write(os.path.join(tmp, "spec_good_colon", "spec.md"), _spec_doc("X-02", ac_lines=2, ac_count=2, ac_form="colon"))
        # Defect D (part 2): the '**AC-N** -' form the template and its examples document must be
        # supported too, or every future spec generated from the template is falsely flagged.
        _write(os.path.join(tmp, "spec_good_bold", "spec.md"), _spec_doc("X-03", ac_lines=3, ac_count=3, ac_form="bold"))
        # Defect E: an AC line quoted inside a fenced code block (documentation example) must not be
        # counted as a real acceptance criterion.
        fenced = _spec_doc("X-04", ac_lines=1, ac_count=1, ac_form="colon")
        fenced += "\n```\n- [ ] AC-99: this is just an example inside a fence, not a real AC\n```\n"
        _write(os.path.join(tmp, "spec_fenced_example", "spec.md"), fenced)

        specs = [read_doc(os.path.join(tmp, sub, "spec.md"), tmp)
                 for sub in ("spec_bad", "spec_good_colon", "spec_good_bold", "spec_fenced_example")]
        findings = check_ac_count(specs)
        bad = [f for f in findings if "spec_bad" in f]
        others = [f for f in findings if "spec_bad" not in f]
        if len(bad) != 1 or others:
            failures.append("check 8 (ac-count accuracy): expected exactly one X-01 finding and none for the "
                             "bold-form, colon-form, or fenced-example specs, got %r" % findings)


def _self_test_ac_status_agreement(failures):
    """Invariant 9's canaries and anti-canaries. The anti-canary set is doing the real work here: the
    two shapes this invariant must NOT flag (a partially-ticked `committed` spec, and a ticked AC
    quoted inside a fence) are the two ways a status/checkbox rule most plausibly turns into a
    false-positive generator, and a rule that false-flags the mid-execution state would be removed
    the first week it fired."""
    with tempfile.TemporaryDirectory() as tmp:
        # Canary 1: fulfilled with an unticked criterion. A spec claiming delivery it never verified.
        _write(os.path.join(tmp, "spec_fulfilled_partial", "spec.md"),
               _spec_doc("Y-01", ac_lines=3, ac_ticked=2, status="fulfilled"))
        # Canary 2: draft with a ticked criterion. Delivery claimed before the contract was agreed.
        _write(os.path.join(tmp, "spec_draft_ticked", "spec.md"),
               _spec_doc("Y-02", ac_lines=3, ac_ticked=1, status="draft"))
        # Canary 3: a status outside the four the invariant knows. Widening the schema enum without
        # widening this invariant must not make it pass silently.
        _write(os.path.join(tmp, "spec_unknown_status", "spec.md"),
               _spec_doc("Y-08", ac_lines=2, ac_ticked=1, status="archived"))

        # Anti-canary: fulfilled, fully ticked. The shape all 8 real fulfilled specs have.
        _write(os.path.join(tmp, "anti_fulfilled_full", "spec.md"),
               _spec_doc("Y-03", ac_lines=3, ac_ticked=3, status="fulfilled"))
        # Anti-canary: draft, none ticked. The shape all 8 real draft specs have.
        _write(os.path.join(tmp, "anti_draft_clean", "spec.md"),
               _spec_doc("Y-04", ac_lines=3, ac_ticked=0, status="draft"))
        # Anti-canary: committed, partially ticked. The mid-execution state the invariant deliberately
        # does not check. Flagging this would break the first effort that ticks a criterion before
        # flipping status, which is precisely what A-02's execution is expected to do.
        _write(os.path.join(tmp, "anti_committed_partial", "spec.md"),
               _spec_doc("Y-05", ac_lines=3, ac_ticked=1, status="committed"))
        # Anti-canary: superseded, partially ticked. A dead end whose ticks assert nothing.
        _write(os.path.join(tmp, "anti_superseded_partial", "spec.md"),
               _spec_doc("Y-06", ac_lines=3, ac_ticked=1, status="superseded"))
        # Anti-canary: a TICKED AC line quoted inside a fence is documentation, not a criterion, so a
        # draft spec that shows one must not be flagged. Invariant 8 proves the fence rule for
        # counting; this fixture proves invariant 9 inherited it rather than reimplementing it.
        fenced = _spec_doc("Y-07", ac_lines=1, ac_ticked=0, status="draft")
        fenced += "\n```\n- [x] AC-99: a ticked example inside a fence, not a real criterion\n```\n"
        _write(os.path.join(tmp, "anti_fenced_ticked", "spec.md"), fenced)

        subs = ("spec_fulfilled_partial", "spec_draft_ticked", "spec_unknown_status",
                "anti_fulfilled_full", "anti_draft_clean", "anti_committed_partial",
                "anti_superseded_partial", "anti_fenced_ticked")
        specs = [read_doc(os.path.join(tmp, sub, "spec.md"), tmp) for sub in subs]
        findings = check_ac_status_agreement(specs)

        canaries = (("spec_fulfilled_partial", "still unticked"),
                    ("spec_draft_ticked", "already ticked"),
                    ("spec_unknown_status", "refusing to skip silently"))
        for canary, fragment in canaries:
            hits = [f for f in findings if canary in f and fragment in f]
            if len(hits) != 1:
                failures.append("check 9 (status/checkbox agreement): expected exactly one %s finding "
                                 "containing %r, got %r" % (canary, fragment, findings))

        noise = [f for f in findings if not any(c in f for c, _ in canaries)]
        if noise:
            failures.append("check 9 (status/checkbox agreement): the fully-ticked fulfilled spec, the "
                             "clean draft, the partially-ticked committed and superseded specs, and the "
                             "fenced ticked example are anti-canaries and must produce zero findings, "
                             "got %r" % noise)


def _self_test_prerelease_tagged_release_plan(failures):
    """Invariant 10's canary, anti-canary, and the baseline-removal proof the task explicitly
    requires: a release plan baselined at one call and NOT baselined at another, same data, so the
    only thing that changes between a passing and a failing run is the baseline argument itself."""
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(_rp(tmp, "80"), "plan.md"), _release_doc("80", "v80.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "81"), "plan.md"), _release_doc("81", "v81.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "82"), "plan.md"), _release_doc("82", "v82.0.0", [], 0, 0))
        complete_doc = _release_doc("83", "v83.0.0", [], 0, 0).replace("status: in-progress", "status: complete")
        _write(os.path.join(_rp(tmp, "83"), "plan.md"), complete_doc)
        _specs, _plans, releases, errors = discover(tmp)
        if errors:
            failures.append("check 10 fixture failed to parse: %r" % errors)
            return

        # v80.0.0 and v81.0.0 are tagged; v82.0.0 is not; v83.0.0 is tagged but its plan is complete.
        tags = {"v80.0.0", "v81.0.0", "v83.0.0"}

        # Canary: plan_80 is pre-release, tagged, and not in an empty baseline.
        findings = check_released_but_prerelease_release_plans(releases, tags, baseline=set())
        hits80 = [f for f in findings if "plan_80_test" in f.replace("\\", "/")]
        hits81 = [f for f in findings if "plan_81_test" in f.replace("\\", "/")]
        hits82 = [f for f in findings if "plan_82_test" in f.replace("\\", "/")]
        hits83 = [f for f in findings if "plan_83_test" in f.replace("\\", "/")]
        if not hits80:
            failures.append("check 10 (prerelease tagged release plan): expected a finding for "
                            "plan_80 against an empty baseline, got %r" % findings)
        if not hits81:
            failures.append("check 10: expected a finding for plan_81 against an empty baseline, "
                            "got %r" % findings)
        if hits82:
            failures.append("check 10: plan_82's target-version is not tagged and must never be "
                            "flagged (anti-canary), got %r" % findings)
        if hits83:
            failures.append("check 10: a 'complete' release plan must never be flagged even when "
                            "its target-version is tagged (anti-canary), got %r" % findings)

        # Anti-canary AND the baseline-removal proof: baselining plan_81 alone removes exactly its
        # finding. Removing that same entry (the empty-baseline call above) is what turns it back
        # on, so this one pair of calls proves both directions with the same fixture data.
        findings_baselined = check_released_but_prerelease_release_plans(
            releases, tags, baseline={("81", "v81.0.0")})
        hits80b = [f for f in findings_baselined if "plan_80_test" in f.replace("\\", "/")]
        hits81b = [f for f in findings_baselined if "plan_81_test" in f.replace("\\", "/")]
        if not hits80b:
            failures.append("check 10: plan_80 is still not in THIS baseline and must still be a "
                            "finding, got %r" % findings_baselined)
        if hits81b:
            failures.append("check 10: plan_81 IS in this baseline and must produce zero findings; "
                            "removing it from the baseline (proved above) is what turns this finding "
                            "back on, got %r" % findings_baselined)

        # The NOTE-printing helper only speaks for plans that both match the shape AND are
        # baselined; plan_80 must never get a note from a baseline it is not in.
        notes = baselined_prerelease_release_plan_notes(releases, tags, baseline={("81", "v81.0.0")})
        note81 = [n for n in notes if "plan_81_test" in n.replace("\\", "/")]
        note80 = [n for n in notes if "plan_80_test" in n.replace("\\", "/")]
        if len(note81) != 1:
            failures.append("check 10: expected exactly one baselined-known note for plan_81, got %r" % notes)
        if note80:
            failures.append("check 10: plan_80 is not in this baseline and must get no note, got %r" % note80)


def _self_test_releases_in_symmetry_and_links(failures):
    # Defect E: release plans (plan.md) must not be silently exempted from invariants 1 and 5 the way
    # they used to be.
    with tempfile.TemporaryDirectory() as tmp:
        rp = _rp(tmp, "50")
        _write(os.path.join(rp, "plan.md"),
               _release_doc("50", "v50.0.0", [], 0, 0, superseded_by="ZZ-99", linked_spec="does-not-exist.md"))
        _specs, _plans, releases, errors = discover(tmp)
        if errors:
            failures.append("releases-in-invariants fixture failed to parse: %r" % errors)
            return
        sym_findings = check_supersession_symmetry([], [], releases)
        if len(sym_findings) != 1 or "ZZ-99" not in sym_findings[0]:
            failures.append("invariant 1 must include release plans: expected exactly one ZZ-99 finding "
                             "on the release plan, got %r" % sym_findings)
        link_findings = check_link_resolution(releases, tmp)
        if len(link_findings) != 1 or "does-not-exist.md" not in link_findings[0]:
            failures.append("invariant 5 must include release plans: expected exactly one dangling "
                             "linked-spec finding on the release plan, got %r" % link_findings)


def _self_test_wiring(failures):
    """Defect B: drive the checks through run_all_checks(), the same top-level entry point the real run uses, over one fixture tree seeded with one violation of every invariant, and confirm every invariant is represented in the findings, by a message fragment unique to that check's own wording (not just a shared seeded id, which would let two checks alias each other and hide either one's removal). This proves the PIPELINE, not just the individual check functions: a check silently removed from run_all_checks() would leave its marker missing here even though that check's own dedicated self-test above still passes in isolation.

    To prove this test actually does that (not just that it passes), comment out one line inside run_all_checks(), rerun this file with --self-test-only, and confirm self-test now fails naming the missing marker; then restore the line. Do this once per invariant (ten cycles) before trusting this fixture; see the delivery report for the transcript of all eight, commit b6c173a's message for the ninth, and this effort's report for the tenth."""
    with tempfile.TemporaryDirectory() as tmp:
        # Every fixture must sit under docs/internal/release-plans/, the tree discover() actually
        # walks: a spec or plan written directly under tmp is invisible to it.
        base = os.path.join(tmp, "docs", "internal", "release-plans")

        # Invariant 1: one-directional supersedes (the real historical shape).
        _write(os.path.join(base, "WA-01_new", "spec.md"), _spec_doc("WA-01", supersedes="WA-02"))
        _write(os.path.join(base, "WA-01_new", "implementation-plan.md"), _plan_doc("WA-01"))
        _write(os.path.join(base, "WA-02_old", "spec.md"), _spec_doc("WA-02"))
        _write(os.path.join(base, "WA-02_old", "implementation-plan.md"), _plan_doc("WA-02"))

        # Invariant 2: two release plans share a target-version but have distinct sequences.
        _write(os.path.join(_rp(tmp, "40"), "plan.md"), _release_doc("40", "v90.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "41"), "plan.md"), _release_doc("41", "v90.0.0", [], 0, 0))

        # Invariant 3: two OTHER release plans share a sequence but have distinct target-versions.
        _write(os.path.join(_rp(tmp, "70"), "plan.md"), _release_doc("70", "v70.0.0", [], 0, 0))
        _write(os.path.join(_rp(tmp, "71"), "plan.md"), _release_doc("70", "v71.0.0", [], 0, 0))

        # Invariant 4: a spec targeting an already-tagged release, still draft. No linked-plan, so it
        # cannot also alias invariant 5's marker.
        _write(os.path.join(base, "WD-04_shipped", "spec.md"),
               _spec_doc("WD-04", status="draft", target_release="v99.0.0", linked_plan=None))

        # Invariant 5: a dangling linked-plan.
        _write(os.path.join(base, "WE-05_badlink", "spec.md"),
               _spec_doc("WE-05", linked_plan="does-not-exist-WE-05.md"))

        # Invariant 6: folder claims WF-06, spec.md carries a different id. Counts/includes for this
        # release plan are declared correctly (1/1/[WF-06]) so invariant 7 stays isolated to plan_43.
        _write(os.path.join(_rp(tmp, "42"), "plan.md"), _release_doc("42", "v42.0.0", ["WF-06"], 1, 1))
        _write(os.path.join(_rp(tmp, "42"), "WF-06_effort", "spec.md"), _spec_doc("WF-06X"))
        _write(os.path.join(_rp(tmp, "42"), "WF-06_effort", "implementation-plan.md"), _plan_doc("WF-06"))

        # Invariant 7: declared counts and includes both disagree with what's actually present.
        _write(os.path.join(_rp(tmp, "43"), "plan.md"), _release_doc("43", "v43.0.0", ["WG-99"], 9, 9))
        _write(os.path.join(_rp(tmp, "43"), "WG-07_effort", "spec.md"), _spec_doc("WG-07"))
        _write(os.path.join(_rp(tmp, "43"), "WG-07_effort", "implementation-plan.md"), _plan_doc("WG-07"))

        # Invariant 8: ac-count disagrees with the actual body. No linked-plan either.
        _write(os.path.join(base, "WH-08_acmismatch", "spec.md"),
               _spec_doc("WH-08", ac_lines=2, ac_count=99, linked_plan=None))

        # Invariant 9: fulfilled with one criterion still unticked. No linked-plan and no
        # target-release, so it cannot alias invariant 4's or 5's marker, and ac-count is left to
        # match the body so invariant 8 stays isolated to WH-08.
        _write(os.path.join(base, "WI-09_statusdrift", "spec.md"),
               _spec_doc("WI-09", ac_lines=2, ac_ticked=1, status="fulfilled", linked_plan=None))

        # Invariant 10: a release plan, still pre-release, whose target-version is already tagged
        # and is not named in the default (module-level) baseline. Sequence '72' and target-version
        # 'v72.0.0' are chosen to collide with nothing else in this fixture AND nothing in
        # BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS, since this call uses that module default.
        _write(os.path.join(_rp(tmp, "72"), "plan.md"), _release_doc("72", "v72.0.0", [], 0, 0))

        specs, plans, releases, errors = discover(tmp)
        if errors:
            failures.append("wiring fixture failed to parse: %r" % errors)
            return
        findings = run_all_checks(tmp, specs, plans, releases, tags={"v99.0.0", "v72.0.0"})

        markers = [
            ("1 (supersession symmetry)", "WA-02"),
            ("2 (target-version uniqueness)", "target-version 'v90.0.0'"),
            ("3 (sequence uniqueness)", "sequence '70'"),
            ("4 (released but unfulfilled)", "WD-04"),
            ("5 (link resolution)", "does-not-exist-WE-05.md"),
            ("6 (folder/id agreement)", "folder name claims id WF-06"),
            ("7 (counts)", "WG-99"),
            ("8 (ac-count)", "WH-08"),
            ("9 (status/checkbox agreement)", "acceptance criteria are still unticked"),
            ("10 (released-but-prerelease release plan)", "v72.0.0"),
        ]
        for label, marker in markers:
            if not any(marker in f for f in findings):
                failures.append("wiring (run_all_checks): expected a finding mentioning %r for invariant %s, "
                                 "found none; a check may be missing from run_all_checks(). Full findings: %r"
                                 % (marker, label, findings))


def decide_tags_action(raw_tags, allow_no_tags):
    """Defect A's decision logic, factored out as a pure function (no I/O, no sys.exit) so self_test() can drive all three branches directly without touching git or the filesystem. Returns (action, tags): action is 'ok' (proceed with raw_tags as given), 'skip-note' (raw_tags was empty and --allow-no-tags was passed: proceed with an empty set, the caller must print a visible note), or 'broken' (raw_tags was empty and --allow-no-tags was NOT passed: the caller must refuse to proceed, naming the likely cause and the remedy)."""
    if raw_tags:
        return ("ok", raw_tags)
    if allow_no_tags:
        return ("skip-note", raw_tags)
    return ("broken", raw_tags)


def _self_test_tag_gate(failures):
    action, tags = decide_tags_action(set(), allow_no_tags=False)
    if action != "broken":
        failures.append("invariant-4/10 tag gate: empty tags without --allow-no-tags must decide 'broken', got %r" % (action,))

    action, tags = decide_tags_action(set(), allow_no_tags=True)
    if action != "skip-note" or tags != set():
        failures.append("invariant-4/10 tag gate: empty tags with --allow-no-tags must decide 'skip-note' with an "
                         "empty tag set, got %r" % ((action, tags),))

    action, tags = decide_tags_action({"v1.0.0", "v2.0.0"}, allow_no_tags=False)
    if action != "ok" or tags != {"v1.0.0", "v2.0.0"}:
        failures.append("invariant-4/10 tag gate: non-empty tags must decide 'ok' and pass the tags through "
                         "unchanged, got %r" % ((action, tags),))

    action, tags = decide_tags_action({"v1.0.0"}, allow_no_tags=True)
    if action != "ok":
        failures.append("invariant-4/10 tag gate: non-empty tags must decide 'ok' regardless of "
                         "--allow-no-tags, got %r" % (action,))


def self_test():
    failures = []
    _self_test_parser(failures)
    _self_test_parser_comments_and_block_sequence(failures)
    _self_test_supersession(failures)
    _self_test_target_version_uniqueness(failures)
    _self_test_sequence_uniqueness(failures)
    _self_test_released_but_unfulfilled(failures)
    _self_test_link_resolution(failures)
    _self_test_folder_id_agreement(failures)
    _self_test_counts(failures)
    _self_test_ac_count(failures)
    _self_test_ac_status_agreement(failures)
    _self_test_prerelease_tagged_release_plan(failures)
    _self_test_releases_in_symmetry_and_links(failures)
    _self_test_wiring(failures)
    _self_test_tag_gate(failures)
    if failures:
        print("BROKEN: gate self-test failed, the detector is not trustworthy.", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        return False
    print("gate self-test: PASS (10 invariants each proved against a canary and an anti-canary, "
          "invariant 10's dated baseline additionally proved removable, the run_all_checks() wiring "
          "proved against one fixture seeding all ten, and the invariant-4/10 tag-availability gate "
          "proved on all three branches)")
    return True


def _run_git_tag_list(repo_root):
    """Actually invoke `git tag -l`. Kept separate from decide_tags_action() so self_test() can drive the decision logic without touching git or requiring a real repository."""
    try:
        proc = subprocess.run(["git", "tag", "-l"], cwd=repo_root, capture_output=True,
                              text=True, encoding="utf-8")
    except OSError as exc:
        print("BROKEN: could not invoke git: %s" % exc, file=sys.stderr)
        sys.exit(2)
    if proc.returncode != 0:
        print("BROKEN: git tag -l failed: %s" % proc.stderr.strip(), file=sys.stderr)
        sys.exit(2)
    return {t.strip() for t in proc.stdout.split("\n") if t.strip()}


def get_git_tags(repo_root, allow_no_tags):
    raw = _run_git_tag_list(repo_root)
    action, tags = decide_tags_action(raw, allow_no_tags)
    if action == "broken":
        print("BROKEN: git tag -l returned no tags, so invariants 4 (released-but-unfulfilled) and "
              "10 (released-but-prerelease release plan) cannot run and would silently prove "
              "nothing if this were allowed to continue as CLEAN.", file=sys.stderr)
        print("  Likely cause: a shallow or tag-less checkout. actions/checkout does not fetch tags "
              "unless fetch-tags: true is set, or a later 'git fetch --tags' step runs.", file=sys.stderr)
        print("  Remedy: fetch tags before running this gate (fetch-tags: true on actions/checkout, or "
              "an explicit 'git fetch --tags'), OR if this repository has genuinely never tagged a "
              "release, pass --allow-no-tags to skip invariants 4 and 10 explicitly.", file=sys.stderr)
        sys.exit(2)
    if action == "skip-note":
        print("NOTE: git tag -l returned no tags; --allow-no-tags was passed, so invariants 4 "
              "(released-but-unfulfilled) and 10 (released-but-prerelease release plan) are "
              "skipped for this run.", file=sys.stderr)
    return tags


def _run(args):
    if not self_test():
        sys.exit(2)

    if args.self_test_only:
        sys.exit(0)

    repo_root = args.repo_root
    specs, plans, releases, errors = discover(repo_root)
    if errors:
        print("BROKEN: could not parse the frontmatter of %d document(s):" % len(errors), file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(2)

    if not specs and not plans and not releases:
        print("BROKEN: found no spec.md, implementation-plan.md or plan.md under %s"
              % os.path.join(repo_root, RELEASE_PLANS_REL), file=sys.stderr)
        sys.exit(2)

    tags = get_git_tags(repo_root, args.allow_no_tags)
    for n in baselined_prerelease_release_plan_notes(releases, tags):
        print("NOTE: " + n, file=sys.stderr)
    findings = run_all_checks(repo_root, specs, plans, releases, tags)

    if findings:
        for f in findings:
            print(f)
        print("FINDINGS: %d cross-file lifecycle invariant violation(s)." % len(findings), file=sys.stderr)
        sys.exit(1)

    print("CLEAN: canary proved, %d specs / %d implementation plans / %d release plans checked, "
          "no cross-file lifecycle invariant violated." % (len(specs), len(plans), len(releases)))
    sys.exit(0)


def main():
    """Top-level entry point. No unexpected exception may ever surface as exit 1: everything below that is not already a deliberate sys.exit() of its own is caught here and reported as BROKEN, exit 2, instead of falling through to Python's default uncaught-exception behavior (a traceback and exit 1, indistinguishable from a real finding)."""
    ap = argparse.ArgumentParser(
        description="Canary-verified cross-file lifecycle gate for docs/internal/release-plans/.")
    ap.add_argument("--repo-root", default=os.getcwd(),
                    help="repository root to scan (default: cwd)")
    ap.add_argument("--self-test-only", action="store_true",
                    help="prove the detector and exit, scanning nothing")
    ap.add_argument("--allow-no-tags", action="store_true",
                    help="proceed when 'git tag -l' returns no tags at all, skipping invariants 4 "
                         "(released-but-unfulfilled) and 10 (released-but-prerelease release plan) "
                         "with a visible note; only for a repository that has genuinely never "
                         "tagged a release. Without this flag, an empty tag list is treated as "
                         "BROKEN, not CLEAN, because a starved CI checkout (actions/checkout "
                         "without fetch-tags: true) produces the same empty list.")
    args = ap.parse_args()

    try:
        _run(args)
    except SystemExit:
        raise
    except Exception as exc:
        print("BROKEN: an unanticipated exception reached the top level: %s: %s"
              % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
