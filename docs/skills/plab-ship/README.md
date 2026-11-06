# plab-ship

**Version:** 1.0.0
**Source:** [`skills/plab-ship/`](../../../skills/plab-ship/)

Carry finished branches over the line in one pass: documented in depth, verified, screened, merged where your merge check allows, cleaned up and reported. It can also publish a new version, and it decides the version number itself. Manual invocation only.

It is built for this plugin's maintainer, whose private merge rule and merge check it relies on. Anyone else needs their own rule and a check that ends in `VERDICT: merge`, or the skill will not merge.

---

## Getting Started

### Before You Start

You need Python 3, git and `gh`, signed in to GitHub. To merge anything, your agent's instructions must also hold a merge rule and its check, which [Words Used Here](#words-used-here) explains. To confirm that, ask the agent "what does your merge rule say?" before the first run. A good answer names the rule and the exact command that runs the check. Without a rule, the skill still documents and verifies, and then leaves the branch open.

### Quick Start

```
/plab-ship feat/my-branch
```

Replace `feat/my-branch` with your branch, either pushed with a pull request or local only. This edits, commits and pushes documentation on that branch, runs its tests, merges it if the merge check, the documents, the review threads and the pending decisions all allow it, and publishes nothing.

The run is unattended unless it needs you. It asks only when you named no branch, when `_local/` is not gitignored, or when `--release` meets a repository with no version tag.

You get a report naming what merged, what stayed open, and which documents changed. The record of the run lands in `_local/_shipped/YYYY-MM-DD_<byline>.md`, where the byline is a few words the agent chooses, such as `2026-11-05_example-flag-shipped.md`.

### Common Invocations

```
# List the candidate branches and ask which to ship
/plab-ship

# Ship several. The skill works out the order, so a branch built on another ships after it
/plab-ship feat/parser feat/parser-docs

# Ship by pull request number
/plab-ship 71

# Ship, then publish a new version. The model picks the number
/plab-ship feat/my-branch --release

# Offline, or when a fetch would hang
/plab-ship feat/my-branch --no-fetch
```

### Installation

Ships with the `prisant-powertools` plugin. Because it carries `disable-model-invocation: true`, and `policy.allow_implicit_invocation: false` for Codex, it runs only when you type `/plab-ship`.

### Words Used Here

| Word | Meaning |
|---|---|
| Merge rule | Instructions you keep outside this plugin that say when an agent may merge without asking. On this maintainer's machine, the solo-repo merge rule |
| Merge check | The script that rule names, which tests one merge and ends in a verdict. On this maintainer's machine, `merge-check.py`, kept in a private configuration repository |
| `VERDICT: merge`, `VERDICT: ask` | The merge check's two answers. Only the first allows a merge. The second names the check that wants you, which this page calls an ask |
| Undo point | The state of the main branch just before a merge: a backup tag or a commit hash. The report gives one per merge |
| Layer | Who a document is for: human readers, technical maintainers, or agents |
| Pending decision | A question recorded in a spec or plan that is still open. It holds back a branch that depends on the answer |
| Cold reader | A fresh agent on the Sonnet model, which reads only the documents and tries to use them |
| Canary | A deliberate fault used to prove a check can fail. A check that cannot fail proves nothing |

---

## When to Use

- A branch or pull request is finished, and you want it documented, checked and merged without steering each step.
- You want to publish a new version of what just merged.
- You used to paste a long close-out prompt at this point. This skill replaces that prompt.

## When NOT to Use

- **The work is not finished.** The skill makes one pass and does no new feature work.
- **You want to end the session.** That is `/plab-wrap-session`, which writes a session log. Run it after this skill if you are also stopping.
- **You want a release plan or a readiness report.** That is `/plab-release-plan --gate`.
- **You want to review a document with another model.** That is `/plab-ai-review`.
- **A branch contains someone else's work.** The merge check sends outside authors to you, so the skill leaves that branch open.

---

## The `--release` flag

Merging and publishing are separate permissions, and the flag controls only publishing.

| You type | Merges | Publishes a version |
|---|---|---|
| `/plab-ship` | Yes, what passes the merge check | No |
| `/plab-ship --release` | Yes, what passes the merge check | Yes, once, for this run |

