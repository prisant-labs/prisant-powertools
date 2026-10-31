---
id: PP-01
title: "plab-project-pulse: what shipped, what is next, and what waits on the owner, across every repository"
type: spec
status: committed
created: 2026-10-30
updated: 2026-10-30
linked-effort: "the maintainer's instruction of 2026-10-30 in session to enrich and build the two audit skills, and the maintainer-local packaging analysis of 2026-10-16 with its ruling of 2026-10-30 (two skills, the pulse kept clearly apart from plab-current-status)"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 26
source-count: 10
requires-human-review: true
target-release: null
priority: P2
---

# Spec: plab-project-pulse, a weekly roll-up of every repository

## Task Summary

**Status:** committed, shipped in v0.11.0; scout escalation (AC-16), the digest (AC-19) and the first `--week` run (AC-26) are still to be shown
**Last updated:** 2026-10-30 by claude (Opus 5.5), written under the maintainer's instruction to enrich the two audit-skill specs and build them
**Linked plan:** `implementation-plan.md` in this folder
**Open questions:** 5, each built on its recommendation as a working default and awaiting ratification (see Open Questions / Decisions)
**Revisions:** 2

### Acceptance Criteria Fulfillment

- [x] AC-1: The skill is manual-only and does not fire on a status question
- [x] AC-2: Discovery finds repositories at each depth, including a root that is a repository
- [x] AC-3: Discovery never enters `node_modules`, `.git`, a link or a junction
- [x] AC-4: A link to another repository appears once, as an alias
- [x] AC-5: Session logs are found flat, in month folders and under `_LOCAL`, and skipped folders are skipped
- [x] AC-6: A log with a nonstandard name is read and listed as nonstandard
- [x] AC-7: Only the owner's commits are counted, by local day in the configured zone
- [x] AC-8: Ahead and behind are reported without fetching, with the age of the remote state
- [x] AC-9: A full sweep writes nothing to any repository
- [x] AC-10: A repository without an upstream is reported and listed
- [x] AC-11: Activity classification and carry-forward follow the dormant rule
- [x] AC-12: A fresh current-status snapshot is read instead of scouting the repository
- [x] AC-13: A hand-written file in `_local/_status/` is never read as a snapshot
- [x] AC-14: Every waiting item carries an age, from its source or its first-seen date
- [x] AC-15: Recent work in an unprotected folder is reported
- [ ] AC-16: Every agent call names a model, and a short scout is escalated once
- [x] AC-17: A contradiction between git and a document becomes a conflict entry
- [x] AC-18: Every next step and waiting item carries its source
- [ ] AC-19: Each log yields one digest record with both field groups
- [x] AC-20: `pulse.json` validates against its schema
- [x] AC-21: The dashboard takes every label and date from data
- [x] AC-22: The dashboard's card count matches `pulse.json`
- [x] AC-23: Output inside an unignored folder of a git repository is refused
- [x] AC-24: The checker proves each rule can fail against its committed sample
- [x] AC-25: `--quick` makes no model call
- [ ] AC-26: A live run on the maintainer's tree produces output the checker passes

### Currently In Progress

Built on 2026-10-30 on `feat/audit-skills`. Evidence: AC-2 to AC-10 by `test-discover-sweep.py`, including a hash of every file in each fixture repository before and after a sweep (AC-9); AC-11 to AC-15 by `test-derive-pulse-facts.py` (30 checks); AC-17, AC-18 and AC-20 to AC-22 by `test-build-render.py` and by `pulse-check.py --self-test`, whose mutations make each of its ten rules fail against the committed sample (AC-24); AC-23 by `check-placement.py`, which is byte-identical to the copy `plab-usage-audit`'s `test-scrub.py` exercises; AC-25 by a live `--quick` run on the maintainer's tree that made no model call, swept every repository under the configured roots in 11 seconds and passed the checker. AC-1's eval case exists but the eval suite has not been run, because each case is a full session on the maintainer's credential. Still open: AC-16, because `test-workflow-reference.py` proves every agent names a model but only a `--week` run can show a short scout being escalated; AC-19, because digest records come from the log agents of a `--week` run; and AC-26, that run itself.

