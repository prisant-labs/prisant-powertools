---
id: RM-01
title: "plab-org-profile-readme: set a standard for a GitHub organization's profile README and keep the page true to it and to the public repositories"
type: spec
status: committed
created: 2026-11-07
updated: 2026-11-08
linked-effort: "the maintainer's request of 2026-11-06 in session for a skill that keeps an organization's README current, made general on 2026-11-07, narrowed to organization pages, and given standards, options and --setup the same day"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 20
source-count: 13
requires-human-review: true
target-release: null
priority: P2
---

# Spec: plab-org-profile-readme, a standard for an organization's profile README and a page kept true to it

## Task Summary

**Status:** committed. Phases 1 to 5 of the implementation plan are built on branch `feat/rm-01-org-profile-readme`; the live run (AC-13) and the release are not done
**Last updated:** 2026-11-08 by claude (Opus 5.5), recording the build, D7 and the criteria the tests fulfil
**Linked plan:** [implementation-plan.md](implementation-plan.md), seven phases
**Open questions:** D2, which does not block the build, and D7, decided provisionally by the agent (see Open Questions / Decisions). D1 and D3 to D6 are decided
**Revisions:** 6

### Acceptance Criteria Fulfillment

- [ ] AC-1: The skill is manual-only in both harnesses and does not fire on a request to edit an ordinary README
- [ ] AC-2: ~~The facts resolve a user or an organization to the right profile page, and name a missing one as broken~~ (SUPERSEDED 2026-11-07 by AC-14; see Revisions)
- [x] AC-3: The facts cover public, non-fork, non-archived repositories, and never output a private one · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-4: The skill, its references and its scripts name no particular owner or repository, and work without a settings file · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-5: The checker accounts for every covered repository, as listed or as excluded with a reason · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-6: The checker rejects a version claim, a release link or a badge that does not match the repository · fulfilled 2026-11-08 by `profile-check.py --self-test`
- [x] AC-7: The checker rejects a private repository's name on the page or in the pull request body · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-8: The checker rejects a lost heading or altered shared text, unless the change is accounted for · fulfilled 2026-11-08 by `profile-check.py --self-test`
- [ ] AC-9: ~~`--init` writes a page in the default layout that the checker passes~~ (SUPERSEDED 2026-11-07 by AC-18; see Revisions)
- [x] AC-10: A freeform page gets the factual checks, and the skipped layout checks are reported as skipped · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-11: The skill never writes to the default branch, updates an open refresh pull request in place, and opens nothing when the page is current · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [ ] AC-12: The checker proves every rule can fail against a committed sample, and CI runs it
- [ ] AC-13: A live run on one of the maintainer's organizations opens a pull request the checker passes
- [ ] AC-14: ~~The facts resolve an organization to its profile page, refuse a user account, and name a missing page as broken~~ (SUPERSEDED 2026-11-07 by AC-15; see Revisions)
- [x] AC-15: The facts resolve an organization to its profile page, refuse a user account, and report a missing page without failing · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-16: Three built-in standards each ship with a reference document and a sample page the checker passes · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-17: `--setup` writes a standard on each of its three paths, and a run against that standard passes the checker · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-18: A run against a standard with no page writes the page, and the checker passes it · fulfilled 2026-11-08 by `test-profile-scripts.py`
- [x] AC-19: The checker rejects a page that breaks its standard's sections or options · fulfilled 2026-11-08 by `profile-check.py --self-test` and `test-profile-scripts.py`
- [ ] AC-20: An instruction run applies the instruction, passes the checker, and lists instruction-driven changes apart from fact-driven ones

### Currently In Progress

Phases 1 to 5 are built on branch `feat/rm-01-org-profile-readme`. AC-1 waits for its eval case to run, AC-12 for CI on the pull request, AC-20 for an instruction run, and AC-13 for the live run in Phase 6.

---

## Purpose

An organization's profile README is its front page on GitHub. Every fact on it belongs to another repository, nothing rebuilds it, and nobody reads it while working, so it drifts [S3]. On 2026-11-06 the Prisant Labs page said ten skills and listed v0.9.0 for a plugin that had fourteen skills and v0.13.0, and it did not list a public repository created on 2026-10-29 [S7].

