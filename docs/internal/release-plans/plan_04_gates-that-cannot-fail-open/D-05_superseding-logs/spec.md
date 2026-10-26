---
id: D-05
title: Declare and archive same-arc superseding session logs
type: spec
status: fulfilled
created: 2026-08-23
updated: 2026-10-26
linked-effort: the maintainer's private defect record for the wrap/continue pair, 2026-08-18
linked-plan: implementation-plan.md
ac-count: 7
source-count: 6
requires-human-review: true
target-release: v0.4.0
linked-release: docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md
priority: P2
---

# Spec: Declare and archive same-arc superseding session logs

## Task Summary

Status: Fulfilled
Last updated: 2026-08-24
Linked plan: implementation-plan.md
Open questions: 3 (see Open Questions / Decisions)
Revisions: 1 (see Revisions)

### Acceptance Criteria Fulfillment

- [x] AC-1: Same-arc judgment produces a supersession sentence in the new log's Summary
- [x] AC-2: Same-arc judgment produces exactly one archive proposal
- [x] AC-3: Confirmed proposal relocates the older file to `_superseded/`
- [x] AC-4: Declined or unanswered proposal is recorded in the same Summary sentence
- [x] AC-5: No judgment means no sentence and no proposal
- [x] AC-6: `log-discovery.md` documents `_superseded/` as excluded, with no pipeline change
- [x] AC-7: No `supersedes:` frontmatter field exists anywhere in the schema

### Currently In Progress

None.

## Purpose

D-05 (superseding logs) gives `plab-wrap-session` a same-arc supersession check: when the newest
existing session log covers the same work as the session being wrapped, the new log declares the
supersession in prose and wrap proposes, under per-action confirmation, archiving the older file to
`_local/_session-logs/_superseded/`. This closes the gap that let two real logs five hours apart on
2026-08-17 diverge on `decisions-count` (7 versus 9) and `files-changed` while covering one arc,
without adding a `supersedes:` frontmatter field that would have no consumer today. D-05 is the
roadmap's D-5.

## Scope

### In Scope

- A wrap-time same-arc judgment against the newest existing log, in deep and final modes.
- A prose declaration of supersession, appended to the new log's Summary section.
- Exactly one per-action-confirmed proposal to archive the older log to
  `_local/_session-logs/_superseded/`.
- Recording the disposition (archived, or not archived) in that same Summary sentence.
- Documenting `_local/_session-logs/_superseded/` in `references/log-discovery.md` as a directory the
  existing discovery allowlist already excludes.
- Version bump and `HISTORY.md` entries for `plab-wrap-session` (the content owner) and
  `plab-continue-session` (a documentation-only touch to `log-discovery.md`).

### Non-Goals

- No `supersedes:` frontmatter field, or any equivalently named field. Rejected in the source as a
  producer with zero consumers, the same defect shape as D-04 (capture-lite consumers).
- No automatic archiving without per-action confirmation.
- No new hygiene-sweep check. `hygiene-sweep.md`'s own "five checks" count is unchanged; this
  mechanism lives in Evidence Gathering, not the sweep (see Requirement 3 for why).
- No script backing the archive move. It is a single, agent-executed, confirmed file relocation
  (mechanization-ladder rung 3, documented convention), not a rung-2 committed script.
- No deletion, ever, of any file.
- No merging or reconciling the two logs' differing content. The newer log stands as written; the
  older is archived unmodified, not rewritten.
- Quick and blocked mode wraps do not run this check ([model-inference]; see Open Questions, OQ2).
- Does not implement D-07 (the Waiting-on blocker contract)'s own "read the previous log" carry-forward
  behavior. D-07 is a separate v0.4.0 effort; see Open Questions, OQ1, for the overlap between the two.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer (JP) | Confirms or declines the archive proposal | Answers the single y/n prompt wrap presents; makes no judgment about "same arc" itself |
| Wrapping agent | Judges same-arc coverage, writes the declaration, executes confirmed moves | Runs Evidence Gathering, drafts the log body, executes the move only on explicit "yes" |

## Requirements

1. Wrap determines the newest existing log in `_local/_session-logs/` (its top level and any
   `YYYY-MM/` folders) using the same newest-wins filename sort already defined in
   `references/log-discovery.md`, and reads enough of that log, at minimum its `summary` frontmatter
   field and title, to judge whether it covers the same arc as the session being wrapped. This runs in
   deep and final modes, the same modes that already run the pre-wrap hygiene sweep. [S1, S4]
