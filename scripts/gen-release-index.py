#!/usr/bin/env python3
"""
Generates docs/internal/release-plans/INDEX.md, the cross-release effort index. Nothing else in this repository shows every effort across every release at a glance: the release plan (plan.md) aggregates only within its own release, so a maintainer wanting the whole picture has to open five folders and twenty spec files by hand. This script derives that picture from frontmatter alone, on every run, so the index can never carry a fact that disk does not also carry.

EXIT-CODE CONTRACT
------------------
0  CLEAN    self-test passed AND (generate mode: the file was written; or --check mode: the committed INDEX.md matches what generation produces right now)
1  FINDINGS self-test passed AND --check found the committed INDEX.md out of date, including the case where INDEX.md does not exist yet (a missing index is out of date, not unreadable input)
2  BROKEN   the self-test could not prove the generator trustworthy, an input file could not be read or parsed, a documented naming or content rule was actually violated (a would-be release or effort folder with the wrong name but real content inside it, an empty required field, an unrecognised boolean spelling), an effort id's series letter is not in the legend map, or any other exception the generator did not anticipate. The top-level dispatcher converts every unanticipated exception to BROKEN rather than let it surface as a bare traceback, which the OS reports as exit 1 and which this contract reserves for "the detector proved itself and found a real problem."

NEVER INTERPRET 2 AS CLEAN. See scripts/check-dashes.py and skills/plab-wrap-session/scripts/path-citation-check.py for the same contract applied elsewhere in this repository.

WHY AN UNKNOWN SERIES LETTER IS EXIT 2, NOT A BLANK CELL
---------------------------------------------------------
The series legend (D, W, C, CI, A, H) is documented nowhere machine-readable except this script. If an effort folder appears with a letter the legend does not cover, silently rendering a blank meaning cell is exactly how an undocumented convention survives unnoticed: the table still looks complete, so nobody goes looking for what the letter means. The generator refuses to render that cell at all. This is proven by a canary that walks a full fixture tree containing an unmapped letter through build_model() itself, not only through the leaf function that owns the map, because the failure this guards against lives in the wiring between the two: a map that is correct but never consulted would pass a leaf-only test and still ship a blank cell.

WHY A NON-EFFORT SIBLING DIRECTORY IS IGNORED, NOT BROKEN
------------------------------------------------------------
A release folder can legitimately hold subdirectories that are not efforts: a documented sibling skill may drop working material next to the per-effort folders it manages. Treating every subdirectory as an effort and then failing on the missing spec.md it does not have makes the generator, and any --check gate built on it, brittle about a normal repository state. An effort is instead recognised by its documented name shape, a series letter and number followed by an underscore and a slug, e.g. "D-03_bidirectional-drift-check". A directory that does not match that shape is skipped, UNLESS it contains a spec.md of its own: that is unambiguous evidence someone meant it as an effort folder and misnamed it, so it fails loud rather than silently dropping a real effort from the index. The identical policy applies one level up, in discover_release_dirs(), using plan.md as the equivalent tell for a release folder.

WHY A MISSING IMPLEMENTATION PLAN IS NOT AN ERROR
------------------------------------------------------
A spec is routinely written before its implementation plan; that gap is a normal, documented intermediate state of the work, not a corrupt input. Hard-requiring implementation-plan.md to exist turned that ordinary state into exit 2 BROKEN, which blocks a release for a situation that is not an error at all. When the file is absent, the effort's row still renders, with its plan-status cell carrying an explicit marker (PLAN_STATUS_NOT_WRITTEN below) rather than a value read from a file that was never written. When the file IS present, its status field is still required and still must be non-empty: presence of the file is what makes "no plan yet" cross over into "a plan exists, and it must say what its status is."

WHY _unassigned/ IS ITS OWN GROUP IN THE INDEX
--------------------------------------------------
docs/internal/release-plans/_unassigned/ is the documented default home a new spec lands in before it is promoted into a release (see skills/plab-spec/SKILL.md and skills/plab-release-plan/references/promote-demote.md). It holds effort folders directly, the same "<id>_<slug>" shape as inside a release, but with no plan.md above them and so no release-level target-version to source from: an unassigned effort's Target Version cell reads "-", never the spec's own target-release field, for the same reason plan.md and not spec.md is the source of truth for that column elsewhere in this file (see below). _unassigned/ does not exist on disk until the first spec is written into it; a generator that treated that absence as an error would fail on every fresh clone of this repository, so absence is handled as the normal empty case, not a failure.

WHY THE INDEX CARRIES NO GENERATION DATE
-----------------------------------------
The precedent in docs/status-skills.md stamps an "As of:" date because a human maintains that file by hand and the date records when they last checked it against reality. This file is not maintained by hand; it is a pure function of the frontmatter under docs/internal/release-plans/. Adding today's date would make --check report FINDINGS every single day even when not one byte of source frontmatter changed, which defeats the freshness gate rather than serving it: a gate that cries wolf daily trains its reader to ignore it. Freshness here means "matches current frontmatter", not "was regenerated recently", and git history already answers the second question for whoever wants it.

WHY --check NORMALIZES LINE ENDINGS BEFORE COMPARING
------------------------------------------------------
This repository has core.autocrlf=true and no .gitattributes. A file committed with LF checks out as CRLF on this maintainer's Windows machine and stays LF on ubuntu-latest. That is a platform artifact of the checkout, not a content change, and comparing raw bytes would make --check report FINDINGS purely because of which OS last checked the file out, which is the same "detector flags the wrong thing" failure mode the dash-check docstring describes for a different cause. --check reads the committed file with newline="" (so no translation happens twice) and normalizes CRLF to LF on that side only before comparing against the freshly generated text, which this script always writes with newline="\n" so its own output is LF exactly once. A self-test canary proves that content differing only by line ending compares as current.

TARGET VERSION COMES FROM plan.md, NOT FROM EACH SPEC
--------------------------------------------------------
Every spec.md in this repository also carries its own target-release field, and today it is identical to its release's plan.md target-version in all sixteen cases (verified by hand before writing this script). The Target Version column is sourced from plan.md's target-version because that is a release-level fact stated once, in the file whose job is to state it; a spec's target-release is that same fact copied onto sixteen other files, and a generator should read a fact from where it is authoritative, not from every place it happens to also appear. This is also why an unassigned effort's Target Version cell is "-" rather than its spec's target-release: there is no plan.md yet to be the authoritative source.

PARSING
-------
Frontmatter in this repository is flat: "key: value" lines between a pair of "---" fences, plus occasional quoted strings and "[a, b]" inline lists. parse_frontmatter() below is a small purpose-built line parser for exactly that shape. It is not a YAML parser and must never grow into one; this repository has deliberately never had a package.json or any dependency manifest, and stdlib-only is a project-wide constraint, not a preference for this script.
"""

