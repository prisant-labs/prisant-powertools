---
id: W-07
title: "Session-aware wrap and continue: tell parallel and long-idle sessions apart"
type: spec
status: draft
created: 2026-11-10
updated: 2026-11-10
linked-effort: "the maintainer's questions of 2026-11-10 about the session-log timestamp and parallel sessions, and the unbuilt parallel-session fixes (a) and (c) proposed in the private threads summary of 2026-10-25"
linked-plan: null
linked-release: null
ac-count: 10
source-count: 11
requires-human-review: true
target-release: null
priority: P2
---

# Spec: Session-aware wrap and continue

## Task Summary

**Status:** draft. Written 2026-11-10; nothing built.
**Last updated:** 2026-11-10 by claude (Opus 5.5), under the maintainer's instruction of 2026-11-10 to write the spec
**Linked plan:** none yet
**Open questions:** 0. D1 to D6 were decided on 2026-11-10, each on its recommended option. D6's Follow-up, a check of `claude --resume`, is owed before the implementation plan (see Open Questions / Decisions)
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: The documents say the file name's time is the wrap time
- [ ] AC-2: `derive-log-facts.py` reports `session-id` and `session-start`
- [ ] AC-3: The log schema carries the session fields and `carried-from`, and logs without them stay valid
- [ ] AC-4: The wrap carries items forward from this session's own lineage
- [ ] AC-5: The wrap names concurrent logs it did not carry forward
- [ ] AC-6: The same-arc archive never targets another session's log
- [ ] AC-7: Continue lists every unconsumed recent session and asks, and sequential sessions consume each other
- [ ] AC-8: Continue behaves as today when one candidate exists
- [ ] AC-9: In a linked worktree, both skills read and write the main checkout's store
- [ ] AC-10: A real parallel case is handled end to end

### Currently In Progress

None.

---

## Purpose

The maintainer often runs sessions in parallel, and often leaves a session idle for days before returning to it [S7]. Both skills assume one session at a time.

A session log's file name is `YYYY-MM-DD_HH-MM_<llm>_<title>.md`, and its `HH-MM` is the time the wrap ran [S1, S9]. No document says so. The log records no session identity and no start time, although `derive-log-facts.py` already finds both in the Claude Code transcript [S2].

`plab-continue-session` resumes from the single newest file name. It treats two logs as a tie only when they share the same minute [S3]. Parallel sessions rarely share a minute, so the most recent wrap hides the others without a word.

`plab-wrap-session` has the same blind spot on the write side. It carries Waiting on You and Parked items forward from the newest log by file name, with no check on branch or session [S2, S4]. Its same-arc check can also propose archiving that log [S4]. So a wrap can copy another session's waiting items into its own log, and can offer to archive a log from work that is still live.

This spec keeps the file name as it is and makes both skills aware of which session wrote each log. It builds the parallel-session fixes (a) and (c), which the 2026-10-25 threads summary proposed and the 2026-11-03 register update recorded as not built [S5, S6].

## Scope

### In Scope

1. `skills/plab-wrap-session/references/frontmatter-schema.md`, `references/session-log-template.md` and `docs/skills/plab-wrap-session/README.md`: the file name's meaning and two new frontmatter fields.
2. `skills/plab-wrap-session/scripts/derive-log-facts.py` and its test: the two fields, the choice of the log to carry forward from, and the list of concurrent logs.
3. `skills/plab-wrap-session/SKILL.md`: Evidence Gathering steps 6 and 7, and the log's write location in a linked worktree.
4. `skills/plab-continue-session/SKILL.md`, `references/log-discovery.md` and `docs/skills/plab-continue-session/README.md`: candidate selection when several sessions have unconsumed logs.
5. `skills/plab-wrap-session/scripts/check-log.py`, only as far as it must accept the two new fields.

### Non-Goals

1. **Changing the file name.** The file name keeps the wrap time (D1). Every reader that sorts on the file name keeps working unchanged.
2. **Arc resume.** Reading and narrating the last N logs is C-05 (arc resume), which depends on W-04 (digest mode). This spec chooses which log to resume; it does not merge several logs into one display.
3. **One shared open-items list per project.** That is fix (d) in the 2026-10-25 summary, and a 2026-10-31 recommendation was to drop it until a conflict recurs [S5]. Waiting on You stays per log.
4. **Limiting hygiene proposals to files this session touched.** That is fix (b) [S5]. It needs its own evidence of a wrap that offered to commit another session's work.
5. **Same-arc detection itself.** D-05 (superseding logs) owns how a log is judged to cover the same arc. This spec only limits which log the check may look at (AC-6).
6. **A start time for Codex sessions.** No transcript lookup exists for Codex today (D5). Codex logs omit the fields and fall back to today's behavior.

