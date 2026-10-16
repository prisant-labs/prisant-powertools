---
id: WD-02
title: "Implementation plan: plab-resolve-open-items --backlog sweep"
type: implementation-plan
status: complete
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
| P1 | The gathering script returns every pending item in one call, and its tests prove it | AC-1, AC-2, AC-3, AC-4, AC-12 | agent | Done |
| P2 | The backlog reference defines the tiers, the cap, the moot presentation and the backlog file | AC-5, AC-6, AC-7, AC-9, AC-10 | agent | Done |
| P3 | `SKILL.md` runs the sweep, and the walk record names the backlog file | AC-8, AC-11 | agent | Done |
| P4 | A headless backlog walk on a fixture repository proves the behaviour | AC-13, and behaviour evidence for AC-4 to AC-10 | agent | Done |
| P5 | HISTORY row and usage README | N/A (release hygiene) | agent | Done |

---

## Phase 1: The gathering script

**Goal:** `gather-backlog.py --repo <root> --json` prints every pending item from typed planning documents and the newest session log's Waiting on You list, writes nothing, and exits 2 naming the source when a source cannot be parsed.

**Files:** Create `skills/plab-resolve-open-items/scripts/gather-backlog.py` and `skills/plab-resolve-open-items/scripts/test-gather-backlog.py`.

**Fulfills:** AC-1, AC-2, AC-3, AC-4, AC-12

