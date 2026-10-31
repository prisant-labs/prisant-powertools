---
id: UA-01
title: "plab-usage-audit: what agent usage cost, whether past changes worked, and what to change next"
type: spec
status: committed
created: 2026-10-30
updated: 2026-10-30
linked-effort: "the maintainer's instruction of 2026-10-30 in session to enrich and build the two audit skills, and the maintainer-local packaging analysis of 2026-10-16 with its ruling of 2026-10-30 (two skills, scripts first)"
linked-plan: implementation-plan.md
linked-release: null
ac-count: 24
source-count: 12
requires-human-review: true
target-release: null
priority: P2
spec-dependencies: ["PP-01"]
---

# Spec: plab-usage-audit, a weekly audit of the owner's own agent usage

## Task Summary

**Status:** committed, built on `feat/audit-skills`; the first live weekly run (AC-24) is still to come
**Last updated:** 2026-10-30 by claude (Opus 5.5), written under the maintainer's instruction to enrich the two audit-skill specs and build them
**Linked plan:** `implementation-plan.md` in this folder
**Open questions:** 6, each built on its recommendation as a working default and awaiting ratification (see Open Questions / Decisions)
**Revisions:** 2

### Acceptance Criteria Fulfillment

- [x] AC-1: The skill is manual-only and does not fire on a usage question
- [x] AC-2: A response split across content-block records counts once
- [x] AC-3: Advisor iterations are priced apart from executor tokens
- [x] AC-4: An unpriced model adds no dollars and makes the collector exit 1
- [x] AC-5: Local days follow the configured IANA zone across a daylight-saving change
- [x] AC-6: Copied transcript folders are counted once
- [x] AC-7: Task-notification records are not counted as user prompts
- [x] AC-8: Responses are reported by the model that ran, and an unseen newest model is flagged
- [x] AC-9: Every count field says whether it is de-duplicated
- [x] AC-10: A session spanning both weeks carries its cost per week
- [x] AC-11: No shipped file carries an owner-specific string
- [x] AC-12: Ledger rows follow schema 2 and a duplicate row is refused
- [x] AC-13: The ledger reader returns the newest row per week
- [x] AC-14: `--reproduce` re-runs a ledger row's method and names any difference
- [x] AC-15: The audit facts come from one script call and never contain a credential value
- [x] AC-16: Workflow costs that do not add up to the workflow lane are reported
- [x] AC-17: Every agent in the workflow reference names a model, and none may open a credential file
- [x] AC-18: The bundle carries a verification record listing every correction
- [x] AC-19: Every recommendation carries an id, a handle, who acts and a mechanism
- [x] AC-20: The scrub leaves no private pattern and every JSON file still parses
- [x] AC-21: The bundle checker proves each rule can fail against its committed sample
- [x] AC-22: Output inside an unignored folder of a git repository is refused unless opted in
- [x] AC-23: The positioning reference names each native tool and what the audit adds
- [ ] AC-24: A live weekly run on the maintainer's machine produces a bundle the checker passes

### Currently In Progress

Built on 2026-10-30 on `feat/audit-skills`. Evidence: AC-2 to AC-11 by `test-collect.py` (76 checks, one synthetic fixture per accounting rule, the daylight-saving week included); AC-12 to AC-14 by `test-ledger.py` (27 checks); AC-15 and AC-16 by `test-derive-audit-facts.py` (59 checks); AC-17 by `test-workflow-reference.py`; AC-18, AC-19 and AC-21 by `bundle-check.py --self-test`, whose mutations make each of rules R1 to R9 fail against the committed sample; AC-20 and AC-22 by `test-scrub.py` (19 checks); AC-23 by `references/positioning.md`. A live run of the deterministic half on the maintainer's machine, over two weeks that had already been audited by hand, reproduced both weekly totals to the cent and found three defects that the fixtures had missed (an unexpanded `~`, a zero-token `<synthetic>` model, an ignored exclude list), each now fixed and tested. AC-1's eval case exists but the eval suite has not been run, because each case is a full session on the maintainer's credential. Still open: AC-24, the first live weekly run with agents, which waits for the owner's next audit day because it measures a real week.

---

## Purpose

