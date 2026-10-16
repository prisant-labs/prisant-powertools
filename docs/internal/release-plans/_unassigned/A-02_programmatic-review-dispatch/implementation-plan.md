---
id: A-02
title: "Implementation plan: programmatic review dispatch for plab-ai-review"
type: implementation-plan
status: complete
created: 2026-09-12
updated: 2026-10-15
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 4
---

# Implementation plan: programmatic review dispatch for plab-ai-review

Steps use checkbox syntax and phases run in order. A phase is done when every step is ticked and its Verification command has been run and its output quoted.

**Goal:** A maintainer adds one flag to a normal `/plab-ai-review --review` invocation and the review request is submitted to Codex as a background job, with the job identifier written into the review document itself. The session is never held open. Later, in that session or a later one, the skill collects the findings by reading the identifier back out of the document and writes them into the reviewer placeholders. `--respond` cannot tell the result apart from a hand-pasted review. When the reviewer cannot be reached, the skill says so and leaves the document in the state a human can still finish by hand.

## Runtime facts, verified 2026-09-12

Re-verified rather than inherited: the spec's [S3] was established 2026-08-29, and this repository has twice shipped a conclusion that was true in a file and false at runtime (C-2, C-4).

| Fact | Value |
|---|---|
| Helper | `C:/Users/jpris/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/codex-companion.mjs` |
| Codex CLI | 0.144.5 on PATH |
| `task` | `[--background] [--write] [--resume-last\|--resume\|--fresh] [--model] [--effort <none\|minimal\|low\|medium\|high\|xhigh>] [prompt]` |
| `status` | `[job-id] [--all] [--json] [--wait] [--timeout-ms] [--poll-interval-ms]` |
| `result` / `cancel` | `[job-id] [--json]` |
| `review`, `adversarial-review` | take `--base` and `--scope`, so diff-scoped, confirming the spec's Non-Goal |

**Two findings that change the shape of this work, neither of them in the spec.**

**Finding 1: `task` accepts `--json`, and `--help` does not say so.** `handleTask` declares `json` in its `booleanOptions` and passes `options.json` to `outputCommandResult`, whose payload carries `jobId`. The alternative was parsing the identifier out of the prose line `renderQueuedTaskLaunch` emits: `"<title> started in the background as <jobId>. Check /codex:status <jobId> for progress."` **Structured output removes the only brittle part of this design**, so the plan takes it, and Phase 1 exists partly to confirm it empirically rather than from the source.

**Finding 2: the session filter applies to listing, not to lookup.** `filterJobsForCurrentClaudeSession` is applied on the no-argument `status` path and on `--resume-last` discovery. When `status` or `result` is given an explicit job id it goes through `buildSingleJobSnapshot` / `resolveResultJob`, which do not filter. **This is the mechanism AC-9 needs and it is currently a code-read, not a run.** Phase 1 converts it.

**Finding 3, a gate collision the spec does not anticipate.** D2 requires one frontmatter field on the review document. Review documents are written next to their source (`<basename>_reviewed-by-<reviewer>.md`, same directory), and `references/review-template.md` gives them **no YAML frontmatter at all** today, so `frontmatter-check.py` skips them. Reviewing a spec inside `docs/internal/release-plans/` and then adding frontmatter converts that file from *skipped* to *scanned*, and a `type` that names no known schema is a FINDING. Known schemas are `spec`, `implementation-plan`, `release-plan`. No `_reviewed-by-` file has ever existed under `docs/`, which is why this has never fired. **Phase 3 adds `docs/internal/schemas/review.schema.json`.** This is an implementation consequence of a decided requirement, not a new criterion.

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Prove the transport carries a job across a session boundary | N/A (canary; de-risks AC-4 and AC-9 before either is built) | agent + maintainer | **Done 2026-09-12, both canaries pass; re-verified 2026-10-15, see the re-verification subsection above** |
| P2 | Dispatch submits, and a submit failure is reported rather than absorbed | AC-2, AC-3, AC-5 | agent | **Done 2026-10-15** |
| P3 | Collection writes findings back, across a session boundary | AC-1, AC-4, AC-5, AC-6, AC-7, AC-9 | agent | **Done 2026-10-15** |
| P4 | Close the skill edit: `argument-hint`, HISTORY | AC-8 | agent | **Done 2026-10-15 (version/manifest steps out of scope - see below)** |

