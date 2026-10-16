---
id: W-02
title: Derive session-log facts from git instead of model recall
type: spec
status: committed
created: 2026-08-23
updated: 2026-10-15
linked-effort: the maintainer's private plab-wrap-session evolution roadmap, 2026-08-16
linked-plan: implementation-plan.md
ac-count: 11
source-count: 10
requires-human-review: false
target-release: null
linked-release: null
priority: P1
---

# Spec: Derive session-log facts from git instead of model recall

## Task Summary

**Status:** Committed. Phases P1 to P6 built and verified 2026-10-15; P7 (AC-11's re-measurement) needs calendar time and has not run.
**Last updated:** 2026-10-15
**Linked plan:** `implementation-plan.md`, updated for the 2026-10-15 build (status `in-progress`)
**Open questions:** see Open Questions / Decisions below for the full set and their status
**Revisions:** 3 (initial draft 2026-08-23; widened to one-step evidence gathering 2026-10-04; built and committed 2026-10-15; see Revisions)

### Acceptance Criteria Fulfillment

- [x] AC-1: Environment fields (machine, repo, branch, date) come from the script, not manual commands
- [x] AC-2: files-changed comes from `git diff --name-only`, grouped
- [x] AC-3: Commit-range and latest-tag data derived without colliding with existing fields
- [x] AC-4: decisions-count is a mechanical count, never a model estimate
- [x] AC-5: Verification content is derived only when a real record exists; otherwise stays model-authored
- [x] AC-6: The four judgment sections receive no script-generated content
- [x] AC-7: Script path resolution follows the `organize-logs.py` precedent
- [x] AC-8: Script writes nothing outside `.git`, fetches only on request and never prunes, supports `--json`, and ships with a stdlib-only test script
- [x] AC-9: `SKILL.md` is rewired to actually call the script
- [x] AC-10: One invocation also emits the Evidence Gathering inputs and the hygiene sweep's detection results
- [ ] AC-11: A re-measurement of completed wraps shows the median step count halved against the 2026-10-01 baseline - NOT PROVEN; needs at least ten completed wraps on the shipped version, which needs calendar time (see implementation plan P7)

### Currently In Progress

Nothing beyond AC-11's P7 measurement, which is blocked on calendar time and is not a build step.

## Purpose

W-02 (the roadmap's W-2, zero-padded per this effort's ID scheme) adds `scripts/derive-log-facts.py` to `plab-wrap-session` and rewires the skill's own Evidence Gathering and Frontmatter instructions to run it, replacing model-recalled transcription of `files-changed`, `machine`/`repo`/`branch`/`date`, `decisions-count`, commit range, tags, and the verification table with values derived directly from git and the environment. Summary, Decisions Made, Waiting on You, and the Continuation Prompt stay entirely agent-authored, since judgment over those four is the actual point of the skill. [S1]

The case for this is not only token cost. A long session's early hours are the haziest part of the model's own context, and they are exactly where today's factual sections draw from, so derivation is the version that stays correct as sessions lengthen, not merely the version that is cheaper to produce. [S1]

The 2026-10-04 revision widens the script's job from the frontmatter facts to everything the wrap gathers before it writes: the Evidence Gathering inputs and the hygiene sweep's detection results. A measurement of 293 wraps across 39 projects found a median of 10 assistant API calls per wrap. Cache reads were 53% of a wrap's cost, cache writes 35%, and the log's own text only 11%. [S9] Each call re-reads the whole session, so the number of calls sets the price far more than the length of the log does. At list prices, the median wrap cost $3.01 at the models actually used, or $1.64 repriced at Opus 5.5. [S9] Evidence Gathering and the sweep run their commands one at a time today [S7, S8], so collapsing them into one invocation attacks the larger share of that cost.

## Scope

### In Scope

1. New file `skills/plab-wrap-session/scripts/derive-log-facts.py`: a stdlib-only Python script that derives the fields named in Requirements below, including the Evidence Gathering inputs and hygiene-sweep detection results of Requirement 10.
2. New file `skills/plab-wrap-session/scripts/test-derive-log-facts.py`: fixture tests with no external test framework, matching the existing `test-organize-logs.py` precedent.
3. Edits to `skills/plab-wrap-session/SKILL.md`: the Evidence Gathering section, the Pre-Wrap Hygiene Sweep section, and the "### Frontmatter" block, wiring the skill's own procedure to run the script and use its output; `metadata.version` bump to the next minor version. Wrap shipped 1.7.0 after this spec was first drafted, so that is 1.8.0 as of the 2026-10-04 revision.
4. A new entry in `skills/plab-wrap-session/HISTORY.md` for that version.
5. Version bookkeeping owned by wrap alone: a `CHANGELOG.md` `[Unreleased]` bullet for wrap's new version, wrap's row in root `README.md`'s skill table, wrap's `version` field in `library.json`, and a regeneration of `manifest.generated.json` and both `plugin.json` files via the existing generator (`AGENTS.md:137`, re-verified 2026-10-15; this line was 117 as of the 2026-10-04 revision and has since moved with unrelated edits to that file).
6. Edits to `skills/plab-wrap-session/references/hygiene-sweep.md`, limited to pointing each check's detection step at the script's output. The resolution protocol in that file, propose and then confirm each action, is unchanged.

### Non-Goals

1. Does not change what Summary, Decisions Made, Waiting on You, or the Continuation Prompt contain, or how they are authored. These stay fully model-written; that is the explicit point the source roadmap makes about this split. [S1]
2. Does not implement or repair W-1's capture-lite `SessionEnd` hook. The script may consume an existing capture-lite record where one is relevant, but building, fixing, or wiring that hook is a separate, already-tracked item (D-4) and is out of scope here. [S6]
3. Does not edit any file under `skills/plab-continue-session/`, any file under `skills/plab-wrap-session/references/` other than `hygiene-sweep.md` (In Scope item 6), or `docs/skills/plab-wrap-session/README.md`. Those restate the same log-format contract from the read side or the human-facing side, and consolidating them is D-10's territory, not this effort's. Touching them here would let two specs claim the same edit. `hygiene-sweep.md` is the exception because it catalogues the sweep's commands rather than the log's format, and this revision moves those commands into the script.
4. Does not commit to a specific frontmatter key name for commit-range or git-tag data without first checking it does not collide with the existing Tier 3 `tags:` field (topic keywords, `frontmatter-schema.md:58`) or `commit-sha` field (single SHA, `frontmatter-schema.md:57`). The exact name is left to implementation; colliding silently with an existing field is explicitly out of bounds (see AC-3).
5. Does not change the plugin-level version in `.claude-plugin/plugin.json` or `.codex-plugin/plugin.json` beyond what the existing generator produces from `library.json`. The release-level plugin version, whatever release ships this effort, is the release plan's own gate to set, not a step in this effort's plan. (Versions are assigned only at ship time per the maintainer's decision register, decision 21; earlier drafts of this spec named v0.7.0, which shipped other efforts before this one was built.)
6. Does not run the project's own validation scripts, the third bullet of the sweep's Check 3. Which scripts exist is specific to each repository, and their output is a finding to read rather than a fact to paste, so the wrapping agent still runs them as a separate step (see D5). [S7]
7. Does not move any judgment or any write into the script. The script reports; the agent still decides whether the newest log covers the same arc, which carried Waiting on You items are resolved, and what to propose, and every proposed action still needs its own confirmation. [S7, S8]
8. Does not change what `plab-continue-session` reads. Narrowing the resume's read to fewer sections is a separate, continue-side change.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer (JP) | Runs and reads the output of wrap sessions | Reads the written log and continuation prompt; does not normally invoke the script directly |
| Wrapping agent (Claude Code or Codex running `plab-wrap-session`) | Executes the skill | Runs `derive-log-facts.py`, folds its output into the frontmatter and Files Changed section, then authors the four judgment sections |

## Requirements

1. The script must derive `machine`, `repo`, `branch`, and `date` from the environment (hostname, git remote or directory name, `git branch --show-current`, system clock) without the wrapping agent running its own equivalent commands and transcribing the result by hand. [S1, S3]
2. The script must derive `files-changed` from `git diff --name-only` against a caller-supplied base ref, grouped consistently with the "grouped by purpose if many" guidance already in `SKILL.md`'s Files Changed section. [S1, S2]
3. The script must derive commit-range and latest-tag information via `git log` and `git describe`, under a name or names that do not collide with the existing Tier 3 `commit-sha` (single SHA) or `tags` (topic keywords) fields already defined in `frontmatter-schema.md`. [S1, S3]
4. `decisions-count` in the written frontmatter must be a deterministic count of the drafted Decisions Made section's entries, computed after that section exists, never a number the model supplies from estimation or memory. [S1]
5. When a tool-call record or transcript is available for the current session, the script should surface verification-relevant facts into the Verification table's content. When none is available, including when only a capture-lite record exists (capture-lite fires at `SessionEnd` and therefore cannot describe a still-open session, per D-4's finding), the Verification section stays fully model-authored, with nothing presented as derived that was not actually derived. [S1, S6]
6. Summary, Decisions Made, Waiting on You, and the Continuation Prompt must receive no script-generated content; all four remain entirely agent-authored text. [S1]
7. The script must resolve its own path relative to the skill's own installed directory, and must treat any git-repository argument as relative to the project being wrapped, matching the resolution rule already shipped for `organize-logs.py`. [S2, S4]
8. The script must write nothing outside the repository's `.git` directory, and inside it only what Requirement 11 allows; by default it inspects git and the environment and writes nothing at all. It must support a `--json` output mode, matching `organize-logs.py`'s existing contract. A stdlib-only sibling test script must exercise it against fixture git repositories with no external test framework. [S4, S5, S10]
9. `SKILL.md`'s Evidence Gathering section and its "### Frontmatter" block must be rewritten to call the script and use its output, rather than leaving the script and the skill's own manual-derivation prose as two disconnected paths. A committed script nothing calls is exactly the "producer with zero consumers" failure D-4 already found once in this pair; this requirement exists so W-02 does not repeat it. [S2, S6]
10. The same single invocation must also emit what Evidence Gathering and the hygiene sweep collect today with separate commands. [S7, S8, S9]
    - Evidence Gathering inputs: capture-lite records newer than the newest existing log, with their count and earliest-to-latest `head` (step 7); the newest existing log's filename (step 8, whose same-arc judgment stays with the agent); and that log's Waiting on You items, verbatim, with their `(blocked since YYYY-MM-DD)` dates (step 9). [S8] The script finds the newest log by the newest-wins rule in `skills/plab-continue-session/references/log-discovery.md`. It mirrors that rule rather than redefining it, which makes a second copy of one contract; consolidating the copies is D-10's job, not this effort's (Non-Goal 3).
    - Files under gitignored locations modified since the newest log's timestamp, as the starting inventory for step 5. [S8, model-inference: the modification-time cutoff is this spec's choice; step 5 names the inventory but not how to find it]
    - The hygiene sweep's detection results for Checks 1, 2, 4 and 5, and Check 3's CHANGELOG and version-versus-tag facts, produced with the commands `hygiene-sweep.md` documents. [S7]
