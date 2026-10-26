---
id: H-06
title: Let a release plan carry no version until it ships
type: spec
status: draft
created: 2026-10-26
updated: 2026-10-26
linked-effort: "the plan half of decision 21 in the maintainer's private decision register, ruled on 2026-10-06 and deferred to its own spec"
linked-plan: null
linked-release: null
ac-count: 8
source-count: 12
requires-human-review: true
target-release: null
priority: P3
---

# Spec: Let a release plan carry no version until it ships

## Task Summary

**Status:** draft
**Last updated:** 2026-10-26 by claude (Opus 5.5), written under the maintainer's go-ahead of 2026-10-26
**Linked plan:** not yet planned
**Open questions:** 2 (see Open Questions / Decisions)
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: The release-plan schema accepts `target-version: null` and still rejects a malformed version
- [ ] AC-2: The cross-release index renders a release plan with no version
- [ ] AC-3: The lifecycle check proves that plans with no version neither collide nor count as tagged
- [ ] AC-4: `plab-release-plan` can create, find and fill a release plan that has no version
- [ ] AC-5: The skill's two references document the version as optional until the release ships
- [ ] AC-6: Release plans 05 to 08 carry no version, and the lifecycle check's baseline is empty
- [ ] AC-7: The user and agent documents describe the optional version
- [ ] AC-8: `plab-release-plan` carries a version bump and a `HISTORY.md` row, and the CHANGELOG records the change

### Currently In Progress

None. This spec was written on 2026-10-26; the build waits for its own go-ahead.

---

## Purpose

On 2026-10-06 the maintainer ruled that a release gets its version number only when it ships, so planned work carries no number in advance [S1]. That ruling has two halves. The spec half shipped the same day: draft specs moved to `_unassigned/` with `target-release: null` [S1, S2]. The plan half did not, because a release plan's `target-version` is required to be a semantic version [S3].

The cost is visible. Release plans 05 to 08 still carry v0.6.0 to v0.9.0, and all four numbers have since shipped as other releases [S2]. The lifecycle check now carries a dated baseline so that those four stale numbers do not fail CI [S4]. `/plab-release-plan --create v0.7.0` refuses while plan 06 holds that number [S2].

This spec defines the plan half: a release plan may carry `target-version: null` until it ships, and every tool that reads the field accepts that.

## Scope

### In Scope

1. Make `target-version` nullable in `docs/internal/schemas/release-plan.schema.json`, keeping the semantic-version pattern for a value that is present.
2. Make `scripts/gen-release-index.py` render a release plan with no version, and prove it in that script's self-test.
3. Prove in `scripts/doc-lifecycle-check.py`'s self-test that invariants 2 and 10 already skip a release plan with no version, and empty invariant 10's dated baseline once plans 05 to 08 drop their numbers.
4. Add a release plan with `target-version: null` to `scripts/frontmatter-check.py`'s self-test as an anti-canary.
5. Change `skills/plab-release-plan/SKILL.md`, `skills/plab-release-plan/references/frontmatter-schema.md` and `skills/plab-release-plan/references/plan-template.md`, so that the skill can create, find and fill a release plan with no version.
6. Set `target-version: null` in release plans 05 to 08.
7. Update the user, agent and release documents that describe the version argument.

### Non-Goals

1. **A `--ship` subcommand, or any step that assigns the version at ship time.** `--ship` stays deferred until the maintainer reviews the wider release plan [S10]. The version is still written by hand when the release is cut.
2. **The wider direction of `plab-release-plan`.** Its manual-only flag is provisional pending that review, and this effort does not change it [S9, S10].
3. **Renumbering, deleting or merging release plans.** Plans 05 to 08 keep their folders, sequences and open items. Whether to delete them is D1 below.
4. **Spec frontmatter.** A spec's `target-release` is already nullable, and the spec half of the ruling has shipped [S1].

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Plans releases and cuts tags | Creates a release plan without a version, and writes the version when the release ships |
| Running agent | Runs `/plab-release-plan` on the maintainer's command | Addresses a release plan with no version by its sequence or folder name |
| CI | Runs the document gates on every pull request | Accepts a release plan with no version, and still rejects a malformed one |

## Requirements

