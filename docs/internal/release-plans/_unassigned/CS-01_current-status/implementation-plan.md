---
id: CS-01
title: "Implementation plan: plab-current-status"
type: implementation-plan
status: in-progress
created: 2026-10-28
updated: 2026-10-28
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 6
---

# Implementation plan: plab-current-status

Steps use checkbox syntax and phases run in order. A phase is done when every step is ticked and its Verification command has been run and its output quoted.

**Goal:** `/plab-current-status` gathers a repository's facts in one script call, reads only the documents those facts name, and writes one dated, ranked status snapshot to `_local/_status/YYYY-MM-DD_<model>_<byline>.md`, which a self-testing checker then passes. It works in any repository, degrading by level and naming each missing source.

**Spec:** `spec.md`

**Target version:** `plab-current-status` 1.0.0, a new skill, and `plab-resolve-open-items` 1.2.0 for the new `--answered-since` argument.

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) in any file this plan touches. One paragraph per line.
- Both new scripts are stdlib-only Python and follow the repository's exit contract: 0 clean, 1 a rule failed, 2 broken. Exit 2 is never read as clean.
- `gather-backlog.py` without `--answered-since` must produce byte-identical output to 1.1.0.
- The facts script writes no file in the working tree.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | The backlog sweep can return recent answers and unrecognised statuses | AC-4, AC-11 (part) | agent | Not started |
| P2 | The facts script returns every fact in one call, with its level and gaps | AC-2, AC-3, AC-11 (part) | agent | Not started |
| P3 | The checker enforces the file's shape and proves every rule can fail | AC-5 to AC-10, AC-11 (part) | agent | Not started |
| P4 | The skill, its reference, its history and its eval case exist | AC-1 | agent | Not started |
| P5 | The plugin registers the skill and CI runs its checks | AC-11 (CI) | agent | Not started |
| P6 | A live run on this repository passes the checker | AC-12 | agent | Not started |

---

## Phase 1: The backlog sweep can return recent answers and unrecognised statuses

**Goal:** `gather-backlog.py --answered-since YYYY-MM-DD` adds answered items updated on or after that date and every out-of-vocabulary item, each with a `kind`. Without the argument, nothing changes.

**Files:**
- Modify `skills/plab-resolve-open-items/scripts/gather-backlog.py`
- Modify `skills/plab-resolve-open-items/scripts/test-gather-backlog.py`
- Modify `skills/plab-resolve-open-items/SKILL.md` (version only), `skills/plab-resolve-open-items/HISTORY.md`

**Fulfills:** AC-4, AC-11 (part)

**Steps:**
- [ ] Add `ANSWERED_STATUSES = {"Decided", "Provisional", "Deferred", "Canceled", "Superseded"}` beside `PENDING_STATUSES`.
- [ ] Thread an optional `answered_since` date through `gather()` into `gather_decisions_items()`. With it unset, the row filter and the item dicts are exactly as before. With it set, every item gains `kind`; answered rows are kept when their `Updated` date parses and is on or after the date; rows in neither set are kept as `unrecognised`.
- [ ] Add the argument to `main()`.
- [ ] Add test cases: default output identical to a run with the argument unset, the answered-date boundary, and the unrecognised row.
- [ ] Bump the skill to 1.2.0 and add its HISTORY row.

**Verification:** `python skills/plab-resolve-open-items/scripts/test-gather-backlog.py` exits 0. With the date comparison removed, it exits non-zero and names the boundary case.

---

## Phase 2: The facts script returns every fact in one call

**Goal:** `derive-status-facts.py --repo <path> --json` returns the facts of the spec's Requirement 2, the level and the gaps, and writes nothing in the working tree.

**Files:**
- Create `skills/plab-current-status/scripts/derive-status-facts.py`
- Create `skills/plab-current-status/scripts/test-derive-status-facts.py`

**Fulfills:** AC-2, AC-3, AC-11 (part)

**Steps:**
- [ ] Git facts by subprocess: branch, head, porcelain status, `git fetch --no-prune origin --tags` with a timeout (a failure is a gap), ahead and behind against the upstream, latest tag and its date, commits since the tag and since the previous snapshot.
- [ ] Pull requests through `gh pr list` when `gh` is on the path and authenticated; otherwise a gap.
- [ ] Session logs by the newest-wins rule, plus every log dated on or after the previous snapshot.
- [ ] The previous snapshot: the newest file in `_local/_status/` matching the snapshot pattern.
- [ ] The decisions sweep by subprocess: `gather-backlog.py --repo <path> --json --answered-since <window start>`. Its exit 2 is this script's exit 2.
- [ ] The level and the gaps, and whether `_local/_status/` is ignored by git.
- [ ] Tests: three fixtures for the three levels, a non-repository for exit 2, a hash of the fixture before and after, and `gh` hidden from the path.

**Verification:** `python skills/plab-current-status/scripts/test-derive-status-facts.py` exits 0. With the level rule forced to `git-only`, it fails and names the level case.

