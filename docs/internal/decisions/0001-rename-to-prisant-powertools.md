---
status: accepted
date: 2026-10-17
decision-makers: [jp]
consulted: [claude]
---

# 1. Rename the plugin to prisant-powertools, changing the name only

## Context and Problem Statement

The plugin, its GitHub repository and its marketplace entry were all named `prisant-utilities`. A rename was first drafted on 2026-09-08 under the target name `prisant-superpowers`, together with a heavier charter that recast the plugin as an end-to-end agentic development workflow. That target name was later dropped in favour of `prisant-powertools`. Three questions had to be settled before the rename could run: how much of the charter changes with the name, which version number the rename ships as, and whether the maintainer's local checkout folder is renamed to match.

## Decision Drivers

- The plugin is built for its maintainer's own use, so continuity for other users carries little weight.
- Every skill's invocation namespace changes with the plugin name, from `prisant-utilities:<skill>` to `prisant-powertools:<skill>`. A permission rule, a hook or a typed command that names a skill by that form stops matching.
- Claude Code keys a project's memory and session transcripts on the absolute folder path, and `plab-continue-session` checks each session log's `repo:` field before it resumes.
- A charter change carried inside a rename pull request would be hard to review and hard to reverse on its own.

## Considered Options

Charter scope:

- Name only: change the plugin name and the one `AGENTS.md` header line that states it, and keep the design frame verbatim.
- Heavy: apply the 2026-09-08 charter draft in the same change.

Version:

- PATCH, on the precedent of v0.4.3, which renamed the marketplace from `agent-plugins` to `prisant-labs` as a patch.
- MINOR, as v0.9.0.
- MAJOR, as v1.0.0, marking the end of pre-1.0 development.

Local checkout folder:

- Keep the old folder name indefinitely, and let the folder name and the repository name diverge.
- Rename the folder in the same migration, by a runbook the maintainer runs from outside the folder.
- Rename the folder later, in a separate session, after the renamed repository has run cleanly for a while.

## Decision Outcome

Chosen: a name-only rename, shipped as MINOR v0.9.0, with the local checkout folder renamed in the same migration.

- **Charter.** The `AGENTS.md` header line is the whole charter edit. The heavier charter becomes its own effort, opened after the maintainer reviews the toolchain and superpowers comparison documents. That effort has to reconcile the draft's promise of GitHub Issues integration with [ADR-2 (the repository is authoritative)](0002-repository-is-authoritative.md).
- **Version.** MINOR, because every skill's invocation namespace changes, and that is more than a patch. The v0.4.3 precedent does not apply: it renamed the marketplace, which changed only the part of the install key after the `@`, so every skill kept its `prisant-utilities:` namespace.
- **Local folder.** The folder is renamed by a runbook the maintainer runs from outside it, after the rename session ends. Claude Code's project folder for the old path, which holds memory and transcripts, is copied to the key for the new path, and the old copy stays as an archive. Every local session log's `repo:` field and folder paths are rewritten, so that `plab-continue-session` still resumes from them. Work aimed at public continuity is skipped.

### Consequences

- Good: the repository, the plugin, the marketplace entry and the local folder carry one name, so nobody has to remember a mapping between them.
- Good: the charter question stays open as a decision of its own instead of being settled by default inside a rename.
- Bad: every existing install has to move by hand. The new key `prisant-powertools@prisant-labs` is installed, and the old key `prisant-utilities@prisant-labs` is uninstalled. A settings entry or hook that names a skill in its namespaced form needs the same edit.
- Bad: Claude Code documents no migration for a path-keyed project folder. The copy is confirmed by observation after the rename, not by documentation.
- Neutral: GitHub redirects the old repository URL, so old links, old clones and the v0.8.1 marketplace pin keep resolving.

### Confirmation

The rename is confirmed when three things are observed after both harnesses restart. The plugin loads under the new name in Claude Code and in Codex. A session in the renamed folder recalls the project's memory and lists its earlier sessions. `plab-continue-session` resumes from a rewritten session log without refusing it as a log from another repository.

## More Information

The maintainer made all three decisions in a decision walk on 2026-10-17 and accepted this record on 2026-10-19. The rename plan of 2026-10-05 had recommended a PATCH version and an unchanged folder name, and the walk overruled both recommendations. The release is described in `CHANGELOG.md` under 0.9.0.
