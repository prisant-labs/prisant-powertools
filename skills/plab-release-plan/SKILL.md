---
name: plab-release-plan
description: "Create and manage a version-scoped release plan folder: scaffold it, promote or demote
  whole effort folders between _unassigned/ and a release, regenerate the aggregation table from
  disk, and report whether a version can be tagged yet against hygiene gates and a doc-update
  checklist. Use when scoping a release, moving efforts in or out of one, or checking release
  readiness: 'create the release plan', 'promote these efforts into v0.5.0', 'can we tag yet',
  'check release readiness'. Do NOT fire on general planning talk, on requests for release notes or
  a changelog, or on questions about what already shipped. Refuses to invent or modify acceptance
  criteria - those live in specs written by /plab-spec; the release plan only aggregates. Explicit
  invocation only: run /plab-release-plan; it does not fire on its own."
argument-hint: "--create vX.Y.Z [--theme <text>] | --promote --from _unassigned --to vX.Y.Z S-NN ... | --demote --from vX.Y.Z [--to _unassigned] S-NN | --update vX.Y.Z | --gate vX.Y.Z"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.6.1"
  updated: 2026-10-30
---

# Release Plan

Aggregate every spec and implementation plan in scope of a release into one self-contained folder. Own the `_unassigned/` -> `plan_NN_<slug>/` promotion ceremony. Gate the tag on hygiene checks + doc-update checklist.

## Subcommand Selection

| Subcommand | When to use |
|-----------|------------|
| `--create vX.Y.Z` | Start a new release plan. Creates the folder, writes the plan document with empty aggregation, scaffolds doc-update checklist + hygiene gates section. |
| `--promote --from _unassigned --to vX.Y.Z S-07 S-09 ...` | Move named per-effort folders into the release. Updates spec frontmatter on each. Refreshes aggregation. |
| `--demote --from vX.Y.Z [--to _unassigned] S-NN` | Reverse of promote. Moves the effort folder back. Clears spec `target-release` / `linked-release`. Default `--to` is `_unassigned`. |
| `--update vX.Y.Z` | Refresh the aggregation table and dynamic frontmatter fields after promotions or spec/plan status changes. Leaves authored sections (theme, decisions, checklist state) untouched. |
| `--gate vX.Y.Z` | Read-only readiness report. Walks hygiene gates and checklist; reports current pass/fail. Does not modify anything. |

## When NOT to Use This Skill

- You're writing the spec or plan itself (use `/plab-spec`, or write the plan against `docs/internal/release-plans/implementation-plan-template.md`)
- You're tagging or pushing (the skill blesses readiness; tagging is a manual human action)
- You're trying to add an AC (refuse; redirect to `/plab-spec --revise`)
- You're modifying CHANGELOG / README / HISTORY content (the skill only manages the *checklist* of what to update, not the content)
- You're auto-promoting based on heuristics (no; explicit human choice required)

## Input Contract (per subcommand)

### `--create vX.Y.Z`

| Input | Required | Notes |
|-------|----------|-------|
| `vX.Y.Z` | Yes | Semver release version. Stored as `target-version:` in frontmatter. **It does not name the folder** (see Folder Naming below) |
| `--theme <text>` | Yes in practice | One-line release theme. The folder slug is derived from it, so `--create` without a theme must ask for one rather than inventing it |
| `--target-date <YYYY-MM-DD>` | No | Optional target ship date for frontmatter |

### `--promote --from _unassigned --to vX.Y.Z S-NN ...`

| Input | Required | Notes |
|-------|----------|-------|
| `--from _unassigned` | Yes (v1) | Source. v1 only supports `_unassigned`; cross-release promote out of scope |
| `--to vX.Y.Z` | Yes | Target release. Must exist (run `--create` first) |
| Effort IDs | Yes | One or more `S-NN`. Each must exist as a folder in `_unassigned/<id>_<slug>/` |

### `--demote --from vX.Y.Z [--to _unassigned] S-NN`

| Input | Required | Notes |
|-------|----------|-------|
| `--from vX.Y.Z` | Yes | Source release |
| `--to _unassigned` | No (defaults to `_unassigned`) | v1 supports only `_unassigned`; direct release-to-release demote out of scope |
| Effort IDs | Yes | One or more `S-NN` currently in the named release |

### `--update vX.Y.Z` and `--gate vX.Y.Z`

| Input | Required | Notes |
|-------|----------|-------|
| `vX.Y.Z` | Yes | Release to refresh or check |

## Folder Naming

**A release folder is named by sequence and theme, never by version:
`plan_NN_<slug>/`, containing `plan.md`.**