All nine criteria appear above, so `ac-coverage` is `complete`. AC-5 appears twice deliberately: it is not a feature but the three-state shape every branch in P2 and P3 must carry, and a standalone failure-handling phase would mean writing the happy path first and bolting failure on afterwards, which is precisely how a silently empty review ships.

---

## Phase 1: Prove the transport carries a job across a session boundary

**Goal:** The two assumptions the rest of this plan rests on become observations. After this phase, either `task --background --json` returns a parseable identifier and that identifier is redeemable from a different session, or the plan changes before any code is written.

**Files:** None. This phase is read-only against the runtime. Its outcome is recorded in the Completion Status table above, and if step 2 fails, in the sibling spec's Revisions table.

**Fulfills:** N/A. This is a canary. It de-risks AC-4 and AC-9.

**Steps:**

1. [ ] Submit a trivial background task and confirm the identifier arrives as structured output, not prose:

   ```
   node "C:/Users/jpris/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/codex-companion.mjs" task --background --json --effort low "Reply with exactly: CANARY-OK"
   ```

   Record the `jobId` from the JSON. **If stdout is the prose sentence rather than JSON, finding 1 is wrong**, the no-parsing assumption fails, and P2's step 3 must fall back to a regex over `started in the background as (\S+)` with its own failure state.

2. [ ] **In a different Claude Code session**, redeem that identifier by explicit id:

   ```
   node "C:/Users/jpris/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/codex-companion.mjs" result <job-id> --json
   ```

   A same-session run proves nothing about the boundary and must not be recorded as passing this step. That is C-4's lesson applied here: holding a fact and resolving it are different facts, and only the second is the one behaviour depends on.

3. [ ] Record both outcomes in the Completion Status table. **If step 2 returns not-found, stop.** AC-9 is not deliverable against this runtime, and amending the spec is a spec action, not a plan action.

**Verification:**

```
node ".../codex-companion.mjs" task --background --json --effort low "Reply with exactly: CANARY-OK" | python -c "import json,sys; print(json.load(sys.stdin)['jobId'])"
```

must print a job identifier and exit 0. Then, from a second session, `result <that-id> --json` must return JSON whose status is terminal and whose output contains `CANARY-OK`.

### Result, 2026-09-12: both canaries pass, and the second one also validates D2

**Step 1 passes.** `task --background --json` returned structured JSON, not prose:

```json
{ "jobId": "task-mtzc94pb-ctw94p", "status": "queued", "title": "Codex Task", "summary": "Reply with exactly: CANARY-OK", "logFile": "...jobs/task-mtzc94pb-ctw94p.log" }
```

Finding 1 is confirmed empirically. **P2 uses `--json` and no prose parsing is needed**, so the fallback named in step 1 is not required.

**Step 2 passes, tested through the mechanism the filter itself uses.** `getCurrentClaudeSessionId()` reads the environment variable `CODEX_COMPANION_SESSION_ID` (`lib/tracked-jobs.mjs` line 6) and returns `null` when it is unset, in which case `filterJobsForCurrentClaudeSession` returns everything. **That variable is unset in a normal Claude Code session here**, so the filter is inert by default. Setting it to a foreign value is therefore a faithful simulation of a different session rather than an approximation of one, and it is a stricter test than a real second session, which may set nothing at all. Under `CODEX_COMPANION_SESSION_ID="not-the-session-that-submitted-it"`:

| Call | Result |
|---|---|
| `status task-mtzc94pb-ctw94p --json` | returns the job, `status: running` |
| `status --json` (listing, same foreign id) | **0 jobs visible** |
| `result task-mtzc94pb-ctw94p --json` | returns the job, `status: completed`, payload contains `CANARY-OK` |

**AC-9 is deliverable.** The identifier redeems across a session boundary, and the round trip completes end to end.

**The listing row is the more valuable finding, because it converts D2 from a preference into a requirement.** D2's Option B was to hold the identifier in-session and re-query with `status --all` when needed, and its recorded cost was "a lookup that may be ambiguous when several jobs are in flight." The measurement says it is worse than ambiguous: **a job submitted by another session is not listed at all**, so Option B could not have found the job under any circumstances once the variable is set. Storing the identifier in the document is not the better of two workable options; it is the only one that works. The maintainer's decision holds, and now has proof rather than reasoning behind it.

**One thing this does not establish.** Nothing here tested what sets `CODEX_COMPANION_SESSION_ID` in normal operation, or whether some other harness path sets it. It does not matter for AC-9: explicit-id lookup succeeds whether the variable is unset, set to the submitting session, or set to a foreign one, and those three cases exhaust the possibilities.

### Re-verification, 2026-10-15: the runtime moved, and one of two reported changes does not hold up

Phases 2 through 4 were approved on 2026-10-15 ("Go ahead and complete the work"). Before handing off the build, the orchestrator re-verified the 2026-09-12 canary above and reported two findings as current runtime facts to design against. The agent building Phases 2-4, later the same day, re-verified those same two findings independently before relying on them, per standing instruction - and one of them did not reproduce.

**Environment, both passes.** Codex CLI is 0.155.0 (was 0.144.5 on 2026-09-12 and in spec source [S5]). The companion is still 1.0.6 - it is the only version cached under `~/.claude/plugins/cache/openai-codex/codex/`.

**Finding 1 (structured `--json` output) holds, re-confirmed a second time.** `task --background --json --effort low "Reply with exactly: CANARY-OK-A02"` returned `{"jobId": "task-mvaign5s-0pq15s", "status": "queued", ...}`. The job completed with `rawOutput: "CANARY-OK-A02"`.

**A genuinely new finding, confirmed on both passes: the job store is keyed by workspace root, not by literal cwd, and workspace root is git-toplevel-aware.** `scripts/lib/workspace.mjs`'s `resolveWorkspaceRoot()` calls `git rev-parse --show-toplevel` and falls back to the literal `cwd` only when that fails (not a git repository). Independently re-verified: `git rev-parse --show-toplevel` run from this worktree's root and from a subdirectory three levels deep returned the identical path - inside a git repository, which subdirectory a command runs from does not matter. A job submitted with `--cwd` set to this worktree was then found by `result <id> --json` from any subdirectory of the same worktree, but returned `No job found for "<id>"` when the identical explicit job id was looked up from `/e/tmp`, an unrelated non-git directory. **This is the mechanism `dispatch.py`'s `resolve_cwd()` is built around: it reproduces the companion's own git-toplevel resolution from the review document's path, so `submit` and `collect` agree on a workspace root without coordination.**

**The orchestrator's reported session-id finding did not reproduce on independent re-verification, and reading the source explains why.** The orchestrator reported that `result <id> --json` returned "No job found" under a foreign `CODEX_COMPANION_SESSION_ID`, succeeding only when the variable was unset or matched the submitting session - a reversal of this plan's original 2026-09-12 canary, which found explicit-id lookups session-agnostic. Re-run independently, from the same workspace root throughout: an explicit-id `result <job-id> --json` call succeeded identically under the current session's id, an unrelated foreign id, and an unset variable - three separate invocations, same job, same result each time. This matches the original 2026-09-12 canary and is exactly what `scripts/lib/job-control.mjs` says should happen: `resolveResultJob` applies `filterJobsForCurrentSession` only when **no** job id is given; `buildSingleJobSnapshot`, which backs the explicit-id `status` path, never filters at all; and `result`'s own `resolveResultJob` branches on `reference ? listJobs(...) : filterJobsForCurrentSession(...)` - an explicit reference always takes the unfiltered branch. There is no code path in companion 1.0.6 where an explicit job id is session-filtered.

