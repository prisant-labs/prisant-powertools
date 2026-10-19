# Architecture Decision Records

This directory tracks architectural decisions for prisant-powertools using the [MADR v4](https://github.com/adr/madr) (Markdown Architectural Decision Records) format.

## What Goes Here

One numbered markdown file per decision: `nnnn-title-in-kebab-case.md` (e.g., `0001-initial-setup.md`, `0002-use-postgres-over-mysql.md`).

**Create an ADR when:**

- A decision affects project architecture, structure, or conventions
- Multiple alternatives were considered
- A future reader (human or AI agent) would ask "why was this done this way?"
- The decision is hard to reverse

**Don't create an ADR for:**

- Implementation details (variable names, minor refactors)
- Trivially reversible choices
- Personal preferences with no structural impact

## Expected Behavior

### For human contributors

Before making a significant architectural change, write a `proposed` ADR describing the options and preferred outcome. Move it to `accepted` once the decision lands.

### For AI agents (claude, codex, and others)

You are expected to read this directory before making architectural changes and to create ADRs when you make architectural decisions yourselves. Use `decision-makers: [claude]` or `decision-makers: [codex]` in the frontmatter.

**Important:** If you see a pattern in the code that looks wrong or non-standard, check this directory first. The most valuable ADRs are the ones that document intentional choices that look incorrect to an outsider - without them, you may "correct" a deliberate decision and undo work.

## Format

Use the MADR v4 template. Required sections:

1. **Title** - short, captures problem + solution
2. **Context and Problem Statement**
3. **Considered Options**
4. **Decision Outcome** - chosen option + justification

Optional sections: Decision Drivers, Consequences, Confirmation, Pros and Cons of the Options, More Information.

### Optional YAML frontmatter

```yaml
---
status: "proposed | accepted | rejected | deprecated | superseded by ADR-0123"
date: YYYY-MM-DD
decision-makers: [jp, claude]
consulted: []
informed: []
---
```

## Lifecycle

```
proposed -> accepted -> [deprecated | superseded by ADR-NNNN]
proposed -> rejected
```

Once an ADR is `accepted`, treat it as immutable history. New circumstances get a new ADR that supersedes the old one - don't rewrite the original.

## Outcomes This Directory Enables

- **Traceability:** every non-trivial architectural choice has a "why" that survives turnover
- **Coherence across agents:** Claude and Codex read the same directory and respect the same decisions
- **Safe refactoring:** future work can check this directory before "correcting" intentional patterns
- **Audit trail:** the decision history is git-tracked, reviewable, and cross-referenceable

## References

- MADR v4 standard: https://github.com/adr/madr
- ADR hub: https://adr.github.io/
