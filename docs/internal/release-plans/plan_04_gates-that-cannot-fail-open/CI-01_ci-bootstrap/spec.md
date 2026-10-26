---
id: CI-01
title: CI bootstrap - toolkit standard gate and repo-wide dash check
type: spec
status: fulfilled
created: 2026-08-23
updated: 2026-10-26
linked-effort: the maintainer's private defect record for the wrap/continue pair, 2026-08-18
linked-plan: implementation-plan.md
ac-count: 8
source-count: 15
requires-human-review: false
target-release: v0.4.0
linked-release: docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md
priority: P1
---

# Spec: CI Bootstrap - Toolkit Standard Gate and Repo-Wide Dash Check

## Task Summary

**Status:** Fulfilled
**Last updated:** 2026-08-24
**Linked plan:** `implementation-plan.md`
**Open questions:** 4 (see Open Questions / Decisions)
**Revisions:** None yet; this is the initial draft.

### Acceptance Criteria Fulfillment

- [x] AC-1: `gate.yml` triggers on pull requests and on pushes to `main`.
- [x] AC-2: The standard-gate job invokes the toolkit Action pinned to `v1.16.1` with `fail-on-error: true`.
- [x] AC-3: The standard-gate job runs with `sarif: true` and uploads the result to the Security tab.
- [x] AC-4: `gate.yml` excludes the two toolkit-internal scripts, with a comment stating why for each.
- [x] AC-5: `scripts/check-dashes.py` is a portable, ripgrep-backed scan with exactly one named exclusion.
- [x] AC-6: The dash check proves its own detector before trusting a result: clean, findings, or broken.
- [x] AC-7: No file under `.github/workflows/` contains inline pass/fail logic of its own.
- [x] AC-8: Nothing in the gate tags a release, edits a changelog, bumps a version, or pushes a commit.

### Currently In Progress

None.

## Purpose

`prisant-utilities` has no `.github/` directory today, so its only conformance check is a command in `AGENTS.md` a human has to remember to run by hand, and its only dash-character enforcement is a PreToolUse hook scoped to one machine that a `cp`-based migration has already bypassed once. CI-01 gives the repo its first GitHub Actions workflow, with two independent jobs that report and never fix: the toolkit's Advanced Skill Library Standard grader, promoted from a manual command to an automatic gate, and a new repo-wide check for the em-dash and en-dash characters the maintainer's global writing rule bans. Both gates prove their own detectors work before trusting a clean result, using three states (clean, findings, broken) rather than a pass/fail binary. CI-01 applies that canary-before-trust pattern inside CI; D-11 (three-state gate canaries) applies the identical pattern to the wrap skill's own Log Self-Check gates. Neither effort is a prerequisite of the other. They are two independent applications of one principle, which originates in the maintainer's own `pii-gate.py` and is recorded in D-11's defect-ledger entry; they share no code and either may land first.

## Scope

### In Scope

- `.github/workflows/gate.yml`: a new workflow with two jobs, `standard-gate` and `dash-check`, triggered on `pull_request` and on `push` to `main`.
- `scripts/check-dashes.py`: a new, portable, ripgrep-backed script that scans git-tracked files for the literal em-dash (U+2014) and en-dash (U+2013) characters, proves its own detector against a canary before trusting any result, and exits 0 (clean), 1 (findings), or 2 (broken).
- A one-line addition to `AGENTS.md`'s "Build and validate" section stating that CI now runs the conformance gate automatically, so that section stops describing a manual-only process.
- A proposed (confirm-before-writing) `CHANGELOG.md` entry under `[Unreleased]` noting the repo's first CI gate now exists.

### Non-Goals

