---
id: D-10
title: Make derive-log-facts.py's output the single log-format contract
type: spec
status: committed
created: 2026-08-23
updated: 2026-11-17
linked-effort: the maintainer's private defect record for the wrap/continue pair, 2026-08-18
linked-plan: implementation-plan.md
ac-count: 8
source-count: 15
requires-human-review: false
target-release: null
linked-release: null
priority: P2
---

# Spec: Make derive-log-facts.py's output the single log-format contract

## Task Summary

**Status:** Committed
**Last updated:** 2026-11-17
**Linked plan:** `implementation-plan.md`
**Open questions:** 7 items, all decided and recorded below (see Open Questions / Decisions); none genuinely open
**Revisions:** Initial draft 2026-08-23; refreshed against current code and the maintainer's rulings 2026-11-17

### Acceptance Criteria Fulfillment

- [x] AC-1: "hostname" derivation text confined to the script, not scattered across reference docs or wrap's SKILL.md
- [x] AC-2: `frontmatter-schema.md` carries no hand-written example that can contradict its own Tier 1 table
- [x] AC-3: No hardcoded count of the schema's fields appears in either skill's shipped documentation
- [x] AC-4: Continue's Phase 2 field list no longer independently hand-enumerated
- [x] AC-5: The versioned-together pairing claim, in one of its two current wordings, asserted in exactly one shipped file
- [x] AC-6: Docs README's per-section descriptions defer to `SKILL.md` rather than restating it
- [x] AC-7: This effort does not start before W-02 ships and wires the script (met: verified 2026-11-13)
- [x] AC-8: A test binds every copy of the field list to the schema, and each of its assertions is proven to fail when broken

### Currently In Progress

None.

## Purpose

