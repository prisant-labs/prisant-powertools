---
id: C-02
title: Reconcile the Session Log Against Repo Reality at Resume
type: spec
status: committed
created: 2026-08-23
updated: 2026-10-26
linked-effort: the maintainer's private plab-continue-session evolution roadmap, 2026-08-16
linked-plan: implementation-plan.md
ac-count: 9
source-count: 9
requires-human-review: true
target-release: null
linked-release: null
priority: P1
---

# Spec: Reconcile the Session Log Against Repo Reality at Resume

## Task Summary

**Status:** Committed. The maintainer approved this build on 2026-10-15 ("Go ahead and complete the work").
**Last updated:** 2026-10-20
**Linked plan:** `implementation-plan.md`
**Open questions:** 7 (see Open Questions / Decisions); none are maintainer-decided yet. OQ1 and OQ3 to OQ6 each carry a working default an agent built against under the 2026-10-15 go-ahead, and OQ7 is a defect found on 2026-10-20 with nothing built yet.
**Revisions:** 3 (initial draft, the 2026-10-15 pre-build refresh, then OQ7 on 2026-10-20; see Revisions)

### Acceptance Criteria Fulfillment

- [x] AC-1: Leading delta section exists and is positioned before "Waiting on you"
- [x] AC-2: Remote and tag state is collected by reusing hygiene-sweep Check 1's commands
- [x] AC-3: Commit count uses `commit-sha` when present, a date-based fallback otherwise
- [x] AC-4: Release-cut detection compares tag creation dates against the log's date
- [x] AC-5: Branch existence is checked locally and on the remote
- [x] AC-6: Continuation-prompt file paths are existence-checked with a rename hint on failure
- [x] AC-7: A next-action-already-done signal is surfaced as an advisory flag
- [x] AC-8: A check that cannot complete reports itself broken, never silently clean
- [x] AC-9: The reconciliation step never mutates repository state

### Currently In Progress

None.

## Purpose

This effort is the roadmap's C-2 (zero-padded here to C-02 per this document set's ID convention). `plab-continue-session`, at 1.5.0 as of this revision, replays a session log's claims without checking them against the repository. C-02 closes that gap: at resume, the skill derives current repository state (commits, tags, branch existence, file existence) and diffs it against what the log claimed, then leads the resumption display with that delta rather than burying it below the fold. This corrects a named asymmetry: `plab-wrap-session`, at 1.7.0 as of this revision, already runs a pre-wrap hygiene sweep that checks remote divergence and release state before writing a log, and the read side has never run the equivalent check before acting on one. This effort adds no capability to `plab-wrap-session`, which this effort does not touch; versions are assigned to skills only at ship time, per decision register entry 21 (versions assigned at ship time), so this document says "the release that ships it" rather than naming a release ladder.

## Scope

### In Scope

- A new canary-tested script, `skills/plab-continue-session/scripts/reconcile.py`, plus its sibling test file, implementing the git commands, the fallback logic for logs missing optional fields, and the explicit broken-state reporting rule (see the "Design change" revision below; this replaces the documented-convention design the implementation plan originally proposed).
- A new reference file documenting how to invoke the script and interpret its output.
- An update to the resumption display's required structure so the delta leads it.
- The version 1.5.0 to 1.6.0 bump for `plab-continue-session` (this effort's `HISTORY.md` row only; the `metadata.version` bump itself, `CHANGELOG.md`, the skill's usage README version line, and `AGENTS.md` are shared release bookkeeping done by whichever change ships this effort).
- An update to the body of the skill's usage README describing the new behavior.

### Non-Goals