- No release automation: nothing in `gate.yml` tags a release, publishes a package, or pushes a commit.
- No auto-fixing: the dash check reports line numbers; it does not rewrite files. A human or an agent fixes findings.
- No invocation of `check-parity.mjs` or `verify-tag-matches-manifests.mjs`. Both are toolkit-internal scripts that fail in this repo for reasons unrelated to this repo's content (see Requirements, R2).
- No change to the wrap or continue skill's Log Self-Check gates. CI-01 establishes the canary-before-trust pattern in CI only; retrofitting it onto `skills/plab-wrap-session/SKILL.md`'s own gates is D-11's job, not this effort's.
- No general-purpose suppression mechanism for the dash check (no ignore-file syntax, no inline suppression comments). The script carries exactly one fixed, named, commented exclusion. Fixed values beat options for a single maintainer.
- No coverage of files outside git's tracked tree. Gitignored and local-only content is out of scope by construction, since `git ls-files` never lists it and a fresh CI checkout never contains it.
- No change to `skills/plab-guide/references/voice-and-style.md`'s own G-11 convention (its manual `grep -P` dash check). Flagged as Open Question OQ-1, not fixed here.
- No bump to `library.json`, `.claude-plugin/plugin.json`, or `.codex-plugin/plugin.json` version numbers. Those move once, at release time, across every effort landing in v0.4.0, not per effort.
- No `README.md` update. This repo's own `doc-update-rules.md` excludes "CI/infrastructure changes" from README updates, and no user-facing skill capability changes here.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer (JP) | Sole owner and approver of this repo | Reads gate results in the PR checks UI and the Security tab; decides whether to fix a finding or, rarely, override it. Never automated around. |
| Agent (any coding session, Claude or Codex) | Writes commits that become pull requests or direct pushes to `main` | Triggers both gate jobs automatically on every push; must resolve findings before a PR can merge cleanly. Reads `AGENTS.md`'s "Build and validate" section before assuming what CI checks. |

## Requirements

1. The repo has no `.github/` directory today; CI is entirely greenfield, confirmed by direct listing of the repo root this session. [S12]
2. The toolkit's reusable Action wraps `scripts/check.mjs` only. `check-parity.mjs` is the toolkit's own validator-parity harness, used by the toolkit's own `.github/workflows/ci.yml` to check agreement between an installed `claude` CLI and a `skills-ref` PyPI release, not by consumer repos. `verify-tag-matches-manifests.mjs` requires a `package.json` among the four manifests it compares; this repo has never had one. [S2] [S3]
3. `AGENTS.md` already documents `check.mjs` as this repo's conformance gate, run manually today via a placeholder path the maintainer fills in by hand. [S4]
4. The maintainer's global "no em-dash or en-dash" rule is enforced today by exactly one mechanism: a PreToolUse hook scoped to a single machine (`~/.claude/hooks/no-em-dashes.py`). A `cp`-based migration has already bypassed it once, letting 31 dashes into this repo. [S7] [S11]
5. In the seven days before this effort, the same failure class (a detector that reports clean while broken) was independently found three times, twice in tools this effort is directed to avoid: a shell escape that expands to a literal backslash-u string in Git Bash rather than the intended character, and a `perl -ne` sweep that reads raw bytes without decoding, so a codepoint escape can never match the UTF-8 byte sequence for an em-dash. Ripgrep, which decodes UTF-8, was proven (by canary, same day) to hit both cases perl missed. [S6]
6. Direct verification this session (a ripgrep-backed scan across the full working tree) found exactly one git-tracked file containing literal em-dash or en-dash characters: `skills/plab-guide/references/voice-and-style.md`. Every instance there is a deliberate "what this character looks like" illustration inside a style guide, not accidental drift. [S9] [S12]
7. The toolkit's own governing document requires, at Standard sec 4.1/4.4, that "CI configuration MUST contain no validation logic of its own; it MUST only invoke the portable scripts." This applies to every workflow this repo adds, not only to the toolkit's own. [S1] [S3]
8. GitHub's Security tab (code scanning) is available at no cost for public repositories, and ripgrep is not among the tools preinstalled on the GitHub-hosted `ubuntu-latest` runner image, so it must be installed as an explicit step. [S13] [S14]

## Acceptance Criteria

**AC-1:** `.github/workflows/gate.yml` triggers on `pull_request` and on `push` to the `main` branch. [S1] [S4]

**AC-2:** The workflow's `standard-gate` job invokes `product-on-purpose/agent-skills-toolkit` pinned to the exact tag `v1.16.1` (never a branch or a floating major-version tag), with `fail-on-error: true`. [S1]

**AC-3:** The `standard-gate` job runs the toolkit Action with `sarif: true`, and a subsequent step uploads the resulting SARIF file to the repository's Security tab, conditioned on the `sarif-path` output being non-empty. [S1] [S13]