11. Remote facts are only true after a fetch, and a fetch writes remote-tracking refs inside `.git`. The script must fetch only when explicitly asked to, must use `git fetch --no-prune origin --tags`, and must never prune. The `--no-prune` flag is written out because a plain fetch prunes whenever `fetch.prune` or `remote.<name>.prune` is set in git configuration, and the explicit flag overrides that setting. On 2026-09-25 a `git fetch --prune`, run during a status check, deleted a remote-tracking ref without the per-action confirmation the sweep requires. [S7, S10]
12. The effort's proof is a re-measurement. Wraps made with the new version must be measured by the same method as the 2026-10-01 baseline, comparing completed wraps with completed wraps: those that wrote their log before any user prompt. That baseline's median is 12 assistant API calls. [S9]

## Acceptance Criteria

**AC-1:** Running `derive-log-facts.py` inside a git checkout emits `machine`, `repo`, `branch`, and `date` values equal to `hostname`, the git remote (or directory name absent a configured remote), `git branch --show-current`, and the system clock, respectively, with none of the four requiring the wrapping agent to separately run git or shell commands to obtain them. [S1, S3]

**AC-2:** The script's output includes a `files-changed` list equal to `git diff --name-only` against a caller-supplied base ref, grouped per the existing "grouped by purpose if many" guidance at `SKILL.md:161` (re-verified 2026-10-15; this line was 155 as of the 2026-10-04 revision, before this effort's own edits to `SKILL.md` shifted it). [S1, S2, S8]

