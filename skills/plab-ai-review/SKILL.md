---
name: plab-ai-review
description: "Run a structured peer review of a document with a second model, then
  synthesize the findings into decisions. Use when you need a second opinion on a plan,
  brief, spec, RFC, or design doc, or when the user says 'review this with codex', 'get a
  second opinion', 'peer review this', or 'close this review'. Three modes: --review
  generates a self-contained review request for another model, or with --dispatch sends it
  to Codex in the background; --respond adds requestor synthesis once findings come back;
  --close archives the pair, applies accepted changes, and writes unresolved decisions to a
  backlog."
argument-hint: "<doc.md> [--reviewer codex|gpt|gemini] [--dispatch] [--respond] [--collect] [--close]"
license: MIT
metadata:
  version: "1.3.0"
  updated: 2026-10-15
---

# AI Review

Generate structured, self-contained review requests for cross-LLM peer review. The reviewer LLM receives a document with everything needed to critique independently - context, targeted questions, severity framework, and response templates. After the reviewer completes findings, add requestor synthesis with inline responses, structured decisions, and proposed actions.

## Modes

### `--review` (Generate Review Request)

```
/plab-ai-review doc.md --reviewer codex [--dispatch]
```

1. Read the source document fully
2. Auto-detect document type (or use `--type`): plan, brief, spec, rfc, doc
3. Select review dimensions from type preset (5-7 sections); confirm with user for `doc` type
4. Generate self-contained review document with:
   - Reviewer Assessment + Requestor Analysis placeholders
   - Structured Decisions placeholder
   - Anti-sycophancy reviewer instructions (see `references/attribution-guide.md`)
   - Source document (embed if < 200 lines, else summarize key claims + reference path)
   - Review sections - each with context line + reviewer/requestor attribution placeholders
   - Proposed Actions placeholder
5. Write to `<basename>_reviewed-by-<reviewer>.md` (same directory as source)
6. **Without `--dispatch`:** tell user to paste into the reviewer LLM, bring back findings, and run `--respond`. This is the default, and is byte-for-byte unchanged from before `--dispatch` existed.
7. **With `--dispatch`:** run `python <this skill's base directory>/scripts/dispatch.py submit <the document just written>`. See `references/dispatch.md` for what the helper does (companion discovery, the submit prompt, the workspace-root rule) and why. Read the single JSON object it prints on stdout:
   - `state: "submitted"` - the job id is already written into the document's `dispatch-job` frontmatter field (the helper does this, not you). Tell the user the job id and that the session is not blocked; findings are collected later with `--collect` (or the no-flag auto-detect), in this session or a later one.
   - `state: "unavailable"` or `state: "failed"` - **do not tell the user dispatch succeeded.** Report exactly what the JSON's `message` says. The document on disk is untouched: no frontmatter was written, every reviewer placeholder is still empty, and the manual paste path from step 6 still works. Tell the user that.

### `--collect` (Collect a Dispatched Review)

```
/plab-ai-review doc_reviewed-by-codex.md --collect
```

The read side of `--dispatch`: fetches a previously-submitted job's findings and fills them into the same placeholders a manual paste would have filled, using only the `dispatch-job` id already sitting in the document's frontmatter. The maintainer is never asked for that id (A-02 AC-9) - this is what makes collection work in a later session, not only the one that submitted it.

1. Run `python <this skill's base directory>/scripts/dispatch.py collect <the document>`.
2. Read the single JSON object it prints on stdout and report its `state` to the user, verbatim where it names what happened:
   - `state: "collected"` - findings are now in the document's Reviewer Assessment and per-dimension placeholders, attributed to Codex with today's date, exactly as a manual paste would have left them. Tell the user `--respond` is next.
   - `state: "running"` - the job has not finished. Tell the user to try `--collect` again later; nothing was written.
   - `state: "failed"` - the reviewer could not be reached, the job itself failed, or there is no `dispatch-job` field to collect at all. Report the `message` verbatim. Placeholders are untouched; the manual paste path still works.
   - `state: "unparseable"` - the job completed, but its output did not parse as the findings this skill expects (wrong shape, or it answered different dimensions than the document has). Report the `message`, which names the sidecar file the raw output was saved to, and tell the user they can read it and complete the review by hand. Placeholders are untouched.
   - `state: "unavailable"` - no `codex-companion.mjs` was found on this machine. The job id stays in the document's frontmatter for a later attempt on a machine where dispatch is available.
