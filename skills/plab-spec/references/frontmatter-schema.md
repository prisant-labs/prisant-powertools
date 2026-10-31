# Frontmatter Schema

The spec's YAML frontmatter is its machine-readable contract with downstream readers: `/plab-release-plan`, which parses it to build a release's aggregation table, and whoever writes the `implementation-plan.md` that sits beside it.

## Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Effort id this spec belongs to. Must match the effort brief. | `S-04` |
| `title` | string | Short, declarative title of the feature. Same string as the effort title or refined. | `Cross-LLM peer review skill` |
| `type` | const | Always `spec`. Distinguishes from plan, brief, etc. | `spec` |
| `status` | enum | One of: `draft`, `committed`, `fulfilled`, `superseded`. | `draft` |
| `created` | ISO date | When this spec file was first written. | `2026-04-14` |
| `updated` | ISO date | Last substantive edit. | `2026-04-14` |
| `linked-effort` | string | What the spec grew out of. **A tracked path when the source is committed; otherwise a plain-language description of the source, never a path into a gitignored directory.** A tracked artifact must not cite an untracked one: the link resolves for nobody who clones the repository, including the author on another machine. When the source is private, summarize its substance into the Sources and Evidence section and name it here descriptively. | `docs/internal/ideas/peer-review-request.md` or `the maintainer's private defect record, 2026-08-18` |
| `ac-count` | integer | Number of acceptance criteria in this spec. Must match actual count. | `7` |

## Optional Fields

| Field | Type | When to use | Example |
|-------|------|-------------|---------|
| `linked-plan` | path \| null | Path to the implementation plan, once it exists. `null` until then. Resolved relative to this file, then to the repo root. | `implementation-plan.md` |
| `linked-release` | path \| null | Path to the release plan this effort is scoped into. `null` while the effort sits in `_unassigned/`. | `docs/internal/release-plans/plan_07_aggregation/plan.md` |
| `linked-strategy-brief` | path | Path to upstream strategy-brief, if one exists. | `supporting/strategy-brief.md` |
| `gh-issue` | integer | GitHub issue number if one tracks this work. | `15` |
| `source-count` | integer | Number of distinct external sources cited in Sources & Evidence. Must match actual count. | `4` |
| `requires-human-review` | boolean | `true` when spec contains `[model-inference]` markers without backing source. Signals reviewers. | `true` |
| `spec-dependencies` | list of strings | Other spec ids this depends on. | `[S-02, S-07]` |
| `target-release` | string | Target release version, if known. | `v1.2.0` |
| `priority` | enum | `P1`, `P2`, `P3`. Inherits from effort if absent. | `P2` |
| `superseded-by` | string | Effort id of the spec that replaces this one. Required when `status` is `superseded`. | `D-12` |
| `supersedes` | string | Effort id of the spec this one replaces. **Write both halves.** The superseded spec carries `superseded-by`, and the replacing spec carries `supersedes` pointing back. | `D-11` |

## Status Lifecycle

```
draft → committed → fulfilled
                 ↘ superseded
```

| Status | Meaning | Who sets it |
|--------|---------|-------------|
| `draft` | Just written or actively being revised. | Skill on creation |
| `committed` | Reviewed and frozen. AC are now contract. | Human review |
| `fulfilled` | All AC verified as met. | Closing the effort |
| `superseded` | Replaced by a newer spec or no longer applicable. Add `superseded-by:` with the replacing id, and add `supersedes:` on that replacing spec pointing back. | Manual |

The skill creates specs in `draft`. Promotion to `committed` is a human (or human-confirmed) action - never automatic.

## Validation Rules

- `id` matches `^[A-Z]{1,2}-\d{2,4}$` (matches the project's effort-id format)
- `type` is always `spec` - required for downstream parsers to identify
- `status` must be one of the enum values; no free-form
- `ac-count` must equal the actual number of `AC-N:` entries in the body
- `source-count` (if present) must equal the number of `[S<n>]` entries listed in Sources & Evidence
- If `requires-human-review: true`, body MUST contain at least one `[model-inference]` marker
- All `linked-*` paths must exist on disk at write time, OR be explicit `null`
- **Supersession is symmetric.** If a spec declares `superseded-by: X`, the spec with id `X` must exist and must declare `supersedes:` pointing back, and the converse. A one-directional supersession is the defect this rule exists to catch: it hides the relationship from whichever end you happen to open first. `scripts/doc-lifecycle-check.py` enforces this across files, which is something a per-file schema cannot do.

## Full Example

```yaml
---
id: S-04
title: Cross-LLM peer review skill
type: spec
status: draft
created: 2026-04-14
updated: 2026-04-14
linked-effort: "the maintainer's request of 2026-04-05"   # or a tracked path when the source is committed
linked-plan: null
linked-strategy-brief: supporting/strategy-brief.md
gh-issue: 15
ac-count: 7
source-count: 4
requires-human-review: false
target-release: v1.2.0
priority: P2
---
```

## Why This Schema

- **Machine parseable**: `/plab-release-plan` reads `title` + `status` to build a release's aggregation table
- **Lifecycle observable**: `status` lets release tools find committed-but-not-fulfilled specs
- **Audit traceable**: `source-count` + `requires-human-review` flag specs that lean on model inference
- **Dependency aware**: `spec-dependencies` lets release planning detect cross-spec coupling

Do not invent fields. If a need arises that this schema doesn't cover, propose an extension in `docs/internal/ideas/` rather than ad-hoc adding it.
