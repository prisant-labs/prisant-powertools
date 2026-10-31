#!/usr/bin/env python3
"""What shipped in the window, for the usage audit's 02-shipped.md (UA-01 scope item 6).

Discovers the repositories under the settings file's `sweep.roots` and runs the PP-01 contract C2 git
sweep on each, using copies of plab-project-pulse's `discover.py` and `sweep.py` that ship beside this
script. With `--pulse-facts`, it reuses the sweep records a pulse run already wrote for the same window
and runs no git command at all.

  shipped.py --config <settings> --start <focus start> --end <audit day> --prior-start <prior start> [--out FILE]
  shipped.py --pulse-facts <pulse-facts.json> [--out FILE]

Output: {"schema_version": 1, "source": "sweep" | "pulse-facts", "window": {...}, "repos": [C2 records with
commits or tags in the window], "totals": {...}, "gaps": [...]}. Exit 0 clean, 1 when any repository could
not be swept (each named in gaps), 2 when no root is readable or the input file is missing.
"""
import argparse
import concurrent.futures
import importlib.util
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def shipped_only(records):
    return [r for r in records if r and (r.get("commits_focus") or r.get("tags_in_window"))]


def totals(records):
    return {
        "repos_with_activity": len(records),
        "commits_focus": sum(r.get("commits_focus") or 0 for r in records),
        "commits_prior": sum(r.get("commits_prior") or 0 for r in records),
        "tags_in_window": sum(len(r.get("tags_in_window") or []) for r in records),
    }


def from_pulse(path):
    facts = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    records = [r.get("sweep") for r in facts.get("repos", []) if not r.get("alias_of")]
    active = shipped_only(records)
    return {"schema_version": 1, "source": "pulse-facts", "window": facts.get("window"),
            "repos": active, "totals": totals(active), "gaps": []}


def from_sweep(args):
    settings = _load("settings").Settings(config_path=args.config, cli={})
    sweep_cfg = settings.raw.get("sweep") or {}
    roots = [os.path.expanduser(r) for r in (sweep_cfg.get("roots") or [])]
    roots = [r for r in roots if os.path.isdir(r)]
    if not roots:
        print("BROKEN: no readable root under sweep.roots in the settings file", file=sys.stderr)
        return None, 2
    tz = settings.timezone or "UTC"
    author = sweep_cfg.get("author_pattern") or ".*"
    max_depth = int(sweep_cfg.get("max_depth") or 2)
    discover, sweep = _load("discover"), _load("sweep")
    found = discover.run(roots, max_depth)
    alias_paths = {a.get("path") for a in found.get("aliases", [])}
    repos = [r for r in found["repos"] if r.get("path") not in alias_paths]
    gaps, records = [], []

    def one(r):
        return sweep.sweep_repo(r["path"], args.start, args.end, args.prior_start, tz, author,
                                repo_name=r.get("rel"), folder=r.get("folder"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(one, r): r for r in repos}
        for fut in concurrent.futures.as_completed(futures):
            try:
                records.append(fut.result())
            except Exception as exc:  # one broken repository is a gap, not a failed run
                gaps.append({"source": "sweep", "detail": f"{futures[fut].get('rel')}: {exc}"})
    active = sorted(shipped_only(records), key=lambda r: (-(r.get("commits_focus") or 0), r.get("repo") or ""))
    out = {"schema_version": 1, "source": "sweep",
           "window": {"start": args.start, "end": args.end, "prior_start": args.prior_start, "timezone": tz},
           "repos_swept": len(repos), "repos": active, "totals": totals(active), "gaps": gaps}
    return out, (1 if gaps else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--config")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--prior-start", dest="prior_start")
    ap.add_argument("--pulse-facts", dest="pulse_facts")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.pulse_facts:
        if not os.path.isfile(args.pulse_facts):
            print(f"BROKEN: {args.pulse_facts} not found", file=sys.stderr)
            return 2
        out, code = from_pulse(args.pulse_facts), 0
    else:
        if not (args.config and args.start and args.end and args.prior_start):
            ap.error("--config, --start, --end and --prior-start are required without --pulse-facts")
        out, code = from_sweep(args)
        if out is None:
            return code
    text = json.dumps(out, indent=1)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
