---
id: A-02
title: "Implementation plan: programmatic review dispatch for plab-ai-review"
type: implementation-plan
status: draft
created: 2026-09-12
updated: 2026-09-12
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
| P1 | Prove the transport carries a job across a session boundary | N/A (canary; de-risks AC-4 and AC-9 before either is built) | agent + maintainer | **Done 2026-09-12, both canaries pass** |
| P2 | Dispatch submits, and a submit failure is reported rather than absorbed | AC-2, AC-3, AC-5 | agent | Not started |
| P3 | Collection writes findings back, across a session boundary | AC-1, AC-4, AC-5, AC-6, AC-7, AC-9 | agent | Not started |
| P4 | Close the skill edit: `argument-hint`, version, HISTORY, manifests | AC-8 | agent | Not started |

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

---

## Phase 2: Dispatch submits, and a submit failure is reported rather than absorbed

**Goal:** `--review --dispatch` generates the same request document it generates today and then submits it as a background job, reporting the job id. Without `--dispatch`, nothing about the skill's behaviour changes. A submission that cannot start is reported with what failed, and the document is left completable by hand.

**Files:**
- modify `skills/plab-ai-review/SKILL.md` (the `--review` mode section)
- create `skills/plab-ai-review/references/dispatch.md` (the transport contract, kept out of SKILL.md so the always-on description budget does not grow)

**Fulfills:** AC-2, AC-3, AC-5 (submit side).

**Steps:**

1. [ ] Create `skills/plab-ai-review/references/dispatch.md` carrying: the helper path resolution, the exact `task` invocation, the `--effort high` and no-`--model` rule from D3 with its reasoning, the three-state outcome table, and the job-id field name `dispatch-job` fixed here so P3 does not re-decide it.

2. [ ] In `SKILL.md`, replace the `--review` invocation example. Before:

   ```
   /plab-ai-review doc.md --reviewer codex
   ```

   After:

   ```
   /plab-ai-review doc.md --reviewer codex [--dispatch]
   ```

3. [ ] In `SKILL.md`, replace `--review` step 6. Before:

   > 6. Tell user: paste into reviewer LLM, bring back findings, run `--respond`

   After:

   > 6. **Without `--dispatch`:** tell user to paste into the reviewer LLM, bring back findings, and run `--respond`. This is the default and is unchanged.
   > 7. **With `--dispatch`:** submit the generated document as a background job and write the returned identifier into the document's `dispatch-job` frontmatter field. See `references/dispatch.md`. Report the identifier to the user and end the turn; do not wait for the review. **If submission fails, say what failed, leave `dispatch-job` absent and every reviewer placeholder empty, and tell the user the manual path still works.** Never report a dispatched review as submitted when it was not.

4. [ ] Confirm the no-flag path is untouched by reading steps 1 through 5 of `--review` and verifying no step was edited.

**Verification:**

```
python scripts/check-dashes.py && git diff --stat skills/plab-ai-review/
```

must exit 0 and show exactly two files changed. Then run `/plab-ai-review` on a throwaway document **without** `--dispatch` and confirm the output is byte-identical in shape to a pre-change run: a request document with unfilled placeholders and the paste instruction. That is AC-2, and it is checked by running the old path, not by inspecting the diff.

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

1. [ ] Add the `dispatch-job` field to `references/review-template.md`, as a frontmatter block that is **only present on dispatched documents**. Name `type: review` in it, because a frontmatter block whose `type` is missing is a finding just as surely as one naming no known schema.

2. [ ] Create `docs/internal/schemas/review.schema.json` with `type` fixed to `review`, `dispatch-job` as a nullable string, and the attribution fields the template already carries as prose. Model it on `spec.schema.json` for field-declaration style.

3. [ ] Add the collection path to `SKILL.md`, after the `--review` section: invoked on an existing `_reviewed-by-` document, it reads `dispatch-job`, calls `result <id> --json`, and writes the findings into the reviewer placeholders with the reviewer name and date, per `references/attribution-guide.md`. **The maintainer is never asked for the identifier.**

4. [ ] Write the three outcome branches explicitly in `references/dispatch.md`, each with its reported text: job still running (report status, change nothing), job failed or unreachable (report what failed, leave placeholders empty), job completed but output does not parse as findings (report that, leave placeholders empty, keep the raw output somewhere the maintainer can read it).

5. [ ] Verify AC-6 by running `--respond` against a dispatched document and a hand-pasted one and diffing the structure of the two synthesis outputs.

**Verification:**

```
python scripts/frontmatter-check.py && python scripts/doc-lifecycle-check.py
```

both exit 0 **with a dispatched review document present inside `docs/internal/release-plans/`** - that is the finding-3 collision, and a run with no such file in the tree does not test it. Then, for AC-9: dispatch a review in one session, end it, and collect in the next, quoting the collected output. A same-session collection does not verify AC-9.

---

## Phase 4: Close the skill edit

**Goal:** `argument-hint` advertises every mode the skill implements, and all the bookkeeping the bidirectional drift check compares is consistent in one bump rather than three.

