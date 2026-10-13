---
id: WD-01
title: "Implementation plan: plab-resolve-open-items, the in-session walk of open questions and decisions"
type: implementation-plan
status: complete
created: 2026-10-07
updated: 2026-10-12
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 7
---

# Implementation plan: plab-resolve-open-items

**For whoever executes this.** Steps use checkbox syntax and phases run in order. Where a step cites a line number, re-verify it first, because a sibling effort landing in between will have moved it.

**Goal:** When the maintainer asks to walk through what is pending, `plab-resolve-open-items` gathers every open question, decision and task from the current session, presents them as Q, D and T items, and takes a one-line answer. It writes each answer back to the item's one home document and records the whole walk in a walk record.

## What proves what

This skill is mostly instructions to a model, so most of its acceptance criteria can only be proven by watching it run. A green checker does not mean the skill works. The criteria fall into three groups by the kind of proof available.

| Proof | Criteria | Where |
|---|---|---|
| A deterministic checker, canary-proven | AC-8 (three surfaces only), AC-10 (walk record exists and is complete), AC-19 (every decision names its follow-up), AC-20 (T answers stay in the record), and the record halves of AC-6 (skips by series) and AC-18 (rounds) | Phase 3 |
| A grep against committed text | AC-14 (no `disable-model-invocation`, three do-NOT-fire clauses) and AC-16 (deferred work named) | Phases 2, 4 and 5 |
| Model behaviour, observed in a live walk | AC-1 to AC-7, AC-9, AC-11 to AC-13, AC-15, AC-17 and AC-18, plus the trigger half of AC-14 | Phase 6 only |

Phase 6 is therefore the phase that decides whether this effort is done. Phases 1 to 5 make it possible.

## The specimen already exists

AU-01 (the audit skill) had to produce its specimen by hand before writing the skill. This effort does not. The three-round walk of 2026-10-06 and 2026-10-07 is the specimen: its walk record lives in the maintainer's gitignored decisions folder, and its answers live in the eleven maintainer blocks of `spec.md`. That walk drew seven reply shapes, and the spec's D9 (three answer rules) exists because of them.

That record predates the format this plan defines. It has no State or Follow-up column, and one item ("PR-20 merge") carries no series letter. Phase 3 therefore treats it as the **first canary**: the record checker must exit 1 on it, as `bundle-check.py` rule R8 exited 1 on the bundle that predated R8. The committed sample is a rewrite of it into the final format, scrubbed of every path that is gitignored or machine-specific.

## Interpretations this plan makes

None of these adds an acceptance criterion. Each one reads a criterion where the spec leaves the mechanics open. The maintainer confirmed I1, I2, I4 and I5 as written in a walk on 2026-10-07 and 2026-10-08, and confirmed I3 in an amended form, replacing a proposed `Reservation` line with a `Provisional` status. I6 came out of that walk, and the maintainer confirmed it the same day.

| # | Criterion | The reading |
|---|---|---|
| I1 | AC-16 (deferred work named) | The frontmatter description names only the `--backlog` mode, because it is the deferred feature a user would ask for. The SKILL.md body and the usage README name all five. AC-16 says "description and documentation", and the frontmatter description is always-on context, paid for in every session. |
| I2 | AC-8 and AC-6 (write-back and skips) | An answered Q item that has a home document is written back like a D item. D4 (where answers are recorded) chose write-back "for a sourced item", not for D items only. A skipped Q item is written nowhere but the walk record, where it is marked assumed. |
| I3 | AC-18 (reservations) | A provisional answer takes the status `Provisional` on all three surfaces, and the maintainer's words of doubt are quoted verbatim in its `Reasoning` line. There is no separate field for them. `Provisional` joins a status list of seven, the maintainer's own: Open and Needs info before an answer, then Decided, Provisional, Deferred, Canceled and Superseded. `Canceled` replaces `Withdrawn`, which no document used. Phase 1 writes the list. |
| I4 | AC-17 (one home) | A copy of an item outside its home receives a pointer on the three surfaces, not the answer: `Resolution` reads `See <home path> <id>`, the status mirrors the home's status, and the maintainer block's `Choice` reads `Recorded in <home path> <id>`. A pointer block carries no `Follow-up` line, because the follow-up lives in the home. |
| I5 | AC-9 (branch guard) | A document's branch is the branch checked out in the working tree that contains it. A gitignored document in the current working tree is on the current branch. A document in another worktree of this repository is never written. A document in another repository needs a confirmation first, under AC-15. |
| I6 | AC-18 (rounds) | **Confirmed by the maintainer, 2026-10-08.** A reply that holds both a choice and a question records the choice, and the question is answered in the same round. Only a reply with no choice is re-presented. Requirement 19 says a question back leaves an item unanswered, but it does not say which wins when a reply holds both. Both hand walks recorded such replies as decided. |

## Preconditions, verify before starting

