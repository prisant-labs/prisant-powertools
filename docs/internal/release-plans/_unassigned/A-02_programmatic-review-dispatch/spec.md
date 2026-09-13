---
id: A-02
title: "Programmatic review dispatch for plab-ai-review"
type: spec
status: committed
created: 2026-08-29
updated: 2026-09-12
linked-effort: "the maintainer's private ai-review growth roadmap, entry A-2 (make the handoff programmatic), written 2026-08-16, which names this the single largest improvement available in the portfolio"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 9
source-count: 5
requires-human-review: false
priority: P1
---

# Spec: Programmatic review dispatch for plab-ai-review

## Task Summary

**Status:** committed
**Last updated:** 2026-09-12 by claude, setting the round-trip link to the implementation plan
**Linked plan:** `implementation-plan.md`
**Open questions:** 0
**Revisions:** 2

### Acceptance Criteria Fulfillment

- [ ] **AC-1** - An opt-in flag sends the review request to the reviewer and writes findings back, with no copying by hand
- [ ] **AC-2** - Without the flag, the existing manual path behaves exactly as it does today
- [ ] **AC-3** - Dispatch goes through the codex-companion `task` helper, not a hand-rolled CLI string
- [ ] **AC-4** - Dispatch is asynchronous: submit, poll, collect, so the session is never blocked
- [ ] **AC-5** - A reviewer that fails or is unavailable produces a distinct reported state, never a silently empty review
- [ ] **AC-6** - A dispatched review produces the same document shape as a manual one, so `--respond` works on it unchanged
- [ ] **AC-7** - Dispatch metadata is recorded in the document for attribution
- [ ] **AC-8** - `argument-hint` documents `--close`, which exists today but is undocumented
- [ ] **AC-9** - A pending job identifier survives the session that submitted it, so a review started before a break is collectable after it

### Currently In Progress

None.

---

## Purpose

`plab-ai-review` generates a self-contained review request and then stops, instructing the maintainer to paste it into a second model, bring the findings back, and run `--respond` [S1]. The maintainer is the transport layer. Every review costs a context switch, two copy-pastes, and a window change, so reviews happen only when there is patience for that ritual [S2].

This effort removes the manual transport while keeping it available. The reviewer becomes reachable by command, which makes review cheap enough to run on work that currently does not get reviewed at all, and makes the review step scriptable rather than dependent on a person being present to ferry text [S2].

## Scope

### In Scope

- An opt-in dispatch path on the `--review` mode that submits the generated review request to a reviewer and returns findings into the same document.
- Use of the installed `codex-companion` runtime as the transport [S3].
- Asynchronous submission and collection, so a long review does not hold the session open [S3].
- An explicit, reported failure state when the reviewer cannot be reached or returns nothing usable.
- Recording which reviewer ran, and when, inside the review document.
- Correcting `argument-hint`, which advertises `--respond` only and omits the `--close` mode the skill already implements [S1].

### Non-Goals

- **Replacing the manual path.** The copy-paste flow is what makes this skill portable to any model with a chat window and no CLI, and it stays the default [S2].
- **Multi-reviewer or disagreement surfacing.** That is a separate roadmap item and only becomes practical once dispatch exists; bundling it here would widen the first exercise of this pipeline into two features [S2].
- **Reusing the runtime's `review` or `adversarial-review` subcommands.** Both are scoped to a code diff, taking `--base <ref>` and `--scope working-tree|branch`, and this skill reviews documents rather than diffs [S3].
- **Changing the review document's body format, the section presets, or the severity framework.** Dispatch changes how the document is filled, not what its sections are. This carve-out is deliberate and narrow, and was added when D2 was decided: dispatch adds exactly one frontmatter field, carrying the pending job identifier, because a handle that does not survive the session defeats the asynchronous submission requirement 3 is built on. No section, preset or severity level changes.
- **Changing `--respond` or `--close` behavior** beyond the `argument-hint` correction.

## Users / Actors

| Actor | Role | Interaction |
|-------|------|-------------|
| Maintainer | Requests a review | Adds the dispatch flag to a normal `--review` invocation, and reads findings when they arrive |
| Requesting agent | Runs the skill | Generates the request document, submits it, collects the result, writes it back |
| Reviewer model | Produces findings | Receives the self-contained request through the runtime and returns structured findings |

## Requirements

