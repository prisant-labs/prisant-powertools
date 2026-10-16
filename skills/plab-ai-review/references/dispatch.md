# Dispatch: the transport contract for `--dispatch` and `--collect`

A-02 (programmatic review dispatch) lets `--review` hand the generated request document to Codex as a background job instead of the maintainer pasting it by hand, and lets `--collect` fetch the findings back later. This file is the contract: what runs, in what order, and what each outcome means. The mechanics live in `scripts/dispatch.py`; this file is read by the agent running the skill, not by that script.

## What `--dispatch` runs

```
python <this skill's base directory>/scripts/dispatch.py submit <review-request.md>
```

`dispatch.py` discovers the highest installed version of `codex-companion.mjs` under `~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs`. If none exists, dispatch is unavailable on this machine and the script reports `state: "unavailable"` without touching the document - this is the portability fallback the spec's Non-Functional Requirements name: the skill stays usable with no Codex CLI installed, because the manual path is never removed.

When a companion is found, `dispatch.py` builds a prompt (the full review request document, plus an instruction asking for a small JSON object of findings - see "Why JSON, not markdown" below) and writes it to a temporary file, then invokes:

```
node <companion> task --background --json --effort high --prompt-file <tmpfile> --cwd <resolved workspace root>
```

`--prompt-file` is used rather than passing the document as a positional argument because a review request can be long, and Windows command lines cap near 32,000 characters; a document near or over that limit would silently truncate or fail to launch at all as a positional argument. `--effort high` and no `--model` follow spec decision D3: effort is a model-independent dial that does not age the way a hard-coded model name would, and this repository's own routing policy reserves depth for judgment work, which a review is.

