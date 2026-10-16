# Backlog: the repository-wide sweep

How `--backlog` gathers, triages, writes a dated snapshot and walks the oldest items first. Workflow step 1 of `SKILL.md`, in its `--backlog` branch.

## Sources and the status filter

`--backlog` reads exactly two kinds of source, both gathered by one call to `scripts/gather-backlog.py --repo <project root> --json`: the "Open Questions / Decisions" section (or a heading variant `references/walk-format.md` names) of every git-tracked Markdown file whose frontmatter `type` is `spec`, `implementation-plan` or `release-plan`, and the "Waiting on You" section of the newest session log, found by the newest-wins rule in `skills/plab-continue-session/references/log-discovery.md`. Only a row or bullet whose status is `Open`, `Needs info` or the legacy `Proposed` is pending; the script applies that filter, so nothing downstream needs to re-check it. Never gather by reading documents one at a time; the script is the only way `--backlog` gathers.

On exit 2, the script names the one source it could not parse. Report that source as broken and stop; do not retry with a narrower scope and do not present a partial walk.

## The three tiers

Assign every gathered item to exactly one tier.

- **Ready.** A D or Q item whose recommendation is small and blocks nothing else: a one-line answer settles it, and nothing downstream depends on which way it goes.
- **Moot.** An item whose premise later work removed. State the evidence in one line, naming a fact the maintainer can check without opening the item's own analysis.
  - A decisions-section item (`source_kind: "decisions-section"`): its own home document's frontmatter `status` is `fulfilled` or `superseded` while the item itself is still `Open`, `Needs info` or `Proposed`. The script's `home_status` field carries this for exactly that check.
  - A Waiting on You item (`source_kind: "waiting-on"`): the bullet's action is already done, for example a named pull request has merged, or a file the bullet asks to delete no longer exists.
- **Judgment.** Everything else: a real trade-off, a fact only the maintainer has, or a task that is not moot.

An item that could fit more than one tier takes the first that applies, in the order above: a moot item is never also called ready.

## Order and cap

Present at most ten items in one walk: every ready item first, then every moot item, then judgment items, oldest first within each tier by the item's `age_days` (an item with `age_days: "unknown"` sorts after every item with a known age, within its tier). The report that opens the walk states how many items the backlog file holds in total and how many are shown, for example "Backlog: 14 open items, 10 shown."

"Oldest first within a tier" governs two things that can give different answers, and both matter: which items are selected when a tier has more candidates than fit under the cap, and the row order inside that tier's table in the backlog file. Both are strict age order across every item in the tier, a D or Q or T or a Waiting on You item alike; a tier of eight items with room for four keeps the four oldest, whatever series they belong to. The backlog file's three tables are written in that same strict age order. The walk's own chat presentation, inside one tier's block, still follows `references/walk-format.md`'s existing convention of D items, then Q, then T, because that convention is what every other walk this skill produces already uses and changing it only for `--backlog` would make one tier read differently from the walk without it.

## Presenting a moot item

A moot item is a D item with two options: **A**, cancel it, recommended, with the moot evidence as the reason; **B**, keep it open. Accepting A writes `Canceled` on the item's home document, on the three surfaces `references/decisions-section.md` defines, with the moot evidence as the `Reasoning` line and `Follow-up` set to `None needed.` unless the evidence names a follow-up of its own. Choosing B leaves the item exactly as gathered; it is presented again by a later sweep.

## Presenting a Waiting on You item

An item with `source_kind: "waiting-on"` is a T item, or a D item when the log's bullet itself names options for the maintainer to choose between. Its source is the session log, named in the presentation; the walk never asks whether to update the log, because logs are dated records and this skill never writes one. The item's answer is recorded in the walk record only, exactly as an in-session walk already records a T item or an item with no source document. `references/write-back.md`'s write-back rules do not apply to it, because it has no home document to write to.

## The backlog file

A sweep that gathers at least one item writes exactly one file, at `_local/decisions/YYYY-MM-DD_HH-MM_backlog.md`, beside the walk records this skill already writes. It is a dated snapshot: write it once, when the sweep runs, and never edit it afterwards, even after the walk answers some of its items. A later answer changes the item's home document and the walk record; the backlog file keeps recording what the sweep saw at the time it ran.

Its format:

```markdown
# Backlog: YYYY-MM-DD HH:MM

Repository: <owner>/<repository>
Items gathered: <count>

## Ready

| Item | Home | Id | Status | Age (days) |
|---|---|---|---|---|
| <title> | <home path, or the session log's path> | <id> | <status> | <age, or "unknown"> |

## Moot

| Item | Home | Id | Status | Age (days) | Evidence |
|---|---|---|---|---|---|
| <title> | <home path> | <id> | <status> | <age, or "unknown"> | <the one-line moot evidence> |

## Judgment

| Item | Home | Id | Status | Age (days) |
|---|---|---|---|---|
| <title> | <home path, or the session log's path> | <id> | <status> | <age, or "unknown"> |
```

A tier with no items keeps its heading and states "None." under it, rather than being omitted, so the file always shows all three tiers were considered.

## Nothing to gather

When the script returns no items, say so in one sentence, for example "Nothing is open across this repository's specs, plans and newest session log," and write neither a backlog file nor a walk record. This mirrors the in-session walk's own empty-walk rule in `SKILL.md` step 1.
