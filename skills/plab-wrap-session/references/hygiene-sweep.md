# Hygiene Sweep

The checks the wrap runs before it writes the log, and the protocol for resolving what they find after it has. Deep and final modes run all five checks; quick and blocked modes run only check 2 and note the skips in the log.

Detection is read-only. The four auto actions below are the only changes made without asking; every other action waits for the maintainer to approve its number.

As of `plab-wrap-session` 1.8.0 (W-02, derived log facts), each check's detection is a field in the single `derive-log-facts.py` invocation Evidence Gathering already runs (`--fetch` in deep and final modes); the wrap reads that field rather than running the commands below by hand. The commands stay documented here as the definition each field is a direct port of, and as what to run by hand if the script is ever unavailable.

## Why this exists

A wrap that only documents the session can leave the repo in a silently dangerous state: month-old uncommitted work, an unpulled remote that another checkout has been releasing from, docs describing versions that no longer exist. The motivating incident: this library's v1.6.0 was released 2026-07-25 from a second checkout while the primary machine sat unpulled with the same work uncommitted, and nothing surfaced the divergence until the next release attempt failed on a duplicate tag two weeks later. A `git fetch` at wrap time would have caught it the same day.

## Check 1: Remote reconciliation

`derive-log-facts.py`'s `check1-remote` field, derived from:

```bash
git fetch origin --tags
git status -sb                     # ahead/behind vs upstream
git log --oneline HEAD..@{u}       # commits the remote has that local lacks
git log --oneline @{u}..HEAD       # unpushed local commits
git ls-remote --heads origin       # branches that exist remotely
git tag -l --sort=v:refname | tail -5   # newest local tags by version; a plain -l puts v0.10 before v0.7
```

Flag: behind-remote (someone else worked), unpushed commits, remote branches with no local counterpart, tags that appeared without a local release.

## Check 2: Working-tree and worktree state

`derive-log-facts.py`'s `check2-worktree` field, derived from:

```bash
git status --short                 # dirty and untracked files
git stash list
git worktree list
```

Flag: uncommitted changes older than this session (they belong to somebody; find out whom before they rot), untracked files that look like work products, stashes nobody remembers, worktrees for branches already merged.

## Check 3: Release and repo hygiene

The first two bullets are `derive-log-facts.py`'s `check3-release` field. The third has no script equivalent: which scripts a repository has is specific to it, and their output is a finding to read, not a fact to paste, so it stays a separate agent step.

- CHANGELOG has content above the last released version heading: is a release pending or overdue?
- Version fields (manifests, frontmatter) vs the latest tag: consistent?
- If the repo has its own validation scripts or linters (this library: `scripts/*.sh`, `scripts/*.py`), run them and report results. Never fix failures silently; a red check is a finding.

## Check 4: Documentation drift

Compare what the session changed against what documents it, in both directions.

Stale docs, caught by reading:

- Skill or component version bumped but its usage doc still shows the old version
- Feature behavior changed but README or reference docs describe the old behavior
- Work completed with no CHANGELOG entry where the repo maintains one

Unbumped versions, caught by this recipe. For each skill directory with content
changed since the last tag, its `metadata.version` should have moved; if it did
not, or if `HISTORY.md` has no entry for the version currently shipping, that is
a finding. `derive-log-facts.py`'s `check4-doc-drift` field is a direct port of
the recipe below. The last tag is the nearest release tag: `--match` skips the
merge check's `pre-merge/*` backup tags and a floating major tag such as `v1`,
because a backup sits nearer HEAD than the release and a diff since it misses
skills changed since the release without a version bump.

```bash
LAST_TAG=$(git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*' 2>/dev/null)
if [ -z "$LAST_TAG" ]; then
  echo "No release tags yet; version-drift comparison has nothing to compare against, skipped."
else
  for dir in skills/*/; do
    skill=$(basename "$dir")
    skill_file="${dir}SKILL.md"
    history_file="${dir}HISTORY.md"
    git cat-file -e "$LAST_TAG:$skill_file" 2>/dev/null || continue    # new since last tag, skip
    git diff --quiet "$LAST_TAG" HEAD -- "$dir" && continue            # unchanged, skip
    head_version=$(grep -m1 'version:' "$skill_file" | sed -E 's/.*"([^"]+)".*/\1/')
    tag_version=$(git show "$LAST_TAG:$skill_file" | grep -m1 'version:' | sed -E 's/.*"([^"]+)".*/\1/')
    [ "$head_version" = "$tag_version" ] && echo "FINDING: $skill changed since $LAST_TAG but metadata.version is still $head_version"
    grep -qE "^\| $head_version \|" "$history_file" 2>/dev/null || echo "FINDING: $skill/HISTORY.md has no entry for version $head_version"
  done
fi
```

Flag: content changed with the version identical to the last tag; a skill's
`HISTORY.md` missing an entry for the version currently in its `metadata.version`.
Skip silently, not as a finding: a skill with no diff since the last tag, and a
skill that did not exist at the last tag.

## Check 5: Session-log store

`derive-log-facts.py`'s `check5-log-store` field, itself produced by calling:

```bash
python scripts/organize-logs.py _local/_session-logs --json
```

The script path resolves against this skill's own directory, wherever the plugin is installed; the store argument is relative to the project being wrapped.

The script is dry run by default, so this check is read-only exactly like the other four. The sweep's detection phase and the script's default mode are the same code path, which is why the check cannot drift from the operation it proposes.

Flag: a non-empty `moves` list. When `collisions` is empty, re-run with `--apply` as an auto action (see Auto actions below) and record it:

> auto: log-store. `organize-logs.py _local/_session-logs --apply` -> 14 logs from 3 closed months (2026-05, 2026-06, 2026-07) filed into month folders.

The standalone `--organize` entry point still shows its plan and asks first, because the maintainer invoked it to see that plan.

Report nothing when `moves` is empty. A store holding only current and previous-month logs is a normal store, not a finding, and a wrap that comments on it every time trains the maintainer to skim the sweep.

A non-empty `collisions` list is different: it means a target filename already exists in its month folder, which should not happen and which the script refuses to resolve. That is an anomaly to name, not a routine proposal, so it goes in Waiting on You rather than the proposal queue.

## Resolution protocol

The log is written first, and the proposals are asked after it, in one message that opens with the Closing Summary (`SKILL.md`, Wrap Order and Closing Summary). Each finding gets one concrete, numbered proposal:

> **H1** Unpushed: 2 commits on main. Push to origin/main.
> **H2** Doc drift: docs/skills/x/README.md says 1.1.0, SKILL.md says 1.2.0. Update the version line.
>
> Answer in one line, such as `H1 y, H2 n`, or `ok` to approve them all.

In the log, each proposal is one line in the Hygiene Sweep section, written before the question is asked and amended after the answer:

```markdown
- **H1** Push 2 unpushed commits on `main` to `origin/main`. Status: unanswered
```

The status word is `unanswered` when written, and becomes `done` or `failed` with the result, or `declined`. A number the answer leaves out stays `unanswered`.

Rules:

1. One proposal per finding, each independently answerable by its number. All of them are presented in one message, never as one "fix everything?" question.
2. Execute exactly what was approved, nothing adjacent.
3. Silence approves nothing. Only `ok`, `all y` or an equivalent explicit phrase approves every proposal.
4. Declined and unanswered proposals stay in the log's Hygiene Sweep section and in the continuation prompt as pending actions.
5. Findings that need the maintainer rather than the agent (a divergence to rule on, a release decision) go in the Waiting on You section with file links, not in the proposal queue.
6. Time-box the sweep: if the repo is enormous or offline, run what is cheap, note what was skipped, and wrap anyway. The sweep serves the wrap, not the reverse.

## Auto actions

Four actions run without asking, before the log is written, in the order of the table. Each one changes only this checkout, can be undone from what the log records, and is refused by git or the script itself when its precondition does not hold, so the check is a command's, not the agent's.

| Rule | Command | When | Why it is safe |
|---|---|---|---|
| `fetch-prune` | `git fetch --prune origin` | Deep and final modes only, when `git remote prune origin --dry-run` lists at least one stale ref. Read each listed ref's SHA with `git rev-parse` first | It deletes only remote-tracking refs whose branch is gone from origin; no local branch and no remote branch changes. The record names each ref and its SHA, so `git update-ref refs/remotes/origin/<branch> <sha>` restores it. It runs first, because `git branch -vv` reads an upstream as `gone` only after its tracking ref is pruned |
| `merged-branch` | `git branch -d <branch>` | `git branch -vv` marks the local branch's upstream `gone`. The facts script does not report this, so `git branch -vv` is the one read the agent adds | `-d` refuses a branch that is not merged. The output names the commit, `(was 1a2b3c4)`, so `git branch <branch> 1a2b3c4` restores it |
| `worktree-prune` | `git worktree prune` | `git worktree list` marks an entry `prunable` | It removes only git's records of worktree folders that no longer exist |
| `log-store` | `organize-logs.py <store> --apply` | Check 5 reports moves and no collisions | It moves files and never deletes, and never files the current or previous month |

Record each one in the Hygiene Sweep section, before any proposal:

```markdown
- auto: fetch-prune. `git fetch --prune origin` -> - [deleted] (none) -> origin/feat/x. It pointed at 1a2b3c4.
- auto: merged-branch. `git branch -d feat/x` -> Deleted branch feat/x (was 1a2b3c4).
```

**Why the pruning fetch is an auto action.** A pruning fetch deleted a remote-tracking ref without confirmation on 2026-09-25, which is why `derive-log-facts.py` fetches with `--no-prune` (W-02, derived log facts, decision D4). The fault that day was a deletion nobody saw and nothing recorded. The maintainer made the pruning fetch an auto action on 2026-11-03 (W-05, wrap hygiene order, decision D2), so it now runs only as a recorded step whose record carries every pruned ref's SHA. The facts script's own fetch stays `--no-prune`, so check 1 reports the remote as it was before the pruning fetch.

Everything else asks. Pushes, remote deletes, commits, tags, marketplace repins, `git branch -D`, stash drops, file deletions and content edits all ask.