D-10 (the source roadmap's own numbering) is named as the structural cause under four already-diagnosed defects: D-1 (trigger narrowing reached the router but not the program), D-2 (a behavior change shipped with no version trail), D-5 (same-arc superseding logs have no mechanism), and D-8 (the wrap skill fails its own gate, inside its own references). All four are instances of one disease: the wrap and continue session-log format has no single source of truth. [S1]

The template lives in wrap's references, the parsing expectations live in continue's references, the frontmatter schema is a third document, and a claim that the two skills "move and version together" is asserted more than once with nothing checking it. [S1] This spec depends on W-02 (Derive session-log facts from git instead of model recall, `docs/internal/release-plans/_unassigned/W-02_derived-log-facts/spec.md`): once `derive-log-facts.py` exists, its actual output becomes the contract for every field it derives, and this effort's job is to make every other document defer to it and delete what they used to restate independently. [S1, S11]

**What changed by 2026-11-17.** W-02 (derived log facts), W-05 (wrap hygiene order) and W-07 (session-aware logs) shipped between this spec's first draft and its build, and the disease spread into code. `check-log.py` now carries its own list of the Tier 1 fields [S13]. `lib/session-logs.py` and continue's `reconcile.py` read named frontmatter fields [S14, S15]. The template's three frontmatter blocks omit two Tier 1 fields, `commit-range` and `latest-tag`, so a wrap that copies the template writes a log `check-log.py` fails [S3, S13]. That drift happened while every pointer this spec originally asked for would have been in place, which is why Requirement 8 adds a test rather than relying on pointers alone.

## Scope

### In Scope

1. Rewrite `skills/plab-wrap-session/references/frontmatter-schema.md`: for every field `derive-log-facts.py` produces, replace hand-written derivation-method text with a pointer to the script; keep the tiering rationale and the guidance for fields the model still authors; record `type` as a constant the agent writes, because the script does not produce it; remove the Example Frontmatter block in favor of a pointer to wrap `SKILL.md`'s Frontmatter block.
2. Rewrite `skills/plab-wrap-session/references/session-log-template.md`: per-field inline comments for derived fields point at the script instead of restating the derivation method, and each mode's frontmatter block carries every Tier 1 field.
3. Rewrite `skills/plab-wrap-session/SKILL.md`'s Frontmatter section the same way. (Added 2026-11-17; see Non-Goal 2.)
4. Rewrite `skills/plab-continue-session/SKILL.md` Phase 2 and `skills/plab-continue-session/references/handoff-display.md`: defer the field list to the schema, following the cross-skill pointer wrap `SKILL.md` already uses for continue's `log-discovery.md`.
5. Rewrite `docs/skills/plab-wrap-session/README.md`: remove every hardcoded field count, the independently restated Tier table, and the Output Shape table's parallel purpose descriptions; point at the single references instead.
6. Rewrite `docs/skills/plab-continue-session/README.md` wherever it independently restates fields or the pairing claim.
7. Consolidate the versioned-together pairing claim (today in `skills/plab-continue-session/HISTORY.md` and root `README.md`) to exactly one location.
8. Add the contract test of Requirement 8 to `skills/plab-wrap-session/scripts/test-check-log.py`.
9. Bump both skills' versions with the bookkeeping the drift check compares. The targets are set in C-04's implementation plan, because both efforts ship in one pull request.

### Non-Goals

1. Does not modify `derive-log-facts.py`'s behaviour. That script belongs to W-02.
2. Does not modify `skills/plab-wrap-session/SKILL.md`'s Evidence Gathering section. Its Frontmatter section was fenced off here until 2026-11-17, because W-02 owned wrap's consumption of the script; W-02 shipped in wrap 1.8.0, so that reason has expired, and the section carries a copy of the `hostname` comment this effort removes.
3. Does not add a new script, workflow step or drift detector beyond Requirement 8's test, which lives in a test file CI already runs. The source is explicit that a shared schema should not be built as a separate artifact, and this test builds none: it reads the existing schema and checks the copies against it. D-3 (the hygiene sweep's bidirectional documentation-drift check) and D-11 (three-state gate canaries), which this non-goal once named as the owners of drift detection, check version bumps and gate canaries, not field lists. (Amended 2026-11-17, ruling D5.)
4. Does not change any session log's actual runtime shape. No field is renamed and no mode's output changes. C-04 (consumption disposition) adds one field in the same pull request, under its own spec.
5. Does not touch `AGENTS.md`. Neither skill is renamed, no trigger phrase changes, and neither skill's blurb there restates the frontmatter contract.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer (JP) | Reads reference docs when auditing or extending either skill | Benefits from one place to check the contract instead of four or five |
| Agent (Claude Code or Codex running either skill) | Loads reference files at runtime | Pays the token cost of every restatement it reads, and risks loading a stale copy when restatements disagree |

## Requirements

1. For every field `derive-log-facts.py` produces, its derivation method must be asserted in exactly one place. `frontmatter-schema.md`, `session-log-template.md` and wrap `SKILL.md`'s Frontmatter block must stop independently restating "hostname," "git diff --name-only," and similar derivation phrases that the script itself already encodes. [S1, S2, S3, S9]
2. `frontmatter-schema.md` must not carry a worked example that contradicts its own Tier 1 table. On 2026-11-13 the example omitted `type`, `machine`, `commit-range` and `latest-tag`, four of the nine fields the table marks as always-include. [S2]
3. Any hardcoded field count must not appear anywhere in either skill's shipped documentation. A reader who wants the count should be pointed at the authoritative source, not handed a number to trust. This effort's own working documents are exempt, since they name the stale strings as the thing being removed. [S6]
4. `skills/plab-continue-session/SKILL.md`'s Phase 2 field list and `references/handoff-display.md`'s parallel description must stop independently restating a shape that can drift from `frontmatter-schema.md`'s tables, as Phase 2 already has: it lists `status`, `session-type`, `model`, and `agent`, but omits the Tier 1 fields `type`, `machine`, and `files-changed`. [S4, S5, S2]
5. The claim that the two skills move and version together must be asserted in exactly one shipped file, keeping one of its two current wordings verbatim. Today it is asserted in `skills/plab-continue-session/HISTORY.md` ("move and version together") and in root `README.md` ("versioned and released together"). [S7, S8]
6. `docs/skills/plab-wrap-session/README.md`'s per-section purpose descriptions, and `docs/skills/plab-continue-session/README.md`'s restatement of field expectations, must defer to the single-source documents. [S6, S10, S9]
7. This effort must not start before `derive-log-facts.py` exists and is wired into wrap's `SKILL.md`. [S1, S11]
8. The schema's field tables are the one list of fields. Every other copy must agree with them, checked by a test in a file CI already runs: `check-log.py`'s Tier 1 lists, the field lines of `derive-log-facts.py`'s text output, wrap `SKILL.md`'s Frontmatter block, the template's three frontmatter blocks, and the fields `lib/session-logs.py` and `reconcile.py` read. [S2, S3, S9, S13, S14, S15]

