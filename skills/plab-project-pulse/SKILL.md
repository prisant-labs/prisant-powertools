---
name: plab-project-pulse
description: "Roll up every repository under the owner's configured roots into one private weekly pulse: what shipped, what each project says is next, and what waits on the owner, ranked across projects with the age of each waiting item. Reads fresh /plab-current-status snapshots instead of re-scouting, carries dormant repositories forward, and writes pulse.json, a readout and a self-contained dashboard. For one repository in depth use /plab-current-status. Explicit invocation only: run /plab-project-pulse; it does not fire on its own."
argument-hint: "[--quick|--week] [--date YYYY-MM-DD] [--config <path>] [--digest <digest.jsonl>] [--out <dir>]"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.0.0"
  updated: 2026-10-30
---

# Project Pulse

Answer "where is everything?" across every repository the owner keeps: what shipped this week, what each project says is next, and which decisions wait on the owner and for how long. One script gathers every fact; agents read only the active repositories that have no fresh `plab-current-status` snapshot; a checker validates the output before it is reported.

"Where is this project?" is `/plab-current-status`. This skill reads that skill's snapshots and never writes one.

## Input

| Input | Default | Notes |
|-------|---------|-------|
| `--quick` or `--week` | `--week` | `--quick` launches no agent: facts, snapshots and carried entries only |
| `--date` | Today | The last day of the focus week, in the configured zone |
| `--config` | `.claude/plab-project-pulse.local.md` in the current repository | See `references/settings-example.md` |
| `--digest` | None | A session-log digest for the same window, from `plab-usage-audit`; no log reader runs |
| `--out` | The settings file's `output_dir` | The run writes `<out>/YYYY-MM-DD/` |

## Output

In `<out>/YYYY-MM-DD/`: `pulse-facts.json`, `digest.jsonl` (week mode), `scouts.json`, `curation.json`, `pulse.json`, `coverage.md`, `readout.md` and `dashboard.html`. The state file named in the settings is updated after validation. All of it is private; nothing is committed, pushed or published.

## Workflow

### 1. Resolve and place

Read the settings file; if it is missing, stop and show `references/settings-example.md`. Then:

```bash
python <this skill's base directory>/scripts/check-placement.py <run folder>
```

On exit 1, stop and ask for `--out`.

### 2. Gather the facts

```bash
python <this skill's base directory>/scripts/derive-pulse-facts.py --config <settings> --mode <quick|week> --end <date> --state <state> --out <run folder>/pulse-facts.json
```

Exit 2 stops the run with its named cause. Every gap it reports goes into `coverage.md`.

### 3. Read logs and scout (week mode only)

Follow `references/workflow.md`. With `--digest`, copy it to the run folder and launch no reader. Scout only the repositories with `to_scout: true`, grouped as the workflow says, and check every scout's returned count against its assignment. Write the scout returns to `scouts.json` in the shape of `references/pulse-schema.md`. Repositories with a fresh snapshot or a carried entry are never scouted.

### 4. Curate

Write `curation.json`: at most ten What's Next items across all repositories, ordered by what unblocks the most work, each with repository, who acts, why, and its source; one line per cross-repository pattern; and the agent routing table. Use the same meanings as `plab-current-status`: Waiting on You is what only the owner can do, What's Next is work an agent can do once unblocked.

### 5. Build, render and check

```bash
python <this skill's base directory>/scripts/build-pulse.py --facts <run>/pulse-facts.json --scouts <run>/scouts.json --curation <run>/curation.json --state <state> --out <run> [--digest <run>/digest.jsonl] [--spend <projects.json>]
python <this skill's base directory>/scripts/render.py --pulse <run>/pulse.json --out <run>/dashboard.html
python <this skill's base directory>/scripts/pulse-check.py <run>
```

On exit 1, fix each named failure and run again. The state file changes only when `build-pulse.py` validates. Exit 2 from the checker means the output is unverified: say so.

### 6. Write the readout

Write `readout.md`: The Answer in three sentences, What's Next, Waiting on You grouped by repository with ages, conflicts, unprotected work, and the active repositories listed as `current_status_candidate`, each with "run `/plab-current-status` there".

### 7. Reply

Give the run folder, The Answer, the three oldest waiting items, and the checker's result line. Offer `/plab-resolve-open-items` for the waiting decisions; do not start it.

## Constraints

- **Facts, not recall.** Repository state comes from `pulse-facts.json`. A scout reads only the documents its prompt names.
- **No repository is changed.** No fetch, pull, checkout, commit or branch deletion.
- **No agent opens a credential file.** The rules block in `references/workflow.md` goes into every agent prompt verbatim.
- **Every agent names a model.** Sonnet or Haiku by default; a short scout is re-run once on the next tier.
- **Git outranks documents, documents outrank logs.** A contradiction is kept as a conflict, quoting both.
- **Ids carry handles.** Never write a bare id; pair it with a short handle on first use.

## References

| File | Load when |
|------|-----------|
| `references/pulse-schema.md` | Steps 3 to 5 |
| `references/workflow.md` | Step 3 |
| `references/carry-forward.md` | When a dormant repository's entry looks old |
| `references/coverage-statement.md` | Step 5, when the checker fails on `coverage.md` |
| `references/settings-example.md` | Step 1, when the settings file is missing |
