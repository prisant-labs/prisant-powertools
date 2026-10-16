# plab-resolve-open-items

**Version:** 1.1.0
**Source:** [`skills/plab-resolve-open-items/`](../../../skills/plab-resolve-open-items/)

Walk through the questions, decisions and tasks a session has left open, answer them all in one line, and have each answer written back beside its question. Every walk also leaves a local walk record, so the conversation that produced the answers can be found again.

---

## Getting Started

### Quick Start

When a session has built up things only you can settle, ask for a walk in your own words:

```
Walk me through the pending questions, decisions, and needed clarifications.
```

The skill gathers what is open, presents it as numbered D, Q and T items, and waits for one line such as `D1 A, D2 B, Q1: the NAS, T1 later`.

### Common Invocations

```
# Walk everything this session has left open
/plab-resolve-open-items

# Walk the open items of one document only
/plab-resolve-open-items docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md

# The same, in plain words; the skill fires on either
resolve the open items in the WD-01 spec

# Sweep the whole repository, not just this session
/plab-resolve-open-items --backlog
```

### The `--backlog` sweep

`--backlog` gathers every pending item from the repository's specs, plans and the newest session log's Waiting on You list, in one script call. It sorts them into three tiers, ready for a yes or no, probably moot, and judgment, oldest first within each, and walks at most ten. The rest stay in a dated snapshot at `_local/decisions/YYYY-MM-DD_HH-MM_backlog.md`, written once per sweep and never edited afterwards; the report says how many items it holds beyond the ten shown. A moot item names the fact that made it moot, such as its home spec being superseded, and is offered as a cancel-or-keep decision. Answers write back exactly as an in-session walk's do; a Waiting on You item's answer lands in the walk record only, and the session log it came from is never written.

### Installation

Install via the prisant-labs marketplace:

```
/plugin marketplace add prisant-labs/agent-plugins
/plugin install prisant-utilities@prisant-labs
```

---

## When to Use

- A session has raised several questions or decisions, and you want to settle them together.
- You say "walk me through the pending questions and decisions", "resolve open items", "what do you need me to decide", or "decision sitting".
- You want one document's open items settled, such as a spec's "Open Questions / Decisions" section.

## When NOT to Use

- **A code walkthrough.** "Walk me through `bundle-check.py`" gets an explanation of the code, not a walk.
- **A single decision question.** "Should the record go in A or B?" gets a direct recommendation.
- **A status question.** "Where are we?" or "what's next?" gets an answer from context. If items are open, the answer says so and offers a walk.

---

## How It Works

1. **Gather.** Items come from two places only: what this conversation left unresolved, and the "Open Questions / Decisions" sections of documents this session read or wrote before you asked for the walk. The walk never goes looking for more. Pointed at one document, the walk covers that document alone.
2. **Present.** Each item is a **D** (a decision between lettered options, with a recommendation and a confidence level), a **Q** (a question only you can answer, with the default the walk assumes if you skip it), or a **T** (a task only you can do). An item found in several documents is shown once, under its one home.
3. **Read your answer.** One line answers everything. Each item ends up with one state.
4. **Write back.** Each answered item's home document is updated on its three surfaces: the summary-table row, the subsection's status, and the maintainer decision block, which gains a `Follow-up` line. Every other copy gets a pointer to the home. A self-check confirms nothing else changed.
5. **Ask again where needed.** Anything you asked about, did not understand, or answered with an alternative comes back in a further round, with more context.
6. **Record.** A walk record lists every item, your answer, and where it landed.
7. **Offer.** For an architectural decision, the skill offers an architecture decision record. On request, it prints a `gh issue create` command for you to run.

## An example walk

The skill presents:

```markdown
### D1: Sync authority (from docs/specs/sync.md, D1)

When both copies changed, which one wins? Conflicts are rare, but each one stops the sync today.

- **Option A:** The laptop wins, and the archive's version is kept beside it.
- **Option B:** The archive wins, and the laptop's version is kept beside it.

**Recommendation:** A. The laptop is where edits happen. Confidence: high.

### Q1: Archive drive name (no source document)

What is the archive drive called on the network?

**Default if skipped:** `archive`, the name in the setup notes.

### T1: Rotate the sync token (no source document)

The token expires on Friday. Answer `done`, `later` or `drop`.

Answer in one line, such as `D1 A, Q1: archive2, T1 later`, or `ok` to accept every recommendation and default.
```

