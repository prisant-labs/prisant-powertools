---
id: H-05
title: Retire dash enforcement in CI and the wrap self-check
type: spec
status: draft
created: 2026-10-26
updated: 2026-10-26
linked-effort: "the maintainer's instruction of 2026-09-14 to remove the dash rule, and the walk ruling of 2026-10-17 that scoped it, both in the maintainer's private decision record"
linked-plan: null
linked-release: null
ac-count: 9
source-count: 11
requires-human-review: true
target-release: null
priority: P3
---

# Spec: Retire dash enforcement in CI and the wrap self-check

## Task Summary

**Status:** draft
**Last updated:** 2026-10-26 by claude (Opus 5.5), written under the maintainer's go-ahead of 2026-10-26
**Linked plan:** not yet planned
**Open questions:** 2 (see Open Questions / Decisions)
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: `scripts/check-dashes.py` and the CI job that runs it are gone, and the other CI jobs are unchanged
- [ ] AC-2: The repository's required status checks are unchanged
- [ ] AC-3: `AGENTS.md` no longer states the dash rule or says CI enforces it
- [ ] AC-4: `dash-check.py` is gone, and the wrap self-check neither runs nor reports a dash check
- [ ] AC-5: `test-check-log.py` still proves that a broken detector breaks the whole self-check
- [ ] AC-6: No live instruction names either deleted script
- [ ] AC-7: `plab-guide` is unchanged, so its G-11 dash cleanup still applies
- [ ] AC-8: The user and technical documents describe the dash rule as it now stands
- [ ] AC-9: Every changed skill carries a version bump and a `HISTORY.md` row, and the CHANGELOG records the removal

### Currently In Progress

None. This spec was written on 2026-10-26; the build waits for its own go-ahead.

---

## Purpose

This repository enforces "never write an em-dash or an en-dash" in three layers. Layer 1 is repository-wide: `scripts/check-dashes.py`, the CI job that runs it, and a convention line in `AGENTS.md` [S4, S8, S10]. Layer 2 is the dash gate in `plab-wrap-session`'s Log Self-Check, `skills/plab-wrap-session/scripts/dash-check.py` [S7]. Layer 3 is G-11 (dash cleanup) in `plab-guide`, which governs guides written for other readers [S6].

On 2026-09-14 the maintainer said to remove the rule, because "It is a [simple] preference that isn't worth the enforcement effort" [S1]. The maintainer's global instructions had already turned the hard ban into a preference, and removed its enforcement hook, on 2026-08-28 [S3]. On 2026-10-17 the maintainer scoped the removal: retire layers 1 and 2, and keep layer 3 [S2].

This spec defines what retiring layers 1 and 2 means, and how to tell that it is done. The preference itself survives in the maintainer's global instructions. Only the enforcement goes.

## Scope

### In Scope

1. Delete `scripts/check-dashes.py` and the `dash-check` job in `.github/workflows/gate.yml`.
2. Delete `skills/plab-wrap-session/scripts/dash-check.py`, and remove the dash check from `check-log.py`, its tests and the Log Self-Check section of `SKILL.md`.
3. Remove the dash convention line from `AGENTS.md`, and the sentence that says CI runs `check-dashes.py`.
4. Reword every live instruction or docstring that names either deleted script, so that nothing points at a missing file.
5. Update the user and technical documents that describe the dash gates, and record the change in the CHANGELOG and each changed skill's `HISTORY.md`.

### Non-Goals

1. **Layer 3.** `plab-guide`'s G-11 stays exactly as it is, by the maintainer's ruling [S2].
2. **Rewriting existing text.** No document is swept to add or remove dashes in either direction. The maintainer's global instructions say not to sweep existing text for them [S3].
3. **Historical records.** `CHANGELOG.md`, every `HISTORY.md`, and the specs and implementation plans of earlier efforts keep their text. They record what was built under the rule at the time.
4. **Data that names a deleted script.** The committed audit sample (`skills/plab-audit/examples/`), the eval prompts (`evals/`) and the command strings in `test-derive-log-facts.py` are left alone. Each uses the script name as data, and none needs the file to exist.
5. **Release plan 04's D2 (dash rule promotion to CI).** This effort reverses that decision's outcome, but its record stays as written [S5].

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Writes prose here, and wraps sessions | Stops seeing CI failures or wrap self-check findings for a dash |
| Running agent (Claude Code or Codex) | Writes files, runs the wrap self-check | No longer reads a dash rule in `AGENTS.md`, and no longer gets a dash finding from `check-log.py` |
| CI | Runs the Gate workflow on every pull request and every push to `main` | Runs one job fewer, and no longer installs ripgrep |

## Requirements

