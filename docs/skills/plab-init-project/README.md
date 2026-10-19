# plab-init-project

**Version:** 1.3.0
**Source:** [`skills/plab-init-project/`](../../../skills/plab-init-project/)

Initialize agentic development infrastructure in a project. Three profiles (minimal / standard / public), non-destructive, and idempotent.

---

## Getting Started

### Quick Start

In an empty or existing directory:

```
/plab-init-project
```

The skill scaffolds the appropriate folders and seed files. It never overwrites existing files (except `.gitignore`, which it merges).

### Common Invocations

```
# Standard profile (default) - private working projects
/plab-init-project

# Minimal profile - quick experiments
/plab-init-project --profile minimal

# Public open-source profile
/plab-init-project --profile public

# Preview what would be created without writing
/plab-init-project --dry-run

# Specify project type (general | code-python | code-node)
/plab-init-project --type code-python

# Skip the interactive onboarding pass
/plab-init-project --no-onboard
```

### Installation

Install via the prisant-labs marketplace:

```bash
/plugin marketplace add prisant-labs/agent-plugins
/plugin install prisant-powertools@prisant-labs
```

Or symlink into a project:

```bash
ln -s /path/to/prisant-powertools/skills/plab-init-project .claude/skills/plab-init-project
```

### Invocation is manual only

This skill ships with `disable-model-invocation: true`. It never fires on its own. Type `/plab-init-project` to run it.

"init", "initialize", "set up project" and "scaffold" are ordinary words in any conversation about a repository, and this skill writes files into the project root. Requiring an explicit command is what keeps an offhand sentence from scaffolding a directory tree.

---

## When to Use

- A brand-new project with no agentic infrastructure
- An existing repo where you want to add agent context, session logs, decision tracking
- Migrating an older project to the current convention (the skill skips existing files; you choose what to upgrade)
- Standardizing structure across multiple projects you work on

## When NOT to Use

- A repo that already has the structure you want (the skill is safe to re-run, but it does nothing new)
- A repo where the agentic convention differs from this one intentionally (the skill imposes a specific layout)
- You need a project type the skill does not support (`general`, `code-python`, `code-node` are the built-in types; add new ones in `references/project-types.md`)

---

## Three Profiles

| Profile | When to Use | What It Creates (high level) |
|---------|-------------|-------------------------------|
| **minimal** | Experiments, weekend projects, throwaway prototypes | CLAUDE.md, README, CHANGELOG, LICENSE, .gitignore, `_local/` |
| **standard** (default) | Working projects, private repos, real ongoing development | + `AGENTS.md` (open standard), `DESIGN.md`, `docs/internal/decisions/` (MADR v4), `docs/internal/backlog.md`, `docs/internal/release-plans/`, `docs/releases/` |
| **public** | Open source, published repos | + `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/` templates |

`docs/internal/` is always tracked in git. `_local/` is always gitignored.

See [`references/folder-spine.md`](../../../skills/plab-init-project/references/folder-spine.md) for the full tree per profile.

---

## The Three-Files-at-Root Convention (v1.2.0)

Three things sometimes get confused. This skill keeps them distinct:

| Name | What it is | Read by |
|------|-----------|---------|
| `AGENTS.md` (file) | Open standard from the [Agentic AI Foundation](https://agents.md/). README-equivalent for AI agents. 20,000+ repos adopt it. Standard+ profiles. | Any AI agent (Claude, Codex, Cursor, Windsurf, etc.) |
| `CLAUDE.md` (file) | Claude Code's project-specific overlay. Supplements `AGENTS.md`. All profiles. | Claude Code only |
| `_local/_session-logs/` (folder) | Session-log home inside the gitignored scratch root. Created on first use by the skill that writes the log, not scaffolded at init. Per-machine working notes, not shared project artifacts. | Written by `/plab-wrap-session`, read by `/plab-continue-session` |

Plus, untouched by this skill:

| Name | What it is | Read by |
|------|-----------|---------|
| `.claude/agents/` (folder) | Claude Code subagent definitions. Per-project or per-plugin. | Claude Code's subagent system. Not scaffolded by `plab-init-project` |

**v1.2.0 dropped the per-agent `<agent>/CONTEXT.md` and `<agent>/TODO.md` files** that v1.1.x scaffolded. They duplicated `AGENTS.md` + `CLAUDE.md` and added noise. If you need agent-specific scratch (rare), create a folder under `_local/` as needed.

**v1.3.0 retired the `_agent-context/` folder.** It held nothing but `session-log/`, so once session logs moved to `_local/_session-logs/` it was an empty directory in every new project. Existing `_agent-context/` folders are left untouched.

---

## What Standard Profile Creates

```
project-root/
├── CLAUDE.md                            # Claude Code overlay
├── AGENTS.md                            # agents.md open standard
├── DESIGN.md                            # Optional design system (Stitch format)
├── README.md
├── CHANGELOG.md                         # Keep a Changelog format
├── LICENSE                              # MIT default
├── .gitignore                           # includes _local/
├── _local/
│   └── README.md                        # Explains: gitignored scratch
└── docs/
    ├── internal/
    │   ├── backlog.md
    │   ├── decisions/
    │   │   ├── README.md                # MADR v4 contract
    │   │   └── 0001-initial-setup.md    # Seed ADR
    │   └── release-plans/
    │       └── _unassigned/             # Pre-release home for new specs/plans
    └── releases/
```

---

## Reconciliation: Safe to Re-Run

The skill is non-destructive and idempotent. Specifically:

- **Existing files are never overwritten** (one exception: `.gitignore` is merged to add missing entries)
- **Re-running on an existing project** is safe; the skill reports `Exists:` for everything present
- **Upgrading profiles** (minimal -> standard or standard -> public) adds the new profile's files; existing ones stay
- **Legacy projects** with `docs/decisions/` or `AGENTS/` (from v1.0.x or v1.1.x) are left alone. The skill creates the new locations alongside without touching the old. Manual migration is documented in [`reconciliation-rules.md`](../../../skills/plab-init-project/references/reconciliation-rules.md).

---

## Output Shape

The skill does not emit a single document; it scaffolds a folder tree plus seed files into the project root, with `{{VARIABLE}}` placeholders (project name, description, date, year, profile, license) filled at creation time. What it creates grows by profile - each profile is a superset of the one before:

| Element | Profile | Purpose |
|---------|---------|---------|
| `CLAUDE.md` | all | Claude Code-specific overlay (project context, rules, conventions, testing, development) |
| `README.md`, `CHANGELOG.md`, `LICENSE`, `.gitignore` | all | Standard repo files; CHANGELOG seeded in Keep a Changelog format, `.gitignore` always carries a `_local/` entry |
| `_local/` + `_local/README.md` | all | Gitignored per-machine scratch with a README explaining the convention; session logs land in `_local/_session-logs/` on first wrap (not created at init) |
| `AGENTS.md` | standard, public | agents.md open-standard instructions (agent-neutral; Claude rules stay in CLAUDE.md) |
| `DESIGN.md` | standard, public | Seeded design system (palette, typography, spacing, component styles) |
| `docs/internal/decisions/` + `README.md` + `0001-initial-setup.md` | standard, public | MADR v4 ADR directory with a seeded contract README and the first ADR |
| `docs/internal/backlog.md`, `docs/internal/release-plans/_unassigned/`, `docs/releases/` | standard, public | Backlog table and release-planning scaffolding |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.github/` templates | public | Open-source community and GitHub issue/PR templates |

Dry-run and onboarding passes additionally write reports into the gitignored `_local/plab-init-project/`. The full seed-file content for every template lives in [`references/seed-templates.md`](../../../skills/plab-init-project/references/seed-templates.md).

---

## Examples

### Example 1: New Standard Project

```
$ /plab-init-project
> Project name: my-project
> Description: A tool for analyzing survey data

Initializing agentic development infrastructure...
Profile: standard | Type: general

Created: CLAUDE.md
Created: README.md
Created: CHANGELOG.md
Created: AGENTS.md
Created: DESIGN.md
Created: LICENSE
Created: .gitignore
Created: _local/
Created: _local/README.md
Created: docs/internal/decisions/
Created: docs/internal/decisions/README.md
Created: docs/internal/decisions/0001-initial-setup.md
Created: docs/internal/backlog.md
Created: docs/internal/release-plans/
Created: docs/internal/release-plans/_unassigned/
Created: docs/releases/

Summary: Created 18 files/directories, skipped 0 existing.
```

### Example 2: Re-Run on Existing Project

```
$ /plab-init-project

Initializing agentic development infrastructure...
Profile: standard | Type: general

Exists: CLAUDE.md
Exists: README.md
... (everything reports Exists:)

Summary: Created 0 files/directories, skipped 18 existing.
```

### Example 3: Upgrade Minimal to Public

```
$ /plab-init-project --profile public

Initializing agentic development infrastructure...
Profile: public | Type: general

Exists: CLAUDE.md
Exists: AGENTS.md
... (existing standard items reported as Exists)
Created: CONTRIBUTING.md
Created: CODE_OF_CONDUCT.md
Created: SECURITY.md
Created: .github/PULL_REQUEST_TEMPLATE.md
Created: .github/ISSUE_TEMPLATE/
Created: .github/ISSUE_TEMPLATE/bug_report.yml
Created: .github/ISSUE_TEMPLATE/feature_request.yml
Created: .github/ISSUE_TEMPLATE/config.yml

Summary: Created 8 files/directories, skipped 18 existing.
```

---

## Dry-Run and Onboarding

Both produce reports written to `_local/plab-init-project/`:

- **`--dry-run`** walks the full creation sequence but creates nothing. The report lists every file/directory that would be created or skipped.
- **Post-init onboarding** (unless `--no-onboard`) walks the user through customizing the seed files: project purpose, conventions, tech stack, design system. Records answers and actions in an onboarding report.

Both reports live in `_local/`, which is gitignored, so they stay per-machine.

---

## Reference Files

| File | Purpose |
|------|---------|
| [`references/folder-spine.md`](../../../skills/plab-init-project/references/folder-spine.md) | Full directory tree per profile + creation sequence |
| [`references/seed-templates.md`](../../../skills/plab-init-project/references/seed-templates.md) | Every seed file template with `{{VARIABLE}}` substitutions |
| [`references/reconciliation-rules.md`](../../../skills/plab-init-project/references/reconciliation-rules.md) | How the skill handles existing files; legacy directory handling |
| [`references/project-types.md`](../../../skills/plab-init-project/references/project-types.md) | Per-type additions (code-python, code-node) and how to add more |

---

## Hard Constraints

- Never overwrite existing files (except `.gitignore` merge)
- Never auto-commit created files
- Always report what was created and what was skipped
- `.gitignore` always includes a `_local/` entry
- Onboarding only modifies files created during this init session
- Decisions live at `docs/internal/decisions/` - never `docs/decisions/`, never per-agent `DECISIONS.md`
- Session logs go to `_local/_session-logs/` (gitignored); never scaffold `_agent-context/` or `AGENTS/`, both retired

---

## Version History

| Version | Date | Notable change |
|---------|------|----------------|
| 1.3.0 | 2026-08-24 | First release in prisant-utilities. Migrated from a private upstream at version 1.3.0; prior history remains there. Seed templates now name `plab-wrap-session` and `plab-continue-session`, and generated decision records credit `prisant-utilities plab-init-project`. |

Full notes in [`HISTORY.md`](../../../skills/plab-init-project/HISTORY.md).