1. Dispatch is opt-in per invocation. Absent the flag, the skill behaves as it does today, ending by telling the maintainer to paste the document into a reviewer [S1]. Preserving that path is a stated design constraint of the effort, not a fallback of convenience [S2].
2. Dispatch uses the `codex-companion` helper rather than a constructed Codex CLI string. The runtime contract states the helper is preferred over hand-rolled CLI strings, and it is the interface that carries job management [S4].
3. Dispatch is asynchronous. The runtime exposes background submission and separate status and result retrieval, with machine-readable output available on both [S3]. A document review is slow enough that blocking the session on it would reintroduce the friction this effort exists to remove [S2].
4. The reviewer's reachability is treated as a distinct outcome. The skill must distinguish "the reviewer ran and found nothing" from "the reviewer never ran", because a silently empty review is indistinguishable from a clean one and would be trusted as a review that happened [model-inference].
5. The dispatched path produces a document identical in shape to the manual path, so `--respond` operates on it without knowing which path produced it [S1].
6. Attribution is preserved. All content is already required to be attributed with role, model name, and date [S1]; dispatch must record the same facts rather than leaving machine-produced findings unlabelled.
7. `--close` is documented in `argument-hint`. It is an implemented mode that the hint omits, so a reader of the hint cannot discover it [S1, S2].
8. The pending job identifier is written into the review document's frontmatter. The runtime returns an identifier and offers `status` and `result` against it [S3], and that identifier is the only handle on a job that may outlive the session which started it [D2].
9. Dispatch requests `high` effort and names no model. The runtime accepts `--effort` and `--model` independently [S3], so effort can be set without pinning a model. Effort is a model-independent setting that does not age; a model identifier written into a skill file is an unversioned reference to something retired on another party's schedule, and no document gate in this repository covers skill files [D3].

## Acceptance Criteria

```
AC-1: A single `--review` invocation carrying the dispatch flag produces a review
      document whose reviewer findings are filled in, with no manual copying at
      any point. [S1, S2]
  Given: a document to review and a reachable reviewer
  When:  the skill is invoked in review mode with dispatch enabled
  Then:  the resulting `_reviewed-by-<reviewer>.md` contains reviewer findings,
         and the maintainer performed no copy or paste

AC-2: The same invocation without the dispatch flag produces exactly the output it
      produces today: a request document with unfilled reviewer placeholders, and
      an instruction to paste it into a reviewer. [S1, S2]

AC-3: Dispatch is performed by invoking the `codex-companion` helper's `task`
      subcommand. The skill does not construct a Codex CLI string itself, and does
      not use the `review` or `adversarial-review` subcommands, which are scoped to
      a code diff rather than a document. [S3, S4]

AC-4: Dispatch does not block. The submission returns before the review completes,
      and the result is collected in a separate step using the job identifier. [S3]

AC-5: When the reviewer cannot be reached, or returns output that does not parse as
      findings, the skill reports that state explicitly and leaves the reviewer
      placeholders unfilled. It never writes a document that reads as a completed
      review with no findings. [model-inference]
  Given: a reviewer that is unavailable or returns unusable output
  When:  dispatch is attempted
  Then:  the skill reports the failure, names what failed, and the document is
         left in a state a human can still complete by the manual path

AC-6: A document produced by the dispatched path is accepted by `--respond` with no
      change to that mode, and produces the same synthesis structure as a document
      produced by the manual path. [S1]

AC-7: The review document records which reviewer produced the findings and when, in
      the attribution form the skill already requires for all model content. [S1]

AC-8: `argument-hint` lists `--close` alongside `--respond`. [S1, S2]

AC-9: A job identifier written by a dispatched submission survives the end of the
      session that submitted it, so a review started before a break is collectable
      after it without the maintainer having recorded anything by hand. [S3]
  Given: a dispatch submitted in one session, and that session then ended
  When:  the skill is invoked in a later session to collect that review
  Then:  the identifier is recovered from the review document itself, the findings
         are written back, and at no point is the maintainer asked to supply the id
```

## Behavior / Examples

### Example 1: A dispatched review, end to end (grounds AC-1, AC-4, AC-6)

The maintainer asks for a review of a spec and enables dispatch. The skill generates the same self-contained request document it generates today, then submits that document's text to the reviewer as a background job and reports the job identifier. The session continues. When the job completes, the skill collects the result and writes the findings into the reviewer placeholders of the existing document. The maintainer then runs `--respond` exactly as they would have after a manual paste, and `--respond` cannot tell the difference.

### Example 2: The reviewer is unreachable (grounds AC-5)

Dispatch is enabled but the runtime cannot start a job. The skill reports that dispatch failed and why. The request document still exists, still self-contained, with its reviewer placeholders empty. The maintainer can paste it into any chat window and continue by hand. The failure costs the dispatch attempt and nothing else.

The distinction that matters: a document with empty placeholders and a reported failure is recoverable, whereas a document with empty findings and a success message would be read as a review that found nothing.

## Non-Functional Requirements