---

## Purpose

An owner with many repositories has no single place to see the week: what shipped, what each repository says is next, and which decisions wait on them. A hand-run review on 2026-10-16 found at least 56 such decisions across 14 of 18 active repositories, the oldest from June, and on 2026-10-30 one repository had sat idle for ten days on five of the owner's decisions [S2, S3]. The owner asked for exactly this view on 2026-10-11, as one page of every project and its next step [S7].

The skill answers three questions on demand: what shipped, what is next, and what waits on me, across every repository under the configured roots. It does not measure agent usage; that is `plab-usage-audit` (UA-01) [S1].

### How this differs from `plab-current-status`

The maintainer's condition for this skill is that its difference from `plab-current-status` is clear [S1]. The two answer different questions at different depths, and the pulse reads the other skill's output rather than repeating its work.

| | `plab-current-status` | `plab-project-pulse` |
|---|---|---|
| Question | Where does this project stand, and what do I do next in it? | Where does everything stand, what shipped this week, and which projects wait on me? |
| Scope | The one repository the session is in | Every repository under the configured roots, typically 30 to 80 |
| Depth | Deep: the previous snapshot, the logs since it, each decision's home section | Shallow: one entry per repository; dormant ones carried forward unread |
| Ranking | Items within one project | Projects and their waiting items against each other |
| Window | Since the previous snapshot | A calendar week in the configured zone |
| Output | One Markdown file in that repository's `_local/_status/` | A private folder outside any one repository: data, a readout and a dashboard |

A one-line test for which to run: "where is this project?" runs `plab-current-status`; "where is everything?" runs the pulse. The pulse reads each repository's newest snapshot when it is fresh (Requirement 9), so a repository with a current snapshot costs the pulse no agent, and the pulse lists active repositories whose snapshot is missing or stale as candidates for `/plab-current-status` [S8]. The sections the two skills share carry the same names and meanings: Waiting on You, What's Next and Pending Decisions [S8].

## Scope

### In Scope

1. A new skill, `skills/plab-project-pulse/`, manual-only, with `SKILL.md`, `HISTORY.md`, references, a dashboard template and a committed synthetic sample.
2. Stdlib-only scripts: `discover.py` (contract C1), `sweep.py` (contract C2), `derive-pulse-facts.py` (every deterministic fact in one call), `build-pulse.py` (assembles `pulse.json` and updates the state file), `render.py` (fills the dashboard) and `pulse-check.py` (validates every output, with a self-test).
3. Optional GitHub enrichment through `gh`: visibility, releases and open pull requests, each call with a timeout.
4. The `--quick` mode (no model calls) and the `--week` mode (log readers and scouts for active repositories without a fresh snapshot).
5. The shared contracts C1 to C5 below, which UA-01 also uses.
6. The plugin's registration of the skill: `library.json`, the regenerated manifests, `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/skills/plab-project-pulse/README.md`, `docs/status-skills.md`, an eval case and the CI steps.

### Non-Goals

1. **Measuring usage or cost.** That is UA-01. The pulse shows per-project spend only when given UA-01's `projects.json`.
2. **Appraising a repository in depth.** That is `plab-audit`, and `plab-current-status` for status. The pulse flags a repository for either.
3. **Changing any repository.** No fetch, pull, checkout, branch deletion or commit, ever.
4. **Publishing.** No upload and no board update in v1; see D3.
5. **The `--full` re-scout of every repository.** A later version; `--week` re-scouts any repository the moment it becomes active.
6. **Ranking readiness for autonomous runs.** See D2.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| The owner | Reads the readout and dashboard, answers the waiting items | Types `/plab-project-pulse`, opens `dashboard.html` |
| The main loop | Runs the scripts, launches the agents, curates What's Next, writes the readout | Follows `SKILL.md` |
| Log readers | Turn the window's session logs into digest records (C3) | Launched with an explicit model |
| Scouts | Read status documents for active repositories without a fresh snapshot | Launched with an explicit model, grouped, with a count check |
| `plab-current-status` | Its snapshots are the pulse's preferred per-repository input | Files read from each repository's `_local/_status/` |
| `plab-usage-audit` | Consumes the digest and the sweep; supplies per-project spend | Files passed by path |

