# Walk record: the account of one walk

Every walk writes one walk record, whatever its outcome. The record holds every presented item, the answer or assumed default each received, every round, and where each answer landed. Step 6 of `SKILL.md`.

The record is the conversation, so it stays local. The outcomes reach tracked files through write-back and, where accepted, architecture decision records. The maintainer's rule, from 2026-10-07: the outcome is tracked, the conversation is local.

## Where it goes

1. **A folder the repository already names** for decision or sitting records, in its `AGENTS.md` or `CLAUDE.md`.
2. **Otherwise, `_local/decisions/`**, created if it does not exist. `_local/` is expected to be gitignored; if it is not, say so in the closing report rather than writing a record that could be committed by accident.

The filename is `YYYY-MM-DD_walk_<slug>.md`, where the slug names what the walk covered, such as `release-scope` or `spec-wd01`. If the file exists, add `-2`, `-3` and so on.

## Frontmatter

```yaml
---
type: walk-record
date: YYYY-MM-DD
repo: <owner>/<repository>
rounds: <the number of rounds, at least 1>
handle: <the one handle used for every write-back in this walk>
handle-source: <the document and block it came from, or "git config user.name">
backlog-file: <the backlog file this walk came from, for a --backlog walk only>
---
```

`handle` and `handle-source` are required, and `scripts/walk-check.py`'s R1 rejects a record missing either. They record the choice `references/write-back.md` makes once, before the first write: the handle used on every write-back in the walk, and where it came from, either a gathered document's filled maintainer block or the `git config user.name` fallback. This keeps one walk from writing two different handles into two different documents, which happened in the WD-01 (resolve open items) live trial before this rule existed.

`backlog-file` is optional, and only a `--backlog` walk writes it: the path of the dated snapshot `references/backlog.md` describes, so the record and the snapshot it walked can be found from each other. `scripts/walk-check.py`'s frontmatter parser reads frontmatter as a flat `key: value` dict and ignores any key its rules do not name, so this field needs no change to the checker; a record carrying it passes exactly as one without it.

## The items table

Under the heading `## Items, answers, and where each landed`, one row per presented item, with exactly these seven columns:

| Column | Contents |
|---|---|
| `Walk ID` | `D1`, `Q1`, `T1`: the item's id in this walk |
| `Home` | The home document and the item's own id there, such as `docs/specs/WD-07.md D2`, or `none` for an item with no source document. `none` may carry a short note, such as `none (merge PR #24)` |
| `Answer` | The maintainer's answer, in their own words in quotes where they gave any. An assumed Q's answer begins `default:`, followed by the default |
| `State` | One state from `references/answer-line.md`, for the item's series |
| `Round` | The round in which the final answer was given, or `-` when there was none |
| `Follow-up` | For a `decided` or `provisional` item, the action it requires and where that is tracked, or `None needed`. Otherwise `-` |
| `Landed` | Where the answer went, in the vocabulary below |

**The `Landed` vocabulary.**

| Value | When |
|---|---|
| `<path> (three surfaces)` | Written to the item's home |
| `<path> (pointer)` | A pointer written to a copy outside the home. Follows the home's entry, separated by a semicolon |
| `walk record only` | Every T item, every item with no source document, and every item from a document not in the decisions format |
| `not written` | An `unanswered` D, an `assumed` Q, and an edit the self-check rejected. A reason may follow a colon |
| `reported as text: branch <name>` | The home was on another branch, so the edit was printed instead |

## Rounds

One `## Round N` section per round, in order. Each says what was presented, by walk ID and handle, and quotes the maintainer's reply verbatim as a blockquote. The number of these sections equals `rounds` in the frontmatter.

A record may end with a short `## What the walk taught` section, for anything the walk showed about the items or the format. It is optional.

## Example

```markdown
---
type: walk-record
date: 2026-11-02
repo: prisant-labs/example
rounds: 2
handle: jp
handle-source: docs/specs/WD-07.md D2's maintainer block
---

# Walk record: release scope

## Items, answers, and where each landed

| Walk ID | Home | Answer | State | Round | Follow-up | Landed |
|---|---|---|---|---|---|---|
| D1 | docs/specs/WD-07.md D2 | "A, but I'm not sure" | provisional | 1 | Build option A in phase 2 of the WD-07 plan | docs/specs/WD-07.md (three surfaces) |
| D2 | docs/specs/WD-07.md D3 | "B", after asking for more context | decided | 2 | None needed | docs/specs/WD-07.md (three surfaces); docs/ideas/brief.md (pointer) |
| D3 | docs/specs/WD-07.md D4 | (no answer) | unanswered | - | - | not written |
| Q1 | none | default: staging | assumed | - | - | not written |
| T1 | none | "later" | later | 1 | - | walk record only |

## Round 1

Presented D1 (sync authority), D2 (record location), D3 (retry policy), Q1 (deploy target) and T1 (rotate the token).

> D1 A, but I'm not sure. D2: expand this. T1 later

## Round 2

Presented D2 again, with a before-and-after of the two record locations.

> D2 B
```

## Checking it

```bash
python <this skill's base directory>/scripts/walk-check.py record <walk record>
```

Exit 0 means the record is complete and consistent. Exit 1 names each rule broken; fix the record. Exit 2 means the check could not run, so say the record is unchecked.
