---
name: plab-wrap-session
description: "Document and close agentic coding sessions with structured session logs.
  Use at the end of any coding session, when wrapping up work, when switching tasks,
  or when blocked. Defaults to a deep log with a verbose copy-paste-ready continuation
  prompt, runs a pre-wrap hygiene sweep (remote divergence, release state, doc drift,
  working-tree reconciliation with per-action confirmation), and always lists what it
  is waiting on from the maintainer with links. Triggers on 'wrap up', 'wrap session',
  'end of session', 'session log', 'close out', or 'document this
  session'. Also use when the session is blocked and needs to capture blocker details
  for the next session."
argument-hint: "[mode: quick|final|deep|blocked] [--organize]"
license: MIT
metadata:
  version: "1.8.1"
  updated: 2026-10-16
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

Before writing the log, run `derive-log-facts.py` once and use its output for everything it returns. Add `--fetch` in deep and final modes, where the Pre-Wrap Hygiene Sweep's remote facts need to be current; omit it in quick and blocked modes.

```bash
python <skill-dir>/scripts/derive-log-facts.py <project-root> --json            # quick, blocked
python <skill-dir>/scripts/derive-log-facts.py <project-root> --fetch --json    # deep, final
```

`<skill-dir>` resolves relative to this skill's own installed directory, the same rule `organize-logs.py` already follows (see Organize Mode below); `<project-root>` is the project being wrapped, never assumed to share a root with the skill. The output supplies: the frontmatter's environment fields and `files-changed`; `commit-range` and `latest-tag`; the newest existing log's filename and its Waiting on You list verbatim, each item keeping its original `(blocked since YYYY-MM-DD)` date; any qualifying capture-lite records' count and earliest-to-latest `head`; and the gitignored-file inventory that starts step 4 below. Run no further git or shell command to obtain any fact this output already contains. Without `--base`, the script defaults to the commit on `HEAD` just before this session started; if the agent knows where the session's own work actually began and the default `base` the output reports looks wrong, pass `--base <ref>` explicitly instead of trusting the default.

From that output, the agent still:

1. Counts decisions made during the session.
2. Identifies what was verified vs. assumed - never conflate "completed" with "tested". When the script's `verification` field found a record, treat it as a starting point, never a substitute for the agent's own read of what the record shows; when it reports no record, verification stays fully agent-authored as before.
3. Checks for blockers, outstanding issues, and risks introduced.
4. Inventories work products in gitignored locations (`_local/` and kin), starting from the script's gitignored-modified list - git-derived file lists cannot otherwise see them.
5. Lists skills invoked this session and any multi-agent workflow runs (run IDs, agent counts, token totals) for the frontmatter and Evidence Index.
6. In deep and final modes, judges whether the script's reported newest existing log covers the same arc as this session. If it does, prepares one archive proposal under the same per-action confirmation protocol the hygiene sweep uses (see `references/hygiene-sweep.md`): propose moving the older file to `_local/_session-logs/_superseded/`, execute only on explicit approval, and record the disposition, declared plus archived-or-not, in the new log's Summary.
7. Carries every still-unresolved Waiting on You item from the script's output forward into this log with its original date, never today's, so a blocker's age survives across wraps instead of resetting. If the script reports no newest log, start fresh and say nothing.

If the script reports git as unavailable, note that and proceed with session context only.

## Pre-Wrap Hygiene Sweep (deep and final modes)

Run before writing the log; record findings in the log's Hygiene Sweep section. The same `derive-log-facts.py --fetch` invocation from Evidence Gathering above already carries every check's detection result; this section judges and proposes from that output rather than re-gathering it. Check catalog, the output field each check reads, and the confirmation protocol live in `references/hygiene-sweep.md`.

