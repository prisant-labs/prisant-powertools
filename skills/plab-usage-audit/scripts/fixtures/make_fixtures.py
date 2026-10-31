# Regenerates the fixture trees under scripts/fixtures/collect/ from scratch. Run after editing this
# file if a fixture needs to change; scripts/test-collect.py asserts against the shapes documented in
# each section's comment below, so keep the two in sync. Every fixture is synthetic: no owner string,
# no real session.
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
COLLECT = os.path.join(ROOT, "collect")


def w(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")


def user(text, ts="2026-01-15T16:00:00Z", extra=None):
    o = {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}}
    if extra: o.update(extra)
    return o


def asst(model, mid, req_id, usage, content=None, ts="2026-01-15T16:00:01Z"):
    return {"type": "assistant", "timestamp": ts, "requestId": req_id,
            "message": {"role": "assistant", "model": model, "id": mid,
                        "content": content or [{"type": "text", "text": "ok"}],
                        "usage": usage}}


def U(input_tokens=0, output_tokens=0, cache_read=0, cache_creation=0, cache_creation_detail=None, iterations=None):
    u = {"input_tokens": input_tokens, "output_tokens": output_tokens,
         "cache_read_input_tokens": cache_read, "cache_creation_input_tokens": cache_creation}
    if cache_creation_detail is not None:
        u["cache_creation"] = cache_creation_detail
    if iterations is not None:
        u["iterations"] = iterations
    return u


# ====================================================================== main fixture tree
# Ported verbatim (as to shape) from the hand-run collector's fixture tree, one file per accounting
# rule from Requirement 1. Rule numbers below match references/accounting-rules.md.
PROJ = os.path.join(COLLECT, "fixture-project")

# ---- rule 1: dedup. Same message id + requestId, 3 streamed content-block records, counted once,
# priced from the FINAL (largest-output) record only: input=1000, output=300 at sonnet-5 rates.
w(os.path.join(PROJ, "fx-dedup.jsonl"), [
    user("please add 2 and 2"),
    asst("claude-sonnet-5", "msg_fx_dedup_1", "req_fx_dedup_1", U(1000, 50, 0, 0)),
    asst("claude-sonnet-5", "msg_fx_dedup_1", "req_fx_dedup_1", U(1000, 150, 0, 0)),
    asst("claude-sonnet-5", "msg_fx_dedup_1", "req_fx_dedup_1", U(1000, 300, 0, 0)),
])

