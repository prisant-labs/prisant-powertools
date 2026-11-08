---
id: RM-01
title: "Implementation plan: plab-org-profile-readme"
type: implementation-plan
status: draft
created: 2026-11-07
updated: 2026-11-08
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 7
---

# Implementation plan: plab-org-profile-readme

Steps use checkbox syntax and phases run in order. A phase is done when every step is ticked and its Verification command has been run and its output quoted.

**Goal:** `/plab-org-profile-readme <org>` reads an organization's public repositories in one script call, keeps the organization's profile README to a standard recorded in one file, and opens or updates one pull request in the organization's `.github` repository that a self-testing checker passes. `--setup` establishes or revises the standard. A quoted instruction changes the page beyond what the facts require.

**Spec:** `spec.md`. Every decision except D2 is answered. D2 does not block the build, because non-goal 4 and the Safety requirement already build its option A: the skill never merges.

**Target version:** `plab-org-profile-readme` 1.0.0, a new skill. The plugin release that ships it also carries `plab-usage-audit` 1.1.1 and `plab-project-pulse` 1.1.1, which merged in pull request 76 and are not yet released.

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) in any file this plan touches. One paragraph per line.
- Every script is stdlib-only Python and follows the repository's exit contract: 0 clean, 1 a rule failed, 2 broken. Exit 2 is never read as clean.
- Every script that calls GitHub accepts `--fixture <dir>`, which replaces each `gh` call with a recorded JSON response, so tests and CI never touch the network.
- No script, reference or sample names a real owner or repository. Samples use `example-org` and invented repository names (AC-4).
- The facts never contain a private repository's name. They carry a SHA-256 digest of each private name, lowercased, so the checker can still reject a private name (AC-3, AC-7).

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | The facts script returns an organization's facts in one call | AC-3, AC-4, AC-15 | agent | Built 2026-11-08 |
| P2 | The standard file, the three built-in standards and the scaffold exist | AC-16, AC-17 (part), AC-18 | agent | Built 2026-11-08 |
| P3 | The checker enforces facts and standards and proves every rule can fail | AC-5 to AC-8, AC-10, AC-12 (part), AC-19, AC-20 (part) | agent | Built 2026-11-08 |
| P4 | The skill, its references, its history and its eval case exist | AC-1, AC-11, AC-17 (part), AC-20 (part) | agent | Built 2026-11-08; the eval case has not run |
| P5 | The plugin registers the skill and CI runs its checks | AC-12 (CI) | agent | Built 2026-11-08; CI runs on the pull request |
| P6 | A live run on one of the maintainer's organizations passes the checker | AC-13 | agent, maintainer | Not started |
| P7 | The release ships, and the two weekly routines are retired | N/A (release, and D3's follow-up) | agent, maintainer | Not started |

AC-2, AC-9 and AC-14 are superseded in the spec and are not built.

**Departures from this plan, 2026-11-08.** The build follows the phases with five departures. The standard gained `include` and `skip_releases`, and R6 became a note, under the spec's D7, after a read-only check of a real page. The facts fixtures are built in a temporary folder by `test-profile-scripts.py` from recorded responses in the test itself, so `scripts/fixtures/` holds only `forbidden-names.txt`. The facts name public forks and archived repositories, because a standard can include a fork by name and both are public. The usage README is `docs/skills/plab-org-profile-readme/README.md`, the plugin's convention for every skill, and the skill folder has no README of its own. The facts reference is `references/facts-format.md`, beside the standard format.

---

## Phase 1: The facts script returns an organization's facts in one call

**Goal:** one call returns everything a run needs to know about an organization, and nothing that names a private repository.

**Files:**
- Create `skills/plab-org-profile-readme/scripts/derive-profile-facts.py`
- Create `skills/plab-org-profile-readme/scripts/test-profile-scripts.py`
- Create `skills/plab-org-profile-readme/scripts/fixtures/` with one folder per fixture organization

**Fulfills:** AC-3, AC-4, AC-15

**Steps:**
- [ ] `derive-profile-facts.py <org> [--fixture <dir>] [--json]`. Confirm the owner type with `gh api users/<org>`, whose `type` field is `Organization` or `User`. A user exits 2 with "plab-org-profile-readme covers organization profile pages; <org> is a user account".
- [ ] List repositories with `gh api orgs/<org>/repos --paginate`. Covered means public, not a fork, not archived, and not `.github`. Private repositories contribute only a `private_digests` list of SHA-256 hex digests of their lowercased names. Forks and archived repositories are counted, not named, because the page never shows them.
- [ ] For each covered repository, record its name, description, topics, default branch, `pushed_at`, latest release tag and date from `gh api repos/<org>/<repo>/releases/latest` (absent when there is none), and the full tag list for release-link checks.
- [ ] Read `profile/README.md` and `profile/standard.json` from `<org>/.github` through the contents API. Report each as `present` or `missing`. A missing page exits 0 (AC-15). A missing `.github` repository is also `missing`, not an error.
- [ ] Find an open pull request from an earlier run: an open pull request in `<org>/.github` whose head branch starts with `plab-org-profile-readme/`. Report its number and branch, or none.
- [ ] Fixtures: an organization with a public repository, a fork, an archived repository and a private repository (AC-3); a user account (AC-15); an organization with no `.github` repository (AC-15); an organization with no standard (AC-4's no-settings case).
- [ ] `test-profile-scripts.py` asserts each case, including that no private name appears anywhere in the JSON. It also holds AC-4's name test: it reads a list of real owner and repository names from `fixtures/forbidden-names.txt` and fails if any appears in `SKILL.md`, `references/` or `scripts/` outside `fixtures/`. A canary proves the name test fails when a forbidden name is planted in a temporary copy.

**Verification:** `python skills/plab-org-profile-readme/scripts/test-profile-scripts.py` reports every case passing, and the canary line reads as proved.

---

## Phase 2: The standard file, the three built-in standards and the scaffold exist

**Goal:** a standard can be written from a short set of answers, and a page skeleton can be built from a standard and the facts.

**Files:**
- Create `skills/plab-org-profile-readme/references/standard-format.md`
- Create `skills/plab-org-profile-readme/references/standards/catalog.md`, `compact.md`, `showcase.md`
- Create `skills/plab-org-profile-readme/examples/standards/catalog/standard.json` and `README.md`, and the same pair for `compact` and `showcase`
- Create `skills/plab-org-profile-readme/scripts/write-standard.py`
- Create `skills/plab-org-profile-readme/scripts/scaffold-page.py`

**Fulfills:** AC-16, AC-17 (part), AC-18

**Steps:**
- [ ] `standard-format.md` defines `profile/standard.json`, which lives beside the page in the `.github` repository. GitHub renders only `profile/README.md`, so the file does not appear on the organization page, though anyone browsing the `.github` repository can read it. Its fields: `base` (`catalog`, `compact`, `showcase`, `adopted` or `custom`), `sections` (ordered list of `{id, heading, kind}`), `options` (the seven of the spec's requirement 8: `recent_changes` as `false` or a count, `badges` as `false` or a list of kinds, `status_labels` as `false` or a vocabulary list, `grouping` as `none` or `category`, `featured` as a list of repository names, `order` as `category`, `latest_release` or `alphabetical`, `shared_text` as a list of `{id, text}`), `categories` (ordered names, each with its repositories), and `exclude` (list of `{repo, reason}`). JSON keeps the scripts stdlib-only.
- [ ] Each standard reference names its sections, which options it uses, and its defaults. Catalog is the maintainer's current organization format; distil it from the two routine prompts named as the spec's S2, then replace every real name. Compact and Showcase follow the spec's requirement 7.
- [ ] Each sample pair is a `standard.json` and a `README.md` for `example-org`, written so the Phase 3 checker passes it against a matching fixture.
- [ ] `write-standard.py --base <base> --answers <answers.json> --out <path>` validates the answers against `standard-format.md`'s rules, fills defaults from the base, and writes the standard. For `adopted` it takes `--from-page <README.md>` and records the page's headings as sections in order; the agent confirms the result with the maintainer before it is used.
- [ ] `scaffold-page.py --standard <path> --facts <path> --out <path>` writes a page with every section, heading, badge row and version line filled from the facts, and marks each prose slot `<!-- describe: <repo> -->` for the agent to replace.
- [ ] Tests in `test-profile-scripts.py`: for each of the three paths (a built-in base, `adopted` from a fixture page, and `custom`), fixture answers give a standard, and the scaffold from that standard passes the checker once the prose markers are replaced by fixed text (AC-17). A standard with no page gives a page that passes (AC-18).

**Verification:** `python skills/plab-org-profile-readme/scripts/test-profile-scripts.py` reports the Phase 2 cases passing.

---

## Phase 3: The checker enforces facts and standards and proves every rule can fail

**Goal:** `profile-check.py` rejects a page or a pull request body that breaks a fact or its standard, and its self-test proves each rule can fail.

**Files:**
- Create `skills/plab-org-profile-readme/scripts/profile-check.py`
- Create `skills/plab-org-profile-readme/examples/sample-run/` holding `facts.json`, `standard.json`, `README.md` and `pr-body.md`

**Fulfills:** AC-5 to AC-8, AC-10, AC-12 (part), AC-19, AC-20 (part)

**Steps:**
- [ ] `profile-check.py --page <README.md> --facts <facts.json> [--standard <standard.json>] [--pr-body <file>] [--instructions-given] [--self-test]`. It reads files only, never the network.
- [ ] Factual rules, run with or without a standard: R1 every covered repository is listed or excluded with a reason (AC-5); R2 every listed repository is covered, so a private, archived or missing one is named (AC-5); R3 a stated version matches the latest release (AC-6); R4 a release link names a tag in the repository's tag list (AC-6); R5 a badge URL names this organization and a listed repository (AC-6); R6 a badge that reads a list by position, such as `$.plugins[1]`, is a finding (AC-6); R7 no word on the page or in the pull request body hashes to a private digest (AC-7).
- [ ] Standard rules, run only with a standard: R8 every section heading is present and in order, and a covered repository's heading is not lost (AC-8, AC-19); R9 each shared text passage is identical (AC-8); R10 no badge when badges are off, and only allowed kinds when on (AC-19); R11 no recent-changes list when off, and none longer than the count when on (AC-19); R12 status labels come from the vocabulary (AC-19); R13 featured repositories come first (AC-19).
- [ ] Pull request rule: R14 with `--instructions-given`, the body has both headings from `references/pr-body.md`, "From the repositories" and "From your instructions" (AC-20).
- [ ] Without a standard, the output lists R8 to R13 as skipped by name and suggests `--setup` (AC-10).
- [ ] `--self-test` runs every rule against `examples/sample-run/`, expects clean, then applies one mutation per rule and expects that rule alone to fire. A mutation that does not fire exits 2 (AC-12).

**Verification:** `python skills/plab-org-profile-readme/scripts/profile-check.py --self-test` prints `CLEAN: canary proved` with fourteen rules named.

---

## Phase 4: The skill, its references, its history and its eval case exist

**Goal:** `SKILL.md` runs the workflow in all three modes, and the skill is manual-only in both harnesses.

**Files:**
- Create `skills/plab-org-profile-readme/SKILL.md`, `HISTORY.md`, `README.md` (the usage README), `agents/openai.yaml`
- Create `skills/plab-org-profile-readme/references/pr-body.md` and `references/setup-interview.md`
- Create `evals/org-profile-readme-manual-no-fire/prompt.md` and `evals/org-profile-readme-manual-no-fire/graders/skill-not-fired.md`

**Fulfills:** AC-1, AC-11, AC-17 (part), AC-20 (part)

**Steps:**
- [ ] Frontmatter: `name: plab-org-profile-readme`, `disable-model-invocation: true`, `version: "1.0.0"`, an `argument-hint` of `<org> [--setup] ["<instructions>"]`, and a description of at most 600 characters. `agents/openai.yaml` carries `policy.allow_implicit_invocation: false`.
- [ ] Refresh workflow: run the facts script and stop on exit 2. With no standard, run the factual checks only and suggest `--setup`. With a standard and no page, scaffold the page. Otherwise edit the page to the facts and the standard. Run the checker until clean. Then branch, commit, and open or update the pull request.
- [ ] The three branch instructions, each a sentence a test can find: never commit to the default branch; when the facts report an open pull request from an earlier run, update that branch and rewrite its body instead of opening another; when the checked page is identical to the current one, make no branch and say the page is current. `test-profile-scripts.py` fails when any of the three is removed (AC-11).
- [ ] Instruction runs: apply the quoted instruction, refuse any instruction that would name a private repository or bypass the branch rules, and write the pull request body with the two headings of `references/pr-body.md` (AC-20).
- [ ] `references/setup-interview.md` lists what `--setup` must establish: the path (built-in, adopted or custom), the base, each option's value, the categories, the exclusions with reasons, the featured repositories and any shared text. It says what to establish, not how to ask, because Claude Code and Codex ask differently. An existing standard supplies the defaults. The interview ends by calling `write-standard.py`, then the refresh workflow on a branch (AC-17).
- [ ] `HISTORY.md` records 1.0.0 under RM-01. The usage README carries `**Version:** 1.0.0` and the three modes with one example each.
- [ ] The eval case asks the agent to update this repository's own `README.md` and asserts that the skill is not invoked (AC-1).

**Verification:** `node E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/check.mjs .` reports no new failure for the skill, and `python scripts/codex-invocation-check.py` is clean.

---

## Phase 5: The plugin registers the skill and CI runs its checks

**Goal:** the skill ships with the plugin, and its scripts gate every pull request.

**Files:**
- Modify `library.json`, then regenerate `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json`
- Modify `AGENTS.md`, `README.md`, `docs/status-skills.md` if it lists skills, `CHANGELOG.md`, `.github/workflows/gate.yml`

**Fulfills:** AC-12 (CI)

**Steps:**
- [ ] Add the component to `library.json` and regenerate the manifests with `node E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/generators/gen-manifest.mjs . --write --target=all`.
- [ ] `AGENTS.md` line 7: "Fourteen general-purpose agent skills" becomes "Fifteen general-purpose agent skills", and the sentence's list gains "keeping an organization's profile README to a standard". Line 9: "Seven of the fourteen ship with" becomes "Eight of the fifteen ship with", and "the same seven also carry" becomes "the same eight also carry". Add a gating paragraph after `plab-ship`'s: the skill writes to a public repository, and "update the README" is an ordinary request. Add a `### plab-org-profile-readme` entry after `plab-ship`'s. Re-verify the line numbers first, because another change may have moved them.
- [ ] `README.md` line 3: "Fourteen agent skills" becomes "Fifteen agent skills", and the skill joins the list. `CHANGELOG.md`: an Unreleased entry.
- [ ] `gate.yml`: after the plab-ship steps, a comment naming RM-01, then `python3 skills/plab-org-profile-readme/scripts/profile-check.py --self-test` and `python3 skills/plab-org-profile-readme/scripts/test-profile-scripts.py`, each with `if: always()`, in the existing job, because branch protection requires checks by job name.

**Verification:** every gate in the Build and validate section of `AGENTS.md` passes locally: `check-dashes`, `frontmatter-check`, `doc-lifecycle-check`, `gen-release-index --check`, `version-parity-check`, `skill-drift-check`, `codex-invocation-check` and the toolkit `check.mjs`.

---

## Phase 6: A live run on one of the maintainer's organizations passes the checker

**Goal:** the skill, loaded from this checkout through a junction in `.claude/skills/`, sets up and refreshes one real organization page.

**Files:** none in this repository. The run writes `profile/standard.json` and `profile/README.md` on a branch of the chosen organization's `.github` repository, and opens a pull request there.

**Fulfills:** AC-13

**Steps:**
- [ ] Ask the maintainer which organization, and for a go-ahead to open a pull request in its public `.github` repository. Prisant Labs is the natural first choice, because its page is the stalest.
- [ ] Ask the maintainer what to do with the routine's open pull request in that repository first (`prisant-labs/.github` #4 or `product-on-purpose/.github` #6). The skill does not recognise it as its own, because its branch does not start with `plab-org-profile-readme/`, so it would otherwise open a second pull request beside it.
- [ ] Run `/plab-org-profile-readme <org> --setup`, adopting the existing page or choosing Catalog. From Git Bash, set `MSYS_NO_PATHCONV=1`, or the slash command is rewritten into a Windows path.
- [ ] Run `profile-check.py` on the result with the run's facts and standard.

**Verification:** the checker's output, quoted, and the pull request's URL.

---

## Phase 7: The release ships, and the two weekly routines are retired

**Goal:** the skill is released and installable, and the two routines that copied its format are gone.

**Files:** the release bookkeeping that `/plab-ship --release` performs. Nothing else in this repository.

**Fulfills:** N/A (release, and D3's follow-up)

**Steps:**
- [ ] Run `/plab-ship --release`. It decides the version from the changes; a new skill is a minor release, so expect v0.14.0. The release also ships `plab-usage-audit` 1.1.1 and `plab-project-pulse` 1.1.1.
- [ ] Repin `prisant-powertools` in the `agent-plugins` marketplace, which the maintainer has pre-approved after a release.
- [ ] D3 is decided as B: retire the two routines once the skill's first live pull request has merged. They are `trig_01K4D4BKzr14s7c777AxuncP` (Prisant Labs, Fridays 22:00 UTC) and `trig_019yFBnuEttfGyeoD8U2YqpV` (Product on Purpose, Fridays 23:00 UTC). Disable each rather than delete it, and tell the maintainer, who can delete them later. Their prompts stay in each profile repository's `_local/readme/` folder as the record of the old format.
- [ ] Tell the maintainer to update both installs. Merged is not installed.

**Verification:** `gh release view v0.14.0 -R prisant-labs/prisant-powertools` shows the release, and the routine list shows both routines disabled.

---

## CI and Documentation Coverage

**CI.** `.github/workflows/gate.yml` gains two steps in the existing job: `profile-check.py --self-test` and `test-profile-scripts.py`. They join the existing job because branch protection requires checks by job name.

**Documentation.** `CHANGELOG.md` under Unreleased, the skill's `HISTORY.md` and usage README, the root `README.md`, `AGENTS.md`, and `docs/status-skills.md` if it lists skills.

## Rollback

Delete `skills/plab-org-profile-readme/`, `evals/org-profile-readme-manual-no-fire/` and the two `gate.yml` steps. Remove the component from `library.json` and regenerate the manifests. Restore `AGENTS.md`'s "Fourteen general-purpose agent skills", "Seven of the fourteen ship with" and "the same seven also carry", remove its gating paragraph and skill entry, and restore `README.md`'s "Fourteen agent skills". There is no schema change and no data migration. A live run leaves `profile/standard.json` and a pull request in an organization's `.github` repository; close the pull request and delete the branch, which removes both. If Phase 7 disabled the routines, re-enable them. Do not roll back a released version; ship a patch that removes the skill instead.