The maintainer wants to know, each week, what their agent usage cost, what it produced, which of their earlier changes worked, and the few things to change next, each with evidence they can check [S1]. Ten weekly audits between August and October 2026 answered that question by hand, in the maintainer's private configuration repository. Only the collector script was reused between them; each run rewrote its agent prompts and typed in facts by hand, about an hour of edits on 2026-10-30 [S2].

The hand-run audits also show what goes wrong without a skill. The collector overcounted tokens about 2.2 times until 2026-09-25, missed the advisor's cost until 2026-10-02, and double-counted copied transcript folders until 2026-10-23 [S2]. On 2026-10-30 the brief workers made six factual errors, one of them an invented approval, and the main loop's own draft held five more that a verifier caught [S3]. For two weeks every Sonnet worker ran an older model than requested, and nothing in the collector could have shown it, because it reported requested models [S3]. A skill with fixtures, a reproduce mode, a model-that-ran check and a mandatory verification stage closes each of those classes of error.

### Positioning against the native tools

The maintainer's condition for this skill is that it expands thoughtfully and substantially on what Claude Code already provides [S1]. Each native tool answers one question about the present; none keeps structured history, exports data across weeks, or checks whether a past change worked [S4, S5]. `references/positioning.md` carries the full comparison. In short:

| Tool | Question it answers | What this skill adds |
|---|---|---|
| `/usage` (also `/cost`, `/stats`) | What am I spending now, and how close am I to plan limits? | Weekly history of the same measures, by lane and by the model that ran, plus whether settings changed without a record |
| `/insights` | How do I work, and which features should I try? | A scorecard of whether past recommendations were adopted, and lessons read from the owner's own session logs |
| The `session-report` plugin | Where did the tokens go in this window? | Dollars by model and lane, the advisor as its own line, calendar weeks in local time, reconciliation against last week |

The rule that follows: every section of the bundle answers a question none of those tools answers, and where one of them already answers a question, the bundle points to it instead of repeating it [S1].

## Scope

### In Scope

1. A new skill, `skills/plab-usage-audit/`, manual-only, with `SKILL.md`, `HISTORY.md`, references and a committed synthetic sample bundle.
2. A stdlib-only collector, `scripts/collect.py`, ported from the maintainer's hand-run collector with the changes in Requirements 1 to 11.
3. A stdlib-only ledger tool, `scripts/ledger.py`, for schema 2 rows.
4. A stdlib-only facts script, `scripts/derive-audit-facts.py`, that gathers in one call every fact the main loop used to type by hand.
5. A stdlib-only scrub, `scripts/scrub.py`, and a bundle checker, `scripts/bundle-check.py`, with a self-test.
6. A copy of the shared git sweep from `plab-project-pulse` (PP-01 contract C2), for the bundle's "what shipped" section.
7. The `--weekly` mode: collect, reconcile, sweep, read session logs or take a digest, write briefs, write the bundle, verify, scrub, check.
8. The plugin's registration of the skill: `library.json`, the regenerated manifests, `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/skills/plab-usage-audit/README.md`, an eval case and the CI steps.

### Non-Goals

1. **The silent `--pulse` threshold check and the monthly `--deep` mode.** Both are later versions; the ledger fields they need ship now [S2].
2. **Billing.** Dollar figures are list-price equivalents. A subscription's real charge comes from elsewhere, and every dollar table says so [S2].
3. **Changing configuration.** The skill recommends; the owner decides; an agent applies a change in a separate step [S2].
4. **Portfolio status.** What each repository says is next belongs to `plab-project-pulse` (PP-01). This skill keeps a thin "what shipped" section [S6].
5. **Codex usage in v1.** See D4.
6. **Live views.** Current-session spend and plan-limit bars are `/usage`'s job [S4].
7. **Committing or pushing.** The skill never commits, pushes or publishes.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| The owner | Reads the bundle, answers its asks, approves changes | Types `/plab-usage-audit`, optionally with a window |
| The main loop | Runs the scripts, launches the agents, writes the bundle, corrects the workers | Follows `SKILL.md` |
| Log readers | Turn the window's session logs into digest records when no digest is supplied | Launched with an explicit model, at most two |
| Brief workers | Write the usage, scorecard and config briefs from the facts | Launched with an explicit model, three in parallel |
| The verifier | Checks every number and every claim about a decision against its source | Launched with an explicit model, after the bundle is written |
| `plab-project-pulse` | Supplies the session-log digest and the sweep when it ran first | Files passed by path |