You never type a number or a size. The model reads what changed since the last version tag and decides:

| What the changes do to someone already using the repository | The number that rises | From 1.4.2 |
|---|---|---|
| Fix behaviour or change documents only | Patch | 1.4.3 |
| Add something, and existing use still works | Minor | 1.5.0 |
| Break existing use | Major | 2.0.0 |

Below 1.0.0, a breaking change raises the minor number, which is the Semantic Versioning convention, so 0.12.0 becomes 0.13.0. The skill moves to 1.0.0 only if the repository's own documents say its interface is stable.

The skill states the version and its reason before tagging, and it does not stop to ask about a major version. The one case where it asks is a repository with no version tag yet, because a first release also decides whether the repository versions at all.

The flag does not override anything else. Failing tests, merge conflicts, deleted files and outside authors all still stop a merge, and the flag does not carry over to a later run.

### Before `--release` can merge a release pull request

Your merge rule has to allow it, because a merge check that sees a release pull request asks you first. The rule lives in your agent's global instructions: for Claude Code, in `CLAUDE.md` or a file under `.claude/rules/` in your home folder, and for Codex, in `.codex/AGENTS.md` there. Add a sentence like this one to the rule, and to any copy of it for another harness:

> Running `/plab-ship --release` is the maintainer's yes for that run's tag and release. It answers a `release` ask from the merge check and no other check.

Until the rule says this, the skill stops at that ask and names it. That is the safe failure: nothing publishes, and the report tells you why.

---

## How It Works

### 1. One script call gathers the facts

`derive-ship-facts.py` reads the branch, the tree, version tags, commits since the last version, open pull requests with their checks and unresolved review threads, pending decisions, worktrees and the documentation map.

| Option | Use |
|---|---|
| `--repo <root>` | The repository to read |
| `--json` | Print the facts as JSON, the only format |
| `--out <file>` | Write the JSON to a file outside the repository, and print one summary line |
| `--no-fetch` | Skip `git fetch`, which becomes a named gap |
| `--gh <exe>` | Name the GitHub CLI executable, which the tests use to simulate its absence |

### 2. Each branch is documented to a standard

The standard is [`references/documentation-standard.md`](../../../skills/plab-ship/references/documentation-standard.md). It has twelve cells: human, technical and agentic docs, each asked whether a reader can discover the change, use it, understand it, and trust it. Each cell names the file updated, the file already correct, or why the cell does not apply.

For a feature or a behaviour change, a Sonnet subagent then reads only the docs, answers five fixed questions, and follows the quick start. The gaps it reports are fixed before the merge.

### 3. Each branch is verified and screened

The skill runs the tests, the build and the repository's validation scripts, and runs any changed script against the real checkout. Then `screen-branch.py` checks that nothing under `_local/` is tracked and that the branch adds no known credential shape.

| Option | Use |
|---|---|
| `--repo <root>` | The repository to read |
| `--range <base>..<head>` | The branch's commits |

It prints the file and the pattern and never the value. It is a pattern screen, so a clean result does not prove that no secret exists.

### 4. The merge check decides

The skill runs your merge check and merges only on `VERDICT: merge`, when the docs match, no review thread is unresolved, and no pending decision blocks the branch. Anything else stays open, and the report says why.

### 5. It records and reports

Every merge is appended to the run record as it lands, so the list survives a compaction. The closing report ends with a table of the documents updated per layer.

---

## Output

**The run record** is `_local/_shipped/YYYY-MM-DD_<byline>.md`, with sections Merged, Left Open, Needs Your Decision, Documents, Release, Cleanup and Unverified. A worked example is [`skills/plab-ship/examples/sample-run/`](../../../skills/plab-ship/examples/sample-run/).

**The documents list in the closing report** looks like this:

```text
Documents updated

feat/example-flag (PR #71, add the example flag)
| Layer     | Updated                                | Already correct | Does not apply                             |
|-----------|----------------------------------------|-----------------|--------------------------------------------|
| Human     | README.md, CHANGELOG.md, docs/guide.md | -               | Trust: the flag has no failure mode        |
| Technical | docs/internal/spec.md                  | docs/index.md   | Use: build and release commands unchanged  |
| Agentic   | AGENTS.md                              | -               | Understand and Trust: no new rule or check |

Cold reader: ran the quick start; 1 gap found and fixed.
```

