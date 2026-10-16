#!/usr/bin/env python3
"""
Field-validity gate for document frontmatter under docs/internal/release-plans/.

EXIT-CODE CONTRACT
------------------
  0  CLEAN    self-test passed AND every scanned frontmatter block validates against its schema
  1  FINDINGS self-test passed AND at least one frontmatter block fails its schema
  2  BROKEN   the detector could not prove itself, or an input could not be read

NEVER INTERPRET 2 AS CLEAN. See `scripts/check-dashes.py` and `skills/plab-wrap-session/scripts/path-citation-check.py` for the two prior gates this one matches in shape, and `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-11_three-state-gate-canaries/spec.md` for why this repository insists on the three-state contract at all.

No unexpected exception is ever allowed to surface as exit 1. `main()` is wrapped at the very bottom of this file: any exception this script did not anticipate and handle explicitly is reported as BROKEN and exits 2, never 1. Exit 1 means, and only means, "the detector proved itself and then found a real problem in a document." An uncaught exception means the detector never got that far, so it cannot mean the same thing as a finding.

WHAT THIS CATCHES
------------------
A spec, implementation plan, or release plan whose frontmatter has drifted from the contract every downstream reader assumes: a status value outside the enum, a date or version string in the wrong shape, a field silently missing, a field nobody documented sitting in the block. None of that is visible from a normal read of the rendered markdown body, and a human skimming past the frontmatter block during a plain-language document review is exactly the failure mode this gate exists to remove. This is the field-validity half of the document lifecycle gate (effort H-01); it does not check cross-document consistency (an `ac-count` that disagrees with the actual `AC-N:` entries in the body, a `linked-release` path that does not resolve) - only that each field, taken alone, has the right shape.

THE SCHEMA FILES ARE DETECTOR CONFIGURATION, NOT SCAN INPUT
-------------------------------------------------------------
The four JSON Schema files in `docs/internal/schemas/` are always loaded from that fixed, script-relative location, never from `--root`. They are part of this detector in the same sense that `check-dashes.py`'s `PATTERN` constant is part of that detector: a fixed instrument, not a document being validated. `--root` controls only which `docs/internal/release-plans/` tree gets scanned, matching `--repo-root` in `path-citation-check.py`, whose docstring makes the same distinction between the project being scanned and the tool's own installed location. Because the schemas are detector configuration, `self_test()` below loads and exercises the real, committed schema files rather than a duplicate copy - a second, hand-maintained copy embedded in this script would be exactly the kind of two-sources-of-truth setup that drifts silently and is never caught, which is what canary discipline exists to prevent. Only the documents being validated (the synthetic `.md` fixtures with frontmatter) are built fresh inside a `tempfile.TemporaryDirectory()` and never touch the real repository, so a clean self-test does not depend on which project happens to be under the cursor.

THE SMALL JSON SCHEMA SUBSET THIS VALIDATOR IMPLEMENTS
---------------------------------------------------------
Exactly: `required`, `type` (the values `string`, `integer`, `boolean`, `array`, `null`, or a JSON array of any of those - e.g. `["string", "null"]` for a nullable field), `enum`, `pattern`, `additionalProperties: false`, `properties`, and `items` (carrying only `type`). `$schema` is read and ignored as metadata. This is not a general JSON Schema engine and must never grow into pretending to be one; see `docs/internal/schemas/README.md` for why the schema files themselves stay within this subset (no `const`, no `"type": "object"` at the root) even though nothing stops a future editor from reaching for a keyword outside it. Only the four schema files this script maps `type` values to (`spec.schema.json`, `implementation-plan.schema.json`, `release-plan.schema.json`, `review.schema.json` - see `SCHEMA_FILES` below) are ever opened; a stray file dropped into `docs/internal/schemas/` under a different name is never read and is not part of this contract. If one of the four mapped schema files uses a keyword this validator does not implement - at any nesting depth, inside `properties` or `items` - the whole run exits 2 (BROKEN) before a single document is scanned. Silently ignoring an unrecognized keyword would mean validating less than the schema claims while still reporting success, which is a fail-open and is exactly the class of defect this repository refuses to ship (see the ripgrep and Perl failures documented in `scripts/check-dashes.py`, a different mechanism producing the identical false-clean shape).

THE COERCION RULE IS SCHEMA-AWARE, NOT GRAMMAR-BASED
---------------------------------------------------------
The frontmatter parser below reads plain text, so every value starts life as a string. A quoted value is never coerced, even if it looks numeric or boolean, because quoting it was the author's way of saying "this is text." For a bare (unquoted) token, coercion is driven by what the *target property's schema* declares, not by the token's own spelling: a bare token is coerced to a Python int only when the schema for that field declares `"integer"` (directly, or as one member of a list-valued `"type"`), and to a Python bool only when the schema declares `"boolean"`. A bare token is never coerced to int or bool against a field whose schema says `"string"`.

This is a deliberate rejection of an earlier, grammar-based rule ("any bare token matching JSON's integer grammar becomes an int") that looked reasonable in isolation but broke on this repository's own documents: `sequence` is schema-typed `"string"` with `"pattern": "^\\d{2}$"` specifically so a two-digit, possibly-leading-zero folder ordinal round-trips as text. A grammar-based rule coerced `sequence: 10` (no leading zero) to the integer `10`, which then failed the schema's own `"string"` type check - a false positive that first bites at release plan 10, while `04` through `09` passed only because a leading zero happens to block the same grammar match. Schema-aware coercion removes the leading-zero special case entirely: every bare `sequence` value, `04` through `99`, stays a string because the schema says `"string"`, and every field genuinely typed `"integer"` (`ac-count`, `phase-count`, `spec-count`, and so on) still coerces correctly regardless of leading zero, because JSON's own integer grammar (`-?(0|[1-9]\\d*)`) never matches a leading-zero token in the first place - so `04` under an `"integer"` schema is a bare token that fails to coerce and is correctly reported as a type violation, not silently accepted as `4`.

One token is coerced unconditionally, independent of the target schema: the bare word `null` always becomes Python `None`. This is deliberately NOT schema-gated. Gating it (coercing to `None` only when the field's schema allows a `"null"` type) would reproduce, rather than fix, exactly the inconsistency this rule replaces: previously a bare `null` on an unpatterned string field passed silently (it is a valid four-character string), while the identical bare `null` on a patterned field like `created` failed the pattern - two different outcomes for the same input, depending on an implementation detail the author had no visibility into. Unconditional coercion to `None` makes the outcome depend only on whether the field's schema actually permits `null` (see the next section) - consistent for every field, patterned or not.

List items are routed through this exact same coercion function, using the array field's `items` schema as the per-item target type. `includes` and `spec-dependencies` both declare `items: {"type": "string"}`, so a bare numeric or boolean-looking item in one of those lists is left as a string by the same schema-aware logic described above - consistent with `sequence`, not an exception to it. A bare `null` item, however, still coerces unconditionally to `None`, and then correctly fails the `items: {"type": "string"}` check, because `None` is not a string. This is proof the routing works in both directions: schema-typed-string items are never wrongly coerced away from their valid string reading, while a token that cannot be a string under any reading (`null`) is still caught.

NULLABLE FIELDS: LIST-VALUED "type" AND THE "null" TYPE
-------------------------------------------------------------
`"type"` may be a single value or a JSON array of values, e.g. `["string", "null"]`. An instance validates if it matches ANY type in the list. `"null"` is a supported type value; an instance matches it only when it is Python `None`. This repository writes literal `null` into a spec's `linked-plan`, `linked-release`, and `target-release` before those facts exist (see `skills/plab-spec/references/frontmatter-schema.md` and `skills/plab-release-plan/references/promote-demote.md`, which clears both fields back to `null` on `--demote`), and into an implementation plan's `linked-release` for the same reason, so those four fields are schema-typed `["string", "null"]` rather than plain `"string"`.

WHY DOCUMENTS ARE READ WITH utf-8-sig
-----------------------------------------
A file saved on Windows can carry a UTF-8 byte-order mark. Read with plain `utf-8`, that BOM attaches to the first line, so a frontmatter block that legitimately opens with `---` reads instead as `\\ufeff---`, fails the opening-fence check, and the file is silently skipped as if it carried no frontmatter at all - a validated file quietly downgrading into an ignored one, with no finding and no BROKEN, which is a fail-open by omission. `utf-8-sig` strips a leading BOM when present and is byte-identical to `utf-8` when one is absent, so every document is read that way below. A file that is not valid UTF-8 at all (for example one saved as cp1252 and carrying a byte no UTF-8 sequence can start with) raises `UnicodeDecodeError` on that same read; this is caught alongside `OSError` and reported as BROKEN for that file, per the general exception rule above - never as an uncaught traceback and never as a silent skip.

BROKEN VS. A FINDING: WHERE THE LINE IS DRAWN
--------------------------------------------------
BROKEN (exit 2) is reserved for the detector itself: self-test failing, `docs/internal/schemas/` missing or containing a schema file that will not parse as JSON or uses an unsupported keyword, the `docs/internal/release-plans/` scan root missing under `--root`, a directory under the scan root that cannot be listed at the OS level (permissions, a vanished mount - `os.walk()` is given an `onerror` callback that re-raises rather than the default of silently swallowing the error), zero files found to check or skip when a clean result is otherwise about to be printed (an emptied, moved, or misdirected scan surface must never read as a clean tree), an OS-level failure opening a `.md` file, or that file's bytes failing to decode as UTF-8 at all. A single document whose *content* does not conform to the flat `key: value` frontmatter shape this repository uses (an unclosed `---` fence, a line that is not `key: value`, a duplicate key, a `type` field that is missing or names no known schema) is reported as a FINDING against that one file, not BROKEN: the detector proved itself fine via self-test, the failure is a property of that one input document, and it does not stop the rest of the scan. Every other `.md` file under the scan root is still checked.

SKIPPING FILES WITH NO FRONTMATTER IS DELIBERATE
----------------------------------------------------
A `.md` file whose first non-blank line is not a `---` fence (for example `docs/internal/release-plans/README.md`) is skipped, not flagged. Leading blank or whitespace-only lines before the fence do not exempt a file: a file whose first non-blank line IS the opening `---` fence is a frontmatter file, full stop, and is scanned exactly as if the fence were on line 1. A schema describes the shape of frontmatter that is present; it says nothing about whether a given file is required to carry frontmatter at all, and that question belongs to a different check, not this one.

COMMENTS INSIDE THE FRONTMATTER BLOCK
------------------------------------------
A line whose first non-whitespace character is `#` is a full-line comment and is skipped, exactly like a blank line. A `key: value` line may also carry a trailing comment - `key: value  # note` - stripped from an unquoted position (a `#` inside a quoted string is just a character in that string, never the start of a comment). `skills/plab-spec/references/frontmatter-schema.md`'s own worked example uses exactly this trailing-comment style on `linked-effort`, so an author copying that example must not have the comment silently baked into the field's value.

WHAT PER-TYPE FRONTMATTER IS REQUIRED VS. OPTIONAL FOLLOWS THE REPO'S OWN AUTHORING CONTRACT, NOT THE FULLEST DOCUMENT ON DISK
-----------------------------------------------------------------------------------------------------------------------------------
`spec.schema.json`'s required list matches exactly what `skills/plab-spec/references/frontmatter-schema.md` documents as required for a spec: `id`, `title`, `type`, `status`, `created`, `updated`, `linked-effort`, `ac-count`. Every other field that reference documents - `linked-plan`, `linked-release`, `source-count`, `requires-human-review`, `priority`, `target-release`, `gh-issue`, `spec-dependencies`, `linked-strategy-brief`, `superseded-by` - is optional: its shape is still enforced when the field is present, but its absence is not a finding. A spec sitting in `_unassigned/` (see `skills/plab-spec/SKILL.md`) genuinely has no release and no target version yet, which is exactly the case `--target-release` being omitted describes, and this schema must not flag that spec for a fact of its lifecycle stage rather than a defect in its frontmatter.
"""

