---
id: WD-02
title: "plab-resolve-open-items --backlog: sweep the repository's open items into one triaged walk"
type: spec
status: committed
created: 2026-10-15
updated: 2026-10-15
linked-effort: "the maintainer's private walk-decisions strategy brief, 2026-10-04, and WD-01's Non-Goal 1"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 13
source-count: 8
requires-human-review: true
target-release: null
priority: P2
---

# Spec: plab-resolve-open-items --backlog, the repository-wide sweep

## Task Summary

**Status:** committed
**Last updated:** 2026-10-15 by claude (Opus 5.5), written and committed under the maintainer's instruction to build it
**Linked plan:** `implementation-plan.md` in this folder
**Open questions:** 6, each built on its recommendation as a working default and awaiting ratification (see Open Questions / Decisions)
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: `--backlog` gathers from planning documents and the newest session log's Waiting on You, and from nothing else
- [ ] AC-2: Only items whose status is `Open`, `Needs info` or the legacy `Proposed` are gathered
- [ ] AC-3: Gathering is one script call that writes nothing and reports broken rather than empty
- [ ] AC-4: Every item carries its home, its own id, its status and its age, or says its age is unknown
- [ ] AC-5: Every item lands in exactly one of three tiers, and a moot item states its evidence
- [ ] AC-6: Every non-empty sweep writes one dated backlog file that is never edited afterwards
- [ ] AC-7: One backlog walk presents at most ten items, in tier order and oldest first
- [ ] AC-8: Answers apply exactly as in the in-session walk, and the walk record names the backlog file
- [ ] AC-9: A session log is never written; its items are answered in the walk record only
- [ ] AC-10: An empty sweep says so in one sentence and writes nothing
- [ ] AC-11: The description and argument hint name `--backlog` as built, within a fixed character budget
- [ ] AC-12: A stdlib test script proves the gathering script against fixture repositories, with a canary
- [ ] AC-13: A headless backlog walk on a fixture repository proves AC-4 to AC-10 by behaviour

### Currently In Progress

None. The spec and plan were written on 2026-10-15; the build follows in its own pull request.

---

## Purpose

WD-01 (the in-session walk) built `plab-resolve-open-items` to settle what one session left open. It deliberately left out the larger case, the sweep across a whole repository, as slice 2 [S1]. This spec is that slice.

The problem slice 2 solves is aging, not presentation. Items that needed the maintainer's yes waited 17 to 31 days regardless of size, while decisions made in the moment got done [S2]. A sweep creates that moment on purpose, for the items no single session will bring up again.

The signal already exists. Every spec and plan this plugin writes carries an Open Questions / Decisions section, and every deep session log carries a Waiting on You list with a `blocked since` date. Nothing reads them across the repository [S3]. The hand-built sweeps showed the other half of the problem: one grew past 40 items, while three to five were worth surfacing at once [S2, S3]. So the sweep must triage and cap, not list everything.

A hand-built decision register already solved triage well, by sorting items into three tiers: ready for a yes or no, probably moot, and needing real judgment [S4]. This spec adopts those tiers rather than inventing new ones.

## Scope

### In Scope

1. A `--backlog` argument to `plab-resolve-open-items` that gathers open items across the current repository, triages them, writes a dated backlog file, and then walks the first ten.
2. A stdlib-only gathering script, `skills/plab-resolve-open-items/scripts/gather-backlog.py`, returning every candidate item in one call, with a sibling test script.
3. A new reference, `skills/plab-resolve-open-items/references/backlog.md`, holding the sources, the tiers, the cap, and the backlog file's format.
4. Edits to the skill's `SKILL.md`: the `--backlog` workflow, the argument hint, and the description's "Not yet built" clause, plus the usage README's body.
5. A `HISTORY.md` row for the minor version this adds.

### Non-Goals

