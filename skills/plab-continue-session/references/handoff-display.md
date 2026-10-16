# Handoff Display Format

The structured resumption context shown to the user in Phase 4 of `/plab-continue-session`.

## Required structure

```markdown
## Resuming from: `<log filename>`

### What changed since this log
<the Markdown output of `scripts/reconcile.py`, pasted verbatim>

**Last session:** <date>, <model>, status `<status>`
**Summary:** <one-line summary from frontmatter>
**Branch:** `<branch>` <warning if mismatch>

### Waiting on you
<bullets from `## Waiting on You`, sorted oldest-blocked-first by each item's `(blocked since YYYY-MM-DD)` marker, links intact, or "Nothing pending." Lead with these: they are the maintainer's open obligations. If the log predates the section (pre-1.3.0 wrap), say so instead of fabricating a list.>

### Outstanding from last session
<bullets from `## Outstanding Issues`, or "None recorded.">

### Declined hygiene proposals
<from `## Hygiene Sweep`: proposals declined or unanswered at wrap time. Omit the heading entirely when there are none.>

### What's next (from last session)
<numbered list from `## What's Next`, or "Not specified.">

### Immediate next action
<the continuation prompt's immediate-action content, rendered as normal markdown - NOT fenced>

Full continuation prompt: `<path to the log>` - say "show the prompt" to print it verbatim.
```

After this block, ask the user one question (Phase 5): resume with the named immediate next action, or pick something else?

## What to include

- **What changed since this log:** the output of `scripts/reconcile.py` (Phase 3), pasted verbatim, leading the display ahead of every other section. This is drift, not a re-derivation of the log: commits landed, a tag cut, the log's branch gone, a cited path missing or renamed, or an advisory that the named next action may already be done. See `references/reconciliation.md` for what each check covers and the `ok` / `finding` / `broken` states. A broken check must stay visible by name; never fold it into a clean-sounding paraphrase (AC-8).
- **Frontmatter facts:** date, model, status, summary, branch. These set the cold-start context in three lines.
- **Waiting on you:** the log's open-obligations list, first. Resumption exists to close these loops; burying them below the fold defeats the section.
- **Outstanding issues:** if the log recorded blockers, risks, or unfinished work, show them. The user resuming needs to know what's known to be incomplete.
- **Declined hygiene proposals:** actions the wrap proposed and the user declined or left unanswered; they are re-decidable now.
- **What's next:** if the log has a `## What's Next` section, show its ordered list. This is the wrapping agent's recommendation; the continuation prompt is its operationalization.
- **Immediate next action:** the one action the prompt names, rendered as ordinary markdown, plus the log path on its own line.

The prompt itself is **not** dumped verbatim. The rule, its rationale, and how to locate the immediate action live in SKILL.md Phase 4, "Do not dump the prompt", and are deliberately not restated here - one rule, one home.

## What to elide

- The full `## Decisions Made` section (read on demand if the user wants depth)
- The full `## Files Changed` list (git status gives the same info, fresher)
- The full `## Verification` checklist (the user can read it if they want depth)
- The `## Summary` body paragraph (the frontmatter summary line is enough)
- The `## Parked` list (optional context; read the log directly if wanted)
- A second, independent re-derivation of facts the "What changed since this log" section already covers (commits, tags, branch existence, cited paths): that section is `scripts/reconcile.py`'s output pasted once, not a claim to re-check by hand elsewhere in the display

The display is a header for re-entry, not a re-read of the entire log. If the user wants depth, they can open the log file (give them the path). The leading "What changed since this log" section is drift against live repository state, not a second pass over the log's own content, so it stays a short, pasted script output rather than growing into its own re-read.

## Mismatch warnings

If the log's `branch` doesn't match `git branch --show-current`, append to the Branch line:

```
**Branch:** `feature/x` (log) - currently on `main` (warning)
```

This fires only when the current branch differs from the log's branch. It is distinct from, and additive to, the "What changed since this log" section's branch-existence check (AC-5), which reports whether the log's own branch still exists at all, locally and on the remote, independent of what branch the resuming session happens to be on. A future reader should not treat the two as duplicates and delete one: this warning can fire while the log's branch still exists (you're just somewhere else), and the reconciliation check can fire while this warning stays silent (you're on the log's own branch, and it has since been deleted out from under you).

If the log's `repo` doesn't match the current repo (per `references/log-discovery.md`), refuse to resume entirely; surface the mismatch and exit.

## When the log lacks structure

If the log file is malformed (missing frontmatter, missing `## Continuation Prompt` section, missing `## Summary`), surface what's missing and offer to:

1. Read the log file directly and decide what to do
2. Pick a different log
3. Start fresh without resuming

Do not synthesize a resumption from a malformed log; the cost of a wrong synthesis is higher than the cost of asking the user to look at the file.

## Tone

Direct. No "I'd be happy to help you continue!" preamble. The user invoked this skill because they want to resume; the skill's job is to present the state and ask one focused question.
