# Skill Status

The current configuration of every skill in `prisant-powertools`, as declared in the repository. One row per skill, plus the setup each one needs and where its output lands.

**Plugin version:** 0.10.1 **Skills:** 11 (7 auto-discoverable, 4 explicit-invocation only) **Verified against:** `library.json`, `manifest.generated.json`, and each `skills/*/SKILL.md` **As of:** 2026-10-30

> This file describes what the repository declares, not what is installed on any given machine. To check a local install, read `~/.claude/plugins/installed_plugins.json`.

---

## At a glance

| Skill | Version | Invocation | Argument hint | Output lands in |
|---|---|---|---|---|
| `plab-ai-review` | 1.3.0 | Auto + explicit | `<doc.md> [--reviewer codex\|gpt\|gemini] [--dispatch] [--respond] [--collect] [--close]` | Beside the source doc, plus `_archive/` on `--close` |
| `plab-audit` | 1.1.0 | **Explicit only** | `<path> [--appraise\|--audit\|--roadmap] [--type ...] [--lens=docs] [--out <path>]` | `_output/plab-audit/<repo>_<YYYY-MM-DD>/` |
| `plab-current-status` | 1.0.0 | **Explicit only** | `[<byline>] [--no-fetch]` | `_local/_status/YYYY-MM-DD_<model>_<byline>.md` (gitignored) |
| `plab-continue-session` | 1.6.0 | Auto + explicit | `[--log <path>]` | Nothing. Displays context only |
| `plab-guide` | 2.2.2 | Auto + explicit | `<topic-or-repo-url> [--type repo-url\|tool\|concept] [--out <dir>] [--force]` | `_output/plab-guide/` |
| `plab-init-project` | 1.3.0 | **Explicit only** | `[--profile minimal\|standard\|public] [--type ...] [--agents ...] [--dry-run]` | The target repository root |
| `plab-release-plan` | 1.6.0 | **Explicit only** | `--create \| --promote \| --demote \| --update \| --gate` | `docs/internal/release-plans/plan_NN_<slug>/` |
| `plab-resolve-open-items` | 1.2.0 | Auto + explicit | `[--backlog \| <document>]` | Each item's home document; the walk record and any backlog file in `_local/decisions/` |
| `plab-spec` | 1.3.3 | Auto + explicit | `--effort <id> [--target-release vX.Y.Z] [--revise] [--dry-run]` | `docs/internal/release-plans/_unassigned/` by default |
| `plab-strategy-brief` | 1.1.1 | Auto + explicit | `[paste raw thinking]` | `_output/plab-strategy-brief/` |
| `plab-wrap-session` | 1.8.1 | Auto + explicit | `[mode: quick\|final\|deep\|blocked] [--organize]` | `_local/_session-logs/` (gitignored) |

**Explicit only** means the skill carries `disable-model-invocation: true`. It never fires on its own and is absent from the auto-loaded skill listing. It runs when you type its name and only then. **`plab-init-project`, `plab-audit`, `plab-release-plan` and `plab-current-status` carry it now.** `plab-release-plan` carried it through 1.3.0, was auto-discoverable from 1.4.0 to 1.5.1, and carries it again from 1.6.0, provisionally. `plab-spec` carried it through 1.2.1 and is now auto-discoverable, using an explicit do-NOT-fire clause in its description instead of the binary flag.

---

## Per-skill detail

### `plab-wrap-session` 1.8.1

The most-used skill in the plugin. Writes a structured session log and hands off to `plab-continue-session`.

| Property | Value |
|---|---|
| Default mode | **deep**. Every wrap produces the full template unless the agent records a specific objection in the log justifying a lighter mode |
| Modes | `deep` (default), `quick`, `final`, `blocked`, plus `--organize` |
| Output | `_local/_session-logs/`, flat, archived into `YYYY-MM/` folders by `--organize` |
| Scripts | `derive-log-facts.py`, `check-log.py`, `dash-check.py`, `organize-logs.py`, `path-citation-check.py`, plus `test-derive-log-facts.py`, `test-check-log.py`, and `test-organize-logs.py` |
| Setup required | Python 3 on PATH. No other dependency; the dash gate is pure-Python regex, with no `ripgrep` requirement (that applies only to the repository-wide `scripts/check-dashes.py`, a different script) |
| References | 4 files |
| Paired with | `plab-continue-session`. A session-log format change in one requires a matching change in the other |

