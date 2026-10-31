---
id: AU-01
title: "plab-audit: repository appraisal, findings and roadmap"
type: spec
status: committed
created: 2026-09-19
updated: 2026-10-30
linked-effort: "docs/internal/ideas/plab-audit-skill-2026-08-15.md, the tracked parent brief. Its why-gate was closed by maintainer ruling on 2026-09-19, recorded in a maintainer-local design note that is not tracked; see Sources below"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 15
source-count: 9
requires-human-review: false
priority: P1
---

# Spec: plab-audit, repository appraisal, findings and roadmap

## Task Summary

**Status:** committed
**Last updated:** 2026-10-30 by claude, eight acceptance criteria ticked from recorded evidence
**Linked plan:** `implementation-plan.md` in this folder
**Open questions:** 0
**Revisions:** 2

**The `AU-` series letter is registered, as of 2026-09-20.** Phase 1 landed it in commit `9d0dfc3`. It required two edits rather than the one the plan named: the legend's only machine-readable home is `SERIES_LEGEND` in `scripts/gen-release-index.py`, which that script says of itself at line 15, and the table in `docs/internal/release-plans/README.md` is prose beside it. A README-only edit would have registered nothing.

This document and its plan were promoted out of `_local/` into this folder on 2026-09-20, which is what the letter was registered for.

### Acceptance Criteria Fulfillment

- [x] **AC-1** - The skill runs only on explicit invocation and never fires from conversational context
- [x] **AC-2** - Three modes run independently or together, defaulting to all three
- [ ] **AC-3** - Repository type is detected from disk, and a flag overrides the detection
- [x] **AC-4** - Every finding carries a file path, and a line number where one applies
- [x] **AC-5** - Every run emits a coverage statement naming what was read, sampled and skipped
- [ ] **AC-6** - The coverage statement records each deterministic tool invoked and its exit code
- [ ] **AC-7** - Appraisal reports current status, recent history and the repository's own declared plans, and ends with a big-picture section
- [ ] **AC-8** - Appraisal compares declared plans against observed state and reports disagreements
- [x] **AC-9** - Every roadmap item above the speculation break cites the finding it traces to
- [x] **AC-10** - Speculative material appears only below a labelled break and is never mixed with findings
- [ ] **AC-11** - Every roadmap item names its mechanization rung
- [ ] **AC-12** - A missing or failing deterministic tool degrades to a reported gap, never to silent omission
- [ ] **AC-13** - Output lands in a gitignored per-run folder, and a flag redirects it
- [x] **AC-14** - The skill's own self-check fails when the coverage statement is absent
- [x] **AC-15** - Every finding is reconciled against the repository's recorded decisions before publication, and the coverage statement names which decision records were read

**Ticked 2026-10-30, three versions after the skill shipped, from recorded evidence only.** Every box had stayed empty since the spec was written, although the skill has shipped 1.0.0, 1.0.1 and 1.1.0.

- **AC-1:** `skills/plab-audit/SKILL.md` carries `disable-model-invocation: true`, and `evals/` holds its manual-only case.
- **AC-2:** plan Phase 7 step 2 wrote all five files (2026-10-06), and step 4's `--appraise` run wrote exactly two (2026-10-05).
- **AC-4, AC-5, AC-9, AC-10, AC-14, AC-15:** `skills/plab-audit/scripts/bundle-check.py` enforces each one as rules R1 to R7. The rules were canary-tested in Phase 6, and CI runs the checker against `skills/plab-audit/examples/sample-bundle/` on every pull request.

**Left unticked, with the reason:**

- **AC-3:** detection was proven by the step 2 run, which detected `agent-plugin`; the override flag was never exercised.
- **AC-6, AC-8, AC-11:** no run record or checker rule verifies them.
- **AC-7:** R8 checks only the closing "Standing back" section, not the status, history and declared-plans content.
- **AC-12:** the degradation run is Phase 7 step 5, which is waived and optional.
- **AC-13:** runs landed in `_output/plab-audit/`, but the redirect flag was never exercised.

### Currently In Progress

None.

---

## Purpose

Point one skill at any repository in the fleet and receive a document that reorders the maintainer's queue: what the repository is and is worth, what is wrong with it, and what to do next, with every claim traceable to a file.

The workflow already exists and has been hand-run at least four times, most recently on 2026-08-29 against this repository. Each run re-derived the method from nothing. That is the signal a workflow is ready to become a skill.

## Scope

### In Scope

- Three composable modes: `--appraise`, `--audit`, `--roadmap`, defaulting to all three.
- Repository type detection with three packs: `agent-plugin`, `tauri`, `generic`, each naming its own deterministic tool list.
- One lens, `--lens=docs`, auditing documentation absence, staleness of substance, and readability.
- A coverage statement emitted on every run.
- A five-file output bundle written to a gitignored per-run folder.
- A labelled speculation break separating evidenced roadmap items from generative questions.