## Users / Actors

- **The maintainer**, who runs several sessions per repository and picks which one to resume.
- **The wrapping agent**, which writes a log and chooses which earlier log to carry items from.
- **The resuming agent**, which chooses the candidate logs and presents them.
- **`derive-log-facts.py`**, which supplies session facts to the wrap.

## Requirements

1. The documents state that the file name's `HH-MM` is the local time the wrap ran, and that a log written days after its session began still carries the wrap time [S1, S9]. They point to `session-start` for the start [S7].
2. `derive-log-facts.py` reports `session-id`, from `CLAUDE_CODE_SESSION_ID` or `--session-id`, and `session-start`, the first timestamp in that session's transcript [S2]. When either cannot be found, the value is null and the digest names the reason, using the reasons `locate_transcript` already returns [S2].
3. The log's frontmatter carries `session-id` and `session-start` whenever the script reported them, and `carried-from` whenever requirement 4 chose a log. A log written before this spec, without these fields, stays valid for every checker and every reader [S1, model-inference].
4. The wrap chooses one log to carry Waiting on You and Parked items from, by this rule order: the log this session resumed from; else the newest log with this session's `session-id`; else the newest log on this branch; else the newest log overall that requirement 5 does not list as concurrent (D4) [S4, model-inference]. The script reports the chosen log and the rule that chose it, and the wrap records the chosen log's file name in `carried-from`.
5. The script also lists every log that another session wrote after this session's `session-start`. The wrap does not carry those logs' items, and it names them in the new log's Summary so their work stays visible [model-inference].
6. The same-arc archive proposal may target only the log chosen by requirement 4. It never targets a log written by another session after this session started, because that session was running at the same time and was not superseded by this one [S4, model-inference].
7. `plab-continue-session` builds a candidate set before it picks a log (D2). A log is a candidate when it was wrapped in the last 7 days, sits outside `_superseded/`, and is not consumed. A log is consumed when a later log names it in `resumed-from` or `carried-from`. A log without a `session-id` is also consumed by any later log on the same branch, which keeps today's newest-wins behavior for every log written before this spec. Logs that share a `session-id` collapse to the newest of them [S3, S8, S11, model-inference].
8. With one candidate, continue behaves exactly as it does today. With more than one, it lists every candidate newest first, each with its branch, session span, title and Waiting on You count, and asks which to resume. When exactly one candidate is on the current branch, it is marked as the default, but continue never picks one silently. Branch is shown rather than used for grouping, because most sessions in this repository run on `main` [S3, S10, S11].
9. With no candidate in the window, continue falls back to today's newest-log rule and its existing age warning [S3].
10. In a linked git worktree, both skills use the main checkout's `_local/_session-logs/` as the one store (D3). The wrap writes its log there and reads earlier logs from there, and continue reads candidates from there. A fresh worktree has no `_local/` of its own, so reading the worktree's store would find nothing. The log's `branch` field still names the worktree's branch [S5, model-inference].
11. The 7-day window in requirement 7 is the same 7 days as continue's existing age warning, so the two cannot disagree [S3].

## Acceptance Criteria

**AC-1:** `skills/plab-wrap-session/references/frontmatter-schema.md`, `docs/skills/plab-wrap-session/README.md` and `skills/plab-continue-session/references/log-discovery.md` each state that the file name's `HH-MM` is the wrap time, and name `session-start` as the place the start is recorded. [S1, S7]

**AC-2:** Given a fixture transcript whose first timestamped line is `2026-11-01T09:00:00.000Z`, `derive-log-facts.py --json --session-id <id>` reports that id as `session-id` and that timestamp as `session-start`. With no session id, both are null and the digest prints `no-session-id`. Changing `get_session_start_ts` to read only line 1 of a transcript whose line 1 has no timestamp makes `test-derive-log-facts.py` fail. [S2]

