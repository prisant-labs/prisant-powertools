# Status snapshot format

The one format `plab-current-status` writes and `scripts/status-check.py` enforces. The rule ids in brackets are the checker's. The committed sample at `examples/sample-status/` passes every rule and is the worked example.

## Location and name [R1]

`_local/_status/YYYY-MM-DD_<model>_<byline>.md` in the repository root.

- `YYYY-MM-DD` is today's date.
- `<model>` is the running model's id without its vendor prefix, in lowercase kebab-case: `claude-opus-5-5` becomes `opus-5-5`, and `claude-fable-5-1` becomes `fable-5-1`.
- `<byline>` is two to six lowercase kebab-case words that say what this snapshot found, such as `export-blocked-on-two-answers`. It is a summary, not a label like `status-update`.

Only files matching this pattern count as earlier snapshots. Hand-written files in the same folder, such as a decision register, are never read as the previous snapshot.

## Frontmatter [R2]

```yaml
---
type: status-snapshot
date: 2026-10-28                 # equals the filename's date
model: opus-5-5                  # equals the filename's model
repo: example-app                # facts: repo.name
branch: main                     # facts: git.branch
head: 4f2a9c1                    # facts: git.head, seven characters
level: decisions                 # facts: level (git-only | logs | decisions)
previous: 2026-10-14_opus-5-5_billing-retry-in-review.md   # facts: previous_status, filename only, or none
waiting: 2                       # total items for Waiting on You, before the cap
pending-decisions: 3             # total pending decision items, before the cap
next: 3                          # total items for What's Next, before the cap
---
```

The three counts let a later reader, such as a page listing every project's snapshot, read the file without parsing its prose.

## Body

### Title and "As of" paragraph [R3]

A level-1 title, `# Status: <repo>, YYYY-MM-DD`, then one paragraph opening with `**As of YYYY-MM-DD.**`. It states the commit, the branch, the upstream comparison and whether a fetch ran, the tree state, the newest tag, and the open pull requests. It then names the sources read, and gives the confidence key: high means checked against a file or a command's output, medium means a reasonable reading of one, low means judgment.

### Sections, exactly these, in this order [R3]

| Section | Contents |
|---|---|
| `## The Answer` | Three to five sentences: where the project is, and the one thing that matters most next. A reader who stops here has a usable answer. |
| `## Changed Since Last Status` | Names the previous snapshot's filename, then lists what shipped, opened, was decided, and is still waiting, compared with it [R7]. With no previous snapshot, says "No previous status snapshot exists" and summarises the window the facts used instead. |
| `## Waiting on You` | Ranked [R4, R5]. What only the maintainer can do: answers, actions, approvals. Items from the newest log's Waiting on You list belong here unless the logs show them done. |
| `## What's Next` | Ranked [R4, R5]. Work an agent can do, in order, including what becomes possible once a waiting item is answered. |
| `## Pending Decisions` | Ranked [R4, R5, R6]. Every pending decision item, with its id, a handle, its home as a backticked path, its age, and its recommendation when the home gives one. |
| `## Recent Decisions` | Bulleted [R6]. Items answered inside the facts' decisions window: what was chosen, by whom, and where it is recorded. "None in the window." when the facts list none. |
| `## Accomplished` | Bulleted. What shipped inside the window: tags, merged pull requests, finished specs. Facts first, then what the logs add. |
| `## Where the Project Is` | One line per stream of work or effort, with its state. At level `git-only`, from the README and the commit history. |
| `## What I Don't Know` | Every gap the facts list, by its `source` name [R8], plus anything the agent could not establish. Unrecognised statuses are reported here as a count, not ranked as pending. |

### Ranked items [R4, R5]

A ranked item is one numbered line. It opens with a bold handle, gives the facts, and ends with a `Why here:` clause saying why it ranks above the next item:

```markdown
1. **Answer EX-02 D1 (column order).** PR #88 cannot be finished until it is set. Why here: it is the only item blocking work in flight.
```

Rank by these, in order: what blocks work in flight; what blocks a release; the oldest; the cheapest to settle. Show at most ten numbered items. When a count exceeds ten, follow the list with one unnumbered line: "N more; the full list is in `<where>`", for example the output of `/plab-resolve-open-items --backlog`. The frontmatter count is the total; the checker requires the number of numbered items to equal the smaller of that count and ten.

### Decision items [R6]

Every item under Pending Decisions and Recent Decisions names its home document as a backticked path, such as `docs/specs/EX-02_csv-export/spec.md`, and pairs its id with a short handle: "EX-02 D1 (column order)", never "D1" alone.

## What the snapshot never does

- It never answers or edits a decision. It reports them, and offers `/plab-resolve-open-items`.
- It never states a repository fact from recall. A fact the script did not report is either read from a source the facts named, or listed under What I Don't Know.
- It is never edited after the run. The next snapshot records what changed.
