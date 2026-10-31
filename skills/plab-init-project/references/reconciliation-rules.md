# Reconciliation Rules

Rules governing how init-project handles existing files and directories. These rules ensure the skill is non-destructive and idempotent.

## Core Rule

For every file or directory the skill would create:

- **If it exists:** skip and report `Exists: [path]`
- **If it doesn't exist:** create and report `Created: [path]`
- **Never modify, merge, or overwrite** existing content (one exception: the `.gitignore` merge below)

## Exception

### .gitignore - Merge

If `.gitignore` exists, append any missing entries from the base template and project-type-specific entries. Do not duplicate existing entries. Do not remove existing entries. Report as `Updated: .gitignore (appended N entries)`.

**`_local/` is always ensured.** If the existing `.gitignore` does not include `_local/`, append it. This is non-negotiable - `_local/` is always gitignored and init-project guarantees this invariant on every run.

### AGENTS.md is not an exception

An existing `AGENTS.md` is skipped and reported `Exists: AGENTS.md`, like any other file. It holds a repository's highest-priority agent instructions, and no rule defines what a merge into it would add or how a re-run would avoid adding it twice. Earlier text said the workflow appends to it; that instruction had no defined content, so it is removed rather than guessed at.

## Scenarios

### Fresh Project (No Existing Structure)

All files and directories are created. Full report shows `Created:` for every item. This is the simple case.

### Re-Running on Existing Project

Safe to re-run at any time. Every item reports `Exists:`. Summary shows `Created 0, skipped N existing`. No files are modified.

### Upgrading Profiles

Running `--profile public` on a project initialized with `standard`:

1. Skip all existing `standard` structure
2. Create public-only additions: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, .github/ templates
3. Report: `Created N, skipped M existing`

### Onboarding and Pre-Existing Files

The onboarding workflow only modifies files that were created during the current init session. It never touches pre-existing files. If a file was skipped (already existed), onboarding will not offer to modify it.

### Projects with Legacy `docs/decisions/` Directory

Some projects scaffolded by init-project v1.0.0 have `docs/decisions/` instead of the current `docs/internal/decisions/`. init-project does **not** migrate the old directory automatically.

Behavior:

- If `docs/decisions/` exists: leave it alone (skip, do not create, do not migrate)
- If `docs/internal/decisions/` does not exist and profile is standard+: create it with README + seed ADR
- Report both: `Exists: docs/decisions/ (legacy location)` and `Created: docs/internal/decisions/`
- Users with legacy projects should manually move ADR files from `docs/decisions/` to `docs/internal/decisions/` and update internal links. No automation - this is a one-time manual step.

### Projects with Legacy `AGENTS/` Directory (init-project v1.1.x)

Some projects scaffolded by plab-init-project v1.1.x have an `AGENTS/` folder at the repo root with `AGENTS/<agent>/CONTEXT.md`, `AGENTS/<agent>/TODO.md`, and `AGENTS/session-log/`. v1.2.0 used `_agent-context/` instead; v1.3.0 drops the tracked agent-working folder entirely. The skill does **not** migrate the old structure automatically.

Behavior:

- If `AGENTS/` exists: leave it alone (skip, do not create, do not migrate)
- Report: `Exists: AGENTS/ (legacy location)`
- Users with legacy projects should manually move `AGENTS/session-log/` content into `_local/_session-logs/` and archive `AGENTS/<agent>/` content (typically to `_local/backup/`) since per-agent CONTEXT/TODO files duplicate `AGENTS.md` + `CLAUDE.md`. No automation - this is a one-time manual step.

### Projects with Legacy `_agent-context/` Directory (init-project v1.2.x)

Some projects scaffolded by plab-init-project v1.2.x have a tracked `_agent-context/session-log/` folder. v1.3.0 drops this: session logs are now local-only and live at `_local/_session-logs/` (gitignored). The skill does **not** migrate automatically.

Behavior:

- If `_agent-context/` exists: leave it alone (skip, do not create, do not remove)
- Report: `Exists: _agent-context/ (legacy location - no longer scaffolded)`
- Users with legacy projects should manually move `_agent-context/session-log/` content into `_local/_session-logs/` and remove `_agent-context/` from git tracking (add to `.gitignore` or delete and commit). No automation - this is a one-time manual step.

## Reporting

Every init run ends with a summary line:

```
Summary: Created N files/directories, skipped M existing[, updated K].
```

The `updated K` portion only appears when `.gitignore` was modified.
