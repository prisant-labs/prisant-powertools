# plab-current-status

**Version:** 1.0.1
**Source:** [`skills/plab-current-status/`](../../../skills/plab-current-status/)

Write a dated status snapshot of the current repository: the answer first, what changed since the last snapshot, what waits on you, what is next, pending and recent decisions ranked with reasons, what was accomplished, and what is still unknown. Manual invocation only.

---

## Getting Started

### Quick Start

```
/plab-current-status
```

The snapshot lands in `_local/_status/YYYY-MM-DD_<model>_<byline>.md` in the repository root, for example `_local/_status/2026-10-28_opus-5-5_export-blocked-on-two-answers.md`. The model is the one that wrote it, so snapshots from different models can be compared later.

### Common Invocations

```
# Let the agent choose the byline
/plab-current-status

# Choose the byline yourself
/plab-current-status release-week-check

# Offline, or when a fetch would hang: compare with the remote as of the last fetch
/plab-current-status --no-fetch
```

### Installation

Ships with the `prisant-powertools` plugin. Nothing to install separately. Because it carries `disable-model-invocation: true`, it is absent from the auto-loaded skill listing and runs only when you type `/plab-current-status`.

---

## When to Use

- You want one document that says where a repository stands and what to do next, ranked, with reasons.
- Several sessions or threads have run since you last looked, and you need them pulled together.
- Before a planning sitting, so the snapshot can feed `/plab-resolve-open-items`.

## When NOT to Use

- **A quick question such as "where are we?"** Ask it. The agent answers from context without writing a file, and this skill does not fire on its own.
- **Resuming a session.** That is `/plab-continue-session`, which replays one session's handoff.
- **Answering decisions.** That is `/plab-resolve-open-items`. A snapshot reports decisions and never edits them.

## How It Works

### 1. One script call gathers the facts

`derive-status-facts.py` reads git (branch, head, tree, upstream after a fetch, tag, commits), GitHub pull requests through `gh`, the session logs, the previous snapshot, and the decisions sweep of `plab-resolve-open-items`, in one call. Facts from a script rather than from the model's memory is the same rule `plab-wrap-session` follows.

### 2. It works in any repository

The facts report a level, and the snapshot degrades with it:

| Level | The repository has | The snapshot draws on |
|---|---|---|
| `git-only` | Git, nothing else | Commits, tags, pull requests and the README |
| `logs` | Session logs in `_local/_session-logs/` | Adds the logs' Waiting on You lists and next actions |
| `decisions` | Specs, plans or release plans with an Open Questions / Decisions section | Adds pending and recently answered decisions |

Every source that is missing, such as no remote, no `gh`, or no logs, is named under What I Don't Know rather than silently left out.

### 3. A window chains the snapshots

Each snapshot covers the time since the previous one. With no previous snapshot, accomplishments run from the latest tag, and recent decisions from fourteen days back.

### 4. A ranked list, not an inventory

Waiting on You, What's Next and Pending Decisions are numbered, each item says why it ranks where it does, and each list shows at most ten items, naming where the rest are.

## Output

A single Markdown file. Its frontmatter carries the date, model, repository, branch, head, level, previous snapshot and three counts, so another tool can read it without parsing prose. The body is an "As of" paragraph and nine sections: The Answer; Changed Since Last Status; Waiting on You; What's Next; Pending Decisions; Recent Decisions; Accomplished; Where the Project Is; What I Don't Know. A worked example is [`skills/plab-current-status/examples/sample-status/`](../../../skills/plab-current-status/examples/sample-status/).

## Its Own Gate

`status-check.py` checks every snapshot the skill writes against eight rules: the location and name, the frontmatter, the sections and their order, a `Why here:` on every ranked item, counts matching the lists, a home path on every decision item, the previous snapshot named, and every gap mentioned. Each run first proves that every rule fails on a mutated copy of the committed sample, so a rule that has gone blind stops the run with exit 2 instead of passing everything. CI runs the self-test on every pull request.

## Hard Constraints

- The snapshot is the only file written. If `_local/_status/` is not gitignored, the skill asks before writing.
- Decisions are reported, never answered or edited.
- A repository fact the script did not report is read from a named source or listed as unknown, never recalled.
- An existing snapshot is never overwritten or edited.

## Tips

- Run it before `/plab-resolve-open-items --backlog`: the snapshot ranks the decisions, and the walk settles them.
- On this machine `~/.gitignore_global` ignores `_local/` in every repository, so the gitignore question rarely comes up here. It will on a machine without that file.