import contextlib
import io
import os
import re
import sys
import tempfile
import traceback

SCRIPT_PATH = os.path.abspath(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_PATH))
RELEASE_PLANS_DIR_NAME = os.path.join("docs", "internal", "release-plans")
REGEN_COMMAND = "python scripts/gen-release-index.py"

RELEASE_DIR_RE = re.compile(r"^plan_(\d+)_")
EFFORT_ID_RE = re.compile(r"^([A-Za-z]+)-(\d+)$")
EFFORT_DIR_RE = re.compile(r"^[A-Za-z]+-\d+_.+$")
FRONTMATTER_LINE_RE = re.compile(r"^([A-Za-z0-9_-]+):\s?(.*)$")

UNASSIGNED_DIR_NAME = "_unassigned"
PLAN_STATUS_NOT_WRITTEN = "(no implementation plan yet)"

TRUE_VALUES = frozenset(["true", "yes", "y", "1"])
FALSE_VALUES = frozenset(["false", "no", "n", "0"])

SERIES_LEGEND = [
    ("D", "defect in the wrap and continue pair"),
    ("W", "wrap-session roadmap item"),
    ("C", "continue-session roadmap item"),
    ("CI", "continuous integration"),
    ("A", "ai-review roadmap item"),
    ("H", "hygiene and repo-wide"),
    ("AU", "audit-skill roadmap item"),
    ("WD", "resolve-open-items roadmap item"),
]
SERIES_LEGEND_MAP = dict(SERIES_LEGEND)


class IndexBuildError(Exception):
    """Raised for any problem that makes the generated index untrustworthy.

    Every raise site below is a case that either the original task or the later defect fixes single out by name: an unreadable or undecodable input, a frontmatter field missing or empty where the schema requires it, an effort id whose series letter is not in the legend, or a folder whose contents (spec.md, or plan.md) prove it was meant as an effort or release but whose name does not match the documented shape. All of these collapse to exit 2 (BROKEN) at the top level, because none of them is "nothing found"; all of them are "could not prove the answer."
    """


class UnknownSeriesLetterError(IndexBuildError):
    pass


def parse_frontmatter(text):
    """Parse the flat "key: value" YAML frontmatter fence at the top of text.

    Returns a dict of raw strings, except a value written as "[a, b]" which is returned as a list of strings. Quoted scalar values have their surrounding quotes stripped. This is deliberately not a YAML parser; see the module docstring for why that is a constraint, not a gap.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise IndexBuildError("frontmatter does not open with a '---' fence")
    fields = {}
    i = 1
    while i < len(lines) and lines[i].strip() != "---":
        line = lines[i]
        i += 1
        if not line.strip():
            continue
        m = FRONTMATTER_LINE_RE.match(line)
        if not m:
            raise IndexBuildError("unparseable frontmatter line: %r" % line)
        key, raw_value = m.group(1), m.group(2).strip()
        fields[key] = _parse_scalar_or_list(raw_value)
    else:
        if i >= len(lines):
            raise IndexBuildError("frontmatter never closes with a '---' fence")
    return fields


def _parse_scalar_or_list(raw_value):
    if raw_value.startswith("[") and raw_value.endswith("]"):
        inner = raw_value[1:-1].strip()
        if not inner:
            return []
        return [_strip_quotes(item.strip()) for item in inner.split(",")]
    return _strip_quotes(raw_value)


def _strip_quotes(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def read_frontmatter_file(path):
    """Read and parse the frontmatter of one file.

    Both an OS-level read failure (missing file, permission denied) and a decode failure (a file that is not valid UTF-8) land here as IndexBuildError, not as a raw exception. Letting a UnicodeDecodeError escape uncaught would surface as an uninterpreted traceback and exit 1, which under this script's contract means "stale, regenerate" when the true state is "could not even read the input" (exit 2, BROKEN).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise IndexBuildError("could not read %s: %s" % (path, exc))
    except UnicodeDecodeError as exc:
        raise IndexBuildError("could not decode %s as UTF-8: %s" % (path, exc))
    return parse_frontmatter(text)


def require_field(fields, key, source_path):
    """Return fields[key], failing loud if the key is absent OR its value is empty.

    Checking only for key presence let a frontmatter line like "status: " parse successfully and then render as a silently blank table cell while the run still reported CLEAN. An index that looks complete while quietly hiding an unset fact is the same failure mode the series-legend gate exists to prevent for a different field.
    """
    if key not in fields:
        raise IndexBuildError(
            "%s is missing required frontmatter field %r" % (source_path, key))
    value = fields[key]
    is_empty = (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, list) and not value)
    )
    if is_empty:
        raise IndexBuildError(
            "%s has an empty value for required frontmatter field %r" % (source_path, key))
    return value