2. The same-arc judgment itself is agent discretion, exactly as the source names it ("when the newest
   existing log covers the same arc"). This spec constrains the observable behavior once a judgment is
   made; it does not attempt to make the judgment method deterministic. [S1]
3. The archive proposal reuses the hygiene sweep's existing resolution protocol, one proposal,
   independently confirmable, executed only on explicit approval, rather than defining a second
   protocol. It is not itself a hygiene-sweep check: the sweep's own "Hygiene Sweep" log section is
   defined as findings from the pre-wrap sweep specifically, and a same-arc judgment is not a sweep
   finding, so its declaration and its proposal both live outside that section to avoid the section's
   own definition going false the way D-1's trigger-narrowing defect did. [S1, S2, S5]
4. No new frontmatter field is added. The `supersedes:` field proposed during design was rejected as a
   producer with zero consumers, the same shape as D-04 (capture-lite consumers), because its only
   named future consumers, W-4 (digest mode) and C-5 (arc resume), do not exist yet. [S1]
5. `_local/_session-logs/_superseded/` requires no change to either discovery pipeline.
   `references/log-discovery.md`'s allowlist already excludes any subdirectory whose name is not
   `YYYY-MM`, a property the file already states is "the mechanism any future deliberately-hidden
   subdirectory relies on." A prior maintainer-local design document independently anticipated this
   exact directory name before D-05 existed as a scheduled effort. [S1, S3, S4]
6. No script is added for the archive move. It is a single, agent-executed, confirmed file relocation,
   consistent with the source's own cost estimate of prose only. [S1]

## Acceptance Criteria

Unless noted, AC-1 through AC-4 apply only in deep and final modes. That scope is this spec's own
inference from the existing hygiene-sweep mode gating (Requirement 1), not stated verbatim in the
source; see Open Questions, OQ2. Each Given below restates the precondition explicitly so the AC reads
as a standalone test contract.

**AC-1:** Given (deep or final mode) the newest existing log in `_local/_session-logs/` is judged by
the wrapping agent to cover the same arc as the current session, when wrap drafts the new log's
Summary section, then the Summary ends with one sentence naming the older log by filename only (no
directory prefix) and stating that it is superseded. [S1, S5, model-inference: mode scope]

**AC-2:** Given (deep or final mode) a same-arc judgment as in AC-1, when wrap presents the archive
option, then exactly one proposal is shown, naming the older log's filename and
`_local/_session-logs/_superseded/` as the destination. [S1, S2, model-inference: mode scope]

**AC-3:** Given the user confirms the archive proposal from AC-2, when wrap executes it, then
`_local/_session-logs/_superseded/<filename>` exists with the filename unchanged, and the file no
longer exists at its original path. [S1, S2]

**AC-4:** Given the user declines or does not answer the archive proposal from AC-2, when wrap
finishes drafting the log, then the Summary sentence from AC-1 also states that the older log was not
archived. [S1, S2]

**AC-5:** Given no existing log is judged to cover the same arc as the current session, when wrap
drafts the new log, then no supersession sentence appears in Summary and no archive proposal is made.
[S1]

**AC-6:** `references/log-discovery.md`'s store-layout table lists `_local/_session-logs/_superseded/`
as a non-discovered path alongside `_capture/`, with no change to either search pipeline: the existing
one-level-deep allowlist already excludes any non-`YYYY-MM` subdirectory. [S1, S3, S4]

**AC-7:** After this change, `references/frontmatter-schema.md` contains no `supersedes:` field, or
equivalent, in any tier table. [S1]

## Behavior / Examples

### Example 1: the motivating case, replayed

Given the wrapping agent is finishing the session that produced
`2026-08-17_22-15_claude_migration-complete-t3-and-cutover.md`, and the newest existing log at that
point is `2026-08-17_17-10_claude_wave1-migration-publish-and-t0.md` [S6], and the wrapping agent
judges both to cover the same migration arc, when it drafts the new log, then:

- The Summary ends with a sentence such as: "This log supersedes
  `2026-08-17_17-10_claude_wave1-migration-publish-and-t0.md` (same arc); archived to
  `_superseded/`." (on confirmation), or "...; not archived." (on decline).
- Exactly one prompt appears: "Move `2026-08-17_17-10_claude_wave1-migration-publish-and-t0.md` to
  `_local/_session-logs/_superseded/`? (y/n)"
- On "y": the session log of 2026-08-17 17:10 no longer
  exists; `_local/_session-logs/_superseded/2026-08-17_17-10_claude_wave1-migration-publish-and-t0.md`
  does.

This matches what actually happened informally that day: the real 22:15 log declared the supersession
in prose and tracked the duplicate as a Waiting-on bullet instead, and the most recent log on record
asked for exactly this mechanism in the maintainer's own words: "Harmless, since resume takes the
newest, but say the word and it goes." [S1] After this change, the skill is the thing that says the
word.

### Example 2: no collision (the common case)

Given no existing log covers the same arc as the session being wrapped, when wrap drafts the log, then
Summary contains no supersession sentence and no archive prompt appears, identical to today's
behavior.

### Example 3: fresh repo, no existing log at all

Given `_local/_session-logs/` contains no prior log (first-ever wrap in a repo), when wrap runs the
same-arc check, then there is nothing to compare against, so the check is a no-op: no sentence, no
proposal, identical to Example 2's outcome. [model-inference: this edge case is not named in the
source; it follows from Requirement 1 having no log to read]

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | Neither skill's `description:` frontmatter grows; all new text lives in SKILL.md body and reference files, paid only on invocation | [S1], design frame |
| Data safety | Archive, never delete. Every move is per-action confirmed and reversible by moving the file back by hand | [S1], design frame |
| Determinism | The same-arc judgment is agent discretion by design; this spec does not attempt to make it deterministic or add a canary-backed detector for it | [S1] |

