#!/usr/bin/env python3
"""
Tests for collect.py. Runs the tool as a subprocess against the synthetic fixture
trees under scripts/fixtures/collect/ (regenerate with scripts/fixtures/make_fixtures.py)
and asserts the expected totals, porting the 31 checks of the hand-run collector's test
suite plus one check per Requirement added in this port. Exits 0 when every check
passes, 1 when any check fails.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "collect.py")
FIXTURES = os.path.join(HERE, "fixtures", "collect")
SKILL_ROOT = os.path.dirname(HERE)

sys.path.insert(0, HERE)
import collect as collect_mod  # noqa: E402
import ledger as ledger_mod  # noqa: E402
import settings as settings_mod  # noqa: E402

TOL = 1e-3

CHECKS = []


def check(name, cond, detail=""):
    CHECKS.append((name, bool(cond), detail))
    mark = "OK" if cond else "FAIL"
    print(f"[{mark}] {name}" + (f" ({detail})" if detail and not cond else ""))


def approx(a, b, tol=TOL):
    return a is not None and b is not None and abs(a - b) <= tol


def run_tool(base, out_dir, extra_args=None):
    cmd = [sys.executable, "-I", TOOL, "--start", "2026-01-01", "--end", "2026-01-31",
           "--cutoff", "2026-02-01T00:00:00Z", "--tz", "America/New_York", "--base", base, "--out", out_dir]
    cmd += extra_args or []
    return subprocess.run(cmd, capture_output=True, text=True)


def load(out_dir, name):
    with open(os.path.join(out_dir, name), encoding="utf-8") as f:
        return json.load(f)


def find_session(sessions, session_id):
    for s in sessions:
        if s["sessionId"] == session_id:
            return s
    raise AssertionError(f"session {session_id} not found; have {[s['sessionId'] for s in sessions]}")


def price_file_as_of():
    with open(os.path.join(SKILL_ROOT, "references", "pricing.json"), encoding="utf-8") as f:
        return json.load(f)["as_of"]


# ====================================================================== AC-9: suffix walker
# A field whose value is a count of responses or records must end _dedup or _raw
# (Requirement 6). Two kinds of key are not checked directly against that rule:
#  - a "data-keyed" container's own children, where the key is a model id, a tool
#    name, a day, a half name and so on, not a schema field name;
#  - a child nested directly under a container whose own key already carries the
#    basis (literally "raw" / "dedup", or a key already ending _dedup / _raw), which
#    inherits that basis rather than repeating it.
# The same two sets are documented verbatim in references/collector-output.md.
DATA_KEYED_CONTAINERS = {
    "skills", "commands", "tools", "mcp", "modes", "main_models", "agent_req_model", "agent_types",
    "workflow_agent_req_models", "sessionKinds", "entrypoints", "versions", "errors_by_tool",
    "daily", "hourly", "cost_by_bucket", "req_models", "model_ids_raw", "unpriced_models",
    "model_report", "copied_folders_skipped", "cost_by_half", "responses_by_half",
    "models", "error_samples", "model_drift", "older_with_responses_dedup",
}


def walk_counts(obj, path, container_key, bad):
    if isinstance(obj, dict):
        inherited = (container_key in DATA_KEYED_CONTAINERS or container_key in ("raw", "dedup")
                     or (isinstance(container_key, str) and (container_key.endswith("_dedup") or container_key.endswith("_raw"))))
        for k, v in obj.items():
            if isinstance(v, bool):
                continue
            if isinstance(v, int):
                if inherited or k in collect_mod.COUNT_SUFFIX_EXEMPT_KEYS or k.startswith(collect_mod.COUNT_SUFFIX_EXEMPT_PREFIXES):
                    continue
                if not (k.endswith("_dedup") or k.endswith("_raw")):
                    bad.append(f"{path}.{k}")
            elif isinstance(v, (dict, list)):
                walk_counts(v, f"{path}.{k}", k, bad)
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            walk_counts(item, f"{path}[{idx}]", container_key, bad)


def main():
    with tempfile.TemporaryDirectory() as out_dir:
        r = run_tool(FIXTURES, out_dir)
        # The main fixture tree always carries a finding (fx-unknown's unpriced model, plus
        # model drift from fx-dedup/fx-cachewrite/fx-subagent-parent's child using an older
        # model than the family's newest priced id) so the collector's exit-code contract
        # (Requirement 11) makes this a 1, not a 0. This is a deliberate change from the
        # original tool, which had no exit-code contract and always exited 0.
        check("tool exits 1 on the fixture tree (it carries findings by design)", r.returncode == 1, r.stderr[-2000:])
        if r.returncode not in (0, 1):
            print(r.stdout[-4000:]); print(r.stderr[-4000:])
            print(f"\n{sum(1 for _, ok, _ in CHECKS if ok)}/{len(CHECKS)} checks passed")
            sys.exit(1)

        sessions = load(out_dir, "sessions.json")
        global_ = load(out_dir, "global.json")
        children = load(out_dir, "children.json")

        # ---- rule 1: dedup across 3 streamed content-block records, priced from the final
        # (largest-output) record only: input=1000, output=300 at sonnet-5 rates -> $0.005.
        s = find_session(sessions, "fx-dedup")
        check("rule1 dedup: n_responses_dedup == 1 (not 3)", s["n_responses_dedup"] == 1, s["n_responses_dedup"])
        check("rule1 dedup: cost == 0.005", approx(s["cost"], 0.005), s["cost"])

        # ---- rule 2: advisor iterations priced separately; executor cost unaffected; depth uses
        # the larger EXECUTOR iteration (450000), not the top-level sum (550000).
        s = find_session(sessions, "fx-advisor")
        check("rule2 advisor: executor cost == 1.155", approx(s["cost"], 1.155), s["cost"])
        check("rule2 advisor: cost_advisor == 2.1", approx(s["cost_advisor"], 2.1), s["cost_advisor"])
        check("rule2 advisor: advisor_calls_dedup == 1", s["advisor_calls_dedup"] == 1, s["advisor_calls_dedup"])

        # ---- rule 3: unknown model id never priced by guess.
        s = find_session(sessions, "fx-unknown")
        check("rule3 unknown model: session cost == 0.0", approx(s["cost"], 0.0), s["cost"])
        up = global_.get("unpriced_models", {}).get("claude-unknown-test-model")
        check("rule3 unknown model: listed in global.json unpriced_models", up is not None, up)
        if up:
            check("rule3 unknown model: responses_dedup == 1", up["responses_dedup"] == 1, up)
            check("rule3 unknown model: tokens tracked (input=777 output=333 cache_read=111)",
                  up["input"] == 777 and up["output"] == 333 and up["cache_read"] == 111, up)

        # ---- rule 4: claude-opus-5-5 prices at Opus 5.5 ($4/$20/M -> $0.05), not Opus 5 ($5/$25/M -> $0.0625).
        s = find_session(sessions, "fx-opus55")
        check("rule4 opus-5-5 pricing: cost == 0.05 (not 0.0625 at Opus 5 rates)", approx(s["cost"], 0.05), s["cost"])

        # ---- rule 5: a 1h cache write prices at 2x input, not 1.25x -> $0.412, not $0.262.
        s = find_session(sessions, "fx-cachewrite")
        check("rule5 1h cache write: cost == 0.412 (not 0.262 at the 5m rate)", approx(s["cost"], 0.412), s["cost"])

        # ---- rule 6: one real compaction (boundary + paired summary) counts once; the interrupt
        # text quoted inside the compaction summary does not count as an interrupt.
        s = find_session(sessions, "fx-compaction")
        check("rule6 compaction: compactions_dedup == 1 (not 2)", s["compactions_dedup"] == 1, s["compactions_dedup"])
        check("rule6 compaction: interrupts_dedup == 0 (summary text is not a real interrupt)",
              s["interrupts_dedup"] == 0, s["interrupts_dedup"])

        # ---- rule 7: a subagent child under <session>/subagents/ resolves correctly.
        kids = [c for c in children if c["parent"] == "fx-subagent-parent"]
        check("rule7 subagent child: exactly one child found", len(kids) == 1, kids)
        if kids:
            c = kids[0]
            check("rule7 subagent child: lane == subagent", c["lane"] == "subagent", c["lane"])
            check("rule7 subagent child: population == interactive", c["population"] == "interactive", c["population"])
            check("rule7 subagent child: cost == 0.0035 (haiku 4.5 rates)", approx(c["cost"], 0.0035), c["cost"])

        # ---- rule 3 (depth): aggregate check across all five PRICED main-lane interactive responses.
        depth = global_["depth"]["focus"]
        check("rule3 depth: 0-100K bin has 3 responses", depth["bins"]["0-100K"]["responses_dedup"] == 3, depth["bins"]["0-100K"])
        check("rule3 depth: 100-200K bin has 1 response (cache-write push)", depth["bins"]["100-200K"]["responses_dedup"] == 1, depth["bins"]["100-200K"])
        check("rule3 depth: 400-500K bin has 1 response (executor_max, not top-level sum)",
              depth["bins"]["400-500K"]["responses_dedup"] == 1, depth["bins"]["400-500K"])
        check("rule3 depth: 500-600K bin has 0 responses (top-level sum would wrongly land here)",
              depth["bins"]["500-600K"]["responses_dedup"] == 0, depth["bins"]["500-600K"])
        check("rule3 depth: n_responses_dedup == 5 total (unpriced fx-unknown excluded)", depth["n_responses_dedup"] == 5, depth["n_responses_dedup"])
        check("rule3 depth: share_responses_ge_400k == 0.2", approx(depth["share_responses_ge_400k"], 0.2, 1e-6), depth)
        check("rule3 depth: share_responses_ge_500k == 0.0", approx(depth["share_responses_ge_500k"], 0.0, 1e-6), depth)

        # ---- collector metadata sanity.
        check("global.json collector_version matches collect.py's COLLECTOR_VERSION",
              global_.get("collector_version") == collect_mod.COLLECTOR_VERSION, global_.get("collector_version"))
        check("global.json price_file_as_of matches the price file",
              global_.get("price_file_as_of") == price_file_as_of(), global_.get("price_file_as_of"))
        check("global.json day_zone records --tz", global_.get("day_zone") == "America/New_York", global_.get("day_zone"))

        # ---- Requirement 5/AC-8 (drift, in the main tree): sonnet and haiku only ever run an
        # older model here, so both are listed; opus and fable both ran their newest id, so
        # neither is listed.
        drift = global_.get("model_drift", {})
        check("model_drift: sonnet listed (only claude-sonnet-5 responded in this tree)", "sonnet" in drift, drift)
        check("model_drift: haiku listed (only claude-haiku-4-5 responded in this tree)", "haiku" in drift, drift)
        check("model_drift: opus not listed (fx-opus55 used the newest id)", "opus" not in drift, drift)
        check("model_drift: fable not listed (the advisor used the newest id)", "fable" not in drift, drift)

    # ---- AC-8 / Requirement 5, isolated: only the older model responds -> drift named;
    # the newer model also responds -> drift empty.
    with tempfile.TemporaryDirectory() as out_a:
        r = run_tool(os.path.join(FIXTURES, "drift-older"), out_a)
        g = load(out_a, "global.json")
        check("AC-8 drift present: sonnet named when only the older id responds", "sonnet" in g.get("model_drift", {}),
              g.get("model_drift"))
    with tempfile.TemporaryDirectory() as out_b:
        r = run_tool(os.path.join(FIXTURES, "drift-newer"), out_b)
        g = load(out_b, "global.json")
        check("AC-8 drift absent: sonnet not named once the newest id also responds",
              "sonnet" not in g.get("model_drift", {}), g.get("model_drift"))

    # ---- AC-7 / Requirement 4: a task notification (structural marker, and the text-tag
    # fallback) is not counted as a user prompt; the one typed prompt in the session is.
    with tempfile.TemporaryDirectory() as out_dir:
        r = run_tool(os.path.join(FIXTURES, "tasknotice"), out_dir)
        sessions = load(out_dir, "sessions.json")
        s = find_session(sessions, "fx-tasknotice")
        check("AC-7 task notice: n_user_prompts_dedup == 1 (not 3)", s["n_user_prompts_dedup"] == 1, s["n_user_prompts_dedup"])
        check("AC-7 task notice: task_notifications_dedup == 2 (one structural, one text-tag fallback)",
              s["task_notifications_dedup"] == 2, s["task_notifications_dedup"])

    # ---- AC-10 / Requirement 7: a session with responses in both halves carries cost_by_half
    # summing to its total cost, and no half field.
    with tempfile.TemporaryDirectory() as out_dir:
        r = run_tool(os.path.join(FIXTURES, "straddle"), out_dir, ["--focus-start", "2026-01-16"])
        sessions = load(out_dir, "sessions.json")
        s = find_session(sessions, "fx-straddle")
        check("AC-10 straddle: no half field on the session row", "half" not in s, s)
        check("AC-10 straddle: cost_by_half has both prior and focus", set(s.get("cost_by_half", {})) == {"prior", "focus"},
              s.get("cost_by_half"))
        total_by_half = sum(s.get("cost_by_half", {}).values())
        check("AC-10 straddle: cost_by_half sums to the session's total cost within one cent",
              abs(total_by_half - s["cost"]) <= 0.01, (total_by_half, s["cost"]))
        check("AC-10 straddle: responses_by_half has one response per half",
              s.get("responses_by_half") == {"prior": 1, "focus": 1}, s.get("responses_by_half"))

    # ---- a missing child file (a .meta.json with no sibling .jsonl) is a finding: exit 1,
    # named in global.json's missing_child_files.
    with tempfile.TemporaryDirectory() as out_dir:
        r = run_tool(os.path.join(FIXTURES, "missingchild"), out_dir)
        check("missing child file: tool exits with findings (1)", r.returncode == 1, r.returncode)
        g = load(out_dir, "global.json")
        check("missing child file: named in global.json", len(g.get("missing_child_files", [])) == 1, g.get("missing_child_files"))

    # ---- AC-6: copied project folder. A second copy of the fixture project must not change
    # any total; the copy is reported, not double-counted.
    with tempfile.TemporaryDirectory() as copy_base, tempfile.TemporaryDirectory() as out_a, \
            tempfile.TemporaryDirectory() as out_b:
        src = os.path.join(FIXTURES, "fixture-project")
        shutil.copytree(src, os.path.join(copy_base, "fixture-project"))
        run_tool(copy_base, out_a)
        shutil.copytree(src, os.path.join(copy_base, "fixture-project-renamed"))
        run_tool(copy_base, out_b)
        ga, gb = load(out_a, "global.json"), load(out_b, "global.json")
        check("AC-6 copy: focus interactive totals unchanged",
              ga["halves"]["focus"]["interactive"] == gb["halves"]["focus"]["interactive"])
        check("AC-6 copy: same number of session rows", len(load(out_a, "sessions.json")) == len(load(out_b, "sessions.json")),
              (len(load(out_a, "sessions.json")), len(load(out_b, "sessions.json"))))
        check("AC-6 copy: same number of child rows", len(load(out_a, "children.json")) == len(load(out_b, "children.json")))
        check("AC-6 copy: skipped copies are reported under copied_folders_skipped",
              sum(gb["copied_folders_skipped"].values()) > 0, gb["copied_folders_skipped"])

    # ---- AC-5: daylight saving. The same response lands on different days and halves in
    # Pacific and Eastern.
    with tempfile.TemporaryDirectory() as dst_base:
        proj = os.path.join(dst_base, "dst-project")
        os.makedirs(proj)
        path = os.path.join(proj, "fx-dst.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "timestamp": "2026-11-02T06:29:00Z",
                                 "message": {"role": "user", "content": "after the clocks change"}}) + "\n")
            f.write(json.dumps({"type": "assistant", "timestamp": "2026-11-02T06:30:00Z", "requestId": "req_fx_dst_1",
                                 "message": {"role": "assistant", "model": "claude-sonnet-5", "id": "msg_fx_dst_1",
                                             "content": [{"type": "text", "text": "ok"}],
                                             "usage": {"input_tokens": 1000, "output_tokens": 100,
                                                       "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}) + "\n")
        os.utime(path, (1793750400, 1793750400))  # 2026-11-04T00:00:00Z; keeps it inside the mtime floor
        for tz, day in (("America/Los_Angeles", "2026-11-01"), ("America/New_York", "2026-11-02")):
            with tempfile.TemporaryDirectory() as out_dst:
                cmd = [sys.executable, "-I", TOOL, "--start", "2026-11-01", "--end", "2026-11-02",
                       "--focus-start", "2026-11-02", "--tz", tz, "--base", dst_base, "--out", out_dst]
                r = subprocess.run(cmd, capture_output=True, text=True)
                g = load(out_dst, "global.json")
                check(f"AC-5 dst {tz}: response counted on {day}", list(g["daily"]) == [day], list(g["daily"]))

    # ---- ledger: --ledger writes rows and a second identical run refuses (exit 1), via collect.py.
    with tempfile.TemporaryDirectory() as out_dir2, tempfile.TemporaryDirectory() as ledger_dir:
        ledger_path = os.path.join(ledger_dir, "ledger.jsonl")
        r1 = run_tool(FIXTURES, out_dir2, ["--ledger", ledger_path])
        rows = ledger_mod.read_rows(ledger_path)
        # No --focus-start was given, so the whole window is the focus period and there is no
        # prior period: one row per population (2), not the four a half-indexed ledger would
        # have written for an empty prior half.
        check("ledger: first run writes 2 rows (1 period x 2 populations; no prior period)", len(rows) == 2, len(rows))
        check("ledger: rows carry schema_version 2", all(row.get("schema_version") == 2 for row in rows), rows)
        check("ledger: rows carry a full method", all(set(row.get("method", {})) >= {"cutoff", "excluded_sessions", "price_file_as_of", "collector_version"} for row in rows), rows)

        r2 = run_tool(FIXTURES, out_dir2, ["--ledger", ledger_path])
        check("ledger: a second identical run refuses (exit 1)", r2.returncode == 1, r2.returncode)
        check("ledger: refusal appends nothing (still 2 rows)", len(ledger_mod.read_rows(ledger_path)) == 2,
              len(ledger_mod.read_rows(ledger_path)))

    # ---- AC-14: --reproduce re-runs a row's recorded method; a changed price file is named.
    with tempfile.TemporaryDirectory() as out_dir3, tempfile.TemporaryDirectory() as ledger_dir2:
        ledger_path2 = os.path.join(ledger_dir2, "ledger.jsonl")
        run_tool(FIXTURES, out_dir3, ["--ledger", ledger_path2])
        rows = ledger_mod.read_rows(ledger_path2)
        focus_interactive = next(r for r in rows if r["population"] == "interactive")
        row_id = focus_interactive["row_id"]
        check("AC-14 setup: the picked row has a non-zero recorded cost", collect_mod.row_total_cost(focus_interactive) > 0,
              focus_interactive)

        r_rep = subprocess.run([sys.executable, "-I", TOOL, "--reproduce", row_id, "--ledger", ledger_path2,
                                 "--base", FIXTURES, "--tz", "America/New_York"], capture_output=True, text=True)
        check("AC-14 reproduce: exits 0 within one dollar with the same price file", r_rep.returncode == 0, r_rep.stdout + r_rep.stderr)

        changed_price = os.path.join(ledger_dir2, "changed-pricing.json")
        with open(os.path.join(SKILL_ROOT, "references", "pricing.json"), encoding="utf-8") as f:
            pd = json.load(f)
        pd["as_of"] = "2099-01-01"
        for mid in pd["models"]:
            pd["models"][mid]["output"] = pd["models"][mid]["output"] * 100
            pd["models"][mid]["input"] = pd["models"][mid]["input"] * 100
        with open(changed_price, "w", encoding="utf-8") as f:
            json.dump(pd, f)
        r_rep2 = subprocess.run([sys.executable, "-I", TOOL, "--reproduce", row_id, "--ledger", ledger_path2,
                                  "--base", FIXTURES, "--tz", "America/New_York", "--price-file", changed_price],
                                 capture_output=True, text=True)
        check("AC-14 reproduce: exits 1 with a changed price file", r_rep2.returncode == 1, r_rep2.stdout)
        check("AC-14 reproduce: names the price file as the difference", "price file" in r_rep2.stdout, r_rep2.stdout)

    # ---- AC-9: every count-of-responses-or-records field in the output ends _dedup or _raw.
    with tempfile.TemporaryDirectory() as out_dir4:
        run_tool(os.path.join(FIXTURES, "straddle"), out_dir4, ["--focus-start", "2026-01-16"])
        bad = []
        for fname in ("global.json", "sessions.json", "children.json", "agent_calls.json",
                      "workflow_calls.json", "projects.json"):
            data = load(out_dir4, fname)
            walk_counts(data, fname, None, bad)
        check("AC-9: every count field ends _dedup or _raw", bad == [], bad)

    # ---- AC-11: no shipped file under the skill carries an owner-specific string.
    # The drive-letter pattern requires a word boundary before the single letter (so an
    # ordinary "key:\n" inside this very test's source, or any other file, is not a false
    # match) and at least one path segment after the slash (so a bare "C:/" is not confused
    # with, say, a URL scheme or a dict value ending in a colon-slash by coincidence).
    patterns = [r"\b[A-Za-z]:[\\/][\w.\\/-]+", r"\bjprisant\b", r"\bprisant\b", r"[Ee]--[Pp]rojects"]
    self_path = os.path.abspath(__file__)
    offenders = []
    for root, dirs, files in os.walk(SKILL_ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for fn in files:
            fp = os.path.join(root, fn)
            if os.path.abspath(fp) == self_path:
                continue  # this file's own source necessarily contains the detection patterns
            try:
                with open(fp, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception:
                continue
            for pat in patterns:
                if re.search(pat, text):
                    offenders.append((os.path.relpath(fp, SKILL_ROOT), pat))
    check("AC-11: no owner-specific string anywhere under the skill", offenders == [], offenders)

    # ---- settings.py: the documented YAML subset parses scalars, lists, one level of mapping.
    sample = (
        "timezone: America/Los_Angeles\n"
        "transcript_root: \"/example/claude/projects\"\n"
        "noise_patterns:\n"
        "  - bench-artifact\n"
        "  - temp-dir\n"
        "aliases:\n"
        "  \"projects-\": \"\"\n"
        "  \"github-example-\": \"gh/\"\n"
        "allow_tracked_output: true\n"
    )
    parsed = settings_mod.parse_yaml_subset(sample)
    check("settings parser: scalar", parsed["timezone"] == "America/Los_Angeles", parsed)
    check("settings parser: quoted scalar", parsed["transcript_root"] == "/example/claude/projects", parsed)
    check("settings parser: list", parsed["noise_patterns"] == ["bench-artifact", "temp-dir"], parsed)
    check("settings parser: one level of mapping with quoted keys", parsed["aliases"] == {"projects-": "", "github-example-": "gh/"}, parsed)
    check("settings parser: boolean", parsed["allow_tracked_output"] is True, parsed)
    md = "---\n" + sample + "---\nbody\n"
    check("settings parser: frontmatter extraction round-trips", settings_mod.parse_yaml_subset(settings_mod.extract_frontmatter(md)) == parsed)

    # ---- settings.py: inline comments and one-line flow lists, as references/settings-example.md writes them.
    extended = (
        "timezone: America/Los_Angeles   # IANA name\n"
        "label: \"a # inside quotes stays\"\n"
        "private_patterns: [\"_local/\", \"_session-logs/\"]\n"
        "automated:\n"
        "  entrypoints: [sdk-cli]\n"
        "  dir_patterns: [bench-, tmp-]   # test folders\n"
        "project_aliases:                 # folder names to labels\n"
        "  \"^home-owner-src-\": \"\"\n"
    )
    ext = settings_mod.parse_yaml_subset(extended)
    check("settings parser: inline comment stripped", ext["timezone"] == "America/Los_Angeles", ext)
    check("settings parser: a # inside quotes is kept", ext["label"] == "a # inside quotes stays", ext)
    check("settings parser: flow list", ext["private_patterns"] == ["_local/", "_session-logs/"], ext)
    check("settings parser: flow list inside a mapping", ext["automated"] == {"entrypoints": ["sdk-cli"], "dir_patterns": ["bench-", "tmp-"]}, ext)
    check("settings parser: a comment after a block key still opens the block", ext["project_aliases"] == {"^home-owner-src-": ""}, ext)
    with tempfile.TemporaryDirectory() as d:
        cfg = os.path.join(d, "s.local.md")
        with open(cfg, "w", encoding="utf-8") as f:
            f.write("---\n" + extended + "---\n")
        s = settings_mod.Settings(config_path=cfg, cli={})
        check("settings: automated.dir_patterns is read as the noise patterns", s.noise_patterns == ["bench-", "tmp-"], s.noise_patterns)
        check("settings: project_aliases is read as the aliases", s.aliases == {"^home-owner-src-": ""}, s.aliases)
    example_doc = open(os.path.join(SKILL_ROOT, "references", "settings-example.md"), encoding="utf-8").read()
    example_block = re.search(r"```yaml\n(.*?)```", example_doc, re.S).group(1)
    try:
        example = settings_mod.parse_yaml_subset(settings_mod.extract_frontmatter(example_block))
        example_ok = example.get("timezone") == "America/Los_Angeles" and isinstance(example.get("sweep"), dict)
    except ValueError as exc:
        example, example_ok = str(exc), False
    check("settings: the shipped settings example parses", example_ok, example)

    passed = sum(1 for _, ok, _ in CHECKS if ok)
    print(f"\n{passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
