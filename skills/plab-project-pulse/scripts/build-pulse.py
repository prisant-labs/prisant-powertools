#!/usr/bin/env python3
"""Assemble pulse.json, coverage.md and (conditionally) state.json for plab-project-pulse.

USAGE
-----
  build-pulse.py --facts pulse-facts.json [--scouts scouts.json]
                  [--curation curation.json] [--digest digest.jsonl]
                  [--spend projects.json] --state state.json --out DIR

EXIT-CODE CONTRACT
------------------
  0  CLEAN     pulse.json validated; pulse.json, coverage.md and state.json written
  1  FINDINGS  pulse.json did not validate; pulse.json and coverage.md are written
               (so the failure is inspectable), state.json is left untouched
  2  BROKEN    an input file was missing, unreadable, or not valid JSON/JSONL

NEVER INTERPRET 2 AS CLEAN.

WHY STATE IS WRITTEN ONLY AFTER VALIDATION (Requirement 18)
-------------------------------------------------------------
`state.json` is the carry-forward store: next week's dormant repositories
read it back as `carried`. Writing it from a `pulse.json` that failed
validation would carry a bad waiting-item source, a malformed activity
value or similar forward into every future week silently. So this script
always assembles and writes `pulse.json` (an inspectable failure is better
than none), always writes `coverage.md`, and writes `state.json` only when
`pulse_check.check_pulse()` (imported by file path from `pulse-check.py`,
because that filename is not a valid module identifier; see
`skills/plab-resolve-open-items/scripts/gather-backlog.py` for the same
import pattern) returns no findings.

WHAT IS NOT RECOMPUTED FOR A CARRIED REPOSITORY
-------------------------------------------------
A dormant repository with a previous state entry "keeps it" (Requirement
7): its status and its `refreshed` stamp (`carried_from`) are rebuilt from
`pulse-facts.json`'s `carried` field, not re-derived here, because that
field already IS the prior entry, forwarded unchanged by
`derive-pulse-facts.py`; nothing new was examined, so nothing here invents
a different value for `summary`, `whats_next`, `pending_decisions` or
`risks`. Its waiting items' `age_days` ARE recomputed from the window's
end date and the state file's `first_seen` map, because an item does not
stop aging while its repository is dormant; only the thing being aged is
unchanged, not the age.

WHY A SCOUT-GAP OR SWEEP-ONLY REPOSITORY WRITES NO STATE ENTRY
------------------------------------------------------------------
A repository marked `to_scout` with no matching record in `scouts.json`,
or one that has never had a snapshot or a scout, gets an explicit `gaps`
entry and an empty status, same as any genuinely sweep-only repository.
If it also got a state entry, the following run would read it back as
`carried` with that empty status, and the gap that explained why would be
gone. So no entry is written for either case, and the repository is
offered to be scouted (or flagged sweep-only) again next time.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing pulse-check.py below must not write __pycache__

WHATS_NEXT_CAP = 10


class Broken(Exception):
    pass


def load_pulse_check():
    path = Path(__file__).resolve().parent / "pulse-check.py"
    spec = importlib.util.spec_from_file_location("plab_pulse_check_for_build", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Loading inputs
# ---------------------------------------------------------------------------


def read_json(path, default=None):
    if path is None:
        return default
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise Broken("cannot read %s: %s" % (path, exc))
    try:
        return json.loads(text)
    except ValueError as exc:
        raise Broken("%s is not valid JSON: %s" % (path, exc))


def read_jsonl(path):
    if path is None:
        return []
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise Broken("cannot read %s: %s" % (path, exc))
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError as exc:
            raise Broken("%s line %d is not valid JSON: %s" % (path, i + 1, exc))
    return out


def spend_map_from(spend_data):
    """Accepts {repo: usd, ...} or [{"repo": ..., "spend_usd": ...}, ...]. Exact-name match only."""
    if spend_data is None:
        return {}
    if isinstance(spend_data, dict):
        return dict(spend_data)
    out = {}
    for row in spend_data:
        name = row.get("repo")
        if name:
            out[name] = row.get("spend_usd")
    return out


# ---------------------------------------------------------------------------
# Waiting-item ages (Requirement 11): since the item's own stated date when
# given, else the state file's first_seen for the same repo and normalized
# text, else today (this window's end), which also seeds first_seen for the
# next run.
# ---------------------------------------------------------------------------


def normalize_text(text):
    text = re.sub(r"\s+", " ", (text or "").strip().lower())
    text = re.sub(r"^[^\w]+", "", text)
    text = re.sub(r"[^\w]+$", "", text)
    return text


def first_seen_key(repo, text):
    return "%s::%s" % (repo, normalize_text(text))


def age_item(repo, item, window_end, old_first_seen, new_first_seen):
    key = first_seen_key(repo, item.get("text", ""))
    since = item.get("since")
    first_seen = since or old_first_seen.get(key) or window_end
    new_first_seen[key] = first_seen
    age_days = (dt.date.fromisoformat(window_end) - dt.date.fromisoformat(first_seen)).days
    out = dict(item)
    out["first_seen"] = first_seen
    out["age_days"] = age_days
    return out


def empty_status():
    return {"summary": None, "whats_next": [], "waiting_on_you": [], "pending_decisions": [], "risks": []}


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_repo(facts_repo, scouts_by_name, old_first_seen, new_first_seen, window_end, gaps, spend_map,
                state_updates):
    name = facts_repo["repo"]
    source = facts_repo.get("status_source")
    conflicts = []
    carried_from = None
    refreshed = None
    head = (facts_repo.get("sweep") or {}).get("head")

    def aged(items):
        return [age_item(name, it, window_end, old_first_seen, new_first_seen) for it in (items or [])]

    if source == "snapshot":
        snap = facts_repo.get("snapshot") or {}
        status = {
            "summary": None,
            "whats_next": snap.get("whats_next", []) or [],
            "waiting_on_you": aged(snap.get("waiting_on_you")),
            "pending_decisions": snap.get("pending_decisions", []) or [],
            "risks": [],
        }
        refreshed = snap.get("date")
        state_updates[name] = {"status": status, "refreshed": refreshed, "head": head}
    elif source == "scout":
        scout = scouts_by_name.get(name)
        if scout is None:
            gaps.append({"source": "scout", "detail": "no scout record for %s" % name})
            status = empty_status()
        else:
            status = {
                "summary": scout.get("summary"),
                "whats_next": scout.get("whats_next", []) or [],
                "waiting_on_you": aged(scout.get("waiting_on_you")),
                "pending_decisions": scout.get("pending_decisions", []) or [],
                "risks": scout.get("risks", []) or [],
            }
            conflicts = scout.get("conflicts", []) or []
            refreshed = window_end
            state_updates[name] = {"status": status, "refreshed": refreshed, "head": head}
    elif source == "carried":
        carried = facts_repo.get("carried") or {}
        carried_from = carried.get("carried_from")
        status = {
            "summary": carried.get("summary"),
            "whats_next": carried.get("whats_next", []) or [],
            "waiting_on_you": aged(carried.get("waiting_on_you")),
            "pending_decisions": carried.get("pending_decisions", []) or [],
            "risks": carried.get("risks", []) or [],
        }
        # The entry itself (status as it last stood, head, refreshed stamp) is
        # carried through unchanged; ages above are recomputed, not the entry.
        state_updates[name] = {"status": {
            "summary": carried.get("summary"),
            "whats_next": carried.get("whats_next", []) or [],
            "waiting_on_you": carried.get("waiting_on_you", []) or [],
            "pending_decisions": carried.get("pending_decisions", []) or [],
            "risks": carried.get("risks", []) or [],
        }, "refreshed": carried_from, "head": head}
    else:
        status = empty_status()

    return {
        "repo": name,
        "path": facts_repo.get("path"),
        "folder": facts_repo.get("folder"),
        "alias_of": facts_repo.get("alias_of"),
        "activity": facts_repo.get("activity"),
        "status_source": source,
        "carried_from": carried_from,
        "sweep": facts_repo.get("sweep"),
        "gh": facts_repo.get("gh"),
        "status": status,
        "conflicts": conflicts,
        "unprotected_work": facts_repo.get("unprotected_work", []) or [],
        "current_status_candidate": bool(facts_repo.get("current_status_candidate", False)),
        "spend_usd": spend_map.get(name),
    }


def build_pulse(facts, scouts, curation, spend_map, old_state):
    window = facts["window"]
    window_end = window["end"]
    old_first_seen = dict(old_state.get("first_seen", {}))
    new_first_seen = {}
    state_updates = {}
    gaps = list(facts.get("gaps", []) or [])
    scouts_by_name = {s["repo"]: s for s in (scouts or [])}

    repos = [build_repo(fr, scouts_by_name, old_first_seen, new_first_seen, window_end, gaps, spend_map,
                         state_updates)
             for fr in facts.get("repos", [])]

    whats_next = [dict(item) for item in (curation.get("whats_next", []) or [])][:WHATS_NEXT_CAP]
    agents = list(curation.get("agents", []) or [])

    # Top-level waiting_on_you: every repository's waiting items, ranked by
    # age_days descending; ties broken by repo then text so the ranking is
    # reproducible.
    pool = []
    for repo in repos:
        for item in repo["status"]["waiting_on_you"]:
            pool.append((repo["repo"], item))
    pool.sort(key=lambda pair: (-pair[1].get("age_days", 0), pair[0], pair[1].get("text", "")))
    waiting_on_you = [
        {"rank": i + 1, "repo": repo_name, "item": item.get("text"),
         "age_days": item.get("age_days"), "source": item.get("source")}
        for i, (repo_name, item) in enumerate(pool)
    ]

    active = sum(1 for r in repos if r["activity"] == "active")
    dormant = sum(1 for r in repos if r["activity"] == "dormant")
    totals = {
        "repos": len(repos),
        "active": active,
        "dormant": dormant,
        "aliases": sum(1 for r in repos if r.get("alias_of")),
        "commits_focus": sum((r.get("sweep") or {}).get("commits_focus", 0) or 0 for r in repos),
        "tags_in_window": sum(len((r.get("sweep") or {}).get("tags_in_window", []) or []) for r in repos),
        "waiting_on_you": len(waiting_on_you),
        "snapshots_fresh": sum(1 for r in repos if r["status_source"] == "snapshot"),
    }

    pulse = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": facts.get("mode"),
        "window": window,
        "totals": totals,
        "repos": repos,
        "whats_next": whats_next,
        "waiting_on_you": waiting_on_you,
        "agents": agents,
        "gaps": gaps,
    }
    new_state = {
        "schema_version": 1,
        "updated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repos": state_updates,
        "first_seen": new_first_seen,
    }
    return pulse, new_state


# ---------------------------------------------------------------------------
# coverage.md (C4, nine headings in order; see pulse-check.py's module
# docstring for why nine and not the ten the prose's own list would suggest)
# ---------------------------------------------------------------------------


def render_coverage(facts, pulse, digest_records, pulse_check):
    window = facts["window"]
    lines = []

    def heading(name):
        lines.append("## %s" % name)
        lines.append("")

    def bullets(items):
        if not items:
            lines.append("None.")
        else:
            for item in items:
                lines.append("- %s" % item)
        lines.append("")

    heading(pulse_check.COVERAGE_HEADINGS[0])  # Window and zone
    bullets(["%s to %s, %s. Prior window started %s." %
             (window["start"], window["end"], window["timezone"], window["prior_start"])])

    heading(pulse_check.COVERAGE_HEADINGS[1])  # Roots and depth
    roots_line = ["Roots: %s." % ", ".join(facts.get("roots", []) or ["none configured"])]
    if facts.get("max_depth") is not None:
        roots_line.append("Maximum depth: %s." % facts["max_depth"])
    else:
        roots_line.append("Maximum depth: not reported by the facts.")
    bullets(roots_line)

    heading(pulse_check.COVERAGE_HEADINGS[2])  # Repositories found and aliases skipped
    aliases = [r for r in pulse["repos"] if r.get("alias_of")]
    rows = ["%d repositories found." % len(pulse["repos"])]
    rows += ["%s is an alias of %s; its sweep is not counted separately."
             % (a["repo"], a["alias_of"]) for a in aliases]
    bullets(rows)

    heading(pulse_check.COVERAGE_HEADINGS[3])  # Repositories without an upstream
    no_upstream = [r["repo"] for r in pulse["repos"] if (r.get("sweep") or {}).get("has_upstream") is False]
    bullets(no_upstream)

    heading(pulse_check.COVERAGE_HEADINGS[4])  # gh failures
    gh_gaps = [g.get("detail") for g in pulse["gaps"] if g.get("source") == "gh"]
    bullets(gh_gaps)

    heading(pulse_check.COVERAGE_HEADINGS[5])  # Snapshots read and stale
    snap_rows = ["%s: read, %s" % (r["repo"], (r.get("sweep") or {}).get("snapshot_utc", "unknown time"))
                 for r in pulse["repos"] if r["status_source"] == "snapshot"]
    stale_rows = ["%s: active with no fresh snapshot, candidate for /plab-current-status" % r["repo"]
                  for r in pulse["repos"] if r.get("current_status_candidate")]
    bullets(snap_rows + stale_rows)

    heading(pulse_check.COVERAGE_HEADINGS[6])  # Logs read and nonstandard names
    log_rows = ["%s (%s)%s" % (l.get("file"), l.get("repo"), " - nonstandard name" if l.get("nonstandard_name") else "")
                for l in digest_records]
    bullets(log_rows)

    heading(pulse_check.COVERAGE_HEADINGS[7])  # Agents
    agent_rows = ["%s/%s: %s, assigned %s, returned %s%s" %
                  (a.get("stage"), a.get("label"), a.get("model"), a.get("assigned"), a.get("returned"),
                   " (escalated)" if a.get("escalated") else "")
                  for a in pulse["agents"]]
    bullets(agent_rows)

    heading(pulse_check.COVERAGE_HEADINGS[8])  # Escalations and items still missing
    escalations = ["%s/%s escalated" % (a.get("stage"), a.get("label")) for a in pulse["agents"] if a.get("escalated")]
    remaining_gaps = ["%s: %s" % (g.get("source"), g.get("detail")) for g in pulse["gaps"] if g.get("source") not in ("gh",)]
    bullets(escalations + remaining_gaps)

    return "\n".join(lines).rstrip() + "\n"


def logs_for_coverage(digest_records, facts):
    if digest_records:
        return digest_records
    return facts.get("logs", []) or []


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def run(args):
    pulse_check = load_pulse_check()

    facts = read_json(args.facts)
    if facts is None:
        raise Broken("--facts is required")
    scouts = read_json(args.scouts, default=[])
    curation = read_json(args.curation, default={})
    digest_records = read_jsonl(args.digest)
    spend_data = read_json(args.spend, default=None)
    # The first run on a tree has no prior state.json yet; the schema's own
    # flow diagram marks it "updated after validation", i.e. an output, so
    # its absence is not an input error, only an empty carry-forward store.
    state_path = Path(args.state)
    old_state = (read_json(args.state, default=None) if state_path.is_file()
                 else {"schema_version": 1, "repos": {}, "first_seen": {}})

    spend_map = spend_map_from(spend_data)
    pulse, new_state = build_pulse(facts, scouts, curation, spend_map, old_state)

    findings = pulse_check.check_pulse(pulse)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pulse.json").write_text(json.dumps(pulse, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    coverage_text = render_coverage(facts, pulse, logs_for_coverage(digest_records, facts), pulse_check)
    (out_dir / "coverage.md").write_text(coverage_text, encoding="utf-8")

    if findings:
        for f in findings:
            print(f)
        print("FINDINGS: %d rule failure(s); state.json was not written" % len(findings))
        return 1

    Path(args.state).write_text(json.dumps(new_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("CLEAN: pulse.json validated; wrote pulse.json, coverage.md and %s" % args.state)
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Assemble pulse.json, coverage.md and state.json.")
    parser.add_argument("--facts", required=True)
    parser.add_argument("--scouts")
    parser.add_argument("--curation")
    parser.add_argument("--digest")
    parser.add_argument("--spend")
    parser.add_argument("--state", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Broken as exc:
        print("BROKEN: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