The maintainer already runs two weekly routines that refresh two organization pages, and they work: one of their pull requests merged on 2026-10-23 [S2, S4]. The drift came from elsewhere. Each routine stops when its last pull request is still open, and two had waited 7 and 14 days, so each weekly run ended after about ten seconds [S4]. A skill must therefore make a waiting pull request stay current, and not only write a better one.

The maintainer ruled that the skill must be generally useful rather than built for particular repositories [S1], and then that it serve organization pages, because an organization's page is a particular kind of profile [S8]. An organization page indexes many projects for visitors, while a user's page is personal and often carries statistics cards and work in other owners' repositories [S5].

The skill does two jobs [S9]. It first establishes a standard: the structure the page follows and the options it uses, chosen from a few built-in standards or defined by the organization. On every later run, it updates the page to that standard from what changed in the public repositories, or from the maintainer's instructions.

## Scope

### In Scope

1. A new skill, `skills/plab-org-profile-readme/`, manual-only, invoked as `/plab-org-profile-readme <org> [--setup] ["<instructions>"]`.
2. A facts script, a checker with a self-test against a committed sample, and the format of one standard file per organization.
3. Three built-in standards, each with a reference document and a sample page.
4. A `--setup` interview that establishes or revises an organization's standard.
5. Organization profile pages, `<org>/.github/profile/README.md`.
6. The plugin's registration of the skill: `library.json`, the manifests, `AGENTS.md`, the root `README.md`, a usage README, `CHANGELOG.md`, a no-fire eval case and the CI steps.

### Non-Goals

1. **The READMEs of the repositories themselves.** The skill reads them as sources and never edits them.
2. **Hosts other than GitHub.**
3. **Scheduling.** Whether a routine runs the skill weekly is D3, outside the skill.
4. **Merging the pull request.** The skill opens or updates it. Any automatic merge is D2.
5. **Rewriting a page's voice.** Existing wording stays unless a fact contradicts it or an instruction asks for a change.
6. **Third-party statistics services,** such as activity cards and star charts. The skill keeps them where they are and does not check them.
7. **User account profile pages,** `<user>/<user>/README.md`. They are a different kind of profile, and a later spec may cover them [S8].

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Owns the pages | Runs `/plab-org-profile-readme <org> --setup` once per organization, then `/plab-org-profile-readme <org>` with or without instructions, and reviews and merges the pull request |
| Running agent (Claude Code or Codex) | Executes the skill | Runs the facts script, conducts the setup interview, edits the page on a branch, runs the checker, opens or updates the pull request |
| Any other GitHub organization | A possible user | Adopts a built-in standard or defines its own through `--setup` |

## Requirements

1. The skill is manual-only in both harnesses, because it writes to a public repository [S6].
2. Given an owner, the facts confirm it is an organization and report its profile page, `<org>/.github/profile/README.md`. A user account is refused with a message saying the skill covers organization pages. A missing page is reported as missing. When a standard exists, the run then writes the page; when none exists, the run directs the maintainer to `--setup` [S1, S8, S9].
3. By default the page covers the organization's public repositories that are not forks and not archived, excluding the profile repository itself [S2]. The standard may exclude repositories, each with a reason [S1].
4. A private repository is never named on the page or in the pull request body, even when the credentials can see it and even when an instruction asks for it [S2].
5. Nothing in the skill, its references or its scripts names a particular owner or repository. An organization's specifics live in one standard file in its `.github` repository, which replaces the settings file of earlier revisions. The facts work without it [S1].
6. The standard is the page's format. It records a base, which is one of the built-in standards, a standard adopted from the existing page, or a custom one. It also records the sections in order, the option values, the categories, the exclusions with reasons, the featured repositories and any shared text. The skill keeps the page to its standard and changes what the facts contradict or an instruction asks [S9, S2].
7. Three built-in standards ship with the skill, each with a reference document that describes its sections and options and a sample page [S9]. **Catalog** is the maintainer's current format: a header, a status and tag legend, an index by category, and a section per project with its version line and recent changes [S2]. **Compact** is a header and one table of projects, with name, one-line description, status and latest release. **Showcase** is a header, a few featured projects with longer descriptions, and a short list of the rest. [model-inference: Compact and Showcase were proposed here, and the maintainer adopted them in D6 without an observed example]
8. A standard sets these options, which the maintainer adopted in D6 [S9, S10]:
   - **Recent changes:** off, or on with the number of entries shown per project.
   - **Badges:** off, or on with the kinds allowed, such as release, license and CI status.
   - **Status labels:** off, or on with the label vocabulary.
   - **Grouping:** none, or by the standard's categories.
   - **Featured:** the repositories shown first, as a "start here" list.
   - **Order:** by category, by latest release, or alphabetical.
   - **Shared text:** passages that must stay identical, which keeps sibling organization pages aligned.