**Steps:**
- [x] Step 1: Scaffold on `skills/plab-wrap-session/scripts/organize-logs.py`'s shape: `argparse`, `from __future__ import annotations`, stdlib only, `--repo` (default the current directory), `--json`, and the three-state exit contract (0 items or none found cleanly, 2 broken). The script resolves its own location from `Path(__file__).resolve().parent`.
- [x] Step 2: List candidate documents with `git -C <repo> ls-files -- '*.md'`, then keep a file only when its frontmatter `type` is `spec`, `implementation-plan` or `release-plan`. A file with no frontmatter is skipped silently; a file whose frontmatter fence never closes is a broken source.
- [x] Step 3: Load the heading rule from `scripts/walk-check.py` with `importlib.util.spec_from_file_location`, since the hyphenated name cannot be imported by name. Find the section, parse its summary table (`ID`, `Title`, `Resolution`, `Status`, `Updated`), and keep rows whose status is `Open`, `Needs info` or `Proposed`. A section whose table has no `ID` or `Status` column is a broken source. **Built wider than first written:** a real-repository dry run (18 of this repository's own specs still use a pre-standard three-column table, `ID | Question | Status` or `ID | Item | Status`, with no `Title`, `Resolution` or `Updated` column) showed that requiring `Title` too would make `--backlog` broken against most of this repository today. `Title` is now optional: missing, the script falls back to the first column that is neither `ID` nor `Status` (`Question`, `Item`, and so on), then to the literal `"(untitled)"`. Only a missing `ID` or `Status` column still exits 2.
- [x] Step 4: Find the newest session log by the newest-wins rule in `skills/plab-continue-session/references/log-discovery.md`: the flat `_local/_session-logs/` store and its `YYYY-MM/` folders, plus the two legacy paths, sorted by filename. Mirror the rule; do not edit that file. Extract each Waiting on You bullet verbatim with its `(blocked since YYYY-MM-DD)` date. A store that does not exist contributes nothing and is not broken.
- [x] Step 5: Compute `age_days` against today's date: the row's `Updated`, else the document's `created`, else the bullet's `blocked since`; otherwise the literal `"unknown"`. Emit `home`, `id`, `title`, `status`, `age_days`, plus `source_kind` (`decisions-section` or `waiting-on`) and, for a decisions item, the home document's own frontmatter `status` so the agent can spot moot items.
- [x] Step 6: Write `test-gather-backlog.py` on `test-organize-logs.py`'s pattern: a `check()` helper and fixture repositories built in a temporary directory with `git init`. Cases: the type filter (an untyped brief contributes nothing), all eight statuses, a numbered heading variant, an unparseable table (exit 2 naming the file), newest-wins across the flat store and a month folder, the age order with each fallback, and a no-write case hashing the fixture before and after.

**Verification:**

`python skills/plab-resolve-open-items/scripts/test-gather-backlog.py` exits 0, 18/18 checks passed, `ALL PASS`.

The status-filter canary: with `if status not in PENDING_STATUSES:` temporarily replaced by `if False:  # CANARY`, the same command drops to 17/18, failing exactly `status filter keeps exactly Open, Needs info and Proposed  |  ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8']` (every status, not only the three pending ones, came through). The filter was restored and the suite returned to 18/18.

`python skills/plab-resolve-open-items/scripts/gather-backlog.py --repo . --json` against this repository itself: 31 items, all `source_kind: "decisions-section"` (this worktree has no `_local/_session-logs/`, so the Waiting on You source legitimately contributes nothing here), spanning 16 of this repository's own specs, implementation plans and release plans, including WD-02's own six `Open` decisions.

---

## Phase 2: The backlog reference

**Goal:** One reference file holds everything the agent needs to triage, present and record a sweep, so `SKILL.md` only points at it.

**Files:** Create `skills/plab-resolve-open-items/references/backlog.md`.

**Fulfills:** AC-5, AC-6, AC-7, AC-9, AC-10

**Steps:**
- [x] Step 1: State the sources and the status filter in two sentences, naming the script as the only way to gather.
- [x] Step 2: Define the tiers exactly as spec Requirement 6 does, with one checkable example of moot evidence for each `source_kind`: a home spec whose own status is `fulfilled` or `superseded`, and a Waiting on You bullet whose action the repository shows done, such as a merged pull request.
- [x] Step 3: State the order and cap: ready, moot, judgment, oldest first within a tier, at most ten presented, and the report states how many remain.
- [x] Step 4: State how a moot item is presented: a D item whose options are A, cancel it (recommended, with the evidence as reason), and B, keep it open. Accepting A writes `Canceled` on the home's three surfaces with the evidence as Reasoning.
- [x] Step 5: State that a Waiting on You item is a T item, or a D item when the bullet names options, with the log as its source; its answer goes in the walk record only, and the log is never written.
- [x] Step 6: Give the backlog file's path pattern `_local/decisions/YYYY-MM-DD_HH-MM_backlog.md` and its format: a header line with the date, the repository and the item count, then one table per tier with columns `Item`, `Home`, `Id`, `Status`, `Age (days)` and, under moot, `Evidence`. State that the file is never edited after the sweep.
- [x] Step 7: State the empty case: one sentence, and no file.

**Verification:** `python scripts/check-dashes.py` exits 0: `CLEAN: canary proved, no banned characters found in tracked files.` A read of `references/backlog.md` against spec Requirements 6 to 12 finds each one stated once: the tiers (R6), the backlog file (R7), the cap and order (R8), the moot presentation (R9), write-back reuse (R10), the Waiting on You presentation (R11), and the empty case (R12).

---

## Phase 3: Wire the sweep into SKILL.md

**Goal:** `--backlog` runs the script, triages with `references/backlog.md`, writes the backlog file, and then continues through the existing steps 2 to 7 unchanged.

**Files:** Modify `skills/plab-resolve-open-items/SKILL.md`, `skills/plab-resolve-open-items/references/walk-record.md`, and `skills/plab-resolve-open-items/scripts/walk-check.py` only if the record check must accept a new header line.

**Fulfills:** AC-8, AC-11

**Steps:**
- [x] Step 1: In the description, replace `Not yet built: the --backlog sweep across every spec, plan and log.` with a clause of at most 120 more characters naming `--backlog` as the repository-wide sweep. Measure both descriptions' lengths and quote them.
- [x] Step 2: Change `argument-hint` from `"[<document>]"` to `"[--backlog | <document>]"`.
- [x] Step 3: In Workflow step 1, add a `--backlog` branch: run `python <this skill's base directory>/scripts/gather-backlog.py --repo <project root> --json`; on exit 2, report the named source as broken and stop; otherwise triage with `references/backlog.md`, write the backlog file, and select the walk's items. Replace the empty-walk sentence's "note that the `--backlog` sweep is not built" with an offer to run `--backlog`.
- [x] Step 4: Remove the `--backlog` bullet from "Not in this version". Add `references/backlog.md` to the References table.
- [x] Step 5: In `references/walk-record.md`, add an optional `backlog-file` frontmatter field naming the backlog file a walk came from. Proved, rather than assumed, that `walk-check.py record` does not reject it: its frontmatter parser reads a flat `key: value` dict and `check_frontmatter` only inspects the keys its own rules name, so an extra key passes unchanged. A record carrying `backlog-file: ...` was run through the checker directly and returned `CLEAN`, so `scripts/walk-check.py` needed no change, matching this step's own conditional.
- [x] **Plan addition, beyond this phase's file list:** `references/walk-format.md` lines naming `--backlog` as "not built" (loaded at the same Workflow step 1 this phase rewrites) were also updated, so the reference a session loads does not contradict the description and argument hint this phase just changed.

**Verification:** `python skills/plab-resolve-open-items/scripts/walk-check.py record skills/plab-resolve-open-items/examples/sample-walk/walk-record.md` exits 0: `CLEAN: canary proved, skills/plab-resolve-open-items/examples/sample-walk/walk-record.md satisfies every record rule.` A diff of `SKILL.md` (`git diff --stat`: 1 file changed, 7 insertions, 5 deletions) shows only the description clause, the argument hint, Workflow step 1, the "Not in this version" list and the References table changed.

---

## Phase 4: Prove it by behaviour

**Goal:** A real headless session runs a backlog walk end to end on a fixture repository, so AC-13 rests on a transcript rather than on a reading of the instructions.

**Files:** None in the repository. The fixture and the transcript live in a temporary directory, and the results are reported in the pull request.

**Fulfills:** AC-13, with behaviour evidence for AC-4 to AC-10

**Steps:**
- [x] Step 1: Build a fixture repository with `git init`: five typed specs and plans holding at least twelve pending items across all tiers, including one whose home spec is `fulfilled` (a moot candidate), an untyped brief with a decisions section, a copy of `references/decisions-section.md` at its root, and `_local/_session-logs/` holding two logs, the newer with two Waiting on You bullets. Built at `E:\tmp\wd02-fixture`: five typed documents (F1, F2 `status: fulfilled`, F3 with a legacy three-column table, `plan_01`, F5 with a numbered `&` heading) holding 12 decisions-section items plus 2 Waiting on You bullets in the newest log, 14 total, spanning all three tiers. `docs/ideas/brief.md` is the untyped decoy, and `decisions-section.md` sits at the fixture root.
- [x] Step 2: Load the branch's skill into the fixture through a `.claude/skills/plab-resolve-open-items` junction to a `git archive` copy of the branch's skill folder. Run `claude -p "/plab-resolve-open-items --backlog"` with `--settings` setting `autoMemoryEnabled` to false and the installed `prisant-utilities@prisant-labs` plugin disabled, `--output-format stream-json --verbose`, and a turn cap. **One addition beyond this step's wording:** the plugin-root `references/decisions-section.md` was archived at two locations, `E:\tmp\wd02-skill\references\` (the archive's own two-up path) and `E:\tmp\wd02-fixture\.claude\references\` (the junction's apparent two-up path), because the transcript showed the agent resolved `SKILL.md`'s "two folders above the skill's base directory" against the junction's own apparent path, not the archive's real target; only the second copy was ever read.
- [x] Step 3: Hash the session logs. Answer with `claude -p --resume <session-id>` and a scripted line that accepts one ready item, cancels the moot item, defers a T item from the log with `later`, and skips the rest. First pass: the two Waiting on You bullets' ages (40 and 35 days) ranked below the cap, so neither was presented and there was no T item to answer against. The newer bullet's `blocked since` date was moved from 2026-09-05 to 2026-07-01 (a fixture-only edit, not a spec or plan change) so it would outrank enough judgment items to be shown, and the walk was rerun from a clean session. Answered `D1 A, D5 A, T1 later`.
- [x] Step 4: Checked below. AC-13 is ticked.

**Verification (quoted from the actual runs; `--repo`, fixture paths and session ids are under `E:\tmp\`, outside this repository):**

Gathering, standalone: `python skills/plab-resolve-open-items/scripts/gather-backlog.py --repo /e/tmp/wd02-fixture --json --today 2026-10-15` returned 14 items (12 `decisions-section`, 2 `waiting-on`), none from `docs/ideas/brief.md`.

Headless walk 1 (session `d659c1fc-2478-42b2-8388-46bf7efa5ed0`), result: `**Backlog: 14 open items, 10 shown.**` ... `4 items are ready, 2 are moot, and 8 need judgment.` The transcript's tool calls read `.claude/skills/plab-resolve-open-items/...` and ran `python .claude/skills/plab-resolve-open-items/scripts/gather-backlog.py --repo /e/tmp/wd02-fixture --json`, confirming the junction copy loaded.

Headless walk 2, after moving the T-candidate's date (session `6acbd56f-e0aa-42c1-8e37-64bbe165613e`): same 14/10 split, now presenting `T1: rotate the fixture's deploy token` as a true T item. Backlog file written: `_local/decisions/2026-10-15_22-51_backlog.md`.