3. Never report a dispatched review as collected when `dispatch.py` did not report `state: "collected"`. This is the same three-state discipline `--dispatch` itself follows (A-02 AC-5), applied to the read side.

### `--respond` (Requestor Synthesis)

```
/plab-ai-review doc_reviewed-by-codex.md --respond
```

1. Read the reviewed document with reviewer findings
2. Write **Reviewer Assessment** - summarize reviewer's overall findings, fill severity table
3. Write **Requestor Analysis** - agreement/disagreement, proposed action count
4. Write **inline responses** per section, scaled by severity:
   - Blocker/Major: full paragraph with evidence and proposed change
   - Minor/Note: one-liner ("Agree. [action]." or "Noted. Deferring.")
5. Write **Structured Decisions** - summary table + per-decision sections. **Every Blocker and every Major finding MUST generate a per-decision section.** Minor and Note findings may generate sections when the requestor judges they need human attention.
6. Write **Recommendations** - top 3 most impactful actions
7. Write **Proposed Actions** table - consolidated Update/Defer rows

### `--close` (Post-Review Lifecycle Automation)

```
/plab-ai-review doc_reviewed-by-<reviewer>.md --close [--backlog path/to/backlog.md]
```

Automates the post-review lifecycle documented in `references/file-lifecycle.md` Step 5:

1. Copy `doc.md` → `_archive/doc_original.md`. Creates `_archive/` if missing.
2. Apply changes from the reviewed-by document back into `doc.md`. **The Proposed Actions table is the source of truth** - every row where `Action = Update` gets applied. Pre-flight check: if any decision has `Status = Rejected` or `Deferred` while its triggered Proposed Actions row is still `Update`, the confirmation prompt flags the divergence (warn-not-block).
3. Move `doc_reviewed-by-<reviewer>.md` → `_archive/doc_original_reviewed-by-<reviewer>.md`.
4. Append unresolved items (Status ∈ Open / Deferred / Needs info) to the file at `--backlog` using `references/backlog-entry-format.md`. Accepted and Rejected decisions are closed - they stay in the archive and are not written to the backlog.

**Before any file operation, print this summary and require `y` confirmation:**

```
--close will:
  - Archive source:  doc.md → _archive/doc_original.md
  - Apply N accepted changes to doc.md
  - Archive review:  doc_reviewed-by-<reviewer>.md → _archive/doc_original_reviewed-by-<reviewer>.md
  - Append M unresolved items to path/to/backlog.md

Proceed? (y/n)
```

If the pre-flight check found rows flagged for decision/action divergence, list them under the "Apply N accepted changes" line so JP sees them before confirming.

**`--backlog <path>` flag:**

- Required when the review has at least one unresolved decision (Status ∈ Open / Deferred / Needs info). Missing flag → skill errors out before any file operation.
- Optional when there are zero unresolved items; silently ignored if provided anyway.
- If `<path>` does not exist, `--close` creates it with a standard header (see `references/backlog-entry-format.md`).
- Existing files are appended to under a new dated heading - never overwritten.

**Edge cases:**

- **Existing `_archive/doc_original.md`:** skill errors out; names the existing archive path in the error; no file operation. JP resolves manually.
- **Missing Proposed Actions table in the reviewed-by doc:** Step 2 applies no changes and surfaces a warning in the confirmation prompt.

### Auto-detect

`/plab-ai-review doc_reviewed-by-codex.md` (no flag) - detect reviewer findings present, confirm with user: "This review has findings. Want me to add my response?" Proceed as `--respond`.

If instead the document's frontmatter carries a `dispatch-job` field and the reviewer placeholders are still empty (no findings present), confirm with user: "This review was dispatched to Codex as `<dispatch-job>`. Want me to check on it?" On confirm, proceed as `--collect`. This is the only way collection happens without the maintainer typing `--collect`; `--respond` itself is not changed and does not attempt collection on its own (A-02 Non-Goals).