**AC-3:** `references/frontmatter-schema.md` and `references/session-log-template.md` define `session-id`, `session-start` and `carried-from`. `check-log.py` passes a fixture log that carries all three fields and a fixture log that carries none of them. [S1, model-inference]

**AC-4:** Given a store holding log A on branch `x`, then a newer log B on branch `y`, a run on branch `x` with no resumed-from and no matching session id reports A as the carry-forward source, with rule `same-branch`. Given `--resumed-from B`, it reports B with rule `resumed-from`. Each of the four rules in Requirement 4 has a fixture case, and reverting the choice to the newest log overall makes the test fail. [S4, model-inference]

**AC-5:** Given a session that started before another session's log was written, `derive-log-facts.py` lists that log under `concurrent-logs`, and the default digest prints it. `skills/plab-wrap-session/SKILL.md` tells the agent to name each concurrent log in Summary and not to carry its items. [model-inference]

**AC-6:** `skills/plab-wrap-session/SKILL.md` Evidence Gathering step 6 judges same-arc only against the carry-forward source from AC-4. No sentence in the skill or its references lets the archive proposal target a log listed under `concurrent-logs`. [S4]

**AC-7:** Given a store with three logs in the window, two from one session on branch `x` and one from another session on branch `y`, continue lists exactly two candidates and asks which to resume. A log named by a later log's `resumed-from` or `carried-from` is not listed, and a log in `_superseded/` is not listed. Given this repository's store as it stood on 2026-11-10, where every log is on `main` and none carries a `session-id`, continue finds exactly one candidate, the newest log. [S3, S8, S11, model-inference]

**AC-8:** Given a store whose only log in the window is the newest log, continue's display and questions are the same as before this spec. Given a store with no log in the last 7 days, continue resumes from the newest log and shows the age warning, as before. [S3]

**AC-9:** A wrap run from a linked worktree writes its log under the main checkout's `_local/_session-logs/`, and `derive-log-facts.py` run there reports its carry-forward source from that store. `plab-continue-session` run in the main checkout, or in another worktree, finds the log. A wrap run in the main checkout reads and writes where it does today. [S5, model-inference]

**AC-10:** The first real case of two sessions in one repository, each wrapped on a different branch, ends with continue listing both and with neither log carrying the other's Waiting on You items. [S7]

## Behavior / Examples

### Example 1: Two parallel sessions, then a resume

Session P starts Monday at 09:00 on `feat/a`. Session Q starts Monday at 10:00 on `feat/b`. P wraps Monday at 17:00 as `2026-11-09_17-00_claude_a-work.md`. Q wraps Tuesday at 11:00 as `2026-11-10_11-00_claude_b-work.md`.

Q's wrap finds no resumed-from, no earlier log of its own, and no earlier log on `feat/b`. P's log is the newest overall, but it was written after Q started, so it is listed under `concurrent-logs`. Q's wrap skips it and carries items from the newest log written before Monday 10:00, under rule `newest-overall`. It names P's log in Summary and proposes no archive. D4 decides whether this last fallback should exist at all.

Q's log does not name P's log in `carried-from`, so P's log stays unconsumed. On Wednesday, `/plab-continue-session` on `main` finds two candidates and asks:

```
Two sessions have unconsumed logs from the last 7 days:

  1. 2026-11-10_11-00_claude_b-work.md  feat/b  (session Mon 10:00 to Tue 11:00, 0 waiting)
  2. 2026-11-09_17-00_claude_a-work.md  feat/a  (session Mon 09:00 to Mon 17:00, 2 waiting)

Which session should I resume?
```

### Example 1b: Sequential sessions do not trigger the question

Session T wraps Monday on `main`. Session U starts Tuesday on `main` without running continue, and wraps Tuesday. U's wrap carries from T's log under rule `same-branch` and records it in `carried-from`. T's log is now consumed, so Wednesday's continue finds one candidate and behaves as it does today.

### Example 2: A session left idle for four days

Session R starts Thursday on `main`, goes idle, and wraps the following Monday. Its log is named for Monday, so it sorts as the newest and continue resumes from it. Its frontmatter shows `session-start` on Thursday, so the four-day span is visible. Under a start-time file name, this log would have sorted below any session started on Friday or later.

### Example 3: Two wraps in one session

