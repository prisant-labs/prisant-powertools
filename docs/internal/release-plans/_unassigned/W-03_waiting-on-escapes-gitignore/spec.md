---
id: W-03
title: Waiting-on items escape the gitignored log via offered GitHub issues
type: spec
status: draft
created: 2026-08-23
updated: 2026-10-26
linked-effort: the maintainer's private plab-wrap-session evolution roadmap, 2026-08-16
linked-plan: implementation-plan.md
ac-count: 6
source-count: 8
requires-human-review: true
target-release: null
linked-release: null
priority: P2
---

# Spec: Waiting-on items escape the gitignored log via offered GitHub issues

## Task Summary

- **Status:** draft
- **Last updated:** 2026-08-23
- **Linked plan:** `implementation-plan.md`
- **Open questions:** 2 (see Open Questions / Decisions)
- **Revisions:** 1 (see Revisions)

### Acceptance Criteria Fulfillment

- [ ] AC-1: Wrap offers promotion for each carried-forward Waiting-on item, one at a time, in deep/final mode
- [ ] AC-2: A declined or unanswered proposal leaves the item on D-07's existing carry-forward path
- [ ] AC-3: An approved promotion's issue body carries the blocked-since date, linked files, and the raising log's filename
- [ ] AC-4: A successful promotion replaces the bullet with a short issue reference in the log being written
- [ ] AC-5: An already-promoted item is excluded from raw-text carry-forward and not re-offered
- [ ] AC-6: The offer step degrades silently, with a noted skip, when `gh` is unavailable

### Currently In Progress

None.

## Purpose

Waiting on You items are supposed to be blockers the maintainer must act on, but a gitignored,
machine-local log is a destination nothing can act on: the same source-of-truth ruling sat there as
blocking for months across successive logs, with nothing changing except the file it lived in. W-03
(the roadmap's W-3) offers, at wrap time and under per-item confirmation, to promote a carried-forward
Waiting-on item into a GitHub issue, giving it a URL, a state, a notification surface, and a history
the log itself cannot provide. It builds on D-07 (the Waiting-on blocker contract, the roadmap's D-7,
shipping in v0.4.0), which first restricts the section to genuine blockers and adds the blocked-since
dates and carry-forward that this effort's issues inherit; W-03 does not replace that mechanism, it
gives its aged items somewhere to go.

## Scope

### In Scope

- Offering, per carried-forward Waiting-on item, to create a GitHub issue in the current repository,
  under the hygiene sweep's existing Resolution protocol.
- Issue content: the item's text, its blocked-since date, any repo file paths the item already links
  to, and the filename of the session log that carried it.
- Marking a promoted item so the next wrap's D-07 carry-forward step stops re-listing it as raw text.
- A graceful, silent skip when `gh` is unavailable, unauthenticated, or the environment is offline.

### Non-Goals

- Not an automation. No issue is ever created without an explicit per-item "y"; this is the effort's
  critical constraint, not a detail.
- Does not replace or modify D-07's blocked-since / carry-forward mechanism for items that are not
  promoted.
- Does not implement backlog item S-06 in full. S-06 itself is not in this repository; this spec
  treats the roadmap's paraphrase of it as a second-hand, unverified reference (see Sources &
  Evidence, Unverified Claims).
- Does not implement cross-repo issue targeting. The current repository is the only target this
  spec's acceptance criteria define (see Open Questions OQ-1, which tracks plan.md's open D2).
