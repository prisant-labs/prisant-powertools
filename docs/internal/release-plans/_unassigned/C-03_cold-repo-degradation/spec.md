---
id: C-03
title: Build Orientation From Repo Reality When No Recent Log Exists
type: spec
status: draft
created: 2026-08-23
updated: 2026-10-26
linked-effort: the maintainer's private plab-continue-session evolution roadmap, 2026-08-16
linked-plan: implementation-plan.md
ac-count: 9
source-count: 9
requires-human-review: true
target-release: null
linked-release: null
priority: P2
---

# Spec: Build Orientation From Repo Reality When No Recent Log Exists

## Task Summary

**Status:** draft
**Last updated:** 2026-08-23
**Linked plan:** `implementation-plan.md`
**Open questions:** 3 (see Open Questions / Decisions; OQ1 is load-bearing, read before implementing)
**Revisions:** 1 (initial draft; see Revisions)

### Acceptance Criteria Fulfillment

- [ ] AC-1: No-log discovery routes to cold-repo orientation instead of the two-bullet dead end
- [ ] AC-2: Orientation includes commits since the maintainer's last authored commit
- [ ] AC-3: Orientation includes open issues and PRs via `gh`, degrading silently when unavailable
- [ ] AC-4: Orientation includes README.md and AGENTS.md content when present
- [ ] AC-5: Orientation includes working-tree state via the reused hygiene-sweep Check 2 commands
- [ ] AC-6: Orientation includes capture-lite records when present, silent when absent
- [ ] AC-7: A log older than 30 days offers both stale-resume and cold-orientation paths
- [ ] AC-8: The always-on `description` field is unchanged from 1.4.0
- [ ] AC-9: The status-question carve-out is confirmed unchanged, matching release-plan decision D2

### Currently In Progress

None.

## Purpose

This effort is the roadmap's C-3 (zero-padded here to C-03 per this document set's ID convention). With 40-plus local project directories, for most repositories on most days no session log exists at all, or the newest one is old enough to be useless as a claim about current state. Today's behavior when discovery finds nothing is a two-bullet menu ("start fresh" or "name a log path"), described in the source roadmap as a dead end dressed as a choice. C-03 treats "no recent log" as a supported path: it builds orientation from commits since the maintainer's last authored commit, open issues and pull requests, README.md and AGENTS.md, working-tree state, and capture-lite records where D-04 (capture-lite consumers, shipped in v0.4.0, one release before this one) has made them consumable. This is deliberately an extension of `plab-continue-session`, not a new skill; the roadmap considered and rejected a separate cold-repo skill because it would add a third always-on description to answer a question this skill already half-answers.