Session S wraps at 12:00 and again at 18:00. Both logs carry the same `session-id`. Continue collapses them to the 18:00 log, so the tie prompt does not fire. The 18:00 wrap carries items from the 12:00 log under rule `same-session`.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Determinism | The candidate set, the carry-forward source and the concurrent list are computed by scripts, never by the model. That is the pattern `derive-log-facts.py` and `reconcile.py` already follow. | [S2, model-inference] |
| Compatibility | Logs without the new fields, legacy stores and month folders keep working with no migration. | [S3] |
| Cost | Continue reads only the frontmatter of logs in the window to build the candidate list, and reads one full log after the maintainer picks. | [model-inference] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-11-10 | claude | added | Initial draft, written under the maintainer's instruction of 2026-11-10 after the timestamp and parallel-session questions. |

## Sources & Evidence

- **[S1]** `skills/plab-wrap-session/references/frontmatter-schema.md`: the file name convention, `date` from the system clock, `resumed-from` semantics, and no session identity field. Class A.
- **[S2]** `skills/plab-wrap-session/scripts/derive-log-facts.py`: `get_date()` reads the clock at wrap time; `locate_transcript()` and `get_session_start_ts()` find the session id and start; `newest_log()` picks by file name alone; none of the three session facts reaches the output. Class A.
- **[S3]** `skills/plab-continue-session/references/log-discovery.md`: newest file name wins, a tie only on the same minute, the 7-day age warning, and the `_superseded/` exclusion. Class A.
- **[S4]** `skills/plab-wrap-session/SKILL.md`, Evidence Gathering steps 6 and 7: the same-arc archive proposal and the carry-forward both read the newest log the script reports. Class A.
- **[S5]** The private threads summary of 2026-10-25, which proposed parallel-session fixes (a) "the resume lists every log written since the last resume", (b), (c) "logs always save to the main checkout, even from a worktree", and (d). A 2026-10-31 record recommended dropping (d). Maintainer-local, gitignored. Class A.
- **[S6]** The private decision register's update of 2026-11-03, which records that hygiene order B shipped and that the parallel-session fixes were not built. Maintainer-local, gitignored. Class A.
- **[S7]** The maintainer's questions of 2026-11-10 about parallel sessions and sessions left idle for days, and the instruction to write this spec. In session. Class A.
- **[S8]** `skills/plab-continue-session/SKILL.md` line 137: the consumed log's file name is recorded in the next wrap's `resumed-from:`, which is how consumption is measured. Class A.
- **[S9]** The six newest logs in this repository's store, checked 2026-11-10: each file name's `HH-MM` is within three minutes of its `date:` line, so the agent takes the time while writing. Maintainer-local, gitignored. Class A.
- **[S10]** `docs/skills/plab-continue-session/README.md`: the `--log <path>` override, today's only way to resume a log other than the newest, and the "rare; concurrent sessions" tie note. Class A.
- **[S11]** A replay of this repository's ten newest logs on 2026-11-10. All ten are on `main`. Only four carry `resumed-from`. Under a rule that counted only `resumed-from` as consumption, the logs of 2026-11-05 and 2026-11-08 would both be candidates, so continue would ask on an ordinary sequential resume. That finding is why Requirement 7 also counts `carried-from` and treats a log without a `session-id` as consumed by any later log on its branch. Maintainer-local, gitignored. Class A.

### Unverified Claims

- Requirements 4 to 7 and 10 are `[model-inference]`: the rule orders, the window and the worktree location are this spec's proposals, not recorded rulings.
- That `claude --resume` keeps a session's id and appends to the same transcript is not verified (D6). If a resume starts a new id, the per-session collapse and `session-start` would both describe only the resumed part.
- That a log written inside a worktree is lost or unseen is inferred. No code in either skill mentions worktrees, but no lost log has been observed.
- That Codex exposes no session start is inferred from the absence of any lookup (D5).


## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Which time the file name carries | Option A | Decided | 2026-11-10 |
| D2 | Which logs continue offers | Option A | Decided | 2026-11-10 |
| D3 | Where a worktree session's log is read and written | Option A | Decided | 2026-11-10 |
| D4 | Whether carry-forward may fall back to another branch | Option A | Decided | 2026-11-10 |
| D5 | What Codex logs carry for session start | Option A | Decided | 2026-11-10 |
| D6 | Whether `claude --resume` keeps the session id | Option A | Decided | 2026-11-10 |

