# Collector output

Every file `scripts/collect.py` writes to `--out`, every field in it, and the settings file that supplies the owner-specific values the shipped code never carries.

## The suffix rule (Requirement 6)

Every field whose value is a count of responses or records ends `_dedup` (counted after the de-duplication of accounting rule 1: one usage per message id and request id) or `_raw` (counted before it, so inflated by streamed content-block repeats). Three kinds of key are not checked against this rule, because their value is not a response or record count:

1. **Token sums and character counts**, named exactly: `input`, `output`, `output_tokens`, `cache_read`, `cache_creation`, `thinking_chars`, `prompt_chars`, `script_chars`, plus any key starting `out_` (`out_main`, `out_subagent`, `out_workflow` in `projects.json`). Identifiers and indices: `spawnDepth`, `schema_version`, `promptIndex`, `turnIndex`. A day count rather than a response count: `active_days`. This exact set is `collect.py`'s `COUNT_SUFFIX_EXEMPT_KEYS` and `COUNT_SUFFIX_EXEMPT_PREFIXES`; `scripts/test-collect.py`'s AC-9 check imports the same constants, so the rule and its test cannot drift apart.
2. **A data-keyed container's own keys**: a dict keyed by a model id, a tool name, a skill name, a day, an hour, a lane name, or a half name is not itself a schema field, so its keys are not checked (though a nested dict's own fields still are). Examples: `model_ids_raw`, `unpriced_models`, `skills`, `commands`, `tools`, `mcp`, `modes`, `main_models`, `agent_req_model`, `agent_types`, `workflow_agent_req_models`, `sessionKinds`, `entrypoints`, `versions`, `errors_by_tool`, `daily`, `hourly`, `cost_by_bucket`, `req_models`, `model_report`, `copied_folders_skipped`, `cost_by_half`, `responses_by_half`, `models` (inside a child record), `error_samples`, `model_drift`, `older_with_responses_dedup`.
3. **A field nested directly under a container already named `raw`, `dedup`, or ending `_dedup` / `_raw`** inherits that basis from its parent and does not repeat the suffix (for example `lanes.<lane>.<bucket>.dedup.msgs`, or `child_files_dedup.subagent`).

## `global.json`

| Field | Meaning |
|---|---|
| `window` | `[start, end]` as given |
| `focus_start` | the start of the focus half |
| `collector_version` | `COLLECTOR_VERSION` |
| `price_file_as_of` | the price file's `as_of` date |
| `day_zone` | the IANA zone timestamps were attributed in |
| `copied_folders_skipped` | `"<skipped folder> -> <kept folder>": <files skipped>`, accounting rule 7 |
| `missing_child_files` | paths of `.meta.json` files with no sibling `.jsonl`, accounting rule 11 |
| `halves.<prior\|focus>.<interactive\|automated>` | the aggregate block below, per half and population |
| `daily` | `"YYYY-MM-DD": {"<lane>:<bucket>": cost}` |
| `hourly` | `"<half>:<HH>": cost` |
| `model_ids_raw` | model id to raw (pre-dedup) line count |
| `model_report` | `"<model id>\|<lane>": {"responses_dedup", "cost_dedup"}`, Requirement 5 |
| `model_drift` | `"<family>": {"newest", "responses_newest_dedup", "older_with_responses_dedup"}`, accounting rule 9 |
| `unpriced_models` | model id to `{"responses_dedup", "input", "output", "cache_read", "cache_creation"}` |
| `depth.<prior\|focus>` | the depth block below, interactive population only, or `null` if that half has no data |

**The aggregate block** (`halves.<half>.<population>`): `sessions_dedup`, `projects_dedup`, `user_prompts_dedup`, `task_notifications_dedup`, `lanes` (per lane and model bucket, `{"raw": {...}, "dedup": {...}}` cells with `msgs`, `cost`, `input`, `output`, `cache_read`, `cache_creation`), `advisor_by_lane` (`{"cost_dedup", "calls_dedup"}` per lane), `cost_advisor`, `advisor_calls_dedup`, `skills`, `commands`, `tools`, `mcp`, `modes`, `main_models` (all tallies), `agent_calls_dedup`, `agent_req_model`, `agent_types`, `agent_inherit_on_frontier_dedup`, `agent_background_dedup`, `workflow_calls_dedup`, `workflow_agents_dedup`, `workflow_agent_req_models`, `child_files_dedup`, `waste` (`tool_errors_dedup`, `perm_denials_dedup`, `hook_blocks_dedup`, `user_negations_dedup`, `compactions_dedup`, `interrupts_dedup`), `sessions_compacting_dedup`, `errors_by_tool`, `sessionKinds`, `entrypoints`, `versions`.