## Shared contracts

Both skills use these. UA-01 refers to them by these headings.

### C1: discovery

1. Walk each root to `max_depth`. Stop descending at a directory that holds `.git`.
2. A root that is itself a repository counts as one. Repositories directly under a root count.
3. Never enter `node_modules`, `.git`, or any directory link or Windows junction. A link that points at another discovered repository is reported once, as an alias of it.
4. Session logs live in `_local/_session-logs/`, at the top level and in `YYYY-MM/` month folders. Match `_local` case-insensitively. Skip `_superseded/` and `_capture/`. Accept the older stores `_agent-context/session-log/` and `AGENTS/session-log/`.
5. Take a log's date from its file name. A name without the `HH-MM_<llm>_` part is still read, ordered by modification time within its day, and listed as nonstandard.

Each rule answers a failure in the hand-run reviews: unbounded searches that timed out at five minutes (again on 2026-10-30), a bounded search that missed a top-level repository, a junction counted twice, and Codex logs without the time segment [S2, S3].

### C2: the git sweep record

One JSON object per repository. No command in the sweep writes to the repository.

| Field | Meaning |
|---|---|
| `repo`, `path`, `folder` | Name relative to its root, absolute path, and the configured folder label |
| `remote`, `branch`, `head` | `origin` URL, the current branch, and the head commit's short hash |
| `commits_prior`, `commits_focus`, `active_days_focus` | Own commits on all branches, by commit date in the configured zone |
| `last_commit_date` | The newest own commit's local date, or null |
| `tags_in_window` | Tags created in the window, with dates |
| `dirty_files`, `staged_files`, `untracked_files` | Counts from `git status --porcelain` |
| `ahead`, `behind`, `has_upstream` | Against `@{u}`, without fetching |
| `remote_state_as_of` | The modification time of `.git/FETCH_HEAD`, so a reader knows how old `behind` is |
| `unmerged_branches`, `worktrees`, `stashes` | Lists |
| `alias_of` | Set when the path is a link to another repository |
| `snapshot_utc` | When the record was taken |

### C3: the session-log digest

One JSON line per session log in the window, in two field groups so one reading serves both skills.

| Group | Fields |
|---|---|
| Identity | `file`, `repo`, `date`, `time`, `harness` (claude, codex), `model`, `nonstandard_name` |
| Status (the pulse reads these) | `summary`, `shipped`, `decisions` (each with where it was recorded and by whom), `waiting_on_owner` (each with a since date when stated), `next_action` |
| Practice (the usage audit reads these) | `tooling_friction` (what, which tool, impact), `practice_lessons`, `global_setup_items`, `scale_notes` |

Whichever skill runs first for a window writes `digest.jsonl`; the other takes it with `--digest <path>` and reads no log again. In a normal week the usage audit runs on its fixed day, so it usually writes the digest.

### C4: the coverage statement

`coverage.md` lists, in this order: the window and zone; the roots and depth; repositories found and aliases skipped; repositories without an upstream; `gh` failures with their commands; snapshots read and snapshots stale; logs read and nonstandard names; every agent with its model and assigned and returned counts; escalations and items still missing; the snapshot times. A gap is written down, never left silent [S6].

### C5: exit codes, routing and credentials

