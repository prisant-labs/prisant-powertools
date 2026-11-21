---
id: RL-01
title: "Release on merge: a deterministic release pipeline driven by plab-ship"
type: spec
status: draft
created: 2026-11-21
updated: 2026-11-21
linked-effort: "the maintainer's private release-on-merge proposal of 2026-11-13 and its decision walk of 2026-11-20 to 2026-11-21, which decided D1 to D7"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 17
source-count: 10
requires-human-review: true
priority: P1
---

# Spec: Release on merge, a deterministic release pipeline driven by plab-ship

## Task Summary

**Status:** draft
**Last updated:** 2026-11-21 by claude (Opus 5.5), when the implementation plan was written
**Linked plan:** [implementation-plan.md](implementation-plan.md), eight phases, not started
**Open questions:** 0 (see Open Questions / Decisions)
**Revisions:** 3 (see Revisions)

### Acceptance Criteria Fulfillment

- [ ] **AC-1** - The pipeline acts only in a repository that carries `RELEASING.md` and the release configuration file
- [ ] **AC-2** - The configuration file names the version surfaces, the test command and the plugin flag
- [ ] **AC-3** - A pull request that bumps the version fails when any listed surface still carries another version
- [ ] **AC-4** - A pull request check fails when the bump size does not match the largest change type since the last tag
- [ ] **AC-5** - A pull request check fails when a bumped version has no CHANGELOG section
- [ ] **AC-6** - A pull request check fails when a skill's description or body changed and the eval result line is missing
- [ ] **AC-7** - No tag is created until the full tests pass on the merged commit
- [ ] **AC-8** - One job creates the tag and the GitHub Release from the CHANGELOG section
- [ ] **AC-9** - A merge whose version already has its tag and Release creates nothing
- [ ] **AC-10** - A rerun after a tag without a Release creates the Release and no second tag
- [ ] **AC-11** - A plugin repository sends one repin request per Release; a non-plugin repository sends none
- [ ] **AC-12** - Every action the pipeline's workflow jobs use is owned by GitHub's `actions` organization
- [ ] **AC-13** - `RELEASING.md` says what happens on merge, how to stop it, and how to undo a release
- [ ] **AC-14** - No text in `AGENTS.md` or `plab-ship`'s `SKILL.md` forbids a version, tag or release in an opted-in repository
- [ ] **AC-15** - `plab-ship`'s `SKILL.md` states the default bump rule
- [ ] **AC-16** - `plab-ship`'s `SKILL.md` says it pushes no tag in an opted-in repository
- [ ] **AC-17** - A pull request that bumps the version fails while any `HISTORY.md` row still reads `Unreleased`

### Currently In Progress

None.

---

## Purpose

A merged change to this plugin does not reach a session until someone bumps the version, tags, publishes, repins the marketplace and updates the installs by hand, and each of those steps has been missed at least once [S1]. This spec defines a pipeline in which `/plab-ship` stays the maintainer's one command: the agent judges whether a set of changes is ready and gives it a version, and scripts perform the tag, the GitHub Release and the repin request [S2]. The maintainer's words: "I want to empower and generally defer to your best judgment to see through release tag and merge" [S2].

## Scope

### In Scope

- An opt-in marker for a repository: `RELEASING.md` plus one release configuration file.
- Pull request checks: version-surface agreement, bump size, the CHANGELOG section, the behaviour-eval result line, and `HISTORY.md` release cells.
- A post-merge release workflow: the full tests on the merged commit, then the tag and the GitHub Release in one job.
- A repin request sent to the marketplace repository after a Release, for a repository that is a plugin.
- `RELEASING.md` for this repository.
- The rule texts that live in this repository: `AGENTS.md`'s CI clause and batched-release wording, and `plab-ship`'s "no version without the flag" rule.
- `plab-ship`'s release step: the default bump rule in Requirements 11 to 13, and which component tags (Requirement 10).
- The batched-release mechanisms: `skill-drift-check.py`'s advisory and enforced modes, and the `Unreleased` cells in each skill's `HISTORY.md` (Requirement 7).

### Non-Goals

- **The marketplace receiver.** The workflow that receives the repin request, validates the pin and commits it lives in `prisant-labs/agent-plugins`, another repository, and gets its own spec there.
- **The solo-repo merge rule and the merge check.** Their amendment (decision D6) lives in the maintainer's private configuration repository. Only the maintainer amends them; this spec names the dependency in Behavior / Examples.
- **Creating the repin token.** The maintainer creates it (decision D2); an agent never creates or handles it.
- **The existing conformance step.** `gate.yml` already uses `product-on-purpose/agent-skills-toolkit` to grade the skills. That step is a test-time dependency, not part of the release pipeline, and this effort leaves it alone.
- **Other plugins.** `nonfiction-studio` and the `product-on-purpose` plugins may copy the pipeline later. Moving it to a shared home is a later decision (decision D7).
- **Running the behaviour evals in CI.** They run locally, by the agent (decision D3).
- **A generated CHANGELOG.** Entries stay hand-written in Keep a Changelog form (decision D5).
- **Installing the new version.** Claude Code picks it up at the next session start; Codex's update path is unverified and out of scope.