- Does not build W-06 (the log as a checkable contract, the roadmap's speculative item).
  `docs/internal/release-plans/plan_08_escape-and-measure/plan.md`'s D1 decision records W-06 as deliberately
  deferred and unscheduled. Neither this effort nor C-04 is W-06.
- Does not retroactively promote items sitting in historical logs; the offer only ever considers the
  current wrap's live, carried-forward Waiting-on list.
- Does not reuse or modify the existing `related-issues` Tier 3 frontmatter field, which serves a
  different, unrelated purpose (agent-detected issue references, not this workflow's writeback).

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Approves or declines each promotion proposal | Answers "y/n" per item during the wrap; nothing is created without this |
| Wrapping agent | Detects carried-forward Waiting-on items, proposes promotion, executes approved creates, rewrites the bullet | Runs the wrap skill; invokes `gh issue create` only on approval |

## Requirements

1. The promotion offer runs only in deep and final wrap modes, matching the hygiene sweep's existing
   mode-gating (quick and blocked modes run only check 2 and note the skip). [S3, S5]
2. The offer reuses the hygiene sweep's Resolution protocol exactly: one proposal per item,
   independently confirmable, nothing adjacent executed without its own confirmation. [S3]
3. No issue is ever created without the maintainer's explicit per-item approval. This is the effort's
   critical constraint, matching the propose-then-per-action-confirm pattern already governing every
   other action in the wrap that touches the world outside the log file. [S1, S3]
4. Promotion builds on D-07 (the Waiting-on blocker contract, the roadmap's D-7, shipping in v0.4.0):
   items arrive at this effort already carrying blocked-since dates and carry-forward history, and
   W-03 leaves that mechanism unchanged for items that are not promoted. [S2, S7]
5. The promotion target defaults to the current repository. `plan.md`'s D2 ("Where promoted
   blockers are filed"), open at authoring time, may add a cross-repo targeting question before this
   effort executes; see Open Questions OQ-1. [S4]
6. This effort does not reuse the existing `related-issues` Tier 3 frontmatter field, a separate
   mechanism for agent-detected issue references unrelated to this workflow's writeback. [S6]
7. Backlog item S-06, which the roadmap describes as already sketching a `gh-issue:` frontmatter-hook
   design, is not present in this repository. This spec treats the roadmap's paraphrase as a
   second-hand, unverified reference and does not depend on any undocumented detail of S-06. [S1, S8]

## Acceptance Criteria

**AC-1:** Given the previous log's Waiting on You section carried at least one item forward under
D-07's mechanism, when a wrap runs in deep or final mode, then the wrap offers to create a GitHub
issue for that item, one item at a time, following the hygiene sweep's Resolution protocol. [S1, S3]

**AC-2:** Given a promotion proposal for a single item, when the maintainer declines or does not
answer, then the item is left unchanged and continues to be carried forward by D-07's existing
mechanism with its original blocked-since date. [S1, S2, S3]

**AC-3:** Given an approved promotion, when the wrap runs `gh issue create` against the current
repository, then the created issue's body includes the item's blocked-since date, any repo file paths
the item already linked to, and the filename (never a path or URL) of the session log that carried
the item. [S1, S4, S6]

**AC-4:** Given an approved promotion, when the current log is written, then that item's Waiting-on
bullet is replaced with a short reference carrying the issue number and URL in place of the full item
text. [model-inference]

**AC-5:** Given an item already carrying an issue reference from a prior promotion, when a later wrap
runs its carry-forward step, then that item is excluded from raw-text carry-forward and is not
re-offered promotion. [model-inference]

**AC-6:** Given `gh` is unavailable, unauthenticated, or the environment is offline, when a wrap
reaches the promotion-offer step, then the step is skipped, the skip is noted in the Hygiene Sweep
section, and the wrap completes normally. [S3]

## Behavior / Examples

**Walkthrough 1: approved promotion.** The previous log's Waiting on You section, carried forward
under D-07's mechanism, reads "Source-of-truth ruling (blocked since 2026-07-xx, 38 days)," the exact
example D-07's own source uses [S2]. This wrap runs in deep mode. The promotion-offer step presents:
"Waiting-on item 'Source-of-truth ruling' (blocked since 2026-07-xx, 38 days): create a GitHub issue
for it in prisant-labs/prisant-utilities? (y/n)". The maintainer answers "y". The wrap runs
`gh issue create`, and the resulting issue body carries the blocked-since date and the filename of the
log that raised the item. This log's own Waiting-on bullet becomes "Source-of-truth ruling: promoted
to issue #142 (https://github.com/prisant-labs/prisant-utilities/issues/142)." The next wrap's
carry-forward step does not re-list it as raw text.

**Walkthrough 2: declined.** Same item, same offer. The maintainer answers "n". The item is left
exactly as D-07 already carries it forward, full text and blocked-since date unchanged, and the
decline is recorded in the log's Hygiene Sweep section per the Resolution protocol's rule on declined
proposals. [S3]

**Walkthrough 3: `gh` unavailable.** `gh` is not installed on this machine. The wrap reaches the
promotion-offer step, skips it, and records "GitHub issue promotion skipped: gh not available" in the
Hygiene Sweep section. The wrap completes normally and the Waiting-on item is carried forward as
usual. [S3]

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | No skill description growth; the mechanism lives entirely in `SKILL.md` body and references | wrap-session.md:117 |
| Safety | No issue is ever created without explicit per-item confirmation | hygiene-sweep.md:69-78 |
| Degradation | The offer step must skip silently, with a noted line, never block the wrap, when `gh` is unavailable or the repo is offline | hygiene-sweep.md:82 |
| Reversibility | A created GitHub issue is not reversible by the skill itself; undoing a wrongly-created issue is a manual, out-of-band maintainer action, unlike this repo's archive-not-delete pattern for local file moves | [model-inference], no source states this risk directly |

## Revisions

| Date | Change | Author |
|---|---|---|
| 2026-08-23 | Initial draft created | agent |

## Sources & Evidence

[S1] the maintainer's private plab-wrap-session evolution roadmap, 2026-08-16. Class A.
Section "W-3. Make 'Waiting on You' escape the gitignored folder," lines 62-73. Primary roadmap source
for this effort; W-03 is the padded form of this document's W-3.

[S2] the maintainer's private defect record for the wrap/continue pair, 2026-08-18. Class A.
Section "D-7. 'Waiting on You' has diluted from a blocker contract into a suggestion list," lines
129-144. D-07 is the padded form of this document's D-7; it is this effort's prerequisite, not its
replacement.

[S3] `skills/plab-wrap-session/references/hygiene-sweep.md`. Class A. "Resolution protocol," lines
69-83; rule 5 (time-boxing / graceful skip), line 82.

[S4] `docs/internal/release-plans/plan_08_escape-and-measure/plan.md`. Class A. Context section, lines 26-33
and 48-51; Open Question D2 ("Where promoted blockers are filed"), lines 146-178.

[S5] `skills/plab-wrap-session/SKILL.md`. Class A. Waiting on You definition, line 153; hygiene sweep
summary and mode-gating, lines 49-61.

[S6] `skills/plab-wrap-session/references/frontmatter-schema.md`. Class A. Tier 3 `related-issues`
field, line 51; filename-only log-citation rule, line 100.

[S7] `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md`. Class A. Confirms D-06 and D-07 ship in
v0.4.0 and names the skill versions for that release (wrap 1.6.0, continue 1.4.0), lines 27-28 and 52.

[S8] the maintainer's private roadmap index, 2026-08-16. Class B. Line 57, a
second, corroborating mention of backlog item S-06; adds no detail beyond [S1].

### Unverified Claims

- Backlog item S-06 itself is not present in this repository. Both [S1] and [S8] paraphrase it as
  sketching issues that point at repo docs and back, with a `gh-issue:` frontmatter hook "already read
  by one of your skills." A repository-wide search of `skills/` for `gh-issue` returns no matches, so
  that hook, if it exists, lives outside this repository. This spec does not depend on it, or on any
  other undocumented detail of S-06.
- AC-4 and AC-5 carry `[model-inference]` because they fill a gap the sources leave open: what happens
  to a promoted item's bullet, and how the carry-forward step recognizes it on the next wrap. Neither
  detail is dictated by [S1] or [S2]; both are this spec's proposed design, consistent with the
  sources' stated intent ("gains a URL, a state, a notification surface, and a history") but not
  verbatim from them.

## Open Questions / Decisions

| ID | Title | Status |
|---|---|---|
| OQ-1 | Cross-repo issue targeting | Open |
| OQ-2 | Carry-forward marker format for promoted items | Open |

### OQ-1: Cross-repo issue targeting

This spec's AC-3 assumes the current repository as the promotion target, the default path under
Option B of `plan.md`'s D2 ("Where promoted blockers are filed"), still open at authoring time.
If D2 resolves to asking for an alternate target on non-repo-specific items (its recommended Option B)
or to a single tracker repository (Option C), AC-3 needs revision to add the target question or
redirect the default. This spec does not restate D2's three-option analysis, which the release plan
owns.

**Update, 2026-10-26.** Release plan 08 now holds no efforts, so this item is the open home of the question its D2 asked: where a promoted blocker is filed. Release plan 08's D2 is marked Superseded and points here. Its three-option analysis stays in that plan as the record of what was weighed, and the maintainer's ruling will be recorded here.

### OQ-2: Carry-forward marker format for promoted items

AC-4 and AC-5 assume a short, issue-URL-bearing replacement line is sufficient for D-07's carry-forward
step to recognize a promoted item and skip re-listing it as raw text on the next wrap. No source
document specifies this marker's exact shape; this spec marks the mechanism `[model-inference]` and
leaves the precise string or parsing rule to implementation time.