9. `--setup` establishes what the standard records, whatever the harness's way of asking. It offers three paths: adopt a built-in standard and set its options, adopt the existing page as the standard, or define a custom standard section by section. Run against an organization that already has a standard, it offers the current values as defaults. It writes the standard, and the page when none exists, under the branch rules of requirement 13 [S9]. [model-inference: that a standard can be derived from an arbitrary existing page is unproven]
10. A run may carry free-text instructions, such as "add a Start here section" or "describe the new repository as experimental". The skill applies them, and the pull request body lists instruction-driven changes in a section apart from fact-driven ones. An instruction never overrides requirement 4 or requirement 13 [S9].
11. A page with no standard gets the factual checks only, and the run says which checks it skipped and suggests `--setup` [model-inference].
12. The checker accounts for every covered repository as listed or excluded, rejects a listed repository that is not public or no longer exists, rejects a version claim that does not match the latest release, rejects a release link that does not resolve, and rejects a badge that points at another owner or repository [S3, S7]. It flags a badge that reads a list by position, because adding an entry to that list changes what it shows [S7]. Against a standard, it also rejects a page whose sections are missing or out of order, or whose content breaks an option [S9].
13. The skill works on a branch and never on the default branch. When an open pull request from an earlier run exists, the skill updates that pull request instead of opening another. When nothing changed, it makes no branch and no pull request [S2, S4].
14. The checker follows the repository's three-state gate contract and proves every rule can fail against a committed sample before it reports clean [S6].
15. The skill must work when run locally by the maintainer, whatever D3 decides about the cloud routines [S4]. [model-inference: whether a cloud routine can load a plugin skill is unverified]

## Acceptance Criteria

**AC-1:** `SKILL.md` carries `disable-model-invocation: true`, `agents/openai.yaml` carries `policy.allow_implicit_invocation: false`, and an eval case whose prompt asks to update an ordinary repository README asserts that the skill is not invoked. [S6]

**AC-2:** (SUPERSEDED 2026-11-07 by AC-14; see Revisions.) Given fixture responses for a user owner and an organization owner, the facts report the type and the profile page path for each. For an owner with no profile page and no `--init`, the facts script exits 2 and names the cause. [S1]

**AC-3:** Given a fixture owner holding a public repository, a fork, an archived repository and a private repository, the facts list only the public one, and the private repository's name appears nowhere in the output. [S2]

**AC-4:** A test fails if `SKILL.md`, a reference or a script contains the name of a fixed owner or repository. The test reads its list of names from its own fixture, so the list is not itself built into the skill. The facts script produces a complete result for a fixture owner with no settings file. [S1]

**AC-5:** Given a page that omits a covered repository, the checker names it. Given a settings file that excludes that repository with a reason, the checker passes it. Given a page that lists a repository the facts say is private or missing, the checker names it. [S3, S7]

**AC-6:** The checker rejects a page whose stated version for a repository differs from that repository's latest release, a release link to a tag that does not exist, and a badge whose URL names another owner or repository. It reports a badge that reads a list by position as a finding. [S7]

**AC-7:** The checker rejects a page or a pull request body that contains the name of a repository the facts list as private. [S2]