### D1: Which time the file name carries (Decided)

**Summary.** The file name's `HH-MM` could record the wrap or the start of the session.

**Context.** The maintainer asked whether to standardize on the start time, because sessions run in parallel and sit idle for days [S7]. Four readers sort on the file name: continue's newest-log pick, its age warning, the wrap's carry-forward, and `--organize`'s month filing [S2, S3].

**Desired outcome.** A reader can tell when a session began and which logs one session wrote, and the freshest handoff still sorts first.

**Options / approaches.**

* **Option A:** Keep the wrap time in the file name, and add `session-start` and `session-id` to the frontmatter.
* **Option B:** Put the session's start time in the file name.

**Recommendation.** Option A. Confidence: medium-high. Under Option B, a session idle for days would sort below sessions that started later, so continue would skip the freshest handoff. Two wraps in one session would share a prefix and trip the tie prompt. The age warning would call a log written today stale. Option A gives the same grouping through `session-id` without breaking any sort.

---

> **Maintainer decision:** Decided 2026-11-10 by jprisant
>
> * **Status:** Decided
> * **Choice:** Option A
> * **Reasoning:** Accepted the recommendation (answer line: "d1 a"). The wrap time keeps every file-name sort correct, and `session-start` and `session-id` in the frontmatter carry the start and the grouping.
> * **Follow-up:** Build Requirements 1 to 3 of this spec, verified by AC-1 to AC-3, once W-07 has an implementation plan.
> * **Decided by / date:** jprisant / 2026-11-10

### D2: Which logs continue offers (Decided)

**Summary.** The rule that decides which logs continue lists when several sessions have wrapped.

**Context.** Today continue offers only the newest log, so a parallel session's log is hidden [S3]. Fix (a) of 2026-10-25 proposed listing every log since the last resume [S5]. A replay of this repository's store showed that a rule counting only `resumed-from` would ask on ordinary sequential resumes, because most sessions never run continue [S11].

**Desired outcome.** Continue asks only when two sessions really left separate handoffs, and behaves as today otherwise.

**Options / approaches.**

* **Option A:** Unconsumed logs from the last 7 days, where `resumed-from` and `carried-from` both consume, collapsed to one per session, as in Requirement 7.
* **Option B:** Every log newer than the newest log that carries `resumed-from`, which is fix (a)'s wording [S5].
* **Option C:** The newest log on each branch, with no consumption check.

**Recommendation.** Option A. Confidence: medium. Option B lists every log since the last explicit resume, which on the replay is several sequential logs. Option C groups nothing in a repository where every session runs on `main` [S11]. Option A reuses `resumed-from` [S8], adds the carry-forward record the wrap already decides, and reuses the existing 7-day threshold.

---

> **Maintainer decision:** Decided 2026-11-10 by jprisant
>
> * **Status:** Decided
> * **Choice:** Option A
> * **Reasoning:** Accepted the recommendation (answer line: "d2 a"). Counting `carried-from` as well as `resumed-from` keeps continue silent on ordinary sequential sessions and asks only when two handoffs are really separate.
> * **Follow-up:** Build Requirements 7 to 9 and 11 of this spec, verified by AC-7 and AC-8, once W-07 has an implementation plan.
> * **Decided by / date:** jprisant / 2026-11-10

### D3: Where a worktree session's log is read and written (Decided)

**Summary.** A wrap inside a linked worktree writes to that worktree's `_local/`, which continue in the main checkout never reads.

**Context.** Fix (c) of 2026-10-25 proposed always saving to the main checkout [S5]. Neither skill mentions worktrees today. A fresh worktree also has no earlier logs, so a wrap there has nothing to carry forward from.

**Desired outcome.** Every session's log lands in one store that every later session reads, whichever checkout it runs in.

**Options / approaches.**

* **Option A:** Read and write the main checkout's `_local/_session-logs/`, found through the repository's common git directory.
* **Option B:** Keep each worktree's own store, and teach continue to read every worktree's store.

**Recommendation.** Option A. Confidence: medium. Removing a worktree removes its untracked `_local/` with it, so Option B can lose logs. One store keeps every other reader unchanged.

---