def parse_bool_field(raw_value, key, source_path):
    """Normalise a frontmatter boolean-ish value, failing loud on anything unrecognised.

    Comparing the raw string only against the literal "true" let any other true spelling ("yes", "Yes", "1") silently render as No, which is a wrong answer that still looks like a clean, confident cell. Recognised spellings are normalised case- and whitespace-insensitively; anything else raises rather than defaulting to False, because a default-to-No here would hide exactly the kind of typo this check exists to catch.
    """
    normalized = str(raw_value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise IndexBuildError(
        "%s has an unrecognised value %r for boolean field %r (expected one of %s or %s)"
        % (source_path, raw_value, key, sorted(TRUE_VALUES), sorted(FALSE_VALUES)))


def series_letter(effort_id):
    m = EFFORT_ID_RE.match(effort_id)
    if not m:
        raise IndexBuildError(
            "effort id %r does not match the <letters>-<digits> format" % effort_id)
    return m.group(1)


def series_meaning(letter):
    if letter not in SERIES_LEGEND_MAP:
        raise UnknownSeriesLetterError(
            "series letter %r has no entry in the legend map (%s). "
            "Add it to SERIES_LEGEND in this script rather than let the "
            "cell render blank." % (letter, ", ".join(SERIES_LEGEND_MAP)))
    return SERIES_LEGEND_MAP[letter]


def handle_from_slug(effort_dir_name):
    """Derive the human-readable handle from an effort folder name.

    Folder names are "<id>_<slug>", e.g. "D-03_bidirectional-drift-check". The handle is the slug with hyphens converted to spaces, exactly as instructed: "bidirectional drift check".
    """
    if "_" not in effort_dir_name:
        raise IndexBuildError(
            "effort folder %r does not contain the expected id_slug separator"
            % effort_dir_name)
    _id_part, slug = effort_dir_name.split("_", 1)
    return slug.replace("-", " ")


def discover_release_dirs(release_plans_dir):
    """Return [(sequence_int, dir_name, dir_path), ...] sorted by sequence.

    A top-level entry that is not a directory is skipped outright: docs/internal/release-plans/ also holds README.md and release-checklist.yaml. _unassigned/, the documented holding area for specs not yet placed in a release, is recognised by name and skipped here too; build_model() processes it separately as its own group rather than as a release.

    Any other directory whose name does not match plan_<digits>_<slug> is skipped UNLESS it contains a plan.md of its own. A plan.md is unambiguous evidence the directory was meant as a release folder; silently dropping it, and every effort inside it, is exactly how --check could report CLEAN while a whole release's worth of efforts went missing from the index. That directory fails loud instead, the same policy discover_effort_dirs() applies one level down using spec.md as its tell.
    """
    try:
        entries = sorted(os.listdir(release_plans_dir))
    except OSError as exc:
        raise IndexBuildError(
            "could not list %s: %s" % (release_plans_dir, exc))
    releases = []
    for name in entries:
        path = os.path.join(release_plans_dir, name)
        if not os.path.isdir(path):
            continue
        if name == UNASSIGNED_DIR_NAME:
            continue
        m = RELEASE_DIR_RE.match(name)
        if not m:
            if os.path.isfile(os.path.join(path, "plan.md")):
                raise IndexBuildError(
                    "%s contains plan.md but its folder name %r does not match "
                    "the required plan_<digits>_<slug> shape; rename it or fix "
                    "this generator's pattern rather than let it, and every "
                    "effort inside it, be silently dropped from the index"
                    % (path, name))
            continue
        releases.append((int(m.group(1)), name, path))
    releases.sort(key=lambda r: r[0])
    return releases


def discover_effort_dirs(container_dir_path):
    """Return sorted effort folder names directly under one container directory.

    The container is either a release folder or _unassigned/; the rule is the same either way. An entry is an effort only if its name matches the documented shape "<letters>-<digits>_<slug>", e.g. "D-03_bidirectional-drift-check". A subdirectory that does not match this shape is not automatically a generator bug: it may be working material a sibling skill placed there, or an unrelated local folder, and that is now a normal state of this repository rather than an error.

    The one case that still fails loud is a non-matching directory that itself contains a spec.md: that is unambiguous evidence someone meant it as an effort folder and misnamed it, so silently skipping it would let a real effort quietly vanish from the index while --check kept reporting CLEAN. See discover_release_dirs() for the identical policy one level up, using plan.md as its tell.
    """
    try:
        entries = sorted(os.listdir(container_dir_path))
    except OSError as exc:
        raise IndexBuildError(
            "could not list %s: %s" % (container_dir_path, exc))
    names = []
    for name in entries:
        path = os.path.join(container_dir_path, name)
        if not os.path.isdir(path):
            continue
        if EFFORT_DIR_RE.match(name):
            names.append(name)
            continue
        if os.path.isfile(os.path.join(path, "spec.md")):
            raise IndexBuildError(
                "%s contains spec.md but its folder name %r does not match "
                "the required <letters>-<digits>_<slug> shape; rename it or "
                "fix this generator's pattern rather than let it be silently "
                "dropped from the index" % (path, name))
    return names


def build_release(seq, dir_name, dir_path):
    plan_path = os.path.join(dir_path, "plan.md")
    fields = read_frontmatter_file(plan_path)
    return {
        "sequence": seq,
        "dir_name": dir_name,
        "dir_path": dir_path,
        "target_version": require_field(fields, "target-version", plan_path),
        "theme": require_field(fields, "theme", plan_path),
    }


def build_effort(release, effort_dir_name):
    """Build one effort row from its spec.md, and its implementation-plan.md if present.

    implementation-plan.md is intentionally NOT required: a spec written before its plan is a normal, documented intermediate state (see /plab-spec), not a corrupt input. When the file is missing, plan_status carries the explicit PLAN_STATUS_NOT_WRITTEN marker instead of a value read from a file that does not exist. When the file IS present, its status field is still required and still must be non-empty, via require_field.
    """
    effort_dir_path = os.path.join(release["dir_path"], effort_dir_name)
    spec_path = os.path.join(effort_dir_path, "spec.md")
    plan_path = os.path.join(effort_dir_path, "implementation-plan.md")

    spec_fields = read_frontmatter_file(spec_path)

    effort_id = require_field(spec_fields, "id", spec_path)
    letter = series_letter(effort_id)
    meaning = series_meaning(letter)  # raises UnknownSeriesLetterError, uncaught here on purpose

    requires_review_raw = require_field(
        spec_fields, "requires-human-review", spec_path)
    requires_review = parse_bool_field(
        requires_review_raw, "requires-human-review", spec_path)

    if os.path.isfile(plan_path):
        plan_fields = read_frontmatter_file(plan_path)
        plan_status = require_field(plan_fields, "status", plan_path)
    else:
        plan_status = PLAN_STATUS_NOT_WRITTEN

    return {
        "id": effort_id,
        "handle": handle_from_slug(effort_dir_name),
        "series_letter": letter,
        "series_meaning": meaning,
        "spec_status": require_field(spec_fields, "status", spec_path),
        "plan_status": plan_status,
        "priority": require_field(spec_fields, "priority", spec_path),
        "requires_review": requires_review,
        "release_dir_name": release["dir_name"],
        "target_version": release["target_version"],
        "spec_rel_path": _posix_join(release["dir_name"], effort_dir_name, "spec.md"),
    }


def _posix_join(*parts):
    return "/".join(parts)


def build_model(release_plans_dir):
    """Walk every release, then every effort inside it, then _unassigned/, and return (releases, efforts, unassigned_group).

    efforts is the flat list across every release AND _unassigned/, in that order, so len(efforts) is always the true total the rendered header claims. unassigned_group is a dict shaped like a release ("dir_name", "dir_path", "efforts") but with target_version fixed at None, since there is no plan.md to source that fact from.

    Every IndexBuildError raised anywhere below (missing file, missing or empty field, malformed id, unmapped series letter, a misnamed folder that contains real content) propagates uncaught to the caller, which is exactly the fail-loud behaviour this script requires: a generator that could not prove one effort's data must not silently render the rest as if nothing were wrong.
    """
    releases = []
    efforts = []
    for seq, dir_name, dir_path in discover_release_dirs(release_plans_dir):
        release = build_release(seq, dir_name, dir_path)
        release["efforts"] = []
        for effort_dir_name in discover_effort_dirs(dir_path):
            effort = build_effort(release, effort_dir_name)
            release["efforts"].append(effort)
            efforts.append(effort)
        releases.append(release)

    unassigned_dir_path = os.path.join(release_plans_dir, UNASSIGNED_DIR_NAME)
    unassigned_group = {
        "dir_name": UNASSIGNED_DIR_NAME,
        "dir_path": unassigned_dir_path,
        "target_version": None,
        "efforts": [],
    }
    if os.path.isdir(unassigned_dir_path):
        for effort_dir_name in discover_effort_dirs(unassigned_dir_path):
            effort = build_effort(unassigned_group, effort_dir_name)
            unassigned_group["efforts"].append(effort)
            efforts.append(effort)
    # else: _unassigned/ has never been created on this checkout (no
    # /plab-spec run without --target-release has happened yet). That is
    # the normal starting state, not an error.

    return releases, efforts, unassigned_group


def _status_counts_cell(items, key):
    counts = {}
    for item in items:
        v = item[key]
        counts[v] = counts.get(v, 0) + 1
    return ", ".join("%s: %d" % (k, counts[k]) for k in sorted(counts))


def _release_cell(dir_name):
    if dir_name == UNASSIGNED_DIR_NAME:
        return "`_unassigned/`"
    return "[%s](%s/plan.md)" % (dir_name, dir_name)


def render_index(releases, efforts, unassigned_group):
    lines = []
    lines.append("# Release Plan Index")
    lines.append("")
    lines.append(
        "Generated file. Regenerate with `%s` from the repository root. "
        "Hand edits will be overwritten on the next regeneration." % REGEN_COMMAND)
    lines.append("")
    lines.append(
        "**Releases:** %d **Efforts:** %d (%d unassigned) **Source:** every "
        "`plan.md` and `spec.md` under `docs/internal/release-plans/`, including "
        "`_unassigned/`, plus each effort's `implementation-plan.md` where present"
        % (len(releases), len(efforts), len(unassigned_group["efforts"])))
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Series Legend")
    lines.append("")
    lines.append(
        "Every effort id's letter prefix names which series it belongs to. "
        "An id whose letter is not listed here is a generator bug, not a rendering gap: "
        "the generator refuses to run rather than leave the meaning blank.")
    lines.append("")
    lines.append("| Letter | Meaning |")
    lines.append("|---|---|")
    for letter, meaning in SERIES_LEGEND:
        lines.append("| %s | %s |" % (letter, meaning))
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Summary by Release")
    lines.append("")
    lines.append("| Release | Target Version | Theme | Efforts | Spec Statuses | Implementation Plan Statuses |")
    lines.append("|---|---|---|---|---|---|")
    for release in releases:
        release_link = "[%s](%s/plan.md)" % (release["dir_name"], release["dir_name"])
        lines.append("| %s | %s | %s | %d | %s | %s |" % (
            release_link,
            release["target_version"],
            release["theme"],
            len(release["efforts"]),
            _status_counts_cell(release["efforts"], "spec_status"),
            _status_counts_cell(release["efforts"], "plan_status"),
        ))
    released_efforts = [e for release in releases for e in release["efforts"]]
    lines.append("| **Total (assigned to a release)** | | | **%d** | %s | %s |" % (
        len(released_efforts),
        _status_counts_cell(released_efforts, "spec_status"),
        _status_counts_cell(released_efforts, "plan_status"),
    ))
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Unassigned Efforts")
    lines.append("")
    lines.append(
        "Specs written before being assigned to a release: the documented default "
        "home `/plab-spec` writes into when `--target-release` is omitted "
        "(`docs/internal/release-plans/_unassigned/`). These carry no target "
        "version until `/plab-release-plan --promote` moves the whole effort "
        "folder into a release. `_unassigned/` does not exist on disk until "
        "the first spec is written there; its absence is normal, not an error.")
    lines.append("")
    if unassigned_group["efforts"]:
        lines.append(
            "| Effort | Handle | Series | Spec Status | Implementation Plan Status | "
            "Priority | Human Review Required |")
        lines.append("|---|---|---|---|---|---|---|")
        for effort in unassigned_group["efforts"]:
            id_link = "[%s](%s)" % (effort["id"], effort["spec_rel_path"])
            series_cell = "%s (%s)" % (effort["series_letter"], effort["series_meaning"])
            review_cell = "Yes" if effort["requires_review"] else "No"
            lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                id_link,
                effort["handle"],
                series_cell,
                effort["spec_status"],
                effort["plan_status"],
                effort["priority"],
                review_cell,
            ))
    else:
        lines.append("None currently.")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## All Efforts")
    lines.append("")
    lines.append(
        "One row per effort, grouped by release in sequence order (see the Release "
        "column), with unassigned efforts listed last.")
    lines.append("")
    lines.append(
        "| Effort | Handle | Series | Spec Status | Implementation Plan Status | "
        "Release | Target Version | Priority | Human Review Required |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for effort in efforts:
        id_link = "[%s](%s)" % (effort["id"], effort["spec_rel_path"])
        series_cell = "%s (%s)" % (effort["series_letter"], effort["series_meaning"])
        release_cell = _release_cell(effort["release_dir_name"])
        review_cell = "Yes" if effort["requires_review"] else "No"
        target_version_cell = effort["target_version"] if effort["target_version"] else "-"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            id_link,
            effort["handle"],
            series_cell,
            effort["spec_status"],
            effort["plan_status"],
            release_cell,
            target_version_cell,
            effort["priority"],
            review_cell,
        ))
    lines.append("")

    return "\n".join(lines) + "\n"


