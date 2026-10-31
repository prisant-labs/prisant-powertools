# Source Traceability

Every non-obvious claim in a spec must trace to a source - or be marked as model inference. This is a hard constraint, not a preference.

## Why

A requirement without a source is a guess. Six months from now, a teammate (or you) will ask "who decided X?" The spec is the answer surface. Without traceability, the only answer is "an LLM said so."

## The Two Citation Forms

### Form 1: External source

```
This requirement comes from a real source. [S1]
This is supported by two sources. [S1, S3]
```

`[S1]` is shorthand for the entry in the Sources & Evidence section:

```
- **[S1]** Strategy brief - `supporting/strategy-brief.md` in the effort folder - class A
```

### Form 2: Model inference

When no external source exists - the requirement is a judgment call you (or the LLM) made:

```
The skill should default to dry-run for safety. [model-inference]
```

**Two consequences when `[model-inference]` is used:**

1. The frontmatter `requires-human-review:` field is set to `true`
2. The verbatim claim is listed in the Sources & Evidence section's Unverified Claims subsection

This makes inference visible, reviewable, and findable. It is NOT a way to skip sourcing - it is a way to mark sourcing's absence honestly.

## Source Hierarchy (Where to Look First)

In order of preference for a given requirement:

| Priority | Source type | Example path |
|----------|-------------|--------------------------|
| 1 | Linked strategy-brief | the path in `linked-strategy-brief`, such as `<effort folder>/supporting/strategy-brief.md` |
| 2 | The effort's source (the linked-effort itself) | the tracked path or the description in `linked-effort` |
| 3 | Linked GitHub issue | resolve `gh-issue:` in effort frontmatter |
| 4 | ADR / decision record | `docs/internal/decisions/NNNN-*.md` |
| 5 | Prior spec (if revising) | `<effort folder>/spec.md` previous content |
| 6 | Authoritative external doc | RFC, official docs, signed-off design |
| 7 | Maintainer or expert blog | named author, well-cited |
| 8 | Community reference | Stack Overflow, tutorials |
| 9 | Model knowledge | mark as `[model-inference]` |

Higher priority = stronger source. A requirement cited from priority 1-4 needs no further explanation. Priorities 6-8 should include why the source is authoritative for this claim.

## Credibility Classes

Each entry in Sources & Evidence carries a class:

| Class | Definition | Examples |
|-------|------------|----------|
| **A** | Authoritative - project's own docs, RFCs, formal specs, signed-off design decisions | Strategy brief, ADR, RFC, official API docs |
| **B** | Credible secondary - named maintainer or recognized expert | Maintainer blog post, conference talk by core team, well-cited GitHub issue |
| **C** | Community informal - useful but not authoritative | Stack Overflow answer, tutorial blog, third-party guide |

A spec built primarily on class C sources should set `requires-human-review: true` even if no claims are `[model-inference]`. Community sources can be wrong; reviewer needs to verify.

## Citation Placement

### Inline citations

Place the `[Sn]` marker at the **end of the sentence or clause it supports**, before terminal punctuation:

```
The CLI must accept --dry-run as a top-level flag [S1].
```

For multi-source claims:

```
Both the strategy brief and the issue agree that defaults should be conservative [S1, S3].
```

### AC citations

Each AC has a citation at the end:

```
AC-3: Skill rejects input missing required fields. [S1]
```

Multi-source AC:

```
AC-4: Behavior matches the precedent set by plab-init-project. [S2, S5]
```

### Section-level citations

For a paragraph where every sentence draws from one source, cite at the start once:

```
Per [S1]: the skill must support both interactive and batch modes. The interactive mode prompts for missing inputs. The batch mode requires all inputs upfront and exits non-zero if any are missing.
```

Don't repeat `[S1]` on every sentence in such cases.

## What Doesn't Need a Citation

Common-knowledge and self-evident statements don't need citations:

- "Markdown supports tables via pipe syntax."
- "YAML frontmatter is delimited by `---` lines."
- "The skill is invoked via the `/plab-spec` command."

Use judgment. The test: would a reviewer ask "where did this come from?" If yes, cite or mark.

## The Sources & Evidence Section

```markdown
## Sources & Evidence

- **[S1]** Strategy brief: plab-spec discovery - `supporting/strategy-brief.md` in the effort folder - class A
- **[S2]** Effort request - the source named in `linked-effort` - class A
- **[S3]** GitHub issue #15 - `https://github.com/<org>/<repo>/issues/15` - class A
- **[S4]** Sibling-plugin skill `deliver-prd` - `<other-plugin>/skills/deliver-prd/SKILL.md` - class B (precedent for AC format)

### Unverified Claims

The following claims appear in this spec without an external source. They reflect model inference and warrant human review:

- "Default mode should be dry-run for safety" - appears in §Requirements
- "Pressure tests should include user-insistence cases" - appears in §AC-7

### Gaps

Areas adjacent to this spec that no source covers - flagged for future research:

- How specs interact with the `add-effort` skill once it ships (no spec yet)
- Whether release-plan should auto-bump status from `committed` to `fulfilled` (deferred)
```

## Validation Rules

- Every `[Sn]` in the body has a matching entry in Sources & Evidence
- Every Sources & Evidence entry is referenced at least once in the body (no orphan sources)
- `source-count` in frontmatter matches the number of `[S]` entries listed
- If any `[model-inference]` appears in the body, frontmatter `requires-human-review: true` AND Unverified Claims subsection lists it verbatim
- Class A sources should outnumber Class C sources (rough heuristic; not blocking)

## Pressure Tests

| Pressure | What the rule says |
|----------|--------------------|
| "Skip Sources, tight deadline" | Refuse. Sourcing is a hard constraint. |
| "I'll add sources later" | The spec is not ready to commit until sources are in place. Status stays `draft`. |
| "It's just my opinion, no source" | Use `[model-inference]` and set `requires-human-review`. Honest absence is fine; fake citation is not. |
| "Cite the strategy-brief generally instead of specific sentences" | Generic citation hides which AC came from which source. Cite per-claim. |

The integrity of the spec - and of every plan and release that depends on it - rests on this.
