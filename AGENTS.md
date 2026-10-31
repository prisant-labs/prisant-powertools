# AGENTS.md

Agent navigation entrypoint for the `prisant-powertools` plugin.

## What this is

Thirteen general-purpose agent skills for the work around the work: scaffolding a repository for agent-assisted development, closing and resuming coding sessions, turning raw thinking into a decision-ready brief, producing guide bundles, getting a second model to review a document, auditing a repository and reordering its backlog on evidence, carrying a feature from written specification through to a taggable release plan, walking the maintainer through the questions and decisions a session leaves open, writing a dated, ranked status snapshot of a repository, auditing a week of the owner's own Claude Code usage, and rolling every repository the owner keeps into one weekly pulse.

Six of the thirteen ship with `disable-model-invocation: true` and run only when invoked by name. Codex does not read that field, so the same six also carry `agents/openai.yaml` with `policy.allow_implicit_invocation: false`, which Codex reads instead; `scripts/codex-invocation-check.py` fails CI when a skill carries one flag without the other.

`plab-init-project` scaffolds files into a repository root, its trigger phrases ("init", "initialize", "set up") are among the most common words in ordinary conversation, and it is run once per repository rather than routinely.

`plab-audit` is gated by maintainer ruling of 2026-09-19: an audit is occasional and explicit, it is expensive to run by accident, and "audit" collides with dependency scanning and with audit logs as a runtime feature. The counter-argument is recorded in the parent brief and is not dismissed: a manual-only skill cannot displace a manual habit, so if the audit habit does not form, a weak description is no longer a candidate explanation and the dogfood gate is the only adoption signal left.

`plab-release-plan` is gated again from 1.6.0 (v0.8.1), by maintainer ruling of 2026-10-17, recorded as provisional pending a review of the wider release plan. The skill has never been run here, it was built for release plans numbered in advance while versions are now assigned at ship time, and its hygiene gate (f) cites two files this repository does not have, so a readiness check it ran unprompted would fail for reasons unrelated to the release. It dropped the flag in 1.4.0 on the argument below; that argument assumed a skill in use, and this one is not yet.

`plab-current-status` ships gated from its first version, 1.0.0 (v0.10.0), under CS-01 (current status skill). `plab-continue-session` and `plab-resolve-open-items` both answer a status question such as "where are we" directly, and a status skill that fired on those phrases would break that contract. The argument that a manual-only skill cannot displace a manual habit is weaker here than for `plab-audit`, because the habit it replaces is the maintainer typing a request for exactly this document.

`plab-usage-audit` ships gated from its first version, 1.0.0 (v0.11.0), under UA-01 (usage audit skill). A weekly run launches up to nine agents and writes ledger rows, so an accidental run costs real money and pollutes the owner's history; and "how much have I spent" is a question `/usage` answers live, which a skill that fired on it would pre-empt.

`plab-project-pulse` ships gated from its first version, 1.0.0 (v0.11.0), under PP-01 (project pulse skill). "What's next?" is an ordinary status question that `plab-continue-session` and `plab-resolve-open-items` answer directly, and a `--week` run launches up to ten agents across every repository.

`plab-spec` carried the same flag through v0.4.3 and no longer does. Its description now carries an explicit do-NOT-fire clause instead, which is the mechanism that took `plab-continue-session` from over-triggering to correct: a narrowed description is a better instrument than a binary gate, because it can distinguish a request from a mention.

## Design frame

**This plugin is built for its maintainer's own use.** The repository is public because there is no reason for it not to be, not because the skills target an adoption curve. Where a general-purpose choice and a personally-useful choice diverge, the personally-useful one wins.

Practical consequences for anyone proposing or changing a skill here:

- Do not add configurability, onboarding affordances, or compatibility shims for hypothetical third-party users.
- Skill descriptions still matter enormously, and arguably more. The description is the trigger mechanism for the one user who matters; a skill that does not fire is a skill that does not exist.
- Always-on context cost is paid by one person in every session, forever. A rarely-used skill should justify its description budget or ship with model invocation disabled so it runs only on explicit command.
- A skill that goes unused has no value at all. There is no second user to rescue it.

Conventions an agent should follow in this repo:

