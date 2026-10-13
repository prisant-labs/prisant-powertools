---
id: WD-01
title: "plab-resolve-open-items: the in-session walk of open questions and decisions"
type: spec
status: committed
created: 2026-10-05
updated: 2026-10-12
linked-effort: "the maintainer's private walk-decisions strategy brief, 2026-10-04"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 20
source-count: 7
requires-human-review: true
priority: P2
---

# Spec: plab-resolve-open-items, the in-session walk of open questions and decisions

## Task Summary

**Status:** committed
**Last updated:** 2026-10-12 by claude (Opus 5.5), status committed: Requirement 2 anchored to the walk request, fixing the over-gathering found by the v0.7.0 install check
**Linked plan:** `implementation-plan.md` in this folder
**Open questions:** 1 (Q1 Needs info, skipped twice with its default in effect; see Open Questions / Decisions)
**Revisions:** 4

### Acceptance Criteria Fulfillment

- [ ] **AC-1** - Gathering is limited to the conversation and documents touched this session
- [ ] **AC-2** - Items are presented as Q, D or T, with lettered options and a recommendation on D items
- [ ] **AC-3** - Every sourced item names its source document and that document's own item id
- [ ] **AC-4** - Every Q item states its default if skipped; a D or T item states none
- [ ] **AC-5** - A one-line answer parses to the exact item and option or text it names
- [ ] **AC-6** - A skipped D item is left untouched; a skipped Q item proceeds on its stated default
- [ ] **AC-7** - A bare accept-all answer is explicit, never inferred from silence
- [ ] **AC-8** - Write-back touches only the three documented surfaces and never the item's own body
- [ ] **AC-9** - A source document on another branch is never written; its edit is reported as text
- [ ] **AC-10** - Every walk produces a walk record naming every item, its answer, and where it landed
- [ ] **AC-11** - The walk record defaults to `_local/decisions/`, or an existing repository convention
- [ ] **AC-12** - ADR promotion for an architectural decision is offered, never performed automatically
- [ ] **AC-13** - The only GitHub action is printing a ready command and body, never filing it
- [ ] **AC-14** - The skill is auto-invocable, with do-NOT-fire clauses for three named cases
- [ ] **AC-15** - Applying answers needs no extra confirmation; only outward actions do
- [ ] **AC-16** - The skill's own description names the deferred future work rather than omitting it
- [ ] **AC-17** - An item found in several documents is presented once and answered only in its home
- [ ] **AC-18** - A reservation marks an answer provisional; a request for more re-presents the item next round
- [ ] **AC-19** - Every decided item names its follow-up action and where it is tracked, or that none is needed
- [ ] **AC-20** - A T item is answered done, later or drop, recorded in the walk record only

### Currently In Progress

