#!/usr/bin/env python3
"""
derive-audit-facts.py - the audit facts in one call (Requirement 18, AC-15, AC-16).

Gathers, in one invocation, every fact SKILL.md step 3 needs that the collector does
not already produce on its own: the reconciliation of the prior week against its
earlier ledger row, the week's workflow count/agent count/per-model split and whether
per-workflow costs sum to the workflow lane total, compactions, the installed Claude
Code version against the state file's last version, settings drift against the
owner's change register, which keys are model pins (and only those get their value
printed), credential-file presence and key names (never values), the newest insights
report, the next recommendation-series letter, and the previous bundle folder.

USAGE
-----
  derive-audit-facts.py --config <settings> --data <bundle>/data --ledger <ledger>
      --state <state> --out <file>
          gather every fact and write it as JSON to <file> (and to stdout).

  derive-audit-facts.py --config <settings> --state <state> --commit-state
      --facts <facts file>
          read a previously written facts file and advance the state: the installed
          Claude Code version, the settings key-hash snapshot, the audit date, and the
          recommendation-series letter following the one the facts file used.

EXIT CODES
----------
  0  clean     no finding, no gap
  1  findings  a workflow cost gap over tolerance (AC-16), a reproduce mismatch, or an
               unregistered settings change
  2  broken    --data is missing or unreadable (gather mode only)

NEVER INTERPRET 2 AS CLEAN. See AGENTS.md's exit-code convention.

CREDENTIAL SAFETY (AC-15)
--------------------------
This script is the ONLY thing in the skill that opens a credential file (SKILL.md,
"No agent opens a credential file"), and it opens one for key names and modification
dates only. A credential value is never placed in any data structure this script
builds, is never interpolated into a message, and is never caught by an exception
handler that might otherwise echo a line of file content. If you are reading this
because a review flagged a value leaking through an error path, that is the bug to
fix first.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ledger as ledger_mod  # noqa: E402
import settings as settings_mod  # noqa: E402

SCHEMA_VERSION = 1
DEFAULT_CLAUDE_SETTINGS = "~/.claude/settings.json"
DEFAULT_WORKFLOW_TOLERANCE_USD = 1.0
REPRODUCE_TIMEOUT_S = 300
CLAUDE_VERSION_TIMEOUT_S = 10
LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]

# Requirement/point 6: a model-pin key, matched against the KEY's last dotted segment.
MODEL_PIN_KEY_RE = re.compile(
    r"^(ANTHROPIC_DEFAULT_.*_MODEL|ANTHROPIC_MODEL|CLAUDE_CODE_SUBAGENT_MODEL|model)$"
)
# A value that looks like a model id, safe to print as-is.
MODEL_ID_VALUE_RE = re.compile(r"^claude-[a-z0-9.-]+$|^(opus|sonnet|haiku|fable)(\[1m\])?$")

WITHHELD = "(not a model id, withheld)"

# key = value / key=value, tolerating an `export ` prefix (.env) and a leading `//` npm
# registry segment (.npmrc). A section header line ([section]) is skipped, not parsed.
_KV_RE = re.compile(r"^\s*(?:export\s+)?([^=\s#;][^=]*?)\s*=\s*(.*?)\s*$")
_ENV_REF_RE = re.compile(r"^\$\{.*\}$|^\$[A-Za-z_][A-Za-z0-9_]*$|^env:")
INLINE_PARSED_EXTS = (".toml", ".ini", ".env", ".npmrc")


def expand(path):
    if not path:
        return None
    return os.path.expanduser(str(path))


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mtime_iso(path):
    try:
        return datetime.datetime.fromtimestamp(
            os.path.getmtime(path), tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return None


def load_json(path):
    """Returns (data, error_str). error_str is None on success."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "not found"
    except Exception as e:  # noqa: BLE001 - deliberately generic; never includes file content
        return None, f"unreadable ({type(e).__name__})"