**AC-3:** The script's output includes commit-range and latest-tag values derived from `git log` and `git describe`, under field or key names distinct from the existing `commit-sha` field (`frontmatter-schema.md:57`) and `tags` field (`frontmatter-schema.md:58`). [S1, S3]

**AC-4:** The `decisions-count` value in a written log's frontmatter equals a manual count of that same log's own Decisions Made section entries; it is never a value the model supplies from estimation or recall. [S1]

**AC-5 (Given/When/Then):** Given a session with an available tool-call or transcript record, when the script runs, then it surfaces verification-relevant facts into the Verification content. Given no such record is available, including when only a `SessionEnd`-triggered capture-lite record exists for a prior, already-closed session, when the script runs, then the Verification section is left for the agent to author, and nothing in the log is presented as derived that was not actually derived. [S1, S6]

**AC-6:** No content in the Summary, Decisions Made, Waiting on You, or Continuation Prompt sections of a written log originates from the script; all four remain fully agent-authored text. [S1]

**AC-7:** The script resolves its own file location relative to the skill's own installed directory rather than the project being wrapped, matching the resolution rule already shipped for `organize-logs.py` at `SKILL.md:107` (re-verified 2026-10-15; this line was 103 as of the 2026-10-04 revision). Any argument identifying the git repository to inspect is relative to the project being wrapped, not the plugin install location. [S2, S4]

