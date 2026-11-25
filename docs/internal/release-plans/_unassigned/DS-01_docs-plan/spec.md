---
id: DS-01
title: "Docs plan: a read-only map of a repository's documentation gaps against the twelve-cell standard and the Diátaxis kinds"
type: spec
status: draft
created: 2026-11-24
updated: 2026-11-24
linked-effort: "the maintainer's request in session on 2026-11-21 for skills that create, expand, curate and update documentation, and his request on 2026-11-24 for their initial specs, approach and questions"
linked-plan: null
linked-release: null
linked-strategy-brief: docs/internal/ideas/2026-11-24_docs-skills-approach.md
ac-count: 10
source-count: 8
requires-human-review: true
target-release: null
priority: P2
---

# Spec: docs plan, a read-only map of a repository's documentation gaps

## Task Summary

**Status:** draft. Nothing is built, and no implementation plan exists
**Last updated:** 2026-11-24 by claude (Opus 5.5), initial draft
**Linked plan:** not yet planned
**Open questions:** 4 (D1 to D4, see Open Questions / Decisions)
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: Every documentation file in the repository is listed with its reader layer and its page kind, or as unclassified with a reason
- [ ] AC-2: The plan grades all twelve cells for the whole repository, each as present, partial or absent, naming the files
- [ ] AC-3: The plan counts every public surface against its reference pages and names each surface with no page
- [ ] AC-4: The plan flags each page that mixes kinds, naming the headings that carry each kind
- [ ] AC-5: Every gap carries a stable id, its cell, the kind of page it needs, a proposed path, its reader and its evidence, in a stated rank order
- [ ] AC-6: A run changes no file except its own output, and every repository fact comes from one script call
- [ ] AC-7: Without a documentation map, the plan proposes one built from the same detection `plab-ship` uses
- [ ] AC-8: The plan leaves version parity and drift to the deterministic gates and to the refresh mode
- [ ] AC-9: A checker validates the plan file, proves every rule can fail against a committed sample, and CI runs it
- [ ] AC-10: A first run on this repository reports the three known absences: an architecture overview, a releases folder and the documentation map

### Currently In Progress

None. The spec was written on 2026-11-24. The next steps are the maintainer's answers to D1 to D4, then an implementation plan.

---

## Purpose

The maintainer asked for skills that create, expand, curate and update documentation [S1]. Before anything is written, someone has to know what is missing, and today that is known only at ship time, for one branch at a time, through `plab-ship`'s twelve-cell documentation standard [S3]. This spec defines the planning capability: a read-only pass over a whole repository that grades it against the same twelve cells and the four Diátaxis kinds [S5], and produces a ranked list of gaps that the write mode (DS-02, docs write) can take one at a time [S2].

## Scope

### In Scope

- Classifying every documentation file by reader layer (human, technical, agentic) and by page kind.
- Grading the twelve cells of the documentation standard for the repository as a whole.
- Counting public surfaces, such as skills, commands and scripts a user invokes, against their reference pages.
- Flagging pages that mix kinds.
- A ranked gap list with stable ids that DS-02 accepts as input.
- Proposing a documentation map when the repository has none.

### Non-Goals

- Writing or changing any documentation. That is DS-02 (docs write).
- Finding documents that are no longer true. That is DS-03 (docs refresh).
- Version parity between documents and manifests, which the repository's deterministic gates own [S4].
- Grading prose style, spelling or grammar [S4].
- Replacing `plab-ship`'s per-branch documentation block. A ship still fills its twelve cells for the change it carries [S3].

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Decides what to document next | Invokes the plan by name and reads the ranked gaps |
| Agent running DS-02 | Downstream consumer | Takes one gap id from the plan as its input |
| Agent running `plab-audit --lens=docs` | Possible consumer, depending on D1 | May read the plan instead of repeating the absence check |

## Requirements

### Classification

1. Every documentation file is assigned one reader layer, using the documentation map when it exists and the detection `plab-ship` already performs when it does not [S3, S6].
2. Every human-layer page is assigned one Diátaxis kind: tutorial, how-to guide, reference or explanation [S5]. Pages that are not Diátaxis kinds get one of the additional kinds D3 settles. [model-inference]
3. A page that serves two kinds is flagged, because Diátaxis holds that one page does one job [S5, S2].

### Grading

4. The twelve cells are the three readers by the four depths of the documentation standard: Discover, Use, Understand and Trust [S3]. Each cell is graded for the whole repository, not for one change.
5. The absence checks of the audit lens carry over: a root instruction file for agents, an onboarding path, a reference page per public surface, and a recorded decision for anything surprising [S4].

### The gap list

6. Each gap is addressable by a stable id, so the write mode can be pointed at one gap, and a later plan run keeps the ids of gaps that remain [S2]. [model-inference]
7. The ranking rule is stated in the plan itself, so a reader can see why one gap precedes another. D4 settles the rule. [model-inference]

