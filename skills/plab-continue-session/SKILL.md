---
name: plab-continue-session
description: "Resume an interrupted work session by replaying its recorded handoff.
  Use when the user explicitly asks to resume: 'resume', 'continue session', 'pick up
  where we left off'. Reads the most recent session log, reports what was outstanding
  and the named next action, then confirms before acting. Do NOT fire on status
  questions like 'where are we' or 'what's next'; answer those directly rather than
  resuming. Companion to plab-wrap-session, which writes the log this reads."
argument-hint: "[--log <path>]"
license: MIT
metadata:
  version: "1.5.0"
  updated: 2026-09-15
---

# Continue Session

Resume the work that the last session left set up to resume. Pairs with `/plab-wrap-session`: that skill writes the continuation prompt, this skill processes it.

## When to Use

- Start of a coding session, when prior work exists
- Resuming after a break (a day, a week)
- Picking up work another agent or person did
- When the user says "continue", "resume", or "pick up where we left off"

## When NOT to Use

- Truly fresh project with no session-log history (just start working)
- The user already named the specific task they want to work on
- Mid-session "what have we done so far" (just summarize from current context; no need to re-read a log)
- **A status question** ("where are we", "where were we", "what's next", "what were we doing"). Answer it directly from context, or read the log and answer from it. Do not run the resumption ritual. This is the most common mis-fire for this skill.

## Workflow

### Phase 1: Locate the latest session log

1. Collect `.md` files from **all three** stores, skipping any that do not exist:
   - `_local/_session-logs/` (current) - both its top level and its `YYYY-MM/` month folders
   - `_agent-context/session-log/` (legacy, plab-wrap-session v1.1.0 - v1.2.x)
   - `AGENTS/session-log/` (legacy, plab-wrap-session v1.0.x)

   Month folders are the only subdirectory shape that is read. `_capture/` and anything else inside the store are deliberately invisible. Full rules and both shell pipelines: `references/log-discovery.md`.
2. Pick the newest across the combined set - not the first location that happens to be non-empty. The filename pattern is `YYYY-MM-DD_HH-MM_<llm>_<title>.md`, so lexical descending sort = most recent first. Searching all locations matters because a project mid-migration has old logs in a legacy path and new ones in `_local/_session-logs/`; stopping at the first non-empty directory would resume from the wrong era. Because the sort is on the filename and never the path, an archived log in `2026-06/` and a hot log at the top level order correctly against each other.
3. Confirm the file exists and is non-empty. If no location yields a log, report "no prior session log found" and ask the user how to proceed.
4. If the winning log came from a legacy path, surface a migration note alongside the resumption.

If multiple logs share the same date+time prefix (rare; concurrent sessions by different LLMs), surface all and ask the user which to resume.

### Phase 2: Read and parse

1. Read the full log file.
2. Extract from frontmatter: `date`, `repo`, `branch`, `summary`, `status`, `session-type`, `model`, `agent`.
3. Extract from body: the `## Continuation Prompt` section (always present in a well-formed log) and any objection statement if the prompt was lighter than verbose (see `references/objection-detection.md`).
4. Extract from body: `## Waiting on You` (required in logs from plab-wrap-session 1.3.0+), `## Outstanding Issues` (if any), `## What's Next` (if present), and any declined or unanswered proposals recorded in `## Hygiene Sweep`.

If the log lacks a `## Continuation Prompt` section, report the log path and ask the user how to proceed without one.

### Phase 3: Reconcile against reality

Before any of the log's content is presented as though it were still current, derive what has actually changed in the repository since the log was written. Run:

```bash
python <this skill's base directory>/scripts/reconcile.py <project_root> <log_path>
```

`<this skill's base directory>` is this skill's own installed location, not the project being resumed in; running the bare relative path `scripts/reconcile.py` from the project root fails, the same convention `plab-resolve-open-items` uses for `scripts/walk-check.py`. `<project_root>` is the current working directory in the normal case; `<log_path>` is the log Phase 1 selected. Full invocation details, the output's three-state (`ok` / `finding` / `broken`) contract, and what each check covers: `references/reconciliation.md`.

Paste the script's Markdown output verbatim under the `### What changed since this log` heading in Phase 4's display. Do not re-summarize it: a broken check must stay visible by name, never be silently folded into a clean-sounding paraphrase.

This step is read-only. It runs a non-pruning fetch against the remote and nothing else that touches the working tree, the index, or HEAD; see `references/reconciliation.md` for the full list of commands it runs and does not run.

### Phase 4: Present the resumption context

Display, in this order, before doing anything else:

```markdown
## Resuming from: <log filename>

### What changed since this log
<the Markdown output of `reconcile.py`, pasted verbatim>

**Last session:** <date>, <model>, status <status>
**Summary:** <one-line summary>
**Branch:** <branch>

### Waiting on you
<bullets from the Waiting on You section, links intact - lead with these; they are the maintainer's open obligations. "Nothing pending" if the log says so; a note if the log predates the section>

### Outstanding from last session
<bullets from Outstanding Issues, if any>

### Declined hygiene proposals
<from the Hygiene Sweep section: proposals declined or unanswered at wrap time, if any>

### What's next (from last session)
<numbered list from `## What's Next`, or "Not specified.">

