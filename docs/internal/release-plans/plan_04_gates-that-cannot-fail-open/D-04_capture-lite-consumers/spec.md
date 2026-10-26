---
id: D-04
title: Consume capture-lite records in wrap and continue
type: spec
status: fulfilled
created: 2026-08-23
updated: 2026-10-26
linked-effort: the maintainer's private defect record for the wrap/continue pair, 2026-08-18
linked-plan: implementation-plan.md
ac-count: 7
source-count: 5
requires-human-review: true
target-release: v0.4.0
linked-release: docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md
priority: P2
---

# Spec: Consume capture-lite records in wrap and continue

## Task Summary

Status: Fulfilled
Last updated: 2026-08-24
Linked plan: implementation-plan.md
Open questions: 3 (see Open Questions / Decisions)
Revisions: 1 (see Revisions)

### Acceptance Criteria Fulfillment

- [x] AC-1: Capture absent means no mention, wrap side
- [x] AC-2: Wrap reports unwrapped-session count and head range in Outstanding Issues
- [x] AC-3: Null `session_id` records are excluded from the count
- [x] AC-4: Continue's no-log-found path surfaces a capture orientation line
- [x] AC-5: Continue's stale-log path surfaces a capture count
- [x] AC-6: Capture absent means unchanged output, continue side
- [x] AC-7: Public skill text references only the five consumed field names

### Currently In Progress

None.

## Purpose

D-04 (capture-lite consumers) wires the capture-lite SessionEnd hook's JSONL records into the two
skills that can use them: wrap gains a count of sessions since the last log that were never wrapped,
and continue gains an orientation substrate on its no-log-found and stale-log paths. The hook, W-1
(capture-lite hook), already writes real records to `_local/_session-logs/_capture/`; grepping the
skills and docs for any reference to reading them returns nothing today, a producer with zero
consumers. D-04 is the roadmap's D-4.

## Scope

### In Scope

- Wrap: an Outstanding Issues report of the unwrapped-session count and head range, in deep and final
  modes, when qualifying capture records exist.
- Continue: an orientation line on the no-log-found path and the stale-log (7+ day) path, when
  qualifying capture records exist.
- Silent degradation, no error, no mention, when `_local/_session-logs/_capture/` does not exist or
  contains no qualifying records.
- A skip rule excluding records with a null `session_id` from any count.
- Minimal field references: both skills' public text names only `ts`, `head`, `session_id`, `branch`,
  and `commits_today` from the capture-lite schema.
- Version bump and `HISTORY.md` entries for both skills.

### Non-Goals

- Wrap does not use capture records to ground the current session's own facts. The hook fires on
  `SessionEnd`, so the current session's own record does not exist yet at wrap time; git stays
  authoritative for this-session facts exactly as it is today.
- No new script. This effort is prose only, in both skills' SKILL.md and reference files.
- No change to the hook itself. It lives outside this repository, under the user's home directory, as
  optional machine-local infrastructure; this repo cannot and does not modify it.
- No automated fix for the `test-123` junk record currently in the capture JSONL. That is a one-off
  manual deletion for the maintainer, unrelated to skill behavior, and out of this effort's scope.
- No enumeration of the hook's full JSONL schema (`harness`, `reason`, `last_tag`, `transcript`,
  `dirty`, `untracked`, `stashes`) in either skill's public text.
- No new consumer beyond these two. W-2 (derived log-facts layer) and W-4 (digest mode) are separate,
  later efforts (v0.7.0 and v0.8.0 respectively) and are not touched here.
- No standing CI gate for the field-minimality mitigation. The source states plainly that the
  mitigation is field discipline, not built validation, "since both ends have the same owner."
