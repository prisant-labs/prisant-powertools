---
id: C-04
title: "Implementation plan: Record whether a resumed log's next action survived contact with reality"
type: implementation-plan
status: in-progress
created: 2026-08-23
updated: 2026-11-17
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 4
---

# Implementation Plan: Record whether a resumed log's next action survived contact with reality

> **For agentic workers:** steps use checkbox syntax for tracking. Execute phases in order. This plan was rewritten on 2026-11-13 against the code at `c572606` (main after v0.14.0). It runs after D-10 (log-format contract) in the same pull request, because both edit `frontmatter-schema.md`, the template and wrap `SKILL.md`'s Frontmatter block, and this plan's field must be covered by D-10's contract test.

**Goal:** A wrap that follows a `/plab-continue-session` resume records, in one frontmatter field of the new log, whether the resumed log's named next action was fulfilled, superseded or ignored. A wrap with no resume writes no such field. Nothing reads the field except the log's own self-check.

**Spec:** `spec.md`

**Target versions:** `plab-wrap-session` 1.11.1 to 1.12.0, a minor bump because the log gains a field and `check-log.py` gains a rule. `plab-continue-session` 1.7.0 to 1.7.1, a patch bump for D-10's documentation changes; continue's behaviour does not change. The plugin version in `library.json` does not move, because versions are assigned at release time.

**Global constraints:** No em-dashes or en-dashes. No hard-wrapped prose. Every reference ID carries a handle. One field, no new section, no new script, no report (spec Non-Goals).

---

## What the audit of 2026-11-13 found

| AC | State on 2026-11-13 | Evidence |
|---|---|---|
| AC-1 (a genuine resume gets a value) | Open | No such field exists; `grep -rn "resumed-from-disposition"` over `skills/` and `lib/` returns nothing |
| AC-2 (no resume, no field) | Open | As above |
| AC-3 (three values defined exactly) | Open | As above |
| AC-4 (only the new log is written) | Holds already as a rule, to be restated for the field | Continue `SKILL.md:148`, "Never modify the session log being resumed from" |
| AC-5 (only wrap writes it; continue writes no file) | Holds already for continue | Continue `SKILL.md:160`, "This skill produces no files" |
| AC-6 (nothing aggregates the field) | Holds; to be re-checked after the build | No reader exists |

Four facts have changed since the 2026-10-06 draft:

1. D-06 (resumed-from semantics) shipped. `frontmatter-schema.md:42-48` holds its rule: `resumed-from` is written only when continue resumed in this session.
2. W-07 (session-aware logs) gave that condition a mechanical handle. Wrap `SKILL.md:39` passes `--resumed-from <file>` to `derive-log-facts.py` only when this session resumed with continue, and the script then reports `carry-forward: <file> (rule resumed-from)`. The judgment step can be gated on exactly that condition rather than on the agent's memory.
3. "Disposition" already means something else in wrap. `SKILL.md:55` uses it for the same-arc archive: "record the disposition, declared plus archived-or-not, in the new log's Summary". That bears on OQ-1 (field name).
4. Both readers of frontmatter anchor on the whole key. `lib/session-logs.py:160` matches `^([A-Za-z][A-Za-z0-9-]*):` and checks the key against `FIELDS`; `check-log.py:178` matches `^{field}:`. A key beginning `resumed-from-` therefore cannot be read as `resumed-from`. Phase 2 proves this with a fixture rather than relying on this reading.

---

## Rulings needed before Phase 1

