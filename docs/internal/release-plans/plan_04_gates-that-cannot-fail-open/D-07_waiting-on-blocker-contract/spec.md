---
id: D-07
title: Restore Waiting on You as an enforced blocker contract
type: spec
status: fulfilled
created: 2026-08-23
updated: 2026-10-26
linked-effort: the maintainer's private defect record for the wrap/continue pair, 2026-08-18
linked-plan: implementation-plan.md
ac-count: 8
source-count: 7
requires-human-review: true
target-release: v0.4.0
linked-release: docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md
priority: P1
---

# Spec: Restore Waiting on You as an enforced blocker contract

## Task Summary

**Status:** Fulfilled
**Last updated:** 2026-08-24
**Linked plan:** implementation-plan.md
**Open questions:** 2 (see Open Questions / Decisions)
**Revisions:** Initial draft created 2026-08-23.

### Acceptance Criteria Fulfillment

- [x] AC-1: Waiting on You definition tightened to blocked-on-maintainer items with a blocked-since marker
- [x] AC-2: Log Self-Check gains a gate rejecting any item beginning with "Optional"
- [x] AC-3: Log Self-Check gains a gate rejecting any item missing a blocked-since marker
- [x] AC-4: Evidence Gathering gains a carry-forward step from the previous log
- [x] AC-5: handoff-display.md sorts Waiting-on bullets oldest first
- [x] AC-6: session-log-template.md's Waiting on You comment states the tightened contract
- [x] AC-7: session-log-template.md gains a Parked list section
- [x] AC-8: Carry-forward degrades sensibly against a previous log written before this schema existed

### Currently In Progress

None.

## Purpose

The Waiting on You section of a session log exists to carry the maintainer's open obligations forward across sessions, but its enforcement has diluted into a suggestion list: a real log carried five items, four prefixed "Optional:", with a genuine blocker open since July camouflaged among them, and the log still passed all of the skill's own Log Self-Check gates [S1][S5]. This spec tightens the section's definition, adds two gates that make the specific failure mechanically rejectable, and adds a carry-forward step so a blocker's age survives across wraps instead of resetting. It is the interim step for W-3 (Waiting-on escapes gitignore, planned for v0.9.0), not a replacement for it: the section still lives inside the gitignored session log after this ships, and only its internal contract changes [S1].

## Scope

### In Scope

- Tightening the Waiting on You definition in `skills/plab-wrap-session/SKILL.md` to items blocked on the maintainer, each carrying a `(blocked since YYYY-MM-DD)` marker.
- Two new Log Self-Check gates enforcing that definition syntactically.
- A new Evidence Gathering step that reads the previous log's Waiting on You section and carries unresolved items forward with their original dates.
- Sorting the read-side display oldest-first in `plab-continue-session`.
- A new Parked list in the session log template as the destination for optional context that no longer belongs in Waiting on You.
- The version bumps and HISTORY.md, CHANGELOG.md, and README entries this effort contributes to the shared v0.4.0 release.

### Non-Goals

- Does not move Waiting on You out of the gitignored session log or into any tracked or externally visible location. That is W-3 (Waiting-on escapes gitignore), planned for v0.9.0; this spec only tightens the contract governing what belongs in the section while it still lives where it lives today.
- Does not build semantic detection of "genuinely blocked" versus "optional." The two new gates are syntactic: a literal "Optional" prefix check and a literal marker-presence check. Judging whether an item is truly maintainer-blocked remains the wrapping agent's responsibility, not a script's.
- Does not change the ordering or contract of the What's Next section.
- Does not retroactively rewrite any existing session log. Carry-forward only takes effect for logs written by a wrap running this version or later.
- Does not add the Parked list to Quick or Blocked mode templates. See Open Question D1.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| The maintainer (JP) | Sole reader of Waiting on You; the person the section exists to reach | Reads the section at resume time via `plab-continue-session`'s display, sorted oldest-first; resolves or defers each item |
| The wrapping agent | Authors the session log every session | Applies the tightened Waiting-on definition, runs the new carry-forward evidence step, and must pass the two new Log Self-Check gates before writing |

## Requirements

