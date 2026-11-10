---
name: plab-wrap-session
description: "Document and close agentic coding sessions with structured session logs.
  Use at the end of any coding session, when wrapping up work, when switching tasks,
  or when blocked. Defaults to a deep log with a verbose copy-paste-ready continuation
  prompt, runs a hygiene sweep (remote divergence, release state, doc drift,
  working-tree reconciliation), writes the log first and then asks its numbered
  hygiene proposals in one batch, and always lists what it is waiting on from the
  maintainer with links. Triggers on 'wrap up', 'wrap session',
  'end of session', 'session log', 'close out', or 'document this
  session'. Also use when the session is blocked and needs to capture blocker details
  for the next session."
argument-hint: "[mode: quick|final|deep|blocked] [--organize]"
license: MIT
metadata:
  version: "1.10.0"
  updated: 2026-11-10
---

# Wrap Session

Leave the project in a legible, resumable, evidence-backed state.

## Mode Selection

**Deep is the default.** Every wrap produces the deep template unless the agent records a specific objection in the log justifying a lighter mode (comply-or-explain, the same contract as the continuation prompt's verbosity rule). The user can always override in either direction.

| Mode | When | What to Include |
|------|------|-----------------|
| **deep** | Default for every session | Full template + evidence index + verification detail + hygiene sweep |
| **final** | Downgrade with stated objection: mid-length, low-risk, nothing autonomous | Full template below |
| **quick** | Downgrade with stated objection: < 30 min, < 3 files, trivial fix | Frontmatter + summary + files + waiting-on + continuation prompt |
| **blocked** | Session ended by unresolved blocker | Frontmatter + summary + blocker detail + waiting-on + continuation prompt |

Valid downgrade objections mirror the verbosity rule: "trivial typo fix, clean tree, nothing pending from the maintainer" or "user asked for a quick wrap". Without a recorded objection, wrap deep.

## Evidence Gathering

Before writing the log, run `derive-log-facts.py` once and read the tool result once. Add `--fetch` in deep and final modes, where the Hygiene Sweep's remote facts need to be current; omit it in quick and blocked modes. If this session resumed with `/plab-continue-session`, add `--resumed-from <that log's file name>`, because the script cannot see what continue resumed and that log is the first carry-forward rule.

```bash
python <skill-dir>/scripts/derive-log-facts.py <project-root>            # quick, blocked
python <skill-dir>/scripts/derive-log-facts.py <project-root> --fetch    # deep, final
```

`<skill-dir>` resolves relative to this skill's own installed directory, the same rule `organize-logs.py` already follows (see Organize Mode below); `<project-root>` is the project being wrapped, never assumed to share a root with the skill. The default (no `--json`) output is a complete wrap digest: every frontmatter field, every Waiting on You item verbatim with its original date (never capped, however many there are), every gitignored-modified path, every hygiene-sweep check's facts and findings as readable text, and the verification facts, each as one compact line (collapsed to one line, capped at 200 characters, showing the 20 newest). Every list that can grow without bound (unpushed commits, commits behind, remote branches, dirty files, gitignored-modified paths) is capped at 10 with an explicit "N more, see `--json`" line, which keeps the digest well under a 20,000-character budget for a typical session. `files-changed` and the Waiting on You list are never capped, because the frontmatter block and the carried-forward log copy both verbatim; on a session that changes several hundred files, that one field alone can exceed the budget (confirmed on `pm-skills`: 239 files, 23,350 characters for that field by itself). That is still the right call to read once in full, not a sign to redirect it to a file or slice it, because files-changed is exactly the field the frontmatter needs complete and verbatim. Read this tool result once, directly from the call; two real wraps that ran long (14 and 15 assistant calls against a 12-call baseline) both redirected `--json` to a file and sliced it in `python -c` calls because the old text mode left those fields out, so this is the behavior those re-reads existed to work around. Do not redirect the output to a file or re-read it in pieces. Do not re-run `git` for remote state (ahead/behind, unpushed commits, remote branches, tags) or re-inventory `_local/` for gitignored-modified files: both are already in this output, and re-deriving them was exactly what made those two wraps long. `--json` still exists, for a script or another program that parses this output; the agent reads the text form. Without `--base`, the script defaults to the commit on `HEAD` just before this session started; if the agent knows where the session's own work actually began and the default `base` the output reports looks wrong, pass `--base <ref>` explicitly instead of trusting the default.

From that output, the agent still:

1. Counts decisions made during the session.
2. Identifies what was verified vs. assumed - never conflate "completed" with "tested". When the script's `verification` field found a record, treat it as a starting point, never a substitute for the agent's own read of what the record shows; when it reports no record, verification stays fully agent-authored as before.
3. Checks for blockers, outstanding issues, and risks introduced.
4. Inventories work products in gitignored locations (`_local/` and kin), starting from the script's gitignored-modified list - git-derived file lists cannot otherwise see them.
5. Lists skills invoked this session and any multi-agent workflow runs (run IDs, agent counts, token totals) for the frontmatter and Evidence Index.
6. In deep and final modes, judges whether the script's `carry-forward` log covers the same arc as this session. That log is the only one the judgment may consider, and only when it is not under `concurrent logs`: a log another session wrote while this one ran was not superseded by this one. If it covers the same arc, prepares one archive proposal for the hygiene batch (see Wrap Order below): propose moving it to `_superseded/` inside the store the script reports, execute only when its number is approved, and record the disposition, declared plus archived-or-not, in the new log's Summary. When the rule is `none`, or the log is concurrent, there is nothing to judge.
7. Carries every still-unresolved Waiting on You item from the script's `carry-forward` log forward into this log with its original date, never today's, so a blocker's age survives across wraps instead of resetting, and copies that log's file name into `carried-from:`. Carries every Parked item the script reports into this log's Parked section the same way, verbatim, dropping only items this session resolved or promoted to Waiting on You; before 1.9.0 nothing read Parked, so a parked item lasted one log. If the script's carry-forward rule is `none`, start fresh and say nothing.
8. Names every log the script lists under `concurrent logs` in this log's Summary, by file name, as work another session did while this one ran, and proposes nothing about those logs. When the `carry-forward` log is one of them, says that the carried items came from that parallel session.

If the script reports git as unavailable, note that and proceed with session context only.

## Hygiene Sweep (deep and final modes)

Detect and judge before writing the log; resolve after it, in one numbered batch (see Wrap Order below). Record findings, proposals and auto actions in the log's Hygiene Sweep section. The same `derive-log-facts.py --fetch` invocation from Evidence Gathering above already carries every check's detection result; this section judges and proposes from that output rather than re-gathering it. Check catalog, the output field each check reads, and the confirmation protocol live in `references/hygiene-sweep.md`.

1. **Remote reconciliation**, from the script's `check1-remote` field: local branch vs its remote (ahead/behind), unpushed commits, remote branches, remote tags vs local. Parallel work from another checkout must surface at wrap time, not at the next release.
2. **Working-tree and worktree state**, from `check2-worktree`: uncommitted changes, untracked files, stashes, worktrees.
3. **Release and repo hygiene**, from `check3-release`: un-released CHANGELOG content and version fields vs the latest tag. The repo's own validation scripts, when it has them, are still run locally as a separate step, chained into one shell command (for example `python scripts/a.py && python scripts/b.py && ...`) so their combined output is read in one call rather than one call per script, and their results reported (never fixed silently) - the script has no way to know what those scripts are.
4. **Documentation drift, both directions.** User or technical docs this session made stale: version tables, skill or feature READMEs vs source of truth, missing CHANGELOG entries. And the inverse, which is the direction that actually shipped here: a skill whose content changed since the last tag while its `metadata.version` did not move, or whose `HISTORY.md` has no entry for the version it currently ships, from the script's `check4-doc-drift` field. `references/hygiene-sweep.md` carries the recipe the field mirrors.
5. **Session-log store**, from `check5-log-store`: logs from closed months sitting unfiled in the store the script reports. When the plan has moves and no collisions, file them as an auto action (see below) and record it; silent when there is nothing to file.

**Resolution: one numbered batch, after the log.** For each finding, draft one concrete proposal (commit these files with this message, push, apply this doc update) and number it `H1`, `H2` and so on. Each proposal runs only when the maintainer approves its number. Unanswered and declined proposals stay recorded in the log and in the continuation prompt.

**Auto actions.** Four actions run without asking, because each changes only this checkout, can be undone from what the log records, and is refused by git or the script when its precondition fails. In this order: a pruning fetch, `git fetch --prune origin`, in deep and final modes when `git remote prune origin --dry-run` lists a stale remote-tracking ref; deleting a local branch with `git branch -d` once its upstream is gone; `git worktree prune`; and `organize-logs.py --apply` on a plan with no collisions. The pruning fetch goes first because a branch's upstream reads `gone` only after its tracking ref is pruned. Each is recorded in the Hygiene Sweep section as `auto: <rule>`, with its command and its output, and the pruning fetch also records each pruned ref's SHA. Every other action asks. The facts already carry `git worktree list`, which marks a prunable entry, and check 5's plan. The extra reads are `git remote prune origin --dry-run` with one `git rev-parse` per stale ref, and `git branch -vv`, which marks a branch whose upstream is gone. The facts were fetched with `--no-prune`, so check 1 describes the remote before the pruning fetch. `references/hygiene-sweep.md` holds the rules and the record format.

In quick and blocked modes, run only check 2 and note the skips.

## Wrap Order

The log is written before any question is asked, and amended after the answers.

1. Run `derive-log-facts.py` once (Evidence Gathering above).
2. Judge the sweep and draft every proposal the wrap will ask about: hygiene findings, the same-arc archive (Evidence Gathering step 6), and surrounding-document updates (see below). Number them `H1` to `Hn`.
3. Run the auto actions the sweep allows, and record each.
4. Write the log. Its Hygiene Sweep section lists every proposal as `- **H1** <action>. Status: unanswered`, and the continuation prompt mirrors the list as pending hygiene actions.
5. Run `check-log.py` (Log Self-Check below) and fix every finding.
6. With no proposals, the wrap is done. Otherwise present every proposal in one message, numbered, and end with the answer line: "Answer in one line, such as `H1 y, H2 n`, or `ok` to approve them all."
7. Carry out exactly the approved proposals, nothing adjacent.
8. Amend the log. In the Hygiene Sweep section and the continuation prompt, change each status word: `done` or `failed` with the result for an approved proposal, `declined` for a declined one, and `unanswered` stays for any number the answer left out. A declined proposal that now needs the maintainer also goes in Waiting on You.
9. Run `check-log.py` again on the amended file. This second clean run completes the wrap.

**Silence approves nothing.** An item the answer line leaves out stays `unanswered`; only `ok`, `all y` or an equivalent explicit phrase approves every proposal. This is the same rule `plab-resolve-open-items` applies to its answer line.

**Why the log comes first.** A terminal closed while a question is open still leaves a complete log, whose unanswered proposals `plab-continue-session` already shows as re-decidable. The ask-first order, decided on 2026-10-19 and reversed on 2026-11-03 before it was built, would have left no log at all in that case. Writing first costs one edit and one more `check-log.py` run, and only on wraps that asked a question.

## Session Log Output

Write to: `<store>/YYYY-MM-DD_HH-MM_<llm>_<brief-kebab-title>.md`, where `<store>` is the path the script reports on its `store:` line. In a normal checkout that is `_local/_session-logs/`; in a linked worktree it is the main checkout's `_local/_session-logs/`, so every session's log lands in one store that survives the worktree's removal. `HH-MM` is the local time of this wrap, not the session's start, which goes in `session-start:`.

- `<llm>` is the short LLM name: `claude`, `codex`, `gpt`, `gemini`, `grok`, `mistral`
- Example, in a normal checkout: `_local/_session-logs/2026-05-28_15-30_claude_deploy-ai-review.md`
- All agents write to the same directory - chronological project timeline
- Create the directory if it doesn't exist
- Session logs are machine-local by design. `_local/` is gitignored, so logs stay out of version control and out of the repo's public surface

**Do not hard-wrap body prose.** One paragraph is one line, however long. A session log is a document to be read rendered or in a soft-wrapping editor, not source to be diffed line by line, and hard wrapping costs it three things: editing one sentence reflows the paragraph so diffs show paragraph-sized churn, the continuation prompt arrives ragged when pasted into a chat box, and any grep for a phrase longer than the wrap width silently fails. That last one is the expensive one, because searching a log is the main thing a log is for.

Tables, code blocks, and frontmatter keep their natural line structure. This rule is about prose.

It is deliberately not a Log Self-Check gate. Nothing can mechanically tell a hard-wrapped line from a genuinely short sentence, so a gate for it would either flag ordinary prose or pass everything, and this release exists to stop shipping checks that cannot do what they claim.

**Always write to the current path**, even when a legacy directory exists. Do not write to a legacy path and do not move existing logs automatically. If either legacy directory contains logs, add one migration note after writing:

| Legacy path | Written by |
|-------------|-----------|
| `_agent-context/session-log/` | plab-wrap-session v1.1.0 - v1.2.x |
| `AGENTS/session-log/` | plab-wrap-session v1.0.x |

> **Migration note:** This project has session logs at `<legacy path>`. New logs are written to `_local/_session-logs/`. `/plab-continue-session` reads both, so nothing is lost. To consolidate, move the old files into `_local/_session-logs/` (they leave version control; git history retains them).

## Organize Mode (`--organize`)

`/plab-wrap-session --organize` files old session logs into `YYYY-MM/` month folders. It runs **instead of** a wrap: no session log is written, no hygiene sweep runs, no other check fires.

```bash
python scripts/organize-logs.py _local/_session-logs
python scripts/organize-logs.py _local/_session-logs --apply
```

`scripts/organize-logs.py` resolves against **this skill's own directory**, wherever the plugin is installed. The store argument is relative to the **project** being wrapped. In a linked worktree, pass the main checkout's store instead, because that is where every log lives: `<main checkout>/_local/_session-logs`, where the main checkout is the parent of the folder `git rev-parse --path-format=absolute --git-common-dir` prints. Do not assume the two share a root: when the installed plugin runs, the skill lives in the plugin cache and the project does not.

1. Run the script with no flags. It is dry run by default and prints the plan.
2. If the plan is empty, say so and stop. Nothing else happens.
3. Otherwise show the plan and ask once: "File these N logs into month folders? (y/n)"
4. On yes, re-run with `--apply` and report the result. On no, stop and change nothing.

**The current month and the previous month are never filed.** Recent logs stay flat, where resume reads them first.

**Never run `--apply` without the user confirming that specific plan.** The script moves files and never deletes, so a wrong move is reversible, but the confirmation is the contract.

The script exits non-zero when a target filename already exists in its month folder. Nothing is overwritten; surface the collision rather than retrying.

Store layout, and why discovery reads both the flat store and month folders, are defined once in `plab-continue-session/references/log-discovery.md`. Do not restate those rules here.

**Requires `plab-continue-session` 1.3.0+.** Older readers cannot see month folders, and a store archived for them reads as empty. Both ship in plugin v0.2.0, so an install is never mismatched with itself.

### Frontmatter

Include all Tier 1 fields. Add Tier 2 and Tier 3 when available. See `references/frontmatter-schema.md` for the complete field reference. `date`, `type`, `machine`, `repo`, `branch`, and `files-changed` come from the Evidence Gathering run of `derive-log-facts.py` above, as do the two fields it adds, `commit-range` and `latest-tag`, and the three W-07 session fields: `session-id` and `session-start` when the script reports them, and `carried-from`, the file name on its `carry-forward:` line, unless the rule is `none`. Omit a field the script reports as null. `decisions-count` is filled in by the agent once the Decisions Made section below is drafted, by counting that section's own entries, and `check-log.py` (see Log Self-Check below) then verifies the count mechanically before the wrap is done - it never ships as an uncorrected estimate. Everything else in this block is agent-filled.

```yaml
---
date: # ISO 8601 datetime - from derive-log-facts.py
type: # always session-log
machine: # hostname - from derive-log-facts.py; which checkout wrote this log; logs are machine-local and cannot cross checkouts
repo: # from derive-log-facts.py
branch: # from derive-log-facts.py
summary: # max 120 chars, human-scannable
files-changed: # from derive-log-facts.py
commit-range: # from derive-log-facts.py; the base..HEAD short-SHA range it diffed
latest-tag: # from derive-log-facts.py; nearest reachable tag - distinct from the tags: topic-keyword field
session-type: # bugfix|feature|refactor|research|planning|review|docs|autonomous|exploration
model: # full model name, e.g. "claude opus 4.6"
model-settings: # key settings, e.g. "extended-thinking max"
agent: # claude-code|codex-cli|other
status: # completed|interrupted|blocked
decisions-count: # integer - agent counts the drafted Decisions Made section's own entries; check-log.py verifies the count mechanically
skills-used: # skills invoked this session, e.g. [plab-guide, plab-ai-review] - feeds usage telemetry
resumed-from: # written only by an in-session /plab-continue-session resume; never back-filled from memory. See references/frontmatter-schema.md.
session-id: # from derive-log-facts.py; omit when it reports null
session-start: # from derive-log-facts.py, ISO 8601 in UTC; omit when it reports null
carried-from: # the file name on the script's carry-forward: line; omit when its rule is none
---
```

### Body Sections (Final Mode)

**Summary** - 2-4 sentences. What happened and why it matters. Then name every concurrent log, as Evidence Gathering step 8 says. When the Evidence Gathering same-arc check above judges the carry-forward log to cover the same arc as this session, end Summary with one additional sentence naming that log by filename only (no path) and stating whether it was archived to `_superseded/` or not archived.

**Work Completed** - Bulleted list of what was accomplished.

**Decisions Made** - Each decision with rationale. Scale verbosity to significance:
- Minor: one-liner ("Chose MIT license - standard for personal repos")
- Significant: 2-3 sentences with reasoning
- Architectural: full alternatives-considered analysis

**Files Changed** - List from git, grouped by purpose if many.

**Gitignored Outputs** - Work products in gitignored locations, path plus a one-liner each. Without this section, `_local/` work is undiscoverable later. Omit only when there are none.

**Verification** - Checklist format. What was tested, what was assumed, what was skipped.

**Outstanding Issues** - Blockers, risks, unfinished work, including any sessions since the last log that were never wrapped (from capture-lite records, when present; see Evidence Gathering above).

**Hygiene Sweep** - Findings from the sweep: state found, one `auto:` line per auto action, and one line per numbered proposal with its status (`unanswered`, then `done`, `failed` or `declined` after the amendment).

**Waiting on You** - Required in every mode. Only items blocked on the maintainer's decision or action belong here, one bullet each: what is awaited, why it blocks, a `(blocked since YYYY-MM-DD)` marker carrying the date the item first blocked, and links to the relevant files. Optional or nice-to-have items go in the Parked list, never here; an item nobody is blocked on dilutes the section until a real blocker hides inside it. Write "Nothing pending" explicitly when the list is empty; never omit the section. Mirror the list inside the continuation prompt so the next session re-presents it.

**What's Next** - Ordered list. Most important action first. When one decision unlocks the rest, name it as the single unlocking decision.

**Continuation Prompt** - In a fenced code block. See requirements below.

### Body Sections (Deep Mode)

Everything in Final Mode, plus four sections. **Evidence Index** and **Verification Detail** as shown in `references/session-log-template.md`, then the two below, placed immediately after Verification Detail so that what was proven is followed at once by what was not.

**Uncertainty Ledger** - One table, sorted by blast radius descending and never by confidence. Columns: item, confidence, blast radius, verified, and what would settle it. It merges two questions that are one list sorted two ways, because "what am I least confident about" and "which assumption would change the outcome most if wrong" produce different orderings of the same set, and the row that matters most sits where they disagree: **high confidence and high blast radius**, an assumption comfortable enough that nobody thought to check it. Asked as two separate sections those rows hide in the gap, since they do not feel uncertain and do not read as remarkable. Mark them `(!)`. Confidence and blast radius are High, Medium or Low, never a percentage. Every row names what would settle it, because an uncertainty with no route to resolution is anxiety rather than a finding. No cap on rows. Write "Nothing material." explicitly rather than omitting the section.

**What You May Not Realize** - Not about the work; about the asymmetry between what the session saw, meaning every file read and every command output, and what the maintainer saw, meaning the conversation. Separate from the ledger because its source is different, not because its items are. **Every item must cite a source from this session** - a file path and line, a command and its output, a corpus document, a verified API response. An item with no source is speculation wearing the clothes of insight and is dropped rather than softened; that rule is the whole reason the section earns its place. Each item carries a confidence marker. Nothing that belongs in the ledger table is repeated here. No cap on items. Write "Nothing surfaced." explicitly rather than omitting the section.

### Body Sections (Quick Mode)

Summary + files changed + waiting-on + continuation prompt. That's it.

### Body Sections (Blocked Mode)

Summary + blocker detail (what, who can unblock, impact) + waiting-on + continuation prompt.

## Continuation Prompt

The single most important output. Must be:

- **Copy-paste ready** - wrapped in a fenced code block, no editing needed
- **Specific** - names exact files, branches, and next actions
- **Bounded** - one clear immediate action, then ordered secondary steps
- **Self-contained** - readable without the original session

A continuation prompt that says "continue where we left off" has failed. It must include enough context that a cold-start session can resume without re-reading anything.

### Default verbosity (v1.1.0)

**The continuation prompt defaults to the deep / verbose form in every mode** (quick, final, blocked, deep). "Verbose" means: includes the task context paragraph, the current state summary, the immediate next action, the ordered secondary actions, the relevant file paths, and the branch name. Even quick-mode sessions get the full prompt - the cost is a dozen extra lines; the benefit is a cold-start session that never has to ask "what's the context?"

The only path to a lighter continuation prompt is for the agent to state a **specific objection** (one short sentence) in the session log explaining why a lighter prompt is appropriate for this particular session. Examples of valid objections: "Session was a trivial typo fix; no context to carry forward" or "User explicitly requested a one-line prompt." Without such an objection, the verbose form is mandatory.

This default is a comply-or-explain rule: produce the verbose form, or produce a lighter form *with the explicit reason recorded*.

## Log Self-Check (one call, after writing)

Write the log, then run one command, and fix every finding before the wrap counts as done. When the wrap asked hygiene questions, run it again after the amendment (Wrap Order step 9); that second clean run is the one that completes the wrap:

```bash
python <skill-dir>/scripts/check-log.py <log-path> --repo-root <project-root> --mode <quick|final|deep|blocked>
```

It runs every mechanical gate this section used to list as separate steps, in one invocation: the two detector-backed gates below exactly as they are, each still proving its own canary corpus before it scans and still reporting clean, findings, or broken, where a broken detector makes this script's own result broken too; `decisions-count` compared against a mechanical count of the Decisions Made section (skipped, not failed, in quick and blocked modes, whose templates carry neither); summary length (120 characters or fewer); Tier 1 frontmatter completeness, including `machine:`; the W-07 session fields, which are optional but must be well formed when present (`session-start` an ISO 8601 timestamp, `carried-from` a bare session-log file name); the Waiting on You rules (section present, "Nothing pending." counting, no item beginning "Optional", every item carrying `(blocked since YYYY-MM-DD)`); and, in deep mode only, that the Uncertainty Ledger and What You May Not Realize sections are present ("Nothing material." and "Nothing surfaced." counting; absence does not). Exit 0 clean, 1 findings, 2 broken; `--json` for machine-readable output. Re-run after every fix until clean.

The two detector scripts it calls:

- Path citations resolve, detector-backed, three-state: `python scripts/path-citation-check.py <log-path> --repo-root <project-root>`. Checks only citations that assert a location: one containing a path separator must exist as written, and a backtick-wrapped citation with no separator is resolved against the repo root and passes silently if it does not resolve. A bare word with a file extension and neither signal is prose, not a path claim, and is not checked. Separator-bearing tokens that are URIs, drive-letter, home-relative (`~/`) or POSIX absolute paths, globs, template placeholders, single-segment slash commands, git ranges, names ending in a version number, or extensionless are excluded too. A backtick span with whitespace is read as a command, and each of its words is checked on its own; see the script docstring for the canary corpus. Exit 0 clean, 1 findings, 2 broken; broken blocks exactly like findings
- No em-dash or en-dash characters anywhere in the log, detector-backed, three-state: `python scripts/dash-check.py <log-path>`. Exit 0 clean, 1 findings, 2 broken; broken blocks exactly like findings

The following gates are judgment calls no script can make and stay the agent's own check:

- Continuation prompt is self-contained (readable by a cold-start session with zero other context)
- Deep mode only: the Uncertainty Ledger is sorted by blast radius descending, every row names what would settle it, and every High-confidence/High-blast-radius row is marked `(!)`
- Deep mode only: **every What You May Not Realize item cites a source from this session**. An item with no source is dropped, never softened into a hedge

`derive-log-facts.py --count-decisions` still works, for compatibility with anything that calls it directly, but `check-log.py` is the one command a wrap now runs.

## Surrounding Document Updates

Before writing the session log, check whether changes warrant updates to:

- **README.md** - only if user-facing capabilities changed
- **CHANGELOG.md** - only if release-worthy (new feature, visible bugfix, breaking change)
- **Active plans** - only if sequence, scope, or assumptions changed
- **Decision records** - if an architectural decision was made this session, propose capturing it as an ADR (MADR, `docs/internal/decisions/` where the repo uses them)
- **Agent memory** - if durable facts or decisions emerged that outlive this session, confirm they are recorded in persistent memory rather than only in the log

**Each intended edit is one proposal in the hygiene batch** (Wrap Order above), naming the file and the change. Never update a surrounding doc until its number is approved.

If nothing warrants an update, move on without commenting.

## Constraints

- Never embed full transcripts - reference the transcript path only
- Never conflate "completed" with "verified" - state verification status explicitly
- Never commit, push, or modify anything beyond the session log until the maintainer approves that proposal by its number. The only exceptions are the four auto actions in `references/hygiene-sweep.md`, each recorded in the log
- Never ask a hygiene question before the log is written; write first, ask in one batch, then amend
- Never update surrounding docs until their proposal is approved
- The Waiting on You section is mandatory in every mode; an empty list is stated, never omitted
- Summary must be ≤ 120 characters (for index display)
- The session log must be self-contained - readable without the original session
- Never produce an empty or generic continuation prompt
- Never produce a lighter-than-verbose continuation prompt without a stated objection (see "Default verbosity" above)