- Quick and blocked mode wraps do not run the capture check. This follows from structure, not
  preference: neither mode's body template has an Outstanding Issues section at all (see Requirement 1
  and Open Questions, OQ1).

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer (JP) | Reads the unwrapped-session count and the orientation lines | No confirmation needed; this is a report, not a proposed mutation |
| Wrapping agent | Reads capture records, computes the filtered count and head range | Runs Evidence Gathering, writes Outstanding Issues |
| Continuing agent | Reads capture records on the no-log or stale-log path | Runs Phase 1, surfaces the orientation line alongside its existing message |

## Requirements

1. Wrap determines the newest existing log's timestamp from its filename, using the same newest-wins
   sort already defined in `references/log-discovery.md`; only the filename is needed, not the log's
   content, so this requires no new "read the previous log" capability. This runs in deep and final
   modes only, the two modes whose body template includes an Outstanding Issues section at all.
   [S1, S3, model-inference: mode scope]
2. When the capture store exists, wrap reads every `.jsonl` file under
   `_local/_session-logs/_capture/` (there may be more than one, roughly one per month), filters to
   records with a non-null `session_id` and a `ts` after the newest existing log's timestamp (or, if no
   existing log exists at all, every qualifying record), and if any remain, reports the count and the
   earliest-to-latest `head` among them in the new log's Outstanding Issues section. [S1, S5]
3. Outstanding Issues, not Hygiene Sweep, is the correct home for this report. `SKILL.md`'s Hygiene
   Sweep bullet is defined as "findings from the pre-wrap sweep"; an unwrapped-session count is not a
   sweep finding, and reporting it there would make that section's own definition false, the same
   text-contradicts-text class D-1's trigger-narrowing defect already demonstrated in this repository.
   "N sessions since the last log were never wrapped" is, on its own terms, an outstanding issue.
   [S1, S2, model-inference: this specific placement reasoning]
4. On continue's no-log-found path and its stale-log (7+ day) path, when the capture store exists and
   yields at least one qualifying record, continue surfaces a short orientation line, branch, head,
   commits_today, and ts of the most recent qualifying record, alongside its existing message.
   [S1, S3]
5. Both consumer additions degrade silently, no error, no mention, when
   `_local/_session-logs/_capture/` does not exist or contains no qualifying `.jsonl` records. [S1]
6. Neither skill's `description:` frontmatter grows to mention capture-lite. [S1]
7. Both skills' public text references only the capture-lite fields actually consumed: `ts`, `head`,
   `session_id`, `branch`, `commits_today`. The source states the goal, "keep field references
   minimal", without naming the fields; this list is this spec's own enumeration, reasoned from
   Requirements 2 and 4 against the schema actually observed in the capture file. The source explicitly
   says the mitigation is field discipline, not built validation, so this is verified once at
   implementation time, not shipped as a standing gate. [S1, S4, model-inference]

## Acceptance Criteria

AC-2 and AC-3 apply only in deep and final modes; this scope is this spec's own inference (Requirement
1), forced by quick and blocked modes having no Outstanding Issues section to write into. Each Given
below restates the precondition so the AC reads as a standalone test contract.

**AC-1:** Given `_local/_session-logs/_capture/` does not exist, or exists but contains no `.jsonl`
files, when wrap runs Evidence Gathering, then the resulting log contains no mention of capture-lite
or of an unwrapped-session count. [S1]

**AC-2:** Given (deep or final mode) `_local/_session-logs/_capture/`'s `.jsonl` files contain at
least one record with a non-null `session_id` and a `ts` after the newest existing log's filename
timestamp, when wrap runs Evidence Gathering, then Outstanding Issues states the count of such records
and the earliest-to-latest `head` among them. [S1, S2, model-inference: mode scope and placement]

**AC-3:** Given (deep or final mode) a capture record has a null `session_id`, when wrap computes the
count for AC-2, then that record is excluded. [S1, S4, model-inference: mode scope]

**AC-4:** Given continue reaches the "no prior session log found" branch, and
`_local/_session-logs/_capture/`'s `.jsonl` files contain at least one record with a non-null
`session_id`, when continue reports that no log was found, then the report also includes a one-line
orientation summary, branch, head, commits_today, and ts, drawn from the most recent such record.
[S1, S3]

