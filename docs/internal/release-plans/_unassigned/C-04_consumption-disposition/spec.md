---
id: C-04
title: Record whether a resumed log's next action survived contact with reality
type: spec
status: committed
created: 2026-08-23
updated: 2026-11-17
linked-effort: the maintainer's private plab-continue-session evolution roadmap, 2026-08-16
linked-plan: implementation-plan.md
ac-count: 6
source-count: 8
requires-human-review: false
target-release: null
linked-release: null
priority: P2
---

# Spec: Record whether a resumed log's next action survived contact with reality

## Task Summary

- **Status:** committed
- **Last updated:** 2026-11-17
- **Linked plan:** `implementation-plan.md`
- **Open questions:** 3, all decided 2026-11-17 (see Open Questions / Decisions)
- **Revisions:** 2 (see Revisions)

### Acceptance Criteria Fulfillment

- [x] AC-1: A genuine skill-mediated resume gets a `resumed-from-outcome:` value in the new log
- [x] AC-2: No resume this session means the field is omitted, never a placeholder
- [x] AC-3: The three values are defined exactly as fulfilled, superseded, and ignored
- [x] AC-4: The field modifies only the new log, never the log named by `resumed-from:`
- [x] AC-5: Only the wrap skill writes the field; continue-session writes no files
- [x] AC-6: No aggregation, digest, or report reads the field as part of this effort

### Currently In Progress

None.

## Purpose

Consumption of a session log is already recorded: `resumed-from:` notes which log a resume consumed. What it cannot say is whether that log's named next action survived contact with reality. C-04 (the roadmap's C-4) closes that loop with one frontmatter field, written by the next wrap, classifying the prior log's next action as fulfilled, superseded, or ignored. The third value is the falsifier the roadmap named, the only signal that would tell the maintainer to stop wrapping.