# ---- rule 2: advisor iterations. Top-level usage = sum of the two "message" iterations exactly
# (input 100000+450000=550000, output 1000+4500=5500). The advisor iteration (fable-5-1, 200000 in /
# 2000 out) is separate work, priced at the advisor's own rate, tracked only in cost_advisor/advisor_calls.
w(os.path.join(PROJ, "fx-advisor.jsonl"), [
    user("do a hard thing and consult the advisor"),
    asst("claude-sonnet-5", "msg_fx_adv_1", "req_fx_adv_1",
         U(550000, 5500, 0, 0, iterations=[
             {"type": "message", "input_tokens": 100000, "output_tokens": 1000,
              "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
             {"type": "advisor_message", "model": "claude-fable-5-1", "input_tokens": 200000, "output_tokens": 2000,
              "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
             {"type": "message", "input_tokens": 450000, "output_tokens": 4500,
              "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
         ])),
])

# ---- rule 3: unknown model id. Never priced by guess: cost must be $0, tokens/response tracked
# separately under global.json's unpriced_models, excluded from every dollar figure and from depth.
w(os.path.join(PROJ, "fx-unknown.jsonl"), [
    user("use a model that does not exist in the price file"),
    asst("claude-unknown-test-model", "msg_fx_unk_1", "req_fx_unk_1", U(777, 333, 111, 0)),
])

# ---- rule 4: claude-opus-5-5 must price at Opus 5.5 rates (4/20/M), not the claude-opus-5 entry (5/25/M).
w(os.path.join(PROJ, "fx-opus55.jsonl"), [
    user("use opus 5.5"),
    asst("claude-opus-5-5", "msg_fx_op55_1", "req_fx_op55_1", U(10000, 500, 0, 0)),
])

# ---- rule 5: a 1-hour cache write prices at 2x input, not 1.25x (the 5-minute rate).
w(os.path.join(PROJ, "fx-cachewrite.jsonl"), [
    user("write to the 1h cache"),
    asst("claude-sonnet-5", "msg_fx_cw_1", "req_fx_cw_1",
         U(5000, 200, 0, 100000, cache_creation_detail={"ephemeral_1h_input_tokens": 100000, "ephemeral_5m_input_tokens": 0})),
])

# ---- rule 6: one real compaction (boundary + its paired summary) must count once, not twice, and the
# interrupt text quoted inside the compaction summary must not be counted as an interrupt.
w(os.path.join(PROJ, "fx-compaction.jsonl"), [
    user("please help me investigate X"),
    {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-01-15T16:05:00Z", "content": "Conversation compacted"},
    user("This session is being continued from a previous conversation. Earlier, the user said "
         "[Request interrupted by user for tool use] during a file edit, before compaction.",
         ts="2026-01-15T16:05:00Z", extra={"isCompactSummary": True}),
])

# ---- rule 7: a subagent child under <session>/subagents/ resolves correctly (cost, lane, population).
w(os.path.join(PROJ, "fx-subagent-parent.jsonl"), [
    user("go do the subtask"),
    asst("claude-sonnet-5", "msg_fx_parent_1", "req_fx_parent_1", U(500, 50, 0, 0),
         content=[{"type": "tool_use", "id": "toolu_fx_child1", "name": "Agent",
                   "input": {"subagent_type": "general-purpose", "description": "test subtask", "prompt": "go do the subtask"}}]),
])
w(os.path.join(PROJ, "fx-subagent-parent", "subagents", "agent-child1.jsonl"), [
    asst("claude-haiku-4-5", "msg_fx_child_1", "req_fx_child_1", U(2000, 300, 0, 0)),
])
with open(os.path.join(PROJ, "fx-subagent-parent", "subagents", "agent-child1.meta.json"), "w", encoding="utf-8") as f:
    json.dump({"agentType": "general-purpose", "description": "test subtask", "toolUseId": "toolu_fx_child1"}, f)

# ====================================================================== rule 8: task notifications
# One real typed prompt and two task-notification records: one with the structural markers
# (turnOrigin / origin.kind), one with only the <task-notification> text tag (the fallback path, for
# a record that for any reason lacks the structural fields).
TASKNOTICE = os.path.join(COLLECT, "tasknotice", "fixture-project")
w(os.path.join(TASKNOTICE, "fx-tasknotice.jsonl"), [
    user("please review the open pull requests"),
    user("<task-notification>agent def456 finished: 3 files changed</task-notification>",
         ts="2026-01-15T16:01:00Z",
         extra={"turnOrigin": "task_notification", "origin": {"kind": "task-notification", "producer": "session-task"}}),
    user("<task-notification>agent abc123 finished: nothing to report</task-notification>",
         ts="2026-01-15T16:02:00Z"),  # no structural fields: must be caught by the text-tag fallback
    asst("claude-sonnet-5", "msg_fx_tn_1", "req_fx_tn_1", U(100, 20, 0, 0)),
])

# ====================================================================== rule 9: model drift
# families.sonnet in references/pricing.json is ["claude-sonnet-5-5", "claude-sonnet-5", ...] (newest
# first). "older" has a response only from the older id; "newer" has one from the newest id too.
DRIFT_OLDER = os.path.join(COLLECT, "drift-older", "fixture-project")
w(os.path.join(DRIFT_OLDER, "fx-drift.jsonl"), [
    user("use the pinned sonnet alias"),
    asst("claude-sonnet-5", "msg_fx_drift_1", "req_fx_drift_1", U(1000, 100, 0, 0)),
])
DRIFT_NEWER = os.path.join(COLLECT, "drift-newer", "fixture-project")
w(os.path.join(DRIFT_NEWER, "fx-drift.jsonl"), [
    user("use the pinned sonnet alias"),
    asst("claude-sonnet-5", "msg_fx_drift_1", "req_fx_drift_1", U(1000, 100, 0, 0)),
    asst("claude-sonnet-5-5", "msg_fx_drift_2", "req_fx_drift_2", U(1000, 100, 0, 0), ts="2026-01-15T16:01:00Z"),
])

# ====================================================================== rule 10: per-half sum
# One session with a response in the prior half and one in the focus half (focus-start 2026-01-16).
STRADDLE = os.path.join(COLLECT, "straddle", "fixture-project")
w(os.path.join(STRADDLE, "fx-straddle.jsonl"), [
    user("first half of the window", ts="2026-01-10T16:00:00Z"),
    asst("claude-sonnet-5", "msg_fx_str_1", "req_fx_str_1", U(1000, 100, 0, 0), ts="2026-01-10T16:00:01Z"),
    user("second half of the window", ts="2026-01-20T16:00:00Z"),
    asst("claude-sonnet-5", "msg_fx_str_2", "req_fx_str_2", U(2000, 200, 0, 0), ts="2026-01-20T16:00:01Z"),
])

# ====================================================================== rule 11: a missing child file
# A .meta.json with no sibling .jsonl: the orphaned child file the collector should flag, distinct from
# an ordinary unlinked Agent/Task call (which is common and not itself a finding).
MISSING = os.path.join(COLLECT, "missingchild", "fixture-project")
w(os.path.join(MISSING, "fx-missingchild.jsonl"), [
    user("go do the subtask"),
])
os.makedirs(os.path.join(MISSING, "fx-missingchild", "subagents"), exist_ok=True)
with open(os.path.join(MISSING, "fx-missingchild", "subagents", "agent-orphan.meta.json"), "w", encoding="utf-8") as f:
    json.dump({"agentType": "general-purpose", "description": "orphaned", "toolUseId": "toolu_fx_orphan"}, f)
# deliberately no agent-orphan.jsonl beside it

print("fixtures written under", COLLECT)
