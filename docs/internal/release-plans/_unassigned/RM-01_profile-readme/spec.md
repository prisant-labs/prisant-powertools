---
id: RM-01
title: "plab-profile-readme: keep any GitHub organization's profile README true to its public repositories"
type: spec
status: draft
created: 2026-11-07
updated: 2026-11-07
linked-effort: "the maintainer's request of 2026-11-06 in session for a skill that keeps an organization's README current, widened on 2026-11-07 to any GitHub user or organization"
linked-plan: null
linked-release: null
ac-count: 14
source-count: 8
requires-human-review: true
target-release: null
priority: P2
---

# Spec: plab-profile-readme, keeping any GitHub organization's profile README true to its public repositories

## Task Summary

**Status:** draft. Nothing is built
**Last updated:** 2026-11-07 by claude (Opus 5.5), narrowing the scope to organization profile pages at the maintainer's ruling
**Linked plan:** none yet
**Open questions:** D2, D3 and D5 (see Open Questions / Decisions). D1 and D4 are decided
**Revisions:** 2

### Acceptance Criteria Fulfillment

- [ ] AC-1: The skill is manual-only in both harnesses and does not fire on a request to edit an ordinary README
- [ ] AC-2: ~~The facts resolve a user or an organization to the right profile page, and name a missing one as broken~~ (SUPERSEDED 2026-11-07 by AC-14; see Revisions)
- [ ] AC-3: The facts cover public, non-fork, non-archived repositories, and never output a private one
- [ ] AC-4: The skill, its references and its scripts name no particular owner or repository, and work without a settings file
- [ ] AC-5: The checker accounts for every covered repository, as listed or as excluded with a reason
- [ ] AC-6: The checker rejects a version claim, a release link or a badge that does not match the repository
- [ ] AC-7: The checker rejects a private repository's name on the page or in the pull request body
- [ ] AC-8: The checker rejects a lost heading or altered shared text, unless the change is accounted for
- [ ] AC-9: `--init` writes a page in the default layout that the checker passes
- [ ] AC-10: A freeform page gets the factual checks, and the skipped layout checks are reported as skipped
- [ ] AC-11: The skill never writes to the default branch, updates an open refresh pull request in place, and opens nothing when the page is current
- [ ] AC-12: The checker proves every rule can fail against a committed sample, and CI runs it
- [ ] AC-13: A live run on one of the maintainer's organizations opens a pull request the checker passes
- [ ] AC-14: The facts resolve an organization to its profile page, refuse a user account, and name a missing page as broken

### Currently In Progress

None. The spec was written on 2026-11-07 and narrowed the same day to organization profile pages. It waits for the maintainer's review and the three open decisions.

---

## Purpose

An organization's profile README is its front page on GitHub. Every fact on it belongs to another repository, nothing rebuilds it, and nobody reads it while working, so it drifts [S3]. On 2026-11-06 the Prisant Labs page said ten skills and listed v0.9.0 for a plugin that had fourteen skills and v0.13.0, and it did not list a public repository created on 2026-10-29 [S7].

The maintainer already runs two weekly routines that refresh two organization pages, and they work: one of their pull requests merged on 2026-10-23 [S2, S4]. The drift came from elsewhere. Each routine stops when its last pull request is still open, and two had waited 7 and 14 days, so each weekly run ended after about ten seconds [S4]. A skill must therefore make a waiting pull request stay current, and not only write a better one.

The maintainer ruled that the skill must be generally useful rather than built for particular repositories [S1]. It should work on any GitHub organization named to it, with that organization's specifics in an optional settings file. On 2026-11-07 the maintainer narrowed it to organization profiles, because an organization's page is a particular kind of profile [S8]. An organization page indexes many projects by category for visitors, while a user's page is personal and often carries statistics cards and work in other owners' repositories [S5].

## Scope

### In Scope