1. `scripts/check-dashes.py` is deleted. The `dash-check` job is removed from `.github/workflows/gate.yml`, together with its ripgrep install step, which no other job uses [S4, S8].
2. The repository's required status checks do not change. Branch protection on `main` requires only the Advanced Skill Library Standard and Document lifecycle checks, so the removed job was never one of them [S8].
3. `AGENTS.md` loses its convention line "Never write em-dashes (U+2014) or en-dashes (U+2013)", and its Build and validate section stops saying that CI runs `check-dashes.py` [S10]. No replacement line is added, because the maintainer's global instructions already carry the preference for every project, and a second statement here could drift from it [S3, model-inference].
4. `skills/plab-wrap-session/scripts/dash-check.py` is deleted. `check-log.py` stops calling it, and its output no longer carries a `dashes` check. The Log Self-Check section of `SKILL.md` stops listing a dash gate, and stops calling the detector-backed gates "two" [S7].
5. `test-check-log.py`'s proof that one broken detector makes the whole self-check broken, while the other checks still run, keeps working. It uses the path-citation detector as its broken stand-in, because the dash detector it uses today is being deleted [S7].
6. No live instruction names a deleted script. Live instructions are `AGENTS.md`, every `SKILL.md` and skill reference, everything under `docs/` except effort folders, the implementation-plan template, the workflows, and every script's docstrings and comments. A docstring that cites `check-dashes.py` as the precedent for the three-state exit contract, or for the cp1252 encoding lesson, cites CI-01's spec instead, which keeps that history [S4, model-inference].
7. `skills/plab-guide/` is not modified [S2, S6].
8. `docs/status-skills.md` and `docs/skills/plab-wrap-session/README.md` stop listing either deleted script as part of the repository. The status page's "Dash rule" row stops saying that CI and a local hook enforce the rule; the hook was already removed on 2026-08-28 [S3, S11].
9. Every skill whose folder changes bumps its own `metadata.version` and adds a `HISTORY.md` row for that version. On today's inventory that is `plab-wrap-session`, `plab-continue-session` (one docstring) and `plab-audit` (one type-pack reference). The CHANGELOG's `[Unreleased]` section gains a Removed entry naming both scripts and the CI job [S9].

## Acceptance Criteria

**AC-1:** `scripts/check-dashes.py` does not exist, and `.github/workflows/gate.yml` contains no job that runs it and no ripgrep install step. Every other job in the workflow is byte-identical to its state before this effort. [S4, S8]

**AC-2:** `gh api repos/prisant-labs/prisant-powertools/branches/main/protection --jq '.required_status_checks.contexts'` returns the same two contexts after the merge as before it: "Advanced Skill Library Standard" and "Document lifecycle (schema, cross-file, index freshness)". [S8]

**AC-3:** `git grep -n -e "U+2014" -e "check-dashes" -- AGENTS.md` returns nothing. [S10]

**AC-4:** `skills/plab-wrap-session/scripts/dash-check.py` does not exist. Running `check-log.py --json` on a clean deep-mode log returns no `dashes` key under `checks`. A log containing an em-dash passes the self-check. [S7]

**AC-5:** `python skills/plab-wrap-session/scripts/test-check-log.py` exits 0, and its broken-detector case replaces `path-citation-check.py` with a stub that exits 2. Canary: with `check-log.py`'s broken-result propagation removed, the same command fails and names that case. [S7]

**AC-6:** This command returns no file:

```
git grep -l -e check-dashes -e dash-check -- . ':!CHANGELOG.md' ':!**/HISTORY.md' ':!docs/internal/release-plans/*/*/**' ':!skills/plab-audit/examples/**' ':!evals/**' ':!skills/plab-wrap-session/scripts/test-derive-log-facts.py'
```