1. The Waiting on You section must contain only items blocked on the maintainer's decision or action, distinguishing it from optional or nice-to-have context that happens to also be true. [S1]
2. Every Waiting on You item must carry a machine-checkable age signal, a `(blocked since YYYY-MM-DD)` marker, so staleness is visible without reading git or session history. [S1]
3. The Log Self-Check must reject a drafted log that violates the tightened definition, closing the specific gap that let a real log pass 13 of 13 gates while violating the section's own stated definition. [S1][S5]
4. Optional or nice-to-have context that does not meet the Waiting-on bar needs a named destination in the log so it is redirected rather than simply dropped. [S1]
5. Blocked-since dates must not reset on every wrap; an item still blocked after multiple sessions must show its original date, not the date of the most recent wrap that mentioned it. [S1]
6. The read-side display in `plab-continue-session` must present the maintainer's open obligations oldest-first, so the longest-blocked item leads rather than whatever was written last. [S1][S3]
7. Carry-forward must degrade sensibly when the previous log predates this schema and its Waiting-on items carry no blocked-since marker to preserve. [model-inference]

## Acceptance Criteria

**AC-1:** `skills/plab-wrap-session/SKILL.md`'s Waiting on You definition is tightened to: only items blocked on the maintainer's decision or action, each carrying a `(blocked since YYYY-MM-DD)` marker; items that do not meet this bar route to What's Next or the new Parked list, never to Waiting on You. [S1][S2]

**AC-2:** `skills/plab-wrap-session/SKILL.md`'s Log Self-Check gate list gains a gate that fails when any Waiting on You item's text begins with "Optional". [S1][S2]

**AC-3:** `skills/plab-wrap-session/SKILL.md`'s Log Self-Check gate list gains a gate that fails when any Waiting on You item lacks a `(blocked since YYYY-MM-DD)` marker. [S1][S2]

**AC-4:** `skills/plab-wrap-session/SKILL.md`'s Evidence Gathering steps gain a step that locates the previous session log (using `plab-continue-session`'s newest-log selection rule) and carries its still-applicable Waiting on You items into the new log, preserving each item's original blocked-since date rather than substituting the current wrap's date. [S1][S6]

**AC-5:** `skills/plab-continue-session/references/handoff-display.md`'s Waiting on you display sorts bullets oldest-blocked-first by the blocked-since date. [S1][S3]

**AC-6:** `skills/plab-wrap-session/references/session-log-template.md`'s Waiting on You section comment is updated, in the Final, Quick, and Blocked mode blocks, to state the tightened contract (blocked-on-maintainer only, blocked-since marker required, optional items redirected), matching the SKILL.md definition. [S1][S4]

**AC-7:** `skills/plab-wrap-session/references/session-log-template.md` gains a new Parked section, with heading and instructional comment, as the named destination for optional or nice-to-have context that does not meet the Waiting on You bar. [S1][S4]