import argparse
import contextlib
import io
import json
import os
import re
import sys
import tempfile

SCAN_ROOT_REL = ("docs", "internal", "release-plans")
SCHEMAS_DIR_REL = ("docs", "internal", "schemas")

SCHEMA_FILES = {
    "spec": "spec.schema.json",
    "implementation-plan": "implementation-plan.schema.json",
    "release-plan": "release-plan.schema.json",
    "review": "review.schema.json",
}

SUPPORTED_SCHEMA_KEYWORDS = {
    "$schema", "type", "required", "enum", "pattern", "additionalProperties", "properties", "items",
}
SUPPORTED_TYPE_VALUES = {"string", "integer", "boolean", "array", "null"}

LINE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]?(.*)$")
BARE_INT_RE = re.compile(r"^-?(0|[1-9]\d*)$")


class SchemaBroken(Exception):
    """A schema file uses a keyword or value this validator does not implement."""


class BrokenInput(Exception):
    """An input the detector needs (a schema file, the scan root, a document) could not be read at all."""


# ---------------------------------------------------------------------------
# Schema loading and the unsupported-keyword guard
# ---------------------------------------------------------------------------

def _type_values(type_field):
    """Normalize a 'type' keyword's value (single string or list) to a list, for uniform handling."""
    return type_field if isinstance(type_field, list) else [type_field]


