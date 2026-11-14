---
id: D-10
title: "Implementation plan: Make derive-log-facts.py's output the single log-format contract"
type: implementation-plan
status: draft
created: 2026-08-23
updated: 2026-11-13
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 6
---

# Implementation Plan: Make derive-log-facts.py's output the single log-format contract

> **For agentic workers:** steps use checkbox syntax for tracking. Execute phases in order. This plan was rewritten on 2026-11-13 against the code at `c572606` (main after v0.14.0), because the 2026-10-06 draft predated W-02 (derived log facts), W-05 (wrap hygiene order) and W-07 (session-aware logs), all of which changed the files below. It ships in one pull request with C-04 (consumption disposition), whose plan runs after this one and carries the version bookkeeping for both.

**Goal:** Every field of a session log is listed once, in `skills/plab-wrap-session/references/frontmatter-schema.md`, and every derived field's method is stated once, in `derive-log-facts.py`. Every other copy either points there or is held to it by a test, so the writer (`plab-wrap-session`), the validator (`check-log.py`) and the reader (`plab-continue-session` and `lib/session-logs.py`) cannot drift apart without a red CI run.

**Spec:** `spec.md`

**Target versions:** `plab-wrap-session` 1.11.1 to 1.12.0 and `plab-continue-session` 1.7.0 to 1.7.1, set in C-04's plan, Phase 4. The plugin version in `library.json` does not move, because versions are assigned at release time.

**Global constraints:** No em-dashes or en-dashes. No hard-wrapped prose. Every reference ID carries a handle. Field names and log shape do not change in this plan (spec Non-Goal 4); C-04 adds one field afterwards.

---

## What the audit of 2026-11-13 found

Each criterion was checked against the code at `c572606` before this plan was written.

| AC | State on 2026-11-13 | Evidence |
|---|---|---|
| AC-1 (no "hostname" derivation text in wrap references) | Open, and wider than the spec knew | `grep -rn hostname` matches `frontmatter-schema.md:15`, `session-log-template.md:15`, `:124`, `:161`, and also wrap `SKILL.md:171`, which the spec fenced off as W-02's territory |
| AC-2 (schema example matches its Tier 1 table) | Open, and worse | The Example Frontmatter block omits `type`, `machine`, `commit-range` and `latest-tag`, four of the nine Tier 1 fields |
| AC-3 (no "18-field" claim) | Met literally, defect moved | "18-field" is gone, but `docs/skills/plab-wrap-session/README.md:295`, `:319` and `:339` now say 28 fields. C-04 makes that 29, so the count is wrong again on C-04's merge |
| AC-4 (continue Phase 2 does not hand-list fields) | Open | `skills/plab-continue-session/SKILL.md:60` and `docs/skills/plab-continue-session/README.md:89` both carry the same eight-field list |
| AC-5 (pairing claim in exactly one file) | Open | `skills/plab-continue-session/HISTORY.md:151` and root `README.md:134` |
| AC-6 (wrap README defers to SKILL.md Body Sections) | Open | The Output Shape table at `docs/skills/plab-wrap-session/README.md:178-191` restates every section's purpose |
| AC-7 (W-02 shipped first) | Met | `derive-log-facts.py` exists and wrap `SKILL.md:39` (Evidence Gathering) runs it |

Five drifts the 2026-10-06 spec did not know about, each of which shows that a pointer alone will not hold:

1. The template's three frontmatter blocks (`session-log-template.md` Final, Quick and Blocked) omit `commit-range` and `latest-tag`. A wrap that copies the template writes a log that `check-log.py` fails, because `check-log.py:123-124` requires all nine Tier 1 fields.
2. The wrap README's Tier table (`README.md:287-291`) omits `skills-used`, `resumed-from`, `session-id`, `session-start` and `carried-from` from Tier 2, and `transcript-path` and `adrs-created` from Tier 3.
3. `type` is not script output. The `data` dict in `derive-log-facts.py:1075-1112` has no `type` key, yet `frontmatter-schema.md:23` and wrap `SKILL.md:165` both say the script produces it. It is a constant, `session-log`.
4. The reader side is now code, not prose. `lib/session-logs.py:55` reads six fields (`date`, `branch`, `session-id`, `session-start`, `resumed-from`, `carried-from`) and `reconcile.py:143` reads five (`date`, `branch`, `repo`, `commit-sha`, `commit-range`). The spec's premise that continue reads the log through the agent alone is out of date.
5. The validator is also code: `check-log.py`'s `TIER1_REQUIRE_NONEMPTY` and `TIER1_REQUIRE_PRESENT_ONLY` are a second, independent statement of Tier 1.

---

## Rulings needed before Phase 1

| ID | Question | Options | Recommendation |
|---|---|---|---|
| R1 (proof mechanism) | What proves the contract holds? | **A.** The AC greps only, quoted failing and then passing, as the spec says. **B.** Also a contract test in `test-check-log.py`, which CI already runs, binding the schema's tables to the writer, validator and reader code. B needs spec Non-Goal 3 amended. | **B.** Drift 1 above already shipped while every pointer was in place. Non-Goal 3 gave D-3 (bidirectional doc drift) and D-11 (three-state gate canaries) as the owners of drift detection, but D-3 checks version bumps and D-11 checks gate canaries; neither checks field lists. |
| R2 (AC-3 scope) | Amend AC-3 from "no 18-field string" to "no hardcoded field count"? | **A.** Amend. **B.** Leave it; AC-3 is met. | **A.** Requirement 3 already says "any hardcoded field count", and C-04 makes the current 28 wrong. |
| R3 (AC-5 survivor) | Which file keeps the pairing claim? | **A.** Root `README.md:134` keeps "versioned and released together"; the continue HISTORY 1.2.0 paragraph points to it. **B.** The HISTORY paragraph keeps "move and version together"; the README points to it. | **A.** The README is the live, reader-facing statement; the HISTORY paragraph is inside a dated 1.2.0 entry. Note that neither wording means the version numbers match: wrap is 1.11.1 and continue is 1.7.0. |

The steps below assume R1 B, R2 A and R3 A. Under R1 A, Phase 2 is dropped and the greps in each phase's Verification are the only proof.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Refresh the spec against current code and the rulings | AC-7 | agent | Not started |
| P2 | Contract test first, failing on the current tree | AC-1, AC-2 (mechanical half) | agent | Not started |
| P3 | Wrap references and wrap SKILL.md's Frontmatter block point at the script | AC-1, AC-2 | agent | Not started |
| P4 | Continue's Phase 2, display reference and README stop hand-listing fields | AC-4 | agent | Not started |
| P5 | Wrap README defers to the schema and to SKILL.md | AC-3, AC-6 | agent | Not started |
| P6 | Pairing claim in exactly one file | AC-5 | agent | Not started |

---

## Phase 1: Refresh the spec against current code and the rulings

**Goal:** The spec describes the repository as it is on 2026-11-13, so the criteria this PR checks off are the criteria the PR actually meets.

**Files:** Modify `docs/internal/release-plans/_unassigned/D-10_log-format-contract/spec.md`.

**Fulfills:** AC-7 (recorded as met, with the evidence).