1. **The options board and the living status page.** Both are separate proposals in the maintainer's decision register. The backlog file is a dated snapshot, not a living page, and nothing here builds either surface (D5).
2. **Gathering across repositories.** A sweep covers the current repository only, as the in-session walk does [S1].
3. **Reading a document in another format.** A decision register or an `OPEN.md` that does not follow `references/decisions-section.md` is not parsed. Walking one named document already covers a register once it is converted [S1].
4. **Writing to a session log.** Logs are dated records, and `plab-continue-session` never modifies the log it resumes from [S6].
5. **Automatic GitHub filing, a Projects board, or a published web page.** These stay deferred, as WD-01 names them [S1].
6. **Changing the in-session walk.** Without `--backlog`, the skill behaves exactly as before.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | The only person who answers | Types `/plab-resolve-open-items --backlog` or asks to walk the backlog, reads the tiered items, and answers in one line |
| Running agent (Claude Code or Codex) | Executes the skill | Runs the gathering script, triages, writes the backlog file, presents the walk, applies answers and writes the walk record |

## Requirements

1. With `--backlog`, gathering reads exactly two kinds of source. The first is the Open Questions / Decisions section of every git-tracked Markdown file whose frontmatter `type` is `spec`, `implementation-plan` or `release-plan`. The second is the Waiting on You section of the newest session log, found by `plab-continue-session`'s newest-wins rule [S3, S6].
2. An item from a decisions section is gathered only when its summary-table status is `Open`, `Needs info` or the legacy `Proposed`. The other statuses record an answer and are not pending [S5]. A Waiting on You bullet is pending by definition.
3. A decisions section is recognised by the same heading definition that `scripts/walk-check.py` uses, so the sweep never gathers from a section the checker cannot verify.
4. Gathering is one invocation of `gather-backlog.py`. It reads the repository and the session-log store, writes nothing, and returns JSON. When a source it should read cannot be read or parsed, it exits 2 and names the source, rather than returning a shorter list [S7, model-inference].
5. Each gathered item carries its home document, its own id there, its title, its status, and its age in days. Age comes from the summary row's `Updated` date, else the document's `created` date, else the bullet's `blocked since` date. An item with none of these is marked `age unknown`, never given an invented age.
6. The running agent assigns each item to exactly one tier: **ready**, a D or Q item with a recommendation that is small and blocks nothing else; **moot**, an item whose premise later work removed; or **judgment**, everything else. A moot item states its evidence, for example that its home spec is `fulfilled` or `superseded` while the item is still open [S4].
7. Every sweep that gathers at least one item writes one backlog file at `_local/decisions/YYYY-MM-DD_HH-MM_backlog.md`, beside the walk records. It lists every gathered item with its tier, age, home and id. It is a snapshot and is never edited after the sweep [S2].
8. One backlog walk presents at most ten items: ready first, then moot, then judgment, oldest first within each tier. The report states how many items remain in the backlog file [S2, S3].
9. A moot item is presented as a D item whose recommended option is to cancel it, with the evidence as the recommendation's reason. Accepting it writes `Canceled` on the three surfaces of its home, with the evidence as the reasoning [S5].
10. Answers apply exactly as in the in-session walk: the one-line answer, the three-surface write-back, one home per item, the branch guard, explicit acceptance only, and the walk record [S1]. The walk record names the backlog file it walked.
11. An item from a session log's Waiting on You list is presented as a T item, or as a D item when the bullet itself names options, with the log as its source. Its answer is recorded in the walk record only. The log is never written.
12. When the sweep gathers nothing, the skill says so in one sentence and writes neither a backlog file nor a walk record.
13. The skill's description stops calling `--backlog` unbuilt and names it as a mode, growing by no more than 120 characters. The argument hint becomes `[--backlog | <document>]`.

## Acceptance Criteria

**AC-1:** Given a repository holding a spec, a plan, a release plan, an untyped brief with a decisions section, and a session-log store, when `--backlog` gathers, then items come only from the three typed documents and from the newest log's Waiting on You section. The brief contributes nothing. [S3, S6]