- Does not modify `plab-wrap-session`. This effort touches none of its files; whatever version it is carrying when this effort ships is unaffected by this change.
- Does not reimplement `claude --resume`. Native resume remains the cheap path when no boundary was crossed; this skill's territory stays the cross-machine, cross-agent, cross-time gap, per the roadmap's "What not to do" section.
- Does not merge `plab-continue-session` into `plab-wrap-session`. The write/read pair separation stands.
- Does not implement C-04 (consumption disposition: fulfilled, superseded, or ignored), the roadmap's C-4. This effort's delta output is a natural future input to that disposition tracking, but no wiring between them is built now.
- Does not implement C-05 (resume the arc: reading multiple logs), the roadmap's C-5.
- Does not take remediating action on any finding. No auto-pull, no auto-checkout, no edit to the log being resumed from. The delta is diagnostic display only (AC-9).
- Does not add a CI-enforced detector. `reconcile.py` is canary-tested by its sibling `test-reconcile.py`, exactly as `organize-logs.py` is tested by `test-organize-logs.py`, but neither script runs in CI: both are agent-run at skill-invocation time, never wired into `.github/workflows/gate.yml`. See the "Design change" revision below and OQ4.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer (JP) | The person resuming work in a repository | Reads the delta block, decides whether to proceed with the log's named next action, redirect, or investigate a flagged discrepancy further |
| Agent (the LLM or harness invoking `/plab-continue-session`) | Executes the reconciliation and presents it | Runs the git checks, computes the delta, reports a broken check honestly instead of silently omitting it, never acts on a finding without the maintainer's confirmation |

## Requirements

1. At resume, before any log content is presented as though it were current, the skill must derive live repository state and compare it against what the log claims, per the roadmap's central instruction to "derive the current state and diff it against the log's claims, then lead with the delta." [S1]
2. The comparison must cover, at minimum, the five categories of drift the roadmap names explicitly: commits landed, a release cut elsewhere, the named next action already done, the branch moved or no longer existing, and a file the continuation prompt points at having been renamed. [S1]
3. Remote and tag state collection must reuse the git command sequence already defined and shipped in `hygiene-sweep.md` Check 1, rather than defining a parallel implementation, per the explicit instruction to reuse rather than reinvent. [S3]
4. The mechanism must work uniformly across logs written with and without the optional `commit-sha` field, since that field is Tier 3 ("nice to have") today and `plab-wrap-session` is unchanged in this release, so a log lacking it is a normal case this effort must handle, not an edge case it can ignore. [S7]
5. Any check that cannot complete (network unavailable, git command errors, a fetch that times out) must report its own failure explicitly. The absence of a finding must never be presented in a way indistinguishable from a verified clean result. [S2]
6. The effort must not add any capability for the skill to modify repository state. The existing "never modify the session log being resumed from" and related constraints continue to apply to the new step. [S4]
7. The effort must not grow the skill's always-on YAML `description`. All new instruction content belongs in the SKILL.md body and a new reference file, both of which are loaded only on invocation, consistent with this repository's standing token-economy principle. [S8]

## Acceptance Criteria

**AC-1:** A new leading section, titled "What changed since this log," appears in the resumption display between the `## Resuming from` header and the `**Last session:**` facts line, ahead of `### Waiting on you`. [S1]

**AC-2:** The delta's remote-and-tag content (branch ahead/behind counts versus its remote, remote branches with no local counterpart, and the last five tags) is produced using the same command sequence as `hygiene-sweep.md` Check 1, with one deliberate deviation: `git fetch --no-prune origin --tags` (not a plain `git fetch origin --tags`), `git status -sb`, `git log --oneline HEAD..@{u}`, `git log --oneline @{u}..HEAD`, `git ls-remote --heads origin`, and `git tag -l` (the last five taken in Python rather than by piping to `tail -5`, since there is no shell pipe at this call site). All six commands run; `test-reconcile.py` asserts their presence in the script's own recorded command list, not merely a subset chosen for convenience. The fetch gains `--no-prune` because a plain fetch prunes whenever `fetch.prune` is set in git config, and on 2026-09-25 a pruning fetch deleted a remote-tracking ref without confirmation, recorded in sibling spec W-02 (derived log facts), decision D4, tested 2026-10-05. If the fetch itself does not succeed, the ahead/behind reading is reported broken rather than computed off a potentially stale `@{u}`, since `@{u}` reflects whatever was fetched last time. [S1][S3]

**AC-3:** Commits landed since the log was written are counted correctly whether or not the log's `commit-sha` field is present: via `git rev-list --count <sha>..HEAD` when present, or by comparing each commit's own date against the log's `date` field in Python when absent, on the log's branch (falling back to `HEAD` with an explicit note if that branch no longer exists locally; see OQ6). The date-fallback path does not use `git log --since=<date>`: that flag's boundary proved inclusive in practice (verified in `test-reconcile.py`), which double-counts the exact commit a wrap session logs against whenever the log's timestamp and that commit's timestamp coincide to the second, the common case since a wrap is normally written immediately after the last commit. [model-inference]

