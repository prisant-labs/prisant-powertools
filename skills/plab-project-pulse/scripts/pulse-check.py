#!/usr/bin/env python3
"""Validate a plab-project-pulse output directory, after proving every rule can fail.

USAGE
-----
  pulse-check.py <dir>
  pulse-check.py --self-test

EXIT-CODE CONTRACT
------------------
  0  CLEAN     the self-test passed AND <dir>'s output satisfies every rule
  1  FINDINGS  the self-test passed AND at least one rule failed; each is named
  2  BROKEN    the self-test failed, or the directory could not be read

NEVER INTERPRET 2 AS CLEAN. Every run proves the rules first, against the
committed sample under `examples/sample-pulse/` and one mutation per rule on
a temporary copy, so a rule that has gone blind stops the run instead of
passing everything. This is the contract `skills/plab-audit/scripts/bundle-check.py`
and `skills/plab-current-status/scripts/status-check.py` already carry.

THE RULES (references/pulse-schema.md, "Rules `pulse-check.py` enforces")
---------------------------------------------------------------------------
  R1  every top-level key is present, and every repository record carries
      every key the schema lists for a repository
  R2  `activity` is `active` or `dormant`; `status_source` is one of the
      four values; `carried_from` is a date exactly when `status_source`
      is `carried`, and null otherwise
  R3  every item under `status.whats_next`, `status.waiting_on_you`,
      `status.pending_decisions`, `status.risks`, the top-level
      `whats_next` and `waiting_on_you`, has a non-empty `source`
  R4  every `status.waiting_on_you` item has an integer `age_days` of zero
      or more, and a `first_seen` date
  R5  the top-level `whats_next` has at most ten items, ranked 1 to n
      without gaps, and each `who` is one of the three values
  R6  the top-level `waiting_on_you` is every repository's waiting items,
      ranked by `age_days` descending, so its length equals the sum of the
      repositories' `status.waiting_on_you` lengths
  R7  `totals.repos` equals the number of repository records, and
      `totals.active` plus `totals.dormant` equals it
  R8  every agent in `agents` names a `model`; `returned` is at most
      `assigned`
  R9  `coverage.md`'s nine level-2 headings appear, in order (Requirement
      20; see the module docstring's note on the schema discrepancy below)
  R10 `dashboard.html`'s count of `class="repo-card"` elements equals the
      number of repository records in `pulse.json` (AC-22)

R1 TO R8 TAKE PARSED JSON; R9 AND R10 NEED THE DIRECTORY
----------------------------------------------------------
`check_pulse(data)` runs R1 to R8 against an already-parsed `pulse.json`
dict, with no filesystem access, so `build-pulse.py` can call it before
`coverage.md` or `dashboard.html` exist (it imports this module by file
path, because `pulse-check.py` is not a valid Python identifier; see
`skills/plab-resolve-open-items/scripts/gather-backlog.py` for the same
pattern). `check_dir(path)` reads all three files and adds R9 and R10.

A SCHEMA DISCREPANCY, REPORTED RATHER THAN SILENTLY RESOLVED
---------------------------------------------------------------
`references/pulse-schema.md`'s contract C4 and this spec's Requirement 20
both say `coverage.md` has "nine headings, in order". But C4's own
semicolon-separated list names TEN items: the window and zone; the roots
and depth; repositories found and aliases skipped; repositories without an
upstream; `gh` failures with their commands; snapshots read and snapshots
stale; logs read and nonstandard names; every agent with its model and
assigned and returned counts; escalations and items still missing; and
the snapshot times, as a tenth, separate clause.

Read literally there are ten clauses, not nine. This checker (and
`build-pulse.py`'s writer) resolve the conflict by reading "the snapshot
times" as elaborating the sixth clause ("snapshots read and snapshots
stale") rather than naming a tenth heading, which is the only reading that
produces nine. `COVERAGE_HEADINGS` below is the single place this
resolution lives; both scripts import it from here rather than restating
it, so the two readings cannot drift apart even though the prose itself
still disagrees with its own count.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# The coverage statement's nine headings, in order. See the module docstring
# for why this is nine and not the ten the prose's own list would suggest.
# ---------------------------------------------------------------------------
COVERAGE_HEADINGS = [
    "Window and zone",
    "Roots and depth",
    "Repositories found and aliases skipped",
    "Repositories without an upstream",
    "gh failures",
    "Snapshots read and stale",
    "Logs read and nonstandard names",
    "Agents",
    "Escalations and items still missing",
]

ACTIVITY_VALUES = {"active", "dormant"}
STATUS_SOURCE_VALUES = {"snapshot", "scout", "carried", "sweep-only"}
WHO_VALUES = {"owner", "agent", "agent-after-yes"}
WHATS_NEXT_CAP = 10
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
CARD_RE = re.compile(r'<[^>]*\bclass="[^"]*\brepo-card\b[^"]*"[^>]*\bdata-repo="([^"]*)"')

TOP_LEVEL_KEYS = ("schema_version", "generated_at", "mode", "window", "totals",
                   "repos", "whats_next", "waiting_on_you", "agents", "gaps")
REPO_KEYS = ("repo", "path", "folder", "alias_of", "activity", "status_source",
             "carried_from", "sweep", "gh", "status", "conflicts",
             "unprotected_work", "current_status_candidate", "spend_usd")
STATUS_KEYS = ("summary", "whats_next", "waiting_on_you", "pending_decisions", "risks")
SOURCED_STATUS_LISTS = ("whats_next", "waiting_on_you", "pending_decisions", "risks")


class Broken(Exception):
    pass


# ---------------------------------------------------------------------------
# R1 to R8: pure functions over parsed JSON
# ---------------------------------------------------------------------------


def _non_empty_source(items, where, out):
    for i, item in enumerate(items):
        if not (item.get("source") or "").strip():
            out.append("R3: %s item %d has an empty source: %r" % (where, i, item))


def r1_keys(data):
    out = []
    for key in TOP_LEVEL_KEYS:
        if key not in data:
            out.append("R1: pulse.json has no top-level key %r" % key)
    for i, repo in enumerate(data.get("repos", [])):
        for key in REPO_KEYS:
            if key not in repo:
                out.append("R1: repository %d (%r) has no key %r" % (i, repo.get("repo"), key))
        status = repo.get("status", {})
        if isinstance(status, dict):
            for key in STATUS_KEYS:
                if key not in status:
                    out.append("R1: repository %d (%r) status has no key %r" % (i, repo.get("repo"), key))
    return out


def r2_enums(data):
    out = []
    for i, repo in enumerate(data.get("repos", [])):
        name = repo.get("repo")
        activity = repo.get("activity")
        if activity not in ACTIVITY_VALUES:
            out.append("R2: repository %d (%r) has activity %r, not one of %s" % (i, name, activity, sorted(ACTIVITY_VALUES)))
        source = repo.get("status_source")
        if source not in STATUS_SOURCE_VALUES:
            out.append("R2: repository %d (%r) has status_source %r, not one of %s" % (i, name, source, sorted(STATUS_SOURCE_VALUES)))
        carried_from = repo.get("carried_from")
        if source == "carried":
            if not (isinstance(carried_from, str) and DATE_RE.match(carried_from)):
                out.append("R2: repository %d (%r) is carried but carried_from is %r, not a date" % (i, name, carried_from))
        elif carried_from is not None:
            out.append("R2: repository %d (%r) has status_source %r but carried_from is %r, not null" % (i, name, source, carried_from))
    return out


def r3_sources(data):
    out = []
    for repo in data.get("repos", []):
        name = repo.get("repo")
        status = repo.get("status", {}) or {}
        for field in SOURCED_STATUS_LISTS:
            _non_empty_source(status.get(field, []) or [], "%s status.%s" % (name, field), out)
    _non_empty_source(data.get("whats_next", []) or [], "top-level whats_next", out)
    _non_empty_source(data.get("waiting_on_you", []) or [], "top-level waiting_on_you", out)
    return out


def r4_ages(data):
    out = []
    for repo in data.get("repos", []):
        name = repo.get("repo")
        status = repo.get("status", {}) or {}
        for i, item in enumerate(status.get("waiting_on_you", []) or []):
            age = item.get("age_days")
            if not isinstance(age, int) or isinstance(age, bool) or age < 0:
                out.append("R4: %s waiting_on_you item %d has age_days %r, not a non-negative integer" % (name, i, age))
            if not item.get("first_seen"):
                out.append("R4: %s waiting_on_you item %d has no first_seen date" % (name, i))
    return out


def r5_whats_next(data):
    out = []
    items = data.get("whats_next", []) or []
    if len(items) > WHATS_NEXT_CAP:
        out.append("R5: top-level whats_next has %d items; at most %d are allowed" % (len(items), WHATS_NEXT_CAP))
    ranks = [item.get("rank") for item in items]
    if ranks != list(range(1, len(items) + 1)):
        out.append("R5: top-level whats_next ranks are %r; expected 1..%d without gaps" % (ranks, len(items)))
    for i, item in enumerate(items):
        if item.get("who") not in WHO_VALUES:
            out.append("R5: top-level whats_next item %d has who %r, not one of %s" % (i, item.get("who"), sorted(WHO_VALUES)))
    return out


def r6_waiting_rank(data):
    out = []
    top = data.get("waiting_on_you", []) or []
    expected_len = sum(len((repo.get("status", {}) or {}).get("waiting_on_you", []) or [])
                        for repo in data.get("repos", []))
    if len(top) != expected_len:
        out.append("R6: top-level waiting_on_you has %d item(s); the repositories' status.waiting_on_you "
                    "lists total %d" % (len(top), expected_len))
    ranks = [item.get("rank") for item in top]
    if ranks != list(range(1, len(top) + 1)):
        out.append("R6: top-level waiting_on_you ranks are %r; expected 1..%d without gaps" % (ranks, len(top)))
    ages = [item.get("age_days") for item in top]
    for i in range(1, len(ages)):
        if isinstance(ages[i - 1], int) and isinstance(ages[i], int) and ages[i] > ages[i - 1]:
            out.append("R6: top-level waiting_on_you is not ranked by age_days descending at rank %d: "
                        "%r then %r" % (i + 1, ages[i - 1], ages[i]))
    return out


def r7_totals(data):
    out = []
    totals = data.get("totals", {}) or {}
    repos = data.get("repos", []) or []
    if totals.get("repos") != len(repos):
        out.append("R7: totals.repos is %r; there are %d repository records" % (totals.get("repos"), len(repos)))
    active = totals.get("active")
    dormant = totals.get("dormant")
    if isinstance(active, int) and isinstance(dormant, int):
        if active + dormant != totals.get("repos"):
            out.append("R7: totals.active (%r) plus totals.dormant (%r) does not equal totals.repos (%r)"
                        % (active, dormant, totals.get("repos")))
    else:
        out.append("R7: totals.active (%r) and totals.dormant (%r) must both be integers" % (active, dormant))
    return out


def r8_agents(data):
    out = []
    for i, agent in enumerate(data.get("agents", []) or []):
        if not (agent.get("model") or "").strip():
            out.append("R8: agent %d (%r) names no model" % (i, agent.get("label")))
        assigned, returned = agent.get("assigned"), agent.get("returned")
        if isinstance(assigned, int) and isinstance(returned, int) and returned > assigned:
            out.append("R8: agent %d (%r) returned %d but was assigned %d" % (i, agent.get("label"), returned, assigned))
    return out


RULES = [r1_keys, r2_enums, r3_sources, r4_ages, r5_whats_next, r6_waiting_rank, r7_totals, r8_agents]


def check_pulse(data):
    """R1 to R8 against an already-parsed pulse.json dict. No filesystem access."""
    out = []
    for rule in RULES:
        out.extend(rule(data))
    return out


# ---------------------------------------------------------------------------
# R9 and R10: need the directory
# ---------------------------------------------------------------------------


def r9_coverage_headings(coverage_text):
    headings = H2_RE.findall(coverage_text)
    if headings != COVERAGE_HEADINGS:
        return ["R9: coverage.md's level-2 headings are %r; expected exactly %r, in order"
                % (headings, COVERAGE_HEADINGS)]
    return []


def r10_card_count(dashboard_text, data):
    cards = CARD_RE.findall(dashboard_text)
    expected = len(data.get("repos", []) or [])
    if len(cards) != expected:
        return ["R10: dashboard.html has %d repo-card element(s); pulse.json lists %d repositor(y/ies)"
                % (len(cards), expected)]
    return []


def _read(path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise Broken("cannot read %s: %s" % (path, exc))


def check_dir(dir_path):
    """All ten rules against a directory holding pulse.json, coverage.md, dashboard.html."""
    d = Path(dir_path)
    if not d.is_dir():
        raise Broken("%s is not a directory" % dir_path)
    pulse_path = d / "pulse.json"
    coverage_path = d / "coverage.md"
    dashboard_path = d / "dashboard.html"
    for p in (pulse_path, coverage_path, dashboard_path):
        if not p.is_file():
            raise Broken("%s is missing from %s" % (p.name, dir_path))
    try:
        data = json.loads(_read(pulse_path))
    except ValueError as exc:
        raise Broken("pulse.json is not valid JSON: %s" % exc)
    if not isinstance(data, dict):
        raise Broken("pulse.json does not hold a JSON object")

    out = check_pulse(data)
    out.extend(r9_coverage_headings(_read(coverage_path)))
    out.extend(r10_card_count(_read(dashboard_path), data))
    return out


# ---------------------------------------------------------------------------
# Self-test: the committed sample passes clean, and one mutation per rule,
# applied to a temporary copy, makes exactly that rule fail.
# ---------------------------------------------------------------------------

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "examples" / "sample-pulse"


def _copy_sample(root):
    dest = Path(tempfile.mkdtemp(dir=root))
    for name in ("pulse.json", "coverage.md", "dashboard.html"):
        shutil.copyfile(SAMPLE_DIR / name, dest / name)
    return dest


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _replace_once(text, old, new, rule_id):
    if text.count(old) < 1:
        raise Broken("self-test mutation anchor for %s not found: %r" % (rule_id, old))
    return text.replace(old, new, 1)


def _first_repo_index(data, predicate):
    for i, repo in enumerate(data["repos"]):
        if predicate(repo):
            return i
    raise Broken("self-test: no repository in the sample matches a required mutation anchor")


def self_test():
    if not SAMPLE_DIR.is_dir():
        raise Broken("sample directory is missing: %s" % SAMPLE_DIR)
    clean = check_dir(SAMPLE_DIR)
    if clean:
        raise Broken("the committed sample fails its own checker: %s" % "; ".join(clean))

    root = tempfile.mkdtemp()
    try:
        sample_data = json.loads((SAMPLE_DIR / "pulse.json").read_text(encoding="utf-8"))
        sample_coverage = (SAMPLE_DIR / "coverage.md").read_text(encoding="utf-8")
        sample_dashboard = (SAMPLE_DIR / "dashboard.html").read_text(encoding="utf-8")

        proved = 0

        # R1: drop a top-level key.
        d = _copy_sample(root)
        data = dict(sample_data)
        del data["gaps"]
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R1", proved)
        proved += 1

        # R2: an invalid activity value.
        d = _copy_sample(root)
        data = json.loads(json.dumps(sample_data))
        data["repos"][0]["activity"] = "ACTIVE"
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R2", proved)
        proved += 1

        # R3: an empty source on a waiting item.
        d = _copy_sample(root)
        data = json.loads(json.dumps(sample_data))
        idx = _first_repo_index(data, lambda r: (r.get("status") or {}).get("waiting_on_you"))
        data["repos"][idx]["status"]["waiting_on_you"][0]["source"] = ""
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R3", proved)
        proved += 1

        # R4: a negative age_days.
        d = _copy_sample(root)
        data = json.loads(json.dumps(sample_data))
        idx = _first_repo_index(data, lambda r: (r.get("status") or {}).get("waiting_on_you"))
        data["repos"][idx]["status"]["waiting_on_you"][0]["age_days"] = -1
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R4", proved)
        proved += 1

        # R5: an eleventh whats_next item, breaking both the cap and the rank run.
        d = _copy_sample(root)
        data = json.loads(json.dumps(sample_data))
        extra = dict(data["whats_next"][-1])
        extra["rank"] = len(data["whats_next"]) + 1
        while len(data["whats_next"]) < WHATS_NEXT_CAP + 1:
            clone = dict(extra)
            clone["rank"] = len(data["whats_next"]) + 1
            data["whats_next"].append(clone)
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R5", proved)
        proved += 1

        # R6: reverse the top-level waiting_on_you order.
        d = _copy_sample(root)
        data = json.loads(json.dumps(sample_data))
        items = data["waiting_on_you"]
        if len(items) < 2:
            raise Broken("self-test: R6 needs at least two top-level waiting_on_you items")
        items.reverse()
        for i, item in enumerate(items, 1):
            item["rank"] = i
        data["waiting_on_you"] = items
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R6", proved)
        proved += 1

        # R7: a wrong totals.repos.
        d = _copy_sample(root)
        data = json.loads(json.dumps(sample_data))
        data["totals"]["repos"] = data["totals"]["repos"] + 1
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R7", proved)
        proved += 1

        # R8: an agent returning more than it was assigned.
        d = _copy_sample(root)
        data = json.loads(json.dumps(sample_data))
        if not data["agents"]:
            raise Broken("self-test: R8 needs at least one agent in the sample")
        data["agents"][0]["returned"] = data["agents"][0]["assigned"] + 1
        _write_json(d / "pulse.json", data)
        _assert_only(d, "R8", proved)
        proved += 1

        # R9: drop a coverage heading.
        d = _copy_sample(root)
        mutated = _replace_once(sample_coverage, "\n## Agents\n", "\n## Agent roster\n", "R9")
        (d / "coverage.md").write_text(mutated, encoding="utf-8")
        _assert_only(d, "R9", proved)
        proved += 1

        # R10: delete one repo-card element bodily.
        d = _copy_sample(root)
        first_card = CARD_RE.search(sample_dashboard)
        if not first_card:
            raise Broken("self-test: R10 needs at least one repo-card in the sample dashboard")
        end = sample_dashboard.index("</article>", first_card.start()) + len("</article>")
        mutated = sample_dashboard[:first_card.start()] + sample_dashboard[end:]
        (d / "dashboard.html").write_text(mutated, encoding="utf-8")
        _assert_only(d, "R10", proved)
        proved += 1

        return proved
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _assert_only(dir_path, rule_id, proved_so_far):
    findings = check_dir(dir_path)
    hits = [f for f in findings if f.startswith(rule_id + ":")]
    if not hits:
        raise Broken("self-test: mutation for %s did not make %s fail (findings: %r)" % (rule_id, rule_id, findings))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate a plab-project-pulse output directory.")
    parser.add_argument("dir", nargs="?", help="directory holding pulse.json, coverage.md, dashboard.html")
    parser.add_argument("--self-test", action="store_true", help="prove the rules against the committed sample only")
    args = parser.parse_args(argv)
    if not args.dir and not args.self_test:
        parser.error("give a directory, or --self-test")

    try:
        proved = self_test()
    except Broken as exc:
        print("BROKEN: %s" % exc)
        return 2
    print("self-test: PASS (the sample is clean and each of %d rules failed its own mutation)" % proved)
    if args.self_test:
        print("CLEAN: canary proved.")
        return 0

    try:
        findings = check_dir(args.dir)
    except Broken as exc:
        print("BROKEN: %s" % exc)
        return 2
    if findings:
        for f in findings:
            print(f)
        print("FINDINGS: %d rule failure(s) in %s" % (len(findings), args.dir))
        return 1
    print("CLEAN: canary proved, %s satisfies every rule." % args.dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