You answer `D1 A, but I'm not sure. T1 later`. The result:

- **D1** is `Provisional`. The spec's D1 shows that status on all three surfaces, with your words "but I'm not sure" quoted in its reasoning and a `Follow-up` line naming the work.
- **Q1** is assumed to be `archive`, because you skipped it. The walk record marks it assumed, not decided, and no document is changed.
- **T1** is `later`, recorded in the walk record only.

## How answers are read

| You write | It means |
|---|---|
| `D1 A` | D1 is decided as option A |
| `D1 A, but I'm not sure` or `D1 A i guess` | D1 is provisional as option A, with your words kept |
| `D1 A. Why not B?` | D1 is decided as A, and your question is answered in the same reply |
| `D1: expand this` or `D1: I don't understand this` | D1 comes back next round, with more context |
| `Q1: the NAS` | Q1's answer is "the NAS", verbatim |
| `T1 done`, `T1 later`, `T1 drop` | The task's state |
| An item left out | A decision stays as it was; a question takes its stated default, marked assumed; a task stays open |
| `ok`, `accept all`, `accept the rest` | Every item not otherwise answered takes its recommendation or default |

Silence is never read as agreement. Only an explicit "ok" or "accept the rest" applies the recommendations.

## Where things land

| What | Where |
|---|---|
| An answer to an item from a document | That item's home document, on its three surfaces |
| Other copies of that item | A pointer to the home, with the home's status |
| Skipped decisions, assumed questions, tasks, and items from the conversation | The walk record only |
| The walk record | `_local/decisions/YYYY-MM-DD_walk_<slug>.md`, or a decisions folder your repository already names |
| An answer whose document is on another branch | Nowhere: the intended edit is printed for you instead |

The walk record stays local because it is the conversation. Its outcomes reach tracked files through write-back.

## Statuses

Write-back uses the seven statuses of `references/decisions-section.md` at the plugin root. **Open** and **Needs info** come before an answer. **Decided**, **Provisional**, **Deferred**, **Canceled** and **Superseded** are what an answer can be.

## The self-check

`scripts/walk-check.py` runs after every write-back and after the walk record is written:

```bash
python skills/plab-resolve-open-items/scripts/walk-check.py writeback <copy before> <document after>
python skills/plab-resolve-open-items/scripts/walk-check.py record <walk record>
```

Exit 0 is clean, 1 names each broken rule, and 2 means the check could not run, which is never read as clean. CI runs both modes against the committed sample in `skills/plab-resolve-open-items/examples/sample-walk/`.

## Not in this version

These are deferred or separate work:

- **No automatic GitHub filing.** The walk prints a `gh issue create` command and never files the issue itself.
- **No GitHub Projects board.** Items are not placed on, or moved across, a board.
- **No gathering across repositories.** A walk covers the current repository only.
- **No published web page.** A walk happens in the conversation, not on a rendered page.

## Reference Files

| File | Purpose |
|------|---------|
| `references/walk-format.md` | Sources, the D, Q and T series, the one-home rule, and the presentation format |
| `references/answer-line.md` | The answer grammar, the states, skips, explicit acceptance, and worked examples |
| `references/write-back.md` | The three surfaces, provisional answers, `Follow-up`, pointers, the branch guard, the self-check, and what needs confirmation |
| `references/walk-record.md` | The walk record's location, table, rounds, and an example |
| `references/backlog.md` | The `--backlog` sources, the three tiers, the cap, the moot presentation and the snapshot file |

## Hard Constraints

- Never writes to a document on another branch.
- Never rewrites an item's own analysis; only its status, its table row and its decision block change.
- Never reads silence as acceptance.
- Never runs `gh issue create`, and never writes an architecture decision record without your yes.
- Asks first only before deleting, pushing, merging, posting outside the repository, or editing outside the repository.
