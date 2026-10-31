# Task Summary Block

The Task Summary block is the **state** layer at the top of every spec. It is **not content** - it is a status surface that agents update as work progresses without rewriting the spec body.

## Why This Exists

The user explicitly required this. Without it, specs go stale the day they're committed because there's no place to record:
- Which AC are fulfilled vs pending
- Whether the spec has been revised
- Which questions are still open
- Who/what is currently working on the spec

Recording these in the spec body would mean rewriting the spec - which conflicts with "spec is stable." The Task Summary block solves this by separating state from content.

## Required Position

Immediately after the H1 title and the frontmatter. Before any other content. Always.

```markdown
# Spec: <Feature Title>

## Task Summary
[block content - see structure below]

## Purpose
[content begins here]
```

## Required Structure

```markdown
## Task Summary

**Status:** draft | committed | fulfilled | superseded
**Last updated:** YYYY-MM-DD HH:MM (UTC) by <agent | human>
**Linked plan:** `<path>` | not yet planned
**Open questions:** N (see Open Questions section)
**Revisions:** N (see Revisions section)

### Acceptance Criteria Fulfillment

- [ ] **AC-1** - <one-line restatement>
- [ ] **AC-2** - <one-line restatement>
- [x] **AC-3** - <one-line restatement> · fulfilled <date> by <commit / PR / verifier>
- [ ] **AC-4** - <one-line restatement>

### Currently In Progress

- AC-1: <agent or person> - started <date>

(Or: "None.")
```

## Field Definitions

| Field | Updated By | When |
|-------|-----------|------|
| `Status` | `/plab-spec`, then any agent on transition | Phase 6 of skill (creates as `draft`); review process promotes |
| `Last updated` | Whichever agent makes the most recent change | Every edit |
| `Linked plan` | the implementation plan's path when it ships | At plan creation |
| `Open questions` | Any agent revising the spec | When count changes |
| `Revisions` | Any agent appending to Revisions section | When a revision is logged |
| AC Fulfillment list | Whichever agent verifies an AC | When AC verified - typically at PR merge or test pass |
| Currently In Progress | Whichever agent claims an AC | At start of work; cleared on completion |

## Update Rules (For Any Agent Working With Specs)

1. **Always update `Last updated`** when changing anything else in the block.
2. **Tick AC checkboxes only with evidence.** Append a fulfillment marker: `· fulfilled <date> by <commit-hash | PR-#nnn | test-suite-name>`. No bare ticks.
3. **Match counts to reality.** If you add to Open Questions section, update the count. If you remove a question, decrement.
4. **Never delete history.** "Currently In Progress" entries that complete move to AC fulfillment, not deletion.
5. **Block stays at the top.** Do not reorder it below other sections, even when the spec body grows.

## Pressure Tests (the block survives these)

| Pressure | What the rule says |
|----------|--------------------|
| "It's just a tiny spec, skip the block" | Block is required even for 1-AC specs. The block IS the contract that this is a spec, not an effort brief. |
| "I'll update the block later" | The block is updated in the same edit as the body content it describes. Otherwise it lies. |
| "AC fulfillment is implicit from the PR" | Implicit fulfillment doesn't survive context switches. Tick the box; cite the PR. |

## Example: Mid-Implementation State

```markdown
## Task Summary

**Status:** committed
**Last updated:** 2026-04-20 14:30 (UTC) by codex
**Linked plan:** `docs/internal/release-plans/plan_03_peer-review/S-04_ai-review/implementation-plan.md`
**Open questions:** 2 (see Open Questions section)
**Revisions:** 1 (see Revisions section)

### Acceptance Criteria Fulfillment

- [x] **AC-1** - Skill produces frontmatter with all required fields · fulfilled 2026-04-19 by PR #42
- [x] **AC-2** - Source citations appear inline · fulfilled 2026-04-19 by PR #42
- [ ] **AC-3** - Spec rejects requests to add implementation steps
- [ ] **AC-4** - Pressure test cases pass (5 of 5)
- [ ] **AC-5** - Quality gate runs at end of pipeline
- [ ] **AC-6** - Output validates against frontmatter-schema.md
- [ ] **AC-7** - Documentation has 1 simple + 1 complex example

### Currently In Progress

- AC-3: claude-opus-4.6 - started 2026-04-20
```

## What This Block Is NOT

- Not a changelog (that's the Revisions section)
- Not a discussion thread (that's PR comments / GH issue)
- Not a place for prose updates ("we decided to…") - those go in Revisions
- Not a place for design notes - those go in the spec body or a linked decisions/ADR

The block is **state**. Compact. Scannable. Truth.