**AC-8:** Run without its fetch option, the script performs no filesystem writes. Run with it, the script's only write is `git fetch --no-prune origin --tags`, which keeps stale remote-tracking refs even when `fetch.prune` is set in git configuration. It supports a `--json` output mode, and ships with a stdlib-only sibling `test-derive-log-facts.py` that exercises it against fixture git repositories with no external test framework, matching the `organize-logs.py` / `test-organize-logs.py` pair. [S4, S5, S10]

**AC-9:** `SKILL.md`'s Evidence Gathering section and its "### Frontmatter" block instruct the agent to run `derive-log-facts.py` and use its output, rather than leaving the script unreferenced by the skill's own procedure. [S2, S6]

**AC-10 (Given/When/Then):** Given a project with a git remote and a session-log store, when the wrapping agent runs the script once, then the output contains every item Requirement 10 names. And the agent runs no further git or shell command to obtain any fact that output contains. Running the project's own validation scripts stays a separate step (Non-Goal 6). [S7, S8, S9]

**AC-11:** Counting only completed wraps, at least ten wraps made with the new version show a median of at most six assistant API calls per wrap, against the baseline's median of twelve. A completed wrap is one that wrote its session log before any user prompt, measured by the same method as the 2026-10-01 baseline. Wraps that stopped at a confirmation prompt before writing are excluded on both sides, because a stopped wrap looks cheap without having saved anything. The measurement report also states the median cost per completed wrap at Opus 5.5 list prices, for both the baseline and the new version. [S9; model-inference for the threshold of six: one script call, one validation call, one write, one self-check, and up to two calls for a fix]

## Behavior / Examples

### Example 1: Pre-prose invocation

Before drafting any prose, the wrapping agent runs the script against the project being wrapped:

```
python <skill-dir>/scripts/derive-log-facts.py --base origin/main --json
```

```json
{
  "machine": "dev-laptop",
  "repo": "prisant-labs/prisant-utilities",
  "branch": "main",
  "date": "2026-08-23T14:12:00-07:00",
  "files-changed": [
    "skills/plab-wrap-session/SKILL.md",
    "skills/plab-wrap-session/scripts/derive-log-facts.py"
  ],
  "commit-range": "a1b2c3d..e4f5g6h",
  "latest-tag": "v0.6.0"
}
```

The agent pastes these values into the frontmatter and the Files Changed section rather than reconstructing them from memory or re-running the underlying git commands one at a time.

### Example 2: decisions-count, computed after the prose exists

The script's frontmatter-and-files-changed output happens before the model drafts prose (see Open Questions / Decisions, item D2, for why). Once the agent has drafted the Decisions Made section, `decisions-count` is filled by a mechanical count of that section's entries rather than by the model's own running tally. A log with three bulleted decisions gets `decisions-count: 3` because three bullets exist under `## Decisions Made`, not because the agent remembers making three decisions.