**AC-5:** Given continue's resolved log is more than 7 days old, and
`_local/_session-logs/_capture/`'s `.jsonl` files contain at least one qualifying record newer than
that log, when continue surfaces the age warning, then it also reports the count of such records since
that log. [S1, S3]

**AC-6:** Given `_local/_session-logs/_capture/` does not exist, when continue runs either the
no-log-found path or the stale-log path, then its output is unchanged from current behavior. [S1]

**AC-7:** The diff for this effort does not introduce the field names `harness`, `reason`, `last_tag`,
`transcript`, `dirty`, `untracked`, or `stashes` into either skill's SKILL.md or references files.
[S1, S4, model-inference]

## Behavior / Examples

### Example 1: unwrapped sessions since the last log

Given the newest existing log is `2026-08-18_13-44_claude_marketplace-ssh-to-https-fix.md`, and
`_local/_session-logs/_capture/2026-08.jsonl` contains three records with a non-null `session_id` and
a `ts` after that log's timestamp, when wrap runs Evidence Gathering (deep or final mode), then
Outstanding Issues includes a line such as: "3 sessions since the last log were never wrapped
(capture-lite), heads 048d1e9..a91f3c2."

### Example 2: capture absent (wrap side)

Given `_local/_session-logs/_capture/` does not exist, when wrap runs Evidence Gathering, then
Outstanding Issues contains no capture-related line, identical to today's output.

### Example 3: continue, no log found

Given `_local/_session-logs/` and both legacy locations contain no `.md` logs at all, and
`_local/_session-logs/_capture/2026-08.jsonl` contains at least one qualifying record, when continue
reaches the no-log-found branch, then its report adds one line before the existing "Options: Start
fresh..." text, for example: "Capture-lite has 4 recorded sessions (branch main, head 048d1e9, 2
commits today, most recent 2026-08-17T04:57:03+00:00), but none were wrapped into a log."

### Example 4: continue, stale log

Given the resolved log is 12 days old, and capture has 2 qualifying records newer than it, when
continue surfaces the age warning, then it also states: "2 sessions since that log were never wrapped
(capture-lite)."

### Example 5: fresh repo, no existing log at all (wrap side)

