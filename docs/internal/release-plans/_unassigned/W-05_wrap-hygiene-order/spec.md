---
id: W-05
title: "plab-wrap-session: write the log first, then ask the hygiene proposals in one batch"
type: spec
status: committed
created: 2026-11-03
updated: 2026-11-03
linked-effort: "the maintainer's walk ruling of 2026-10-19 that placed W-05 in the backlog, and the maintainer's instruction of 2026-11-03 to implement it with hygiene order B"
linked-plan: null
linked-release: null
ac-count: 6
source-count: 7
requires-human-review: true
target-release: null
priority: P2
---

# Spec: plab-wrap-session writes the log first, then asks the hygiene proposals in one batch

## Task Summary

**Status:** committed. Built as `plab-wrap-session` 1.9.0, not yet released. AC-6 waits on the first real wrap under 1.9.0.
**Last updated:** 2026-11-03 by claude (Opus 5.5), written and built under the maintainer's instruction of 2026-11-03
**Linked plan:** none; the build followed this spec directly
**Open questions:** 1, D2, built on its recommendation as a working default (see Open Questions / Decisions)
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [x] AC-1: `SKILL.md` writes the log before asking any hygiene question, and checks it after the amendment
- [x] AC-2: The proposals are numbered, asked in one message, and silence approves nothing
- [x] AC-3: Exactly three auto actions run without asking, each recorded
- [x] AC-4: Parked items are carried forward like Waiting on You items
- [x] AC-5: A log with unanswered proposals, and its amended copy, both pass `check-log.py`
- [ ] AC-6: The first real deep wrap under 1.9.0 follows the order

### Currently In Progress

None. Built on 2026-11-03 on `feat/wrap-hygiene-order-b`. Evidence: AC-1 to AC-3 by reading the changed `SKILL.md` and `references/hygiene-sweep.md`; AC-4 by `test-derive-log-facts.py` (91 checks, 5 new), where a canary that counts indented sub-bullets fails two; AC-5 by `check-log.py` run on a fixture log before and after its amendment. AC-6 waits on a real wrap, because a wrap is run only when the maintainer asks for one.

---

## Purpose

Through 1.8.2 the wrap ran its hygiene sweep "before writing the log", but nothing told it to wait for the maintainer's answers to its proposals. Surrounding-document edits were proposed after the log, and the self-check ran once, straight after writing. Two logs were edited after their wraps to record approvals given later [S1]. Separately, nothing carried a log's Parked section into the next log, so a parked item lasted one log and then vanished [S5].

This spec fixes the order of a wrap and closes the Parked gap. The maintainer chose to write the log first and ask afterwards (D1), so that a terminal closed while a question is open still leaves a complete log.

## Scope

### In Scope

1. `skills/plab-wrap-session/SKILL.md`: a Wrap Order section, the hygiene sweep's resolution, Evidence Gathering steps 6 and 7, Surrounding Document Updates, the Log Self-Check, and the constraints.
2. `skills/plab-wrap-session/references/hygiene-sweep.md`, `session-log-template.md` and `doc-update-rules.md`.
3. `skills/plab-wrap-session/scripts/derive-log-facts.py` and its test, for the Parked carry-forward.
4. The version bump to 1.9.0 and the documents that name the version or describe the old order.

### Non-Goals

1. **The usage suggestions and parallel-session fixes** proposed alongside the hygiene order on 2026-10-24. The maintainer's instruction of 2026-11-03 named the order only [S3].
2. **Showing Parked items in `plab-continue-session`'s display.** The resume skill still omits Parked; this spec only stops the wrap from dropping it.
3. **A mechanical gate on the order itself.** `check-log.py` reads one file at one moment and cannot tell whether a question was asked before or after it was written. The order is the agent's instruction, proven by AC-6.

## Users / Actors

- **The maintainer**, who answers the hygiene proposals and reads the log at the next resume.
- **The wrapping agent**, which follows the order.
- **`plab-continue-session`**, which reads the log and shows unanswered proposals as re-decidable.

## Requirements