1. **Remote reconciliation**, from the script's `check1-remote` field: local branch vs its remote (ahead/behind), unpushed commits, remote branches, remote tags vs local. Parallel work from another checkout must surface at wrap time, not at the next release.
2. **Working-tree and worktree state**, from `check2-worktree`: uncommitted changes, untracked files, stashes, worktrees.
3. **Release and repo hygiene**, from `check3-release`: un-released CHANGELOG content and version fields vs the latest tag. The repo's own validation scripts, when it has them, are still run locally as a separate step, chained into one shell command (for example `python scripts/a.py && python scripts/b.py && ...`) so their combined output is read in one call rather than one call per script, and their results reported (never fixed silently) - the script has no way to know what those scripts are.
4. **Documentation drift, both directions.** User or technical docs this session made stale: version tables, skill or feature READMEs vs source of truth, missing CHANGELOG entries. And the inverse, which is the direction that actually shipped here: a skill whose content changed since the last tag while its `metadata.version` did not move, or whose `HISTORY.md` has no entry for the version it currently ships, from the script's `check4-doc-drift` field. `references/hygiene-sweep.md` carries the recipe the field mirrors.
5. **Session-log store**, from `check5-log-store`: logs from closed months sitting unfiled in `_local/_session-logs/`. Offer to file them into `YYYY-MM/` folders (see Organize Mode below). Read-only until confirmed; silent when there is nothing to file.

**Resolution protocol: propose, then per-action confirmation.** For each finding, propose one concrete action (commit these files with this message, push, prune this worktree, apply this doc update) and execute only what the user approves, action by action. Declined or unanswered proposals are recorded in the log and carried into the continuation prompt. The sweep itself changes nothing; only confirmed actions do.

In quick and blocked modes, run only check 2 and note the skips.

## Session Log Output

Write to: `_local/_session-logs/YYYY-MM-DD_HH-MM_<llm>_<brief-kebab-title>.md`

- `<llm>` is the short LLM name: `claude`, `codex`, `gpt`, `gemini`, `grok`, `mistral`
- Example: `_local/_session-logs/2026-05-28_15-30_claude_deploy-ai-review.md`
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

`scripts/organize-logs.py` resolves against **this skill's own directory**, wherever the plugin is installed. The store argument is relative to the **project** being wrapped. Do not assume the two share a root: when the installed plugin runs, the skill lives in the plugin cache and the project does not.

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

