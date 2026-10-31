---
name: plab-spec
description: "Write a feature specification with numbered, source-cited acceptance criteria into a
  per-effort folder under docs/internal/release-plans/. Produces a spec.md carrying frontmatter, an
  agent-updated Task Summary block, and links to the related effort and plan. Writes into
  _unassigned/ by default; pass --target-release vX.Y.Z to write straight into a release folder.
  Use when the problem space is already explored and the requirements need a durable home that
  survives rewrites of the plan beneath them: 'write the spec', 'spec this effort', 'turn this into
  acceptance criteria'. Do NOT fire on a passing mention of the word spec, on questions about an
  existing spec, or on a request to implement one. Defines WHAT to build; the implementation-plan
  template under docs/internal/release-plans/ defines HOW and /plab-strategy-brief explores WHY."
argument-hint: "--effort <id-or-path> [--from-brief <path>] [--target-release vX.Y.Z] [--slug <slug>] [--out <path>] [--revise] [--dry-run]"
license: MIT
metadata:
  version: "1.3.4"
  updated: 2026-10-30
---

# Create Spec

Produce a feature specification: the contract between intent and implementation. Spec defines **what** to build and how the team knows it's done. Plan defines **how**. Strategy-brief defines **why**. This skill produces the spec - nothing more, nothing less.

## Track Progress

Use the todo tool to track these phases. Mark each as complete before proceeding.

- [ ] Phase 1: Intake & scope check
- [ ] Phase 2: Locate and gather sources
- [ ] Phase 3: Build frontmatter + Task Summary block
- [ ] Phase 4: Write requirements + acceptance criteria (with citations)
- [ ] Phase 5: Add behavior, examples, non-functional, revisions, open questions
- [ ] Phase 6: Verify quality gates and deliver

## When to Use This Skill

- The team has decided to build a feature (problem space already explored)
- Acceptance criteria need a stable home that survives plan rewrites
- Multiple agents (or humans) will read the requirements; they need a parseable contract
- An audit trail from requirement → source is required
- The feature spans more than one session or ships to users

## When NOT to Use This Skill

- The problem space hasn't been explored yet → use `/plab-strategy-brief` first
- You're writing implementation steps → that's `docs/internal/release-plans/implementation-plan-template.md`
- Bundling completed features for a tagged release → that's `/plab-release-plan`
- The feature is one sentence and one AC → write it inline in the effort brief or backlog row
- The skill being requested is itself a skill → use `/skill-creator`

## Input Contract

| Input | Required | Default | Notes |
|-------|----------|---------|-------|
| `--effort <id-or-path>` | Yes | - | Effort id (e.g., `S-04`) or path to effort brief. Spec attaches to this effort |
| `--target-release <vX.Y.Z>` | No | - | If set, write into `release-plans/plan_NN_<slug>/<id>_<slug>/`; otherwise write into `release-plans/_unassigned/<id>_<slug>/`. The whole folder moves between the two via `/plab-release-plan --promote` |
| `--slug <text>` | No | derived from effort title | Slug for the per-effort folder name; auto-kebab-cased from the effort title if omitted |
| `--from-brief <path>` | No | - | Seed AC + scope from an existing strategy-brief's Recommendation section |
| `--out <path>` | No | (computed - see Output Contract) | Override the computed output path |
| `--revise` | No | off | Append to existing spec's Revisions section instead of overwriting |
| `--dry-run` | No | off | Show what would be written without writing |

If `--effort` is missing or doesn't resolve, ask the user. Don't invent an effort id.

## Output Contract

A single markdown file `spec.md` inside a per-effort folder. Path depends on `--target-release`:

- **`--target-release vX.Y.Z` passed:** `docs/internal/release-plans/plan_NN_<slug>/<id>_<slug>/spec.md`
- **`--target-release` omitted (default):** `docs/internal/release-plans/_unassigned/<id>_<slug>/spec.md`

The whole per-effort folder is the unit of release scoping (see `docs/internal/planning-artifact-model.md` D1). Move it between `_unassigned/` and `plan_NN_<slug>/` via `/plab-release-plan --promote` / `--demote`.

> **Legacy v1.0.0 path:** spec used to write to `docs/internal/efforts/<id>/<id>_spec.md`. Specs written by v1.0.0 are not migrated automatically; v1.1.0 only governs new specs. The legacy path is documented in `docs/internal/planning-artifact-model.md` D1 implementation notes.

The spec file shape is unchanged (full template at `references/spec-template.md`):

```
---
[frontmatter - see references/frontmatter-schema.md]
---

# Spec: <Feature Title>

## Task Summary
[agent-updated status block - see references/task-summary-block.md]

## Purpose
## Scope
## Non-Goals
## Users / Actors
## Requirements
## Acceptance Criteria
## Behavior / Examples
## Non-Functional Requirements
## Revisions
## Sources & Evidence
## Open Questions
```

Every section is mandatory. Empty sections include a one-line "N/A - <reason>" rather than being omitted.

## Workflow

### Phase 1 - Intake & Scope Check