Every script exits 0 when clean, 1 when it has findings, and 2 when it could not run. Every agent names a model, and the coverage statement carries the routing table. No agent may open, read, search or filter a credential file: any `.env` file, any file whose name contains `secret` or `token`, and the owner's configured credential files [S3, S9].

## Requirements

**Discovery and sweep**

1. Discovery follows C1 and finishes on the owner's tree, about 80 repositories, in under a minute [S2].
2. The sweep follows C2 and never runs a command that writes to a repository [S6].
3. Commit dates and windows use the configured IANA time zone, never a fixed offset [S2].
4. `gh` enrichment is optional; a failure or timeout is recorded in the coverage statement and the run continues [S2].

**Facts, classification and carry-forward**

5. `derive-pulse-facts.py` returns, in one call, discovery, the sweep, `gh` facts, activity classes, carried entries, snapshot reads, unprotected work, waiting-item ages and the list of repositories to scout, as `pulse-facts.json` in the shape `references/pulse-schema.md` defines [S8].
6. A repository is active when it has an own commit or a new session log in the window; every other repository is dormant [S1].
7. A dormant repository with a previous entry in the state file keeps it, stamped with the date it was last refreshed (`carried_from`), and launches no agent. It is refreshed the moment it becomes active [S2].
8. A dormant repository with no previous entry gets a record of sweep facts only, with no model call [model-inference].
9. For each repository, the newest file in `_local/_status/` whose name matches `plab-current-status`'s snapshot pattern `YYYY-MM-DD_<model>_<byline>.md` is its snapshot. A snapshot is fresh when its `head` frontmatter equals the repository's head commit, or its date is on or after the last own commit's date. A fresh snapshot's frontmatter counts and its Waiting on You, What's Next and Pending Decisions items become the repository's status, with the snapshot as the source, and the repository is not scouted [S8].
10. Files in `_local/_status/` that do not match the snapshot pattern, such as a hand-kept register, are never read as snapshots [S8].
11. Every waiting item carries an age in days. The age comes from the item's stated since date when its source gives one, and otherwise from the date the state file first saw the same item, matched by repository and normalized text [S3].
12. For each repository, files changed in the window under gitignored working folders, `_local/` other than `_session-logs/` and `_status/`, and the configured `unprotected_globs`, are counted and reported as `unprotected_work`. A week of work once sat in such folders on one machine with no copy anywhere [S3].
13. Active repositories with no fresh snapshot are listed as candidates for `/plab-current-status` in the readout [S8].

**Agents**

14. Every agent is launched with an explicit model, Sonnet or Haiku, and none Opus by default [S9].
15. The workflow checks each scout's returned count against its assignment. Missing repositories re-run once on the next tier, with the failure described, and anything still missing is listed in the coverage statement. On 2026-10-09 a Haiku scout returned 1 of 13 repositories and only the main loop's eye caught it [S2].
16. Git facts outrank status documents, which outrank session logs. A contradiction is kept as a `conflicts` entry quoting both, not resolved silently [S2].
17. Every next step and waiting item carries the path it came from [S2].

**Outputs**

18. `build-pulse.py` assembles `pulse.json` from the facts, the scout records and the main loop's curation, validates it, and updates the state file's entries and first-seen dates only after validation passes [model-inference].
19. The dashboard derives every label, date and filter from `pulse.json`, and needs no network access [S2].
20. `pulse-check.py` validates `pulse.json` against `references/pulse-schema.md`, every source field, the coverage statement's headings and order, the What's Next cap of ten, and that the dashboard's repository card count equals the number of repositories in `pulse.json`. On 2026-10-30 a dashboard was built and never looked at [S3].
21. Per-repository spend, when supplied, matches by exact folder-qualified name, so no repository's spend is counted twice [S2].
22. An output folder inside a git repository is refused unless `git check-ignore` confirms it is ignored [S6].
23. Nothing the skill writes is committed, pushed or published by the skill.

## Acceptance Criteria

