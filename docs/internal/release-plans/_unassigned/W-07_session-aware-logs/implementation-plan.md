---
id: W-07
title: "Implementation plan: Session-aware wrap and continue"
type: implementation-plan
status: draft
created: 2026-11-10
updated: 2026-11-10
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 7
---

# Implementation Plan: Session-aware wrap and continue

> **For agentic workers:** steps use checkbox syntax for tracking. Execute phases in order. Every phase that changes code writes its failing test first.

**Goal:** A session log records which session wrote it and when that session started. A wrap carries Waiting on You and Parked items from the log it resumed from, or else from the newest log, as today, and it names every log another session wrote while it ran. Such a parallel log stays visible to continue, and no wrap proposes archiving it. Continue lists every recent session whose handoff no later log has taken up, and asks which to resume when there is more than one. A session in a linked worktree reads and writes the main checkout's log store. When only one session is in play, both skills behave exactly as they do today.

**Architecture:** One new shared module, `lib/session-logs.py`, holds every rule both skills need: where the store is, which logs exist, what their frontmatter says, which logs are concurrent, which log a wrap carries from, and which logs are still candidates. It is stdlib-only, and it reads and never writes. `derive-log-facts.py` (wrap) and a new `list-candidates.py` (continue) load it by file path through `importlib`, the way `check-log.py` already loads `derive-log-facts.py`, because a hyphenated file name cannot be imported by name. Both skills therefore compute the same answer from the same code. The model chooses nothing in this effort: the candidate set, the carry-forward source and the concurrent list all come from scripts, as the spec's determinism requirement says.

**Spec:** `spec.md`. Its D1 to D7 were decided on 2026-11-10, all on their recommended options. D7 (which log a wrap carries waiting items from) chose Option C: the wrap carries from the resumed-from log or else the newest log overall, as today, and being concurrent decides only whether a carry consumes a log and whether the archive may target it.

**Target versions:** `plab-wrap-session` 1.9.1 to 1.10.0, and `plab-continue-session` 1.6.2 to 1.7.0. Both are minor bumps, because both skills gain behavior and the log gains optional fields. The plugin's release version is assigned at ship time.

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) in any file this plan touches. `scripts/check-dashes.py` reads tracked files only, so scan new files directly before they are committed.
- Do not hard-wrap prose. One paragraph is one line.
- Every rule lives once, in `lib/session-logs.py`. The skills' `SKILL.md` files and references describe what the script reports; they do not restate the rule order in a second form an agent could follow instead.
- No log is ever moved, renamed or rewritten by this effort. Old logs without the new fields keep working with no migration.
- Canaries patch the loaded module inside the test process. They never edit a tracked file, because `test-reconcile.py`'s canary once left `reconcile.py` modified in the working tree.
- Line numbers cited below were read on 2026-11-10. Re-verify each one before editing, because a sibling effort may have moved it.

