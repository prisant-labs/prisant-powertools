---
id: SH-01
title: "plab-ship: document, verify, merge and optionally release finished branches"
type: spec
status: committed
created: 2026-11-06
updated: 2026-11-06
linked-effort: "the maintainer's request of 2026-11-05 in session to turn a pasted close-out prompt into a skill"
linked-plan: null
linked-release: null
ac-count: 15
source-count: 7
requires-human-review: true
target-release: null
priority: P2
---

# Spec: plab-ship, documenting, verifying, merging and optionally releasing finished branches

## Task Summary

**Status:** committed. Built on `feat/plab-ship`; AC-15 waits on the first run in another repository
**Last updated:** 2026-11-06 by claude (Opus 5.5), writing and building under the maintainer's instruction to deliver the skill
**Linked plan:** none. The spec and the build landed together, under the instruction to deliver
**Open questions:** D1 and D2 (see Open Questions / Decisions). Neither blocks the skill, which fails safe until they are settled
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [x] AC-1: The skill is manual-only in both harnesses and does not fire on the maintainer's own close-out prompt
- [x] AC-2: No machine path appears in the skill, and the skill names the merge rule instead
- [x] AC-3: A missing merge rule or check means no merge
- [x] AC-4: `--release` takes no number and no size
- [x] AC-5: The model decides the version, and a major version does not stop to ask
- [x] AC-6: Only a repository with no version tag stops to ask about a release
- [x] AC-7: The latest version ignores backup tags and floating major tags, and sorts by number
- [x] AC-8: The screen runs before the merge and never prints a value
- [x] AC-9: The facts write nothing in the working tree and name every gap
- [x] AC-10: All twelve documentation cells are required, each with a file or a reason
- [x] AC-11: The documents list is compared with the real commits, in both directions
- [x] AC-12: Every new flag and skill must appear in a human-layer file
- [x] AC-13: The run record is written before the first merge and appended as merges land
- [x] AC-14: The closing report lists the documents updated, per layer
- [ ] AC-15: A first run in a repository other than this one produces a record the checker passes

### Currently In Progress

Built on 2026-11-06. Evidence: AC-2, AC-4 and AC-7 to AC-9 by `test-ship-scripts.py`; AC-10 to AC-12 by `ship-check.py --self-test`, which proves ten rules on mutations; AC-1 by the eval case `ship-manual-no-fire` and `scripts/codex-invocation-check.py`.

---

## Purpose

The maintainer closes out finished work by pasting a long prompt: document each branch in three layers, verify it, merge at high confidence, release and clean up, and report. A measurement of 8 sessions across 6 repositories between 2026-10-28 and 2026-11-05 showed what the prompt alone did not secure [S1]. A secret scanner ran in 0 of 8 sessions, and a `_local/` check in 1 of 8. `git branch -D` ran 16 times against 7 for `-d`. Two sessions ran about 40 hours through 3 compactions under one approval.

The maintainer also ruled that high-quality, multi-depth human, technical and agentic documentation is the point of the skill, and that the goal is best in class rather than average [S2]. A prompt can ask for that. Only a standard with a gate can show whether it happened.

## Scope

### In Scope

1. A new skill, `skills/plab-ship/`, manual-only, with `SKILL.md`, `HISTORY.md`, a documentation standard and a record format.
2. Stdlib-only scripts: `derive-ship-facts.py`, `screen-branch.py`, `ship-check.py` with a self-test against a committed sample, and `test-ship-scripts.py`.
3. The plugin's registration: `library.json`, the regenerated manifests, `AGENTS.md`, the root `README.md`, `docs/status-skills.md`, a usage README, `CHANGELOG.md`, an eval case and the CI steps.

### Non-Goals

1. **Changing the merge rule or the merge check.** Both live in the maintainer's private configuration, and an agent does not widen its own permissions. See D1 and D2.
2. **A full secret scanner.** The screen matches common credential shapes. No scanner is installed, and adopting one must pass the maintainer's dependency maturity check first.
3. **Proving documentation quality mechanically.** The gate proves presence. The cold reader tests quality, and no baseline for it exists yet.
4. **Working across repositories.** One run covers one repository.
5. **A session log.** That is `plab-wrap-session`.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | The only reader | Types `/plab-ship`, optionally with branches and `--release`, and reads the report |
| Running agent (Claude Code or Codex) | Executes the skill | Runs the scripts, writes the documents and the record, and merges what the check permits |
| Cold reader (a Sonnet subagent) | Tests the documents | Reads only the human-layer documents and follows the quick start |

