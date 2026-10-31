# Example: Simple Spec (3 AC)

Demonstrates the template applied to a small, single-actor feature with one source. Use this when you're stuck on shape for a small spec.

---

```markdown
---
id: I-04
title: validate-script-docs CI script
type: spec
status: draft
created: 2026-04-15
updated: 2026-04-15
linked-effort: "a CI gap found while reviewing script documentation"
linked-plan: null
ac-count: 3
source-count: 1
requires-human-review: false
priority: P3
---

# Spec: validate-script-docs CI script

## Task Summary

**Status:** draft
**Last updated:** 2026-04-15 09:00 (UTC) by plab-spec
**Linked plan:** not yet planned
**Open questions:** 0
**Revisions:** 0

### Acceptance Criteria Fulfillment

- [ ] **AC-1** - Script lists all `.sh` files in scripts/ and confirms each has a matching `.md`
- [ ] **AC-2** - Script exits 0 with summary message when all docs present
- [ ] **AC-3** - Script exits non-zero with specific error per missing doc

### Currently In Progress

None.

---

## Purpose

Add a CI check that enforces the convention "every script in `scripts/` has a companion `<name>.md`." Without this check, the convention drifts and `README_SCRIPTS.md` becomes stale. [S1]

## Scope

### In Scope

- Read all `*.sh` files in `scripts/`
- For each, check that `<name>.md` exists in the same directory
- Print pass/fail per file
- Return appropriate exit code

### Non-Goals

- Validate the *content* of the companion `.md` (separate concern)
- Update `README_SCRIPTS.md` automatically (separate skill)
- Handle non-shell scripts (`.py`, `.ps1`) - out of scope for v1
- Run on commit / pre-commit (only on push and PR)

## Users / Actors

| Actor | Role | Interaction |
|-------|------|-------------|
| CI runner | Runs script in GitHub Actions | Invokes `bash scripts/validate-script-docs.sh` |
| Developer | Adds new scripts | Sees CI failure if companion doc missing |

## Requirements

The script must enumerate `*.sh` files in `scripts/`, check for matching `.md`, and report pass/fail per file with non-zero exit on any failure. Output should be readable in CI logs and not require structured parsing. [S1]

## Acceptance Criteria

AC-1: Script lists all `*.sh` files in `scripts/` and confirms a matching `<name>.md` exists in the same directory. [S1]

AC-2: When all docs present, script exits 0 with summary message `PASSED: All scripts have companion docs (<n> checked)`. [S1]
  Given: `scripts/foo.sh` and `scripts/foo.md` both exist
  When: `bash scripts/validate-script-docs.sh` runs
  Then: stdout includes `PASSED: All scripts have companion docs (1 checked)` and exit code is 0

AC-3: When any doc missing, script exits non-zero with one `ERROR: missing companion .md for scripts/<name>.sh` line per missing doc and a final `FAILED: <n> error(s) found` line. [S1]

## Behavior / Examples

### Example 1: Mixed pass/fail

```
$ bash scripts/validate-script-docs.sh
ERROR: missing companion .md for scripts/build.sh
ERROR: missing companion .md for scripts/deploy.sh
FAILED: 2 error(s) found
$ echo $?
1
```

## Non-Functional Requirements

| Category | Requirement | Source |
|----------|-------------|--------|
| Performance | Completes under 1s for typical scripts/ folder (< 50 files) | [model-inference] |
| Portability | Pure bash; no external dependencies beyond standard utilities | [S1] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-04-15 | plab-spec | added | Initial draft created |

## Sources & Evidence

- **[S1]** Effort lifecycle review - `docs/internal/ideas/effort-lifecycle-review.md` - class A (Q5: CI Handling and Script Documentation)

### Unverified Claims

- "Completes under 1s for typical scripts/ folder" - appears in §Non-Functional Requirements

### Gaps

- Whether to also enforce that `README_SCRIPTS.md` was updated in the same commit as a new script - deferred per the source doc.

## Open Questions

None at this time.
```

---

## Notes on This Example

- **Single source (S1).** Small features often need only one. That's fine - class A from a real doc beats five sources of mixed quality.
- **One `[model-inference]`.** The performance NFR is a guess; marked honestly. `requires-human-review` would be set to `true`; this example sets it to `false` because the inference is small and low-risk. In a real spec, set `true` whenever any `[model-inference]` appears.
- **Behavior section is short.** Just one example. Trivial features don't need elaborate walkthroughs.
- **Open Questions is empty.** Sometimes there genuinely aren't open questions. That's fine - write "None at this time." Don't invent questions to fill the section.
- **NFR has only 2 entries.** Most features are constrained on a few axes, not all of them. Skip categories that don't apply rather than padding.

## What Makes This Spec Work

1. AC are testable (you can write a shell test against AC-2 and AC-3 without ambiguity)
2. Non-goals are specific (rules out 4 adjacent things explicitly)
3. Citation is honest (1 real source, 1 marked inference, no padding)
4. Task Summary is at the top with the AC checklist that survives revisions