**Rule names.** The script reports the carry-forward rule under one of three names, used in the spec's AC-4 and examples, and nowhere renamed: `resumed-from`, `newest-overall`, and `none` when the store has no earlier log.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Build the shared session-log module and its test suite | AC-4, AC-7, AC-9 (the rules) | agent | Not started |
| P2 | Report the session fields, the carry-forward source and the concurrent list from `derive-log-facts.py` | AC-2, AC-4, AC-5 (the script), AC-9 (the wrap's reads) | agent | Not started |
| P3 | Add the three fields to the log schema, the template and `check-log.py` | AC-1 (the schema), AC-3 | agent | Not started |
| P4 | Rewire the wrap's Evidence Gathering, write location and Summary to the script's output | AC-5 (the skill), AC-6, AC-9 (the wrap's write) | agent | Not started |
| P5 | Give continue a candidate script and a candidate list | AC-1 (discovery), AC-7, AC-8, AC-9 (continue's reads) | agent | Not started |
| P6 | Documentation, versions and CI | AC-1 (the README) | agent | Not started |
| P7 | Live runs, then the first real parallel case | AC-7 (the real store), AC-9 (a real worktree), AC-10 | agent, then maintainer | Not started |

---

## Phase 1: The shared session-log module

**Goal:** One module answers every question about the log store, and a fixture suite proves each answer, with a canary for each rule that guards against the bug this spec exists to fix.

**Files:**
- Create `lib/session-logs.py`.
- Create `lib/test-session-logs.py`.
- Modify `lib/README.md`: add a row to its Contents table.

**Fulfills:** AC-4, AC-7 and AC-9, at the level of the rules. Phases 2 and 5 prove them through the two skills' own scripts.

**Steps:**
- [ ] Step 1: Write `lib/test-session-logs.py` first, on the shape of `skills/plab-wrap-session/scripts/test-derive-log-facts.py`: a `check()` helper, throwaway fixtures in a temporary directory, real `git init` repositories with a pinned identity, and no external framework. It loads the module with `importlib.util.spec_from_file_location`, as `check-log.py`'s `load_derive_log_facts()` does. Run it and confirm every case fails because the module does not exist.
- [ ] Step 2: `store_root(project_root)`. Run `git rev-parse --git-dir` and `git rev-parse --git-common-dir` in the project root, and resolve both against it. When the two differ, the checkout is a linked worktree, and the main checkout is the common directory's parent, provided the common directory is named `.git`. Return `(store_path, how)`, where `how` is `checkout`, `main-checkout`, or `checkout-fallback: <reason>` for a bare repository, a non-`.git` common directory, or git unavailable. Copy `derive-log-facts.py`'s `GIT_OPTIONAL_LOCKS=0` environment so a read never touches `.git/index`. Test cases: a plain repository, a linked worktree made with `git worktree add`, and a directory that is not a repository.
- [ ] Step 3: `pool_logs(store, project_root)`. Move the pooling rule from `derive-log-facts.py` lines 250 to 273: the store's top level, its `YYYY-MM/` folders, and the two legacy stores, sorted by file name, newest first. The legacy stores stay relative to the project root, because nothing writes to them. `_superseded/` and `_capture/` stay outside the corpus by the existing allowlist. Keep `LOG_NAME_RE` and `MONTH_DIR_RE` identical to the current constants.
- [ ] Step 4: `read_frontmatter(path)`. A flat `key: value` reader of the opening `---` block that returns `branch`, `date`, `session-id`, `session-start`, `resumed-from` and `carried-from`, with surrounding quotes stripped. A missing field is `None`. Never raise on a malformed log; return what was read and a `malformed` flag.
- [ ] Step 5: `wrapped_at_utc(path, fm)`. Prefer the frontmatter `date:` field, which carries an explicit offset, and fall back to the file name's local time only when that field is absent. This is the rule `log_cutoff_utc()` in `derive-log-facts.py` already follows; move it here and leave a delegating wrapper behind.
- [ ] Step 6: `concurrent_logs(logs, session_id, session_start_utc)`. A log is concurrent when its `wrapped_at_utc` is later than this session's start and its `session-id` differs from this session's. A log with no `session-id` counts as another session's. With no `session-start`, return an empty list and the reason `no-session-start`, so a Codex or transcript-less wrap behaves as today (spec D5).
- [ ] Step 7: `carry_forward_source(logs, resumed_from)`. Apply Requirement 4 and return `(log, rule)`: the pooled log whose file name equals `resumed_from`, under `resumed-from`, whatever its age or session; else the newest pooled log, under `newest-overall`, whichever session wrote it; else `(None, "none")`. Concurrency plays no part in this choice (D7). If `resumed_from` names a log the store does not hold, fall through to `newest-overall` and report the miss, rather than failing.
- [ ] Step 8: `candidates(logs, now_utc, window_days=7)`. Apply Requirement 7. A log is in the window when its file-name date is within `window_days` of today, which is the same arithmetic as continue's age warning (Requirement 11). A newer log consumes it in three cases: the newer log names it in `resumed-from`; the newer log names it in `carried-from` and the newer log's `session-start` is later than this log's `wrapped_at_utc`; or the newer log names it in `carried-from` and has no `session-start`, which is today's behavior. A log with no `session-id` is also consumed by any newer pooled log on its branch. A `carried-from` from a session that started before this log was written does not consume it, so a parallel handoff stays a candidate (D7). Collapse logs that share a `session-id` to the newest. Return the candidates newest first, each with its path, branch, `session-start`, wrap time, and Waiting on You count.
- [ ] Step 9: `waiting_count(text)`. Count the items in the log's `## Waiting on You` section. Move `extract_section()` and `extract_waiting_on_you()` from `derive-log-facts.py` into this module, and leave delegating wrappers there, because `check-log.py` calls them through `load_derive_log_facts()`.
- [ ] Step 10: Fixture cases the suite must hold, one per bullet:
  - AC-4's stores: A on `x` then B on `y` gives B under `newest-overall`; with `resumed_from` set to A it gives A under `resumed-from`; an empty store gives `none`.
  - AC-4's concurrent store: log C written before this session started and a newer log D by another session written after it. The source is D under `newest-overall`, and D is listed as concurrent.
  - Example 1: P on `feat/a` and Q on `feat/b`. Q carries from P under `newest-overall`, P is concurrent to Q, and continue's candidates are Q and P, because Q's `carried-from` does not consume P.
  - Example 1b: T then U on `main`, sequential. U carries from T, U started after T was written, so T is consumed and continue's candidates are U alone.
  - Example 3: two wraps sharing a `session-id` collapse to one candidate.
  - AC-7's store: three logs in the window, two from one session on `x` and one from another session on `y`, give exactly two candidates. A log named in a later `resumed-from` is excluded, a log named in the `carried-from` of a session that started after it was written is excluded, and a log in `_superseded/` is excluded.
  - Logs with no session fields at all, the shape of every log written before this spec, give exactly one candidate, the newest.
  - A store with nothing in the window gives zero candidates.
  - `store_root` in a linked worktree returns the main checkout's store with `how` equal to `main-checkout` (AC-9).
- [ ] Step 11: Canaries, each run in-process by replacing one function or one constant on the loaded module and asserting that the named case now fails, then restoring it:
  - Make `carry_forward_source` ignore `resumed_from`: the `resumed-from` case fails (AC-4's canary).
  - Remove `carried-from` from the consumption test: Example 1b's case fails, because T becomes a candidate again (the defect S11 found).
  - Let every `carried-from` consume, ignoring the session-start comparison: Example 1's case fails, because P drops out of the candidates (AC-7's canary, the parallel handoff D7 keeps visible).
  - Make `store_root` return the project root's own store: the worktree case fails.
- [ ] Step 12: Add a row to `lib/README.md`'s Contents table: `session-logs.py`, its purpose in one sentence, its consumers `plab-wrap-session` and `plab-continue-session`, and since `plab-wrap-session` 1.10.0.

**Verification:** `python lib/test-session-logs.py` exits 0 and prints an all-pass summary that names each canary as proved. With any one canary's patch left in place by hand, the suite exits non-zero and names the case that caught it.

---

## Phase 2: The wrap's facts script

**Goal:** One call to `derive-log-facts.py` reports this session's id and start, the store it read, the log it chose to carry from and why, and the logs other sessions wrote while it ran. Waiting on You and Parked come from the chosen log, which differs from today's only when this session resumed from an older log.

**Files:**
- Modify `skills/plab-wrap-session/scripts/derive-log-facts.py`.
- Modify `skills/plab-wrap-session/scripts/test-derive-log-facts.py`.

**Fulfills:** AC-2, AC-4, AC-5 (the script's half) and AC-9 (the wrap's reads).

**Steps:**
- [ ] Step 1: Write the new test cases first and watch them fail:
  - AC-2's fixture: a transcript whose first timestamped line is `2026-11-01T09:00:00.000Z`, run with `--json --session-id <id> --transcript-dir <fixture>`. `session-id` is that id and `session-start` is that timestamp. With no id, both are null and the default digest prints `no-session-id`.
  - AC-2's canary: patch `get_session_start_ts` on the loaded module to read only line 1, against a transcript whose line 1 has no timestamp, and assert the case fails.
  - AC-4 end to end: the C-and-D store from Phase 1, run through the script with `--session-id`, reports `carry-forward: {log: D, rule: newest-overall}` and lists D under `concurrent-logs`. With `--resumed-from C`, it reports C under `resumed-from`. With `--resumed-from` naming a file the store lacks, it reports D under `newest-overall` and names the miss.
  - AC-5: the same run's default digest prints D's file name under a "Concurrent logs" line.
  - AC-9: run from a linked worktree of a fixture repository whose main checkout holds a log. The script reports the main checkout's store, finds that log, and carries from it.
- [ ] Step 2: Add a `--resumed-from <file name>` option. The wrap passes it when this session ran continue, because the script cannot see what continue resumed. The help text names it as the same file name the wrap writes into `resumed-from:`.
- [ ] Step 3: Load `lib/session-logs.py` once at import time, by the path `Path(__file__).resolve().parents[3] / "lib" / "session-logs.py"`. If the file is missing, exit 2 with a message naming the path, because a wrap without the rules would silently fall back to newest-overall.
- [ ] Step 4: In `main()` (lines 979 to 1055), replace `log_path = newest_log(project_root)` with: resolve the store through `store_root`, pool the logs, compute the concurrent list and the carry-forward source, and use that source's path as `log_path`. The cutoff for capture records and gitignored files stays the newest log's time, not the source's, because those two fields ask what happened since anyone last wrapped.
- [ ] Step 5: Add these keys to the output. In `--json`, `session-id` and `session-start` sit at the top level beside `date`, and `store` holds `{path, how}`. Under `evidence-gathering`, `carry-forward` holds `{log, rule}` and `concurrent-logs` holds a list of file names, with a `reason` when the list could not be computed. Keep `newest-log` as it is, because readers may use it, and make `waiting-on-you` and `parked` come from the carry-forward log.
- [ ] Step 6: Point `pool_logs`, `capture_records` (line 366) and `check5_log_store` (line 571) at the resolved store instead of `project_root / "_local" / "_session-logs"`. `newest_log` and `pool_logs` become thin wrappers over the module.
- [ ] Step 7: In `render()` (line 857), add four lines to the digest after `date`: `session-id`, `session-start` (or the reason it is null), `store` with its `how`, and under Evidence Gathering, `carry-forward: <file> (rule <name>)` and `concurrent logs: <names>` or `concurrent logs: none`. Keep the digest under its 20,000-character budget; these lines are short.
- [ ] Step 8: Re-run the whole existing suite. Every case that passed before still passes, which proves Requirement 3's compatibility half for the script.

**Verification:** `python skills/plab-wrap-session/scripts/test-derive-log-facts.py` exits 0 with every old and new case passing, and it names the AC-2 canary as proved. Then run `python skills/plab-wrap-session/scripts/derive-log-facts.py . --json` in this repository and confirm that `session-id` equals `CLAUDE_CODE_SESSION_ID` and that `session-start` equals the first timestamp in this session's transcript.

---

## Phase 3: The log schema and its checker

**Goal:** The three fields have one written definition, and the log checker accepts a log that carries them and a log that does not.

**Files:**
- Modify `skills/plab-wrap-session/references/frontmatter-schema.md`.
- Modify `skills/plab-wrap-session/references/session-log-template.md`.
- Modify `skills/plab-wrap-session/scripts/check-log.py`.
- Modify `skills/plab-wrap-session/scripts/test-check-log.py`.

**Fulfills:** AC-1 for `frontmatter-schema.md`, and AC-3.

**Steps:**
- [ ] Step 1: Write two `test-check-log.py` fixtures first: a log carrying `session-id`, `session-start` and `carried-from`, and a log carrying none of them. Add a third that carries `session-id` with a malformed `session-start`, which must be flagged. Run the suite and confirm the third fails to be flagged.
- [ ] Step 2: In `frontmatter-schema.md`'s Tier 2 table, add three rows after `resumed-from`:
  - `session-id`, String, from `derive-log-facts.py`, from `CLAUDE_CODE_SESSION_ID`, omitted when the script reports null. Example `d7a7141e-930b-4a78-9521-6b03879064a3`.
  - `session-start`, ISO 8601 datetime in UTC, from `derive-log-facts.py`, the first timestamp in this session's transcript, omitted when null. Example `2026-11-06T09:00:00.000Z`.
  - `carried-from`, a file name, from `derive-log-facts.py`'s `carry-forward` log, omitted when the rule is `none`. It is cited by file name only, as the "Citing another session log" section already requires.
- [ ] Step 3: Add a `### carried-from semantics` paragraph after `### resumed-from semantics`. It says that `carried-from` records which log this wrap copied Waiting on You and Parked items from, that continue treats a log named here as consumed only when this session started after that log was written, so a carry from a parallel session leaves its handoff visible, and that the value is copied from the script, never chosen by the agent. Add one sentence distinguishing it from the existing Tier 2 `parent-session` field: `parent-session` is a suggested lineage hint, while `carried-from` records what was actually carried.
- [ ] Step 4: In the Filename Convention table, change the Time row so that it says what the time is.
  - Before: `| Time | \`HH-MM\` (24h) | \`09-36\` |`
  - After: `| Time | \`HH-MM\` (24h), the local time the wrap ran, not the time the session started; see \`session-start\` | \`09-36\` |`
  Add one paragraph under the table: a log written days after its session began still carries the wrap time, so the newest handoff always sorts first; `session-start` records when the session began.
- [ ] Step 5: In `session-log-template.md`, add the three fields to every mode's frontmatter block, each marked "from the script; omit when null".
- [ ] Step 6: In `check-log.py`, add `check_session_fields()`. When `session-start` is present, it must parse as ISO 8601. When `session-id` is present, `session-start` should be too; report its absence as a finding, not a failure, because a transcript can be missing. When `carried-from` is present, it must be a bare file name matching the log name pattern, with no directory. When all three are absent, the check passes. Register it in `run_all_checks()` (line 314).

**Verification:** `python skills/plab-wrap-session/scripts/test-check-log.py` exits 0, with the with-fields and without-fields fixtures both passing and the malformed-start fixture flagged. With `check_session_fields()` patched to always pass, the malformed-start case fails.

---

## Phase 4: The wrap skill

**Goal:** The wrap writes its log to the store the script names, carries items only from the source the script chose, names every concurrent log, and proposes a same-arc archive only against that source.

**Files:** Modify `skills/plab-wrap-session/SKILL.md`.

**Fulfills:** AC-5 (the skill's half), AC-6, and AC-9 (the wrap's write).

**Steps:**
- [ ] Step 1: In Evidence Gathering (line 39), add to the instruction that runs the script: "If this session resumed with `/plab-continue-session`, pass `--resumed-from <that log's file name>`."
- [ ] Step 2: Replace step 6 (line 55).
  - Before: `6. In deep and final modes, judges whether the script's reported newest existing log covers the same arc as this session. If it does, prepares one archive proposal for the hygiene batch (see Wrap Order below): propose moving the older file to \`_local/_session-logs/_superseded/\`, execute only when its number is approved, and record the disposition, declared plus archived-or-not, in the new log's Summary.`
  - After: `6. In deep and final modes, judges whether the script's \`carry-forward\` log covers the same arc as this session. That log is the only one the judgment may consider, and only when it is not under \`concurrent-logs\`: a log another session wrote while this one ran was not superseded by this one. If it covers the same arc, prepares one archive proposal for the hygiene batch (see Wrap Order below): propose moving it to \`_superseded/\` inside the store the script reports, execute only when its number is approved, and record the disposition, declared plus archived-or-not, in the new log's Summary. When the rule is \`none\`, or the log is concurrent, there is nothing to judge.`
- [ ] Step 3: Replace step 7's opening clause (line 56).
  - Before: `7. Carries every still-unresolved Waiting on You item from the script's output forward into this log with its original date, never today's,`
  - After: `7. Carries every still-unresolved Waiting on You item from the script's \`carry-forward\` log forward into this log with its original date, never today's, and copies that log's file name into \`carried-from:\`;`
  Leave the rest of step 7 unchanged, and change its final sentence from "If the script reports no newest log" to "If the script's carry-forward rule is `none`".
- [ ] Step 4: Add step 8: `8. Names every log the script lists under \`concurrent-logs\` in this log's Summary, by file name, as work another session did while this one ran, and proposes nothing about them. When the \`carry-forward\` log is one of them, says that the carried items came from that parallel session.`
- [ ] Step 5: In Session Log Output (line 96), replace the location.
  - Before: `Write to: \`_local/_session-logs/YYYY-MM-DD_HH-MM_<llm>_<brief-kebab-title>.md\``
  - After: `Write to: \`<store>/YYYY-MM-DD_HH-MM_<llm>_<brief-kebab-title>.md\`, where \`<store>\` is the path the script reports. In a normal checkout that is \`_local/_session-logs/\`; in a linked worktree it is the main checkout's \`_local/_session-logs/\`, so every session's log lands in one store that survives the worktree's removal. \`HH-MM\` is the local time of this wrap.`
  Change the example line below it to say it shows a normal checkout.
- [ ] Step 6: In the Frontmatter section (line 145), add `session-id`, `session-start` and `carried-from` to the list of fields copied from the script, beside the other derived fields.
- [ ] Step 7: Check every other mention of `_local/_session-logs/` in `SKILL.md` with `grep -n "_session-logs" skills/plab-wrap-session/SKILL.md`. A mention that tells the agent where to write or archive becomes "the store the script reports". A mention that describes the store's layout stays.
- [ ] Step 8: `organize-logs.py` defaults its store to `_local/_session-logs` relative to the working directory (line 28, `DEFAULT_STORE`), so `--organize` run from a worktree would file the worktree's empty store. `organize-logs.py` already takes the store as an optional positional argument (lines 117 to 120), so no script change is needed. In Organize Mode, tell the agent to pass the store `derive-log-facts.py` reports as that argument.

**Verification:** `git diff -U0 -- skills/plab-wrap-session/SKILL.md | grep '^@@'` shows hunks only in Evidence Gathering, Session Log Output, Frontmatter, and any `_session-logs` mention Step 7 changed. A read of the Hygiene Sweep, Wrap Order and Body Sections shows them unchanged.

---

## Phase 5: Continue's candidate list

**Goal:** Continue builds its candidate set with a script, resumes silently when there is one candidate, asks with a list when there are several, and falls back to today's newest-log rule when there are none.

**Files:**
- Create `skills/plab-continue-session/scripts/list-candidates.py`.
- Create `skills/plab-continue-session/scripts/test-list-candidates.py`.
- Modify `skills/plab-continue-session/SKILL.md`.
- Modify `skills/plab-continue-session/references/log-discovery.md`.
- Modify `skills/plab-continue-session/references/handoff-display.md`.

**Fulfills:** AC-1 for `log-discovery.md`, AC-7, AC-8, and AC-9 (continue's reads).

**Steps:**
- [ ] Step 1: Write `test-list-candidates.py` first, with the AC-7 store, a one-candidate store, an empty-window store, a store of logs with no session fields, and a linked-worktree case. Run it and confirm it fails because the script does not exist.
- [ ] Step 2: Write `list-candidates.py <project_root> [--json]`. It loads `lib/session-logs.py` by path, as Phase 2 does, and exits 2 naming the path if the module is missing. It prints `store` with its `how`; `mode`, which is `one`, `choose` or `fallback`; the candidates, newest first, each with its path, branch, session span, title (the file name's slug) and Waiting on You count; `default`, the one candidate on the current branch when exactly one is; and, in `fallback`, the newest log overall with its age in days. It reads only frontmatter and the Waiting on You section, never a whole log body beyond that, per the spec's cost requirement.
- [ ] Step 3: Rewrite Phase 1 of `SKILL.md` (lines 36 to 48) around the script.
  - Step 1 becomes: run `python <this skill's base directory>/scripts/list-candidates.py <project_root>` and read its output once.
  - Step 2 becomes: in mode `one`, resume from that candidate, exactly as before. In mode `choose`, show the list in the form `references/log-discovery.md` gives and ask which to resume; mark the default when the script names one, and never pick silently. In mode `fallback`, resume from the newest log and show the existing age warning.
  - Steps 3 and 4, the empty check and the legacy migration note, stay.
  - Replace the paragraph "If multiple logs share the same date+time prefix (rare; concurrent sessions by different LLMs), surface all and ask the user which to resume." with: "Two logs of the same minute are two sessions, so the candidate list already shows both."
  - Keep `--log <path>`: it bypasses the script entirely, as it bypasses discovery today.
- [ ] Step 4: In `log-discovery.md`, add a section "Candidate set" after "Selection rule", which says what the script computes in plain words and points to `lib/session-logs.py` as the rule's one home. Do not restate the rule order. Add one paragraph to "Sort rule" saying that the file name's `HH-MM` is the wrap time, not the start, and that `session-start` holds the start (AC-1). Add a section "Worktrees" saying that in a linked worktree the store is the main checkout's. Keep the shell pipelines; mark them as the manual fallback for a harness that cannot run the script.
- [ ] Step 5: Replace the "Tie-breaking" example in `log-discovery.md` with the spec's Example 1 list, because the candidate list replaces the same-minute tie prompt.
- [ ] Step 6: In `handoff-display.md`, add the `choose` display: the list, then "Which session should I resume?", then Phase 4's display for the chosen log only. Continue still resumes from exactly one log per invocation, as its Constraints section requires.
- [ ] Step 7: Confirm that `reconcile.py` needs no change. It takes the chosen log's path, so a log in the main checkout's store from a worktree is read the same way. Its path-existence check resolves cited paths against the project root, which is the worktree; that is correct, because the cited files are the worktree's.

**Verification:** `python skills/plab-continue-session/scripts/test-list-candidates.py` exits 0. The AC-7 store gives `choose` with exactly two candidates, the one-candidate store gives `one`, the empty-window store gives `fallback` with the age, and the worktree case reads the main checkout's store. With the module's `candidates()` patched to return every log in the window unfiltered, the AC-7 case fails.

---

## Phase 6: Documentation, versions and CI

**Goal:** Every human-facing document matches the new behavior, both skills carry their new versions in every place the drift and parity checks read, and CI runs the two new test suites.

**Files:**
- Modify `docs/skills/plab-wrap-session/README.md` and `docs/skills/plab-continue-session/README.md`.
- Modify `skills/plab-wrap-session/SKILL.md` and `skills/plab-continue-session/SKILL.md` (frontmatter `metadata.version` and `updated` only).
- Modify `skills/plab-wrap-session/HISTORY.md` and `skills/plab-continue-session/HISTORY.md`.
- Modify `library.json`, `CHANGELOG.md`, root `README.md`.
- Regenerate `manifest.generated.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`.
- Modify `.github/workflows/gate.yml`.

**Fulfills:** AC-1 for the wrap README. The rest is release hygiene with no criterion of its own.

**Steps:**
- [ ] Step 1: In `docs/skills/plab-wrap-session/README.md`, beside the file-name pattern at lines 25 and 152, add that `HH-MM` is the wrap time and `session-start` holds the start. Describe the three new fields, the carry-forward rule names, the concurrent-logs line and the worktree store in plain words, in the section that already describes carry-forward.
- [ ] Step 2: In `docs/skills/plab-continue-session/README.md`, replace the "rare; concurrent sessions" tie note with the candidate list, show Example 1's list, and say that `--log <path>` still overrides.
- [ ] Step 3: Bump `metadata.version` to `1.10.0` in the wrap's `SKILL.md` and `1.7.0` in continue's, set `updated` to the build date, and match both in `library.json` and in each README's `**Version:**` line. The skill-drift check reads each skill's folder and will not see `lib/`, so these two bumps are named here rather than left to it.
- [ ] Step 4: Add a `HISTORY.md` row and section for each skill, in the existing style: what a user sees change, then why. The wrap's entry names the three fields, the carry-forward rule, the concurrent list and the worktree store. Continue's entry names the candidate list and the worktree store.
- [ ] Step 5: Add a `CHANGELOG.md` bullet under `[Unreleased]` for each skill, led by the user-visible change: parallel sessions no longer copy each other's waiting items, and continue asks which session to resume when two left handoffs.
- [ ] Step 6: Update the two skills' version cells in the root `README.md`, then regenerate the manifests with `node <agent-skills-toolkit>/scripts/generators/gen-manifest.mjs . --write --target=all`.
- [ ] Step 7: In `gate.yml`, in the session-pair block after line 330, add two steps in the existing form: "The shared session-log rules" running `python3 lib/test-session-logs.py`, and "The continue-session candidate list" running `python3 skills/plab-continue-session/scripts/test-list-candidates.py`. Both use `if: always()`. The workflow globs nothing, so a suite without its own `run:` line never runs.

**Verification:** Run `python scripts/version-parity-check.py && python scripts/skill-drift-check.py && python scripts/frontmatter-check.py && python scripts/doc-lifecycle-check.py && python scripts/gen-release-index.py --check && python scripts/codex-invocation-check.py && python scripts/check-dashes.py`, and every one exits 0. `git diff` on the three generated manifests shows only the two skills' version and description fields.

---

## Phase 7: Live runs and the first real parallel case

**Goal:** The rules hold on the maintainer's real store and in a real worktree before merge, and AC-10 is settled by the first real case after release.

**Files:** None in the repository, except the spec's Task Summary and Revisions when each result is recorded.

**Fulfills:** AC-7 (the real store), AC-9 (a real worktree), and AC-10.

**Steps:**
- [ ] Step 1: Run `list-candidates.py .` against this repository's real store, read-only. The store will have moved since 2026-11-10, so check the result against the rule rather than a fixed answer: every log the script lists must be in the window, carry a `session-id` or have no later log on its branch, and be named in no later log's `resumed-from` or `carried-from`. For the snapshot AC-7 names, copy the store as it stood on 2026-11-10 from the maintainer's backup, or reconstruct it from the file list in S13, and confirm mode `one` with the 2026-11-08 log. Record both outputs in the spec's Revisions.
- [ ] Step 2: Run `derive-log-facts.py . --json` from a real linked worktree of this repository, such as one at `E:/tmp/pt-w07`. It must report `how: main-checkout` and the main checkout's newest log. Then write a throwaway log from that worktree with the wrap, confirm it lands in the main checkout's store, and move it to `_superseded/` by hand afterwards. Run continue from the main checkout and confirm it sees the log before the move.
- [ ] Step 3: In one session resumed with `claude --resume`, print `CLAUDE_CODE_SESSION_ID` and confirm that it equals the id from before the resume. This settles the one D6 fact the transcript scans could not see. Record the result in the spec's Unverified Claims.
- [ ] Step 4: After release and after the maintainer updates the install, verify the install by behavior: a wrap's digest shows a `carry-forward:` line, which version 1.9.1 cannot print. Check both harnesses. Both scripts exit 2 when `lib/session-logs.py` is missing, and only the Claude Code cache was confirmed to carry `lib/`, so a Codex install must be checked by running `list-candidates.py` from its installed path.
- [ ] Step 5: AC-10 waits for the first real case of two overlapping sessions in one repository. When it happens, check that continue lists both and that neither log's Waiting on You carries the other's items. Tick AC-10 only then. Until then the spec stays `committed`, not `fulfilled`.

**Verification:** Steps 1 to 3 each produce a recorded output that matches the expectation stated in the step. AC-10's checkbox is ticked only from a real case, never from a fixture.

---

## CI and Documentation Coverage

### CI

Two new steps in `gate.yml` (Phase 6, Step 7), for `lib/test-session-logs.py` and `skills/plab-continue-session/scripts/test-list-candidates.py`. The two existing suites this plan extends, `test-derive-log-facts.py` and `test-check-log.py`, already run there. No other workflow changes.

### Agent-facing documentation

- `skills/plab-wrap-session/SKILL.md`: Evidence Gathering steps 6 to 8, Session Log Output, and the Frontmatter list (Phase 4).
- `skills/plab-wrap-session/references/frontmatter-schema.md` and `session-log-template.md`: the three fields and the file-name time (Phase 3).
- `skills/plab-continue-session/SKILL.md` Phase 1, `references/log-discovery.md` and `references/handoff-display.md` (Phase 5).
- `lib/README.md`: the new module (Phase 1).
- `AGENTS.md` needs no change: no skill is added or renamed, no trigger phrase changes, and its skill summaries do not describe log discovery at this depth.

### Human-facing documentation

Both usage READMEs, both `HISTORY.md` files, `CHANGELOG.md` and the root `README.md` (Phase 6).

### Not covered here

- **A stale transcript copy.** S12 found 54 session ids whose transcript exists in two project folders, after a repository rename or a worktree session. `locate_transcript()` takes the first match alphabetically, so the wrap's verification facts can come from an outdated copy. `session-start` is unaffected, because both copies begin with the same timestamp. The fix, preferring the most recently modified match, is a separate defect with its own cause and belongs in its own change.
- **Capture-lite records written in a worktree.** The `SessionEnd` capture hook is machine-local, and where it writes from a worktree is outside this repository. Phase 2 reads `_capture/` from the resolved store, so records written into a worktree's own `_local/` are not seen.
- **An eval case for the candidate list.** The behavior suite in `evals/` covers triggers and side effects. A multi-candidate case would cost a full session per run, and Phase 5's script tests cover the logic, so none is added.

---

## Rollback

Each phase is reversible on its own, but two pairs must be reverted together.

- **Phases 1 and 2 together.** `derive-log-facts.py` loads `lib/session-logs.py` and exits 2 without it, so deleting the module alone breaks every wrap. To roll back the wrap's behavior, restore `derive-log-facts.py` and its test to their pre-1.10.0 text, which restores `newest_log()` as the carry-forward source, then delete the module and its test.
- **Phases 4 and 2 together.** `SKILL.md` step 7 tells the agent to read `carry-forward`, which only the new script prints. Reverting the script without `SKILL.md` leaves the agent reading a key that no longer exists.
- **Phase 5 alone** is safe to revert: restore continue's `SKILL.md` Phase 1 and its two references, and delete `list-candidates.py` and its test. Continue then returns to newest-wins.
- **Phase 3** is safe to revert alone. The three fields are optional, so logs that carry them stay valid under the old checker.

There is no data migration to unwind. Logs written by 1.10.0 carry three extra frontmatter fields, which 1.9.1 ignores. A log written from a worktree under 1.10.0 sits in the main checkout's store, where 1.9.1 also reads it. No log is moved or rewritten by this effort, so no log needs restoring.

---

## Before opening the pull request

- [ ] `phase-count` is 7, and there are seven `## Phase` sections.
- [ ] AC-1 to AC-10 each appear in the Completion Status table.
- [ ] No acceptance criterion appears here that is not in the spec.
- [ ] `python scripts/frontmatter-check.py`, `python scripts/doc-lifecycle-check.py` and `python scripts/gen-release-index.py --check` exit 0.
- [ ] New files are scanned for dashes directly, because `check-dashes.py` reads tracked files only.
- [ ] Both skills' versions, `HISTORY.md` entries, README version lines and manifests agree (Phase 6).
