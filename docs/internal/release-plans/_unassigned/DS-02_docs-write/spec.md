---
id: DS-02
title: "Docs write: create or expand one documentation page of one kind, with real examples and a cold reader"
type: spec
status: draft
created: 2026-11-24
updated: 2026-11-24
linked-effort: "the maintainer's request in session on 2026-11-21 for skills that create, expand, curate and update documentation, and his request on 2026-11-24 for their initial specs, approach and questions"
linked-plan: null
linked-release: null
linked-strategy-brief: docs/internal/ideas/2026-11-24_docs-skills-approach.md
ac-count: 10
source-count: 6
requires-human-review: true
spec-dependencies: [DS-01]
target-release: null
priority: P2
---

# Spec: docs write, one page of one kind

## Task Summary

**Status:** draft. Nothing is built, and no implementation plan exists
**Last updated:** 2026-11-24 by claude (Opus 5.5), initial draft
**Linked plan:** not yet planned
**Open questions:** 2 (D1 and D2, see Open Questions / Decisions), plus DS-01 D1 (packaging), which this spec inherits
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: A run takes either a gap id from a docs plan or an explicit cell, kind and path, and refuses with neither
- [ ] AC-2: A run writes or expands exactly one page, and the page is of exactly one kind
- [ ] AC-3: Expanding a page keeps its kind; content of another kind goes to a new or linked page
- [ ] AC-4: The checker rejects a page that mixes kinds, naming the offending headings
- [ ] AC-5: Every command in the page was run and its real output shown, or it is marked as not run with the reason
- [ ] AC-6: Every path, flag and skill name the page cites exists in the repository
- [ ] AC-7: The new page is reachable from the repository's discovery surface, or the run says why not
- [ ] AC-8: The cold reader from the documentation standard runs on human-layer pages, and each gap it finds is fixed or recorded
- [ ] AC-9: The run writes only on a branch other than the default branch, and never merges
- [ ] AC-10: The checker proves every rule can fail against a committed sample, and CI runs it

### Currently In Progress

None. The spec was written on 2026-11-24. It waits on DS-01's decisions, then on the first docs plan run, whose gaps decide which page kinds this mode must handle first.

---

## Purpose

The maintainer asked for skills that create and expand documentation [S1]. The docs plan (DS-01) finds what is missing; this spec defines the mode that fills one gap at a time. It writes to the standard `plab-ship` already holds, whose bar is "best in class, not adequate" and whose rule is that examples are real [S3], and it keeps Diátaxis's rule that one page does one job [S4]. The decision page recommended deciding on a writer only after a real plan run shows which gaps are worth filling [S6]; this spec is written now so that decision has something concrete to accept or reject.

## Scope

### In Scope

- Writing a new page, or expanding an existing one, for one cell and one kind.
- Agentic-layer pages, including `AGENTS.md` sections and skill reference files, which no outside skill covers [S2].
- Running every command the page shows.
- The cold reader for human-layer pages.

### Non-Goals

- Deciding what to write. That is DS-01 (docs plan), or the maintainer naming the cell, kind and path.
- Rewriting a page that is out of date. That is DS-03 (docs refresh).
- Guide bundles in four formats, which `plab-guide` produces [S5].
- Merging, tagging or releasing, which `plab-ship` does [S5].

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Picks the gap and approves the page | Invokes the write mode with a gap id or an explicit target |
| Cold reader | A Sonnet subagent in a fresh context | Reads only the changed human-layer page and answers the standard's five questions |
| `plab-ship` | Downstream | Ships the branch the page was written on, filling its documentation block as usual |

## Requirements

### Input and output

1. A run has exactly one target: a gap id from a docs plan, or a cell, a kind and a path given explicitly [S2].
2. A run writes or expands one page, and that page is of one kind, because a page that does two jobs does neither well [S4].
3. Expanding a page never changes its kind. Content of another kind is written to its own page and linked [S4]. [model-inference]

### Quality

4. Examples are real: "an example that has not been run is a claim, not documentation" [S3].
5. Names are exact: every path, flag and skill name in the page exists, because a reader searches for the word they were given [S3].
6. A page nobody can find has not filled a Discover gap; each page is linked from a discovery surface, such as a docs index, the README or an `AGENTS.md` entry [S3].
7. The cold reader tests whether someone new can use the page, as the standard defines it [S3].
8. The repository's house rules hold: no hard-wrapped prose and no em-dashes or en-dashes [S5].

### Conduct

9. Work happens on a branch, and the main branch is protected; merging belongs to `plab-ship` and the merge check [S5].
10. The mode follows the checker pattern: a committed sample, a canary proven to fail, and a CI self-test [S5].

## Acceptance Criteria

AC-1: A run given `--gap gap-NN` writes the page that gap names; a run given an explicit cell, kind and path writes that page; a run given neither, or a gap id absent from the newest plan, writes nothing and says which input is missing. [S2]

AC-2: After a run, exactly one documentation file is new or changed, apart from the one link AC-7 allows, and the checker classifies it as a single kind. [S4]

