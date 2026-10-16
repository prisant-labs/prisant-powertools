---
id: W-02
title: "Implementation plan: Derive session-log facts from git instead of model recall"
type: implementation-plan
status: in-progress
created: 2026-08-23
updated: 2026-10-15
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 7
---

# Implementation Plan: Derive session-log facts from git instead of model recall

> **For agentic workers:** steps use checkbox syntax for tracking. Execute phases in order.

**Goal:** Replace model-recalled session-log facts with values derived from git and the environment, via a new `derive-log-facts.py` script that `plab-wrap-session`'s `SKILL.md` is rewired to call. The same single invocation also returns everything else the wrap gathers before writing, so a wrap reaches its written log in about half the steps it takes today.

**Revised 2026-10-05** to match the spec's 2026-10-04 revision. Phase 3 (evidence and hygiene detection in the same call) and Phase 7 (the re-measurement that proves AC-11) are new; the old Phases 3 to 5 became Phases 4 to 6. The wrap version moved from 1.7.0 to 1.8.0, because 1.7.0 shipped in v0.5.4 while this plan waited.

**Built 2026-10-15** under the maintainer's go-ahead. Phases P1 to P6 below are complete; AC-11 (P7, the re-measurement over at least ten completed wraps) needs calendar time this build does not have and stays NOT PROVEN. Status moves to `in-progress` rather than `complete` for exactly that reason. `metadata.version` was deliberately not bumped in `SKILL.md`: this release's shared bookkeeping (version bumps, CHANGELOG, manifests) is a separate closing pull request's job, not this plan's.

**Architecture:** `derive-log-facts.py` is a single stdlib-only Python script at `skills/plab-wrap-session/scripts/derive-log-facts.py`, invoked twice per wrap. The first call, before any prose is drafted, returns the environment fields, files-changed, commit-range and tags, the Evidence Gathering inputs, and the hygiene sweep's detection results. The second call, after the Decisions Made section exists, returns `decisions-count` (see spec Open Questions item D2). The script writes nothing unless asked to fetch, and its fetch never prunes (spec D4). `SKILL.md`'s Evidence Gathering, Pre-Wrap Hygiene Sweep and Frontmatter sections are rewritten to call it in place of manual derivation. Step-level detail stays lighter than the implementation-plan template asks for, because sibling efforts will move `SKILL.md`'s line numbers before this one executes; steps describe what changes, and any step that cites a line number must be re-verified first.

**Spec:** `spec.md`

**Target versions:** `plab-wrap-session` 1.8.0; the release that ships it (versions are assigned only at ship time, per the maintainer's decision register, decision 21). `plab-continue-session`'s move to 1.6.0 is unaffected by this plan; it belongs to D-10 (log format contract).

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) anywhere in any file this plan touches. Use " - " or restructure.
- State a contract once, in one named file. This plan deliberately does not touch the reference docs that restate the frontmatter or template contract (`references/frontmatter-schema.md`, `references/session-log-template.md`, anything under `skills/plab-continue-session/`, `docs/skills/plab-wrap-session/README.md`); that consolidation is D-10's job, sequenced after this one. The one exception is `references/hygiene-sweep.md`, which catalogues the sweep's commands rather than the log's format (spec In Scope item 6).
- This plugin is built for its one maintainer. No configurability for hypothetical third-party users.
- Token economy is a first-class objective. Do not grow `SKILL.md`'s description.
- Archive, never delete; dry-run by default; per-action confirmation for anything that touches the world. The script writes nothing by default, and its one write, an explicit fetch, is confined to `.git` and never prunes. Nothing in this plan may introduce a write path that skips confirmation.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Build the core derivation script (environment fields, files-changed, commit-range/tags, path resolution) | AC-1, AC-2, AC-3, AC-7 | agent | Done 2026-10-15 |
| P2 | Add decisions-count and verification-table derivation with graceful degradation | AC-4, AC-5 | agent | Done 2026-10-15 |
| P3 | Return the Evidence Gathering inputs and the hygiene sweep's detection results from the same call, with a fetch that never prunes | AC-10, AC-8 (fetch half) | agent | Done 2026-10-15 |
| P4 | Lock the write contract and `--json`, and add the stdlib-only test script | AC-8 | agent | Done 2026-10-15 |
| P5 | Wire the script into `SKILL.md` and `hygiene-sweep.md`; confirm the four judgment sections stay untouched | AC-6, AC-9 | agent | Done 2026-10-15 |
| P6 | Version bump and release bookkeeping (HISTORY, CHANGELOG, README, manifests) | N/A (release hygiene) | agent | Partial 2026-10-15: HISTORY.md entry added; version bump and CHANGELOG/README/manifest bookkeeping deferred to this release's own closing pull request (out of this build's scope) |
| P7 | Re-measure completed wraps against the 2026-10-01 baseline | AC-11 | maintainer, then agent | Not started; needs calendar time, see rewritten phase below |