Resume with `D1 A, D5 A, T1 later`: result quotes `Both write-backs passed the self-check with exit 0` and names the handle `fixture`, taken from the release plan's own filled maintainer block.

Independent checks, run from this repository against the fixture's own files, not taken from the agent's self-report:

```
python skills/plab-resolve-open-items/scripts/walk-check.py record /e/tmp/wd02-fixture/_local/decisions/2026-10-15_walk_backlog.md
```
`CLEAN: canary proved, ... satisfies every record rule.` (exit 0). The frontmatter carries `backlog-file: _local/decisions/2026-10-15_22-51_backlog.md`.

```
python skills/plab-resolve-open-items/scripts/walk-check.py writeback <before-copy> <after>
```
for each of F1, F2, `plan_01` and F5: all four `CLEAN` (exit 0). F3 (the legacy three-column spec) returns `BROKEN: ... summary table lacks the column(s) Title, Resolution, Updated` (exit 2), which is expected: F3 is not in the decisions format, so `walk-check.py` cannot verify a write-back to it, and none was attempted. A direct `diff` of F3's before and after copies is empty: F3 is byte-identical.

Session log hashes, before and after both headless walks: `999376ba...` (newer log) and `9feda5ec...` (older log), identical in both readings. The older log and the brief's decoy item never appear in either `_local/decisions/` file (`grep` for the decoy's title returns no match there).

