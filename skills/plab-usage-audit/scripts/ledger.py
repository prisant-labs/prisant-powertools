#!/usr/bin/env python3
"""
plab-usage-audit ledger: schema 2 rows, one JSON line per row, never rewritten.

Two row kinds:

  "measurement" (the default) - one row per period and population, recording
  what a collector run measured and the full method it used to measure it.
  A new row whose period, population and method all match an existing row is
  refused: ledger.py exits 1 and writes nothing. A row with a different
  method (a different cutoff, a different exclusion list, a different price
  file, a newer collector version) is a re-measure and is appended alongside
  the old one; `latest` returns the row with the newest measured_at for a
  given period and population.

  "audit_run" - one row per weekly run of the skill itself, recording what
  the run cost: its own agents, models, tokens, dollars when known, and
  minutes. audit_run rows are never deduplicated against each other or
  against measurement rows: a repeated run of the same week is expected.

See references/ledger-schema.md for the full field list and the mapping-
file format that lets a ledger of pre-schema-2 rows (no period_start or
period_end) be read as schema 2 without being rewritten.

CLI:
  ledger.py append --ledger <path> --row-json <path-or-dash>
      exits 0 on success, 1 on a refused duplicate measurement row, 2 broken.
  ledger.py latest --ledger <path> --period-start <d> --period-end <d>
      --population <p> [--mapping <path>]
      prints the newest matching measurement row as JSON; exits 0 if found,
      1 if no row matches, 2 broken.
  ledger.py show --ledger <path> --row-id <id>
      prints the row with that row_id; exits 0 if found, 1 if not, 2 broken.
"""
import argparse
import hashlib
import json
import os
import sys
import datetime

SCHEMA_VERSION = 2
ROW_KINDS = ("measurement", "audit_run")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_method_json(method):
    return json.dumps(method or {}, sort_keys=True, separators=(",", ":"))


def compute_row_id(period_start, period_end, population, method, row_kind="measurement", salt=None):
    """A deterministic short id. For a measurement row, the id is a hash of the
    quadruple that defines its duplicate-check identity, so two independent
    appends of the same method produce the same id and the duplicate check can
    be a simple membership test. audit_run rows take `salt` (the run's own
    measured_at) because repeated runs of one week are expected and must not
    collide."""
    parts = [row_kind, period_start or "", period_end or "", population or "", canonical_method_json(method)]
    if salt:
        parts.append(salt)
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return "R" + h[:16]


def read_rows(path):
    """Read every parseable JSON line. A line that is not valid JSON is skipped,
    not fatal: an old ledger file may carry a line written by a different tool."""
    rows = []
    if not path or not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def _row_kind(row):
    return row.get("row_kind") or "measurement"  # rows from before row_kind existed are measurement rows


def is_duplicate_measurement(path, period_start, period_end, population, method):
    """True if a measurement row with this exact period, population and method
    already exists in the ledger at `path`."""
    target = (period_start, period_end, population, canonical_method_json(method))
    for row in read_rows(path):
        if _row_kind(row) != "measurement":
            continue
        existing = (row.get("period_start"), row.get("period_end"), row.get("population"),
                    canonical_method_json(row.get("method")))
        if existing == target:
            return True
    return False


def append(path, row):
    """Append one row, applying the duplicate refusal for measurement rows.
    Returns (ok, reason). On ok, `row` has row_id, row_kind, measured_at and
    schema_version filled in if they were missing; the caller's dict is not
    mutated, a copy is returned via the third element when ok."""
    row = dict(row)
    row.setdefault("schema_version", SCHEMA_VERSION)
    kind = row.setdefault("row_kind", "measurement")
    if kind not in ROW_KINDS:
        return False, f"unknown row_kind: {kind}", None
    row.setdefault("measured_at", now_iso())
    if kind == "measurement":
        period_start, period_end = row.get("period_start"), row.get("period_end")
        population, method = row.get("population"), row.get("method")
        if not period_start or not period_end or not population:
            return False, "a measurement row needs period_start, period_end and population", None
        if is_duplicate_measurement(path, period_start, period_end, population, method):
            return False, (f"a measurement row already exists for {period_start}..{period_end} "
                            f"/ {population} with this exact method"), None
        row.setdefault("row_id", compute_row_id(period_start, period_end, population, method, "measurement"))
    else:
        row.setdefault("row_id", compute_row_id(row.get("period_start"), row.get("period_end"), None,
                                                  row.get("run"), "audit_run", salt=row["measured_at"]))
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    return True, None, row


