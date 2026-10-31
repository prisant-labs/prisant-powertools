#!/usr/bin/env python3
"""
plab-usage-audit collector: a deterministic reader of Claude Code transcripts.

Ported from the owner's hand-run collector (version 2026-10-23) with its
accounting rules kept intact and these changes:

- Owner-specific values (the automated-session folder patterns, the project
  display aliases, the time zone, the transcript root) are read from a
  settings file passed with --config, never hard-coded. See settings.py for
  the settings file's format and `references/collector-output.md` for the
  settings keys this script reads.
- A user record that is a task notification (a background agent's
  completion notice, not text the owner typed) is not counted as a user
  prompt.
- Responses and cost are reported by the model id that actually ran,
  de-duplicated, per lane, and `model_drift` names a model family whose
  newest priced model has no response in the window while an older model
  of that family does.
- Every count field in the output ends in `_dedup` (a count after the
  de-duplication rule below) or `_raw` (a count of records before it).
  See `references/collector-output.md` for the exemption list (token
  sums, character counts and similar fields that are not response or
  record counts).
- Session rows carry `cost_by_half` and `responses_by_half` instead of a
  single `half` label.
- Every ledger row records its full method (the period, the cutoff, the
  excluded sessions, the price file's `as_of`, and the collector version),
  and `--reproduce <row_id> --ledger <file>` re-runs that method and
  compares totals.
- Exit codes: 0 clean, 1 findings (an unpriced model, model drift, a
  missing child file), 2 broken.

Accounting rules, unchanged from the ported collector, each proven by a
fixture under scripts/fixtures/ (see references/accounting-rules.md):

1. DEDUPE: one usage per (message.id, requestId). Claude Code repeats
   message.usage on every content-block record of a streamed response;
   summing raw records overcounts. The dedup is per file, so a transcript
   folder that is a copy of another (holding the same session files) is
   read once, from its largest copy.
2. Attribution is by MESSAGE timestamp, counted as a local day in the
   configured IANA zone via zoneinfo, with daylight saving applied per
   timestamp, never a fixed offset.
3. Prices come from a dated JSON file, never a guessed substring match. A
   recorded model id prices against an entry only if it equals that entry
   exactly, or equals the entry plus "-" plus a run of digits only (a
   dated snapshot). An id matching nothing is never priced by guess.
4. Advisor iterations (usage.iterations entries with type ==
   "advisor_message") are separate model work, priced at the advisor's own
   rate, in new fields that never fold into executor cost.
5. Context depth, for main-lane responses, is the largest input +
   cache_read + cache_creation over any executor ("message"-type)
   iteration, never the top-level sum (which can be roughly double the
   true depth for an advisor response).
6. A compaction is counted only from type == "system", subtype ==
   "compact_boundary" records.
"""
import argparse
import collections
import datetime
import glob
import hashlib
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import settings as settings_mod  # noqa: E402
import ledger as ledger_mod  # noqa: E402

COLLECTOR_VERSION = "1.0.0"

# A generic default: Claude Code's own transcript location. Not owner-specific.
DEFAULT_TRANSCRIPT_ROOT = os.path.join(os.path.expanduser("~"), ".claude", "projects")
DEFAULT_PRICE_FILE = os.path.join(HERE, "..", "references", "pricing.json")

FRONTIER_BUCKETS = {"opus", "fable"}  # mythos folds into "fable" in bucket() below

CMD_RE = re.compile(r'<command-name>\s*/?([^<\s]+)\s*</command-name>')
TAG_RE = re.compile(r'<[^>]+>')
NEG_RE = re.compile(r"^\s*(no\b|nope|stop\b|wait\b|that'?s (?:not|wrong)|that is (?:not|wrong)|don'?t\b|do not\b|undo\b|revert\b|actually\b|incorrect\b|you'?re wrong|not what|that'?s incorrect)", re.I)
WF_ID_RE = re.compile(r'\bwf_[0-9a-f]{8}-[0-9a-f]{3}\b')
WF_NAME_RE = re.compile(r"name\s*:\s*['\"]([^'\"]+)['\"]")

DEPTH_BIN_ORDER = ["0-100K", "100-200K", "200-300K", "300-400K", "400-500K", "500-600K", "600K+"]
DEPTH_BINS_GE_400 = {"400-500K", "500-600K", "600K+"}
DEPTH_BINS_GE_500 = {"500-600K", "600K+"}

# Keys whose int value is not a count of responses or records, so Requirement 6's
# _dedup / _raw suffix rule does not apply to them. Documented again, verbatim, in
# references/collector-output.md; scripts/test-collect.py imports this same set so
# the rule and its test can never drift apart.
COUNT_SUFFIX_EXEMPT_KEYS = {
    "input", "output", "cache_read", "cache_creation", "output_tokens",  # token sums, not response counts
    "thinking_chars", "prompt_chars", "script_chars",  # character counts
    "spawnDepth",  # a depth index, not a count
    "schema_version", "promptIndex", "turnIndex",  # identifiers / indices
    "active_days",  # a count of calendar days, not of responses or records
}
# A key starting with one of these prefixes is also a token sum, not a response or record
# count (the lane name varies: out_main, out_subagent, out_workflow).
COUNT_SUFFIX_EXEMPT_PREFIXES = ("out_",)


def bin_of(tokens):
    k = tokens / 1000.0
    if k < 100: return "0-100K"
    if k < 200: return "100-200K"
    if k < 300: return "200-300K"
    if k < 400: return "300-400K"
    if k < 500: return "400-500K"
    if k < 600: return "500-600K"
    return "600K+"


def zero_u():
    return {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}


def cache_split(usage, cache_mult):
    cc = usage.get("cache_creation") or {}
    w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
    w5m = cc.get("ephemeral_5m_input_tokens", 0) or 0
    wtot = usage.get("cache_creation_input_tokens", 0) or 0
    if w1h + w5m == 0 and wtot:
        w5m = wtot  # no TTL breakdown recorded: assume the cheaper 5m write
    return w5m, w1h


def u_of(usage, cache_mult):
    w5m, w1h = cache_split(usage, cache_mult)
    return {"input": usage.get("input_tokens", 0) or 0, "output": usage.get("output_tokens", 0) or 0,
            "cache_read": usage.get("cache_read_input_tokens", 0) or 0, "cache_creation": w5m + w1h}


def depth_tokens(usage_like, cache_mult):
    u = u_of(usage_like, cache_mult)
    return u["input"] + u["cache_read"] + u["cache_creation"]