## Users / Actors

| Actor | Role | Interaction |
|-------|------|-------------|
| Maintainer | Owner of every rule and every secret | Types `/plab-ship`; creates the repin token; amends the merge rule |
| Shipping agent | Author of each pull request | Decides the bump, writes the version and the CHANGELOG entry, runs the evals, merges |
| Pull request checks | CI gate before merge | Fail the pull request on any rule in AC-2 to AC-6 and AC-17 |
| Release workflow | Automation after merge | Reruns the tests, tags, publishes, sends the repin request |
| Marketplace repository | Receiver of the repin request | Out of scope here; named so AC-11 has a target |

## Requirements

### Opting in

1. A repository opts in to release on merge by carrying `RELEASING.md` and one release configuration file; a repository without both keeps today's manual path [S2].
2. The configuration file lists the repository's version surfaces, its full test command, and whether it is a plugin with a marketplace to repin [S1, S2]. For this repository the surfaces are `library.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `manifest.generated.json`, the `Plugin version` line of `docs/status-skills.md`, the version heading in `CHANGELOG.md`, and the Release cell of each changed skill's `HISTORY.md` row, which are the places the v0.14.1 release commit changed [S5]. `scripts/version-parity-check.py` already compares several of these claims with `library.json` [S10], so the surface check extends that gate rather than adding a second one [model-inference].

### Before the merge

3. The pull request carries its own release: when the agent decides the change should release, the same pull request bumps every version surface and adds the CHANGELOG section, so a release no longer needs a second `chore(release)` pull request [S1, S4].
4. The agent decides the size, and a script checks it against the largest conventional change type among the pull request titles merged since the latest version tag, this one included: `fix` is a patch, `feat` is a minor, and a breaking marker is a major, except below 1.0.0, where a breaking change raises the minor number [S2, S7]. Checking against everything since the tag, not only this title, lets a held-back `feat` release through a later `fix` pull request (Requirement 13) [model-inference].
5. A title type that carries no size, such as `docs`, `chore`, `refactor`, `test` or `ci`, adds nothing to the expected size; when every type since the tag is of that kind and the agent bumps, the expected size is a patch [model-inference].
6. The CHANGELOG entry is hand-written in plain English under a version heading, in Keep a Changelog form [S2, S8].
7. The batched-release mechanisms stay, with one rule added. A pull request that does not bump leaves its skill rows reading `Unreleased`, and `skill-drift-check.py` stays advisory for it. A pull request that bumps fills every `Unreleased` cell with the new version, and `skill-drift-check.py` is then enforced, as it already is whenever `library.json`'s version moves [S1, S3].
8. A pull request that changes a skill's `description` or the body of its `SKILL.md` carries the result of a local behaviour-eval run in its body. A change to `metadata.version` alone does not need one, because every script fix bumps that field and the evals test triggering, not scripts [S1, S2].

### After the merge

9. The release workflow reruns the full test command on the merged commit before it creates anything, so CI and the tests pass twice before a repin [S1]. The tag and the GitHub Release are created in the same job, because a tag pushed with the default workflow token starts no other workflow [S1, S6]. A merge whose version already has its tag and Release releases nothing [S2].
10. In an opted-in repository the release workflow is the only component that creates a version tag or a GitHub Release: `plab-ship`'s release step pushes no tag, and `publish-release.yml` remains only for a tag the maintainer pushes by hand [S4, S5] [model-inference].

### The bump rule

11. By default the agent bumps the version for a change to what users run: a skill's `SKILL.md`, its scripts, its references, or `lib/` [S2].
12. By default the agent does not bump the version for a change to internal material only: CI, internal documents, release plans or tests [S2].
13. The agent may hold a bump back to group several pull requests into one release, and says so in `plab-ship`'s report [S2].

### Self-containment and records

14. Every pipeline file lives in this repository and uses only actions owned by GitHub's `actions` organization and the `gh` command; no workflow job the pipeline adds calls into another repository [S2].
15. `RELEASING.md` tells a reader what a merge does, where to stop the pipeline, and that the undo for a bad release is a new patch release, because a published version cannot be withdrawn by deleting a tag [S1, S9].
16. The rules written in this repository agree with the pipeline: `AGENTS.md`'s "CI reports; it never fixes, bumps, or tags" and `plab-ship`'s "no version without the flag" gain an exception for an opted-in repository [S1, S3, S4].