- Every skill name carries the `plab-` prefix and matches its directory name exactly.
- Skills load shared utilities from the plugin root: `references/` for authoring guidance, `lib/` for executable helpers.
- Generated artifacts go to `_output/<skill-name>/`, which is gitignored. Four skills are the exception. The three planning skills write where their artifacts belong: `plab-spec` and `plab-release-plan` into `docs/internal/release-plans/`, and `plab-init-project` into the repository it scaffolds. `plab-resolve-open-items` writes each answer into the document its question came from, and its walk record into gitignored `_local/decisions/`.
- Never write em-dashes (U+2014) or en-dashes (U+2013). Use " - " or restructure.
- **Do not hard-wrap prose to a fixed width, in any document.** One paragraph is one line, however long. Where a file is genuinely reviewed line by line, break at sentence boundaries instead of at a column. Tables, code blocks, frontmatter, and ASCII diagrams keep their natural line structure; this rule is about prose. Measured 2026-08-27: a one-word edit inside a 75-column hard-wrapped paragraph produces a 4-line diff, against 1 line for either one-paragraph-per-line or one-sentence-per-line, because the reflow cascades. Fixed-width wrapping therefore loses on the only argument made for it, and additionally makes any grep for a phrase crossing the wrap boundary return nothing. This generalizes the session-log rule that `plab-wrap-session` has carried since v0.4.1; that rule was scoped to one file type, which is why the convention leaked back in elsewhere.

## Engineering discipline

The working rules for any agent making changes here. They are self-contained: they were distilled from the `superpowers` discipline skills when that plugin was disabled on 2026-09-01 as a reversible experiment, and they are the rules whether or not it is enabled.

- **No building before agreement.** For anything larger than a trivial fix, state what is being built and why, and get explicit agreement first. Plan mode covers the light case for code. `/plab-strategy-brief` covers the case where the thinking itself deserves a durable document, and `/plab-spec` the case where the requirements need a contract that survives rewrites of the plan beneath them.
- **No fix without a named cause.** Reproduce the problem, state a hypothesis, test the hypothesis, then fix. A patch that works for unexplained reasons is a finding, not a fix.
- **Every change carries its proof.** Where code has tests, the failing test comes first. Where the artifact is a document, a gate, or a detector, the canary comes first, and it must be proven to fail when the rule it guards is removed. A gate that cannot fail is not a gate. A change with no way to show it worked is not done.
- **Never claim done without running the verification and quoting its output.** Failing tests are reported as failing, with the output.
- **Review feedback is verified before it is applied.** Check each claim against the code, and push back with evidence when it is wrong. Agreement without verification is worthless, and a reviewer who is wrong is more expensive to obey than to answer.
- **Work happens on a branch.** Merge via pull request when CI is green. Never commit to `main` directly. **Enforced mechanically since 2026-09-14**, not left to discipline: `main` carries branch protection requiring a pull request, requiring the Standard and Document-lifecycle checks to pass, blocking force pushes and deletions, and applying to administrators. Approvals are set to zero, because a single-maintainer repository that required one would be unmergeable. Note that the Gate workflow already ran on direct pushes to `main`, so CI was never bypassed; it simply reported after the commit had landed, which made it advisory rather than a gate. Protection is what converts it. Linear history is deliberately **not** required, because PR #8 used a merge commit on purpose so that `scripts/doc-lifecycle-check.py` could keep citing `b6c173a` for invariant 9's canary.

The HOW stage of the pipeline carries a template rather than a skill: `docs/internal/release-plans/implementation-plan-template.md`, distilled from the sixteen implementation plans already tracked in that tree. Those sixteen were written with no plan-authoring skill involved and shipped through every hygiene gate, which is why this stage is served by a template and an exemplar corpus instead of machinery.

## Skills

### plab-wrap-session

