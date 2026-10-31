#!/usr/bin/env python3
"""
Tests for derive-audit-facts.py. Every fixture is synthetic and built in a temp
directory at test time: no real home paths, no real credential files. `claude` is
stubbed with a fake script placed on PATH (via PLAB_CLAUDE_BIN), never the real binary.

Exits 0 when every check passes, 1 when any check fails.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "derive-audit-facts.py")

sys.path.insert(0, HERE)
import ledger as ledger_mod  # noqa: E402

spec = importlib.util.spec_from_file_location("derive_audit_facts", TOOL)
daf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(daf)

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    mark = "OK" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" ({detail})" if detail and not cond else ""))


def run_tool(args, env=None, tool=TOOL):
    cmd = [sys.executable, "-I", tool] + args
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=full_env)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def write_json(path, data):
    write(path, json.dumps(data))


def make_settings_file(path, **overrides):
    # An empty string parses as YAML null, which falls back to the real
    # ~/.claude/settings.json (settings.py's _resolve default chain). Default to a
    # sibling path that does not exist instead, so a test that forgets to override
    # claude_settings fails loudly (claude_settings: not found) rather than silently
    # reading the operator's real settings file.
    default_claude_settings = os.path.join(os.path.dirname(path), "unset-claude-settings.json")
    body = {
        "claude_settings": overrides.get("claude_settings", default_claude_settings),
        "credential_files": overrides.get("credential_files", []),
        "change_register": overrides.get("change_register", ""),
        "workflow_tolerance_usd": overrides.get("workflow_tolerance_usd", 1.0),
        "output_dir": overrides.get("output_dir", ""),
        "transcript_root": overrides.get("transcript_root", ""),
        "timezone": overrides.get("timezone", "America/New_York"),
        "recommendation_series": overrides.get("recommendation_series", {"next": "A", "skip": []}),
    }
    lines = ["---"]
    for k, v in body.items():
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for sk, sv in v.items():
                if isinstance(sv, list):
                    lines.append(f"  {sk}: [{', '.join(str(x) for x in sv)}]")
                else:
                    lines.append(f"  {sk}: {sv}")
        elif isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v!r}" if "'" not in str(v) else f'{k}: "{v}"')
    lines.append("---")
    write(path, "\n".join(lines) + "\n")


def minimal_global_json(win_start="2026-01-08", focus_start="2026-01-08", win_end="2026-01-14",
                         workflow_lane_cost=0.0, compactions=0):
    return {
        "window": [win_start, win_end],
        "focus_start": focus_start,
        "halves": {
            "prior": {
                "interactive": {"lanes": {}, "waste": {"compactions_dedup": 0}, "sessions_compacting_dedup": 0},
                "automated": {"lanes": {}, "waste": {"compactions_dedup": 0}, "sessions_compacting_dedup": 0},
            },
            "focus": {
                "interactive": {
                    "lanes": {"workflow": {"sonnet": {"dedup": {"cost": workflow_lane_cost}}}},
                    "waste": {"compactions_dedup": compactions}, "sessions_compacting_dedup": 1 if compactions else 0,
                },
                "automated": {"lanes": {}, "waste": {"compactions_dedup": 0}, "sessions_compacting_dedup": 0},
            },
        },
    }


def make_fake_claude(dir_path, version="2.1.300"):
    path = os.path.join(dir_path, "fake-claude.py")
    write(path, f'#!/usr/bin/env python3\nprint("{version} (Claude Code)")\n')
    return [sys.executable, path]


def make_mutated_copy():
    """A copy of derive-audit-facts.py with one deliberate leak: scan_credential_file
    keeps the raw value instead of discarding it. Lives beside the real script (so its
    `sys.path.insert(0, HERE)` still finds ledger.py/settings.py) and is deleted by the
    caller. This is the canary: AC-15's own subprocess checks, run against this copy,
    must fail."""
    with open(TOOL, encoding="utf-8") as f:
        text = f.read()
    marker = "                try:\n                    if _is_inline(value):\n                        inline_keys.append(key)\n                finally:\n                    value = None  # never retained past this check"
    mutated_marker = ("                if _is_inline(value):\n"
                       "                    inline_keys.append(key + '=' + value)  # CANARY: deliberately leaks the value")
    if marker not in text:
        raise AssertionError("canary: the credential-parsing block to mutate was not found; "
                              "derive-audit-facts.py's scan_credential_file must have changed shape")
    mutated = text.replace(marker, mutated_marker)
    copy_path = os.path.join(HERE, "_canary-derive-audit-facts.py")
    write(copy_path, mutated)
    return copy_path


# ----------------------------------------------------------------------------- tests
def test_ac15_no_value_leak():
    with tempfile.TemporaryDirectory() as tmp:
        secret_npmrc = "ghp_FAKEVALUE123"
        secret_bare_npmrc = "npmtok_FAKEVALUE456"
        secret_env = "sk_FAKEVALUE789"

        npmrc_with_stem = os.path.join(tmp, "fake.npmrc")
        write(npmrc_with_stem, f"//registry.npmjs.org/:_authToken={secret_npmrc}\nother_key = plain\n")

        bare_npmrc_dir = os.path.join(tmp, "bare-npmrc")
        bare_npmrc = os.path.join(bare_npmrc_dir, ".npmrc")
        write(bare_npmrc, f"registry_token={secret_bare_npmrc}\n")

        bare_env_dir = os.path.join(tmp, "bare-env")
        bare_env = os.path.join(bare_env_dir, ".env")
        write(bare_env, f"export API_SECRET={secret_env}\nREF_KEY=${{SOME_ENV_VAR}}\n")

        cred_paths = [npmrc_with_stem, bare_npmrc, bare_env]
        secrets = [secret_npmrc, secret_bare_npmrc, secret_env]

        data_dir = os.path.join(tmp, "data")
        write_json(os.path.join(data_dir, "global.json"), minimal_global_json())
        write_json(os.path.join(data_dir, "workflow_calls.json"), [])

        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, credential_files=cred_paths,
                            claude_settings=os.path.join(tmp, "claude-settings.json"))
        write_json(os.path.join(tmp, "claude-settings.json"), {"model": "opus"})

        out_path = os.path.join(tmp, "facts.json")
        ledger_path = os.path.join(tmp, "ledger.jsonl")
        state_path = os.path.join(tmp, "state.json")

        proc = run_tool(["--config", settings_path, "--data", data_dir, "--ledger", ledger_path,
                          "--state", state_path, "--out", out_path],
                         env={"PLAB_CLAUDE_BIN": "no-such-claude-binary-xyz"})

        out_text = ""
        if os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as f:
                out_text = f.read()

        for secret in secrets:
            check(f"AC-15: a secret is absent from stdout ({secret[:6]}...)", secret not in proc.stdout)
            check(f"AC-15: a secret is absent from stderr ({secret[:6]}...)", secret not in proc.stderr)
            check(f"AC-15: a secret is absent from the output file ({secret[:6]}...)", secret not in out_text)

        facts = json.loads(out_text) if out_text else {}
        creds = facts.get("credentials", [])
        check("AC-15: all three credential files reported", len(creds) == 3, str(creds))
        by_path = {c["path"]: c for c in creds}
        if npmrc_with_stem in by_path:
            check("AC-15: .npmrc (with stem) key name reported",
                  any("_authToken" in k for k in by_path[npmrc_with_stem].get("inline_keys", []) or []),
                  str(by_path[npmrc_with_stem]))
        if bare_npmrc in by_path:
            check("AC-15: bare .npmrc key name reported",
                  "registry_token" in (by_path[bare_npmrc].get("inline_keys") or []), str(by_path[bare_npmrc]))
        if bare_env in by_path:
            rec = by_path[bare_env]
            check("AC-15: .env `export KEY=` reported as inline",
                  "API_SECRET" in (rec.get("inline_keys") or []), str(rec))
            check("AC-15: .env env-reference value is NOT reported as inline",
                  "REF_KEY" not in (rec.get("inline_keys") or []), str(rec))
        check("AC-15: mtime reported", all(c.get("mtime") is not None for c in creds), str(creds))

    # The canary runs against a real subprocess invocation of a mutated copy, so it
    # exercises the exact gate above (stdout/stderr/output-file), not a hand check.
    test_ac15_canary()


def test_ac15_canary():
    """AGENTS.md: a gate must be proven to fail when the rule it guards is removed.
    Build a copy of the script with scan_credential_file's one safety line removed (it
    appends `key=value` to inline_keys instead of discarding the value), run the exact
    AC-15 checks above against that copy as a real subprocess, and confirm at least one
    of the three absence checks fails. The copy is deleted whether or not this passes."""
    copy_path = make_mutated_copy()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            secret = "ghp_CANARYVALUE999"
            cred_path = os.path.join(tmp, "fake.npmrc")
            write(cred_path, f"//registry.npmjs.org/:_authToken={secret}\n")

            data_dir = os.path.join(tmp, "data")
            write_json(os.path.join(data_dir, "global.json"), minimal_global_json())
            write_json(os.path.join(data_dir, "workflow_calls.json"), [])

            settings_path = os.path.join(tmp, "settings.local.md")
            make_settings_file(settings_path, credential_files=[cred_path],
                                claude_settings=os.path.join(tmp, "claude-settings.json"))
            write_json(os.path.join(tmp, "claude-settings.json"), {})

            out_path = os.path.join(tmp, "facts.json")
            proc = run_tool(["--config", settings_path, "--data", data_dir,
                              "--ledger", os.path.join(tmp, "ledger.jsonl"),
                              "--state", os.path.join(tmp, "state.json"), "--out", out_path],
                             env={"PLAB_CLAUDE_BIN": "no-such-claude-binary-xyz"}, tool=copy_path)

            out_text = ""
            if os.path.exists(out_path):
                with open(out_path, encoding="utf-8") as f:
                    out_text = f.read()

            stdout_leaked = secret in proc.stdout
            stderr_leaked = secret in proc.stderr
            file_leaked = secret in out_text
            n_failed = sum([stdout_leaked, stderr_leaked, file_leaked])
            check("AC-15 canary: the mutated copy leaks the secret somewhere "
                  f"({n_failed} of 3 checks failed)", n_failed >= 1,
                  f"stdout={stdout_leaked} stderr={stderr_leaked} file={file_leaked}")
    finally:
        if os.path.exists(copy_path):
            os.remove(copy_path)
        check("AC-15 canary: mutated copy removed", not os.path.exists(copy_path))


def test_ac16_cost_gap_exits_1():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        # lane total 1.00, per-workflow sum 11.00 -> gap 10.00 > tolerance 2.00
        write_json(os.path.join(data_dir, "global.json"), minimal_global_json(workflow_lane_cost=1.00))
        write_json(os.path.join(data_dir, "workflow_calls.json"), [
            {"half": "focus", "population": "interactive", "cost": 6.0, "n_agents_dedup": 2,
             "req_models": {"claude-sonnet-4-5": 2}},
            {"half": "focus", "population": "interactive", "cost": 5.0, "n_agents_dedup": 1,
             "req_models": {"claude-sonnet-4-5": 1}},
        ])

        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, workflow_tolerance_usd=2.0,
                            claude_settings=os.path.join(tmp, "claude-settings.json"))
        write_json(os.path.join(tmp, "claude-settings.json"), {})

        out_path = os.path.join(tmp, "facts.json")
        proc = run_tool(["--config", settings_path, "--data", data_dir,
                          "--ledger", os.path.join(tmp, "ledger.jsonl"),
                          "--state", os.path.join(tmp, "state.json"), "--out", out_path],
                         env={"PLAB_CLAUDE_BIN": "no-such-claude-binary-xyz"})
        check("AC-16: exits 1 on an over-tolerance workflow gap", proc.returncode == 1, proc.stdout)
        facts = json.loads(open(out_path, encoding="utf-8").read())
        cg = facts["workflows"]["cost_gap"]
        check("AC-16: gap_usd computed", abs(cg["gap_usd"] - 10.0) < 1e-6, str(cg))
        check("AC-16: over_tolerance true", cg["over_tolerance"] is True)
        check("AC-16: workflow_count is 2", facts["workflows"]["workflow_count"] == 2)
        check("AC-16: agent_count is 3", facts["workflows"]["agent_count"] == 3)
        check("AC-16: model_split reported", facts["workflows"]["model_split"] == {"claude-sonnet-4-5": 3})


def test_settings_drift_registered_and_unregistered():
    prev_snapshot = {
        "env.FOO": daf.sha256_json("old-value"),
        "env.BAR": daf.sha256_json("same-value"),
    }
    now_flat = {"env.FOO": "new-value", "env.BAR": "same-value"}

    with tempfile.TemporaryDirectory() as tmp:
        register_path = os.path.join(tmp, "config-changes.md")
        write(register_path, "| Date | What |\n|---|---|\n| 2026-02-01 | pinned env.FOO on purpose |\n")

        gaps = []
        drift = daf.compute_settings_drift(now_flat, prev_snapshot, register_path, "2026-01-01", gaps)
        unregistered_keys = {u["key"] for u in drift["unregistered"]}
        check("settings_drift: FOO is registered (not reported)", "env.FOO" not in unregistered_keys,
              str(drift))
        check("settings_drift: no new-value anywhere in drift output", "new-value" not in json.dumps(drift))

        register_path2 = os.path.join(tmp, "config-changes-empty.md")
        write(register_path2, "| Date | What |\n|---|---|\n| 2025-01-01 | unrelated, and too old anyway |\n")
        drift2 = daf.compute_settings_drift(now_flat, prev_snapshot, register_path2, "2026-01-01", gaps)
        unregistered_keys2 = {u["key"] for u in drift2["unregistered"]}
        check("settings_drift: FOO unregistered when register doesn't mention it after last_audit_date",
              "env.FOO" in unregistered_keys2, str(drift2))
        check("settings_drift: BAR not reported (value unchanged)", "env.BAR" not in unregistered_keys2)
        check("settings_drift: key name only, never a value", "new-value" not in json.dumps(drift2)
              and "old-value" not in json.dumps(drift2))

        # The register's own format pairs a row date with a later "review on" date.
        # The ROW date (first column) must gate "after last_audit_date", not a review
        # date that happens to be later.
        register_path3 = os.path.join(tmp, "config-changes-review-date.md")
        write(register_path3,
              "| Date | What | Review on |\n|---|---|---|\n"
              "| 2025-06-01 | pinned env.FOO, reviewed later | 2026-06-01 |\n")
        drift3 = daf.compute_settings_drift(now_flat, prev_snapshot, register_path3, "2026-01-01", gaps)
        unregistered_keys3 = {u["key"] for u in drift3["unregistered"]}
        check("settings_drift: a stale row's later review-on date does not register the change",
              "env.FOO" in unregistered_keys3, str(drift3))


def test_model_pins():
    flat = {
        "env.ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4-5",
        "model": "opus",
        "env.ANTHROPIC_DEFAULT_HAIKU_MODEL": "not-a-model-id!!",
        "env.SOME_OTHER_KEY": "claude-sonnet-4-5",  # not a pin key name; should not appear
    }
    pins = daf.compute_model_pins(flat)
    by_key = {p["key"]: p["value"] for p in pins}
    check("model_pins: a real model id is reported with its value",
          by_key.get("env.ANTHROPIC_DEFAULT_SONNET_MODEL") == "claude-sonnet-4-5", str(pins))
    check("model_pins: top-level `model` matched", by_key.get("model") == "opus", str(pins))
    check("model_pins: a non-model value is withheld",
          by_key.get("env.ANTHROPIC_DEFAULT_HAIKU_MODEL") == daf.WITHHELD, str(pins))
    check("model_pins: a non-pin key name is not reported", "env.SOME_OTHER_KEY" not in by_key, str(pins))


def test_series_wrap_and_skip():
    check("series: Z wraps to A", daf.skip_adjust("Z", set()) == "Z")
    check("series: Z skipped wraps past A to B", daf.skip_adjust("Z", {"Z", "A"}) == "B")
    check("series: a non-skip letter is unchanged", daf.skip_adjust("C", {"D"}) == "C")
    check("series: advance_letter wraps Z to A", daf.advance_letter("Z") == "A")


def test_commit_state_advances_and_snapshots():
    with tempfile.TemporaryDirectory() as tmp:
        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, recommendation_series={"next": "A", "skip": ["D"]})

        facts_path = os.path.join(tmp, "facts.json")
        snapshot = {"env.FOO": "deadbeef"}
        write_json(facts_path, {
            "next_series_letter": "C",
            "claude_version": {"installed": "2.1.300"},
            "settings_snapshot": snapshot,
            "audit_date": "2026-02-10",
        })
        state_path = os.path.join(tmp, "state.json")

        proc = run_tool(["--config", settings_path, "--state", state_path,
                          "--commit-state", "--facts", facts_path])
        check("commit-state: exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
        new_state = json.loads(open(state_path, encoding="utf-8").read())
        check("commit-state: advances C to D, skips D, lands on E",
              new_state.get("recommendation_series", {}).get("next") == "E", str(new_state))
        check("commit-state: writes last_claude_version", new_state.get("last_claude_version") == "2.1.300")
        check("commit-state: writes the settings snapshot verbatim",
              new_state.get("settings_snapshot") == snapshot)
        check("commit-state: writes last_audit_date", new_state.get("last_audit_date") == "2026-02-10")


def test_commit_state_skips_snapshot_on_claude_settings_gap():
    """A gather run that could not read claude_settings carries an empty snapshot and a
    claude_settings gap. commit-state must not overwrite a good prior snapshot with
    that empty one, or every real key reads as newly added next run."""
    with tempfile.TemporaryDirectory() as tmp:
        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, recommendation_series={"next": "A", "skip": []})

        good_snapshot = {"env.FOO": "deadbeef", "model": "abc123"}
        state_path = os.path.join(tmp, "state.json")
        write_json(state_path, {"settings_snapshot": good_snapshot, "last_audit_date": "2026-01-01"})

        facts_path = os.path.join(tmp, "facts.json")
        write_json(facts_path, {
            "next_series_letter": "B",
            "claude_version": {"installed": None},
            "settings_snapshot": {},
            "audit_date": "2026-02-10",
            "gaps": ["claude_settings: not found (/no/such/path.json)"],
        })

        proc = run_tool(["--config", settings_path, "--state", state_path,
                          "--commit-state", "--facts", facts_path])
        check("commit-state gap guard: exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
        new_state = json.loads(open(state_path, encoding="utf-8").read())
        check("commit-state gap guard: keeps the previous snapshot",
              new_state.get("settings_snapshot") == good_snapshot, str(new_state))
        check("commit-state gap guard: still advances the series letter",
              new_state.get("recommendation_series", {}).get("next") == "C", str(new_state))
        check("commit-state gap guard: still advances last_audit_date",
              new_state.get("last_audit_date") == "2026-02-10", str(new_state))


def test_missing_claude_binary_is_a_gap():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        write_json(os.path.join(data_dir, "global.json"), minimal_global_json())
        write_json(os.path.join(data_dir, "workflow_calls.json"), [])
        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, claude_settings=os.path.join(tmp, "claude-settings.json"))
        write_json(os.path.join(tmp, "claude-settings.json"), {})
        out_path = os.path.join(tmp, "facts.json")

        proc = run_tool(["--config", settings_path, "--data", data_dir,
                          "--ledger", os.path.join(tmp, "ledger.jsonl"),
                          "--state", os.path.join(tmp, "state.json"), "--out", out_path],
                         env={"PLAB_CLAUDE_BIN": os.path.join(tmp, "definitely-not-a-real-binary")})
        facts = json.loads(open(out_path, encoding="utf-8").read())
        check("missing claude binary: installed is None", facts["claude_version"]["installed"] is None, str(facts["claude_version"]))
        check("missing claude binary: recorded as a gap",
              any("claude_version" in g for g in facts["gaps"]), str(facts["gaps"]))
        check("missing claude binary: no crash (exit code is 0 or 1, never 2)", proc.returncode in (0, 1), proc.stdout)


def test_claude_version_found_and_changed():
    with tempfile.TemporaryDirectory() as tmp:
        fake_claude_cmd = make_fake_claude(tmp, version="2.1.300")
        data_dir = os.path.join(tmp, "data")
        write_json(os.path.join(data_dir, "global.json"), minimal_global_json())
        write_json(os.path.join(data_dir, "workflow_calls.json"), [])
        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, claude_settings=os.path.join(tmp, "claude-settings.json"))
        write_json(os.path.join(tmp, "claude-settings.json"), {})
        state_path = os.path.join(tmp, "state.json")
        write_json(state_path, {"last_claude_version": "2.1.200"})
        out_path = os.path.join(tmp, "facts.json")

        # fake_claude_cmd is [sys.executable, path]; PLAB_CLAUDE_BIN takes one token,
        # so point it at a tiny wrapper .bat/.sh that calls the real interpreter. On
        # POSIX this can just be the script path with a shebang and +x; keep it simple
        # and portable by writing a one-line shell/batch wrapper instead.
        wrapper = os.path.join(tmp, "claude" + (".bat" if os.name == "nt" else ""))
        if os.name == "nt":
            write(wrapper, f'@echo off\r\n"{fake_claude_cmd[0]}" "{fake_claude_cmd[1]}" %*\r\n')
        else:
            write(wrapper, f'#!/bin/sh\nexec "{fake_claude_cmd[0]}" "{fake_claude_cmd[1]}" "$@"\n')
            os.chmod(wrapper, 0o755)

        proc = run_tool(["--config", settings_path, "--data", data_dir,
                          "--ledger", os.path.join(tmp, "ledger.jsonl"),
                          "--state", state_path, "--out", out_path],
                         env={"PLAB_CLAUDE_BIN": wrapper})
        facts = json.loads(open(out_path, encoding="utf-8").read())
        cv = facts["claude_version"]
        check("claude_version: installed is parsed from the fake binary", cv.get("installed") == "2.1.300", str(cv))
        check("claude_version: previous_recorded read from state", cv.get("previous_recorded") == "2.1.200", str(cv))
        check("claude_version: changed is True", cv.get("changed") is True, str(cv))
        check("claude_version: no gap when the binary is found",
              not any("claude_version" in g for g in facts["gaps"]), str(facts["gaps"]))


def test_reproduce_no_prior_row_reports_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        write_json(os.path.join(data_dir, "global.json"), minimal_global_json())
        write_json(os.path.join(data_dir, "workflow_calls.json"), [])
        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, claude_settings=os.path.join(tmp, "claude-settings.json"))
        write_json(os.path.join(tmp, "claude-settings.json"), {})
        out_path = os.path.join(tmp, "facts.json")

        proc = run_tool(["--config", settings_path, "--data", data_dir,
                          "--ledger", os.path.join(tmp, "ledger.jsonl"),  # does not exist
                          "--state", os.path.join(tmp, "state.json"), "--out", out_path],
                         env={"PLAB_CLAUDE_BIN": "no-such-claude-binary-xyz"})
        facts = json.loads(open(out_path, encoding="utf-8").read())
        check("reconciliation: no ledger -> found is False", facts["reconciliation"]["found"] is False,
              str(facts["reconciliation"]))
        check("reconciliation: no crash reading an absent ledger", proc.returncode in (0, 1))


def test_reproduce_found_row_reproduces():
    """A real positive path through collect.py --reproduce, against an EMPTY synthetic
    transcript root (no real transcripts are read), so the recorded and re-run totals
    are both zero and the reproduction agrees."""
    with tempfile.TemporaryDirectory() as tmp:
        transcript_root = os.path.join(tmp, "empty-projects")
        os.makedirs(transcript_root, exist_ok=True)

        settings_path = os.path.join(tmp, "settings.local.md")
        make_settings_file(settings_path, transcript_root=transcript_root,
                            claude_settings=os.path.join(tmp, "claude-settings.json"))
        write_json(os.path.join(tmp, "claude-settings.json"), {})

        ledger_path = os.path.join(tmp, "ledger.jsonl")
        prior_start, prior_end, focus_start = "2026-01-01", "2026-01-07", "2026-01-08"
        row = {
            "period_start": prior_start, "period_end": prior_end, "population": "interactive",
            "method": {"cutoff": "9999-12-31T00:00:00Z", "excluded_sessions": [],
                       "price_file_as_of": "2026-01-01", "collector_version": "1.0.0"},
            "cost": {"executor_cost_total": 0.0, "advisor_cost_total": 0.0},
        }
        ok, reason, written = ledger_mod.append(ledger_path, row)
        check("reproduce fixture: ledger row appended", ok, str(reason))

        data_dir = os.path.join(tmp, "data")
        write_json(os.path.join(data_dir, "global.json"),
                   minimal_global_json(win_start=prior_start, focus_start=focus_start, win_end="2026-01-14"))
        write_json(os.path.join(data_dir, "workflow_calls.json"), [])
        out_path = os.path.join(tmp, "facts.json")

        proc = run_tool(["--config", settings_path, "--data", data_dir, "--ledger", ledger_path,
                          "--state", os.path.join(tmp, "state.json"), "--out", out_path],
                         env={"PLAB_CLAUDE_BIN": "no-such-claude-binary-xyz"})
        facts = json.loads(open(out_path, encoding="utf-8").read())
        recon = facts["reconciliation"]
        check("reproduce: a prior-week row was found", recon.get("found") is True, str(recon))
        if recon.get("found"):
            rows = recon.get("rows", [])
            check("reproduce: one population row returned", len(rows) == 1, str(rows))
            if rows:
                check("reproduce: reproduced against an empty transcript root (both totals ~0)",
                      rows[0].get("reproduced") is True, str(rows[0]))


def main():
    test_ac15_no_value_leak()
    test_ac16_cost_gap_exits_1()
    test_settings_drift_registered_and_unregistered()
    test_model_pins()
    test_series_wrap_and_skip()
    test_commit_state_advances_and_snapshots()
    test_commit_state_skips_snapshot_on_claude_settings_gap()
    test_missing_claude_binary_is_a_gap()
    test_claude_version_found_and_changed()
    test_reproduce_no_prior_row_reports_not_found()
    test_reproduce_found_row_reproduces()

    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
