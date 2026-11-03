#!/usr/bin/env python3
"""Fixture tests for readiness.py (PP-01 D2).

Run: python skills/plab-project-pulse/scripts/test-readiness.py

readiness.py is imported by file path (`importlib`), as test-build-render.py
imports its scripts, because the scripts folder is not a package.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SCRIPT = SCRIPTS / "readiness.py"

spec = importlib.util.spec_from_file_location("plab_readiness_under_test", SCRIPT)
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

results = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("  PASS  " if ok else "  FAIL  ") + name + ("" if ok else "  |  " + str(detail)))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def repo(name, path, remote="git@github.com:owner/%s.git", activity="active", dirty=0, staged=0,
         commits=1, alias_of=None, next_items=None):
    return {"repo": name, "path": str(path), "activity": activity, "alias_of": alias_of,
            "sweep": {"remote": remote % name.split("/")[-1] if "%s" in remote else remote,
                      "dirty_files": dirty, "staged_files": staged, "commits_focus": commits},
            "status": {"whats_next": next_items or [{"text": "do %s" % name, "source": "docs/plan.md"}]}}


def judged(name, met=True, work="do it"):
    return {"repo": name, "work_item": {"text": work, "source": "docs/plan.md"},
            "criteria": {k: {"met": met, "evidence": "read docs/plan.md"} for k in rd.JUDGED}}


def run(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for n in ("ready", "dirty", "busy", "asleep", "mirror", "nogit"):
            (tmp / n).mkdir()
        (tmp / "ready" / "AGENTS.md").write_text("x\n", encoding="utf-8")
        (tmp / "dirty" / "CLAUDE.md").write_text("x\n", encoding="utf-8")

        pulse = {
            "window": {"start": "2026-10-24", "end": "2026-10-30"},
            "repos": [
                repo("g/busy", tmp / "busy", commits=9),
                repo("g/ready", tmp / "ready", commits=1),
                repo("g/dirty", tmp / "dirty", dirty=2, staged=1, commits=5),
                repo("g/asleep", tmp / "asleep", activity="dormant"),
                repo("g/mirror", tmp / "mirror", alias_of="g/ready"),
                repo("g/nogit", tmp / "nogit", remote="git@example.com:owner/nogit.git", commits=3),
            ],
            "whats_next": [{"rank": 1, "repo": "g/busy", "who": "owner"},
                           {"rank": 2, "repo": "g/ready", "who": "agent"}],
        }

        # --- candidates -----------------------------------------------------
        cands = rd.build_candidates(pulse, 8)["candidates"]
        names = [c["repo"] for c in cands]
        check("candidates: dormant and alias repositories are left out",
              "g/asleep" not in names and "g/mirror" not in names, names)
        check("candidates: a repository with an agent-actionable next item comes first",
              names[0] == "g/ready", names)
        check("candidates: the rest follow by focus-week commits",
              names[1:] == ["g/busy", "g/dirty", "g/nogit"], names)
        check("candidates: --max caps the list", len(rd.build_candidates(pulse, 2)["candidates"]) == 2)
        by = {c["repo"]: c["criteria"] for c in cands}
        check("mechanical: a GitHub remote meets github_pr_flow",
              by["g/ready"]["github_pr_flow"]["met"] is True, by["g/ready"])
        check("mechanical: a non-GitHub remote does not",
              by["g/nogit"]["github_pr_flow"]["met"] is False, by["g/nogit"])
        check("mechanical: AGENTS.md or CLAUDE.md meets agent_instructions",
              by["g/ready"]["agent_instructions"]["met"] and by["g/dirty"]["agent_instructions"]["met"])
        check("mechanical: neither file fails agent_instructions",
              by["g/busy"]["agent_instructions"]["met"] is False)
        check("mechanical: modified or staged files fail clean_branch, naming the counts",
              by["g/dirty"]["clean_branch"] == {"met": False, "evidence": "2 modified and 1 staged file(s)"},
              by["g/dirty"]["clean_branch"])
        check("mechanical: every mechanical criterion carries evidence",
              all(v["evidence"] for c in cands for v in c["criteria"].values()))

        # --- build ----------------------------------------------------------
        cand_doc = rd.build_candidates(pulse, 8)
        judge = {"agent": {"label": "judge-1", "model": "sonnet", "escalated": False},
                 "results": [judged("g/ready"), judged("g/busy"), judged("g/dirty", met=False),
                             judged("g/nogit")]}
        out = rd.build_readiness(cand_doc, judge)
        items = {i["repo"]: i for i in out["items"]}
        check("build: all seven met is high", items["g/ready"]["level"] == "high" and items["g/ready"]["met_count"] == 7,
              items["g/ready"])
        check("build: six met is medium", items["g/busy"]["level"] == "medium", items["g/busy"])
        check("build: two met is low", items["g/dirty"]["level"] == "low" and items["g/dirty"]["met_count"] == 2,
              items["g/dirty"])
        check("build: items rank by met count", [i["repo"] for i in out["items"]][0] == "g/ready"
              and [i["rank"] for i in out["items"]] == [1, 2, 3, 4], out["items"])
        check("build: the agent record keeps its model and counts what it was given",
              out["agent"]["model"] == "sonnet" and out["agent"]["assigned"] == 4 and out["agent"]["returned"] == 4,
              out["agent"])
        check("build: no gaps when every candidate is judged", out["gaps"] == [], out["gaps"])

        # A missing return and an unusable one (empty evidence) become gaps; exit 1.
        bad = judged("g/busy")
        bad["criteria"]["safe_tests"]["evidence"] = " "
        cpath, jpath, opath = tmp / "cand.json", tmp / "judge.json", tmp / "readiness.json"
        write_json(cpath, cand_doc)
        write_json(jpath, {"agent": {"model": "sonnet"}, "results": [judged("g/ready"), bad, judged("g/nogit")]})
        proc = run("build", "--candidates", str(cpath), "--judge", str(jpath), "--out", str(opath))
        written = json.loads(opath.read_text(encoding="utf-8"))
        check("build: an unjudged candidate exits 1", proc.returncode == 1, proc.stdout)
        check("build: each unjudged candidate is a named gap",
              sorted(g["detail"] for g in written["gaps"]) == ["no usable judgement for g/busy",
                                                              "no usable judgement for g/dirty"], written["gaps"])
        check("build: an unjudged candidate gets no item", sorted(i["repo"] for i in written["items"]) == ["g/nogit", "g/ready"])

        write_json(jpath, {"agent": {"label": "judge-1"}, "results": []})
        proc = run("build", "--candidates", str(cpath), "--judge", str(jpath), "--out", str(opath))
        check("build: a judge record with no model is broken (exit 2)", proc.returncode == 2, proc.stdout)

        proc = run("candidates", "--pulse", str(tmp / "absent.json"), "--out", str(cpath))
        check("candidates: an unreadable pulse.json is broken (exit 2)", proc.returncode == 2, proc.stdout)

        # --- canary: a level rule that ignores the count must fail the level checks.
        original = rd.level_for
        try:
            rd.level_for = lambda met: "high"
            mutated = {i["repo"]: i["level"] for i in rd.build_readiness(cand_doc, judge)["items"]}
            check("canary: with the level rule disabled, a two-met item reads high",
                  mutated["g/dirty"] == "high", mutated)
        finally:
            rd.level_for = original
        check("canary: the restored rule gives low again",
              {i["repo"]: i["level"] for i in rd.build_readiness(cand_doc, judge)["items"]}["g/dirty"] == "low")

    failed = [n for n, ok, _ in results if not ok]
    print()
    print(f"{len(results) - len(failed)}/{len(results)} checks passed.")
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