## Requirements

**The collector**

1. The collector applies these accounting rules, each proven by a fixture: count a response once per message id and request id; attribute by message time with a frozen cutoff; split lanes into main, subagent and workflow, and populations into interactive and automated; price from a dated price file and never by a prefix guess; price cache writes by their recorded TTL; count advisor iterations separately at the advisor's rates; measure context depth from the largest executor iteration; count compactions from boundary records only; find child transcripts recursively [S2, S7].
2. Local days come from the configured IANA zone through `zoneinfo`, never a fixed offset [S7].
3. A transcript folder that is a copy of another, holding the same session files, is counted once. The collector reports each copy it skipped [S2].
4. A user record that is a task notification, a background agent's completion notice rather than text the owner typed, is not counted as a user prompt [S2].
5. The collector reports responses and cost by the model id the API returned, de-duplicated, for every lane. For each model family in the price file, when the family's newest priced model has no response in the window while an older model of that family does, the collector lists the family under `model_drift` and exits 1. On 2026-10-30 this would have caught a settings pin that held every Sonnet worker on an older model for two weeks [S3].
6. Every count field in the collector's output names its basis: `_dedup` for counts after the de-duplication of Requirement 1, `_raw` for record counts before it. On 2026-10-30 a raw record count of 33,836 was nearly published as responses; the de-duplicated count was about 15,600 [S3].
7. Each session row carries `cost_by_half` and `responses_by_half`, and no single `half` label. A worker once read the label as attribution and split a reconciliation wrongly [S2].
8. Owner-specific values, the automated-session folder patterns and the project display aliases, come from the settings file, never from the shipped code [S2].
9. Every ledger row the collector writes records its full method: the period, the cutoff, the excluded sessions, the price file's `as_of` date and the collector version [S2].
10. `--reproduce <row_id>` re-runs a ledger row's recorded method and compares the totals. It exits 0 when they agree within one dollar, and exits 1 naming whether the price file, the cutoff or the exclusions differ [S2].
11. The collector exits 0 when clean, 1 when it has findings such as an unpriced model, model drift or a missing child file, and 2 when it could not run. That is the plugin's three-state convention [S8].

**The ledger**

12. Ledger rows follow schema 2 in `references/ledger-schema.md`: one JSON line per week and population, never rewritten, with `schema_version`, a stable `row_id`, `period_start`, `period_end`, `population`, `method`, `measured_at`, and the volume, cost, depth, routing, friction and output fields [S2].
13. The writer refuses a row whose period, population and method match an existing row, and appends a re-measure made by another method. `ledger.py latest` returns, for each period and population, the row with the newest `measured_at` [S2].
14. A ledger of older rows without `period_start` and `period_end` is read through a mapping file the owner supplies, so old rows read as schema 2 without being rewritten. The mapping lives with the owner's data, not in the skill [S2].
15. Rows carry the split routing measure: `frontier_share_delegated_executor`, the top-tier share of delegated executor spend against the routing rule's target, and `advisor_share_total`, the advisor's share of all spend on its own line [S2, S9].
16. Rows carry an optional `plan_limit` object holding the session and weekly plan-limit percentages the owner read from `/usage`, with the time they were read. The field is empty when the owner gives none; see D6 [S4].
17. Each weekly run appends one `audit_run` row recording its own agents, models, tokens, dollars when known, and minutes, so the agent budget in D2 can be revisited on evidence [S3].

**The audit facts**

18. `derive-audit-facts.py` returns, in one call, the facts the main loop typed by hand on 2026-10-30: the reconciliation of the prior week against its earlier ledger row; the week's workflow count, agent count and per-model split; whether per-workflow costs sum to the workflow lane total; compactions; the installed Claude Code version against the state file's last version; settings keys changed since the last run that have no row in the configured change register; and, for each configured credential file, whether it exists, its modification date, and the names of the keys whose values look inline. It never outputs a credential value [S3].
19. Settings changed without a register row are reported as drift, whatever made the change. `/usage` can apply some recommended fixes automatically, so a change can arrive between audits with nobody writing it down [S4].

**The weekly run**