**AC-1:** `skills/plab-project-pulse/SKILL.md` carries `disable-model-invocation: true`, and an eval case whose prompt is "what's next across all my projects?" asserts that the skill is not invoked. [S5]

**AC-2:** On a fixture tree, discovery returns every repository at depth 1 and 2 under each root, including a root that is itself a repository. [S2]

**AC-3:** Discovery never lists a path inside `node_modules` or `.git`, and never descends through a directory link or junction. [S2]

**AC-4:** A link pointing at another fixture repository appears once, with `alias_of` set to that repository, and its commits are not counted twice. [S2]

**AC-5:** Session logs are found at the top level of `_local/_session-logs/`, in its `YYYY-MM/` folders, and under `_LOCAL/_session-logs/`; logs under `_superseded/` and `_capture/` are not. [S2]

**AC-6:** A log named without `HH-MM_<llm>_` is listed with `nonstandard_name: true`. [S2]

**AC-7:** Only commits whose author matches `author_pattern` are counted. Under `America/Los_Angeles`, a fixture commit at 2026-11-02T07:30Z counts on 2026-11-01. [S2]

**AC-8:** A fixture repository two commits behind its upstream reports `behind: 2` and `ahead: 0`, and `remote_state_as_of` equals its `FETCH_HEAD` modification time or null when there is none. [S2]

**AC-9:** After a full sweep, every fixture repository's refs, index, `FETCH_HEAD` and working tree are byte-identical to before. [S6]

**AC-10:** A repository with no upstream reports `has_upstream: false`, and the coverage statement lists it. [S2]

**AC-11:** A repository with no own commit and no new log in the window is `dormant`; with a previous state entry it carries that entry plus `carried_from`; without one it has `status_source: "sweep-only"`. A previously dormant repository with one new commit is `active` and listed to scout. [S2]

**AC-12:** A fixture repository whose newest snapshot's `head` equals its head commit has `status_source: "snapshot"`, takes its waiting count from the snapshot's `waiting` field, and is not in the list to scout. With a snapshot older than the last commit, it is listed to scout and as a `/plab-current-status` candidate. [S8]

**AC-13:** A fixture file `_local/_status/decision-register.md` is never read as a snapshot. [S8]

**AC-14:** A waiting item with a stated since date reports its age from that date. An item without one, present in the state file from a run seven days earlier, reports an age of seven days. [S3]

**AC-15:** A fixture repository with a file changed in the window under gitignored `_local/notes/` reports one file in `unprotected_work`; a change under `_local/_session-logs/` is not reported. [S3]

**AC-16:** A test reads `references/workflow.md` and finds a model named for every agent stage and the C5 credential rule in the text every agent receives. Given a scout record set missing one assigned repository, the coverage statement records the escalation. [S2, S9]

**AC-17:** A fixture whose newest log says a branch is unmerged, while git shows it merged, yields a `conflicts` entry quoting both. [S2]

**AC-18:** `pulse-check.py` fails a `pulse.json` in which any `next_steps` or `waiting_on_you` item has an empty source. [S2]

**AC-19:** Each log in the window yields exactly one digest record, which carries both field groups, empty lists allowed. [S2]

**AC-20:** `pulse-check.py` fails a `pulse.json` missing a required field of `references/pulse-schema.md`. [S2]

**AC-21:** Rendering the sample data for two different windows produces two dashboards whose week labels differ, and the template holds no date literal. [S2]

**AC-22:** `pulse-check.py` fails a dashboard whose repository card count differs from the number of repositories in `pulse.json`. [S3]

**AC-23:** With the output folder inside a fixture git repository that does not ignore it, the run exits 1 before any write, asking for `--out`. [S6]

**AC-24:** `pulse-check.py --self-test` exits 0 against the committed sample, and disabling any one rule makes it exit 2. CI runs it and the script tests. [S6]

**AC-25:** `--quick` makes no model call and writes `pulse.json`, `coverage.md` and `dashboard.html`. [S1]