def generate(release_plans_dir):
    releases, efforts, unassigned_group = build_model(release_plans_dir)
    return render_index(releases, efforts, unassigned_group)


# ---------------------------------------------------------------------------
# Self-test: canary-proven before any CLEAN or FINDINGS result is trusted.
# Every fixture below is built in a tempfile.TemporaryDirectory() and torn
# down with it; none of this ever touches the real repository, so the
# generator's trustworthiness does not depend on which project happens to
# be under the cursor when it runs.
# ---------------------------------------------------------------------------

_FIXTURE_PLAN_MD = """---
sequence: %(seq)s
target-version: %(target_version)s
title: "Release plan %(seq)s: Fixture theme"
type: release-plan
status: in-progress
created: 2026-01-01
updated: 2026-01-01
theme: "Fixture theme"
includes: [%(includes)s]
spec-count: %(count)s
plan-count: %(count)s
checklist-complete: false
---

# Fixture release plan
"""

_FIXTURE_SPEC_MD = """---
id: %(id)s
title: Fixture effort %(id)s
type: spec
status: %(status)s
created: 2026-01-01
updated: 2026-01-01
linked-effort: fixture, not a real source
linked-plan: implementation-plan.md
ac-count: 1
source-count: 1
requires-human-review: %(review)s
target-release: %(target_version)s
linked-release: %(release_dir)s/plan.md
priority: P2
---

# Fixture spec
"""