---

## Phase 3: The checker enforces the file's shape

**Goal:** `status-check.py <file> [--facts <json>]` enforces the spec's Requirements 6 and 8 to 13, and `--self-test` proves each rule fails on a mutated copy of the committed sample.

**Files:**
- Create `skills/plab-current-status/scripts/status-check.py`
- Create `skills/plab-current-status/examples/sample-status/2026-10-28_opus-5-5_billing-retry-shipped-export-next.md` (not under a `_local/` folder, which `.gitignore` ignores at every depth; the self-test checks it under the logical path `_local/_status/<name>`)
- Create `skills/plab-current-status/examples/sample-status/facts.json`

**Fulfills:** AC-5 to AC-10, AC-11 (part)

**Steps:**
- [ ] One function per rule: path and filename, frontmatter fields and integer counts, sections present and in order, numbered items with `Why here:`, counts matching the numbered items up to ten, backticked paths in decision items, the previous-snapshot statement, and gaps covered.
- [ ] `--self-test`: run every rule against the sample (all clean), then against one mutation per rule (each must fail). Any rule that does not fail its mutation exits 2.
- [ ] Every run of the checker runs the self-test first, so a checker that cannot fail never reports clean.

**Verification:** `python skills/plab-current-status/scripts/status-check.py --self-test` exits 0, and `status-check.py <sample> --facts <sample facts>` exits 0. Disabling one rule makes the self-test exit 2.

---

## Phase 4: The skill exists

**Goal:** `skills/plab-current-status/SKILL.md` runs the workflow: facts, reading, ranking, writing, checking. It is manual-only.

**Files:**
- Create `skills/plab-current-status/SKILL.md`, `skills/plab-current-status/HISTORY.md`, `skills/plab-current-status/references/status-format.md`
- Create `evals/current-status-manual-no-fire/prompt.md`, `evals/current-status-manual-no-fire/graders/skill-not-fired.md`

**Fulfills:** AC-1

**Steps:**
- [ ] `SKILL.md` frontmatter with `disable-model-invocation: true` and a description of at most 600 characters.
- [ ] The workflow: run the facts script; on exit 2 report and stop; ask before writing when `_local/_status/` is not ignored; read the newest log and logs since the previous snapshot, and the home sections of pending items; rank; write; run the checker with `--facts`; reply with the path and The Answer.
- [ ] `references/status-format.md` holds the file template, the ranking rules and the cap.
- [ ] The eval case asks a status question and asserts the skill is not invoked.

**Verification:** `node <agent-skills-toolkit>/scripts/check.mjs .` reports no new failure for the skill.

---

## Phase 5: The plugin registers the skill and CI runs its checks

**Goal:** the skill ships with the plugin and its scripts gate every pull request.

**Files:**
- Modify `library.json`, then regenerate `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`
- Modify `AGENTS.md`, `README.md`, `CHANGELOG.md`, `.github/workflows/gate.yml`

**Fulfills:** AC-11 (CI)

**Steps:**
- [ ] Add the component to `library.json` and regenerate the manifests.
- [ ] `AGENTS.md`: ten skills become eleven, three manual-only become four, and a skill entry.
- [ ] `README.md` and `CHANGELOG.md` under Unreleased.
- [ ] `gate.yml`: the checker against the sample, and both test scripts, in the existing job so branch protection gates them.

**Verification:** every gate in the Build and validate section of `AGENTS.md` passes locally.

---

## Phase 6: A live run passes the checker

**Goal:** the skill, run from this checkout through a junction, writes a snapshot of this repository that the checker passes.

**Files:** none tracked. The run writes `_local/_status/YYYY-MM-DD_opus-5-5_<byline>.md`.

**Fulfills:** AC-12

**Steps:**
- [ ] Run the workflow on this repository.
- [ ] Run `status-check.py --facts` on the result.

**Verification:** the checker's output, quoted.

---

## CI and Documentation Coverage

**CI.** `.github/workflows/gate.yml` gains three steps in the existing job: `status-check.py` against the committed sample, `test-derive-status-facts.py`, and `test-gather-backlog.py` if it is not already run. They join the existing job because branch protection requires checks by job name.

**Documentation.** `CHANGELOG.md` under Unreleased, both skills' `HISTORY.md`, the root `README.md`, and `AGENTS.md`.

## Rollback

Delete `skills/plab-current-status/`, `evals/current-status-manual-no-fire/` and this effort folder. Remove the component from `library.json` and regenerate the manifests. Restore `AGENTS.md`'s "Ten" and "Three of the ten", and remove the README, CHANGELOG and `gate.yml` additions. `gather-backlog.py`'s new argument may stay, because without it the output is unchanged; to remove it, revert Phase 1 and the 1.2.0 HISTORY row together. There is no schema change and no data migration. The snapshots under `_local/_status/` are local and untracked.