def find_unsupported(node, path="$"):
    """Return a list of problem strings for any keyword or type value this validator cannot enforce."""
    if not isinstance(node, dict):
        return ["%s: schema node is not a JSON object" % path]
    problems = []
    for key in node:
        if key not in SUPPORTED_SCHEMA_KEYWORDS:
            problems.append("%s.%s: unimplemented schema keyword" % (path, key))
    if "type" in node:
        for tv in _type_values(node["type"]):
            if tv not in SUPPORTED_TYPE_VALUES:
                problems.append("%s.type: unsupported type value %r" % (path, tv))
    if isinstance(node.get("properties"), dict):
        for prop_name, sub in node["properties"].items():
            problems.extend(find_unsupported(sub, "%s.properties.%s" % (path, prop_name)))
    if "items" in node:
        problems.extend(find_unsupported(node["items"], "%s.items" % path))
    return problems


def load_schema(path):
    """Load one schema file and refuse it (SchemaBroken) if it uses anything unsupported."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise BrokenInput("could not read schema %s: %s" % (path, exc))
    except json.JSONDecodeError as exc:
        raise SchemaBroken("%s is not valid JSON: %s" % (path, exc))
    problems = find_unsupported(data)
    if problems:
        raise SchemaBroken("%s uses keyword(s) this validator does not implement:\n  %s"
                           % (path, "\n  ".join(problems)))
    return data


def schemas_dir():
    """Fixed, script-relative location. Never taken from --root; see module docstring."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), *SCHEMAS_DIR_REL)


def load_all_schemas():
    directory = schemas_dir()
    if not os.path.isdir(directory):
        raise BrokenInput("schema directory does not exist: %s" % directory)
    schemas = {}
    for type_name, filename in SCHEMA_FILES.items():
        schemas[type_name] = load_schema(os.path.join(directory, filename))
    return schemas


# ---------------------------------------------------------------------------
# The validator: the small keyword subset, applied recursively
# ---------------------------------------------------------------------------

def type_matches(instance, type_name):
    if type_name == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if type_name == "boolean":
        return isinstance(instance, bool)
    if type_name == "string":
        return isinstance(instance, str)
    if type_name == "array":
        return isinstance(instance, list)
    if type_name == "null":
        return instance is None
    raise SchemaBroken("unsupported type value %r reached the validator" % type_name)


def validate_node(instance, node, path, findings):
    """Check instance against one (already keyword-checked) schema node. Appends (field_path, message) tuples to `findings`, never a file path - the caller (scan()) owns the file's rel path and joins it with these at print time, so a field path can never be mistaken for part of the file path when the two are later concatenated for display."""
    if "type" in node:
        type_list = _type_values(node["type"])
        if not any(type_matches(instance, tv) for tv in type_list):
            findings.append((path, "expected type %s, got %s (%r)"
                             % (node["type"], type(instance).__name__, instance)))
            return
    if "enum" in node and instance not in node["enum"]:
        findings.append((path, "value %r is not one of %s" % (instance, node["enum"])))
    if "pattern" in node and isinstance(instance, str):
        if re.search(node["pattern"], instance) is None:
            findings.append((path, "value %r does not match pattern %s" % (instance, node["pattern"])))
    if isinstance(instance, dict):
        for key in node.get("required", []):
            if key not in instance:
                findings.append((path, "missing required field '%s'" % key))
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    findings.append((path, "unexpected field '%s' not permitted by schema" % key))
        for key, sub in properties.items():
            if key in instance:
                validate_node(instance[key], sub, "%s.%s" % (path, key), findings)
    if isinstance(instance, list) and "items" in node:
        for i, item in enumerate(instance):
            validate_node(item, node["items"], "%s[%d]" % (path, i), findings)