## Acceptance Criteria

**AC-1:** The string "hostname" as a derivation-method comment or table cell appears nowhere in `skills/plab-wrap-session/references/frontmatter-schema.md`, `skills/plab-wrap-session/references/session-log-template.md` or `skills/plab-wrap-session/SKILL.md` after this effort ships; they instead point at `derive-log-facts.py` for how derived fields are produced. Verified by `grep -rn hostname skills/plab-wrap-session/references/ skills/plab-wrap-session/SKILL.md` returning no matches. [S1, S2, S3, S9]

**AC-2:** `frontmatter-schema.md` carries no hand-maintained example frontmatter block; it points at wrap `SKILL.md`'s Frontmatter block, which AC-8's test holds to the Tier 1 table. Verified by reading the schema and confirming no fenced YAML example remains. [S2]

**AC-3:** No claim about the number of fields in the schema appears in either skill's shipped documentation. Verified by `grep -rnE --include=*.md "\b[0-9]{2,}[- ]fields?\b|\b[0-9]+-field\b" skills/plab-wrap-session skills/plab-continue-session docs/skills/plab-wrap-session docs/skills/plab-continue-session README.md` returning no matches. The pattern requires either two digits or a hyphenated count, so it does not match "Tier 1 fields". The scope excludes `docs/internal/release-plans/`, where this spec and its plan name the stale strings, and the `.py` files, where a count of the fields a check verified is output, not documentation. (Amended 2026-11-17, ruling D6; the original criterion checked only the literal "18-field", which had already been replaced by an equally stale "28 fields".) [S6]

**AC-4:** `skills/plab-continue-session/SKILL.md`'s Phase 2 no longer hand-enumerates a frontmatter field list that duplicates `frontmatter-schema.md`'s tables; it names the schema and says which fields it uses for what. Verified by reading Phase 2 and confirming the phrase "Extract from frontmatter:" is no longer followed by an independently maintained field list. [S4, S2]

**AC-5:** The claim that `plab-wrap-session` and `plab-continue-session` move and version together is asserted in exactly one shipped file, using one of its two current wordings verbatim. Verified by `grep -rlnE "version together|versioned and released together" skills/ docs/skills/ README.md CHANGELOG.md` returning exactly one file. [S7, S8]

**AC-6:** `docs/skills/plab-wrap-session/README.md`'s per-section purpose descriptions defer to `SKILL.md`'s Body Sections prose rather than independently re-describing each section's purpose a second time. Verified by reading the "Output Shape" section and confirming it references the source instead of carrying its own parallel prose for what each section contains. [S6, S9]

**AC-7:** This effort's implementation plan does not begin until `skills/plab-wrap-session/scripts/derive-log-facts.py` exists and `skills/plab-wrap-session/SKILL.md`'s Evidence Gathering section references it. Verified on 2026-11-13: the script exists and Evidence Gathering runs it. [S1, S11]