**Steps:**
- [ ] Step 1: Retire Non-Goal 2. Before: "Does not modify `skills/plab-wrap-session/SKILL.md`'s Evidence Gathering or Frontmatter sections. W-02 owns wrap's own consumption of the script". After: "Does not modify `skills/plab-wrap-session/SKILL.md`'s Evidence Gathering section. Its Frontmatter block is in scope from 2026-11-13: W-02 shipped in 1.8.0, so the reason for fencing it off has expired, and the block carries the fourth copy of the `hostname` comment."
- [ ] Step 2: Under R1 B, amend Non-Goal 3 to rule out a new script or CI step while allowing a test inside the existing `test-check-log.py`, and add Requirement 8 and AC-8: "The schema's tables, `check-log.py`'s Tier 1 lists, the field lines of `derive-log-facts.py`'s text output, wrap `SKILL.md`'s Frontmatter block, the template's three frontmatter blocks, and the fields `lib/session-logs.py` and `reconcile.py` read agree, checked by `test-check-log.py`, with each assertion's canary proven to fail."
- [ ] Step 3: Under R2 A, amend AC-3's verification to `grep -rnE "[0-9]+[- ]fields?\b" skills/plab-wrap-session skills/plab-continue-session docs/skills/plab-wrap-session docs/skills/plab-continue-session README.md`, returning no claim about the size of the schema.
- [ ] Step 4: Add the wrap SKILL.md Frontmatter block and the wrap README Tier table to In Scope. Change the version line in In Scope item 7 from "continue to 1.6.0" to "both skills, per C-04's plan Phase 4".
- [ ] Step 5: Tick AC-7 in the Task Summary, set `updated: 2026-11-13`, `ac-count` to 8 under R1 B, and add a Revisions row naming every change above.

**Verification:** `C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe scripts/frontmatter-check.py && C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe scripts/doc-lifecycle-check.py` both exit 0.

---

## Phase 2: Contract test first, failing on the current tree