Given there is no existing log to compare against (the first-ever wrap in a repository), when wrap
computes "since the last log," then every qualifying capture record counts, since there is no earlier
boundary to filter against. [model-inference: this edge case is not named in the source; it follows
from Requirement 2's filter having no lower bound to apply]

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | No description growth on either skill; two paragraphs of body text total across both skills, no scripts | [S1] |
| Cross-repo coupling | Public skill text references at most 5 named capture-lite fields; the hook's remaining schema stays undocumented in this repo | [S1], Requirement 7 |
| Silent degradation | Both consumer paths behave identically to today when the capture store is absent, since it is optional machine-local infrastructure and the plugin ships publicly from a marketplace | [S1] |

## Revisions

| Date | Change | By |
|---|---|---|
| 2026-08-23 | Initial draft created | agent |

## Sources & Evidence

- [S1] the maintainer's private defect record for the wrap/continue pair, 2026-08-18, D-4 section, the "Rejected and rescoped"
  table (the timing-constraint correction), and the D-1 section (cited for the text-contradicts-text
  precedent in Requirement 3). Maintainer-local, class A (primary design source).
- [S2] `skills/plab-wrap-session/SKILL.md`, Evidence Gathering, the Outstanding Issues bullet (line
  149), the Hygiene Sweep bullet (line 151), and the Quick/Blocked mode body definitions (neither
  lists an Outstanding Issues section). In-repo, class A, verified by direct read.
- [S3] `skills/plab-continue-session/references/log-discovery.md` (Empty or missing directory, Age
  warning, and the store-layout table's existing `_capture/` exclusion) and
  `skills/plab-continue-session/SKILL.md` (the existing `_capture/` mention at line 43). In-repo, class
  A, verified by direct read.
- [S4] `_local/_session-logs/_capture/2026-08.jsonl`. Maintainer-local, class A: read directly, 11
  records at time of writing, confirming the field names (`ts`, `machine`, `harness`, `session_id`,
  `reason`, `repo`, `branch`, `head`, `dirty`, `untracked`, `stashes`, `last_tag`, `transcript`,
  `commits_today`) and the presence of null-`session_id` records.
- [S5] the maintainer's private plab-wrap-session evolution roadmap, 2026-08-16, the W-1 (capture-lite hook) section: the
  hook's design constraint (`SessionEnd` timing) and its stated purpose ("converts an unknown into a
  floor"). Maintainer-local, class A, verified by direct read.

### Unverified Claims

- AC-2 and AC-3's "(deep or final mode)" precondition is a [model-inference] scope decision; see Open
  Questions, OQ1.
- AC-7's five-field list is this spec's own enumeration of "actually consumed," not a list the source
  names explicitly; see Open Questions, OQ2.
- Example 5 (fresh repo, no existing log) is a [model-inference] edge case not named in the source.

## Open Questions / Decisions

**Closed 2026-10-26.** JP approved closing the items below as one batch, after a read-only check on 2026-10-25 confirmed each against shipped code. Each closed item ends with what the check found.

| ID | Title | Status |
|---|---|---|
| OQ1 | Mode scope for wrap's capture report | Decided |
| OQ2 | Exact minimal field list | Decided |
| OQ3 | Evidence Gathering numbering overlap with D-05 | Canceled |

### OQ1: Mode scope for wrap's capture report

This spec scopes the wrap-side report to deep and final modes because quick and blocked mode body
templates have no Outstanding Issues section to write into (`references/session-log-template.md`'s
Quick and Blocked skeletons confirm this). That is a structural argument, stronger than D-05's mode
scoping, but the source itself does not state a mode restriction. Recommend confirming; if a future
change adds an Outstanding Issues-equivalent to the light modes, this scope should be revisited
alongside it.

**Closed, Decided.** The deep and final scope shipped and still holds. The capture-lite count is reported in Outstanding Issues, which only the Final and Deep body templates carry (`skills/plab-wrap-session/SKILL.md`).

### OQ2: Exact minimal field list

`ts`, `head`, `session_id`, `branch`, and `commits_today` are the fields this spec's mechanism actually
reads. If an even smaller public surface is wanted, `commits_today` is the most droppable of the five:
Examples 3 and 4 use it for color but neither AC-4 nor AC-5 strictly requires it. Recommend confirming
the list before implementation locks it in as the AC-7 boundary.

**Closed, Decided.** The five-field list shipped and still holds for both consumers. On the wrap side, `capture_records()` in `skills/plab-wrap-session/scripts/derive-log-facts.py` reads only `session_id`, `ts` and `head`. On the continue side, the orientation line in `skills/plab-continue-session/references/log-discovery.md` names only `branch`, `head`, `commits_today` and `ts`.

### OQ3: Evidence Gathering numbering overlap with D-05

D-04 and D-05 (superseding logs) each add a new numbered item to wrap's Evidence Gathering list.
Neither this spec nor D-05's should assume the other's item already exists, since the two may be
implemented in either order. Both implementation plans instruct "add as the next available number"
rather than a hard-coded integer, which resolves this regardless of execution order; recorded here so
the reason for that phrasing is not lost.

**Closed, Canceled.** The overlap never arose. D-04's capture count ended up inside `derive-log-facts.py`'s digest rather than as its own numbered Evidence Gathering item, and D-04 and D-05 shipped together in v0.4.0. W-02 (derived log facts) later replaced that numbered list's structure, so the question cannot come back.