## Acceptance Criteria

AC-1: In a repository without both `RELEASING.md` and the release configuration file, the pull request checks and the release workflow exit successfully without checking or creating anything. [S2]

AC-2: The release configuration file names the version surfaces, the full test command, and a plugin flag with its marketplace repository, and the pull request check fails when any of the three is missing. [S1, S2]

AC-3: A pull request that raises `library.json`'s version fails a check, naming the file, when any surface listed in the configuration still carries a different version. [S1, S5, S10]

AC-4: A pull request check fails when the version is above the latest version tag and the size of the bump does not match the largest conventional change type among the pull request titles merged since that tag, this one included. [S2, S7]
  Given: the latest version tag is `v0.14.1`, and the only titles since it are this one, `fix(plab-ship): ...`
  When: the pull request sets the version to `0.15.0`
  Then: the check fails and names the expected version, `0.14.2`

AC-5: A pull request check fails when the version is above the latest version tag and `CHANGELOG.md` has no section headed with that version. [S1, S8]

AC-6: A pull request check fails when the pull request changes a skill's `description` or the body of its `SKILL.md` and its body carries no behaviour-eval result line; a change to `metadata.version` alone does not trigger it. [S1, S2]

AC-7: After a merge to `main` whose version has no tag, the release workflow creates no tag when the full test command exits non-zero on the merged commit. [S1]

AC-8: When the tests pass, one job creates the version tag and a GitHub Release whose notes are that version's CHANGELOG section. [S1, S5, S6]

AC-9: After a merge whose version already has both its tag and its GitHub Release, the release workflow creates no tag, no Release and no repin request. [S2]

AC-10: Rerunning the release workflow on a merged commit whose tag exists but whose Release does not creates the Release and pushes no second tag. [model-inference]

AC-11: After a Release in a repository whose configuration marks it a plugin, the workflow sends exactly one repin request to the named marketplace repository, and a repository not marked a plugin sends none. [S2]

AC-12: Every `uses:` line in a workflow job that this effort adds or changes names an action owned by the `actions` organization. [S2]

AC-13: `RELEASING.md` contains a section on what a merge does, a section on how to stop the pipeline, and a section on undoing a bad release with a new patch release. [S1, S9]

AC-14: After this effort, `AGENTS.md` and `skills/plab-ship/SKILL.md` contain no sentence that forbids a version, a tag or a release in an opted-in repository. [S1, S3, S4]

AC-15: `skills/plab-ship/SKILL.md` states the default bump rule: a bump for a change to what users run, none for internal material only, and a held-back bump named in the report. [S2]

AC-16: `skills/plab-ship/SKILL.md` states that in an opted-in repository its release step pushes no tag and creates no GitHub Release. [S4, S5] [model-inference]

AC-17: A pull request that raises `library.json`'s version fails a check while any row in any `skills/*/HISTORY.md` still carries `Unreleased` in its Release cell. [S1, S3]

## Behavior / Examples

### Example 1: a skill fix that releases (grounds AC-4, AC-7, AC-8, AC-11)

The agent ships a fix to `skills/plab-ship/scripts/derive-ship-facts.py`. Under Requirement 11 the change is one users run, so the agent bumps 0.14.1 to 0.14.2 in every surface, fills the skill's `HISTORY.md` Release cell with `v0.14.2`, and writes a CHANGELOG section in the same pull request, titled `fix(plab-ship): ...`. The pull request checks pass and the agent merges. The release workflow reruns the tests on the merge commit, creates `v0.14.2` and its Release in one job, and sends one repin request to `prisant-labs/agent-plugins`. The maintainer typed only `/plab-ship`.

### Example 2: an internal change that does not release (grounds AC-9)

The agent ships an edit to a release plan under `docs/internal/`. Under Requirement 12 there is no bump. The merge lands, the release workflow finds that `v0.14.2` and its Release already exist, and it does nothing. The change goes out with the next release that carries a bump.

### Example 3: a held-back feature released through a later fix (grounds AC-4)