def sha256_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- settings
def claude_settings_flat(settings):
    """Load the Claude Code settings.json named by `claude_settings` (default
    ~/.claude/settings.json) and flatten it to dotted-path -> value. A list is a leaf
    (hashed whole), so reordering one entry does not read as N separate changes."""
    path = expand(settings.raw.get("claude_settings") or DEFAULT_CLAUDE_SETTINGS)
    data, err = load_json(path)
    if err:
        return path, None, err
    flat = {}

    def walk(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(f"{prefix}.{k}" if prefix else str(k), v)
        else:
            flat[prefix] = obj

    walk("", data)
    return path, flat, None


def settings_snapshot(flat):
    return {k: sha256_json(v) for k, v in (flat or {}).items()}


def compute_model_pins(flat):
    """Requirement/point 6: report the key and value only when the value looks like a
    model id; otherwise withhold the value."""
    out = []
    for key, value in sorted((flat or {}).items()):
        last = key.rsplit(".", 1)[-1]
        if not MODEL_PIN_KEY_RE.match(last):
            continue
        if isinstance(value, str) and MODEL_ID_VALUE_RE.match(value):
            out.append({"key": key, "value": value})
        else:
            out.append({"key": key, "value": WITHHELD})
    return out


def _register_mentions(key, register_text, after_date):
    """A row (any line containing a YYYY-MM-DD date) dated strictly after `after_date`
    (ISO string compare) that also mentions the key's last segment or full path."""
    last = key.rsplit(".", 1)[-1]
    for line in register_text.splitlines():
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", line)
        if not dates:
            continue
        row_date = dates[0]  # the row's own date (first column); a later date on the
        # same line is a "review on" date, not when the row was written
        if after_date and row_date <= after_date:
            continue
        if key in line or last in line:
            return True
    return False


def compute_settings_drift(flat_now, prev_snapshot, register_path, last_audit_date, gaps):
    """Returns the settings_drift object. No prior snapshot means this is the baseline
    run: nothing can have drifted yet, so nothing is reported (Requirement 18/19)."""
    if prev_snapshot is None:
        return {"baseline": True, "unregistered": []}

    now_snapshot = settings_snapshot(flat_now)
    added = sorted(set(now_snapshot) - set(prev_snapshot))
    removed = sorted(set(prev_snapshot) - set(now_snapshot))
    changed = sorted(k for k in set(now_snapshot) & set(prev_snapshot) if now_snapshot[k] != prev_snapshot[k])

    changes = ([(k, "added") for k in added] + [(k, "removed") for k in removed] +
               [(k, "changed") for k in changed])
    if not changes:
        return {"baseline": False, "unregistered": []}

    register_text = ""
    if register_path:
        try:
            with open(register_path, encoding="utf-8") as f:
                register_text = f.read()
        except FileNotFoundError:
            gaps.append(f"change_register not found: {register_path}")
        except Exception as e:  # noqa: BLE001
            gaps.append(f"change_register unreadable: {type(e).__name__}")
    else:
        gaps.append("change_register not configured")

    unregistered = [
        {"key": key, "status": status}
        for key, status in changes
        if not _register_mentions(key, register_text, last_audit_date)
    ]
    return {"baseline": False, "unregistered": unregistered}


# ------------------------------------------------------------------------- credentials
def _is_inline(raw_value):
    """True when a value is a non-empty literal, not an environment reference."""
    v = raw_value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    if v == "":
        return False
    if _ENV_REF_RE.match(v):
        return False
    return True


def scan_credential_file(path):
    """Returns {"path", "exists", "mtime", "inline_keys"} and never the value. A key
    name is the text before the first `=`; the value itself is examined only to decide
    whether it looks inline and is discarded immediately after."""
    rec = {"path": path, "exists": False, "mtime": None, "inline_keys": None}
    if not path or not os.path.exists(path):
        rec["inline_keys"] = []
        return rec
    rec["exists"] = True
    rec["mtime"] = mtime_iso(path)

    basename = os.path.basename(path).lower()
    if not any(ext in basename for ext in INLINE_PARSED_EXTS):
        rec["inline_keys"] = None
        rec["format_note"] = "format not parsed"
        return rec

    inline_keys = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith(";"):
                    continue
                if stripped.startswith("["):
                    continue  # a TOML/INI section header, not a key
                m = _KV_RE.match(line.rstrip("\n"))
                if not m:
                    continue
                key = m.group(1).strip()
                if len(key) >= 2 and key[0] == key[-1] and key[0] in "'\"":
                    key = key[1:-1]
                value = m.group(2)
                try:
                    if _is_inline(value):
                        inline_keys.append(key)
                finally:
                    value = None  # never retained past this check
    except Exception:  # noqa: BLE001 - never echoes file content
        rec["inline_keys"] = None
        rec["format_note"] = "unreadable"
        return rec
    rec["inline_keys"] = inline_keys
    return rec


# --------------------------------------------------------------------------- versions
def installed_claude_version():
    binary = os.environ.get("PLAB_CLAUDE_BIN") or shutil.which("claude") or "claude"
    try:
        proc = subprocess.run([binary, "--version"], capture_output=True, text=True,
                               timeout=CLAUDE_VERSION_TIMEOUT_S)
    except FileNotFoundError:
        return None, "claude binary not found"
    except subprocess.TimeoutExpired:
        return None, "claude --version timed out"
    except Exception as e:  # noqa: BLE001
        return None, f"claude --version failed ({type(e).__name__})"
    m = re.search(r"\d+\.\d+\.\d+", (proc.stdout or "") + (proc.stderr or ""))
    if not m:
        return None, "claude --version produced no parseable version"
    return m.group(0), None


# ---------------------------------------------------------------------------- series
def advance_letter(letter):
    idx = (LETTERS.index(letter) + 1) % len(LETTERS)
    return LETTERS[idx]


def skip_adjust(letter, skip_set):
    letter = (letter or "A").upper()
    if letter not in LETTERS:
        letter = "A"
    seen = 0
    while letter in skip_set and seen < len(LETTERS):
        letter = advance_letter(letter)
        seen += 1
    return letter


def resolve_series(state, settings):
    series_settings = settings.raw.get("recommendation_series") or {}
    skip = set((series_settings.get("skip") or [])) if isinstance(series_settings, dict) else set()
    state_series = (state or {}).get("recommendation_series") or {}
    candidate = state_series.get("next") or series_settings.get("next") or "A"
    return skip_adjust(candidate, skip)


# --------------------------------------------------------------------------- ledger / reconciliation
def prior_period(global_json):
    win_start = global_json.get("window", [None, None])[0]
    focus_start = global_json.get("focus_start")
    if not win_start or not focus_start or focus_start <= win_start:
        return None
    prior_end = (datetime.date.fromisoformat(focus_start) - datetime.timedelta(days=1)).isoformat()
    return win_start, prior_end


def run_reproduce(row_id, ledger_path, config_path):
    collect_py = os.path.join(HERE, "collect.py")
    cmd = [sys.executable, "-I", collect_py, "--reproduce", row_id, "--ledger", ledger_path]
    if config_path:
        cmd += ["--config", config_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=REPRODUCE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"reproduced": False, "broken": True, "detail": "collect.py --reproduce timed out"}
    except Exception as e:  # noqa: BLE001
        return {"reproduced": False, "broken": True, "detail": f"collect.py --reproduce failed ({type(e).__name__})"}

    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"recorded total \$([-\d.]+), re-run total \$([-\d.]+), diff \$([-\d.]+)", out)
    entry = {"row_id": row_id, "reproduced": proc.returncode == 0, "exit_code": proc.returncode}
    if m:
        entry["recorded_total_usd"] = float(m.group(1))
        entry["rerun_total_usd"] = float(m.group(2))
        entry["delta_usd"] = float(m.group(3))
    diff_m = re.search(r"difference: (.+)", out)
    entry["differences"] = [diff_m.group(1).strip()] if diff_m else []
    if proc.returncode == 2:
        entry["broken"] = True
        entry["detail"] = out.strip().splitlines()[-1] if out.strip() else "broken"
    return entry