1. A new skill, `skills/plab-profile-readme/`, manual-only, invoked as `/plab-profile-readme <org> [--init]`.
2. A facts script, a checker with a self-test against a committed sample, a default layout, and an optional per-owner settings file format.
3. Organization profile pages, `<org>/.github/profile/README.md`.
4. The plugin's registration of the skill: `library.json`, the manifests, `AGENTS.md`, the root `README.md`, a usage README, `CHANGELOG.md`, a no-fire eval case and the CI steps.

### Non-Goals

1. **The READMEs of the repositories themselves.** The skill reads them as sources and never edits them.
2. **Hosts other than GitHub.**
3. **Scheduling.** Whether a routine runs the skill weekly is D3, outside the skill.
4. **Merging the pull request.** The skill opens or updates it. Any automatic merge is D2.
5. **Rewriting a page's voice.** Existing wording stays unless a fact contradicts it.
6. **Third-party statistics services,** such as activity cards and star charts. The skill keeps them where they are and does not check them.
7. **User account profile pages,** `<user>/<user>/README.md`. They are a different kind of profile, and a later spec may cover them [S8].

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Owns the pages | Types `/plab-profile-readme <org>`, reviews and merges the pull request |
| Running agent (Claude Code or Codex) | Executes the skill | Runs the facts script, edits the page on a branch, runs the checker, opens or updates the pull request |
| Any other GitHub organization | A possible user | Uses the skill with no settings file, on the defaults |

## Requirements

1. The skill is manual-only in both harnesses, because it writes to a public repository [S6].
2. Given an owner, the facts confirm it is an organization and report its profile page, `<org>/.github/profile/README.md`. A user account is refused with a message saying the skill covers organization pages. A missing page is reported as broken, unless `--init` was passed [S1, S8].
3. By default the page covers the owner's public repositories that are not forks and not archived, excluding the profile repository itself [S2]. The settings file may exclude repositories with a reason [S1].
4. A private repository is never named on the page or in the pull request body, even when the credentials can see it [S2].
5. Nothing in the skill, its references or its scripts names a particular owner or repository. An organization's specifics live in an optional settings file in its `.github` repository [S1].
6. The page's existing structure is the format. The skill keeps headings, ordering and shared text, and changes what the facts contradict. Text the settings mark as shared must stay identical, which keeps sibling pages aligned [S2]. [model-inference: that keeping an arbitrary page's structure works well is unproven beyond the maintainer's two consistent organization pages]
7. `--init` writes a new page in a default layout, distilled from the maintainer's organization format: a header, a status and tag legend, an index by category, and a section per project with its version line and recent changes [S2].
8. A page with no recognisable layout gets the factual checks only, and the run says which layout checks it skipped [model-inference].
9. The checker accounts for every covered repository as listed or excluded, rejects a listed repository that is not public or no longer exists, rejects a version claim that does not match the latest release, rejects a release link that does not resolve, and rejects a badge that points at another owner or repository [S3, S7]. It flags a badge that reads a list by position, because adding an entry to that list changes what it shows [S7].
10. The skill works on a branch and never on the default branch. When an open pull request from an earlier run exists, the skill updates that pull request instead of opening another. When nothing changed, it makes no branch and no pull request [S2, S4].
11. The checker follows the repository's three-state gate contract and proves every rule can fail against a committed sample before it reports clean [S6].
12. The skill must work when run locally by the maintainer, whatever D3 decides about the cloud routines [S4]. [model-inference: whether a cloud routine can load a plugin skill is unverified]

## Acceptance Criteria

**AC-1:** `SKILL.md` carries `disable-model-invocation: true`, `agents/openai.yaml` carries `policy.allow_implicit_invocation: false`, and an eval case whose prompt asks to update an ordinary repository README asserts that the skill is not invoked. [S6]

**AC-2:** (SUPERSEDED 2026-11-07 by AC-14; see Revisions.) Given fixture responses for a user owner and an organization owner, the facts report the type and the profile page path for each. For an owner with no profile page and no `--init`, the facts script exits 2 and names the cause. [S1]

**AC-3:** Given a fixture owner holding a public repository, a fork, an archived repository and a private repository, the facts list only the public one, and the private repository's name appears nowhere in the output. [S2]