**AC-26:** A `--week` run on the maintainer's tree writes output that `pulse-check.py` passes. [model-inference: the live run is this spec's own test design]

## Behavior / Examples

### Example 1: a weekly run

Discovery finds 70 folders under two roots in twenty seconds. The sweep marks 15 active. Four of those have a fresh `plab-current-status` snapshot, so their status comes from the snapshot. Fifty-five dormant repositories keep their entries from last week, stamped with that date. The usage audit already wrote this week's digest, so no log reader runs. One Sonnet scout reads the four busiest of the remaining eleven, and two Haiku scouts read the other seven; each count matches. The main loop orders ten next items, `build-pulse.py` writes `pulse.json`, `render.py` writes the dashboard, and `pulse-check.py` exits 0. The readout lists the eleven scouted repositories as candidates for `/plab-current-status`.

### Example 2: a link

A repository folder is a Windows junction into another repository. Discovery records it as `alias_of` the target, and the sweep skips it, so its commits are counted once.

### Example 3: a stale log

A repository's newest log lists a merge as blocked, but git shows the commit on `main`. The scout records the git fact as status and adds a `conflicts` entry quoting both, and the dashboard marks that card.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Performance | Discovery under 60 seconds and `--quick` under 2 minutes, on about 80 repositories | [S2] |
| Performance | `--week` under 15 minutes for 20 active repositories | [S2] |
| Cost | `--week` launches at most 10 agents, none Opus, unless the owner overrides the models | [S9] |
| Privacy | All output is private. The template and scripts ship; no output does | [S1] |
| Portability | Python 3.11 or later, standard library only. Git 2.30 or later. `gh` optional | [S6] |
| Safety | No command that writes to a repository | [S6] |
| Context budget | The description is at most 600 characters | [S5] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-10-30 | claude | added | Initial spec, from the maintainer-local spec brief of 2026-10-16 and its review of 2026-10-30. Changes from the brief: the comparison with `plab-current-status` and the snapshot reader, the shared vocabulary, waiting-item ages, unprotected work, the dashboard card check, the credential rule in C5, the facts script and assembly step, Pacific examples, and the stale board context in D3. The decisions below are built on their recommendations as working defaults and stay `Open` until the maintainer ratifies or overturns them. |
| 2026-10-30 | claude | changed | Status moved to `committed` with 23 of 26 criteria ticked on the evidence in Currently In Progress. AC-16, AC-19 and AC-26 stay open until a live `--week` run. |

## Sources & Evidence

- **[S1]** The maintainer's rulings in session on 2026-10-30: two skills, scripts first, and the condition that the pulse's difference from `plab-current-status` be clear. Class A.
- **[S2]** The hand-run project reviews of 2026-10-09, 2026-10-16, 2026-10-23 and 2026-10-30: their discovery failures, scout escalations, conflict findings and dashboards. Maintainer-local private repository; restated here, not linked. Class A.
- **[S3]** The 2026-10-30 review's findings: the repository idle for ten days on five decisions, the week of work in gitignored folders, the dashboard never looked at, and the search that timed out again. Maintainer-local; restated here. Class A.
- **[S4]** The 2026-10-02 design brief for the usage skill, whose plugin-settings pattern this skill follows. Maintainer-local. Class A.
- **[S5]** `AGENTS.md`: the manual-only rulings, and the warning that status questions are the most common mis-fire. Class A.
- **[S6]** `skills/plab-audit/SKILL.md` and `skills/plab-audit/references/coverage-statement.md`: output placement, coverage discipline and exit codes. Class A.
- **[S7]** The maintainer's request of 2026-10-11 for one view of every project and its next step. Maintainer-local. Class A.
- **[S8]** `skills/plab-current-status/SKILL.md` and `references/status-format.md`, whose frontmatter counts exist so that a page listing every project's snapshot can read them. Class A.
- **[S9]** The maintainer's subagent model-routing rule. Maintainer-local global instructions. Class A.
- **[S10]** The maintainer-local review of the two spec briefs, 2026-10-30. Class A.

