# Skill Status

The current configuration of every skill in `prisant-utilities`, as declared in the repository. One row per skill, plus the setup each one needs and where its output lands.

**Plugin version:** 0.7.0 **Skills:** 10 (8 auto-discoverable, 2 explicit-invocation only) **Verified against:** `library.json`, `manifest.generated.json`, and each `skills/*/SKILL.md` **As of:** 2026-10-09

> This file describes what the repository declares, not what is installed on any given machine. To check a local install, read `~/.claude/plugins/installed_plugins.json`.

---

## At a glance

| Skill | Version | Invocation | Argument hint | Output lands in |
|---|---|---|---|---|
| `plab-ai-review` | 1.2.1 | Auto + explicit | `<doc.md> [--reviewer codex\|gpt\|gemini] [--respond]` | Beside the source doc, plus `_archive/` on `--close` |
| `plab-audit` | 1.1.0 | **Explicit only** | `<path> [--appraise\|--audit\|--roadmap] [--type ...] [--lens=docs] [--out <path>]` | `_output/plab-audit/<repo>_<YYYY-MM-DD>/` |
| `plab-continue-session` | 1.5.0 | Auto + explicit | `[--log <path>]` | Nothing. Displays context only |
| `plab-guide` | 2.2.2 | Auto + explicit | `<topic-or-repo-url> [--type repo-url\|tool\|concept] [--out <dir>] [--force]` | `_output/plab-guide/` |
| `plab-init-project` | 1.3.0 | **Explicit only** | `[--profile minimal\|standard\|public] [--type ...] [--agents ...] [--dry-run]` | The target repository root |
| `plab-release-plan` | 1.5.1 | Auto + explicit | `--create \| --promote \| --demote \| --update \| --gate` | `docs/internal/release-plans/plan_NN_<slug>/` |
| `plab-resolve-open-items` | 1.0.1 | Auto + explicit | `[<document>]` | Each item's home document; the walk record in `_local/decisions/` |
| `plab-spec` | 1.3.3 | Auto + explicit | `--effort <id> [--target-release vX.Y.Z] [--revise] [--dry-run]` | `docs/internal/release-plans/_unassigned/` by default |
| `plab-strategy-brief` | 1.1.1 | Auto + explicit | `[paste raw thinking]` | `_output/plab-strategy-brief/` |
| `plab-wrap-session` | 1.7.0 | Auto + explicit | `[mode: quick\|final\|deep\|blocked] [--organize]` | `_local/_session-logs/` (gitignored) |

**Explicit only** means the skill carries `disable-model-invocation: true`. It never fires on its own and is absent from the auto-loaded skill listing. It runs when you type its name and only then. **`plab-init-project` and `plab-audit` carry it now.** `plab-spec` and `plab-release-plan` carried it through 1.2.1 and 1.3.0 respectively; both are now auto-discoverable, using explicit do-NOT-fire clauses in their descriptions instead of the binary flag.

---

## Per-skill detail

### `plab-wrap-session` 1.7.0

The most-used skill in the plugin. Writes a structured session log and hands off to `plab-continue-session`.

| Property | Value |
|---|---|
| Default mode | **deep**. Every wrap produces the full template unless the agent records a specific objection in the log justifying a lighter mode |
| Modes | `deep` (default), `quick`, `final`, `blocked`, plus `--organize` |
| Output | `_local/_session-logs/`, flat, archived into `YYYY-MM/` folders by `--organize` |
| Scripts | `dash-check.py`, `organize-logs.py`, `path-citation-check.py`, `test-organize-logs.py` |
| Setup required | Python 3 on PATH. `ripgrep` for the dash gate, which reports `broken` rather than `clean` if absent |
| References | 4 files |
| Paired with | `plab-continue-session`. A session-log format change in one requires a matching change in the other |

Runs a pre-wrap hygiene sweep across five checks (remote divergence, working tree, release state, documentation drift, session-log store) under per-action confirmation, and a Log Self-Check gate before writing. Two of those gates are canary-proven and report three states: `clean`, `findings`, `broken`, where `broken` blocks exactly as `findings` does.

### `plab-continue-session` 1.5.0

Reads the newest session log and replays its recorded handoff.

| Property | Value |
|---|---|
| Default behavior | Find newest log, display resumption context, confirm before acting |
| Output | **None.** The output is the displayed context and the act of starting the named next action |
| Scripts | None |
| Setup required | Nothing beyond a readable session-log store |
| References | 3 files |
| Discovery paths | `_local/_session-logs/` (current, including `YYYY-MM/` folders), `_agent-context/session-log/` (legacy), `AGENTS/session-log/` (legacy) |

