---
id: PH-01
title: "A skill that keeps a GitHub organization's Pages hub true to the organization's live project sites"
type: spec
status: draft
created: 2026-11-08
updated: 2026-11-08
linked-effort: "the maintainer's agreement in session on 2026-11-08 that the organization's profile README and its GitHub Pages hub are two skills sharing one facts script, and the request to specify the second"
linked-plan: null
linked-release: null
ac-count: 11
source-count: 7
requires-human-review: true
spec-dependencies: [RM-01]
target-release: null
priority: P3
---

# Spec: a Pages hub kept true to the organization's live project sites

## Task Summary

**Status:** draft. Nothing is built, and no implementation plan exists
**Last updated:** 2026-11-08 by claude (Opus 5.5), initial draft
**Linked plan:** not yet planned
**Open questions:** 4 (D1 to D4, see Open Questions / Decisions)
**Revisions:** 1

### Acceptance Criteria Fulfillment

- [ ] AC-1: The skill is manual-only in both harnesses and does not fire on a request to edit an ordinary web page
- [ ] AC-2: The facts list every public project site with its real address, and never carry a private repository's name
- [ ] AC-3: A missing hub repository or a hub with Pages turned off is reported, and the run stops without a branch
- [ ] AC-4: A hub with Pages on and no page gets a first page from the built-in template, which the checker passes
- [ ] AC-5: The checker accounts for every live project site, as a card or as excluded with a reason
- [ ] AC-6: The checker rejects a card whose link, path line or repository does not match the facts
- [ ] AC-7: The checker rejects a card whose markup differs from the page's other cards, and reports a title that differs from the site's own heading
- [ ] AC-8: The checker rejects any change outside the card list unless an instruction in the pull request body asks for it
- [ ] AC-9: The skill writes only the page, only on a branch, updates an open pull request in place, and opens nothing when the hub is current
- [ ] AC-10: The checker proves every rule can fail against a committed sample, and CI runs it
- [ ] AC-11: A live run on the Prisant Labs hub opens a pull request the checker passes

### Currently In Progress

None. The spec was written on 2026-11-08. The next steps are the maintainer's answers to D1 to D4, then an implementation plan.

---

## Purpose

An organization's GitHub Pages hub is the page at the organization's own Pages address that links to each project's live site. Prisant Labs has one: `prisant-labs.github.io`, served at `projects.prisantlabs.com`, a hand-written `index.html` with one card per project [S2]. Every card has been added by hand in its own pull request, five pull requests in six weeks [S3].

The hub drifts the same way the profile README does, because nothing rebuilds it. The Ultimate Cable Box documentation site was live from 2026-10-10, and the hub did not link to it until 2026-11-08 [S3]. After that card, the hub's three cards cover the organization's three public repositories with live sites. A fourth live site belongs to a private repository, which is D2 [S4].

This is a separate skill from RM-01 ([plab-org-profile-readme](../RM-01_profile-readme/spec.md)), by the maintainer's agreement [S1]. The two pages differ in what they list, in format and in risk. The README lists every public repository in Markdown on github.com. The hub lists only the projects with a live site, in HTML, and a merge to the hub deploys straight to a public domain [S2, S5]. The two share their facts: both start from the organization's public repositories, and both must keep private repository names off a public surface [S5].

## Scope

### In Scope

1. A new skill, manual-only, invoked with an organization argument and optional free-text instructions. Its name is D4.
2. The organization's Pages hub repository, `<org>/<org>.github.io`, and the one page it serves as the hub's index.
3. A card for each project with a live public Pages site, using the card markup the page already uses.
4. A checker with a self-test against a committed sample.
5. One built-in page template, used only when a hub has Pages turned on and no page yet.
6. The plugin's registration of the skill: `library.json`, the manifests, `AGENTS.md`, the root `README.md`, a usage README, `CHANGELOG.md`, a no-fire eval case and the CI steps.

### Non-Goals