| ID | Question | Options | Recommendation |
|---|---|---|---|
| OQ-1 (field name) | What is the field called? | **A.** `resumed-from-outcome`. **B.** `resumed-from-disposition`, as the spec proposed. | **A.** The maintainer's writing rules use one word for one thing, and "disposition" already names the same-arc archive decision at wrap `SKILL.md:55`. The effort folder keeps its name; only the field changes. |
| OQ-2 (no fourth value) | Keep exactly three values? | **A.** Yes; the wrap commits to the closest of the three. **B.** Add `partial`. | **A.** As the spec argues: the field inherits D-06's "worth one line and no more" ceiling, and a mixed value would weaken the falsifier `ignored` exists to be. |
| R1 (proof mechanism; shared with D-10's plan) | What proves AC-1 and AC-2? | **A.** The spec's three prose walkthroughs only. **B.** Also a rule in `check-log.py`, which every wrap already runs: `resumed-from` present requires the new field, the new field requires `resumed-from`, and its value must be one of the three. B needs AC-6 clarified. | **B.** A walkthrough checks the text of the step once; the rule checks every log. AC-6 forbids digests, aggregation and reports. A self-check that reads only the log being written is none of those, but the spec should say so. |

The steps below assume OQ-1 A, OQ-2 A and R1 B, and write the field as `resumed-from-outcome`. Under OQ-1 B, substitute the spec's name throughout. Under R1 A, Phase 2 is dropped and Phase 3's verification is the three walkthroughs.

**Ruled 2026-11-17.** The maintainer chose every recommendation: OQ-1 A, OQ-2 A and R1 B.

**Execution record, 2026-11-17.** The plan ran as written, with three differences:

1. **All three template blocks got the field, not only the Final block.** The Quick and Blocked blocks also lacked `resumed-from`, so a quick wrap after a resume had nowhere to record it. Both now carry `resumed-from` and `resumed-from-outcome`, with the same omit-both comment. `check-log.py` applies the pairing rule in every mode, so the template had to match it.
2. **The test count changed.** Phase 2 planned five fixture cases; seven were written, adding a second clean value (`ignored`) and an empty outcome.
3. **The rule was run over the real store.** 24 of the maintainer's 49 logs carry `resumed-from`, and all 24 would now be flagged, because they predate the field. Only a wrap runs `check-log.py`, and only on the log it has just written, so no existing log is ever checked against the rule. Nothing else calls `check-log.py`.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Refresh the spec against current code and the rulings | N/A (spec amendment) | agent | Done 2026-11-17 |
| P2 | `check-log.py` rule, tests first | AC-1, AC-2 (mechanical half) | agent | Done 2026-11-17 |
| P3 | Schema row, template, and the wrap-time judgment step | AC-1, AC-2, AC-3, AC-4, AC-5 | agent | Done 2026-11-17 |
| P4 | Restraint check, then version and document both efforts | AC-6 | agent | Done 2026-11-17 |

---

## Phase 1: Refresh the spec against current code and the rulings

**Goal:** The spec carries the field's final name, the rulings, and current evidence, so the PR checks off criteria it actually meets.

**Files:** Modify `docs/internal/release-plans/_unassigned/C-04_consumption-disposition/spec.md`.

**Fulfills:** N/A (spec amendment; no criterion changes substance).

**Steps:**
- [x] Step 1: Record OQ-1 and OQ-2 as decided, with the maintainer's answers and the date, and rename the field throughout under OQ-1 A.
- [x] Step 2: Update the Purpose and Requirement 3 dependency text. D-06 shipped, not "shipping in v0.4.0". The gate is the same condition that adds `--resumed-from` at wrap `SKILL.md:39`.
- [x] Step 3: Under R1 B, append to AC-6: "The log's own self-check in `check-log.py`, which reads only the log being written, is not consumption in this sense." Add "Verified by `check-log.py`" to AC-1 and AC-2.
- [x] Step 4: Unwrap the hard-wrapped prose the 2026-08-23 draft carries, because AGENTS.md forbids it. Set `updated: 2026-11-13`, and add a Revisions row.

**Verification:** `C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe scripts/frontmatter-check.py && C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe scripts/doc-lifecycle-check.py` both exit 0.

---

## Phase 2: `check-log.py` rule, tests first

**Goal:** `check-log.py` reports a finding for any log whose `resumed-from` and `resumed-from-outcome` disagree, and the tests showing this were red before the rule existed.

**Files:** Modify `skills/plab-wrap-session/scripts/test-check-log.py`, `skills/plab-wrap-session/scripts/check-log.py`, `lib/test-session-logs.py`.

**Fulfills:** AC-1 and AC-2, mechanical half.

**Steps:**
- [x] Step 1: Add five fixture cases to `test-check-log.py`: both fields present with `fulfilled` (clean); `resumed-from` alone (finding: "resumed-from is set, so resumed-from-outcome must be fulfilled, superseded or ignored"); the outcome alone (finding: "resumed-from-outcome needs resumed-from"); `resumed-from-outcome: partial` (finding naming the three values); neither field (clean). Run them and quote the three red cases before Step 3.
- [x] Step 2: Add one case to `lib/test-session-logs.py`: a log carrying `resumed-from: a.md` and `resumed-from-outcome: fulfilled` reads `resumed-from` as `a.md`. This proves the key does not collide.
- [x] Step 3: Add the rule to `check_session_fields()` in `check-log.py`, beside the W-07 checks, with `OUTCOME_VALUES = ("fulfilled", "superseded", "ignored")` as the one place in code the three values live. Extend the function's docstring and the "all present" detail line.
- [x] Step 4: Add `resumed-from-outcome` to the schema's Tier 2 table (Phase 3 Step 1) before running D-10's contract test, which otherwise fails on a field the schema does not list.

**Verification:** `C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe skills/plab-wrap-session/scripts/test-check-log.py && C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe lib/test-session-logs.py` both exit 0 after Step 3, and the quoted pre-rule run shows the three finding cases failing.

---

## Phase 3: Schema row, template, and the wrap-time judgment step

**Goal:** The field is defined once in the schema, appears in the Final template and in wrap `SKILL.md`'s Frontmatter block, and wrap has one step that writes it only after a resume this session.

**Files:** Modify `skills/plab-wrap-session/references/frontmatter-schema.md`, `skills/plab-wrap-session/references/session-log-template.md`, `skills/plab-wrap-session/SKILL.md`.

**Fulfills:** AC-1, AC-2, AC-3, AC-4, AC-5.

**Steps:**
- [x] Step 1: In the schema's Tier 2 table, after `resumed-from`, add: "| `resumed-from-outcome` | Enum | What happened to the resumed log's named next action: `fulfilled`, `superseded` or `ignored`. Written only with `resumed-from` | Semi - agent judges |".
- [x] Step 2: After the "`resumed-from` semantics" subsection, add "`resumed-from-outcome` semantics", defining the values in the spec's AC-3 words. `fulfilled`: the prior log's named next action was completed. `superseded`: circumstances changed and the plan was correctly abandoned. `ignored`: the session re-derived context and went on without engaging the named action. Add that the field is written only when `resumed-from` is, into the new log only, never into the resumed log, and that `check-log.py` enforces the pairing.
- [x] Step 3: In the template's Final block, add after `resumed-from:` the line `resumed-from-outcome: # fulfilled|superseded|ignored; only with resumed-from, else omit`. Add the same line to wrap `SKILL.md`'s Frontmatter block after line 185.
- [x] Step 4: Add Evidence Gathering step 9 to wrap `SKILL.md`, after step 8: "When this session resumed with `/plab-continue-session`, the same condition that adds `--resumed-from`, judge the resumed log's named next action against this session's work, and write one of the three values in `references/frontmatter-schema.md` into this log's `resumed-from-outcome:`. Write it only into the log being written, never into the resumed log. With no resume this session, omit both fields."
- [x] Step 5: Walk the spec's three walkthroughs (fulfilled, ignored, no resume) against Step 4's text and record the result in the PR body.

**Verification:** `grep -n "resumed-from-outcome" skills/plab-wrap-session/references/frontmatter-schema.md skills/plab-wrap-session/references/session-log-template.md skills/plab-wrap-session/SKILL.md` matches all three files, and the schema match names all three values. `test-check-log.py` still exits 0, including D-10's contract test.

---

## Phase 4: Restraint check, then version and document both efforts

**Goal:** The effort stayed at one field and one self-check rule, and both skills carry the version, history and documentation the drift check compares.

**Files:** Modify `skills/plab-wrap-session/SKILL.md` and `skills/plab-continue-session/SKILL.md` (`metadata.version`, `updated`), both `HISTORY.md` files, `library.json`, `CHANGELOG.md`, root `README.md` (skill table), both `docs/skills/*/README.md` (`**Version:**` line, and one paragraph on the new field in wrap's README); regenerate `manifest.generated.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`.

**Fulfills:** AC-6.

**Steps:**
- [x] Step 1: `git diff --stat origin/main` lists no new file under `scripts/` and no new section in the template. `grep -rn "resumed-from-outcome" --include=*.py .` matches only `check-log.py` and the two test files.
- [x] Step 2: Bump wrap to 1.12.0 and continue to 1.7.1, with `updated: 2026-11-13`, in each `SKILL.md`, `library.json` and both usage READMEs.
- [x] Step 3: Write wrap's 1.12.0 HISTORY entry (D-10 consolidation, the template's missing `commit-range` and `latest-tag`, the contract test, the new field and its rule) and continue's 1.7.1 entry (Phase 2 now defers to the schema; the pairing paragraph points to the README). Neither entry may quote "18-field" or either pairing wording (D-10 plan, Phase 6 Step 2).
- [x] Step 4: Add `[Unreleased]` bullets to `CHANGELOG.md`, user value first: a resumed session's log now records whether the plan it resumed survived, and a wrap that follows the template no longer fails its own self-check.
- [x] Step 5: Regenerate the manifests with `node <agent-skills-toolkit>/scripts/generators/gen-manifest.mjs . --write --target=all`; never hand-edit them.
- [x] Step 6: Run the gates in AGENTS.md, "Build and validate", plus both skills' test suites, and run `check-log.py` read-only against the newest real log in the main checkout's store and `derive-log-facts.py` against the worktree. Quote each output in the PR body.

**Verification:** `C:/Users/jpris/AppData/Local/Programs/Miniconda3/python.exe scripts/skill-drift-check.py` reports both skills bumped with HISTORY entries, `scripts/version-parity-check.py` exits 0, and `git diff origin/main -- library.json` shows only the two skill versions changed.

---

## CI and Documentation Coverage

### CI

No change to `.github/workflows/gate.yml`. The new rule's tests sit in `test-check-log.py` (`gate.yml:320`), and the no-collision case sits in `lib/test-session-logs.py` (`gate.yml:338`), so both run on every pull request already.

### Documentation

Agent-facing: `frontmatter-schema.md` (row and semantics subsection), `session-log-template.md` (Final block), wrap `SKILL.md` (Frontmatter block and Evidence Gathering step 9). Continue's `SKILL.md` changes only its version in this plan. Human-facing: wrap's usage README gains one paragraph saying the field is one line with nothing behind it, so no reader expects a dashboard; both HISTORY files, `CHANGELOG.md` and root `README.md` change as in Phase 4. `AGENTS.md` does not change.

---

## Rollback

The field is additive and nothing reads it but the self-check, so removing it loses only the recorded values. To undo: remove the schema row and its semantics subsection, the two template and Frontmatter-block lines, Evidence Gathering step 9, the rule and `OUTCOME_VALUES` in `check-log.py`, and the six test cases. Then lower wrap to 1.11.1 and continue to 1.7.0 in every place Phase 4 set them, with HISTORY entries recording the revert. Partial-rollback hazard: removing the rule but keeping step 9 leaves an unchecked field; removing the schema row but keeping the template line fails D-10's contract test. Logs already written with the field keep it harmlessly, because no reader requires its absence.