**A note on the D-04 dependency.** AC-6 reads a JSONL schema that D-04's implementation, not this effort's, defines and populates. At the time this spec was written, D-04's own effort folder did not yet exist under `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/`, so D-04's own spec could not be read or cited directly; this spec instead cites the D-04 defect entry that specifies the schema (pair-defects.md, padded from the source's "D-4" to D-04) and the actual JSONL file already on disk in this repository. See the Open Questions / Decisions entry on this dependency for how it is recorded, given the frontmatter schema this document set uses has no dependency field.

**A note on the status-question trigger question.** The v0.6.0 release plan (`docs/internal/release-plans/plan_05_reconcile-at-resume/plan.md`) records its own open decision, D2, on whether this effort should restore any part of the "where were we" / "what were we doing" trigger surface that D-01 removed. D2's analysis and its current recommendation, Option A, leave the entire trigger surface unchanged in this release, exist at the release-plan level already. This spec ships consistent with that recommendation (AC-8, AC-9) rather than restating a second, independent analysis of the same question; see Open Questions below for how the two documents stay reconciled if D2 is later revised.

## Scope

### In Scope

- A cold-repo orientation path that replaces the current no-log dead end, built from five sources: authored-commit history, issues and pull requests, README/AGENTS.md, working-tree state, and capture-lite records.
- Extending the same orientation offer to a stale-log case (log exists but is more than 30 days old), alongside the existing resume-anyway option.
- A narrowed status-question carve-out in the SKILL.md body (not the always-on description) that lets a genuinely unanswerable status question reach the orientation path.
- The version 1.4.0 to 1.5.0 bump for `plab-continue-session` (shared with C-02 in the same v0.6.0 release).
- Updates to `HISTORY.md`, `CHANGELOG.md`, the skill's usage README, and `AGENTS.md`.

### Non-Goals

- Does not become a separate skill. The roadmap explicitly rejected this: a standalone cold-repo skill would add a third always-on description to answer a question this skill already half-answers.
- Does not change the trigger surface at all in this release: neither the always-on `description` field (AC-8) nor the body's "When NOT to Use" status-question guidance (AC-9). The cold-repo orientation path is reached only through the skill's existing explicit-resume triggers. This matches the v0.6.0 release plan's own D2 decision record (open, pending the maintainer, currently recommending exactly this), which this spec defers to rather than re-litigating independently; see Open Questions.
- Does not require D-04 to function. The capture-lite bullet (AC-6) is an enrichment that degrades silently when the capture directory or its records are absent, matching D-04's own explicit degradation rule.
- Does not implement C-05 (resume the arc: reading multiple logs), the roadmap's C-5, which ships in v0.8.0.
- Does not reimplement `claude --resume`. Native resume remains the cheap path when no boundary was crossed.
- Does not merge `plab-continue-session` into `plab-wrap-session`. The write/read pair separation stands.
- Does not take remediating action on anything the orientation surfaces (no auto-filing of issues, no auto-commit, no auto-pull). The orientation is display only, exactly as the existing resumption context is display only.
- Does not modify `plab-wrap-session`, which ships unchanged in v0.6.0.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer (JP) | The person entering a repository they have been away from | Reads the orientation, decides what to work on; there is no continuation prompt to confirm here, only a question about direction |
| Agent (the LLM or harness invoking `/plab-continue-session`) | Builds the orientation from available sources | Gathers each source, degrades silently when a source is unavailable, never fabricates a source it could not reach |

## Requirements

1. When discovery finds no log in any of the three stores, the skill must build orientation rather than present a dead end, per the roadmap's explicit instruction to treat "no recent log" as a supported path. [S1]
2. The orientation must draw on the specific sources the roadmap names: commits since the maintainer's last authored commit, open issues and pull requests, README and AGENTS.md, the working-tree state, and capture-lite records where available. [S1]
3. This effort must remain an extension of `plab-continue-session`, never a new skill, per the roadmap's explicit rejection of that alternative and the same reasoning already applied once in this codebase's own planning history (the maintainer's private skill-candidates memo, 2026-08-15's Candidate 4 reached the identical conclusion independently). [S1][S3]
4. Working-tree state collection must reuse the git commands already defined in `hygiene-sweep.md` Check 2, rather than defining a parallel implementation. [S7]
5. Capture-lite consumption must degrade silently when the capture directory or its records are absent, per D-04's own explicit mechanism note that both of its consumer clauses must degrade silently. [S2]
6. The always-on `description` field must not change in this release; any routing change needed to reach the orientation path through a status question must be achieved, if at all, through the SKILL.md body, which is loaded only on invocation. [S8]
7. Whether to narrow the status-question carve-out at all is a live decision tracked at the release-plan level (D2 in the v0.6.0 release plan), not this spec's to make independently. This spec ships consistent with that decision's current recommendation, leaving the carve-out unchanged, rather than pre-empting a choice the maintainer has not yet confirmed. [S9]

## Acceptance Criteria

**AC-1:** When Phase 1 discovery finds no `.md` log in any of the three stores, the skill builds and displays a cold-repo orientation instead of the current two-bullet menu ("start fresh" or "name a log path"). The interaction still ends in a question to the maintainer; what changes is that the question is informed by real repository data rather than asked in a vacuum. [S1][S4]

**AC-2:** The orientation includes commits made since the maintainer's last authored commit, found via `git log --author="$(git config user.email)" -1 --format=%H` with a fallback to matching `git config user.name` when the email-based query returns nothing (handling repositories where the maintainer has committed under a different configured email). [model-inference]

**AC-3:** Open issues and pull requests are included via the `gh` CLI (`gh issue list`, `gh pr list`) when it is installed, authenticated, and the remote is GitHub; the subsection is omitted entirely, not shown with an error, when any of those is not true. [S1][model-inference]

**AC-4:** The orientation includes a one-line summary drawn from README.md and, separately, from AGENTS.md, when each is present in the repository; a missing file is noted as absent rather than causing the orientation to fail. [S1]

**AC-5:** The orientation includes working-tree state (dirty and untracked file counts, stash list, worktree list) collected via the same commands as `hygiene-sweep.md` Check 2: `git status --short`, `git stash list`, `git worktree list`. [S1][S7]

**AC-6:** Given/When/Then. Given the `_local/_session-logs/_capture/` directory exists and contains records, when building the orientation, then the skill reports a session count and head-range since the last log (or since a fixed lookback window when no log exists at all), reading the `head`, `dirty`, `untracked`, `stashes`, `last_tag`, `commits_today`, `session_id`, and `ts` fields the hook already writes. Given that directory does not exist or contains no records, when building the orientation, then this subsection is omitted silently, with no "not found" note. [S2][S6]

**AC-7:** Given/When/Then. Given a log exists but its `date` is more than 30 days old, when the skill would otherwise present the existing age-warning-then-resume flow, then it instead offers both options explicitly (resume from the stale log with the existing warning, or build fresh cold-repo orientation instead) and proceeds only after the maintainer picks one. The 30-day threshold is distinct from, and not a replacement for, the existing 7-day soft age warning, which continues to apply unchanged to logs between 7 and 30 days old. [model-inference]

**AC-8:** The skill's YAML frontmatter `description` field is byte-for-byte unchanged from `plab-continue-session` 1.4.0: identical trigger phrases, identical do-not-fire clause, verified by a direct diff of the frontmatter block before and after this effort. [S2]

**AC-9:** The "When NOT to Use" section's status-question guidance is left byte-for-byte unchanged from `plab-continue-session` 1.4.0, matching this release's Option A resolution of the trigger-surface question recorded in the v0.6.0 release plan's D2 decision (open, pending the maintainer, but not reversed at time of writing): the cold-repo orientation path built by AC-1 through AC-7 is reached only when the skill is already invoked through an existing, unambiguous trigger, an explicit `/plab-continue-session` command or the phrases "resume," "continue," or "pick up where we left off", never through a bare status-question phrase alone. [S1][S9]

## Behavior / Examples

### Example 1: No log found, cold-repo orientation

```
## No recent session log for this repository

**Log search:** none found in `_local/_session-logs/` or the legacy paths.
**Your last commit:** 2026-05-02, `a1b2c3d`, "wire up the export flow"

### What happened since then
- 14 commits on `main` since your last authored commit, by you (9) and
  one other contributor (5)
- Open issues: 3 (#41 "export timeout on large files", #38, #36)
- Open PRs: 1 (#44, "bump dependency floor", opened 6 days ago)
- Working tree: clean, no stashes
- Capture-lite: 3 unlogged sessions recorded since 2026-05-02, heads
  a1b2c3d..f9e0111

### From the repository itself
- README: "A CLI for batch-exporting project archives."
- AGENTS.md: not found.

What would you like to work on?
```

### Example 2: Stale log, both paths offered

```
The most recent session log is from 2026-06-20 (64 days ago), well past
the point where its claims are likely still accurate.

I can:
  1. Resume from it anyway (I will still flag what has changed since,
     via the reconciliation delta).
  2. Build fresh orientation from the repository's current state instead,
     skipping the log entirely.

Which would you prefer?
```

This composes with C-02: choosing option 1 still runs C-02's reconciliation delta (its AC-1 leading section, informed by its AC-3 through AC-7 checks), so an old log is never replayed blind even when the maintainer chooses to use it.

### Example 3: A status question and an explicit resume, in the same cold repository

```
User: where were we on this one?

Agent: I don't have session-log history or current-session context for
this repository, so I can't answer that directly.
```

This is unchanged from `plab-continue-session` 1.4.0 (AC-9): the bare phrase alone does not invoke the skill's cold-repo orientation in this release, per the v0.6.0 release plan's D2 recommendation.

```
User: let's resume, or /plab-continue-session

Agent: [Phase 1 finds no log; routes to cold-repo orientation]

## No recent session log for this repository
...
```

The two interactions differ only in which phrase the maintainer used. This release deliberately does not make the first phrasing alone reach the second behavior; AC-1 through AC-7 still apply once the skill is invoked through an unambiguous trigger. See AC-9 and the release plan's D2 for the reasoning and the option this spec did not take.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | No growth to the always-on `description`; new orientation content lives only in the SKILL.md body and a new reference file, loaded on invocation | [S8] |
| Degradation | Every new information source (`gh`, capture-lite, README, AGENTS.md) must degrade silently when absent rather than erroring or displaying a conspicuous "not found" line for a source that most repositories will legitimately lack | [S2] |
| Network dependency | `gh issue list` / `gh pr list` require network access and prior authentication; the orientation must not block or hang when either is unavailable | [model-inference] |
| Schema coupling | The capture-lite field names read in AC-6 are owned by a hook outside this repository (D-04's substrate); this effort keeps the field list minimal and does not add validation for it, per D-04's own stated mitigation for this exact risk | [S2] |

## Revisions

| Date | Revision | Author |
|---|---|---|
| 2026-08-23 | Initial draft created | Claude (agent) |

## Sources & Evidence

[S1] the maintainer's private plab-continue-session evolution roadmap, 2026-08-16, section "C-3. Degrade gracefully when there is no recent log," and the "What not to do" section. Credibility A: first-party, maintainer-authored design intent, read in full. This document's C-03 is the roadmap's unpadded C-3.

[S2] the maintainer's private defect record for the wrap/continue pair, 2026-08-18, entries D-1 ("Trigger narrowing reached the router but not the program") and D-4 ("Capture-lite is a producer with zero consumers"). Credibility A: first-party, verified-against-file-and-line defect record, read in full. Padded here to D-01 and D-04 respectively; the source document uses the unpadded "D-1" and "D-4."

[S3] the maintainer's private skill-candidates memo, 2026-08-15, "Candidate 4: Cold-repo re-orientation," which independently reached the same "extend continue-session" conclusion the roadmap later adopted. Credibility A: first-party, maintainer-commissioned analysis, read in full.

[S4] `skills/plab-continue-session/references/log-discovery.md`, the current "Empty or missing directory" dead-end menu and the existing 7-day "Age warning" section this effort extends. Credibility A: shipped, in-repo, read in full.

[S5] `skills/plab-continue-session/SKILL.md`, current Phase 1 and the "When NOT to Use" section. Credibility A: shipped, in-repo, read in full.

[S6] `_local/_session-logs/_capture/2026-08.jsonl` (private to the maintainer's machine). Credibility A: directly observed real data; the field names cited in AC-6 (`ts`, `machine`, `harness`, `session_id`, `reason`, `repo`, `branch`, `head`, `dirty`, `untracked`, `stashes`, `last_tag`, `transcript`, `commits_today`) were read from actual records, not inferred from the hook's description.

[S7] `skills/plab-wrap-session/references/hygiene-sweep.md`, Check 2 ("Working-tree and worktree state"), the exact command block this effort reuses. Credibility A: shipped, in-repo, read in full.

[S8] `AGENTS.md`, line 17 (the token-economy principle) and the `plab-continue-session` blurb. Credibility A: shipped, in-repo, read in full.

[S9] `docs/internal/release-plans/plan_05_reconcile-at-resume/plan.md`, decision D2 ("Reintroducing the 'where were we' trigger"). Credibility A: the release plan aggregating this effort, read in full; its Option A recommendation is not yet confirmed by the maintainer (recorded there as open), but is the authoritative record of this exact question and this spec ships consistent with it rather than deciding independently.

### Unverified Claims

- AC-2's author-matching mechanism (`git config user.email` with a name-based fallback), AC-3's `gh` availability check, and AC-7's specific 30-day threshold are this document's own design synthesis, not specified at this level of detail by any source. They satisfy the roadmap's stated goals but should be reviewed before an agent implements them without discussion. AC-9 is no longer this spec's own inference: it defers entirely to the v0.6.0 release plan's D2 decision [S9], so the residual uncertainty (whether Option A is the final answer) lives at the release-plan level, not in this spec.

## Open Questions / Decisions

| ID | Question | Status |
|---|---|---|
| OQ1 | Should the trigger surface (description or body carve-out) eventually change to route status questions to this path more reliably? Tracked as D2 in the v0.6.0 release plan. | Open |
| OQ2 | Is 30 days the right staleness threshold, or should it be tunable, or derived from the repository's own commit cadence rather than fixed? | Open |
| OQ3 | How should the D-04 (capture-lite consumers) dependency be recorded, given this document set's frontmatter schema has no dependency field? | Resolved; recorded here |

**OQ1: Should the trigger surface eventually change to route status questions here more reliably?**
This is the tension the task explicitly flagged and asked to be handled carefully. This spec's first draft worked through the routing mechanics independently (the description is the router, evaluated before any body content is read; D-01 established that principle) and reached a body-only carve-out design. Re-reading the v0.6.0 release plan afterward surfaced that the same question is already tracked there as D2, with a more conservative recommendation, Option A: leave the entire trigger surface unchanged, including the body carve-out, and reach the orientation path only through the skill's already-existing explicit-resume triggers. This spec was revised to match D2's recommendation (AC-8, AC-9) rather than ship a design one step ahead of it.

The full two-option analysis, restoring the phrases with a body-level carve-out versus leaving the surface alone entirely, lives in D2, not here. Duplicating it in this spec would create exactly the "text contradicting text" risk this repository's conventions name as its dominant defect class: one decision recorded in two places that could quietly drift apart. This entry exists to point at the authoritative record and confirm this spec's consistency with it. If D2 is later revised (the maintainer decision is still pending at time of writing), update this spec to match rather than negotiating between two versions.

**Update, 2026-10-26.** Release plan 05 now holds no efforts, so this item is the open home of the trigger question. Release plan 05's D2 is marked Superseded and points here. Its two-option analysis stays in that plan as the record of what was weighed, and the maintainer's ruling will be recorded here. Until then, this spec stays consistent with that analysis's Option A: leave the trigger surface unchanged.

**OQ2: Threshold tuning.**
30 days is this spec's own choice; the roadmap only says "months old." Held fixed and un-configurable for v1, consistent with this plugin's stated design frame of fixed values over configurability for a single user. Revisit only if dogfooding shows 30 days is clearly wrong in either direction.

**OQ3: Recording the D-04 dependency without a frontmatter field.**
The task instruction that produced this spec asked for a `spec-dependencies` frontmatter field. The conventions governing this document set define spec.md's frontmatter as closed and explicitly instruct not to invent fields, naming this exact class of mistake as something that has already caused problems in this repository. Given the direct conflict, this spec follows the closed-schema instruction as the more specific, harder constraint, and instead records the D-04 dependency in three places in prose: the Purpose section's dependency note, Requirement 5, and this entry. A sibling effort in this same document set, `docs/internal/release-plans/_unassigned/C-05_arc-resume/spec.md` (its own Open Questions, D1), faced an identical instruction to declare a `spec-dependencies: [W-04]` field for its dependency on the digest-mode effort, and independently reached the same resolution for the same reason, which is corroborating evidence this reading of the conflict is correct rather than an isolated judgment call. If a durable, machine-checkable cross-effort dependency field is wanted, it should be added once to the shared frontmatter schema in the conventions document, not introduced ad hoc by a single spec.
