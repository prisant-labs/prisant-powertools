---
status: accepted
date: 2026-10-17
decision-makers: [jp]
consulted: [claude]
---

# 2. The repository stays authoritative over GitHub, with no Decision issue type

## Context and Problem Statement

This repository records what each release contains in files. An effort's folder sits under its release plan's folder, and the effort's frontmatter names the release. GitHub could record the same thing, as issues assigned to milestones. If the two records ever disagree, one of them has to win. Until now the repository has won by construction, because GitHub has never been used as a work surface: the repository has never had an issue. A related question was whether to add a "Decision" issue type to the prisant-labs organization and file the drafted decision issues, as a test of whether GitHub issues would actually get read.

## Decision Drivers

- The plugin has one maintainer and no other contributors.
- Promoting an effort into a release already moves its folder and updates its fields in one commit, and CI checks those files on every pull request.
- Two authorities need sync tooling between them, and that tooling has to be built and then maintained.

## Considered Options

Which record wins:

- Split ownership: the repository owns release membership and GitHub milestones are derived from it, while GitHub owns day-to-day fields such as assignee and comments.
- Repository authority: the repository owns everything, and GitHub becomes close to read-only for planning.
- GitHub authority: milestones own release membership, and the repository imports it.

The Decision issue type:

- Add the Decision type to the organization and file the drafted decision issues.
- File the drafts under the existing Task type and accept the mismatch.
- Add no type and file nothing.

## Decision Outcome

Chosen: repository authority, with no Decision issue type and nothing filed.

The files under `docs/internal/` are the record of what is planned, decided and released. GitHub carries the code, the pull requests, CI and the published Releases, and nothing on GitHub is consulted to settle what a release contains. No sync tooling is built.

### Consequences

- Good: there is one source of truth, and `scripts/frontmatter-check.py` and `scripts/doc-lifecycle-check.py` already check it on every pull request.
- Good: there is no sync tooling to build or to maintain.
- Bad: GitHub's issue and milestone views show nothing about planned work, so a reader who looks only at the GitHub page sees an incomplete picture.
- Neutral: the GitHub Issues integration that the 2026-09-08 charter draft promised is not adopted. The charter effort that [ADR-1 (the rename)](0001-rename-to-prisant-powertools.md) defers has to reconcile with this record.

## More Information

Both decisions are to be revisited if a second contributor appears. The maintainer made them in a decision walk on 2026-10-17 and accepted this record on 2026-10-19.