### Unverified Claims

- Requirement 8 (sweep-only records for never-refreshed dormant repositories) has not run by hand.
- Requirement 9's freshness rule is a proposal; how many repositories carry snapshots is unknown.
- Requirement 11's first-seen matching by normalized text will miss an item whose wording changes between runs.
- The performance targets come from hand runs; a scripted run may differ.
- AC-26's live run is this spec's own test design.

## Open Questions / Decisions

**What these statuses mean.** Every item below is `Open`: the maintainer has not chosen. Each Recommendation ends by saying the build used it as a working default, so a walk can ratify or overturn it. The build followed the maintainer's instruction of 2026-10-30 to enrich and build the skills.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Skill name | (none) | Open | 2026-10-30 |
| D2 | Readiness ranking in v1 | (none) | Open | 2026-10-30 |
| D3 | A GitHub Projects feed | (none) | Open | 2026-10-30 |
| D4 | Manual-only invocation | (none) | Open | 2026-10-30 |
| D5 | Series letter | (none) | Open | 2026-10-30 |

### D1: Skill name (Open)

**Summary.** `plab-project-pulse` or `plab-portfolio-pulse`?

**Context.** "Portfolio" also names the owner's career portfolio catalogs. "Project" matches the folder-and-repository unit the skill reports on.

**Desired outcome.** A name that says "every project" and does not suggest résumé work.

**Options / approaches.**

* **Option A:** `plab-project-pulse`.
* **Option B:** `plab-portfolio-pulse`.

**Recommendation.** Option A. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Readiness ranking in v1 (Open)

**Summary.** Should v1 rank work that is ready for long autonomous runs?

**Context.** Readiness was ranked by hand on 2026-10-09 and again on 2026-10-28, so the need recurs. Each ranking took a judge agent at high effort, and few ranked items have been launched.

**Desired outcome.** The pulse stays cheap by default, and the ranking is there when the owner wants to start an autonomous run.

**Options / approaches.**

* **Option A:** Leave it out of v1, and add `--readiness` next, reading `pulse.json`.
* **Option B:** Include it in `--week`.

**Recommendation.** Option A, now with a named next version, because the need has recurred. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D3: A GitHub Projects feed (Open)

**Summary.** Should the pulse later push its next steps onto the owner's GitHub Projects board?

**Context.** The owner's private board was built on 2026-10-25, with the `project` scope granted, and is in a two-week read-or-archive test that ends on 2026-11-08.

**Desired outcome.** One place where next steps live, without two systems drifting apart.

**Options / approaches.**

* **Option A:** Decide after the board's test ends, and keep v1 file-only.
* **Option B:** Build a one-way feed in v1.

**Recommendation.** Option A, because a feed into a board that may be archived on 2026-11-08 is wasted work. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D4: Manual-only invocation (Open)

**Summary.** Should the skill set `disable-model-invocation: true`?

**Context.** "What's next?" is also an ordinary status question, which `plab-continue-session` and `plab-resolve-open-items` answer directly. A `--week` run launches up to ten agents.

**Desired outcome.** No accidental agent spend.

**Options / approaches.**

* **Option A:** Manual only.
* **Option B:** Auto-discoverable, with do-NOT clauses for status questions.

**Recommendation.** Option A, matching `plab-audit` and `plab-current-status`. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D5: Series letter (Open)

**Summary.** Which effort series does this work go under?

**Context.** The usage skill uses `UA-`. The pulse is a third audit-family skill beside `plab-audit` (`AU-`).

**Desired outcome.** Effort ids that say which skill they belong to.

**Options / approaches.**

* **Option A:** A new `PP-` series, registered in `scripts/gen-release-index.py` and the release-plans README.
* **Option B:** Fold it into `UA-`.

**Recommendation.** Option A. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
