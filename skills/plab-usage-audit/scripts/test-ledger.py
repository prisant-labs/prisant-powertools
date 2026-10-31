#!/usr/bin/env python3
"""
Tests for ledger.py. Stdlib only, plain asserts collected into a pass/fail
tally so one failure does not hide the rest. Run as `python test-ledger.py`;
exits 0 when every check passes, 1 when any check fails.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ledger  # noqa: E402

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    mark = "OK" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" ({detail})" if detail and not cond else ""))


def method(cutoff="2026-10-30T16:00:00Z", excluded=None, price_as_of="2026-10-06", version="1.0.0"):
    return {"cutoff": cutoff, "excluded_sessions": sorted(excluded or []),
            "price_file_as_of": price_as_of, "collector_version": version}


def measurement_row(period_start="2026-10-24", period_end="2026-10-30", population="interactive", m=None):
    return {"period_start": period_start, "period_end": period_end, "population": population,
            "method": m or method(), "volume": {"sessions_dedup": 3}}


def main():
    tmp = tempfile.mkdtemp(prefix="ua-ledger-test-")
    try:
        ledger_path = os.path.join(tmp, "ledger.jsonl")

        # ---- append writes schema fields.
        ok, reason, row = ledger.append(ledger_path, measurement_row())
        check("append: first row succeeds", ok, reason)
        check("append: schema_version == 2", row.get("schema_version") == 2, row)
        check("append: row_kind defaults to measurement", row.get("row_kind") == "measurement", row)
        check("append: row_id is set", bool(row.get("row_id")), row)
        check("append: measured_at is set", bool(row.get("measured_at")), row)
        rows_on_disk = ledger.read_rows(ledger_path)
        check("append: exactly one row on disk", len(rows_on_disk) == 1, len(rows_on_disk))

        # ---- duplicate refusal: identical period, population and method.
        ok2, reason2, row2 = ledger.append(ledger_path, measurement_row())
        check("append: identical period/population/method is refused", ok2 is False, (ok2, reason2))
        check("append: refusal names the duplicate", reason2 is not None and "already exists" in reason2, reason2)
        rows_after = ledger.read_rows(ledger_path)
        check("append: refused row writes nothing (still 1 row)", len(rows_after) == 1, len(rows_after))

        # ---- a re-measure with a different method succeeds and both rows are kept.
        ok3, reason3, row3 = ledger.append(ledger_path, measurement_row(m=method(cutoff="2026-10-30T09:00:00Z")))
        check("append: a different method is not a duplicate", ok3, reason3)
        rows_after3 = ledger.read_rows(ledger_path)
        check("append: re-measure appends a second row (2 total)", len(rows_after3) == 2, len(rows_after3))
        check("append: the two rows have different row_id", rows_after3[0]["row_id"] != rows_after3[1]["row_id"],
              [r["row_id"] for r in rows_after3])

        # ---- row_id is deterministic: the same inputs hash the same way.
        id_a = ledger.compute_row_id("2026-10-24", "2026-10-30", "interactive", method())
        id_b = ledger.compute_row_id("2026-10-24", "2026-10-30", "interactive", method())
        check("compute_row_id: deterministic for identical inputs", id_a == id_b, (id_a, id_b))
        id_c = ledger.compute_row_id("2026-10-24", "2026-10-30", "automated", method())
        check("compute_row_id: differs when population differs", id_a != id_c, (id_a, id_c))

        # ---- latest returns the newer measured_at among rows for the same period/population.
        ledger_path2 = os.path.join(tmp, "ledger2.jsonl")
        _, _, older = ledger.append(ledger_path2, measurement_row(m=method(cutoff="2026-10-30T09:00:00Z")))
        older["measured_at"] = "2026-10-30T10:00:00Z"
        _, _, newer = ledger.append(ledger_path2, measurement_row(m=method(cutoff="2026-10-30T16:00:00Z")))
        newer["measured_at"] = "2026-10-31T10:00:00Z"
        # rewrite the file with the edited measured_at values (append() already set its own; this test
        # wants to control ordering explicitly rather than relying on wall-clock timing).
        with open(ledger_path2, "w", encoding="utf-8") as f:
            f.write(json.dumps(older) + "\n")
            f.write(json.dumps(newer) + "\n")
        best = ledger.latest_measurement(ledger_path2, "2026-10-24", "2026-10-30", "interactive")
        check("latest: returns the row with the newer measured_at", best is not None and best["row_id"] == newer["row_id"],
              best)

        # ---- mapping file: a pre-schema-2 row with no period fields reads with them filled in.
        legacy_row = {"schema_version": 1, "window_start": "2026-10-17", "window_end": "2026-10-30",
                      "half": "focus", "population": "interactive", "method": method()}
        ledger_path3 = os.path.join(tmp, "legacy.jsonl")
        with open(ledger_path3, "w", encoding="utf-8") as f:
            f.write(json.dumps(legacy_row) + "\n")
        mapping_path = os.path.join(tmp, "mapping.json")
        mapping = {ledger.legacy_key(legacy_row): {"period_start": "2026-10-24", "period_end": "2026-10-30"}}
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(mapping, f)
        found = ledger.latest_measurement(ledger_path3, "2026-10-24", "2026-10-30", "interactive", mapping_path)
        check("mapping: legacy row resolves once mapped", found is not None, found)
        if found:
            check("mapping: period_start filled in", found.get("period_start") == "2026-10-24", found)
        without_mapping = ledger.latest_measurement(ledger_path3, "2026-10-24", "2026-10-30", "interactive")
        check("mapping: without the mapping file the legacy row does not resolve", without_mapping is None,
              without_mapping)

        # ---- audit_run rows are never deduplicated, even with identical fields.
        ledger_path4 = os.path.join(tmp, "runs.jsonl")
        run_row = {"row_kind": "audit_run", "period_start": "2026-10-24", "period_end": "2026-10-30",
                   "run": {"agents": 8, "models": {"claude-sonnet-5": 6}, "tokens": 1210000, "dollars": 4.5,
                           "minutes": 10.2}}
        ok_r1, _, _ = ledger.append(ledger_path4, run_row)
        ok_r2, _, _ = ledger.append(ledger_path4, run_row)
        check("audit_run: repeated identical rows both succeed", ok_r1 and ok_r2, (ok_r1, ok_r2))
        check("audit_run: both rows are written", len(ledger.read_rows(ledger_path4)) == 2,
              len(ledger.read_rows(ledger_path4)))

        # ---- show finds a row by row_id.
        shown = ledger.find_row(ledger_path, rows_after3[0]["row_id"])
        check("show/find_row: finds the written row", shown is not None, shown)

        # ---- a measurement row with no period_start is rejected, not silently accepted.
        bad = {"population": "interactive", "method": method()}
        ok_bad, reason_bad, _ = ledger.append(os.path.join(tmp, "bad.jsonl"), bad)
        check("append: a measurement row missing period_start is rejected", ok_bad is False, reason_bad)

        # ---- append-run, the CLI SKILL.md step 9 calls: agents, models, tokens and the plan-limit reading.
        agents_path = os.path.join(tmp, "agents.json")
        with open(agents_path, "w", encoding="utf-8") as f:
            json.dump([{"stage": "brief", "label": "usage", "model": "sonnet", "tokens": 1000, "minutes": 3},
                       {"stage": "verify", "label": "verifier", "model": "sonnet", "tokens": 500, "minutes": 2}], f)
        run_ledger = os.path.join(tmp, "append-run-cli.jsonl")
        cli = [sys.executable, os.path.join(HERE, "ledger.py"), "append-run", "--ledger", run_ledger,
               "--date", "2026-11-06", "--agents", agents_path, "--plan-session", "41", "--plan-weekly", "63",
               "--plan-read-at", "2026-11-06T16:05:00Z"]
        r = subprocess.run(cli, capture_output=True, text=True)
        rows_run = ledger.read_rows(run_ledger)
        written_run = rows_run[0] if rows_run else {}
        check("append-run: exits 0 and writes one audit_run row", r.returncode == 0 and len(rows_run) == 1
              and written_run.get("row_kind") == "audit_run", (r.returncode, r.stdout, r.stderr))
        check("append-run: the period is the seven days ending on --date",
              written_run.get("period_start") == "2026-10-31" and written_run.get("period_end") == "2026-11-06", written_run)
        check("append-run: agents, models, tokens and minutes are summed",
              written_run.get("run", {}).get("agents") == 2 and written_run["run"].get("models") == {"sonnet": 2}
              and written_run["run"].get("tokens") == 1500 and written_run["run"].get("minutes") == 5, written_run.get("run"))
        check("append-run: the plan-limit reading is kept",
              written_run.get("plan_limit") == {"session_pct": 41.0, "weekly_pct": 63.0, "read_at": "2026-11-06T16:05:00Z"},
              written_run.get("plan_limit"))
        with open(agents_path, "w", encoding="utf-8") as f:
            json.dump([{"stage": "brief", "label": "nameless"}], f)
        r2 = subprocess.run(cli[:-6], capture_output=True, text=True)
        check("append-run: an agent with no model is a finding, exit 1", r2.returncode == 1 and "nameless" in r2.stdout,
              (r2.returncode, r2.stdout))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n{passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
