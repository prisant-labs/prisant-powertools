#!/usr/bin/env python3
"""One post-write Log Self-Check gate for a drafted plab-wrap-session log.

Runs every mechanical gate SKILL.md's Log Self-Check section lists, in one
invocation, instead of the agent running each one as its own call. A clean
1.8.0 wrap still ran `derive-log-facts.py`, the repository's own validation
scripts, the write, `--count-decisions`, and then `path-citation-check.py`
and `dash-check.py` as two more separate calls, plus fixes: six to nine
calls total. This script collapses the last three (decisions count,
path-citation, dash) and six more agent-judged rules into this single call,
run once after the log is written.

EXIT-CODE CONTRACT
------------------
  0  CLEAN    every mechanical gate passed
  1  FINDINGS at least one gate found a real problem, no gate was broken
  2  BROKEN   a gate could not prove itself, the log could not be read, or
              `derive-log-facts.py` could not be imported

NEVER INTERPRET 2 AS CLEAN. `scripts/path-citation-check.py` and
`scripts/dash-check.py` are canary-verified and three-state already; this
script calls them as they are and keeps their own canaries and contracts
intact. If either one reports broken (its own self-test failed, or it could
not read the log), that makes this script's own result broken, because a
gate built out of a broken gate cannot itself be clean. The remaining checks
below have no embedded self-test of their own; they are proved instead by
`test-check-log.py`'s fixture logs and canary, the same split
`derive-log-facts.py` and `test-derive-log-facts.py` already use for a
multi-check orchestrator rather than a single pattern detector.

WHY THIS IS NOT A FULL YAML PARSER
-----------------------------------
`parse_frontmatter_block()` and `frontmatter_field()` read the frontmatter
block as flat `key: value` lines at column 0, the same shape
`derive-log-facts.py` already assumes when it reads a log's `date:` line.
A full YAML parser is not needed and is not stdlib; this script only ever
needs one field's raw value at a time, never a nested structure.

WHY TIER 1 IS CHECKED THE SAME WAY IN EVERY MODE
----------------------------------------------------
`references/frontmatter-schema.md` titles Tier 1 "Essential (Always
Include)" with no per-mode carve-out, and 1.8.0 moved `commit-range` and
`latest-tag` into that tier alongside the five fields already there. This
script checks all nine fields for presence in every mode. The Quick and
Blocked templates in `references/session-log-template.md` have not been
updated to list the two new fields; a quick or blocked log written from
those templates as they stand today will correctly be flagged here. That
template gap is real and is not this script's job to close; surfacing it
is the fail-open-by-omission gates in this repository exist to prevent (see
`scripts/doc-lifecycle-check.py`'s docstring for the same principle applied
to cross-file drift).

Six of the nine fields (`date`, `type`, `machine`, `repo`, `branch`,
`summary`) must be present AND non-empty: `derive-log-facts.py` always
supplies a real value for the first five, and the agent always writes a
real summary. The other three (`files-changed`, `commit-range`,
`latest-tag`) are checked for presence only, because all three have a
legitimate empty-looking value: `files-changed: []` for a session that
changed nothing tracked, and `commit-range: null` / `latest-tag: null`
for a repository with no base ref or no tags yet.

WHY A MISSING FRONTMATTER BLOCK IS A FINDING, NOT BROKEN
-------------------------------------------------------------
A log with an unclosed or absent `---` fence is parsed as an empty
frontmatter block rather than aborting the run. Every field-dependent check
then reports its own missing-field finding, exactly as it would for a log
that has a frontmatter block but omits one field. This mirrors
`doc-lifecycle-check.py`'s rule: a document whose content does not conform
to the expected shape is a finding against that one document, not a reason
to call the detector itself broken.

WHY DECISIONS-COUNT IS SKIPPED, NOT FAILED, IN QUICK AND BLOCKED MODE
--------------------------------------------------------------------------
Neither mode's template (`references/session-log-template.md`) carries a
`## Decisions Made` section or a `decisions-count` frontmatter field. A
missing field that was never supposed to be there is not a finding; it is
reported as `skipped` so the overall result stays clean rather than
accumulating noise a quick wrap can never satisfy.

WHY THE WAITING-ON-YOU "OPTIONAL" CHECK STRIPS MARKDOWN EMPHASIS FIRST
---------------------------------------------------------------------------
The 1.6.0 defect this gate was built to catch was four items prefixed
`**Optional:**`, bold markdown around the word, not the bare word itself.
`normalize_waiting_item()` strips the leading bullet and any run of `*` or
`_` before testing for a leading "optional" (case-insensitive), so bold,
italic, and plain forms are all caught.

WHY EVERY SUBPROCESS CALL PINS encoding="utf-8" AND PYTHONIOENCODING
-------------------------------------------------------------------------
`dash-check.py` prints the offending line, which by construction contains
an em-dash or en-dash, to stdout when it finds one. Python's subprocess
text-mode decoding and the child's own stdout encoding both default to the
locale encoding absent an override, which is cp1252 on this maintainer's
machine and cannot represent either character; `doc-lifecycle-check.py`'s
docstring records the same failure mode for a different subprocess call in
this repository. Both the parent's `subprocess.run(encoding=...)` and the
child's `PYTHONIOENCODING` environment variable are set to `utf-8` here so
neither side can silently drop or mis-decode the exact bytes the dash gate
exists to find.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PATH_CITATION_SCRIPT = SCRIPT_DIR / "path-citation-check.py"
DASH_CHECK_SCRIPT = SCRIPT_DIR / "dash-check.py"
DERIVE_LOG_FACTS_SCRIPT = SCRIPT_DIR / "derive-log-facts.py"

MODES = ("deep", "final", "quick", "blocked")

# references/frontmatter-schema.md Tier 1, "Always Include", no per-mode
# exception. See the module docstring for why these two groups are checked
# differently.
TIER1_REQUIRE_NONEMPTY = ["date", "type", "machine", "repo", "branch", "summary"]
TIER1_REQUIRE_PRESENT_ONLY = ["files-changed", "commit-range", "latest-tag"]

BLOCKED_SINCE_RE = re.compile(r"\(blocked since \d{4}-\d{2}-\d{2}\)")


# ---------------------------------------------------------------------------
# derive-log-facts.py reuse
# ---------------------------------------------------------------------------

def load_derive_log_facts():
    """Import derive-log-facts.py as a module, so decisions-counting and
    section-extraction logic is reused rather than copied. The filename is
    hyphenated, so a plain `import` statement cannot name it."""
    spec = importlib.util.spec_from_file_location(
        "wrap_session_derive_log_facts", DERIVE_LOG_FACTS_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a module spec for {DERIVE_LOG_FACTS_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def read_log(log_path: Path) -> str:
    # utf-8-sig so a UTF-8 byte-order mark does not attach itself to the
    # opening '---' fence, the same reasoning path-citation-check.py uses.
    return log_path.read_text(encoding="utf-8-sig")


def parse_frontmatter_block(text: str) -> str:
    """Return the raw text between the first two '---' fence lines, or an
    empty string when there is no such block. See the module docstring for
    why that case is a finding, not an abort."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i])
    return ""