def load_mapping(path):
    """The mapping file for Requirement 14: a JSON object whose keys are the
    string form of {"window_start","window_end","half","population"} from a
    pre-schema-2 row (json.dumps, sort_keys=True) and whose values are
    {"period_start": ..., "period_end": ...}. See references/ledger-schema.md."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def legacy_key(row):
    return json.dumps({"window_start": row.get("window_start"), "window_end": row.get("window_end"),
                        "half": row.get("half"), "population": row.get("population")}, sort_keys=True)


def with_mapping(row, mapping):
    """Return a copy of `row` with period_start/period_end filled in from the
    mapping when the row is missing them and the mapping names them. The
    stored row on disk is never touched."""
    if row.get("period_start") and row.get("period_end"):
        return row
    entry = mapping.get(legacy_key(row))
    if not entry:
        return row
    out = dict(row)
    out["period_start"] = entry.get("period_start")
    out["period_end"] = entry.get("period_end")
    return out


def latest_measurement(path, period_start, period_end, population, mapping_path=None):
    mapping = load_mapping(mapping_path)
    best = None
    for row in read_rows(path):
        if _row_kind(row) != "measurement":
            continue
        filled = with_mapping(row, mapping)
        if filled.get("period_start") == period_start and filled.get("period_end") == period_end \
                and filled.get("population") == population:
            if best is None or (filled.get("measured_at") or "") > (best.get("measured_at") or ""):
                best = filled
    return best


def find_row(path, row_id):
    for row in read_rows(path):
        if row.get("row_id") == row_id:
            return row
    return None


def build_run_row(audit_day, agents, period_start=None, minutes=None, dollars=None,
                  plan_session=None, plan_weekly=None, plan_read_at=None):
    """The audit_run row SKILL.md step 9 appends: the run's own agents, models, tokens and minutes,
    and the owner's plan-limit reading when one was given (UA-01 Requirements 16 and 17)."""
    import datetime as _dt
    end = _dt.date.fromisoformat(audit_day)
    start = _dt.date.fromisoformat(period_start) if period_start else end - _dt.timedelta(days=6)
    models = {}
    tokens = 0
    for a in agents:
        m = a.get("model") or "unnamed"
        models[m] = models.get(m, 0) + 1
        tokens += int(a.get("tokens") or 0)
    if minutes is None:
        mins = [a.get("minutes") for a in agents if isinstance(a.get("minutes"), (int, float))]
        minutes = round(sum(mins), 1) if mins else None
    plan = None
    if plan_session is not None or plan_weekly is not None:
        plan = {"session_pct": plan_session, "weekly_pct": plan_weekly, "read_at": plan_read_at}
    return {
        "row_kind": "audit_run",
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "run": {"agents": len(agents), "models": models, "tokens": tokens or None,
                "dollars": dollars, "minutes": minutes, "agent_list": agents},
        "plan_limit": plan,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_append = sub.add_parser("append")
    p_append.add_argument("--ledger", required=True)
    p_append.add_argument("--row-json", required=True, help="path to a JSON file holding the row, or - for stdin")

    p_run = sub.add_parser("append-run", help="append the audit_run row for one weekly run")
    p_run.add_argument("--ledger", required=True)
    p_run.add_argument("--date", required=True, help="the audit day, YYYY-MM-DD")
    p_run.add_argument("--period-start", default=None, help="defaults to six days before --date")
    p_run.add_argument("--agents", required=True, help="agents.json: a list of {stage, label, model, assigned, returned, escalated, tokens, minutes}")
    p_run.add_argument("--minutes", type=float, default=None)
    p_run.add_argument("--dollars", type=float, default=None)
    p_run.add_argument("--plan-session", type=float, default=None)
    p_run.add_argument("--plan-weekly", type=float, default=None)
    p_run.add_argument("--plan-read-at", default=None)

    p_latest = sub.add_parser("latest")
    p_latest.add_argument("--ledger", required=True)
    p_latest.add_argument("--period-start", required=True)
    p_latest.add_argument("--period-end", required=True)
    p_latest.add_argument("--population", required=True)
    p_latest.add_argument("--mapping", default=None)

    p_show = sub.add_parser("show")
    p_show.add_argument("--ledger", required=True)
    p_show.add_argument("--row-id", required=True)

    args = ap.parse_args()

    if args.cmd == "append":
        text = sys.stdin.read() if args.row_json == "-" else open(args.row_json, encoding="utf-8").read()
        try:
            row = json.loads(text)
        except Exception as e:
            print(f"broken: could not parse row JSON: {e}")
            return 2
        ok, reason, written = append(args.ledger, row)
        if not ok:
            print(f"refused: {reason}")
            return 1
        print(json.dumps(written))
        return 0

    if args.cmd == "append-run":
        try:
            agents = json.loads(open(args.agents, encoding="utf-8").read())
        except Exception as e:
            print(f"broken: could not read agents file: {e}")
            return 2
        if not isinstance(agents, list) or any(not isinstance(a, dict) for a in agents):
            print("broken: the agents file must be a JSON list of objects")
            return 2
        unnamed = [a.get("label") or "?" for a in agents if not a.get("model")]
        row = build_run_row(args.date, agents, args.period_start, args.minutes, args.dollars,
                            args.plan_session, args.plan_weekly, args.plan_read_at)
        ok, reason, written = append(args.ledger, row)
        if not ok:
            print(f"refused: {reason}")
            return 1
        print(json.dumps(written))
        if unnamed:
            print("finding: agents with no model named: " + ", ".join(unnamed))
            return 1
        return 0

    if args.cmd == "latest":
        row = latest_measurement(args.ledger, args.period_start, args.period_end, args.population, args.mapping)
        if row is None:
            print("no matching row")
            return 1
        print(json.dumps(row))
        return 0

    if args.cmd == "show":
        row = find_row(args.ledger, args.row_id)
        if row is None:
            print("no such row_id")
            return 1
        print(json.dumps(row))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