**The depth block**: `bins` (one of the seven `DEPTH_BIN_ORDER` width buckets to `{"responses_dedup", "cost"}`), `n_responses_dedup`, `total_cost`, `share_responses_ge_400k`, `share_cost_ge_400k`, `share_responses_ge_500k`.

## `sessions.json`

One row per session: `sessionId`, `project`, `display`, `population`, `dir_noise`, `sessionKind`, `entrypoint`, `version`, `title`, `first_ts`, `last_ts`, `n_user_prompts_dedup`, `n_responses_dedup`, `cost`, `cost_advisor`, `advisor_calls_dedup`, `cost_by_bucket`, `cost_by_half`, `responses_by_half` (Requirement 7: no `half` field), `output_tokens`, `skills`, `commands`, `mcp`, `modes`, `main_models`, `tool_errors_dedup`, `perm_denials_dedup`, `hook_blocks_dedup`, `hook_block_samples`, `user_negations_dedup`, `compactions_dedup`, `interrupts_dedup`, `task_notifications_dedup`, `thinking_chars`, `errors_by_tool`, `error_samples`, `n_agent_calls_dedup`, `n_workflow_calls_dedup`.

## `children.json`

One row per subagent or workflow-step transcript: `project`, `display`, `parent`, `lane`, `wf_id`, `file`, `population`, `agentType`, `req_model`, `description`, `toolUseId`, `spawnDepth`, `cost`, `cost_advisor`, `advisor_calls_dedup`, `output_tokens`, `n_responses_dedup`, `models`, `cost_by_bucket`. (No `half`; a child file belongs to the half its own responses fall in, read from `responses_by_half`-equivalent data if ever needed; today's consumers key off the parent session.)

## `agent_calls.json`

One row per `Agent`/`Task` tool call: the fields `scan_session` records (`tool_use_id`, `day`, `subagent_type`, `req_model`, `session_model`, `description`, `prompt_chars`, `background`, `isolation`), plus `sessionId`, `project`, `display`, `population`, `half`, `linked`, and, when a child transcript links to it, `child_cost`, `child_output`, `child_responses_dedup`, `child_bucket`, `child_agentType`.

## `workflow_calls.json`

One row per `Workflow` tool call: `tool_use_id`, `day`, `name`, `script_chars`, `wf_id`, `session_model`, `sessionId`, `project`, `display`, `population`, `half`, `n_agents_dedup`, `cost`, `cost_by_bucket`, `req_models`.

## `projects.json`

One row per project, half and population, sorted by `cost_total` descending: `project`, `display`, `half`, `population`, `n_sessions_dedup`, `user_prompts_dedup`, `active_days`, `agent_calls_dedup`, `workflow_calls_dedup`, `skills`, `waste` (five `_dedup` fields), `cost_main`, `cost_subagent`, `cost_workflow`, `cost_main_<bucket>` and similarly per lane and bucket, `out_main`, `out_subagent`, `out_workflow`, `cost_total`.

## The settings file (Requirement 8)

`--config <path>` points at a Markdown file with YAML frontmatter, conventionally `.claude/plab-usage-audit.local.md`. See `scripts/settings.py` for the exact (small) YAML subset it parses. The keys the collector reads:

| Key | Shape | Meaning |
|---|---|---|
| `timezone` | scalar | the IANA zone local days are counted in; `--tz` overrides it |
| `transcript_root` | scalar | the base folder holding one subfolder per Claude Code project; `--base` overrides it |
| `noise_patterns` | list of strings | a case-insensitive substring match against a project folder's name marks every session in it `automated` rather than `interactive` |
| `aliases` | one-level mapping | a project folder's lowercased name, after the generic drive-letter strip, has its longest matching key replaced by that key's value |

None of these four keys has a built-in value in the shipped code: a run with no `--config` and no matching CLI flag gets no noise patterns, no aliases, and the machine's own time zone and the generic default transcript root (`~/.claude/projects`).