20. The audit excludes itself from its own measurement, by session id or by a cutoff before its first agent, and the data README names which. The default cutoff is 09:00 local time on the audit day, because cutoffs at 16:00 missed $511 and $244 of evening work in two reconciliations [S2, S3].
21. Every agent the skill launches names a model, Sonnet or Haiku by default, none Opus by default. A worker that returns short is re-run once on the next tier with the failure described, and the data README says so [S9].
22. No agent the skill launches may open, read, search or filter a credential file: the configured credential files, any `.env` file, and any file whose name contains `secret` or `token`. Only `derive-audit-facts.py` touches them, and only for key names and dates. On 2026-10-23 an audit's agents were allowed to read a credential file, which is how secret values reach transcripts [S3].
23. The practice lane reads a PP-01 contract C3 digest when given one with `--digest`, and otherwise reads the window's session logs with at most two readers. When a `/insights` report newer than the previous audit exists, the lane reads its feature suggestions and reports which were adopted, without repeating its friction analysis [S5, S6].
24. The scorecard scores only items found in the configured decision sources, lists every source it read, and gives every verdict an evidence entry: a path and line, a command and its output, or a ledger row. Verdicts are Done, Partial, Not done, Overtaken, and Decided not applied. Each open ask carries the number of consecutive audits that have raised it [S2, S3].
25. A claim that the owner approved, chose or declined something must quote the record that says so. A worker's claim of approval without a record is removed. On 2026-10-30 a brief worker reported an approval the owner never gave [S3].
26. After the bundle is written, one verifier agent checks every number in it against the collector and facts output, and every claim about a decision against its record. The main loop applies or rejects each finding, and `data/README.md` lists every correction in a section headed `## Verification`. The bundle is not reported done before that section exists [S3].
27. Every recommendation in `05-recommendations.md` carries an id, a short handle, who acts (the owner decides, the owner acts, an agent, or an agent after a yes) and a mechanism (setting, rule, hook, skill, script, decision or habit). Across the audits, changes carried by a rule, hook, setting or skill stuck, and habits mostly did not [S2].
28. Recommendation ids come from a rotating letter series stored in the state file, which wraps from Z to A and skips reserved letters. The bundle date disambiguates a reused letter [S3].

**Output**

29. An output folder inside a git repository is refused unless the repository ignores it, or the settings file sets `allow_tracked_output: true` [S8].
30. `scrub.py` redacts the configured private patterns and the home path inside decoded JSON strings and in text, so it cannot corrupt an escaped quote. It runs before the check [S2].
31. `bundle-check.py` exits 0 when the bundle is clean, 1 when a rule fails, and 2 when the bundle is broken or the checker cannot prove itself. It fails on any remaining private pattern, a missing file, a recommendation missing a tag, a JSON file that does not parse, or a missing `## Verification` section. Its `--self-test` mutates the committed sample once per rule and proves each mutation fails [S8].

## Acceptance Criteria

**AC-1:** `skills/plab-usage-audit/SKILL.md` carries `disable-model-invocation: true`, and an eval case whose prompt is a usage question asserts that the skill is not invoked. [S8]

**AC-2:** A fixture response split across three content-block records with one message id and request id is counted once, with the largest output token count. [S7]

**AC-3:** A fixture response with iterations `message, advisor_message, message` reports executor tokens equal to the top-level usage and advisor tokens separately at the advisor's rates, and its depth equals the larger executor iteration. [S7]

**AC-4:** A fixture model id missing from the price file adds nothing to any dollar total, is listed under `unpriced`, and makes the collector exit 1. [S7]

**AC-5:** Under `America/Los_Angeles`, a fixture response at 2026-11-02T07:30Z counts on 2026-11-01 and one at 2026-10-31T06:30Z counts on 2026-10-30. Under `America/New_York`, the first counts on 2026-11-02. [S7]

**AC-6:** Given two fixture folders holding the same session file, the session is counted once and the copy is listed under `copied_folders_skipped`. [S2]

**AC-7:** A fixture user record whose text is a task notification is not counted in `user_prompts`, and a typed prompt in the same session is. [S2]

**AC-8:** Given a price file in which a family has an older and a newer model, and a fixture where only the older one responds, `model_drift` names that family and the collector exits 1. When the newer one responds, `model_drift` is empty. [S3]

**AC-9:** Every key in the collector's output whose value is a count of responses or records ends in `_dedup` or `_raw`. [S3]