1. `release-plan.schema.json` gives `target-version` the type `["string", "null"]` and keeps the pattern `^v\d+\.\d+\.\d+$`, which applies only to a string. The field stays required, so an absent field is still a finding [S3, model-inference].
2. `gen-release-index.py` reads a null `target-version` without exiting 2, and renders `-` in the Target Version column, as it already does for the unassigned group [S5].
3. `doc-lifecycle-check.py`'s invariants 2 and 10 already skip a release plan whose `target-version` is null or empty [S4]. Its self-test proves both skips, so that a later edit cannot remove them unnoticed.
4. Release plans 05 to 08 set `target-version: null`. Their four entries in `BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS` are then dead, and are removed. The baseline mechanism stays, and the self-test keeps proving it with its own injected baseline [S2, S4].
5. `frontmatter-check.py`'s self-test gains a valid release plan with `target-version: null` as an anti-canary. It also gains a canary with a malformed version, such as `0.7`, because none exists today for a release plan's version [S6].
6. In `plab-release-plan`, `--create` takes an optional version. Without one, it writes `target-version: null`. The refusal for a version another plan already claims applies only when a version is given [S7].
7. A version argument never matches a release plan whose `target-version` is null. Such a plan is addressed by its sequence or folder name, which `SKILL.md` already accepts for every subcommand [S7].
8. `--promote` into a release plan with no version writes `target-release: null` on each promoted spec, and still sets `linked-release` [S7, model-inference].
9. `skills/plab-release-plan/references/frontmatter-schema.md` and `skills/plab-release-plan/references/plan-template.md` show `target-version` as optional and null until the release ships. The documented title convention stops embedding a version, matching the existing "Release plan NN: <theme>" titles [S8].
10. The `argument-hint` and the command tables in `SKILL.md`, `docs/skills/plab-release-plan/README.md`, `docs/internal/release-plans/README.md` and `docs/status-skills.md` show the version as optional where a release may have none. `AGENTS.md`'s paragraph on `plab-release-plan` stops saying the skill was built only for release plans numbered in advance [S9, S12].
11. `plab-release-plan` bumps its own `metadata.version` and adds a `HISTORY.md` row. The CHANGELOG's `[Unreleased]` section gains a Changed entry [S11].

## Acceptance Criteria

**AC-1:** `python scripts/frontmatter-check.py` exits 0 on the repository, and its self-test passes a release plan with `target-version: null` and fails one with `target-version: 0.7`. Canary: with the schema's type reverted to `"string"`, the self-test fails and names the null anti-canary. [S3, S6]

**AC-2:** `python scripts/gen-release-index.py --check` exits 0 on the repository after AC-6, and `INDEX.md` shows `-` as the Target Version of release plans 05 to 08. The script's self-test includes a release plan with a null `target-version`. [S5]

**AC-3:** `python scripts/doc-lifecycle-check.py` passes a self-test case in which two release plans both carry `target-version: null` and raise no invariant 2 finding, and a case in which a pre-release plan with a null `target-version` raises no invariant 10 finding, whatever tags exist. [S4]

**AC-4:** `skills/plab-release-plan/SKILL.md` states that `--create` without a version writes `target-version: null`. It states that the duplicate-version refusal applies only to a given version, that a null plan is addressed by sequence or folder name, and that `--promote` into it writes `target-release: null`. Its `argument-hint` shows the version on `--create` as optional. [S7]

**AC-5:** Neither `skills/plab-release-plan/references/frontmatter-schema.md` nor `skills/plab-release-plan/references/plan-template.md` presents `target-version` as required. Each shows `null` as the value until the release ships. [S8]

**AC-6:** Release plans 05 to 08 carry `target-version: null`, and `BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS` has no entries. `python scripts/doc-lifecycle-check.py` exits 0 and prints no "known baselined violation" note. [S2, S4]

**AC-7:** `git grep -n -e "--create vX.Y.Z" -- docs/ AGENTS.md skills/plab-release-plan/SKILL.md ':!docs/internal/release-plans/*/*/**'` returns no line; it returns six today. Each of those command tables shows the version as optional instead, for example `--create [vX.Y.Z]`. `AGENTS.md`'s `plab-release-plan` paragraph no longer says the skill was built for release plans numbered in advance. [S9, S12, model-inference: the grep form is this spec's own test]

**AC-8:** `python scripts/version-parity-check.py` and `python scripts/skill-drift-check.py --strict` both exit 0 on the closing release pull request, and `CHANGELOG.md`'s release section for this effort has a Changed entry for the optional `target-version`. [S11]

## Behavior / Examples

### Example 1: Creating a release with no number

The maintainer runs `/plab-release-plan --create --theme "Wrap and continue"`. The skill derives sequence 09, creates that release plan from the theme, and writes `target-version: null` in it. A later `/plab-release-plan --promote --from _unassigned --to 09 C-02` moves the effort in, and writes `target-release: null` on its spec. When the release ships as, say, v0.10.0, the maintainer writes that number into the plan by hand.

### Example 2: The four stale plans

Before this effort, `doc-lifecycle-check.py` prints four notes saying plans 05 to 08 are known baselined violations. After it, the four plans carry no version, the baseline is empty, and the check prints no note.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Compatibility | A release plan that carries a semantic version stays valid and behaves exactly as before. | [S3, S7] |
| Safety | The field stays required, so a release plan that omits it entirely still fails the schema check. | [S3] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-10-26 | claude | added | Initial spec, written on the maintainer's go-ahead of 2026-10-26 for the plan half of decision 21, which the 2026-10-06 ruling deferred to its own spec. |

## Sources & Evidence

