---
id: RL-01
title: "Release on merge: a deterministic release pipeline driven by plab-ship"
type: spec
status: draft
created: 2026-11-21
updated: 2026-11-21
linked-effort: "the maintainer's private release-on-merge proposal of 2026-11-13 and its decision walk of 2026-11-20 to 2026-11-21, which decided D1 to D7"
linked-plan: null
linked-release: null
ac-count: 14
source-count: 9
requires-human-review: true
priority: P1
---

# Spec: Release on merge, a deterministic release pipeline driven by plab-ship

## Task Summary

**Status:** draft
**Last updated:** 2026-11-21 by claude (Opus 5.5), under the maintainer's "yes" to writing this spec
**Linked plan:** not yet planned
**Open questions:** 0 (see Open Questions / Decisions)
**Revisions:** 1 (see Revisions)

### Acceptance Criteria Fulfillment

- [ ] **AC-1** - The pipeline acts only in a repository that carries `RELEASING.md` and the release configuration file
- [ ] **AC-2** - The configuration file names the version surfaces, the test command and the plugin flag
- [ ] **AC-3** - A pull request check fails when the version surfaces disagree
- [ ] **AC-4** - A pull request check fails when the bump size does not match the title type
- [ ] **AC-5** - A pull request check fails when a bumped version has no CHANGELOG section
- [ ] **AC-6** - A pull request check fails when a `SKILL.md` changed and the body has no eval result line
- [ ] **AC-7** - No tag is created until the full tests pass on the merged commit
- [ ] **AC-8** - One job creates the tag and the GitHub Release from the CHANGELOG section
- [ ] **AC-9** - A merge with no new version creates no tag, no Release and no repin request
- [ ] **AC-10** - A rerun after a tag without a Release creates the Release and no second tag
- [ ] **AC-11** - A plugin repository sends one repin request per Release; a non-plugin repository sends none
- [ ] **AC-12** - No pipeline file calls a workflow or action from another of the maintainer's repositories
- [ ] **AC-13** - `RELEASING.md` says what happens on merge, how to stop it, and how to undo a release
- [ ] **AC-14** - No text in `AGENTS.md` or `plab-ship`'s `SKILL.md` contradicts the pipeline for an opted-in repository

### Currently In Progress

None.

---

## Purpose

A merged change to this plugin does not reach a session until someone bumps the version, tags, publishes, repins the marketplace and updates the installs by hand, and each of those steps has been missed at least once [S1]. This spec defines a pipeline in which `/plab-ship` stays the maintainer's one command: the agent judges whether a set of changes is ready and gives it a version, and scripts perform the tag, the GitHub Release and the repin request [S2]. The maintainer's words: "I want to empower and generally defer to your best judgment to see through release tag and merge" [S2].

## Scope

### In Scope

- An opt-in marker for a repository: `RELEASING.md` plus one release configuration file.
- Pull request checks: version-surface agreement, bump size against the title type, the CHANGELOG section, and the behaviour-eval result line.
- A post-merge release workflow: the full tests on the merged commit, then the tag and the GitHub Release in one job.
- A repin request sent to the marketplace repository after a Release, for a repository that is a plugin.
- `RELEASING.md` for this repository.
- The rule texts that live in this repository: `AGENTS.md`'s CI clause and batched-release wording, and `plab-ship`'s "no version without the flag" rule.
- `plab-ship`'s release step: the default bump rule in Requirements 9 to 11.

### Non-Goals

- **The marketplace receiver.** The workflow that receives the repin request, validates the pin and commits it lives in `prisant-labs/agent-plugins`, another repository, and gets its own spec there.
- **The solo-repo merge rule and the merge check.** Their amendment (decision D6) lives in the maintainer's private configuration repository. Only the maintainer amends them; this spec names the dependency in Behavior / Examples.
- **Creating the repin token.** The maintainer creates it (decision D2); an agent never creates or handles it.
- **Other plugins.** `nonfiction-studio` and the `product-on-purpose` plugins may copy the pipeline later. Moving it to a shared home is a later decision (decision D7).
- **Running the behaviour evals in CI.** They run locally, by the agent (decision D3).
- **A generated CHANGELOG.** Entries stay hand-written in Keep a Changelog form (decision D5).
- **Installing the new version.** Claude Code picks it up at the next session start; Codex's update path is unverified and out of scope.

## Users / Actors

| Actor | Role | Interaction |
|-------|------|-------------|
| Maintainer | Owner of every rule and every secret | Types `/plab-ship`; creates the repin token; amends the merge rule |
| Shipping agent | Author of each pull request | Decides the bump, writes the version and the CHANGELOG entry, runs the evals, merges |
| Pull request checks | CI gate before merge | Fail the pull request on any rule in AC-3 to AC-6 |
| Release workflow | Automation after merge | Reruns the tests, tags, publishes, sends the repin request |
| Marketplace repository | Receiver of the repin request | Out of scope here; named so AC-11 has a target |

## Requirements

