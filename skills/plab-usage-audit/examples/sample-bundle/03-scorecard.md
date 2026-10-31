# Scorecard - 2026-10-19 to 2026-10-25

## Previous recommendations scored

| ID (handle) | Verdict | Evidence |
|---|---|---|
| Y3 (routing-haiku-scouts) | Done | `data/collector-output.json` shows haiku's scout share rose from 4 percent to 19 percent in the week after the change |
| Y4 (advisor-before-write) | Done | all 14 advisor calls this week were pre-write calls, matching the rule added in the Y4 write-up |
| Y5 (backup-health-line) | Partial | the backup check script exists and runs, but `04-config.md` reports it has not been wired into this bundle's own config section yet |
| Y6 (drop-weekly-manual-prompts) | Not done | the owner still typed the brief prompts by hand for three of the last four weeks, which is exactly what this skill replaces starting this week |
| Y7 (gitignore-session-logs) | Overtaken | superseded by the global rule in the maintainer's own configuration, which now covers every repository at once |
| Y8 (pin-sonnet-alias) | Decided not applied | the owner decided not to pin the alias yet, recorded in `docs/internal/decisions/sonnet-alias.md`, preferring to watch one more drift cycle first |

## Decision records consulted

`docs/internal/decisions/sonnet-alias.md` and `docs/internal/decisions/haiku-scout-routing.md` were both read in full. No decision record exists yet for the backup-health wiring in Y5, which is noted here as absent rather than silently skipped.

## Due and overdue open items

Y6 (drop-weekly-manual-prompts) has now been raised in 4 consecutive audits without being closed; this is the fourth. Y5 (backup-health-line) has been raised in 2 consecutive audits.

## The decision pattern

Of the six items scored this week, the two carried by a rule or a skill (Y3, Y4) are Done. The one carried by nothing but intent to remember (Y6) is Not done after four audits. This matches the pattern recorded across every prior audit: a mechanism sticks, a habit mostly does not.

## The owner's own decision, named

The owner decided not to apply Y8 this cycle; that decision is recorded at `docs/internal/decisions/sonnet-alias.md` and is not a finding against this week's bundle, only a fact carried forward into A1 below.

## The smallest set of asks

Given the pattern above, this week's asks are narrowed to the one item that needs an actual owner decision (A1, which restates Y8 with a week's more drift evidence) and the one item that needs an agent fix with no owner input (A2). B1 and B2 are agent-executable once a yes is given.