**AC-2:** Given decisions sections holding items in all eight statuses (`Open`, `Needs info`, `Proposed`, `Decided`, `Provisional`, `Deferred`, `Canceled`, `Superseded`), when gathering runs, then exactly the `Open`, `Needs info` and `Proposed` items are returned. [S5]

**AC-3:** `gather-backlog.py` makes no filesystem write: hashing the fixture repository and log store before and after a run gives identical results. Given a typed document whose decisions table cannot be parsed, the script exits 2 and names that file. [S7, model-inference]

**AC-4:** Every gathered item in the script's JSON carries `home`, `id`, `title`, `status` and `age_days`, where `age_days` is an integer or the literal `"unknown"`, derived by the order in Requirement 5.

**AC-5:** In a backlog file, every item appears under exactly one of the three tiers, and every item under **moot** carries a one-line evidence statement naming a checkable fact. [S4]

**AC-6:** A sweep that gathers at least one item writes exactly one file matching `_local/decisions/YYYY-MM-DD_HH-MM_backlog.md`. Any later answer changes the items' homes and the walk record, never the backlog file. [S2]

**AC-7:** Given more than ten gathered items, the walk presents exactly ten, ordered ready, moot, judgment and oldest first within a tier, and its report states the number left in the backlog file. [S2, S3]

**AC-8:** Answers to backlog items pass `walk-check.py writeback` on each changed home, and the walk record passes `walk-check.py record` and names the backlog file. [S1]

**AC-9:** After a backlog walk that answered an item drawn from a session log, the log's hash is unchanged and the item's answer appears in the walk record. [S6]

**AC-10:** Given a repository with no pending item in any source, `--backlog` replies in one sentence and creates no file under `_local/decisions/`.

**AC-11:** The `description` names `--backlog` as a mode and no longer says it is unbuilt, and it is at most 120 characters longer than the 1.0.2 description. The `argument-hint` is `[--backlog | <document>]`.

**AC-12:** `test-gather-backlog.py` exits 0 against fixture repositories covering AC-1 to AC-4, the newest-wins log choice across the flat store and a month folder, and the age order. With the status filter removed from the script, the same command fails and names the status case.

**AC-13:** A headless `--backlog` walk on a fixture repository with at least twelve pending items, driven by a scripted answer line, produces a backlog file, presents ten items in tier order, writes the answers back, and leaves the fixture's session log unchanged. The transcript and the files are the evidence for AC-4 to AC-10. [model-inference: the fixture and the scripted answers are this spec's own test design]

## Behavior / Examples

### Example 1: A sweep with three tiers

The maintainer types `/plab-resolve-open-items --backlog`. The script returns fourteen items from five specs and the newest log. The agent sorts them: four ready, two moot, eight judgment. It writes `_local/decisions/2026-10-20_09-14_backlog.md` and presents ten:

```
Backlog: 14 open items, 10 shown. Full list: _local/decisions/2026-10-20_09-14_backlog.md

Ready for a yes or no
D1  C-02 (reconcile at resume) OQ3, fetch timeout. Waited 5 days.
    A: 20 seconds (recommended)  B: 60 seconds
...
Probably moot
D5  C-04 (consumption disposition) OQ2. Waited 21 days.
    Its home spec is superseded by C-06. A: Cancel it (recommended)  B: Keep it open
...
```

The maintainer answers `D1 A, D5 A, D6 later`. The answers land in each home spec and in the walk record, and the report says four items remain in the backlog file.

### Example 2: Nothing open