Document and close agentic coding sessions with structured session logs. Deep mode is the default: a full log with an evidence index, a pre-wrap hygiene sweep (remote divergence, release state, doc drift, working-tree reconciliation, unfiled session logs, all with per-action confirmation), a mandatory "waiting on you" section with file links, an uncertainty ledger pairing confidence against blast radius so that a high-confidence high-impact assumption cannot hide between the two, a source-cited "what you may not realize" section, and a verbose copy-paste-ready continuation prompt in every mode. The facts and the sweep's detection results come from one call to `skills/plab-wrap-session/scripts/derive-log-facts.py` rather than from model recall and one command at a time, because the number of calls sets a wrap's cost. Writes to `_local/_session-logs/`, which is expected to be gitignored. `--organize` runs instead of a wrap and files logs from closed months into `YYYY-MM/` subfolders via `skills/plab-wrap-session/scripts/organize-logs.py`, leaving the current and previous month flat.

**Trigger:** `/plab-wrap-session`, "wrap up", "end of session", "session log", "close out"

---

### plab-continue-session

Resume an interrupted work session by replaying its recorded handoff. The read-side companion to `/plab-wrap-session`. Reads the most recent session log, reports what is blocked on the maintainer, surfaces the outstanding work and the named next action, and confirms before acting. Before presenting the handoff, it reconciles the log against live repository state via `skills/plab-continue-session/scripts/reconcile.py` (commits locally and on the remote, tags, branch existence, cited paths, next-action overlap) and leads the display with what changed since the log; a check that cannot complete names itself rather than reading as clean. Discovery pools the flat store with its `YYYY-MM/` month folders and the legacy locations, newest filename wins. Does not fire on status questions; those get answered directly.

**Trigger:** `/plab-continue-session`, "continue", "resume", "pick up where we left off"

---

### plab-strategy-brief

Transform messy thinking into a structured, decision-ready analysis document. Use when someone provides raw, unstructured thoughts and wants them organised, expanded, and turned into an actionable artifact. Not for summarising already-structured documents or for pure research queries with no raw thinking supplied.

**Trigger:** `/plab-strategy-brief`, "help me think through", "brain dump", "make sense of this", "strategy primer"

---

### plab-guide

Generate a paired guide bundle for any topic: a standard Markdown guide, an ADHD-formatted variant, a quick-reference HTML page, and a 1-2 page PDF operator card. Accepts a repository URL, a tool name, or a concept.

**Trigger:** `/plab-guide`, "create a guide", "build a cheat sheet", "explain X with a quick reference"

---

### plab-ai-review

Generate and synthesise structured peer reviews across models. Three modes: `--review` produces a self-contained review request for a second LLM, optionally dispatching it to Codex in the background with `--dispatch` instead of waiting for a manual paste; `--respond` adds requestor synthesis once the reviewer has filed findings; and `--close` archives the source and review, applies accepted changes, and writes unresolved decisions to a backlog. `--collect` fetches a dispatched job's findings into the document, by itself or through the no-flag auto-detect. Designed to be run in a different harness from the one that produced the document under review.

**Trigger:** `/plab-ai-review`, "review this with a second model", "get a second opinion", "peer review this"

---

### plab-spec

Create a feature specification: the contract between intent and implementation. Writes a `spec.md` into a per-effort folder under `docs/internal/release-plans/`, carrying frontmatter, an agent-updated Task Summary block, numbered acceptance criteria each cited to a source, and links to the related effort and plan. Lands in `_unassigned/` by default, or straight into a release folder with `--target-release vX.Y.Z`. Defines WHAT to build; the implementation-plan template under `docs/internal/release-plans/` defines HOW and `/plab-strategy-brief` explores WHY. Refuses to write implementation steps.

**Invocation:** auto-discoverable as of 1.3.0. Fires on an explicit request to write a spec or turn requirements into acceptance criteria. Its description carries a do-NOT-fire clause for passing mentions of the word "spec", questions about an existing spec, and requests to implement one.

---

### plab-release-plan

Aggregate every spec and implementation plan in scope of a release into one self-contained folder, and gate the tag on hygiene checks plus a doc-update checklist. Five subcommands: `--create` scaffolds the release folder and plan document, `--promote` and `--demote` move whole per-effort folders between `_unassigned/` and a release, `--update` regenerates the aggregation table from disk, `--gate` reports readiness read-only. The aggregation table is generated, never hand-edited. Refuses to add or modify acceptance criteria; those live in specs.

**Invocation:** manual only (`disable-model-invocation: true`) from 1.6.0, provisionally; see the paragraph near the top of this file. `/plab-release-plan`. It was auto-discoverable from 1.4.0 to 1.5.1.