def compute_reconciliation(global_json, ledger_path, mapping_path, config_path, gaps):
    period = prior_period(global_json)
    if period is None:
        return {"found": False, "note": "no prior half in this run's window"}
    prior_start, prior_end = period
    rows = []
    for population in ("interactive", "automated"):
        row = ledger_mod.latest_measurement(ledger_path, prior_start, prior_end, population, mapping_path)
        if row:
            rows.append((population, row))
    if not rows:
        return {"found": False, "prior_period": [prior_start, prior_end],
                "note": "no ledger row exists for the prior week"}

    results = []
    for population, row in rows:
        entry = run_reproduce(row["row_id"], ledger_path, config_path)
        entry["population"] = population
        results.append(entry)
    return {"found": True, "prior_period": [prior_start, prior_end], "rows": results}


# ------------------------------------------------------------------------- workflows
def compute_workflows(data_dir, settings, gaps, findings):
    wf_path = os.path.join(data_dir, "workflow_calls.json")
    global_path = os.path.join(data_dir, "global.json")
    wf_calls, err = load_json(wf_path)
    if err:
        gaps.append(f"workflow_calls.json: {err}")
        wf_calls = []
    global_json, gerr = load_json(global_path)
    if gerr:
        gaps.append(f"global.json: {gerr}")
        global_json = {}

    focus_calls = [w for w in wf_calls if w.get("half") == "focus"]
    model_split = {}
    for w in focus_calls:
        for model, n in (w.get("req_models") or {}).items():
            model_split[model] = model_split.get(model, 0) + n

    workflow_sum = round(sum(w.get("cost", 0.0) for w in focus_calls), 4)
    agent_count = sum(w.get("n_agents_dedup", 0) for w in focus_calls)

    lane_total = 0.0
    halves = global_json.get("halves") or {}
    focus_block = halves.get("focus") or {}
    for population in ("interactive", "automated"):
        lanes = (focus_block.get(population) or {}).get("lanes") or {}
        wf_lane = lanes.get("workflow") or {}
        for bucket_cell in wf_lane.values():
            lane_total += (bucket_cell.get("dedup") or {}).get("cost", 0.0)
    lane_total = round(lane_total, 4)

    tolerance = settings.raw.get("workflow_tolerance_usd")
    tolerance = float(tolerance) if isinstance(tolerance, (int, float)) else DEFAULT_WORKFLOW_TOLERANCE_USD
    gap = round(workflow_sum - lane_total, 4)
    over_tolerance = gap > tolerance

    cost_gap = {"workflow_sum_usd": workflow_sum, "lane_total_usd": lane_total,
                "gap_usd": gap, "tolerance_usd": tolerance, "over_tolerance": over_tolerance}
    if over_tolerance:
        findings.append(f"workflow cost gap ${gap:.2f} exceeds tolerance ${tolerance:.2f}")

    return {"scope": {"half": "focus", "populations": ["interactive", "automated"]},
            "workflow_count": len(focus_calls), "agent_count": agent_count,
            "model_split": model_split, "cost_gap": cost_gap}