The script returns no items. The skill replies: "Nothing is open across this repository's specs, plans and newest session log." No file is written.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Cost | Gathering is one tool call however many documents exist, because the number of calls drives a session's cost far more than its text does. | [S7] |
| Portability | The script is stdlib-only Python, like every other script in this plugin, and the walk works in Claude Code and Codex alike. | [S1] |
| Safety | Every tracked file the sweep writes cites no `_local/` path. The backlog file itself lives under gitignored `_local/`. | [S1] |
| Context budget | The description grows by at most 120 characters, because it is loaded in every session. | [S8] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-10-15 | claude | added | Initial spec, written and committed the same day under the maintainer's instruction to build the backlog sweep. All six decisions below are built on their recommendations as working defaults and stay `Open` until the maintainer ratifies or overturns them. |

## Sources & Evidence

- **[S1]** `docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md`, the in-session walk's spec. Class A, read for Non-Goal 1, the Backlog section, D8 (overlap with the options board and status document), D10 (the T series), and the answer, write-back and record requirements this spec reuses.
- **[S2]** The maintainer's private walk-decisions strategy brief, 2026-10-04. Maintainer-local, gitignored. Class A. Its backlog mode gathers spec and plan decisions tables and the newest log's Waiting on You list, triages into three tiers, caps a walk, and writes a standalone file. It records that items needing a yes waited 17 to 31 days, and that one hand-built sweep grew past 40 items.
- **[S3]** A private toolchain design document, 2026-08-26, sections 8.1 and 8.7. Maintainer-local, gitignored. Class A. It measured that every spec and plan carries an Open Questions / Decisions section and every deep log a Waiting on You list, that nothing reads them, and that three to five of 40-plus items were worth surfacing at once.
- **[S4]** The maintainer's private decision register. Maintainer-local, gitignored. Class A. Its three tiers, ready for a yes or no, probably moot, and needing real judgment, were used by hand in several sittings.
- **[S5]** `references/decisions-section.md`, the shared decisions format and its seven statuses. Class A.
- **[S6]** `skills/plab-continue-session/references/log-discovery.md` and that skill's constraint never to modify the log it resumes from. Class A.
- **[S7]** The maintainer's private measurement of wrap and continue cost, 2026-10-01: the number of assistant calls drives a session's cost far more than the length of its text. Maintainer-local, gitignored. Class A for the counts.
- **[S8]** `AGENTS.md`, the design frame: always-on context cost is paid by one person in every session. Class A.

### Unverified Claims

- Requirement 4 and AC-3, that an unparseable typed document should stop the sweep with exit 2 rather than be skipped. This is the repository's three-state gate rule applied to a new script, marked `[model-inference]`.
- AC-13's fixture and scripted answers are this spec's own test design, marked `[model-inference]`.

## Open Questions / Decisions

**What these statuses mean.** Every item below is `Open`: the maintainer has not chosen. Each Recommendation ends by saying the build used it as a working default, so a walk can ratify or overturn it. The build followed the maintainer's instruction of 2026-10-15 to complete this work.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Which sources the sweep reads | (none) | Open | 2026-10-15 |
| D2 | How items are triaged and ordered | (none) | Open | 2026-10-15 |
| D3 | How many items one walk presents | (none) | Open | 2026-10-15 |
| D4 | What the backlog file is | (none) | Open | 2026-10-15 |
| D5 | Overlap with the options board and status page | (none) | Open | 2026-10-15 |
| D6 | How gathering runs | (none) | Open | 2026-10-15 |

### D1: Which sources the sweep reads (Open)

**Summary.** Which documents a backlog sweep gathers from.

**Context.** The design brief named spec and plan decisions tables, the newest log's Waiting on You list, and `OPEN.md` where one exists [S2]. This repository has no `OPEN.md`, and the maintainer's register uses its own format. Reading every tracked Markdown file would also gather the example decisions sections inside skill references and fixtures.

**Desired outcome.** The sweep finds every real open item and no example or template item.

**Options / approaches.**