| Part | Derivation |
|---|---|
| `NN` | Next unused two-digit sequence: scan `docs/internal/release-plans/` for `plan_(\d\d)_`, take max + 1, zero-padded. Gaps are legal and are never backfilled |
| `<slug>` | `--theme`, kebab-cased, lowercase, punctuation stripped |
| Version | Lives in `target-version:` frontmatter only |

**Why, stated once so it is not re-litigated.** A version in a path is a prediction, and semver is free to invalidate it: any unplanned minor release consumes the number a later plan had reserved. That happened twice in eight releases in this repository, and each time it forced a folder rename plus a cascade of path rewrites (358 references the first time, 140 the second). Naming by sequence makes the version a one-line frontmatter edit instead. This is the same reasoning `_unassigned/` already embodies: when a fact is not yet known, do not encode it in a path.

**Resolving a version argument to a folder.** `--promote --to`, `--demote --from`, `--update`, and `--gate` all still take `vX.Y.Z`, because that is how a maintainer thinks about a release. Resolve it by reading `target-version:` from each `plan_*/plan.md` and matching. A sequence (`05`) or a folder name (`plan_05_reconcile-at-resume`) is also accepted. If a version matches zero folders, refuse and list what exists. **If it matches more than one, refuse**: two plans claiming one version is a real defect and must not be silently disambiguated.

## Output

Per subcommand:

| Subcommand | Writes | Reads |
|-----------|--------|-------|
| `--create` | `plan_NN_<slug>/` folder + `plan.md` | release-checklist.yaml (if present, for checklist extension) |
| `--promote` | Moves effort folders; updates spec frontmatter; refreshes plan's aggregation + dynamic fields | Each effort's `spec.md` (for frontmatter update) |
| `--demote` | Moves effort folders back; clears spec frontmatter fields; refreshes plan | Same |
| `--update` | Aggregation table + dynamic frontmatter (`spec-count`, `plan-count`, `checklist-complete`) | Every effort folder in the release |
| `--gate` | Nothing (read-only) | Plan, every effort's spec + plan, checklist |

## Workflow

### `--create vX.Y.Z`

1. Require `--theme`. Without it the folder slug cannot be derived; ask rather than inventing one.
2. Derive `NN` (max existing sequence + 1) and `<slug>` (kebab-cased theme) per Folder Naming above.
3. Verify no existing `plan_*/plan.md` already carries this `target-version:`. If one does, refuse and name it: two plans claiming one version is the defect this naming scheme exists to prevent.
4. Verify `plan_NN_<slug>/plan.md` does not already exist. If it does, refuse without `--update`.
5. Create `docs/internal/release-plans/plan_NN_<slug>/` if missing.
6. Write `plan.md` inside it (template at `references/plan-template.md`):
   - Frontmatter per `references/frontmatter-schema.md`, including `sequence: NN` and `target-version: vX.Y.Z`
   - Release theme line (from `--theme` or `"<release version> release"`)
   - Empty aggregation table (no efforts yet)
   - Hygiene gates section with default gates listed (all marked N/A while folder is empty)
   - Doc-update checklist with built-in defaults + any items from `docs/internal/release-plans/release-checklist.yaml` `add:` list (see `references/checklist-extension.md`)
7. Report: created path, derived sequence and slug, target version, checklist item count, "next: run `--promote`".

### `--promote --from _unassigned --to vX.Y.Z S-NN ...`

1. Verify each effort id resolves to a folder in `_unassigned/`. Refuse if any are missing.
2. Verify `plan_NN_<slug>/` exists. Refuse if not (instruct to run `--create` first).
3. For each effort:
   - Move `release-plans/_unassigned/<id>_<slug>/` -> `release-plans/plan_NN_<slug>/<id>_<slug>/` (whole folder, atomic per `references/promote-demote.md`)
   - Read the moved `spec.md` frontmatter; set `target-release: vX.Y.Z` and `linked-release: docs/internal/release-plans/plan_NN_<slug>/plan.md`
   - If the folder contains `implementation-plan.md`, update its `linked-release` field to match
4. Run `--update vX.Y.Z` to refresh the aggregation table and dynamic frontmatter fields.
5. Report: per-effort moves, frontmatter updates, current aggregation state.

Per D1 (spec section 9): promote ALLOWS specs with `status: draft`; the hygiene gate (AC-5(a)) catches drafts before tag rather than blocking at promote.

### `--demote --from vX.Y.Z [--to _unassigned] S-NN`

1. Verify each effort id resolves to a folder in `plan_NN_<slug>/`. Refuse if missing.
2. For each effort:
   - Move `release-plans/plan_NN_<slug>/<id>_<slug>/` -> `release-plans/_unassigned/<id>_<slug>/`
   - Clear the spec's `target-release` (set to null) and `linked-release` (set to null)
   - If `implementation-plan.md` exists, clear its `linked-release` too