**AC-8:** Given a page from which a heading was removed while its repository is still covered, the checker names the heading. Given settings that mark a passage as shared, the checker rejects a page whose copy of that passage differs. [S2]

**AC-9:** (SUPERSEDED 2026-11-07 by AC-18; see Revisions.) For a fixture owner with no profile page, `--init` writes a page in the default layout, and the checker passes it. [S2]

**AC-10:** Given a freeform fixture page, the checker runs the checks of AC-5 to AC-7, skips those of AC-8, and its output names each skipped check. [model-inference]

**AC-11:** `SKILL.md` instructs that the skill never commits to the default branch, that it updates an open pull request from an earlier run in place, and that it makes no branch when nothing changed. A test fails if any of the three instructions is removed. [S2, S4]

**AC-12:** The checker's self-test proves each of its rules fails on a mutation of the committed sample and exits 2 if one does not, and CI runs the self-test and the facts tests. [S6]

**AC-13:** Running `/plab-org-profile-readme` on one of the maintainer's organizations, once the skill is installed, opens or updates a pull request whose page the checker passes. [model-inference: the live run is this spec's own test design]

**AC-14:** (SUPERSEDED 2026-11-07 by AC-15; see Revisions.) Given fixture responses for an organization owner, the facts report the type and the path `<org>/.github/profile/README.md`. Given a user owner, the facts script exits 2 and says the skill covers organization profile pages. For an organization with no profile page and no `--init`, the facts script exits 2 and names the cause. [S1, S8]

**AC-15:** Given fixture responses for an organization owner, the facts report the type and the path `<org>/.github/profile/README.md`. Given a user owner, the facts script exits 2 and says the skill covers organization profile pages. Given an organization with no profile page, the facts report the page as missing and exit 0. [S1, S8, S9]

**AC-16:** The skill ships the Catalog, Compact and Showcase standards. Each has a reference document naming its sections and the options it uses, and a sample page that uses only example owners. The checker passes each sample under its own standard. [S9, S2]

**AC-17:** Given fixture answers for each of the three `--setup` paths (a built-in standard, the existing page adopted, and a custom standard), `--setup` writes a standard file. A run against each standard on the fixture organization produces a page the checker passes. [S9]

**AC-18:** Given a fixture organization with a standard and no profile page, a run writes the page in that standard, and the checker passes it. [S9]

**AC-19:** Against a standard, the checker rejects a page with a section missing or out of order, badges when badges are off, a recent-changes list when recent changes are off or longer than the set count, a status label outside the vocabulary, and a featured repository that is not shown first. [S9]

**AC-20:** Given a run with a free-text instruction, the page reflects the instruction, the checker passes it, and the pull request body lists the instruction's changes under their own heading, apart from the fact-driven changes. Given an instruction to name a private repository, the skill refuses it and AC-7 still holds. [S9, S2]

## Behavior / Examples

### Example 1: An organization with a new repository

The maintainer types `/plab-org-profile-readme example-org`, whose standard is Catalog with three recent changes per project. The facts find a repository that became public last week and is not on the page, and a release newer than the page's version line for another. The skill adds a section for the new repository in the category its description fits, updates the version line and recent changes, runs the checker, and opens a pull request that names each change and the fact behind it.

### Example 2: A pull request is already waiting

A pull request from last week's run is still open. The skill updates that pull request's branch to reflect this week's facts and rewrites its body, so the waiting pull request is current when the maintainer reads it.

### Example 3: A user account is named

The maintainer types `/plab-org-profile-readme example-user`. The facts find a user account rather than an organization, so the skill stops and says it covers organization profile pages. It makes no branch.

### Example 4: Nothing changed

Every fact matches the page. The skill makes no branch and no pull request and says the page is current.

### Example 5: Setting up a new organization

The maintainer types `/plab-org-profile-readme example-org --setup` for an organization with no page. The skill shows the three built-in standards with their samples. The maintainer picks Compact, turns badges off, and names two featured repositories. The skill writes the standard and a first page on a branch, runs the checker, and opens a pull request.

### Example 6: An instruction