On a reviewed-by file where initial synthesis is already filled in, `--respond` auto-detects pending clarifications: scans for `**Maintainer Clarification Request**` sub-blocks containing content but no filled `**Requestor Response - **` below. If any are found, prompts: *"Found N pending clarification(s). Address them?"* On confirm, fills only those sub-blocks; does not modify resolved decisions or the initial synthesis.

## Phase Model

| Phase | Actor | What happens |
|-------|-------|--------------|
| **P2** | `--review` | Generates the template with placeholders. |
| **P3** | Reviewer LLM (Codex/GPT/etc.) | Fills findings per section. JP pastes reviewer output back into the file. |
| **P4** | `--respond` first pass | Writes Reviewer Assessment, Requestor Analysis, inline responses, per-decision sections (Part 1 populated, Parts 2/3 left as placeholders), summary table with `Status = Open`, Proposed Actions table. |
| **P5** | JP (manual) | Fills Maintainer Response per decision (Status / Reasoning / free-form notes); optionally writes Clarification questions; updates Final Decision and Last Updated columns. |
| **P6** | `--respond` second pass | Answers pending clarifications only. Leaves resolved decisions and initial synthesis untouched. |

P1 is intentionally unused (historical gap from an earlier draft); do not renumber the others.

**With `--dispatch`, P3 is automated rather than skipped:** `--dispatch` submits the P2 document as a background job, and `--collect` (or the auto-detect prompt) later writes exactly what a human reviewer would have written into the same placeholders, attributed to Codex. P4 through P6 are unchanged either way - `--respond` cannot tell which path produced the findings it is reading (A-02 AC-6).

## Document Types

Types are optional - the skill auto-detects and proposes dimensions. Use `--type` to skip the proposal step.

| Type | Focus | Sections |
|------|-------|----------|
| **plan** | Executability - can this be built as written? | 7 |
| **brief** | Decision quality - is the thinking rigorous? | 7 |
| **spec** | Completeness - is this testable and unambiguous? | 6 |
| **rfc** | Technical soundness - is the proposal correct? | 7 |
| **doc** | Generic - LLM proposes 5-7 custom dimensions | varies |

`spec` and `prd` are synonyms. See `references/section-presets.md` for default dimensions per type.

## LLM Identifiers

`claude` | `codex` | `gpt` | `gemini` | `grok` | `mistral` | `local-<model>`

## Output

Use the template in `references/review-template.md`. File naming and archive workflow per `references/file-lifecycle.md`.

- **`--review`**: Write `<basename>_reviewed-by-<reviewer>.md` in same directory as source
- **`--review --dispatch`**: Same file, plus a `dispatch-job` frontmatter field recording the submitted job id (see `references/dispatch.md`)
- **`--collect`**: Update existing `_reviewed-by-` file in place (fill reviewer placeholders only, from a dispatched job's findings)
- **`--respond`**: Update existing `_reviewed-by-` file in place (fill placeholders)
- **`--close`**: Archive source + reviewed-by to `_archive/`, apply accepted changes to source, append unresolved items to `--backlog` file (see edge cases in `--close` section)

## Constraints

- **Every Blocker finding and every Major finding MUST generate a corresponding per-decision section.** Requestor LLM retains judgment for Minor and Note findings. Silent drops of Blocker/Major findings are a skill violation.
- Review document must be **self-contained** - reviewer needs nothing beyond this document
- Every review section must have a **specific question**, not "what do you think?"
- Every finding must **cite specific evidence** (sections, quotes, file paths)
- Do **not** call the reviewer LLM yourself, and do **not** construct a Codex CLI string by hand - without `--dispatch`, the user handles the handoff; with it, `scripts/dispatch.py` is the only thing that talks to Codex, and only through the installed `codex-companion.mjs` helper's `task` subcommand (see `references/dispatch.md`)
- All LLM content **attributed** with role + LLM name + date (see `references/attribution-guide.md`)
- Reviewer Assessment and Requestor Analysis are **separate** top-level sections
- Proposed Actions is a **single table** at the bottom - no per-section update lines
- Response depth **scales with severity** - Blockers get paragraphs, Notes get one-liners
- Review should be **shorter than the source** - focused, not exhaustive
