# Plugin-Level Shared References

Markdown reference content shared across multiple skills in this plugin. Skills in `skills/plab-*/` reference these files via relative path (e.g., `../../references/diagrams.md`).

This folder is a **plugin utility**, not a skill.

## Contents

| File | Purpose | Consumers |
|------|---------|-----------|
| `diagrams.md` | Mermaid diagram authoring guidance: when to use a diagram, which type fits which need, syntax validity rules, quality checklist | `plab-guide`, `plab-strategy-brief` |
| `decisions-section.md` | Shared decisions-section format: the seven statuses, the three surfaces a write-back may touch, and the `Follow-up` line | `plab-spec`, `plab-strategy-brief`, `plab-resolve-open-items`, `plab-release-plan` |

## When to add a file here

Add a shared reference when:

- 2 or more skills need the same authoring/decision content
- The content is supporting infrastructure, not a workflow entry point
- A user wouldn't invoke this directly (otherwise promote to a skill)

If only one skill consumes a reference, keep it under that skill's `references/`.

## When to promote a utility to a skill

Promote when:

- Users want to invoke the content directly (e.g., "help me build a flowchart")
- The content has substantial decision-making depth that benefits from skill-style discoverability
- Eval-driven trigger optimization is worth the overhead

The utility pattern is a starting point; promotion is a one-way ratchet that's cheap when the use case justifies it.