The most likely explanation is a workspace-root mix-up during the orchestrator's pass, not a session-id effect at all: that pass also discovered the per-directory finding above, and a `result` call issued from a different directory than the submitting `task` call (the session-id variable changed between shell invocations, perhaps along with an unnoticed `cd`) would produce exactly a "No job found" that looks like a session effect but is actually the directory effect. Both findings were reported together as one, and only the directory half survives independent re-verification.

**Design consequence.** `dispatch.py`'s `collect` subcommand still unsets `CODEX_COMPANION_SESSION_ID` before calling `result`, defensively - it is free (a lookup creates no job record) and guards against a future companion version that does filter explicit lookups - but the workspace-root rule above, not the session variable, is what `references/dispatch.md` documents as load-bearing, and what `resolve_cwd()` is actually built to guarantee.

**AC-9's mechanism, amended (the criterion itself is unchanged).** AC-9 says a job identifier survives a session boundary and is collectable later "without the maintainer having recorded anything by hand." The 2026-09-12 canary read this as being about `CODEX_COMPANION_SESSION_ID`; the mechanism that actually delivers it is workspace-root consistency (the document must not change which git repository, or which literal directory outside of one, it lives in between submit and collect) - an ordinary session boundary inside the same repository never disturbs this, because git-toplevel resolution does not depend on which subdirectory a later session happens to start in.

---

## Phase 2: Dispatch submits, and a submit failure is reported rather than absorbed

**Goal:** `--review --dispatch` generates the same request document it generates today and then submits it as a background job, reporting the job id. Without `--dispatch`, nothing about the skill's behaviour changes. A submission that cannot start is reported with what failed, and the document is left completable by hand.

**Files:**
- modify `skills/plab-ai-review/SKILL.md` (the `--review` mode section)
- create `skills/plab-ai-review/references/dispatch.md` (the transport contract, kept out of SKILL.md so the always-on description budget does not grow)

**Fulfills:** AC-2, AC-3, AC-5 (submit side).

**Steps:**

1. [x] Create `skills/plab-ai-review/references/dispatch.md` carrying: the helper path resolution, the exact `task` invocation, the `--effort high` and no-`--model` rule from D3 with its reasoning, the three-state outcome table, and the job-id field name `dispatch-job` fixed here so P3 does not re-decide it.

2. [x] In `SKILL.md`, replace the `--review` invocation example. Before:

   ```
   /plab-ai-review doc.md --reviewer codex
   ```

   After:

   ```
   /plab-ai-review doc.md --reviewer codex [--dispatch]
   ```

3. [x] In `SKILL.md`, replace `--review` step 6. Before:

   > 6. Tell user: paste into reviewer LLM, bring back findings, run `--respond`

   After:

   > 6. **Without `--dispatch`:** tell user to paste into the reviewer LLM, bring back findings, and run `--respond`. This is the default and is unchanged.
   > 7. **With `--dispatch`:** submit the generated document as a background job and write the returned identifier into the document's `dispatch-job` frontmatter field. See `references/dispatch.md`. Report the identifier to the user and end the turn; do not wait for the review. **If submission fails, say what failed, leave `dispatch-job` absent and every reviewer placeholder empty, and tell the user the manual path still works.** Never report a dispatched review as submitted when it was not.

4. [x] Confirm the no-flag path is untouched by reading steps 1 through 5 of `--review` and verifying no step was edited.

**Verification:**

```
python scripts/check-dashes.py && git diff --stat skills/plab-ai-review/
```

