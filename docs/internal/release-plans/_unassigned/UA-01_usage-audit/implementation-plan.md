---
id: UA-01
title: "Implementation plan: plab-usage-audit"
type: implementation-plan
status: in-progress
created: 2026-10-30
updated: 2026-10-30
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 7
---

# Implementation plan: plab-usage-audit

Steps use checkbox syntax and phases run in order unless marked parallel. A phase is done when every step is ticked and its Verification command has been run and its output quoted.

**Goal:** `/plab-usage-audit` measures the owner's week of Claude Code usage with a fixture-proven collector, reconciles it against the ledger, gathers every other fact in one script call, runs bounded and routed agents including a verifier, and writes a scrubbed bundle that a self-testing checker passes.

**Spec:** `spec.md`

**Target version:** `plab-usage-audit` 1.0.0, a new skill.

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) in any file this plan touches. One paragraph per line.
- Every script is stdlib-only Python 3.11+ and follows the exit contract: 0 clean, 1 findings, 2 broken.
- No shipped file carries an owner-specific string: no drive-letter path, home path, user name or owner folder pattern. Fixtures are synthetic.
- No script prints a credential value.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | The collector is ported with every accounting rule proven by a fixture | AC-2 to AC-11 | agent (parallel) | Done |
| P2 | The ledger writes, refuses and reads schema 2 rows, and `--reproduce` works | AC-12 to AC-14 | agent (with P1) | Done |
| P3 | The audit facts come from one call | AC-15, AC-16 | agent (after P1) | Done |
| P4 | The scrub, the bundle checker and the sample bundle | AC-18 to AC-22 | agent (parallel) | Done |
| P5 | The skill, its references and its eval case | AC-1, AC-17, AC-23 | agent | Done |
| P6 | The plugin registers the skill and CI runs its checks | AC-21 (CI) | agent | Done |
| P7 | A live weekly run passes the checker | AC-24 | agent with the owner | Waiting for the owner's next audit day |

---

## Phase 1: The collector

**Goal:** `scripts/collect.py` reproduces the hand-run collector's totals and adds spec Requirements 1 to 11.

**Files:**
- Create `skills/plab-usage-audit/scripts/collect.py`
- Create `skills/plab-usage-audit/scripts/test-collect.py` and `skills/plab-usage-audit/scripts/fixtures/`
- Create `skills/plab-usage-audit/references/pricing.json`, `references/accounting-rules.md`, `references/collector-output.md`

**Fulfills:** AC-2 to AC-11

**Steps:**
- [x] Port the maintainer-local collector, version 2026-10-23, keeping every accounting rule and its tests, with owner values moved to a settings file read by `--config`.
- [x] Add the task-notification filter, the model-that-ran breakdown and `model_drift`, the `_dedup` and `_raw` suffixes, and `cost_by_half` and `responses_by_half`.
- [x] Document every output file and field in `references/collector-output.md`.
- [x] One synthetic fixture per rule, including the daylight-saving week under `America/Los_Angeles`.

**Verification:** `python skills/plab-usage-audit/scripts/test-collect.py` exits 0; with the task-notice filter removed, it fails and names that case.

---

## Phase 2: The ledger

**Goal:** `scripts/ledger.py` appends schema 2 rows, refuses duplicates, returns the newest row per week, reads older rows through an owner mapping, and the collector's `--reproduce` compares a row's method.

**Files:**
- Create `skills/plab-usage-audit/scripts/ledger.py`, `scripts/test-ledger.py`, `references/ledger-schema.md`
- Modify `skills/plab-usage-audit/scripts/collect.py` (`--ledger`, `--reproduce`)

**Fulfills:** AC-12 to AC-14

**Verification:** `python skills/plab-usage-audit/scripts/test-ledger.py` exits 0; with the duplicate check removed, it fails.

---

## Phase 3: The audit facts

**Goal:** `scripts/derive-audit-facts.py` returns spec Requirement 18's facts in one call and never outputs a credential value.

**Files:**
- Create `skills/plab-usage-audit/scripts/derive-audit-facts.py`, `scripts/test-derive-audit-facts.py`

**Fulfills:** AC-15, AC-16

**Verification:** `python skills/plab-usage-audit/scripts/test-derive-audit-facts.py` exits 0; the credential test fails when the value redaction is removed.

---

## Phase 4: The scrub, the checker and the sample

**Goal:** `scripts/scrub.py` and `scripts/bundle-check.py` enforce `references/bundle-format.md`, and `--self-test` proves each rule can fail against `examples/sample-bundle/`.

**Files:**
- Create `skills/plab-usage-audit/scripts/scrub.py`, `scripts/bundle-check.py`, `scripts/test-scrub.py`, `scripts/check-placement.py`
- Create `skills/plab-usage-audit/examples/sample-bundle/`

**Fulfills:** AC-18 to AC-22

**Verification:** `python skills/plab-usage-audit/scripts/bundle-check.py --self-test` exits 0, and `python skills/plab-usage-audit/scripts/test-scrub.py` exits 0.

---

## Phase 5: The skill

**Goal:** `SKILL.md`, `HISTORY.md`, and the references `workflow.md`, `positioning.md`, `scorecard.md` and `settings-example.md` describe a run end to end; the eval case proves the skill is manual-only.

**Files:**
- Create `skills/plab-usage-audit/SKILL.md`, `HISTORY.md`, `references/workflow.md`, `references/positioning.md`, `references/scorecard.md`, `references/settings-example.md`
- Copy `skills/plab-project-pulse/scripts/sweep.py` into `skills/plab-usage-audit/scripts/sweep.py`
- Create `evals/usage-audit-manual-no-fire/`
- Create `skills/plab-usage-audit/scripts/test-workflow-reference.py`

**Fulfills:** AC-1, AC-17, AC-23

**Verification:** `python skills/plab-usage-audit/scripts/test-workflow-reference.py` exits 0; the toolkit gate reports no error for the skill.

---

## Phase 6: Registration and CI

**Files:** `library.json` and the regenerated manifests, `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/skills/plab-usage-audit/README.md`, `evals/README.md`, `.github/workflows/gate.yml`, `scripts/gen-release-index.py`, `docs/internal/release-plans/README.md`, the regenerated `INDEX.md`.

**Verification:** the toolkit gate, `check-dashes.py`, `frontmatter-check.py`, `doc-lifecycle-check.py`, `gen-release-index.py --check`, `version-parity-check.py` and `skill-drift-check.py` all exit 0, quoted.

---

## Phase 7: A live weekly run

**Goal:** a weekly run on the maintainer's machine writes a bundle that `bundle-check.py` passes. This runs on the owner's next audit day, because it measures a real week and costs a real run.

**Fulfills:** AC-24

**Verification:** the checker's output, quoted.

---

## CI and Documentation Coverage

**CI.** `.github/workflows/gate.yml` gains steps in the existing job: `bundle-check.py --self-test`, and the collector, ledger, facts, scrub and workflow-reference tests.

**Documentation.** `CHANGELOG.md` under Unreleased, `HISTORY.md`, `README.md`, `AGENTS.md`, `docs/skills/plab-usage-audit/README.md`.

## Rollback

Delete `skills/plab-usage-audit/`, `evals/usage-audit-manual-no-fire/`, `docs/skills/plab-usage-audit/` and this effort folder. Remove the component from `library.json` and regenerate the manifests, and revert the `AGENTS.md`, `README.md`, `CHANGELOG.md`, `gate.yml` and series-legend additions. The owner's ledger and bundles live outside the plugin and are untouched.