**AC-10:** A fixture session with responses in both weeks carries `cost_by_half` values that sum to its total cost within one cent, and has no `half` field. [S2]

**AC-11:** A search of `skills/plab-usage-audit/` for a drive letter path, a home folder path, the maintainer's user name, and the owner's folder patterns finds nothing. [S2]

**AC-12:** Every row `ledger.py append` writes carries every schema 2 field. Appending a row identical in period, population and method exits 1 and writes nothing; appending one with a different cutoff succeeds. [S2]

**AC-13:** With two rows for one week, `ledger.py latest` returns the one with the newer `measured_at`. With a mapping file, an older row without period fields reads with them filled in. [S2]

**AC-14:** `collect.py --reproduce <row_id>` on a fixture ledger row exits 0 when the totals agree within one dollar. With a changed price file, it exits 1 and names the price file as the difference. [S2]

**AC-15:** Given a fixture credential file holding a key with an inline value, `derive-audit-facts.py --json` reports the key name and the file's modification date, and the value string appears nowhere in its output. [S3]

**AC-16:** Given fixture collector output in which per-workflow costs sum to more than the workflow lane total by more than the configured tolerance, `derive-audit-facts.py` lists the gap and exits 1. [S3]

**AC-17:** A test reads `references/workflow.md` and finds a model named for every agent stage, and the credential rule of Requirement 22 in the text every agent receives. [S3, S9]

**AC-18:** `bundle-check.py` fails a bundle whose `data/README.md` has no `## Verification` section. [S3]

**AC-19:** `bundle-check.py` fails a bundle in which any recommendation in `05-recommendations.md` lacks an id, a handle, a who-acts tag or a mechanism tag. [S2]

**AC-20:** After `scrub.py`, `bundle-check.py` finds no configured private pattern and no home path in the bundle, and every JSON file in it parses. [S2]

**AC-21:** `bundle-check.py --self-test` exits 0 against the committed sample, and disabling any one rule makes it exit 2. CI runs it, and runs the collector's, the ledger's and the facts script's tests. [S8]

**AC-22:** With the output folder inside a fixture git repository that does not ignore it and no `allow_tracked_output`, the skill's placement check exits 1 before any write. [S8]

**AC-23:** `references/positioning.md` names `/usage`, `/insights` and the `session-report` plugin, the question each answers, and what the audit adds over each. [S4, S5]

**AC-24:** A weekly run on the maintainer's machine writes a bundle that `bundle-check.py` passes, with a `## Verification` section and an `audit_run` ledger row. [model-inference: the live run is this spec's own test design]

## Behavior / Examples

### Example 1: a weekly run

The owner types `/plab-usage-audit`. The skill reads the settings file, resolves the focus week ending today and the prior week before it in the configured zone, and sets the cutoff at 09:00 local time. `collect.py` writes the output files and four ledger rows. `derive-audit-facts.py` reproduces last week's published total exactly, attributes the rest to evening work after the old cutoff, finds that per-workflow costs exceed the lane total by $12, and lists two settings keys with no register row. The pulse ran first, so the practice lane takes its digest and launches no reader. Three Sonnet briefs run in parallel. The main loop writes the bundle, removes a brief's claim of an approval that no record holds, and launches the verifier, which finds a raw count labelled as responses. The main loop corrects it, writes `## Verification`, scrubs, and `bundle-check.py` exits 0.

### Example 2: the week daylight saving ends

The focus week covers 2026-10-31 to 2026-11-06. A response at 2026-11-02T07:30Z is 23:30 on 2026-11-01 in Los Angeles, after the change back to standard time. The skill counts it on November 1. A fixed seven-hour offset would have counted it on November 2.

### Example 3: a pinned model

A settings file pins the `sonnet` alias to an older model id. All Sonnet responses in the window come from that id, and none from the family's newest priced id. `model_drift` names the Sonnet family, the collector exits 1, and `04-config.md` reports the pin with the settings key that causes it.

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Performance | The collector covers two weeks of the owner's transcripts in under five minutes | [S2] |
| Cost | `--weekly` launches at most eight agents plus the verifier, none Opus by default | [S3, S9] |
| Privacy | The skill, fixtures and sample bundle ship. Bundles, the ledger, the state file and the settings file never do | [S2] |
| Safety | No shipped script prints a credential value, and no agent opens a credential file | [S3] |
| Portability | Python 3.11 or later, standard library only. Windows, macOS and Linux | [S8] |
| Context budget | The description is at most 600 characters | [S8] |

