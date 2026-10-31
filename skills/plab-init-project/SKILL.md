---
name: plab-init-project
description: "Initialize agentic development infrastructure in a project. Creates standardized
  folders and seed files: AGENTS.md (open standard agent instructions), CLAUDE.md (Claude-specific
  overlay), session logs written to gitignored _local/_session-logs/, and MADR v4 decision records.
  Three profiles: minimal (experiments), standard (working projects), public (open source).
  Non-destructive and idempotent - safe to run against an existing repository. Use when setting up
  a new project for AI-assisted development, or when adding agent support to an existing repo.
  Explicit invocation only: run /plab-init-project; it does not fire on its own. Pairs with
  /plab-wrap-session and /plab-continue-session, which write and read the session logs it
  scaffolds."
argument-hint: "[--profile minimal|standard|public] [--type general|code-python|code-node] [--license apache|--no-license] [--no-onboard] [--dry-run]"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.3.1"
  updated: 2026-10-30
---

# Init Project

Create standardized agentic development infrastructure -- folders, seed files, agent context, and documentation scaffolding.

## Input

| Input | Default | Options |
|-------|---------|---------|
| Project root | Current directory | Any writable directory |
| Profile | standard | minimal, standard, public |
| Project type | general | See `references/project-types.md` |
| License | MIT | `--license apache` for Apache-2.0; `--no-license` to skip LICENSE |
| Description | *(ask user)* | Free text |
| `--dry-run` | off | Preview without creating files |
| `--no-onboard` | off | Skip post-init onboarding |

## Profile Selection

| Profile | When to Use | What It Creates |
|---------|-------------|-----------------|
| **minimal** | Experiments, weekend projects | CLAUDE.md, README, CHANGELOG, LICENSE, .gitignore, `_local/` |
| **standard** (default) | Working projects, private repos | + AGENTS.md (open standard), DESIGN.md, `docs/internal/decisions/` (with README), `docs/internal/backlog.md`, `docs/internal/release-plans/`, `docs/releases/` |
| **public** | Open source, published repos | + CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, .github/ templates |

`docs/internal/` is always tracked in git. `_local/` is always gitignored.

### Naming clarification (v1.3.0)

Two things sometimes get confused; this skill keeps them distinct:

- **`AGENTS.md` (file at root)** is the open standard from the Agentic AI Foundation. A "README for AI agents" - what any agent (Claude, Codex, Cursor, Windsurf) reads to understand the project. Standard+ profiles only.
- **`CLAUDE.md` (file at root)** is the Claude Code-specific overlay. Read by Claude Code first; supplements AGENTS.md. All profiles.

Session logs are local-only working notes. They are written to `_local/_session-logs/` (gitignored) and never committed to the repository. The `_agent-context/session-log/` tracked folder that earlier versions scaffolded is no longer created. The `_agent-context/` folder concept is dropped entirely.

## Workflow

1. **Gather input** -- ask for project name and description. Select profile, type, license. Confirm or use defaults.
2. **Pre-flight checks** -- verify project root exists and is writable. Check if git is initialized (warn if not, proceed anyway). Scan for existing agentic structure.
3. **Create structure** -- follow the creation sequence in `references/folder-spine.md`. Directories before files, parent before child. Apply project type additions from `references/project-types.md`.
4. **Populate seed files** -- use templates from `references/seed-templates.md`. Replace all `{{VARIABLE}}` placeholders with actual values.
5. **Reconcile with existing** -- follow rules in `references/reconciliation-rules.md`. Skip existing files, including an existing AGENTS.md, and merge .gitignore (always appends `_local/`).
6. **Report results** -- print Created/Exists/Updated for each item, then summary line.
7. **Onboarding** (unless `--no-onboard`) -- walk user through customizing seed files. Save report to `_local/plab-init-project/plab-init-project_onboard_YYYY-MM-DD.md`.

## Dry-Run Mode

With `--dry-run`: walk the full creation sequence but create nothing. Report `would create:` / `exists:` for each item. Save preview report to `_local/plab-init-project/plab-init-project_dry-run_YYYY-MM-DD.md`.

## Output Format

```
Initializing agentic development infrastructure...
Profile: standard | Type: general

Created: AGENTS.md
Created: CLAUDE.md
Created: _local/
Created: _local/README.md
Created: docs/internal/decisions/
Created: docs/internal/decisions/README.md
Created: docs/internal/decisions/0001-initial-setup.md
Created: docs/internal/release-plans/
Exists:  README.md
...

Summary: Created N files/directories, skipped M existing.
```

## Constraints

- Never overwrite existing files (one exception: `.gitignore` merge - see `references/reconciliation-rules.md`)
- Never auto-commit created files
- Always report what was created and what was skipped
- Create directories before files within them
- Use relative paths in seed file content
- `.gitignore` always includes a `_local/` entry (merge-safe - appended if missing)
- Onboarding only modifies files created during this init session
- Decisions live at `docs/internal/decisions/` - never at `docs/decisions/`, never at per-agent `DECISIONS.md`
- Session logs are local-only; they go to `_local/_session-logs/` (gitignored) and are never scaffolded as a tracked folder