### Example 3: Verification section with no available record

A session run in a harness that exposes no transcript or tool-call record, and with no capture-lite record relevant to it (capture-lite describes prior closed sessions only, never the current one), produces a Verification section identical in authorship to today's: the agent writes it from context, and the log does not claim any part of it was derived.

### Example 4: One step instead of many (added 2026-10-04)

Today a deep wrap runs Evidence Gathering's commands, reads the previous log, scans the capture records, and then runs each hygiene check, each as its own tool call. With this revision the agent runs the script once, with the fetch option, and gets back one output holding the frontmatter facts, the Evidence Gathering inputs, and the sweep's detection results. It then runs the project's own validation scripts, writes the log, and runs the self-check. A wrap whose sweep finds nothing to propose reaches a written, checked log in about five calls, where completed wraps took a median of twelve at the baseline. Where the sweep does find something, each proposal still gets its own confirmation, exactly as before. [S7, S8, S9]

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Token cost | One script invocation whose output is pasted into context replaces several manual git tool-calls plus the model's own transcription of their results, on every wrap. Baseline measured 2026-10-01: a median of 10 assistant API calls and $1.64 per wrap at Opus 5.5 list prices, with cache reads 53% of the cost. Completed wraps, those that wrote their log before any user prompt, took a median of 12 calls. AC-11 sets the target against that figure. | [S1, S9] |
| Correctness under session length | Derived-field accuracy must not degrade as a session gets longer, unlike model-recalled facts drawn from early-session context. | [S1] |
| Portability | stdlib-only Python, no third-party dependencies, matching the existing script in this skill. | [S4] |
| Consistency | Git commands the script needs that the hygiene sweep already documents (for example, tag lookups) are reused from `hygiene-sweep.md` rather than re-invented a second way. | [S7] |
| Safety | No filesystem writes by default, so every invocation is safe to re-run and never needs a dry-run flag. The fetch option is the only write, it is confined to `.git`, and it never prunes. | [S4, S10] |

## Revisions

| Date | Change | By |
|---|---|---|
| 2026-08-23 | Initial draft created | agent |
| 2026-10-04 | Widened from derived facts to one-step evidence gathering, after a measurement (S9) showed that a wrap's cost is driven by its number of steps. Added Requirements 10 to 12, AC-10 and AC-11, In Scope item 6, Non-Goals 6 to 8, Example 4, decisions D4 and D5, and sources S8 to S10. Narrowed Requirement 8 and AC-8 to allow an explicit fetch that never prunes. Corrected stale references: wrap shipped 1.7.0 in the meantime, so the bump now targets the next minor version; `SKILL.md:143` became `SKILL.md:155`, `SKILL.md:91` became `SKILL.md:103`, `frontmatter-schema.md:49` and `:50` became `:57` and `:58`, `AGENTS.md:73` became `AGENTS.md:117`, and Non-Goal 5's release version became v0.7.0. The implementation plan has not yet been updated to match. Same day, before publication: AC-11 and Requirement 12 now count only completed wraps, those that wrote their log before any user prompt. The measurement window ends at the first prompt, so a wrap that stopped to ask for confirmation looked cheap without having finished; the completed-wrap baseline is a median of 12 calls, not 10. Requirement 10 now names the newest-wins rule the script mirrors from `log-discovery.md`. | agent |
| 2026-10-05 | Requirement 11 and AC-8 now specify `git fetch --no-prune origin --tags`. The earlier `git fetch origin --tags` would prune whenever `fetch.prune` is set in git configuration; checked on 2026-10-05 with a fixture clone holding a stale branch ref and `fetch.prune=true`, where the plain fetch deleted the ref and the `--no-prune` fetch kept it. The implementation plan's P3 step 1, P4 step 6 and P4 verification were changed to match, and the no-prune test case now sets `fetch.prune=true` so it exercises the configuration path. | agent |
| 2026-10-15 | Status moved from `draft` to `committed` under the maintainer's go-ahead ("Go ahead and complete the work", 2026-10-15). Phases P1 to P6 of the implementation plan were built: `scripts/derive-log-facts.py` and `scripts/test-derive-log-facts.py` added, `SKILL.md` and `references/hygiene-sweep.md` rewired, and `HISTORY.md` given a 1.8.0 entry. AC-1 through AC-10 ticked above, each against the test suite and a live run against the maintainer's real checkout. AC-11 stays unticked; P7's re-measurement needs at least ten completed wraps on the shipped version, which needs calendar time this session does not have. D1 decided (see below); D6 to D9 added as open decisions taken under the maintainer's go-ahead but not yet ratified, covering choices the spec left to implementation without naming them. Non-Goal 5 and implementation-plan.md line 26 corrected from a hardcoded v0.7.0 to "the release that ships it", per decision register item 21 (versions assigned at ship time). Implementation-plan.md Phase 7 rewritten: the spec stays `committed` until AC-11 settles, and whether to tag before that measurement is a maintainer ruling, not one this revision makes (precedent: AU-01 and WD-01 shipped before their own trials by maintainer ruling). `metadata.version` in `SKILL.md` was deliberately NOT bumped to 1.8.0 in this change: shared release bookkeeping (version bumps, CHANGELOG, manifests) is owned by a separate closing pull request for this release, not by this effort's build. | agent |