## Revisions

| Date | Author | Type | Description |
|------|--------|------|-------------|
| 2026-10-30 | claude | added | Initial spec, from the maintainer-local spec brief of 2026-10-16 and its review of 2026-10-30. Changes from the brief: the verification stage, the credential rule, the model-that-ran check, de-duplication labels, the copied-folder and task-notice rules, Pacific examples, the positioning against native tools, the plan-limit field, the self-cost row, and the scope narrowed to `--weekly`. The decisions below are built on their recommendations as working defaults and stay `Open` until the maintainer ratifies or overturns them. |
| 2026-10-30 | claude | changed | Status moved to `committed` with AC-1 to AC-23 ticked on the evidence in Currently In Progress. AC-24 stays open for the first live weekly run. |

## Sources & Evidence

- **[S1]** The maintainer's rulings in session on 2026-10-30: two skills, scripts first, and the condition that this skill expand thoughtfully and substantially on the native tools. Class A.
- **[S2]** The ten hand-run weekly usage audits of 2026-08-14 to 2026-10-30, their method notes, the collector and its 31 tests, and the KPI ledger. Maintainer-local private repository; restated here, not linked. Class A.
- **[S3]** The 2026-10-30 audit: its six brief errors and five verifier corrections, the Sonnet pin, the credential rule added to its agent prompts, the per-workflow cost gap, the 09:00 cutoff, and the cost of its gather run (8 agents, 1.21M tokens, 10.2 minutes). Maintainer-local; restated here. Class A.
- **[S4]** Claude Code's documentation for `/usage` and `/insights`, read 2026-10-30, and the changelog entry for the automatic-fix key in 2.1.305. Class A.
- **[S5]** The installed `session-report` plugin's `SKILL.md` and `analyze-sessions.mjs`, read 2026-10-30. Class A.
- **[S6]** `docs/internal/release-plans/_unassigned/PP-01_project-pulse/spec.md`, which owns the shared contracts C1 to C5. Class A.
- **[S7]** The accounting fixtures and tests of the hand-run collector, version 2026-10-23. Maintainer-local; restated here. Class A.
- **[S8]** `skills/plab-audit/SKILL.md` and `AGENTS.md`: manual-only invocation, output placement, the three-state exit convention, and the bundle checker pattern. Class A.
- **[S9]** The maintainer's subagent model-routing rule. Maintainer-local global instructions. Class A.
- **[S10]** `skills/plab-current-status/SKILL.md`, the derive-facts-in-one-call convention. Class A.
- **[S11]** The 2026-10-02 design brief for this skill. Maintainer-local; restated where relied on. Class A.
- **[S12]** The maintainer-local review of the two spec briefs, 2026-10-30. Class A.

### Unverified Claims

- The agent budget rests on four hand runs. A skill-run audit's dollar cost has not been measured; Requirement 17 measures it.
- The `/usage` and `/insights` facts come from a research agent's reading of the documentation, not from running either command on this machine.
- Requirement 5's drift rule assumes the price file lists each family's models in release order. That holds for the current file, not as a rule.
- AC-24's live run is this spec's own test design.

## Open Questions / Decisions

**What these statuses mean.** Every item below is `Open`: the maintainer has not chosen. Each Recommendation ends by saying the build used it as a working default, so a walk can ratify or overturn it. The build followed the maintainer's instruction of 2026-10-30 to enrich and build the skills.

| ID | Title | Resolution | Status | Updated |
|----|-------|------------|--------|---------|
| D1 | Recommendation id scheme | (none) | Open | 2026-10-30 |
| D2 | Weekly agent budget | (none) | Open | 2026-10-30 |
| D3 | Practice lane placement | (none) | Open | 2026-10-30 |
| D4 | Codex adapter timing | (none) | Open | 2026-10-30 |
| D5 | Writing into a tracked folder | (none) | Open | 2026-10-30 |
| D6 | Recording plan-limit use | (none) | Open | 2026-10-30 |

### D1: Recommendation id scheme (Open)

