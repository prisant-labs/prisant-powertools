---
id: DS-03
title: "Docs refresh: find the documentation that is no longer true, and propose each fix"
type: spec
status: draft
created: 2026-11-24
updated: 2026-11-24
linked-effort: "the maintainer's request in session on 2026-11-21 for skills that create, expand, curate and update documentation, and his request on 2026-11-24 for their initial specs, approach and questions"
linked-plan: null
linked-release: null
linked-strategy-brief: docs/internal/ideas/2026-11-24_docs-skills-approach.md
ac-count: 10
source-count: 5
requires-human-review: true
spec-dependencies: [DS-01]
target-release: null
priority: P2
---

# Spec: docs refresh, finding documentation that is no longer true

## Task Summary

**Status:** draft. Nothing is built, and no implementation plan exists
**Last updated:** 2026-11-24 by claude (Opus 5.5), initial draft
**Linked plan:** not yet planned
**Open questions:** 2 (D1 and D2, see Open Questions / Decisions), plus DS-01 D1 (packaging), which this spec inherits
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: Every path a document cites that does not exist is reported
- [ ] AC-2: Every flag or skill name a document cites that the code does not define is reported
- [ ] AC-3: Every count a document states that disagrees with the repository is reported
- [ ] AC-4: A tracked document that cites a gitignored file is reported
- [ ] AC-5: A document that promises something about itself and does not deliver it is reported, marked as judged by a model
- [ ] AC-6: Every finding names its file and line, the claim, the evidence it is false, and a proposed fix
- [ ] AC-7: A finding a deterministic gate should have caught is reported as a gate gap, not only as a document fix
- [ ] AC-8: A default run covers the documents changed or cited since the latest version tag, and a full run covers every document
- [ ] AC-9: No document changes until the maintainer says yes, and accepted fixes land on one branch
- [ ] AC-10: The checker proves every rule can fail against a committed sample, and CI runs it

### Currently In Progress

None. The spec was written on 2026-11-24. It waits on DS-01's decisions; it is the last of the three modes in the recommended order.

---

## Purpose

The maintainer asked for skills that curate and update documentation, not only create it [S1]. No outside skill found on 2026-11-21 keeps documents current [S2], and in this repository a stale document is caught only when a wrap's hygiene sweep or an audit happens to touch it [S3]. The documentation standard says "a stale sentence does more harm than a missing one" [S4]. This spec defines a mode that finds what is no longer true across the repository, between releases, mostly with scripts.

## Scope

### In Scope

- Claims a script can check: cited paths, flags, skill names, stated counts, and citations of gitignored files from tracked files.
- Claims a model must judge, kept separate and marked: a file's promises about itself, and tense contradictions inside an unreleased section [S3].
- A proposed fix for every finding, and a report of gate gaps.

### Non-Goals

- Version parity between documents and manifests, which the deterministic gates own [S3].
- Finding missing documents. That is DS-01 (docs plan).
- Writing new pages. That is DS-02 (docs write).
- Prose style, spelling and grammar [S3].

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Accepts or rejects each fix | Invokes the refresh by name, between releases or before one |
| Facts script | Deterministic checker | Runs every mechanical check and reports findings with evidence |
| Judge agent | Model reading for what scripts cannot check | Reports self-promises and tense contradictions, each marked as judged |

## Requirements

### What is checked

1. A cited path that does not resolve is the most common stale claim, and a tracked file citing a gitignored one is "unresolvable by construction" [S3].
2. Commands, flags and names in documents are tested against the current tree [S3].
3. A file's promise about itself, such as "this list is generated" for a hand-maintained list, is among "the highest-yield staleness findings", because the file states its own contract [S3].
4. Counts stated in prose, such as the number of skills, are checked against the repository. [model-inference]

### How findings are made

5. Mechanical checks run as a script with no model, and model judgments are reported apart from them and marked, so a reader knows which findings are proven [S5].
6. If the refresh keeps finding drift a deterministic gate missed, the gate is fixed rather than the refresh widened [S3].

### Conduct

7. The refresh proposes and the maintainer disposes: nothing changes without a yes, and work lands on a branch through the merge check [S5].
8. The mode follows the checker pattern: a committed sample, a canary proven to fail, and a CI self-test [S5].

## Acceptance Criteria

AC-1: Given a document that cites `skills/plab-x/missing.md`, which does not exist, the refresh reports that file and line with the finding "path does not exist". [S3]

AC-2: Given a document that cites `--no-such-flag` for a skill whose scripts and `argument-hint` define no such flag, or names a `plab-` skill with no `skills/<name>/` folder, the refresh reports it. [S3]

AC-3: Given a document stating "Fifteen general-purpose agent skills" in a repository with sixteen `skills/*/SKILL.md` files, the refresh reports the count, the stated number and the real number. [model-inference]