## Sources & Evidence

- [S1] the maintainer's private plab-wrap-session evolution roadmap, 2026-08-16, section "W-2. Split the log into a derived layer and an authored layer." Maintainer-local, gitignored, exists on disk. Credibility A (primary design source for this effort; the full section, including the fact/judgment table, was read before writing this spec).
- [S2] `skills/plab-wrap-session/SKILL.md` (current, v1.5.0). Repo file, credibility A, read in full.
- [S3] `skills/plab-wrap-session/references/frontmatter-schema.md`. Repo file, credibility A, read in full.
- [S4] `skills/plab-wrap-session/scripts/organize-logs.py`. Repo file, credibility A, read in full.
- [S5] `skills/plab-wrap-session/scripts/test-organize-logs.py`. Repo file, credibility A, read in full.
- [S6] the maintainer's private defect record for the wrap/continue pair, 2026-08-18, section "D-4. Capture-lite is a producer with zero consumers." Maintainer-local, gitignored, exists on disk. Credibility A.
- [S7] `skills/plab-wrap-session/references/hygiene-sweep.md`. Repo file, credibility A, read in full, and re-read in full on 2026-10-04 for the revision.
- [S8] `skills/plab-wrap-session/SKILL.md` at v1.7.0, re-read 2026-10-04 for the revision: Evidence Gathering at lines 36 to 53, the Pre-Wrap Hygiene Sweep at line 55. Repo file, credibility A. S2 records the v1.5.0 text the initial draft was written against.
- [S9] the maintainer's private measurement of wrap and continue cost, 2026-10-01, re-run 2026-10-02. It covers 293 wraps and 181 resumes across 3,645 transcripts in 39 projects. A wrap's median is 10 assistant API calls, and its cost splits into cache reads 53%, cache writes 35%, output 11%. The median wrap cost $3.01 at the models used and $1.64 repriced at Opus 5.5 list prices. Of 300 wrap starts, 201 wrote their log before any user prompt, with a median of 12 calls, and 99 stopped at a prompt first, with a median of 6. Maintainer-local, gitignored, exists on disk. Credibility A for the counts, which are computed from transcripts. Credibility B for the dollar figures: they use a cached list-price table, and they are lower bounds, because a confirmation prompt ends the measured window.
- [S10] the maintainer's private session log for 2026-09-20, written 2026-09-27, Hygiene Sweep section. It records that a `git fetch --prune` during a 2026-09-25 status check removed the stale `origin/release/v0.5.5` remote-tracking ref without the per-action confirmation the sweep requires. Maintainer-local, gitignored, exists on disk. Credibility A.

### Unverified Claims

None.

## Open Questions / Decisions