1. The wrap writes the session log before it asks any hygiene question. It drafts every proposal first, numbers them `H1` to `Hn`, and writes each into the log's Hygiene Sweep section with `Status: unanswered` [S3].
2. The same-arc archive proposal and every intended surrounding-document edit are proposals in the same batch, so a wrap asks one round of questions [S4].
3. After writing, the wrap runs `check-log.py`. With no proposals, the wrap is done. Otherwise it presents every proposal in one message, ending with an answer line such as `H1 y, H2 n`, and carries out exactly the approved proposals [S2, S3].
4. Silence approves nothing. A number the answer leaves out stays `unanswered`; only `ok`, `all y` or an equivalent explicit phrase approves every proposal. This is the rule `plab-resolve-open-items` applies to its own answer line [S7].
5. After carrying out the answers, the wrap amends each status word, in the Hygiene Sweep section and the continuation prompt, to `done` or `failed` with the result, or `declined`, and runs `check-log.py` again. The second clean run completes the wrap.
6. Three actions run without asking, before the log is written: `git branch -d` on a local branch whose upstream is gone, `git worktree prune`, and `organize-logs.py --apply` on a plan with no collisions. Each is recorded as an `auto:` line with its command and output. Every other action asks, including `git fetch --prune` (D2) [S2, S6].
7. The constraint that nothing beyond the log changes without confirmation names the three auto actions as its only exceptions, so the skill does not contradict itself [S2].
8. `derive-log-facts.py` reports the newest log's top-level Parked items as `parked`, by the same rule as Waiting on You, and the wrap carries them forward verbatim, dropping only items the session resolved or promoted [S2, S5].

## Acceptance Criteria

**AC-1:** `skills/plab-wrap-session/SKILL.md` carries a Wrap Order section whose steps run in this order: gather facts, draft numbered proposals, run auto actions, write the log with every proposal `unanswered`, run `check-log.py`, ask, carry out the approved proposals, amend, run `check-log.py` again. No sentence in the skill or its references tells the agent to ask a hygiene question before the log exists. [S3, S4]

**AC-2:** `references/hygiene-sweep.md`'s resolution protocol presents every proposal in one message with an `H1 y, H2 n` answer line, states that silence approves nothing, and defines the status words `unanswered`, `done`, `failed` and `declined`. [S3, S7]

**AC-3:** `references/hygiene-sweep.md` lists exactly three auto actions with their record format, and names `git fetch --prune` as an action that asks. `SKILL.md`'s constraints name those three as the only exceptions to asking. [S2, S6]

**AC-4:** Given a newest log whose Parked section holds two top-level items and one indented sub-bullet, `derive-log-facts.py --json` reports exactly the two items, and the default digest prints them. A log with no Parked section yields an empty list, and no log yields null. Making the extractor count indented sub-bullets makes `test-derive-log-facts.py` fail. [S5]

**AC-5:** A deep-mode fixture log whose Hygiene Sweep section holds an `auto:` line and two `Status: unanswered` proposals passes `check-log.py`, and so does the same log after the two statuses are amended. [S4]

**AC-6:** The first real deep wrap under 1.9.0 that has at least one proposal writes its log before asking, and its amended log passes `check-log.py`. [S3]

## Behavior / Examples

### Example 1: A wrap with two proposals

The facts show two unpushed commits and a stale version line in a skill README. The wrap drafts H1 (push) and H2 (update the line), writes the log with both `unanswered`, and runs `check-log.py` clean. It asks both in one message. The maintainer answers `H1 y, H2 n`. The wrap pushes, changes H1 to `done` and H2 to `declined` in the log and the continuation prompt, and runs `check-log.py` clean again.

### Example 2: The terminal closes before the answer

The same wrap is interrupted after it asks. The log already exists, with H1 and H2 `unanswered`, and the next `/plab-continue-session` shows both under its declined-or-unanswered hygiene proposals.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Cost | Writing first adds one edit and one `check-log.py` run, and only to wraps that asked a question. A wrap with no proposals costs what it did before. | [S3] |
| Safety | An auto action is local, reversible from what the log records, and refused by git or the script when its precondition fails. | [S2, S6] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-11-03 | claude | added | Initial spec, written and built in one pull request under the maintainer's instruction of 2026-11-03, following the shape ruled on 2026-10-19 with the order reversed. |