| Category | Requirement | Source |
|----------|-------------|--------|
| Portability | The skill must remain usable in a harness with no Codex CLI installed. Dispatch is an accelerator on top of the manual path, never a replacement for it | [S2] |
| Observability | A dispatched review must be distinguishable from a manual one after the fact, by reading the document alone | [S1] |
| Failure behavior | Reviewer unreachability is reported, never absorbed into a clean-looking result | [model-inference] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-08-29 | plab-spec | added | Initial draft created |
| 2026-09-12 | claude | amended | Round-trip link set: `linked-plan` from `null` to `implementation-plan.md`, per the planning artifact model's rule that plan creation sets the spec's link. No acceptance criterion, requirement, scope boundary or decision changed; `ac-count` is unchanged at 9. |
| 2026-09-01 | claude | amended | D1, D2 and D3 resolved by the maintainer. The Non-Goal on document format narrowed to the body, so it no longer contradicts the single frontmatter field D2 requires. AC-9 added, because AC-4 alone was satisfied by an in-session-only identifier and so did not test the session-boundary property D2 exists to deliver. Requirements 8 and 9 added for the identifier's persistence and the effort setting. Status promoted from draft to committed. |

## Sources & Evidence

- **[S1]** `plab-ai-review` SKILL.md, version 1.2.1 - the current three-mode contract, the manual handoff instruction in `--review` step 6, the constraint "Do not call the reviewer LLM - user handles the handoff", the attribution requirement, and the `argument-hint` that omits `--close` - `skills/plab-ai-review/SKILL.md` - class A
- **[S2]** The maintainer's private ai-review growth roadmap, entry A-2, written 2026-08-16. Names the manual handoff the single largest improvement available in the portfolio, argues that programmatic dispatch makes reviews cheap enough to run on work that currently goes unreviewed and makes the review step scriptable, states explicitly that the manual path must keep working because it is what makes the skill portable to models with no CLI, and defers multi-reviewer work until dispatch exists. Not a tracked file; its substance is summarized here rather than cited by path, per this repository's rule that a tracked artifact must not cite an untracked one - class A
- **[S3]** `codex-companion.mjs` usage output, verified by direct inspection 2026-08-29. Implements `task [--background] [--write] [--model] [--effort] [prompt]`, `status [job-id] [--json]`, `result [job-id] [--json]`, and `cancel [job-id]`, plus `review` and `adversarial-review` which take `--base <ref>` and `--scope <auto|working-tree|branch>` and are therefore diff-scoped rather than document-scoped - class A
- **[S4]** `codex-cli-runtime` SKILL.md, version 1.0.6 of the Codex plugin. States that the companion helper is preferred over hand-rolled Codex CLI strings, and scopes its own instructions to the rescue subagent - class A
- **[S5]** Codex CLI presence verified on this machine 2026-08-29, reporting version 0.144.5 on PATH. The transport this spec depends on is installed, not assumed - class A

### Unverified Claims

- "a silently empty review is indistinguishable from a clean one and would be trusted as a review that happened" - appears in Requirements item 4, AC-5, and Non-Functional Requirements. This is the three-state gate principle applied to a new surface. It is this repository's own established design rule rather than an external source, so it is marked as inference rather than cited.

### Credibility Classes (reminder)

- **A** - Authoritative (project docs, RFCs, formal specs)
- **B** - Credible secondary (maintainer blog, expert talk, well-cited issue)
- **C** - Community / informal (Stack Overflow, tutorials)

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Dispatch opt-in shape | Option A: a per-invocation flag; the manual path stays the default | Decided | 2026-09-01 |
| D2 | Where the pending job identifier lives | Option A: the review document's frontmatter, with the Non-Goal narrowed and AC-9 added | Decided | 2026-09-01 |
| D3 | Reviewer model and effort selection | Option B at `high`: pass `--effort high`, pin no model | Decided | 2026-09-01 |

### D1: Dispatch opt-in shape (Decided)

**Summary.** Is dispatch a flag on each invocation, or a configured default with an opt-out?

**Context.** The manual path must keep working [S2], but if dispatch requires remembering a flag every time, the cheap-review benefit is partly lost to the same friction this effort removes.

**Desired outcome.** Reviews are cheap to run without the maintainer having to think about transport, while a machine with no Codex CLI still works.

**Options / approaches.**

* **Option A: per-invocation flag, manual remains default.** Smallest change, no surprise, and nothing behaves differently until asked. Costs a flag every time.
* **Option B: dispatch by default when the runtime is present, with an opt-out flag.** Cheapest at the point of use and degrades naturally on a machine without the CLI. Costs surprise: the same command behaves differently on two machines.