1. **The project sites themselves.** The skill reads each site and never edits a project's repository or its site.
2. **The organization's profile README.** That is RM-01.
3. **Creating a hub repository, turning Pages on, or changing the custom domain.** These are repository settings the maintainer changes. The facts report their state [S4].
4. **Merging or deploying.** The skill opens or updates a pull request and never merges, because a merge deploys to the public domain [S2].
5. **Watching deployments.** A cancelled deployment once left a merged card off the live site until an empty commit redeployed it [S3]. A later version may report that the live page differs from the default branch. This version does not.
6. **Restyling the page or rewriting its wording.** Existing styles, head, footer and card text stay unless a fact contradicts them or an instruction asks for a change.
7. **The launch decision.** The page carries a `noindex` tag with a pre-launch comment [S2]. Only an instruction removes it.
8. **User account sites,** `<user>.github.io`, and hosts other than GitHub Pages.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Owns the hub | Runs the skill with an organization, with or without instructions, and reviews and merges the pull request |
| Running agent (Claude Code or Codex) | Executes the skill | Runs the facts script, edits the page on a branch, runs the checker, opens or updates the pull request |

## Requirements

1. The skill is manual-only in both harnesses, because it writes to a repository whose merge deploys a public site [S6, S2].
2. The facts report the hub repository: whether it exists, whether Pages is on, its source branch and path, and its custom domain [S2, S4].
3. A project site is a candidate for a card when its repository is not a fork, not archived, and not the hub itself, and its Pages site is public and answers with success [S4]. A private repository is never a candidate unless D2 decides otherwise.
4. Each candidate's address comes from GitHub's Pages record for that repository, never from the repository name. One observed site serves from its own custom domain rather than a path under the hub [S4].
5. The facts carry a private repository's name only as a digest, by the same rule as RM-01, so the checker can reject a card for one without the facts naming it [S5]. One private repository has a public site under the hub's domain and is not on the hub [S4]. D2 decides whether it may be.
6. **Every file in the hub repository is publicly served.** The hub's `README.md`, `CNAME` and `.nojekyll` each answered with success on the public domain, although the repository is private [S7]. The skill therefore writes no file to the hub repository except the page, and nothing it writes there names a private repository. Where any skill state lives is D3.
7. A card follows the markup of the page's existing cards, and has a title, a path line, a description and a button that links to the site [S2]. The title matches the site's own heading, and the description is drawn from the repository description, as the latest card was written [S3]. The button label suits the site, such as "Open the demo" or "Read the docs" [S2].
8. Existing cards keep their order, and a new card is added after them, as each card so far was added [S3]. [model-inference: that appending is the maintainer's preferred order is inferred from five pull requests, not stated]
9. A run changes only the card list. The `CNAME` file, the `.nojekyll` file, the `404.html` page, the page head including its `noindex` tag, the styles and the footer stay as they are, unless an instruction asks for a change [S2].
10. A run may carry free-text instructions. The skill applies them, and the pull request body lists instruction-driven changes apart from fact-driven ones. An instruction never overrides requirement 5 or requirement 6 [S5].
11. The checker accounts for every candidate as a card or as excluded with a reason, rejects a card whose link is not a candidate's address, and rejects a card for a repository that is not a candidate [S3, S4]. It follows the repository's three-state gate contract and proves every rule can fail against a committed sample [S6].
12. The skill works on a branch and never on the default branch. When an open pull request from an earlier run exists, the skill updates it instead of opening another. When nothing changed, it makes no branch and no pull request [S5].
13. A hub with Pages on and no page gets a first page from the built-in template, which is the card markup and page shape of requirement 7 [S2]. A missing hub repository, or a hub with Pages off, is reported with the setting the maintainer must change, and the run stops [S4].
14. The facts come from the facts script RM-01 builds, extended with what this skill needs beyond RM-01: whether each repository has Pages, its Pages address, whether the site is public, whether it answers, and the site's own heading. There is no second collector of repository facts [S1, S5]. [model-inference: RM-01's Phase 1 does not produce these fields; where the shared code lives is the implementation plan's choice]
15. The skill's text and scripts name no particular organization or repository [S5]. Whether it is otherwise built for the maintainer's hubs alone or for any organization is D1.

## Acceptance Criteria

**AC-1:** `SKILL.md` carries `disable-model-invocation: true`, `agents/openai.yaml` carries `policy.allow_implicit_invocation: false`, and an eval case whose prompt asks to edit an ordinary web page's `index.html` asserts that the skill is not invoked. [S6]

**AC-2:** Given a fixture organization holding a public repository with a public site under the hub, a public repository whose site uses its own custom domain, a fork with a site, an archived repository with a site, and a private repository with a public site, the facts list the first two as candidates, each with the address from its Pages record, and the private repository's name appears nowhere in the output. [S4, S5]

**AC-3:** Given a fixture organization with no hub repository, and another whose hub has Pages off, the facts report each state with the setting to change, and the skill makes no branch. [S4]

**AC-4:** Given a fixture hub with Pages on and no page, a run writes a page from the built-in template with a card per candidate, and the checker passes it. [S2]

**AC-5:** Given a page that omits a candidate, the checker names the candidate. Given an exclusion of that candidate with a reason, the checker passes the page. [S3, S4]

**AC-6:** The checker rejects a card whose link differs from the candidate's Pages address, a card whose path line differs from its link, and a card for a repository that is archived, a fork, private or without a site. [S2, S4, S5]

**AC-7:** The checker rejects a card whose elements and classes differ from those of the page's other cards, and it reports a card title that differs from the site's own heading as a finding. [S2, S3]

**AC-8:** Given a branch that changes the `noindex` tag, the styles, the footer, `CNAME`, `.nojekyll` or `404.html`, the checker rejects it, unless the pull request body lists an instruction that asks for that change. [S2]

**AC-9:** `SKILL.md` instructs that the skill writes no file to the hub repository except the page, never commits to the default branch, updates an open pull request from an earlier run in place, and makes no branch when nothing changed. A test fails if any of the four instructions is removed. [S5, S7]

**AC-10:** The checker's self-test proves each of its rules fails on a mutation of the committed sample and exits 2 if one does not, and CI runs the self-test and the facts tests. [S6]

**AC-11:** Running the skill on Prisant Labs, once it is installed, opens or updates a pull request on the hub repository whose page the checker passes. Product on Purpose cannot be the live run, because its hub has Pages off [S4]. [model-inference: the live run is this spec's own test design]

## Behavior / Examples

### Example 1: A live site with no card

The maintainer runs the skill on `example-org`. The facts find four public project sites, and the hub has cards for three. The skill adds a card for the fourth after the others, with the site's own heading as its title and the repository description as its text. It runs the checker and opens a pull request that names the new card and the facts behind it.

### Example 2: A site that moved

A project's site moved from a path under the hub to its own custom domain. The facts carry the new address, and the checker rejects the old card's link. The skill updates the card's link and path line, and the pull request says why.

### Example 3: A hub with Pages off

The maintainer runs the skill on an organization whose hub repository exists with Pages off. The skill says that Pages must be turned on in the repository's settings, and it makes no branch.

### Example 4: An instruction

The maintainer runs the skill with "remove the noindex tag, we are launching". The skill removes the tag and its pre-launch comment, adds no card because none is missing, and lists the change under the instruction in the pull request body.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Privacy | No private repository is named on the hub, in any file the skill writes to the hub repository, or in its pull request | [S5, S7] |
| Safety | The skill writes only the page, only on a branch, and never merges | [S2] |
| Cost | Repository and site facts come from one script call | [S6] |
| Portability | The scripts are stdlib Python, use `gh` for GitHub, and work in Claude Code and Codex | [S6] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-11-08 | claude | added | Initial draft, at the maintainer's request after agreeing that the hub is a separate skill from RM-01, and after an advisor review. The series prefix PH is new and is added to `scripts/gen-release-index.py`. |

## Sources & Evidence

- **[S1]** The maintainer's answers in session on 2026-11-08: "I agree with your recommending for two skills", and, asked which spec to write, the new Pages hub spec with RM-01 left unchanged rather than also adding Pages fields to RM-01. Class A.
- **[S2]** The Prisant Labs hub repository as read on 2026-11-08: a private repository holding `index.html` (three cards, each a list item with a linked title, a path line, a description and a button; a `noindex` tag with a pre-launch comment; a footer), `404.html`, `.nojekyll`, `CNAME` set to `projects.prisantlabs.com`, and a one-line `README.md`. Its Pages record is a legacy build from the root of `main` with HTTPS enforced, so a merge to `main` deploys. Maintainer-owned and private, so described here rather than linked. Class A.
- **[S3]** The hub repository's five pull requests, 2026-09-30 to 2026-11-08. Each added or fixed one card by hand. The fifth added the Cable Box card for a site live since 2026-10-10, with its title matching the site's heading and its description drawn from the repository description. The fourth was an empty commit to redeploy after a cancelled deployment. The third records that the repository has no tests or CI. Class A.
- **[S4]** A survey on 2026-11-08 of every repository with Pages in the Prisant Labs and Product on Purpose organizations, through each repository's Pages record and a request to each site. Ten sites are public and each answered 200. One Prisant Labs site belongs to a private repository and is not on the hub. One Product on Purpose site serves from its own custom domain. The Product on Purpose hub repository exists with Pages off and a placeholder README. Class A.
- **[S5]** [RM-01's spec](../RM-01_profile-readme/spec.md): the shared facts, the private-name rule and digests, instruction runs, and the branch and pull request rules. Class A.
- **[S6]** `AGENTS.md`: the design frame, the manual-only rulings, the three-state gate contract, and the `lib/` convention for shared helpers. Class A.
- **[S7]** A request on 2026-11-08 to the hub's public domain for `README.md`, `CNAME` and `.nojekyll`. Each answered 200, so the hub repository's files are public although the repository is private. Class A.

### Unverified Claims

- Requirement 8: that new cards belong after the existing ones is inferred from how five cards were added, not stated by the maintainer.
- Requirement 14: RM-01's facts script does not yet produce the Pages fields, and where the shared code lives is unplanned.
- AC-11: the live run is this spec's own test design.

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Whether the skill is built for the maintainer's hubs or general across organizations | Pending | Open | 2026-11-08 |
| D2 | Whether a private repository's public site may have a card | Pending | Open | 2026-11-08 |
| D3 | Where exclusions and their reasons are recorded | Pending | Open | 2026-11-08 |
| D4 | The skill's name | Pending | Open | 2026-11-08 |

### D1: Built for the maintainer's hubs, or general (Open)

**Summary.** RM-01 is general by the maintainer's ruling, as a deliberate exception to the `AGENTS.md` design frame [S5, S6]. That ruling was for RM-01, and agreeing to two skills is not a ruling on this one [S1]. The only hub observed is one hand-written page with one card shape [S2].

**Options.** A: built for the maintainer's hubs. The page's existing card markup is the format, there is one built-in template for a new hub, and there is no setup interview, but no organization's name is built in. B: general, like RM-01, with built-in standards and a `--setup` interview.

**Recommendation.** A. The design frame applies unless a ruling says otherwise, and with one observed hub there is nothing to choose between. Requirement 15 keeps the skill free of built-in names, so B stays open for a later version.

### D2: A private repository's public site (Open)

**Summary.** One private Prisant Labs repository has a public site under the hub's domain, and the hub has no card for it [S4]. The site's address already shows the repository's name. RM-01 never names a private repository [S5].

**Options.** A: never a candidate. The facts carry its name only as a digest, and the checker rejects a card for it. B: a candidate only when the maintainer lists it by name for this hub. C: a candidate like any public repository, because its site is public.

**Recommendation.** A. The hub leaves it off today, which may be deliberate, and A matches RM-01's rule. Choose B if the maintainer wants that site on the hub.

### D3: Where exclusions are recorded (Open)

**Summary.** Requirement 11 lets a candidate be excluded with a reason, so the reasons need a home. Every file in the hub repository is public [S7].

**Options.** A: an HTML comment in the page, naming only public repositories. One file holds everything, and the comment is public, which is harmless for public names. B: a file in the organization's `.github` repository, beside RM-01's standard file. That repository is public too, and it couples this skill to a format RM-01 has not built. C: no exclusions. Every candidate gets a card.

**Recommendation.** A. It keeps the skill to the one file requirement 6 allows, and a private repository never needs an exclusion, because under D2's option A it is never a candidate.

### D4: The skill's name (Open)

**Summary.** RM-01's name is `plab-org-profile-readme` [S5]. This page is not a profile, and it lists live sites rather than repositories.

**Options.** A: `plab-org-pages-hub`. B: `plab-org-site-hub`. C: `plab-org-profile-site`.

**Recommendation.** A. It names the GitHub feature and the kind of page, and it shares the `plab-org-` start with RM-01, so the two sort together.
