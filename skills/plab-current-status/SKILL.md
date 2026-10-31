---
name: plab-current-status
description: "Write a dated status snapshot of the current repository to _local/_status/YYYY-MM-DD_<model>_<byline>.md: the answer first, what changed since the last snapshot, what waits on the maintainer, what is next, pending and recent decisions ranked with reasons, what was accomplished, and what is unknown. Use when the maintainer wants a project status report, a status snapshot, or a prioritized next-steps and decisions document. Facts come from one script call; works in any git repository. Explicit invocation only: run /plab-current-status; it does not fire on its own."
argument-hint: "[<byline>] [--no-fetch]"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.0.1"
  updated: 2026-10-30
---

# Current Status

Write one dated, ranked snapshot of where this repository stands, so the maintainer can stop reading at any paragraph and still know what to do next. Each run writes a new file and never edits an old one; the next snapshot says what changed since this one.

## Input

| Input | Default | Notes |
|-------|---------|-------|
| `<byline>` | Chosen by the agent | Two to six lowercase kebab-case words summarising the snapshot, such as `export-blocked-on-two-answers` |
| `--no-fetch` | Fetch | Skip `git fetch`; the remote comparison is then as of the last fetch, and that becomes a named gap |

## Output

One file: `_local/_status/YYYY-MM-DD_<model>_<byline>.md` in the repository root. `<model>` is the running model's id without its vendor prefix, so `claude-opus-5-5` becomes `opus-5-5`. Nothing else is written: no session log, no spec, no tracked file.

## Workflow

### 1. Gather the facts

Run, with a facts path in a temp folder outside the repository:

```bash
python <this skill's base directory>/scripts/derive-status-facts.py --repo <project root> --json --out <temp folder>/status-facts.json
```

Add `--no-fetch` when the maintainer passed it. On exit 2, report the named cause and stop; never write a snapshot from recall. Every fact about repository state in the snapshot comes from this output: branch, head, tree, upstream, tag, commits, pull requests, logs, previous snapshot, decisions and gaps.

### 2. Check where the file will land

If `status_dir_ignored` is false, ask before writing, and offer to add `_local/` to `.gitignore`. A snapshot carries machine paths and candid narrative and should not be committed.

### 3. Read what the facts name, and nothing else

- The previous snapshot (`previous_status.path`), if one exists, for Changed Since Last Status.
- Every log in `session_logs.since_previous`. With no previous snapshot, the newest log only.
- The "Open Questions / Decisions" section of each document that is the `home` of an item you will show under Pending Decisions or Recent Decisions.
- At level `git-only`, the root `README.md`, for Where the Project Is.

Do not search the repository, list folders, or read memory files for more. A source the facts did not name is out of scope, and a gap stays a gap.

### 4. Rank

Follow `references/status-format.md`. Waiting on You holds what only the maintainer can do: answers, actions and approvals. What's Next holds the work an agent can do once unblocked. Pending Decisions holds every pending decision item, the most blocking first, then the oldest. Each ranked item says, in a `Why here:` clause, why it sits above the next one. Show at most ten per section and state how many more exist and where they live.

### 5. Write the snapshot

Choose the byline, or use the maintainer's. Never overwrite an existing file; if the name is taken, choose another byline. Write the file in the format of `references/status-format.md`: the frontmatter, the "As of" paragraph, and the nine sections in order. Every decision item pairs its id with a short handle and names its home as a backticked path. Every gap in the facts appears under What I Don't Know. Mark confidence on load-bearing claims.

### 6. Check it

```bash
python <this skill's base directory>/scripts/status-check.py <snapshot> --facts <temp folder>/status-facts.json
```

Exit 0 means the snapshot satisfies every rule. Exit 1 names each failure: fix the snapshot and run the check again. Exit 2 means the checker could not prove itself: report the snapshot as unverified, never as checked.

### 7. Reply

Give the snapshot's path, its The Answer section, and the checker's result line. Offer `/plab-resolve-open-items` when decisions are pending; do not start it.

## Constraints

- **Facts, not recall.** A fact about repository state that the facts script did not report is either read from a named source or listed under What I Don't Know.
- **One write.** The snapshot is the only file written. Decisions are reported, never answered or edited; that is `/plab-resolve-open-items`.
- **Ids carry handles.** Never write a bare reference id such as `D1` or `PR #88`; pair it with a short handle on first use.
- **Silence is not clean.** A source that could not be read is a named gap, never omitted.

## References

| File | Load when |
|------|-----------|
| `references/status-format.md` | Steps 4 and 5 |