**AC-4:** A release cut after the log was written is detected by comparing each tag's creation date (`git for-each-ref refs/tags --sort=-creatordate --format='%(refname:short) %(creatordate:iso-strict)'`, not the date-only `%(creatordate:short)`) against the log's `date` frontmatter field, independent of any tag information recorded in the log itself. The precision was widened from date-only to a full timestamp comparison because a date-only format would false-positive a tag cut earlier the same calendar day as the log. [model-inference]

**AC-5:** The delta reports whether the log's `branch` field still exists, both locally (`git branch --list <branch>`) and on the remote (`git ls-remote --heads origin <branch>`). This check is additive to, and distinct from, the existing current-branch-mismatch warning already defined in `references/handoff-display.md`, which only fires when the current branch differs from the log's branch and says nothing about whether the log's branch still exists at all. [model-inference]

**AC-6:** A file path named in the continuation prompt is scoped for checking using the same three-way rule D-12 (path-citation precision) already adopted: a citation containing a path separator is checked for existence and, if missing, gets a rename-hint attempt before being reported as missing; a backtick-wrapped citation with no separator is resolved against the repository root and produces no finding whether it resolves or not, matching D-12's own adopted behavior for that branch exactly rather than a looser reading of it; a bare prose word carrying a file extension, with neither signal, is excluded from checking entirely. The rename-hint attempt deviates from the literal command this spec originally proposed (`git log --follow --diff-filter=R -- <path>`): verified empirically against a fixture that this finds nothing, because `--follow` tracks a path that exists at the tip of history backward through renames, and a citation to a path missing at HEAD because it was renamed away needs the opposite direction. Restricting by pathspec at all turns out to be the defeating factor, not `--follow` specifically, so the implemented hint scans every rename record in history with no pathspec (`git log --diff-filter=R --name-status --format=%H`) and matches the old name in Python. [S2][S9]

**AC-7:** Given/When/Then. Given a continuation prompt naming a next action tied to specific files, when commits have landed since the log that touch those same files, then the delta states that the named next action may already be complete and asks the maintainer to verify before proceeding, rather than asserting completion as fact. [model-inference]

**AC-8:** Given/When/Then. Given any step of the delta computation cannot complete (git unavailable, the fetch fails, the fetch times out, the repository is offline), when the resumption display is produced, then the delta section names which specific check failed and states that reconciliation is incomplete, rather than omitting the section or presenting an unqualified "no changes found" result. [S2]

**AC-9:** The reconciliation step executes no git command that mutates repository state: no `pull`, `merge`, `checkout`, `reset`, `push`, or equivalent appears anywhere in the delta's command set. [S4]

## Behavior / Examples

### Example 1: Drift found, log resumed with informed context

```
## Resuming from: 2026-08-10_09-15_claude_v1.9.0-prep.md

### What changed since this log

Log written 2026-08-10 at `fa13177`. Since then: 4 commits on `main`
(3 local, 1 pulled from origin), tag `v1.9.0` cut from another checkout,
and `skills/plab-guide/SKILL.md`, named in the continuation prompt's next
action, was modified in commit `9c2a441`. The stated next action ("bump
plab-guide's version line") may already be complete; verify before
repeating it.

**Last session:** 2026-08-10T09:15:00-07:00, claude opus 4.6, status `completed`
**Summary:** Prepped the v1.9.0 release notes
**Branch:** `main`

### Waiting on you
...
```

This mirrors the worked example already in the source roadmap and adds the file-overlap advisory from AC-7. [S1]

### Example 2: Reconciliation cannot complete

```
## Resuming from: 2026-08-15_14-02_claude_docs-cleanup.md

### What changed since this log

Reconciliation incomplete: `git fetch origin --tags` did not return
(offline or origin unreachable). Local-only facts: no new commits on
`main` since this log's date. Remote state, tags, and branch existence
on the remote could not be verified this run.

**Last session:** 2026-08-15T14:02:00-07:00, claude opus 4.6, status `completed`
...
```

The section still appears, still names what it could and could not verify, and never implies a clean result it did not earn (AC-8).

### Example 3: Branch no longer exists