## Requirements

1. The skill carries `disable-model-invocation: true` and `policy.allow_implicit_invocation: false`, because it merges and publishes [S3].
2. The skill holds no machine path. It names the solo-repo merge rule, which holds the command in both harnesses, so the path stays in one place [S2, S4].
3. Every merge requires `VERDICT: merge`. When the rule or the check is missing, the skill does not merge, because a missing check is never a pass [S4].
4. `--release` approves one release for one run. It takes no number and no size [S2].
5. The model decides patch, minor or major by reading what changed since the latest version tag. A major version does not stop to ask, and the version and reason are stated before tagging [S2].
6. A repository below 1.0.0 raises the minor number for a breaking change, and moves to 1.0.0 only if its own documents say its interface is stable. [model-inference: the convention, and this repository's own v0.9.0 rename, which raised the minor number]
7. A repository with no version tag stops to ask, because a first release also decides whether the repository versions at all. [model-inference]
8. The facts read the latest version by listing version-shaped tags and sorting them by number, because `git describe` returns the merge check's backup tags [S5].
9. The screen runs before the merge, and prints file and pattern names only [S1].
10. Each merged branch accounts for twelve documentation cells, each naming a file updated, a file already correct, or a reason [S2].
11. A feature or behaviour change gets a cold reader on Sonnet, and its gaps are fixed before the merge [S2, S6].
12. The run record lives at `_local/_shipped/YYYY-MM-DD_<byline>.md`, outside the session-log folder, is created before the first merge, and is appended as each merge lands [S1, S7].
13. The closing report lists the documents updated for each branch, per layer [S2].
14. `ship-check.py` exits 0, 1 or 2 on the repository's three-state contract, and proves every rule can fail before reporting clean [S3].

## Acceptance Criteria

**AC-1:** `SKILL.md` carries `disable-model-invocation: true`, `agents/openai.yaml` carries `policy.allow_implicit_invocation: false`, and the eval case `ship-manual-no-fire`, whose prompt is the maintainer's own close-out prompt, asserts that the skill is not invoked. [S1, S3]

**AC-2:** `test-ship-scripts.py` fails if `SKILL.md` or a reference holds a machine path, or if `SKILL.md` does not name the solo-repo merge rule. [S2, S4]

**AC-3:** `SKILL.md` instructs that a missing rule or check means no merge, and `test-ship-scripts.py` fails if the instruction is removed. [S4]

**AC-4:** `test-ship-scripts.py` fails unless the `argument-hint` reads `[<branch|PR> ...] [--release] [--no-fetch]`. [S2]

**AC-5:** `SKILL.md` gives the rule for patch, minor and major, and states that a major version does not stop to ask. [S2]

**AC-6:** `SKILL.md` names a repository with no version tag as the only release question it asks. [model-inference]

**AC-7:** Given a fixture holding `v0.9.0`, `v0.10.0`, a `pre-merge/` tag and `v1`, the facts report `v0.10.0` as the latest version and count two tags as ignored. [S5]

**AC-8:** Given fixtures holding a token, an assigned secret, a `.env` file and a tracked `_local/` file, `screen-branch.py` exits 1 and names each, its output never contains a matched value, and an unreadable range exits 2. [S1]

**AC-9:** Running the facts leaves `git status --porcelain` and a hash of every file unchanged, an absent `gh` and an absent remote are named gaps, and a folder that is not a repository exits 2. [S3]

**AC-10:** `ship-check.py` rejects a record with a missing cell, an unknown state, an `updated` or `correct` cell with no path, or an `n/a` cell with a reason under three words. [S2]

**AC-11:** With `--repo`, `ship-check.py` rejects a record listing a file as updated that did not change in the merge, and one omitting a document that did. [S2]

**AC-12:** With `--repo`, `ship-check.py` rejects a merge that adds a flag or a skill no Human-layer file in the record mentions. Its self-test proves this on a real commit with the mention removed. [S2]

**AC-13:** `SKILL.md` instructs that the record is created before any merge and appended as each merge lands, and `ship-check.py` rejects a Merged row without a commit or an undo point. [S1, S7]

**AC-14:** `SKILL.md` step 9 requires a documents table per merged branch in the closing report. [S2]

**AC-15:** Running `/plab-ship` on a repository other than this one, once this version is installed, writes one record that `ship-check.py --repo` passes. [model-inference: the live run is this spec's own test design]

## Behavior / Examples

### Example 1: A finished feature, no release

The maintainer types `/plab-ship feat/parser`. The skill documents the branch, a cold reader finds that the guide never says what the default is, and the guide is fixed. Tests pass, the screen is clean, CI is green and the merge check says `VERDICT: merge`. The skill merges, appends the row, deletes the branch, and reports the documents per layer. No version is created.

### Example 2: A breaking change with a release

The maintainer types `/plab-ship feat/rename --release` in a repository at v2.3.1. The diff renames a command. The skill states "Releasing v3.0.0, because the command `old` no longer exists", without stopping to ask, and releases through the repository's own path.

### Example 3: No merge rule

The maintainer runs the skill on a machine whose instructions hold no merge rule. The skill documents and verifies the branch, leaves it open, and reports that no rule or check was available.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Cost | Repository facts are one tool call | [S3] |
| Portability | The scripts are stdlib-only Python, and the skill works in Claude Code and Codex | [S3] |
| Safety | Secret values are never printed, and history is never rewritten | [S4] |
| Context budget | The description is at most 600 characters | [S3] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-11-06 | claude | added | Initial spec, written and built under the maintainer's instruction to deliver the skill. |

## Sources & Evidence

- **[S1]** A measurement of the 8 sessions in which the prompt ran, from the session transcripts, on 2026-11-05. The counts come from regular expressions over each whole session, so they are medium confidence. Maintainer-local. Class A.
- **[S2]** The maintainer's rulings in session on 2026-11-05 and 2026-11-06: the home in this plugin, a flag with no number, the name, the documentation standard, a documents list in the output, no absolute paths, and the model deciding minor and major. Class A.
- **[S3]** `AGENTS.md`, the design frame, the manual-only rulings and the three-state gate contract, and `skills/plab-current-status/`, the pattern this skill follows. Class A.
- **[S4]** The maintainer's solo-repo merge rule and `tools/merge-check.py`. Maintainer-local, outside this repository. Class A.
- **[S5]** A measurement in `product-on-purpose/critique-skills` on 2026-11-05: `git describe` returned a `pre-merge/` tag where the true answer was `v0.2.0`, so a check saw 8 changed files against 1,149. Class A.
- **[S6]** The 2026-10-27 discussion that produced the three-layer documentation taxonomy, and the maintainer's model-routing rule, which routes a rubric-style reader to Sonnet. Maintainer-local. Class A.
- **[S7]** `docs/internal/release-plans/_unassigned/W-05_wrap-hygiene-order/spec.md`, which moved the wrap to writing its log first. Class A.

### Unverified Claims

- Requirements 6 and 7 are model inference, marked above.
- Whether the credential patterns are enough. They were tested on fixtures, not against a corpus of real leaks.
- Whether the cold reader finds gaps a maintainer would care about. It was run once by hand on this skill's own usage README, and no baseline exists.

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | The sentence in the merge rule that lets `--release` answer the merge check's `release` ask | Pending | Open | 2026-11-06 |
| D2 | Where the merge check keeps its backups | Pending | Open | 2026-11-06 |

### D1: The sentence in the merge rule (Open)

**Summary.** The merge rule stops on any ask and requires the maintainer's yes for tags and releases, so `--release` cannot merge a release pull request or tag until the rule says it may.

**Why it is not built.** The rule lives in the maintainer's private configuration and sets what an agent may do unasked, so an agent should not widen it for itself. The skill fails safe in the meantime: it stops at the ask and names it.

**Proposed text.** "Running `/plab-ship --release` is the maintainer's yes for that run's tag and release. It answers a `release` ask from the merge check and no other check."

### D2: Where the merge check keeps its backups (Open)

**Summary.** The merge check's backup tags mislead every script that asks for the latest tag. Seven scripts in this plugin read tags, and only the `git describe` form is confirmed to give a wrong answer.

**Recommendation.** Store backups under `refs/backups/pre-merge/` with `git update-ref`. A test in a throwaway repository on 2026-11-05 confirmed that `git describe` then returns the version, that the reference restores as a branch, and that a clone does not carry it. The cost is one change in `merge-check.py`, moving 46 tags in 9 repositories, and a change to the rule's text.

**Why it is not built.** It deletes and rewrites tags across repositories, so it needs the maintainer's explicit yes. This skill is unaffected either way, because its facts script ignores backup tags.
