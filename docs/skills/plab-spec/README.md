# plab-spec

**Version:** 1.3.3
**Source:** [`skills/plab-spec/`](../../../skills/plab-spec/)

Produce a feature specification: the contract between intent and implementation. Spec defines **what** to build and how the team knows it's done. Distinct from the implementation-plan template in `docs/internal/release-plans/` (how to build) and `/plab-strategy-brief` (explore problem space).

> **v1.1.0 note:** the default output path changed. Specs now live in per-effort folders under `release-plans/_unassigned/` (or directly in a release folder when `--target-release` is passed). The legacy `docs/internal/efforts/<id>/<id>_spec.md` path is no longer the default. That change predates this plugin; prior history remains in the private upstream.

---

## Getting Started

### Quick Start

```
/plab-spec --effort S-11
```

This reads effort `S-11`, walks the 6-phase pipeline, and writes a spec at `docs/internal/release-plans/_unassigned/S-11_<slug>/spec.md` (the slug is auto-derived from the effort title; pass `--slug` to override).

### Common Invocations

```
# Baseline - writes into _unassigned/ until a release is assigned
/plab-spec --effort S-11

# Born directly into a release folder
/plab-spec --effort S-11 --target-release v1.5.0

# Override the auto-derived slug
/plab-spec --effort S-11 --slug my-feature

# Seed from an upstream strategy brief
/plab-spec --effort S-11 --from-brief docs/internal/.../<id>_strategy-brief.md

# Preview without writing
/plab-spec --effort S-11 --dry-run

# Revise an existing spec (append-only to Revisions section)
/plab-spec --effort S-11 --revise
```

### Installation

Install via the prisant-labs marketplace:

```bash
/plugin marketplace add prisant-labs/agent-plugins
/plugin install prisant-powertools@prisant-labs
```

Or symlink into a project:

```bash
ln -s /path/to/prisant-powertools/skills/plab-spec .claude/skills/plab-spec
```

### Invocation

**Auto-discoverable as of 1.3.0.** Through 1.2.1 this skill shipped with `disable-model-invocation: true` and ran only when typed. That flag is gone. It now fires on an explicit request to write a spec or turn requirements into acceptance criteria, and its description carries a do-NOT-fire clause covering the three ways the word "spec" appears without being a request: a passing mention, a question about an existing spec, and a request to implement one.

Typing `/plab-spec` still works and is still the precise way to run it.

---

## When to Use

- A team has decided to build a feature -- the problem space is already explored
- Acceptance criteria need a stable home that survives plan rewrites
- Multiple agents or reviewers will read the requirements and need a parseable contract
- The feature spans more than one session or ships to users
- Audit trail from requirement to source is required

## When NOT to Use

- The problem space hasn't been explored yet -- use `/plab-strategy-brief` first
- You're writing implementation steps -- that's `docs/internal/release-plans/implementation-plan-template.md`
- Bundling completed features for release -- that's `/plab-release-plan`
- The feature is one sentence and one AC -- write it inline in the effort brief
- The skill being spec'd is itself a new skill -- use `/skill-creator` (it has its own discovery/zone flow)

---

## The Skill Chain

```
plab-strategy-brief  ->  plab-spec  ->  implementation-plan.md  ->  [implementation]  ->  plab-release-plan
   (explore)           (commit what)    (commit how)                                 (bundle + ship)
```

Each artifact has a distinct purpose. `plab-spec` produces the middle one: **commit what to build**, with acceptance criteria, source traceability, and links to the related effort and plan.

---

## Output Shape

Every spec includes (in order):

| Section | Purpose |
|---------|---------|
| Frontmatter | Machine-readable metadata -- see [frontmatter-schema.md](../../../skills/plab-spec/references/frontmatter-schema.md) |
| `## Task Summary` | Agent-updated status block -- state, not content. See [task-summary-block.md](../../../skills/plab-spec/references/task-summary-block.md) |
| `## Purpose` | 2-4 sentences; what the feature does and why |
| `## Scope` / `## Non-Goals` | What's in, what's deliberately out |
| `## Users / Actors` | Who interacts, how |
| `## Requirements` | Prose requirements with citations |
| `## Acceptance Criteria` | Numbered AC-1, AC-2, ...; one observable outcome each; cited |
| `## Behavior / Examples` | Walkthroughs for non-trivial AC |
| `## Non-Functional Requirements` | Performance, security, etc. -- only what's actually constrained |
| `## Revisions` | Append-only change log |
| `## Sources & Evidence` | Citations with credibility classes A/B/C |
| `## Open Questions` | Outstanding decisions |

All sections required. Empty sections write `N/A - <reason>` rather than being omitted.

---

## Examples

Canonical worked examples live in the skill's references:

- **[Simple example](../../../skills/plab-spec/references/examples/example-spec-simple.md)** -- 3 AC, 1 source, small CI-script feature. Shows the template applied to a minimal case.
- **[Complex example](../../../skills/plab-spec/references/examples/example-spec-complex.md)** -- 7 AC, 4 sources, multi-actor (plab-ai-review), with mid-implementation Task Summary state and a Revisions entry. Shows the template at full complexity.

A third set of worked artifacts ships in this repository itself: every `spec.md` under `docs/internal/release-plans/` was written to this template. Sixteen of them exist across five planned releases, at a range of sizes.

---

## Key Concepts

**Spec vs implementation-plan vs strategy-brief.** Three distinct artifacts. Spec is the stable contract (what to build). Implementation plan is the dynamic implementation steps (how, who, when). Strategy-brief is the upstream exploration (why, what are the options). An AC change never touches a plan; a phase reorder never touches a spec.

**Task Summary block.** Separates state from content. As implementation progresses, agents update the Task Summary block at the top (AC fulfillment, revision count, open-questions count) without rewriting the spec body. This keeps the spec stable while still reflecting reality.

**Source traceability.** Every requirement and AC cites either an external source `[Sn]` (listed in Sources & Evidence with credibility class A/B/C) or is marked `[model-inference]`. No unsourced claims -- if there's no source, mark it honestly.

**Append-only revisions.** Committed AC are never silently rewritten. To change an AC, mark the original as superseded with a date marker and add a new numbered AC. The Revisions table records the change. Stable AC IDs let plans, tests, and PRs reference the same AC across time.

**Constraint-driven enforcement.** The skill refuses to relax its rules under pressure -- "just skip sources, I'm in a hurry" or "put the AC in the plan, it's simpler" get rejected. The rules exist because the ecosystem (plans, releases, audits) depends on them.

---

## Reference Files

Loaded on demand per SKILL.md's references table:

| File | Purpose | When to Read |
|------|---------|-------------|
| `references/spec-template.md` | Full output template with all sections | Building the output |
| `references/frontmatter-schema.md` | Required + optional frontmatter fields, validation rules | Populating frontmatter |
| `references/task-summary-block.md` | Position, structure, update rules for the status block | Writing or updating the block |
| `references/ac-format.md` | AC writing rules, Given/When/Then pattern, common smells | Writing acceptance criteria |
| `references/source-traceability.md` | Citation format, credibility classes, model-inference marker | Sourcing requirements and AC |
| `references/examples/example-spec-simple.md` | Worked example: 3 AC, small feature | When stuck on shape for a simple case |
| `references/examples/example-spec-complex.md` | Worked example: 7 AC, multi-actor, with revisions | When stuck on shape for a complex case |

---

## Hard Constraints

Non-negotiable. Pressure tests (deadline, "just this once", user insistence) do not relax them:

1. **AC lives in the spec.** Never in the plan. If asked to write AC into a plan, the skill refuses and redirects.
2. **Every claim has a source.** External `[Sn]` citation or `[model-inference]` marker.
3. **Frontmatter required fields are required.** `id`, `title`, `type`, `status`, `created`, `updated`, `linked-effort`, `ac-count`.
4. **Spec stays in scope.** No problem re-exploration, no implementation steps, no feature bundling.
5. **Task Summary at top.** Position is load-bearing -- other agents update it; they expect to find it there.
6. **Revisions are append-only.** Never silently rewrite committed AC.

See [SKILL.md § Hard Constraints](../../../skills/plab-spec/SKILL.md) for the full list with enforcement notes.

---

## Workflow (What Happens When You Invoke)

1. **Intake & scope check** -- resolves `--effort`, size-checks AC count, confirms output doesn't already exist (unless `--revise`)
2. **Locate and gather sources** -- reads effort brief, strategy-brief, linked issue, ADRs
3. **Build frontmatter + Task Summary block** -- writes the top-of-file contract
4. **Write requirements + AC** -- with citations per each; updates Task Summary AC checklist
5. **Add behavior, examples, NFR, revisions, open questions** -- rounds out the spec
6. **Verify quality gates** -- runs 8 structural + source checks before declaring done

Each phase produces verifiable output. If a gate fails in Phase 6, the skill surfaces the failure to the user before writing the final file.

---

## Improvement Ideas

Candidates for future versions (propose them in `docs/internal/ideas/`):

- **v1.1.0**: clearer bias toward `N/A` for empty NFR sections; open-questions count auto-sync; user-session credibility-class guidance
- **v1.2.0**: AC-smell detector with rewrite suggestions; auto-detect "is this better as inline-in-effort?" via size check
- **Future**: spec linter script (structural validation beyond CI frontmatter lint); cross-LLM review (`/plab-ai-review`) of sample outputs