A `feat(plab-wrap-session): ...` pull request merges without a bump, because the agent holds it back under Requirement 13 and its skill row reads `Unreleased`. A later `fix(plab-ship): ...` pull request bumps the version. The largest type since `v0.14.1` is `feat`, so the expected version is 0.15.0, and a bump to 0.14.2 fails the check. The same pull request fills both `Unreleased` cells with `v0.15.0` (AC-17).

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
| 2026-11-21 | claude (Opus 5.5) | clarified | Before first merge, after an advisor review: the size check reads every title since the tag; the surface list adds the `HISTORY.md` Release cells; the eval trigger excludes `metadata.version`; AC-9 requires the Release too; AC-12 allows only `actions` actions; AC-15 to AC-17 added for the bump rule, the tag owner and the `Unreleased` cells |
| 2026-11-21 | claude (Opus 5.5) | clarified | The implementation plan closed three Gaps: titles are read from merge-commit bodies with git alone, the dispatch endpoint needs Contents write (medium-high confidence, proven live in the plan's Phase 8), and the names are `.github/release-on-merge.json` and `MARKETPLACE_REPIN_TOKEN`. Of Requirement 2's seven surfaces, the configuration lists the five that hold one version; the CHANGELOG heading and the `HISTORY.md` Release cells are checked by AC-5 and AC-17. No acceptance criterion changed |

## Sources & Evidence

The proposal and the walk are private documents, so their substance is summarized here.

- **[S1]** The maintainer's release-on-merge proposal, 2026-11-13 (private). It records the problem (nineteen merged pull requests sat unreleased before v0.14.0; thirteen tags sat without Releases until 2026-09-14), the five jobs to be done, the default-token constraint, the merge check's `release` rule, the five written rules the pipeline would overturn including the batched-release mechanisms, and approach C, the deterministic pipeline - class A
- **[S2]** The maintainer's decision walk, 2026-11-20 to 2026-11-21 (private). D1 C: a deterministic pipeline with `/plab-ship` as the one command, where the maintainer said he was not asking for every merge to release, and "I want to empower and generally defer to your best judgment to see through release tag and merge". D2 A: a fine-grained token on the marketplace repository. D3 A: local evals with a pull request check. D4 A: the author picks the size and CI checks it. D5 A: a hand-written CHANGELOG. D6 A: amend the rules for opted-in repositories only. D7: self-contained, "Powertools should be self contained ... best in Class, best practice deterministic solutions" - class A
- **[S3]** `AGENTS.md`, the Build and validate section: "CI reports; it never fixes, bumps, or tags", the `publish-release.yml` paragraph, and `skill-drift-check.py`'s advisory and enforced modes - class A
- **[S4]** `skills/plab-ship/SKILL.md`, step 7 ("Release, only with `--release`"), which pushes the tag, and the "The flag covers one run" constraint - class A
- **[S5]** `.github/workflows/publish-release.yml`, which runs on a pushed `v*` tag, and the v0.14.1 release commit `c48f301`, which changed the version surfaces named in Requirement 2 - class A
- **[S6]** GitHub Docs, "Automatic token authentication": events triggered by `GITHUB_TOKEN` do not create new workflow runs - `https://docs.github.com/en/actions/security-guides/automatic-token-authentication` - class A
- **[S7]** Semantic Versioning 2.0.0 - `https://semver.org/spec/v2.0.0.html` - class A
- **[S8]** Keep a Changelog 1.1.0 - `https://keepachangelog.com/en/1.1.0/` - class A
- **[S9]** `skills/plab-ship/references/documentation-standard.md`, the Human / Trust cell (upgrade, migration and rollback) - class A
- **[S10]** `scripts/version-parity-check.py`, which compares the versions tracked documents claim with `library.json` and each `SKILL.md` - class A

### Unverified Claims

- "the surface check extends that gate rather than adding a second one" - appears in Requirement 2
- "Checking against everything since the tag, not only this title, lets a held-back `feat` release through a later `fix` pull request" - appears in Requirement 4
- "when every type since the tag is of that kind and the agent bumps, the expected size is a patch" - appears in Requirement 5
- "In an opted-in repository the release workflow is the only component that creates a version tag or a GitHub Release" - appears in Requirement 10 and AC-16
- "Rerunning the release workflow on a merged commit whose tag exists but whose Release does not creates the Release and pushes no second tag" - appears in AC-10
- "Two release workflows never run at once for the same repository, so two quick merges cannot race on one tag" - appears in Non-Functional Requirements

### Gaps

- Closed by the implementation plan: whether a fine-grained token with contents write can send a repository dispatch. GitHub's fine-grained permission reference lists the dispatch endpoint under Contents, write. Medium-high confidence, because the page was read through a summarizing fetcher; the plan's Phase 8 proves it with the first real dispatch.
- Closed by the implementation plan: how the size check reads titles. A GitHub merge commit carries the pull request title as the first line of its body, so git alone suffices.
- Whether Codex updates a plugin on its own after a repin. Not verified.
- Closed by the implementation plan: the names are `.github/release-on-merge.json` and `MARKETPLACE_REPIN_TOKEN`.

## Open Questions / Decisions

None at this time. Decisions D1 to D7 were made in the maintainer's decision walk of 2026-11-20 to 2026-11-21 [S2], and [ADR-3 (release on merge)](../../../decisions/0003-release-on-merge.md) records D1.
