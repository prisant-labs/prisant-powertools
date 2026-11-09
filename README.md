# prisant-powertools

Fifteen agent skills for the work around the work: scaffolding a repository for agent-assisted development, closing and resuming coding sessions, turning raw thinking into a decision-ready brief, producing guide bundles, getting a second model to review a document, auditing a repository and reordering its backlog on evidence, carrying a feature from written specification through to a taggable release plan, walking the maintainer through the questions and decisions a session leaves open, writing a dated, ranked status snapshot of a repository, auditing a week of your own Claude Code usage, rolling every repository you keep into one weekly pulse, shipping finished branches, and keeping a GitHub organization's profile README to a standard.

Works with Claude Code and Codex.

## Skills

| Skill | What it does | Version |
|---|---|---|
| [`plab-wrap-session`](docs/skills/plab-wrap-session/README.md) | Close a coding session with a structured log: hygiene sweep, evidence index, an uncertainty ledger, and a copy-paste-ready continuation prompt for next time | 1.9.0 |
| [`plab-continue-session`](docs/skills/plab-continue-session/README.md) | Resume from the most recent session log and pick up the named next action | 1.6.2 |
| [`plab-strategy-brief`](docs/skills/plab-strategy-brief/README.md) | Turn a brain dump into a structured, decision-ready analysis document | 1.1.1 |
| [`plab-guide`](docs/skills/plab-guide/README.md) | Generate a guide bundle: standard Markdown, an ADHD-formatted variant, a quick-reference HTML page, and a 1-2 page PDF | 2.2.3 |
| [`plab-ai-review`](docs/skills/plab-ai-review/README.md) | Run a structured peer review of a document with a second model, then synthesise the findings | 1.3.0 |
| [`plab-spec`](docs/skills/plab-spec/README.md) | Write a feature spec: numbered acceptance criteria, each cited to a source, in a per-effort folder | 1.3.4 |
| [`plab-release-plan`](docs/skills/plab-release-plan/README.md) **&sup1;** | Scope a release, promote efforts into it, and gate the tag on hygiene checks and a doc-update checklist | 1.6.2 |
| [`plab-resolve-open-items`](docs/skills/plab-resolve-open-items/README.md) | Walk through the open questions, decisions and tasks a session has raised, take a one-line answer, and write each answer back to its home document | 1.2.0 |
| [`plab-init-project`](docs/skills/plab-init-project/README.md) **&sup1;** | Scaffold agent infrastructure into a repository: AGENTS.md, CLAUDE.md, session logs, decision records | 1.3.1 |
| [`plab-audit`](docs/skills/plab-audit/README.md) **&sup1;** | Audit a repository into a five-file bundle: what it is worth, what is wrong with a file path on every finding, and a ranked roadmap that traces to those findings | 1.1.1 |
| [`plab-current-status`](docs/skills/plab-current-status/README.md) **&sup1;** | Write a dated status snapshot of a repository: the answer first, what changed, what waits on you, what is next, and pending and recent decisions, ranked with reasons | 1.1.0 |
| [`plab-usage-audit`](docs/skills/plab-usage-audit/README.md) **&sup1;** | Audit a week of your own Claude Code usage: spend by lane and by the model that ran, routing, a reconciliation of last week, a scorecard of past recommendations, configuration drift, and ranked recommendations, fact-checked before you read them | 1.1.1 |
| [`plab-project-pulse`](docs/skills/plab-project-pulse/README.md) **&sup1;** | Roll every repository you keep into one weekly pulse: what shipped, what is next, and what waits on you with its age, reusing fresh status snapshots, with a self-contained dashboard | 1.1.1 |
| [`plab-ship`](docs/skills/plab-ship/README.md) **&sup1;** | Ship finished branches: document them in depth across human, technical and agentic docs, verify and screen them, merge what passes the merge check, and report what changed, with an optional release whose version the model decides | 1.0.0 |
| [`plab-org-profile-readme`](docs/skills/plab-org-profile-readme/README.md) **&sup1;** | Keep a GitHub organization's profile README to a standard you choose once, and true to its public repositories, through one checked pull request that it never merges | 1.1.0 |