Before this effort it returns 17 files. [model-inference: the exclusion list is this spec's own reading of Non-Goals 3 and 4]

**AC-7:** `git diff <base>..HEAD -- skills/plab-guide/` is empty, where `<base>` is the commit this effort branched from. [S2, S6]

**AC-8:** Neither `docs/status-skills.md` nor `docs/skills/plab-wrap-session/README.md` names `dash-check.py` or `check-dashes.py`. The status page's dash row, if it is kept, says the rule is a preference with no enforcement in this repository. [S11]

**AC-9:** `python scripts/version-parity-check.py` and `python scripts/skill-drift-check.py --strict` both exit 0 on the closing release pull request. `CHANGELOG.md`'s release section for this effort has a Removed entry naming `scripts/check-dashes.py`, `skills/plab-wrap-session/scripts/dash-check.py` and the `dash-check` CI job. [S9]

## Behavior / Examples

### Example 1: A pull request with an em-dash

Before this effort, a pull request whose README gains an em-dash fails the "No em-dash / en-dash (repo-wide)" job. That job is not required, so the pull request can still merge, but it shows red. After this effort, the job does not exist, and the pull request shows only the remaining checks.

### Example 2: A wrap whose log contains an en-dash

Before this effort, `check-log.py` reports the `dashes` check as findings, and the wrap must rewrite the line before it is done. After this effort, the self-check runs the path-citation detector and its agent-judged rules, and the en-dash is not a finding.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Sequencing | Build after the citation-checker fix for markdown links merges, because both edit `skills/plab-wrap-session/scripts/path-citation-check.py`. | [model-inference] |
| Cost | Each wrap's self-check runs one detector subprocess fewer, and each CI run runs one job fewer. | [S7, S8] |
| Safety | No required check changes, so branch protection needs no settings edit. | [S8] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-10-26 | claude | added | Initial spec, written on the maintainer's go-ahead of 2026-10-26 to write the dash-retirement spec the 2026-10-17 walk ruled on. |

## Sources & Evidence

- **[S1]** The maintainer's instruction of 2026-09-14 to remove the dash rule: "It is a [simple] preference that isn't worth the enforcement effort." Recorded in the maintainer's private decision register, entry 3. Maintainer-local, gitignored. Class A.
- **[S2]** The maintainer's walk ruling of 2026-10-17: write the small spec retiring layers 1 and 2, meaning `check-dashes.py`, its CI job and the `AGENTS.md` line, plus the wrap self-check's dash check; keep `plab-guide`'s G-11. Recorded in a private walk record. Maintainer-local, gitignored. Class A.
- **[S3]** The maintainer's global agent instructions, which turned the hard ban into a preference and removed its enforcement hook on 2026-08-28, and which say not to sweep existing text for dashes. Maintainer-local. Class A.
- **[S4]** `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/CI-01_ci-bootstrap/spec.md`, the effort that created `check-dashes.py` and its CI job, and that records the three-state contract and the encoding lesson other scripts cite. Its OQ-1 asked whether G-11 should reuse this script's engine. Class A.
- **[S5]** `docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md`, D2 (dash rule promotion to CI), the decision this effort reverses. Class A.
- **[S6]** `skills/plab-guide/references/voice-and-style.md`, G-11 (dash cleanup). Class A.
- **[S7]** `skills/plab-wrap-session/SKILL.md` (Log Self-Check), `skills/plab-wrap-session/scripts/check-log.py`, which calls `dash-check.py`, and `skills/plab-wrap-session/scripts/test-check-log.py`, whose broken-detector case stubs out `dash-check.py`. Class A.
- **[S8]** `.github/workflows/gate.yml`, the `dash-check` job and its ripgrep step, and the branch protection on `main`, read on 2026-10-26 with `gh api`: the required checks are the Advanced Skill Library Standard and Document lifecycle checks only. Class A.
- **[S9]** `scripts/skill-drift-check.py` and `scripts/version-parity-check.py`, which require a changed skill to bump its version and record it. Class A.
- **[S10]** `AGENTS.md`, the convention line on dashes and the Build and validate sentence naming `check-dashes.py`. Class A.
- **[S11]** `docs/status-skills.md`, which lists both scripts and says a local PreToolUse hook enforces the rule, and `docs/skills/plab-wrap-session/README.md`, which lists `dash-check.py`. Class A.

### Unverified Claims

- Requirement 3, that `AGENTS.md` should carry no replacement preference line. This is this spec's reading of the duplication risk, marked `[model-inference]`.
- Requirement 6 and AC-6, which name the live instructions and the exclusion list. The ruling names the layers, not every file, so the boundary is this spec's reading, marked `[model-inference]`.
- The sequencing requirement, which rests on the citation-checker fix being built first. Marked `[model-inference]`.

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Whether `plab-audit`'s own no-dash output rule goes too | (none) | Open | 2026-10-26 |
| D2 | Whether the no-dash constraint lines in unbuilt implementation plans go too | (none) | Open | 2026-10-26 |

### D1: Whether `plab-audit`'s own no-dash output rule goes too (Open)

**Summary.** `skills/plab-audit/references/output-bundle.md` tells the audit skill to write its bundle with no em-dashes and no en-dashes. The ruling did not name it.

**Context.** The ruling named three layers and kept the third, G-11, because it governs documents written for other readers [S2]. The audit rule is not one of the three layers. It is an unenforced style line in a skill's output contract, and no script checks it.

**Desired outcome.** The audit skill's output rules match the maintainer's intent, and this effort does not quietly widen the ruling.

**Options / approaches.**

* **Option A:** Keep it. An audit bundle is a deliverable like a guide, and the line costs nothing because nothing enforces it.
* **Option B:** Remove it, so that no skill tells an agent to avoid dashes.

**Recommendation.** Option A. It matches the ruling's reason for keeping G-11, and it leaves `plab-audit` untouched by this effort, apart from the one type-pack line in Requirement 9.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Whether the no-dash constraint lines in unbuilt implementation plans go too (Open)

**Summary.** Seven implementation plans that are still draft or in progress open with a global constraint saying not to write em-dashes or en-dashes in any file they touch.

**Context.** The plans are C-03, C-04, C-05, D-10, W-02, W-03 and W-04. Each line constrains only the agent that executes that plan. None of them runs a deleted script, so none becomes a broken instruction. Non-Goal 3 leaves plan text alone in general.

**Desired outcome.** An agent executing one of these plans later is not held to a rule the maintainer retired, unless the maintainer wants that.

**Options / approaches.**

* **Option A:** Leave the lines. They match the preference that survives in the global instructions, and editing seven plans for a preference is churn.
* **Option B:** Remove the lines in this effort, so that no plan states a retired rule.

**Recommendation.** Option A. The lines are stricter than the preference but never contradict it, and each plan's executing agent can drop the line when that plan is next opened.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