**Recommendation.** Option A for the first release. This is the first effort to run through this pipeline end to end, and a default that varies by machine is a poor thing to be debugging at the same time as the pipeline itself. Revisit once dispatch has been used in anger.

---

> **Maintainer decision:** Option A, a per-invocation flag.
>
> * **Status:** Decided
> * **Choice:** Option A. Dispatch is requested per invocation; absent the flag the skill behaves exactly as it does today.
> * **Reasoning:** Accepted the recommendation after review. A-02 is the first effort to run through this pipeline end to end, and a default that varies by machine would put a second unknown into any failure: a review that did not dispatch could mean the feature is broken or merely that the runtime is absent here, with nothing distinguishing the two. One typed flag buys a command that means the same thing on every machine. Option B stays available and gets cheaper to adopt once dispatch has been used in anger, at which point the behaviour it would default to is already understood.
> * **Decided by / date:** JP / 2026-09-01

### D2: Where the pending job identifier lives (Decided)

**Summary.** Between submitting a background review and collecting it, the job identifier has to survive somewhere.

**Context.** The runtime returns a job identifier and offers `status` and `result` against it [S3]. If a session ends between submit and collect, that identifier is the only handle on a job that may still be running.

**Desired outcome.** A review submitted before a break is collectable after it, without the maintainer having recorded anything by hand.

**Options / approaches.**

* **Option A: in the review document's frontmatter.** The handle travels with the artifact it belongs to, and the wrap and resume loop already carries documents across sessions. Costs a frontmatter field on a document format this spec otherwise leaves alone.
* **Option B: hold it only in-session and re-query with `status --all` when needed.** No format change; costs a lookup that may be ambiguous when several jobs are in flight.

**Recommendation.** Option A. A handle that does not survive the session is exactly the failure mode this portfolio has already engineered out elsewhere.

---

> **Maintainer decision:** Option A, the review document's frontmatter, with both consequences resolved here rather than deferred.
>
> * **Status:** Decided
> * **Choice:** Option A. The pending job identifier is written into the review document's frontmatter.
> * **Reasoning:** Accepted the recommendation: a handle that does not survive the session is the failure mode this portfolio has already engineered out elsewhere, and it is the one property that makes requirement 3's asynchronous submission worth having. Two consequences were surfaced during the review of this spec and directed to be fixed in the spec rather than left to the implementation plan. First, the Non-Goals forbade changing the review document format, which this decision contradicts; that Non-Goal is now narrowed to the body, with the single frontmatter field named as a deliberate carve-out. Second, no criterion tested the property this decision exists to deliver: AC-4 requires only that collection happen in a separate step, which an in-session-only identifier satisfies completely, so AC-9 was added to test survival across a session boundary. Adding a criterion is a spec action, not a plan action.
> * **Decided by / date:** JP / 2026-09-01

### D3: Reviewer model and effort selection (Decided)

**Summary.** Should the skill pin a model and effort for review dispatch, or leave both unset?

**Context.** The runtime accepts `--model` and `--effort` and defaults both to unset [S3, S4]. Review is a judgment task, which argues for a capable model, and the maintainer's own routing rule reserves the strongest tier for adversarial verification and hard reasoning.

**Desired outcome.** Reviews are good enough to be worth reading, without pinning a model name that will age badly in a skill file.

**Options / approaches.**

* **Option A: leave both unset and inherit the runtime's defaults.** Nothing to maintain, and the skill never carries a stale model name. Costs control over review quality.
* **Option B: pass a high effort but no model.** Effort is a stable, model-independent knob, so it does not age the way a model identifier does.

**Recommendation.** Option B, if it can be expressed without pinning a model. It buys review depth on the axis that is safe to hard-code.

---

> **Maintainer decision:** Option B at `high`.
>
> * **Status:** Decided
> * **Choice:** Option B. Dispatch passes `--effort high` and names no model.
> * **Reasoning:** The recommendation's hedge, "if it can be expressed without pinning a model", was verified on 2026-09-01 against codex-companion 1.0.6 and Codex CLI 0.144.5: `--effort` accepts `none|minimal|low|medium|high|xhigh` independently of `--model`, so the split is expressible and the hedge resolves. Effort is a dial that means the same thing regardless of which model sits behind it, whereas a model identifier is an unversioned reference to something retired on another party's schedule, and skill files are not covered by this repository's document gates, so such a reference would rot unobserved. `xhigh` was considered and declined: review is adversarial work and the routing rule does reserve the strongest tier for it, but every review would then cost more and take longer, which pushes against the one thing this effort exists to achieve, namely making reviews cheap enough to actually run.
> * **Decided by / date:** JP / 2026-09-01