**AC-4:** A test fails if `SKILL.md`, a reference or a script contains the name of a fixed owner or repository. The test reads its list of names from its own fixture, so the list is not itself built into the skill. The facts script produces a complete result for a fixture owner with no settings file. [S1]

**AC-5:** Given a page that omits a covered repository, the checker names it. Given a settings file that excludes that repository with a reason, the checker passes it. Given a page that lists a repository the facts say is private or missing, the checker names it. [S3, S7]

**AC-6:** The checker rejects a page whose stated version for a repository differs from that repository's latest release, a release link to a tag that does not exist, and a badge whose URL names another owner or repository. It reports a badge that reads a list by position as a finding. [S7]

**AC-7:** The checker rejects a page or a pull request body that contains the name of a repository the facts list as private. [S2]

**AC-8:** Given a page from which a heading was removed while its repository is still covered, the checker names the heading. Given settings that mark a passage as shared, the checker rejects a page whose copy of that passage differs. [S2]

**AC-9:** For a fixture owner with no profile page, `--init` writes a page in the default layout, and the checker passes it. [S2]

**AC-10:** Given a freeform fixture page, the checker runs the checks of AC-5 to AC-7, skips those of AC-8, and its output names each skipped check. [model-inference]

**AC-11:** `SKILL.md` instructs that the skill never commits to the default branch, that it updates an open pull request from an earlier run in place, and that it makes no branch when nothing changed. A test fails if any of the three instructions is removed. [S2, S4]

**AC-12:** The checker's self-test proves each of its rules fails on a mutation of the committed sample and exits 2 if one does not, and CI runs the self-test and the facts tests. [S6]

**AC-13:** Running `/plab-profile-readme` on one of the maintainer's organizations, once the skill is installed, opens or updates a pull request whose page the checker passes. [model-inference: the live run is this spec's own test design]

**AC-14:** Given fixture responses for an organization owner, the facts report the type and the path `<org>/.github/profile/README.md`. Given a user owner, the facts script exits 2 and says the skill covers organization profile pages. For an organization with no profile page and no `--init`, the facts script exits 2 and names the cause. [S1, S8]

## Behavior / Examples

### Example 1: An organization with a new repository

The maintainer types `/plab-profile-readme example-org`. The facts find a repository that became public last week and is not on the page, and a release newer than the page's version line for another. The skill adds a section for the new repository in the category its description fits, updates the version line and recent changes, runs the checker, and opens a pull request that names each change and the fact behind it.

### Example 2: A pull request is already waiting

A pull request from last week's run is still open. The skill updates that pull request's branch to reflect this week's facts and rewrites its body, so the waiting pull request is current when the maintainer reads it.

### Example 3: A user account is named

The maintainer types `/plab-profile-readme example-user`. The facts find a user account rather than an organization, so the skill stops and says it covers organization profile pages. It makes no branch.

### Example 4: Nothing changed

Every fact matches the page. The skill makes no branch and no pull request and says the page is current.

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

## Sources & Evidence

- **[S1]** The maintainer's rulings in session: on 2026-11-06, the request for a skill that updates each organization's README in a similar format; on 2026-11-07, the name `plab-profile-readme` because a user account has one too, and "it doesn't need to be for the specific repos, it needs to be generally useful as a skill". Class A.
- **[S2]** The two weekly routine prompts that refresh the Prisant Labs and Product on Purpose pages, about 14 KB each. After the organization names are swapped, they differ in 16 lines, which is evidence the format is already general. Maintainer-local, in each profile repository's gitignored `_local/readme/` folder. Class A.
- **[S3]** `_local/profile-readme-automation.md` in the Product on Purpose profile repository, 2026-08-07: a measured drift table, including a public repository missing from the page for three weeks. Maintainer-local. Class A.
- **[S4]** The two refresh pull requests open on 2026-11-06, `prisant-labs/.github` #4 from 2026-10-30 and `product-on-purpose/.github` #6 from 2026-10-23, and the log of the Prisant Labs routine's run that day, which stopped at its first step after 10 seconds. Class A.
- **[S5]** The maintainer's account profile README, `jprisant/jprisant`, whose opening comment says its descriptions, word badges and project list are edited by hand, and names a dated badge removal. Class A.
- **[S6]** `AGENTS.md`: the design frame, the manual-only rulings, and the three-state gate contract; and `skills/plab-ship/`, whose checker and record pattern this skill follows. Class A.
- **[S7]** A comparison on 2026-11-06 of the Prisant Labs page with the organization's public repositories: a stale skill count and version, an unlisted public repository, and a marketplace badge that reads `plugins[1]` by position. Class A.