def compute_compactions(data_dir, gaps):
    global_json, err = load_json(os.path.join(data_dir, "global.json"))
    if err:
        gaps.append(f"global.json: {err}")
        return {}
    out = {}
    halves = global_json.get("halves") or {}
    for half in ("prior", "focus"):
        out[half] = {}
        for population in ("interactive", "automated"):
            block = (halves.get(half) or {}).get(population) or {}
            waste = block.get("waste") or {}
            out[half][population] = {
                "compactions_dedup": waste.get("compactions_dedup", 0),
                "sessions_compacting_dedup": block.get("sessions_compacting_dedup", 0),
            }
    return out


# ------------------------------------------------------------------------- insights / bundles
def compute_insights_report(claude_settings_path, last_audit_date, gaps):
    base = os.path.dirname(claude_settings_path) if claude_settings_path else None
    if not base:
        gaps.append("insights_report: no claude_settings directory to search")
        return {"found": False}
    pattern = os.path.join(base, "usage-data", "report*.html")
    matches = glob.glob(pattern)
    if not matches:
        return {"found": False}
    newest = max(matches, key=os.path.getmtime)
    mtime = mtime_iso(newest)
    newer = None
    if last_audit_date and mtime:
        newer = mtime[:10] > last_audit_date
    return {"found": True, "path": newest, "mtime": mtime, "newer_than_last_audit": newer}


def compute_previous_bundle(settings, out_file, gaps):
    output_dir = settings.raw.get("output_dir")
    if not output_dir:
        gaps.append("previous_bundle: output_dir not configured")
        return None
    output_dir = expand(output_dir)
    if not os.path.isdir(output_dir):
        gaps.append(f"previous_bundle: output_dir not found: {output_dir}")
        return None
    current_bundle = None
    if out_file:
        data_dir = os.path.dirname(os.path.abspath(out_file))
        current_bundle = os.path.basename(os.path.dirname(data_dir))
    candidates = [d for d in glob.glob(os.path.join(output_dir, "*_claude-usage")) if os.path.isdir(d)]
    candidates = [d for d in candidates if os.path.basename(d) != current_bundle]
    if not candidates:
        return None
    return max(candidates, key=lambda d: os.path.basename(d))