**AC-8:** `skills/plab-wrap-session/scripts/test-check-log.py` asserts that the copies named in Requirement 8 agree with the schema's tables, and that no derived field's "How to Derive" cell carries a shell command. Each assertion has a canary: a mutated input that must make it fail. Verified by the test failing on the tree as it stood on 2026-11-13, passing after this effort, and every canary reporting that it failed as intended. [S2, S3, S9, S13, S14, S15]

## Behavior / Examples

### Example 1: The "hostname" consolidation

Before this effort: `grep -rn hostname skills/plab-wrap-session/` matches `references/frontmatter-schema.md`, three per-mode blocks of `references/session-log-template.md`, and wrap `SKILL.md`'s Frontmatter block. After this effort, the same grep over the references and `SKILL.md` returns nothing; the only remaining matches under `skills/plab-wrap-session/` are inside `scripts/derive-log-facts.py` and its test file, where the word names the implementation.

### Example 2: Continue's Phase 2, before and after

Before: "Extract from frontmatter: `date`, `repo`, `branch`, `summary`, `status`, `session-type`, `model`, `agent`," a hand-typed list. After: Phase 2 names the schema as the field list, then says which fields the display shows and which ones the constraints compare.

### Example 3: The contract test catches a template drift

A later change adds a Tier 1 field to the schema and to `check-log.py` but forgets the template. Before this effort, nothing noticed until a wrap that copied the template failed its own self-check. After it, `test-check-log.py` fails in CI on the pull request that introduced the gap, naming the field and the template block that lacks it.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | Fewer independently authored restatements means fewer tokens spent loading redundant reference content at skill-load time, across both skills. | [S1] |
| Maintainability / auditability | Every AC is verifiable by grep, by direct reading, or by a test CI already runs. | [S1] |
| Compatibility | Consolidating the contract must not change any field name or log shape; a log written the day before this effort ships must still parse the same way the day after. | [S1] |

## Revisions

| Date | Change | By |
|---|---|---|
| 2026-08-23 | Initial draft created | agent |
| 2026-11-17 | Refreshed against the code at `635ed7b` and the maintainer's rulings D5 to D7. Non-Goal 2 narrowed to Evidence Gathering; Non-Goal 3 amended to allow one test in an existing test file; AC-1 extended to wrap `SKILL.md`; AC-2 now requires removing the hand-written example; AC-3 amended from the literal "18-field" to any field count; Requirement 8 and AC-8 added; AC-7 recorded as met; sources S13 to S15 added; status set to committed | agent |

## Sources & Evidence

- [S1] the maintainer's private defect record for the wrap/continue pair, 2026-08-18, section "D-10. The structural cause under D-1, D-2, D-5, and D-8." Maintainer-local, gitignored. Credibility A (primary design source for this effort).
- [S2] `skills/plab-wrap-session/references/frontmatter-schema.md`. Repo file, credibility A, read in full 2026-11-13.
- [S3] `skills/plab-wrap-session/references/session-log-template.md`. Repo file, credibility A, read in full.
- [S4] `skills/plab-continue-session/SKILL.md`. Repo file, credibility A, read in full 2026-11-13.
- [S5] `skills/plab-continue-session/references/handoff-display.md`. Repo file, credibility A, read in full 2026-11-13.
- [S6] `docs/skills/plab-wrap-session/README.md`. Repo file, credibility A.
- [S7] `skills/plab-continue-session/HISTORY.md`. Repo file, credibility A.
- [S8] `README.md` (repository root). Repo file, credibility A.
- [S9] `skills/plab-wrap-session/SKILL.md`. Repo file, credibility A, read in full 2026-11-13. Cited for the cross-skill pointer to continue's `log-discovery.md`, for the Frontmatter block, and for the Body Sections prose that other documents restate.
- [S10] `docs/skills/plab-continue-session/README.md`. Repo file, credibility A.
- [S11] `docs/internal/release-plans/_unassigned/W-02_derived-log-facts/spec.md`.
- [S12] `AGENTS.md`. Repo file, credibility A. Cited for the "personally useful, not maximal" design frame.
- [S13] `skills/plab-wrap-session/scripts/check-log.py`, `TIER1_REQUIRE_NONEMPTY` and `TIER1_REQUIRE_PRESENT_ONLY`. Repo file, credibility A, read 2026-11-13.
- [S14] `lib/session-logs.py`, `FIELDS`. Repo file, credibility A, read 2026-11-13.
- [S15] `skills/plab-continue-session/scripts/reconcile.py`, its frontmatter regex. Repo file, credibility A, read 2026-11-13.

