# Accounting rules

Every rule `scripts/collect.py` applies, each proven by a fixture under `scripts/fixtures/collect/` and asserted in `scripts/test-collect.py`. Rule numbers 1 to 6 carry over unchanged from the hand-run collector (version 2026-10-23) that this skill ports; rules 7 to 11 are new in this port, from spec Requirements 4 to 11.

## 1. Dedup: one usage per (message.id, requestId)

Claude Code repeats `message.usage` on every content-block record of a streamed response. Summing raw records overcounts tokens and cost. The collector keeps only the record with the largest output token count for each `(message.id, requestId)` pair, per file, and prices from that record alone.

**Fixture:** `fx-dedup.jsonl`, three records sharing one message id and request id. **Test:** `rule1 dedup` in `scripts/test-collect.py`.

## 2. Advisor iterations are separate model work

A response's `usage.iterations` can carry `type: "advisor_message"` entries alongside the executor's own `type: "message"` entries. The top-level usage already equals the sum of the executor iterations, so executor cost is unaffected; the advisor's tokens are priced at the advisor's own rate and tracked only in new fields (`cost_advisor`, `advisor_calls_dedup`), never folded into executor cost.

**Fixture:** `fx-advisor.jsonl`. **Test:** `rule2 advisor`.

## 3. Prices come from a dated file, never a guessed prefix

A model id prices against a price-file entry only if it equals that entry exactly, or equals the entry plus `-` plus a run of digits only (a dated snapshot such as `claude-haiku-4-5-20251001`). Among digit-suffix matches the longest (most specific) entry wins, so `claude-opus-5-5` matches itself exactly rather than falling through to `claude-opus-5`. An id matching nothing is never priced by guess: it contributes $0 to every dollar figure and is listed under `unpriced_models`.

**Fixtures:** `fx-unknown.jsonl` (no match), `fx-opus55.jsonl` (exact match beats a shorter prefix). **Tests:** `rule3 unknown model`, `rule4 opus-5-5 pricing`.

## 4. Cache writes price by their recorded TTL

A 1-hour cache write (`cache_creation.ephemeral_1h_input_tokens`) prices at 2x the input rate; a 5-minute write (`ephemeral_5m_input_tokens`) prices at 1.25x. When no TTL breakdown is recorded, `cache_creation_input_tokens` is treated as a 5-minute write (the cheaper assumption).

**Fixture:** `fx-cachewrite.jsonl`. **Test:** `rule5 1h cache write`.

## 5. Context depth is the largest executor iteration

For main-lane responses, depth is `input + cache_read + cache_creation` for the largest `type: "message"` iteration, never the top-level sum (which, for an advisor response, is roughly double the true depth, since it sums two executor turns either side of the advisor call).

**Fixture:** `fx-advisor.jsonl` (depth bin assertions in the same test block as rule 2). **Test:** `rule3 depth`.

## 6. A compaction counts only from a `compact_boundary` record

Only `type: "system", subtype: "compact_boundary"` records count a compaction. A paired `isCompactSummary` user record is skipped entirely: it is not a second compaction, and it is not scanned for interrupt text (a compaction summary can quote `[Request interrupted by user` from the conversation it is compacting).

**Fixture:** `fx-compaction.jsonl`. **Test:** `rule6 compaction`.

## 7. A copied transcript folder is counted once

A transcript folder that is a copy of another, holding the same session files (for example, after a repository rename), is counted once: the largest copy of each file, ties going to the first folder in sorted order. Every skipped copy is reported under `global.json`'s `copied_folders_skipped`.

**Fixture:** the main fixture tree, copied with `shutil.copytree` inside the test (there is no static fixture for this one, since the rule is about two folders holding identical files). **Test:** `AC-6 copy`.

## 8. A task notification is not a user prompt

A user record that is a background agent's completion notice, not text the owner typed, is detected by two structural markers (`turnOrigin == "task_notification"`, or `origin.kind == "task-notification"`), with a text-tag fallback (`<task-notification>` at the start of the record's text) for a record that for any reason carries neither structural field. A task notification is skipped before any of the other per-record checks (it is never scanned for interrupt text or negation) and is counted in `task_notifications_dedup`, not `n_user_prompts_dedup`.

**Fixture:** `tasknotice/fixture-project/fx-tasknotice.jsonl`, one typed prompt plus one structurally-marked notice and one text-tag-only notice. **Test:** `AC-7 task notice`.

## 9. Model drift

For each model family named in the price file's `families` list (newest model first), if the newest model has zero responses in the window while an older model of that family does, the family is listed in `global.json`'s `model_drift` and the collector exits 1. `families` states release order explicitly; the collector never infers it from the id string.

**Fixtures:** `drift-older/fixture-project/fx-drift.jsonl` (only the older id responds), `drift-newer/fixture-project/fx-drift.jsonl` (the newest id also responds). **Tests:** `AC-8 drift present`, `AC-8 drift absent`.

## 10. Per-half cost and response counts, no single half label

A session with responses in both halves of the window carries `cost_by_half` and `responses_by_half` (one entry per half it has data in), and no single `half` field: a session is not one half or the other, it has activity in each.

**Fixture:** `straddle/fixture-project/fx-straddle.jsonl`. **Test:** `AC-10 straddle`.

## 11. A missing child file is a finding

A subagent's `.meta.json` file with no sibling `.jsonl` transcript is listed in `global.json`'s `missing_child_files` and the collector exits 1. This is narrower than an unlinked `Agent`/`Task` tool call (common in real data, and not itself an error): it is a file the collector expected to find on disk and did not.

**Fixture:** `missingchild/fixture-project/fx-missingchild/subagents/agent-orphan.meta.json`, with no `agent-orphan.jsonl` beside it. **Test:** `missing child file`.

## Local days follow the configured IANA zone

Every timestamp is a UTC transcript time; the local day and hour it is attributed to come from `zoneinfo.ZoneInfo(tz)`, applying daylight saving per timestamp, never a fixed offset. Without `--tz` or a `timezone` setting, the machine's own zone is used (which still applies daylight saving).

**Fixture:** a synthetic response at `2026-11-02T06:30:00Z`, built inline in the test (not a static fixture file) because the point is the same instant read in two zones. **Test:** `AC-5 dst`.