_FIXTURE_IMPL_MD = """---
id: %(id)s
title: "Implementation plan: fixture effort %(id)s"
type: implementation-plan
status: %(status)s
created: 2026-01-01
updated: 2026-01-01
linked-spec: spec.md
linked-release: %(release_dir)s/plan.md
ac-coverage: complete
phase-count: 1
---

# Fixture implementation plan
"""


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _build_fixture_effort(release_plans_dir, release_dir, effort_id, slug,
                           spec_status="draft", plan_status="draft",
                           target_version="v0.1.0", review="false"):
    effort_dir_name = "%s_%s" % (effort_id, slug)
    effort_dir = os.path.join(release_plans_dir, release_dir, effort_dir_name)
    _write(os.path.join(effort_dir, "spec.md"), _FIXTURE_SPEC_MD % {
        "id": effort_id, "status": spec_status, "review": review,
        "target_version": target_version, "release_dir": release_dir,
    })
    _write(os.path.join(effort_dir, "implementation-plan.md"), _FIXTURE_IMPL_MD % {
        "id": effort_id, "status": plan_status, "release_dir": release_dir,
    })
    return effort_dir_name


def _build_valid_fixture_tree(base_dir):
    """One release, two known-letter efforts. Used as the anti-canary tree for both build_model() and the --check comparator."""
    release_plans_dir = os.path.join(base_dir, "release-plans")
    release_dir = "plan_01_fixture-theme"
    _write(os.path.join(release_plans_dir, release_dir, "plan.md"), _FIXTURE_PLAN_MD % {
        "seq": "01", "target_version": "v0.1.0", "count": 2,
        "includes": "D-01, W-02",
    })
    _build_fixture_effort(release_plans_dir, release_dir, "D-01", "known-good-defect",
                          spec_status="fulfilled", plan_status="complete",
                          target_version="v0.1.0", review="true")
    _build_fixture_effort(release_plans_dir, release_dir, "W-02", "known-good-wrap",
                          spec_status="draft", plan_status="draft",
                          target_version="v0.1.0", review="false")
    return release_plans_dir


def _self_test_series_map():
    failures = []
    for letter, _meaning in SERIES_LEGEND:
        try:
            series_meaning(letter)
        except UnknownSeriesLetterError:
            failures.append(
                "  known-good letter %r was wrongly rejected by series_meaning()" % letter)
    try:
        series_meaning("Z")
        failures.append(
            "  known-bad letter 'Z' was NOT rejected by series_meaning()")
    except UnknownSeriesLetterError:
        pass
    return failures


def _self_test_require_field_nonempty():
    """Defect E (batch): require_field must reject an empty value, not just a missing key."""
    failures = []

    try:
        require_field({"status": "draft"}, "status", "fixture.md")
    except IndexBuildError:
        failures.append(
            "  require_field wrongly rejected a present, non-empty field")

    for bad_fields, label in [
        ({"status": ""}, "empty-string value"),
        ({"status": "   "}, "whitespace-only value"),
        ({}, "missing key"),
        ({"status": []}, "empty list value"),
    ]:
        try:
            require_field(bad_fields, "status", "fixture.md")
            failures.append(
                "  require_field did not reject a %s" % label)
        except IndexBuildError:
            pass

    return failures


def _self_test_requires_review_normalization():
    """Defect E (batch): requires-human-review must accept common true/false spellings and fail loud on anything else, rather than defaulting silently to No."""
    failures = []

    for spelling in ["true", "True", "TRUE", " true ", "yes", "Yes", "y", "1"]:
        result = parse_bool_field(spelling, "requires-human-review", "fixture.md")
        if result is not True:
            failures.append(
                "  parse_bool_field(%r) returned %r, expected True" % (spelling, result))

    for spelling in ["false", "False", "no", "N", "0"]:
        result = parse_bool_field(spelling, "requires-human-review", "fixture.md")
        if result is not False:
            failures.append(
                "  parse_bool_field(%r) returned %r, expected False" % (spelling, result))

    try:
        parse_bool_field("maybe", "requires-human-review", "fixture.md")
        failures.append("  parse_bool_field('maybe') was NOT rejected as unrecognised")
    except IndexBuildError:
        pass

    # Wiring-level: a spelling other than the literal "true" must still
    # normalise correctly when read through build_effort() -> build_model().
    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        _build_fixture_effort(release_plans_dir, "plan_01_fixture-theme", "H-70",
                              "yes-spelling", spec_status="draft",
                              target_version="v0.1.0", review="yes")
        _releases, efforts, _unassigned = build_model(release_plans_dir)
        by_id = {e["id"]: e for e in efforts}
        if "H-70" not in by_id or by_id["H-70"]["requires_review"] is not True:
            failures.append(
                "  requires-human-review: yes was not normalised to True "
                "through build_model()")

    return failures