**AC-8:** Given a previous log written before this schema shipped, whose Waiting on You items carry no blocked-since marker, when the wrapping agent carries an item forward, then it records the item as newly observed (blocked-since equals the current wrap's date) rather than fabricating an earlier date it cannot verify. [model-inference]

## Behavior / Examples

**Example 1: the motivating case, re-expressed under the new contract.** The real log at `the session log of 2026-08-17 22:15:105-111` carries five Waiting-on items; four begin "Optional:" and the fifth reads "Open since July: the source-of-truth ruling" [S5]. Under AC-1, the four optional items are not eligible for Waiting on You at all; they move to Parked (AC-7) or What's Next. The fifth remains, reformatted to carry a marker, illustratively:

```
### Waiting on You
- Open since July: the source-of-truth ruling for jp-init-project, jp-spec, and
  jp-release-plan (blocked since 2026-07-DD, N days). Link: [file or thread].
```

The exact original date is illustrative here; AC-4's carry-forward is what would have supplied the real one had this schema existed at the time. The point the source evidence makes still holds without it: one blocker alone in its section reads differently from the same words buried under four Optionals [S1].

**Example 2: the gate firing.** Given a drafted log whose Waiting on You section contains "Optional: smoke-test plab-strategy-brief", when the Log Self-Check runs (AC-2), then it fails and names the offending item; the agent must move it to Parked or What's Next before the log can be written.

**Example 3: carry-forward, ordinary case.** Given the previous log's Waiting on You contains "Open since July: the source-of-truth ruling (blocked since 2026-07-15, 39 days)" and the maintainer has not ruled on it, when the current wrap runs Evidence Gathering (AC-4), then the new log's Waiting on You includes the same item with the same `2026-07-15` date, not today's date.

**Example 4: carry-forward, pre-schema previous log (AC-8).** Given the previous log predates this schema and its Waiting-on items carry no `(blocked since ...)` marker, when the current wrap carries an item forward, then it is recorded as newly observed with today's date; the agent does not guess or fabricate an earlier date.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | The two new gate bullets and the new Evidence Gathering step add body text to `SKILL.md` only, loaded on invocation; the always-on skill description is unchanged, so per-session baseline cost does not rise. | [S1], design frame (conventions section 3) |
| Process cost / ceremony | Carry-forward requires the wrap to read the previous session log at every session, which wrap does not do today. This is genuine new behavior and the one deliberate ceremony cost in this set; it is accepted because without it, blocked-since dates reset every wrap and the age signal the whole mechanism exists to produce is lost. | [S1] |
| Pairing contract | This effort changes the session-log format and its gates on both the write side (`plab-wrap-session`) and the read side (`plab-continue-session`), so both skills version-bump together per the pairing contract both HISTORY.md files assert. | [S1], `skills/plab-continue-session/HISTORY.md` |

## Revisions

| Date | Change |
|---|---|
| 2026-08-23 | Initial draft created. |

## Sources & Evidence

- [S1] the maintainer's private defect record for the wrap/continue pair, 2026-08-18, section "D-7. 'Waiting on You' has diluted from a blocker contract into a suggestion list" (lines 129-145). Class A: maintainer-authored roadmap with evidence verified against the shipped artifacts. Maintainer-local, gitignored, exists on disk.
- [S2] `skills/plab-wrap-session/SKILL.md`. Class A: the file this effort edits. Cited lines: 36-47 (Evidence Gathering), 153 (Waiting on You definition), 186 (Log Self-Check heading), 190-195 (the six current gates).
- [S3] `skills/plab-continue-session/references/handoff-display.md`. Class A: the file this effort edits. Cited lines: 14-15 (Waiting on you display block).
- [S4] `skills/plab-wrap-session/references/session-log-template.md`. Class A: the file this effort edits. Cited lines: 73-78 (Final Mode comment), 121-123 (Quick Mode comment), 163-165 (Blocked Mode comment).
- [S5] the session log of 2026-08-17 22:15. Class A: primary evidence artifact, a real shipped session log. Cited lines: 105-111 (Waiting on You section, five items, four "Optional:" prefixed).
- [S6] `skills/plab-continue-session/references/log-discovery.md`. Class A: the file defining the newest-log selection rule this effort's carry-forward step reuses by reference rather than restating. Cited lines: 40-57 (Selection rule and Sort rule).
- [S7] `docs/skills/plab-continue-session/README.md`, lines 100-101. Class A: existing human-facing documentation. Its worked example already shows a Waiting-on item in the `(blocked since YYYY-MM-DD)` shape this spec formalizes, which corroborates that the target format is not a new invention but a generalization of an example already in the docs.

### Unverified Claims

- AC-8 and Requirement 7 are [model-inference]: the source roadmap specifies that carry-forward preserves "original blocked-since dates" but does not address what happens when the previous log has no such date to preserve, because no log written before this ships will carry the marker. The fallback (treat as newly observed, today's date) is this spec's addition, not the source's.

## Open Questions / Decisions

| ID | Question | Status |
|---|---|---|
| D1 | Should the Parked list exist in Quick and Blocked mode templates, or Final/Deep mode only? | Decided for this spec: Final/Deep only |
| D2 | How does the wrapping agent decide an item is "still applicable" when carrying it forward, versus mechanically re-copying every previous item forever? | Superseded |

**D1: Parked list scope.** This spec scopes the new Parked section to Final and Deep mode (AC-7), matching where the Waiting-on section's full contract lives and where the dilution incident occurred [S1][S5]. Quick and Blocked mode sessions are short or urgent by definition (under 30 minutes, or ended by a blocker), so optional context rarely accumulates in them. If a Quick-mode wrap produces optional items with nowhere to go, revisit.

**D2: Resolution judgment.** The source roadmap says carry-forward moves "unresolved items forward" [S1] but does not specify how the wrapping agent determines an item is unresolved rather than settled. This spec leaves that to the agent's existing judgment, the same kind already exercised for `decisions-count`, verification status, and mode selection, rather than inventing a new sub-mechanism the source does not describe. If carry-forward in practice produces stale or wrongly-dropped items, this may need an explicit resolution-check step in a later effort.

**D2 closed 2026-10-26, Superseded.** On 2026-10-20 the maintainer approved a successor design for this question. At resume, each Waiting on You item is re-checked against a closed list of read-only kinds that a computer can check, and reported as still waiting, done since the wrap, or not checkable. That design replaces this item's reliance on the agent's judgment. It is not yet specified or built. JP approved this closure on 2026-10-26, as part of a batch checked against shipped code the day before.
