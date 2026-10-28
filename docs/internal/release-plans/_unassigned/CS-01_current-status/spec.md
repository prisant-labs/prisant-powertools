---
id: CS-01
title: "plab-current-status: a dated, per-repository status snapshot"
type: spec
status: fulfilled
created: 2026-10-28
updated: 2026-10-28
linked-effort: "the maintainer's request of 2026-10-28 in session, and stream 3 (seeing everything in one place) of the maintainer's private consolidated status file of 2026-10-25"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 12
source-count: 9
requires-human-review: true
target-release: null
priority: P2
---

# Spec: plab-current-status, a dated per-repository status snapshot

## Task Summary

**Status:** fulfilled, shipped in v0.10.0
**Last updated:** 2026-10-28 by claude (Opus 5.5), written and committed under the maintainer's instruction to write and build it
**Linked plan:** `implementation-plan.md` in this folder
**Open questions:** 4, each built on its recommendation as a working default and awaiting ratification (see Open Questions / Decisions)
**Revisions:** 2

### Acceptance Criteria Fulfillment

- [x] AC-1: The skill is manual-only and does not fire on a status question
- [x] AC-2: Facts come from one script call that writes nothing in the working tree and reports broken rather than empty
- [x] AC-3: The facts name the repository's level and every source that was missing
- [x] AC-4: The backlog sweep can also return recent answers and unrecognised statuses, and its default output is unchanged
- [x] AC-5: The file lands at `_local/_status/YYYY-MM-DD_<model>_<byline>.md` and never overwrites
- [x] AC-6: The file carries the agreed frontmatter and the ten sections in order
- [x] AC-7: Every ranked item is numbered and says why it ranks where it does
- [x] AC-8: Every decision item names its home document
- [x] AC-9: The file says what changed since the previous snapshot, or that there is none
- [x] AC-10: Every gap the facts report appears in What I Don't Know
- [x] AC-11: Stdlib tests and a self-testing checker prove the scripts, each with a canary, and CI runs them
- [x] AC-12: A live run on this repository produces a file the checker passes

### Currently In Progress

None. Built on 2026-10-28 on `feat/plab-current-status`. Evidence: AC-2 and AC-3 by `test-derive-status-facts.py` (31 checks); AC-4 by `test-gather-backlog.py` (25 checks) and a byte comparison of the 1.1.0 and 1.2.0 default output on this repository; AC-5 to AC-10 by `status-check.py --self-test`, whose mutations fail each rule; AC-11 by the three canaries in the plan; AC-12 by a headless run whose snapshot the checker passed. AC-1's eval case exists but the eval suite has not been run, because each case is a full session on the maintainer's credential.

---

## Purpose

The maintainer has written a repository status document by hand at least twice: a status update on 2026-10-05 and a consolidated, ranked list of every open thread on 2026-10-25 [S1]. Each took a full session of reading logs, registers and specs, and each was out of date within days. A skill that produces the same document on demand turns that session into one command [S2].

The hand-written versions share a shape that worked: an "as of" header with the commit and tag, the sources read, a confidence key, a short answer first, what waits on the maintainer separated from the agent's own next moves, and a reason for every ranking [S1]. This spec keeps that shape.

The skill must stand alone. It runs in any repository, whether or not that repository has session logs, specs or decision records, and it does not depend on the cross-project browser page the maintainer chose on 2026-10-24 [S2, S3]. That page may later read these files, so each file carries machine-readable frontmatter, but nothing here builds it.

## Scope

### In Scope

1. A new skill, `skills/plab-current-status/`, manual-only, with `SKILL.md`, `HISTORY.md` and a format reference.
2. A stdlib-only facts script, `skills/plab-current-status/scripts/derive-status-facts.py`, with a sibling test script.
3. A stdlib-only checker, `skills/plab-current-status/scripts/status-check.py`, with a built-in self-test and a committed sample it passes.
4. An `--answered-since` argument to `skills/plab-resolve-open-items/scripts/gather-backlog.py`, with tests, and the minor version bump that adds it.
5. The plugin's registration of the new skill: `library.json`, the regenerated manifests, `AGENTS.md`, the root `README.md`, `CHANGELOG.md`, an eval case, and the CI steps.

