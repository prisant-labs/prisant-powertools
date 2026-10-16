# Checklist Extension

How the doc-update checklist combines built-in defaults with project-level extensions.

## Built-in defaults

Hardcoded into the skill. They describe a conventional agent-plugin release contract:

| Doc | Update |
|-----|--------|
| `CHANGELOG.md` | Move items from [Unreleased] to vX.Y.Z section |
| `README.md` | Bump any version references |
| `AGENTS.md` | Reflect new or renamed skills |
| `docs/skills/README.md` | Sync per-skill version table |
| `skills/*/HISTORY.md` | Append the version's changes (per affected skill) |
| `.claude-plugin/plugin.json` | Bump plugin `version` |
| `skills/*/SKILL.md` | Bump per-skill `version` frontmatter (per affected skill) |
| Git tag `vX.Y.Z` | Create the annotated tag once all of the above are done |

These items always appear in the generated checklist. `--create` includes them; `--update` preserves them.

## Project-level extensions

If `docs/internal/release-plans/release-checklist.yaml` exists, its `add:` list is merged into the checklist after the defaults.

### YAML schema

```yaml
# docs/internal/release-plans/release-checklist.yaml
# Optional. Skill applies built-in defaults plus anything listed here.

add:
  - doc: "marketplace.json"
    update: "Description text references new version"
  - doc: ".github/workflows/release.yml"
    update: "Bump version variable if used"

# Future: support 'remove:' to suppress a default if it doesn't apply to this project
```

Schema rules:

- Top-level keys: `add` (list, optional). `remove` is reserved for future use; ignored in v1.
- Each `add` entry is an object with two required string fields: `doc` and `update`.
- Order of `add` entries is preserved in the generated checklist.

## Merge algorithm

```
defaults = [built-in 8 rows]
extensions = read release-checklist.yaml; default to empty if file missing or empty

checklist = defaults + extensions     # extensions appended after defaults

write checklist to plan.md's Doc-Update Checklist section
```

## Per-release tweaks

The generated checklist remains hand-editable. If a release needs a one-off item ("update the migration guide for breaking change in v1.4.0"), edit `plan_v1.4.0.md` directly. The next `--update` will NOT clobber your manual edits to checklist text - it only updates checkbox state for items whose `doc` matches.

If you find yourself making the same manual edit across releases, promote it to `release-checklist.yaml`.

## Removing a default

V1 of the skill does not support `remove:` in the YAML. If a default item doesn't apply to your project (e.g., your project has no `AGENTS.md`), check the box manually with a note: `[x] N/A - project has no AGENTS.md` and move on. The gate counts checked vs total; an N/A note still counts as checked.

If `remove:` becomes a real need (multiple projects need to suppress different defaults), the schema can be extended in a future skill version.

## Why hybrid (built-ins + YAML extension)?

This is the resolution of D3 in the spec:

- **Pure hardcode** would make the skill awkward for any project whose doc set differs from these defaults.
- **Pure config-first** is YAGNI overhead before there's a second consumer.

The hybrid gives correct defaults for a conventional plugin layout plus a clean extension surface for any project whose doc set differs. This repository is itself a worked example: see `docs/internal/release-plans/release-checklist.yaml`, which adds six rows and marks one built-in as not applicable. The YAML config is optional; absent file = empty extension, defaults only.

## When the YAML file is malformed

If `release-checklist.yaml` exists but doesn't parse, refuse to write the checklist. Report the parse error and exit. Don't silently fall back to defaults-only because that hides a configuration problem.

## When the YAML file conflicts with a default

If an `add:` entry has the same `doc` value as a default (e.g., adding `CHANGELOG.md` again), the default wins; the extension is ignored (with a warning). Use `update:` text for clarification, not duplication.
