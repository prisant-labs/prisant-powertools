# Frontmatter Schema Reference

The session log YAML frontmatter has 3 tiers. Always include Tier 1. Add Tier 2 and Tier 3 when the data is available.

---

## Tier 1: Essential (Always Include)

This file is the one list of session-log fields. Every other copy of the list (wrap `SKILL.md`'s Frontmatter block, the template's three frontmatter blocks, `check-log.py`'s Tier 1 lists, and the fields `lib/session-logs.py` and continue's `reconcile.py` read) is checked against these tables by `scripts/test-check-log.py`, which CI runs. Change a field here first.

Where a field's "How to Derive" cell names `derive-log-facts.py`, the script is the one statement of how the value is found; copy the value from the script's `Frontmatter fields` output and do not re-derive it. `check-log.py` fails a log that is missing any Tier 1 field.

| Field | Type | How to Derive | Example |
|-------|------|--------------|---------|
| `date` | ISO 8601 datetime | `derive-log-facts.py`; the wrap's time, never the session's start | `2026-04-05T14:30:00-07:00` |
| `type` | const | Constant, always `session-log`; the agent writes it | `session-log` |
| `machine` | String | `derive-log-facts.py`; which checkout wrote this log, because logs are machine-local | `dev-laptop` |
| `repo` | String | `derive-log-facts.py` | `acme/example-repo` |
| `branch` | String | `derive-log-facts.py` | `main` |
| `summary` | String (≤120 chars) | Agent generates from session context | `"Deployed strategy-brief skill and CI pipeline"` |
| `files-changed` | List of paths | `derive-log-facts.py`; copy the whole list verbatim | `["skills/plab-strategy-brief/SKILL.md"]` |
| `commit-range` | String | `derive-log-facts.py`; the `base..HEAD` short-SHA range it diffed | `a1b2c3d..e4f5a6b` |
| `latest-tag` | String or null | `derive-log-facts.py`; the nearest release tag, never a merge-check backup tag. Distinct from the Tier 3 `tags:` topic-keyword field below | `v0.6.0` |

`commit-range` and `latest-tag` were added in 1.8.0 (W-02, derived log facts). Neither collides with the Tier 3 `commit-sha` (a single SHA) or `tags` (topic keywords) fields. The agent writes `summary` and the constant `type`; the script produces the other seven.

## Tier 2: High Value (When Available)

| Field | Type | How to Derive | Auto? |
|-------|------|--------------|-------|
| `session-type` | Enum | Agent assesses from work done | Semi - suggest, user overrides |
| `parent-session` | Filename | Most recent session log in same repo/branch | Semi - suggest if found |
| `model` | String | Full model name (e.g., "claude opus 4.6", "codex gpt 5.4") | Auto |
| `model-settings` | String | Key settings active during session (e.g., "extended-thinking max", "fast mode") | Auto when detectable |
| `agent` | Enum | Environment detection (claude-code, codex-cli, etc.) | Auto |
| `status` | Enum | How session ended | Semi - agent assesses |
| `decisions-count` | Integer | Count from decisions section | Auto |
| `skills-used` | List | Skills invoked during the session (usage telemetry; feeds pruning decisions) | Semi - agent recalls, user corrects |
| `resumed-from` | Filename | The session log this session resumed from via /plab-continue-session, if any (measures log consumption) | Auto when resumption happened |
| `resumed-from-outcome` | Enum | What happened to the resumed log's named next action: `fulfilled`, `superseded` or `ignored`. Written only with `resumed-from` | Semi - agent judges |
| `session-id` | String | This session's id, from `derive-log-facts.py`, which reads `CLAUDE_CODE_SESSION_ID`. Omitted when the script reports null, as under Codex | Auto |
| `session-start` | ISO 8601 datetime, UTC | When this session began: the first timestamp in its transcript, from `derive-log-facts.py`. Omitted when the script reports null | Auto |
| `carried-from` | Filename | The log this wrap carried Waiting on You and Parked items from: the script's `carry-forward` log | Auto when the script names one |

### `resumed-from` semantics

Written only when `/plab-continue-session` performed the resume in the current session. Never
back-fill this field from narrative memory of a resume that happened in some prior session; if no
resume occurred this session, omit the field entirely rather than guessing. Cross-repo lineage, when
it matters, belongs in the Summary section's prose, not in this field: continue already refuses
cross-repo resumption, so a value this field ever holds is always a same-repo filename.

### `resumed-from-outcome` semantics

Records whether the resumed log's named next action survived this session. Written only when `resumed-from` is, and into this log only, never into the log `resumed-from` names. Exactly one of three values:

- `fulfilled`: the resumed log's named next action was completed.
- `superseded`: circumstances changed, and the plan was correctly abandoned.
- `ignored`: the session re-derived context and went on without engaging the named action.

A mixed session takes the closest of the three; there is no fourth value. `ignored` is the value that matters most, because a run of them says the handoffs are not being used. `check-log.py` reports a finding when `resumed-from` appears without this field, when this field appears without `resumed-from`, or when its value is not one of the three. Nothing else reads the field: no digest or report is built on it. Added in 1.12.0 (C-04, consumption disposition).

### `carried-from` semantics

Records which log this wrap copied Waiting on You and Parked items from. The value is copied from `derive-log-facts.py`'s `carry-forward` line, never chosen by the agent: it is the log this session resumed from, or else the newest log in the store. Continue treats a log named here as consumed only when this session started after that log was written, so a carry from a session that ran in parallel leaves that session's handoff visible. Cite it by file name only, like `resumed-from`. It differs from `parent-session`, which is a suggested lineage hint: `carried-from` records what was actually carried.

### `session-id` and `session-start` semantics

Both come from `derive-log-facts.py` and are omitted when it reports null. Together they tell continue which logs one session wrote and when that session began, so two wraps of one session collapse to one candidate, and a log another session wrote while this one ran is recognized as parallel work. `session-start` is the session's start, not the wrap's: the wrap's time is in `date:` and in the file name. Since 1.11.1, `check-log.py` reports a finding when `date` is not later than `session-start`, or when the file name's time is earlier than the `carried-from` log's, because either means the session's start was used where the wrap's time belongs.

### Session Types

`bugfix` | `feature` | `refactor` | `research` | `planning` | `review` | `docs` | `autonomous` | `exploration`

### Status Values

`completed` | `interrupted` | `blocked` | `in-progress`

## Tier 3: Nice to Have (When Applicable)

| Field | Type | How to Derive |
|-------|------|--------------|
| `duration-minutes` | Integer | Estimate from session context |
| `tokens-used` | Integer | From `/cost` or `/usage` if available |
| `commit-sha` | String | `git rev-parse --short HEAD` |
| `tags` | List | Agent suggests from session topics |
| `related-issues` | List | Agent detects issue references |
| `transcript-path` | String | Platform-specific transcript location |
| `adrs-created` | List of filenames | ADRs created this session (e.g., `[0008-centralize-session-logs.md, 0009-adopt-madr.md]`) |

## Example Frontmatter

The frontmatter a wrap writes is wrap `SKILL.md`'s Frontmatter block, filled in from `derive-log-facts.py`'s `Frontmatter fields` output. There is deliberately no second hand-kept example here: the one this section carried until 1.12.0 had drifted to omit four of the nine Tier 1 fields.

## Filename Convention

Session logs are written to a centralized directory:

```
_local/_session-logs/YYYY-MM-DD_HH-MM_<llm>_<brief-kebab-title>.md
```

| Component | Format | Example |
|-----------|--------|---------|
| Date | `YYYY-MM-DD` | `2026-04-08` |
| Time | `HH-MM` (24h), the local time the wrap ran, not the time the session started; see `session-start` | `09-36` |
| LLM | Short name | `claude`, `codex`, `gpt`, `gemini` |
| Title | kebab-case | `deploy-ai-review` |

The time is the wrap's, so a log written days after its session began still carries the day it was written, and the newest handoff always sorts first. `session-start` records when the session began.

All agents write to the same `_local/_session-logs/` directory. In a linked git worktree, that is the main checkout's directory, which `derive-log-facts.py` reports as the store. The LLM short name in the filename identifies who did the work. Full model details (name, version, settings) go in the frontmatter, not the filename.

## Citing another session log

Reference other logs **by filename only**, never by directory-qualified path. This applies to `resumed-from:`, to evidence tables, and to prose anywhere in the log.

- Correct: `2026-08-17_22-15_claude_migration-complete-t3-and-cutover.md`
- Wrong: `_local/_session-logs/2026-08-17_22-15_claude_migration-complete-t3-and-cutover.md`

The filename is the log's identity: unique, sortable, and stable. The directory is storage, and `/plab-wrap-session --organize` moves logs into `YYYY-MM/` folders once their month closes. A path-qualified reference breaks on that move; a filename never does.

This is why archiving needs no link-rewriting step, and therefore has no link-rewriting bugs. The durable fix for a reference a move can break is not to rewrite it on move, but to stop writing it that way.

## Field Dependencies

These Tier 1 fields are load-bearing for future hook matching (SessionStart injection):

- `date` - determines recency
- `repo` - prevents cross-repo contamination
- `branch` - scopes to current work stream

Getting these three right is more important than including all Tier 3 fields.