AC-4: A tracked document that cites a path inside a gitignored folder is reported as unresolvable for anyone who clones the repository. [S3]

AC-5: A document that says its content is generated, or that changes will be recorded in it, and does not deliver that, is reported in a separate section marked as judged by a model, with the sentence quoted. [S3]

AC-6: Every finding carries the file, the line, the claim as written, the evidence that it is false, and a proposed replacement or deletion. [S4]

AC-7: A finding of a kind an existing gate is meant to catch, such as a version number or a dash, is reported under "gate gaps", naming the gate, in addition to the document fix. [S3]

AC-8: A run without options covers documents changed since the latest version-shaped tag, plus documents that cite a file changed since that tag; `--all` covers every document the documentation map names. [model-inference]

AC-9: After a run and before a yes, `git status --porcelain` shows no change except the refresh's own report; after a yes, the accepted fixes are applied on one branch other than the default branch. [S5]

AC-10: The checker's self-test runs in CI against a committed sample with one planted finding of each mechanical kind, and removing any one rule makes its canary fail. [S5]

## Behavior / Examples

### Example 1: a refresh before a release (AC-1, AC-3, AC-6)

A skill was renamed since the last tag. The refresh finds two documents still citing the old folder, reports each with its line and the new path as the proposed fix, and finds that `AGENTS.md`'s opening sentence states the old skill count. The maintainer accepts all three, and the fixes land on one branch, which `plab-ship` then carries.

### Example 2: a gate gap (AC-7)

The refresh finds a version number in a document that disagrees with `library.json`. Version parity belongs to `scripts/version-parity-check.py`, so the refresh reports the document fix and, under gate gaps, that the parity check does not read that document.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Determinism | Two runs on the same commit report the same mechanical findings | [S5] |
| Cost | The judge agent runs only on the documents in scope, with an explicit model | [S5] |

## Revisions

| Date | Author | Type | Description |
|---|---|---|---|
| 2026-11-24 | claude (Opus 5.5) | added | Initial draft created |

## Sources & Evidence

- **[S1]** The maintainer's request in session on 2026-11-21: "a couple skills for creating, expanding, curating, and updating docs" - private session transcript, summarized in [S2] - class A
- **[S2]** Approach and open questions for the docs skills, including the 2026-11-21 research finding that no outside skill handles maintenance - `docs/internal/ideas/2026-11-24_docs-skills-approach.md` - class A
- **[S3]** The audit's docs lens: staleness of substance, self-promises, citations that do not resolve, and the rule to fix gates rather than widen a lens - `skills/plab-audit/references/lenses/docs.md` - class A
- **[S4]** The documentation standard: "Update what the change made false" - `skills/plab-ship/references/documentation-standard.md` - class A
- **[S5]** The repository's engineering discipline, facts-script convention and branch protection - `AGENTS.md` - class A

### Unverified Claims

- "Counts stated in prose, such as the number of skills, are checked against the repository." - appears in Requirements and AC-3
- "A run without options covers documents changed since the latest version-shaped tag" - appears in AC-8, pending D1

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Default scope of a refresh | (none) | Open | (none) |
| D2 | Report only, or apply fixes | (none) | Open | (none) |

### D1: Default scope of a refresh (Open)

**Summary.** A refresh can cover what changed since the last release, or every document every time.

**Context.** A full run on this repository reads every specification, plan and reference file, which costs judge time for documents nothing has touched. A since-tag run can miss a document that went stale because something it does not cite changed.

**Desired outcome.** A routine refresh is cheap enough to run before every release, and a full refresh is available when wanted.

**Options / approaches.**

* **Option A:** documents changed or citing a changed file since the latest version tag by default; `--all` for everything.
* **Option B:** every document, every run.
* **Option C:** since the previous refresh, recorded in a state file.

**Recommendation.** Option A. The mechanical checks are cheap enough to run on everything, so the scope limit can apply to the judge agent only if the first runs show the since-tag scope missing findings.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Report only, or apply fixes (Open)

**Summary.** The refresh can stop at a report, or apply the fixes the maintainer accepts.

**Context.** Most mechanical fixes are one-line replacements with an exact proposed text, which a person should not have to retype. Judged findings, such as a self-promise, need a decision about what the document should say.

**Desired outcome.** Accepting a fix costs one word, and no fix is applied that the maintainer did not see.

**Options / approaches.**

* **Option A:** report with a proposed patch per finding; apply the accepted ones in one batch on a yes, on one branch.
* **Option B:** report only; the maintainer or DS-02 makes the changes.
* **Option C:** apply mechanical fixes automatically and report the judged ones.

**Recommendation.** Option A. It keeps every change visible and reviewable, and it does not leave the maintainer retyping fixes the run already worked out.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