**&sup1; Manual invocation only.** These eight skills ship with `disable-model-invocation: true`, and with `policy.allow_implicit_invocation: false` in `agents/openai.yaml` for Codex, and never fire on their own in either harness; type `/plab-release-plan`, `/plab-init-project`, `/plab-audit`, `/plab-current-status`, `/plab-usage-audit`, `/plab-project-pulse`, `/plab-ship` or `/plab-org-profile-readme` to run them. `plab-init-project`'s trigger phrases ("init", "initialize", "set up") are too common in ordinary conversation to be safe auto-matches, and it writes files into your repository root. `plab-audit` is gated because an audit is occasional, explicit, and expensive to start by accident, and because "audit" collides with dependency scanning and with audit logs as a runtime feature. `plab-release-plan` is gated again from 1.6.0, provisionally, because it was built for release plans numbered in advance while versions are now assigned at ship time, and because its readiness gate cites two files this repository does not have. `plab-current-status` is gated because two other skills already answer a status question such as "where are we" directly, without writing a file. `plab-usage-audit` and `plab-project-pulse` are gated because each run launches up to ten agents, and because their natural trigger questions, "what have I spent" and "what's next", are answered live by `/usage` and by the session skills. `plab-org-profile-readme` is gated because it opens pull requests in a public repository, and because "update the README" usually means a repository's own README.

`plab-spec` carried the same flag through v0.4.3. It is now auto-discoverable, with an explicit do-NOT-fire clause in its description in place of the flag.

The session pair is a contract: `plab-wrap-session` writes the log that `plab-continue-session` reads. They are versioned and released together.

The document trio is a pipeline: `plab-spec` writes the acceptance criteria, an `implementation-plan.md` is written beside it against the template in `docs/internal/release-plans/`, and `plab-release-plan` aggregates whole effort folders into a release and decides whether it can ship.

## Install

In Claude Code:

```
/plugin marketplace add prisant-labs/agent-plugins
/plugin install prisant-powertools@prisant-labs
```

In Codex, from a terminal:

```
codex plugin marketplace add prisant-labs/agent-plugins
codex plugin add prisant-powertools@prisant-labs
```

Both harnesses read the same marketplace, `prisant-labs`, which pins a released tag. Then invoke any skill by name, for example `/plab-wrap-session`.

To update after a release: in Claude Code, `claude plugin marketplace update prisant-labs` then `claude plugin update prisant-powertools@prisant-labs`, and restart; in Codex, `codex plugin marketplace upgrade prisant-labs`.

## Conventions

**Generated artifacts** are written to `_output/<skill-name>/` relative to your working directory. Every producing skill accepts an explicit destination to override that. Add `_output/` to your `.gitignore`.

That applies to the content-producing skills. The three planning skills write where their artifacts belong instead: `plab-spec` and `plab-release-plan` into per-effort folders under `docs/internal/release-plans/`, and `plab-init-project` into the repository it is scaffolding, with its dry-run and onboarding reports under `_local/plab-init-project/`. `plab-resolve-open-items` writes each answer into the document its question came from, and keeps its walk record in `_local/decisions/`, which is expected to be gitignored.

**Session logs** are written to `_local/_session-logs/`, which is expected to be gitignored. They are local working notes and are not intended to be committed. Once a store has been running a while, `/plab-wrap-session --organize` files logs from closed months into `YYYY-MM/` subfolders; `/plab-continue-session` reads the flat store and those month folders as one set, so resume keeps working either way.

**Toolchain.** `plab-guide` shells out to headless Chrome for PDF rendering, and optionally to `pdfinfo` and `mmdc` (Mermaid CLI). It reports what is missing and degrades gracefully rather than failing. Run `skills/plab-guide/scripts/check-toolchain.sh` to see the current state.

## Provenance

These skills were developed in a private library and carry their version numbers forward. Each one's `HISTORY.md` starts at the version it was migrated at and records what changed for public release.

## License

MIT. See [`LICENSE`](LICENSE).
