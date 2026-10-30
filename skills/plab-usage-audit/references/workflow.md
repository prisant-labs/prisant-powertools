# Agent stages

The agents a weekly run launches, their models, what each reads, and the prompt each receives. Launch every agent with the Agent tool (or the harness's equivalent) and an explicit model. Workflow scripts may run the same stages; the prompts and models do not change.

## Routing

| Stage | Agents | Model | Effort, where the harness takes one | Escalation |
|---|---|---|---|---|
| Log readers | 0 to 2 | sonnet | medium | A reader that returns fewer records than the logs it was given re-runs once on opus for the missing logs |
| Usage brief | 1 | sonnet | medium | A brief missing a required section re-runs once on opus |
| Scorecard brief | 1 | sonnet | high | The same |
| Config brief | 1 | sonnet | medium | The same |
| Verifier | 1 | sonnet | high | None: the main loop judges its findings |

At most eight agents plus the verifier per run (UA-01 D2). Record every agent in `data/agents.json` and in the `## Agents` table of `data/README.md`.

## The rules every agent receives

Paste this block, unchanged, at the top of every agent prompt.

```text
RULES FOR THIS TASK
1. CREDENTIAL FILES ARE OFF LIMITS. Never open, Read, cat, head, grep, search or filter these files in any way, not even to check key names: ~/.codex/config.toml, ~/.codex/auth.json, ~/.npmrc, ~/.claude/.credentials.json, any .env file, any file whose name contains "secret" or "token", and every file listed under credential_files in the owner's settings. Credential presence is already in audit-facts.json, by key name only.
2. Use only the files this prompt names. Do not search the disk for more.
3. Every number you write must come from a named file. Write the file name beside it. If a number is not in the files, write "not measured" instead of estimating.
4. Never claim the owner approved, chose, declined or decided anything unless you quote the record that says so and name its path. If you cannot find the record, write "no record found".
5. Say whether each count is de-duplicated (_dedup) or raw (_raw), using the field name.
6. Write plain sentences under 25 words. No em-dashes or en-dashes.
```

## Log readers

**Input:** a list of session-log paths for the window, at most 20 per reader.

**Prompt:** the rules block, then:

```text
Read each session log in this list and return one JSON object per log, one per line, with exactly these fields (PP-01 contract C3): file, repo, date, time, harness (claude or codex), model, nonstandard_name, summary, shipped (list), decisions (list of {text, recorded_in, by}), waiting_on_owner (list of {text, since or null}), next_action, tooling_friction (list of {what, tool, impact}), practice_lessons (list), global_setup_items (list), scale_notes (list). Empty lists are fine. Return exactly one object per log you were given, and nothing else. Do not quote passwords, tokens, keys or personal details that appear in a log.
LOGS:
<paths>
```

**Check:** the count of returned records equals the count of logs given; otherwise escalate once for the missing ones.

## Usage brief

**Reads:** `data/global.json`, `data/sessions.json`, `data/children.json`, `data/agent_calls.json`, `data/workflow_calls.json`, `data/projects.json`, `data/audit-facts.json`, and the previous bundle's `01` when the facts name one. `references/positioning.md` for what not to repeat.

**Prompt:** the rules block, then:

```text
Write the usage brief for the week <focus start> to <audit day>, against the prior week <prior start> to <prior end>, in Markdown with these sections:
## Totals by lane (main, subagent, workflow, advisor; both weeks; change in dollars and per day)
## Reconciliation (from audit-facts.json reconciliation: does last week's published total reproduce, and what explains the rest)
## Routing (frontier_share_delegated_executor against the 25% target; advisor_share_total on its own line)
## The model that ran (responses_dedup and cost by model id; every model_drift entry, and what it means)
## Workflows (count, agents, models, and any per-workflow cost gap from audit-facts.json)
## Context depth (the share of main-loop responses and cost at or above 400K tokens; compactions)
## Spend by project (top ten, both weeks)
## Friction (tool errors, permission denials, interrupts)
## Five headline findings (each one sentence, each with its file and a confidence of high, medium or low)
Do not restate what /usage, /insights or session-report already show live; report the weekly history and the changes.
```

## Scorecard brief

**Reads:** the previous bundle's `05-recommendations.md`, the configured decision sources (`decision_sources` in the settings), the change register, `data/audit-facts.json`, and `references/scorecard.md`.

**Prompt:** the rules block, then:

```text
Score every recommendation in the previous bundle's 05-recommendations.md, and every item in the decision sources due on or before <audit day>, using only the verdicts and evidence rule in references/scorecard.md. For each item give: id and handle, verdict, evidence (a path and line, a command and its output, or a ledger row), and asked_count (how many consecutive audits raised it; read it from the previous scorecard when present). Then list the overdue items, the pattern in what got decided and what stalled, and at most three asks for the owner. Return Markdown with sections: ## Scored items (a table), ## Overdue, ## Decision pattern, ## Asks.
```

## Config brief

**Reads:** `data/audit-facts.json` (versions, drift, credential presence by key name), the change register, the settings file named in the settings as `claude_settings` (read for keys and values other than secrets; never a credential file), and the upstream Claude Code changelog entries between the last and the installed version when the facts list them.

**Prompt:** the rules block, then:

```text
Write the config brief: ## Findings (a table: finding, severity high/medium/low, evidence, smallest fix), ## Settings drift (every changed key with no register row), ## Versions (installed against last audited, and the changelog entries between them that matter to this setup), ## Credentials (presence by key name and file date only, from audit-facts.json; never a value), ## Model pins (any env or settings key that pins a model alias, and whether model_drift shows its effect).
```

## Verifier

**Reads:** the written bundle, every file under `data/`, and the decision sources.

**Prompt:** the rules block, then:

```text
You are checking a finished audit bundle before the owner reads it. For every number in README.md and 01 to 05, find it in a data file and confirm it, or report it with the file and the correct value. For every claim that the owner approved, chose, declined or decided something, find the record, or report it as unsupported. Check that each count's basis (_dedup or _raw) is stated correctly. Check that no two places in the bundle give different values for the same measure. Return a table: location (file and section), claim, finding (confirmed / wrong / unsupported / inconsistent), correct value or record, source file. List only problems; end with the count of claims checked.
```

The main loop applies or rejects each finding. A rejected finding is listed under `## Verification` with the reason.
