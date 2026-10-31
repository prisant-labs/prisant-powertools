---
name: plab-usage-audit
description: "Run the owner's weekly audit of their own Claude Code usage and write a dated, scrubbed bundle: spend by lane and by the model that actually ran, routing against the owner's rules, a reconciliation of last week, a scorecard of past recommendations, configuration drift, lessons from session logs, and ranked recommendations, each fact-checked by a verifier. Goes beyond /usage, /insights and session-report by keeping weekly history and checking whether past changes worked. Use when the owner runs /plab-usage-audit for the weekly review; it never fires on its own."
argument-hint: "[--date YYYY-MM-DD] [--config <path>] [--digest <digest.jsonl>] [--out <dir>]"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.0.0"
  updated: 2026-10-30
---

# Usage Audit

Measure one week of the owner's Claude Code usage against the week before, check whether last week's recommendations happened, and write the few changes worth making next, each with evidence the owner can check. Every number comes from a script; every agent names a model; a verifier checks the bundle before it is reported done.

## Input

| Input | Default | Notes |
|-------|---------|-------|
| `--date` | Today | The audit day. The focus week is the seven local days ending on it; the prior week is the seven before |
| `--config` | `.claude/plab-usage-audit.local.md` in the current repository | The owner's settings; see `references/settings-example.md` |
| `--digest` | None | A session-log digest from `plab-project-pulse` for the same window; the practice lane then reads no log |
| `--out` | The settings file's `output_dir` | The parent folder; the bundle is `<out>/YYYY-MM-DD_claude-usage/` |

## Output

One bundle folder in the format of `references/bundle-format.md`, new rows in the owner's ledger, and an updated state file. Nothing is committed, pushed or published.

## Workflow

`references/workflow.md` holds the agent stages, their models and their prompts. Read it before step 5.

### 1. Resolve and place

Read the settings file. If it is missing, stop and show `references/settings-example.md`. Compute the windows in the configured zone, and the cutoff: 09:00 local time on the audit day, converted to UTC, unless the settings set `cutoff_local`. Then run:

```bash
python <this skill's base directory>/scripts/check-placement.py <bundle folder> [--allow-tracked]
```

Pass `--allow-tracked` only when the settings set `allow_tracked_output: true`. On exit 1, stop and ask for `--out`.

### 2. Ask for plan limits once

Ask the owner one question: "What do `/usage`'s session and weekly plan-limit bars read right now? Reply with two percentages, or skip." Record the answer and the time for step 9. A skipped answer is named in `data/README.md` under Not measured.

### 3. Collect and gather the facts

```bash
python <this skill's base directory>/scripts/collect.py --config <settings> --start <prior start> --end <audit day> --focus-start <focus start> --cutoff <cutoff UTC> --out <bundle>/data --ledger <ledger>
python <this skill's base directory>/scripts/derive-audit-facts.py --config <settings> --data <bundle>/data --ledger <ledger> --state <state> --out <bundle>/data/audit-facts.json
python <this skill's base directory>/scripts/shipped.py --config <settings> --start <focus start> --end <audit day> --prior-start <prior start> --out <bundle>/data/sweep.json
```

When a `plab-project-pulse` run already covered the same week, pass `--pulse-facts <its pulse-facts.json>` to `shipped.py` instead of the window, and it runs no git command.

The collector exits 1 on findings such as an unpriced model or model drift: carry those into the bundle; they are findings, not failures. Exit 2 from any script stops the run with its named cause. Never write a figure the scripts did not produce.

### 4. The practice lane

With `--digest`, copy the digest to `<bundle>/data/digest.jsonl` and launch no reader. Otherwise launch the log readers in `references/workflow.md` over the session logs in the window, at most two, and write their records to `<bundle>/data/digest.jsonl`. If `audit-facts.json` names a `/insights` report newer than the previous audit, the usage brief reads its feature suggestions.

### 5. The briefs

Launch the three brief workers in `references/workflow.md` in parallel: usage, scorecard and config. Each gets only the files its prompt names. Save each return to `<bundle>/data/briefs/`.

### 6. Write the bundle

Write `README.md` and `01` to `05` from the briefs and the data, in the format of `references/bundle-format.md`. Correct a brief wherever the data disagrees, and note each correction for step 7. Remove any claim that the owner approved, chose or declined something unless it quotes the record (`references/scorecard.md`). Take recommendation ids from `audit-facts.json`'s `next_series_letter`. Write `data/README.md` with every required heading except `## Verification`.

### 7. Verify

Launch the verifier in `references/workflow.md`. Apply or reject each finding with a reason, then write `## Verification` in `data/README.md`, listing the brief corrections from step 6 and the verifier's findings. The bundle is not done before this section exists.

### 8. Scrub and check

```bash
python <this skill's base directory>/scripts/scrub.py <bundle> --private-pattern <each private pattern>
python <this skill's base directory>/scripts/bundle-check.py <bundle> --private-pattern <each private pattern>
```

On exit 1, fix each named failure and run both again. Exit 2 means the bundle is broken: report it as unverified, never as checked.

### 9. Record the run

Append the `audit_run` row, with the plan-limit answer from step 2, and advance the state:

```bash
python <this skill's base directory>/scripts/ledger.py append-run --ledger <ledger> --date <audit day> --agents <bundle>/data/agents.json [--plan-session <pct> --plan-weekly <pct> --plan-read-at <UTC>]
python <this skill's base directory>/scripts/derive-audit-facts.py --config <settings> --state <state> --commit-state --facts <bundle>/data/audit-facts.json
```

`agents.json` is the routing table of step 5 to 7 as JSON: one object per agent with `stage`, `label`, `model`, `assigned`, `returned`, `escalated`, and tokens and minutes when known.

### 10. Reply

Give the bundle path, its five-minute version, the recommendations that need the owner, and the checker's result line. Offer `/plab-resolve-open-items` for the asks; do not start it.

## Constraints

- **Facts, not recall.** Every number comes from the collector, the facts script or the sweep. A number they did not produce is not written.
- **No agent opens a credential file.** The rule in `references/workflow.md` goes into every agent prompt verbatim. Only `derive-audit-facts.py` touches credential files, and only for key names and dates.
- **Every agent names a model.** Sonnet or Haiku by default, none Opus. A short return is re-run once on the next tier with the failure described.
- **Approvals carry their record.** A claim that the owner decided something quotes or links where.
- **The skill never commits, pushes or publishes.**
- **Ids carry handles.** Never write a bare id such as `A3` or `O-08`; pair it with a short handle on first use.

## References

| File | Load when |
|------|-----------|
| `references/workflow.md` | Steps 4, 5 and 7 |
| `references/bundle-format.md` | Step 6 |
| `references/scorecard.md` | Step 5, for the scorecard brief, and step 6 |
| `references/positioning.md` | Step 6, for `01` and `04`, and when the owner asks how this differs from the native tools |
| `references/collector-output.md` | Steps 5 and 6, to read the data |
| `references/ledger-schema.md` | Step 9, and when reading trends |
| `references/accounting-rules.md` | When a number looks wrong |
| `references/settings-example.md` | Step 1, when the settings file is missing |
