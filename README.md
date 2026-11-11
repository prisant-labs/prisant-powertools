<a id="readme-top"></a>

# [prisant-powertools](https://github.com/prisant-labs/prisant-powertools)

**Fifteen agent skills for the work around the work.**

They scaffold a repository for agent-assisted development, close and resume coding sessions, turn raw thinking into a decision-ready brief, produce guide bundles, and get a second model to review a document. They also audit a repository, carry a feature from written specification to a taggable release plan, walk you through the decisions a session leaves open, snapshot a repository's status, audit a week of your own Claude Code usage, roll every repository you keep into one weekly pulse, ship finished branches, and keep a GitHub organization's profile README to a standard.

[**What it is**](#-what-this-is) &nbsp;·&nbsp; [**Install**](#-quick-start) &nbsp;·&nbsp; [**Skills**](#-the-skills) &nbsp;·&nbsp; [**Conventions**](#-conventions) &nbsp;·&nbsp; [**Status**](#-project-status)

<p>
  <img src="https://img.shields.io/badge/status-active-success?style=flat-square" alt="Status: active">
  <a href="https://github.com/prisant-labs/prisant-powertools/releases"><img src="https://img.shields.io/github/v/release/prisant-labs/prisant-powertools?style=flat-square&label=release" alt="Latest release"></a>
  <a href="https://github.com/prisant-labs/prisant-powertools/actions/workflows/gate.yml"><img src="https://img.shields.io/github/actions/workflow/status/prisant-labs/prisant-powertools/gate.yml?branch=main&style=flat-square&label=gate" alt="Gate workflow status on main"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/works%20with-Claude%20Code%20%7C%20Codex-6f42c1?style=flat-square" alt="Works with Claude Code and Codex">
  <a href="https://agentskills.io/specification"><img src="https://img.shields.io/badge/spec-agentskills.io-orange?style=flat-square" alt="Agent Skills specification"></a>
</p>

---

<details>
<summary><strong>Table of Contents</strong></summary>

- [What this is](#-what-this-is)
- [Quick start](#-quick-start)
- [The skills](#-the-skills)
  - [Sessions](#sessions) · [Thinking and documents](#thinking-and-documents) · [Specifications and releases](#specifications-and-releases) · [Repository health](#repository-health) · [Shipping and publishing](#shipping-and-publishing) · [Weekly review](#weekly-review)
  - [How the skills fit together](#how-the-skills-fit-together)
- [Conventions](#-conventions)
- [Project status](#-project-status)
  - [At a glance](#at-a-glance) · [Repo structure](#repo-structure)
- [Provenance](#-provenance)
- [License](#-license)

</details>

---

## 🧰 What this is

`prisant-powertools` is a plugin of agent skills for the work that surrounds writing code: starting and ending sessions, thinking a problem through, writing specifications, checking a repository's health, shipping, and reviewing the week. Every skill name carries the `plab-` prefix, and every skill runs in both Claude Code and Codex from the same files.

The skills are built for their maintainer's own use. The repository is public because there is no reason for it not to be, not because the skills target an adoption curve. Where a general-purpose choice and a personally useful one diverge, the personally useful one wins, so there is no configurability for hypothetical other users.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## ⚡ Quick start

**Claude Code:**

```
/plugin marketplace add prisant-labs/agent-plugins
/plugin install prisant-powertools@prisant-labs
```

**Codex**, from a terminal:

```bash
codex plugin marketplace add prisant-labs/agent-plugins
codex plugin add prisant-powertools@prisant-labs
```

Both harnesses read the same marketplace, `prisant-labs`, which pins a released tag.

**Your first run.** Work in a git repository, and add `_local/` to its `.gitignore` first, because the session skills keep their local notes there. At the end of a coding session, type `/plab-wrap-session`. It writes a session log to `_local/_session-logs/` with what was done, what waits on you, and a continuation prompt, and prints the log's path when it finishes. When you come back, type `/plab-continue-session`. It reads that log, checks it against what has changed in the repository since, and confirms with you before it picks up the named next action.

**To update after a release:** in Claude Code, run `claude plugin marketplace update prisant-labs`, then `claude plugin update prisant-powertools@prisant-labs`, and restart. In Codex, run `codex plugin marketplace upgrade prisant-labs`.

**If a skill does not appear** after an install or an update, restart the harness. A running session keeps the plugin version it started with, and clearing the conversation does not reload it. Each skill's usage guide, linked from its name below, says what the skill is for and, for most skills, when not to use it.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 📚 The skills

Each skill name links to its usage guide. ✋ marks the eight skills that run only when you type their name, for example `/plab-audit`; the rest also fire when a request matches their description. The current version of every skill is listed in [`docs/status-skills.md`](docs/status-skills.md).

### Sessions

- [**plab-wrap-session**](docs/skills/plab-wrap-session/README.md) - Close a coding session with a structured log: hygiene sweep, evidence index, an uncertainty ledger, and a copy-paste-ready continuation prompt for next time.
- [**plab-continue-session**](docs/skills/plab-continue-session/README.md) - Resume from the most recent session log and pick up the named next action.
- [**plab-resolve-open-items**](docs/skills/plab-resolve-open-items/README.md) - Walk through the open questions, decisions and tasks a session has raised, take a one-line answer, and write each answer back to its home document.

### Thinking and documents

- [**plab-strategy-brief**](docs/skills/plab-strategy-brief/README.md) - Turn a brain dump into a structured, decision-ready analysis document.
- [**plab-guide**](docs/skills/plab-guide/README.md) - Generate a guide bundle: standard Markdown, an ADHD-formatted variant, a quick-reference HTML page, and a 1-2 page PDF.
- [**plab-ai-review**](docs/skills/plab-ai-review/README.md) - Run a structured peer review of a document with a second model, then synthesise the findings.

### Specifications and releases

- [**plab-spec**](docs/skills/plab-spec/README.md) - Write a feature spec: numbered acceptance criteria, each cited to a source, in a per-effort folder.
- [**plab-release-plan**](docs/skills/plab-release-plan/README.md) ✋ - Scope a release, promote efforts into it, and gate the tag on hygiene checks and a doc-update checklist.

### Repository health

- [**plab-init-project**](docs/skills/plab-init-project/README.md) ✋ - Scaffold agent infrastructure into a repository: AGENTS.md, CLAUDE.md, session logs, decision records.
- [**plab-audit**](docs/skills/plab-audit/README.md) ✋ - Audit a repository into a five-file bundle: what it is worth, what is wrong with a file path on every finding, and a ranked roadmap that traces to those findings.
- [**plab-current-status**](docs/skills/plab-current-status/README.md) ✋ - Write a dated status snapshot of a repository: the answer first, what changed, what waits on you, what is next, and pending and recent decisions, ranked with reasons.

### Shipping and publishing

- [**plab-ship**](docs/skills/plab-ship/README.md) ✋ - Ship finished branches: document them in depth across human, technical and agentic docs, verify and screen them, merge what passes the merge check, and report what changed, with an optional release whose version the model decides.
- [**plab-org-profile-readme**](docs/skills/plab-org-profile-readme/README.md) ✋ - Keep a GitHub organization's profile README to a standard you choose once, and true to its public repositories, through one checked pull request that it never merges.

### Weekly review

- [**plab-usage-audit**](docs/skills/plab-usage-audit/README.md) ✋ - Audit a week of your own Claude Code usage: spend by lane and by the model that ran, routing, a reconciliation of last week, a scorecard of past recommendations, configuration drift, and ranked recommendations, fact-checked before you read them.
- [**plab-project-pulse**](docs/skills/plab-project-pulse/README.md) ✋ - Roll every repository you keep into one weekly pulse: what shipped, what is next, and what waits on you with its age, reusing fresh status snapshots, with a self-contained dashboard.

<details>
<summary><strong>Why the eight ✋ skills are manual-only</strong></summary>

Each of the eight ships with `disable-model-invocation: true` for Claude Code, and with `policy.allow_implicit_invocation: false` in `agents/openai.yaml` for Codex, so it never fires on its own in either harness.

- **`plab-init-project`** writes files into your repository root, and its trigger phrases ("init", "initialize", "set up") are too common in ordinary conversation to be safe auto-matches.
- **`plab-audit`** is occasional, explicit, and expensive to start by accident, and "audit" collides with dependency scanning and with audit logs as a runtime feature.
- **`plab-release-plan`** is gated again from 1.6.0, provisionally. It was built for release plans numbered in advance, while versions are now assigned at ship time, and its readiness gate cites two files this repository does not have.
- **`plab-current-status`** would collide with two other skills that already answer a status question such as "where are we" directly, without writing a file.
- **`plab-usage-audit`** and **`plab-project-pulse`** each launch up to ten agents per run, and their natural trigger questions, "what have I spent" and "what's next", are answered live by `/usage` and by the session skills.
- **`plab-ship`** merges pull requests and, with `--release`, publishes versions, so an accidental run has effects outside the session.
- **`plab-org-profile-readme`** opens pull requests in a public repository, and "update the README" usually means a repository's own README.

`plab-spec` carried the same flag through v0.4.3. It is now auto-discoverable, with an explicit do-NOT-fire clause in its description in place of the flag.

</details>

### How the skills fit together

**The session pair is a contract.** `plab-wrap-session` writes the log that `plab-continue-session` reads. They are versioned and released together.

**The document trio is a pipeline.** `plab-spec` writes the acceptance criteria, an `implementation-plan.md` is written beside it against the template in `docs/internal/release-plans/`, and `plab-release-plan` aggregates whole effort folders into a release and decides whether it can ship.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🧭 Conventions

- **Generated artifacts** are written to `_output/<skill-name>/` relative to your working directory. Every producing skill accepts an explicit destination to override that. Add `_output/` to your `.gitignore`.
- **Planning and decision skills write where their artifacts belong instead.** `plab-spec` and `plab-release-plan` write into per-effort folders under `docs/internal/release-plans/`. `plab-init-project` writes into the repository it is scaffolding, with its dry-run and onboarding reports under `_local/plab-init-project/`. `plab-resolve-open-items` writes each answer into the document its question came from, and keeps its walk record in `_local/decisions/`, which is expected to be gitignored.
- **Session logs** are written to `_local/_session-logs/`, which is expected to be gitignored. They are local working notes and are not intended to be committed. Once a store has been running a while, `/plab-wrap-session --organize` files logs from closed months into `YYYY-MM/` subfolders. `/plab-continue-session` reads the flat store and those month folders as one set, so resume keeps working either way.
- **Toolchain.** `plab-guide` shells out to headless Chrome for PDF rendering, and optionally to `pdfinfo` and `mmdc` (Mermaid CLI). It reports what is missing and degrades gracefully rather than failing. Run `skills/plab-guide/scripts/check-toolchain.sh` to see the current state.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 📊 Project status

Active, and released in small versions as each skill changes. User-facing changes are in [`CHANGELOG.md`](CHANGELOG.md), and each release has a [GitHub Release](https://github.com/prisant-labs/prisant-powertools/releases) built from its changelog section.

### At a glance

|  |  |
|---|---|
| **Latest release** | [GitHub Releases](https://github.com/prisant-labs/prisant-powertools/releases) |
| **Skills** | 15: seven auto-discoverable, eight manual-only |
| **Skill versions** | [`docs/status-skills.md`](docs/status-skills.md), checked against each `SKILL.md` in CI |
| **Harnesses** | Claude Code and Codex, from the same skill files |
| **Conformance** | Graded in CI by [`.github/workflows/gate.yml`](.github/workflows/gate.yml) against the Advanced Skill Library Standard; the declared Standard and tier are in [`library.json`](library.json) |
| **Behaviour suite** | [`evals/`](evals/), run locally before a release with `claude plugin eval .` |
| **License** | [MIT](LICENSE) |

### Repo structure

```
prisant-powertools/
├── skills/                  # the fifteen skills, one folder each
│   └── plab-<name>/         #   SKILL.md, HISTORY.md, references/, scripts/, examples/
├── docs/
│   ├── skills/              # one usage guide per skill
│   ├── status-skills.md     # every skill's current version, invocation and output location
│   └── internal/            # specs, implementation plans and release plans
├── references/              # shared authoring guidance the skills load
├── lib/                     # shared executable helpers
├── scripts/                 # CI gates: dashes, version parity, skill drift, doc lifecycle
├── evals/                   # trigger and side-effect cases for every skill
├── .github/workflows/       # the gate, and the release publisher
├── library.json             # the canonical manifest
├── AGENTS.md                # agent instructions (CLAUDE.md points here)
└── CHANGELOG.md             # version history
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 🧾 Provenance

These skills were developed in a private library and carry their version numbers forward. Each one's `HISTORY.md` starts at the version it was migrated at and records what changed for public release.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## 📄 License

MIT. See [`LICENSE`](LICENSE).

<p align="center">
  <strong>Built by <a href="https://github.com/prisant-labs">Prisant Labs</a></strong><br>
  <sub>Skills for the work around the work</sub>
</p>

<div align="right"><a href="#readme-top">Back to top ↑</a></div>