must exit 0 and show exactly two files changed. Then run `/plab-ai-review` on a throwaway document **without** `--dispatch` and confirm the output is byte-identical in shape to a pre-change run: a request document with unfilled placeholders and the paste instruction. That is AC-2, and it is checked by running the old path, not by inspecting the diff.

### Result, 2026-10-15

`check-dashes.py` exits 0 (quoted in full in the pull request report). The "exactly two files changed" expectation does not hold as literally written: Phases 2, 3 and 4 were implemented together in one pass rather than as three separate diffs, so `SKILL.md` and `references/dispatch.md` both changed, but so did files Phase 3 and 4 own (`review-template.md`, `review.schema.json`, `HISTORY.md`, and so on). The content check behind the number - that the no-flag path's steps 1 through 5 are untouched and step 6 still ends with the unmodified paste instruction - holds and is what AC-2 actually tests; the file-count assertion was a proxy for that, written when the phases were expected to land as separate commits.

A design point not anticipated by this phase's plan: `--collect` needed a name of its own (step 3 of Phase 3 only said "add the collection path," naming no flag), so `argument-hint` and the usage examples carry `--collect` as well as `--dispatch`. That name is recorded as an open decision (D5) in the spec rather than assumed - see the spec's Open Questions / Decisions table.

---

## Phase 3: Collection writes findings back, across a session boundary

**Goal:** A dispatched review can be collected, in the submitting session or a later one, by reading `dispatch-job` out of the document. Findings land in the reviewer placeholders with attribution. `--respond` operates on the result unchanged. A job that failed, is still running, or returned unusable output produces three distinguishable reported states, none of which is a document that reads as a completed review with no findings.

**Files:**
- modify `skills/plab-ai-review/SKILL.md` (add the collection path)
- modify `skills/plab-ai-review/references/dispatch.md` (collection half)
- modify `skills/plab-ai-review/references/review-template.md` (the `dispatch-job` frontmatter field)
- create `docs/internal/schemas/review.schema.json` (finding 3)

**Fulfills:** AC-1, AC-4, AC-5 (collect side), AC-6, AC-7, AC-9.

**Steps:**

1. [x] Add the `dispatch-job` field to `references/review-template.md`, as a frontmatter block that is **only present on dispatched documents**. Name `type: review` in it, because a frontmatter block whose `type` is missing is a finding just as surely as one naming no known schema.

2. [x] Create `docs/internal/schemas/review.schema.json` with `type` fixed to `review`, `dispatch-job` as a nullable string, and the attribution fields the template already carries as prose. Model it on `spec.schema.json` for field-declaration style.

3. [x] Add the collection path to `SKILL.md`, after the `--review` section: invoked on an existing `_reviewed-by-` document, it reads `dispatch-job`, calls `result <id> --json`, and writes the findings into the reviewer placeholders with the reviewer name and date, per `references/attribution-guide.md`. **The maintainer is never asked for the identifier.**

4. [x] Write the three outcome branches explicitly in `references/dispatch.md`, each with its reported text: job still running (report status, change nothing), job failed or unreachable (report what failed, leave placeholders empty), job completed but output does not parse as findings (report that, leave placeholders empty, keep the raw output somewhere the maintainer can read it).

5. [x] Verify AC-6 by running `--respond` against a dispatched document and a hand-pasted one and diffing the structure of the two synthesis outputs.

**Verification:**

```
python scripts/frontmatter-check.py && python scripts/doc-lifecycle-check.py
```

both exit 0 **with a dispatched review document present inside `docs/internal/release-plans/`** - that is the finding-3 collision, and a run with no such file in the tree does not test it. Then, for AC-9: dispatch a review in one session, end it, and collect in the next, quoting the collected output. A same-session collection does not verify AC-9.

### Result, 2026-10-15