> **Maintainer decision:** Decided 2026-11-10 by jprisant
>
> * **Status:** Decided
> * **Choice:** Option A
> * **Reasoning:** Accepted the recommendation (answer line: "d3 a"). One store in the main checkout cannot be lost when a worktree is removed, and every other reader stays unchanged.
> * **Follow-up:** Build Requirement 10 of this spec, verified by AC-9, once W-07 has an implementation plan.
> * **Decided by / date:** jprisant / 2026-11-10

### D4: Whether carry-forward may fall back to another branch (Decided)

**Summary.** When a session has no lineage and its branch has no earlier log, should the wrap still carry items from the newest log overall?

**Context.** Waiting on You items are often project-wide, such as a pending release approval. Today every wrap carries from the newest log overall [S4], which is the behavior that copies a parallel session's items.

**Desired outcome.** Standing blockers survive a change of branch, and no wrap copies a concurrent session's items.

**Options / approaches.**

* **Option A:** Keep the fallback to the newest log overall, but never from a log under `concurrent-logs`.
* **Option B:** Stop at the same-branch rule. A new branch starts with no carried items.

**Recommendation.** Option A. Confidence: low. Option B would drop project-wide blockers at every new branch. The exclusion of concurrent logs prevents the copying this spec exists to stop.

---

> **Maintainer decision:** Decided 2026-11-10 by jprisant
>
> * **Status:** Decided
> * **Choice:** Option A
> * **Reasoning:** Accepted the recommendation (answer line: "d4 a"). Project-wide blockers survive a change of branch, and excluding `concurrent-logs` stops the copying this spec exists to prevent.
> * **Follow-up:** Build Requirement 4 of this spec, verified by AC-4 and AC-5, once W-07 has an implementation plan.
> * **Decided by / date:** jprisant / 2026-11-10

### D5: What Codex logs carry for session start (Decided)

**Summary.** The start-time lookup reads Claude Code's transcript only.

**Context.** `locate_transcript` reads `CLAUDE_CODE_SESSION_ID` and the Claude Code projects folder [S2]. Nothing looks up a Codex session.

**Desired outcome.** Codex logs keep working at least as well as they do today.

**Options / approaches.**

* **Option A:** Omit the session fields on Codex logs, which then follow the legacy rule in Requirement 7.
* **Option B:** Find Codex's own session record and read its start, as a separate check before building.

**Recommendation.** Option A. Confidence: medium. Codex wraps in this repository are rare, and Option A loses nothing that today's behavior has.

---

> **Maintainer decision:** Decided 2026-11-10 by jprisant
>
> * **Status:** Decided
> * **Choice:** Option A
> * **Reasoning:** Accepted the recommendation (answer line: "d5 a"). Codex wraps are rare here, and omitting the fields loses nothing today's behavior has.
> * **Follow-up:** None beyond Requirement 2 of this spec: under Codex the session fields are null with a reason, and no Codex lookup is built.
> * **Decided by / date:** jprisant / 2026-11-10

### D6: Whether `claude --resume` keeps the session id (Decided)

**Summary.** The maintainer restores idle sessions with `claude --resume`. This spec assumes the resumed session keeps its id and its transcript.

**Context.** If a resume starts a new id or a new transcript, `session-start` would show the resume time, and the two halves of one session would not collapse in continue's list. The code in this repository cannot answer this.

**Desired outcome.** `session-start` and `session-id` describe the whole session, from first start to wrap, across any resume.

**Options / approaches.**

* **Option A:** Check a resumed session's transcript before building. If the id changes, record the earlier id through the transcript's own link to it, if one exists.
* **Option B:** Build as written, and accept that a resumed session counts as a new one.

**Recommendation.** Option A. Confidence: high that the check is worth doing first; it is one transcript inspection.

---

> **Maintainer decision:** Decided 2026-11-10 by jprisant
>
> * **Status:** Decided
> * **Choice:** Option A
> * **Reasoning:** Accepted the recommendation (answer line: "d6 a"). The check is one transcript inspection, and its answer decides whether `session-id` can be trusted across a resume.
> * **Follow-up:** Before the implementation plan is written: note a session's `CLAUDE_CODE_SESSION_ID`, exit, run `claude --resume` on it, and compare the resumed session's id and transcript file. Record the result in this spec's Revisions and Unverified Claims sections.
> * **Decided by / date:** jprisant / 2026-11-10