## Revisions

| Date | Change | By |
|---|---|---|
| 2026-08-23 | Initial draft created | agent |

## Sources & Evidence

- [S1] the maintainer's private defect record for the wrap/continue pair, 2026-08-18, D-5 section and the "Rejected and rescoped"
  table. Maintainer-local, class A (primary design source; the mechanism, cost, and rejection are
  authored analysis, not inference).
- [S2] `skills/plab-wrap-session/references/hygiene-sweep.md`, the Resolution protocol (rules 1-5) and
  Check 5's report-nothing-when-empty norm. In-repo, class A, verified by direct read.
- [S3] the maintainer's private W-5 log-archiving spec, 2026-08-18, the store-layout table naming "future
  `_superseded/`" and the explicit "D-5 ships separately" out-of-scope row. Maintainer-local, class A,
  verified by direct read; this document predates D-05 being a scheduled effort and independently
  anticipated the directory name.
- [S4] `skills/plab-continue-session/references/log-discovery.md`, the store-layout table and the
  one-level-deep allowlist mechanism. In-repo, class A, verified by direct read.
- [S5] `skills/plab-wrap-session/SKILL.md`, Evidence Gathering, the Summary bullet definition, and the
  Hygiene Sweep bullet definition. In-repo, class A, verified by direct read.
- [S6] the session log of 2026-08-17 17:10 and
  the session log of 2026-08-17 22:15. Maintainer-local,
  class B: existence verified directly (directory listing); the decisions-count and files-changed
  divergence is [S1]'s characterization of their content, not independently re-verified here.

### Unverified Claims

- AC-1 and AC-2's "(deep or final mode)" precondition is a [model-inference] scope decision, reasoned
  from the existing hygiene-sweep mode gating (Requirement 1). The source does not state a mode scope
  for the same-arc check explicitly. See Open Questions, OQ2.
- Example 3 (fresh repo, no existing log) is a [model-inference] edge case not named in the source.

## Open Questions / Decisions

**Closed 2026-10-26.** JP approved closing the items below as one batch, after a read-only check on 2026-10-25 confirmed each against shipped code. Each closed item ends with what the check found.

| ID | Title | Status |
|---|---|---|
| OQ1 | Overlap with D-07's "read the previous log" | Superseded |
| OQ2 | Mode scope for the same-arc check | Decided |
| OQ3 | Whether the archive move should eventually be scripted | Deferred |

### OQ1: Overlap with D-07's "read the previous log"

D-05 and D-07 (the Waiting-on blocker contract) both independently add a "read the newest, or
previous, existing log" capability to `plab-wrap-session`'s Evidence Gathering: D-05 to judge same-arc
coverage, D-07 to carry forward unresolved Waiting-on items with their original blocked-since dates.
Neither this spec nor D-07's own spec should assume the other's read already exists, since specs in
this release are written and may be implemented independently. Whichever effort lands second should
detect whether Evidence Gathering already reads the newest log (for the other effort's purpose) and
reuse that read rather than adding a second one. Not blocking either effort individually; flagged here
for whoever integrates both, and mirrored in the implementation plan's Phase 1 notes.

**Closed, Superseded by W-02 (derived log facts).** D-05's same-arc check and D-07's carry-forward both read the newest existing log from one shared call to `derive-log-facts.py` (`skills/plab-wrap-session/SKILL.md`, Evidence Gathering). That is a stronger fix than this item's convention, in which whichever effort landed second would reuse the other's read.

### OQ2: Mode scope for the same-arc check

This spec scopes the same-arc check to deep and final modes, matching the existing hygiene-sweep
gating. The source does not state this explicitly. Quick and blocked mode sessions are short, low-risk,
or blocker-focused by their own mode definitions, which makes them unlikely candidates for covering the
same arc as a substantial prior log, but "unlikely" is not "impossible." Recommend confirming this scope
before treating it as settled; if wrong, the fix is a one-line change to Requirement 1's mode list.

**Closed, Decided.** The deep and final scope for the same-arc check shipped and still holds (`skills/plab-wrap-session/SKILL.md`, Evidence Gathering).

### OQ3: Whether the archive move should eventually be scripted

The source's own cost estimate ("one paragraph in wrap SKILL.md plus a sentence in log-discovery.md")
implies a rung-3 documented convention, not a rung-2 script, and this spec follows that. If same-arc
collisions turn out to be frequent enough that the manual move becomes routine, a small script
analogous to `organize-logs.py` (dry-run by default, single-file move, never delete) would be the next
mechanization step. Not needed now; recorded so the option is not lost.

**Closed, Deferred.** The archive move is still a step the agent performs on approval, with no script. Nothing shows that same-arc collisions have become frequent enough to justify one, so revisit only if they do.