1. Resolve `--effort` to an effort id and brief path. If unresolved: ask user.
2. Read the effort brief; extract title, type, status. Derive slug from the title (kebab-cased) unless `--slug` is passed.
3. Determine output path: if `--target-release vX.Y.Z` is set, target `release-plans/plan_NN_<slug>/<id>_<slug>/spec.md`; otherwise target `release-plans/_unassigned/<id>_<slug>/spec.md`. If the release folder doesn't exist yet, prompt the user before creating it (a release plan should usually be scaffolded by `/plab-release-plan --create` first).
4. Size check: estimate AC count from the brief.
   - **AC ≤ 1**: confirm spec is warranted; offer inline-in-effort instead.
   - **AC > 10 OR spans multiple actor types**: warn - likely should be split into multiple specs. Ask user before proceeding.
5. Confirm: target file path does not already exist (unless `--revise`). Create the per-effort folder if needed.

### Phase 2 - Locate and Gather Sources

1. Read these in order if present:
   - The effort brief itself
   - `--from-brief` strategy-brief (if provided)
   - Linked GitHub issue (if `gh-issue:` in effort frontmatter)
   - Any `decisions/` ADRs the brief references
   - Prior specs in the same effort folder (rare, possible)
2. Build a working list of facts → sources mapping.
3. Mark any requirement-shaped statement that has no external source - these will get `[model-inference]` markers.

See `references/source-traceability.md` for citation rules.

### Phase 3 - Build Frontmatter + Task Summary Block

1. Generate frontmatter (see `references/frontmatter-schema.md`):
   - id, title, type=spec, status=draft, created, updated, linked-effort, linked-plan (null until plan exists), linked-strategy-brief (if any), linked-release (set to the release plan path if `--target-release` was passed; otherwise null), source-count, ac-count
2. Generate Task Summary block (see `references/task-summary-block.md`):
   - Pre-fill structure with placeholders for every AC
   - Status: draft
   - Open questions: count from Phase 4 (initially 0 - updated as written)
   - Last-updated: today
3. Write both to the output file.

### Phase 4 - Write Requirements + Acceptance Criteria

1. Requirements section: prose paragraphs, each citing a source `[S1]` or marked `[model-inference]`.
2. Acceptance Criteria: numbered list, AC format from `references/ac-format.md`. Each AC:
   - Numbered (AC-1, AC-2, ...)
   - One observable outcome per AC
   - Testable phrasing (a future agent must be able to verify)
   - Optional Given/When/Then for behavior-heavy AC
   - Source citation per AC
3. Update Task Summary's AC checklist (one entry per AC, all unchecked at draft time).
4. Increment `ac-count` in frontmatter.

### Phase 5 - Add Behavior, Examples, NFR, Revisions, Open Questions

1. Behavior / Examples: concrete walk-throughs for non-trivial AC.
2. Non-Functional Requirements: performance, security, accessibility, observability - only what's actually constrained. Skip rather than invent.
3. Revisions: stub the section header. First revision row goes in when spec is committed.
4. Sources & Evidence: full source list with credibility class (A/B/C - see `references/source-traceability.md`).
5. Open Questions: list; update `open-questions:` count in Task Summary.

### Phase 6 - Verify Quality Gates

Before delivering, check (these are **constraints** - must hold):

- [ ] Every required section present (none omitted; "N/A" lines acceptable)
- [ ] Frontmatter has all required fields (`references/frontmatter-schema.md`)
- [ ] Every requirement and AC has a citation OR `[model-inference]` marker
- [ ] AC count in frontmatter matches actual count
- [ ] Source-count in frontmatter matches Sources & Evidence section
- [ ] No content from strategy-brief's "Approaches" section copied in (scope-creep guard)
- [ ] No implementation steps (those belong in plan) - run the "would I write this in a plan?" test on each section
- [ ] Task Summary block at top with AC checklist + last-updated timestamp

If any gate fails, stop and surface to user before delivering.

## Hard Constraints

These are non-negotiable. Pressure-test cases (deadline, "just this once", user insistence) do not relax them.

1. **AC lives in the spec.** Never in the plan. If asked to write AC into a plan, refuse and redirect.
2. **Every claim has a source.** External citation or `[model-inference]` marker. No exceptions.
3. **Frontmatter required fields are required.** Skipping any (id, status, created, linked-effort, ac-count) fails the quality gate.
4. **Spec stays in scope.** Do not re-explore problem space. Do not add implementation steps. Do not bundle multiple features.
5. **Task Summary block stays at the top.** It is state, not content. Other agents will update it; preserve its position and structure.
6. **Revisions are append-only.** Never silently rewrite a committed AC. Add a revision entry, mark the original AC as superseded, write the new AC.

## References

| File | Purpose | Load when |
|------|---------|-----------|
| `references/spec-template.md` | Full output template with all sections | Phase 3 onward |
| `references/frontmatter-schema.md` | Required and optional frontmatter fields, types, examples | Phase 3 |
| `references/task-summary-block.md` | The agent-updated status block format | Phase 3 |
| `references/ac-format.md` | Acceptance criteria writing rules + Given/When/Then optional pattern | Phase 4 |
| `references/source-traceability.md` | Citation format, credibility classes, `[model-inference]` marker | Phase 2, 4, 5 |
| `references/examples/example-spec-simple.md` | Worked example: 3-AC small feature | When stuck on shape |
| `references/examples/example-spec-complex.md` | Worked example: multi-actor, multi-AC, with NFR and revisions | When stuck on complex case |

Load on demand - the SKILL.md body is the entry point and the constraints; depth lives in the references.