One call to `derive-log-facts.py` gathers the frontmatter facts, the previous log's Waiting on You items, and the detection results of a pre-wrap hygiene sweep across five checks (remote divergence, working tree, release state, documentation drift, session-log store). The agent judges and proposes from that output under per-action confirmation, writes the log, then runs one call to `check-log.py` as the Log Self-Check. It runs the two existing canary-proven detector gates (path citations, dashes) exactly as before, plus the decisions-count comparison, summary length, Tier 1 frontmatter completeness, and the Waiting on You rules, and in deep mode the Uncertainty Ledger and What You May Not Realize presence checks. It reports the same three states as the detectors it calls: `clean`, `findings`, `broken`, where `broken` blocks exactly as `findings` does.

### `plab-continue-session` 1.6.0

Reads the newest session log and replays its recorded handoff.

| Property | Value |
|---|---|
| Default behavior | Find newest log, reconcile it against the repository, display resumption context led by what changed, confirm before acting |
| Output | **None.** The output is the displayed context and the act of starting the named next action |
| Scripts | `reconcile.py`, plus `test-reconcile.py` |
| Setup required | Python 3 on PATH and a readable session-log store. Reconciliation runs one non-pruning fetch, with a 20-second timeout |
| References | 4 files |
| Discovery paths | `_local/_session-logs/` (current, including `YYYY-MM/` folders), `_agent-context/session-log/` (legacy), `AGENTS/session-log/` (legacy) |

Deliberately does **not** fire on status questions ("where are we", "what's next"). Those get answered directly. Never auto-executes a continuation prompt without confirmation.

### `plab-ai-review` 1.3.0

Structured peer review of a document by a second model.

| Property | Value |
|---|---|
| Default mode | `--review`, which generates a self-contained review request |
| Modes | `--review` (default, optionally with `--dispatch`), `--collect`, `--respond`, `--close` |
| Output | A review request beside the source doc; `--close` archives the pair into `_archive/` and writes unresolved items to a backlog |
| Scripts | `dispatch.py`, plus `test-dispatch.py`, which CI runs against a fake companion |
| Setup required | **A second model reachable by you.** The handoff is manual by default: you paste the request into a reviewer and bring findings back. With `--dispatch`, the Codex plugin's `codex-companion` helper submits it as a background job, and `--collect` writes the findings back; submit and collect from the same directory |
| References | 6 files, 1 example |
| Reviewers named | `codex`, `gpt`, `gemini` |

`argument-hint` now lists every mode, including `--close`, which it omitted through 1.2.1.

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

### `plab-release-plan` 1.6.0, explicit only

Manages a version-scoped release plan folder.

| Property | Value |
|---|---|
| Invocation | `disable-model-invocation: true`, from 1.6.0 and provisionally. It was auto-discoverable from 1.4.0 to 1.5.1 |
| Subcommands | `--create`, `--promote`, `--demote`, `--update`, `--gate` |
| Output | `docs/internal/release-plans/plan_NN_<slug>/plan.md`. **Folders are named by sequence and theme, not version**; the version lives in `target-version:` frontmatter |
| Scripts | None |
| Setup required | A `release-checklist.yaml` is optional; project rows merge with built-in defaults, and the built-in wins on collision |
| References | 6 files |

Auto-generates the aggregation table from folder contents and enforces hygiene gates plus a doc-update checklist that gates the tag. **Refuses to invent or modify acceptance criteria**; those live in specs, and the release plan only aggregates.

### `plab-resolve-open-items` 1.2.0

Walks the maintainer through what a session has left open, and writes each answer back to where its question came from.