---

## Its Own Gate

The skill runs this itself at the end of every run. To run it by hand, from the installed skill's `scripts` folder, use `python ship-check.py <record> --repo <root>`. It checks the record against ten rules, listed in [`references/record-format.md`](../../../skills/plab-ship/references/record-format.md), and `--self-test` proves the rules alone. Three of the rules read the real commits: every file listed as updated must have changed in that merge, every changed document must be listed, and every new flag or skill must appear in a human-facing file. So the documents list cannot overclaim. Each run first proves that every rule fails on a mutated copy of the committed sample, and CI runs that proof on every pull request.

It proves presence, not quality. Only the cold reader tests whether the documents actually work for someone new.

---

## How to Tell It Worked

- The report ends with the checker's line, such as `CLEAN: canary proved, _local/_shipped/2026-11-05_example-flag-shipped.md satisfies every rule.`
- Every merge in the report has an undo point.
- `git status` is clean on the main branch, and the merged branches are gone.
- With `--release`, the tag exists and each workflow it triggered succeeded.

---

## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| The report says nothing merged because no rule or check was available | The agent's instructions hold no merge rule, or the check could not run | Install the rule, or merge by hand. A missing check is never a pass |
| The record's Unverified section names `pull requests` as a gap | `gh` is missing or not signed in, so pull requests and review threads were not read | Install `gh` and run `gh auth login`, then run the skill again |
| A branch stayed open with test output in the report | Its tests, build or validation scripts failed | Fix them on the branch and run the skill again |
| The run stopped partway | A crash, a closed session or a limit | Run it again, naming the branches still open. This is safe, because a merged branch is no longer a candidate and each merge is checked again. The earlier record stays, and the new run writes its own |
| The cold reader reports a gap that cannot be fixed now | The documents do not yet work for a new reader | The gap is fixed before the merge, or the agent records why not under Unverified. Read that section |
| The first step hangs | `git fetch` cannot reach the remote | Run again with `--no-fetch`. The comparison with the remote then becomes a named gap |
| `VERDICT: ask` naming `release` | A release pull request needs your merge rule to accept `--release` | Add the sentence above to your rule |
| `VERDICT: ask` naming another check | That check found something the skill must not decide | Read what it reported. The branch stays open |
| `screen-branch.py` FINDINGS | A file holds a credential shape, or `_local/` is tracked | Inspect the named file. If the match is a false positive, merge it yourself |
| `ship-check.py` R8 | The record and the real commits disagree | Correct the record, or ship the missing document on a new branch |
| `ship-check.py` R9 | A new flag or skill appears in no human-facing file | Document it. This is the gate working |
| `ship-check.py` any other rule | The record's format is wrong. [`references/record-format.md`](../../../skills/plab-ship/references/record-format.md) says what each rule wants | Correct the record, and the agent runs the check again |
| `ship-check.py` exit 2 | The checker could not prove itself, or could not read the record | Treat the record as unverified. The line above the exit names the cause |
| It asks before writing the record | `_local/` is not gitignored | Accept the offer to ignore it. The record carries candid notes that should not ship |

### Undoing a merge

The record's Merged table gives two things for each merge: the commit, and the undo point, which is the main branch just before it. To reverse a merge, create a new branch from the main branch, run `git revert <commit>` there, adding `-m 1` if the commit is a merge commit, and put the revert through a pull request. Use the undo point to compare against, such as `git diff <undo point> main`. Do not rewrite the main branch.

---

## Settings

A map at `.claude/plab-ship.local.md` tells the skill which files belong to which layer. Without one it detects a map and proposes it in the record. The format is in [`references/documentation-standard.md`](../../../skills/plab-ship/references/documentation-standard.md).

## Hard Constraints

- The merge check decides every merge, and a missing check never counts as a pass.
- One pass, then stop.
- No version, tag or release without `--release`.
- A matched secret value is never printed.
- The skill never force-pushes, and never edits the merge rule or its repository list.

## Tips

- Run `/plab-wrap-session` afterwards if you are also ending the session. The two do different jobs.
- The record is what a later review of your merge rule reads, so it is worth keeping.
- Name the branches. With none named the skill asks, which costs a round trip.