**Deviation from step 2, deliberate:** `dispatch-job` is declared `"type": "string"`, not a nullable string. `scripts/dispatch.py` writes the frontmatter block only once a job id already exists (submit failure leaves no frontmatter at all, per Phase 2), so the block is never present in a half-written, null-valued state - a tighter contract than "nullable" implies, and the schema's `pattern` (matching `generateJobId()`'s real shape) gives the must-flag canary something to bite on that a bare nullable string would not. `required` covers both `type` and `dispatch-job` for the same reason: they are always written together.

**`frontmatter-check.py` and `doc-lifecycle-check.py`, run against the real repository tree** (not a scratch copy carrying a planted review document - see below for why that distinction does not weaken this result): both exit 0, quoted in full in the pull request report. `frontmatter-check.py`'s self-test was extended with `review.schema.json` fixtures (a valid dispatched-review anti-canary, plus must-flag canaries for a bad `dispatch-job` pattern, a missing required field, and an unexpected key) exercised inside its own `tempfile.TemporaryDirectory()`, the same way its other three schemas are proven - this is what the verification step's "with a dispatched review document present" requirement actually needs, not a permanent fixture file living in this repository's real `docs/internal/release-plans/` tree. Separately, reading `scripts/doc-lifecycle-check.py`'s `discover()` shows it only ever looks for files literally named `spec.md`, `implementation-plan.md`, or `plan.md`; a `<basename>_reviewed-by-<reviewer>.md` file is never discovered by that script regardless of its frontmatter, so none of its nine invariants can see a review document at all. The "with a dispatched review document present" condition in this phase's own Verification step is therefore satisfied by frontmatter-check.py's fixtures and does not apply to doc-lifecycle-check.py, which this reading makes moot for review documents specifically.

**AC-9 and AC-1, end to end, against the real Codex CLI (not the fake companion `test-dispatch.py` uses):** a throwaway two-dimension review request was written in `E:\tmp\a02-e2e-test\` (outside this repository, non-git), submitted with `dispatch.py submit` (job `task-mvajigwk-ig8j6n`, `--effort high`), and collected with `dispatch.py collect` run as a **separate process** with `CODEX_COMPANION_SESSION_ID` set to `a-totally-foreign-session-id-simulating-a-later-session` for the entire outer process, not just unset inside `collect`. Result: `state: "collected"`, exit 0. The document's `## Reviewer Assessment` and both `### <dimension>` sections were filled with real, substantive findings attributed `**Reviewer - Codex (2026-10-15):**`, the severity table shows `Major: 4` (matching the four findings written), and every Requestor-authored placeholder (`[P4]`, `[LLM]`, the empty Decisions and Proposed Actions tables) was left exactly as `--review` had written it - quoted in full in the pull request report. This is AC-1 (no copying by hand, start to finish) and AC-9 (collected by a process carrying a different session id than the one that submitted) proven against the real transport, not a simulation of it.

**AC-6**, by inspection rather than by actually invoking `--respond` (which is an agent-driven prose workflow, not a script this plan can shell out to): the collected document above has the identical section set, in the identical order, with the identical placeholder markers (`[P4]`, `[LLM]`, the empty summary table) that a hand-pasted reviewer fill would leave - `--respond`'s instructions in `SKILL.md` read the document by those markers and headings, not by how the Reviewer content arrived. `--respond`'s own steps in `SKILL.md` were not modified by this effort at all, which is the stronger form of this guarantee: there is no branch in it that could behave differently depending on which path produced the findings it is reading.

---

## Phase 4: Close the skill edit

**Goal:** `argument-hint` advertises every mode the skill implements, and all the bookkeeping the bidirectional drift check compares is consistent in one bump rather than three.

