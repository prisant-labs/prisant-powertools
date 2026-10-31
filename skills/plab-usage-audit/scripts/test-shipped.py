#!/usr/bin/env python3
"""Tests for shipped.py: the pulse-facts path keeps only repositories with commits or tags in the window
and skips aliases; the sweep path refuses a settings file with no readable root. Exit 0 when every
check passes, 1 otherwise."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
SHIPPED = HERE / "shipped.py"
CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  |  {detail}"))


def run(args):
    return subprocess.run([sys.executable, str(SHIPPED), *args], capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        facts = {
            "window": {"start": "2026-10-24", "end": "2026-10-30", "prior_start": "2026-10-17", "timezone": "UTC"},
            "repos": [
                {"repo": "work/busy", "alias_of": None, "sweep": {"repo": "work/busy", "commits_focus": 5, "commits_prior": 2, "tags_in_window": [{"tag": "v1.0.0", "date": "2026-10-29"}]}},
                {"repo": "work/tagged", "alias_of": None, "sweep": {"repo": "work/tagged", "commits_focus": 0, "commits_prior": 0, "tags_in_window": [{"tag": "v0.2.0", "date": "2026-10-25"}]}},
                {"repo": "work/quiet", "alias_of": None, "sweep": {"repo": "work/quiet", "commits_focus": 0, "commits_prior": 4, "tags_in_window": []}},
                {"repo": "work/link", "alias_of": "work/busy", "sweep": {"repo": "work/link", "commits_focus": 5, "commits_prior": 2, "tags_in_window": []}},
            ],
        }
        fp = tmp / "pulse-facts.json"
        fp.write_text(json.dumps(facts), encoding="utf-8")
        out = tmp / "sweep.json"
        r = run(["--pulse-facts", str(fp), "--out", str(out)])
        data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
        names = sorted(x["repo"] for x in data.get("repos", []))
        check("pulse-facts: exits 0", r.returncode == 0, r.stdout + r.stderr)
        check("pulse-facts: keeps repositories with commits or tags in the window, drops the quiet one and the alias",
              names == ["work/busy", "work/tagged"], names)
        check("pulse-facts: totals add up", data.get("totals") == {"repos_with_activity": 2, "commits_focus": 5, "commits_prior": 2, "tags_in_window": 2}, data.get("totals"))
        check("pulse-facts: a missing file exits 2", run(["--pulse-facts", str(tmp / "absent.json")]).returncode == 2)

        cfg = tmp / "s.local.md"
        cfg.write_text("---\ntimezone: UTC\nsweep:\n  roots: [" + (tmp / "no-such-root").as_posix() + "]\n---\n", encoding="utf-8")
        r2 = run(["--config", str(cfg), "--start", "2026-10-24", "--end", "2026-10-30", "--prior-start", "2026-10-17"])
        check("sweep: no readable root exits 2", r2.returncode == 2, (r2.returncode, r2.stderr))

    passed = sum(1 for _, ok in CHECKS if ok)
    print(f"\n{passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
