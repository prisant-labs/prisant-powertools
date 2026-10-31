# Coverage statement

`build-pulse.py` writes `coverage.md` with these nine level-2 headings, in this order, every run (PP-01 contract C4). `pulse-check.py` fails a statement that lacks one or holds them out of order. A gap is written down, never left silent.

| Heading | What it holds |
|---|---|
| `## Window and zone` | The focus week, the prior week, and the time zone |
| `## Roots and depth` | Each root and the maximum depth |
| `## Repositories found and aliases skipped` | How many were found, active and dormant, and each alias skipped with its target |
| `## Repositories without an upstream` | Every repository with `has_upstream: false` |
| `## gh failures` | Whether `gh` ran, and each failed call with its command |
| `## Snapshots read and stale` | Snapshots read and fresh, snapshots found stale, the `/plab-current-status` candidates, and when the sweep ran |
| `## Logs read and nonstandard names` | Logs read, logs with nonstandard names, and whether a supplied digest replaced the readers |
| `## Agents` | Every agent with its model and its assigned and returned counts |
| `## Escalations and items still missing` | Each escalation, and every assigned repository that no scout returned |
