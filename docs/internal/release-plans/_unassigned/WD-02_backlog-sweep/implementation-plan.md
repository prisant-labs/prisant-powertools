---
id: WD-02
title: "Implementation plan: plab-resolve-open-items --backlog sweep"
type: implementation-plan
status: draft
created: 2026-10-15
updated: 2026-10-15
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 5
---

# Implementation plan: plab-resolve-open-items --backlog sweep

Steps use checkbox syntax and phases run in order. A phase is done when every step is ticked and its Verification command has been run and its output quoted.

**Goal:** `/plab-resolve-open-items --backlog` gathers every pending item from the repository's typed planning documents and the newest session log in one script call, sorts them into three tiers, writes a dated backlog file, and walks the first ten with the same answer line, write-back and walk record the in-session walk already uses. Without `--backlog`, nothing about the skill changes.

**Spec:** `spec.md`

**Target version:** `plab-resolve-open-items` 1.1.0, on top of 1.0.2. Build this branch after the 1.0.2 fixes merge, because both edit the same skill and 1.0.2 defines the decisions-section heading rule this plan reuses.

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) in any file this plan touches. One paragraph per line.
- Gathering writes nothing. The only files a backlog walk writes are the backlog file, each item's home on the three surfaces, and the walk record.
- One definition of a decisions-section heading: the script imports it from `scripts/walk-check.py`, never re-declares it.
- The description grows by at most 120 characters.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | The gathering script returns every pending item in one call, and its tests prove it | AC-1, AC-2, AC-3, AC-4, AC-12 | agent | Not started |
| P2 | The backlog reference defines the tiers, the cap, the moot presentation and the backlog file | AC-5, AC-6, AC-7, AC-9, AC-10 | agent | Not started |
| P3 | `SKILL.md` runs the sweep, and the walk record names the backlog file | AC-8, AC-11 | agent | Not started |
| P4 | A headless backlog walk on a fixture repository proves the behaviour | AC-13, and behaviour evidence for AC-4 to AC-10 | agent | Not started |
| P5 | HISTORY row and usage README | N/A (release hygiene) | agent | Not started |

---

## Phase 1: The gathering script

**Goal:** `gather-backlog.py --repo <root> --json` prints every pending item from typed planning documents and the newest session log's Waiting on You list, writes nothing, and exits 2 naming the source when a source cannot be parsed.

**Files:** Create `skills/plab-resolve-open-items/scripts/gather-backlog.py` and `skills/plab-resolve-open-items/scripts/test-gather-backlog.py`.

**Fulfills:** AC-1, AC-2, AC-3, AC-4, AC-12

**Steps:**
- [ ] Step 1: Scaffold on `skills/plab-wrap-session/scripts/organize-logs.py`'s shape: `argparse`, `from __future__ import annotations`, stdlib only, `--repo` (default the current directory), `--json`, and the three-state exit contract (0 items or none found cleanly, 2 broken). The script resolves its own location from `Path(__file__).resolve().parent`.
- [ ] Step 2: List candidate documents with `git -C <repo> ls-files -- '*.md'`, then keep a file only when its frontmatter `type` is `spec`, `implementation-plan` or `release-plan`. A file with no frontmatter is skipped silently; a file whose frontmatter fence never closes is a broken source.
- [ ] Step 3: Load the heading rule from `scripts/walk-check.py` with `importlib.util.spec_from_file_location`, since the hyphenated name cannot be imported by name. Find the section, parse its summary table (`ID`, `Title`, `Resolution`, `Status`, `Updated`), and keep rows whose status is `Open`, `Needs info` or `Proposed`. A section whose table has no `Status` column is a broken source.
- [ ] Step 4: Find the newest session log by the newest-wins rule in `skills/plab-continue-session/references/log-discovery.md`: the flat `_local/_session-logs/` store and its `YYYY-MM/` folders, plus the two legacy paths, sorted by filename. Mirror the rule; do not edit that file. Extract each Waiting on You bullet verbatim with its `(blocked since YYYY-MM-DD)` date. A store that does not exist contributes nothing and is not broken.
- [ ] Step 5: Compute `age_days` against today's date: the row's `Updated`, else the document's `created`, else the bullet's `blocked since`; otherwise the literal `"unknown"`. Emit `home`, `id`, `title`, `status`, `age_days`, plus `source_kind` (`decisions-section` or `waiting-on`) and, for a decisions item, the home document's own frontmatter `status` so the agent can spot moot items.
- [ ] Step 6: Write `test-gather-backlog.py` on `test-organize-logs.py`'s pattern: a `check()` helper and fixture repositories built in a temporary directory with `git init`. Cases: the type filter (an untyped brief contributes nothing), all eight statuses, a numbered heading variant, an unparseable table (exit 2 naming the file), newest-wins across the flat store and a month folder, the age order with each fallback, and a no-write case hashing the fixture before and after.

