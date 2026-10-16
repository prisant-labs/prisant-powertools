#!/usr/bin/env python3
"""Fixture tests for dispatch.py (A-02, programmatic review dispatch).

Run: python skills/plab-ai-review/scripts/test-dispatch.py

No test framework required, matching
skills/plab-wrap-session/scripts/test-organize-logs.py's shape. Every case
runs against a throwaway review document in a temp directory and a fake
`codex-companion.mjs` (also written fresh into that temp directory, never a
committed fixture), so these tests never touch a real Codex and never touch
the real companion helper under ~/.claude/plugins/cache/.

THE CANARY THIS FILE EXISTS TO PROVE
-------------------------------------
Case 10 (dimension mismatch) is the canary for AC-5's three-state contract
applied to collection: a reviewer that answers the wrong dimensions must
produce the `unparseable` state with the document's reviewer placeholders
left untouched, never a partial splice that fills some dimensions and
silently skips others. Comment out the `doc_dims != parsed_dims` guard in
dispatch.py's `splice_findings()` and this case is the one that starts
failing (the document would show one real dimension answered and "Dimension
Two" still carrying its placeholder text, but the overall call would report
`collected` as if the review were complete).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "dispatch.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


FAKE_COMPANION = r"""#!/usr/bin/env node
// Fake codex-companion.mjs for dispatch.py's test suite. Controlled entirely
// via environment variables; never touches a real Codex.
const [subcommand, ...argv] = process.argv.slice(2);

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + "\n");
}

const mode = process.env.FAKE_COMPANION_MODE || "ok";

if (subcommand === "task") {
  if (mode === "submit-fail") {
    process.stderr.write("fake companion: submission failed\n");
    process.exit(1);
  }
  if (mode === "submit-bad-json") {
    process.stdout.write("not json\n");
    process.exit(0);
  }
  if (mode === "submit-no-job-id") {
    out({ status: "queued" });
    process.exit(0);
  }
  out({
    jobId: process.env.FAKE_COMPANION_JOB_ID || "task-fake00-000001",
    status: "queued",
    title: "Codex Task",
    summary: "fake",
  });
  process.exit(0);
} else if (subcommand === "result") {
  if (mode === "lookup-fail") {
    process.stderr.write("No job found for \"" + (argv[0] || "") + "\".\n");
    process.exit(1);
  }
  if (mode === "bad-json") {
    process.stdout.write("not json\n");
    process.exit(0);
  }
  const status = process.env.FAKE_COMPANION_JOB_STATUS || "completed";
  const rawOutput = process.env.FAKE_COMPANION_RAW_OUTPUT || "";
  out({
    job: { id: argv[0] || "task-fake00-000001", status },
    storedJob: {
      errorMessage: process.env.FAKE_COMPANION_ERROR_MESSAGE || null,
      result: { rawOutput },
    },
    sawSessionEnv: process.env.CODEX_COMPANION_SESSION_ID || null,
  });
  process.exit(0);
} else {
  process.stderr.write("fake companion: unknown subcommand " + subcommand + "\n");
  process.exit(1);
}
"""

REVIEW_DOC = """# AI Review: Canary Doc

**Document:** `doc.md`

**Document type:** doc

**Date:** 2026-10-15

**Requestor:** Claude | **Reviewer:** Codex | **Human:** JP

---

## Reviewer Assessment

> **Reviewer - [LLM] ([date]):** [pending]

| Severity | Count |
|----------|-------|
| Blocker  | -     |
| Major    | -     |
| Minor    | -     |
| Note     | -     |

## Requestor Analysis & Proposed Actions

[P4: requestor fills after reviewing all findings]

### Decisions for JP

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|

## Instructions for Reviewer

**Your role:** Independent critical reviewer.

## Document Under Review

Canary source, two paragraphs.

## Findings

### Dimension One

*One sentence about dimension one.*

**Reviewer - [LLM] ([date]):**

> *Findings go here.* [P3]

**Requestor - [LLM] ([date]):**

> *Response goes here.* [P4]

---

### Dimension Two

*One sentence about dimension two.*

**Reviewer - [LLM] ([date]):**

> *Findings go here.* [P3]

**Requestor - [LLM] ([date]):**

> *Response goes here.* [P4]

---

## Proposed Actions