---

### plab-init-project

Initialize agent development infrastructure in a repository: `AGENTS.md`, `CLAUDE.md`, gitignored `_local/_session-logs/`, and MADR v4 decision records. Three profiles: `minimal`, `standard`, `public`. Non-destructive and idempotent, so it is safe to run against a repository that already has some of this. Pairs with `plab-wrap-session` and `plab-continue-session`, which write and read the session logs it scaffolds.

**Invocation:** manual only (`disable-model-invocation: true`). `/plab-init-project`.

---

### plab-audit

Audit a repository and produce a five-file bundle: what it is and is worth, what is wrong with it with a file path on every finding, and what to do next ranked and traceable. Three composable modes, `--appraise`, `--audit` and `--roadmap`, defaulting to all three. Detects repository type from disk (`agent-plugin`, `tauri`, `generic`) and runs that type's deterministic tools first, recording every command and exit code in a coverage statement naming what was read, sampled and skipped, so a missing tool becomes a recorded gap rather than a silence. Every candidate finding is reconciled against the repository's own recorded decisions before it is published; on the fixture run that specified the skill, that step withdrew 7 of 15 candidates including the two highest-ranked. Its own output is gated by `skills/plab-audit/scripts/bundle-check.py`, which CI runs against the committed sample under `skills/plab-audit/examples/sample-bundle/`.

**Invocation:** manual only (`disable-model-invocation: true`). `/plab-audit`.

---

### plab-resolve-open-items

Walk the maintainer through the open questions, decisions and tasks a session has raised, take a one-line answer such as `D1 A, Q1: the NAS`, and write each answer back to its home document. Items are gathered from the conversation and from the "Open Questions / Decisions" sections of documents the session has touched, or from one document the maintainer names. Each answer lands on the three surfaces `references/decisions-section.md` defines, with a `Follow-up` line naming the work the decision causes, and every other copy of the item gets a pointer to its home. Silence is never acceptance: an omitted decision is left as found, and an omitted question proceeds on its stated default, recorded as assumed. Every walk writes a local walk record. Both the write-back and the record are checked by `skills/plab-resolve-open-items/scripts/walk-check.py`, which CI runs against the committed sample under `skills/plab-resolve-open-items/examples/sample-walk/`. `--backlog` sweeps the whole repository instead: `skills/plab-resolve-open-items/scripts/gather-backlog.py` returns every pending item from the specs, plans and release plans and the newest session log's Waiting on You list in one call, the agent sorts them into ready, moot and judgment tiers, writes a dated backlog file to `_local/decisions/`, and walks at most ten.

**Invocation:** auto-discoverable from 1.0.0. Fires on an explicit request to walk what is pending: "walk me through the pending questions and decisions", "resolve open items". Its description carries do-NOT-fire clauses for a code walkthrough, a single standalone decision question, and a status question.

---

### plab-current-status

Write a dated, ranked status snapshot of the current repository to `_local/_status/YYYY-MM-DD_<model>_<byline>.md`: the answer first, what changed since the previous snapshot, what waits on the maintainer, what is next, pending and recent decisions each with a `Why here:` reason, what was accomplished, where the project is, and what is unknown. Every repository fact comes from one call to `skills/plab-current-status/scripts/derive-status-facts.py`, which reports a level (`git-only`, `logs`, `decisions`) and names every missing source as a gap, so the skill works in any git repository. Decisions come from `plab-resolve-open-items`'s `gather-backlog.py --answered-since`. Each snapshot is checked by `skills/plab-current-status/scripts/status-check.py`, whose self-test CI runs against the committed sample under `skills/plab-current-status/examples/sample-status/`. Each run writes a new file and never edits an old one.

**Invocation:** manual only (`disable-model-invocation: true`). `/plab-current-status`.

---

### plab-usage-audit

