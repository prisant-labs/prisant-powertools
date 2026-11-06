# Documentation standard

The bar for every branch `/plab-ship` carries is best in class, not adequate. A reader in any layer should find the change, use it correctly the first time, understand why it works that way, and confirm it worked or recover when it did not.

This standard takes the opposite posture from `plab-wrap-session`'s `references/doc-update-rules.md`, which says "when in doubt, don't update". That rule suits a wrap, which reconciles documents it did not set out to change. Shipping is the moment a change becomes real to everyone who relies on the documents, so here the question is reversed: when in doubt, update, or record why not.

## The twelve cells

Three layers are the readers. Four depths are what each reader needs.

| Depth | The question | Human | Technical | Agentic |
|---|---|---|---|---|
| **Discover** | Does the reader know it exists? | README, CHANGELOG or release notes, docs index | Architecture overview, spec status, release index | `AGENTS.md` entry, skill description with its trigger and do-not-fire clauses |
| **Use** | Can they do it correctly the first time? | Quick start, guide, real examples, help and FAQ | Build, test, run and release commands, config register | Exact commands, flags and paths, and how to invoke it in each harness |
| **Understand** | Is the reason recorded? | Explanation, limits, when not to use it | Decision record with the rejected options, design notes, schemas | Rules with their reasons, non-obvious constraints and traps |
| **Trust** | Can they confirm it worked and recover if it did not? | Expected output, error messages, troubleshooting, upgrade and migration | Test evidence, failure modes, rollback | Evals, check scripts, and what remains unverified |

## How to fill a cell

Every cell holds one of three states, and `ship-check.py` rejects anything else.

| State | Meaning | The cell must name |
|---|---|---|
| `updated` | This branch changed a file for this cell | The file, in backticks. The check confirms it changed in the merge |
| `correct` | A file already covers this cell, and you read it to confirm that | The file, in backticks. The check confirms it exists |
| `n/a` | The cell does not apply to this change | A reason of at least three words |

An empty cell is the failure this format exists to expose. "Docs updated" hides a missing troubleshooting section, and a row that must say `n/a` with a reason does not.

## Scale to the change

| The change | What it owes |
|---|---|
| A fix that changes no behaviour | Its CHANGELOG line and any cell the fix touches. The other cells are `n/a`, and "This fix changes no behaviour" is a sufficient reason |
| A fix that changes behaviour | The same, plus the Use and Trust cells that described the old behaviour |
| A feature | Every cell considered on its merits. Expect most to be `updated` or `correct` |
| A breaking change | Everything a feature owes, plus a migration path in Human / Trust, naming what to do and in what order |

## What good looks like

- **Examples are real.** Run every command you write down. An example that has not been run is a claim, not documentation.
- **The reason is recorded where the rule is.** "Do not hard-wrap prose" is weak. The same rule followed by the measurement behind it survives a future agent's temptation to undo it.
- **Limits are stated plainly.** Say what a tool does not prove, such as that a pattern screen does not rule out a secret.
- **The same word means the same thing.** Do not vary a name for elegance across the layers. A reader searches for the word they were given.
- **Update what the change made false.** Search the documents for the old name, the old flag and the old count. A stale sentence does more harm than a missing one.
- **Write for someone who was not in the session.** Do not rely on context that exists only in the conversation that produced the change.

## The new-surface gate

List every new flag, command, path and skill name on the block's `**New surface:**` line. `ship-check.py --repo` adds the flags and skills it can detect in the diff: `add_argument` definitions, `argument-hint` lines, and added `skills/<name>/SKILL.md` files. Each token must appear in a file the record names in its Human layer, at the merged commit.

This proves presence and not quality. It catches the common failure, a flag that exists only in the code, and nothing subtler.

## The cold reader

The cold reader tests what the gate cannot: whether someone new can use the documents. Run it for a feature or a behaviour change, as a Sonnet subagent with an explicit model, in a fresh context. Where the harness has no subagent, record that it did not run and why.

Give it only the human-layer documents the branch changed, and these instructions:

> You have never seen this project. Read only the documents listed below, and do not read any source code, tests or other files. Answer each question from the documents alone, quoting the line you relied on:
>
> 1. What is this for, and who is it for?
> 2. When should I not use it?
> 3. What exactly do I run first?
> 4. What should I see when it worked?
> 5. What do I do when it fails?
>
> Then follow the quick start exactly as written, unless it would change something outside a throwaway folder. In that case, say what you would have run and do not run it. Report each question you could not answer and each step that did not behave as written. Do not suggest improvements beyond those gaps.

Fix each gap on the branch before merging, and record the result on the block's `**Cold reader:**` line. A gap you decide not to fix goes in the record's Unverified section with the reason.

For a change where a second opinion is worth its cost, `/plab-ai-review --dispatch` sends the documents to Codex. For a topic that deserves its own multi-depth bundle, `/plab-guide` is the route. Neither is part of a routine run.

## The documentation map

Each repository may keep a map in `.claude/plab-ship.local.md`, so the skill does not have to guess which files belong to which layer:

```markdown
---
human: README.md, CHANGELOG.md, docs/skills/*
technical: docs/internal/*, docs/status-skills.md
agentic: AGENTS.md, CLAUDE.md, skills/*/SKILL.md, skills/*/references/*
not-docs: evals/*, */examples/*
---
```

Each line is a comma-separated list of globs. Without the file, `derive-ship-facts.py` detects a map and reports `source: detected`. Propose the map in the record's Unverified section in that case, so it can be kept.
