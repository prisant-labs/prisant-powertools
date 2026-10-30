# Coverage statement

`build-pulse.py` writes `coverage.md` with these nine level-2 headings, in this order, every run (PP-01 contract C4). `pulse-check.py` fails a statement that lacks one or holds them out of order. A gap is written down, never left silent.

| Heading | What it holds |
|---|---|
| `## Window` | The focus week, the prior week, and the time zone |
| `## Roots` | Each root and the maximum depth |
| `## Repositories` | How many were found, active and dormant, and each alias skipped with its target |
| `## Without upstream` | Every repository with `has_upstream: false` |
| `## GitHub` | Whether `gh` ran, and each failed call with its command |
| `## Snapshots` | Snapshots read and fresh, snapshots found stale, and the `/plab-current-status` candidates |
| `## Session logs` | Logs read, logs listed as nonstandard names, and whether a supplied digest replaced the readers |
| `## Agents` | Every agent with its model, assigned and returned counts, and each escalation; items still missing |
| `## Snapshot times` | When the sweep ran and when the logs were read |