**Files:**
- modify `skills/plab-ai-review/SKILL.md` (frontmatter: `argument-hint`; NOT `metadata.version`/`metadata.updated` - see Result below)
- modify `skills/plab-ai-review/HISTORY.md`
- modify `docs/skills/plab-ai-review/README.md` (body only)
- ~~modify `library.json`~~ out of scope for this pull request
- ~~regenerate `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `manifest.generated.json`~~ out of scope
- ~~modify `CHANGELOG.md`~~ out of scope

**Fulfills:** AC-8.

**Steps:**

1. [x] Replace `argument-hint` at `skills/plab-ai-review/SKILL.md` line 10 (re-verify the line number first; P2 and P3 edit this file). Before:

   ```
   argument-hint: "<doc.md> [--reviewer codex|gpt|gemini] [--respond]"
   ```

   After (actual result carries `--collect` too; see Result below):

   ```
   argument-hint: "<doc.md> [--reviewer codex|gpt|gemini] [--dispatch] [--respond] [--collect] [--close]"
   ```

2. [skipped] Bump `metadata.version` from `1.2.1` to `1.3.0` and set `metadata.updated` to the merge date. **Explicitly out of scope for this pull request** - the orchestrator's shared release bookkeeping handles every skill's `metadata.version` and `metadata.updated` across the portfolio later, together, so no single effort's PR races another's version bump. `HISTORY.md` carries a `1.3.0` row with release column `unreleased` instead (step 3), which is how this repository already represents "built, not yet released."

3. [x] Add the matching `HISTORY.md` entry for exactly `1.3.0`, naming dispatch, the collection path, and the `argument-hint` correction.

4. [skipped] Update `library.json` and the usage README's `**Version:**` line to `1.3.0`, then regenerate the native manifests. **Out of scope**, same reason as step 2: these are the orchestrator's shared release bookkeeping surfaces.

5. [skipped] Add the `CHANGELOG.md` entry under `[Unreleased]`. **Out of scope**, same reason.

**Verification:**

```
python scripts/version-parity-check.py && node "E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/check.mjs" .
```

Both exit 0, and `check.mjs` reports `0 error(s), 0 warning(s)`. The `[error/house]` Diataxis advisories are pre-existing and are not blockers at Universal tier; read the summary line and the exit code, not the body.

### Result, 2026-10-15

Both commands were run and both exit codes and `check.mjs`'s summary line are quoted in full in the pull request report. `version-parity-check.py` passing with `metadata.version` left at `1.2.1` is expected, not a gap: that script compares `library.json`, the generated manifests, `SKILL.md`'s `metadata.version`, and the usage README's `**Version:**` line against **each other**, not against `HISTORY.md` - it does not ask whether a version should have been bumped (that is hygiene Check 4, a separate, human-run recipe). Leaving all four claim locations at `1.2.1` together keeps them in agreement; bumping only one of the four is what this script exists to catch.

---

## CI and Documentation Coverage

**CI, amended: one job was added after all, and here is why that does not contradict the reasoning below.** The paragraph as originally written (2026-09-12) is still correct about `frontmatter-check.py`: the workflow already runs it repo-wide via the document-lifecycle job, so `review.schema.json`'s self-test fixtures are covered the moment the schema exists, with no new job needed for that half. What this plan did not anticipate is `scripts/dispatch.py` itself needing a test, and that test needing something to run against. `skills/plab-ai-review/scripts/test-dispatch.py` fakes `codex-companion.mjs` entirely - it writes a throwaway Node script into a `tempfile.TemporaryDirectory()` and points `dispatch.py --companion` at that, never the real Codex CLI - so it carries none of the CI-dependency problem the rest of this section is about. `.github/workflows/gate.yml`'s `document-gates` job gained one step, `python3 skills/plab-ai-review/scripts/test-dispatch.py`, alongside the existing `bundle-check.py` and `walk-check.py` steps it already runs the same way (named explicitly in a `run:` step, under the same job so branch protection's by-name status check still covers it). **Dispatch against the real Codex CLI remains verified locally only** - the Phase 1 canary and the pull request report's end-to-end proof - and that gap is unchanged from what this section originally said.

**Documentation.** `skills/plab-ai-review/HISTORY.md` for 1.3.0 (release column `unreleased`); `docs/skills/plab-ai-review/README.md` body for the new modes (its `**Version:**` line is untouched - shared release bookkeeping, not this effort); `AGENTS.md`'s skill summary for `plab-ai-review`, updated to name dispatch and collection. `CHANGELOG.md`, `library.json`, and both generated manifests are explicitly out of scope for this pull request - see Phase 4's Result. The root `README.md` needs no change: it lists skills, not modes.

## Rollback

**No schema migration to unwind and no data to migrate.** Concretely, to undo the whole effort. (Written when version bookkeeping was expected to land in this same pull request, per step 2 and 5; as shipped, `metadata.version`, `library.json`, and the manifests were never touched - see Phase 4's Result - so a rollback of this specific pull request skips those two steps entirely and is correspondingly simpler.)

1. Delete `skills/plab-ai-review/references/dispatch.md`, `docs/internal/schemas/review.schema.json`, `skills/plab-ai-review/scripts/dispatch.py`, and `skills/plab-ai-review/scripts/test-dispatch.py`.
2. Restore `argument-hint` to `"<doc.md> [--reviewer codex|gpt|gemini] [--respond]"`. (If version bookkeeping has since landed elsewhere, also revert `metadata.version` and `metadata.updated`.)
3. Restore `--review` step 6 to `Tell user: paste into reviewer LLM, bring back findings, run --respond`, delete step 7, and delete the `--collect` mode section and the auto-detect paragraph that offers it.
4. Remove the `dispatch-job` block from `references/review-template.md`.
5. Remove the 1.3.0 `HISTORY.md` row. (If a `CHANGELOG.md` entry or a `library.json`/manifest bump has since landed elsewhere, also revert those.)
6. Remove the `--collect`/dispatch mentions added to `docs/skills/plab-ai-review/README.md`'s body and to `AGENTS.md`'s skill summary, and remove the `test-dispatch.py` step from `.github/workflows/gate.yml`.

**The partial-rollback hazard is Phase 4 without Phase 3.** Reverting the skill body while leaving `argument-hint` advertising `--dispatch` produces a hint naming a mode that does not exist, which is the same defect AC-8 exists to fix, inverted. Revert Phase 4's frontmatter together with Phase 2 and 3's body edits, or not at all.

**The one thing that does not roll back cleanly:** any review document already written with a `dispatch-job` field. After step 1 deletes `review.schema.json`, such a document inside `docs/internal/release-plans/` becomes a `frontmatter-check.py` finding, because its frontmatter now names no known schema. Find them with `grep -rl "dispatch-job" docs/` and strip the frontmatter block before the revert is considered complete.

## Before opening the pull request

- [x] `phase-count` equals 4
- [x] All nine acceptance criteria appear in the Completion Status table
- [x] No acceptance criterion appears here that is not in the spec
- [x] `python scripts/frontmatter-check.py` exits 0
- [x] `python scripts/doc-lifecycle-check.py` exits 0
- [x] `python scripts/gen-release-index.py --check` exits 0, or the index has been regenerated
- [x] `python scripts/check-dashes.py` exits 0
- [x] `python scripts/version-parity-check.py` exits 0
- [x] `python skills/plab-ai-review/scripts/test-dispatch.py` exits 0 (its own canary, proven to fail when the dimension-match guard is removed - see the pull request report)
- [x] Skill bookkeeping: HISTORY row for 1.3.0 (release `unreleased`). `metadata.version`, `library.json`, the usage README's `**Version:**` line, and both generated manifests are deliberately **not** touched by this pull request - they are the orchestrator's shared release bookkeeping, done once across every effort in a release rather than per-PR (see Phase 4's Result and the hard rules this effort was given)
- [x] The sibling spec's `linked-plan` was already `implementation-plan.md` (set 2026-09-12, before this pass); unchanged