One backlog file exists (`2026-10-15_22-51_backlog.md`), lists all 14 items under exactly one of its three tier tables, in strict oldest-first order within each tier regardless of series (confirmed: the Judgment table reads 158, 158, 106, 56, 44, 35, 35, 15 days), and is unchanged after the walk answered three of its items; the home documents and the walk record carry the answers instead, per AC-6.

Second, empty-fixture session at `E:\tmp\wd02-fixture-empty` (session `7511a46c-2421-4501-b01b-2b055b982320`): result is `The backlog sweep found no pending items, so I wrote no backlog file and no walk record.` `find /e/tmp/wd02-fixture-empty/_local -type f` shows only the fixture's own pre-existing session log; no `_local/decisions/` directory was created.

---

## Phase 5: HISTORY and usage README

**Goal:** The new mode is recorded where a reader looks for it. Version numbers are set by the closing release pull request, not here.

**Files:** Modify `skills/plab-resolve-open-items/HISTORY.md` and `docs/skills/plab-resolve-open-items/README.md` (body only, not its `**Version:**` line).

**Fulfills:** N/A (release hygiene)

**Steps:**
- [x] Step 1: Add a 1.1.0 row to `HISTORY.md` with release column `unreleased`, naming the backlog sweep and its six working-default decisions.
- [x] Step 2: In the usage README, replace any statement that `--backlog` is unbuilt with a short section on running it and what it writes.

**Verification:** `python scripts/version-parity-check.py` exits 0: `CLEAN: canary proved, 10 skill(s) checked across 4 claim locations, every claimed version matches what the repository declares.` Unaffected, because `metadata.version` and the README's `**Version:**` line were deliberately left at 1.0.1, per this effort's hard rule that the closing release pull request owns every version claim.

---

## CI and Documentation Coverage

### CI

No CI change. `test-gather-backlog.py` joins `test-organize-logs.py` and the wrap and continue test scripts as a committed script the maintainer runs, because no workflow runs a skill's test script today and adding the first one changes what a red check means for every skill. `walk-check.py`, which CI already runs on the committed sample, keeps running unchanged; if Phase 3 teaches it a new header line, the sample check exercises that path.

### Documentation

`skills/plab-resolve-open-items/SKILL.md` and `references/walk-record.md` (Phase 3), the new `references/backlog.md` (Phase 2), `HISTORY.md` and the usage README body (Phase 5). The closing release pull request owns `CHANGELOG.md`, `library.json`, the root `README.md` skills table, `docs/status-skills.md`, the usage README's `**Version:**` line, the skill's `metadata.version`, and the generated manifests. `AGENTS.md`'s `plab-resolve-open-items` section says the `--backlog` sweep is not built; the closing pull request changes that sentence.

## Rollback

Delete `scripts/gather-backlog.py`, `scripts/test-gather-backlog.py` and `references/backlog.md`. In `SKILL.md`, restore the description's final sentence to `Not yet built: the --backlog sweep across every spec, plan and log.`, the argument hint to `"[<document>]"`, Workflow step 1's empty-walk sentence, and the "Not in this version" bullet, and remove the References row. Revert the `Backlog file:` line in `references/walk-record.md` and any matching `walk-check.py` change together, because the checker and the format must agree. No schema or data migration exists: backlog files and walk records already written stay in gitignored `_local/decisions/` and are harmless.
