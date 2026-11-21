---
status: accepted
date: 2026-11-21
decision-makers: [jp]
consulted: [claude]
---

# 3. Release on merge through a deterministic pipeline, with plab-ship as the one command

## Context and Problem Statement

A merged skill change in this plugin reaches nobody's session until four more steps happen by hand: bump the version and write the CHANGELOG entry, tag and publish a GitHub Release, repin the marketplace, and update the installs. Each step has been missed at least once. Nineteen merged pull requests sat unreleased before v0.14.0, and thirteen tags sat with no Release until a backfill on 2026-09-14. Releases became sessions of their own, so they were batched, and batching is what made merged work sit unused. The maintainer asked for releases to follow merges, to be deterministic, to run CI and the tests before a repin, and to follow best practice.

## Decision Drivers

- The maintainer wants to defer to the shipping agent's judgment on whether and when changes release, and not to remember release steps.
- Every step that publishes should be a script with an exit code, so that a step cannot be skipped silently.
- The tests must pass on the exact commit that is released.
- The CHANGELOG must stay readable plain English, because `plab-ship`'s report depends on it.
- The plugin should be self-contained, with no release automation borrowed from another repository.

## Considered Options

- Keep releasing by hand, with a checklist.
- Let `/plab-ship` perform every release step itself on every run.
- A deterministic pipeline: the pull request carries its version bump and CHANGELOG entry, and a post-merge workflow reruns the tests, tags, publishes and requests the repin.
- A release bot such as release-please, which keeps a standing release pull request computed from commit messages.

## Decision Outcome

Chosen: the deterministic pipeline, with `/plab-ship` as the maintainer's one command.

The agent decides whether a pull request releases, and gives it a version. The release fires when a merged pull request carries a version with no tag, not on every merge, so internal changes can merge without releasing. The pipeline lives entirely in this repository. A repository opts in by carrying `RELEASING.md` and a release configuration file, and a repository that is not a plugin skips the repin. The requirements are in [RL-01 (release on merge)](../release-plans/_unassigned/RL-01_release-on-merge/spec.md).

### Consequences

- Good: every publishing step is a script, and the tests run on the pull request and again on the merged commit before anything is tagged.
- Good: a release needs one pull request, not a feature pull request followed by a `chore(release)` one.
- Good: any merge that carries a version releases, whoever made it.
- Bad: the maintainer must create and renew a fine-grained token for the marketplace repin.
- Bad: the merge check asks the maintainer on every pull request once the release workflow exists, until the maintainer amends the solo-repo merge rule and its check for opted-in repositories.
- Bad: a bad release is a published version, so the undo is a new patch release rather than deleting a tag.
- Neutral: two pull requests open at once conflict on the version and the CHANGELOG, and the second must rebase.

### Why not the alternatives

- Releasing by hand is today's process, and today's process is the problem.
- `/plab-ship` alone would leave every step to the model, and a merge made outside the skill would release nothing.
- release-please releases only when its own pull request merges, and generates its CHANGELOG from commit subjects. A sibling repository has run it in shadow since July 2026 and, read from its commit subjects (medium confidence), still cut its recent releases by hand.

## More Information

The maintainer made this decision, with six companion decisions on the token, the evals, the version size, the CHANGELOG, the rule amendments and the pipeline's home, in a decision walk from 2026-11-20 to 2026-11-21. Revisit the pipeline's home if a second plugin adopts it.
