---
title: "The docs skills: approach and open questions for DS-01 to DS-03"
date: 2026-11-24
author: claude (Opus 5.5)
status: draft
specs:
  - docs/internal/release-plans/_unassigned/DS-01_docs-plan/spec.md
  - docs/internal/release-plans/_unassigned/DS-02_docs-write/spec.md
  - docs/internal/release-plans/_unassigned/DS-03_docs-refresh/spec.md
---

# The docs skills: approach and open questions

**Recommendation: build one manual-only skill, `plab-docs`, with three modes, and build the modes in order: `--plan` first, then `--write`, then `--refresh`.** The three specs define what each mode must do. This document records the research behind them, how they fit the skills that already exist, the order of work, and the questions only the maintainer can answer. Packaging is decision D1 (one skill, three skills, or part of `plab-audit`) in DS-01, so nothing here is settled until that is ruled.

## What the maintainer asked for

On 2026-11-21 the maintainer asked for "a couple skills for creating, expanding, curating, and updating docs", in the session that also researched Diátaxis and other documentation standards. On 2026-11-24 he asked for the initial specs, approach and questions. The three specs cover the four verbs:

| Verb | Spec | Mode |
|---|---|---|
| Planning what to create | DS-01 (docs plan) | `--plan`: read-only, finds and ranks the gaps |
| Creating and expanding | DS-02 (docs write) | `--write`: writes or expands one page of one kind |
| Curating and updating | DS-03 (docs refresh) | `--refresh`: finds documents that are no longer true, and proposes fixes |

## What the research found (2026-11-21)

A Sonnet research agent searched GitHub, skill registries and the Diátaxis site on 2026-11-21. Its findings were not independently re-checked, so treat them as medium confidence.

- **No mature outside skill exists.** Several Diátaxis skills exist, all solo-maintained. The best evidenced sits in `pproenca/dot-skills` (227 stars for the whole repository, pushed 2026-08-15). None covers agent-facing documents, changelogs, decision records, or keeping documents current. That last point rests on a negative search.
- **Diátaxis is a lens, not a template set.** It sorts human documents into four kinds: tutorials (learning by doing), how-to guides (reaching a goal), reference (looking facts up) and explanation (understanding). Its rule that one page does one job is the part worth keeping. It has no notion of an agent reader, no maintenance workflow and no verification step.
- **Each reader layer gets a standard for page shape.** `plab-ship`'s twelve-cell documentation standard stays the contract for what must exist:

| Layer | Standards that shape its pages |
|---|---|
| Human | Diátaxis, Keep a Changelog, and the Standard Readme section order |
| Technical | MADR decision records (already scaffolded by `plab-init-project`), plus three arc42 sections: context, building blocks and risks |
| Agentic | `AGENTS.md`, plus Anthropic's skill best-practices guide |

The agentic layer is where nothing outside exists, so it is where these skills would add the most.

## How the modes fit what already exists

| Existing piece | What it does today | How the docs skills relate |
|---|---|---|
| `skills/plab-ship/references/documentation-standard.md` | The twelve cells, applied to one branch at ship time | The docs skills apply the same grid to the whole repository, between ships. They reuse the file; they do not copy it |
| `skills/plab-audit/references/lenses/docs.md` | An audit lens: absence, staleness, readability by audience, release discipline | `--plan` overlaps its absence check and `--refresh` overlaps its staleness check. D1 in DS-01 decides whether the lens or the skill owns each |
| `plab-wrap-session`'s `doc-update-rules.md` | "When in doubt, don't update" during a wrap | Unchanged. A wrap reconciles; the docs skills are deliberate work |
| `plab-guide` | A four-format guide bundle for one topic | Unchanged. A guide is a standalone deliverable; `--write` writes a page that belongs in the repository's own tree |
| `.claude/plab-ship.local.md` | The documentation map: which globs belong to which layer | All three modes read it, and `--plan` proposes one when it is missing |

The lens keeps one rule the docs skills must also keep: **if a check keeps finding drift that a deterministic gate missed, fix the gate rather than widening the check.** DS-03 carries this as an acceptance criterion.

## Order of work

1. **Rule the decisions in DS-01**, above all D1 (packaging). DS-02 and DS-03 inherit the answer.
2. **Build `--plan` first and run it on this repository.** It has a known answer: this repository lacks an architecture overview, a releases folder and the documentation map, recorded in the maintainer's private to-do list. A plan that misses those three has failed, which makes the first run a real test rather than a demonstration.
3. **Build `--write` against the gaps that first run finds.** This follows the decision page's DOC-2 recommendation: build a writer for gaps a real run shows, not for imagined ones.
4. **Build `--refresh` last.** It is the most mechanical, so most of it is scripts, and it benefits from the classification `--plan` already does.

Each mode follows the repository's checker pattern: one facts script, one checker with a committed sample, a canary proven to fail, and a CI self-test.

## How this relates to the decision page

The Toolchain Decision Sitting page of 2026-11-22 carries DOC-1 (where documentation auditing lives) and DOC-2 (a skill that writes the documents). Its DOC-1 recommendation, extend `plab-audit --lens=docs` and build no skill, was written before the maintainer asked for these specs. DS-01's D1 now carries the page's choices beside a one-skill option the page never offered. A reply on the page maps to DS-01 D1 as follows:

| Reply on the decision page | DS-01 D1 option |
|---|---|
| DOC-1 A with DOC-2 A (lens only; decide on a writer later) | D |
| DOC-1 A with DOC-2 B (lens for planning; build a writer now) | C |
| DOC-1 B or C (a planning skill, or all three skills) | B |
| DOC-1 D (not now) | D1 deferred |
| None: option A, one `plab-docs` skill with three modes | A, the recommendation | No card on the page covered curating and updating; DS-03 fills that gap.

## The open questions, in one place

Each question lives in its spec, under that spec's "Open Questions / Decisions" section.

| Spec | Question | Recommendation |
|---|---|---|
| DS-01 D1 | One skill with three modes, three skills, or the plan as part of `plab-audit` | One skill, `plab-docs`, with three modes |
| DS-01 D2 | Manual-only, or auto-discoverable | Manual-only in both harnesses |
| DS-01 D3 | Which page kinds beyond Diátaxis's four | Four more: changelog, decision record, agent instructions, skill reference |
| DS-01 D4 | How gaps are ranked | By depth (Discover, Use, Understand, Trust), then by evidence of need |
| DS-02 D1 | Whether `--write` commits | Write to the working tree on a branch; commit only on a yes; never merge |
| DS-02 D2 | Whether the cold reader runs on every human page | Yes for Discover and Use pages; optional for the others |
| DS-03 D1 | Default scope of a refresh | Documents changed or cited since the last version tag; `--all` for the whole repository |
| DS-03 D2 | Report only, or apply fixes | Report with a proposed patch, applied in one batch on a yes |

## What is not known

- Whether a model can classify a page's Diátaxis kind reliably enough for a checker to reject mixed pages. A wrong rejection would make `--write` refuse good pages. The first `--plan` run should measure agreement against a hand classification of this repository's pages.
- What a run costs. Nothing has been measured.
- Whether the maintainer wants these skills used beyond this repository. The specs assume any repository, because the documentation standard is not specific to this one.