# ---------------------------------------------------------------------------
# The flat frontmatter parser
# ---------------------------------------------------------------------------

def strip_quotes(token):
    """Return (value, was_quoted) for one token that may be wrapped in matching quote characters."""
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
        return token[1:-1], True
    return token, False


def strip_inline_comment(raw):
    """Strip a trailing '# ...' comment that starts outside any quoted string. A '#' only starts a comment when it is the first character of the value or is preceded by whitespace, matching the worked example in skills/plab-spec/references/frontmatter-schema.md. A '#' inside a quoted string is just a character in that string."""
    in_quote = None
    for i, ch in enumerate(raw):
        if in_quote:
            if ch == in_quote:
                in_quote = None
            continue
        if ch in ('"', "'"):
            in_quote = ch
            continue
        if ch == "#" and (i == 0 or raw[i - 1].isspace()):
            return raw[:i]
    return raw


def parse_raw_value(raw):
    """Parse one 'key: value' RHS into an uncoerced raw form: ('scalar', value_str, was_quoted) for a bare or quoted scalar, or ('list', [(value_str, was_quoted), ...]) for a bracketed list. No int/bool/null coercion happens here - see coerce_token(), which needs the target property's schema to decide how a bare token should be read (see module docstring)."""
    raw = strip_inline_comment(raw).strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return ("list", [])
        items = [strip_quotes(tok.strip()) for tok in inner.split(",")]
        return ("list", items)
    value, was_quoted = strip_quotes(raw)
    return ("scalar", value, was_quoted)


def node_type_set(node):
    """The set of type names a schema property node declares, or an empty set if the node is unknown (an undeclared/additional field) or declares no 'type' at all."""
    if not node:
        return set()
    t = node.get("type")
    if t is None:
        return set()
    return set(_type_values(t))


def coerce_token(value_str, was_quoted, node):
    """Coerce one bare token per the schema-aware rule explained in the module docstring. `node` is the schema node the token will be validated against (a property node for a scalar field, or an `items` node for a list element), or None when the field is not declared by the schema at all."""
    if was_quoted:
        return value_str
    if value_str == "null":
        return None
    types = node_type_set(node)
    if value_str == "true" and "boolean" in types:
        return True
    if value_str == "false" and "boolean" in types:
        return False
    if "integer" in types and BARE_INT_RE.match(value_str):
        return int(value_str)
    return value_str


def coerce_frontmatter(raw_fm, schema):
    """Turn the uncoerced raw parse of a frontmatter block into final Python values, driven by `schema`'s per-field 'type' declarations (see coerce_token / module docstring). `schema` may be None (the document's 'type' field named no known schema); every value is then left as its raw string/list-of-strings form, which is fine because scan() reports a finding and stops before validating further in that case."""
    properties = (schema or {}).get("properties", {})
    result = {}
    for key, raw in raw_fm.items():
        node = properties.get(key)
        if raw[0] == "list":
            item_node = (node or {}).get("items") if node else None
            result[key] = [coerce_token(v, q, item_node) for (v, q) in raw[1]]
        else:
            _, value_str, was_quoted = raw
            result[key] = coerce_token(value_str, was_quoted, node)
    return result


def extract_frontmatter_block(text):
    """Return the raw lines between the opening and closing '---' fence, or None if the file's first non-blank line is not an opening fence at all (the file deliberately carries no frontmatter - see module docstring). Leading blank or whitespace-only lines before the fence do NOT exempt a file: only the position of the first non-blank line decides whether this is a frontmatter file."""
    lines = text.splitlines()
    start = 0
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    if start >= len(lines) or lines[start].strip() != "---":
        return None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            return lines[start + 1:i]
    raise ValueError("frontmatter opened with '---' but no closing '---' line was found")


def parse_flat_frontmatter(block_lines):
    """Parse the raw lines of one frontmatter block into key -> raw-value form (see parse_raw_value). Full-line comments and blank lines are skipped. A duplicate key is a parse failure (a per-file finding via the ValueError path in scan()), matching what a real YAML parser would refuse rather than silently resolving last-wins."""
    result = {}
    for line in block_lines:
        if not line.strip():
            continue
        if line.strip().startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m:
            raise ValueError("line does not match the flat 'key: value' shape: %r" % line)
        key, raw_value = m.group(1), m.group(2)
        if key in result:
            raise ValueError("duplicate key '%s' in frontmatter block" % key)
        result[key] = parse_raw_value(raw_value)
    return result


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def find_markdown_files(scan_root):
    """List every .md file under scan_root. A directory that cannot be listed at the OS level (permissions, a vanished mount) is NOT silently skipped: os.walk()'s default onerror behavior swallows scandir/listdir errors, which would let an unreadable subtree disappear from the scan with no finding and no BROKEN - the same fail-open-by-omission the BOM and leading-blank-line handling above exist to close. The onerror callback here re-raises as BrokenInput instead."""
    found = []

    def onerror(exc):
        raise BrokenInput("could not list a directory while scanning %s: %s" % (scan_root, exc))

    for dirpath, _dirs, filenames in os.walk(scan_root, onerror=onerror):
        for fn in filenames:
            if fn.endswith(".md"):
                found.append(os.path.join(dirpath, fn))
    found.sort()
    return found