- **[S8]** The maintainer's ruling in session on 2026-11-07, after the first draft merged: "the org profile should be the focus of the skill because that is a particular kind of profile". Class A.

### Unverified Claims

- Requirement 6: that keeping an arbitrary page's structure works. It is proven only for the maintainer's two consistent organization pages.
- Requirement 8 and AC-10: the handling of a freeform page is a design choice, not observed behaviour.
- Requirement 12: whether a cloud routine can load a plugin skill. The routine prompts also record that organization-level API paths can return 403 in that environment [S2].

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Whether the skill is general or built for the maintainer's own pages | General across organizations, by ruling | Decided | 2026-11-07 |
| D2 | Whether a purely factual update may merge without review | Pending | Open | 2026-11-07 |
| D3 | What happens to the two weekly routines | Pending | Open | 2026-11-07 |
| D4 | Whether the account page ships in 1.0 | Organization pages only, by ruling | Decided | 2026-11-07 |
| D5 | Whether the skill keeps the name `plab-profile-readme` | Pending | Open | 2026-11-07 |

### D1: General or built for the maintainer's pages (Decided)

**Summary.** `AGENTS.md` says not to add configurability for hypothetical third-party users. The maintainer ruled the opposite for this skill: "it needs to be generally useful as a skill" [S1].

**Resolution.** The skill is general, as a deliberate exception, and the exception is kept small: one owner argument, one optional settings file, and no onboarding features. From the same day, the generality is across organizations, and user pages are out of scope (D4).

### D2: Automatic merge of factual updates (Open)

**Summary.** The review queue, not the writing, caused the drift [S4]. Version lines, counts and recent changes are facts the checker can verify, while new or removed repositories and status labels need judgement.

**Options.** A: every update waits for review, and the skill keeps a waiting pull request current. B: an update that changes only facts the checker verified merges through the maintainer's merge check, and anything else waits.

**Recommendation.** A for 1.0, then B once a few reviewed runs show the factual updates are reliable. Both profile repositories are on the maintainer's solo list, so B is possible under the merge rule.

### D3: The two weekly routines (Open)

**Summary.** Two routines refresh the organization pages today [S2].

**Options.** A: convert them to call the skill, if a routine can load it. B: retire them and run the skill by hand. C: keep them as they are.

**Recommendation.** A if the plugin loads in a routine, otherwise B. C keeps two copies of the format rules that will drift from the skill.

### D4: The account page in 1.0 (Decided)

**Summary.** The account page draws on two organizations and uses its own layout [S5].

**Options.** A: 1.0 covers organization and account pages. B: 1.0 covers organization pages, and the account page follows.

**Recommendation (not taken).** A, because the sources setting is small and the account page repeats the organization pages' projects, so the shared-text check is most useful across all three.

**Resolution.** B, and narrower: this spec covers organization pages only, and the account page is a non-goal rather than a later version of this skill [S8]. The maintainer's reason was that an organization page is a particular kind of profile. The `sources:` setting that only the account page needed is dropped.

### D5: The skill's name (Open)

**Summary.** The name `plab-profile-readme` was chosen on 2026-11-07 because a user account has a profile README too [S1]. With user pages out of scope (D4), that reason no longer applies.

**Options.** A: keep `plab-profile-readme`, which leaves room for a later spec that covers user pages. B: rename to `plab-org-profile`, which says what the skill now does.

**Recommendation.** B, because the description is the trigger mechanism and the name should match the scope. The spec's id and folder, `RM-01_profile-readme`, can stay as they are.
