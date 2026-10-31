---
id: PP-01
title: "Implementation plan: plab-project-pulse"
type: implementation-plan
status: in-progress
created: 2026-10-30
updated: 2026-10-30
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 6
---

# Implementation plan: plab-project-pulse

Steps use checkbox syntax and phases run in order unless marked parallel. A phase is done when every step is ticked and its Verification command has been run and its output quoted.

**Goal:** `/plab-project-pulse` finds every repository under the configured roots, gathers every deterministic fact in one call, reads fresh `plab-current-status` snapshots instead of scouting, scouts the rest with routed agents, and writes a private `pulse.json`, readout and dashboard that a self-testing checker passes.

**Spec:** `spec.md`

**Target version:** `plab-project-pulse` 1.0.0, a new skill.

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) in any file this plan touches. One paragraph per line.
- Every script is stdlib-only Python 3.11+ and follows the exit contract: 0 clean, 1 findings, 2 broken.
- No script runs a git command that writes to a repository; tests build their fixture repositories in a temporary folder.
- No shipped file carries an owner-specific string. Fixtures are synthetic.
- `references/pulse-schema.md` is the contract between the scripts. A change to it is made there first.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Discovery and the sweep follow C1 and C2 | AC-2 to AC-10 | agent (parallel) | Done |
| P2 | The facts script classifies, carries forward, reads snapshots, ages waiting items and finds unprotected work | AC-11 to AC-15 | agent (with P1) | Done |
| P3 | Assembly, the dashboard and the checker | AC-17, AC-18, AC-20 to AC-24 | agent (parallel) | Done |
| P4 | The skill, its references and its eval case | AC-1, AC-16, AC-19 | agent | Done; AC-16 and AC-19 wait for a `--week` run |
| P5 | The plugin registers the skill and CI runs its checks | AC-24 (CI) | agent | Done |
| P6 | Live runs pass the checker | AC-25, AC-26 | agent | `--quick` done (AC-25); `--week` waits for the owner's next audit day |

---

## Phase 1: Discovery and the sweep

**Files:**
- Create `skills/plab-project-pulse/scripts/discover.py`, `scripts/sweep.py`, `scripts/test-discover-sweep.py`

**Fulfills:** AC-2 to AC-10

**Verification:** `python skills/plab-project-pulse/scripts/test-discover-sweep.py` exits 0; with the link check removed, it fails and names the alias case.

---

## Phase 2: The facts script

**Files:**
- Create `skills/plab-project-pulse/scripts/derive-pulse-facts.py`, `scripts/test-derive-pulse-facts.py`

**Fulfills:** AC-11 to AC-15

**Verification:** `python skills/plab-project-pulse/scripts/test-derive-pulse-facts.py` exits 0; with the snapshot filename pattern loosened to any `.md`, the register case fails.

---

## Phase 3: Assembly, the dashboard and the checker

**Files:**
- Create `skills/plab-project-pulse/scripts/build-pulse.py`, `scripts/render.py`, `scripts/pulse-check.py`, `scripts/test-build-render.py`
- Create `skills/plab-project-pulse/assets/dashboard.html`
- Create `skills/plab-project-pulse/examples/sample-pulse/`

**Fulfills:** AC-17, AC-18, AC-20 to AC-24

**Verification:** `python skills/plab-project-pulse/scripts/pulse-check.py --self-test` exits 0, and `python skills/plab-project-pulse/scripts/test-build-render.py` exits 0.

---

## Phase 4: The skill

**Files:**
- Create `skills/plab-project-pulse/SKILL.md`, `HISTORY.md`, `references/workflow.md`, `references/carry-forward.md`, `references/coverage-statement.md`, `references/settings-example.md`. The digest and scout formats live in `references/pulse-schema.md` beside the other contracts, instead of in two separate JSON schema files, so one file holds every format the scripts and agents exchange
- Create `skills/plab-project-pulse/scripts/test-workflow-reference.py`
- Create `evals/project-pulse-manual-no-fire/`

**Fulfills:** AC-1, AC-16, AC-19

**Verification:** `python skills/plab-project-pulse/scripts/test-workflow-reference.py` exits 0.

---

## Phase 5: Registration and CI

**Files:** `library.json` and the regenerated manifests, `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/skills/plab-project-pulse/README.md`, `docs/status-skills.md`, `evals/README.md`, `.github/workflows/gate.yml`, `scripts/gen-release-index.py`, `docs/internal/release-plans/README.md`, the regenerated `INDEX.md`.

**Verification:** every repository gate exits 0, quoted.

---

## Phase 6: Live runs

**Goal:** a `--quick` run on the maintainer's tree makes no model call and passes the checker; a `--week` run follows on the owner's next audit day.

**Fulfills:** AC-25, AC-26

**Verification:** the checker's output, quoted.

---

## CI and Documentation Coverage

**CI.** `.github/workflows/gate.yml` gains steps in the existing job: `pulse-check.py --self-test` and the discovery, facts, build and workflow-reference tests.

**Documentation.** `CHANGELOG.md` under Unreleased, `HISTORY.md`, `README.md`, `AGENTS.md`, `docs/status-skills.md`, `docs/skills/plab-project-pulse/README.md`.

## Rollback

Delete `skills/plab-project-pulse/`, `evals/project-pulse-manual-no-fire/`, `docs/skills/plab-project-pulse/` and this effort folder. Remove the component from `library.json`, regenerate the manifests, and revert the documentation, CI and series-legend additions. The owner's pulse output and state file live outside the plugin and are untouched.