### Non-Goals

- **Drift and version-parity checking.** Owned by `plab-wrap-session`'s hygiene sweep and the repository's deterministic gates. If this lens keeps finding drift those gates missed, fix the gates rather than widening the lens.
- **Conformance grading.** `check.mjs` in the toolkit does this model-free, which is strictly better.
- **Security review of a diff.** Harness-native review commands cover changed code.
- **Cross-model document review.** That is `plab-ai-review`, and the maintainer ruled on 2026-09-18 that the two are different jobs.
- **Generating features from nothing.** Speculation is bounded to a labelled list that hands off to `plab-strategy-brief`.
- **`--deep` multi-agent fan-out.** Deferred; described in the parent brief but never designed to an executable specification.
- **`--ideate` formal chain.** Deferred to v1.1. The mechanism exists (`chain-contract.mjs` enforces orphans and phantoms) but requires a `plab-strategy-brief` scope amendment.
- **`--lens=publish-readiness`.** Cut on 2026-09-19 because its source document, S-22 (the plab-audit backlog proposal), is not in this repository and both briefs cite it second-hand.
- **A persistent committed audit file that diffs across runs.** A v2 candidate borrowed from `ksimback/tech-debt-skill`.

## Users / Actors

One: the maintainer, auditing their own repositories and occasionally an unfamiliar one. There is no second user, no onboarding path, and no configurability requirement. The known-repo path is optimised; the unfamiliar case degrades gracefully rather than being a co-equal mode.

## Requirements

1. The skill carries `disable-model-invocation: true` and runs only when invoked by name.
2. Modes compose. Any subset may run; the default is all three.
3. Type detection reads the filesystem: `library.json` or `.claude-plugin/plugin.json` means `agent-plugin`; `src-tauri/` or `tauri.conf.json` means `tauri`; otherwise `generic`. `--type` overrides.
4. Each pack is a data file naming its deterministic tools, its type-specific judgment questions, and what complete documentation means for that type.
5. The deterministic layer runs first. The model interprets tool output and makes only the judgments no tool can make.
6. A tool that is absent, fails, or times out is recorded as a coverage gap with its exit code. It never produces silence, and it never produces generic advice in place of a real check.
7. Findings carry severity, a file path, and a line number where the finding is line-scoped.
8. Roadmap items above the speculation break cite a finding identifier and name a mechanization rung.
9. Ranking follows the calibration default: token economy, deterministic enforcement over remembering, documentation agents read, evidence and reversibility, cross-harness durability, session continuity. Contributor onboarding, community growth and external backwards compatibility are unweighted.

## Acceptance Criteria

**AC-1 - Explicit invocation only.**
`SKILL.md` frontmatter carries `disable-model-invocation: true`. A trigger evaluation over three conversational phrasings that describe auditing a repository produces zero firings, and `/plab-audit` fires.
*Source: maintainer ruling, 2026-09-19.*

**AC-2 - Composable modes.**
Running `--appraise` alone produces `appraise.md` and `evidence.md` and no `findings.md`. Running with no mode flag produces all five files.
*Source: parent brief section 4, Approach A.*

**AC-3 - Type detection with override.**
Run against a fixture containing `library.json` and the report names type `agent-plugin`. Run the same fixture with `--type=generic` and the report names `generic`.
*Source: extension brief section 5, type packs.*

**AC-4 - Findings carry citations.**
Every entry in `findings.md` carries a file path. Entries scoped to a line carry a line number. A findings file containing an uncited claim fails the skill's self-check.
*Source: parent brief section 3, "findings that carry a file and a line are checkable; findings that do not are opinions".*

**AC-5 - Coverage statement present.**
`evidence.md` names, for the audited repository, which paths were read in full, which were sampled, and which were skipped, with the reason for each skip.
*Source: parent brief section 5, next step 3, "design the coverage statement first".*

**AC-6 - Tool invocations recorded with exit codes.**
`evidence.md` lists each deterministic tool the pack invoked, the exact command, and its exit code.
*Source: `_local/audits/2029-08-29_sol-xhigh/evidence.md`, "Validation commands and outcomes" (folder slug reads 2029, body reads 2026-08-29; the slug is a typo).*

**AC-7 - Appraisal covers status, history and declared plans.**
`appraise.md` contains: what the repository is, a current-status table (version, last release, last commit, open pull requests, branches in flight), recent history across the last releases, and a section reporting what the repository's own planning artifacts declare as next. It ends with a big-picture section headed "Standing back", which says what the repository is beyond its parts, what most distinguishes it and what most constrains it, and in a full run names the theme connecting the findings. The skill's self-check fails an `appraise.md` whose last section is not a non-empty "Standing back".
*Source: maintainer request, 2026-09-19; the closing section by maintainer ruling, 2026-10-06 (source 9).*