def scan(root, schemas):
    """Validate every frontmatter-bearing .md file under root/docs/internal/release-plans/. Returns (findings, checked_count, skipped_count). Raises BrokenInput if the scan root is missing, a directory under it cannot be listed, or a file cannot be opened or decoded at the OS level at all."""
    scan_root = os.path.join(root, *SCAN_ROOT_REL)
    if not os.path.isdir(scan_root):
        raise BrokenInput("scan root does not exist: %s" % scan_root)

    findings = []
    checked = 0
    skipped = 0

    for path in find_markdown_files(scan_root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            with open(path, encoding="utf-8-sig") as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise BrokenInput("could not read %s: %s" % (rel, exc))

        try:
            block = extract_frontmatter_block(text)
        except ValueError as exc:
            findings.append("%s: %s" % (rel, exc))
            continue
        if block is None:
            skipped += 1
            continue

        try:
            raw_fm = parse_flat_frontmatter(block)
        except ValueError as exc:
            findings.append("%s: %s" % (rel, exc))
            continue

        type_raw = raw_fm.get("type")
        type_value = type_raw[1] if type_raw is not None and type_raw[0] == "scalar" else None
        if not isinstance(type_value, str) or type_value not in schemas:
            findings.append("%s: frontmatter 'type' field is missing or unrecognized (%r); expected one of %s"
                            % (rel, type_value, sorted(schemas)))
            continue

        checked += 1
        schema = schemas[type_value]
        fm = coerce_frontmatter(raw_fm, schema)

        node_findings = []
        validate_node(fm, schema, "$", node_findings)
        for field_path, message in node_findings:
            findings.append("%s: %s: %s" % (rel, field_path, message))

    return findings, checked, skipped


# ---------------------------------------------------------------------------
# Self-test: proves the parser, the validator, and the unsupported-keyword guard
# ---------------------------------------------------------------------------

VALID_SPEC = """---
id: X-01
title: Canary valid spec
type: spec
status: draft
created: 2026-01-01
updated: 2026-01-01
linked-effort: a plain-language description of where this came from, 2026-01-01
linked-plan: implementation-plan.md
linked-release: docs/internal/release-plans/plan_00_canary/plan.md
ac-count: 1
source-count: 1
requires-human-review: false
priority: P2
target-release: v0.1.0
---

# Spec: Canary
"""

# Repo authoring contract per DEFECT C / skills/plab-spec/references/frontmatter-schema.md: only id, title, type, status, created, updated, linked-effort, ac-count are required. A spec sitting in _unassigned/ genuinely has none of the optional fields set yet.
UNASSIGNED_SPEC = """---
id: X-02
title: Canary unassigned spec
type: spec
status: draft
created: 2026-01-01
updated: 2026-01-01
linked-effort: docs/internal/efforts/X-02.md
linked-plan: null
linked-release: null
ac-count: 1
---

# Spec: Canary unassigned
"""

SPEC_BAD_STATUS = VALID_SPEC.replace("status: draft", "status: nope", 1)

SPEC_BAD_ID = VALID_SPEC.replace("id: X-01", "id: not-an-id", 1)

SPEC_BAD_DATE = VALID_SPEC.replace("created: 2026-01-01", "created: 01/01/2026", 1)

SPEC_WRONG_TYPE = VALID_SPEC.replace("ac-count: 1", 'ac-count: "one"', 1)

SPEC_MISSING_REQUIRED = VALID_SPEC.replace("title: Canary valid spec\n", "", 1)

SPEC_UNKNOWN_KEY = VALID_SPEC.replace(
    "priority: P2\n", "priority: P2\nnot-a-real-field: surprise\n", 1)

SPEC_BAD_TARGET_RELEASE = VALID_SPEC.replace("target-release: v0.1.0", "target-release: 0.1.0", 1)

VALID_IMPLEMENTATION_PLAN = """---
id: X-01
title: "Implementation plan: Canary valid spec"
type: implementation-plan
status: draft
created: 2026-01-01
updated: 2026-01-01
linked-spec: spec.md
linked-release: docs/internal/release-plans/plan_00_canary/plan.md
ac-coverage: complete
phase-count: 1
---

# Implementation Plan: Canary
"""

PLAN_BAD_ID = VALID_IMPLEMENTATION_PLAN.replace("id: X-01", "id: not-an-id", 1)

PLAN_BAD_ENUM = VALID_IMPLEMENTATION_PLAN.replace("ac-coverage: complete", "ac-coverage: nope", 1)

PLAN_BAD_DATE = VALID_IMPLEMENTATION_PLAN.replace("created: 2026-01-01", "created: 01/01/2026", 1)

PLAN_WRONG_TYPE = VALID_IMPLEMENTATION_PLAN.replace("phase-count: 1", 'phase-count: "one"', 1)

PLAN_MISSING_REQUIRED = VALID_IMPLEMENTATION_PLAN.replace("phase-count: 1\n", "", 1)

PLAN_UNKNOWN_KEY = VALID_IMPLEMENTATION_PLAN.replace(
    "phase-count: 1\n", "phase-count: 1\nnot-a-real-field: surprise\n", 1)

VALID_RELEASE_PLAN = """---
sequence: 00
target-version: v0.1.0
title: "Release plan 00: Canary"
type: release-plan
status: in-progress
created: 2026-01-01
updated: 2026-01-01
theme: "Canary"
includes: [X-01]
spec-count: 1
plan-count: 1
checklist-complete: false
---

# Release Plan 00: Canary
"""

# DEFECT D canary: bare sequence values 04, 09, 10, 12 must ALL be valid (schema-aware coercion leaves them as strings because the sequence field's schema type is "string", not "integer").
SEQUENCE_04 = VALID_RELEASE_PLAN.replace("sequence: 00", "sequence: 04", 1)
SEQUENCE_09 = VALID_RELEASE_PLAN.replace("sequence: 00", "sequence: 09", 1)
SEQUENCE_10 = VALID_RELEASE_PLAN.replace("sequence: 00", "sequence: 10", 1)
SEQUENCE_12 = VALID_RELEASE_PLAN.replace("sequence: 00", "sequence: 12", 1)

# a genuinely wrong sequence shape (3 digits) must still be flagged
RELEASE_PLAN_BAD_SEQUENCE = VALID_RELEASE_PLAN.replace("sequence: 00", "sequence: 005", 1)

RELEASE_PLAN_BAD_ENUM = VALID_RELEASE_PLAN.replace("status: in-progress", "status: nope", 1)

RELEASE_PLAN_BAD_DATE = VALID_RELEASE_PLAN.replace("created: 2026-01-01", "created: 01/01/2026", 1)

RELEASE_PLAN_WRONG_TYPE = VALID_RELEASE_PLAN.replace("spec-count: 1", 'spec-count: "one"', 1)

RELEASE_PLAN_MISSING_REQUIRED = VALID_RELEASE_PLAN.replace("theme: \"Canary\"\n", "", 1)

RELEASE_PLAN_UNKNOWN_KEY = VALID_RELEASE_PLAN.replace(
    "checklist-complete: false\n", "checklist-complete: false\nnot-a-real-field: surprise\n", 1)

# review.schema.json: a dispatched plab-ai-review document. Unlike the other three
# document types, a review carries frontmatter ONLY when A-02's dispatch flag was used;
# the overwhelming majority of `_reviewed-by-` files carry none at all and are skipped
# (see SKIPPING FILES WITH NO FRONTMATTER IS DELIBERATE above) - this fixture covers the
# minority that do. `dispatch-job` matches the real job id shape codex-companion.mjs's
# generateJobId() produces: "<prefix>-<base36 timestamp>-<base36 random>".
VALID_REVIEW = """---
type: review
dispatch-job: task-mvaign5s-0pq15s
---

# AI Review: Canary
"""

REVIEW_BAD_DISPATCH_JOB_PATTERN = VALID_REVIEW.replace(
    "dispatch-job: task-mvaign5s-0pq15s", "dispatch-job: not-a-job-id", 1)

REVIEW_MISSING_DISPATCH_JOB = VALID_REVIEW.replace("dispatch-job: task-mvaign5s-0pq15s\n", "", 1)

REVIEW_UNKNOWN_KEY = VALID_REVIEW.replace(
    "dispatch-job: task-mvaign5s-0pq15s\n",
    "dispatch-job: task-mvaign5s-0pq15s\nreviewer: codex\n",
    1,
)

# DEFECT B canary: a leading blank line before the opening fence must NOT exempt a real document.
LEADING_BLANK_THEN_SPEC = "\n" + SPEC_BAD_STATUS

# DEFECT E / null-item canary: a bare `null` list item must still be schema-checked (items are typed "string" here, so None correctly fails, proving items are routed through coercion at all - previously list items were never coerced, so a bare `null` item stayed the four-character string "null" and passed).
RELEASE_PLAN_NULL_LIST_ITEM = VALID_RELEASE_PLAN.replace(
    "includes: [X-01]", "includes: [X-01, null]", 1)

# DEFECT G canaries: comments and duplicate keys. The trailing comment sits on target-release specifically (not on an unconstrained free-text field like linked-effort) so this fixture is self-verifying: target-release has a pattern (^v\d+\.\d+\.\d+$), so if the trailing comment were ever NOT stripped, the field's value would include the comment text, fail the pattern, and this fixture would move from must_not_flag to flagged - the self-test would catch the regression itself rather than silently accepting an unstripped comment because the field had no pattern to violate.
SPEC_WITH_COMMENTS = VALID_SPEC.replace(
    "linked-effort: a plain-language description of where this came from, 2026-01-01",
    "# a full-line comment, should be skipped entirely\n"
    "linked-effort: a plain-language description of where this came from, 2026-01-01",
    1,
).replace(
    "target-release: v0.1.0",
    "target-release: v0.1.0  # trailing comment, must not become part of the value",
    1,
)

SPEC_DUPLICATE_KEY = VALID_SPEC.replace(
    "priority: P2\n", "priority: P2\npriority: P3\n", 1)

NO_FRONTMATTER = "# README\n\nJust prose, no frontmatter block at all.\n"

BROKEN_SCHEMA_JSON = json.dumps({
    "required": ["x"],
    "additionalProperties": False,
    "properties": {"x": {"type": "string", "minLength": 3}},
})


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _check_item_coercion(failures):
    """DEFECT G proof, isolated from the main fixture tree: list items are routed through the same schema-aware coercion as scalars. Uses a synthetic items:{"type":"integer"} node (none of the four real schemas need an integer-typed array today) so both directions are demonstrated: a bare numeric token coerces and validates, a bare non-numeric token stays a string and is correctly flagged against the integer item type."""
    int_items_node = {"type": "array", "items": {"type": "integer"}}
    fm = coerce_frontmatter(
        {"nums": ("list", [("5", False), ("abc", False), ("6", False)])},
        {"properties": {"nums": int_items_node}},
    )
    if fm["nums"] != [5, "abc", 6]:
        failures.append("  item coercion did not route bare tokens through the items schema: got %r" % (fm["nums"],))
        return
    node_findings = []
    validate_node(fm["nums"], int_items_node, "$.nums", node_findings)
    flagged_indices = {f[0] for f in node_findings}
    if "$.nums[1]" not in flagged_indices:
        failures.append("  a non-numeric list item against an integer items schema was NOT flagged")
    if "$.nums[0]" in flagged_indices or "$.nums[2]" in flagged_indices:
        failures.append("  a correctly-coerced integer list item was wrongly flagged")


def _check_onerror_wiring(fixture, failures):
    """DEFECT A proof (unit level, portable): find_markdown_files must not silently swallow an OS-level directory-listing error. A nonexistent directory triggers the same os.walk() onerror path a permissions failure on a real subdirectory would; the default onerror (None) would make os.walk() yield nothing and find_markdown_files() would return an empty list with no error at all, which is the exact fail-open this canary exists to catch."""
    try:
        find_markdown_files(os.path.join(fixture, "this-directory-does-not-exist"))
        failures.append("  find_markdown_files() did not raise when a directory could not be listed"
                        " (onerror not wired, or not re-raising)")
    except BrokenInput:
        pass
    except Exception as exc:  # noqa: BLE001
        failures.append("  find_markdown_files() raised the wrong exception type on a listing failure: %r" % exc)


def _check_zero_file_floor(failures):
    """DEFECT A proof: scanning a real, existing, but completely empty release-plans tree must not be indistinguishable from scanning nothing. Calls run() directly (the same function main() calls, minus sys.exit) so this canary observes the actual exit code the CLI would produce, not just scan()'s raw counts - a regression in run()'s own floor check (as opposed to scan()'s counting) is caught here too. Output is captured and discarded; it is not part of what this canary checks."""
    with tempfile.TemporaryDirectory() as empty_root:
        os.makedirs(os.path.join(empty_root, *SCAN_ROOT_REL), exist_ok=True)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = run(empty_root)
        if code != 2:
            failures.append("  expected run() to report BROKEN (exit 2) for an empty, "
                            "frontmatter-free release-plans tree, got exit code %d" % code)


def _check_non_utf8_broken(schemas, failures):
    """DEFECT G proof: a file that is not valid UTF-8 at all must be reported as BrokenInput, never surface an uncaught UnicodeDecodeError. Isolated in its own tempdir, not the main fixture tree, because a bad-byte file there would abort scan() partway through and wreck the checked/skipped count assertions the main fixture relies on."""
    with tempfile.TemporaryDirectory() as bad_byte_root:
        path = os.path.join(bad_byte_root, *SCAN_ROOT_REL, "x")
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "spec.md"), "wb") as fh:
            fh.write(b"---\ntitle: cp1252 byte \x92 here\ntype: spec\n---\n")
        try:
            scan(bad_byte_root, schemas)
            failures.append("  scan() did not raise on a non-UTF-8 byte; a UnicodeDecodeError may be "
                            "escaping uncaught")
        except BrokenInput:
            pass
        except Exception as exc:  # noqa: BLE001
            failures.append("  a non-UTF-8 byte raised the wrong exception type: %r" % exc)