def frontmatter_field(frontmatter: str, field: str) -> str | None:
    """The first `field: value` line at column 0 inside the frontmatter
    block, or None when the key never appears. The value is returned raw,
    not unquoted."""
    pattern = re.compile(rf"^{re.escape(field)}:[ \t]*(.*)$", re.MULTILINE)
    match = pattern.search(frontmatter)
    return match.group(1) if match else None


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


# ---------------------------------------------------------------------------
# Detector subprocess wrapper (path-citation-check.py, dash-check.py)
# ---------------------------------------------------------------------------

def run_detector_script(script: Path, args: list[str]) -> dict:
    """Run a sibling canary-verified detector script and classify its exit
    code into the three-state contract the two scripts already share.
    Never raises; a launch failure (missing interpreter, missing file) is
    reported as broken rather than propagated."""
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"state": "broken", "detail": [f"could not run {script.name}: {exc}"]}
    if proc.returncode == 0:
        return {"state": "clean", "detail": proc.stdout.strip() or "clean"}
    if proc.returncode == 1:
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        return {"state": "findings", "detail": lines or ["findings reported with no detail line"]}
    detail = (proc.stdout + proc.stderr).strip()
    return {"state": "broken", "detail": [detail or f"{script.name} exited {proc.returncode}"]}


