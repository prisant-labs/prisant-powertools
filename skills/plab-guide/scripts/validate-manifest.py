#!/usr/bin/env python3
"""validate-manifest.py

Validate a MANIFEST.yaml file produced by plab-guide against the schema
defined in the spec.

Usage:
    scripts/validate-manifest.py <manifest-path>

Exit codes:
    0 - valid
    1 - schema violation (errors printed to stderr)
    2 - file not found or unreadable
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("error: pyyaml not installed (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


REQUIRED_TOP_KEYS = {
    "schema",
    "topic",
    "slug",
    "input_type",
    "generated",
    "generator_version",
    "input",
    "research",
    "artifacts",
}

ALLOWED_INPUT_TYPES = {"repo-url", "tool", "concept"}
# "low-confidence draft" is the value SKILL.md, both templates and the references
# tell the agent to write. "low-confidence" is still accepted so that manifests
# written before 2.2.3 keep validating.
ALLOWED_CONFIDENCE = {"high", "medium", "low-confidence draft", "low-confidence"}
ALLOWED_CREDIBILITY = {"A", "B", "C"}
# Core artifact types every bundle should produce.
RECOMMENDED_ARTIFACT_TYPES = {
    "explanatory-standard",
    "explanatory-adhd",
    "quick-reference-html",
    "quick-reference-pdf",
}
# All permitted types. v2.1.0 adds external Mermaid diagram SVGs:
# lib/render-mermaid.py writes <slug>_diagram-N.svg files referenced by <img>.
ALLOWED_ARTIFACT_TYPES = RECOMMENDED_ARTIFACT_TYPES | {"quick-reference-diagram"}


def err(msg: str, errors: list) -> None:
    errors.append(msg)


def validate_top_keys(m: dict, errors: list) -> None:
    missing = REQUIRED_TOP_KEYS - set(m.keys())
    if missing:
        err(f"missing required top-level keys: {sorted(missing)}", errors)


def validate_schema(m: dict, errors: list) -> None:
    schema = m.get("schema")
    if schema != "plab-guide/v1":
        err(f"schema mismatch: got {schema!r}, expected 'plab-guide/v1'", errors)


def validate_input_type(m: dict, errors: list) -> None:
    it = m.get("input_type")
    if it not in ALLOWED_INPUT_TYPES:
        err(f"input_type must be one of {sorted(ALLOWED_INPUT_TYPES)}; got {it!r}", errors)


def validate_research(m: dict, errors: list) -> None:
    r = m.get("research", {})
    if not isinstance(r, dict):
        err("research: must be a mapping", errors)
        return
    sc = r.get("source_count")
    if not isinstance(sc, int) or sc < 0:
        err(f"research.source_count: must be a non-negative integer; got {sc!r}", errors)
    sbc = r.get("sources_by_class", {})
    if not isinstance(sbc, dict):
        err("research.sources_by_class: must be a mapping with keys A, B, C", errors)
    else:
        bad = set(sbc.keys()) - ALLOWED_CREDIBILITY
        if bad:
            err(f"research.sources_by_class: unexpected keys {sorted(bad)}", errors)
        if isinstance(sc, int):
            total = sum(v for v in sbc.values() if isinstance(v, int))
            if total != sc:
                err(
                    f"research.source_count ({sc}) != sum of sources_by_class ({total})",
                    errors,
                )
    conf = r.get("confidence")
    if conf not in ALLOWED_CONFIDENCE:
        err(
            f"research.confidence: must be one of {sorted(ALLOWED_CONFIDENCE)}; got {conf!r}",
            errors,
        )


def validate_artifacts(m: dict, manifest_path: Path, errors: list) -> None:
    arts = m.get("artifacts", [])
    if not isinstance(arts, list):
        err("artifacts: must be a list", errors)
        return
    if len(arts) < 1:
        err("artifacts: must have at least one entry", errors)
    seen_types = set()
    output_dir = manifest_path.parent
    for i, a in enumerate(arts):
        if not isinstance(a, dict):
            err(f"artifacts[{i}]: must be a mapping", errors)
            continue
        path = a.get("path")
        atype = a.get("type")
        if atype not in ALLOWED_ARTIFACT_TYPES:
            err(
                f"artifacts[{i}].type: must be one of {sorted(ALLOWED_ARTIFACT_TYPES)}; got {atype!r}",
                errors,
            )
        seen_types.add(atype)
        if not isinstance(path, str):
            err(f"artifacts[{i}].path: must be a string", errors)
        else:
            full = output_dir / path
            if not full.exists():
                err(f"artifacts[{i}].path: file does not exist on disk: {full}", errors)
        if atype == "quick-reference-pdf":
            pages = a.get("pages")
            if not isinstance(pages, int) or pages < 1:
                err(f"artifacts[{i}].pages: must be a positive integer; got {pages!r}", errors)
            elif pages > 2:
                err(
                    f"artifacts[{i}].pages: expected 1 or 2 (G-8, v2.0.0 auto-fit); got {pages} (warning)",
                    errors,
                )
    # Recommended: all 4 core artifact types present (diagram SVGs are optional).
    expected = RECOMMENDED_ARTIFACT_TYPES
    missing = expected - seen_types
    if missing:
        err(f"artifacts: missing recommended types {sorted(missing)} (warning)", errors)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate-manifest.py <manifest-path>", file=sys.stderr)
        return 1

    manifest_path = Path(argv[1])
    if not manifest_path.is_file():
        print(f"error: file not found: {manifest_path}", file=sys.stderr)
        return 2

    try:
        text = manifest_path.read_text(encoding="utf-8")
        m = yaml.safe_load(text)
    except (OSError, yaml.YAMLError) as e:
        print(f"error: could not read or parse {manifest_path}: {e}", file=sys.stderr)
        return 2

    if not isinstance(m, dict):
        print("error: manifest top level must be a mapping", file=sys.stderr)
        return 1

    errors: list[str] = []
    validate_top_keys(m, errors)
    validate_schema(m, errors)
    validate_input_type(m, errors)
    validate_research(m, errors)
    validate_artifacts(m, manifest_path, errors)

    if errors:
        print(f"validation failed for {manifest_path}:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"ok: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