**AC-4:** `gate.yml` does not invoke `check-parity.mjs` or `verify-tag-matches-manifests.mjs`. A comment in the workflow states, for each, why it is excluded. [S2] [S3] [S4]

**AC-5:** `scripts/check-dashes.py` scans git-tracked files for the literal em-dash (U+2014) and en-dash (U+2013) characters by invoking ripgrep as a subprocess, not perl and not a shell-escaped pattern, with exactly one named, commented exclusion (`skills/plab-guide/references/voice-and-style.md`). [S6] [S9] [S11]

**AC-6:** Before trusting any scan result, `check-dashes.py` proves ripgrep still detects a known-positive canary and correctly ignores a known-negative anti-canary (a plain hyphen and a numeric range). The script exits 0 for a clean scan, 1 when it finds a banned character outside the exclusion, and 2 when the canary proof fails, so a broken detector is distinguishable from both a clean tree and a real finding. [S6] [S8]

**AC-7:** No file under `.github/workflows/` makes a pass/fail decision using inline string or regex logic against file contents. Every such decision happens inside a committed script (`scripts/check-dashes.py`) or the pinned Action; the only conditionals in workflow YAML reference step outputs (for example `steps.gate.outputs.sarif-path`) or a script's exit code, never file content directly. [S1] [S3]

**AC-8:** `gate.yml` contains no step that tags a release, edits a changelog, bumps a version file, or pushes a commit. The toolkit Action's own inputs (`path`, `profile`, `strict`, `fail-on-error`, `annotations`, `sarif`, `node-version`) confirm it is report-only by construction; nothing added by this effort changes that. [S1]

## Behavior / Examples

**Walkthrough 1: a clean pull request.**
Given a PR that touches only ASCII-clean files, when `dash-check` runs, then `check-dashes.py` first proves its canary (a known-positive string containing both banned characters, piped to ripgrep via stdin, must match; a known-negative string containing only plain hyphens and a numeric range like "2-5" must not match), then scans `git ls-files` minus the one named exclusion, finds nothing, prints `CLEAN: canary proved, no banned characters found in tracked files.`, and exits 0. The `standard-gate` job runs in parallel, reports a tier, and uploads a SARIF file (which may contain zero results) to the Security tab.

**Walkthrough 2: a PR introduces a stray em-dash.**
Given a PR that adds an em-dash to a new or edited tracked file outside the exclusion, when `dash-check` runs, then the canary proof still passes (the detector itself is fine), the real scan matches the new line, the script prints the matching file and line number, prints `FINDINGS: N line(s) contain an em-dash or en-dash. Replace with ' - ' or restructure.` to stderr, and exits 1. The PR check shows red with the exact file and line surfaced in the log; no automatic rewrite happens.

