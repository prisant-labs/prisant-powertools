---
id: C-02
title: "Implementation plan: Reconcile the Session Log Against Repo Reality at Resume"
type: implementation-plan
status: complete
created: 2026-08-23
updated: 2026-10-26
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 3
---

# Implementation Plan: Reconcile the Session Log Against Repo Reality at Resume

> **For agentic workers:** steps use checkbox syntax for tracking. Execute phases in order.

**Goal:** Make `plab-continue-session` check the session log's claims against the repository's current state before replaying them, and lead the resumption display with what changed.

**Architecture (revised 2026-10-15; see spec.md Revisions and OQ4):** A new reconciliation step sits between reading the log (current Phase 2) and displaying it (current Phase 3). The mechanism itself lives in `skills/plab-continue-session/scripts/reconcile.py`, a canary-tested stdlib script with a sibling `test-reconcile.py`, on the same pattern `plab-wrap-session` already uses for `organize-logs.py` and `path-citation-check.py`. It reuses the same remote-and-tag commands `plab-wrap-session`'s hygiene-sweep Check 1 defines (with one documented deviation, `--no-prune` on the fetch) and adds the checks of its own that AC-3 through AC-9 need (commit count, tag-date release detection, branch existence, continuation-prompt path existence with a rename hint, next-action overlap) plus an explicit broken-state path for when any check cannot complete. A short reference file documents how to invoke the script and read its output; it does not restate the mechanism the script already implements and tests. No change touches `plab-wrap-session` or the session-log write format; this is a pure read-side addition.

