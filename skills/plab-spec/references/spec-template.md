# Spec Template

The full structural contract for the output `spec.md`, written inside the effort's folder `<id>_<slug>/`. Sections appear in this order. None are optional - empty sections include a one-line "N/A - <reason>".

```markdown
---
id: <S-NN | F-NN | etc.>
title: <Feature Title>
type: spec
status: draft
created: YYYY-MM-DD
updated: YYYY-MM-DD
linked-effort: <tracked path, or a plain-language description of the source>
linked-plan: null
linked-strategy-brief: <path | omit>
gh-issue: <n | omit>
ac-count: <n>
source-count: <n>
requires-human-review: <true | false>
target-release: <vX.Y.Z | omit>
priority: <P1 | P2 | P3 | omit>
---

# Spec: <Feature Title>

## Task Summary

**Status:** draft
**Last updated:** YYYY-MM-DD HH:MM (UTC) by plab-spec
**Linked plan:** not yet planned
**Open questions:** <n>
**Revisions:** 0

### Acceptance Criteria Fulfillment

- [ ] **AC-1** - <one-line restatement>
- [ ] **AC-2** - <one-line restatement>
- [ ] **AC-3** - <one-line restatement>

### Currently In Progress

None.

---

## Purpose

<2-4 sentences. What this feature does and why it exists. Cite the
strategy-brief or issue that justified building this. NO problem-space
re-exploration - that's strategy-brief territory.>

Source: [S1] (linked strategy-brief), or [model-inference] if no source.

## Scope

### In Scope

- <Specific behavior 1>
- <Specific behavior 2>
- <Specific user/actor 1>
- <Specific output / artifact>

### Non-Goals

- <Behavior explicitly NOT included>
- <Adjacent feature this spec deliberately doesn't cover>
- <Future enhancement this spec is not the time for>

Non-goals are as load-bearing as in-scope items. Be specific.

## Users / Actors

| Actor | Role | Interaction |
|-------|------|-------------|
| <e.g., end user> | <e.g., consumer of the feature> | <e.g., invokes via CLI> |
| <e.g., agent> | <e.g., downstream consumer> | <e.g., parses the output> |

For single-actor features, one row is fine. For multi-actor, list each.

## Requirements

Numbered, prose-grouped requirements. Each requirement must trace to a
source. Use `[Sn]` inline citations.

1. <Requirement statement.> [S1]
2. <Requirement statement.> [S2, S3]
3. <Requirement statement.> [model-inference]

Group by theme if many requirements (3-4 themes max).

## Acceptance Criteria

The load-bearing section. Each AC must be:

- Numbered (AC-1, AC-2, ...)
- One observable outcome
- Testable (a future agent can verify it)
- Cited (`[Sn]` or `[model-inference]`)

```
AC-1: <Outcome.> [S1]

AC-2: <Outcome.> [S2]
  Given: <precondition>
  When: <action>
  Then: <observable result>

AC-3: <Outcome.> [model-inference]
```

The Given/When/Then form is optional but useful for behavior-heavy AC.

See `references/ac-format.md` for the full AC writing rules.

## Behavior / Examples

Concrete walk-throughs for non-trivial AC. Include only when prose AC
needs grounding. Skip if AC are self-evident.

### Example 1: <Scenario name>

<Walkthrough - input, processing, output. Reference the AC it grounds.>

## Non-Functional Requirements

Only list constraints that are actually constrained. Skip categories
that don't apply rather than inventing aspirational ones.

| Category | Requirement | Source |
|----------|-------------|--------|
| Performance | <e.g., response under 200ms for inputs < 10kb> | [S1] |
| Security | <e.g., no secrets in logs even at debug level> | [S2] |
| Accessibility | <if applicable> | <source> |
| Observability | <if applicable> | <source> |

If this section ends up empty, write "N/A - feature has no NFR
constraints beyond the project defaults."

## Revisions

Append-only. Never silently rewrite a committed AC. To change an AC,
mark the original as superseded and add the new one.

| Date | Author | Type | Description |
|------|--------|------|-------------|
| YYYY-MM-DD | <agent / person> | added | Initial draft created |

Types: `added`, `superseded` (mark previous AC), `clarified` (no
behavior change, wording only), `closed` (status transition).

## Sources & Evidence

Numbered list matching the inline `[Sn]` citations.

- **[S1]** <Source title or description> - `<path or URL>` - class A | B | C
- **[S2]** <Source title or description> - `<path or URL>` - class A | B | C
- **[S3]** <Source title or description> - `<path or URL>` - class A | B | C

### Unverified Claims

If any requirement or AC carries `[model-inference]`, list it here:

- "<verbatim claim text>" - appears in <section>

If none, write "None."

### Credibility Classes (reminder)

- **A** - Authoritative (project docs, RFCs, formal specs)
- **B** - Credible secondary (maintainer blog, expert talk, well-cited issue)
- **C** - Community / informal (Stack Overflow, tutorials)

See `references/source-traceability.md` for full rules.

## Open Questions / Decisions

Outstanding decisions or unknowns that affect the implementation but don't block writing the spec. Uses the decisions-section standard (see `references/decisions-section.md`). If none, write "None at this time." Update the `Open questions: <n>` count in Task Summary when this section changes.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | <short handle> | (none) | Open | (none) |

### D1: <Title> (Open)

**Summary.** One-line restatement of the question.

**Context.** Why this is open, the background, why it matters.

**Desired outcome.** What good looks like, independent of which option wins.

**Options / approaches.**

* **Option A:** <description + key trade-off>
* **Option B:** <description + key trade-off>

**Recommendation.** <Pick + 1 to 3 sentence rationale.>

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
```

---

## Notes on the Template

- The frontmatter is canonical. `/plab-release-plan` parses it; downstream tools depend on the field names exactly as listed.
- The Task Summary block is **always at the top** and **always has the same shape**. Other agents update it; the structure must be predictable.
- Sections are in **dependency order**: Purpose justifies Scope; Scope frames Requirements; Requirements ground AC; AC drive Behavior examples; Behavior surfaces NFR; NFR + AC + Behavior produce Sources; Sources expose Open Questions.
- Empty sections include `N/A - <reason>`. Omitting a heading breaks downstream parsers.

## When to Deviate

You don't. The template is the contract. If a real need exists for an extra section, propose it in `docs/internal/ideas/` for the next version.