## Sources & Evidence

- **[S1]** The session logs of 2026-10-09 and 2026-10-16, both edited after their wraps to record approvals given later. Maintainer-local, gitignored. Class A.
- **[S2]** The maintainer's walk ruling of 2026-10-19, which decided W-05's shape: one numbered batch, approved actions carried out before the log is final, the narrow auto list, the constraint change, and Parked carried forward. Maintainer-local, gitignored. Class A.
- **[S3]** The maintainer's instruction of 2026-11-03 to implement the wrap updates with hygiene order B. In session. Class A.
- **[S4]** `skills/plab-wrap-session/SKILL.md` as of 1.8.2: the sweep ran "before writing the log", Surrounding Document Updates came after it, and the self-check ran once. Class A.
- **[S5]** `skills/plab-continue-session/references/handoff-display.md`, which leaves the Parked list out of the display, and `skills/plab-wrap-session/scripts/derive-log-facts.py` as of 1.8.2, which extracted only Waiting on You. Class A.
- **[S6]** `docs/internal/release-plans/_unassigned/W-02_derived-log-facts/spec.md`, decision D4, and `skills/plab-continue-session/references/reconciliation.md`: a pruning fetch deleted a remote-tracking ref without confirmation on 2026-09-25. Class A.
- **[S7]** `skills/plab-resolve-open-items/references/answer-line.md`, whose answer grammar never infers acceptance from silence. Class A.

### Unverified Claims

- AC-6 is unproven until a real wrap runs under 1.9.0.
- [S1] and [S2] live outside this repository.

## Open Questions / Decisions

**What these statuses mean.** D1 was decided by the maintainer. D2 is `Open`: the build followed its recommendation as a working default, so a walk can ratify or overturn it.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Whether the wrap asks before or after writing the log | Option B | Decided | 2026-11-03 |
| D2 | Whether `git fetch --prune` is an auto action | (none) | Open | (none) |

### D1: Whether the wrap asks before or after writing the log (Decided)

**Summary.** The order of the two steps that close a wrap: asking the hygiene proposals, and writing the log.

**Context.** The 2026-10-19 ruling put the questions first [S2]. On 2026-10-24 a second order was proposed: write the log first, then amend it with the answers.

**Desired outcome.** Every wrap leaves a log, and the log records what the maintainer answered.

**Options / approaches.**

* **Option A:** Ask first, then write the log. The log is written once, but a terminal closed before the answer leaves no log at all.
* **Option B:** Write the log first, ask, then amend it. A log always exists, at the cost of one edit and one more `check-log.py` run on wraps that asked something.

**Recommendation.** Option B. Confidence: medium. A lost log costs a whole session's record, and the extra edit costs a few cents.

---

> **Maintainer decision:** Decided 2026-11-03 by jprisant
>
> * **Status:** Decided
> * **Choice:** Option B
> * **Reasoning:** The maintainer asked for the recommended wrap updates with order B.
> * **Follow-up:** Built as `plab-wrap-session` 1.9.0 on 2026-11-03; AC-6 waits on the first real wrap.
> * **Decided by / date:** jprisant / 2026-11-03

### D2: Whether `git fetch --prune` is an auto action

**Summary.** The 2026-10-19 ruling listed `git fetch --prune` among the actions a wrap runs without asking [S2]. This build leaves it out.

**Context.** A pruning fetch deleted a remote-tracking ref without confirmation on 2026-09-25, and W-02's D4 made `derive-log-facts.py` fetch with `--no-prune` for that reason [S6]. A pruned ref can be recreated only by fetching it again while the remote branch still exists.

**Desired outcome.** No action the wrap takes unasked can lose something the maintainer has not seen.

**Options / approaches.**

* **Option A:** Leave `git fetch --prune` out of the auto list; it is proposed and asked like any other action.
* **Option B:** Restore it to the auto list, as the 2026-10-19 ruling had it.

**Recommendation.** Option A. Confidence: medium. The other three auto actions can be undone from what the log records, and a pruning fetch cannot, which is the reason W-02 D4 gave. Working default: built on this recommendation on 2026-11-03; not yet ratified.
