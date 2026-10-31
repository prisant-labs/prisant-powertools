# Scorecard rules

The scorecard scores only items the owner was asked to decide or do, found in the configured decision sources, and lists every source it read.

## Verdicts

| Verdict | Meaning | Evidence it needs |
|---|---|---|
| Done | Applied and in effect | A file and line, a setting, or a command and its output |
| Partial | Some of it applied | The same, for the applied part |
| Not done | Nothing changed | The unchanged file, or the absence the item named |
| Overtaken | A later decision replaced it | The later decision's record |
| Decided, not applied | The owner decided, and nobody acted | The decision record and the unchanged target |

## The evidence rule

Every verdict carries an evidence entry: a path and line, a command and its output, or a ledger row. A verdict without evidence is not written.

## The approval rule

A claim that the owner approved, chose, declined, decided or said yes to something quotes the record in double quotes or names its path in backticks. A claim of approval without a record is removed, because a worker once reported an approval the owner never gave. `bundle-check.py` rule R9 enforces this in the written bundle.

## Asked count

Each open ask carries `asked_count`, the number of consecutive audits that have raised it, read from the previous scorecard. When an ask reaches three, the recommendation changes form: offer the groundwork that would make the decision easy (a plain explainer, a built tool, or a proposal to drop the ask) instead of asking again.

## Decision pattern

After the table, say in a few sentences what got decided this week and what stalled, and what the stalled items have in common. The useful finding is usually the kind of groundwork a stalled item lacks.