The maintainer types `/plab-org-profile-readme example-org "mark the new repository as experimental"`. The skill sets that repository's status label, which the standard's vocabulary allows, and also updates two stale version lines. The pull request body lists the label change under the instruction and the version lines under facts.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Privacy | No private repository is named on a public page or in a public pull request | [S2] |
| Safety | The skill writes only to a branch of the profile repository, and never merges | [S2] |
| Cost | Repository facts come from one script call | [S6] |
| Portability | The scripts are stdlib Python, use `gh` for GitHub, and work in Claude Code and Codex | [S6] |
| Context budget | The description is at most 600 characters | [S6] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-11-07 | claude | added | Initial draft, written at the maintainer's instruction after an advisor review. D1 records the maintainer's ruling that the skill be generally useful. |
| 2026-11-07 | claude | changed | Narrowed to organization profile pages by the maintainer's ruling [S8]. AC-2 superseded by AC-14, which refuses a user account. Requirements 2, 3 and 5, Scope, Users, Purpose and Example 3 follow. User pages become non-goal 7. D4 decided, and D5 (the skill's name) added. |
| 2026-11-07 | claude | changed | Standards, options, `--setup` and instruction runs added at the maintainer's direction [S9]. The skill is renamed `plab-org-profile-readme` (D5), and AC-13 and the examples use the new name. `--init` is dropped: AC-9 superseded by AC-18, and AC-14 superseded by AC-15, which reports a missing page instead of failing. AC-16 to AC-20 added. The standard file replaces the settings file, so "settings" in AC-4, AC-5 and AC-8 means the standard. D1's exception widened, and D6 (the option set and built-in standards) added. |
| 2026-11-07 | claude | changed | D6 decided: option A, requirements 7 and 8 adopted as written, by the maintainer's answer [S10]. No criterion changes. |
| 2026-11-07 | claude | changed | D3 decided: option B, retire the two routines, by the maintainer's answer [S11]. Status set to committed and the implementation plan linked, at the maintainer's request to prepare the build. D2 noted as not blocking. No criterion changes. |
| 2026-11-08 | claude | changed | Built Phases 1 to 5 at the maintainer's instruction to build the skill [S12]. D7 added and decided provisionally by the agent, from checking a real organization page with live facts before any pull request [S13]: the standard gains `include` for public forks a page shows, which amends requirement 3, and `skip_releases` for releases a page leaves out with a reason, which narrows requirement 12's version rule; rule R6 reports a positional badge as a note, not a failure. No criterion is rewritten. Fourteen criteria ticked with the tests that show them. |

## Sources & Evidence

- **[S1]** The maintainer's rulings in session: on 2026-11-06, the request for a skill that updates each organization's README in a similar format; on 2026-11-07, the name `plab-profile-readme` because a user account has one too, and "it doesn't need to be for the specific repos, it needs to be generally useful as a skill". Class A.
- **[S2]** The two weekly routine prompts that refresh the Prisant Labs and Product on Purpose pages, about 14 KB each. After the organization names are swapped, they differ in 16 lines, which is evidence the format is already general. Maintainer-local, in each profile repository's gitignored `_local/readme/` folder. Class A.
- **[S3]** `_local/profile-readme-automation.md` in the Product on Purpose profile repository, 2026-08-07: a measured drift table, including a public repository missing from the page for three weeks. Maintainer-local. Class A.
- **[S4]** The two refresh pull requests open on 2026-11-06, `prisant-labs/.github` #4 from 2026-10-30 and `product-on-purpose/.github` #6 from 2026-10-23, and the log of the Prisant Labs routine's run that day, which stopped at its first step after 10 seconds. Class A.
- **[S5]** The maintainer's account profile README, `jprisant/jprisant`, whose opening comment says its descriptions, word badges and project list are edited by hand, and names a dated badge removal. Class A.
- **[S6]** `AGENTS.md`: the design frame, the manual-only rulings, and the three-state gate contract; and `skills/plab-ship/`, whose checker and record pattern this skill follows. Class A.
- **[S7]** A comparison on 2026-11-06 of the Prisant Labs page with the organization's public repositories: a stale skill count and version, an unlisted public repository, and a marketplace badge that reads `plugins[1]` by position. Class A.
- **[S8]** The maintainer's ruling in session on 2026-11-07, after the first draft merged: "the org profile should be the focus of the skill because that is a particular kind of profile". Class A.
- **[S9]** The maintainer's direction in session on 2026-11-07, after the second revision merged: the name "Org-profile-readme"; the skill should "focus on establishing the standard structure for the readme" and update it from public repository changes "or based on the user's instructions"; a few standard examples "with documentation and samples" that can be adopted, or a standard the user defines; options such as showing a change log or not and using badges or not; and "--setup that questions the user to establish the template". Class A.

