# Write-back: applying the answers

How each answer reaches its home document, what is never touched, and what needs the maintainer's confirmation first. Steps 4 and 7 of `SKILL.md`.

Applying the answer line needs no confirmation. Writing answers into current-branch documents and writing the walk record happen in the same pass that reads the reply.

## What is written where

| Item | Written to |
|---|---|
| A sourced D or Q item that is `decided`, `provisional`, `deferred` or `canceled` | Its home's three surfaces, below |
| Every other copy of that item | A pointer to the home, below |
| An `unanswered` D, an `assumed` Q, or any T | Nothing but the walk record |
| An item with no source document | Nothing but the walk record |

A skipped item's document is left exactly as found. An assumed Q is not a decision, so it is never written as one.

## The three surfaces

`references/decisions-section.md`, at the plugin root, defines three surfaces that change together when an item's status changes. Update all three, and nothing else.

1. **The summary-table row.** Set `Resolution` to a short outcome, such as `Option A`, `Option A, provisional`, `Deferred to the layout effort`, or a Q's answer in a few words. Set `Status` and `Updated`, the date as `YYYY-MM-DD`.
2. **The subsection header's trailing status.** `### D3: <Title> (Open)` becomes `### D3: <Title> (Decided)`.
3. **The maintainer block.** Replace the pending block with the filled form:

```markdown
> **Maintainer decision:** <Status> <YYYY-MM-DD> by <handle>
>
> * **Status:** <Status>
> * **Choice:** <Option X, or the Q's answer>
> * **Reasoning:** <the maintainer's own words in quotes where they gave any, then why, in one or two sentences>
> * **Follow-up:** <the action this requires, and where it is tracked>, or None needed.
> * **Decided by / date:** <handle> / <YYYY-MM-DD>
```

**One handle for the whole walk.** Choose the handle once, before the first write of the walk, not per document. Look through the walk's gathered documents, in the order in which this session touched them (`references/walk-format.md`), for the first filled maintainer block, meaning one whose `Decided by / date` names a handle rather than `(none)`, and use that handle for every write in the walk, even one to a document whose own filled blocks use a different handle. Only when no gathered document has a filled block, use `git config user.name`. Record which source supplied the handle, the document and its block or `git config user.name`, in the walk record's frontmatter (`references/walk-record.md`).

The document statuses map from the walk's states: `decided` is `Decided`, `provisional` is `Provisional`, `deferred` is `Deferred`, and `canceled` is `Canceled`.

**Never edit the item's body.** Its Summary, Context, Desired outcome, Options, Recommendation, Confidence and "Default if skipped" text stay exactly as they were. They are the record of what was on the table when the maintainer chose.

## Provisional answers

A `provisional` answer takes the status `Provisional` on all three surfaces. The `Reasoning` line quotes the maintainer's words of doubt verbatim, for example: `In the maintainer's words: "A. However this feels a little incomplete and unsettled and I can't articulate why."` The choice is in force; the status says it may be revisited.

## Follow-up

Every `Decided` or `Provisional` block carries a `Follow-up` line, because a decision recorded as made can sit unbuilt with no status that says so. Name the concrete next action and where it is tracked: a phase of an implementation plan, a spec's requirement, a backlog entry, or the walk record. Write `None needed.` when the decision is its own end, such as an approval that has already been carried out.

## Pointers in other copies

Every copy of an item outside its home receives a pointer on its own three surfaces, never a second copy of the answer:

- the table row's `Resolution` reads `See <home path> <id>`, and its `Status` mirrors the home's status;
- the header's trailing status mirrors the home's status;
- the block's `Choice` reads `Recorded in <home path> <id>`, its `Reasoning` reads `Answered in the home document.`, and it carries no `Follow-up` line, because the follow-up lives in the home.

Mirroring the status matters. A copy still marked `Needs info` after the answer exists would be gathered and asked again by the next walk that touches it.

## The branch guard

Never write to a document whose working tree is on a different branch from the walk's.

```bash
git -C <folder containing the document> rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref HEAD
```

The first command gives the document's branch, the second the walk's. A gitignored document inside the current working tree is on the current branch.

- **The branches differ** (the document is in another worktree): write nothing. Print the intended edit as text, in full, under a line naming the branch it would have targeted.
- **The document is in another repository, or in no repository:** this is an edit outside the current repository, so ask before writing it.

## The self-check

`HEAD` is not a safe "before", because the session may already have edited the document for other reasons. So, immediately before the first edit to a document, copy it to a temporary file. After the last edit, compare the two:

```bash
python <this skill's base directory>/scripts/walk-check.py writeback <copy> <document>
```

| Exit | Meaning | What to do |
|---|---|---|
| 0 | Only the three surfaces changed, consistently | Report the write-back as done |
| 1 | Something else changed, or the surfaces disagree | Undo the offending edit, and report what the check named |
| 2 | The check could not run | Report the write-back as unverified, never as done |

## What needs confirmation

Ask before any action that:

- deletes a file or folder;
- pushes, merges, or tags;
- posts anything outside the repository, such as an issue or a comment;
- edits a document outside the current repository.

Ask nothing else. The answer line is the maintainer's instruction; asking "shall I write these?" after it adds a round for nothing.

## The architecture decision record offer

`references/decisions-section.md` sets the bar in its Lifecycle section: a decision becomes architectural when alternatives were considered, it is hard to reverse, and it would look wrong to a reader without its context. For each decided item that meets the bar, offer once:

> D4 meets the bar for an architecture decision record: <one line on why>. Promote it to `docs/internal/decisions/NNNN-<slug>.md`?

Write nothing unless the maintainer accepts. If accepted, write a MADR v4 record in the repository's existing decision-record folder, or `docs/internal/decisions/` if none exists. Then name the record in the home item's `Follow-up` line. The record is tracked, so it cites no `_local/` path and no path outside the repository.

## The GitHub command

Print a ready command when the maintainer asks for one, or when the item's home already tracks it as an issue. Write the body to a file beside the walk record, then print:

```bash
gh issue create --title "<walk id>: <handle>" --body-file <path to the body file>
```

The body states the question, every option in full, the recommendation with its confidence, and the home document. It is public text, so it cites no `_local/` path. Never run the command. Filing is the maintainer's action.
