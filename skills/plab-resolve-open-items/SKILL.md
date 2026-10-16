---
name: plab-resolve-open-items
description: "Walk the maintainer through every open question, decision and task in the current session, then write each answer back to the document it came from. Use when the user asks to go through what is pending: 'walk me through the pending questions and decisions', 'resolve open items', 'what do you need me to decide', 'decision sitting'. Presents items as Q, D and T, D items with lettered options and a recommendation, takes a one-line answer such as 'D1 A, Q1: the NAS', and writes a walk record. Can be pointed at one named document. Do NOT fire on a request to walk through code or a file, on a single standalone decision question, or on a status question like 'where are we' or 'what's next'; answer those directly. '--backlog' sweeps every spec, plan and the newest session log for pending items, triages them, and walks up to ten, oldest first, writing a dated backlog file."
argument-hint: "[--backlog | <document>]"
license: MIT
metadata:
  version: "1.1.0"
  updated: 2026-10-15
---

# Resolve Open Items

Walk the maintainer through what the session has left open, take their answers in one line, and put each answer where it belongs. A walk holds three kinds of item: a **Q** is a question only the maintainer can answer, a **D** is a decision between lettered options, and a **T** is a task only the maintainer can perform.

An answer that lives only in the conversation is lost when the session ends. This skill writes each answer beside its question, in the document the question came from, and keeps one walk record of the whole exchange. The outcome is tracked; the conversation stays local.

## When to Use

- The maintainer asks to go through what is pending: "walk me through the pending questions, decisions, and needed clarifications", "resolve open items", "what do you need me to decide", "decision sitting".
- The maintainer names one document and asks to resolve its open items: "resolve the open items in `docs/.../spec.md`". The walk then covers that document alone.
- Several questions or decisions have built up in the session, and the maintainer asks to settle them together.

## When NOT to Use

- **A code walkthrough.** "Walk me through `bundle-check.py`" or "walk me through this file" asks for an explanation of code. Explain it.
- **A single standalone decision question.** "Should the record go in A or B?" asks for one recommendation. Give it directly, without a walk.
- **A status question.** "Where are we?" or "what's next?" asks for an answer from context. Give it. If items are open, say how many and offer a walk; do not start one.

## Workflow

### 1. Gather

**With `--backlog`:** run `python <this skill's base directory>/scripts/gather-backlog.py --repo <project root> --json`. On exit 2, report the named source as broken and stop; do not retry with a narrower scope. Otherwise triage the result into the three tiers of `references/backlog.md`, write the dated backlog file it describes, and select the items the walk will present: at most ten, ready then moot then judgment, oldest first within a tier. When the script returns no items, say so in one sentence and write neither a backlog file nor a walk record. The two sources below are for the walk without `--backlog`; skip them.

**Without `--backlog`:** collect open items from exactly two sources, both fixed at the moment the maintainer asks for the walk: this conversation's own unresolved items, and the "Open Questions / Decisions" section of every document this session read or wrote before that request. Never list a folder, open a file, or read a memory file to look for items; a file read during gathering is not a source. When the maintainer names one document, gather from that document's section alone. Assign each item to the Q, D or T series, and give each item one home. Rules: `references/walk-format.md`.

If nothing is open, say so in one sentence, offer to run `--backlog` or to walk one document the maintainer names, and stop. Do not write a walk record for an empty walk.

### 2. Present

Present every item in the format of `references/walk-format.md`: D items first, then Q, then T. End with one line on how to answer, for example: "Answer in one line, such as `D1 A, D2 B, Q1: the NAS, T1 later`, or `ok` to accept every recommendation and default."

The one-line answer is the contract, in Claude Code and in Codex alike. A structured multiple-choice prompt may present the same items where one exists, but the walk must work without it.

### 3. Read the answer line

Parse the reply with `references/answer-line.md`. Every presented item leaves this step with exactly one state. Silence about an item accepts nothing: an omitted D stays unanswered, an omitted Q proceeds on its stated default, and an omitted T stays open. Only an explicit "ok" or "accept the rest" accepts recommendations.

### 4. Apply