### Conduct

8. The plan changes nothing in the repository, and every repository fact comes from one script call rather than model recall, as in the repository's other facts-script skills [S6].
9. The plan is gated by a checker with a committed sample and a canary that is proven to fail, because "a gate that cannot fail is not a gate" [S6].
10. If the plan keeps finding drift a deterministic gate missed, the gate is fixed rather than the plan widened [S4].

## Acceptance Criteria

AC-1: Every tracked file matched by the documentation map's human, technical and agentic globs appears in the plan's inventory with exactly one layer and one kind, or as `unclassified` with a reason of at least three words. [S3, S5]

AC-2: The plan contains one row for each of the twelve cells, and each row reads `present`, `partial` or `absent`, names the files it relied on for `present` and `partial`, and names what is missing for `partial` and `absent`. [S3]

AC-3: The plan states the number of public surfaces, the number of reference pages, and names each surface that has no reference page. [S4]
  Given: a repository with fifteen skills and fourteen `docs/skills/<name>/` folders
  When: the plan runs
  Then: it reports 15 surfaces, 14 pages, and names the one skill without a page

AC-4: Each page the plan flags as mixing kinds names the page, the kinds it found, and the headings that carry each kind. [S5]

AC-5: Every gap row carries an id of the form `gap-NN`, its cell, the kind of page it needs, a proposed path, the reader it serves, and the evidence for the gap; the rows appear in the order the plan's stated ranking rule produces. [S2]

AC-6: After a run, `git status --porcelain` differs from before only by the plan's own output path, and the run makes exactly one call to its facts script. [S6]

AC-7: In a repository without `.claude/plab-ship.local.md`, the plan includes a proposed map in that file's format, built from the same detection `derive-ship-facts.py` reports as `source: detected`, and does not write the file. [S3]

AC-8: The plan reports no finding about a version number disagreeing with a manifest, and no finding that a document's claim is out of date; such issues are named as out of scope, owned by the gates and by DS-03 (docs refresh). [S4]

AC-9: A checker script validates the plan's structure (all twelve cells, every gap row complete, ids unique), CI runs its self-test against a committed sample plan, and removing any one of its rules makes its canary fail. [S6]

AC-10: A first run on this repository lists, among its gaps, an architecture overview, a releases folder and the documentation map file, the three documents the maintainer's to-do list records as missing. [S2]

## Behavior / Examples

### Example 1: the first run on this repository (AC-5, AC-10)

The plan reads the twelve cells and finds Technical / Discover partial: `docs/internal/release-plans/INDEX.md` gives spec status, but no architecture overview exists. It writes `gap-01` for that cell, kind explanation, proposed path `docs/internal/architecture.md`, reader technical, evidence "no file in the technical globs describes the plugin's structure". The write mode can then be run against `gap-01` alone.

### Example 2: a mixed page (AC-4)

A skill's user guide carries a step-by-step quick start (a how-to guide) and a full flag table (reference) on one page. The plan flags it, naming the "Quick start" heading as how-to and the "Flags" heading as reference. It does not split the page; that is the write mode's work.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Cost | A run launches no more agents than the classification needs, and names every agent's model | [S6] |
| Privacy | The plan never quotes the content of a gitignored file into a tracked location | [S4] |

## Revisions

| Date | Author | Type | Description |
|---|---|---|---|
| 2026-11-24 | claude (Opus 5.5) | added | Initial draft created |

## Sources & Evidence

- **[S1]** The maintainer's request in session on 2026-11-21: "a couple skills for creating, expanding, curating, and updating docs" - private session transcript, summarized in [S2] - class A
- **[S2]** Approach and open questions for the docs skills - `docs/internal/ideas/2026-11-24_docs-skills-approach.md` - class A
- **[S3]** The documentation standard: twelve cells, three readers by four depths, and the documentation map - `skills/plab-ship/references/documentation-standard.md` - class A
- **[S4]** The audit's docs lens: absence, staleness, readability by audience, and its exclusions - `skills/plab-audit/references/lenses/docs.md` - class A
- **[S5]** Diátaxis, the four kinds of documentation and the one-page-one-job rule - https://diataxis.fr/ - class A
- **[S6]** The repository's engineering discipline and facts-script convention - `AGENTS.md` - class A
- **[S7]** The Toolchain Decision Sitting page of 2026-11-22, items DOC-1 (where documentation auditing lives) and DOC-2 (a skill that writes the documents) - the maintainer's private decision page, summarized in [S2] - class B
- **[S8]** A Sonnet research agent's survey of Diátaxis skills and documentation standards, 2026-11-21, not independently re-checked - private session transcript, summarized in [S2] - class B

### Unverified Claims