3. Run `--update vX.Y.Z` to refresh the (now-shrunk) aggregation.
4. Report: per-effort moves, frontmatter clears, current aggregation.

Per D2: `--to` defaults to `_unassigned` when omitted. Direct release-to-release demote and `_shelved/` target are out of scope for v1.

### `--update vX.Y.Z`

1. Read `plan_NN_<slug>/plan.md`.
2. Walk `plan_NN_<slug>/` for per-effort subfolders matching `<id>_<slug>/`. For each: read `spec.md` frontmatter (status, ac-count, title); if `implementation-plan.md` exists, read its frontmatter (status, ac-coverage, phase-count).
3. Regenerate the aggregation table (columns: `id`, `title`, `spec-status`, `plan-status`, `AC-coverage`, `has-plan?`).
4. Update dynamic frontmatter fields: `spec-count`, `plan-count`, `checklist-complete` (computed from the checklist's checkbox state).
5. Leave all other sections (theme, decisions, doc-update checklist text, hygiene gates section) untouched.
6. Report: efforts found, aggregation diff vs previous.

### `--gate vX.Y.Z`

Read-only. Walks:

0. **Emptiness check (precondition).** Count the efforts in scope for the release. If the count is zero, report the release as `INCONCLUSIVE` and do NOT emit PASS lines for gates (a) through (e): those gates iterate per-effort artifacts, so with nothing to iterate they would each report a vacuous PASS that reads as a clean bill of health. State explicitly that (a)-(e) are *unevaluated*, not passing. Still evaluate gate (f) and the doc-update checklist, which do not depend on efforts. See the "Emptiness guard" section of `references/hygiene-gates.md`.
1. Hygiene gates (a) through (f) per `references/hygiene-gates.md`. Report each as PASS / FAIL with the specific cause when FAIL.
2. Doc-update checklist: count checked vs total.
3. Release readiness: READY only when there is at least one effort in scope AND every gate passes AND every checklist item is checked.

Output: structured report; no file modification. An empty release is never READY; it is `INCONCLUSIVE` until efforts are in scope. If a release is intentionally tracked outside the spec chain (as v1.4.0 and v1.5.0 were), gate on (f) plus the checklist alone and record that choice in the plan's Decisions section. The skill never sets `status: released` automatically (the maintainer does that after tagging).

## Hard Constraints

1. **AC live in specs, not in the release plan.** If user input attempts to add an AC, refuse and redirect: "AC belong in the spec. Edit the linked spec or run `/plab-spec --revise`."
2. **Atomicity of promote/demote.** A folder move either completes (spec + plan + supporting all moved, frontmatter updated) or fails with no partial state. See `references/promote-demote.md`.
3. **Aggregation is generated, not authored.** `--update` regenerates the table; never hand-edit aggregation rows. The skill is the only writer of that section.
4. **Status flows up from evidence.** Never auto-set `status: released`. The skill reports readiness; the human acts on it.
5. **Checklist is a gate, not a reminder.** `--gate` reports unchecked items as FAIL. Tag time requires every item checked.
6. **Folder is self-contained.** `plan.md` lives INSIDE `plan_NN_<slug>/`, not as a sibling. The release folder is the unit of release-time freeze.

## Pairings

- **`/plab-spec`** writes `spec.md` into `_unassigned/<id>_<slug>/` (or directly into `plan_NN_<slug>/<id>_<slug>/` if `--target-release` is passed).
- **`docs/internal/release-plans/implementation-plan-template.md`** is the shape `implementation-plan.md` takes. The plan is written into the same per-effort folder as its spec.
- **`/plab-release-plan --promote`** moves committed efforts from `_unassigned/` into the release. The promotion is the explicit commitment to ship.
- **`/plab-release-plan --gate`** is the pre-tag sanity check.

## References

| File | Purpose | Load when |
|------|---------|-----------|
| `references/plan-template.md` | Full output template for `plan.md` (frontmatter + theme + aggregation + checklist + gates) | `--create` |
| `references/frontmatter-schema.md` | `type: release-plan` frontmatter fields, types, validation | `--create`, `--update` |
| `references/aggregation-table.md` | The aggregation table format and what to read from each effort folder | `--update`, `--gate` |
| `references/hygiene-gates.md` | The five default hygiene gates (a)-(e); how each is computed | `--gate` |
| `references/checklist-extension.md` | `release-checklist.yaml` schema and merge rules with built-in defaults | `--create`, `--update` |
| `references/promote-demote.md` | Atomicity rules; frontmatter side effects; failure modes | `--promote`, `--demote` |