**Summary.** A rotating letter per audit, or ids scoped by date?

**Context.** The hand-run audits used W, X, Y and Z in turn, and on 2026-10-30 the series wrapped to A. Other series use D, Q, T, O and K, so some letters collide.

**Desired outcome.** Ids that read naturally in conversation and need no lookup to place in time.

**Options / approaches.**

* **Option A:** A rotating letter from a configured sequence that skips reserved letters, stored in the state file, wrapping after Z. The bundle date disambiguates.
* **Option B:** Date-scoped ids such as "2026-10-30 R3".
* **Option C:** A letter plus the ISO week, such as "W44-3".

**Recommendation.** Option A, which the hand-run audits already practise. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D2: Weekly agent budget (Open)

**Summary.** How many agents may `--weekly` launch?

**Context.** The 2026-10-02 brief allowed one worker. The 2026-10-16 brief proposed six. The 2026-10-30 run used eight in its gather stage, plus a verifier, for 1.21M tokens in 10.2 minutes.

**Desired outcome.** A bundle as detailed as the hand-run ones, at a cost the owner sees and accepts.

**Options / approaches.**

* **Option A:** At most eight plus the verifier: two readers, three briefs, up to three escalations or scouts. The run records its own cost (Requirement 17).
* **Option B:** Six, as the 2026-10-16 brief proposed, dropping the verifier when the budget is spent.
* **Option C:** Three briefs and the verifier, relying on the pulse's digest.

**Recommendation.** Option A, revisited after four `audit_run` rows. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D3: Practice lane placement (Open)

**Summary.** Should reading the session logs for lessons run weekly?

**Context.** The practice lane produced the most concrete findings in several runs, including two hook defects later reproduced on disk. Reading 30 logs takes two Sonnet agents. A pulse digest makes it free.

**Desired outcome.** Lessons arrive while fresh, without paying twice for one reading.

**Options / approaches.**

* **Option A:** Weekly, bounded to two readers, and free when a digest is supplied.
* **Option B:** Only in a later monthly mode.

**Recommendation.** Option A. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D4: Codex adapter timing (Open)

**Summary.** Include Codex usage in v1, or add it later?

**Context.** Claude Code holds most measured spend. A Codex-run audit in September worked out the Codex accounting rules, so an adapter has a starting point.

**Desired outcome.** A trustworthy v1 first, without losing the Codex rules.

**Options / approaches.**

* **Option A:** Later, behind the same normalized output.
* **Option B:** In v1, with two sets of accounting rules to prove.

**Recommendation.** Option A. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D5: Writing into a tracked folder (Open)

**Summary.** May the skill write its bundle straight into a private repository's audits folder?

**Context.** The owner commits each scrubbed bundle to a private repository. The plugin's placement rule refuses an output folder that git does not ignore, which would block that flow.

**Desired outcome.** The normal flow works, and an accidental write into a public repository cannot happen.

**Options / approaches.**

* **Option A:** An explicit `allow_tracked_output: true` in the settings file; scrub and check must pass before success. The skill still never commits.
* **Option B:** Always write to `_output/`, and the owner copies the bundle.
* **Option C:** Allow tracked output only when `gh` confirms the repository is private.

**Recommendation.** Option A. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)

### D6: Recording plan-limit use (Open)

**Summary.** How should the ledger get the plan-limit percentages that only `/usage` shows?

**Context.** On a subscription, the plan limit is the real constraint; list-price dollars only approximate it. `/usage` shows the percentages but exports nothing, and whether a status line or hook receives them is unchecked.

**Desired outcome.** The weekly history holds the measure that actually limits the owner, without a manual step that gets skipped.

**Options / approaches.**

* **Option A:** The skill asks the owner once per run for the two percentages, and writes them with the read time. A skipped answer leaves the field empty and is named in the data README.
* **Option B:** Leave plan limits out until an automatic source is found.
* **Option C:** Investigate the status-line input first, and build Option A only if it carries nothing.

**Recommendation.** Option A now, with Option C as a follow-up, because one question per week is cheap and the measure matters most. Working default: built on this recommendation on 2026-10-30; not yet ratified.

---

> **Maintainer decision:** _(pending)_
>
> * **Status:** Open
> * **Choice:** (none)
> * **Reasoning:** (none)
> * **Decided by / date:** (none)