def match_price(model, price_models):
    """Exact id match wins over everything. Otherwise the id must equal a known entry
    plus "-" plus a run of digits only (a dated snapshot); among digit-suffix matches
    the longest (most specific) entry wins. No fallback guess."""
    if not model:
        return None
    if model in price_models:
        return price_models[model]
    best = None
    for entry in price_models:
        prefix = entry + "-"
        if model.startswith(prefix):
            suffix = model[len(prefix):]
            if suffix.isdigit() and (best is None or len(entry) > len(best)):
                best = entry
    return price_models[best] if best else None


def cost_usd(model, usage, price_models, cache_mult):
    """(cost, priced). priced=False means the id matched nothing in the price file."""
    entry = match_price(model, price_models)
    if entry is None:
        return 0.0, False
    w5m, w1h = cache_split(usage, cache_mult)
    inp = usage.get("input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    cread = usage.get("cache_read_input_tokens", 0) or 0
    pin, pout, pread = entry["input"], entry["output"], entry["cache_read"]
    cost = (inp * pin + cread * pread + w5m * pin * cache_mult["5m"] + w1h * pin * cache_mult["1h"] + out * pout) / 1e6
    return cost, True


def bucket(m):
    if not m: return "unknown"
    if "haiku" in m: return "haiku"
    if "sonnet" in m: return "sonnet"
    if "opus" in m: return "opus"
    if "fable" in m or "mythos" in m: return "fable"
    if m.startswith("<synthetic"): return "synthetic"
    return "other"


def dir_noise(name, noise_patterns):
    """Owner-specific automated-session folder patterns come only from settings
    (Requirement 8); the shipped code names none of its own."""
    n = name.lower()
    for p in noise_patterns:
        if p.lower() in n:
            return p
    return None


def display_name(dirname, aliases):
    """Strip the generic Claude Code project-folder drive-letter encoding: a
    single lowercase letter followed by two hyphens, which Claude Code writes
    in place of a Windows drive letter and colon when it names a project
    folder from the working directory. Then apply the owner's configured
    aliases (longest-first so a more specific prefix is not shadowed by a
    shorter one), first match wins."""
    s = dirname.lower()
    s = re.sub(r'^[a-z]--', '', s)
    for prefix in sorted(aliases, key=len, reverse=True):
        if s.startswith(prefix):
            return aliases[prefix] + s[len(prefix):]
    return s


def is_task_notification(o, txt):
    """Requirement 4: a user record that is a background agent's completion
    notice, not text the owner typed. Two structural markers, checked first,
    and a text-tag fallback for a record that for any reason lacks them."""
    if o.get("turnOrigin") == "task_notification":
        return True
    origin = o.get("origin") or {}
    if isinstance(origin, dict) and origin.get("kind") == "task-notification":
        return True
    return bool(txt) and txt.lstrip().startswith("<task-notification>")


def text_of(content):
    if isinstance(content, str): return content
    out = []
    if isinstance(content, list):
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                out.append(b.get("text", "") or "")
    return "\n".join(out)


def clean(s, n=600):
    s = TAG_RE.sub(' ', s or '')
    return re.sub(r'\s+', ' ', s).strip()[:n]


class Ctx:
    """Everything one collection run needs, resolved from CLI flags and the
    settings file (explicit CLI flags win; see settings.py)."""
    def __init__(self, args, settings):
        self.win_start = args.start
        self.win_end = args.end
        self.focus_start = args.focus_start or args.start
        self.cutoff = args.cutoff
        self.exclude_sessions = set(args.exclude_session or [])
        tz_name = args.tz or settings.timezone
        self.tz_name = tz_name
        self.day_tz = ZoneInfo(tz_name) if tz_name else None
        self.day_zone = tz_name or f"machine ({datetime.datetime.now().astimezone().tzname()})"
        self.base = args.base or settings.transcript_root or DEFAULT_TRANSCRIPT_ROOT
        self.noise_patterns = settings.noise_patterns
        self.aliases = settings.aliases
        self.mtime_floor = (datetime.datetime.fromisoformat(self.win_start) - datetime.timedelta(days=1)).timestamp()

    def half_of(self, day):
        if not day or day < self.win_start or day > self.win_end:
            return None
        return "focus" if day >= self.focus_start else "prior"

    def local_day(self, ts):
        try:
            d = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if d.tzinfo is None:
                d = d.replace(tzinfo=datetime.timezone.utc)
            d = d.astimezone(self.day_tz)
            return d.strftime("%Y-%m-%d"), d.hour
        except Exception:
            return None, None

    def period_for_half(self, half):
        if half == "prior":
            if self.focus_start <= self.win_start:
                return None
            prior_end = (datetime.date.fromisoformat(self.focus_start) - datetime.timedelta(days=1)).isoformat()
            return self.win_start, prior_end
        return self.focus_start, self.win_end


class State:
    """Fresh per collection run, so collect() can be called more than once in one
    process (tests, and --reproduce re-running a different window)."""
    def __init__(self):
        self.ledger = collections.defaultdict(lambda: {"raw": self._cell(), "dedup": self._cell()})
        self.daily = collections.defaultdict(lambda: collections.defaultdict(float))
        self.hourly = collections.Counter()
        self.proj = collections.defaultdict(lambda: collections.defaultdict(float))
        self.model_ids_raw = collections.Counter()
        self.model_report = collections.defaultdict(lambda: {"responses_dedup": 0, "cost_dedup": 0.0})  # (model, lane)
        self.model_responses_dedup_total = collections.Counter()  # model -> dedup responses, whole window
        self.unpriced = collections.defaultdict(lambda: {"responses_dedup": 0, **zero_u()})
        self.unpriced_count = collections.Counter()  # (half, pop)
        self.advisor = collections.defaultdict(lambda: {"calls_dedup": 0, "cost_dedup": 0.0, "frontier_cost_dedup": 0.0})
        self.depth = collections.defaultdict(lambda: {"responses": collections.Counter(), "cost": collections.Counter()})
        self.copies_skipped = collections.Counter()
        self.missing_child_files = []

    @staticmethod
    def _cell():
        return {"msgs": 0, "cost": 0.0, **zero_u()}


def add_usage(cell, u, c):
    cell["msgs"] += 1; cell["cost"] += c
    for k in ("input", "output", "cache_read", "cache_creation"): cell[k] += u[k]


def scan_usage(path, proj, pop, lane, ctx, st, price_models, cache_mult):
    """Walk one transcript's assistant records. Returns a per-file summary (dedup)."""
    seen = {}
    summ = {"cost": 0.0, "output": 0, "models": collections.Counter(), "first_ts": None, "last_ts": None,
            "cost_by_bucket": collections.Counter(), "halves": collections.Counter(),
            "cost_advisor": 0.0, "advisor_calls_dedup": 0}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"assistant"' not in line: continue
                try: o = json.loads(line)
                except Exception: continue
                if o.get("type") != "assistant": continue
                msg = o.get("message") or {}
                model = msg.get("model"); usage = msg.get("usage")
                ts = o.get("timestamp")
                if not model or not usage or not ts or ts > ctx.cutoff: continue
                day, hr = ctx.local_day(ts)
                h = ctx.half_of(day)
                if not h: continue
                u = u_of(usage, cache_mult)
                c, priced = cost_usd(model, usage, price_models, cache_mult)
                b = bucket(model)
                st.model_ids_raw[model] += 1
                add_usage(st.ledger[(h, pop, lane, b)]["raw"], u, c)
                key = (msg.get("id"), o.get("requestId"))
                if key[0] is None: key = (id(o), None)
                prev = seen.get(key)
                if prev is None or u["output"] >= prev["u"]["output"]:
                    seen[key] = {"model": model, "u": u, "c": c, "priced": priced, "usage": usage,
                                 "day": day, "hr": hr, "h": h, "ts": ts}
    except Exception:
        return summ
    for rec in seen.values():
        model, u, c, priced, usage = rec["model"], rec["u"], rec["c"], rec["priced"], rec["usage"]
        day, hr, h, ts = rec["day"], rec["hr"], rec["h"], rec["ts"]
        b = bucket(model)
        if not priced:
            up = st.unpriced[model]
            up["responses_dedup"] += 1
            for k in ("input", "output", "cache_read", "cache_creation"): up[k] += u[k]
            st.unpriced_count[(h, pop)] += 1
        add_usage(st.ledger[(h, pop, lane, b)]["dedup"], u, c)
        st.daily[day][f"{lane}:{b}"] += c
        st.hourly[(h, hr)] += c
        pk = (proj, h, pop)
        st.proj[pk][f"cost_{lane}"] += c
        st.proj[pk][f"cost_{lane}_{b}"] += c
        st.proj[pk][f"out_{lane}"] += u["output"]
        summ["cost"] += c; summ["output"] += u["output"]; summ["models"][model] += 1
        summ["cost_by_bucket"][b] += c; summ["halves"][h] += 1
        if summ["first_ts"] is None or ts < summ["first_ts"]: summ["first_ts"] = ts
        if summ["last_ts"] is None or ts > summ["last_ts"]: summ["last_ts"] = ts

        st.model_report[(model, lane)]["responses_dedup"] += 1
        st.model_report[(model, lane)]["cost_dedup"] += c
        if priced:
            st.model_responses_dedup_total[model] += 1

        exec_msgs = []
        for it in (usage.get("iterations") or []):
            it_type = it.get("type")
            if it_type == "advisor_message":
                am = it.get("model")
                if am is None: am = "claude-fable-5-1"
                ac, am_priced = cost_usd(am, it, price_models, cache_mult)
                ab = bucket(am)
                acell = st.advisor[(h, pop, lane)]
                acell["calls_dedup"] += 1; acell["cost_dedup"] += ac
                if ab in FRONTIER_BUCKETS: acell["frontier_cost_dedup"] += ac
                summ["cost_advisor"] += ac; summ["advisor_calls_dedup"] += 1
                if am_priced:
                    st.model_responses_dedup_total[am] += 1
                if not am_priced:
                    upa = st.unpriced[am]; upa["responses_dedup"] += 1
                    ui = u_of(it, cache_mult)
                    for k in ("input", "output", "cache_read", "cache_creation"): upa[k] += ui[k]
            elif it_type == "message":
                exec_msgs.append(it)

        if lane == "main" and priced:
            depth_val = max((depth_tokens(it, cache_mult) for it in exec_msgs), default=None)
            if depth_val is None: depth_val = u["input"] + u["cache_read"] + u["cache_creation"]
            bn = bin_of(depth_val)
            dcell = st.depth[(h, pop)]
            dcell["responses"][bn] += 1
            dcell["cost"][bn] += c
    summ["n_responses_dedup"] = len(seen)
    return summ


def scan_session(path, dirname, ctx):
    rec = {"sessionId": os.path.splitext(os.path.basename(path))[0], "project": dirname.lower(),
           "display": display_name(dirname, ctx.aliases), "version": None, "entrypoint": None, "sessionKind": None,
           "title": None, "n_user_prompts_dedup": 0, "prompt_days": collections.Counter(),
           "skills": collections.Counter(), "commands": collections.Counter(),
           "tools": collections.Counter(), "mcp": collections.Counter(), "modes": collections.Counter(),
           "agent_calls": [], "workflow_calls": [], "tool_errors_dedup": 0, "perm_denials_dedup": 0,
           "hook_blocks_dedup": 0, "hook_block_samples": [], "user_negations_dedup": 0, "compactions_dedup": 0,
           "compactions_by_half": collections.Counter(), "interrupts_dedup": 0,
           "interrupts_by_half": collections.Counter(), "task_notifications_dedup": 0,
           "first_prompt": None, "prompts": [], "thinking_chars": 0,
           "main_models": collections.Counter(), "errors_by_tool": collections.Counter(),
           "error_samples": {}}
    pending_wf = {}
    tu_name = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try: o = json.loads(line)
                except Exception: continue
                t = o.get("type"); ts = o.get("timestamp")
                if rec["version"] is None and o.get("version"): rec["version"] = o.get("version")
                if rec["entrypoint"] is None and o.get("entrypoint"): rec["entrypoint"] = o.get("entrypoint")
                if rec["sessionKind"] is None and o.get("sessionKind"): rec["sessionKind"] = o.get("sessionKind")
                if t == "ai-title" and o.get("aiTitle"): rec["title"] = o.get("aiTitle")
                if t == "mode" and o.get("mode"): rec["modes"][o.get("mode")] += 1
                day, _ = ctx.local_day(ts) if ts else (None, None)
                in_win = ctx.half_of(day) is not None and (ts or "") <= ctx.cutoff
                if t == "assistant":
                    msg = o.get("message") or {}
                    if msg.get("model") and in_win: rec["main_models"][msg.get("model")] += 1
                    content = msg.get("content") or []
                    if not isinstance(content, list) or not in_win: continue
                    for b in content:
                        if not isinstance(b, dict): continue
                        if b.get("type") == "thinking":
                            rec["thinking_chars"] += len(b.get("thinking", "") or "")
                        if b.get("type") != "tool_use": continue
                        nm = b.get("name", ""); inp = b.get("input") or {}
                        rec["tools"][nm] += 1
                        tu_name[b.get("id")] = nm.split("__")[1] + ":" + nm.split("__")[-1] if nm.startswith("mcp__") else nm
                        if nm == "Skill":
                            sk = inp.get("skill") or inp.get("command")
                            if sk: rec["skills"][str(sk)] += 1
                        elif nm in ("Task", "Agent"):
                            rec["agent_calls"].append({
                                "tool_use_id": b.get("id"), "day": day,
                                "subagent_type": inp.get("subagent_type") or "(default)",
                                "req_model": inp.get("model") or "(inherit)",
                                "session_model": msg.get("model"),
                                "description": (inp.get("description") or "")[:120],
                                "prompt_chars": len(inp.get("prompt") or ""),
                                "background": bool(inp.get("run_in_background")),
                                "isolation": inp.get("isolation")})
                        elif nm == "Workflow":
                            scr = inp.get("script") or ""
                            mname = WF_NAME_RE.search(scr[:4000])
                            pending_wf[b.get("id")] = len(rec["workflow_calls"])
                            rec["workflow_calls"].append({
                                "tool_use_id": b.get("id"), "day": day,
                                "name": (mname.group(1) if mname else inp.get("name") or
                                         ("resume" if inp.get("resumeFromRunId") else "(script)")),
                                "script_chars": len(scr), "wf_id": inp.get("resumeFromRunId"),
                                "session_model": msg.get("model")})
                        elif nm.startswith("mcp__"):
                            parts = nm.split("__")
                            if len(parts) >= 2: rec["mcp"][parts[1]] += 1
                elif t == "user":
                    if o.get("isSidechain"): continue
                    msg = o.get("message") or {}
                    content = msg.get("content")
                    if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
                        if not in_win: continue
                        for b in content:
                            if not (isinstance(b, dict) and b.get("type") == "tool_result"): continue
                            tc = b.get("content")
                            txt = tc if isinstance(tc, str) else " ".join(
                                x.get("text", "") for x in tc if isinstance(x, dict)) if isinstance(tc, list) else ""
                            if b.get("tool_use_id") in pending_wf:
                                m = WF_ID_RE.search(txt)
                                if m: rec["workflow_calls"][pending_wf[b.get("tool_use_id")]]["wf_id"] = m.group(0)
                            low = txt[:500].lower()
                            if b.get("is_error"):
                                rec["tool_errors_dedup"] += 1
                                tn = tu_name.get(b.get("tool_use_id"), "?")
                                rec["errors_by_tool"][tn] += 1
                                sl = rec["error_samples"].setdefault(tn, [])
                                if len(sl) < 4: sl.append(clean(txt, 200))
                                if "hook" in low and ("block" in low or "denied" in low or "deny" in low):
                                    rec["hook_blocks_dedup"] += 1
                                    if len(rec["hook_block_samples"]) < 3: rec["hook_block_samples"].append(clean(txt, 160))
                            if ("permission" in low and ("denied" in low or "not been granted" in low or "rejected" in low)) \
                               or "user doesn't want to proceed" in low or "haven't granted" in low:
                                rec["perm_denials_dedup"] += 1
                            if "interrupted by user" in low:
                                rec["interrupts_dedup"] += 1
                                hw = ctx.half_of(day)
                                if hw: rec["interrupts_by_half"][hw] += 1
                        continue
                    txt = text_of(content)
                    if not in_win: continue
                    # Requirement 4: a task notification is not a typed prompt and is skipped
                    # before any of the checks below (it is not scanned for interrupt text,
                    # negation, or counted as a prompt).
                    if is_task_notification(o, txt):
                        rec["task_notifications_dedup"] += 1
                        continue
                    for cm in CMD_RE.findall(txt): rec["commands"][cm] += 1
                    if o.get("isCompactSummary"):
                        continue
                    if "[request interrupted by user" in txt.lower():
                        rec["interrupts_dedup"] += 1
                        hw = ctx.half_of(day)
                        if hw: rec["interrupts_by_half"][hw] += 1
                        continue
                    if o.get("isMeta"):
                        continue
                    if "this session is being continued from a previous conversation" in txt.lower():
                        continue
                    human = clean(txt)
                    cmds = CMD_RE.findall(txt)
                    if human and not (cmds and len(human) < 4):
                        rec["n_user_prompts_dedup"] += 1; rec["prompt_days"][day] += 1
                        if rec["first_prompt"] is None: rec["first_prompt"] = human[:500]
                        if len(rec["prompts"]) < 6: rec["prompts"].append(human[:280])
                        if NEG_RE.search(human): rec["user_negations_dedup"] += 1
                elif t == "system" and o.get("subtype") == "compact_boundary" and in_win:
                    rec["compactions_dedup"] += 1
                    hw = ctx.half_of(day)
                    if hw: rec["compactions_by_half"][hw] += 1
    except Exception as e:
        rec["_error"] = str(e)
    return rec


def find_copies(base):
    """A transcript folder that is a copy of another, holding the same session
    files, is counted once (the largest copy); the others are reported under
    copied_folders_skipped."""
    dirs = sorted(p for p in glob.glob(os.path.join(base, "*")) if os.path.isdir(p))
    copies = collections.defaultdict(list)
    for d in dirs:
        for f in glob.glob(os.path.join(d, "*.jsonl")):
            copies[("top", os.path.basename(f))].append(f)
        for f in glob.glob(os.path.join(d, "*", "subagents", "**", "*.jsonl"), recursive=True):
            copies[("child", os.path.relpath(f, d).replace("\\", "/"))].append(f)
    keep_files = set()
    skipped = collections.Counter()
    for group in copies.values():
        best = max(group, key=os.path.getsize)
        keep_files.add(best)
        for p in group:
            if p != best:
                skipped[(os.path.relpath(p, base).split(os.sep)[0], os.path.relpath(best, base).split(os.sep)[0])] += 1
    return dirs, keep_files, skipped


def agg(half, pop, ctx, st, sessions, agent_calls, wf_calls, children):
    ss = [s for s in sessions if s["half"] == half and s["population"] == pop]
    all_pop_ss = [s for s in sessions if s["population"] == pop]

    def merge(key):
        c = collections.Counter()
        for s in ss: c.update(s[key])
        return dict(c.most_common())

    lanes = {}
    for (h, p, lane, b), v in st.ledger.items():
        if h != half or p != pop: continue
        lanes.setdefault(lane, {})[b] = {
            "raw": {("cost" if k == "cost" else k): (round(x, 2) if k == "cost" else x) for k, x in v["raw"].items()},
            "dedup": {("cost" if k == "cost" else k): (round(x, 2) if k == "cost" else x) for k, x in v["dedup"].items()}}
    advisor_by_lane = {}
    for lane in set(lanes) | {l for (h, p, l) in st.advisor if h == half and p == pop}:
        acell = st.advisor.get((half, pop, lane))
        advisor_by_lane[lane] = {"cost_dedup": round(acell["cost_dedup"], 2) if acell else 0.0,
                                  "calls_dedup": acell["calls_dedup"] if acell else 0}
    ac = [a for a in agent_calls if a["half"] == half and a["population"] == pop]
    wc = [w for w in wf_calls if w["half"] == half and w["population"] == pop]
    kids = [c for c in children if c["half"] == half and c["population"] == pop]
    compactions_h = sum(s["compactions_by_half"].get(half, 0) for s in all_pop_ss)
    interrupts_h = sum(s["interrupts_by_half"].get(half, 0) for s in all_pop_ss)
    sessions_compacting_h = sum(1 for s in all_pop_ss if s["compactions_by_half"].get(half, 0) > 0)
    cost_advisor_total = sum(st.advisor[(half, pop, lane)]["cost_dedup"] for lane in ("main", "subagent", "workflow") if (half, pop, lane) in st.advisor)
    advisor_calls_total = sum(st.advisor[(half, pop, lane)]["calls_dedup"] for lane in ("main", "subagent", "workflow") if (half, pop, lane) in st.advisor)
    return {
        "sessions_dedup": len(ss), "projects_dedup": len({s["project"] for s in ss}),
        "user_prompts_dedup": sum(s["n_user_prompts_dedup"] for s in ss),
        "task_notifications_dedup": sum(s["task_notifications_dedup"] for s in ss),
        "lanes": lanes,
        "advisor_by_lane": advisor_by_lane,
        "cost_advisor": round(float(cost_advisor_total), 2), "advisor_calls_dedup": advisor_calls_total,
        "skills": merge("skills"), "commands": merge("commands"), "tools": merge("tools"),
        "mcp": merge("mcp"), "modes": merge("modes"), "main_models": merge("main_models"),
        "agent_calls_dedup": len(ac),
        "agent_req_model": dict(collections.Counter(a["req_model"] for a in ac).most_common()),
        "agent_types": dict(collections.Counter(a["subagent_type"] for a in ac).most_common()),
        "agent_inherit_on_frontier_dedup": sum(1 for a in ac if a["req_model"] == "(inherit)" and bucket(a["session_model"]) in FRONTIER_BUCKETS),
        "agent_background_dedup": sum(1 for a in ac if a["background"]),
        "workflow_calls_dedup": len(wc), "workflow_agents_dedup": sum(w["n_agents_dedup"] for w in wc),
        "workflow_agent_req_models": dict(collections.Counter(c["req_model"] or "(none)" for c in kids if c["lane"] == "workflow").most_common()),
        "child_files_dedup": dict(collections.Counter(c["lane"] for c in kids)),
        "waste": {"tool_errors_dedup": sum(s["tool_errors_dedup"] for s in ss), "perm_denials_dedup": sum(s["perm_denials_dedup"] for s in ss),
                  "hook_blocks_dedup": sum(s["hook_blocks_dedup"] for s in ss), "user_negations_dedup": sum(s["user_negations_dedup"] for s in ss),
                  "compactions_dedup": compactions_h, "interrupts_dedup": interrupts_h},
        "sessions_compacting_dedup": sessions_compacting_h,
        "errors_by_tool": merge("errors_by_tool"),
        "sessionKinds": dict(collections.Counter(s["sessionKind"] or "none" for s in ss)),
        "entrypoints": dict(collections.Counter(s["entrypoint"] or "none" for s in ss)),
        "versions": dict(collections.Counter((s["version"] or "?") for s in ss).most_common(8)),
    }


def depth_block(half, pop, st):
    d = st.depth.get((half, pop))
    if not d:
        return None
    H, C = d["responses"], d["cost"]
    n = sum(H.values()); tc = sum(C.values())
    return {
        "bins": {b: {"responses_dedup": H.get(b, 0), "cost": round(C.get(b, 0.0), 2)} for b in DEPTH_BIN_ORDER},
        "n_responses_dedup": n, "total_cost": round(tc, 2),
        "share_responses_ge_400k": round(sum(H.get(b, 0) for b in DEPTH_BINS_GE_400) / n, 4) if n else None,
        "share_cost_ge_400k": round(sum(C.get(b, 0) for b in DEPTH_BINS_GE_400) / tc, 4) if tc else None,
        "share_responses_ge_500k": round(sum(H.get(b, 0) for b in DEPTH_BINS_GE_500) / n, 4) if n else None,
    }


def lane_totals(half, pop, st):
    out = {}
    for (h, p, lane, b), cell in st.ledger.items():
        if h == half and p == pop:
            d = out.setdefault(lane, {"responses_dedup": 0, "cost": 0.0})
            d["responses_dedup"] += cell["dedup"]["msgs"]
            d["cost"] += cell["dedup"]["cost"]
    return out


def frontier_share_delegated_executor(half, pop, st):
    """Requirement 15: the frontier (opus/fable) share of delegated (subagent +
    workflow) EXECUTOR spend. The advisor is excluded from both sides of this
    ratio; see advisor_share_total for the advisor's own share."""
    deleg_cost = 0.0; deleg_frontier = 0.0
    for (h, p, lane, b), cell in st.ledger.items():
        if h == half and p == pop and lane in ("subagent", "workflow"):
            cost = cell["dedup"]["cost"]
            deleg_cost += cost
            if b in FRONTIER_BUCKETS: deleg_frontier += cost
    return round(deleg_frontier / deleg_cost, 4) if deleg_cost > 0 else None


def advisor_share_total(half, pop, st):
    """Requirement 15: the advisor's share of ALL spend (every lane's executor
    cost plus the advisor's own cost), on its own line."""
    executor_cost = 0.0
    for (h, p, lane, b), cell in st.ledger.items():
        if h == half and p == pop:
            executor_cost += cell["dedup"]["cost"]
    adv_cost = sum(st.advisor[(half, pop, lane)]["cost_dedup"] for lane in ("main", "subagent", "workflow") if (half, pop, lane) in st.advisor)
    total = executor_cost + adv_cost
    return round(adv_cost / total, 4) if total > 0 else None


def model_drift(st, price_data):
    """Requirement 5: for each model family in the price file, if the family's
    newest priced model has zero responses in the window while an older model of
    that family does, list it. `families` in the price file states release
    order explicitly (newest first); this does not infer it from the id string."""
    out = {}
    families = price_data.get("families") or {}
    for family, model_list in families.items():
        if not model_list:
            continue
        newest = model_list[0]
        responses_newest = st.model_responses_dedup_total.get(newest, 0)
        if responses_newest > 0:
            continue
        older_with_responses = {m: st.model_responses_dedup_total[m] for m in model_list[1:]
                                 if st.model_responses_dedup_total.get(m, 0) > 0}
        if older_with_responses:
            out[family] = {"newest": newest, "responses_newest_dedup": 0, "older_with_responses_dedup": older_with_responses}
    return out


def find_missing_child_files(dirs, keep_files):
    """Requirement 11's 'missing child file' finding: a child's .meta.json exists
    on disk with no sibling .jsonl transcript. This is narrower than an unlinked
    Agent/Task tool call (common, and not itself an error); it is a file the
    collector expected to find and did not."""
    missing = []
    for d in dirs:
        for mp in glob.glob(os.path.join(d, "*", "subagents", "**", "*.meta.json"), recursive=True):
            jp = mp[:-len(".meta.json")] + ".jsonl"
            if not os.path.exists(jp):
                missing.append(os.path.relpath(mp, os.path.dirname(d)))
    return missing


def collect(ctx, price_data):
    price_models = price_data["models"]
    cache_mult = price_data["cache_write_multiplier"]
    price_as_of = price_data["as_of"]
    st = State()

    dirs, keep_files, skipped = find_copies(ctx.base)
    st.copies_skipped = skipped
    st.missing_child_files = find_missing_child_files(dirs, keep_files)

    sessions, children = [], []
    for d in dirs:
        dn = os.path.basename(d); proj = dn.lower(); noise = dir_noise(dn, ctx.noise_patterns)
        tops = [f for f in glob.glob(os.path.join(d, "*.jsonl")) if os.path.getmtime(f) >= ctx.mtime_floor and f in keep_files]
        sess_pop = {}
        for f in tops:
            if os.path.splitext(os.path.basename(f))[0] in ctx.exclude_sessions: continue
            rec = scan_session(f, dn, ctx)
            pop = "automated" if (noise or rec["sessionKind"] == "bg" or rec["entrypoint"] == "sdk-cli") else "interactive"
            summ = scan_usage(f, proj, pop, "main", ctx, st, price_models, cache_mult)
            if not summ.get("n_responses_dedup") and not rec["n_user_prompts_dedup"]: continue
            rec["population"] = pop; rec["dir_noise"] = noise
            rec["cost"] = round(summ["cost"], 4); rec["output_tokens"] = summ["output"]
            rec["cost_advisor"] = round(summ["cost_advisor"], 4); rec["advisor_calls_dedup"] = summ["advisor_calls_dedup"]
            rec["n_responses_dedup"] = summ.get("n_responses_dedup", 0)
            rec["cost_by_bucket"] = {k: round(v, 3) for k, v in summ["cost_by_bucket"].items()}
            rec["first_ts"] = summ["first_ts"]; rec["last_ts"] = summ["last_ts"]
            rec["cost_by_half"] = {h: round(v, 4) for h, v in
                                    _cost_by_half(f, ctx, st, price_models, cache_mult).items()}
            rec["responses_by_half"] = dict(summ["halves"])
            rec["half"] = summ["halves"].most_common(1)[0][0] if summ["halves"] else \
                (ctx.half_of(min(rec["prompt_days"])) if rec["prompt_days"] else None)
            sess_pop[rec["sessionId"]] = pop
            sessions.append(rec)
        for f in glob.glob(os.path.join(d, "*", "subagents", "**", "*.jsonl"), recursive=True):
            if os.path.getmtime(f) < ctx.mtime_floor or f not in keep_files: continue
            rel = os.path.relpath(f, d).replace("\\", "/")
            parent = rel.split("/")[0]
            if parent in ctx.exclude_sessions: continue
            m = re.search(r"/(wf_[0-9a-f]{8}-[0-9a-f]{3})/", "/" + rel)
            lane = "workflow" if m else "subagent"
            pop = sess_pop.get(parent) or ("automated" if noise else "interactive")
            meta = {}
            mp = f[:-6] + ".meta.json"
            if os.path.exists(mp):
                try: meta = json.load(open(mp, encoding="utf-8"))
                except Exception: meta = {}
            summ = scan_usage(f, proj, pop, lane, ctx, st, price_models, cache_mult)
            if not summ.get("n_responses_dedup"): continue
            children.append({"project": proj, "display": display_name(dn, ctx.aliases), "parent": parent, "lane": lane,
                "wf_id": m.group(1) if m else None, "file": os.path.basename(f), "population": pop,
                "agentType": meta.get("agentType"), "req_model": meta.get("model"),
                "description": (meta.get("description") or "")[:120], "toolUseId": meta.get("toolUseId"),
                "spawnDepth": meta.get("spawnDepth"),
                "half": summ["halves"].most_common(1)[0][0], "cost": round(summ["cost"], 4),
                "cost_advisor": round(summ["cost_advisor"], 4), "advisor_calls_dedup": summ["advisor_calls_dedup"],
                "output_tokens": summ["output"], "n_responses_dedup": summ["n_responses_dedup"],
                "models": dict(summ["models"]), "cost_by_bucket": {k: round(v, 3) for k, v in summ["cost_by_bucket"].items()}})

    child_by_tuid = {c["toolUseId"]: c for c in children if c.get("toolUseId")}
    wf_children = collections.defaultdict(list)
    for c in children:
        if c["wf_id"]: wf_children[(c["parent"], c["wf_id"])].append(c)
    agent_calls, wf_calls = [], []
    for s in sessions:
        for a in s["agent_calls"]:
            c = child_by_tuid.get(a["tool_use_id"])
            row = {**a, "sessionId": s["sessionId"], "project": s["project"], "display": s["display"],
                   "population": s["population"], "half": ctx.half_of(a["day"]), "linked": bool(c)}
            if c:
                row.update({"child_cost": c["cost"], "child_output": c["output_tokens"],
                            "child_responses_dedup": c["n_responses_dedup"],
                            "child_bucket": max(c["cost_by_bucket"], key=c["cost_by_bucket"].get) if c["cost_by_bucket"] else None,
                            "child_agentType": c["agentType"]})
            agent_calls.append(row)
        for w in s["workflow_calls"]:
            wkids = wf_children.get((s["sessionId"], w["wf_id"]), []) if w["wf_id"] else []
            req = collections.Counter(k["req_model"] or "(none)" for k in wkids)
            wf_calls.append({**w, "sessionId": s["sessionId"], "project": s["project"], "display": s["display"],
                "population": s["population"], "half": ctx.half_of(w["day"]), "n_agents_dedup": len(wkids),
                "cost": round(sum(k["cost"] for k in wkids), 3),
                "cost_by_bucket": dict(sum((collections.Counter(k["cost_by_bucket"]) for k in wkids), collections.Counter())),
                "req_models": dict(req)})

    g = {"window": [ctx.win_start, ctx.win_end], "focus_start": ctx.focus_start,
         "collector_version": COLLECTOR_VERSION, "price_file_as_of": price_as_of, "day_zone": ctx.day_zone,
         "copied_folders_skipped": {f"{s} -> {k}": n for (s, k), n in sorted(st.copies_skipped.items())},
         "missing_child_files": sorted(st.missing_child_files),
         "halves": {h: {p: agg(h, p, ctx, st, sessions, agent_calls, wf_calls, children) for p in ("interactive", "automated")} for h in ("prior", "focus")},
         "daily": {d: {k: round(v, 2) for k, v in sorted(x.items())} for d, x in sorted(st.daily.items())},
         "hourly": {f"{h}:{hr:02d}": round(v, 2) for (h, hr), v in sorted(st.hourly.items())},
         "model_ids_raw": dict(st.model_ids_raw.most_common()),
         "model_report": {f"{m}|{lane}": {"responses_dedup": v["responses_dedup"], "cost_dedup": round(v["cost_dedup"], 4)}
                           for (m, lane), v in st.model_report.items()},
         "model_drift": model_drift(st, price_data),
         "unpriced_models": {m: dict(v) for m, v in st.unpriced.items()},
         "depth": {h: depth_block(h, "interactive", st) for h in ("prior", "focus")}}

    plist = []
    for (proj, h, pop), m in st.proj.items():
        ss = [s for s in sessions if s["project"] == proj and s["half"] == h and s["population"] == pop]
        row = {"project": proj, "display": display_name(proj, ctx.aliases), "half": h, "population": pop,
               "n_sessions_dedup": len(ss), "user_prompts_dedup": sum(s["n_user_prompts_dedup"] for s in ss),
               "active_days": len({d for s in ss for d in s["prompt_days"]}),
               "agent_calls_dedup": sum(1 for a in agent_calls if a["project"] == proj and a["half"] == h),
               "workflow_calls_dedup": sum(1 for w in wf_calls if w["project"] == proj and w["half"] == h),
               "skills": dict(sum((collections.Counter(s["skills"]) for s in ss), collections.Counter()).most_common(10)),
               "waste": {k: sum(s[k] for s in ss) for k in ("tool_errors_dedup", "perm_denials_dedup", "hook_blocks_dedup", "user_negations_dedup", "compactions_dedup")}}
        row.update({k: round(v, 2) if k.startswith("cost") else int(v) for k, v in m.items()})
        row["cost_total"] = round(sum(v for k, v in m.items() if k in ("cost_main", "cost_subagent", "cost_workflow")), 2)
        plist.append(row)
    plist.sort(key=lambda x: -x["cost_total"])

    slim_keys = ("sessionId", "project", "display", "population", "dir_noise", "sessionKind", "entrypoint",
                 "version", "title", "first_ts", "last_ts", "n_user_prompts_dedup", "n_responses_dedup", "cost", "cost_advisor",
                 "advisor_calls_dedup", "cost_by_bucket", "cost_by_half", "responses_by_half",
                 "output_tokens", "skills", "commands", "mcp", "modes", "main_models", "tool_errors_dedup", "perm_denials_dedup",
                 "hook_blocks_dedup", "hook_block_samples", "user_negations_dedup", "compactions_dedup", "interrupts_dedup",
                 "task_notifications_dedup", "thinking_chars", "errors_by_tool", "error_samples")
    sessions_out = [{k: s.get(k) for k in slim_keys} | {"n_agent_calls_dedup": len(s["agent_calls"]),
                     "n_workflow_calls_dedup": len(s["workflow_calls"])} for s in sessions]

    rows = []
    for half in ("prior", "focus"):
        period = ctx.period_for_half(half)
        if period is None:
            continue
        period_start, period_end = period
        for pop in ("interactive", "automated"):
            a = g["halves"][half][pop]
            lt = lane_totals(half, pop, st)
            d = depth_block(half, pop, st) or {}
            method = {"cutoff": ctx.cutoff, "excluded_sessions": sorted(ctx.exclude_sessions),
                      "price_file_as_of": price_as_of, "collector_version": COLLECTOR_VERSION}
            executor_cost_total = round(float(sum(v["cost"] for v in lt.values())), 2)
            rows.append({
                "schema_version": 2, "row_kind": "measurement",
                "period_start": period_start, "period_end": period_end, "population": pop,
                "day_zone": ctx.day_zone, "method": method,
                "volume": {"sessions_dedup": a["sessions_dedup"], "projects_dedup": a["projects_dedup"],
                           "user_prompts_dedup": a["user_prompts_dedup"],
                           "task_notifications_dedup": a["task_notifications_dedup"]},
                "cost": {"executor_cost_total": executor_cost_total, "advisor_cost_total": a["cost_advisor"],
                         "cost_by_lane": {lane: round(v["cost"], 2) for lane, v in lt.items()}},
                "responses_by_lane_dedup": {lane: v["responses_dedup"] for lane, v in lt.items()},
                "unpriced_responses_dedup": st.unpriced_count.get((half, pop), 0),
                "depth": {"share_responses_ge_400k": d.get("share_responses_ge_400k"),
                          "share_cost_ge_400k": d.get("share_cost_ge_400k"),
                          "share_responses_ge_500k": d.get("share_responses_ge_500k")},
                "routing": {"frontier_share_delegated_executor": frontier_share_delegated_executor(half, pop, st),
                            "advisor_share_total": advisor_share_total(half, pop, st)},
                "friction": {"compactions_dedup": a["waste"]["compactions_dedup"],
                             "sessions_compacting_dedup": a["sessions_compacting_dedup"],
                             "interrupts_dedup": a["waste"]["interrupts_dedup"],
                             "tool_errors_dedup": a["waste"]["tool_errors_dedup"],
                             "perm_denials_dedup": a["waste"]["perm_denials_dedup"],
                             "hook_blocks_dedup": a["waste"]["hook_blocks_dedup"],
                             "user_negations_dedup": a["waste"]["user_negations_dedup"]},
                "output": {"agent_calls_no_model_dedup": a["agent_req_model"].get("(inherit)", 0),
                           "workflow_agents_no_model_dedup": a["workflow_agent_req_models"].get("(none)", 0)},
                "plan_limit": None,
            })

    findings = []
    if g["unpriced_models"]:
        findings.append("unpriced_models")
    if g["model_drift"]:
        findings.append("model_drift")
    if g["missing_child_files"]:
        findings.append("missing_child_files")
    exit_code = 1 if findings else 0

    return {
        "global": g, "sessions": sessions_out, "children": children, "agent_calls": agent_calls,
        "workflow_calls": wf_calls, "projects": plist, "ledger_rows": rows, "findings": findings,
        "exit_code": exit_code,
    }


def _cost_by_half(path, ctx, st, price_models, cache_mult):
    """A session can carry responses in both the prior and the focus half
    (Requirement 7). This re-derives, from the same file, the cost attributable
    to each half, without re-adding to the shared ledger (a throwaway State)."""
    tmp = State()
    scan_usage(path, "__cost_by_half__", "__scratch__", "main", ctx, tmp, price_models, cache_mult)
    out = {}
    for (h, p, lane, b), cell in tmp.ledger.items():
        out[h] = out.get(h, 0.0) + cell["dedup"]["cost"]
    return out


def dump(out_dir, name, obj):
    with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, default=str)