| Property | Value |
|---|---|
| Invocation | **Auto-discoverable from 1.0.0.** Fires on an explicit request to walk what is pending. Do-NOT-fire clauses cover a code walkthrough, a single standalone decision question, and a status question |
| Default behavior | Gather open items from the conversation and from documents the session touched, present them as D, Q and T, read a one-line answer, write back, and write a walk record |
| Named-document mode | `[<document>]` walks one document's "Open Questions / Decisions" section alone |
| Backlog mode | `--backlog` gathers every pending item from the repository's specs, plans and release plans and the newest session log's Waiting on You list in one script call, sorts them into ready, moot and judgment tiers, writes a dated backlog file, and walks at most ten |
| Output | Each answered item's home document, on the three surfaces of `references/decisions-section.md`; a pointer in every other copy; the walk record in `_local/decisions/` (gitignored) |
| Scripts | `walk-check.py`, run by the skill after each write-back and walk record, and by CI against a committed sample. Eight record rules and five write-back rules. `gather-backlog.py` for `--backlog`, with `test-gather-backlog.py`. From 1.2.0 its `--answered-since` argument also returns recent answers and out-of-vocabulary statuses, for `plab-current-status` |
| Setup required | Python 3 on PATH for the self-check. Without it, the walk still runs and reports its write-backs as unverified |
| References | 5 files, plus the plugin-root `references/decisions-section.md` |

**Silence is never acceptance.** An omitted decision is left exactly as found, an omitted question proceeds on its stated default and is recorded as assumed, and only an explicit "ok" or "accept the rest" applies recommendations. A document on another branch is never written; the intended edit is printed instead. Not built yet: automatic GitHub filing, a Projects board, cross-repository gathering, and a web-page rendering.

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

### `plab-current-status` 1.0.0, explicit only

Writes a dated, ranked status snapshot of the current repository.

| Property | Value |
|---|---|
| Invocation | `disable-model-invocation: true`, from 1.0.0 |
| Output | `_local/_status/YYYY-MM-DD_<model>_<byline>.md`. A new file each run; an existing one is never overwritten. It asks before writing when that folder is not gitignored |
| Sections | The Answer, Changed Since Last Status, Waiting on You, What's Next, Pending Decisions, Recent Decisions, Accomplished, Where the Project Is, What I Don't Know |
| Levels | `git-only`, `logs`, `decisions`, reported by the facts script; each missing source is a named gap |
| Scripts | `derive-status-facts.py`, with `test-derive-status-facts.py`; `status-check.py`, its own output gate, which proves eight rules against the committed sample on every run. It calls `plab-resolve-open-items`'s `gather-backlog.py --answered-since` for decisions |
| Setup required | Python 3. `gh` is optional; without it, pull requests become a named gap |
| References | 1 file |

**A ranked list, not an inventory.** Each ranked section shows at most ten items, each with a `Why here:` clause, and names where the rest are. The frontmatter carries the counts, the level and the previous snapshot, so another tool can read the file without parsing its prose.

---

## Shared plugin-root dependencies

Used by skills rather than duplicated inside them:

| Path | Used by | Purpose |
|---|---|---|
| `lib/render-mermaid.py` | `plab-guide` | Mermaid diagram rendering |
| `references/diagrams.md` | `plab-guide` | Diagram conventions |
| `references/decisions-section.md` | `plab-spec`, `plab-strategy-brief`, `plab-resolve-open-items`, `plab-release-plan` | Shared decisions-section format. Resolves at plugin root, not skill root |
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

Every skill carries a `HISTORY.md` and a usage README at `docs/skills/<name>/README.md`. All ten usage READMEs currently state the same version as their skill.

---

## Keeping this file accurate

Every value above should match `library.json`, `manifest.generated.json`, and the frontmatter of each `skills/*/SKILL.md`. This file is hand-maintained, not generated: `scripts/version-parity-check.py` gates the version claims here and in `README.md` against those sources, but it only reports drift, it does not write the correction. When a skill's version, argument hint, or dormancy flag changes, update this file by hand and re-run the gate.