- [x] PR #22 (D9 and D10 ratified into the spec) merged as `bf6c675`, with all four CI checks green. Verified 2026-10-07.
- [x] This terminal loads plugin 0.6.1. Verified 2026-10-07 from a skill's base directory line.
- [x] This plan is merged to `main`, as PR #23 (`2d8a483`), 2026-10-08.
- [x] The maintainer confirmed I1 to I6 on 2026-10-08, I3 in an amended form.
- [ ] A branch exists for the build: `feat/plab-resolve-open-items`, cut from `main` after this plan merges.

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | The shared decisions format has seven statuses and defines `Follow-up` | AC-18, AC-19 (format halves) | agent | **Done** 2026-10-08, `d5b21fd` |
| P2 | The skill is authored under `skills/` | AC-1 to AC-20, authored | agent | **Done** 2026-10-08, `6031624` |
| P3 | The walk checker exists, runs in CI, and is proven to fail | AC-6, AC-8, AC-10, AC-18, AC-19, AC-20 (deterministic halves) | agent | **Done** 2026-10-08, `a55b8de`, 14 canaries |
| P4 | `library.json` registers ten skills at plugin 0.7.0, and the manifests agree | AC-14 (invocation setting) | agent | **Done** 2026-10-08, `d3d295d` |
| P5 | Every human-facing file names the new skill | AC-16 (documentation half) | agent | **Done** 2026-10-08, `29108f1` |
| P6 | A live walk proves the behaviour | AC-1 to AC-15 and AC-17 to AC-20 (behaviour, including AC-14's trigger test) | agent and maintainer | **Done** 2026-10-12, against 1.0.1; all 20 criteria pass. Run headless and relayed; see the note under Phase 6 |
| P7 | v0.7.0 ships with `plab-audit` 1.1.0 and loads from the cache | N/A (release) | agent and maintainer | **Released ahead of P6** by maintainer ruling, 2026-10-09; see the note under Phase 6 |

---

## Phase 1: Seven statuses and a Follow-up line in the shared format

**Goal:** `references/decisions-section.md` carries the maintainer's seven-status list and defines the optional `Follow-up` line, so a block the walk writes is conforming rather than improvised. Without this phase, the write-back step in Phase 2 has no definition to follow.

**Files:** `references/decisions-section.md` (modify).

**Fulfills:** AC-18 and AC-19, format halves. Requirement 20 of the spec requires the `Follow-up` amendment by name. The status list is the maintainer's ruling of 2026-10-08, recorded as interpretation I3.

**Steps:**

1. [ ] **Replace the status vocabulary table** under the line `**Status vocabulary.**` (lines 49 to 55 at the time of writing). Before:

   ```markdown
   | Status | Meaning |
   |--------|---------|
   | `Open` | Awaiting maintainer decision. Default for a newly added item. |
   | `Decided` | Maintainer has chosen. Outcome and reasoning recorded in the maintainer block. |
   | `Deferred` | Intentionally postponed. The decision is to not decide yet; note when to revisit. |
   | `Needs info` | Blocked on clarification. Usually triggers a re-run of the producing skill. |
   | `Withdrawn` | No longer relevant. Keep the row for traceability; do not delete history. |
   ```

   After:

   ```markdown
   | Status | Meaning |
   |--------|---------|
   | `Open` | Awaiting maintainer decision. Default for a newly added item. |
   | `Needs info` | Blocked on clarification. Usually triggers a re-run of the producing skill. |
   | `Decided` | Maintainer has chosen. Outcome and reasoning recorded in the maintainer block. |
   | `Provisional` | Maintainer has chosen but said they were unsure. The choice is in force, and the maintainer's words of doubt are quoted verbatim in `Reasoning`. |
   | `Deferred` | Intentionally postponed. The decision is to not decide yet; note when to revisit. |
   | `Canceled` | No longer relevant. Keep the row for traceability; do not delete history. |
   | `Superseded` | Replaced by a later decision. `Choice` names the item or record that replaced it. Keep the row for traceability. |

   The first two statuses come before an answer. The other five are what an answer can be. `Canceled` replaced `Withdrawn` in 2026-10; no document had used the old name.
   ```

2. [ ] **Find the filled-block example.** It is the fenced block that follows the sentence "When the maintainer decides, the block fills:" (lines 99 to 111 at the time of writing) and ends with the line `> * **Decided by / date:** jp / 2026-06-16`.
3. [ ] Immediately after that fenced block, and before the sentence beginning "Optionally, a clarification request can follow", insert this text:

   ````markdown
   An optional `Follow-up` line may follow `Reasoning`:

   ```markdown
   > * **Follow-up:** <the action this decision requires, and where that action is tracked>, or "None needed."
   ```

   `Follow-up` separates a decision from the work it causes. A decision can be recorded as made and still sit unbuilt, with no status that says so. The line names what has to happen next and where that is tracked, or states that nothing does. `plab-resolve-open-items` writes it on every item it records as `Decided` or `Provisional`.
   ````

4. [ ] Do not change the Lifecycle section. The release plans' drifted labels (Ratified, Proposed, Resolved, Needs ruling and Applied) are mapped onto the seven statuses by the separate layout effort, not here.
5. [ ] No skill's version moves for this phase. A search on 2026-10-08 found no skill that copies this vocabulary. `plab-ai-review` keeps its own Accepted and Rejected values for review findings, and its "unresolved" set (Open, Deferred and Needs info) is unchanged by this phase. `plab-spec` and `plab-strategy-brief` cite this file without restating the list.

**Verification:**

```bash
grep -c '^| `Provisional` \|^| `Canceled` \|^| `Superseded` \|\*\*Follow-up:\*\*' references/decisions-section.md
grep -c 'Withdrawn' references/decisions-section.md
python scripts/check-dashes.py
```

The first count is 4. The second count is 1, from the sentence recording the rename. `check-dashes.py` exits 0. The spec's own D9 block already carries a `Follow-up` line, so after this phase that line is defined rather than ahead of its definition.

---

## Phase 2: Author the skill under skills/

**Goal:** A complete `plab-resolve-open-items` skill exists in `skills/`, where the conformance gate can see it. AU-01's Phase 4 recorded why drafting outside `skills/` is a mistake: it defers every conformance check to install time, and an over-length description surfaced only then.

**Files:** create, all under `skills/plab-resolve-open-items/`:

```
SKILL.md
HISTORY.md
references/walk-format.md
references/answer-line.md
references/write-back.md
references/walk-record.md
```

Modify `docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md` (status only).

**Fulfills:** AC-1 to AC-20, as authored content.

**Steps:**

1. [ ] **Move the spec to `committed`**, because building starts here. In `spec.md`, change the frontmatter line `status: draft` to `status: committed`, and the Task Summary line `**Status:** draft` to `**Status:** committed`. Set `updated` to the execution date. Leave every acceptance-criterion box unticked: `doc-lifecycle-check.py` invariant 9 does not check a `committed` spec's boxes, and Phase 6 ticks them.
2. [ ] **Write the `SKILL.md` frontmatter exactly as follows**, with the execution date in `updated`. It carries no `disable-model-invocation` line, which is AC-14 and the maintainer's D7 (invocation) ruling.

   ```yaml
   ---
   name: plab-resolve-open-items
   description: "Walk the maintainer through every open question, decision and task in the current session, then write each answer back to the document it came from. Use when the user asks to go through what is pending: 'walk me through the pending questions and decisions', 'resolve open items', 'what do you need me to decide', 'decision sitting'. Presents items as Q, D and T, D items with lettered options and a recommendation, takes a one-line answer such as 'D1 A, Q1: the NAS', and writes a walk record. Can be pointed at one named document. Do NOT fire on a request to walk through code or a file, on a single standalone decision question, or on a status question like 'where are we' or 'what's next'; answer those directly. Not yet built: the --backlog sweep across every spec, plan and log."
   argument-hint: "[<document>]"
   license: MIT
   metadata:
     version: "1.0.0"
     updated: YYYY-MM-DD
   ---
   ```

   The description is 783 characters, measured 2026-10-07, against the Universal-tier limit of 1,024. The first trigger phrase is the maintainer's own prompt, recorded in the design brief: "Walk me through the pending questions, decisions, and needed clarifications." If the description changes, re-measure it before Phase 4.
3. [ ] **Write the `SKILL.md` body** with these sections, in this order:
   - **When to use** and **When NOT to use.** The second names the three do-NOT-fire cases, each with an example: "walk me through `bundle-check.py`" (code walkthrough), "should the record go in A or B?" (a single standalone decision question, answered directly), and "where are we?" (status question).
   - **Workflow**, as seven numbered steps: 1 gather, 2 present, 3 read the answer line, 4 apply, 5 re-present anything that needs more, 6 write the walk record, 7 make the offers (an architecture decision record, a `gh issue create` command). Each step cites its reference file.
   - **Not in this version.** One line each for the five deferred items AC-16 names: the `--backlog` mode, automatic GitHub filing, a GitHub Projects board, gathering across repositories, and a published web-page rendering.
   - **Constraints.** At minimum: never write a document on another branch (AC-9); never run `gh issue create` (AC-13); never perform an ADR promotion without acceptance (AC-12); never infer acceptance from silence (AC-7); never rewrite an item's body (AC-8); confirm only before deleting, pushing, merging, posting externally, or editing outside the current repository (AC-15).
   - **References**, as a table naming the four files and when to load each.
4. [ ] **Write `references/walk-format.md`** (gathering and presentation). It must define:
   - The two sources of AC-1, and the named-document mode that replaces them when the maintainer names one document.
   - "Touched" as read or written by the current session. This is the spec's Requirement 2, flagged there as its own judgment call.
   - The Q, D and T series, numbered locally to the walk, with uppercase option letters A to D (AC-2).
   - The presentation line for each series. A D item gives a handle, its source, two to four options, one recommendation, and a confidence level. A Q item gives a handle, its source, and "Default if skipped". A T item gives a handle and the three answers "done", "later" and "drop" (AC-2, AC-4).
   - The source line, for example "D4, from the WD-01 spec's D1", or "No source document" (AC-3).
   - The one-home rule of Requirement 18: a tracked document closest to the work wins over an untracked one, and a tie between two tracked documents becomes a Q item asking which is the home (AC-17).
5. [ ] **Write `references/answer-line.md`** (reading the answer). It must define:
   - The grammar. Split the line at each item id (`Q<n>`, `D<n>`, `T<n>`). An option letter directly after an id is the choice. Text after a colon is free text, kept verbatim. Any other text left in an item's segment goes to step 6 for interpretation.
   - The answer states, by series. D: `decided`, `provisional`, `deferred`, `canceled`, `unanswered`. `canceled` follows the maintainer's seven statuses of 2026-10-08. Q: `decided`, `provisional`, `assumed`. T: `done`, `later`, `drop`, `open`.
   - Skips (AC-6): an omitted D item stays `unanswered` and is written nowhere, while an omitted Q item becomes `assumed` on its stated default. An omitted T item stays `open`.
   - Explicit acceptance (AC-7). "ok", "accept all", "accept the rest" and "yes to all" accept every presented item's recommendation or default, and each such item is recorded `decided`. A line that merely omits an item accepts nothing.
   - Leftover text, which the model interprets, never the grammar. Words of doubt such as "but I'm not sure" or "i guess" make the answer `provisional`, and the words are kept verbatim for its `Reasoning` line. A request for more context, a question back, or "I don't understand this" leaves the item unanswered and queues it for the next round with more context (AC-18). A reply holding both a choice and a question follows interpretation I6.
   - Worked examples, quoted exactly: AC-5's "D1 A, D2 B, Q1: the NAS"; AC-18's "D1 A, but I'm not sure. D2: expand this. D3: I don't understand this"; the spec's Example 3, "D2 B, Q1: the NAS, accept the rest"; and the seven reply shapes of the first walk ("A", "A i guess", "A. However this feels a little incomplete and unsettled and I can't articulate why", "A. Are there other types than Q and D?", "expand this and provide more context", "I don't understand this", and a reply of four questions).
   - An id the walk did not present is reported back and applies nothing.
6. [ ] **Write `references/write-back.md`** (applying answers). It must define:
   - The three surfaces of `references/decisions-section.md`, and the rule that an item's Summary, Context, Desired outcome, Options, Recommendation and Confidence text is never edited (AC-8).
   - The `Provisional` status of interpretation I3, with the maintainer's words of doubt in `Reasoning`, and the `Follow-up` line on every `Decided` or `Provisional` item (AC-19), both citing the Phase 1 text.
   - The pointer of interpretation I4, written into every copy outside the home (AC-17).
   - The branch guard of interpretation I5, with the command: `git -C <folder containing the document> rev-parse --abbrev-ref HEAD`, compared with the same command run at the repository root. On a mismatch, the walk writes nothing to that document and prints the intended edit as text, naming the branch it would have targeted (AC-9).
   - The self-check. Copy each document to a temporary file immediately before its first edit, and after the last edit run `python <skill base directory>/scripts/walk-check.py writeback <copy> <document>`. Exit 1 means the write-back touched something it must not; undo that edit and report it. Exit 2 means the check could not run, and the output says so rather than claiming success. `HEAD` is not a safe "before", because the session may already have edited the document.
   - The confirmation boundary of AC-15: write-back and the walk record need none, while deleting, pushing, merging, posting externally, or editing outside the current repository each need one.
   - The architecture decision record offer of AC-12, using the bar in `references/decisions-section.md`'s Lifecycle section: alternatives considered, hard to reverse, and looks wrong without context. The skill offers once per qualifying item and writes nothing unless the offer is accepted.
   - The GitHub command of AC-13, as a template: `gh issue create --title "<id>: <handle>" --body-file <file>`, with a body stating every option in full. The skill prints it and never runs it.
7. [ ] **Write `references/walk-record.md`** (the record). It must define:
   - The location of AC-11. First, a folder for decision or sitting records named in the repository's `AGENTS.md` or `CLAUDE.md`. Otherwise, `_local/decisions/`. The filename is `YYYY-MM-DD_walk_<slug>.md`.
   - The frontmatter: `type: walk-record`, `date`, `repo`, and `rounds`, an integer of at least 1.
   - The items table, with exactly these columns: `| Walk ID | Home | Answer | State | Round | Follow-up | Landed |`.
   - The vocabulary for `Landed`: `<path> (three surfaces)`, `<path> (pointer)`, `walk record only`, `not written`, or `reported as text: branch <name>`.
   - One `## Round N` section per round, holding the presented items and the maintainer's reply verbatim (AC-18).
   - A short example. It must cite no `_local/` path and no drive path, because the example ships in a public repository.
8. [ ] **Write `HISTORY.md`** in the shape of `skills/plab-continue-session/HISTORY.md`, with one row:

   ```
   | 1.0.0 | YYYY-MM-DD | unreleased | added | First version. Walks the open questions, decisions and tasks of the current session, or of one named document, takes a one-line answer, writes each answer back to its one home, and writes a walk record that `walk-check.py` verifies. |
   ```

**Verification:**

```bash
python -c "import re;t=open('skills/plab-resolve-open-items/SKILL.md',encoding='utf-8').read();d=re.search(r'^description: \"(.*?)\"$',t,re.M|re.S).group(1);print(len(d))"
grep -c 'disable-model-invocation' skills/plab-resolve-open-items/SKILL.md
python scripts/check-dashes.py
```

The first prints a number no greater than 1024. The second prints 0. The third exits 0. Then confirm by reading that `references/answer-line.md` quotes AC-5's and AC-18's answer lines exactly, and that the SKILL.md body names all five deferred items. `check.mjs` is deliberately not run yet: the skill is not in `library.json` until Phase 4.

---

## Phase 3: The walk checker, its sample, and its canary

**Goal:** A deterministic checker verifies a walk record's structure and a write-back's scope. It runs in CI against a committed sample, and it has been shown to fail when each rule it guards is broken.

**Files:**
- `skills/plab-resolve-open-items/scripts/walk-check.py` (create)
- `skills/plab-resolve-open-items/examples/sample-walk/walk-record.md`, `before.md` and `after.md` (create)
- `.github/workflows/gate.yml` (modify)
- `_local/verification/wd01-walk-check-canary/RESULTS.md` (create, gitignored)

**Fulfills:** AC-8, AC-10, AC-19 and AC-20, and the record halves of AC-6 and AC-18.

**Steps:**

1. [ ] **Write `walk-check.py`**, modelled on `skills/plab-audit/scripts/bundle-check.py`. It has three exit states: 0 clean, 1 findings, 2 broken. It runs an embedded self-test before every real run and exits 2 if the self-test fails. Each fixture lives in its own temporary directory and never touches the repository. It opens every file as UTF-8, because the maintainer's machine defaults to cp1252. Usage is `walk-check.py record <walk-record.md>` or `walk-check.py writeback <before.md> <after.md>`.
2. [ ] **Implement the record rules:**
   - R1: The frontmatter has `type: walk-record`, a `date` in `YYYY-MM-DD` form, a `repo`, and a `rounds` integer of at least 1.
   - R2: The items table exists with exactly the seven columns of `references/walk-record.md`, and at least one row.
   - R3: Every Walk ID matches `^[QDT]\d+$` and is unique (AC-2).
   - R4: Every Home is `none` or ends in an item id (AC-3).
   - R5: Every State belongs to its series' vocabulary in `references/answer-line.md`.
   - R6: Every `decided` or `provisional` row has a Follow-up that is neither empty nor `-` (AC-19).
   - R7: Every T row's Landed reads `walk record only` (AC-20). Every `unanswered` D row's Landed reads `not written`. Every `assumed` Q row's Answer begins `default:` (AC-6).
   - R8: The number of `## Round N` sections equals `rounds`, no Round cell exceeds it, and every `provisional` row's Answer quotes the maintainer's words of doubt (AC-18).
3. [ ] **Implement the write-back rules**, comparing two copies of one document with line endings normalized:
   - W1: Everything outside the `## Open Questions / Decisions` section is identical.
   - W2: Each item subsection is identical from the line after its header down to the `---` rule before its maintainer block. Only the header's trailing `(status)` may differ (AC-8).
   - W3: In the summary table, only the `Resolution`, `Status` and `Updated` cells may differ. No row is added or removed, and no `ID` or `Title` changes.
   - W4: For each changed item, the table status, the header status and the block's `Status` line agree.
   - W5: Each changed block whose status is `Decided` or `Provisional` carries a `Follow-up` line (AC-19). A pointer block, whose `Choice` begins `Recorded in`, is exempt, per interpretation I4.
   - A file that is missing, or has no decisions section, exits 2. A changed item count is a finding and exits 1.
4. [ ] **Build the sample walk record** by rewriting the first walk record into the final format. Keep its three rounds, its replies verbatim, and every item. Give the "PR-20 merge" item the series letter D. Add the State and Follow-up columns. Replace every gitignored or machine-specific path with a plain-language description.
5. [ ] **Build the write-back pair.** `before.md` holds a decisions section of three items: D1 Open, D2 Open, and Q1 Needs info with a stated default. `after.md` decides D1 with a `Follow-up` line on all three surfaces, leaves D2 untouched (a skipped D), and leaves Q1 untouched (an assumed Q).
6. [ ] **Confirm the sample is clean of paths.** `grep -rnE '_local/|(^|[^A-Za-z])[A-Za-z]:[/\\]' skills/plab-resolve-open-items/examples/` must print nothing. The pattern matches `_local/` and drive paths in either slash direction, and it skips `https://`. AU-01's sample hit this exact trap: its fixture carried seven absolute paths.
7. [ ] **Run the canaries** against scratch copies under `_local/verification/wd01-walk-check-canary/`. Each one must give the stated exit code:

   | # | Mutation | Expected |
   |---|---|---|
   | 1 | None: the sample record and the sample pair | 0 and 0 |
   | 2 | The first, hand-made walk record, unmodified | 1 (R2, R8). Corrected on execution: the plan first said R3, but the record's "PR-20 merge" item is named only in its frontmatter; in its table it is `D9`, a valid id. It has no `## Round` sections, so R8 fires instead |
   | 3 | Blank one decided row's Follow-up cell | 1 (R6) |
   | 4 | Set one T row's Landed to a document path | 1 (R7) |
   | 5 | Drop one `## Round N` section | 1 (R8) |
   | 6 | Edit one Options line in `after.md` | 1 (W2) |
   | 7 | Change one table Title in `after.md` | 1 (W3) |
   | 8 | Leave the header at `(Open)` while the block says Decided | 1 (W4) |
   | 9 | Delete the `Follow-up` line from D1's block in `after.md` | 1 (W5) |
   | 9a | Make D2 in `after.md` a pointer block (`Choice: Recorded in other.md D2`, status Decided, no `Follow-up`) | 0 (W5's exemption is an anti-canary) |
   | 10 | A path that does not exist | 2 |
   | 11 | Remove the R6 check from the pipeline function | the self-test exits 2 |
   | 11b | Added on execution: remove the round-section check from the record pipeline | the self-test exits 2 |
   | 12 | Added on execution: the real WD-01 spec against itself | 0, with the parser extracting all eleven items |
   | 13 | Added on execution: the real spec before and after PR #22 (D9 and D10 ratified, plus requirement edits) | 1, W1 only |

   Canary 11 matters most. It proves the self-test covers the shipped pipeline and not only each check function in isolation, which is how R8 was proven in PR #20.
8. [ ] **Record every result** in `RESULTS.md`, with the exact output and exit code of each run. Then delete the scratch copies and keep `RESULTS.md`.
9. [ ] **Add the CI steps.** In `.github/workflows/gate.yml`, directly after the step named `The audit bundle checker, against its committed sample`, add:

   ```yaml
      # The walk checker, in both of its modes, against its committed sample.
      # Same job as the bundle checker, for the same reason: branch protection
      # requires status checks by job name, so a new job would not gate.
      # Exit 2 means the checker could not prove itself. Never read it as clean.
      - name: The walk checker, against its committed sample walk record
        if: always()
        run: python3 skills/plab-resolve-open-items/scripts/walk-check.py record skills/plab-resolve-open-items/examples/sample-walk/walk-record.md

      - name: The walk checker, against its committed write-back pair
        if: always()
        run: python3 skills/plab-resolve-open-items/scripts/walk-check.py writeback skills/plab-resolve-open-items/examples/sample-walk/before.md skills/plab-resolve-open-items/examples/sample-walk/after.md
   ```

   Re-read the job first. Do not rename the job: its comment records that the protection rule matches the job name.

**Verification:**

`RESULTS.md` shows canary 1 at exit 0 twice, canaries 2 to 9 at exit 1 each, canary 9a at exit 0, canary 10 at exit 2, and canaries 11 and 11b with the self-test exiting 2. A phase that produces only passing results has tested nothing.

**Executed 2026-10-08.** All 14 canaries behaved as expected, and each exit 1 named the rule its mutation targeted. The record is in the gitignored canary folder named above. The self-test passed on its first run, so canaries 11 and 11b are what prove it can fail: with R6 removed it reported "R6 a decision with no Follow-up: expected a finding, got none" and exited 2.

---

## Phase 4: Register ten skills at plugin 0.7.0

**Goal:** `library.json` declares plugin 0.7.0 with ten skills, every per-skill version in it matches that skill's `SKILL.md`, and the generated manifests agree.

**Files:** `library.json` (modify); `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` and `manifest.generated.json` (regenerate, never hand-edit).

**Fulfills:** AC-14, the invocation setting half.

**Steps:**

1. [ ] Change the plugin version `"version": "0.6.1"` to `"version": "0.7.0"`.
2. [ ] **Change the `plab-audit` entry's `"version": "1.0.1"` to `"version": "1.1.0"`.** Its `SKILL.md` has declared 1.1.0 since PR #20, but `library.json` was not touched there. No gate catches this: `scripts/version-parity-check.py` reads only `SKILL.md`, four documentation locations and the plugin version, never per-skill versions in `library.json`. This step is therefore required, and the verification below checks it directly.
3. [ ] Add this entry after the `plab-audit` entry, matching the indentation of its siblings:

   ```json
   {
     "name": "plab-resolve-open-items",
     "path": "skills/plab-resolve-open-items/SKILL.md",
     "version": "1.0.0",
     "tier": "universal",
     "status": "active"
   }
   ```

4. [ ] Change the plugin `description`. Before:

   `General-purpose agent skills for the work around the work: session continuity, structured analysis, guide authoring, cross-LLM peer review, repository auditing, and the specification and release-planning documents that sit between an idea and a tag. Use when wrapping or resuming a coding session, turning raw thinking into a decision-ready brief, generating a guide bundle, getting a second-model review of a document, auditing a repository, writing a feature spec, managing a version-scoped release plan, or scaffolding agent infrastructure into a repository.`

   After:

   `General-purpose agent skills for the work around the work: session continuity, structured analysis, guide authoring, cross-LLM peer review, repository auditing, resolving open questions and decisions, and the specification and release-planning documents that sit between an idea and a tag. Use when wrapping or resuming a coding session, turning raw thinking into a decision-ready brief, generating a guide bundle, getting a second-model review of a document, auditing a repository, walking through the questions and decisions a session left open, writing a feature spec, managing a version-scoped release plan, or scaffolding agent infrastructure into a repository.`
5. [ ] Regenerate the manifests. The generator prints nothing on success, so check the result with `git diff --stat`, not by waiting for output:

   ```bash
   node <agent-skills-toolkit>/scripts/generators/gen-manifest.mjs . --write --target=all
   ```

**Verification:**

```bash
node <agent-skills-toolkit>/scripts/check.mjs .
for d in skills/*/; do n=$(basename "$d"); s=$(grep -m1 '^  version:' "$d/SKILL.md" | tr -dc '0-9.'); l=$(grep -A3 "\"name\": \"$n\"" library.json | grep '"version"' | tr -dc '0-9.'); [ "$s" = "$l" ] && echo "ok $n $s" || echo "MISMATCH $n skill=$s library=$l"; done
```

`check.mjs` reports 0 errors and 0 warnings and exits 0. Expect advisory `[error/house]` lines above that summary. They predate this effort, and the new directory picks up the same `folder-readme (G8)` advisory as every sibling. The description score must be at least 0.70; a score of exactly 0.65 means the lexicon could not match the "Use when" pattern (ADR 0049 in the toolkit), so check that before calling the description a defect. The loop prints `ok` for all ten skills and no `MISMATCH` line.

The loop is proven able to fail. Run on `main` at `bf6c675` on 2026-10-07, it printed `MISMATCH plab-audit skill=1.1.0 library=1.0.1` and `ok` for the other eight skills.

---

## Phase 5: Documentation wiring

**Goal:** Every human-facing file that counts or lists the skills includes the new one, and the usage README names the deferred work.

**Files:** modify `AGENTS.md`, `README.md`, `docs/status-skills.md` and `CHANGELOG.md`; create `docs/skills/plab-resolve-open-items/README.md`.

**Fulfills:** AC-16, the documentation half.

**Steps:**

1. [ ] `AGENTS.md`, line 7. Before: `Nine general-purpose agent skills for the work around the work: scaffolding a repository for agent-assisted development, closing and resuming coding sessions, turning raw thinking into a decision-ready brief, producing guide bundles, getting a second model to review a document, auditing a repository and reordering its backlog on evidence, and carrying a feature from written specification through to a taggable release plan.` After: `Ten general-purpose agent skills for the work around the work: scaffolding a repository for agent-assisted development, closing and resuming coding sessions, turning raw thinking into a decision-ready brief, producing guide bundles, getting a second model to review a document, auditing a repository and reordering its backlog on evidence, carrying a feature from written specification through to a taggable release plan, and walking the maintainer through the questions and decisions a session leaves open.`
2. [ ] `AGENTS.md`, line 9. Before: `Two of the nine ship with` After: `Two of the ten ship with`
3. [ ] `AGENTS.md`: add a `### plab-resolve-open-items` section after the `### plab-audit` section and its `---` rule, before `## Build and validate`. Give it a summary paragraph and an **Invocation:** line in the shape of the `plab-spec` entry: auto-discoverable from 1.0.0, firing on an explicit request to walk what is pending, with do-NOT-fire clauses for a code walkthrough, a single standalone decision question, and a status question.
4. [ ] `README.md`, line 3. Before: `Nine agent skills for the work around the work:` and ending `and carrying a feature from written specification through to a taggable release plan.` After: `Ten agent skills for the work around the work:`, ending `carrying a feature from written specification through to a taggable release plan, and walking the maintainer through the questions and decisions a session leaves open.`
5. [ ] `README.md`: add this row to the skills table, after the `plab-release-plan` row and before the two rows marked `&sup1;`:

   ```
   | [`plab-resolve-open-items`](docs/skills/plab-resolve-open-items/README.md) | Walk through the open questions, decisions and tasks a session has raised, take a one-line answer, and write each answer back to its home document | 1.0.0 |
   ```

   The footnote at line 21, "Both skills ship with `disable-model-invocation: true`", stays true and does not change.
6. [ ] `docs/status-skills.md`, line 5. Before: `**Plugin version:** 0.6.1 **Skills:** 9 (7 auto-discoverable, 2 explicit-invocation only)` After: `**Plugin version:** 0.7.0 **Skills:** 10 (8 auto-discoverable, 2 explicit-invocation only)`. Set `**As of:**` to the execution date.
7. [ ] `docs/status-skills.md`: add a row to the At a glance table, in alphabetical order after `plab-release-plan`:

   ```
   | `plab-resolve-open-items` | 1.0.0 | Auto + explicit | `[<document>]` | Each item's home document; the walk record in `_local/decisions/` |
   ```

8. [ ] `docs/status-skills.md`: add a `### `plab-resolve-open-items` 1.0.0` section after the `plab-release-plan` section, in the shape of the `plab-spec` section. Its rows: Invocation, Default behavior, Output, Scripts (`walk-check.py`, run by CI against a committed sample, with eight record rules and five write-back rules), Setup required (Python 3 for the self-check), and References (4 files).
9. [ ] `docs/status-skills.md`, the Shared plugin-root dependencies table. Before: `| `references/decisions-section.md` | `plab-spec`, `plab-strategy-brief` |` After: `| `references/decisions-section.md` | `plab-spec`, `plab-strategy-brief`, `plab-resolve-open-items` |`
10. [ ] Create `docs/skills/plab-resolve-open-items/README.md` in the structure of `docs/skills/plab-continue-session/README.md`, with `**Version:** 1.0.0`. It must carry a "Not in this version" section naming the five deferred items of AC-16, and an example walk with its answer line. `scripts/version-parity-check.py` requires one usage README per skill.
11. [ ] `CHANGELOG.md`: under `## [Unreleased]`, `### Added`, after the `plab-audit` 1.1.0 bullet, add one bullet for `plab-resolve-open-items` 1.0.0. Name what it does, the self-check and its CI steps, the Phase 1 amendment to `references/decisions-section.md`, and the five deferred items.
12. [x] **Added on execution, 2026-10-08: the output-location conventions.** This phase first listed only the files that count or list skills. Two more lines state where skills write, and both said "the three planning skills" are the only exceptions to `_output/`: `AGENTS.md` line 32, which agents read, and `README.md` line 43. Both now name `plab-resolve-open-items`, which writes into answered documents and `_local/decisions/`. A post-merge audit of every documentation surface found the gap, together with the spec's stale "Currently In Progress" line and a stale canary count in the CHANGELOG.

**Verification:**

```bash
python scripts/version-parity-check.py && python scripts/check-dashes.py && node <agent-skills-toolkit>/scripts/check.mjs .
for p in 'backlog' 'GitHub Projects' 'automatic' 'across repositories' 'web page'; do printf '%s: ' "$p"; grep -c "$p" docs/skills/plab-resolve-open-items/README.md; done
```

All three gates exit 0. The loop prints a count of at least 1 for each of the five deferred items. If a phrase is worded differently in the README, adjust the grep to the README's words rather than the README to the grep.

---

## Phase 6: A live walk proves the behaviour

**Run after the release, by maintainer ruling of 2026-10-09.** The maintainer, the plugin's only user, chose to ship v0.7.0 first and run this walk against the installed version, as v0.6.0 did for `plab-audit`. Three steps change as a result. Skip step 1: the skill loads from the installed plugin, and Phase 7 step 7 has already removed the junction. In step 5, the base-directory line must name the `prisant-utilities\0.7.0` cache instead of the junction. And a defect this walk finds ships as a patch release, 0.7.1, rather than blocking the tag. The spec stays `committed` until this phase ticks its boxes; it has no `target-release`, so invariant 4 does not require it to be `fulfilled`.

**As run, 2026-10-12.** A headless install check of 0.7.0 found that an empty session over-gathered, so the skill was fixed as 1.0.1 first and the walk ran against that fix through the step 1 junction, not against the installed cache. Two more changes followed from what the run met:

- **The walk ran headless, relayed turn by turn.** The maintainer was away from the computer. A fresh session started with `claude -p` and continued with `--resume`, receiving the scripted lines of steps 6 to 11; it never saw the session that relayed them. The one unscripted answer, Q1's, is the maintainer's own text, relayed verbatim.
- **The walk session ran with the installed plugin and auto-memory switched off,** through a `--settings` file. With the plugin on, the unfixed copy is also on offer under the plugin's namespace. With memory on, the project memory tells the session about the defect and this trial.

Every check in step 12 passed except the write-back check on the design brief, which exits 2 because the brief's section heading is not the standard one; a manual diff shows only its three surfaces changed. No check failed, so step 14 needed no repeat.

**Goal:** In a fresh session that loads the skill through a junction, a real walk shows every behaviour the checker cannot see. The same walk answers the spec's last open item, Q1 (what happened to past walk answers).

**Files:**
- `.claude/skills/plab-resolve-open-items` (create, a junction, gitignored)
- `_local/verification/wd01-trial/` (create): `fixture.md`, `fixture-b.md`, their pre-trial copies, and `RESULTS.md`
- A worktree at `../prisant-utilities-wd01-trial` on branch `trial/wd01-branch-guard` (create, then remove)
- `spec.md`: Q1's three surfaces through the walk, and the Task Summary boxes (modify)

**Fulfills:** AC-1 to AC-15 and AC-17 to AC-20 in behaviour, including the trigger half of AC-14. AC-16 is documentation, proven by the Phase 5 grep.

**The maintainer is needed for this phase.** The answer lines in steps 7 and 9 must be typed by the maintainer, because only the maintainer can answer Q1 truthfully.

**Steps:**

1. [x] **Create the junction**, in PowerShell from the repository root:

   ```powershell
   New-Item -ItemType Junction -Path .claude\skills\plab-resolve-open-items -Target (Resolve-Path skills\plab-resolve-open-items)
   ```

2. [x] **Write `fixture.md`**, a document whose decisions section follows `references/decisions-section.md`. It holds five D items (D1 to D5) and one Q item with a stated default. Make D4 architectural: it must state alternatives considered and be hard to reverse, so that it meets the ADR bar. Write `fixture-b.md` with two D items and one Q item. Copy both to `*.before.md` beside them.
3. [x] **Create the branch-guard worktree:** `git worktree add ../prisant-utilities-wd01-trial -b trial/wd01-branch-guard`. In it, write `_local/branch-guard.md` with one Open D item in the same format, and record its SHA-256 hash.
4. [x] **Make pre-trial copies of `spec.md` and of the maintainer's private design brief** for this skill, dated 2026-10-04 and kept in the gitignored ideas folder. Copy each into `_local/verification/wd01-trial/`. The brief's Q1 is the same item as the spec's Q1, and the spec is its home, so the pair tests the one-home rule. Do not use `git show HEAD:` as the spec's "before": Phase 2 already changed the spec's status, and Phase 2 step 6 explains why `HEAD` is not a safe baseline.
5. [x] **Start a fresh Claude Code session** in the repository root, because `/clear` does not reload skills. When the skill first loads, confirm that its base directory line names the `.claude\skills\plab-resolve-open-items` junction. On Windows the line uses backslashes.
6. [x] **Touch the sources.** Ask the session to read `fixture.md`, the worktree's `branch-guard.md`, `spec.md` and the design brief. Then say two things in conversation: "I haven't decided whether the trial results go in RESULTS.md or a session log" (a sourceless Q), and "I still need to delete the decision-21 canary clone" (a T item). Do not let it read the maintainer's decision register, because that register's absence from the walk is the AC-1 test.
7. [x] **Ask for the walk** with the maintainer's own words: "Walk me through the pending questions, decisions, and needed clarifications." Check the presentation against AC-1 to AC-4 and AC-17. No item may come from the decision register. Q1 must appear once, naming the spec as its home. Every D item has options and a recommendation with confidence. Every Q item has a default. The T item has done, later and drop.
8. [x] **Answer round 1**, using the walk's own numbers for these roles:
   - fixture D1: `A, but I'm not sure`
   - fixture D2: `expand this`
   - fixture D3: `I don't understand this`
   - the branch-guard item: any letter
   - spec Q1: the maintainer's true answer
   - the T item: `later`
   - Omit fixture D4, fixture D5, the fixture's Q, and the conversation Q.
9. [x] **Answer round 2**, which must re-present fixture D2 and D3 with more context, and nothing else: answer D2 `B`, D3 `A`, and D4 `A`. Fixture D5 and both remaining Q items stay omitted.
10. [x] **Ask for the GitHub command** for fixture D2. Then decline the ADR offer that D4 should have triggered.
11. [x] **Run a second walk in named-document mode:** "Resolve the open items in `_local/verification/wd01-trial/fixture-b.md`." Answer `ok`.
12. [x] **Check each result** and record it in `RESULTS.md`, with one row per acceptance criterion, its evidence, and pass or fail:

    | Check | Criteria | Pass condition |
    |---|---|---|
    | `walk-check.py writeback fixture.before.md fixture.md` | AC-8, AC-18, AC-19 | Exit 0. D1's status is `Provisional`, with the maintainer's words verbatim in `Reasoning`. D2, D3 and D4 are decided with Follow-up lines. D5 is unchanged. |
    | `walk-check.py writeback <spec pre-trial copy> spec.md` | AC-8, AC-19 | Exit 0. Q1 is decided, with a Follow-up line. |
    | `walk-check.py writeback <brief pre-trial copy> <brief>` | AC-17 | Exit 0, and Q1 carries a pointer block to the spec, with no answer and no Follow-up line. |
    | The hash of the worktree's `branch-guard.md` | AC-9 | Unchanged, and the session printed the intended edit naming `trial/wd01-branch-guard`. |
    | The walk records in `_local/decisions/` | AC-10, AC-11 | Two records exist, and `walk-check.py record` exits 0 on each. |
    | The first walk record | AC-6, AC-18, AC-20 | Two rounds. Fixture D5 is `unanswered` and `not written`. The fixture Q and the conversation Q are `assumed`. The T item is `later` and `walk record only`. |
    | The second walk record and `fixture-b.md` | AC-1, AC-7 | Only `fixture-b.md` items appear. All are decided on their recommendation or default. |
    | The session transcript | AC-12, AC-13, AC-15 | The ADR offer appears for D4 only, and `docs/internal/decisions/` does not exist. No Bash call runs `gh issue create`. No confirmation question comes between an answer line and its write-back. |
    | The presentation, read in step 7 | AC-2, AC-3, AC-4, AC-5 | As stated in step 7, and every answer token resolved to the item it named. |

13. [x] **Run the trigger test** for AC-14 in headless sessions, one per prompt:

    ```bash
    claude -p "<prompt>" --output-format stream-json --verbose --max-turns 3 > trig_N.jsonl
    grep '"name":"Skill"' trig_N.jsonl | grep -c plab-resolve-open-items
    ```

    Re-verify the event shape on the first run: the grep assumes compact JSON with a `"name":"Skill"` tool-use field. It must fire, with a count of at least 1, on: "Walk me through the pending questions, decisions, and needed clarifications.", "resolve open items", and "what do you need me to decide before we go on?" It must not fire, with a count of 0, on: "Walk me through how skills/plab-audit/scripts/bundle-check.py works.", "Should walk records go in _local/decisions or docs/decisions? Just tell me which.", and "Where are we?"
14. [x] **Fix and repeat.** A failed check is fixed in `skills/plab-resolve-open-items/`, which the junction exposes at once, and re-run in a fresh session. Record the failure and the fix in `RESULTS.md` rather than overwriting it.
15. [x] **Run every step-12 check first.** The Task Summary and the spec's `updated:` frontmatter sit outside the decisions section, so editing them before step 12's `writeback` check makes W1 fire on this step's own edit. The skill itself must not touch either, under AC-8.
    **Tick each proven criterion** in the spec's Task Summary. Update its `**Open questions:**` line, because Q1 is now answered. Leave unticked any criterion that did not pass, and say why in `RESULTS.md`.
16. [x] **Clean up.** Run `git worktree remove ../prisant-utilities-wd01-trial` and `git branch -D trial/wd01-branch-guard`. Keep the junction until Phase 7, step 7.

**Verification:**

`RESULTS.md` holds a row for each of AC-1 to AC-20, each marked pass with evidence, or fail with the reason and the fix. AC-16's row cites the Phase 5 grep. The spec's Task Summary ticks match the pass rows. `python scripts/doc-lifecycle-check.py` exits 0.

---

## Phase 7: Release v0.7.0

**Goal:** v0.7.0 is tagged and published, it carries both `plab-resolve-open-items` 1.0.0 and `plab-audit` 1.1.0, and a fresh session loads the new skill from the installed cache.

**Files:** `CHANGELOG.md`, `skills/plab-audit/HISTORY.md`, `skills/plab-resolve-open-items/HISTORY.md`, `docs/status-skills.md`, `spec.md` and this plan (modify); `.claude-plugin/marketplace.json` in the `prisant-labs/agent-plugins` repository (modify).

**Fulfills:** N/A (release).

**Ask the maintainer before each merge and before the tag.** This is a standing convention in this repository.

**As run.** Steps 1 to 4 and 6 to 9 ran on 2026-10-09 in PR #27, ahead of Phase 6, by maintainer ruling. Step 5 ran on 2026-10-12, after Phase 6 ticked every criterion. The fix that Phase 6 ran against ships as 0.7.1, by the same procedure.

**Steps:**

1. [x] `CHANGELOG.md`. Before: `## [Unreleased]` After: `## [0.7.0] - YYYY-MM-DD`, dated with the tag date. A date written in advance is a prediction rather than a record, as AU-01 Phase 7 step 8 found.
2. [x] `skills/plab-audit/HISTORY.md`, the 1.1.0 row. Before: `| 1.1.0 | 2026-10-06 | unreleased | added |` After: `| 1.1.0 | 2026-10-06 | v0.7.0 | added |`
3. [x] `skills/plab-resolve-open-items/HISTORY.md`, the 1.0.0 row: `unreleased` becomes `v0.7.0` in the same way.
4. [x] `docs/status-skills.md`: set `**As of:**` to the tag date.
5. [x] If Phase 6 ticked every criterion, change the spec's `status: committed` to `status: fulfilled`, and its Task Summary status line to match. Invariant 9 requires every box to be ticked first. Then set this plan's `status: complete` and fill in its Completion Status table.
6. [x] Open the release PR, wait for all checks, ask, and merge with a merge commit. Then tag the merge commit: `git tag -a v0.7.0 -m "v0.7.0" <merge-sha>` and `git push origin v0.7.0`. Confirm with `gh release view v0.7.0` that `publish-release.yml` created the release from the CHANGELOG section.
7. [x] **Remove the junction before verifying the install.** Use `cmd /c rmdir .claude\skills\plab-resolve-open-items`, which removes only the link. Do not use `Remove-Item -Recurse`, which can follow a junction and delete the real files. While the junction exists, a session loads the skill from the repository, so it proves nothing about the cache.
8. [x] Repin the marketplace in the `prisant-labs/agent-plugins` repository's `.claude-plugin/marketplace.json`: `"ref": "v0.6.1"` becomes `"ref": "v0.7.0"`, and `"version": "0.6.1"` becomes `"version": "0.7.0"`. Add "resolving open questions and decisions" to its `description` in the same position as step 4 of Phase 4. Commit and push that repository, asking first.
9. [x] Run `claude plugin marketplace update prisant-labs`, then `claude plugin update prisant-utilities@prisant-labs`.

**Verification:**

```bash
claude -p "Walk me through the pending questions, decisions, and needed clarifications." --output-format stream-json --verbose --max-turns 2 | grep -oE 'prisant-utilities[\\/]+0\.7\.0[\\/]+skills[\\/]+plab-resolve-open-items' | head -1
```

It prints the 0.7.0 cache path. The pattern accepts either slash, because on Windows the base directory line uses backslashes and JSON doubles them. Version 0.6.1 has no such skill, so nothing else can produce that line. A cache listing or a manifest is not proof that a version is loaded; this repository has been caught by that before.

**Known risk:** GitHub moves the `ubuntu-latest` label to Ubuntu 26 from 2026-10-19, and the required checks run on that label. If this release slips past that date, watch the first run on the new image, or pin `ubuntu-24.04` in a separate change.

---

## CI and Documentation Coverage

**CI changes.** Phase 3 adds two `run:` steps to the `Document lifecycle (schema, cross-file, index freshness)` job in `.github/workflows/gate.yml`, one per checker mode, both against the committed sample. They go in the existing job rather than a new one, because branch protection requires status checks by job name, and a new job would report without gating. The workflow enumerates its checks and globs nothing, so without these steps `walk-check.py` would never run in CI. The Standard gate and the lifecycle scripts are directory-scoped and pick up the new skill and this plan with no change.

**Documentation.** Phase 5 covers `AGENTS.md`, `README.md`, `docs/status-skills.md`, `CHANGELOG.md`, and the new `docs/skills/plab-resolve-open-items/README.md`. Phase 2 creates `skills/plab-resolve-open-items/HISTORY.md`. Phase 1 amends the shared `references/decisions-section.md`. Phase 7 fills both HISTORY Release cells, including `plab-audit`'s, which has read `unreleased` since PR #20 on purpose.

## Rollback

There is no schema change and no data migration. To undo the whole effort:

- Delete `skills/plab-resolve-open-items/` and `docs/skills/plab-resolve-open-items/`.
- Remove both walk-checker steps from `.github/workflows/gate.yml`. Leaving them fails every later run, because their targets are gone.
- Remove the `plab-resolve-open-items` entry from `library.json`, and restore the plugin version to `0.6.1` if v0.7.0 was never tagged. Keep `plab-audit` at `1.1.0` in `library.json`, because that matches its `SKILL.md` either way.
- Regenerate the manifests with the Phase 4 command. Do not hand-edit them.
- Restore the exact prior text quoted in Phase 5: `AGENTS.md` lines 7 and 9, `README.md` line 3, the `docs/status-skills.md` header and shared-dependencies row. Remove the new rows, sections and CHANGELOG bullet.
- Remove the junction with `cmd /c rmdir`, never with `Remove-Item -Recurse`.
- Return the spec to `draft` only after unticking every box, because invariant 9 fails a `draft` spec with any box ticked.

**Keep the Phase 1 amendment.** By the time anyone rolls back, walks will have written `Provisional` statuses and `Follow-up` lines into real documents, and the spec's D9 block already carries a `Follow-up` line. Removing the definitions would leave those documents using undefined terms, while keeping them costs nothing.

**Partial-rollback hazards.** Reverting Phase 4 without Phase 5 leaves `AGENTS.md` and `README.md` claiming ten skills over a manifest of nine. Reverting Phase 3's sample without its CI steps fails every run. Revert each pair together or not at all.

## Before opening the pull request

- [ ] `phase-count` equals the number of `## Phase` sections (7)
- [ ] Every acceptance criterion in `spec.md` appears in the Completion Status table (AC-1 to AC-20)
- [ ] No acceptance criterion appears here that is not in the spec
- [ ] `python scripts/frontmatter-check.py` exits 0
- [ ] `python scripts/doc-lifecycle-check.py` exits 0
- [ ] `python scripts/gen-release-index.py --check` exits 0, or the index has been regenerated
- [ ] `python scripts/check-dashes.py` exits 0
- [ ] `python scripts/version-parity-check.py` exits 0
- [ ] `node <agent-skills-toolkit>/scripts/check.mjs .` exits 0
- [ ] `.github/workflows/gate.yml` contains both walk-checker steps
- [ ] Phase 3's canary record shows eight exit-1 results, one exit-2 result, a self-test failure, and the passing W5 anti-canary, not only passes
- [ ] Every per-skill version in `library.json` matches its `SKILL.md`, per the Phase 4 loop