- **[S1]** The maintainer's ruling of 2026-10-06 on decision 21 in the private decision register: a release gets its version only when it ships. The spec half shipped in PR #19. The plan half was deferred to its own small spec, naming the schema, `gen-release-index.py`, the `frontmatter-check.py` fixture, `SKILL.md`, two references and a skill version bump. Maintainer-local, gitignored. Class A.
- **[S2]** `docs/internal/release-plans/plan_06_derived-facts/plan.md`, `plan_07_aggregation/plan.md` and `plan_08_escape-and-measure/plan.md`, each D3 and its 2026-10-16 update: the ruling recorded, the stale `target-version` values, and the `--create` refusal they cause. Release plan 05's D3 records the same ruling. Class A.
- **[S3]** `docs/internal/schemas/release-plan.schema.json`, where `target-version` is required and string-only. Class A.
- **[S4]** `scripts/doc-lifecycle-check.py`: `check_unique_release_field()` and `check_released_but_prerelease_release_plans()` skip a null or empty value, and `BASELINED_PRERELEASE_TAGGED_RELEASE_PLANS` holds plans 05 to 08. Class A.
- **[S5]** `scripts/gen-release-index.py`, `build_release()`, which calls `require_field()` on `target-version`, and the renderer, which already prints `-` for the unassigned group. Class A.
- **[S6]** `scripts/frontmatter-check.py`, its `VALID_RELEASE_PLAN` fixture and the schema validator's nullable-type support. Class A.
- **[S7]** `skills/plab-release-plan/SKILL.md`: the Input Contract, the rule for resolving a version argument to a folder, and the `--create` and `--promote` workflows. Class A.
- **[S8]** `skills/plab-release-plan/references/frontmatter-schema.md` and `skills/plab-release-plan/references/plan-template.md`. Class A.
- **[S9]** `AGENTS.md`, the paragraph on why `plab-release-plan` is manual-only. Class A.
- **[S10]** The maintainer's walk ruling of 2026-10-17 on `plab-release-plan`'s direction, recorded as provisional: manual-only now, with `--ship` deferred until the wider release plan is reviewed. Maintainer-local, gitignored. Class A.
- **[S11]** `scripts/skill-drift-check.py` and `scripts/version-parity-check.py`, which require a changed skill to bump its version and record it. Class A.
- **[S12]** `docs/skills/plab-release-plan/README.md`, `docs/internal/release-plans/README.md` and `docs/status-skills.md`, the command tables that show `--create vX.Y.Z`. Class A.

### Unverified Claims

- Requirement 1, that `target-version` should stay required and accept null, rather than become optional and absent. This is this spec's choice, made so that an omitted field stays visible, marked `[model-inference]`.
- Requirement 8, that a spec promoted into a plan with no version gets `target-release: null`. This follows from the ruling, but no source states it, marked `[model-inference]`.
- AC-7's grep form is this spec's own test design, marked `[model-inference]`.

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Whether to delete the four empty release plans instead of clearing their versions | (none) | Open | 2026-10-26 |
| D2 | Whether to fix the skill's `released` status, which the schema calls `complete` | (none) | Open | 2026-10-26 |

### D1: Whether to delete the four empty release plans instead of clearing their versions (Open)

**Summary.** Release plans 05 to 08 hold no efforts. This spec clears their versions. It could delete them instead.

**Context.** All four were emptied when their efforts moved to `_unassigned/` [S2]. Three of them still hold open items: release plan 06's D2 (a missing derive script), release plan 07's D1 (where the shared aggregation layer lives) and release plan 08's D1 (W-06, the log as a checkable contract).

**Desired outcome.** No release plan carries a number that has shipped as something else, and no open item loses its home.

**Options / approaches.**

* **Option A:** Clear the four versions and keep the plans, so their open items and history stay where they are.
* **Option B:** Delete the four plans, after moving their open items into the specs they concern.

**Recommendation.** Option A. Deleting them would need a new home for three open items, and that is a separate decision from making the version optional.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Whether to fix the skill's `released` status, which the schema calls `complete` (Open)

**Summary.** `plab-release-plan`'s own references name a release plan's final status `released`, but the repository's schema and its scripts call it `complete`.

**Context.** `skills/plab-release-plan/references/frontmatter-schema.md`, `skills/plab-release-plan/references/plan-template.md` and `skills/plab-release-plan/SKILL.md` all say `released`. `docs/internal/schemas/release-plan.schema.json` allows only `draft`, `in-progress` and `complete`, and `doc-lifecycle-check.py` treats `complete` as the terminal status [S3, S4, S8]. A maintainer who followed the skill and set `status: released` would fail the schema check in CI. This effort edits two of those three files anyway.

**Desired outcome.** The skill and the schema name the final status with the same word.

**Options / approaches.**

* **Option A:** Change the skill's three files to `complete` in this effort, because CI enforces the schema.
* **Option B:** Leave it for a separate fix, keeping this effort to the version field alone.

**Recommendation.** Option A. The fix is a word in files this effort already edits, and the schema is the side that CI enforces.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