def _self_test_effort_dir_discovery():
    """Defect A: a non-effort-shaped sibling directory is ignored, UNLESS it contains spec.md, in which case it fails loud instead of silently dropping a real effort."""
    failures = []

    with tempfile.TemporaryDirectory() as base_dir:
        container = os.path.join(base_dir, "container")
        os.makedirs(os.path.join(container, "D-01_real-effort"))
        _write(os.path.join(container, "D-01_real-effort", "spec.md"), "placeholder")
        os.makedirs(os.path.join(container, "supporting"))  # no spec.md: ignore
        names = discover_effort_dirs(container)
        if names != ["D-01_real-effort"]:
            failures.append(
                "  discover_effort_dirs did not ignore a non-effort-shaped "
                "sibling directory without spec.md: got %r" % (names,))

    with tempfile.TemporaryDirectory() as base_dir:
        container = os.path.join(base_dir, "container")
        os.makedirs(os.path.join(container, "not-an-effort-name"))
        _write(os.path.join(container, "not-an-effort-name", "spec.md"), "placeholder")
        try:
            discover_effort_dirs(container)
            failures.append(
                "  a directory containing spec.md but not matching the "
                "id_slug shape was silently ignored instead of raising")
        except IndexBuildError:
            pass

    return failures


def _self_test_release_dir_fail_loud():
    """Defect E (batch): a release folder whose name does not match plan_<digits>_ must fail loud if it contains plan.md, and be safely ignored if it does not. _unassigned/ is never treated as a malformed release name."""
    failures = []

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = os.path.join(base_dir, "release-plans")
        _write(os.path.join(release_plans_dir, "plan04-typo", "plan.md"), _FIXTURE_PLAN_MD % {
            "seq": "04", "target_version": "v0.4.0", "count": 0, "includes": "",
        })
        try:
            discover_release_dirs(release_plans_dir)
            failures.append(
                "  a directory containing plan.md but named outside the "
                "plan_<digits>_ shape was silently dropped instead of raising")
        except IndexBuildError:
            pass

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = os.path.join(base_dir, "release-plans")
        os.makedirs(os.path.join(release_plans_dir, "notes"))  # no plan.md
        _write(os.path.join(release_plans_dir, "plan_01_ok", "plan.md"), _FIXTURE_PLAN_MD % {
            "seq": "01", "target_version": "v0.1.0", "count": 0, "includes": "",
        })
        releases = discover_release_dirs(release_plans_dir)
        names = [r[1] for r in releases]
        if names != ["plan_01_ok"]:
            failures.append(
                "  discover_release_dirs did not cleanly ignore a plan.md-less "
                "stray directory: got %r" % names)

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = os.path.join(base_dir, "release-plans")
        os.makedirs(os.path.join(release_plans_dir, UNASSIGNED_DIR_NAME))
        try:
            releases = discover_release_dirs(release_plans_dir)
        except IndexBuildError as exc:
            failures.append(
                "  _unassigned/ was wrongly treated as a malformed release "
                "folder: %s" % exc)
        else:
            if releases:
                failures.append(
                    "  _unassigned/ was wrongly included as a release: %r" % releases)

    return failures


def _self_test_optional_implementation_plan():
    """Defect B: a missing implementation-plan.md is a normal intermediate state, not an error; a present-but-empty status is still caught."""
    failures = []

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        release_dir = "plan_01_fixture-theme"
        effort_dir_name = _build_fixture_effort(
            release_plans_dir, release_dir, "H-50", "spec-without-plan",
            spec_status="draft", target_version="v0.1.0", review="false")
        os.remove(os.path.join(
            release_plans_dir, release_dir, effort_dir_name, "implementation-plan.md"))
        release = {
            "dir_name": release_dir,
            "dir_path": os.path.join(release_plans_dir, release_dir),
            "target_version": "v0.1.0",
        }
        try:
            effort = build_effort(release, effort_dir_name)
        except IndexBuildError as exc:
            failures.append(
                "  an effort folder missing implementation-plan.md was wrongly "
                "rejected instead of rendered with an explicit plan-status "
                "marker: %s" % exc)
        else:
            if effort["plan_status"] != PLAN_STATUS_NOT_WRITTEN:
                failures.append(
                    "  effort missing implementation-plan.md got plan_status "
                    "%r, expected the explicit marker %r"
                    % (effort["plan_status"], PLAN_STATUS_NOT_WRITTEN))

    # Anti-canary: when implementation-plan.md IS present, its real status
    # still comes through untouched.
    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        release_dir = "plan_01_fixture-theme"
        release = {
            "dir_name": release_dir,
            "dir_path": os.path.join(release_plans_dir, release_dir),
            "target_version": "v0.1.0",
        }
        effort = build_effort(release, "D-01_known-good-defect")
        if effort["plan_status"] != "complete":
            failures.append(
                "  effort WITH implementation-plan.md did not report its "
                "real status: got %r, expected 'complete'" % effort["plan_status"])

    # Present but with an empty status value: require_field's non-empty
    # check must still catch this, not render a blank cell.
    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        release_dir = "plan_01_fixture-theme"
        effort_dir_name = _build_fixture_effort(
            release_plans_dir, release_dir, "H-51", "spec-with-blank-plan-status",
            spec_status="draft", target_version="v0.1.0", review="false")
        impl_path = os.path.join(
            release_plans_dir, release_dir, effort_dir_name, "implementation-plan.md")
        _write(impl_path, _FIXTURE_IMPL_MD % {
            "id": "H-51", "status": "", "release_dir": release_dir,
        })
        release = {
            "dir_name": release_dir,
            "dir_path": os.path.join(release_plans_dir, release_dir),
            "target_version": "v0.1.0",
        }
        try:
            build_effort(release, effort_dir_name)
            failures.append(
                "  implementation-plan.md with an empty status value was NOT "
                "rejected; it would render as a silently blank table cell")
        except IndexBuildError:
            pass

    return failures


