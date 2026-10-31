# Usage - 2026-10-19 to 2026-10-25

## Spend by lane

The main loop spent $86.40 this week, the advisor spent $21.10 across 14 invocations, and subagent workers spent $34.80, for a total of $142.30. Last week's total was $118.90, so spend rose 19.7 percent, mostly from the `alpha-app` release-plan work described below.

## Reconciliation

This week's re-run of last week's cutoff reproduces last week's published total of $118.90 exactly, which confirms the collector's dedup logic held across the week boundary. The sum of this week's per-workflow costs is $139.20 against a workflow lane total of $142.30, a gap of $3.10, inside the configured tolerance of $5.00 and attributed to two short ad hoc sessions that ran outside any named workflow.

## Advisor

The advisor ran 14 times this week at an average of $1.51 per call, against 11 calls and $1.38 per call last week. All 14 calls were invoked before substantive work, per the standing rule; none were post-hoc justification calls.

## Workflows

Two workflows ran: `release-plan-build` (6 runs, $61.20) on `alpha-app`, and `audit-skill-scaffold` (3 runs, $78.00) on this plugin itself. Both stayed within one standard deviation of their trailing four-week average cost.

## Depth

The main loop's average iteration depth was 3.2 turns before handing off to a subagent, down from 4.1 last week, consistent with the routing rule change recorded in `03-scorecard.md` as A1 from two audits ago.

## Automated population

`collect.py` populated every field in `data/collector-output.json` from the transcripts directly; no field in this section was typed in by hand, which was not true for any of the ten hand-run audits before this skill existed.

## Routing

73 percent of subagent turns ran on `sonnet`, 19 percent on `haiku`, and 8 percent on `opus`, against a target of keeping frontier share under 25 percent. The 8 percent opus share is entirely the verifier stage described in `data/README.md`.

## The model that ran

Every response in the window carries the model id that actually answered, not the alias requested. One finding follows from this: `04-config.md` reports that the `sonnet` alias is pinned to an id one release behind the family's current model, which this section's routing numbers already reflect correctly because they are read from the response records, not from the alias.

## Friction

Two sessions hit a permission prompt for a `gh pr create` call that the allowlist should already cover; `04-config.md` traces this to a settings key that was reverted during a merge on 2026-10-21 and never restored.

## Spend by project

`alpha-app` cost $97.10 this week (release-plan build and two bug-fix sessions). `beta-lib` cost $16.90 (a dependency bump and its test-suite repair). The remaining $28.30 is this plugin's own scaffolding work, which is unassigned to either project.