**Spec:** `spec.md`
**Target versions:** `plab-continue-session` 1.5.0 to 1.6.0 (this effort's `HISTORY.md` row; the shared release bookkeeping, including the `metadata.version` bump itself, is done by whichever change ships this effort). `plab-wrap-session` is not touched by this effort.

**Global constraints:**

- No em-dash (U+2014) or en-dash (U+2013) in any file this plan touches. Use " - " or restructure. Numeric ranges use plain hyphens.
- State a contract once, in one named file, and have everything else cite it. The reconciliation mechanism belongs entirely in `references/reconciliation.md`; SKILL.md points at it rather than restating it.
- Never grow the always-on `description`. All new instruction content goes in the SKILL.md body and the new reference file.
- Archive, never delete. This effort adds no deletion capability; the reconciliation step is read-only by design (AC-9).
- C-03 (cold-repo degradation) is a separate, still-unbuilt effort in `_unassigned/`; the two no longer share a planned release or a version bump (that coordination note was written when both were expected to ship together in one release; versions are now assigned only at ship time, decision register entry 21 (versions assigned at ship time)). Whichever of C-02 or C-03 ships first takes `plab-continue-session` to 1.6.0; the other then bumps from 1.6.0 at its own ship time. This plan's Phase 3 covers only this effort's own `HISTORY.md` row.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Build the reconciliation script, its tests, and its reference file | AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9 | agent | Done |
| P2 | Wire the reconciliation step into the workflow and display | AC-1, AC-5 | agent | Done |
| P3 | HISTORY row and usage-README body | N/A | agent | Done |

---

## Phase 1: Build the reconciliation script, its tests, and its reference file (revised 2026-10-15; see OQ4)

**Goal:** Implement the reconciliation delta as a canary-tested script, with a reference file documenting how to invoke it and read its output, rather than a rung-3 documented convention. The original Phase 1 made reconciliation a documented convention on the grounds that `plab-continue-session` "has no independent execution runtime ... so there is no standalone script for a canary to test against." That no longer holds: `plab-wrap-session` already ships agent-run scripts with sibling tests (`organize-logs.py` / `test-organize-logs.py`, `path-citation-check.py`), and a 2026-10-01 measurement found tool-call count, not text length, drives wrap/resume cost. See spec.md OQ4.

**Files:** Create `skills/plab-continue-session/scripts/reconcile.py`, `skills/plab-continue-session/scripts/test-reconcile.py`, `skills/plab-continue-session/references/reconciliation.md`

**Fulfills:** AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8, AC-9

**Steps:**
- [x] Step 1: Implement the remote-and-tag commands, citing `hygiene-sweep.md` Check 1 by name: `git fetch --no-prune origin --tags` (the one documented deviation from Check 1's plain fetch; see spec.md AC-2), `git status -sb`, `git log --oneline HEAD..@{u}`, `git log --oneline @{u}..HEAD`, `git ls-remote --heads origin` (unscoped; used to flag remote branches with no local counterpart, Check 1's own named flag), `git tag -l` with the last five taken in Python. All six run; a check that the fetch itself failed makes the ahead/behind reading broken rather than a stale-data pass (AC-2, AC-8).
- [x] Step 2: Implement the commit-counting logic: `git rev-list --count <sha>..HEAD` when the log's `commit-sha` frontmatter field is present; otherwise compare each commit's own date against the log's `date` field in Python (not `git log --since=`, whose boundary proved inclusive against a fixture; see spec.md AC-3) (AC-3).
- [x] Step 3: Implement the tag-date release-detection logic: `git for-each-ref refs/tags --sort=-creatordate --format='%(refname:short) %(creatordate:iso-strict)'` (not the date-only `:short` form; see spec.md AC-4), comparing each tag's creation date against the log's `date` field (AC-4).
- [x] Step 4: Implement the branch-existence check: `git branch --list <branch>` locally, `git ls-remote --heads origin <branch>` remotely. State explicitly that this is additive to the existing branch-mismatch warning in `references/handoff-display.md`, not a replacement for it (AC-5).
- [x] Step 5: Implement the continuation-prompt file-existence check, mirroring D-12's (path-citation precision) three-way scoping rule from `path-citation-check.py` with a comment naming that file as the rule's source, per D-12's spec at `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-12_path-citation-precision/spec.md`: a path-separator citation is checked and, if missing, gets a rename-hint attempt; a backtick-wrapped citation with no separator is resolved against the repo root and produces no finding either way; a bare prose word with a file extension is excluded entirely. The rename-hint command deviates from the literal `git log --follow --diff-filter=R -- <path>` this spec originally proposed, because that command finds nothing for a path missing at HEAD; see spec.md AC-6 (AC-6).
- [x] Step 6: Implement the next-action-overlap heuristic: when files touched since the log (reusing Step 2's result) overlap with path citations found in the continuation prompt, report the possibility and ask for verification. Advisory only; never a hard assertion (AC-7).
- [x] Step 7: Implement the three-state (ok, finding, broken) contract per check, mirroring the exit-code convention `path-citation-check.py` / `scripts/doc-lifecycle-check.py` / `scripts/version-parity-check.py` already use (0 ok, 1 findings, 2 broken), with a network timeout (`--fetch-timeout`, default 20 seconds per spec.md OQ3) producing broken, never a hang or a silently clean result (AC-8).
- [x] Step 8: Write `test-reconcile.py` on the `test-organize-logs.py` pattern: throwaway git fixtures in a temp directory, covering commit count by both commit-sha and date fallback, a tag cut after the log date, a branch deleted locally and remotely, a renamed file with a rename hint, a missing path with none, the file-overlap advisory, a fetch failure, a timeout, a no-mutation assertion against the actual recorded command list, and a canary that disables one rule and restores it (AC-2 through AC-9).
- [x] Step 9: Write `references/reconciliation.md`: how to invoke the script (the project root and log path as explicit arguments, the script's own path resolving against this skill's directory per the `organize-logs.py` convention), how to read `ok` / `finding` / `broken` per check, and a note that the mechanism itself lives in the script and its tests, not in this file (AC-8).

**Verification:** Run `python skills/plab-continue-session/scripts/test-reconcile.py` and confirm every check passes, including the canary. Grep `reconcile.py` for `pull`, `merge`, `checkout -`, `reset`, and `push`; no hit may appear as a command this script runs.

---

## Phase 2: Wire the reconciliation step into the workflow and display

**Goal:** Make the reconciliation step actually run during a resume, and make its output the leading section of the resumption display.

**Files:** Modify `skills/plab-continue-session/SKILL.md`, `skills/plab-continue-session/references/handoff-display.md`

**Fulfills:** AC-1, AC-5

**Steps:**
- [x] Step 1: In `SKILL.md`, insert a new phase between the current Phase 2 (Read and parse) and Phase 3 (Present the resumption context), titled "Phase 3: Reconcile against reality," directing the agent to `references/reconciliation.md`. Renumber the current Phase 3, 4, and 5 to Phase 4, 5, and 6.
- [x] Step 2: Update the References table at the bottom of `SKILL.md` to add `references/reconciliation.md`, loaded at the new Phase 3.
- [x] Step 3: In `handoff-display.md`, add a `### What changed since this log` section to the Required structure block, positioned immediately after the `## Resuming from` header and before the `**Last session:**` line (AC-1).
- [x] Step 4: Update `handoff-display.md`'s "What to include" list with a bullet for the delta section, in the same style as the existing "Waiting on you" bullet, and add a one-line note in "What to elide" clarifying that the delta reports drift, not a full re-derivation of every fact in the log (so the section stays a header, not a re-read).
- [x] Step 5: Add a sentence to the new delta section's description in `handoff-display.md` cross-referencing the existing branch-mismatch warning ("Mismatch warnings" section) and stating that the AC-5 branch-existence check is additive to it, not a replacement, so a future reader does not treat the two as duplicates and delete one.

**Verification:** Read `SKILL.md`'s Workflow section top to bottom; confirm phases are numbered consecutively 1 through 6 with no gap or duplicate, and that Phase 3 is the only new one. Read `handoff-display.md`'s Required structure block; confirm `### What changed since this log` appears in exactly the position AC-1 specifies, between the header and the facts line.

---

## Phase 3: HISTORY row and usage-README body (revised 2026-10-15: scope narrowed to this PR's own files)

**Goal:** Record this effort's behavior change in the one file this PR owns the version history for, and describe the new behavior in the skill's usage README body. Everything else version-and-release-shaped (the `metadata.version` bump itself, `CHANGELOG.md`, `AGENTS.md`, `library.json`, both plugin manifests, `manifest.generated.json`, and the root `README.md` skill table) is shared release bookkeeping that the change shipping this effort does in one place, not per-effort; see the implementation-defined report for this effort for the exact `AGENTS.md` wording proposed for that closing change.

**Files:** Modify `skills/plab-continue-session/HISTORY.md`, `docs/skills/plab-continue-session/README.md` (body only, not the `**Version:**` line)

**Fulfills:** N/A (documentation; no new capability introduced in this phase)

**Steps:**
- [x] Step 1: Add a single `1.6.0` entry to `skills/plab-continue-session/HISTORY.md`, in the same format as the existing `1.5.0` entry, with release column `unreleased` (this effort's `metadata.version` bump itself is deferred to the change that ships it; see Goal above).
- [x] Step 2: Update `docs/skills/plab-continue-session/README.md`'s body: add a subsection under "How It Works" for the new reconciliation phase, in the same per-phase style already used there, and a worked example showing the delta block from a real drift scenario. Do not touch the `**Version:**` line at the top; that bump belongs to the same shared release change as Goal above describes.

**Verification:** `git diff --stat` shows exactly `skills/plab-continue-session/HISTORY.md` and `docs/skills/plab-continue-session/README.md` touched by this phase. Confirm the README's `**Version:**` line is unchanged from before this phase ran.

---

## CI and Documentation Coverage

### CI

No CI change. CI already exists at `.github/workflows/gate.yml` (the implementation plan's original claim that "this repository has no `.github/` directory yet" was false even when drafted). This effort adds no rung-1 (CI-enforced) check. The ok / finding / broken discipline in AC-8 is implemented in `reconcile.py` and proven by its sibling `test-reconcile.py` (see Phase 1, revised 2026-10-15, and spec.md OQ4), on the same rung `organize-logs.py` / `test-organize-logs.py` occupies: canary-tested, but run by the invoking agent at skill-invocation time, never wired into `gate.yml`. The existing conformance gate (`check.mjs`) validates SKILL.md structure and frontmatter automatically; this effort introduces no new frontmatter field or schema element, so the gate needs no change to cover it.

### Agent-facing documentation

- `skills/plab-continue-session/SKILL.md`: new phase directing the agent to run `reconcile.py` and paste its output under the delta heading, later phases renumbered, References table entry.
- `skills/plab-continue-session/scripts/reconcile.py` and `skills/plab-continue-session/scripts/test-reconcile.py`: new files, the complete mechanism and its proof (AC-2 through AC-9).
- `skills/plab-continue-session/references/reconciliation.md`: new file, documenting invocation and output interpretation; it does not restate the mechanism the script and its tests already own.
- `skills/plab-continue-session/references/handoff-display.md`: new leading section in the required structure and the "What to include" / "What to elide" lists.
- `AGENTS.md`: the closing release change, not this PR, adds the `plab-continue-session` blurb's new clause (see this effort's report for the proposed wording).

These are runtime configuration read by an agent every time the skill fires; a stale line here poisons every future resumption, so precision matters more than prose polish.

### Human-facing documentation

- `docs/skills/plab-continue-session/README.md`: a new subsection under How It Works and a worked delta example under Examples (this PR); the `**Version:**` line (the closing release change, not this PR).
- `CHANGELOG.md`, root `README.md`'s skill table, `library.json`, both plugin manifests, and `manifest.generated.json`: the closing release change, not this PR.
- `skills/plab-continue-session/HISTORY.md`: the `1.6.0` entry, release column `unreleased` (this PR).

A reader returning after three months should be able to read the README's new subsection alone and understand that resuming now tells them what changed since the log was written, without needing to read this plan or the source roadmap.

---

## Rollback

Revert `SKILL.md`, `scripts/reconcile.py`, `scripts/test-reconcile.py`, `references/reconciliation.md`, `references/handoff-display.md`, `HISTORY.md`, and the README body change in a single commit revert. The effort touches no schema, no other skill, and no CI workflow, so reverting is a pure file-content rollback with no data migration. The delta is computed at resume time from live git state and is never written into the log itself, so no log produced while this effort is live needs any change if the effort is rolled back.