def _self_test_unicode_decode_handling():
    """Defect D: an input that cannot be decoded as UTF-8 must raise IndexBuildError, not a raw UnicodeDecodeError that would surface as an uncaught traceback (exit 1) instead of BROKEN (exit 2)."""
    failures = []
    with tempfile.TemporaryDirectory() as base_dir:
        bad_path = os.path.join(base_dir, "bad.md")
        with open(bad_path, "wb") as fh:
            fh.write(b"---\n\xff\xfetitle: invalid utf-8 bytes\n---\n")
        try:
            read_frontmatter_file(bad_path)
            failures.append("  a file with invalid UTF-8 bytes was NOT rejected")
        except UnicodeDecodeError:
            failures.append(
                "  a file with invalid UTF-8 bytes raised raw UnicodeDecodeError "
                "instead of IndexBuildError")
        except IndexBuildError:
            pass
    return failures


def _self_test_build_model_wiring():
    """Prove the fail-loud path fires through build_model(), not only in the leaf function, and that a normal tree (including a harmless non-effort sibling directory) builds cleanly end to end."""
    failures = []

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        # A non-effort sibling directory, the shape Defect A's repro used: a
        # directory a sibling skill placed there, with no spec.md. It must
        # not turn the whole release BROKEN.
        os.makedirs(os.path.join(release_plans_dir, "plan_01_fixture-theme", "supporting"))
        try:
            releases, efforts, unassigned_group = build_model(release_plans_dir)
        except IndexBuildError as exc:
            failures.append(
                "  known-good fixture tree with a harmless non-effort sibling "
                "directory was wrongly rejected: %s" % exc)
            releases, efforts, unassigned_group = [], [], {"efforts": []}

        if len(efforts) != 2:
            failures.append(
                "  expected 2 efforts from the known-good fixture (the "
                "non-effort 'supporting' directory must be ignored), got %d"
                % len(efforts))
        by_id = {e["id"]: e for e in efforts}
        if "D-01" in by_id:
            d01 = by_id["D-01"]
            if d01["handle"] != "known good defect":
                failures.append(
                    "  handle_from_slug produced %r, expected 'known good defect'"
                    % d01["handle"])
            if d01["series_letter"] != "D" or "defect" not in d01["series_meaning"]:
                failures.append("  D-01 series letter/meaning wired incorrectly")
            if d01["requires_review"] is not True:
                failures.append(
                    "  requires-human-review: true was not parsed as boolean True")
        else:
            failures.append("  D-01 missing from known-good fixture result")
        if releases and releases[0]["target_version"] != "v0.1.0":
            failures.append("  target_version not sourced from plan.md correctly")
        if unassigned_group["efforts"]:
            failures.append(
                "  known-good fixture tree with no _unassigned/ produced "
                "unassigned efforts anyway: %r" % unassigned_group["efforts"])

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        # Inject one effort with an unmapped series letter into the SAME
        # release the known-good efforts already live in, so the walk
        # visits good and bad data in one pass, same as it would on a real
        # partially-broken repository.
        _build_fixture_effort(release_plans_dir, "plan_01_fixture-theme",
                              "Z-99", "unmapped-letter")
        try:
            build_model(release_plans_dir)
            failures.append(
                "  fixture tree containing Z-99 (unmapped letter) did NOT raise "
                "through build_model()")
        except UnknownSeriesLetterError:
            pass
        except IndexBuildError as exc:
            failures.append(
                "  Z-99 raised IndexBuildError but not the expected "
                "UnknownSeriesLetterError subtype: %s" % exc)

    return failures


def _self_test_unassigned_group():
    """Defect C: _unassigned/ is its own group, absence is normal, presence contributes efforts with no target version, and the rendered index surfaces both."""
    failures = []

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        try:
            _releases, _efforts, unassigned_group = build_model(release_plans_dir)
        except IndexBuildError as exc:
            failures.append(
                "  absent _unassigned/ was wrongly treated as an error: %s" % exc)
        else:
            if unassigned_group["efforts"]:
                failures.append(
                    "  absent _unassigned/ produced nonempty efforts: %r"
                    % unassigned_group["efforts"])

    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        _build_fixture_effort(release_plans_dir, UNASSIGNED_DIR_NAME, "H-60",
                              "not-yet-released", spec_status="draft",
                              target_version="v9.9.9", review="false")
        releases, efforts, unassigned_group = build_model(release_plans_dir)
        if len(unassigned_group["efforts"]) != 1:
            failures.append(
                "  _unassigned/ effort was not discovered: got %d efforts, "
                "expected 1" % len(unassigned_group["efforts"]))
        elif unassigned_group["efforts"][0]["target_version"] is not None:
            failures.append(
                "  unassigned effort carried a target version (%r) instead "
                "of none" % unassigned_group["efforts"][0]["target_version"])
        if len(efforts) != 3:  # 2 known-good + 1 unassigned
            failures.append(
                "  combined efforts list did not include the unassigned "
                "effort: got %d, expected 3" % len(efforts))
        rendered = render_index(releases, efforts, unassigned_group)
        if "H-60" not in rendered or "_unassigned" not in rendered:
            failures.append(
                "  rendered index did not surface the unassigned effort or group")

    return failures