# --------------------------------------------------------------------------------- gather
def gather(args):
    settings = settings_mod.Settings(config_path=args.config)
    gaps = []
    findings = []

    if not args.data or not os.path.isdir(args.data):
        print(f"broken: --data not found or not a directory: {args.data}")
        return 2, None
    global_path = os.path.join(args.data, "global.json")
    global_json, gerr = load_json(global_path)
    if gerr:
        print(f"broken: could not read {global_path}: {gerr}")
        return 2, None

    state, _ = load_json(args.state) if args.state else (None, "no state path given")
    prev_snapshot = (state or {}).get("settings_snapshot")
    last_audit_date = (state or {}).get("last_audit_date")

    claude_settings_path, flat, cs_err = claude_settings_flat(settings)
    if cs_err:
        gaps.append(f"claude_settings: {cs_err} ({claude_settings_path})")
        flat = {}

    mapping_path = expand(settings.raw.get("ledger_mapping"))
    reconciliation = compute_reconciliation(global_json, args.ledger, mapping_path, args.config, gaps)
    for row in reconciliation.get("rows", []):
        if row.get("broken"):
            gaps.append(f"reproduce {row.get('row_id')}: {row.get('detail')}")
        elif not row.get("reproduced"):
            findings.append(f"reproduce {row.get('row_id')} did not agree: {row.get('differences')}")

    workflows = compute_workflows(args.data, settings, gaps, findings)
    compactions = compute_compactions(args.data, gaps)

    claude_version, cv_err = installed_claude_version()
    if cv_err:
        gaps.append(f"claude_version: {cv_err}")
    claude_version_block = {"installed": claude_version,
                             "previous_recorded": (state or {}).get("last_claude_version"),
                             "changed": (claude_version is not None and (state or {}).get("last_claude_version") is not None
                                         and claude_version != (state or {}).get("last_claude_version"))}

    register_path = expand(settings.raw.get("change_register"))
    settings_drift = compute_settings_drift(flat, prev_snapshot, register_path, last_audit_date, gaps)
    if settings_drift.get("unregistered"):
        findings.append(f"{len(settings_drift['unregistered'])} unregistered settings change(s)")

    model_pins = compute_model_pins(flat)

    credentials = []
    for raw_path in (settings.raw.get("credential_files") or []):
        credentials.append(scan_credential_file(expand(raw_path)))

    insights_report = compute_insights_report(claude_settings_path, last_audit_date, gaps)
    next_series_letter = resolve_series(state, settings)
    previous_bundle = compute_previous_bundle(settings, args.out, gaps)

    facts = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "audit_date": global_json.get("window", [None, None])[1],
        "reconciliation": reconciliation,
        "workflows": workflows,
        "compactions": compactions,
        "claude_version": claude_version_block,
        "settings_drift": settings_drift,
        "model_pins": model_pins,
        "credentials": credentials,
        "insights_report": insights_report,
        "next_series_letter": next_series_letter,
        "previous_bundle": previous_bundle,
        "settings_snapshot": settings_snapshot(flat),
        "findings": findings,
        "gaps": gaps,
    }
    exit_code = 1 if findings else 0
    return exit_code, facts


# --------------------------------------------------------------------------------- commit-state
def commit_state(args):
    settings = settings_mod.Settings(config_path=args.config)
    facts, ferr = load_json(args.facts)
    if ferr:
        print(f"broken: could not read facts file {args.facts}: {ferr}")
        return 2, None

    state, _ = load_json(args.state) if args.state and os.path.exists(args.state) else ({}, None)
    state = state or {}

    series_settings = settings.raw.get("recommendation_series") or {}
    skip = set((series_settings.get("skip") or [])) if isinstance(series_settings, dict) else set()
    used = facts.get("next_series_letter") or "A"
    new_next = skip_adjust(advance_letter(used.upper()), skip)

    new_state = dict(state)
    new_state["schema_version"] = 1
    new_state["updated_at"] = now_iso()
    if facts.get("claude_version", {}).get("installed"):
        new_state["last_claude_version"] = facts["claude_version"]["installed"]
    claude_settings_gap = any(str(g).startswith("claude_settings:") for g in (facts.get("gaps") or []))
    if "settings_snapshot" in facts and not claude_settings_gap:
        # A gather run that could not read claude_settings carries an empty/partial
        # snapshot; committing that as the new baseline would read every real key as
        # "added" on the next run. Keep the previous snapshot instead.
        new_state["settings_snapshot"] = facts["settings_snapshot"]
    if facts.get("audit_date"):
        new_state["last_audit_date"] = facts["audit_date"]
    new_state["recommendation_series"] = {"next": new_next}

    write_json_atomic(args.state, new_state)
    return 0, new_state


def write_json_atomic(path, data):
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".audit-state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------------- CLI
def build_arg_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=None, help="the plab-usage-audit settings file")
    ap.add_argument("--data", default=None, help="the collector's --out directory")
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--state", default=None)
    ap.add_argument("--out", default=None, help="write the gathered facts JSON here")
    ap.add_argument("--commit-state", action="store_true")
    ap.add_argument("--facts", default=None, help="the facts file --commit-state reads")
    return ap


def main():
    ap = build_arg_parser()
    args = ap.parse_args()

    if args.commit_state:
        if not args.facts or not args.state:
            print("broken: --commit-state needs --facts and --state")
            return 2
        exit_code, result = commit_state(args)
        if result is not None:
            print(json.dumps(result, indent=2, sort_keys=True))
        return exit_code

    exit_code, facts = gather(args)
    if facts is None:
        return exit_code
    text = json.dumps(facts, indent=2, sort_keys=True)
    print(text)
    if args.out:
        directory = os.path.dirname(os.path.abspath(args.out))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