**Verification:** `python skills/plab-resolve-open-items/scripts/test-gather-backlog.py` exits 0 with an all-pass summary. Then delete the status filter from the script, run the same command, and quote the failure naming the status case; restore the filter. Finally run `python skills/plab-resolve-open-items/scripts/gather-backlog.py --repo . --json` in this repository and quote the item count.

---

## Phase 2: The backlog reference

**Goal:** One reference file holds everything the agent needs to triage, present and record a sweep, so `SKILL.md` only points at it.

**Files:** Create `skills/plab-resolve-open-items/references/backlog.md`.

**Fulfills:** AC-5, AC-6, AC-7, AC-9, AC-10

**Steps:**
- [ ] Step 1: State the sources and the status filter in two sentences, naming the script as the only way to gather.
- [ ] Step 2: Define the tiers exactly as spec Requirement 6 does, with one checkable example of moot evidence for each `source_kind`: a home spec whose own status is `fulfilled` or `superseded`, and a Waiting on You bullet whose action the repository shows done, such as a merged pull request.
- [ ] Step 3: State the order and cap: ready, moot, judgment, oldest first within a tier, at most ten presented, and the report states how many remain.
- [ ] Step 4: State how a moot item is presented: a D item whose options are A, cancel it (recommended, with the evidence as reason), and B, keep it open. Accepting A writes `Canceled` on the home's three surfaces with the evidence as Reasoning.
- [ ] Step 5: State that a Waiting on You item is a T item, or a D item when the bullet names options, with the log as its source; its answer goes in the walk record only, and the log is never written.
- [ ] Step 6: Give the backlog file's path pattern `_local/decisions/YYYY-MM-DD_HH-MM_backlog.md` and its format: a header line with the date, the repository and the item count, then one table per tier with columns `Item`, `Home`, `Id`, `Status`, `Age (days)` and, under moot, `Evidence`. State that the file is never edited after the sweep.
- [ ] Step 7: State the empty case: one sentence, and no file.

**Verification:** `python scripts/check-dashes.py` exits 0, and a read of the file against spec Requirements 6 to 12 finds each one stated once.

---

## Phase 3: Wire the sweep into SKILL.md

**Goal:** `--backlog` runs the script, triages with `references/backlog.md`, writes the backlog file, and then continues through the existing steps 2 to 7 unchanged.

**Files:** Modify `skills/plab-resolve-open-items/SKILL.md`, `skills/plab-resolve-open-items/references/walk-record.md`, and `skills/plab-resolve-open-items/scripts/walk-check.py` only if the record check must accept a new header line.

**Fulfills:** AC-8, AC-11

**Steps:**
- [ ] Step 1: In the description, replace `Not yet built: the --backlog sweep across every spec, plan and log.` with a clause of at most 120 more characters naming `--backlog` as the repository-wide sweep. Measure both descriptions' lengths and quote them.
- [ ] Step 2: Change `argument-hint` from `"[<document>]"` to `"[--backlog | <document>]"`.
- [ ] Step 3: In Workflow step 1, add a `--backlog` branch: run `python <this skill's base directory>/scripts/gather-backlog.py --repo <project root> --json`; on exit 2, report the named source as broken and stop; otherwise triage with `references/backlog.md`, write the backlog file, and select the walk's items. Replace the empty-walk sentence's "note that the `--backlog` sweep is not built" with an offer to run `--backlog`.
- [ ] Step 4: Remove the `--backlog` bullet from "Not in this version". Add `references/backlog.md` to the References table.
- [ ] Step 5: In `references/walk-record.md`, add an optional `Backlog file:` header line naming the backlog file a walk came from. If `walk-check.py record` rejects an unknown header line, teach it this one, add a test case, and prove the committed sample still passes.