```
### What changed since this log

Log written 2026-08-01 on branch `feature/spec-gates`. That branch no
longer exists locally or on origin; it was likely merged and deleted.
Currently on `main`. Confirm before resuming whether this work already
landed.
```

This is distinct from the existing branch-mismatch warning (which fires when the current branch merely differs from the log's) because here the log's branch is gone entirely (AC-5).

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | No growth to the always-on `description`; new instruction content lives only in the SKILL.md body and a new reference file, loaded on invocation | [S8] |
| Latency | `git fetch origin --tags` adds a network round trip at the start of a session, when the maintainer wants to get moving; the check must be time-boxed and degrade to the AC-8 broken-state report rather than hang indefinitely | [S3] |
| Reliability | The delta must not fail open: a git command that errors must produce an explicit "could not verify" state, never a silently-empty "no changes" result | [S2] |
| Compatibility | The mechanism must produce correct output for logs written by `plab-wrap-session` 1.2.0 through the current version, including logs that predate `commit-sha` ever being populated | [S7] |

## Revisions

| Date | Revision | Author |
|---|---|---|
| 2026-08-23 | Initial draft created | Claude (agent) |
| 2026-10-15 | Pre-build refresh under the maintainer's 2026-10-15 go-ahead ("Go ahead and complete the work"), before implementation. Status moved draft to committed. Stale facts corrected: `plab-continue-session` was 1.4.0/1.5.0 in the draft's framing and is 1.5.0 now (this effort takes it to 1.6.0, not 1.5.0); `plab-wrap-session` was described as reaching 1.6.0 and is 1.7.0 now; the "release ladder" and specific release numbers (v0.4.0, v0.6.0, v0.8.0, v0.9.0) are obsolete because versions are assigned to skills only at ship time, per decision register entry 21 (versions assigned at ship time), so every such reference now reads "the release that ships it"; the implementation plan's claim that "this repository has no `.github/` directory yet" was false even when the plan was drafted, since CI already exists at `.github/workflows/gate.yml`. AC-2's fetch command gained `--no-prune` (see AC-2) because a plain fetch prunes when `fetch.prune` is set in git config, which deleted a remote-tracking ref without confirmation on 2026-09-25 (sibling spec W-02, decision D4, tested 2026-10-05). AC-4's tag-date comparison moved from `creatordate:short` to `creatordate:iso-strict` (see AC-4). AC-6's rename-hint command dropped `--follow` after it was proved empirically not to find a rename for a path missing at HEAD (see AC-6). Design change: reconciliation is implemented as a canary-tested script (`skills/plab-continue-session/scripts/reconcile.py`) with a sibling test file (`test-reconcile.py`), not the rung-3 documented convention the implementation plan originally specified; see OQ4. The Open Questions / Decisions section below was reformatted into this plugin's standard decisions-section form (`references/decisions-section.md`) and gained OQ4, OQ5 and OQ6 for decisions an agent took on the maintainer's behalf; none of OQ1, OQ3, OQ4, OQ5 or OQ6 is maintainer-decided, each carries a working default the build proceeded on. | Claude (agent) |
| 2026-10-20 | Added OQ7 (`reconcile.py` ignores `commit-range`), a defect found on the first resume after the v0.9.0 rename. The commit check reads only `commit-sha`, which the wrap never writes, so a pull request merged during a wrap reads as landing after the log. Recorded here so the `--backlog` sweep sees it. Nothing else in the spec changed. | Claude (agent) |

## Sources & Evidence

[S1] the maintainer's private plab-continue-session evolution roadmap, 2026-08-16, section "C-2. Reconcile the log against reality, do not just replay it." Credibility A: first-party, maintainer-authored design intent, read in full. This document's C-02 is the roadmap's unpadded C-2.

[S2] the maintainer's private defect record for the wrap/continue pair, 2026-08-18, entries D-11 ("The Log Self-Check gates are two-state and can fail open") and D-12 ("The path-existence gate treats bare filenames as repo-relative paths"). Credibility A: first-party, verified-against-file-and-line defect record, read in full. D-11 and D-12 are already two-digit in the source and need no repadding; this spec follows the same precision rule D-12 established for its own gate rather than restating a looser one.

[S3] `skills/plab-wrap-session/references/hygiene-sweep.md`, Check 1 ("Remote reconciliation"), the exact command block this effort reuses. Credibility A: shipped, in-repo, read in full.

[S4] `skills/plab-continue-session/SKILL.md`, the current Phase 1 through Phase 5 workflow and the Constraints section (including "Never modify the session log being resumed from"). Credibility A: shipped, in-repo, read in full.

[S5] `skills/plab-continue-session/references/log-discovery.md`, the existing age-warning (7-day threshold) and repo/branch-mismatch mechanisms this effort extends without replacing. Credibility A: shipped, in-repo, read in full.

[S6] `skills/plab-continue-session/references/handoff-display.md`, the current required display structure this effort adds a leading section to. Credibility A: shipped, in-repo, read in full.

[S7] `skills/plab-wrap-session/references/frontmatter-schema.md`, Tier 2 (`resumed-from`) and Tier 3 (`commit-sha`) field definitions. Credibility A: shipped, in-repo, read in full.

[S8] `AGENTS.md`, line 17: "Always-on context cost is paid by one person in every session, forever." Credibility A: shipped, in-repo, read in full.

[S9] `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-12_path-citation-precision/spec.md`, AC-1 through AC-3, the committed three-way scoping rule (path separator checked and flagged; backtick-wrapped-no-separator resolved with no finding either way; bare word excluded entirely). Credibility A: a sibling effort's own spec in this document set, read in full; cited directly rather than re-deriving the rule from the underlying roadmap entry, since D-12 already resolved the ambiguity in the source prose that its own Open Questions section flags.

### Unverified Claims

- AC-3, AC-4, AC-5, AC-7, and the rename-hint half of AC-6 (the git-level mechanisms for the commit-sha/date fallback, the tag-creation-date comparison, the branch-existence check, the file-overlap heuristic, and the rename-hint attempt on a missing path) were not themselves named at this level of detail in any source; they were this document's own design synthesis, flagged for review before an agent implemented them without discussion. The maintainer's 2026-10-15 go-ahead ("Go ahead and complete the work") is the review this flag asked for: see OQ5 below, which records that authorization and the two mechanism deviations testing against a fixture surfaced while building AC-4 and AC-6 (see the 2026-10-15 Revisions row, and AC-4/AC-6 above). AC-6's scoping rule itself (which citations get checked at all) remains non-inferential: it cites D-12's committed spec [S9] directly.

## Open Questions / Decisions

This section follows `references/decisions-section.md`. None of the items below is maintainer-decided. OQ1 to OQ6 each carry a working default an agent built against under the maintainer's 2026-10-15 go-ahead; the maintainer's next walk through this document is expected to rule on each one explicitly. OQ7 was added on 2026-10-20 as a defect report, and nothing has been built for it.

**Update, 2026-10-26.** JP approved closing OQ1 and OQ3 to OQ6 as one batch, after a read-only check confirmed that each working default shipped and still holds. OQ7 is still `Open`, and OQ2 stays `Deferred`.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| OQ1 | Hard-block or advisory-only for the next-action-already-done signal | Option A: advisory only | Decided | 2026-10-26 |
| OQ2 | Promote `commit-sha` from Tier 3 to Tier 1 on the wrap side | Deferred to a future `plab-wrap-session` effort | Deferred | 2026-08-23 |
| OQ3 | Fetch timeout budget for the network checks | Option A: 20 seconds, set by `--fetch-timeout` | Decided | 2026-10-26 |
| OQ4 | Implement reconciliation as a script, or as a documented convention | Option A: a canary-tested script | Decided | 2026-10-26 |
| OQ5 | Build AC-3, AC-4, AC-5, AC-7 and AC-6's rename hint as specified, without a separate per-mechanism maintainer review | Option A: built as specified, deviations disclosed | Decided | 2026-10-26 |
| OQ6 | AC-3's date-fallback base ref when the log's branch no longer exists locally | Option A: fall back to `HEAD`, named in the output | Decided | 2026-10-26 |
| OQ7 | `reconcile.py` ignores `commit-range`, so commits merged during a wrap read as new | (none) | Open | 2026-10-20 |

### OQ1: Hard-block or advisory-only for the next-action-already-done signal (Decided)

**Summary.** Whether AC-7's overlap signal should ever refuse to proceed with the named next action, rather than only flagging it.

**Context.** The roadmap's own worked example treats this as informational ("The stated next action may already be complete"). The underlying signal is a heuristic (file-path overlap between recent commits and continuation-prompt text), not a certainty.

**Desired outcome.** A maintainer resuming work is warned when the next action may already be done, without being blocked by a false positive.

**Options / approaches.**

* **Option A:** Advisory only. Surface the possibility and ask the maintainer to verify; never refuse to proceed.
* **Option B:** Hard-block. Refuse the named next action until the maintainer explicitly overrides.

**Recommendation.** Option A, because a false hard-block on a heuristic this coarse would cost more than a false advisory note; revisit after dogfooding shows the heuristic's actual false-positive rate. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** Decided 2026-10-26 by JP
>
> * **Status:** Decided
> * **Choice:** Option A, advisory only.
> * **Reasoning:** The working default shipped and still holds. `skills/plab-continue-session/scripts/reconcile.py` marks the next-action overlap signal as advisory, and the signal never blocks the named next action.
> * **Follow-up:** None needed.
> * **Decided by / date:** JP / 2026-10-26, approving a batch of closures after a read-only check on 2026-10-25 confirmed that the working default shipped and still holds.

### OQ2: Promote `commit-sha` from Tier 3 to Tier 1 on the wrap side (Deferred)

**Summary.** Whether `plab-wrap-session` should eventually promote `commit-sha` from Tier 3 to Tier 1, removing the need for AC-3's date-based fallback.

**Context.** AC-3's fallback exists specifically because `commit-sha` is Tier 3 today and this effort does not touch `plab-wrap-session`. A Tier 1 promotion would collapse AC-3 to a single code path, but that is a `plab-wrap-session` change, out of scope here, and needs its own effort whenever wrap is next open for change.

**Desired outcome.** Noted for whoever next plans a `plab-wrap-session` effort.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Deferred
> * **Choice:** Deferred to a future `plab-wrap-session` effort
> * **Reasoning:** Out of scope for this effort; `plab-wrap-session` is not touched here.
> * **Decided by / date:** (none)

### OQ3: Fetch timeout budget for the network checks (Decided)

**Summary.** What the exact timeout budget should be for `git fetch --no-prune origin --tags` and the `git ls-remote` calls before a check reports itself broken rather than hanging.

**Context.** `hygiene-sweep.md`'s own resolution protocol says to time-box the sweep without naming a number [S3]. Resume-time latency tolerance (a session just starting) may differ from wrap-time tolerance (a session already ending) in ways no source has measured.

**Desired outcome.** A number that fails fast on a dead or slow remote without false-triggering on an ordinary network round trip.

**Options / approaches.**

* **Option A:** 20 seconds, applied uniformly to the fetch and all three `ls-remote` calls, exposed as a `--fetch-timeout` CLI argument so it can be changed without editing the script.
* **Option B:** A shorter budget (5 to 10 seconds), trading a higher false-broken rate on a slow connection for a faster resume on a dead one.

**Recommendation.** Option A: `reconcile.py` implements `--fetch-timeout` defaulting to 20 seconds. `test-reconcile.py` proves the timeout path reports broken, never a silent hang or a silently clean result, using a deliberately tiny override. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** Decided 2026-10-26 by JP
>
> * **Status:** Decided
> * **Choice:** Option A, 20 seconds.
> * **Reasoning:** The working default shipped and still holds. `skills/plab-continue-session/scripts/reconcile.py` defaults `--fetch-timeout` to 20 seconds.
> * **Follow-up:** None needed.
> * **Decided by / date:** JP / 2026-10-26, approving a batch of closures after a read-only check on 2026-10-25 confirmed that the working default shipped and still holds.

### OQ4: Implement reconciliation as a script, or as a documented convention (Decided)

**Summary.** The implementation plan this effort started from made reconciliation a rung-3 documented convention, on the grounds that `plab-continue-session` "has no independent execution runtime ... so there is no standalone script for a canary to test against."

**Context.** That reasoning no longer holds: `plab-wrap-session` already ships agent-run scripts with sibling test files (`organize-logs.py` / `test-organize-logs.py`, `path-citation-check.py`), and a 2026-10-01 measurement found that the number of tool calls drives a wrap's or resume's cost far more than text length, which undercuts the token-cost argument a convention-only design implicitly leaned on.

**Desired outcome.** The nine AC-2 through AC-9 checks are provably correct and provably regression-tested, the same bar `organize-logs.py` clears, rather than resting on an agent re-reading prose correctly every run.

**Options / approaches.**

* **Option A:** Build `skills/plab-continue-session/scripts/reconcile.py` plus `test-reconcile.py`, on the `organize-logs.py` / `test-organize-logs.py` pattern: stdlib-only, takes the project root and log path as arguments, `--json` and Markdown output, a canary-tested rename-hint and path-citation classifier mirrored from `path-citation-check.py`. Stays out of CI, exactly like `test-organize-logs.py`.
* **Option B:** Keep the documented-convention design the implementation plan originally specified.

**Recommendation.** Option A, for the reasons in Context. Implemented: `skills/plab-continue-session/scripts/reconcile.py` and `skills/plab-continue-session/scripts/test-reconcile.py`. The spec's own Non-Goal about a CI-enforced, canary-tested detector is narrowed accordingly (the script stays out of CI; see Non-Goals above). Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** Decided 2026-10-26 by JP
>
> * **Status:** Decided
> * **Choice:** Option A, a script.
> * **Reasoning:** The working default shipped and still holds. `skills/plab-continue-session/scripts/reconcile.py` and its sibling `test-reconcile.py` shipped in `plab-continue-session` 1.6.0, in v0.8.0.
> * **Follow-up:** None needed.
> * **Decided by / date:** JP / 2026-10-26, approving a batch of closures after a read-only check on 2026-10-25 confirmed that the working default shipped and still holds.

### OQ5: Build AC-3, AC-4, AC-5, AC-7 and AC-6's rename hint as specified, without a separate per-mechanism maintainer review (Decided)

**Summary.** This spec's own Unverified Claims section flagged AC-3, AC-4, AC-5, AC-7 and AC-6's rename-hint mechanism for review before an agent implemented them, since none is named at this level of detail in any source document.

**Context.** The maintainer's 2026-10-15 instruction ("Go ahead and complete the work") was given with this flag already pointed out in the effort brief, as a go-ahead to build rather than a line-by-line sign-off on each mechanism. Building surfaced two further mechanism corrections against the literal spec text: AC-4's tag-date comparison needed `creatordate:iso-strict` rather than `creatordate:short` to avoid a same-day false positive, and AC-6's rename hint needed to drop `--follow` and the pathspec restriction entirely, because neither finds a rename for a path missing at HEAD (verified empirically in `test-reconcile.py`; see AC-4 and AC-6 above).

**Desired outcome.** The flagged mechanisms are built and tested now, with every deviation from the literal spec text disclosed in the spec itself, rather than leaving the effort blocked on a mechanism-by-mechanism maintainer review the go-ahead was already meant to clear.

**Options / approaches.**

* **Option A:** Build as specified, with the AC-4 and AC-6 deviations disclosed in this document and proven in `test-reconcile.py`.
* **Option B:** Pause before implementation for a line-by-line maintainer review of each flagged mechanism.

**Recommendation.** Option A, given the go-ahead already covers this review and a further pause would block the effort on a formality the maintainer's instruction already addressed. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** Decided 2026-10-26 by JP
>
> * **Status:** Decided
> * **Choice:** Option A, built as specified.
> * **Reasoning:** The flagged mechanisms were built under the 2026-10-15 go-ahead without a separate line-by-line review. Later concerns about them have arrived as defect reports, such as OQ7, rather than as a blocking review.
> * **Follow-up:** None needed. A later defect in one of these mechanisms is recorded as its own item, as OQ7 is.
> * **Decided by / date:** JP / 2026-10-26, approving a batch of closures after a read-only check on 2026-10-25 confirmed that the working default shipped and still holds.

### OQ6: AC-3's date-fallback base ref when the log's branch no longer exists locally (Decided)

**Summary.** When a log has no `commit-sha` field and its `branch` field names a branch that no longer exists locally (the drift AC-5 exists to catch), what should AC-3's date-based commit count be measured against.

**Context.** `git log` needs some ref to count commits on. The log's own branch is gone, by construction of this exact scenario.

**Desired outcome.** AC-3 and AC-7 (which reuses AC-3's touched-files list) still produce a usable result in this case, rather than going broken every time AC-5 finds a deleted branch.

**Options / approaches.**

* **Option A:** Fall back to `HEAD`, with an explicit note in the check's own detail message naming the substitution.
* **Option B:** Report `commits_since` (and therefore `next_action_overlap`) as broken, on the grounds that there is no agreed base to count from once the log's own branch is gone.

**Recommendation.** Option A: implemented in `reconcile.py`. A broken result here would also suppress the next-action-overlap advisory on exactly the resume where a deleted branch makes that advisory most worth seeing, and `HEAD` is the best available substitute as long as the substitution stays visible in the output. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** Decided 2026-10-26 by JP
>
> * **Status:** Decided
> * **Choice:** Option A, fall back to `HEAD`.
> * **Reasoning:** The working default shipped and still holds. When the log's branch no longer exists locally, `skills/plab-continue-session/scripts/reconcile.py` counts against `HEAD` and says so in the check's own output.
> * **Follow-up:** None needed.
> * **Decided by / date:** JP / 2026-10-26, approving a batch of closures after a read-only check on 2026-10-25 confirmed that the working default shipped and still holds.

### OQ7: `reconcile.py` ignores `commit-range`, so commits merged during a wrap read as new (Open)

**Summary.** Whether `reconcile.py` should anchor its commit count on the end SHA of the log's `commit-range` field, and call remote commits unreflected only when the local branch is actually behind.

**Context.** The first resume after the v0.9.0 rename, on 2026-10-20, exposed two faults in `skills/plab-continue-session/scripts/reconcile.py`.

* **The commit check never sees a SHA.** It reads only `commit-sha` (line 478), a Tier 3 field the wrap does not write, so every log from `plab-wrap-session` 1.8.0 onward takes AC-3's date fallback. Since 1.8.0, `derive-log-facts.py` writes `commit-range` as a Tier 1 field, so the anchor this check needs is already in every new log. The date fallback misfires because a log's `date` comes from the system clock when the wrap starts. A pull request merged during the wrap therefore counts as landing after the log.
* **The remote wording is wrong.** The detail message at line 552 says remote commits are "not yet reflected in the local branch". The count behind it, `remote_count`, is every commit on the remote branch since the anchor, not the commits missing locally. The real behind figure is computed separately at line 536.

The reproduction is the resume of `2026-10-19_19-28_claude_rename-closed-split-repaired-lifecycle-baseline.md`, which reported two findings. Both were false. The two commits were PR #45's own, `46d8877` at 20:19 and its merge `0802aac` at 20:22, and the log lists them in `commit-range: 21bca39..0802aac`. `HEAD` and `origin/main` were the same SHA. Rerunning the installed 0.9.0 script on a copy of that log with `commit-sha: 0802aac` added returned all nine checks `[ok]`, which confirms the cause.

This item changes the ground under OQ2. OQ2 deferred promoting `commit-sha` on the wrap side, and wrap 1.8.0 has since added an anchor of its own in `commit-range`. The gap now lies on the read side. Whether OQ2 becomes Superseded is left to the maintainer's walk.

**Desired outcome.** A resume reports commits since the log only when they landed after the last commit the log records. It reports remote commits as unreflected only when the local branch is behind its remote.

**Options / approaches.**

* **Option A:** When `commit-sha` is absent, take the right-hand SHA of `commit-range` as the anchor. Print "not yet reflected" only when the behind count is above zero. The canary is the 2026-10-20 reproduction: the same log must produce a finding without the anchor and none with it. The trade-off is that the anchor is only as fresh as the wrap's derivation run, so a merge after that run would still count as new.
* **Option B:** Keep the date fallback and fix only the wording. Every wrap that merges a pull request then keeps producing a false "commits since the log" finding at the next resume.
* **Option C:** Promote `commit-sha` to Tier 1 on the wrap side, as OQ2 proposed. This duplicates a SHA that `commit-range` already carries, and it changes two skills instead of one.

**Recommendation.** Option A. It is a read-side change of a few lines in one script, and its canary already exists. Build it in the first wrap-and-continue release after the rename, beside W-05 (wrap ordering) and the citation-checker fix. Confidence: high on the cause, verified by the rerun; medium on the release placement.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