### Non-Goals

1. **The cross-project browser page.** It is a separate, later piece that may read these files [S3].
2. **Gathering across repositories.** One run covers one repository [S2].
3. **A living page edited in place.** Each run writes a new dated snapshot. The 2026-10-25 file was edited in place the next day and drifted into replacing the register's role, which is the failure this avoids [S1].
4. **Answering or writing back decisions.** That is `plab-resolve-open-items`. This skill reads decisions and writes only its own file [S4].
5. **Writing to a session log, a spec, or any tracked file.** The snapshot is the only file a run writes.
6. **Moving the decisions sweep into `lib/`.** See D1.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | The only reader | Types `/plab-current-status`, optionally with a byline, and reads the file |
| Running agent (Claude Code or Codex) | Executes the skill | Runs the facts script, reads the sources it names, ranks, writes the file, runs the checker |

## Requirements

1. The skill carries `disable-model-invocation: true`. `plab-continue-session` and `plab-resolve-open-items` both answer status questions such as "where are we" directly, and a status skill that fired on those phrases would break that contract [S5].
2. Every fact about repository state comes from one invocation of `derive-status-facts.py`, which returns JSON. The facts are: the repository name, branch, head commit, whether the tree is clean, the upstream comparison, the latest tag, commits since that tag and since the previous snapshot, open and recently merged pull requests, the newest session log and every log written since the previous snapshot, the previous snapshot itself, and the decisions sweep's pending, recently answered and unrecognised items. Facts from a script rather than from the model's recall is the convention `plab-wrap-session` follows, because the number of calls sets a run's cost [S6].
3. The facts script writes no file in the working tree. A `git fetch` that updates remote-tracking refs is permitted, because it changes no tracked or untracked file. When the target is not a git repository, or a step that must succeed fails, the script exits 2 and names the cause rather than returning partial facts [model-inference].
4. The facts report the repository's level: `git-only` when it has neither session logs nor typed planning documents with a decisions section, `logs` when it has logs but no such documents, and `decisions` when it has such documents. Every source that could not be read for an expected reason, such as `gh` being absent, no remote, or no logs, is listed as a named gap rather than treated as broken [S2, S7].
5. The decisions sweep is `gather-backlog.py`, called by its path inside the plugin. A new `--answered-since YYYY-MM-DD` argument makes it also return items whose status is an answer and whose `Updated` date is on or after that date, and items whose status is outside the vocabulary of `references/decisions-section.md`. Each item then carries a `kind` of `pending`, `answered` or `unrecognised`. Without the argument, its output is byte-identical to before. Unrecognised statuses are returned because six open items were invisible to every sweep until 2026-10-26, when their status words were found to be outside the vocabulary [S4, S8].
6. The snapshot is written to `_local/_status/YYYY-MM-DD_<model>_<byline>.md`. `<model>` is the short name of the running model, such as `opus-5-5`, derived from the model id by dropping the vendor prefix. `<byline>` is two to six lowercase kebab-case words summarising the snapshot. An existing file is never overwritten; the agent chooses a different byline instead [S2].
7. The facts report whether `_local/_status/` is ignored by git. When it is not, the skill asks the maintainer before writing, and offers to add `_local/` to `.gitignore`, because the snapshot carries machine paths and candid narrative that should not be committed [model-inference, following the maintainer's global rule for session logs].
8. The snapshot opens with YAML frontmatter carrying `type: status-snapshot`, `date`, `model`, `repo`, `branch`, `head`, `level`, `previous` (the previous snapshot's filename or `none`), and three integer counts: `waiting`, `pending-decisions` and `next`, each the total number of items before any cap. The counts let a later consumer, such as the browser page, read the file without parsing its prose [S2].
9. The body carries these level-2 sections, in this order: The Answer; Changed Since Last Status; Waiting on You; What's Next; Pending Decisions; Recent Decisions; Accomplished; Where the Project Is; What I Don't Know. Before the first section, an "as of" paragraph states the commit, tag, pull-request state and tree state, and names the sources read and the confidence key [S1, S2].
10. Waiting on You, What's Next and Pending Decisions are ranked numbered lists. Each item carries a `Why here:` clause saying why it ranks above the next one. The 2026-10-25 file's reasons for its order were what made it a prioritised list rather than an inventory [S1].
11. Every item under Pending Decisions and Recent Decisions pairs its id with a short handle and names its home document as a backticked path, following the maintainer's global rule that a reference id never stands alone [S9].
12. Changed Since Last Status names the previous snapshot by filename, or states that no previous snapshot exists. Only files matching the snapshot filename pattern count as previous snapshots, so older hand-written files in the folder and any register kept there are never mistaken for one.
13. What I Don't Know lists every gap the facts reported, and adds any the agent found while reading. A silent gap would make the file look more complete than it is, which is the rule `plab-audit`'s coverage statement follows [S7].
14. `status-check.py` verifies Requirements 6 and 8 to 13 on a written file and exits 0 when clean, 1 when a rule fails, and 2 when it cannot prove itself. It proves every rule can fail against its committed sample before reporting clean, as the repository's other checkers do [S6, S7].

## Acceptance Criteria

**AC-1:** `skills/plab-current-status/SKILL.md` carries `disable-model-invocation: true`, and an eval case whose prompt is a status question asserts that the skill is not invoked. [S5]

**AC-2:** Given a fixture repository, running `derive-status-facts.py --repo <fixture> --json` twice leaves `git status --porcelain` and a hash of every file under the fixture unchanged, and the JSON carries every fact Requirement 2 names. Given a directory that is not a git repository, the script exits 2 and names the cause. [model-inference]

**AC-3:** Given three fixtures, one with git only, one adding a session log, and one adding a spec with an open decision, the facts report `level` as `git-only`, `logs` and `decisions` respectively. In the git-only fixture, `gaps` names the session logs and the decision documents. With `gh` unavailable, `gaps` names the pull requests and the exit code is 0. [S2, S7]

**AC-4:** For a fixture holding items in every status, plus one with an out-of-vocabulary status, `gather-backlog.py --json` output is byte-identical with and without the change. With `--answered-since`, the output adds exactly the answered items whose `Updated` date is on or after the given date and the out-of-vocabulary item, each carrying the correct `kind`. [S4, S8]

**AC-5:** `status-check.py` rejects a file whose path is not under `_local/_status/`, or whose name does not match `YYYY-MM-DD_<model>_<byline>.md` with a two-to-six-word byline. `SKILL.md` instructs that an existing file is never overwritten. [S2]

**AC-6:** `status-check.py` rejects a file missing any frontmatter field Requirement 8 names, carrying a non-integer count, or missing any section of Requirement 9 or holding them out of order. [S1, S2]

**AC-7:** `status-check.py` rejects a file in which any numbered item under Waiting on You, What's Next or Pending Decisions lacks a `Why here:` clause, and one whose section holds a number of numbered items other than the smaller of its frontmatter count (`waiting`, `pending-decisions` or `next`) and ten. [S1]

**AC-8:** `status-check.py` rejects a file in which any list item under Pending Decisions or Recent Decisions carries no backticked path. [S9]

**AC-9:** `status-check.py` rejects a file whose Changed Since Last Status section neither names the frontmatter's `previous` filename nor, when `previous` is `none`, says that no previous snapshot exists.

**AC-10:** Given `--facts <facts.json>`, `status-check.py` rejects a file whose What I Don't Know section omits any gap the facts list. [S7]

**AC-11:** `test-derive-status-facts.py` and `gather-backlog.py`'s test script exit 0, and `status-check.py --self-test` exits 0 against the committed sample. Removing the level rule from the facts script makes its test fail and name the level case; removing the `--answered-since` filter makes the backlog test fail; and disabling any one checker rule makes the self-test exit 2. CI runs all three. [S6]

**AC-12:** Running `/plab-current-status` on this repository writes one file under `_local/_status/`, and `status-check.py --facts` passes it. [model-inference: the live run is this spec's own test design]

## Behavior / Examples

### Example 1: This repository

The maintainer types `/plab-current-status`. The facts script reports level `decisions`, `main` level with `origin`, tag v0.9.0, three merged pull requests since the previous snapshot, nineteen pending decision items, two answered in the last fourteen days, and one gap: the previous snapshot is `none`, because no file yet matches the pattern. The agent reads the newest session log and the pending items' home sections, ranks them, and writes `_local/_status/2026-10-28_opus-5-5_status-skill-built.md`. The checker passes it, and the agent replies with the file's path and its The Answer section.

### Example 2: A repository with only git

In a repository with no logs and no specs, the facts report level `git-only` and gaps for session logs and decision documents. The snapshot's Accomplished and Where the Project Is sections come from commits and tags. Pending Decisions says no decision record was found, and What I Don't Know names both gaps.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Cost | Repository facts are one tool call. The agent reads only the documents the facts name. | [S6] |
| Portability | Both scripts are stdlib-only Python, and the skill works in Claude Code and Codex alike. | [S6] |
| Safety | A run writes one file under gitignored `_local/`, and asks first when that folder is not ignored. | [model-inference] |
| Context budget | The description is at most 600 characters, because it is loaded in every session even for a manual-only skill. | [S5] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-10-28 | claude | added | Initial spec, written and committed the same day under the maintainer's instruction to write and build it. The four decisions below are built on their recommendations as working defaults and stay `Open` until the maintainer ratifies or overturns them. |
| 2026-10-28 | claude | status | Status moved to `fulfilled`: all twelve acceptance criteria were verified with the evidence in the Task Summary, and the skill ships in v0.10.0. D1 to D4 remain `Open`; a later answer that overturns one changes the skill in a follow-up version, not this spec's criteria. |

## Sources & Evidence

- **[S1]** The maintainer's two hand-written status documents, 2026-10-05 and 2026-10-25. Maintainer-local, gitignored. Class A, read for their shared shape, their ranking reasons, and the in-place edit of the second.
- **[S2]** The maintainer's rulings in session on 2026-10-28: the output folder and filename, acceptance of the proposed outline, and a standalone skill that may later feed the browser page. Class A.
- **[S3]** The maintainer's choice of 2026-10-24 that the cross-project waiting list goes in a browser page. Maintainer-local memory. Class A.
- **[S4]** `docs/internal/release-plans/_unassigned/WD-02_backlog-sweep/spec.md` and `skills/plab-resolve-open-items/scripts/gather-backlog.py`. Class A.
- **[S5]** `AGENTS.md`, the design frame and the manual-only rulings for `plab-audit` and `plab-init-project`, and the descriptions of `plab-continue-session` and `plab-resolve-open-items`. Class A.
- **[S6]** `skills/plab-wrap-session/scripts/derive-log-facts.py` and the measurement it cites: the number of calls sets a run's cost. Class A.
- **[S7]** `skills/plab-audit/references/coverage-statement.md`, which makes a missing tool a recorded gap rather than a silence. Class A.
- **[S8]** PR #47 (closing verified decision items), merged 2026-10-26, which found six open items whose status words no sweep recognised. Class A.
- **[S9]** The maintainer's global instructions, which require every reference id to carry a human-readable handle. Maintainer-local, outside this repository. Class A.

### Unverified Claims

- Requirement 3 and AC-2, that a failed required step should stop the facts script with exit 2. This is the repository's three-state gate rule applied to a new script, marked `[model-inference]`.
- Requirement 7, that an unignored `_local/_status/` warrants a question before writing. It follows the maintainer's global rule for session logs rather than a ruling about this skill, marked `[model-inference]`.
- Requirement 11 cites the maintainer's global instructions on reference ids, which live outside this repository.
- AC-12's live run is this spec's own test design.

## Open Questions / Decisions

**What these statuses mean.** Every item below is `Open`: the maintainer has not chosen. Each Recommendation ends by saying the build used it as a working default, so a walk can ratify or overturn it. The build followed the maintainer's instruction of 2026-10-28 to write and build the skill.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Where the decisions sweep lives | (none) | Open | 2026-10-28 |
| D2 | Whether the facts script fetches before comparing with the remote | (none) | Open | 2026-10-28 |
| D3 | The look-back window for recent decisions and accomplishments | (none) | Open | 2026-10-28 |
| D4 | How many items each ranked section shows | (none) | Open | 2026-10-28 |

### D1: Where the decisions sweep lives (Open)

**Summary.** Whether the new skill calls `gather-backlog.py` in its current home, or the sweep moves to the plugin's shared `lib/` folder first.

**Context.** `lib/README.md` says logic two skills invoke belongs in `lib/`. But `gather-backlog.py` loads `walk-check.py` from its own folder to share the decisions heading definition, so moving the sweep would either move the walk checker too or make `lib/` depend on a skill folder. The plugin ships every skill together, so a plugin-relative path always resolves.

**Desired outcome.** One definition of a decisions section, and no refactor of a working skill that this effort does not need.

**Options / approaches.**

* **Option A:** Call `gather-backlog.py` by its plugin path, with the new `--answered-since` argument. Default output unchanged.
* **Option B:** Move `gather-backlog.py` and the parsing half of `walk-check.py` into `lib/` first, then call that.
* **Option C:** Give the new skill its own parser.

**Recommendation.** Option A. It adds one argument and changes no existing behaviour, while Option B refactors a shipped skill and Option C creates a second definition that could drift. Revisit if a third skill needs the sweep. Working default: built on this recommendation on 2026-10-28 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Whether the facts script fetches before comparing with the remote (Open)

**Summary.** Whether "level with GitHub" is checked against a fresh fetch or against the last one.

**Context.** A status that says the branch is level with the remote is only true as of the last fetch. `plab-continue-session`'s reconcile step fetches with `git fetch --no-prune origin --tags`, because a plain fetch with `fetch.prune=true` prunes. A fetch needs the network and can hang.

**Desired outcome.** The upstream comparison is current when the network is available, and a failed fetch is visible rather than silent.

**Options / approaches.**

* **Option A:** Fetch with `--no-prune origin --tags` and a timeout. A failed fetch becomes a named gap, and the comparison is reported as of the last fetch.
* **Option B:** Never fetch; report the comparison as of the last fetch and say so.

**Recommendation.** Option A, because the "as of" line is the one fact every reader trusts without checking. Working default: built on this recommendation on 2026-10-28; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D3: The look-back window for recent decisions and accomplishments (Open)

**Summary.** How far back Recent Decisions and Accomplished reach.

**Context.** The natural boundary is the previous snapshot, so each file covers what the last one did not. The first run in a repository has no previous snapshot.

**Desired outcome.** Consecutive snapshots neither overlap much nor leave a gap, and a first run is still useful.

**Options / approaches.**

* **Option A:** Since the previous snapshot's date; with none, since the latest tag for accomplishments and 14 days for decisions.
* **Option B:** A fixed 14 days always.

**Recommendation.** Option A, because it makes consecutive snapshots read as a chain. Working default: built on this recommendation on 2026-10-28; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D4: How many items each ranked section shows (Open)

**Summary.** Whether Waiting on You, What's Next and Pending Decisions are capped.

**Context.** The backlog sweep returned 42 items on 2026-10-25, and the hand-built consolidation reduced them to one action and two answers. A list of 42 is an inventory, not a priority.

**Desired outcome.** The top of each list is the part that gets read, and nothing is silently dropped.

**Options / approaches.**

* **Option A:** Show at most ten per section, ranked, and state how many more exist and where they live.
* **Option B:** Show everything.

**Recommendation.** Option A, the same cap `plab-resolve-open-items --backlog` uses. Working default: built on this recommendation on 2026-10-28; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