### Opting in

1. A repository opts in to release on merge by carrying `RELEASING.md` and one release configuration file; a repository without both keeps today's manual path [S2].
2. The configuration file lists the repository's version surfaces, its full test command, and whether it is a plugin with a marketplace to repin [S1, S2]. For this repository the surfaces are `library.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `manifest.generated.json`, `CHANGELOG.md` and `docs/status-skills.md`, the files the v0.14.1 release commit changed [S5].

### Before the merge

3. The pull request carries its own release: when the agent decides the change should release, the same pull request bumps every version surface and adds the CHANGELOG section, so a release no longer needs a second `chore(release)` pull request [S1, S4].
4. The agent decides the size, and a script checks it against the pull request title: `fix` is a patch, `feat` is a minor, and a breaking marker is a major, except below 1.0.0, where a breaking change raises the minor number [S2, S7].
5. The CHANGELOG entry is hand-written in plain English under a version heading, in Keep a Changelog form [S2, S8].
6. A pull request that changes any `SKILL.md` carries the result of a local behaviour-eval run in its body, because only a real model session shows whether a skill fires when it should [S1, S2].

### After the merge

7. The release workflow reruns the full test command on the merged commit before it creates anything, so CI and the tests pass twice before a repin [S1].
8. The tag and the GitHub Release are created in the same job, because a tag pushed with the default workflow token starts no other workflow [S1, S6].
9. A merge whose version already has a tag releases nothing, so internal changes can merge and ride in the next release [S2].

### The bump rule

10. By default the agent bumps the version for a change to what users run: a skill's `SKILL.md`, its scripts, its references, or `lib/` [S2].
11. By default the agent does not bump the version for a change to internal material only: CI, internal documents, release plans or tests [S2].
12. The agent may hold a bump back to group several pull requests into one release, and says so in `plab-ship`'s report [S2].

### Self-containment and records

13. Every pipeline file lives in this repository and uses only GitHub's own Actions features and the `gh` command; no workflow calls into another of the maintainer's repositories [S2].
14. `RELEASING.md` tells a reader what a merge does, where to stop the pipeline, and that the undo for a bad release is a new patch release, because a published version cannot be withdrawn by deleting a tag [S1, S9].
15. The rules written in this repository agree with the pipeline: `AGENTS.md`'s "CI reports; it never fixes, bumps, or tags" and `plab-ship`'s "no version without the flag" gain an exception for an opted-in repository [S1, S3, S4].

## Acceptance Criteria

AC-1: In a repository without both `RELEASING.md` and the release configuration file, the pull request checks and the release workflow exit successfully without checking or creating anything. [S2]

AC-2: The release configuration file names the version surfaces, the full test command, and a plugin flag with its marketplace repository, and the pull request check fails when any of the three is missing. [S1, S2]

AC-3: A pull request check fails, naming the file, when any version surface listed in the configuration disagrees with `library.json`'s version. [S1, S5]

AC-4: A pull request check fails when the version is above the latest version tag and the size of the bump does not match the pull request title's conventional type. [S2, S7]
  Given: the latest version tag is `v0.14.1` and the title starts `fix(plab-ship):`
  When: the pull request sets the version to `0.15.0`
  Then: the check fails and names the expected version, `0.14.2`

AC-5: A pull request check fails when the version is above the latest version tag and `CHANGELOG.md` has no section headed with that version. [S1, S8]

AC-6: A pull request check fails when the pull request changes a `SKILL.md` and its body carries no behaviour-eval result line. [S2]

AC-7: After a merge to `main` whose version has no tag, the release workflow creates no tag when the full test command exits non-zero on the merged commit. [S1]

AC-8: When the tests pass, one job creates the version tag and a GitHub Release whose notes are that version's CHANGELOG section. [S1, S5, S6]

AC-9: After a merge whose version already has a tag, the release workflow creates no tag, no Release and no repin request. [S2]

AC-10: Rerunning the release workflow on a merged commit whose tag exists but whose Release does not creates the Release and pushes no second tag. [model-inference]

AC-11: After a Release in a repository whose configuration marks it a plugin, the workflow sends exactly one repin request to the named marketplace repository, and a repository not marked a plugin sends none. [S2]

AC-12: No workflow file added by this effort contains a `uses:` line that names a repository owned by `prisant-labs`, `product-on-purpose` or `github-jprisant`. [S2]

AC-13: `RELEASING.md` contains a section on what a merge does, a section on how to stop the pipeline, and a section on undoing a bad release with a new patch release. [S1, S9]

AC-14: After this effort, `AGENTS.md` and `skills/plab-ship/SKILL.md` contain no sentence that forbids a version, a tag or a release in an opted-in repository. [S1, S3, S4]

## Behavior / Examples

### Example 1: a skill fix that releases (grounds AC-4, AC-7, AC-8, AC-11)

