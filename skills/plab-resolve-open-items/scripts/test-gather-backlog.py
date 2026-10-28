#!/usr/bin/env python3
"""Fixture tests for gather-backlog.py. No test framework required.

Run: python skills/plab-resolve-open-items/scripts/test-gather-backlog.py

Every case builds a throwaway git repository in a temp directory, so the
tests never touch this plugin's own repository. `--today` pins the clock so
age_days results do not drift as the calendar moves, mirroring
test-organize-logs.py's `--today` convention.

The canary for the status filter is not automated here, because it edits
the script under test rather than its input: per the implementation plan's
Phase 1 Verification, delete PENDING_STATUSES' filtering from
gather-backlog.py, rerun this file, and confirm the failure below names
"status filter"; then restore it.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "gather-backlog.py"
TODAY = "2026-02-01"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = f"  |  {detail}" if detail and not ok else ""
    print(f"{'PASS' if ok else 'FAIL'}  {name}{suffix}")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")


def init_repo(root: Path) -> Path:
    repo = root
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "test@example.com")
    git(repo, "config", "user.name", "Test")
    return repo


def commit_all(repo: Path) -> None:
    git(repo, "add", "-A")
    r = git(repo, "commit", "-q", "-m", "fixture")
    if r.returncode != 0 and "nothing to commit" not in (r.stdout + r.stderr):
        raise RuntimeError("git commit failed: %s %s" % (r.stdout, r.stderr))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def frontmatter(doc_type: str, status: str = "draft", created: str | None = "2026-01-01") -> str:
    lines = ["---", "type: %s" % doc_type, "status: %s" % status]
    if created is not None:
        lines.append("created: %s" % created)
    lines.append("---")
    return "\n".join(lines) + "\n"


def typed_doc(doc_type="spec", status="draft", created="2026-01-01",
              heading="## Open Questions / Decisions", table_lines=None) -> str:
    body = ["", "# Test document", "", heading, ""]
    if table_lines is None:
        body.append("None at this time.")
    else:
        body.extend(table_lines)
    body += ["", "## Sources", "", "- none", ""]
    return frontmatter(doc_type, status, created) + "\n".join(body)


def canonical_table(rows: list[tuple[str, str, str, str, str]]) -> list[str]:
    lines = ["| ID | Title | Resolution | Status | Updated |", "|---|---|---|---|---|"]
    for row in rows:
        lines.append("| %s | %s | %s | %s | %s |" % row)
    return lines


def run(repo: Path, *args: str, today: str = TODAY) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--today", today, *args],
        capture_output=True, text=True, encoding="utf-8",
    )


def gathered(repo: Path, today: str = TODAY) -> list[dict]:
    r = run(repo, "--json", today=today)
    if r.returncode != 0:
        raise AssertionError("gather-backlog.py exited %d: %s" % (r.returncode, r.stderr))
    return json.loads(r.stdout)


def hash_tree(repo: Path) -> dict[str, str]:
    """Content hash of every file under repo, .git excluded, keyed by
    relative path. A dict (not one combined digest) so a mismatch names
    which file changed."""
    out = {}
    for p in sorted(repo.rglob("*")):
        if ".git" in p.parts or not p.is_file():
            continue
        out[str(p.relative_to(repo))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # 1. The type filter: an untyped document contributes nothing, even
        # with a well-formed decisions section holding an Open item.
        repo = init_repo(root / "type-filter")
        write(repo / "spec.md", typed_doc("spec", table_lines=canonical_table(
            [("D1", "A real item", "(none)", "Open", "(none)")])))
        write(repo / "brief.md",
              "# A brief, no frontmatter type\n\n"
              "## Open Questions / Decisions\n\n"
              + "\n".join(canonical_table([("D1", "An example, not a real item", "(none)", "Open", "(none)")]))
              + "\n")
        commit_all(repo)
        items = gathered(repo)
        check("typed doc's item is gathered", any(i["home"] == "spec.md" for i in items), str(items))
        check("untyped brief contributes nothing",
              not any(i["home"] == "brief.md" for i in items), str(items))

        # 2. All eight statuses: only Open, Needs info and the legacy Proposed pass.
        repo = init_repo(root / "statuses")
        rows = [
            ("D1", "Open item", "(none)", "Open", "(none)"),
            ("D2", "Needs info item", "(none)", "Needs info", "(none)"),
            ("D3", "Proposed item", "(none)", "Proposed", "(none)"),
            ("D4", "Decided item", "Option A", "Decided", "2026-01-02"),
            ("D5", "Provisional item", "Option A, provisional", "Provisional", "2026-01-02"),
            ("D6", "Deferred item", "Deferred", "Deferred", "2026-01-02"),
            ("D7", "Canceled item", "Canceled", "Canceled", "2026-01-02"),
            ("D8", "Superseded item", "See D9", "Superseded", "2026-01-02"),
        ]
        write(repo / "spec.md", typed_doc("spec", table_lines=canonical_table(rows)))
        commit_all(repo)
        items = gathered(repo)
        got = sorted(i["id"] for i in items)
        check("status filter keeps exactly Open, Needs info and Proposed",
              got == ["D1", "D2", "D3"], str(got))

        # 3. A numbered heading variant, as walk-format.md names it.
        repo = init_repo(root / "numbered-heading")
        write(repo / "spec.md", typed_doc(
            "spec", heading="## 7. Open Questions & Decisions",
            table_lines=canonical_table([("D1", "Behind a numbered heading", "(none)", "Open", "(none)")])))
        commit_all(repo)
        items = gathered(repo)
        check("a numbered '&' heading variant is still gathered",
              any(i["id"] == "D1" for i in items), str(items))

        # 4. An unparseable table: exits 2 and names the file.
        repo = init_repo(root / "broken-table")
        write(repo / "spec.md", typed_doc("spec", table_lines=[
            "| ID | Title |", "|---|---|", "| D1 | Missing a Status column |",
        ]))
        commit_all(repo)
        r = run(repo, "--json")
        check("a table missing Status exits 2", r.returncode == 2, "exit=%d stderr=%r" % (r.returncode, r.stderr))
        check("the broken exit names the file", "spec.md" in r.stderr, r.stderr)
        check("the broken exit prints nothing to stdout", r.stdout == "", repr(r.stdout))

        # 5. Newest-wins across the flat store and a month folder.
        repo = init_repo(root / "newest-wins")
        write(repo / "_local" / "_session-logs" / "2026-01-05_08-00_claude_older-hot.md",
              "---\ntype: session-log\n---\n\n## Waiting on You\n\n"
              "- **Older item** (blocked since 2026-01-01). From the older hot log.\n")
        write(repo / "_local" / "_session-logs" / "2026-01" / "2026-01-30_23-00_claude_newest.md",
              "---\ntype: session-log\n---\n\n## Waiting on You\n\n"
              "- **Newest item** (blocked since 2026-01-20). From the archived-but-newer log.\n")
        commit_all(repo)
        items = gathered(repo)
        waiting = [i for i in items if i["source_kind"] == "waiting-on"]
        check("exactly one log's items are gathered", len(waiting) == 1, str(waiting))
        check("the archived-but-newer log outranks the older flat log",
              bool(waiting) and waiting[0]["home"].endswith("2026-01-30_23-00_claude_newest.md"), str(waiting))

        # 6. Age order with each fallback.
        repo = init_repo(root / "age-fallbacks")
        write(repo / "with-created.md", typed_doc("spec", created="2026-01-01", table_lines=canonical_table([
            ("D1", "Row Updated wins", "(none)", "Open", "2026-01-25"),
            ("D2", "Falls back to the document's created date", "(none)", "Open", "(none)"),
        ])))
        no_created_text = (
            "---\ntype: spec\nstatus: draft\n---\n\n## Open Questions / Decisions\n\n"
            + "\n".join(canonical_table([("D3", "No Updated and no created: unknown", "(none)", "Open", "(none)")]))
            + "\n"
        )
        write(repo / "no-created.md", no_created_text)
        write(repo / "_local" / "_session-logs" / "2026-01-31_09-00_claude_log.md",
              "---\ntype: session-log\n---\n\n## Waiting on You\n\n"
              "- **Has a date** (blocked since 2026-01-20). Age from blocked since.\n"
              "- **No date at all** no marker on this bullet, so age is unknown.\n")
        commit_all(repo)
        items = gathered(repo)
        by_id = {i["id"]: i for i in items if i["source_kind"] == "decisions-section"}
        check("D1 ages from the row's own Updated date", by_id["D1"]["age_days"] == 7, str(by_id.get("D1")))
        check("D2 falls back to the document's created date", by_id["D2"]["age_days"] == 31, str(by_id.get("D2")))
        check("D3 is unknown with neither Updated nor created", by_id["D3"]["age_days"] == "unknown", str(by_id.get("D3")))
        waiting = [i for i in items if i["source_kind"] == "waiting-on"]
        by_title = {i["title"]: i for i in waiting}
        check("a bullet with blocked since ages from that date",
              by_title.get("Has a date", {}).get("age_days") == 12, str(waiting))
        check("a bullet without a blocked since marker is unknown, not invented",
              by_title.get("No date at all", {}).get("age_days") == "unknown", str(waiting))

        # 7. No write: gathering must not change a single byte on disk.
        repo = init_repo(root / "no-write")
        write(repo / "spec.md", typed_doc("spec", table_lines=canonical_table(
            [("D1", "An item", "(none)", "Open", "(none)")])))
        write(repo / "_local" / "_session-logs" / "2026-01-15_08-00_claude_log.md",
              "---\ntype: session-log\n---\n\n## Waiting on You\n\n"
              "- **A task** (blocked since 2026-01-10). Something pending.\n")
        commit_all(repo)
        before = hash_tree(repo)
        r = run(repo, "--json")
        check("no-write run exits 0", r.returncode == 0, r.stderr)
        after = hash_tree(repo)
        check("gathering writes nothing: identical file set and hashes", before == after,
              "before=%r after=%r" % (before, after))

        # 8. A text (non-JSON) summary still reports a usable count.
        repo = init_repo(root / "text-mode")
        write(repo / "spec.md", typed_doc("spec", table_lines=canonical_table(
            [("D1", "An item", "(none)", "Open", "(none)")])))
        commit_all(repo)
        r = run(repo)
        check("text mode exits 0", r.returncode == 0, r.stderr)
        check("text mode reports a count", "1 item" in r.stdout, repr(r.stdout))

        # 9. --answered-since (1.2.0, for plab-current-status). Without it the
        # output is unchanged; with it, recent answers and out-of-vocabulary
        # statuses are added, each with a kind.
        repo = init_repo(root / "answered-since")
        write(repo / "spec.md", typed_doc("spec", table_lines=canonical_table([
            ("D1", "Still open", "(none)", "Open", "(none)"),
            ("D2", "Decided on the boundary day", "Option A", "Decided", "2026-01-20"),
            ("D3", "Decided the day before the boundary", "Option B", "Decided", "2026-01-19"),
            ("D4", "Paraphrased answer, recent", "Option A", "Decided, see below", "2026-01-25"),
            ("D5", "Out of vocabulary", "(none)", "Needs ruling", "(none)"),
            ("D6", "Answered with no date", "Option A", "Canceled", "(none)"),
        ])))
        commit_all(repo)
        default = run(repo, "--json")
        default_items = json.loads(default.stdout)
        check("without --answered-since only the pending item returns, with no kind field",
              [i["id"] for i in default_items] == ["D1"] and "kind" not in default_items[0],
              default.stdout)
        r = run(repo, "--json", "--answered-since", "2026-01-20")
        check("--answered-since exits 0", r.returncode == 0, r.stderr)
        kinds = {i["id"]: i.get("kind") for i in json.loads(r.stdout or "[]")}
        check("answered-since boundary: the boundary day is in, the day before is out",
              kinds.get("D2") == "answered" and "D3" not in kinds, str(kinds))
        check("a status starting with an answer word counts as answered",
              kinds.get("D4") == "answered", str(kinds))
        check("an out-of-vocabulary status returns as unrecognised",
              kinds.get("D5") == "unrecognised", str(kinds))
        check("an answer with no Updated date is not called recent",
              "D6" not in kinds, str(kinds))
        check("the pending item carries kind pending", kinds.get("D1") == "pending", str(kinds))

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