Deliberately does **not** fire on status questions ("where are we", "what's next"). Those get answered directly. Never auto-executes a continuation prompt without confirmation.

### `plab-ai-review` 1.2.1

Structured peer review of a document by a second model.

| Property | Value |
|---|---|
| Default mode | `--review`, which generates a self-contained review request |
| Modes | `--review` (default), `--respond`, `--close` |
| Output | A review request beside the source doc; `--close` archives the pair into `_archive/` and writes unresolved items to a backlog |
| Scripts | None |
| Setup required | **A second model reachable by you.** The handoff is manual: you paste the request into a reviewer and bring findings back |
| References | 5 files, 1 example |
| Reviewers named | `codex`, `gpt`, `gemini` |

Known gap: `argument-hint` advertises only `--respond`, so a reader of the hint alone would not learn `--close` exists. The description documents all three.

### `plab-guide` 2.2.2

Generates a paired guide bundle from a topic, tool name, or GitHub URL.

| Property | Value |
|---|---|
| Default behavior | Produces the full four-artifact bundle |
| Output | `_output/plab-guide/`, overridable with `--out` |
| Artifacts | Standard Markdown, ADHD Markdown, quick-reference HTML, and a 1-2 page PDF |
| Scripts | 8, including `check-toolchain.sh`, `render-pdf.sh`, `validate-manifest.py`, `regression-test.sh` |
| Setup required | **A Chromium-based browser** (Chrome, Chromium, or Edge) for PDF rendering. `check-toolchain.sh` detects it during intake and warns without blocking |
| References | 9 files, 1 asset |
| Shared deps | `lib/render-mermaid.py` and `references/diagrams.md` at plugin root |

PDF rendering spends **zero LLM tokens**; the script invokes a local browser binary. The renderer steps `--fit-scale` down from 1.00 to 0.85 until content fits, failing only if it still overflows at minimum scale.

### `plab-strategy-brief` 1.1.1

Turns raw, unstructured thinking into a decision-ready analysis document.

| Property | Value |
|---|---|
| Default behavior | Full structured brief: problem space, analysis, approaches, an 80/20 recommendation, evidence map, open items |
| Output | `_output/plab-strategy-brief/` |
| Scripts | None |
| Setup required | Nothing |
| References | 4 files |

Explicitly not for summarizing already-structured documents, editing polished prose, or pure research queries with no raw thinking supplied.

### `plab-spec` 1.3.3

Writes a feature specification optimized for agent execution.

| Property | Value |
|---|---|
| Invocation | **Auto-discoverable as of 1.3.0.** Fires on an explicit request to write a spec. Do-NOT-fire clause covers passing mentions of "spec", questions about an existing spec, and requests to implement one |
| Default output | `docs/internal/release-plans/_unassigned/<effort>/spec.md` |
| With `--target-release` | Writes straight into `plan_NN_<slug>/` |
| Scripts | None |
| Setup required | Nothing. Creates its folders |
| References | 6 files |

Produces frontmatter, an agent-updated Task Summary block, and numbered acceptance criteria with source citations. Defines **what** to build. The implementation-plan template in `docs/internal/release-plans/` defines how; `/plab-strategy-brief` explores why.

### `plab-release-plan` 1.5.1

Manages a version-scoped release plan folder.

| Property | Value |
|---|---|
| Invocation | **Auto-discoverable as of 1.4.0.** Fires on release scoping, promotion, and readiness checks. Do-NOT-fire clause covers general planning talk, changelog requests, and questions about what shipped |
| Subcommands | `--create`, `--promote`, `--demote`, `--update`, `--gate` |
| Output | `docs/internal/release-plans/plan_NN_<slug>/plan.md`. **Folders are named by sequence and theme, not version**; the version lives in `target-version:` frontmatter |
| Scripts | None |
| Setup required | A `release-checklist.yaml` is optional; project rows merge with built-in defaults, and the built-in wins on collision |
| References | 6 files |

Auto-generates the aggregation table from folder contents and enforces hygiene gates plus a doc-update checklist that gates the tag. **Refuses to invent or modify acceptance criteria**; those live in specs, and the release plan only aggregates.

### `plab-resolve-open-items` 1.0.1

Walks the maintainer through what a session has left open, and writes each answer back to where its question came from.