| ID | Item | Status |
|---|---|---|
| D1 | Exact field/key names for commit-range and git-describe-tag data | Decided 2026-10-15, see below |
| D2 | Whether `decisions-count` needs a second script invocation after the Decisions Made section is drafted | Decided, see below |
| D3 | Whether capture-lite (W-1 / D-4) grounds the current session's Verification table | Decided, see below |
| D4 | Whether the script may fetch from the remote | Decided 2026-10-04, see below |
| D5 | Whether the script runs the project's own validation scripts | Decided 2026-10-04, see below |
| D6 | `files-changed` diff scope: committed-only (`<base>..HEAD`) or base-vs-working-tree (`<base>`) | Open, see below |
| D7 | Default `--base` resolution order when the caller passes none | Open, see below |
| D8 | Mechanism for grouping `files-changed` "by purpose if many" | Open, see below |
| D9 | Which transcript Bash calls count as "verification-relevant" for AC-5 | Open, see below |

**D1.** The roadmap names "commit range and tags" as one derivable row but does not name field keys. `frontmatter-schema.md` already has Tier 3 fields `commit-sha` (single SHA) and `tags` (topic keywords) that a careless implementation could collide with. AC-3 constrains the answer (must not collide) without dictating the exact name. **Decided at implementation 2026-10-15:** the fields are `commit-range` (e.g. `"a1b2c3d..e4f5g6h"`, matching Example 1) and `latest-tag` (e.g. `"v0.6.0"`). Neither collides with `commit-sha` (a single SHA, `frontmatter-schema.md:57`) or `tags` (topic keywords, `frontmatter-schema.md:58`); both were checked against that file before use. **Decided by / date:** claude, left to implementation by this spec / 2026-10-15.

**D2.** The roadmap's implementation shape describes the script as emitting "a frontmatter block and a files-changed section... which the skill then wraps prose around," which reads as the script running before the model drafts prose. But `decisions-count` depends on the Decisions Made section's content, which does not exist yet at that point. This spec resolves the ordering by treating `decisions-count` as computed after that section is drafted (AC-4), which may mean a second, smaller invocation of the script, or a single generation pass in which the model still authors the whole document but defers the exact count to a mechanical recount rather than free recall. The precise mechanism is left to the implementation plan; the fixed outcome is a mechanical count, never an estimate.

**D3.** D-4 already established that a `SessionEnd`-triggered capture-lite record for the *current* session does not exist at wrap time, so it cannot ground this session's Verification table. AC-5 reflects this directly: verification derivation depends on a tool-call or transcript record if the harness exposes one, not on capture-lite, which is the record W-1 defines for prior sessions. Where no such record exists, the section stays model-authored, same as today. This spec treats the source roadmap's table row ("Verification table... tool-call record, or capture-lite from W-1") as needing this caveat rather than taking it literally, since a literal reading would contradict D-4's own, already-settled finding.

**D4.** The sweep's Check 1 can only report true remote facts after a fetch, and a fetch writes remote-tracking refs, which the initial draft's Requirement 8 forbade. Three options were considered. The agent could fetch first, but that adds back one of the calls this revision removes. The script could always fetch, but then it would mutate state silently, and a later change adding `--prune` would delete refs unasked, which already happened once by hand. Decided: the script fetches only when explicitly asked to, uses `git fetch origin --tags`, and never prunes (Requirement 11, AC-8). [S7, S10]

**D5.** Check 3 also runs the project's own validation scripts. Which scripts exist differs by repository, some are slow, and their output is a finding to read rather than a fact to paste. Decided: they stay a separate agent step (Non-Goal 6), so a wrap with no findings takes about two commands before writing, not one. AC-11's threshold allows for that call. [S7, model-inference]

### D6: `files-changed` diff scope (Open)

**Summary.** Should `files-changed` compare the base ref to `HEAD` (committed changes only) or to the current working tree (including staged and unstaged edits to tracked files)?

**Context.** AC-2 reads "a files-changed list equal to `git diff --name-only` against a caller-supplied base ref", which is the two-argument form comparing a ref to the working tree. The implementation plan's Phase 1 step 3 text instead describes `git diff --name-only <base>..HEAD`, the committed-only form. The two commands disagree whenever the session has uncommitted tracked edits, which is the normal state of a final or deep wrap written before its own commit.

**Desired outcome.** `files-changed` should reflect the session's actual current state at the moment the script runs, so the agent never has to separately check for uncommitted work the field missed.

**Options / approaches.**

* **Option A:** `git diff --name-only <base>..HEAD` (committed only). Matches the implementation plan's literal text; misses any tracked edit not yet committed.
* **Option B:** `git diff --name-only <base>` (base vs. working tree). Matches AC-2's literal wording; includes staged and unstaged tracked edits, which is what a wrap in progress actually has.