**Walkthrough 3: ripgrep itself is unavailable or broken.**
Given a runner (or a maintainer's local machine) where `rg` is missing from PATH, when `check-dashes.py` runs, then `shutil.which("rg")` returns `None` before any scan is attempted, the script prints `BROKEN: ripgrep (rg) not found on PATH.` to stderr, and exits 2, immediately, without ever reporting the tree as clean. The same exit-2 path fires if `rg` is present but the canary self-test fails (known-positive not matched, or known-negative wrongly matched): the script never reaches the real scan, and a broken detector can never be silently read as "0 findings."

**Walkthrough 4: verifying the findings path without fabricating a violation.**
Because `skills/plab-guide/references/voice-and-style.md` already legitimately contains both banned characters (Requirements, R6), a maintainer can prove the findings path works without ever creating a new file containing a literal em-dash (which the very PreToolUse hook this effort promotes would block on this machine): temporarily comment out that one line in `EXCLUDE`, run the script, confirm exit 1 and that the reported lines match `voice-and-style.md`'s known examples, then restore the exclusion.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Cost | GitHub-hosted runners and the toolkit's public Action incur no cost for this public repo. | [S13] |
| Token economy | Both gate jobs run with zero ongoing model-token cost; neither invokes an LLM. This is mechanization-ladder rung 1. | design frame, rung 1 |
| Determinism | Every third-party Action reference is pinned to an exact tag, never a floating branch (`v1.16.1`, `actions/checkout@v7`, `actions/setup-python@v6`, `github/codeql-action/upload-sarif@v3`). | [S1] |
| Portability | `scripts/check-dashes.py` runs identically in CI and on the maintainer's own machine; no CI-only code path exists. | [S1] [S3] |
| Latency | `standard-gate` and `dash-check` run as two independent, parallel jobs rather than sequential steps in one job, so a slow toolkit grade never delays dash-check feedback. | design choice (this spec) |

## Revisions

| Date | Change |
|---|---|
| 2026-08-23 | Initial draft created. |

## Sources & Evidence

- [S1] `E:\Projects\product-on-purpose\agent-skills-toolkit\action.yml` (local clone, `product-on-purpose/agent-skills-toolkit`; confirmed byte-identical to the `v1.16.1` tag via `git diff v1.16.1 HEAD -- action.yml`, empty). Action definition, inputs, outputs, the documented SARIF usage example, and the Standard sec 4.1/4.4 quote. Credibility A (opened directly).
- [S2] `E:\Projects\product-on-purpose\agent-skills-toolkit\scripts\check-parity.mjs` (same clone, confirmed identical to `v1.16.1` via `git diff`). Header comment: what it validates and that it is toolkit-internal (`used-by: .github/workflows/ci.yml` in the toolkit's own repo). Credibility A.
- [S3] `E:\Projects\product-on-purpose\agent-skills-toolkit\scripts\verify-tag-matches-manifests.mjs` (same clone, confirmed identical to `v1.16.1` via `git diff`). Header comment naming the four manifests it compares, including `package.json`, and a second, independent quote of Standard sec 4.4. Credibility A.
- [S4] `AGENTS.md:71` (this repo). "Conformance gate: `node <agent-skills-toolkit>/scripts/check.mjs .`" Credibility A.
- [S5] `skills/plab-wrap-session/SKILL.md:186-195` (this repo). The Log Self-Check gates, including the em-dash/en-dash gate and the file-existence gate, that D-11 later applies canaries to. Cited for the dependency-direction claim in Purpose. Credibility A.
- [S6] `the maintainer's private defect record for the wrap/continue pair, 2026-08-18:187-207` (maintainer-local; gitignored, exists on disk). D-11 (three-state gate canaries): the three same-week detector failures, the clean / findings / broken mechanism, and the `pii-gate.py` precedent (14 canaries and 14 anti-canaries, exit 2 for broken). Credibility A.
- [S7] `the maintainer's private skill-candidates memo, 2026-08-15:46` (maintainer-local). "Your no-em-dash PreToolUse hook was bypassed by `cp`, letting 31 dashes into the new repo." Credibility A.
- [S8] `the maintainer's private skill-candidates memo, 2026-08-15:37-57` (maintainer-local). Candidate 1, verification integrity: the general idea CI-01 partially instantiates, independently citing the same `pii-gate.py` precedent. Credibility A.
- [S9] `skills/plab-guide/references/voice-and-style.md:26-43,74-84` (this repo). The one file with literal em-dash/en-dash characters (deliberate pedagogical use), and G-11, `plab-guide`'s own existing, manual, rung-3 dash convention. Credibility A.
- [S10] `CHANGELOG.md:20-38`, specifically lines 28-29 (this repo). Confirms G-11 is "a written-discipline rule verified by grep," not an automated sweep, and that a previously-documented but nonexistent sweep script was already corrected in `plab-guide` 2.2.2. Credibility A.
- [S11] The maintainer's machine-local PreToolUse dash hook, installed under the user's Claude Code configuration directory and outside this repository. The existing single-machine enforcement this effort promotes to CI, and the source of the escape-sequence pattern that `scripts/check-dashes.py`'s canary design reuses: the banned codepoints are written as Unicode escapes in source rather than as literal characters, so the checker stays authorable under the rule it enforces. Credibility A: read directly. Named descriptively rather than by path, because a tracked artifact must not cite an absolute path on one machine.
- [S12] Direct verification, this session. A ripgrep-backed scan (this session's Grep tool, pattern `[\u{2014}\u{2013}]`) across the full working tree, and a listing of the repo root, confirming both the absence of any `.github/` directory and that exactly one tracked file contains the banned characters. Credibility A (reproducible).
- [S13] `https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/uploading-a-sarif-file-to-github` (fetched this session). Confirms `github/codeql-action/upload-sarif@v4` as GitHub's current documented tag, and that code scanning applies to public repositories without the private/internal Advanced Security requirement. Credibility A.
- [S14] `https://raw.githubusercontent.com/actions/runner-images/main/images/ubuntu/Ubuntu2404-Readme.md` (fetched this session). Confirms ripgrep is not among the tools preinstalled on the GitHub-hosted `ubuntu-latest` runner image. Credibility A.
- [S15] `actions/setup-python` release history (searched this session). Confirms `v6` as the current major-version tag. Credibility B (search-summarized, not a direct fetch of the releases page).

### Unverified Claims

None.

## Open Questions / Decisions

| ID | Question | Status |
|---|---|---|
| OQ-1 | Should G-11 (`plab-guide`'s own manual `grep -P` dash check) migrate to reuse `check-dashes.py`'s engine? | Superseded |
| OQ-2 | Should this spec carry a `spec-dependencies` frontmatter field for the CI-01 to D-11 relationship? | Decided: no |
| OQ-3 | Which `codeql-action/upload-sarif` tag to pin? | Decided: `v3` |
| OQ-4 | Does CI-01 warrant a `CHANGELOG.md [Unreleased]` entry? | Decided: yes, propose and confirm |

**OQ-1.** `skills/plab-guide/references/voice-and-style.md` documents G-11 as a manual check run with `grep -P '[\x{2013}\x{2014}]' <output-file>` [S9]. `CHANGELOG.md` confirms this is "a written-discipline rule verified by grep," not an automated sweep [S10]. GNU `grep -P`'s Unicode handling for `\x{...}` escapes is not guaranteed correct without an explicit UTF-8 mode, which is the same failure shape D-11 already found twice elsewhere [S6]. Fixing G-11 is out of scope for CI-01: it belongs to a different skill's internal, rung-3 convention, not to a repo-wide CI gate, and the instruction governing this spec is to record disagreement rather than silently redesign what exists elsewhere. Recorded here for whoever next touches D-11 or `plab-guide`.

**OQ-1 closed 2026-10-26, Superseded by H-05 (retire dash enforcement).** On 2026-10-17 the maintainer ruled to retire `check-dashes.py` and its CI job and to keep G-11 as it is, so there is no engine left for G-11 to reuse. The ruling is specified in `docs/internal/release-plans/_unassigned/H-05_retire-dash-enforcement/spec.md`.

**OQ-2.** This effort's dispatch instructions suggested using `spec-dependencies` frontmatter to record the CI-01 to D-11 relationship. The conventions this spec must follow list a closed frontmatter schema for `spec.md` (id, title, type, status, created, updated, linked-effort, linked-plan, ac-count, source-count, requires-human-review, target-release, linked-release, priority) with no `spec-dependencies` field, and state plainly: "Do not invent frontmatter fields. The schemas below are closed." Adding the field risks the release gate's parser; the conventions take precedence over the dispatch suggestion, which was itself conditional ("if appropriate"). The relationship is instead recorded in prose, in Purpose and here: CI-01 applies the canary-before-trust, three-state pattern inside CI, and D-11 applies the identical pattern to `skills/plab-wrap-session/SKILL.md`'s own Log Self-Check gates [S5] [S6]. It is a shared principle rather than a dependency: neither effort consumes the other's artifacts, and neither blocks the other.

**OQ-3.** The toolkit's own `action.yml` usage example, verified against the `v1.16.1` tag, pins `github/codeql-action/upload-sarif@v3` [S1]. GitHub's current documentation, fetched this session, shows `@v4` as current [S13]. This plan follows the toolkit's own tested example (`v3`) since it is the maintainer's confirmed working integration point for consuming this specific Action's `sarif-path` output; the toolkit author has demonstrably exercised that exact pairing. Revisit independently of this effort if `v3` is ever deprecated.

**OQ-4.** This repo's own `skills/plab-wrap-session/references/doc-update-rules.md` excludes "CI tweaks" from `CHANGELOG.md` updates. CI-01 is not a tweak to existing CI; it is this repo's first CI. Decision: propose a short `[Unreleased]` entry and confirm before writing it, matching the maintainer's standing per-action-confirmation preference, rather than silently deciding either way. See the implementation plan's Human-facing documentation section.
