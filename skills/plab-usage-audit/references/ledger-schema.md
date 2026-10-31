# Ledger schema 2

`scripts/ledger.py` appends, reads and reproduces rows in a JSONL ledger file: one JSON object per line, lines never rewritten, never deleted. Two row kinds share the file.

## `measurement` rows

Written by `scripts/collect.py --ledger <path>`, one row per period and population it measured.

| Field | Meaning |
|---|---|
| `schema_version` | `2` |
| `row_kind` | `"measurement"` |
| `row_id` | a deterministic id: a short hash of `row_kind`, `period_start`, `period_end`, `population` and the canonical JSON of `method`. Two rows with identical period, population and method always hash to the same id. |
| `period_start`, `period_end` | the calendar dates this row covers, in the configured zone |
| `population` | `"interactive"` or `"automated"` |
| `day_zone` | the IANA zone used to attribute local days |
| `method` | `{"cutoff", "excluded_sessions", "price_file_as_of", "collector_version"}`, Requirement 9's "full method". `excluded_sessions` is sorted, so method comparison is order-independent. |
| `measured_at` | the UTC instant this row was appended |
| `volume` | `{"sessions_dedup", "projects_dedup", "user_prompts_dedup", "task_notifications_dedup"}` |
| `cost` | `{"executor_cost_total", "advisor_cost_total", "cost_by_lane"}` |
| `responses_by_lane_dedup` | `{"main": n, "subagent": n, "workflow": n}` |
| `unpriced_responses_dedup` | count of responses from a model id not in the price file |
| `depth` | `{"share_responses_ge_400k", "share_cost_ge_400k", "share_responses_ge_500k"}` |
| `routing` | `{"frontier_share_delegated_executor", "advisor_share_total"}`, Requirement 15 (see below) |
| `friction` | `{"compactions_dedup", "sessions_compacting_dedup", "interrupts_dedup", "tool_errors_dedup", "perm_denials_dedup", "hook_blocks_dedup", "user_negations_dedup"}` |
| `output` | `{"agent_calls_no_model_dedup", "workflow_agents_no_model_dedup"}` |
| `plan_limit` | optional; `null` unless the owner supplied it (Requirement 16): `{"session_pct", "weekly_pct", "read_at"}` |

**The routing fields (Requirement 15).** `frontier_share_delegated_executor` is the frontier (opus or fable bucket) share of delegated (subagent plus workflow) EXECUTOR spend; the advisor is excluded from both the numerator and the denominator. `advisor_share_total` is the advisor's own share of all spend: advisor cost divided by (every lane's executor cost, plus the advisor's cost). These replace the hand-run collector's single `frontier_share_delegated_incl_advisor`, which mixed the two: Requirement 15 asks for the advisor's share on its own line instead of folded into the frontier ratio.

**Duplicate refusal.** `ledger.py append` refuses (exit 1, writes nothing) a measurement row whose `period_start`, `period_end`, `population` and `method` all match an existing measurement row exactly. A row that differs in any one of those (a different cutoff, a different exclusion list, a newer price file, a newer collector version) is a re-measure and is appended alongside the old one. `ledger.py latest` returns, for a given period and population, the measurement row with the newest `measured_at`.

## `audit_run` rows (Requirement 17)

One row per weekly run of the skill itself, recording what the run cost. Never deduplicated against another `audit_run` row or against a measurement row: a repeated run of the same week is expected, not an error.

| Field | Meaning |
|---|---|
| `schema_version` | `2` |
| `row_kind` | `"audit_run"` |
| `row_id` | a hash salted with `measured_at`, so repeated runs never collide |
| `period_start`, `period_end` | the week the run audited |
| `measured_at` | when the run finished |
| `run` | `{"agents", "models", "tokens", "dollars", "minutes"}`; `dollars` is `null` when not known |

## The mapping file (Requirement 14)

A ledger written before schema 2 existed carries `window_start`, `window_end`, `half` and `population` instead of `period_start` and `period_end`, and has no way to recover the missing `focus_start` that would let a reader compute them. An owner-supplied mapping file fills them in at read time, without rewriting the ledger:

```json
{
  "{\"half\": \"focus\", \"population\": \"interactive\", \"window_end\": \"2026-10-30\", \"window_start\": \"2026-10-17\"}":
    {"period_start": "2026-10-24", "period_end": "2026-10-30"}
}
```

Each key is `json.dumps({"window_start", "window_end", "half", "population"}, sort_keys=True)` from the old row (see `ledger.legacy_key`); each value names the period that half actually covered. `ledger.py latest --mapping <path>` applies it only to a row that is missing `period_start` or `period_end`; a row that already carries them is read as-is. The mapping file is the owner's own data and never ships with the skill.

## `--reproduce` (Requirement 10)

`collect.py --reproduce <row_id> --ledger <path>` looks up the row, re-runs the collection with its recorded `period_start`, `period_end`, `cutoff` and `excluded_sessions`, against the CURRENT price file (never the row's own, so a price change is exactly what this detects), and compares `executor_cost_total + advisor_cost_total` between the two. Within one dollar: exit 0. Otherwise: exit 1, naming the price file when its `as_of` differs from the row's recorded one, and naming the cutoff or the exclusions only when the invocation explicitly overrode them with `--cutoff` or `--exclude-session` (otherwise both are taken verbatim from the row, so they cannot differ on their own). The settings a reproduction run needs beyond the method (the time zone, the transcript root, the settings file) are not part of `method` and must still be supplied on the command line or via `--config`; a reproduction attempted from a different machine or a different settings file is reproducing the method, not the whole environment.