The job id (`jobId` in the companion's `--json` output) is written into the review document's own frontmatter **only after it is in hand** - a submission that fails leaves the document exactly as `--review` wrote it, with no frontmatter block at all:

```yaml
---
type: review
dispatch-job: task-mvaign5s-0pq15s
---
```

`type: review` is required alongside `dispatch-job` because `scripts/frontmatter-check.py` flags any frontmatter block whose `type` names no known schema; `docs/internal/schemas/review.schema.json` is what recognizes it. This is the one frontmatter field spec decision D2 allows, plus the type tag every other document in this repository's frontmatter-checked tree already carries.

## What `--collect` runs

```
python <this skill's base directory>/scripts/dispatch.py collect <review-request.md>
```

`dispatch.py` reads `dispatch-job` back out of the document's own frontmatter - the maintainer is never asked to supply it (AC-9) - then calls:

```
node <companion> result <dispatch-job> --json --cwd <resolved workspace root>
```

with `CODEX_COMPANION_SESSION_ID` explicitly unset for this one call (see "The session-id variable" below).

## Why submit and collect must run from the same workspace root

`codex-companion.mjs` keys its job store by **workspace root**, not by the literal directory a command happened to run from. `scripts/lib/workspace.mjs`'s `resolveWorkspaceRoot(cwd)` resolves to `git rev-parse --show-toplevel` run from `cwd` when that directory is inside a git repository, and falls back to the literal `cwd` otherwise. `dispatch.py`'s `resolve_cwd()` reproduces exactly this from the review document's own path and passes the result as `--cwd` on both `submit` and `collect`, so the two calls agree on a workspace root without either one needing to be told one.

**Re-verified directly, 2026-10-15 (this effort), inside this repository's own worktree:**

- `git rev-parse --show-toplevel` run from the worktree root and from a subdirectory three levels deep (`skills/plab-ai-review/`) returned the identical path. Inside a git repository, subdirectory does not matter.
- A job submitted with `--cwd` set to this worktree was found by an explicit-id `result <id> --json` call run from any subdirectory of the same worktree, but returned `No job found for "<id>"` when the same call was run from `/e/tmp`, an unrelated directory outside this repository entirely - even though the job id itself was given explicitly and correctly.

**The practical rule this produces: a review document must not change which repository (or, outside of any repository, which literal directory) it lives in between `submit` and `collect`.** Moving a dispatched review document to a different clone, or collecting from a shell whose current directory is outside the repository in a way that resolves to a different git toplevel, breaks the lookup. Nothing about an ordinary session boundary breaks it: a later Claude Code session invoked against the same repository resolves to the same workspace root regardless of which subdirectory it happens to start in.

## The session-id variable: what is re-verified, and what is not

`codex-companion.mjs` sets `CODEX_COMPANION_SESSION_ID` in Claude Code sessions to the Claude session id, and stamps it onto every job a session creates (`scripts/lib/tracked-jobs.mjs`).

`dispatch.py`'s `collect` subcommand unsets this variable before calling `result`, defensively. Re-verified directly, 2026-10-15, against companion version 1.0.6: an explicit-id `result <id> --json` lookup succeeded identically whether the variable was unset, set to the submitting session's own id, or set to an unrelated, foreign session id. Reading `scripts/lib/job-control.mjs` confirms why: `resolveResultJob` applies its session filter only when **no** job id is given (`reference ? listJobs(...) : filterJobsForCurrentSession(...)`), and `buildSingleJobSnapshot`, which backs the explicit-id `status` path, never filters at all. The original Phase 1 canary recorded in this effort's implementation plan (2026-09-12) shows the identical result. **Unsetting the variable is not load-bearing against this companion version** - the per-directory rule above is what actually matters - and it is kept anyway because it is free (a lookup creates no job record to pollute) and protects against a future companion version that does filter explicit lookups.

This is a correction to an earlier pass of this effort's own re-verification, done the same day, which reported that a foreign session id made the lookup fail. That result could not be reproduced on independent re-verification and is not consistent with the source above or with the original Phase 1 canary; it is best explained as a workspace-root mix-up (per-directory, not per-session) during that earlier pass rather than as real companion behavior. The per-directory rule is the one to design against.

## Why JSON, not markdown, is asked of the reviewer

`task` has no `--output-schema` path (that belongs to `review`/`adversarial-review` only), so dispatch cannot constrain Codex's output format at the transport level the way a structured review command could. Asking Codex to return the entire filled-in document verbatim would require trusting a live model to reproduce every section it was *not* asked to touch - Requestor Analysis, Decisions, Proposed Actions - byte-for-byte, which is exactly the kind of silent drift AC-6 (same document shape as the manual path) exists to prevent.

Instead, the submit prompt asks for one small JSON object: an overall assessment, a severity-count object, and one `{dimension, finding}` pair per review dimension, using the dimension's exact heading text as it already appears in the document. `collect` then splices this into the existing document deterministically - it never trusts the model to reproduce structure, only to answer the content asked of it. If the dimensions Codex answered do not exactly match the dimensions the document has (missing one, inventing one, renaming one), that is the `unparseable` state: nothing is written, and the raw output is saved to a sidecar file next to the document for the maintainer to read.

## The three (five) reported states

Both `submit` and `collect` print one JSON object with a `state` field and exit 0 only on success; every other state is a definite report, never a crash and never silence:

| `state` | Meaning | Document effect |
|---|---|---|
| `submitted` | (submit only) Job accepted, id in hand | `dispatch-job` frontmatter written |
| `collected` | (collect only) Findings parsed and spliced in | Reviewer placeholders filled |
| `running` | (collect only) Job not finished yet | Untouched |
| `failed` | Reviewer unreachable, job failed, or (collect) no `dispatch-job` field at all | Untouched |
| `unavailable` | No `codex-companion.mjs` installed | Untouched (submit); job id preserved (collect) |
| `unparseable` | (collect only) Output did not parse as the expected findings, or answered the wrong dimensions | Untouched; raw output saved to `<doc>.dispatch-raw-<job-id>.txt` |

A document with empty placeholders and a reported `failed`/`unavailable`/`unparseable` state is always recoverable by the manual paste path from `--review` step 6. A document that silently looked like a completed, empty review would not be - this table, and the all-or-nothing matching in `splice_findings()`, is how that is ruled out (AC-5).

## The `--collect` flag's name is an open decision

Whether the collection command should be named `--collect`, something else, or not be its own flag at all was not specified by A-02's spec or implementation plan; the plan said only to "add the collection path." This file and `SKILL.md` were written using `--collect` as a working default. See the spec's Open Questions / Decisions table and its "D5" subsection for the recorded choice, its reasoning, and how to change it.