Include all Tier 1 fields. Add Tier 2 and Tier 3 when available. See `references/frontmatter-schema.md` for the complete field reference. `date`, `type`, `machine`, `repo`, `branch`, and `files-changed` come from the Evidence Gathering run of `derive-log-facts.py` above, as do the two fields it adds, `commit-range` and `latest-tag`. `decisions-count` is filled in by the agent once the Decisions Made section below is drafted, by counting that section's own entries, and `check-log.py` (see Log Self-Check below) then verifies the count mechanically before the wrap is done - it never ships as an uncorrected estimate. Everything else in this block is agent-filled.

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
---
```

### Body Sections (Final Mode)

**Summary** - 2-4 sentences. What happened and why it matters. When the Evidence Gathering same-arc check above judges the newest existing log to cover the same arc as this session, end Summary with one additional sentence naming that log by filename only (no path) and stating whether it was archived to `_superseded/` or not archived.

**Work Completed** - Bulleted list of what was accomplished.

**Decisions Made** - Each decision with rationale. Scale verbosity to significance:
- Minor: one-liner ("Chose MIT license - standard for personal repos")
- Significant: 2-3 sentences with reasoning
- Architectural: full alternatives-considered analysis

**Files Changed** - List from git, grouped by purpose if many.

**Gitignored Outputs** - Work products in gitignored locations, path plus a one-liner each. Without this section, `_local/` work is undiscoverable later. Omit only when there are none.

**Verification** - Checklist format. What was tested, what was assumed, what was skipped.

**Outstanding Issues** - Blockers, risks, unfinished work, including any sessions since the last log that were never wrapped (from capture-lite records, when present; see Evidence Gathering above).

**Hygiene Sweep** - Findings from the pre-wrap sweep: state found, actions proposed, actions taken vs declined.

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

Write the log, then run one command, and fix every finding before the wrap counts as done:

```bash
python <skill-dir>/scripts/check-log.py <log-path> --repo-root <project-root> --mode <quick|final|deep|blocked>
```

It runs every mechanical gate this section used to list as separate steps, in one invocation: the two detector-backed gates below exactly as they are, each still proving its own canary corpus before it scans and still reporting clean, findings, or broken, where a broken detector makes this script's own result broken too; `decisions-count` compared against a mechanical count of the Decisions Made section (skipped, not failed, in quick and blocked modes, whose templates carry neither); summary length (120 characters or fewer); Tier 1 frontmatter completeness, including `machine:`; the Waiting on You rules (section present, "Nothing pending." counting, no item beginning "Optional", every item carrying `(blocked since YYYY-MM-DD)`); and, in deep mode only, that the Uncertainty Ledger and What You May Not Realize sections are present ("Nothing material." and "Nothing surfaced." counting; absence does not). Exit 0 clean, 1 findings, 2 broken; `--json` for machine-readable output. Re-run after every fix until clean.

The two detector scripts it calls:

- Path citations resolve, detector-backed, three-state: `python scripts/path-citation-check.py <log-path> --repo-root <project-root>`. Checks only citations that assert a location: one containing a path separator must exist as written, and a backtick-wrapped citation with no separator is resolved against the repo root and passes silently if it does not resolve. A bare word with a file extension and neither signal is prose, not a path claim, and is not checked. Separator-bearing tokens that are URIs, drive-letter absolute paths, globs, template placeholders, single-segment slash commands, or extensionless are excluded too; see the script docstring for the canary corpus. Exit 0 clean, 1 findings, 2 broken; broken blocks exactly like findings
- No em-dash or en-dash characters anywhere in the log, detector-backed, three-state: `python scripts/dash-check.py <log-path>`. Exit 0 clean, 1 findings, 2 broken; broken blocks exactly like findings

The following gates are judgment calls no script can make and stay the agent's own check:

- Continuation prompt is self-contained (readable by a cold-start session with zero other context)
- Deep mode only: the Uncertainty Ledger is sorted by blast radius descending, every row names what would settle it, and every High-confidence/High-blast-radius row is marked `(!)`
- Deep mode only: **every What You May Not Realize item cites a source from this session**. An item with no source is dropped, never softened into a hedge

`derive-log-facts.py --count-decisions` still works, for compatibility with anything that calls it directly, but `check-log.py` is the one command a wrap now runs.

## Surrounding Document Updates

After writing the session log, check if changes warrant updates to:

- **README.md** - only if user-facing capabilities changed
- **CHANGELOG.md** - only if release-worthy (new feature, visible bugfix, breaking change)
- **Active plans** - only if sequence, scope, or assumptions changed
- **Decision records** - if an architectural decision was made this session, propose capturing it as an ADR (MADR, `docs/internal/decisions/` where the repo uses them)
- **Agent memory** - if durable facts or decisions emerged that outlive this session, confirm they are recorded in persistent memory rather than only in the log

**Before making any edit, state the intended change and ask for confirmation.** Never update surrounding docs silently.

If nothing warrants an update, move on without commenting.

## Constraints

- Never embed full transcripts - reference the transcript path only
- Never conflate "completed" with "verified" - state verification status explicitly
- Never commit, push, or modify anything beyond the session log without explicit per-action confirmation; the hygiene sweep proposes, the user disposes
- Never update surrounding docs without confirmation
- The Waiting on You section is mandatory in every mode; an empty list is stated, never omitted
- Summary must be ≤ 120 characters (for index display)
- The session log must be self-contained - readable without the original session
- Never produce an empty or generic continuation prompt
- Never produce a lighter-than-verbose continuation prompt without a stated objection (see "Default verbosity" above)