**Verification:** `python skills/plab-resolve-open-items/scripts/walk-check.py record skills/plab-resolve-open-items/examples/sample-walk/walk-record.md` exits 0, and a diff of `SKILL.md` shows only the description clause, the argument hint, Workflow step 1, the "Not in this version" list and the References table changed.

---

## Phase 4: Prove it by behaviour

**Goal:** A real headless session runs a backlog walk end to end on a fixture repository, so AC-13 rests on a transcript rather than on a reading of the instructions.

**Files:** None in the repository. The fixture and the transcript live in a temporary directory, and the results are reported in the pull request.

**Fulfills:** AC-13, with behaviour evidence for AC-4 to AC-10

**Steps:**
- [ ] Step 1: Build a fixture repository with `git init`: five typed specs and plans holding at least twelve pending items across all tiers, including one whose home spec is `fulfilled` (a moot candidate), an untyped brief with a decisions section, a copy of `references/decisions-section.md` at its root, and `_local/_session-logs/` holding two logs, the newer with two Waiting on You bullets.
- [ ] Step 2: Load the branch's skill into the fixture through a `.claude/skills/plab-resolve-open-items` junction to a `git archive` copy of the branch's skill folder. Run `claude -p "/plab-resolve-open-items --backlog"` with `--settings` setting `autoMemoryEnabled` to false and the installed `prisant-utilities@prisant-labs` plugin disabled, `--output-format stream-json --verbose`, and a turn cap.
- [ ] Step 3: Hash the session logs. Answer with `claude -p --resume <session-id>` and a scripted line that accepts one ready item, cancels the moot item, defers a T item from the log with `later`, and skips the rest.
- [ ] Step 4: Check: one backlog file exists and lists every gathered item under one tier; the walk showed ten items in tier order; each answered home passes `walk-check.py writeback` against its pre-walk copy; the walk record passes `walk-check.py record` and names the backlog file; the log hashes are unchanged; the brief's item never appeared. Run a second session on a fixture with nothing pending and confirm the one-sentence reply and no new file.

**Verification:** Quote each check's command and output in the pull request. AC-13 is ticked only when every check passes.

---

## Phase 5: HISTORY and usage README

**Goal:** The new mode is recorded where a reader looks for it. Version numbers are set by the closing release pull request, not here.

**Files:** Modify `skills/plab-resolve-open-items/HISTORY.md` and `docs/skills/plab-resolve-open-items/README.md` (body only, not its `**Version:**` line).

**Fulfills:** N/A (release hygiene)

**Steps:**
- [ ] Step 1: Add a 1.1.0 row to `HISTORY.md` with release column `unreleased`, naming the backlog sweep and its six working-default decisions.
- [ ] Step 2: In the usage README, replace any statement that `--backlog` is unbuilt with a short section on running it and what it writes.

**Verification:** `python scripts/version-parity-check.py` exits 0, since no claimed version changed.

---

## CI and Documentation Coverage

### CI

No CI change. `test-gather-backlog.py` joins `test-organize-logs.py` and the wrap and continue test scripts as a committed script the maintainer runs, because no workflow runs a skill's test script today and adding the first one changes what a red check means for every skill. `walk-check.py`, which CI already runs on the committed sample, keeps running unchanged; if Phase 3 teaches it a new header line, the sample check exercises that path.

### Documentation

`skills/plab-resolve-open-items/SKILL.md` and `references/walk-record.md` (Phase 3), the new `references/backlog.md` (Phase 2), `HISTORY.md` and the usage README body (Phase 5). The closing release pull request owns `CHANGELOG.md`, `library.json`, the root `README.md` skills table, `docs/status-skills.md`, the usage README's `**Version:**` line, the skill's `metadata.version`, and the generated manifests. `AGENTS.md`'s `plab-resolve-open-items` section says the `--backlog` sweep is not built; the closing pull request changes that sentence.

## Rollback

Delete `scripts/gather-backlog.py`, `scripts/test-gather-backlog.py` and `references/backlog.md`. In `SKILL.md`, restore the description's final sentence to `Not yet built: the --backlog sweep across every spec, plan and log.`, the argument hint to `"[<document>]"`, Workflow step 1's empty-walk sentence, and the "Not in this version" bullet, and remove the References row. Revert the `Backlog file:` line in `references/walk-record.md` and any matching `walk-check.py` change together, because the checker and the format must agree. No schema or data migration exists: backlog files and walk records already written stay in gitignored `_local/decisions/` and are harmless.