Run the owner's weekly audit of their own Claude Code usage and write a dated, scrubbed bundle: spend by lane and by the model that actually ran, routing against the owner's rules, a reconciliation of last week against its published figure, a scorecard of past recommendations with the number of audits each open ask has waited, configuration drift against the owner's change register, lessons from the window's session logs, and ranked recommendations each tagged with who acts and a mechanism. `scripts/collect.py` measures transcripts with fixture-proven accounting rules and flags a model family whose newest model never ran; `scripts/derive-audit-facts.py` gathers every other fact in one call and reads credential files for key names and dates only; every agent names a model and receives a shared rules block that forbids opening a credential file; a verifier checks every number and every claim of an approval before the bundle is done. `references/positioning.md` sets out what it adds over `/usage`, `/insights` and the `session-report` plugin. Its output is gated by `skills/plab-usage-audit/scripts/bundle-check.py`, whose self-test CI runs against the committed sample under `skills/plab-usage-audit/examples/sample-bundle/`.

**Invocation:** manual only (`disable-model-invocation: true`). `/plab-usage-audit`.

---

### plab-project-pulse

Roll up every repository under the owner's configured roots into one private weekly pulse: what shipped, what each project says is next, and what waits on the owner, ranked across projects with the age of each waiting item. `scripts/derive-pulse-facts.py` runs discovery, a read-only git sweep, optional `gh` enrichment, activity classification, carry-forward of dormant repositories, and the reading of fresh `plab-current-status` snapshots in one call, so a repository with a current snapshot costs no agent. Scouts read only the remaining active repositories, with a count check and one-tier escalation. `scripts/build-pulse.py` assembles `pulse.json` and writes the state file only after validation; `scripts/render.py` writes a self-contained dashboard. Output is checked by `skills/plab-project-pulse/scripts/pulse-check.py`, whose self-test CI runs against the committed sample under `skills/plab-project-pulse/examples/sample-pulse/`. For one repository in depth, `plab-current-status` is the tool; the pulse reads its snapshots and never writes one.

**Invocation:** manual only (`disable-model-invocation: true`). `/plab-project-pulse`.

---

## Build and validate

- Conformance gate: `node <agent-skills-toolkit>/scripts/check.mjs .`
- CI runs the same gate automatically: `.github/workflows/gate.yml` grades against the Advanced Skill Library Standard on every pull request and every push to `main`, and runs `scripts/check-dashes.py` repo-wide. CI reports; it never fixes, bumps, or tags. The two toolkit-internal scripts it deliberately skips are named and explained in the workflow header.
- `scripts/skill-drift-check.py`, also run by that workflow, mechanizes the hygiene-sweep's Check 4 recipe in CI: a skill whose folder changed since the latest tag must have bumped its own version and recorded it in `HISTORY.md`, reported ADVISORY while no release is in progress and ENFORCED once `library.json`'s own version has moved.
- Skill behaviour suite: `claude plugin eval .` runs the cases in `evals/` (trigger and side-effect checks for every skill), with the exact flags in `evals/README.md`. Always pass `--no-publish`, because the default publishes the report to claude.ai. Run it locally before a release; it is deliberately not in CI, because every case is a full Claude session on the maintainer's credential. `evals/README.md` also gives the measured cost and what the suite does not cover.
- A second workflow publishes releases: `.github/workflows/publish-release.yml` fires when a `v*` tag is pushed, asks `scripts/release-notes-from-changelog.py` for that version's CHANGELOG section, and creates the GitHub Release from it. **This does not weaken the line above.** It chooses no version, writes no file, and creates no tag; the tag is the trigger rather than the product, and the notes are the entry the maintainer already wrote. It exists because a hand-cut tag is only a git ref, so thirteen tags sat with zero Releases until the backfill of 2026-09-14. Fixed-width content is stripped, because release notes are read on a web page and in the mobile app where monospace wraps badly, and a tag with no matching CHANGELOG section fails the run rather than publishing an empty release.
- `scripts/codex-invocation-check.py`, also run by that workflow, fails when a skill is manual-only in one harness and not the other: `disable-model-invocation: true` in `SKILL.md` for Claude Code, `policy.allow_implicit_invocation: false` in `agents/openai.yaml` for Codex. A new manual-only skill needs both.
- The canonical manifest is `library.json`. `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` are generated from it; do not hand-edit them.
- Regenerate native manifests: `node <agent-skills-toolkit>/scripts/generators/gen-manifest.mjs . --write --target=all`

## License

MIT. See `LICENSE`.