**AC-8 - Declared plans compared against observed state.**
`appraise.md` contains a section reporting where declared plans and observed state disagree, or stating explicitly that they agree. A stalled branch named in a current release plan is an instance that must be caught.
*Source: maintainer request, 2026-09-19.*

**AC-9 - Roadmap items trace to findings.**
Every item above the speculation break names the finding identifier it traces to, and that identifier resolves to an entry in `findings.md`.
*Source: parent brief section 5, next step 4, the boundary test.*

**AC-10 - Speculation is separated and labelled.**
`roadmap.md` contains exactly one horizontal break introducing a section headed with a phrase naming these as questions the audit cannot answer, and stating that nothing below traces to evidence. No item below it carries a finding citation; no item above it lacks one.
*Source: parent brief section 7, epistemic contamination; maintainer ruling, 2026-09-19.*

**AC-11 - Mechanization rung named.**
Every roadmap item above the break names its rung: CI check, committed script, documented convention, or remembered practice.
*Source: parent brief section 7, the mechanization ladder.*

**AC-12 - Degradation is reported, not silent.**
Run the audit against repo-sync-tool with `cargo` unavailable on PATH. The run completes, `evidence.md` records the tool as a gap with its failure, and `findings.md` contains no Rust-specific finding asserted without tool backing.
*Source: extension brief section 3, "the deterministic-first spine has to handle that gracefully rather than padding with generic advice".*

**AC-13 - Output location.**
Default output is `_output/plab-audit/<repo>_<YYYY-MM-DD>/`. `--out <path>` redirects it. `_output/` is already gitignored.
*Source: AGENTS.md, generated-artifact convention.*

**AC-14 - The self-check can fail.**
Remove the coverage section from a sample output and the skill's self-check reports failure. This is the canary: a check that cannot be shown failing is not a check.
*Source: AGENTS.md engineering discipline, "a gate that cannot fail is not a gate".*

**AC-15 - Findings are reconciled against recorded decisions before publication.**
Before a candidate becomes a finding, it is checked against what the audited repository has already decided: architecture decision records, suppression configuration, release notes, changelog, and any prior audit in the tree. `evidence.md` carries a section naming each decision record consulted and what it settled. A candidate that a recorded decision already answers is either withdrawn or narrowed to the part the decision leaves open, and the withdrawal is reported rather than deleted.
*Source: the Phase 2 fixture run of 2026-09-20, in which this step withdrew 7 of 15 candidates, including the two highest-ranked. `_local/ideas/audit/draft/fixture/findings.md`, "Candidate findings withdrawn on evidence".*

## Behavior / Examples

### Example 1: Full run on an agent-plugin repository (grounds AC-2, AC-3, AC-7, AC-9)

`/plab-audit E:/Projects/prisant-labs/Nonfiction`

Detects `agent-plugin` from `library.json`. Runs the agent-plugin pack's deterministic tools. Writes five files to `_output/plab-audit/nonfiction-studio_2026-09-20/`. `appraise.md` reports 14 skills, version, release cadence and what the repository's release plans declare as next. `roadmap.md` ranks items, each citing a finding, and ends with a labelled speculation section.

### Example 2: Tauri repository with a missing toolchain (grounds AC-12, AC-6)

`/plab-audit E:/Projects/prisant-labs/repo-sync-tool` on a machine without `cargo`.

Detects `tauri` from `src-tauri/`. The pack attempts `cargo clippy` and `cargo audit`, both fail to launch. `evidence.md` records both commands with their failure. `findings.md` carries no Rust finding. `appraise.md` states that the Rust surface was not assessed. The run exits successfully, because an honest partial audit is the correct outcome.

### Example 3: Appraise only (grounds AC-2)

`/plab-audit . --appraise` writes `appraise.md` and `evidence.md` only.

## Non-Functional Requirements

- **Cost ceiling.** `--appraise` alone on a repository the size of nonfiction-studio completes without exhausting a single session's context. Measured on the fixture run and recorded in the plan; this replaces the parent brief's unmeasurable "minutes and pennies".
- **Read-only.** The skill writes only inside its output folder. It never modifies the repository under audit.
- **Cross-harness.** Pack files and reference documents are plain Markdown, readable by Codex as well as Claude Code.

## Revisions

**R-1, 2026-09-20: AC-15 added, and `ac-count` raised from 14 to 15.**

The Phase 2 fixture audit of nonfiction-studio produced 15 candidate findings and published 8. The 7 withdrawals were all caused by the same step, which no acceptance criterion required: checking a candidate against the audited repository's own recorded decisions before publishing it.

