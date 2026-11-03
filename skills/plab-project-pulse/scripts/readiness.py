#!/usr/bin/env python3
"""Rank the week's work by readiness for a long autonomous run (PP-01 D2).

USAGE
-----
  readiness.py candidates --pulse <run>/pulse.json --out <run>/readiness-candidates.json [--max 8]
  readiness.py build --candidates <run>/readiness-candidates.json --judge <run>/readiness-judge.json
                     --out <run>/readiness.json

EXIT-CODE CONTRACT
------------------
  0  CLEAN     the file was written and every candidate was judged
  1  FINDINGS  readiness.json was written, but the judge returned nothing usable
               for at least one candidate; each is named in `gaps`, and the main
               loop re-runs the judge once on the next tier for those
  2  BROKEN    an input could not be read or was malformed

NEVER INTERPRET 2 AS CLEAN.

THE SEVEN CRITERIA, AND WHO SCORES WHICH
------------------------------------------
The criteria are the ones the owner's hand-run rankings of 2026-10-09 and
2026-10-28 used, copied into `references/workflow.md`. Three are facts this
script reads without a model, so the judge agent never spends a turn on them:

  github_pr_flow       the sweep's `remote` is on GitHub
  agent_instructions   AGENTS.md or CLAUDE.md exists at the repository root
  clean_branch         the sweep counts no modified and no staged file

The other four need a reading of the repository, and the judge scores them:

  tests_pass           a test command, with evidence that it passes
  spec_with_acs        a spec with acceptance criteria for this work item
  checkpointed_stages  the work splits into stages that each end in a commit
  safe_tests           the tests have no destructive side effects

A candidate's level is `high` when all seven are met, `medium` at five or six,
and `low` below five. Items rank by met count, then by candidate order.

WHY CANDIDATES ARE CAPPED
---------------------------
The original D2 recommendation objected to a weekly judge's cost. One judge
reads at most four files for each of at most eight candidates, so the stage
costs one Sonnet agent. Candidates are the active repositories, with those
holding agent-actionable What's Next items first, then by focus-week commits.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_MAX = 8
MECHANICAL = ("github_pr_flow", "agent_instructions", "clean_branch")
JUDGED = ("tests_pass", "spec_with_acs", "checkpointed_stages", "safe_tests")
CRITERIA = ("github_pr_flow", "tests_pass", "spec_with_acs", "agent_instructions",
            "checkpointed_stages", "safe_tests", "clean_branch")
AGENT_WHO = ("agent", "agent-after-yes")


class Broken(Exception):
    pass


def now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise Broken("cannot read %s: %s" % (path, exc))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def level_for(met_count):
    if met_count == len(CRITERIA):
        return "high"
    if met_count >= 5:
        return "medium"
    return "low"


# ------------------------------------------------------------------ candidates
def mechanical_criteria(repo):
    sweep = repo.get("sweep") or {}
    remote = sweep.get("remote") or ""
    on_github = "github.com" in remote.lower()
    path = repo.get("path") or ""
    found = [n for n in ("AGENTS.md", "CLAUDE.md") if path and os.path.isfile(os.path.join(path, n))]
    dirty = int(sweep.get("dirty_files") or 0)
    staged = int(sweep.get("staged_files") or 0)
    return {
        "github_pr_flow": {"met": on_github,
                           "evidence": ("remote %s" % remote) if on_github
                           else ("remote is not on GitHub: %s" % (remote or "none"))},
        "agent_instructions": {"met": bool(found),
                               "evidence": ("%s at the root" % " and ".join(found)) if found
                               else "no AGENTS.md or CLAUDE.md at the root"},
        "clean_branch": {"met": dirty == 0 and staged == 0,
                         "evidence": "%d modified and %d staged file(s)" % (dirty, staged)},
    }


def select_candidates(pulse, max_count):
    repos = [r for r in pulse.get("repos", []) if r.get("activity") == "active" and not r.get("alias_of")]
    best_rank = {}
    for item in pulse.get("whats_next", []) or []:
        if item.get("who") in AGENT_WHO:
            best_rank.setdefault(item.get("repo"), item.get("rank") or 99)

    def order(r):
        rank = best_rank.get(r["repo"])
        return (0 if rank is not None else 1, rank or 0, -int((r.get("sweep") or {}).get("commits_focus") or 0), r["repo"])

    return sorted(repos, key=order)[:max_count]


def build_candidates(pulse, max_count):
    out = []
    for repo in select_candidates(pulse, max_count):
        status = repo.get("status") or {}
        out.append({
            "repo": repo["repo"],
            "path": repo.get("path"),
            "work_items": [{"text": w.get("text"), "source": w.get("source")}
                           for w in status.get("whats_next", []) or []],
            "criteria": mechanical_criteria(repo),
        })
    return {"schema_version": SCHEMA_VERSION, "generated_at": now_iso(),
            "window": pulse.get("window"), "max": max_count, "candidates": out}


# ----------------------------------------------------------------------- build
def usable_judgement(entry):
    """A judge entry is usable when it names a work item with a source and scores
    all four judged criteria, each with a boolean and non-empty evidence."""
    if not isinstance(entry, dict):
        return False
    work = entry.get("work_item") or {}
    if not (work.get("text") and work.get("source")):
        return False
    crit = entry.get("criteria") or {}
    for key in JUDGED:
        c = crit.get(key)
        if not isinstance(c, dict) or not isinstance(c.get("met"), bool) or not (c.get("evidence") or "").strip():
            return False
    return True


def build_readiness(candidates, judge):
    if not isinstance(judge, dict) or not isinstance(judge.get("results"), list):
        raise Broken("readiness-judge.json must hold an object with a `results` list")
    agent = judge.get("agent")
    if not isinstance(agent, dict) or not agent.get("model"):
        raise Broken("readiness-judge.json's `agent` record must name a model")
    by_repo = {}
    for entry in judge["results"]:
        if isinstance(entry, dict) and entry.get("repo"):
            by_repo[entry["repo"]] = entry

    items, gaps = [], []
    for order, cand in enumerate(candidates.get("candidates", [])):
        entry = by_repo.get(cand["repo"])
        if not usable_judgement(entry):
            gaps.append({"source": "readiness-judge",
                         "detail": "no usable judgement for %s" % cand["repo"]})
            continue
        criteria = {}
        for key in CRITERIA:
            src = cand["criteria"] if key in MECHANICAL else entry["criteria"]
            criteria[key] = {"met": bool(src[key]["met"]), "evidence": src[key]["evidence"].strip()}
        met = sum(1 for c in criteria.values() if c["met"])
        items.append({"repo": cand["repo"], "work_item": entry["work_item"]["text"],
                      "source": entry["work_item"]["source"], "level": level_for(met),
                      "met_count": met, "criteria": criteria, "_order": order})
    items.sort(key=lambda i: (-i["met_count"], i["_order"]))
    for rank, item in enumerate(items, 1):
        item.pop("_order")
        item["rank"] = rank
    agent = dict(agent)
    agent.setdefault("stage", "readiness-judge")
    agent.setdefault("assigned", len(candidates.get("candidates", [])))
    agent.setdefault("returned", len(by_repo))
    return {"schema_version": SCHEMA_VERSION, "generated_at": now_iso(),
            "window": candidates.get("window"), "agent": agent,
            "items": [{k: i[k] for k in ("rank", "repo", "work_item", "source", "level", "met_count", "criteria")}
                      for i in items],
            "gaps": gaps}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Rank readiness for long autonomous runs.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates")
    c.add_argument("--pulse", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--max", type=int, default=DEFAULT_MAX)
    b = sub.add_parser("build")
    b.add_argument("--candidates", required=True)
    b.add_argument("--judge", required=True)
    b.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    try:
        if args.cmd == "candidates":
            data = build_candidates(load_json(args.pulse), max(1, args.max))
            write_json(args.out, data)
            print("CLEAN: %d candidate(s) written to %s" % (len(data["candidates"]), args.out))
            return 0
        data = build_readiness(load_json(args.candidates), load_json(args.judge))
        write_json(args.out, data)
    except Broken as exc:
        print("BROKEN: %s" % exc)
        return 2
    if data["gaps"]:
        print("FINDINGS: %d candidate(s) not judged: %s"
              % (len(data["gaps"]), "; ".join(g["detail"] for g in data["gaps"])))
        return 1
    print("CLEAN: %d item(s) ranked in %s" % (len(data["items"]), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