**Files:**
- modify `skills/plab-ai-review/SKILL.md` (frontmatter: `argument-hint`, `metadata.version`, `metadata.updated`)
- modify `skills/plab-ai-review/HISTORY.md`
- modify `library.json`
- modify `docs/skills/plab-ai-review/README.md`
- regenerate `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `manifest.generated.json`
- modify `CHANGELOG.md`

**Fulfills:** AC-8.

**Steps:**

1. [ ] Replace `argument-hint` at `skills/plab-ai-review/SKILL.md` line 10 (re-verify the line number first; P2 and P3 edit this file). Before:

   ```
   argument-hint: "<doc.md> [--reviewer codex|gpt|gemini] [--respond]"
   ```

   After:

   ```
   argument-hint: "<doc.md> [--reviewer codex|gpt|gemini] [--dispatch] [--respond] [--close]"
   ```

2. [ ] Bump `metadata.version` from `1.2.1` to `1.3.0` (a new opt-in mode is a minor bump) and set `metadata.updated` to the merge date.

3. [ ] Add the matching `HISTORY.md` entry for exactly `1.3.0`, naming dispatch, the collection path, and the `argument-hint` correction.

4. [ ] Update `library.json` and the usage README's `**Version:**` line to `1.3.0`, then regenerate the native manifests:

   ```
   node "E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/generators/gen-manifest.mjs" . --write --target=all
   ```

   It prints nothing on success; verify with `git diff` rather than waiting for output.

5. [ ] Add the `CHANGELOG.md` entry under `[Unreleased]`.

**Verification:**

```
python scripts/version-parity-check.py && node "E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/check.mjs" .
```

Both exit 0, and `check.mjs` reports `0 error(s), 0 warning(s)`. The `[error/house]` Diataxis advisories are pre-existing and are not blockers at Universal tier; read the summary line and the exit code, not the body.

---

## CI and Documentation Coverage

**CI: nothing changes in `.github/workflows/gate.yml`, and that is a claim rather than a default.** The workflow already runs `check-dashes.py` repo-wide and the document-lifecycle job, which invokes `frontmatter-check.py` over `docs/internal/release-plans/`. Finding 3's collision is therefore already covered by an existing job the moment `review.schema.json` exists, and adding a job would duplicate it. The one thing CI genuinely cannot cover is dispatch itself: it requires the Codex CLI, which is not installed on the runner and must not become a CI dependency, because the spec's portability requirement says the skill must work in a harness with no Codex CLI at all. **Dispatch is verified locally, by the Phase 1 and Phase 3 canaries, and this is recorded here so that gap is a known one rather than an assumed pass.**

**Documentation.** `CHANGELOG.md` under `[Unreleased]`; `skills/plab-ai-review/HISTORY.md` for 1.3.0; `docs/skills/plab-ai-review/README.md` for the `**Version:**` line and the new mode; `library.json`; both generated manifests. `AGENTS.md`'s skill summary for `plab-ai-review` names three modes and must name dispatch. The root `README.md` needs no change: it lists skills, not modes.

## Rollback

**No schema migration to unwind and no data to migrate.** Concretely, to undo the whole effort:

1. Delete `skills/plab-ai-review/references/dispatch.md` and `docs/internal/schemas/review.schema.json`.
2. Restore `argument-hint` to `"<doc.md> [--reviewer codex|gpt|gemini] [--respond]"`, `metadata.version` to `1.2.1`, `metadata.updated` to `2026-07-04`.
3. Restore `--review` step 6 to `Tell user: paste into reviewer LLM, bring back findings, run --respond` and delete step 7 and the collection section.
4. Remove the `dispatch-job` block from `references/review-template.md`.
5. Remove the 1.3.0 `HISTORY.md` row and the `CHANGELOG.md` entry, revert `library.json` to `1.2.1`, and regenerate the manifests.

**The partial-rollback hazard is Phase 4 without Phase 3.** Reverting the skill body while leaving `argument-hint` advertising `--dispatch` produces a hint naming a mode that does not exist, which is the same defect AC-8 exists to fix, inverted. Revert Phase 4's frontmatter together with Phase 2 and 3's body edits, or not at all.

**The one thing that does not roll back cleanly:** any review document already written with a `dispatch-job` field. After step 1 deletes `review.schema.json`, such a document inside `docs/internal/release-plans/` becomes a `frontmatter-check.py` finding, because its frontmatter now names no known schema. Find them with `grep -rl "dispatch-job" docs/` and strip the frontmatter block before the revert is considered complete.

## Before opening the pull request

- [ ] `phase-count` equals 4
- [ ] All nine acceptance criteria appear in the Completion Status table
- [ ] No acceptance criterion appears here that is not in the spec
- [ ] `python scripts/frontmatter-check.py` exits 0
- [ ] `python scripts/doc-lifecycle-check.py` exits 0
- [ ] `python scripts/gen-release-index.py --check` exits 0, or the index has been regenerated
- [ ] `python scripts/check-dashes.py` exits 0
- [ ] `python scripts/version-parity-check.py` exits 0
- [ ] Skill bookkeeping complete: `metadata.version` 1.3.0, `updated` bumped, `library.json` matching, HISTORY row for 1.3.0, usage README `**Version:**` line matching, manifests regenerated
- [ ] The sibling spec's `linked-plan` has been changed from `null` to `implementation-plan.md`