---

## Phase 1: Build the core derivation script

**Goal:** Emit `machine`, `repo`, `branch`, `date`, `files-changed`, commit-range, and latest-tag as JSON or Markdown, resolving paths per the `organize-logs.py` precedent.

**Files:** Create `skills/plab-wrap-session/scripts/derive-log-facts.py`.

**Fulfills:** AC-1, AC-2, AC-3, AC-7

**Steps:**
- [x] Step 1: Scaffold the script on `organize-logs.py`'s shape: `argparse`, `from __future__ import annotations`, a `--json` flag, stdlib-only imports (`subprocess` for git, `socket` for hostname, `datetime` for the clock).
- [x] Step 2: Implement environment-field derivation: `machine` via `socket.gethostname()`, `repo` via `git remote -v` falling back to the directory name, `branch` via `git branch --show-current`, `date` via the system clock.
- [x] Step 3: Implement `files-changed` via `git diff --name-only <base>` (base vs. the current working tree, not `<base>..HEAD`; see spec Open Questions item D6, decided during this build toward AC-2's literal wording so uncommitted tracked edits are included), with a `--base` argument defaulting per item D7, revised 2026-10-15 after the orchestrator's review found Option B empty for a pushed session: session-start (the commit before the transcript's first timestamp) first, then upstream, then latest tag, then none, grouped consistently with the "grouped by purpose if many" guidance in `SKILL.md`'s Files Changed section (line 161, re-verified 2026-10-15; this was line 155 as of the 2026-10-04 revision, before this effort's own edits to `SKILL.md`).
- [x] Step 4: Implement commit-range (`git log`) and latest-tag (`git describe`) derivation under names resolved per spec Open Questions item D1, confirmed not to collide with the existing `commit-sha` or `tags` fields.
- [x] Step 5: Resolve the script's own path relative to `Path(__file__).resolve().parent`, matching `organize-logs.py`; accept the project root to inspect as a separate, explicit argument, never assumed to share a root with the script's own location.

**Verification:** `python skills/plab-wrap-session/scripts/derive-log-facts.py --json` run from inside this repo prints a JSON object whose `machine`, `repo`, and `branch` values match `hostname`, this repo's remote, and `git branch --show-current` run directly; `files-changed` matches `git diff --name-only` for the same base ref. **Done 2026-10-15:** confirmed by `test-derive-log-facts.py`'s basic-derivation case and by a manual run in this worktree.

---

## Phase 2: decisions-count and verification-table derivation

**Goal:** Add the decisions-count mechanism (a mechanical count, computed after prose exists) and verification-content derivation with graceful degradation when no record is available.

**Files:** Modify `skills/plab-wrap-session/scripts/derive-log-facts.py`.

**Fulfills:** AC-4, AC-5

**Steps:**
- [x] Step 1: Implement a mode that accepts a drafted log body (path or stdin) and returns a mechanical count of `## Decisions Made` entries, resolving spec item D2's chosen mechanism: a second, small invocation, `--count-decisions <path>`, run after the Decisions Made section is drafted.
- [x] Step 2: Implement verification-content derivation that reads a transcript when `CLAUDE_CODE_SESSION_ID` resolves to a matching `~/.claude/projects/*/<id>.jsonl`, streamed line by line; return an explicit "no record available" signal otherwise, never a fabricated entry.
- [x] Step 3: Confirm the "no record available" path is what fires when capture-lite is the only thing present, since capture-lite cannot describe the current, still-open session (D-4, the maintainer's private defect record cited by spec D3).

**Verification:** Given a fixture log body with three `## Decisions Made` bullets, the script reports `3`. Given a fixture run with no transcript and no capture-lite record, the script's verification output is the explicit "no record" signal, not a silent empty success. **Done 2026-10-15**, plus a live check: `--count-decisions` against the maintainer's real newest log returned `11`, matching that log's own `decisions-count: 11` frontmatter exactly.

---

## Phase 3: Evidence and hygiene detection in the same call

**Goal:** One invocation also returns the Evidence Gathering inputs and the hygiene sweep's detection results, so the wrapping agent gathers nothing else by hand. Remote facts are fresh only when the agent asks for a fetch, and the fetch never prunes.

**Files:** Modify `skills/plab-wrap-session/scripts/derive-log-facts.py`.

**Fulfills:** AC-10; the fetch half of AC-8.

**Steps:**
- [x] Step 1: Add a `--fetch` option that runs `git fetch --no-prune origin --tags` and no other write. Pass `--no-prune` explicitly, because a plain fetch prunes whenever `fetch.prune` is set in git configuration, and never pass `--prune`: a by-hand `git fetch --prune` deleted a remote-tracking ref without confirmation on 2026-09-25 (spec D4). Without the option, run no fetch, and state in the output that remote facts are as of the last fetch.
- [x] Step 2: Port the sweep's detection commands from `references/hygiene-sweep.md` rather than re-inventing them (spec NFR "Consistency"). Cover Check 1's ahead/behind, unpushed commits, remote branches and tags; Check 2's dirty and untracked files, stashes and worktrees; Check 3's CHANGELOG content above the last release heading and its version fields against the latest tag; Check 4's per-skill version-drift recipe; and Check 5's `organize-logs.py --json` dry run. Emit findings only. The script never emits a proposal and never acts on a finding.
- [x] Step 3: Find the newest session log by the newest-wins rule in `skills/plab-continue-session/references/log-discovery.md`: the flat store, its `YYYY-MM/` folders, and the two legacy paths, sorted by filename rather than by path. Mirror the rule in the script; do not edit that file (spec Non-Goal 3).
- [x] Step 4: From that log, emit its filename and its Waiting on You bullets verbatim, each with its `(blocked since YYYY-MM-DD)` date unchanged.
- [x] Step 5: From `_local/_session-logs/_capture/*.jsonl`, emit the records with a non-null `session_id` and a `ts` after the newest log's filename timestamp, with their count and earliest-to-latest `head`. The filename carries local time and `ts` carries UTC, so convert before comparing; the cutoff prefers the log's own frontmatter `date:` field (an explicit offset) and only falls back to the filename when that field is absent.
- [x] Step 6: List files under gitignored paths modified since the newest log's timestamp, as the starting inventory for Evidence Gathering step 5 (spec Requirement 10). `git ls-files --others --ignored --exclude-standard` names the candidates, and their modification times filter them. Cap the list and report the overflow count, because one ignored dependency folder can hold thousands of files.

**Verification:** In this repository, run `python skills/plab-wrap-session/scripts/derive-log-facts.py --base origin/main --json`. Its Waiting on You list must equal the newest log's section line for line. Its capture-record count must equal a manual filter of the capture files. Each hygiene field must match the corresponding command from `hygiene-sweep.md`, run by hand. The repository's `.git` directory must be unchanged by the run, because no `--fetch` was passed.

**Done 2026-10-15, live run against the maintainer's real checkout** (`E:\Projects\prisant-labs\prisant-utilities`, read-only, no `--fetch`): the script's Waiting on You list matched that checkout's newest log (`2026-10-13_13-12_claude_wd01-fix-phase6-v071-and-toolchain-review.md`) 23 of 23 bullets, byte-for-byte once line endings are normalized. Its capture-record result (`none-qualifying`) matched a hand-written filter of the same `.jsonl` files against the log's own frontmatter `date:` cutoff. `tags-tail`, `remote-branches`, `worktrees`, and `stashes` were cross-checked by running the equivalent git commands from this worktree, since those are repository-wide facts shared across every worktree of the same checkout, and matched. The CHANGELOG and `library.json`-vs-tag facts were cross-checked by reading those two files directly and matched (`has-unreleased-heading: false`, consistent with the maintainer's own note that `[Unreleased]` needs re-adding; version `0.7.1` equals tag `v0.7.1`). Branch-specific facts for the checkout's own checked-out branch (ahead/behind, dirty working tree) could not be independently cross-checked from this worktree, because this worktree is on a different branch; this is a stated limit, not a verified match. The full, exhaustive gitignored-modified enumeration could likewise not be independently reproduced, because `git ls-files` against that checkout is blocked by this agent's worktree-isolation sandbox; the three files it did report were each confirmed by direct `stat` to have a later mtime than the cutoff.

---

## Phase 4: Write contract, `--json`, and the test script

**Goal:** Lock in that the script writes nothing without `--fetch` and never prunes with it, and add a stdlib-only sibling test script that proves both, with a canary for each.

**Files:** Create `skills/plab-wrap-session/scripts/test-derive-log-facts.py`. No behavior change to `derive-log-facts.py` beyond fixing any write path this phase's audit finds.

**Fulfills:** AC-8

**Steps:**
- [x] Step 1: Audit `derive-log-facts.py` for any filesystem write other than the `--fetch` path; there should be none. Fix if one is found. (None was found; every git call sets `GIT_OPTIONAL_LOCKS=0` so a read never opportunistically touches `.git/index`.)
- [x] Step 2: Scaffold `test-derive-log-facts.py` on `test-organize-logs.py`'s shape: a `check()` helper, throwaway fixtures in a temp directory, no external framework.
- [x] Step 3: Build fixture git repositories (`git init` in a temp dir, a couple of commits, a tag) to exercise files-changed, commit-range, and tag derivation deterministically.
- [x] Step 4: Add cases for the Phase 2 decisions-count and verification-degradation paths.
- [x] Step 5: Add a no-write case. Without `--fetch`, hash every file under the fixture's `.git` directory and working tree before and after a run, and assert the hashes are identical.
- [x] Step 6: Add a no-prune case. Make a fixture clone, set `fetch.prune=true` in its configuration, delete a branch on its remote, then run with `--fetch`, and assert the clone's stale remote-tracking ref still exists. Canary: temporarily remove `--no-prune` from the script's fetch call, and confirm this case fails.
- [x] Step 7: Add log-store cases. Place logs in the flat store, in a `YYYY-MM/` folder and in a legacy path, and assert the newest filename wins regardless of folder. Assert that Waiting on You extraction preserves each `(blocked since ...)` date exactly.
- [x] Step 8: Add capture-record cases, including one record within the local-time offset of the cutoff, which a comparison that skips the timezone conversion would misclassify.

**Verification:** `python skills/plab-wrap-session/scripts/test-derive-log-facts.py` exits 0 and prints an all-pass summary, matching `test-organize-logs.py`'s own reporting style. With `--no-prune` temporarily removed from the fetch call, the same command exits non-zero, naming the no-prune case.

**Done 2026-10-15:** 37/37 checks pass. The canary was run by temporarily removing `--no-prune` from the fetch call, confirming the no-prune case failed and named itself, then restoring the flag and re-confirming 37/37.

---

## Phase 5: Wire the script into SKILL.md and hygiene-sweep.md

**Goal:** Evidence Gathering, the Pre-Wrap Hygiene Sweep and the Frontmatter block call the script instead of running their commands one at a time; the four judgment sections are untouched.

**Files:** Modify `skills/plab-wrap-session/SKILL.md` and `skills/plab-wrap-session/references/hygiene-sweep.md`.

**Fulfills:** AC-6, AC-9

**Steps:**
- [x] Step 1: In Evidence Gathering, replace the commands of steps 1, 7 and 9, and the gathering half of step 8, with one instruction: run the script once, with `--fetch` in deep and final modes, and use its output. Step 5's inventory starts from the script's list. The judgment in steps 2 to 4, 6 and 8 stays with the agent.
- [x] Step 2: In the Pre-Wrap Hygiene Sweep, point each check's detection at the script's output. The project's own validation scripts, Check 3's third bullet, stay an agent step (spec D5). The resolution protocol, propose and then confirm each action, is unchanged.
- [x] Step 3: In `hygiene-sweep.md`, replace each check's command block with a pointer to the output field that carries its result. Keep every "Flag:" paragraph and the Resolution protocol section word for word.
- [x] Step 4: Replace the "### Frontmatter" block's per-field manual guidance for derived fields with a short pointer to the script; leave the agent-authored fields (`session-type`, `model`, `model-settings`, `agent`, `status`, `skills-used`, `resumed-from`) as agent-filled, unchanged.
- [x] Step 5: Re-read the Body Sections instructions for Summary, Decisions Made, Waiting on You, and Continuation Prompt and confirm none of them were touched by this phase.
- [ ] Step 6: **Deferred, not skipped.** `metadata.version` stays at `1.7.0` in this build. This release's shared version bookkeeping (every skill's `metadata.version`, CHANGELOG, manifests) is owned by a separate closing pull request for the release, not by this effort's own branch; bumping it here would conflict with that PR. `HISTORY.md` still carries the 1.8.0 entry (Phase 6) so the content is documented even though the frontmatter field has not moved yet.

**Verification:** Diff `SKILL.md` before and after this phase; the only sections that changed are Evidence Gathering, the Pre-Wrap Hygiene Sweep, and the Frontmatter block (not the version frontmatter, per the Step 6 deferral above). Diff `hygiene-sweep.md`; every "Flag:" paragraph and the Resolution protocol section are unchanged. A manual read of Summary, Decisions Made, Waiting on You, and Continuation Prompt shows text unchanged from before this effort.

**Done 2026-10-15:** `git diff -U0 origin/main -- skills/plab-wrap-session/SKILL.md | grep '^@@'` shows exactly two hunks, at the Evidence Gathering/Hygiene Sweep block and the Frontmatter block; a content diff confirms no Flag paragraph or the Resolution protocol section in `hygiene-sweep.md` changed.

---

## Phase 6: Version bump and release bookkeeping

**Goal:** Update HISTORY, CHANGELOG, README, and manifests for wrap's move to 1.8.0.

**Files:** Modify `skills/plab-wrap-session/HISTORY.md`, `CHANGELOG.md`, `README.md`, `library.json`; regenerate `manifest.generated.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`.

**Fulfills:** N/A - release hygiene, not a functional AC.

**Steps:**
- [x] Step 1: Add a `skills/plab-wrap-session/HISTORY.md` entry for 1.8.0 describing the derived-facts split and the one-step evidence gathering, following the existing entry style (see the 1.7.0 entry).
- [x] Step 2: Correct the 1.7.0 row's release column, which still reads `unreleased`. Version 1.7.0 shipped in v0.5.4: `git tag --contains c75ca7a`, the commit that added the row, lists v0.5.4 first. **Verified 2026-10-15, already correct:** the row already reads `v0.5.4`, confirmed against `git tag --contains c75ca7a` (first tag: v0.5.4); no edit was needed, and none was made.
- [ ] Step 3: **Deferred to this release's closing pull request**, not built here: a `CHANGELOG.md` `[Unreleased]` bullet for wrap 1.8.0 is out of this branch's scope per the orchestrating task's hard rules.
- [ ] Step 4: **Deferred to this release's closing pull request**, not built here: wrap's version cell in root `README.md`'s skill table and wrap's `version` field in `library.json` are out of this branch's scope.
- [ ] Step 5: **Deferred to this release's closing pull request**, not built here: the manifest regeneration via `node <agent-skills-toolkit>/scripts/generators/gen-manifest.mjs . --write --target=all` (per `AGENTS.md:137`, re-verified 2026-10-15; this was line 117 as of the 2026-10-04 revision) touches `manifest.generated.json` and both `plugin.json` files, which this branch does not edit.

**Verification:** `git diff library.json manifest.generated.json .claude-plugin/plugin.json .codex-plugin/plugin.json` shows only wrap's version and description fields changed, and the generated files match what the generator produces rather than hand-typed edits. `python scripts/version-parity-check.py` exits 0.

**2026-10-15:** only Step 1 and the verification half of Step 2 were built, per the deferrals above. `python scripts/version-parity-check.py` was still run as one of this branch's own pre-PR gates (see the report) and passed, since this branch changes no version field at all.

---

## Phase 7: Re-measure completed wraps

**Goal:** AC-11 is settled by measurement, not assumed. Completed wraps made with the new version are counted and compared with the 2026-10-01 baseline, a median of 12 assistant API calls.

**Files:** None in the repository. The measurement scripts are the maintainer's private ones from 2026-10-01 (spec S9), and the results are kept beside them.

**Fulfills:** AC-11

**This phase needs calendar time this build does not have, and tagging ahead of it is a maintainer ruling, not a rule this plan sets.** The spec's `target-release` is `null` (see frontmatter), so lifecycle invariant 4 of `scripts/doc-lifecycle-check.py` (a spec targeting an already-tagged release must be `fulfilled` or `superseded`, never still `draft` or `committed`) does not apply to this spec at all while that field stays null; nothing in `doc-lifecycle-check.py` forces this phase to finish before any tag. The spec stays `committed` until this measurement settles AC-11 one way or the other. Whether the release that ships Phases P1 to P6 should tag before this phase runs is a decision for the maintainer to make, not one this plan makes on their behalf: precedent exists either way. AU-01 (the `plab-audit` repository-audit skill) and WD-01 (the `plab-resolve-open-items` walk-the-open-items skill) both shipped before their own post-ship trials ran, by maintainer ruling at the time. This plan does not repeat that ruling here; it only notes that it is available.

**Steps:**
- [ ] Step 1: Make the unreleased wrap load in this repository, by the project-level skill link that AU-01 (the `plab-audit` skill) is testing in its own Phase 7. Confirm it by behaviour, not by a cache listing: a wrap's transcript shows a `derive-log-facts.py` call. If the link does not load, record that, and amend the spec's AC-11 rather than treating W-02 as settled with no measurement.
- [ ] Step 2: After at least ten completed wraps on the new version, run the completed-wrap measurement. Restrict the new side to wraps whose window contains a `derive-log-facts.py` call, and the baseline side to wraps before this effort.
- [ ] Step 3: Report the median API calls per completed wrap for both sides, and the median cost per completed wrap at Opus 5.5 list prices for both sides. Extend the private cost script to the completed-wrap subset if it does not already cover it.
- [ ] Step 4: If the new median is above six, AC-11 has failed. Record the result in the spec, leave the spec unfulfilled, and do not tag. Do not lower the threshold to pass.

**Verification:** The measurement report states both medians and both costs, and counts at least ten new-version completed wraps. AC-11's checkbox is ticked only if the new median is six or fewer.

---

## CI and Documentation Coverage

### CI

No CI change, for a stated reason. No step in `gate.yml` runs a skill's test script: it runs the toolkit's standard and the repository's document gates, and `test-organize-logs.py` is not run in CI either. `test-derive-log-facts.py` joins it at the same rung, a committed script the maintainer runs. Moving both into CI would be worth doing, but it changes what a red check means for every skill, so it belongs to its own effort rather than being folded in here.

### Agent-facing documentation

`skills/plab-wrap-session/SKILL.md`: Evidence Gathering, the Pre-Wrap Hygiene Sweep and the Frontmatter block rewritten to call the script (Phase 5); `metadata.version` stays at 1.7.0 in this build, deferred to the release's closing pull request (Phase 5 Step 6). `skills/plab-wrap-session/references/hygiene-sweep.md`: each check's command block replaced by a pointer to the script's output, with its Flag paragraphs and Resolution protocol unchanged (Phase 5). No other file under `skills/plab-wrap-session/references/` changes (D-10's territory), and no change to `AGENTS.md` (no new trigger phrase, no skill renamed, no change to the plugin's skill list).

### Human-facing documentation

`skills/plab-wrap-session/HISTORY.md` (new 1.8.0 entry, and the 1.7.0 row's release column corrected), `CHANGELOG.md` (`[Unreleased]` bullet), root `README.md` (wrap's version cell). `docs/skills/plab-wrap-session/README.md` is explicitly not touched here; its restatement of the frontmatter contract is D-10's territory, and editing it in both plans would create the exact double-ownership the conventions warn against.

---

## Rollback

If `derive-log-facts.py` ships with a defect that produces wrong facts (for example, a wrong branch value, a bad files-changed diff, or a wrong Waiting on You carry-forward), revert `SKILL.md`'s Evidence Gathering, Pre-Wrap Hygiene Sweep and Frontmatter sections, and `references/hygiene-sweep.md`, to their pre-1.8.0 text. Those two files are the only ones that change agent-facing runtime behavior, so reverting them returns the skill to manual derivation immediately. There is no session-log format change to unwind, because the log's own shape does not change, only how its fields get filled in. The script writes nothing except an explicit, non-pruning fetch inside `.git` (AC-8), so rollback carries no data-migration risk; the script can stay in the tree, unused, until the defect is fixed. Revert the two files together: reverting `SKILL.md` alone would leave `hygiene-sweep.md` pointing at output the skill no longer produces.