def write_output(out_dir, result):
    os.makedirs(out_dir, exist_ok=True)
    dump(out_dir, "global.json", result["global"])
    dump(out_dir, "sessions.json", result["sessions"])
    dump(out_dir, "children.json", result["children"])
    dump(out_dir, "agent_calls.json", result["agent_calls"])
    dump(out_dir, "workflow_calls.json", result["workflow_calls"])
    dump(out_dir, "projects.json", result["projects"])


def build_arg_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--focus-start", default=None)
    ap.add_argument("--cutoff", default="9999-12-31T00:00:00Z")
    ap.add_argument("--exclude-session", action="append", default=[])
    ap.add_argument("--tz", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--base", default=None)
    ap.add_argument("--price-file", default=None)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--config", default=None, help="a .claude/plab-usage-audit.local.md settings file")
    ap.add_argument("--reproduce", default=None, metavar="ROW_ID",
                     help="re-run a ledger row's recorded method and compare totals; needs --ledger")
    return ap


def load_price_data(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def row_total_cost(row):
    cost = row.get("cost") or {}
    return round((cost.get("executor_cost_total") or 0.0) + (cost.get("advisor_cost_total") or 0.0), 4)


def run_reproduce(args, settings):
    if not args.ledger:
        print("broken: --reproduce needs --ledger")
        return 2
    old_row = ledger_mod.find_row(args.ledger, args.reproduce)
    if old_row is None:
        print(f"broken: no row with row_id {args.reproduce} in {args.ledger}")
        return 2
    method = old_row.get("method") or {}
    price_file = args.price_file or DEFAULT_PRICE_FILE
    price_data = load_price_data(price_file)

    period_start, period_end = old_row.get("period_start"), old_row.get("period_end")
    cutoff = args.cutoff if args.cutoff != build_arg_parser().get_default("cutoff") else method.get("cutoff", args.cutoff)
    exclude = args.exclude_session or method.get("excluded_sessions") or []

    class _A: pass
    a = _A()
    a.start, a.end, a.focus_start = period_start, period_end, period_start
    a.cutoff, a.exclude_session, a.tz, a.base = cutoff, exclude, args.tz, args.base
    ctx = Ctx(a, settings)
    new_result = collect(ctx, price_data)
    new_row = None
    for r in new_result["ledger_rows"]:
        if r["population"] == old_row.get("population"):
            new_row = r
            break

    old_total = row_total_cost(old_row)
    new_total = row_total_cost(new_row) if new_row else 0.0
    diff = abs(old_total - new_total)

    reasons = []
    if price_data.get("as_of") != method.get("price_file_as_of"):
        reasons.append(f"price file (was {method.get('price_file_as_of')}, now {price_data.get('as_of')})")
    if args.cutoff is not None and method.get("cutoff") and args.cutoff != method.get("cutoff") and \
            args.cutoff != build_arg_parser().get_default("cutoff"):
        reasons.append(f"cutoff (row had {method.get('cutoff')}, this run used {args.cutoff})")
    if args.exclude_session and sorted(args.exclude_session) != sorted(method.get("excluded_sessions") or []):
        reasons.append("exclusions")

    print(f"reproduce {args.reproduce}: recorded total ${old_total:.2f}, re-run total ${new_total:.2f}, "
          f"diff ${diff:.2f}")
    if diff <= 1.0:
        print("agreement within one dollar")
        return 0
    if reasons:
        print("difference: " + "; ".join(reasons))
    else:
        print("difference: unexplained (no recorded method field differs)")
    return 1


def main():
    ap = build_arg_parser()
    args = ap.parse_args()
    settings = settings_mod.Settings(config_path=args.config, cli={"timezone": args.tz, "transcript_root": args.base})

    if args.reproduce:
        return run_reproduce(args, settings)

    if not args.start or not args.end or not args.out:
        print("broken: --start, --end and --out are required (unless using --reproduce)")
        return 2

    price_file = args.price_file or DEFAULT_PRICE_FILE
    try:
        price_data = load_price_data(price_file)
    except Exception as e:
        print(f"broken: could not read price file {price_file}: {e}")
        return 2

    ctx = Ctx(args, settings)

    if args.ledger:
        # Checked before the transcript scan, so a refusal costs nothing (Requirement 9/12).
        conflicts = []
        for half in ("prior", "focus"):
            period = ctx.period_for_half(half)
            if period is None:
                continue
            period_start, period_end = period
            method = {"cutoff": ctx.cutoff, "excluded_sessions": sorted(ctx.exclude_sessions),
                      "price_file_as_of": price_data["as_of"], "collector_version": COLLECTOR_VERSION}
            for pop in ("interactive", "automated"):
                if ledger_mod.is_duplicate_measurement(args.ledger, period_start, period_end, pop, method):
                    conflicts.append((period_start, period_end, pop))
        if conflicts:
            print(f"refusing to append to {args.ledger}: a row already exists for {conflicts}")
            return 1

    result = collect(ctx, price_data)
    write_output(args.out, result)

    if args.ledger:
        for row in result["ledger_rows"]:
            ok, reason, _ = ledger_mod.append(args.ledger, row)
            if not ok:
                print(f"ledger: refused a row unexpectedly: {reason}")
        print(f"ledger: appended {len(result['ledger_rows'])} rows to {args.ledger}")

    print(f"sessions={len(result['sessions'])} children={len(result['children'])}")
    if result["findings"]:
        print("findings:", result["findings"])
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