- **[S10]** The maintainer's answer in session on 2026-11-07, after the third revision merged: "D6 yes adopt the options and standards". Class A.

- **[S11]** The maintainer's answer in session on 2026-11-07, after D3 was explained: "B . Polish anything needed so the next session can create and release the skill". Class A.

- **[S12]** The maintainer's instruction in session on 2026-11-08: "Build org profile readme skill". Class A.

- **[S13]** A read-only check on 2026-11-08 of one of the maintainer's organization pages against live facts, with the new scripts. Without a standard, the checker named a fork the page lists on purpose, an excluded placeholder repository, and a release the page leaves off; under a standard adopted from the page, two releases the page leaves off, each of whose notes says it changes nothing a user will see, and two badges that read a list by position. Class A.

### Unverified Claims

- Requirement 7: the Compact and Showcase standards are proposals, not observed formats.
- Requirement 9: that a standard can be derived from an arbitrary existing page. It is proven only for the maintainer's two consistent organization pages.
- Requirement 11 and AC-10: the handling of a page with no standard is a design choice, not observed behaviour.
- Requirement 15: whether a cloud routine can load a plugin skill. The routine prompts also record that organization-level API paths can return 403 in that environment [S2]. D3's answer, retiring the routines, means the build does not depend on it.

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Whether the skill is general or built for the maintainer's own pages | General across organizations, with standards and setup, by ruling | Decided | 2026-11-07 |
| D2 | Whether a purely factual update may merge without review | Pending | Open | 2026-11-07 |
| D3 | What happens to the two weekly routines | B: retire them, by ruling | Decided | 2026-11-07 |
| D4 | Whether the account page ships in 1.0 | Organization pages only, by ruling | Decided | 2026-11-07 |
| D5 | Whether the skill keeps the name `plab-profile-readme` | `plab-org-profile-readme`, by ruling | Decided | 2026-11-07 |
| D6 | The option set and the built-in standards | A: requirements 7 and 8 as written | Decided | 2026-11-07 |
| D7 | What a real page needs that the criteria did not foresee | `include`, `skip_releases`, and R6 as a note, decided provisionally by the agent | Decided | 2026-11-08 |

### D1: General or built for the maintainer's pages (Decided)

**Summary.** `AGENTS.md` says not to add configurability or onboarding for hypothetical third-party users. The maintainer ruled the opposite for this skill: "it needs to be generally useful as a skill" [S1].

**Resolution.** The skill is general, as a deliberate exception. The first draft kept the exception small: one owner argument, one optional settings file, and no onboarding features. On the same day the maintainer widened it [S9], and its size is now: one organization argument, one standard file, three built-in standards, the option set of requirement 8, and a `--setup` interview. Anything beyond that still needs a ruling. User pages are out of scope (D4).

### D2: Automatic merge of factual updates (Open)

**Summary.** The review queue, not the writing, caused the drift [S4]. Version lines, counts and recent changes are facts the checker can verify, while new or removed repositories and status labels need judgement.

**Options.** A: every update waits for review, and the skill keeps a waiting pull request current. B: an update that changes only facts the checker verified merges through the maintainer's merge check, and anything else waits.

**Recommendation.** A for 1.0, then B once a few reviewed runs show the factual updates are reliable. Both profile repositories are on the maintainer's solo list, so B is possible under the merge rule.

**Note, 2026-11-07.** D2 does not block the build. Non-goal 4 and the Safety requirement already build option A, because the skill never merges. D2 matters only when a later version considers automatic merges.