- "Pages that are not Diátaxis kinds get one of the additional kinds D3 settles." - appears in Requirements
- "a later plan run keeps the ids of gaps that remain" - appears in Requirements
- "D4 settles the rule." - appears in Requirements

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | How the three docs modes are packaged | (none) | Open | (none) |
| D2 | Manual-only or auto-discoverable | (none) | Open | (none) |
| D3 | Which page kinds beyond Diátaxis's four | (none) | Open | (none) |
| D4 | How gaps are ranked | (none) | Open | (none) |

### D1: How the three docs modes are packaged (Open)

**Summary.** Plan, write and refresh can be one skill with three modes, three skills, or the plan can live inside `plab-audit`.

**Context.** The decision page's DOC-1 recommended extending `plab-audit --lens=docs` and building no skill [S7]. That was written before the maintainer asked for these specs. A reply on the decision page maps to this decision as follows: DOC-1 A with DOC-2 A is option D; DOC-1 A with DOC-2 B is option C; DOC-1 B or C is option B; DOC-1 D defers this decision. Option A has no card on the page. The plan overlaps the lens's absence check, and the refresh overlaps its staleness check [S4]. Every auto-discoverable skill costs description budget in every session, so the number of skills matters [S6].

**Desired outcome.** One name for the maintainer to remember, no duplicated logic between the lens and the docs skills, and modes that share one facts script and the documentation map.

**Options / approaches.**

* **Option A:** one skill, `plab-docs`, with `--plan`, `--write` and `--refresh`, like `plab-audit`'s composable modes. The lens keeps its judgment questions and reads the plan's facts. One name and one facts script; the skill is larger.
* **Option B:** three skills, `plab-docs-plan`, `plab-docs-write` and `plab-docs-refresh`, as sketched on 2026-11-21. Each is small; three names and three descriptions.
* **Option C:** the plan becomes part of `plab-audit --lens=docs` (DOC-1 option A), and one skill, `plab-docs`, holds write and refresh. No new planning surface; the audit's five-file bundle is heavy for a gap list.
* **Option D:** no skill now; extend the lens only, and decide on a writer after a lens run (DOC-1 A with DOC-2 A).

**Recommendation.** Option A. It gives the maintainer one name for all four verbs he asked for, shares one facts script, and adds one skill rather than three. Confidence medium: option C is close, and is better if the maintainer wants documentation findings to stay inside the audit habit.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Manual-only or auto-discoverable (Open)

**Summary.** Whether the docs skill fires on its own or only when invoked by name.

**Context.** Eight of the fifteen skills are manual-only, and a manual-only skill must carry the flag in both harnesses, which `scripts/codex-invocation-check.py` enforces [S6]. "Update the docs" is an ordinary request in any session, which a skill that fired on it would hijack, and the write and refresh modes change files.

**Desired outcome.** The skill never fires on an ordinary documentation edit, and costs no description budget when unused.

**Options / approaches.**

* **Option A:** manual-only in both harnesses.
* **Option B:** auto-discoverable, with a do-NOT-fire clause for ordinary edits, as `plab-spec` does.

**Recommendation.** Option A. The trigger words collide with ordinary work, and the modes are deliberate, occasional runs.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D3: Which page kinds beyond Diátaxis's four (Open)

**Summary.** Diátaxis names four kinds for human documents; the technical and agentic layers need others.

**Context.** Diátaxis has no kind for changelogs, decision records, agent instructions or release notes, and no notion of an agent reader [S5, S8]. The documentation standard's cells name such files directly [S3].

**Desired outcome.** Every documentation file in this repository fits one kind, and no kind is so broad that the mixed-page check means nothing.

**Options / approaches.**

* **Option A:** the four Diátaxis kinds plus four more: changelog, decision record, agent instructions (`AGENTS.md`, `CLAUDE.md`), and skill reference (`SKILL.md` and its references).
* **Option B:** the four Diátaxis kinds only, with every other file `unclassified`.
* **Option C:** option A plus troubleshooting as its own kind, because the Trust depth asks for it and Diátaxis folds it into how-to guides.

**Recommendation.** Option A. It covers every file type the twelve cells name. Option C is worth it only if the first run shows troubleshooting content getting lost inside how-to pages.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D4: How gaps are ranked (Open)

**Summary.** The order in which the plan lists gaps decides what gets written first.

**Context.** The standard's depths run from Discover to Trust [S3]. A reader who cannot discover a feature never reaches its troubleshooting page, which argues for depth order. Evidence of need, such as a question the maintainer typed or a detour an audit took, argues for evidence order [S4].

**Desired outcome.** The top of the list is the gap whose page would be read soonest and most often.

**Options / approaches.**

* **Option A:** by depth (Discover, Use, Understand, Trust), then by evidence of need within a depth.
* **Option B:** by evidence of need first, then by depth.
* **Option C:** by reader, agentic first, because agentic files load into every session.

**Recommendation.** Option A. It is predictable, and evidence still orders the gaps within each depth.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