### Immediate next action
<the prompt's immediate-action content, rendered as normal markdown - NOT fenced. See "Do not dump the prompt" below.>

Full continuation prompt: `<path to the log>` - say "show the prompt" to print it verbatim.
```

If the prompt is lighter than verbose and carries an objection ("trivial typo fix; no context to carry forward" etc.), surface the objection in the display.

#### Do not dump the prompt

**Never print the continuation prompt verbatim in a fenced block unless the user asks for it.** A verbose prompt runs to a hundred lines or more, and inside a fenced block none of its markdown renders, so the user reads `**bold**` and backtick noise as literal source. It is the single longest thing on screen and the least readable.

The verbatim form exists so a prompt can be **pasted into a cold-start session that has not read the log**. This skill is the opposite case: it has already read the whole log, and so has the user's own last session. Reprinting it carries no information the agent does not already hold.

So:

1. **Render, don't fence.** Extract the prompt's immediate-action content and present it as ordinary prose and lists, so the markdown actually renders.
2. **Point at the source.** Give the log path on one line. The full prompt is always one `cat` away.
3. **Keep verbatim as opt-in.** If the user says "show the prompt", print the whole thing in a fenced block exactly as written. Someone resuming in a different tool still needs to copy it.

**Finding the immediate-action content.** `/plab-wrap-session` requires the prompt to be "bounded - one clear immediate action, then ordered secondary steps", but does **not** mandate a heading for it. Prefer an explicit heading (`## Immediate next action` or similar) when the prompt carries one. Otherwise take the prompt's first imperative block, and if the prompt is short enough to be unambiguous, render the whole thing. Never invent an action the prompt does not name.

**Everything above this section still displays in full.** Waiting on you, outstanding issues, declined proposals and what's next are short, they render as markdown, and they are the part the user is re-entering for.

### Phase 5: Confirm before acting

Ask the user: "Resume with the named immediate next action, or pick something else?"

- **Resume:** proceed with the action named in the continuation prompt.
- **Pick something else:** stop here. The user takes over from this state.
- **Read more context:** open the log file for the user to inspect, then ask again.

Never auto-execute the continuation prompt without explicit user confirmation. The prompt is a recommendation, not a command.

### Phase 6: Hand off

When the user confirms resumption, do not narrate "I'll continue from where we left off." Just start the named immediate next action. The continuation prompt was the handoff; processing it is acting on it.

Note the consumed log's filename: when this session is eventually wrapped, `/plab-wrap-session` (1.4.0+) records it in the new log's `resumed-from:` frontmatter. That field is how log consumption, and the wrap/continue pair's actual payout rate, gets measured.

## Constraints

- Never modify the session log being resumed from
- Never auto-execute the continuation prompt without user confirmation
- Never dump the whole continuation prompt in a fenced block unless the user asks; render its immediate action and give the log path instead (Phase 4, "Do not dump the prompt")
- When the user does ask to see it, reproduce it verbatim; never paraphrase the prompt itself
- If the latest log is older than 7 days, surface "this log is N days old; are you sure?" before resuming
- If the log's `branch` field doesn't match the current git branch, surface the mismatch and ask
- If the log's `repo` field doesn't match the current repo, refuse and surface a cross-repo warning
- Never blend multiple logs together; resume from exactly one log per invocation
- The Phase 3 reconciliation step never mutates repository state: it runs no `pull`, `merge`, `checkout`, `reset`, or `push`, nor any equivalent, and `scripts/test-reconcile.py` asserts this against the script's own recorded command list at runtime

## Output

This skill produces no files. Its output is the resumption context (displayed to the user) and the act of beginning the named next action (or stopping, if the user redirects).

## Pairing with `/plab-wrap-session`

`/plab-wrap-session` writes the continuation prompt at session end. `/plab-continue-session` reads and processes it at session start. Together they bracket a session and make agent / human handoff reliable across context resets.

If a session you're resuming was wrapped poorly (missing prompt, vague prompt), surface the gap to the user so they can decide whether to invest in better wrapping going forward.

## References

| File | Purpose | Load when |
|------|---------|-----------|
| `references/log-discovery.md` | How to find the latest log; newest-wins search across current and legacy locations; tie-breaking rules | Phase 1 |
| `references/objection-detection.md` | How to detect and surface a stated objection that justifies a lighter-than-verbose continuation prompt | Phase 2 |
| `references/reconciliation.md` | How to invoke `scripts/reconcile.py`, read its three-state (`ok` / `finding` / `broken`) output, and what each check covers | Phase 3 |
| `references/handoff-display.md` | The resumption context display format; what to include and what to elide | Phase 4 |