| Property | Value |
|---|---|
| Invocation | **Auto-discoverable from 1.0.0.** Fires on an explicit request to walk what is pending. Do-NOT-fire clauses cover a code walkthrough, a single standalone decision question, and a status question |
| Default behavior | Gather open items from the conversation and from documents the session touched, present them as D, Q and T, read a one-line answer, write back, and write a walk record |
| Named-document mode | `[<document>]` walks one document's "Open Questions / Decisions" section alone |
| Output | Each answered item's home document, on the three surfaces of `references/decisions-section.md`; a pointer in every other copy; the walk record in `_local/decisions/` (gitignored) |
| Scripts | `walk-check.py`, run by the skill after each write-back and walk record, and by CI against a committed sample. Eight record rules and five write-back rules |
| Setup required | Python 3 on PATH for the self-check. Without it, the walk still runs and reports its write-backs as unverified |
| References | 4 files, plus the plugin-root `references/decisions-section.md` |

**Silence is never acceptance.** An omitted decision is left exactly as found, an omitted question proceeds on its stated default and is recorded as assumed, and only an explicit "ok" or "accept the rest" applies recommendations. A document on another branch is never written; the intended edit is printed instead. Not built yet: the `--backlog` sweep across every spec, plan and log, automatic GitHub filing, a Projects board, cross-repository gathering, and a web-page rendering.

### `plab-init-project` 1.3.0, explicit only

Scaffolds agentic development infrastructure into a repository.

| Property | Value |
|---|---|
| Invocation | `disable-model-invocation: true` |
| Profiles | `minimal` (experiments), `standard` (working projects), `public` (open source) |
| Types | `general`, `code-python`, `code-node` |
| Output | The target repository root |
| Scaffolds | `AGENTS.md`, `CLAUDE.md`, gitignored `_local/_session-logs/`, MADR v4 decision records |
| Scripts | None |
| Setup required | Nothing. Non-destructive and idempotent, safe against an existing repo |
| Dry run | `--dry-run` |
| References | 4 files |

Pairs with `plab-wrap-session` and `plab-continue-session`, which write and read the session logs it scaffolds.

---

### `plab-audit` 1.1.0, explicit only

Audits a repository into a five-file bundle: what it is worth, what is wrong with it, and what to do next.

| Property | Value |
|---|---|
| Invocation | `disable-model-invocation: true` |
| Modes | `--appraise`, `--audit`, `--roadmap`, composable, all three by default |
| Types | `agent-plugin`, `tauri`, `generic`, detected from disk, `--type` overrides |
| Lenses | `--lens=docs` |
| Output | `_output/plab-audit/<repo>_<YYYY-MM-DD>/`, or `--out <path>`. It refuses a location inside the audited repository unless that repository gitignores it |
| Produces | `appraise.md`, `findings.md`, `roadmap.md`, `evidence.md`, `README.md` |
| Scripts | `bundle-check.py`, its own output gate, run by CI against a committed sample. Eight rules, the eighth requiring `appraise.md` to end with its big-picture section |
| Setup required | Nothing. Read-only against the audited repository |
| Dry run | None. It never writes to the repository it audits |
| References | 7 files |

**The deterministic layer produces candidates, not findings.** A candidate becomes a finding only after reconciliation against the repository's own recorded decisions; on the fixture run that specified the skill, that withdrew 7 of 15 candidates including the two highest-ranked. `evidence.md` is produced in every mode, and a tool that is absent or fails is recorded as a coverage gap with its exit code rather than as silence.

---

## Shared plugin-root dependencies

Used by skills rather than duplicated inside them:

| Path | Used by | Purpose |
|---|---|---|
| `lib/render-mermaid.py` | `plab-guide` | Mermaid diagram rendering |
| `references/diagrams.md` | `plab-guide` | Diagram conventions |
| `references/decisions-section.md` | `plab-spec`, `plab-strategy-brief`, `plab-resolve-open-items` | Shared decisions-section format. Resolves at plugin root, not skill root |
| `scripts/check-dashes.py` | CI | Canary-proven dash detector, invoked by `.github/workflows/gate.yml` |

---

## Conventions in force

| Convention | Value |
|---|---|
| Prefix | `plab-` (org-level, prisant-labs) |
| Output root | `_output/<skill-name>/` |
| Session logs | `_local/_session-logs/`, gitignored, never committed |
| Conformance tier | Universal, standard 0.14 |
| Agent targets | `claude`, `codex` |
| License | MIT, on the plugin and every skill |
| Dash rule | No em-dashes or en-dashes anywhere. Enforced in CI and by a local PreToolUse hook |

Every skill carries a `HISTORY.md` and a usage README at `docs/skills/<name>/README.md`. All eight usage READMEs currently state the same version as their skill.

---

## Regenerating this file

Every value above is derived from `library.json`, `manifest.generated.json`, and the frontmatter of each `skills/*/SKILL.md`. Nothing here is authored judgment, so nothing here should be hand-maintained: when a skill version, argument hint, or dormancy flag changes, this file is stale until regenerated from those sources.