def _self_test_check_comparator():
    """Prove the --check comparator distinguishes current from stale, and that a difference only in line ending does NOT count as stale."""
    failures = []
    with tempfile.TemporaryDirectory() as base_dir:
        release_plans_dir = _build_valid_fixture_tree(base_dir)
        current_text = generate(release_plans_dir)
        index_path = os.path.join(release_plans_dir, "INDEX.md")

        # Anti-canary: byte-identical content must compare as current.
        _write(index_path, current_text)
        status, _detail = check_index(release_plans_dir, index_path)
        if status != "current":
            failures.append(
                "  identical committed INDEX.md was wrongly reported as %r" % status)

        # Anti-canary: CRLF-only difference must still compare as current.
        with open(index_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(current_text.replace("\n", "\r\n"))
        status, _detail = check_index(release_plans_dir, index_path)
        if status != "current":
            failures.append(
                "  CRLF-only difference was wrongly reported as %r (expected 'current')"
                % status)

        # Canary: real content drift must be flagged stale.
        _write(index_path, current_text + "\nan extra stray line\n")
        status, _detail = check_index(release_plans_dir, index_path)
        if status != "stale":
            failures.append(
                "  drifted committed INDEX.md was wrongly reported as %r" % status)

        # Canary: a missing committed file is stale (findings), not broken.
        os.remove(index_path)
        status, _detail = check_index(release_plans_dir, index_path)
        if status != "stale":
            failures.append(
                "  missing committed INDEX.md was reported as %r, expected 'stale'"
                % status)

    return failures


def _guarded_exit_code(fn):
    """Run fn() and return the process exit code, never letting an unanticipated exception surface as a bare traceback.

    An uninterpreted traceback exits the process with code 1 on both CPython's default behaviour and this platform, which under this script's own contract means "the detector proved itself and found a real problem" (FINDINGS). An exception fn() never anticipated is the opposite: the detector never ran. Any exception that is not itself a controlled sys.exit(...) is caught here, reported as BROKEN with its traceback for diagnosis, and mapped to exit 2.
    """
    try:
        fn()
    except SystemExit as exc:
        return 0 if exc.code is None else exc.code
    except BaseException as exc:
        print("BROKEN: unexpected %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        print("Exiting 2. Do NOT read this as a clean or stale result.", file=sys.stderr)
        return 2
    return 0


def _self_test_top_level_guard():
    """Defect D (general rule): an unanticipated exception must map to exit 2, and normal exit codes must pass through the guard untouched."""
    failures = []

    def _boom():
        raise TypeError("injected fault for top-level guard canary")

    # The guard prints its BROKEN diagnostic to stderr on the way to
    # returning 2; that print is real production behaviour (it is how a
    # human would learn what broke) but has no place appearing in a normal,
    # successful self-test run, where it would read as a false alarm.
    # Swallow it here; the exit code is still checked below.
    captured_stderr = io.StringIO()
    with contextlib.redirect_stderr(captured_stderr):
        code = _guarded_exit_code(_boom)
    if code != 2:
        failures.append(
            "  an unanticipated exception through _guarded_exit_code "
            "returned exit code %r, expected 2 (BROKEN)" % (code,))
    if "BROKEN" not in captured_stderr.getvalue():
        failures.append(
            "  _guarded_exit_code did not print a BROKEN diagnostic for an "
            "unanticipated exception")

    for expected in (0, 1, 2):
        def _normal_exit(expected=expected):
            sys.exit(expected)
        code = _guarded_exit_code(_normal_exit)
        if code != expected:
            failures.append(
                "  a normal sys.exit(%d) was altered by _guarded_exit_code: got %r"
                % (expected, code))

    return failures


def self_test():
    """Prove the generator before trusting any CLEAN or FINDINGS result."""
    failures = []
    failures += _self_test_series_map()
    failures += _self_test_require_field_nonempty()
    failures += _self_test_requires_review_normalization()
    failures += _self_test_effort_dir_discovery()
    failures += _self_test_release_dir_fail_loud()
    failures += _self_test_optional_implementation_plan()
    failures += _self_test_unicode_decode_handling()
    failures += _self_test_build_model_wiring()
    failures += _self_test_unassigned_group()
    failures += _self_test_check_comparator()
    failures += _self_test_top_level_guard()

    if failures:
        print("BROKEN: generator self-test failed, the detector is not trustworthy.",
              file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean or stale result.", file=sys.stderr)
        return False
    print("self-test: PASS (series map, required-field/boolean normalisation, "
          "effort and release folder discovery, optional implementation plan, "
          "unicode decoding, build_model wiring, unassigned group, --check "
          "comparator, and the top-level exception guard all proven against "
          "fixtures)")
    return True


def check_index(release_plans_dir, index_path):
    """Return ("current"|"stale", detail) comparing generated text against the committed INDEX.md, ignoring line-ending differences only.

    A missing index_path is "stale": regenerating fixes it, so it belongs with FINDINGS (exit 1), not with BROKEN (exit 2), which stays reserved for inputs the generator could not read at all.
    """
    current_text = generate(release_plans_dir)
    if not os.path.exists(index_path):
        return "stale", "committed INDEX.md does not exist yet"
    with open(index_path, encoding="utf-8", newline="") as fh:
        committed_text = fh.read()
    normalized_committed = committed_text.replace("\r\n", "\n")
    if normalized_committed == current_text:
        return "current", None
    return "stale", "committed INDEX.md does not match freshly generated content"


def main():
    check_mode = "--check" in sys.argv[1:]

    if not self_test():
        sys.exit(2)

    release_plans_dir = os.path.join(REPO_ROOT, RELEASE_PLANS_DIR_NAME)
    index_path = os.path.join(release_plans_dir, "INDEX.md")

    if check_mode:
        try:
            status, detail = check_index(release_plans_dir, index_path)
        except IndexBuildError as exc:
            print("BROKEN: could not build the index for comparison: %s" % exc,
                  file=sys.stderr)
            sys.exit(2)
        if status == "current":
            print("CLEAN: canary proved, %s matches current frontmatter." % index_path)
            sys.exit(0)
        print("FINDINGS: %s is out of date (%s). Regenerate with `%s`."
              % (index_path, detail, REGEN_COMMAND), file=sys.stderr)
        sys.exit(1)

    try:
        text = generate(release_plans_dir)
    except IndexBuildError as exc:
        print("BROKEN: could not build the index: %s" % exc, file=sys.stderr)
        sys.exit(2)

    try:
        with open(index_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError as exc:
        print("BROKEN: could not write %s: %s" % (index_path, exc), file=sys.stderr)
        sys.exit(2)

    print("CLEAN: canary proved, wrote %s (%d bytes)." % (index_path, len(text)))
    sys.exit(0)


if __name__ == "__main__":
    sys.exit(_guarded_exit_code(main))