* **Option A:** Typed planning documents (frontmatter `type` of `spec`, `implementation-plan` or `release-plan`) plus the newest log's Waiting on You list. Precise, and it skips examples by construction. A brief or register is walked by naming it.
* **Option B:** Option A plus `OPEN.md` and the register, each parsed in its own format. Wider, but two more parsers for formats this plugin does not own.
* **Option C:** Every tracked Markdown file with a decisions section. Widest, and it gathers fixture and template items as noise.

**Recommendation.** Option A. It reads only what this plugin writes, and the named-document walk already reaches everything else. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: How items are triaged and ordered (Open)

**Summary.** Whether the sweep sorts items into tiers, and in what order a walk presents them.

**Context.** The maintainer's register sorted its items into ready, probably moot, and judgment, and suggested taking ready and moot items in one short sitting before the judgment calls [S4]. Pure age order would put a hard judgment call ahead of a quick yes.

**Desired outcome.** The quick answers come first, so a short sitting clears the most items.

**Options / approaches.**

* **Option A:** Three tiers, presented ready, then moot, then judgment, oldest first within each.
* **Option B:** No tiers; oldest first across everything.
* **Option C:** Three tiers, judgment first, because those items matter most.

**Recommendation.** Option A. It is the order the hand-built register already used, and ready and moot items take seconds each. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D3: How many items one walk presents (Open)

**Summary.** The cap on items presented in one backlog walk.

**Context.** One hand-built sweep grew past 40 items, and three to five of 40-plus were worth surfacing at once [S2, S3]. The register's suggested first sitting covered nine items in about five minutes [S4].

**Desired outcome.** One walk is short enough to finish, and nothing is lost by the cap.

**Options / approaches.**

* **Option A:** Ten items; the rest stay in the backlog file and the report says how many.
* **Option B:** Five items, matching the toolchain document's finding.
* **Option C:** No cap.

**Recommendation.** Option A. Ten matches the register's own first sitting, and ready and moot items answer fast. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D4: What the backlog file is (Open)

**Summary.** Whether each sweep writes a new dated file or rewrites one living file.

**Context.** Answers already land in each item's home and in the walk record. A living file would duplicate that record and drift from it, while a dated snapshot records what the sweep saw.

**Desired outcome.** The maintainer can see what was open on a given day without a second record to keep in sync.

**Options / approaches.**

* **Option A:** A dated snapshot per sweep in `_local/decisions/`, beside the walk records, never edited afterwards.
* **Option B:** One living `_local/decisions/backlog.md`, rewritten on every sweep.

**Recommendation.** Option A. The homes and the walk record already carry the answers, and a snapshot cannot drift. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D5: Overlap with the options board and status page (Open)

**Summary.** Whether the sweep should become, or merge with, the proposed options board and living status page.

**Context.** WD-01's D8 (overlap with the options board and status document) deferred this question to the design of this mode [S1]. Both surfaces would show what waits on the maintainer, as the sweep does. Neither is built, and both sit in the maintainer's register as separate proposals.

**Desired outcome.** One surface per job, and nothing built here that a later decision on those proposals would have to undo.

**Options / approaches.**

* **Option A:** The sweep reads what exists and builds neither surface. The backlog file is a dated snapshot, which either proposal could later read.
* **Option B:** Make the backlog file the living status page now.
* **Option C:** Decide the options board and status page first, and pause this mode.

**Recommendation.** Option A. It answers the aging problem now and leaves both proposals open, because a snapshot is something either could consume. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D6: How gathering runs (Open)

**Summary.** Whether gathering is a script or the agent reading documents one at a time.

**Context.** A repository can hold dozens of specs and plans. Read one by one, a sweep costs one tool call per document, and the number of calls drives a session's cost [S7]. A script also lets the status filter and the age rule be tested.

**Desired outcome.** Gathering is cheap, deterministic and tested, and judgment stays with the agent.

**Options / approaches.**

* **Option A:** A stdlib script returns every candidate in one call; the agent triages.
* **Option B:** The agent reads each document and gathers by hand.

**Recommendation.** Option A. One call however large the repository, and its filter has a canary. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