| # | Action | Target | Change | Triggered By |
|---|--------|--------|--------|-------------|
"""

GOOD_FINDINGS_JSON = json.dumps({
    "assessment": "Solid overall direction with one real gap in dimension two.",
    "severityCounts": {"blocker": 0, "major": 1, "minor": 1, "note": 0},
    "findings": [
        {"dimension": "Dimension One", "finding": "- [Minor | High] Nothing serious here. -> No action needed."},
        {"dimension": "Dimension Two", "finding": "- [Major | Medium] A real gap. -> Fix it before merging."},
    ],
})

MISMATCHED_FINDINGS_JSON = json.dumps({
    "assessment": "Reviewed under the wrong dimension names.",
    "severityCounts": {"blocker": 0, "major": 0, "minor": 0, "note": 1},
    "findings": [
        {"dimension": "Dimension One", "finding": "- [Note | Low] Fine. -> None."},
        {"dimension": "Totally Different Dimension", "finding": "- [Note | Low] Fine. -> None."},
    ],
})


def write_doc(case_dir: Path) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    doc = case_dir / "doc_reviewed-by-codex.md"
    doc.write_text(REVIEW_DOC, encoding="utf-8")
    return doc


def make_companion(root: Path) -> Path:
    path = root / "fake-companion.mjs"
    path.write_text(FAKE_COMPANION, encoding="utf-8")
    return path


def run(action: str, doc: Path, companion: Path, env_overrides: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.pop("CODEX_COMPANION_SESSION_ID", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(SCRIPT), action, str(doc), "--companion", str(companion)],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )


def parse_state(proc: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        companion = make_companion(root)

        # 1. submit: success path.
        doc = write_doc(root / "case1")
        proc = run("submit", doc, companion, {"FAKE_COMPANION_MODE": "ok", "FAKE_COMPANION_JOB_ID": "task-case1-abc123"})
        payload = parse_state(proc)
        check("submit success exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("submit success reports state=submitted", payload.get("state") == "submitted", proc.stdout)
        after = doc.read_text(encoding="utf-8")
        check("submit writes dispatch-job frontmatter", "dispatch-job: task-case1-abc123" in after, after[:200])
        check("submit writes type: review frontmatter", "type: review" in after, after[:200])
        check("submit leaves the body text intact", "### Dimension One" in after and "### Dimension Two" in after)

        # 2. submit: companion unavailable (bogus override path).
        doc = write_doc(root / "case2")
        bogus = root / "case2" / "does-not-exist.mjs"
        proc = run("submit", doc, bogus)
        payload = parse_state(proc)
        check("submit unavailable exits 1", proc.returncode == 1, proc.stdout + proc.stderr)
        check("submit unavailable reports state=unavailable", payload.get("state") == "unavailable", proc.stdout)
        check("submit unavailable leaves the document untouched", doc.read_text(encoding="utf-8") == REVIEW_DOC)

        # 3. submit: companion task invocation fails.
        doc = write_doc(root / "case3")
        proc = run("submit", doc, companion, {"FAKE_COMPANION_MODE": "submit-fail"})
        payload = parse_state(proc)
        check("submit failure exits 1", proc.returncode == 1, proc.stdout + proc.stderr)
        check("submit failure reports state=failed", payload.get("state") == "failed", proc.stdout)
        check("submit failure leaves the document untouched", doc.read_text(encoding="utf-8") == REVIEW_DOC)

        # 4. submit: companion returns no jobId.
        doc = write_doc(root / "case4")
        proc = run("submit", doc, companion, {"FAKE_COMPANION_MODE": "submit-no-job-id"})
        payload = parse_state(proc)
        check("submit with no jobId exits 1", proc.returncode == 1)
        check("submit with no jobId reports state=failed", payload.get("state") == "failed", proc.stdout)
        check("submit with no jobId leaves the document untouched", doc.read_text(encoding="utf-8") == REVIEW_DOC)

        # 5. submit: document has no dimensions at all.
        no_dims = root / "case5"
        no_dims.mkdir()
        empty_doc = no_dims / "empty_reviewed-by-codex.md"
        empty_doc.write_text("# AI Review: Nothing\n\n## Findings\n\n## Proposed Actions\n", encoding="utf-8")
        proc = run("submit", empty_doc, companion)
        payload = parse_state(proc)
        check("submit with no dimensions exits 1", proc.returncode == 1)
        check("submit with no dimensions reports state=failed", payload.get("state") == "failed", proc.stdout)

        # 6. collect: no dispatch-job field present (never submitted).
        doc = write_doc(root / "case6")
        proc = run("collect", doc, companion)
        payload = parse_state(proc)
        check("collect with no dispatch-job exits 1", proc.returncode == 1)
        check("collect with no dispatch-job reports state=failed", payload.get("state") == "failed", proc.stdout)

        # Helper: a doc already carrying a dispatch-job field, as submit would leave it.
        def dispatched_doc(case_dir: Path, job_id: str = "task-caseN-abc123") -> Path:
            case_dir.mkdir(exist_ok=True)
            doc = case_dir / "doc_reviewed-by-codex.md"
            doc.write_text("---\ntype: review\ndispatch-job: %s\n---\n\n%s" % (job_id, REVIEW_DOC), encoding="utf-8")
            return doc

        # 7. collect: job still running.
        doc = dispatched_doc(root / "case7")
        before = doc.read_text(encoding="utf-8")
        proc = run("collect", doc, companion, {"FAKE_COMPANION_MODE": "ok", "FAKE_COMPANION_JOB_STATUS": "running"})
        payload = parse_state(proc)
        check("collect running exits 1", proc.returncode == 1)
        check("collect running reports state=running", payload.get("state") == "running", proc.stdout)
        check("collect running leaves the document untouched", doc.read_text(encoding="utf-8") == before)

        # 8. collect: job failed.
        doc = dispatched_doc(root / "case8")
        before = doc.read_text(encoding="utf-8")
        proc = run("collect", doc, companion, {
            "FAKE_COMPANION_MODE": "ok", "FAKE_COMPANION_JOB_STATUS": "failed",
            "FAKE_COMPANION_ERROR_MESSAGE": "Codex CLI exited with an auth error.",
        })
        payload = parse_state(proc)
        check("collect job-failed exits 1", proc.returncode == 1)
        check("collect job-failed reports state=failed", payload.get("state") == "failed", proc.stdout)
        check("collect job-failed surfaces the error message",
              "auth error" in payload.get("message", ""), proc.stdout)
        check("collect job-failed leaves the document untouched", doc.read_text(encoding="utf-8") == before)

        # 9. collect: companion lookup fails outright (e.g. wrong workspace root).
        doc = dispatched_doc(root / "case9")
        before = doc.read_text(encoding="utf-8")
        proc = run("collect", doc, companion, {"FAKE_COMPANION_MODE": "lookup-fail"})
        payload = parse_state(proc)
        check("collect lookup-fail exits 1", proc.returncode == 1)
        check("collect lookup-fail reports state=failed", payload.get("state") == "failed", proc.stdout)
        check("collect lookup-fail leaves the document untouched", doc.read_text(encoding="utf-8") == before)

        # 10. collect: completed, but the reviewer answered the wrong dimensions.
        #     This is this file's canary; see the module docstring.
        doc = dispatched_doc(root / "case10")
        before = doc.read_text(encoding="utf-8")
        proc = run("collect", doc, companion, {
            "FAKE_COMPANION_MODE": "ok", "FAKE_COMPANION_JOB_STATUS": "completed",
            "FAKE_COMPANION_RAW_OUTPUT": MISMATCHED_FINDINGS_JSON,
        })
        payload = parse_state(proc)
        check("collect dimension-mismatch exits 1", proc.returncode == 1)
        check("collect dimension-mismatch reports state=unparseable", payload.get("state") == "unparseable", proc.stdout)
        check("collect dimension-mismatch leaves the document untouched", doc.read_text(encoding="utf-8") == before)
        raw_path = payload.get("rawOutputPath")
        check("collect dimension-mismatch saves the raw output",
              bool(raw_path) and Path(raw_path).exists(), proc.stdout)
        if raw_path and Path(raw_path).exists():
            check("the saved raw output is exactly what the fake reviewer returned",
                  Path(raw_path).read_text(encoding="utf-8") == MISMATCHED_FINDINGS_JSON)

        # 11. collect: completed, output is not JSON at all.
        doc = dispatched_doc(root / "case11")
        before = doc.read_text(encoding="utf-8")
        proc = run("collect", doc, companion, {"FAKE_COMPANION_MODE": "bad-json"})
        payload = parse_state(proc)
        check("collect bad-json exits 1", proc.returncode == 1)
        check("collect bad-json reports state=failed", payload.get("state") == "failed", proc.stdout)
        # bad-json makes the OUTER `result --json` call itself unparseable (a companion
        # bug), distinct from case 12 below where the call succeeds but the raw task
        # output nested inside it is not the findings JSON.
        check("collect bad-json leaves the document untouched", doc.read_text(encoding="utf-8") == before)

        # 12. collect: result call succeeds, but the task's own raw output is garbage.
        doc = dispatched_doc(root / "case12")
        before = doc.read_text(encoding="utf-8")
        proc = run("collect", doc, companion, {
            "FAKE_COMPANION_MODE": "ok", "FAKE_COMPANION_JOB_STATUS": "completed",
            "FAKE_COMPANION_RAW_OUTPUT": "I looked at the document and it seems fine overall.",
        })
        payload = parse_state(proc)
        check("collect garbage-output exits 1", proc.returncode == 1)
        check("collect garbage-output reports state=unparseable", payload.get("state") == "unparseable", proc.stdout)
        check("collect garbage-output leaves the document untouched", doc.read_text(encoding="utf-8") == before)

        # 13. collect: companion unavailable (job id preserved for a later attempt).
        doc = dispatched_doc(root / "case13")
        before = doc.read_text(encoding="utf-8")
        bogus13 = root / "case13" / "does-not-exist.mjs"
        proc = run("collect", doc, bogus13)
        payload = parse_state(proc)
        check("collect unavailable exits 1", proc.returncode == 1)
        check("collect unavailable reports state=unavailable", payload.get("state") == "unavailable", proc.stdout)
        check("collect unavailable preserves the dispatch-job field", "dispatch-job:" in doc.read_text(encoding="utf-8"))

        # 14. collect: the success path, end to end. This is the AC-1/AC-6 proof at
        #     the unit level: findings land in the placeholders, the Requestor
        #     sections and the rest of the document are untouched, and the shape
        #     --respond expects is preserved.
        doc = dispatched_doc(root / "case14", job_id="task-case14-xyz789")
        proc = run("collect", doc, companion, {
            "FAKE_COMPANION_MODE": "ok", "FAKE_COMPANION_JOB_STATUS": "completed",
            "FAKE_COMPANION_RAW_OUTPUT": GOOD_FINDINGS_JSON,
        })
        payload = parse_state(proc)
        check("collect success exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
        check("collect success reports state=collected", payload.get("state") == "collected", proc.stdout)
        result_text = doc.read_text(encoding="utf-8")
        check("collect success retains the dispatch-job field",
              "dispatch-job: task-case14-xyz789" in result_text)
        check("collect success fills the Reviewer Assessment attribution",
              "> **Reviewer - Codex (" in result_text)
        check("collect success fills the Reviewer Assessment content",
              "Solid overall direction with one real gap in dimension two." in result_text)
        check("collect success fills the Major severity count",
              "| Major    | 1     |" in result_text, result_text)
        check("collect success fills Dimension One's finding",
              "Nothing serious here." in result_text)
        check("collect success fills Dimension Two's finding",
              "A real gap." in result_text)
        check("collect success does not touch the Requestor placeholder",
              "*Response goes here.* [P4]" in result_text)
        check("collect success does not touch Requestor Analysis",
              "[P4: requestor fills after reviewing all findings]" in result_text)
        check("collect success replaces both reviewer placeholder blockquotes",
              "*Findings go here.* [P3]" not in result_text, result_text)

        # 15. discover_companion() picks the highest installed version.
        versions_root = root / "versions" / ".claude" / "plugins" / "cache" / "openai-codex" / "codex"
        for v in ("1.0.0", "1.0.6", "1.2.0", "9.0.0-not-semver"):
            vdir = versions_root / v / "scripts"
            vdir.mkdir(parents=True)
            (vdir / "codex-companion.mjs").write_text("// v%s\n" % v, encoding="utf-8")
        sys.path.insert(0, str(SCRIPT.parent))
        import importlib
        dispatch = importlib.import_module("dispatch")
        old_home = os.environ.get("HOME")
        old_userprofile = os.environ.get("USERPROFILE")
        os.environ["HOME"] = str(root / "versions")
        os.environ["USERPROFILE"] = str(root / "versions")
        try:
            found = dispatch.discover_companion(None)
        finally:
            if old_home is not None:
                os.environ["HOME"] = old_home
            else:
                os.environ.pop("HOME", None)
            if old_userprofile is not None:
                os.environ["USERPROFILE"] = old_userprofile
            else:
                os.environ.pop("USERPROFILE", None)
        check("discover_companion() picks the highest numeric version",
              found is not None and os.sep + "1.2.0" + os.sep in found, str(found))

    failed = [name for name, ok, _ in results if not ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed.")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