AC-3: When a run expands an existing page, the page's kind before and after the run is the same; any content of another kind appears in a separate page that the expanded page links to. [S4] [model-inference]

AC-4: The checker fails a page whose headings carry two kinds, and its message names each heading and the kind it carries. [S4]
  Given: a how-to page to which a run has added a full flag table
  When: the checker runs on it
  Then: it fails, naming the flag table's heading as reference

AC-5: Every fenced command in the page is followed by output the run captured from executing it, or by a line saying it was not run and why, such as that it changes something outside a throwaway folder. [S3]

AC-6: The checker fails a page that cites a path, a command-line flag or a `plab-` skill name that does not exist in the repository at the branch's head. [S3]

AC-7: The run adds one link to the new page from a discovery surface named by the documentation map, or reports why no link is needed; a page that already had an inbound link needs none. [S3]

AC-8: For a human-layer page, the run sends only that page to a Sonnet cold reader with the standard's five questions, and the run's report lists every question the reader could not answer, each marked fixed on the branch or recorded as unfixed with a reason. [S3]

AC-9: A run on the default branch writes nothing and says to create a branch; a run on any other branch never runs `git merge`, `gh pr merge` or `git push` to the default branch. [S5]

AC-10: The checker's self-test runs in CI against a committed sample page, and removing any one of its rules (single kind, real commands, existing names) makes its canary fail. [S5]

## Behavior / Examples

### Example 1: filling a gap from the plan (AC-1, AC-7)

The plan's `gap-01` asks for an explanation page at `docs/internal/architecture.md`. The write mode reads the gap, gathers its facts from the repository, writes the page as an explanation (what the plugin is made of and why), adds a link to it from `AGENTS.md`'s Build and validate section, and runs the checker. It does not run the cold reader, because the page is technical-layer.

### Example 2: refusing to mix (AC-3, AC-4)

The maintainer asks to expand a skill's how-to page with every flag. The mode writes the flags to the skill's reference page instead, and adds one line to the how-to page linking there. The how-to page stays a how-to page.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Safety | A command the page shows that would change anything outside a throwaway folder is not run; the page says so | [S3] |
| Cost | The cold reader runs on Sonnet with an explicit model, never inheriting the session model | [S5] |

## Revisions

| Date | Author | Type | Description |
|---|---|---|---|
| 2026-11-24 | claude (Opus 5.5) | added | Initial draft created |

## Sources & Evidence

- **[S1]** The maintainer's request in session on 2026-11-21: "a couple skills for creating, expanding, curating, and updating docs" - private session transcript, summarized in [S2] - class A
- **[S2]** Approach and open questions for the docs skills - `docs/internal/ideas/2026-11-24_docs-skills-approach.md` - class A
- **[S3]** The documentation standard: twelve cells, "What good looks like", and the cold reader - `skills/plab-ship/references/documentation-standard.md` - class A
- **[S4]** Diátaxis, the four kinds of documentation and the one-page-one-job rule - https://diataxis.fr/ - class A
- **[S5]** The repository's conventions, engineering discipline and skill list - `AGENTS.md` - class A
- **[S6]** The Toolchain Decision Sitting page of 2026-11-22, item DOC-2 (a skill that writes the documents), recommending a writer only for gaps a real run shows - the maintainer's private decision page, summarized in [S2] - class B

### Unverified Claims

- "Content of another kind is written to its own page and linked" - appears in Requirements and AC-3, as a reading of Diátaxis's one-page-one-job rule

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Whether the write mode commits | (none) | Open | (none) |
| D2 | Which pages get the cold reader | (none) | Open | (none) |

### D1: Whether the write mode commits (Open)

**Summary.** The mode can leave its page in the working tree, commit it, or open a pull request.

**Context.** `plab-ship` carries finished branches over the line, so the write mode need not [S5]. Leaving changes uncommitted is safest but makes a series of pages harder to review one at a time.

**Desired outcome.** Each page lands as a reviewable unit, and nothing reaches the default branch without the merge check.

**Options / approaches.**

* **Option A:** write to the working tree on a branch, and commit only on the maintainer's yes. Never push or open a pull request.
* **Option B:** commit each page on the branch automatically, with a conventional message; never push.
* **Option C:** commit, push and open a pull request, leaving the merge to `plab-ship`.

**Recommendation.** Option A for the first version. It matches how the maintainer reviews today, and option B is a small change once the pages prove trustworthy.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Which pages get the cold reader (Open)

**Summary.** The cold reader costs one Sonnet agent per page; it could run on every human page or only some.

**Context.** The standard runs the cold reader for a feature or a behaviour change [S3]. Its five questions (what is it for, when not to use it, what do I run first, what should I see, what do I do when it fails) fit Discover and Use pages best.

**Desired outcome.** Every page a newcomer depends on is cold-read, and no agent runs on a page its questions do not fit.

**Options / approaches.**

* **Option A:** every human-layer page.
* **Option B:** human-layer Discover and Use pages always; Understand and Trust pages only on request.
* **Option C:** only on request.

**Recommendation.** Option B. The five questions are a quick start's test, and an explanation page cannot answer "what do I run first".

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