Phases 1 to 5 of `implementation-plan.md` are built and merged (PR #25, 2026-10-08). Next is Phase 6, the live walk in a fresh session, which is what ticks these criteria. No box is ticked yet, because no criterion has been proven by a real walk.

---

## Purpose

`plab-resolve-open-items` turns a request the maintainer already types by hand, roughly a dozen times since early September 2026, into a dependable command [S1]. Given the current conversation, the skill finds every pending question and decision inside it, lists each one with context and a recommendation, and accepts the maintainer's answer as a single line of chat.

This spec covers only the first of two planned slices: the in-session walk, including writing each answer back to where its question came from. A second slice, the `--backlog` mode, is explicitly out of scope here, following the maintainer's answer to D2 (first slice) below [S7]. It is named in Non-Goals below.

The format this skill reads and writes is not new. `references/decisions-section.md` already defines the lettered-option, recommendation, and maintainer-block structure this skill operates on, and the maintainer has already hand-run an equivalent walk at least once over a different project's backlog [S2, S4]. This spec packages that existing design into one skill, rather than inventing a new format.

## Scope

### In Scope

1. Gathering pending items from exactly two sources: the current conversation's own unresolved questions and decisions, and the "Open Questions / Decisions" section of any document the session has read or edited. When the maintainer names one document to walk, such as a decision register, gathering is limited to that document's section instead (D2, option C).
2. Presenting gathered items in three numbered series: Q, a question whose answer only the maintainer has; D, a decision carrying two to four lettered options and a recommendation with a stated confidence level; and T, a task only the maintainer can perform, answered "done", "later" or "drop" (D10).
3. Naming, for every item drawn from a source document, that document and the item's own id there.
4. Accepting a single-line maintainer answer such as "D1 A, D2 B, Q1: the NAS" and parsing each token against the item it names.
5. Writing an answered decision's choice into its source document's maintainer decision block, updating the three surfaces `references/decisions-section.md` defines for a status change, and leaving that item's own body untouched.
6. Writing a walk record for every walk, holding every item, whether answered, skipped, or sourceless, and, for a sourced item, where its answer landed.
7. Writing to a document's maintainer block only when that document's own working-tree branch matches the walk's current branch; otherwise reporting the intended edit as text, never writing it.
8. Offering, never performing, promotion to a MADR architecture decision record for a decided item that meets `references/decisions-section.md`'s own architectural bar.
9. Printing a ready `gh issue create` command and body for a decision where GitHub tracking applies, and never invoking that command.
10. Running from an explicit walk request rather than a manual-only command, carrying a description with do-NOT-fire clauses for three named cases.
11. Treating a skipped decision item and a skipped question item differently: a decision left unanswered is left exactly as found, while a question left unanswered proceeds on its own stated default, recorded in the walk record as assumed rather than decided.
12. Recognizing a bare "ok" or "accept all" answer as an explicit instruction to accept every item's recommendation or default, never inferring acceptance from an answer line's silence.
13. Recording an answer that is more than a choice: a reservation marks the answer provisional, while a request for more context, a question back, or "I don't understand" leaves the item unanswered and re-presents it, with more context, in a further round of the same walk (D9).
14. Presenting an item that appears in several documents once, under its one home, and writing its answer only there, with a pointer in each other copy (D9).
15. Naming, for every decided item, its follow-up action and where that action is tracked, or that none is needed (D9).

### Non-Goals

1. The `--backlog` mode: gathering across a repository's specs, plans, session logs, and any tracker of open items at once; sorting the result into tiers; writing a standalone backlog file. This is slice 2, deferred to its own future spec. Walking one document the maintainer names is in scope (Scope item 1); sweeping every source at once is not.
2. Automatically filing a GitHub issue, or managing a GitHub Projects board, for any item.
3. Adding a "Decision" GitHub issue type to any organization's settings. This spec depends on no such type existing.
4. Applying any default to a skipped decision item. Only a skipped question gets a stated default; a skipped decision is left exactly as found (see In Scope item 11).
5. Gathering across more than the current repository, or across more than the current session's own documents.
6. A published web-page rendering of a walk.
7. A persistent, fleet-wide view of open items, such as a redesigned options board for a resume-style skill, or a living status document a wrap-style skill might write in place. D8 (overlap with the options board and the living status document), deferred by the maintainer to the backlog mode on 2026-10-07, stages this: slice 1, this spec, reads nothing from either surface, and the future `--backlog` slice is where they are expected to merge, because a backlog walk and either surface would otherwise gather the same "waiting on the maintainer" material twice.

### Backlog

Options the maintainer chose not to take now, kept here so they stay with this effort rather than being discarded. Recorded at the maintainer's request on 2026-10-07 [S7].

1. **D2, option A: in-session walk only, then the full backlog sweep.** The design brief's original recommendation. Superseded by option C, which adds walking one named document to slice 1.
2. **D2, option B: the backlog sweep first.** The fallback if walking one named document proves too narrow for the backlog, which is where items age.
3. **The `--backlog` mode itself.** Non-Goal 1. It is also where D8 (overlap with the options board and the living status document) is revisited.
4. **D6, option B: file a GitHub issue after confirmation.** Revisit after the maintainer's pending test of a Decision issue type.
5. **Converting the maintainer's decision register to this format.** Option C can walk a named document only if its decisions section follows `references/decisions-section.md`. The register does not yet, so walking it needs a one-time conversion, outside this spec.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | The only human reader and the only person who answers a walk | Types the walk request, reads the presented items, types the one-line answer, confirms any outward action |
| Running agent (Claude Code or Codex) | Executes the skill | Gathers items, presents them, parses the answer, writes back, writes the walk record |

## Requirements

1. Gathering is limited to two sources: the current conversation's own unresolved items, and the Open Questions / Decisions section of any document the session has read or edited. This is a deliberately narrow slice of a broader gathering design already written for a repository's specs, plans, and session logs; that broader design stays reserved for the `--backlog` mode, outside this spec (see Non-Goals). When the maintainer names one document to walk, gathering is limited to that document's Open Questions / Decisions section. [S1, S3, S7]
2. A document counts as touched when the current session read it or wrote to it before the maintainer asked for the walk. A file read during gathering, in order to find items, is not touched, so the set of sources cannot grow while the walk runs. The design brief itself notes that what counts as pending inside a session is not defined anywhere, so this definition is this spec's own judgment call. [S1, model-inference]
3. Every gathered item is presented under one of three series: Q, a question only the maintainer can answer; D, a decision carrying two to four lettered options and exactly one recommendation with a stated confidence level; or T, a task only the maintainer can perform. [S1, S2, S7]
4. An item drawn from a source document names that document and the item's own id there. An item with no source document is marked as having none, never given a fabricated one. [S1]
5. Every Q item states the default the skill will assume if the maintainer does not answer it. A D item carries no such default, and an unanswered D item is left exactly as found. A T item carries no default either, and an unanswered T item stays open. [S1, S7]
6. The maintainer's answer arrives as one line, such as "D1 A, D2 B, Q1: the NAS". Each token in that line resolves to exactly the item and option, or free text, it names. [S1, S4]
7. A bare answer such as "ok" or "accept all" is recognized as an explicit instruction accepting every item's recommendation or default. Such acceptance is never inferred from an answer line's silence about an item. [S1, model-inference]
8. For a D item with a source document, write-back updates exactly the three surfaces `references/decisions-section.md` defines for a status change: the summary-table row, the subsection header's status, and the maintainer decision block. The item's own Summary, Context, Desired outcome, Options, and Recommendation text is never rewritten. [S2]
9. Write-back to a source document never happens when that document's own working-tree branch differs from the walk's current branch. The walk instead reports the intended edit as text, under the branch it would have targeted. [S1]
10. Every walk produces one walk record, regardless of outcome, naming every presented item, the answer or assumed default each received, and, for a sourced item, where its write-back landed. [S1]
11. The walk record's default location is `_local/decisions/`. When the current repository already defines its own folder for decision or sitting records, the walk record follows that convention instead. [S1]
12. For a decided item meeting `references/decisions-section.md`'s own architectural bar, the skill offers promotion to a MADR architecture decision record; it never performs that promotion without the offer being accepted. [S2]
13. The skill's only GitHub-facing action, for any item, is printing a ready `gh issue create` command and an issue body stating that item's options in full. It never runs the command itself. [S1]
14. The skill carries no `disable-model-invocation` setting and fires from its own description. That description carries explicit do-NOT-fire clauses for a code-walkthrough request, a single standalone decision question, and a status question. [S1, S5, S6]
15. Applying the maintainer's answer line, including write-back to current-branch documents and writing the walk record, happens in the same pass that reads the answer line, without an added confirmation step. [S1, S4]
16. A confirmation step is required only before an action that deletes, pushes, merges, posts externally, or edits a document outside the current repository or the current branch. [S1, S4]
17. The skill's own description and documentation name the `--backlog` mode, automatic GitHub filing, a GitHub Projects board, cross-repository gathering, and a published web-page rendering as deferred or separate work, rather than omitting any of them silently. [S1]
18. When a gathered item appears in more than one document, the walk presents it once and names its home. The home is the tracked document closest to the work, an effort's spec or plan, over an untracked one such as a brief or a register. When two tracked documents tie, the walk asks which is the home, as a Q item. Write-back goes only to the home; each other copy receives a one-line pointer to the home, never a second copy of the answer. [S7]
19. Besides an option letter or free text, an answer may carry a reservation or ask for more. A reservation is recorded verbatim with the answer, and the answer is marked provisional. A request for more context, a question back, or a statement that the item was not understood leaves the item unanswered; the walk re-presents it, with more context, in a further round. The walk record keeps every round. [S7]
20. Every decided item's record names its follow-up action and where that action is tracked, or states that none is needed, so that a decision is never mistaken for work done. The maintainer decision block carries this as an optional `Follow-up` line, which `references/decisions-section.md` is amended to define. [S7]
21. A T item is answered "done", "later" or "drop". Its answer is recorded in the walk record only; slice 1 writes no task back to any document. [S7]

## Acceptance Criteria

**AC-1:** Gathering is limited to exactly two sources per walk: the current conversation's own unresolved items, and the "Open Questions / Decisions" section of a document the session has read or edited. When the maintainer names one document to walk, the walk gathers from that document's section alone. [S1, S3, S7]

**AC-2:** Every gathered item is presented under one of three series: Q for a question only the maintainer can answer, D for a decision carrying two to four lettered options and exactly one recommendation with a stated confidence level, or T for a task only the maintainer can perform. [S1, S2, S7]

**AC-3:** An item drawn from a source document names that document and the item's own id there, for example "D4, from the WD-01 spec's D1." An item with no source document is marked as having none. [S1]

**AC-4:** Every Q item states the default the skill will assume if the maintainer skips it. A D or T item states no default; an unanswered D item is left exactly as found, and an unanswered T item stays open. [S1, S7]

**AC-5:** A one-line answer parses to the exact item, and the option or text, it names. [S1, S4]
  Given: an answer line reading "D1 A, D2 B, Q1: the NAS"
  When: the skill reads it
  Then: D1 resolves to option A, D2 resolves to option B, and Q1's free text is captured verbatim, with no other item changed.

**AC-6:** A skipped item is handled differently by series. [S1]
  Given: an answer line that omits D3 and Q2
  When: the walk applies the given answers
  Then: D3's source document is not written to and D3's status is unchanged, while Q2 proceeds on its own stated default, and the walk record marks Q2's value as assumed rather than decided.

**AC-7:** A bare answer such as "ok" or "accept all" is treated as an explicit instruction accepting every presented item's recommendation or default. Such acceptance is never inferred from an answer line's silence about an item. [S1, model-inference]

**AC-8:** Write-back to a sourced item's document updates only the three surfaces `references/decisions-section.md` names for a status change: the summary-table row, the subsection header's status, and the maintainer decision block. The item's own Summary, Context, Desired outcome, Options, and Recommendation text is never rewritten. [S2]

**AC-9:** A branch mismatch blocks the write. [S1]
  Given: a source document whose own working-tree branch differs from the walk's current branch
  When: the walk applies an answer targeting that document
  Then: no write happens to that document, and the walk's output reports the intended edit as text, naming the branch it would have targeted.

**AC-10:** Every walk produces one walk record, regardless of outcome, naming every presented item, the answer or assumed default it received, and, for a sourced item, where its write-back landed. [S1]

**AC-11:** The walk record's default location is `_local/decisions/`. When the current repository already defines its own folder for decision or sitting records, the walk record is written there instead. [S1]

**AC-12:** For a decided item meeting `references/decisions-section.md`'s own architectural bar, the skill offers promotion to a MADR architecture decision record. It never performs that promotion without the offer being accepted. [S2]

**AC-13:** For any item, the skill's only GitHub-facing action is printing a ready `gh issue create` command and an issue body stating that item's options in full. It never runs the command itself. [S1]

**AC-14:** The skill carries no `disable-model-invocation` setting and fires from a trigger matching an explicit walk request. Its description carries do-NOT-fire clauses for a code-walkthrough request, a single standalone decision question, and a status question. [S1, S5, S6]

**AC-15:** Applying the maintainer's answer line, including write-back to current-branch documents and writing the walk record, happens in the same pass that reads the answer line. A confirmation step is required only before an action that deletes, pushes, merges, posts externally, or edits a document outside the current repository or the current branch. [S1, S4]

**AC-16:** The skill's own description and documentation name the `--backlog` mode, automatic GitHub filing, a GitHub Projects board, cross-repository gathering, and a published web-page rendering as deferred or separate, rather than omitting any of them silently. [S1]

**AC-17:** An item in several documents has one home. [S7]
  Given: a decision that appears in an effort's spec and in a gitignored brief
  When: the walk gathers and the maintainer answers it
  Then: the item was presented once, naming the spec as its home; the answer is written only to the spec; and the brief receives a one-line pointer to the spec, not a second copy of the answer.

**AC-18:** An answer is recorded as what it meant. [S7]
  Given: an answer line reading "D1 A, but I'm not sure. D2: expand this. D3: I don't understand this"
  When: the walk applies it
  Then: D1 is recorded as option A, marked provisional, with the reservation kept verbatim; D2 and D3 are not written anywhere and are re-presented, with more context, in a second round; and the walk record holds both rounds.

**AC-19:** Every item recorded as decided, in the walk record and in its home's maintainer block, names a follow-up action and where that action is tracked, or states that none is needed. [S7]

**AC-20:** A T item is answered "done", "later" or "drop", and its answer appears in the walk record and in no other document. [S7]

## Behavior / Examples

### Example 1: A walk with one decision and one question (grounds AC-2, AC-5, AC-8, AC-10)

The maintainer asks for a walk mid-session. The skill finds one open decision in a spec the session edited earlier, and one question with no source document, drawn from the conversation itself. It presents:

```
D1 (sync authority), from the WD-07 spec's D2. Options A/B/C. Recommendation: A.
Q1 (deploy target). No source document. Default if skipped: staging.
```

The maintainer answers "D1 A, Q1: production". The skill writes D1's choice into the WD-07 spec's maintainer decision block, updating its table row, its subsection header's status, and the maintainer block itself, and leaves the rest of that item's body untouched. It writes a walk record noting Q1's answer as production, decided rather than assumed, and noting where D1's answer landed.

### Example 2: A branch mismatch (grounds AC-9)

A gathered decision's source document lives on a branch other than the one currently checked out. The maintainer answers it along with two other items. The skill writes the other two answers normally, and for this one prints the intended maintainer-block edit as text, naming the branch the document actually lives on, with nothing written to disk.

### Example 3: Silence versus an explicit skip (grounds AC-6, AC-7)

A walk presents D1 through D3 and Q1. The maintainer answers "D2 B, Q1: the NAS, accept the rest". D1 and D3 each already carry a stated recommendation, and "accept the rest" explicitly applies each one. The skill writes D1 and D3 back as their recommended options because the answer said so, not merely because the line left them unmentioned.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Portability | The one-line maintainer answer format, such as "D1 A, Q1: free text", is the contract that works in both Claude Code and Codex. A structured prompt such as Claude Code's own multiple-choice tool may present the same items, but the skill's correctness never depends on one being available. | [S1] |
| Safety | Any tracked output this skill ever writes, including a promoted architecture decision record or a printed GitHub issue body, cites no path under `_local/` and no path outside the current repository, matching this plugin's own public-repository convention. | [S1, S6] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-10-05 | claude | added | Initial draft created |
| 2026-10-07 | claude | changed | Recorded the maintainer's answers to D1 to D8 from walks on 2026-10-06 and 2026-10-07. Renamed the skill `plab-resolve-open-items` (D1) and the backlog mode `--backlog`. Widened gathering to a single named document (D2, option C: Scope item 1, Requirement 1, AC-1; `ac-count` unchanged). Added the Backlog section, rows D2 and D8 so this document is the single home for all nine items, and two new Proposed items, D9 and D10 |
| 2026-10-07 | claude | changed | The maintainer ratified D9 (three answer rules) and D10 (T series). Written into Scope items 2 and 13 to 15, Requirements 3, 5 and 18 to 21, AC-2 and AC-4, and new AC-17 to AC-20; `ac-count` 16 to 20 |
| 2026-10-07 | claude | changed | Linked `implementation-plan.md`, which covers all 20 criteria in seven phases. D9's Follow-up line now names Phase 1 of that plan. No criterion changed |
| 2026-10-12 | claude | changed | Anchored Requirement 2's definition of a touched document to the moment the walk is requested. The v0.7.0 install check showed that "read or written by the session" let a walk make its own sources: an empty headless session listed `_local/` folders and read memory files instead of saying nothing was open, against AC-1. Fixed in the skill as 1.0.1. No criterion changed |

## Sources & Evidence

- **[S1]** The maintainer's private walk-decisions strategy brief, 2026-10-04. Maintainer-local, gitignored, exists on disk. Class A; the primary design source for this spec, read in full.
- **[S2]** `references/decisions-section.md` (this repository). Class A, read in full; defines the item format, the three-surface write-back rule, and the ADR-promotion lifecycle this skill reuses.
- **[S3]** A private toolchain design document in the maintainer's own working notes, its section on the decision and task layer, 2026-08-26. Maintainer-local, gitignored, exists on disk. Class A, read in full; the source for the finding that gathering signals from specs, plans, and session logs is already designed, and for the caution against surfacing every open item at once.
- **[S4]** A hand-built decision-sitting document in the maintainer's own private planning project, 2026-10-03. Maintainer-local, outside this repository, exists on disk. Class A; its opening instructions and its "Answer sheet" section were read directly, and are the precedent for the one-line batch-answer format and for confirming only outward actions.
- **[S5]** `skills/plab-continue-session/SKILL.md` (this repository). Class A; precedent for a narrowed description carrying a do-NOT-fire clause for a status question, rather than disabling model invocation.
- **[S7]** The maintainer's answers to this section's items, given in session on 2026-10-06 and 2026-10-07 and recorded in the maintainer decision blocks below. Class A, direct instruction.
- **[S6]** `AGENTS.md` (this repository). Class A; records the design frame favoring a narrowed description over a manual-only flag, and the convention that a tracked document in this repository cites no gitignored path.

### Unverified Claims

- "A document counts as touched when the current session read it or wrote to it before the maintainer asked for the walk." Appears in Requirements item 2. The design brief names the gap this definition fills, but does not itself define it.
- "A bare answer such as 'ok' or 'accept all' is recognized as an explicit instruction accepting every item." Appears in Requirements item 7 and AC-7. The exact trigger wording is this spec's own choice.

### Gaps

- Whether Codex exposes a structured multiple-choice prompt equivalent to Claude Code's own tool is unverified. The plain-text answer line (Requirements item 6) is the contract this spec relies on regardless of the answer. [S1]
- How reliably the skill locates and edits the correct maintainer decision block, when another session edits the same file at the same time, is untested. This spec's branch guard (AC-9) narrows that risk without removing it. [S1]

## Open Questions / Decisions

**What these statuses mean.** `Decided` and `Deferred` carry the maintainer's answer, given in two walks on 2026-10-06 and 2026-10-07 and recorded in each item's maintainer block; that block is the authoritative record. `Proposed` marks an answer adopted as a working default that the maintainer has not ratified. `Needs info` marks a question only the maintainer can answer. This section is the single home for these items. The design brief [S1] carried the same D1 to D8 and Q1 with fuller analysis, and points here; D2 and D8 were first omitted from this spec as settled by its scope, and are now recorded here so that no item has two homes. D9 and D10 came out of the 2026-10-06 walk and were ratified on 2026-10-07. Q1 is the only item still open, and its default is in effect.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Skill name | `plab-resolve-open-items` | Decided | 2026-10-07 |
| D2 | First slice | Option C: in-session walk, or one named document | Decided | 2026-10-07 |
| D3 | Numbering and item types | Option A | Decided | 2026-10-06 |
| D4 | Where answers are recorded | Option A, provisional; see D9 | Decided | 2026-10-06 |
| D5 | Where the walk record lives | Option A | Decided | 2026-10-07 |
| D6 | GitHub issues | Option A | Decided | 2026-10-06 |
| D7 | Invocation | Option A | Decided | 2026-10-06 |
| D8 | Overlap with the options board and status document | Deferred to the backlog mode | Deferred | 2026-10-07 |
| D9 | Answers that are not a letter, and items with several homes | Option A, all three rules | Decided | 2026-10-07 |
| D10 | A third series for maintainer tasks | Option A, a T series | Decided | 2026-10-07 |
| Q1 | What happened to past walk answers | Skipped twice; default in effect | Needs info | 2026-10-07 |

### D1: Skill name (Decided)

**Summary.** What this skill should be called.

**Context.** An earlier proposal for the same functionality used a different name. The maintainer's own recent phrasing favors "walk decisions," and the name is also this skill's strongest trigger phrase. [S1]

**Desired outcome.** The name matches words the maintainer already types, and covers both this spec's in-session walk and a later backlog mode.

**Options / approaches.**

* **Option A:** `plab-walk-decisions`. Matches the maintainer's own phrasing and this plugin's verb-first naming pattern.
* **Option B:** `plab-decision-sitting`. Matches the earlier proposal and a hand-built precedent, but names the rarer backlog case.
* **Option C:** `plab-decisions`. Short and neutral, but reads as a record viewer rather than an action.

**Recommendation.** Option A, which this spec adopts throughout as its working default.

**Confidence:** Medium.

---

> **Maintainer decision:** Decided 2026-10-07 by jp
>
> * **Status:** Decided
> * **Choice:** None of the listed options: `plab-resolve-open-items`, reached over two rounds.
> * **Reasoning:** The maintainer disliked "sitting", was lukewarm on "walk decisions", and noted that a walk holds questions as well as decisions. Weighed on 2026-10-06 and 2026-10-07: `plab-walk-pending`, `plab-open-items`, `plab-unblock` and `plab-resolve-open`. "Resolve" names what the skill does, getting items answered and written back, and covers questions, decisions and tasks; "items" keeps "open" an adjective rather than a second verb.
> * **Decided by / date:** jp / 2026-10-07

### D2: First slice (Decided)

**Summary.** Which case gets built first: the in-session walk, or the walk over the whole backlog.

**Context.** The in-session walk is frequent and small. The backlog walk is rare, large, and has been built by hand four times. The design brief [S1] notes that the real problem is aging, and items age in the backlog, while its recommendation for the in-session walk rested on how often the prompt is typed. This item was first treated as settled by this spec's scope; it is recorded here once the maintainer asked for the fuller context.

**Desired outcome.** The first release gets used within a week, and it reaches the backlog where items age.

**Options / approaches.**

* **Option A:** The in-session walk first, the full backlog sweep next.
* **Option B:** The backlog sweep first.
* **Option C:** The in-session walk first, which can also be pointed at one document the maintainer names, such as a decision register. The full sweep comes later. A named document must follow `references/decisions-section.md` for write-back to work.

**Recommendation.** Option C. It keeps slice 1 small and still lets the maintainer walk the backlog file where items age.

**Confidence:** Medium-low. A hand walk of the decision register would test it cheaply before anything is built.

---

> **Maintainer decision:** Decided 2026-10-07 by jp
>
> * **Status:** Decided
> * **Choice:** Option C. Options A and B are recorded in this spec's Backlog rather than discarded.
> * **Reasoning:** Chosen after the maintainer asked for more context ("expand this and provide more context") and for the mode not to be called "sitting"; it is `--backlog`.
> * **Decided by / date:** jp / 2026-10-07

### D3: Numbering and item types (Decided)

**Summary.** How items inside a walk should be numbered and typed.

**Context.** Earlier hand-built walks used three different numbering schemes, and one of them let a group letter collide with an option letter. [S1]

**Desired outcome.** Every answer is unambiguous when typed as one line in chat.

**Options / approaches.**

* **Option A:** Two series, Q for maintainer-only information and D for a lettered decision, uppercase options, no group letters; a clarification counts as a Q.
* **Option B:** One D series only, with a question marked by the Needs info status instead of its own series.
* **Option C:** A section letter plus a number, with lowercase options, matching an existing hand-built precedent.

**Recommendation.** Option A, which this spec adopts throughout Scope, Requirements, and Acceptance Criteria above.

**Confidence:** High.

---

> **Maintainer decision:** Decided 2026-10-06 by jp
>
> * **Status:** Decided
> * **Choice:** Option A, the Q and D series with uppercase options.
> * **Reasoning:** Accepted as recommended. The maintainer asked whether other types exist; the answer offered was one, tasks only the maintainer can perform, now D10.
> * **Decided by / date:** jp / 2026-10-06

### D4: Where answers are recorded (Decided)

**Summary.** Where an answer goes once the maintainer gives it.

**Context.** `references/decisions-section.md` already makes a source document's maintainer block the authoritative record for a sourced item. A separate walk record is still useful for an item with no source document. [S1, S2]

**Desired outcome.** An answer sits beside its own question, and a whole walk can still be reviewed later as one record.

**Options / approaches.**

* **Option A:** Write back to the source document's maintainer block for a sourced item, and keep one walk record covering every item, including where each sourced item's answer landed.
* **Option B:** Keep one walk record only, and leave every source document untouched.
* **Option C:** Write a MADR architecture decision record for every decided item.

**Recommendation.** Option A, which is this spec's write-back and walk-record design above (Requirements items 8 and 10).

**Confidence:** Medium, because write-back reliability stays the open implementation risk (see Gaps above).

---

> **Maintainer decision:** Decided 2026-10-06 by jp
>
> * **Status:** Decided
> * **Choice:** Option A, provisionally.
> * **Reasoning:** In the maintainer's words: "A. However this feels a little incomplete and unsettled and I can't articulate why." Three candidate causes were offered back, and D9 carries them as a proposal: one item with several homes, answers that are not letters, and decided-is-not-done.
> * **Decided by / date:** jp / 2026-10-06

### D5: Where the walk record lives (Decided)

**Summary.** Whether the walk record is tracked or local, and where it is written.

**Context.** A walk record can carry candid notes, similar to a session log, and this repository is public. [S1]

**Desired outcome.** Nothing private ships by accident, and the record stays findable by a later session.

**Options / approaches.**

* **Option A:** Default to `_local/decisions/`; follow an existing decision or sitting-record folder convention instead, when the current repository already has one.
* **Option B:** Always tracked, under a documented decisions folder in the repository.
* **Option C:** Always local, with no repository-convention override.

**Recommendation.** Option A, which this spec adopts as AC-11.

**Confidence:** High.

---

> **Maintainer decision:** Decided 2026-10-07 by jp
>
> * **Status:** Decided
> * **Choice:** Option A.
> * **Reasoning:** Follows from the rule of thumb the maintainer accepted on 2026-10-07: the outcome is tracked, the conversation is local. A walk record is conversation; its outcomes reach tracked files through write-back and ADRs. The maintainer's further questions on ADR criteria, frontmatter links and folder layout belong to a separate repository-layout effort, not this spec.
> * **Decided by / date:** jp / 2026-10-07

### D6: GitHub issues (Decided)

**Summary.** What role GitHub issues play in a walk.

**Context.** No "Decision" issue type exists in the maintainer's GitHub organization today, and this repository has never filed an issue. [S1]

**Desired outcome.** GitHub becomes part of the workflow only once the maintainer's own behavior shows it is a place they look.

**Options / approaches.**

* **Option A:** The skill prints a ready `gh issue create` command and body per item; it never files on its own.
* **Option B:** A flag files the issue directly once the maintainer confirms.
* **Option C:** Leave GitHub out of this skill entirely.

**Recommendation.** Option A, which this spec adopts as AC-13.

**Confidence:** Medium, because it depends on a usage test that has not yet run.

---

> **Maintainer decision:** Decided 2026-10-06 by jp
>
> * **Status:** Decided
> * **Choice:** Option A, print a ready command and never file.
> * **Reasoning:** In the maintainer's words: "A i guess". Low-conviction acceptance; option B is kept in this spec's Backlog.
> * **Decided by / date:** jp / 2026-10-06

### D7: Invocation (Decided)

**Summary.** Whether the skill can start itself from the model's own reading of the conversation, or only by an explicit command.

**Context.** Two sibling skills in this plugin run only by explicit command. Two others moved from that mode to automatic invocation guarded by an explicit do-NOT-fire clause, which this plugin's own documentation records as the better instrument. [S1, S5, S6]

**Desired outcome.** The skill fires on a genuine walk request, and never on a code walkthrough, a single standalone decision question, or a status question.

**Options / approaches.**

* **Option A:** Automatic invocation, with a do-NOT-fire clause for those three cases.
* **Option B:** Manual only, requiring an explicit command every time.

**Recommendation.** Option A, which this spec adopts as AC-14.

**Confidence:** Medium, because trigger accuracy is only provable after real use.

---

> **Maintainer decision:** Decided 2026-10-06 by jp
>
> * **Status:** Decided
> * **Choice:** Option A, automatic invocation with do-NOT-fire clauses.
> * **Reasoning:** Accepted as recommended.
> * **Decided by / date:** jp / 2026-10-06

### D8: Overlap with the options board and status document (Deferred)

**Summary.** Whether this skill should be designed together with two other proposals that show what is waiting on the maintainer.

**Context.** Three lists already show what is waiting: each session log's "Waiting on You" section, the maintainer's decision register, and a proposed options board that would show the next choices when a session resumes. A fourth, a living status page, is also proposed. A backlog walk would read the same material. The in-session walk reads none of it.

**Desired outcome.** One design for one surface, not several that overlap.

**Options / approaches.**

* **Option A:** Fold the options board into this effort now.
* **Option B:** Keep them separate; this skill only reads what the wrap writes.
* **Option C:** Decide the options board and status page first, then return to this skill.
* **Option D:** Staged: separate for slice 1, merged when the backlog mode is designed.

**Recommendation.** Option D. Slice 1 needs nothing from either surface.

**Confidence:** Low. This is a judgment about scope.

---

> **Maintainer decision:** Deferred 2026-10-07 by jp
>
> * **Status:** Deferred
> * **Choice:** Deferred to the backlog mode, where it is revisited (Backlog item 3).
> * **Reasoning:** The in-session walk touches neither surface. Answered explicitly after a plain-language re-explanation; the first presentation was not understood.
> * **Decided by / date:** jp / 2026-10-07

### D9: Answers that are not a letter, and items with several homes (Decided)

**Summary.** Three rules that would resolve the reservation the maintainer attached to D4.

**Context.** The 2026-10-06 walk was this design's first real test, and the reply had more shapes than the spec handles: a letter, a letter "i guess", a letter with a reservation, a letter plus a question back, "expand this", and "I don't understand this". Requirements items 5 to 7 know only answered and skipped, so three of those replies would have been recorded as skips. The same walk showed one item living in several documents: this spec's D1 to D7, the design brief's D1 to D8, and a row in another repository's open-items list. And a decision recorded as made can sit unbuilt, as the maintainer's register showed the same day, with no status that says so.

**Desired outcome.** Every reply is recorded as what it meant, every item has one home, and a decision does not look finished when only its ruling exists.

**Options / approaches.**

* **Option A:** Adopt all three rules. One home per item, with every other copy pointing to it. Answer states for "with reservation" and "needs more context", which re-present the item in the next round rather than record it. Each decided item names its follow-up action and where that is tracked.
* **Option B:** Adopt only the answer states, the change the 2026-10-06 walk demonstrated directly.
* **Option C:** Leave the spec as it is and revisit after the first build.

**Recommendation.** Option A. All three causes were observed in this effort's own walk, not hypothesized.

**Confidence:** Medium.

---

> **Maintainer decision:** Decided 2026-10-07 by jp
>
> * **Status:** Decided
> * **Choice:** Option A, all three rules: one home per item, answer states for a reservation and for a request for more, and a follow-up named for every decided item.
> * **Reasoning:** Selected as recommended, once the item was explained as a spec change parked as Proposed. Written into Requirements 18 to 20 and AC-17 to AC-19.
> * **Follow-up:** Implementation amends `references/decisions-section.md` to define the optional `Follow-up` line; tracked in Phase 1 of this effort's `implementation-plan.md`.
> * **Decided by / date:** jp / 2026-10-07. Proposed by claude the same day, raised in the walk as its D10; the maintainer said they did not know what to do with it, and it was parked here as Proposed.

### D10: A third series for maintainer tasks (Decided)

**Summary.** Whether a walk should carry a T series for actions only the maintainer can perform.

**Context.** The maintainer asked whether types other than Q and D exist. One does: a session log's "Waiting on You" list mixes decisions with tasks such as restarting the harness, deleting a temporary folder, or wrapping a session in another repository. A task is neither a question nor a choice; its answer is "done", "later" or "drop". Approvals of outward actions, such as merging a pull request, stay D items with two options.

**Desired outcome.** Every item a walk shows has an answer shape that fits it.

**Options / approaches.**

* **Option A:** Add a T series, answered "done", "later" or "drop". The letter does not collide with option letters A to D.
* **Option B:** Keep two series and leave tasks out of walks.
* **Option C:** Treat a task as a D item with options "done" and "not yet".

**Recommendation.** Option A for the backlog mode, where tasks are common. In-session walks rarely carry them, so slice 1 may need only to recognise one.

**Confidence:** Medium.

---

> **Maintainer decision:** Decided 2026-10-07 by jp
>
> * **Status:** Decided
> * **Choice:** Option A, a T series answered "done", "later" or "drop".
> * **Reasoning:** Selected as recommended, with the note that it matters mostly for the backlog mode and that slice 1 need only recognise a task. Written into Scope item 2, Requirements 3, 5 and 21, AC-2, AC-4 and AC-20.
> * **Follow-up:** None beyond building the criteria above.
> * **Decided by / date:** jp / 2026-10-07. Proposed by claude the same day, raised in the walk as its D11 and parked here as Proposed.

### Q1: What happened to past walk answers (Needs info)

**Summary.** After roughly a dozen earlier in-session walks the maintainer typed by hand, did any answer ever need to be found again later, or was each one acted on at once and then forgotten?

**Context.** This decides whether write-back genuinely belongs in this first slice, or whether a lighter, format-only skill would already have been enough. [S1]

**Default if skipped.** This spec assumes an answer mattered later at least some of the time, so write-back and the walk record both stay in this slice's scope (Requirements items 8 through 11).

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Needs info
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