### Unverified Claims

None.

## Open Questions / Decisions

| ID | Item | Status |
|---|---|---|
| D1 | Whether `frontmatter-schema.md` is deleted outright or retained for agent-authored fields only | Decided, see below |
| D2 | The source's "both HISTORY files" framing for the pairing claim | Decided, correcting the source, see below |
| D3 | Whether to build a generator or regeneration pipeline for the consolidated contract | Decided, see below |
| D4 | The task briefing's instruction to record the W-02 dependency via a `spec-dependencies` field | Decided, flagging a conflict, see below |
| D5 | What proves the copies agree | Decided 2026-11-17, see below |
| D6 | Whether AC-3 forbids any field count or only "18-field" | Decided 2026-11-17, see below |
| D7 | Which file keeps the pairing claim | Decided 2026-11-17, see below |

**D1.** `frontmatter-schema.md` is retained, not deleted, because it still documents fields the script does not produce: `session-type`, `model`, `model-settings`, `agent`, `status`, `skills-used`, `resumed-from`, the Tier 3 fields, and the tiering rationale itself. What changes is narrower: the document stops independently asserting the derivation method for fields the script does produce, and it stops carrying an example that can contradict its own table. [S2, S12]

**D2.** The task briefing that produced this spec, and the source's D-10 section, both describe the versioned-together claim as appearing in "both HISTORY files." Direct verification found it in only one, `skills/plab-continue-session/HISTORY.md`; `skills/plab-wrap-session/HISTORY.md` does not contain it. The second live instance is root `README.md`. AC-5 targets what was actually found. [S7, S8]

**D3.** The source is explicit that a shared schema should not be built as a separate artifact. This spec reads that as ruling out a generated or regenerated markdown file, and treats deletion of the duplicate prose, plus a pointer to the script itself, as the correct minimal-machinery resolution. No regeneration pipeline is proposed. D5's test is consistent with this: it generates nothing and reads the schema that already exists. [S1]

**D4.** The task briefing said to record the W-02 dependency using "spec-dependencies." No such frontmatter field exists in the closed `spec.md` schema. The dependency is recorded in prose instead, in Purpose, Requirement 7 and AC-7.

**D5. Decided by the maintainer, 2026-11-17: add a contract test (option B).** The alternative was the AC greps alone, run once. The template's missing `commit-range` and `latest-tag` show that drift arrives after a one-time check passes, so the test runs on every pull request. It lives in `test-check-log.py`, which CI already runs, so Non-Goal 3's bar on a new script or workflow step still holds.

**D6. Decided by the maintainer, 2026-11-17: AC-3 forbids any hardcoded field count (option A).** Requirement 3 already said "any hardcoded field count"; the original AC tested only the string it was written against, which had since become "28 fields". C-04 adds a field in the same pull request, so a count left in place would be wrong on merge.

**D7. Decided by the maintainer, 2026-11-17: root `README.md` keeps the claim, "versioned and released together" (option A).** The README is the live, reader-facing statement; continue's copy sat inside its dated 1.2.0 HISTORY entry, which now points to the README. Neither wording means the two skills carry the same version number: wrap is 1.11.1 and continue 1.7.0 when this was decided. They are released together, in one plugin.