The agent ships a fix to `skills/plab-ship/scripts/derive-ship-facts.py`. Under Requirement 10 the change is one users run, so the agent bumps 0.14.1 to 0.14.2 in every surface and writes a CHANGELOG section in the same pull request, titled `fix(plab-ship): ...`. The pull request checks pass and the agent merges. The release workflow reruns the tests on the merge commit, creates `v0.14.2` and its Release in one job, and sends one repin request to `prisant-labs/agent-plugins`. The maintainer typed only `/plab-ship`.

### Example 2: an internal change that does not release (grounds AC-9)

The agent ships an edit to a release plan under `docs/internal/`. Under Requirement 11 there is no bump. The merge lands, the release workflow finds that `v0.14.2` already exists, and it does nothing. The change goes out with the next release that carries a bump.

### Example 3: a bump that does not match its title (grounds AC-4)

A pull request titled `fix: ...` sets the version to 0.15.0. The check fails and names 0.14.2 as the expected version. The agent either changes the bump or retitles the pull request `feat: ...` if the change adds something.

### Rollout dependency on the merge rule

The merge check asks the maintainer whenever a workflow that runs on a push to the base branch contains a publish step such as `gh release create` [S1]. Once AC-8's workflow exists, every pull request in this repository would end in "ask JP" until the maintainer amends the solo-repo merge rule and its check under decision D6 [S2]. The pull request that adds the release workflow should therefore merge after that amendment, or by the maintainer's own hand.

## Non-Functional Requirements

| Category | Requirement | Source |
|----------|-------------|--------|
| Security | No workflow log prints the repin token, and the token is scoped to the marketplace repository with contents write only | [S2] |
| Reliability | Two release workflows never run at once for the same repository, so two quick merges cannot race on one tag | [model-inference] |
| Cost | No pull request check or release workflow calls a paid model API | [S1, S2] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-11-21 | claude (Opus 5.5) | added | Initial draft from the release-on-merge proposal and its decision walk |

## Sources & Evidence

The proposal and the walk are private documents, so their substance is summarized here.

- **[S1]** The maintainer's release-on-merge proposal, 2026-11-13 (private). It records the problem (nineteen merged pull requests sat unreleased before v0.14.0; thirteen tags sat without Releases until 2026-09-14), the five jobs to be done, the default-token constraint, the merge check's `release` rule, the five written rules the pipeline would overturn, and approach C, the deterministic pipeline - class A
- **[S2]** The maintainer's decision walk, 2026-11-20 to 2026-11-21 (private). D1 C (a deterministic pipeline with `/plab-ship` as the one command; "I wasn't saying every merge needs to release"; "defer to your best judgment to see through release tag and merge"); D2 A (a fine-grained token on the marketplace repository); D3 A (local evals with a pull request check); D4 A (the author picks the size, CI checks it); D5 A (hand-written CHANGELOG); D6 A (amend the rules for opted-in repositories only); D7 self-contained ("Powertools should be self contained ... best in Class, best practice deterministic solutions") - class A
- **[S3]** `AGENTS.md`, the Build and validate section: "CI reports; it never fixes, bumps, or tags", the `publish-release.yml` paragraph, and `skill-drift-check.py`'s batched-release behaviour - class A
- **[S4]** `skills/plab-ship/SKILL.md`, step 7 ("Release, only with `--release`") and the "The flag covers one run" constraint - class A
- **[S5]** `.github/workflows/publish-release.yml` and the v0.14.1 release commit `c48f301`, which changed the version surfaces named in Requirement 2 - class A
- **[S6]** GitHub Docs, "Automatic token authentication": events triggered by `GITHUB_TOKEN` do not create new workflow runs - `https://docs.github.com/en/actions/security-guides/automatic-token-authentication` - class A
- **[S7]** Semantic Versioning 2.0.0 - `https://semver.org/spec/v2.0.0.html` - class A
- **[S8]** Keep a Changelog 1.1.0 - `https://keepachangelog.com/en/1.1.0/` - class A
- **[S9]** `skills/plab-ship/references/documentation-standard.md`, the Human / Trust cell (upgrade, migration and rollback) - class A

### Unverified Claims

- "Rerunning the release workflow on a merged commit whose tag exists but whose Release does not creates the Release and pushes no second tag" - appears in AC-10
- "Two release workflows never run at once for the same repository, so two quick merges cannot race on one tag" - appears in Non-Functional Requirements

### Gaps

- Whether a fine-grained token with contents read and write is enough to send a repository dispatch to the marketplace. Medium-high confidence from GitHub's permission model; the implementation plan should confirm it against current GitHub documentation.
- Whether Codex updates a plugin on its own after a repin. Not verified.
- The exact names of the configuration file and the repin secret. The implementation plan fixes them; `MARKETPLACE_REPIN_TOKEN` is a placeholder.

## Open Questions / Decisions

None at this time. Decisions D1 to D7 were made in the maintainer's decision walk of 2026-11-20 to 2026-11-21 [S2], and [ADR-3 (release on merge)](../../../decisions/0003-release-on-merge.md) records D1.
