#!/usr/bin/env python3
"""Fixture tests for check-log.py. No test framework required.

Run: python skills/plab-wrap-session/scripts/test-check-log.py

Every case writes a throwaway log file and a throwaway --repo-root into a
temp directory, matching the precedent set by test-organize-logs.py and
test-derive-log-facts.py in this same directory. Most cases run check-log.py
against this skill's own real path-citation-check.py, dash-check.py, and
derive-log-facts.py, which is deliberate integration coverage; two cases
(missing-siblings, stub-detector-broken) run it from a scratch copy of the
scripts directory instead, so they can exercise a missing or broken sibling
without ever touching the shipped detectors.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "check-log.py"

EM_DASH = chr(0x2014)
CROSS = chr(0x274C)  # never the literal glyph in a committed file

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def run_check(log_path: Path, root: Path, mode: str = "deep", json_out: bool = True):
    args = [sys.executable, str(SCRIPT), str(log_path), "--repo-root", str(root), "--mode", mode]
    if json_out:
        args.append("--json")
    return subprocess.run(
        args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
    )


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

DEFAULT_FIELDS = {
    "date": "2026-10-16T09:00:00-07:00",
    "type": "session-log",
    "machine": "test-machine",
    "repo": "acme/example",
    "branch": "main",
    "summary": '"A short fixture summary"',
    "files-changed": "[]",
    "commit-range": "aaaaaaa..bbbbbbb",
    "latest-tag": "v1.0.0",
    "decisions-count": "2",
}


def make_frontmatter(overrides: dict | None = None, omit: list[str] | None = None) -> str:
    fields = dict(DEFAULT_FIELDS)
    if overrides:
        fields.update(overrides)
    omit = omit or []
    lines = ["---"]
    for key, value in fields.items():
        if key in omit:
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


DECISIONS_TWO = (
    "## Decisions Made\n\n"
    "1. **Decision one.** Reasoning for the first decision.\n"
    "2. **Decision two.** Reasoning for the second decision.\n\n"
)

WAITING_OK = (
    "## Waiting on You\n\n"
    "- **Item one** (blocked since 2026-10-01). Detail about item one.\n\n"
)

WAITING_NOTHING_PENDING = "## Waiting on You\n\nNothing pending.\n\n"

LEDGER_OK = (
    "## Uncertainty Ledger\n\n"
    "| # | Claim | Confidence | Blast radius | Verified? | What would settle it |\n"
    "|---|---|---|---|---|---|\n"
    "| 1 | Fixture claim | Low | Low | no | Nothing yet |\n\n"
)

WYMNR_OK = (
    "## What You May Not Realize\n\n"
    "- **Low.** Fixture item citing a source. Source: this fixture.\n\n"
)


def build_log(frontmatter: str, *sections: str) -> str:
    body = "# Session log\n\n" + "".join(sections)
    return frontmatter + "\n\n" + body


def clean_deep_log() -> str:
    return build_log(make_frontmatter(), DECISIONS_TWO, WAITING_OK, LEDGER_OK, WYMNR_OK)


def main() -> int:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)

        # ------------------------------------------------------------------
        # 1. A fully clean deep log exits 0 and every check reports clean.
        # ------------------------------------------------------------------
        repo1 = root / "repo1"
        repo1.mkdir()
        log1 = write(repo1 / "log.md", clean_deep_log())
        proc = run_check(log1, repo1, mode="deep")
        check("clean deep log exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        check("clean deep log: overall is clean", data["overall"] == "clean", str(data))
        check(
            "clean deep log: every check reports clean",
            all(r["state"] == "clean" for r in data["checks"].values()),
            str(data["checks"]),
        )

        # ------------------------------------------------------------------
        # 2. Dash violation in the body is caught by the dash-check pass-through.
        # ------------------------------------------------------------------
        repo2 = root / "repo2"
        repo2.mkdir()
        dashed_decisions = DECISIONS_TWO.replace(
            "Reasoning for the first decision.",
            f"Reasoning {EM_DASH} with a dash right here.",
        )
        log2 = write(repo2 / "log.md", build_log(make_frontmatter(), dashed_decisions, WAITING_OK, LEDGER_OK, WYMNR_OK))
        proc = run_check(log2, repo2, mode="deep")
        data = json.loads(proc.stdout)
        check("dash violation exits 1", proc.returncode == 1, proc.stdout)
        check("dash violation: dashes check reports findings", data["checks"]["dashes"]["state"] == "findings", str(data["checks"]["dashes"]))

        # ------------------------------------------------------------------
        # 3. A missing path citation is caught by the path-citation pass-through.
        # ------------------------------------------------------------------
        repo3 = root / "repo3"
        repo3.mkdir()
        missing_path_decisions = DECISIONS_TWO.replace(
            "Reasoning for the first decision.",
            "Reasoning, see `missing/nope.md` for the source.",
        )
        log3 = write(repo3 / "log.md", build_log(make_frontmatter(), missing_path_decisions, WAITING_OK, LEDGER_OK, WYMNR_OK))
        proc = run_check(log3, repo3, mode="deep")
        data = json.loads(proc.stdout)
        check("missing path citation exits 1", proc.returncode == 1, proc.stdout)
        check(
            "missing path citation: path-citations check reports findings",
            data["checks"]["path-citations"]["state"] == "findings",
            str(data["checks"]["path-citations"]),
        )

        # ------------------------------------------------------------------
        # 4. decisions-count mismatch (frontmatter says 3, body has 2).
        # ------------------------------------------------------------------
        repo4 = root / "repo4"
        repo4.mkdir()
        log4 = write(
            repo4 / "log.md",
            build_log(make_frontmatter({"decisions-count": "3"}), DECISIONS_TWO, WAITING_OK, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log4, repo4, mode="deep")
        data = json.loads(proc.stdout)
        check("decisions-count mismatch exits 1", proc.returncode == 1, proc.stdout)
        check(
            "decisions-count mismatch reported",
            data["checks"]["decisions-count"]["state"] == "findings"
            and "3" in data["checks"]["decisions-count"]["detail"][0]
            and "2" in data["checks"]["decisions-count"]["detail"][0],
            str(data["checks"]["decisions-count"]),
        )

        # ------------------------------------------------------------------
        # 5. decisions-count missing entirely in deep mode is a finding.
        # ------------------------------------------------------------------
        repo5 = root / "repo5"
        repo5.mkdir()
        log5 = write(
            repo5 / "log.md",
            build_log(make_frontmatter(omit=["decisions-count"]), DECISIONS_TWO, WAITING_OK, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log5, repo5, mode="deep")
        data = json.loads(proc.stdout)
        check(
            "missing decisions-count in deep mode is a finding",
            data["checks"]["decisions-count"]["state"] == "findings",
            str(data["checks"]["decisions-count"]),
        )

        # ------------------------------------------------------------------
        # 6. decisions-count is skipped, not failed, in quick mode.
        # ------------------------------------------------------------------
        repo6 = root / "repo6"
        repo6.mkdir()
        log6 = write(
            repo6 / "log.md",
            build_log(make_frontmatter(omit=["decisions-count"]), WAITING_OK),
        )
        proc = run_check(log6, repo6, mode="quick")
        data = json.loads(proc.stdout)
        check(
            "quick mode skips decisions-count rather than flagging it",
            data["checks"]["decisions-count"]["state"] == "skipped",
            str(data["checks"]["decisions-count"]),
        )
        check("quick mode: no ledger/WYMNR keys at all", "uncertainty-ledger" not in data["checks"] and "what-you-may-not-realize" not in data["checks"])
        check("quick mode, otherwise clean, exits 0", proc.returncode == 0, proc.stdout)

        # ------------------------------------------------------------------
        # 7. summary over 120 characters is a finding.
        # ------------------------------------------------------------------
        repo7 = root / "repo7"
        repo7.mkdir()
        long_summary = '"' + ("x" * 130) + '"'
        log7 = write(
            repo7 / "log.md",
            build_log(make_frontmatter({"summary": long_summary}), DECISIONS_TWO, WAITING_OK, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log7, repo7, mode="deep")
        data = json.loads(proc.stdout)
        check(
            "summary over 120 chars is a finding",
            data["checks"]["summary-length"]["state"] == "findings",
            str(data["checks"]["summary-length"]),
        )

        # ------------------------------------------------------------------
        # 8. summary missing is a finding (and also a Tier 1 finding).
        # ------------------------------------------------------------------
        repo8 = root / "repo8"
        repo8.mkdir()
        log8 = write(
            repo8 / "log.md",
            build_log(make_frontmatter(omit=["summary"]), DECISIONS_TWO, WAITING_OK, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log8, repo8, mode="deep")
        data = json.loads(proc.stdout)
        check("missing summary: summary-length is a finding", data["checks"]["summary-length"]["state"] == "findings")
        check("missing summary: tier1-frontmatter is also a finding", data["checks"]["tier1-frontmatter"]["state"] == "findings")

        # ------------------------------------------------------------------
        # 9. Tier 1 non-empty field missing ('machine').
        # ------------------------------------------------------------------
        repo9 = root / "repo9"
        repo9.mkdir()
        log9 = write(
            repo9 / "log.md",
            build_log(make_frontmatter(omit=["machine"]), DECISIONS_TWO, WAITING_OK, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log9, repo9, mode="deep")
        data = json.loads(proc.stdout)
        check(
            "missing 'machine' is a Tier 1 finding naming the field",
            data["checks"]["tier1-frontmatter"]["state"] == "findings"
            and any("machine" in d for d in data["checks"]["tier1-frontmatter"]["detail"]),
            str(data["checks"]["tier1-frontmatter"]),
        )

        # ------------------------------------------------------------------
        # 10. Tier 1 present-only field missing ('latest-tag', the W-02 addition).
        # ------------------------------------------------------------------
        repo10 = root / "repo10"
        repo10.mkdir()
        log10 = write(
            repo10 / "log.md",
            build_log(make_frontmatter(omit=["latest-tag"]), DECISIONS_TWO, WAITING_OK, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log10, repo10, mode="deep")
        data = json.loads(proc.stdout)
        check(
            "missing 'latest-tag' is a Tier 1 finding naming the field",
            data["checks"]["tier1-frontmatter"]["state"] == "findings"
            and any("latest-tag" in d for d in data["checks"]["tier1-frontmatter"]["detail"]),
            str(data["checks"]["tier1-frontmatter"]),
        )

        # ------------------------------------------------------------------
        # 11. Waiting on You section missing entirely.
        # ------------------------------------------------------------------
        repo11 = root / "repo11"
        repo11.mkdir()
        log11 = write(
            repo11 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log11, repo11, mode="deep")
        data = json.loads(proc.stdout)
        check("missing Waiting on You section is a finding", data["checks"]["waiting-on-you"]["state"] == "findings")

        # ------------------------------------------------------------------
        # 12. Waiting on You item missing the (blocked since ...) marker.
        # ------------------------------------------------------------------
        repo12 = root / "repo12"
        repo12.mkdir()
        undated_waiting = "## Waiting on You\n\n- **Item one.** No date marker here.\n\n"
        log12 = write(
            repo12 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, undated_waiting, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log12, repo12, mode="deep")
        data = json.loads(proc.stdout)
        check(
            "undated Waiting on You item is a finding",
            data["checks"]["waiting-on-you"]["state"] == "findings"
            and any("blocked since" in d for d in data["checks"]["waiting-on-you"]["detail"]),
            str(data["checks"]["waiting-on-you"]),
        )

        # ------------------------------------------------------------------
        # 13. Waiting on You item begins with 'Optional', plain and bold.
        # ------------------------------------------------------------------
        repo13 = root / "repo13"
        repo13.mkdir()
        optional_waiting = (
            "## Waiting on You\n\n"
            "- Optional: a plain-text optional item (blocked since 2026-10-01).\n"
            "- **Optional:** a bold optional item (blocked since 2026-10-01).\n\n"
        )
        log13 = write(
            repo13 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, optional_waiting, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log13, repo13, mode="deep")
        data = json.loads(proc.stdout)
        optional_findings = [d for d in data["checks"]["waiting-on-you"]["detail"] if "Optional" in d]
        check(
            "both plain and bold 'Optional' items are flagged",
            data["checks"]["waiting-on-you"]["state"] == "findings" and len(optional_findings) == 2,
            str(data["checks"]["waiting-on-you"]),
        )

        # ------------------------------------------------------------------
        # 14. Waiting on You with explicit 'Nothing pending.' is clean.
        # ------------------------------------------------------------------
        repo14 = root / "repo14"
        repo14.mkdir()
        log14 = write(
            repo14 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, WAITING_NOTHING_PENDING, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log14, repo14, mode="deep")
        data = json.loads(proc.stdout)
        check("'Nothing pending.' is clean", data["checks"]["waiting-on-you"]["state"] == "clean", str(data["checks"]["waiting-on-you"]))

        # ------------------------------------------------------------------
        # 14b. An indented sub-bullet under a dated top-level item is not its
        # own item (found on the real 2026-10-07 log; see derive-log-facts.py's
        # extract_waiting_on_you()). A dated top-level item carrying indented
        # sub-bullets must stay clean, not generate one undated finding per
        # sub-bullet.
        # ------------------------------------------------------------------
        repo14b = root / "repo14b"
        repo14b.mkdir()
        waiting_with_subbullets = (
            "## Waiting on You\n\n"
            "- **Approve the thing** (blocked since 2026-10-07). It would:\n"
            "  - unify the criteria in one place;\n"
            "  - write the follow-up doc.\n\n"
        )
        log14b = write(
            repo14b / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, waiting_with_subbullets, LEDGER_OK, WYMNR_OK),
        )
        proc = run_check(log14b, repo14b, mode="deep")
        data = json.loads(proc.stdout)
        check(
            "indented sub-bullets under a dated top-level item are not flagged as undated items",
            data["checks"]["waiting-on-you"]["state"] == "clean",
            str(data["checks"]["waiting-on-you"]),
        )

        # ------------------------------------------------------------------
        # 15/16. Deep mode: Uncertainty Ledger missing, then present-but-empty.
        # ------------------------------------------------------------------
        repo15 = root / "repo15"
        repo15.mkdir()
        log15 = write(
            repo15 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, WAITING_OK, WYMNR_OK),
        )
        proc = run_check(log15, repo15, mode="deep")
        data = json.loads(proc.stdout)
        check("missing Uncertainty Ledger is a finding", data["checks"]["uncertainty-ledger"]["state"] == "findings")

        repo16 = root / "repo16"
        repo16.mkdir()
        empty_ledger = "## Uncertainty Ledger\n\n## What You May Not Realize\n\n"
        log16 = write(
            repo16 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, WAITING_OK, empty_ledger),
        )
        proc = run_check(log16, repo16, mode="deep")
        data = json.loads(proc.stdout)
        check("empty Uncertainty Ledger is a finding", data["checks"]["uncertainty-ledger"]["state"] == "findings")
        check("empty What You May Not Realize is also a finding", data["checks"]["what-you-may-not-realize"]["state"] == "findings")

        # ------------------------------------------------------------------
        # 17. Deep mode: both deep sections present with their empty markers is clean.
        # ------------------------------------------------------------------
        repo17 = root / "repo17"
        repo17.mkdir()
        markers = "## Uncertainty Ledger\n\nNothing material.\n\n## What You May Not Realize\n\nNothing surfaced.\n\n"
        log17 = write(
            repo17 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, WAITING_OK, markers),
        )
        proc = run_check(log17, repo17, mode="deep")
        data = json.loads(proc.stdout)
        check("'Nothing material.' satisfies the ledger check", data["checks"]["uncertainty-ledger"]["state"] == "clean")
        check("'Nothing surfaced.' satisfies the WYMNR check", data["checks"]["what-you-may-not-realize"]["state"] == "clean")
        check("fully populated deep log exits 0", proc.returncode == 0, proc.stdout)

        # ------------------------------------------------------------------
        # 18. final mode never evaluates the two deep-only sections.
        # ------------------------------------------------------------------
        repo18 = root / "repo18"
        repo18.mkdir()
        log18 = write(
            repo18 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, WAITING_OK),
        )
        proc = run_check(log18, repo18, mode="final")
        data = json.loads(proc.stdout)
        check(
            "final mode has no uncertainty-ledger or what-you-may-not-realize keys",
            "uncertainty-ledger" not in data["checks"] and "what-you-may-not-realize" not in data["checks"],
            str(data["checks"]),
        )
        check("final mode, otherwise clean, exits 0", proc.returncode == 0, proc.stdout)

        # ------------------------------------------------------------------
        # 19. A nonexistent log path is BROKEN, not a finding.
        # ------------------------------------------------------------------
        repo19 = root / "repo19"
        repo19.mkdir()
        proc = run_check(repo19 / "does-not-exist.md", repo19, mode="deep", json_out=False)
        check("nonexistent log path exits 2 (broken)", proc.returncode == 2, proc.stdout + proc.stderr)
        check("nonexistent log path reports BROKEN in stderr", "BROKEN" in proc.stderr, proc.stderr)

        # ------------------------------------------------------------------
        # 20. check-log.py copied alone, with no sibling scripts, is BROKEN.
        # ------------------------------------------------------------------
        isolated = root / "isolated-check-log"
        isolated.mkdir()
        shutil.copy2(SCRIPT, isolated / "check-log.py")
        repo20 = root / "repo20"
        repo20.mkdir()
        log20 = write(repo20 / "log.md", clean_deep_log())
        proc = subprocess.run(
            [sys.executable, str(isolated / "check-log.py"), str(log20), "--repo-root", str(repo20), "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        check("check-log.py with no siblings exits 2 (broken)", proc.returncode == 2, proc.stdout + proc.stderr)

        # ------------------------------------------------------------------
        # 21. A broken sibling detector makes the whole result broken, and the
        #     other checks still run rather than being short-circuited.
        # ------------------------------------------------------------------
        scratch = root / "scratch-scripts"
        scratch.mkdir()
        for name in ("check-log.py", "dash-check.py", "path-citation-check.py", "derive-log-facts.py"):
            shutil.copy2(SCRIPT_DIR / name, scratch / name)
        (scratch / "dash-check.py").write_text(
            "import sys\nprint('BROKEN: stub detector', file=sys.stderr)\nsys.exit(2)\n",
            encoding="utf-8",
        )
        repo21 = root / "repo21"
        repo21.mkdir()
        log21 = write(repo21 / "log.md", clean_deep_log())
        proc = subprocess.run(
            [sys.executable, str(scratch / "check-log.py"), str(log21), "--repo-root", str(repo21), "--json"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        check("a broken sibling detector exits 2 overall", proc.returncode == 2, proc.stdout + proc.stderr)
        data = json.loads(proc.stdout)
        check("the broken detector's own check is reported broken", data["checks"]["dashes"]["state"] == "broken", str(data["checks"]["dashes"]))
        check(
            "other checks still ran rather than being short-circuited",
            data["checks"]["tier1-frontmatter"]["state"] == "clean"
            and data["checks"]["decisions-count"]["state"] == "clean"
            and data["checks"]["waiting-on-you"]["state"] == "clean",
            str(data["checks"]),
        )

        # ------------------------------------------------------------------
        # 22. Encoding robustness, write side: an undated Waiting on You item
        #     containing a non-ASCII character is echoed verbatim in its
        #     finding line. The TEXT output path (render_text's print() calls,
        #     not --json: json.dumps() defaults to ensure_ascii=True, which
        #     already escapes the character to a plain-ASCII "❌" and
        #     never exercises this bug) must not crash writing that line to a
        #     pipe whose encoding cannot represent the character. -X utf8=0,
        #     PYTHONUTF8=0 and LC_ALL=C force Python out of UTF-8 mode so the
        #     test does not depend on ambient locale state.
        # ------------------------------------------------------------------
        repo22 = root / "repo22"
        repo22.mkdir()
        undated_nonascii_waiting = f"## Waiting on You\n\n- **Approve the thing {CROSS}.** No date marker here, on purpose.\n\n"
        log22 = write(
            repo22 / "log.md",
            build_log(make_frontmatter(), DECISIONS_TWO, undated_nonascii_waiting, LEDGER_OK, WYMNR_OK),
        )
        enc_env = os.environ.copy()
        enc_env["PYTHONUTF8"] = "0"
        enc_env["LC_ALL"] = "C"
        proc = subprocess.run(
            [sys.executable, "-X", "utf8=0", str(SCRIPT), str(log22), "--repo-root", str(repo22), "--mode", "deep"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=enc_env, timeout=30,
        )
        check(
            "a non-ASCII character in a flagged Waiting on You item does not crash on write",
            proc.returncode == 1,
            proc.stdout[-300:] + "\n" + proc.stderr[-1200:],
        )
        if proc.returncode == 1:
            check(
                "the finding still names the undated item, cross mark included",
                CROSS in proc.stdout,
                proc.stdout,
            )

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