def self_test():
    """Prove the parser, the validator, and the unsupported-keyword guard before trusting a clean run."""
    failures = []

    try:
        schemas = load_all_schemas()
    except (BrokenInput, SchemaBroken) as exc:
        print("BROKEN: could not load the real schema files needed to run the self-test: %s" % exc,
              file=sys.stderr)
        return False

    with tempfile.TemporaryDirectory() as fixture:
        release_plans = os.path.join(fixture, *SCAN_ROOT_REL)

        must_flag = {
            # spec.schema.json: bad pattern / bad enum / bad date pattern / wrong scalar type /
            # missing required / unexpected extra key.
            "canary/spec-bad-id/spec.md": SPEC_BAD_ID,
            "canary/spec-bad-status/spec.md": SPEC_BAD_STATUS,
            "canary/spec-bad-date/spec.md": SPEC_BAD_DATE,
            "canary/spec-wrong-type/spec.md": SPEC_WRONG_TYPE,
            "canary/spec-missing-required/spec.md": SPEC_MISSING_REQUIRED,
            "canary/spec-unknown-key/spec.md": SPEC_UNKNOWN_KEY,
            "canary/spec-bad-target-release/spec.md": SPEC_BAD_TARGET_RELEASE,
            "canary/spec-duplicate-key/spec.md": SPEC_DUPLICATE_KEY,
            "canary/leading-blank-then-spec/spec.md": LEADING_BLANK_THEN_SPEC,
            # implementation-plan.schema.json: same six categories. DEFECT F: this schema had NO
            # must-flag canary at all before this fix.
            "canary/plan-bad-id/implementation-plan.md": PLAN_BAD_ID,
            "canary/plan-bad-enum/implementation-plan.md": PLAN_BAD_ENUM,
            "canary/plan-bad-date/implementation-plan.md": PLAN_BAD_DATE,
            "canary/plan-wrong-type/implementation-plan.md": PLAN_WRONG_TYPE,
            "canary/plan-missing-required/implementation-plan.md": PLAN_MISSING_REQUIRED,
            "canary/plan-unknown-key/implementation-plan.md": PLAN_UNKNOWN_KEY,
            # release-plan.schema.json: same six categories (uses 'sequence' pattern in place of
            # 'id', which this schema does not have).
            "canary/release-bad-sequence/plan.md": RELEASE_PLAN_BAD_SEQUENCE,
            "canary/release-bad-enum/plan.md": RELEASE_PLAN_BAD_ENUM,
            "canary/release-bad-date/plan.md": RELEASE_PLAN_BAD_DATE,
            "canary/release-wrong-type/plan.md": RELEASE_PLAN_WRONG_TYPE,
            "canary/release-missing-required/plan.md": RELEASE_PLAN_MISSING_REQUIRED,
            "canary/release-unknown-key/plan.md": RELEASE_PLAN_UNKNOWN_KEY,
            "canary/release-null-list-item/plan.md": RELEASE_PLAN_NULL_LIST_ITEM,
            # review.schema.json: same must-flag discipline as the other three types -
            # a bad pattern, a missing required field, an unexpected extra key.
            "canary/review-bad-dispatch-job/spec_reviewed-by-codex.md": REVIEW_BAD_DISPATCH_JOB_PATTERN,
            "canary/review-missing-dispatch-job/spec_reviewed-by-codex.md": REVIEW_MISSING_DISPATCH_JOB,
            "canary/review-unknown-key/spec_reviewed-by-codex.md": REVIEW_UNKNOWN_KEY,
        }
        must_not_flag = {
            "anti-canary/spec/spec.md": VALID_SPEC,
            "anti-canary/spec-unassigned/spec.md": UNASSIGNED_SPEC,
            "anti-canary/spec-with-comments/spec.md": SPEC_WITH_COMMENTS,
            "anti-canary/plan/implementation-plan.md": VALID_IMPLEMENTATION_PLAN,
            "anti-canary/release/plan.md": VALID_RELEASE_PLAN,
            "anti-canary/release-sequence-04/plan.md": SEQUENCE_04,
            "anti-canary/release-sequence-09/plan.md": SEQUENCE_09,
            "anti-canary/release-sequence-10/plan.md": SEQUENCE_10,
            "anti-canary/release-sequence-12/plan.md": SEQUENCE_12,
            "anti-canary/no-frontmatter/README.md": NO_FRONTMATTER,
            # A dispatched review document is the minority case (most `_reviewed-by-`
            # files carry no frontmatter at all and are skipped, not checked here) -
            # this is the one that does, and it must validate cleanly.
            "anti-canary/review-dispatched/spec_reviewed-by-codex.md": VALID_REVIEW,
        }
        for rel, content in {**must_flag, **must_not_flag}.items():
            _write(os.path.join(release_plans, rel), content)

        findings, checked, skipped = scan(fixture, schemas)
        flagged_files = {f.split(": ", 1)[0] for f in findings}

        for rel in must_flag:
            expected = ("docs/internal/release-plans/" + rel)
            if expected not in flagged_files:
                failures.append("  should have been flagged but was not: %s" % rel)
        for rel in must_not_flag:
            expected = ("docs/internal/release-plans/" + rel)
            if expected in flagged_files:
                failures.append("  should NOT have been flagged but was: %s" % rel)
        # 1 fixture is skipped as frontmatter-free (NO_FRONTMATTER); 1 more (the duplicate-key
        # fixture) fails to parse at all and lands only in `findings`, the same way an unclosed
        # fence would - it is neither "checked" (validated against a schema) nor "skipped" (no
        # frontmatter present). Both are subtracted from the total fixture count below.
        skipped_count = 1
        structural_only_count = 1  # canary/spec-duplicate-key
        if skipped != skipped_count:
            failures.append("  expected exactly %d file(s) skipped as frontmatter-free, got %d"
                            % (skipped_count, skipped))
        expected_checked = len(must_flag) + len(must_not_flag) - skipped_count - structural_only_count
        if checked != expected_checked:
            failures.append("  expected %d files checked, got %d" % (expected_checked, checked))

        bad_schema_path = os.path.join(fixture, "not-a-real-schema.schema.json")
        _write(bad_schema_path, BROKEN_SCHEMA_JSON)
        try:
            load_schema(bad_schema_path)
            failures.append("  a schema using 'minLength' (unimplemented) was NOT rejected")
        except SchemaBroken:
            pass
        except Exception as exc:  # noqa: BLE001 - any other exception is also a self-test failure
            failures.append("  unsupported-keyword schema raised the wrong exception type: %r" % exc)

        _check_onerror_wiring(fixture, failures)

    _check_zero_file_floor(failures)
    _check_item_coercion(failures)
    _check_non_utf8_broken(schemas, failures)

    if failures:
        print("BROKEN: gate self-test failed, the detector is not trustworthy.", file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        return False

    print("gate self-test: PASS (%d canaries flagged, %d anti-canaries correctly ignored, "
          "1 unsupported-keyword schema correctly rejected, onerror wiring proved, "
          "zero-file floor proved, item coercion proved, non-UTF-8 byte proved)"
          % (len(must_flag), len(must_not_flag)))
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def default_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(root):
    """Run one full scan against `root` and return the process exit code that should follow (1 or 2; 0 means CLEAN). Assumes self_test() has already passed. Deliberately never calls sys.exit() itself, so this same logic - including the zero-file floor below - can be exercised directly by self_test()'s own canary (see _check_zero_file_floor), rather than being reachable only through a real CLI invocation that self_test() has no way to observe the exit code of."""
    try:
        schemas = load_all_schemas()
        findings, checked, skipped = scan(root, schemas)
    except (BrokenInput, SchemaBroken) as exc:
        print("BROKEN: %s" % exc, file=sys.stderr)
        return 2

    if findings:
        for f in findings:
            print(f)
        print("FINDINGS: %d problem(s) across %d file(s) checked (%d skipped, no frontmatter)."
              % (len(findings), checked, skipped), file=sys.stderr)
        return 1

    if checked == 0 and skipped == 0:
        print("BROKEN: 0 files checked and 0 skipped under %s; the scan surface may be empty, "
              "moved, or misdirected. Refusing to report CLEAN." % os.path.join(root, *SCAN_ROOT_REL),
              file=sys.stderr)
        return 2

    print("CLEAN: canary proved, %d file(s) validated, %d skipped (no frontmatter)." % (checked, skipped))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Canary-verified frontmatter field-validity gate for docs/internal/release-plans/.")
    ap.add_argument("--root", default=None,
                    help="repo root to scan (default: inferred from this script's location)")
    ap.add_argument("--self-test-only", action="store_true",
                    help="prove the detector and exit, scanning nothing")
    args = ap.parse_args()

    if not self_test():
        sys.exit(2)

    if args.self_test_only:
        sys.exit(0)

    root = args.root or default_root()
    sys.exit(run(root))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - the general rule: no unexpected exception is exit 1
        print("BROKEN: unexpected internal error (%s: %s)" % (type(exc).__name__, exc), file=sys.stderr)
        sys.exit(2)
