#!/usr/bin/env python3
"""List the session logs plab-continue-session should offer (W-07).

Usage: python list-candidates.py <project_root> [--json]

Builds continue's candidate set with the rules in the plugin's shared
lib/session-logs.py, which plab-wrap-session loads too, so the two skills
cannot disagree about which handoff is still open. A candidate is a log from
the last 7 days that no newer log took up, one per session. The rules are
explained once, in that module's docstring.

Modes:
  one       exactly one candidate: resume from it, as continue always has.
  choose    several candidates: list them newest first and ask which to resume.
            `default` names the one candidate on the current branch, if exactly
            one is; it is a marker, never a silent pick.
  fallback  logs exist but none is in the window: resume from the newest log
            and show the existing age warning. `newest` carries its age.
  none      no log anywhere: continue's "no prior session log" path.

In a linked git worktree the store is the main checkout's, because that is
where every session's log lives (spec D3).

Reads only. Exit 0 on any of the four modes; exit 2 when the project root is
not a directory or lib/session-logs.py is missing, which is an install defect.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SESSION_LOGS_PATH = SCRIPT_DIR.parents[2] / "lib" / "session-logs.py"


def _load_session_logs():
    if not SESSION_LOGS_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("plab_session_logs", SESSION_LOGS_PATH)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SL = _load_session_logs()


def current_branch(project_root: Path) -> str | None:
    rc, out = SL.run_git(["branch", "--show-current"], project_root)
    return (out or None) if rc == 0 else None


def build(project_root: Path, now: dt.datetime | None = None) -> dict:
    now = now or dt.datetime.now(dt.timezone.utc)
    store, how = SL.store_root(project_root)
    infos = [SL.describe(p) for p in SL.pool_logs(store, project_root)]
    branch = current_branch(project_root)
    out = {"store": {"path": str(store), "how": how}, "branch": branch,
           "candidates": [], "default": None, "newest": None}
    if not infos:
        out["mode"] = "none"
        return out
    newest = infos[0]
    try:
        age = (now.astimezone().date() - dt.date.fromisoformat(newest["name"][:10])).days
    except ValueError:
        age = None
    out["newest"] = {"name": newest["name"], "path": str(newest["path"]), "age-days": age}
    cands = SL.candidates(infos, now)
    out["candidates"] = cands
    if not cands:
        out["mode"] = "fallback"
    elif len(cands) == 1:
        out["mode"] = "one"
    else:
        out["mode"] = "choose"
        on_branch = [c for c in cands if branch and c["branch"] == branch]
        if len(on_branch) == 1:
            out["default"] = on_branch[0]["name"]
    return out


def _local(iso: str | None) -> str | None:
    if not iso:
        return None
    parsed = SL.parse_utc(iso)
    return parsed.astimezone().strftime("%a %Y-%m-%d %H:%M") if parsed else None


def render(data: dict) -> str:
    lines = [f"store: {data['store']['path']} ({data['store']['how']})",
             f"current branch: {data['branch'] or '(detached or unknown)'}",
             f"mode: {data['mode']}"]
    mode = data["mode"]
    if mode == "none":
        lines.append("No session log found.")
        return "\n".join(lines)
    if mode == "fallback":
        n = data["newest"]
        lines.append(f"No log from the last 7 days is waiting. Newest log: {n['name']} ({n['age-days']} days old).")
        lines.append(f"  path: {n['path']}")
        return "\n".join(lines)
    cands = data["candidates"]
    if mode == "one":
        c = cands[0]
        lines.append(f"Resume from: {c['name']}")
        lines.append(f"  path: {c['path']}")
        return "\n".join(lines)
    lines.append(f"{len(cands)} sessions have unconsumed logs from the last 7 days:")
    lines.append("")
    for i, c in enumerate(cands, 1):
        start, end = _local(c["session-start"]), _local(c["wrapped"])
        span = f"session {start} to {end}" if start else f"wrapped {end}, start unknown"
        marker = "  [default: on the current branch]" if c["name"] == data["default"] else ""
        lines.append(f"  {i}. {c['name']}  {c['branch'] or '?'}  ({span}, {c['waiting']} waiting){marker}")
        lines.append(f"     path: {c['path']}")
    lines.append("")
    lines.append("Which session should I resume?")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="List the session logs plab-continue-session should offer.")
    parser.add_argument("project_root", nargs="?", default=".", help="the project to resume in")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)
    if SL is None:
        print(f"error: the shared session-log rules are missing: {SESSION_LOGS_PATH}", file=sys.stderr)
        return 2
    project_root = Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"error: {project_root} is not a directory", file=sys.stderr)
        return 2
    data = build(project_root)
    print(json.dumps(data, indent=2) if args.json else render(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