# ---------------------------------------------------------------------------
# Mechanical checks
# ---------------------------------------------------------------------------

def check_decisions_count(text: str, frontmatter: str, mode: str, dlf) -> dict:
    if mode in ("quick", "blocked"):
        return {"state": "skipped", "detail": f"no Decisions Made section in {mode} mode"}
    mechanical = dlf.count_decisions(text)
    raw = frontmatter_field(frontmatter, "decisions-count")
    if raw is None or not raw.strip():
        return {"state": "findings", "detail": ["decisions-count is missing from the frontmatter"]}
    try:
        declared = int(raw.strip())
    except ValueError:
        return {"state": "findings", "detail": [f"decisions-count '{raw.strip()}' is not an integer"]}
    if declared != mechanical:
        return {
            "state": "findings",
            "detail": [
                f"decisions-count in the frontmatter is {declared}, but the Decisions Made "
                f"section has {mechanical} entries"
            ],
        }
    return {"state": "clean", "detail": f"decisions-count {declared} matches the Decisions Made section"}


def check_summary_length(frontmatter: str) -> dict:
    raw = frontmatter_field(frontmatter, "summary")
    if raw is None or not raw.strip():
        return {"state": "findings", "detail": ["summary is missing from the frontmatter"]}
    value = unquote(raw)
    if len(value) > 120:
        return {"state": "findings", "detail": [f"summary is {len(value)} characters, over the 120 limit"]}
    return {"state": "clean", "detail": f"summary is {len(value)} characters"}


def check_tier1_frontmatter(frontmatter: str) -> dict:
    findings = []
    for field in TIER1_REQUIRE_NONEMPTY:
        raw = frontmatter_field(frontmatter, field)
        if raw is None or not raw.strip():
            findings.append(f"Tier 1 field '{field}' is missing or empty")
    for field in TIER1_REQUIRE_PRESENT_ONLY:
        raw = frontmatter_field(frontmatter, field)
        if raw is None:
            findings.append(f"Tier 1 field '{field}' is missing")
    if findings:
        return {"state": "findings", "detail": findings}
    return {"state": "clean", "detail": "all 9 Tier 1 fields present"}


def normalize_waiting_item(line: str) -> str:
    """Strip the leading bullet ('- ' or '* ') and any markdown emphasis, so
    a bold or italic 'Optional' is caught the same as a plain one."""
    text = line.lstrip()
    if text.startswith("- ") or text.startswith("* "):
        text = text[2:]
    return text.lstrip("*_ ")


def check_waiting_on_you(text: str, dlf) -> dict:
    body = dlf.extract_section(text, "Waiting on You")
    if body is None:
        return {"state": "findings", "detail": ["Waiting on You section is missing"]}
    nonblank = [line for line in body if line.strip()]
    has_nothing_pending = any("nothing pending" in line.lower() for line in nonblank)
    bullets = dlf.extract_waiting_on_you(text) or []
    findings = []
    if not bullets and not has_nothing_pending:
        findings.append("Waiting on You has no items and does not say 'Nothing pending.'")
    for bullet in bullets:
        if not BLOCKED_SINCE_RE.search(bullet):
            findings.append(f"Waiting on You item missing '(blocked since YYYY-MM-DD)': {bullet.strip()}")
        if normalize_waiting_item(bullet).lower().startswith("optional"):
            findings.append(f"Waiting on You item begins with 'Optional': {bullet.strip()}")
    if findings:
        return {"state": "findings", "detail": findings}
    detail = f"{len(bullets)} item(s), each dated, none optional" if bullets else "Nothing pending."
    return {"state": "clean", "detail": detail}