**Goal:** A test exists that fails today, naming drift 1 (the template's missing `commit-range` and `latest-tag`), and each of its assertions is shown to fail when the rule it guards is broken.

**Files:** Modify `skills/plab-wrap-session/scripts/test-check-log.py`.

**Fulfills:** AC-8 under R1 B, and the mechanical half of AC-1 and AC-2.

**Steps:**
- [ ] Step 1: Add a parser that reads the field names from the three tier tables in `frontmatter-schema.md`, keyed by tier. It reads backtick-quoted names in the first column only.
- [ ] Step 2: Add these assertions, each written as a function of text so a canary can feed it a mutated copy:
  - the Tier 1 set equals `TIER1_REQUIRE_NONEMPTY + TIER1_REQUIRE_PRESENT_ONLY` from `check-log.py`;
  - every `name:` line under `Frontmatter fields` in `derive-log-facts.py`'s text output, from the fixture repository the existing derive tests already build, is a schema field;
  - wrap `SKILL.md`'s Frontmatter YAML block and each of the template's three frontmatter blocks carry every Tier 1 field;
  - every field in `lib/session-logs.py`'s `FIELDS` and in `reconcile.py`'s frontmatter regex is a schema field;
  - no "How to Derive" cell for a field the script produces carries a shell command (`hostname`, `git `), so the method lives in the script.
- [ ] Step 3: Add one canary per assertion: drop a Tier 1 row, add a fake key to the reader list, delete `latest-tag:` from a block, and put `hostname` back in a cell. Each mutated input must make its assertion fail.
- [ ] Step 4: Run the suite on the unchanged tree and quote the failure. Expected: the template-block assertion fails for `commit-range` and `latest-tag` in all three modes, and the How-to-Derive assertion fails on `machine`, `repo`, `branch` and `files-changed`.

**Verification:** `C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe skills/plab-wrap-session/scripts/test-check-log.py` exits non-zero before Phase 3, naming exactly those fields, and every canary reports that it failed as intended.

---

## Phase 3: Wrap references and wrap SKILL.md's Frontmatter block point at the script

**Goal:** The schema lists every field once, and each derived field's method is the script's. The template and wrap SKILL.md's block carry every Tier 1 field and no method text.

**Files:** Modify `skills/plab-wrap-session/references/frontmatter-schema.md`, `skills/plab-wrap-session/references/session-log-template.md`, `skills/plab-wrap-session/SKILL.md` (the Frontmatter section, lines 163-190, re-verified first).

**Fulfills:** AC-1, AC-2.

**Steps:**
- [ ] Step 1: In the schema's Tier 1 table, set the "How to Derive" cell to `derive-log-facts.py` for `date`, `machine`, `repo`, `branch`, `files-changed`, `commit-range` and `latest-tag`. Keep the Example column. For instance, the `machine` cell, before: "`hostname` - which checkout wrote this log (logs are machine-local)". After: "`derive-log-facts.py`; which checkout wrote this log, because logs are machine-local". For `type`, before: "Always `session-log` (per document-conventions.md §2.4)". After: "Constant, always `session-log`; the agent writes it, the script does not".
- [ ] Step 2: Correct the paragraph under the table. Before: "Both come from the same `derive-log-facts.py` run as the other six script-derived Tier 1 fields (`date`, `type`, `machine`, `repo`, `branch`, `files-changed`); `summary` is the one Tier 1 field the agent writes." After: "Both come from the same `derive-log-facts.py` run as `date`, `machine`, `repo`, `branch` and `files-changed`. The agent writes `summary` and the constant `type`."
- [ ] Step 3: Delete the Example Frontmatter block and its heading. Put in its place: "The frontmatter a wrap writes is wrap `SKILL.md`'s Frontmatter block, filled from the script's `Frontmatter fields` output. `test-check-log.py` checks that the block carries every Tier 1 field, so there is no second hand-kept example here to drift."
- [ ] Step 4: In the template's three frontmatter blocks, add `commit-range:` and `latest-tag:` after `files-changed:`, each commented `# from derive-log-facts.py`. Change `machine: # hostname` to `machine: # from derive-log-facts.py`. Give `date:`, `repo:`, `branch:` and `files-changed:` the same comment.
- [ ] Step 5: In wrap `SKILL.md`, change line 171. Before: "`machine: # hostname - from derive-log-facts.py; which checkout wrote this log; logs are machine-local and cannot cross checkouts`". After: "`machine: # from derive-log-facts.py; which checkout wrote this log`". In line 165, remove `type` from the list of script-derived fields and add "`type` is the constant `session-log`."

**Verification:** `grep -rn hostname skills/plab-wrap-session/references/ skills/plab-wrap-session/SKILL.md` returns nothing, and `test-check-log.py` exits 0.

---

## Phase 4: Continue's Phase 2, display reference and README stop hand-listing fields

**Goal:** Continue names the fields it uses by their purpose and defers the field list to the schema, following the cross-skill pointer that wrap `SKILL.md:159` already uses for `log-discovery.md`.

**Files:** Modify `skills/plab-continue-session/SKILL.md`, `skills/plab-continue-session/references/handoff-display.md`, `docs/skills/plab-continue-session/README.md`.

**Fulfills:** AC-4.

**Steps:**
- [ ] Step 1: In continue `SKILL.md` Phase 2, change step 2. Before: "Extract from frontmatter: `date`, `repo`, `branch`, `summary`, `status`, `session-type`, `model`, `agent`." After: "Read the frontmatter. Its fields are defined once, in `plab-wrap-session/references/frontmatter-schema.md`; do not restate them here. Phase 4 displays `date`, `model`, `status`, `summary` and `branch`, and Constraints compares `repo` and `branch` with the current checkout."
- [ ] Step 2: In `handoff-display.md`, "What to include", change the Frontmatter facts bullet to cite the same schema for the field definitions and keep the five display fields.
- [ ] Step 3: In `docs/skills/plab-continue-session/README.md:89`, make the same change as Step 1 in reader-facing words.

**Verification:** `grep -n "Extract from frontmatter:" skills/plab-continue-session/SKILL.md docs/skills/plab-continue-session/README.md` returns nothing, and Phase 2 names the schema file.

---

## Phase 5: Wrap README defers to the schema and to SKILL.md

**Goal:** The human-facing wrap README carries no field count, no tier table of its own, and no second description of each section's purpose.

**Files:** Modify `docs/skills/plab-wrap-session/README.md`.

**Fulfills:** AC-3, AC-6.

**Steps:**
- [ ] Step 1: Replace the Tier table at lines 287-291 and the paragraph at line 293 with: "Every log carries YAML frontmatter in three tiers: Tier 1 always, Tier 2 and Tier 3 when the data exists. The field list, what each field means, and which ones `derive-log-facts.py` fills in are in [`references/frontmatter-schema.md`](../../../skills/plab-wrap-session/references/frontmatter-schema.md). `check-log.py` fails a log that is missing a Tier 1 field."
- [ ] Step 2: At line 295, change "(28 fields, including ...)" to drop the count. At lines 319 and 339, change "Complete 28-field metadata specification (3 tiers)" and "28-field metadata reference (3 tiers)" to "The field list, in three tiers".
- [ ] Step 3: In the Output Shape table at lines 178-191, keep the Section / Element column. Replace the Purpose column with one sentence above the table: "What each section must contain is defined in `SKILL.md`, Body Sections (Final Mode), and the Final-mode table under Four Modes above summarizes it." Leave the table as a list of section names in order.

**Verification:** Under R2 A, the amended AC-3 grep returns no schema-size claim. `grep -n "28" docs/skills/plab-wrap-session/README.md` returns no field count.

---

## Phase 6: Pairing claim in exactly one file

**Goal:** The claim that the two skills move together is stated once, in root `README.md`.

**Files:** Modify `skills/plab-continue-session/HISTORY.md`.

**Fulfills:** AC-5.

**Steps:**
- [ ] Step 1: Under R3 A, in the 1.2.0 entry, change the Pairing contract paragraph. Before: "This skill reads what `/plab-wrap-session` writes. The two move and version together; a change to the session-log format in one requires a matching change in the other." After: "This skill reads what `/plab-wrap-session` writes. The pairing contract is stated in the root README, under How the skills fit together." Keep the legacy-locations sentence that follows.
- [ ] Step 2: Write the new HISTORY and CHANGELOG entries (C-04 plan, Phase 4) without either wording, because the AC-5 grep scans `skills/` and `CHANGELOG.md`.

**Verification:** `grep -rlnE "version together|versioned and released together" skills/ docs/skills/ README.md CHANGELOG.md` prints exactly `README.md`.

---

## CI and Documentation Coverage

### CI

No change to `.github/workflows/gate.yml`. Under R1 B, the contract test lives in `skills/plab-wrap-session/scripts/test-check-log.py`, which the gate already runs (`gate.yml:320`), so it runs on every pull request without a new step. Under R1 A, nothing new runs in CI, and the contract is held by the greps in this plan only on the day this plan runs.

### Documentation

Agent-facing: `frontmatter-schema.md`, `session-log-template.md`, wrap `SKILL.md` (Frontmatter section only), continue `SKILL.md` (Phase 2 only), `handoff-display.md`. Human-facing: both `docs/skills/*/README.md` files and continue's `HISTORY.md` 1.2.0 paragraph. The version lines, `HISTORY.md` entries, `CHANGELOG.md` `[Unreleased]`, `library.json`, root `README.md` skill table and the regenerated manifests are done once for both efforts in C-04's plan, Phase 4. `AGENTS.md` does not change, because no trigger, skill name or blurb-level behaviour changes.

---

## Rollback

There is no schema change and no data migration: no field is renamed, and a log written before this plan parses the same way after it. To undo the whole effort, revert the six files Phases 3 to 6 touch and the test added in Phase 2. To restore the old text exactly, take it from `c572606`, for example `git show c572606:skills/plab-wrap-session/references/frontmatter-schema.md`. Reverting Phase 3 without Phase 2 leaves a red CI run, because the contract test then fails on the template again; revert the two together. Reverting Phase 6 alone puts the pairing claim back in two files, which is harmless but fails AC-5. C-04 depends on Phase 3's template blocks and Phase 2's test, so revert C-04 first if both are being undone.