**Recommendation.** Option B. It satisfies AC-2 as written and serves the actual use case; Option A would silently under-report files-changed for the common case of a wrap written before its own final commit. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D7: Default `--base` resolution order (Open)

**Summary.** When the caller passes no `--base`, what should the script compare against?

**Context.** Neither the spec nor the implementation plan names a default; Phase 1 step 3 only says "a sensible upstream ref". Evidence Gathering needs a working default so the agent is not required to supply `--base` on every invocation.

**Desired outcome.** A default that resolves to something meaningful in the common cases (a branch tracking a remote; a tagged release with no tracking branch) and degrades to "no base" rather than erroring when neither is available.

**Options / approaches.**

* **Option A:** Always require `--base` explicitly; error otherwise. Simplest, but reintroduces a manual step Evidence Gathering is trying to remove.
* **Option B:** Try the upstream tracking ref (`@{u}`) first, then the latest reachable tag (`git describe --tags --abbrev=0`), then report no base available. Covers the common cases without guessing at an arbitrary ref.
* **Option C:** Default to `HEAD~1`. Cheap but meaningless for a multi-commit session; would understate files-changed for any session with more than one commit.

**Recommendation.** Option B, implemented in `resolve_base()`. The resolved base and how it was chosen are both included in the script's output, so the agent can see what was actually compared against. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D8: `files-changed` grouping mechanism (Open)

**Summary.** AC-2 requires grouping "per the existing 'grouped by purpose if many' guidance" at `SKILL.md:161`. "Purpose" is a judgment call; what should the script compute mechanically?

**Context.** `SKILL.md`'s Files Changed section guidance is deliberately loose prose aimed at a human-authored log, not a mechanical rule. A script has no notion of "purpose", only of paths.

**Desired outcome.** A grouping that is a defensible mechanical proxy for purpose, without blocking the flat list AC-2 actually tests for equality against `git diff --name-only`.

**Options / approaches.**

* **Option A:** Group by first path segment (top-level directory). `skills/plab-wrap-session/...` and `docs/...` already separate by area of the repository, which is a reasonable proxy for purpose in this codebase's layout.
* **Option B:** Leave `files-changed` flat and let the agent group by hand when drafting the log, as before this effort.
* **Option C:** Group by file extension or type. Does not track "purpose" at all; two edits to the same feature in different file types would split across groups.

**Recommendation.** Option A, emitted as a separate `files-changed-grouped` field alongside the flat `files-changed` list, so AC-2's "equal to `git diff --name-only`" is still literally testable against the flat field. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D9: Verification-relevant command filter (Open)

**Summary.** AC-5 asks the script to surface "verification-relevant facts (for example, the test, gate and check commands run this session and whether each tool result was an error)" from the current session's transcript. Which Bash calls qualify?

**Context.** A transcript's Bash calls are overwhelmingly not verification commands (file reads via `cat`, exploratory `grep`, `git status`, and so on). Surfacing all of them would bury the few that matter; a wrong filter could also miss a real gate run under an unexpected name.

**Desired outcome.** A filter that catches the gate, test, check, and lint commands this repository's own conventions actually use, without requiring an exhaustive, hand-maintained list of script names.

**Options / approaches.**

* **Option A:** A keyword regex over the command text (`test|check|gate|lint|verify`, case-insensitive). Catches every gate script in this repository (`check-dashes.py`, `doc-lifecycle-check.py`, `gen-release-index.py --check`, `version-parity-check.py`, `test-organize-logs.py`, and this effort's own `test-derive-log-facts.py`) without naming any of them.
* **Option B:** An exact allowlist of script basenames. More precise, but silently misses a new gate script added later until the list is updated, which is the opposite of what a derivation script should do.
* **Option C:** Surface every Bash tool call verbatim, with no filter. Satisfies nothing about the field being useful; the Verification section would have to wade through the whole command history.

**Recommendation.** Option A, capped at 50 captured facts with an overflow count and each command truncated to 200 characters, so one noisy session cannot balloon the output. Working default: built on this recommendation on 2026-10-15 under the maintainer's go-ahead; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
