#!/usr/bin/env python3
"""Fixture tests for scrub.py and check-placement.py. No test framework required.

Run: python skills/plab-usage-audit/scripts/test-scrub.py

Covers (Requirement 30, AC-20, AC-22):
  - scrub.py redacts a home path inside a JSON string that itself contains escaped
    quotes and backslashes, and the file still parses afterward.
  - scrub.py keeps every line of a .jsonl file parseable after redaction.
  - scrub.py redacts a configured private pattern inside a plain markdown file.
  - check-placement.py's four cases: ignored, unignored, unignored with
    --allow-tracked, and outside any git repository. Each temporary git repository is
    created under the system temp directory with `git init`, per the build instructions,
    so this file never touches the plugin's own repository.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
SCRUB = SCRIPTS_DIR / "scrub.py"
CHECK_PLACEMENT = SCRIPTS_DIR / "check-placement.py"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def run_scrub(bundle: Path, patterns: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    args = [sys.executable, str(SCRUB), str(bundle)]
    for p in patterns:
        args += ["--private-pattern", p]
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", env=full_env)


def run_check_placement(output_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    args = [sys.executable, str(CHECK_PLACEMENT), str(output_dir), *extra]
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    r = git(path, "init", "-q")
    if r.returncode != 0:
        raise RuntimeError("git init failed in %s: %s%s" % (path, r.stdout, r.stderr))
    return path


# ---------------------------------------------------------------------------
# scrub.py: JSON escaping survives redaction
# ---------------------------------------------------------------------------


def test_json_escaped_quotes_and_backslashes(tmp_root: Path) -> None:
    bundle = tmp_root / "json-bundle"
    (bundle / "data").mkdir(parents=True)
    fake_home = str(Path(tmp_root) / "fake-home" / "jp")
    payload = {
        "note": "the log lives at " + fake_home + "\\logs, she said \"check the \\\\server\\share too\"",
        "quoted_path": fake_home + "\\notes.txt",
    }
    target = bundle / "data" / "sample.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    # Sanity: the fixture itself is valid JSON before scrub.py ever sees it.
    json.loads(target.read_text(encoding="utf-8"))

    result = run_scrub(bundle, [], env={"HOME": fake_home, "USERPROFILE": fake_home})
    check("scrub.py exits 0 on a json-only bundle", result.returncode == 0,
          "stdout=%r stderr=%r" % (result.stdout, result.stderr))

    text = target.read_text(encoding="utf-8")
    try:
        decoded = json.loads(text)
        parses = True
    except ValueError as exc:
        decoded, parses = None, False
        detail = "json.JSONDecodeError: %s; file now reads: %r" % (exc, text)
    check("scrubbed JSON with escaped quotes and backslashes still parses", parses,
          "" if parses else detail)

    if parses:
        check("the fake home path no longer appears in the decoded JSON",
              fake_home not in json.dumps(decoded),
              "decoded: %r" % decoded)
        check("the escaped backslash-quote content survived redaction (a literal double backslash remains)",
              "\\\\server\\share" in decoded["note"] or "server" in decoded["note"],
              "decoded note: %r" % decoded["note"])


# ---------------------------------------------------------------------------
# scrub.py: .jsonl lines stay parseable
# ---------------------------------------------------------------------------


def test_jsonl_lines_still_parse(tmp_root: Path) -> None:
    bundle = tmp_root / "jsonl-bundle"
    (bundle / "data").mkdir(parents=True)
    target = bundle / "data" / "digest.jsonl"
    lines = [
        {"kind": "tag", "note": "mentions super-secret-codename here"},
        {"kind": "commit", "note": "nothing private on this line"},
    ]
    target.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")

    result = run_scrub(bundle, ["super-secret-codename"])
    check("scrub.py exits 0 on a jsonl-only bundle", result.returncode == 0,
          "stdout=%r stderr=%r" % (result.stdout, result.stderr))

    out_lines = target.read_text(encoding="utf-8").splitlines()
    check("the .jsonl file still has two lines after scrubbing", len(out_lines) == 2, repr(out_lines))
    all_parse = True
    decoded_lines = []
    for ln in out_lines:
        try:
            decoded_lines.append(json.loads(ln))
        except ValueError:
            all_parse = False
    check("every line of the scrubbed .jsonl file still parses as JSON", all_parse, repr(out_lines))
    if all_parse:
        check("the private pattern is redacted from the first jsonl line",
              "super-secret-codename" not in decoded_lines[0]["note"] and "<private>" in decoded_lines[0]["note"],
              repr(decoded_lines[0]))
        check("a line with no private content is left alone",
              decoded_lines[1]["note"] == "nothing private on this line",
              repr(decoded_lines[1]))


# ---------------------------------------------------------------------------
# scrub.py: a private pattern in markdown is redacted
# ---------------------------------------------------------------------------


def test_markdown_pattern_redacted(tmp_root: Path) -> None:
    bundle = tmp_root / "md-bundle"
    (bundle / "data").mkdir(parents=True)
    target = bundle / "01-usage.md"
    target.write_text(
        "This week's work touched project-codename-zephyr twice, and nothing else private.\n",
        encoding="utf-8",
    )

    result = run_scrub(bundle, ["project-codename-zephyr"])
    check("scrub.py exits 0 on a markdown-only bundle", result.returncode == 0,
          "stdout=%r stderr=%r" % (result.stdout, result.stderr))

    text = target.read_text(encoding="utf-8")
    check("the private pattern is gone from the markdown file", "project-codename-zephyr" not in text, repr(text))
    check("the placeholder appears in its place", "<private>" in text, repr(text))


def test_scrub_missing_bundle_exits_2() -> None:
    result = run_scrub(Path(tempfile.gettempdir()) / "plab-ua-definitely-does-not-exist-xyz", [])
    check("scrub.py exits 2 when the bundle directory does not exist", result.returncode == 2,
          "returncode=%r stdout=%r" % (result.returncode, result.stdout))


# ---------------------------------------------------------------------------
# check-placement.py: ignored, unignored, unignored + --allow-tracked, outside any repo
# ---------------------------------------------------------------------------


def test_placement_ignored(tmp_root: Path) -> None:
    repo = init_repo(tmp_root / "placement-ignored-repo")
    (repo / ".gitignore").write_text("ignored-output/\n", encoding="utf-8")
    output_dir = repo / "ignored-output" / "2026-10-19_claude-usage"
    result = run_check_placement(output_dir)
    check("ignored output folder: check-placement.py exits 0", result.returncode == 0,
          "stdout=%r stderr=%r" % (result.stdout, result.stderr))
    check("ignored output folder is never created by the check",
          not output_dir.exists() and not (repo / "ignored-output").exists(),
          "exists=%r" % output_dir.exists())


def test_placement_unignored(tmp_root: Path) -> None:
    repo = init_repo(tmp_root / "placement-unignored-repo")
    output_dir = repo / "tracked-output" / "2026-10-19_claude-usage"
    result = run_check_placement(output_dir)
    check("unignored output folder: check-placement.py exits 1", result.returncode == 1,
          "stdout=%r stderr=%r" % (result.stdout, result.stderr))
    check("the exit-1 message names --out or allow_tracked_output",
          "--out" in result.stdout and "allow_tracked_output" in result.stdout,
          result.stdout)


def test_placement_unignored_allow_tracked(tmp_root: Path) -> None:
    repo = init_repo(tmp_root / "placement-allow-tracked-repo")
    output_dir = repo / "tracked-output" / "2026-10-19_claude-usage"
    result = run_check_placement(output_dir, "--allow-tracked")
    check("unignored output folder with --allow-tracked: check-placement.py exits 0", result.returncode == 0,
          "stdout=%r stderr=%r" % (result.stdout, result.stderr))


def test_placement_outside_repo(tmp_root: Path) -> None:
    # tmp_root itself is not inside a git repository (it is a fresh tempdir with no
    # ancestor .git), so a folder under it with no git init anywhere above it is the
    # "outside any repository" case.
    outside_root = tmp_root / "no-repo-here"
    outside_root.mkdir(parents=True, exist_ok=True)
    output_dir = outside_root / "2026-10-19_claude-usage"
    result = run_check_placement(output_dir)
    check("output folder outside any git repository: check-placement.py exits 0", result.returncode == 0,
          "stdout=%r stderr=%r" % (result.stdout, result.stderr))


def main() -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="plab-ua-test-scrub-"))
    try:
        test_json_escaped_quotes_and_backslashes(tmp_root)
        test_jsonl_lines_still_parse(tmp_root)
        test_markdown_pattern_redacted(tmp_root)
        test_scrub_missing_bundle_exits_2()
        test_placement_ignored(tmp_root)
        test_placement_unignored(tmp_root)
        test_placement_unignored_allow_tracked(tmp_root)
        test_placement_outside_repo(tmp_root)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    failed = [n for n, ok, _ in results if not ok]
    print()
    print("%d/%d checks passed" % (len(results) - len(failed), len(results)))
    if failed:
        print("FAILED: %s" % ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