def check_section_present(text: str, dlf, heading: str, empty_marker: str) -> dict:
    body = dlf.extract_section(text, heading)
    if body is None:
        return {"state": "findings", "detail": [f"{heading} section is missing"]}
    nonblank = [line.strip() for line in body if line.strip()]
    if not nonblank:
        return {
            "state": "findings",
            "detail": [f"{heading} section is empty; write '{empty_marker}' explicitly"],
        }
    return {"state": "clean", "detail": f"{heading} section present"}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_all_checks(log_path: Path, repo_root: str, mode: str) -> dict:
    text = read_log(log_path)
    dlf = load_derive_log_facts()
    frontmatter = parse_frontmatter_block(text)

    results: dict[str, dict] = {}
    results["path-citations"] = run_detector_script(
        PATH_CITATION_SCRIPT, [str(log_path), "--repo-root", repo_root]
    )
    results["dashes"] = run_detector_script(DASH_CHECK_SCRIPT, [str(log_path)])
    results["decisions-count"] = check_decisions_count(text, frontmatter, mode, dlf)
    results["summary-length"] = check_summary_length(frontmatter)
    results["tier1-frontmatter"] = check_tier1_frontmatter(frontmatter)
    results["waiting-on-you"] = check_waiting_on_you(text, dlf)
    if mode == "deep":
        results["uncertainty-ledger"] = check_section_present(
            text, dlf, "Uncertainty Ledger", "Nothing material."
        )
        results["what-you-may-not-realize"] = check_section_present(
            text, dlf, "What You May Not Realize", "Nothing surfaced."
        )
    return results


def overall_state(results: dict) -> str:
    states = {result["state"] for result in results.values()}
    if "broken" in states:
        return "broken"
    if "findings" in states:
        return "findings"
    return "clean"


def render_text(results: dict, overall: str, log_path: Path) -> None:
    for name, result in sorted(results.items()):
        state = result["state"]
        detail = result["detail"]
        lines = detail if isinstance(detail, list) else [detail]
        for line in lines:
            print(f"{state.upper():9} {name}: {line}")

    finding_count = sum(
        len(result["detail"]) if isinstance(result["detail"], list) else 1
        for result in results.values()
        if result["state"] == "findings"
    )
    if overall == "clean":
        print(f"CLEAN: every mechanical Log Self-Check gate passed for {log_path}")
    elif overall == "findings":
        print(
            f"FINDINGS: {finding_count} issue(s) across the Log Self-Check gates.",
            file=sys.stderr,
        )
    else:
        print(
            "BROKEN: at least one gate could not prove itself. Do NOT read this as a clean log.",
            file=sys.stderr,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-call Log Self-Check gate for a drafted plab-wrap-session log."
    )
    parser.add_argument("log_path", help="the drafted session log to check")
    parser.add_argument(
        "--repo-root", default=os.getcwd(),
        help="the project being wrapped (default: cwd), passed through to path-citation-check.py",
    )
    parser.add_argument(
        "--mode", choices=MODES, default="deep",
        help="which mode's gates apply (default: deep)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log_path = Path(args.log_path)

    try:
        results = run_all_checks(log_path, args.repo_root, args.mode)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"BROKEN: could not read {log_path}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - converted to BROKEN, never left as a bare traceback
        print(f"BROKEN: could not run the Log Self-Check: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    overall = overall_state(results)

    if args.json:
        print(json.dumps({"overall": overall, "mode": args.mode, "checks": results}, indent=2))
    else:
        render_text(results, overall, log_path)

    return {"clean": 0, "findings": 1, "broken": 2}[overall]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - the backstop for anything unanticipated above
        print(f"BROKEN: unexpected {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