Write the answers back in the same pass, without asking first, following `references/write-back.md`. For each answered item with a home document, update its three surfaces and add a `Follow-up` line. Give every other copy of the item a pointer to its home. Before the first edit to a document, copy it; after the last edit, check the change:

```bash
python <this skill's base directory>/scripts/walk-check.py writeback <copy> <document>
```

Exit 0 means the edit stayed inside the three surfaces. Exit 1 means it touched something else: undo that edit and report it. Exit 2 means the check could not run, so report the edit as unverified rather than as done.

Never write a document on another branch; print the intended edit instead. Ask first only before deleting, pushing, merging, posting outside the repository, or editing a document outside the current repository.

### 5. Re-present what needs more

An item whose reply asked for more context, asked a question without making a choice, proposed an alternative, or said it was not understood is still open. Present those items again, as the next round, with more context than before. Show the concrete thing the item decides, such as a before-and-after of the text it would change, rather than describing it again. Then return to step 3. Items the maintainer skipped are not re-presented; a skip is an answer.

### 6. Write the walk record

Write one walk record for the walk, holding every item, every round, and where each answer landed, in the format and location of `references/walk-record.md`. Then check it:

```bash
python <this skill's base directory>/scripts/walk-check.py record <walk-record>
```

Fix whatever exit 1 reports. Exit 2 means the check could not run; say so.

### 7. Make the offers, then report

- **An architecture decision record.** For each decided item that meets the architectural bar in `references/decisions-section.md`, offer once to promote it to a MADR record. Write nothing unless the offer is accepted.
- **A GitHub issue.** When the maintainer asks for one, or the item's home already tracks it as an issue, print a ready `gh issue create` command and its body. Never run the command.

Close with a short report: what was written where, what was printed as text instead, what is still open, and the walk record's path.

## Not in this version

These are deferred or separate work, named here so their absence is not mistaken for an oversight:

- **Automatic GitHub filing.** The walk prints a `gh issue create` command; it never files an issue itself.
- **A GitHub Projects board.** No item is placed on, or moved across, a board.
- **Gathering across repositories.** A walk covers the current repository only.
- **A published web-page rendering of a walk.** A walk happens in the conversation.

## Constraints

- Never write to a document whose working tree is on another branch. Print the intended edit, naming the branch.
- Never rewrite an item's Summary, Context, Desired outcome, Options, Recommendation or Confidence text. Only the three surfaces change.
- Never infer acceptance from silence. Only "ok", "accept all", "accept the rest" or an equivalent explicit phrase accepts recommendations.
- Never run `gh issue create`. Never write an architecture decision record without an accepted offer.
- Never record a reply as a choice when it made none. A question without a choice re-presents the item.
- Never fabricate a source. An item from the conversation is marked "no source document".
- Any tracked file this skill writes, such as a decision record or an issue body, cites no `_local/` path and no path outside the repository.
- Confirm before deleting, pushing, merging, posting outside the repository, or editing outside the current repository. Ask nothing else before applying answers.

## References

| File | Purpose | Load when |
|------|---------|-----------|
| `references/walk-format.md` | The two sources, the Q, D and T series, the presentation format, and the one-home rule | Steps 1 and 2 |
| `references/answer-line.md` | The answer grammar, the answer states, skips, explicit acceptance, and worked examples | Steps 3 and 5 |
| `references/write-back.md` | The three surfaces, `Provisional`, `Follow-up`, pointers, the branch guard, the self-check, and what needs confirmation | Steps 4 and 7 |
| `references/walk-record.md` | Where the walk record goes, its table, its rounds, and an example | Step 6 |
| `references/backlog.md` | The `--backlog` sources, the three tiers, the cap, the moot presentation and the backlog file | Step 1, `--backlog` only |
| `references/decisions-section.md` (plugin root) | The decisions-section format and its seven statuses, which every write-back follows | Step 4 |

`references/decisions-section.md` is shared by several skills and lives at the plugin root, two folders above this skill's base directory, not in this skill's own `references/` folder. In a checkout of the plugin's repository, it is `references/decisions-section.md` at the repository root.
