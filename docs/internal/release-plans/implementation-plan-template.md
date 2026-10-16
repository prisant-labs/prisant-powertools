# Implementation plan template

The shape every `implementation-plan.md` in this tree shares, written down so it does not have to be re-derived from the exemplars each time.

**Where this came from.** Not from a style preference. Three sections appear in all twenty implementation plans currently tracked here, in the same order: `Completion Status`, `CI and Documentation Coverage`, and `Rollback`, with numbered phases between the first and the second. Everything below is that observed spine plus the phase-internal structure those twenty also share.

**What this is not.** It is not a skill and it does not generate anything. `/plab-spec` writes the spec that this plan implements, and `/plab-release-plan` gates the release that ships it. This stage is a template because the exemplars were written with no plan-authoring skill involved and passed every hygiene gate regardless, so machinery here would be solving a problem this repository does not have.

**The one rule that matters most.** A plan never introduces an acceptance criterion. Criteria live in the spec, where they are contract and where the maintainer promoted them deliberately. If executing a plan reveals a missing criterion, the spec is amended and its `ac-count` and Revisions table updated, and only then does the plan reference it. A plan that invents its own criteria is grading its own homework.

---

## Frontmatter

Fenced here so this template is not itself validated as a document. Copy the block without the fences into the real plan. **The authoritative field list is `docs/internal/schemas/implementation-plan.schema.json`**, because that is what `scripts/frontmatter-check.py` validates against and therefore what CI enforces. `skills/plab-spec/references/frontmatter-schema.md` is the human-readable companion and explains what each field means, but where the two ever disagree the schema wins.

```yaml
id: X-NN                       # matches the effort folder name and the sibling spec's id
title: "Implementation plan: <what this builds>"
type: implementation-plan
status: draft                  # draft | in-progress | complete
created: YYYY-MM-DD
updated: YYYY-MM-DD
linked-spec: spec.md           # resolved relative to this file, then to the repo root
linked-release: docs/internal/release-plans/plan_NN_<slug>/plan.md
ac-coverage: partial           # partial | complete
phase-count: N                 # must equal the number of Phase sections below
```

`doc-lifecycle-check.py` enforces that the folder name, this file's `id`, and the sibling `spec.md`'s `id` all agree, and that `linked-spec` and `linked-release` resolve to real files. Run it before opening the pull request rather than discovering it in CI.

---

## Body

### Header

A one-line note for whoever executes the plan, then the goal. The exemplars open with a note that steps use checkbox syntax and phases run in order, followed by a `**Goal:**` paragraph stating what the finished work does, in the present tense, from outside.

### Completion Status

The table that makes the plan auditable. One row per phase, and the `Fulfills AC` column is the join back to the spec.

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | <short goal, matching the Phase 1 heading> | AC-1, AC-3 | agent | Not started |
| P2 | <short goal> | AC-2 | agent | Not started |
| P3 | <short goal> | N/A (documentation) | agent | Not started |

Every acceptance criterion in the spec must appear in at least one row, or `ac-coverage` is `partial` and the plan says which criteria are deliberately out of scope and why. Phases that fulfill no criterion, typically version bumps and HISTORY entries, carry `N/A` with the reason in parentheses rather than being left blank.

### Phase sections

One `## Phase N: <goal>` per row above, in order, each with the same five parts.

**Goal:** One or two sentences on what is true after this phase that was not true before. Written as an outcome, not as a list of edits.

**Files:** The exact paths this phase creates, modifies or deletes, each labelled with which. A phase touching files not listed here has grown beyond its plan.

**Fulfills:** The criteria from the Completion Status row, repeated so the phase is readable alone.

**Steps:** Numbered checkbox items. This is where the exemplars are strongest and where a thin plan fails: **each step carries the exact text being changed, before and after, not a description of the change.** A step reading "update the intro sentence" is a wish; a step quoting the sentence as it stands and as it should read is executable by an agent that has never seen the file. Where a step depends on line numbers, say so and instruct the executor to re-verify them first, because a sibling effort landing in between will have moved them.

**Verification:** One command, and what its output must show. Not "confirm it works" but the command, run against the change, with the expected result stated precisely enough that a wrong result is unambiguous. Where the phase's product is a detector, verification includes proving the canary fails when the rule it guards is removed, per the discipline rule in `AGENTS.md` that a gate which cannot fail is not a gate.

End each phase with a `---` rule.

### CI and Documentation Coverage

Two things, in this order.

**CI.** What changes in `.github/workflows/gate.yml`, or an explicit statement that nothing does, with the reason. The exemplars treat "no CI change" as a claim requiring justification rather than a default, because a check that only ever runs locally is one forgetting away from not running at all.

**Documentation.** Every human-facing file this effort obliges someone to update: `CHANGELOG.md`, the skill's `HISTORY.md`, the root `README.md`, any usage README, `AGENTS.md`. The drift check compares skill content against these, so an omission here becomes a gate failure later.

### Rollback

How to undo the whole effort, concretely: the files to delete, the exact prior wording to restore, and whether any other effort has come to depend on this one in the meantime. State explicitly when there is no schema change and no data migration to unwind, and name any partial-rollback hazard where reverting one phase without another would leave the tree inconsistent.

A rollback section that says "revert the commit" has not been written. The reason the exemplars spell it out is that by the time a rollback is wanted, the commit is rarely the unit anyone still has.

---

## Before opening the pull request

- [ ] `phase-count` equals the number of `## Phase` sections
- [ ] Every acceptance criterion in the sibling spec appears in the Completion Status table, or `ac-coverage: partial` names the exclusions and why
- [ ] No acceptance criterion appears here that is not in the spec
- [ ] `python scripts/frontmatter-check.py` exits 0
- [ ] `python scripts/doc-lifecycle-check.py` exits 0
- [ ] `python scripts/gen-release-index.py --check` exits 0, or the index has been regenerated
- [ ] `python scripts/check-dashes.py` exits 0
- [ ] If the effort changed any skill: its `metadata.version` and `updated` are bumped, `library.json` matches, a `HISTORY.md` entry exists for that exact version, the usage README's `**Version:**` line matches, and the manifests have been regenerated. This is what the bidirectional drift check compares, and it is the gate most likely to bite an executor who changed skill content without the bookkeeping.