It depends on D-06 (resumed-from semantics, the roadmap's D-6), which shipped and is recorded in `frontmatter-schema.md`'s "`resumed-from` semantics" subsection: `resumed-from` is written only from an actual skill-mediated resume and never back-filled from narrative memory. C-04's field inherits that exact discipline, and D-06's own honest assessment, that this metric class is worth one line and no further investment, applies to it too. Since W-07 (session-aware logs), that condition also has a mechanical handle: the wrap passes `--resumed-from <file>` to `derive-log-facts.py` only when this session resumed with `/plab-continue-session` [S7].

The field was proposed as `resumed-from-disposition` and is named `resumed-from-outcome` by ruling OQ-1, because wrap already uses "disposition" for an unrelated decision. The effort folder keeps its original name.

## Scope

### In Scope

- One new Tier 2 frontmatter field, `resumed-from-outcome`, written into the log currently being written.
- Exactly three permitted values: `fulfilled`, `superseded`, `ignored`.
- Writing the field only when this session's `resumed-from:` was itself set via an actual `/plab-continue-session` resume performed this session.
- Omitting the field entirely when no such resume occurred.
- One rule in `check-log.py`, the log's own self-check, holding `resumed-from` and the new field to each other and the value to the three permitted ones (ruling R1).

### Non-Goals

- No aggregation, digest, or cross-log reporting of outcome values; the field is read by opening a log's frontmatter, nothing more.
- No new evidence-gathering step, script, or session-log section beyond the one field.
- Does not change `resumed-from`'s own semantics beyond what D-06 already fixes; C-04 only adds a sibling field.
- Does not measure the "log written but never consumed" case. A session that never invoked `/plab-continue-session` carries neither `resumed-from:` nor this field, and that silence is not something this field resolves (see Behavior / Examples, Walkthrough 3).
- Does not build W-06 (the log as a checkable contract, the roadmap's speculative item). `docs/internal/release-plans/plan_08_escape-and-measure/plan.md`'s D1 decision records W-06 as deliberately deferred and unscheduled. Neither this effort nor W-03 is W-06.
- Does not retroactively backfill outcome values for historical logs.
- Does not add a fourth "unclear" or "partial" value; see OQ-2.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Wrapping agent | Judges and writes the outcome value, using evidence already gathered for the log | Writes `resumed-from-outcome:` into the new log's frontmatter, only when `resumed-from:` is itself present |
| Maintainer | Eventual reader of accumulated outcome values, deciding whether wrapping still pays for itself | Reads individual log frontmatter directly; no tooling is built for this in this effort |

## Requirements

1. The outcome field is written only by `/plab-wrap-session`, never by `/plab-continue-session`, which produces no files of its own. [S3]
2. The field is written into the frontmatter of the log currently being written, never back into the log named by `resumed-from:`, matching continue's existing constraint never to modify the log it resumed from. [S3]
3. The field is written only when this session's `resumed-from:` value was itself set via an actual `/plab-continue-session` resume in this session, mirroring D-06's rule for `resumed-from` itself: never inferred from narrative memory, and omitted when no resume occurred. The wrap step is gated on the same condition that adds `--resumed-from` to the facts script. [S2, S4, S7]
4. The three permitted values are exactly `fulfilled`, `superseded`, and `ignored`, matching the roadmap's own definitions. [S1]
5. The outcome judgment draws only on evidence the wrap already gathers (git state, conversation context); no new evidence-gathering step, script, or report is added. [S2]
6. This field measures only the "consumed but ignored" half of the falsifier the roadmap named. A session that never invoked `/plab-continue-session` carries neither `resumed-from:` nor this field, and that non-consumption case remains invisible to this field by construction. [S1, S5]

## Acceptance Criteria

**AC-1:** Given this session's `resumed-from:` value was set via an actual `/plab-continue-session` resume performed in this session, when the wrap writes the new log, then it writes `resumed-from-outcome:` valued exactly one of `fulfilled`, `superseded`, or `ignored`. Verified by `check-log.py`, which reports a finding for a log that carries `resumed-from` without the field or with any other value. [S1, S2, S8]

**AC-2:** Given this session did not perform a skill-mediated resume, when the wrap writes the new log, then `resumed-from-outcome:` is omitted entirely, never written with a placeholder or empty value. Verified by `check-log.py`, which reports a finding for the field without `resumed-from`. [S2, S8]

**AC-3:** Given the wrap is classifying the outcome, when it assigns a value, then `fulfilled` means the prior log's named next action was completed, `superseded` means circumstances changed and the plan was correctly abandoned, and `ignored` means the session re-derived context and proceeded without engaging the prior log's next action. [S1]

**AC-4:** Given a wrap writes `resumed-from-outcome:`, when the write happens, then it modifies only the new log being written and never the log named by `resumed-from:`. [S3]

**AC-5:** Given a session invoked `/plab-continue-session` and later ends, when that session is wrapped, then `resumed-from-outcome:` is written by the wrap skill; `/plab-continue-session` itself writes no file at any point in the exchange. [S3]

**AC-6:** Given this field exists, when the repository is inspected for tooling that reads it, then none is found: no digest, aggregation script, or report consumes `resumed-from-outcome` as part of this effort. The log's own self-check in `check-log.py`, which reads only the log being written, is not consumption in this sense. [S2, S8]

## Behavior / Examples

**Walkthrough 1: fulfilled.** The prior log's Continuation Prompt named a specific immediate next action. This session invoked `/plab-continue-session`, resumed from that log, and did exactly that. This session's wrap writes `resumed-from: <prior log filename>` and `resumed-from-outcome: fulfilled`.

**Walkthrough 2: ignored.** Same prior log, same resume. This session's conversation shows the maintainer redirected to unrelated work without engaging the named action, whether by choosing "pick something else" at continue's confirmation step or by drifting after starting. `resumed-from:` is still set, since a skill-mediated resume did occur; `resumed-from-outcome: ignored`.

**Walkthrough 3: no resume, field silent.** This session never invoked `/plab-continue-session`. Neither `resumed-from:` nor `resumed-from-outcome:` appears in this log's frontmatter. This case is, by this field alone, indistinguishable from a log that nobody ever consumed; the roadmap's "logs written but never consumed" half of the falsifier is visible only as the absence of `resumed-from:` across a corpus of logs, a cross-log reading concern and not something this single field resolves by itself.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | One frontmatter field and one self-check rule; no new section, script, or report | [S2] |
| Investment ceiling | No further investment beyond this field, explicitly inherited from D-06's own honest assessment of the sibling field | [S2] |
| Data integrity | Written only from actual skill-mediated resume state this session; never inferred or back-filled from narrative memory | [S2] |

## Revisions

| Date | Change | Author |
|---|---|---|
| 2026-08-23 | Initial draft created | agent |
| 2026-11-17 | Refreshed against the code at `635ed7b` and the maintainer's rulings. OQ-1 renames the field to `resumed-from-outcome`; OQ-2 keeps three values; R1 adds a `check-log.py` rule, so AC-1 and AC-2 gain a verification and AC-6 says the self-check is not consumption. D-06 recorded as shipped; the W-07 `--resumed-from` handle added to Requirement 3; sources S7 and S8 added; prose unwrapped per AGENTS.md; status set to committed | agent |

## Sources & Evidence

[S1] the maintainer's private plab-continue-session evolution roadmap, 2026-08-16. Class A. Section "C-4. Close the consumption loop." Primary roadmap source; C-04 is the padded form of this document's C-4.

[S2] the maintainer's private defect record for the wrap/continue pair, 2026-08-18. Class A. Section "D-6. The `resumed-from` field is an unresolvable pointer." D-06 is the padded form of this document's D-6; its semantics fix and its cost-and-risk assessment are both inherited whole by this effort's field.

[S3] `skills/plab-continue-session/SKILL.md`. Class A. Phase 6 (hand-off: wrap records the consumed log's filename), Constraints (never modify the session log being resumed from), Output (this skill produces no files). Read 2026-11-13.

[S4] `skills/plab-wrap-session/references/frontmatter-schema.md`. Class A. The Tier 2 definition of `resumed-from` and its semantics subsection, the sibling field this effort's field sits beside.

[S5] `docs/internal/release-plans/plan_08_escape-and-measure/plan.md`. Class A. Context section (C-04 paragraph); Open Question D1 (W-06 deferred, resolved).

[S6] `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md`. Class A. The release plan that scheduled D-06.

[S7] `skills/plab-wrap-session/SKILL.md`, Evidence Gathering: "If this session resumed with `/plab-continue-session`, add `--resumed-from <that log's file name>`". Class A, read 2026-11-13.

[S8] `skills/plab-wrap-session/scripts/check-log.py`, `check_session_fields()`. Class A, read 2026-11-13. The W-07 session-field checks the new rule sits beside.

### Unverified Claims

None. Every acceptance criterion above cites a verified anchor; none carries `[model-inference]`.

## Open Questions / Decisions

| ID | Title | Status |
|---|---|---|
| OQ-1 | Field name | Decided 2026-11-17 |
| OQ-2 | No escape hatch for genuinely ambiguous outcome | Decided 2026-11-17 |
| R1 | What proves AC-1 and AC-2 | Decided 2026-11-17 |

### OQ-1: Field name

No source document names the new field; both [S1] and [S2] describe it only as "one frontmatter field." This spec first proposed `resumed-from-disposition`. **Decided by the maintainer, 2026-11-17: `resumed-from-outcome`.** Wrap `SKILL.md` already uses "disposition" for the same-arc archive decision, recorded in a log's Summary, and the maintainer's writing rules use one word for one thing. The new name still sits beside `resumed-from` in the Tier 2 table.

### OQ-2: No escape hatch for genuinely ambiguous outcome

AC-1 requires exactly one of three values whenever a genuine resume occurred this session. The roadmap does not anticipate a session whose outcome is genuinely mixed, for example partially fulfilled and then superseded partway through. **Decided by the maintainer, 2026-11-17: no fourth value.** This is consistent with the "invest nothing further" constraint inherited from D-06; the wrap agent uses judgment and commits to the closest of the three.

### R1: What proves AC-1 and AC-2

The 2026-08-23 draft relied on three prose walkthroughs. **Decided by the maintainer, 2026-11-17: also add a rule to `check-log.py`**, which every wrap already runs: `resumed-from` present requires the new field, the new field requires `resumed-from`, and its value must be one of the three. A walkthrough checks the step's text once; the rule checks every log written after it ships.