### D3: The two weekly routines (Decided)

**Summary.** Two routines refresh the organization pages today [S2].

**Options.** A: convert them to call the skill, if a routine can load it. B: retire them and run the skill by hand. C: keep them as they are.

**Recommendation (not taken).** A if the plugin loads in a routine, otherwise B. C keeps two copies of the format rules that will drift from the skill.

**Resolution.** B, by the maintainer's answer [S11]: retire both routines, and run the skill by hand.

**Follow-up.** The implementation plan's Phase 7 disables both routines once the skill's first live pull request has merged, so the pages are never left with neither mechanism. Disabling rather than deleting leaves the maintainer to delete them later.

### D4: The account page in 1.0 (Decided)

**Summary.** The account page draws on two organizations and uses its own layout [S5].

**Options.** A: 1.0 covers organization and account pages. B: 1.0 covers organization pages, and the account page follows.

**Recommendation (not taken).** A, because the sources setting is small and the account page repeats the organization pages' projects, so the shared-text check is most useful across all three.

**Resolution.** B, and narrower: this spec covers organization pages only, and the account page is a non-goal rather than a later version of this skill [S8]. The maintainer's reason was that an organization page is a particular kind of profile. The `sources:` setting that only the account page needed is dropped.

### D5: The skill's name (Decided)

**Summary.** The name `plab-profile-readme` was chosen on 2026-11-07 because a user account has a profile README too [S1]. With user pages out of scope (D4), that reason no longer applies.

**Options.** A: keep `plab-profile-readme`, which leaves room for a later spec that covers user pages. B: rename to `plab-org-profile`, which says what the skill now does.

**Recommendation (not taken).** B, because the description is the trigger mechanism and the name should match the scope.

**Resolution.** `plab-org-profile-readme`, the maintainer's own choice [S9], which keeps both the scope and the word README. The spec's id and folder, `RM-01_profile-readme`, stay as they are.

### D6: The option set and the built-in standards (Decided)

**Summary.** The maintainer named two options, a change log and badges, and asked for "a few others" [S9]. Requirement 8 proposes seven, and requirement 7 proposes Compact and Showcase beside the maintainer's own Catalog format.

**Options.** A: adopt requirements 7 and 8 as written. B: adopt them with the maintainer's edits. C: ship Catalog alone in 1.0, with the options, and add the other two standards later.

**Recommendation.** A. Three standards give a real choice in `--setup` without a large surface, and each option maps to one checker rule in AC-19, so the set stays testable. An option that a real run never changes should be removed in a later version.

**Resolution.** A, by the maintainer's answer [S10]: the three built-in standards of requirement 7 and the seven options of requirement 8, as written.

**Follow-up.** None before the build. The implementation plan builds all three standards and all seven options, and AC-16 and AC-19 test them.

### D7: What a real page needs that the criteria did not foresee (Decided, provisionally)

**Summary.** Before any pull request, the new scripts checked one of the maintainer's real organization pages against live facts [S13]. Three things the criteria did not foresee would have made a correct page fail, so AC-13's live run could not pass. First, the page lists a public fork that publishes its own releases, and requirement 3 leaves forks out. Second, the page leaves off releases whose notes say they change nothing a user will see, as its routine's rules required, and a strict newest-release rule rejects that. Third, two badges read a marketplace list by position, which requirement 12 calls a flag, and failing the page for it would block a deliberate, correct badge.

**Options.** A: amend the standard and the rules. B: change the real page to fit the rules. C: stop and ask before building further.

**Resolution.** A, by the agent, provisionally, because the maintainer had asked for the skill to be built and B would have rewritten deliberate choices on the maintainer's page. The standard gains `include`, public forks the page shows, each with a reason; and `skip_releases`, releases the page leaves out, each with a reason, which R3 does not count. R6 is a NOTE line that leaves the exit code clean. Each entry carries a reason, so nothing is skipped silently.

**Follow-up.** The maintainer confirms or overrules D7 when reviewing the pull request. Overruling it means removing the two fields and making R6 a finding, and the live run would then need the page changed first.
