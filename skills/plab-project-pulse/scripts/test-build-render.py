#!/usr/bin/env python3
"""Fixture tests for build-pulse.py, render.py and pulse-check.py.

Run: python skills/plab-project-pulse/scripts/test-build-render.py

Every case builds its own minimal facts/scouts/curation/state fixtures in a
temp directory rather than touching the committed `examples/sample-pulse/`,
so a bug in the sample cannot hide a bug the tests should catch. The three
scripts under test have hyphenated filenames, so they are loaded by file
path (`importlib`), the same pattern `gather-backlog.py` and `build-pulse.py`
itself already use to load each other.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPTS = Path(__file__).resolve().parent


def load(name, alias):
    spec = importlib.util.spec_from_file_location(alias, SCRIPTS / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_pulse = load("build-pulse.py", "plab_build_pulse_under_test")
pulse_check = load("pulse-check.py", "plab_pulse_check_under_test")
render_mod = load("render.py", "plab_render_under_test")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    suffix = "  |  %s" % detail if detail and not ok else ""
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, suffix))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def base_facts(window_end="2026-10-30", window_start="2026-10-24"):
    return {
        "schema_version": 1, "generated_at": "2026-10-30T16:00:00Z", "mode": "week",
        "window": {"start": window_start, "end": window_end, "prior_start": "2026-10-17",
                   "timezone": "America/Los_Angeles"},
        "roots": ["/home/owner/src/work"],
        "repos": [],
        "logs": [], "gaps": [], "timings": {"discover_seconds": 1.0, "sweep_seconds": 1.0},
    }


def base_sweep(repo, head="aaa1111"):
    return {
        "repo": repo, "path": "/home/owner/src/%s" % repo, "folder": repo.split("/")[0],
        "remote": "git@example.com:owner/%s.git" % repo.split("/")[-1], "branch": "main", "head": head,
        "commits_prior": 0, "commits_focus": 1, "active_days_focus": 1, "last_commit_date": "2026-10-29",
        "tags_in_window": [], "dirty_files": 0, "staged_files": 0, "untracked_files": 0,
        "ahead": 0, "behind": 0, "has_upstream": True, "remote_state_as_of": "2026-10-30T12:00:00Z",
        "unmerged_branches": [], "worktrees": [], "stashes": [], "alias_of": None,
        "snapshot_utc": "2026-10-30T16:00:00Z",
    }


def main():
    tmp_root = Path(tempfile.mkdtemp(prefix="pp-test-"))
    try:
        run_tests(tmp_root)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    failed = [name for name, ok, _ in results if not ok]
    print()
    print("%d/%d checks passed." % (len(results) - len(failed), len(results)))
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("ALL PASS")
    return 0


def run_tests(tmp_root: Path) -> None:
    # -----------------------------------------------------------------
    # AC-17: a scout conflict is carried into pulse.json's repo record.
    # -----------------------------------------------------------------
    facts = base_facts()
    facts["repos"] = [{
        "repo": "work/beta", "path": "/home/owner/src/work/beta", "folder": "work", "alias_of": None,
        "sweep": base_sweep("work/beta"), "gh": None, "activity": "active", "logs_in_window": [],
        "snapshot": None, "status_source": "scout", "carried": None, "unprotected_work": [], "to_scout": True,
        "current_status_candidate": True,
    }]
    conflict = {"fact": "branch feat/x", "git_says": "merged into main", "doc_says": "blocked",
                "source": "_local/_session-logs/2026-10-28_x.md"}
    scouts = [{"repo": "work/beta", "scouted_by": {"model": "haiku", "agent": "s1"}, "summary": "ok",
               "whats_next": [], "waiting_on_you": [], "pending_decisions": [], "risks": [],
               "conflicts": [conflict]}]
    pulse, _ = build_pulse.build_pulse(facts, scouts, {}, {}, {"repos": {}, "first_seen": {}})
    check("AC-17: a scout conflict is carried into the repository's conflicts list",
          pulse["repos"][0]["conflicts"] == [conflict], json.dumps(pulse["repos"][0]["conflicts"]))

    # -----------------------------------------------------------------
    # Age computation: from `since`, and from the state file's first_seen.
    # -----------------------------------------------------------------
    new_first_seen = {}
    since_item = build_pulse.age_item("work/beta", {"text": "do the thing", "source": "docs/a.md",
                                                     "since": "2026-10-20"},
                                       "2026-10-30", {}, new_first_seen)
    check("age from an explicit since date", since_item["age_days"] == 10, str(since_item))

    old_first_seen = {"work/beta::do the other thing": "2026-10-23"}
    no_since_item = build_pulse.age_item("work/beta", {"text": "do the other thing", "source": "docs/b.md"},
                                          "2026-10-30", old_first_seen, {})
    check("age from the state file's first_seen, seven days earlier",
          no_since_item["age_days"] == 7 and no_since_item["first_seen"] == "2026-10-23", str(no_since_item))

    brand_new = build_pulse.age_item("work/beta", {"text": "a brand new item", "source": "docs/c.md"},
                                      "2026-10-30", {}, {})
    check("an item with no since and no prior first_seen is seen today, at age zero",
          brand_new["age_days"] == 0 and brand_new["first_seen"] == "2026-10-30", str(brand_new))

    # -----------------------------------------------------------------
    # AC-18 / AC-20-adjacent: build-pulse propagates a bad input through to
    # an invalid pulse.json, exits 1, and never touches state.json.
    # -----------------------------------------------------------------
    case_dir = tmp_root / "ac18"
    facts = base_facts()
    facts["repos"] = [{
        "repo": "work/gamma", "path": "/home/owner/src/work/gamma", "folder": "work", "alias_of": None,
        "sweep": base_sweep("work/gamma"), "gh": None, "activity": "active", "logs_in_window": [],
        "snapshot": None, "status_source": "scout", "carried": None, "unprotected_work": [], "to_scout": True,
        "current_status_candidate": True,
    }]
    scouts = [{"repo": "work/gamma", "scouted_by": {"model": "haiku", "agent": "s1"}, "summary": "ok",
               "whats_next": [], "waiting_on_you": [{"text": "approve this", "source": ""}],
               "pending_decisions": [], "risks": [], "conflicts": []}]
    write_json(case_dir / "pulse-facts.json", facts)
    write_json(case_dir / "scouts.json", scouts)
    write_json(case_dir / "curation.json", {})
    state_path = case_dir / "state.json"
    original_state = {"schema_version": 1, "repos": {"keep": "me"}, "first_seen": {}}
    write_json(state_path, original_state)
    state_before = state_path.read_text(encoding="utf-8")

    class Args:
        pass
    args = Args()
    args.facts = str(case_dir / "pulse-facts.json")
    args.scouts = str(case_dir / "scouts.json")
    args.curation = str(case_dir / "curation.json")
    args.digest = None
    args.spend = None
    args.state = str(state_path)
    args.out = str(case_dir / "out")
    rc = build_pulse.run(args)
    check("AC-18: build-pulse exits 1 when a waiting item's source is empty", rc == 1, "exit=%d" % rc)
    check("pulse.json is still written on a validation failure, so the failure is inspectable",
          (case_dir / "out" / "pulse.json").is_file())
    state_after = state_path.read_text(encoding="utf-8")
    check("state.json is byte-identical after a validation failure (never touched)",
          state_before == state_after)

    # The same inputs with a real source validate cleanly and DO update state.
    scouts[0]["waiting_on_you"][0]["source"] = "docs/a.md"
    write_json(case_dir / "scouts.json", scouts)
    rc2 = build_pulse.run(args)
    state_after_valid = state_path.read_text(encoding="utf-8")
    check("build-pulse only writes state.json after validation passes",
          rc2 == 0 and state_after_valid != state_before, "rc=%d" % rc2)

    # -----------------------------------------------------------------
    # AC-20: pulse-check.py fails a pulse.json missing a required field.
    # -----------------------------------------------------------------
    good = json.loads((case_dir / "out" / "pulse.json").read_text(encoding="utf-8"))
    missing_field = json.loads(json.dumps(good))
    del missing_field["totals"]
    findings = pulse_check.check_pulse(missing_field)
    check("AC-20: pulse-check fails a pulse.json missing the totals key",
          any(f.startswith("R1:") for f in findings), str(findings))

    # -----------------------------------------------------------------
    # AC-21: rendering the sample for two different windows produces two
    # dashboards whose week labels differ, and the template holds no date
    # literal (checked against the actual shipped template).
    # -----------------------------------------------------------------
    sample_dir = SCRIPTS.parent / "examples" / "sample-pulse"
    sample_pulse = json.loads((sample_dir / "pulse.json").read_text(encoding="utf-8"))
    pulse_a = json.loads(json.dumps(sample_pulse))
    pulse_b = json.loads(json.dumps(sample_pulse))
    pulse_b["window"] = {"start": "2026-11-07", "end": "2026-11-13", "prior_start": "2026-10-31",
                          "timezone": "America/Los_Angeles"}
    template_text = (SCRIPTS.parent / "assets" / "dashboard.html").read_text(encoding="utf-8")
    rendered_a = render_mod.render(pulse_a, template_text)
    rendered_b = render_mod.render(pulse_b, template_text)
    label_a = render_mod.window_label(pulse_a["window"])
    label_b = render_mod.window_label(pulse_b["window"])
    check("AC-21: rendering two different windows produces two different week labels",
          label_a != label_b and label_a in rendered_a and label_b in rendered_b,
          "%r vs %r" % (label_a, label_b))
    date_literal = re.compile(r"20\d\d-\d\d-\d\d")
    check("AC-21: the template itself holds no date literal", not date_literal.search(template_text))

    # -----------------------------------------------------------------
    # AC-22: pulse-check fails a dashboard whose card count differs from
    # pulse.json's repository count.
    # -----------------------------------------------------------------
    mismatch_dir = tmp_root / "ac22"
    mismatch_dir.mkdir()
    write_json(mismatch_dir / "pulse.json", sample_pulse)
    shutil.copyfile(sample_dir / "coverage.md", mismatch_dir / "coverage.md")
    dashboard_text = (sample_dir / "dashboard.html").read_text(encoding="utf-8")
    first = pulse_check.CARD_RE.search(dashboard_text)
    end = dashboard_text.index("</article>", first.start()) + len("</article>")
    truncated = dashboard_text[:first.start()] + dashboard_text[end:]
    (mismatch_dir / "dashboard.html").write_text(truncated, encoding="utf-8")
    findings = pulse_check.check_dir(mismatch_dir)
    check("AC-22: pulse-check fails when the dashboard's card count does not match pulse.json",
          any(f.startswith("R10:") for f in findings), str(findings))

    # -----------------------------------------------------------------
    # Requirement 5 / "a scouted repo missing from scouts.json": an empty
    # status, a gaps entry naming it, and no state.repos entry (so it is
    # offered to be scouted again next time rather than silently becoming
    # a dormant "carried" repository with nothing in it).
    # -----------------------------------------------------------------
    facts = base_facts()
    facts["repos"] = [{
        "repo": "work/missing-scout", "path": "/home/owner/src/work/missing-scout", "folder": "work",
        "alias_of": None, "sweep": base_sweep("work/missing-scout"), "gh": None, "activity": "active",
        "logs_in_window": [], "snapshot": None, "status_source": "scout", "carried": None,
        "unprotected_work": [], "to_scout": True, "current_status_candidate": True,
    }]
    pulse, new_state = build_pulse.build_pulse(facts, [], {}, {}, {"repos": {}, "first_seen": {}})
    repo_record = pulse["repos"][0]
    check("a scouted repository missing from scouts.json gets an empty status",
          repo_record["status"] == build_pulse.empty_status(), json.dumps(repo_record["status"]))
    check("a scouted repository missing from scouts.json gets a gaps entry naming it",
          any(g.get("source") == "scout" and "work/missing-scout" in g.get("detail", "") for g in pulse["gaps"]),
          str(pulse["gaps"]))
    check("a scouted repository missing from scouts.json writes no state.repos entry",
          "work/missing-scout" not in new_state["repos"])

    # -----------------------------------------------------------------
    # First run on a tree: --state names a file that does not exist yet.
    # The schema's own flow diagram marks state.json "updated after
    # validation", an output, so its absence must not be a BROKEN input.
    # -----------------------------------------------------------------
    fresh_dir = tmp_root / "fresh-state"
    facts = base_facts()
    facts["repos"] = [{
        "repo": "work/first-run", "path": "/home/owner/src/work/first-run", "folder": "work",
        "alias_of": None, "sweep": base_sweep("work/first-run"), "gh": None, "activity": "dormant",
        "logs_in_window": [], "snapshot": None, "status_source": "sweep-only", "carried": None,
        "unprotected_work": [], "to_scout": False, "current_status_candidate": False,
    }]
    write_json(fresh_dir / "pulse-facts.json", facts)
    write_json(fresh_dir / "curation.json", {})
    fresh_state_path = fresh_dir / "state.json"
    check("a state.json path does not exist before the first run (fixture sanity)",
          not fresh_state_path.exists())

    args2 = Args()
    args2.facts = str(fresh_dir / "pulse-facts.json")
    args2.scouts = None
    args2.curation = str(fresh_dir / "curation.json")
    args2.digest = None
    args2.spend = None
    args2.state = str(fresh_state_path)
    args2.out = str(fresh_dir / "out")
    rc3 = build_pulse.run(args2)
    check("a first run with no prior state.json exits 0 and creates it",
          rc3 == 0 and fresh_state_path.is_file(), "exit=%d" % rc3)


if __name__ == "__main__":
    sys.exit(main())