The step is not optional polish. Two of the withdrawn candidates were the highest-ranked findings of the first draft, and one of them recommended a change that the audited repository's `askit.config.json` records as already tested and rejected with measured evidence (28 errors from a competing check). A skill built to the 14-criterion spec would have published that recommendation.

Source 8 is added to the sources table for the fixture run.

**R-2, 2026-10-06: AC-7 amended to require a closing big-picture section. `ac-count` is unchanged at 15.**

The hand-made fixture audit of 2026-09-20 ended its `appraise.md` with a seventh section, "Standing back": a synthesis of what the repository is and what constrains it. The specification defined six sections, so the skill's first full run, on 2026-10-06, wrote six and omitted nothing the specification required. Phase 7 step 3 of the implementation plan recorded the difference as an open question.

The maintainer ruled on 2026-10-06 that every appraisal ends with that section, because it shows that the model saw the repository as a whole. This is source 9. The criterion is amended rather than added, because the section belongs to the appraisal that AC-7 already defines. `bundle-check.py` rule R8 enforces the section's structure; what it says is a reading task, defined in `skills/plab-audit/references/output-bundle.md`.

## Sources & Evidence

| # | Source | Class |
|---|---|---|
| 1 | `docs/internal/ideas/plab-audit-skill-2026-08-15.md`, the tracked parent brief | First-party, tracked |
| 2 | `_local/ideas/2026-08-23_audit-skill-family-plan.md`, the extension brief | First-party, gitignored |
| 3 | `_local/ideas/2026-08-15_skill-candidates.md`, the skill-candidates memo | First-party, gitignored |
| 4 | `_local/audits/2029-08-29_sol-xhigh/`, the 2026-08-29 hand-run audit | First-party working prototype |
| 5 | Maintainer rulings, 2026-09-18 and 2026-09-19, recorded in `2026-09-18_design-decisions.md` | Direct instruction |
| 6 | `scripts/checks/description-score.mjs` and `chain-contract.mjs` in agent-skills-toolkit | Directly observed |
| 7 | `docs/internal/release-plans/README.md`, the series legend | First-party, tracked |
| 8 | `_local/ideas/audit/draft/fixture/`, the 2026-09-20 hand-run fixture audit of nonfiction-studio | First-party, gitignored |
| 9 | Maintainer ruling, 2026-10-06: every appraisal ends with a big-picture section. Recorded in the maintainer's private decision register | Direct instruction |

**Five of these nine sources are maintainer-local and cannot be opened by any other reader of this repository.** Sources 2, 3, 4, 8 and 9 live under gitignored `_local/`. They are cited rather than paraphrased because the provenance of an acceptance criterion matters more than its reachability, and because a criterion whose source is silently dropped is indistinguishable from one that was invented. Where a claim from one of them is load-bearing, it is restated in full in this document rather than left behind the citation. Source 1 and source 7 are tracked and readable by anyone.

### Unverified Claims

- **S-22 (the plab-audit backlog proposal) is unreadable.** Both briefs cite it as the origin of the publish-readiness lens. The document is not in this repository and was not located. The lens is cut on that basis rather than built from a second-hand summary.
- **The 0.65 description score for `plab-ai-review` may be a tool artifact.** ADR 0049 in the toolkit documents that a description whose `WHEN` pattern the English lexicon cannot match caps at 0.65 and cannot pass at any quality. Check before treating that score as a defect.

## Open Questions / Decisions

### D-AU-1: Model invocation (Decided)

**Decision: disabled. Explicit invocation only.**

The parent brief argued the opposite: the skill exists to displace a working manual habit, and a manual-only skill displaces nothing. The maintainer ruled for explicit invocation on 2026-09-19. This makes `plab-audit` the second skill carrying `disable-model-invocation: true`, alongside `plab-init-project`.

Consequence recorded rather than re-argued: if the skill goes unused, a weak description is no longer a candidate cause, so the dogfood gate becomes the only adoption signal available.

### D-AU-2: Tauri pack depth (Decided)

**Decision: full pack, not a stub.**

Both briefs scoped tauri as a stub declaring its tool list without running it. The maintainer named repo-sync-tool as a fixture and ruled on 2026-09-19 that it should be really audited. The degradation test moves from "the stub is honest about being a stub" to AC-12, where a genuinely missing toolchain is reported rather than padded.

### D-AU-3: Where speculation lives (Decided)

**Decision: a labelled break at the foot of `roadmap.md`, not a separate file and not a formal chain.**

Keeps one document the maintainer reads while preserving epistemic separation. The formal `--ideate` chain to `plab-strategy-brief` is deferred to v1.1, which removes a scope amendment and version bump from this effort.
