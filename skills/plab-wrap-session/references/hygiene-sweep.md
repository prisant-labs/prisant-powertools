# Pre-Wrap Hygiene Sweep

The checks the wrap runs before writing the log, and the protocol for acting on what they find. Deep and final modes run all five checks; quick and blocked modes run only check 2 and note the skips in the log.

Everything here is read-only until the user confirms an action. The sweep proposes; the user disposes.

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
git tag -l | tail -5               # local tags vs expectations after --tags fetch
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
the recipe below:

```bash
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null)
if [ -z "$LAST_TAG" ]; then
  echo "No tags yet; version-drift comparison has nothing to compare against, skipped."
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

Flag: a non-empty `moves` list. Report the count and the month folders, then propose:

> Log store: 14 logs from 3 closed months (2026-05, 2026-06, 2026-07) are unfiled.
> File them into month folders? (y/n)

On approval, re-run with `--apply` and report the result. Nothing else in the sweep changes.

Report nothing when `moves` is empty. A store holding only current and previous-month logs is a normal store, not a finding, and a wrap that comments on it every time trains the maintainer to skim the sweep.

A non-empty `collisions` list is different: it means a target filename already exists in its month folder, which should not happen and which the script refuses to resolve. That is an anomaly to name, not a routine proposal, so it goes in Waiting on You rather than the proposal queue.

## Resolution protocol

For each finding, present one concrete, singular proposal:

> Unpushed: 2 commits on main. Push to origin/main now? (y/n)
> Doc drift: docs/skills/x/README.md says 1.1.0, SKILL.md says 1.2.0. Update the version line? (y/n)

Rules:

1. One proposal per finding, each independently confirmable. No batch "fix everything?" prompts.
2. Execute exactly what was approved, nothing adjacent.
3. Declined and unanswered proposals are recorded in the log's Hygiene Sweep section and repeated in the continuation prompt as pending actions.
4. Findings that need the maintainer rather than the agent (a divergence to rule on, a release decision) go in the Waiting on You section with file links, not in the proposal queue.
5. Time-box the sweep: if the repo is enormous or offline, run what is cheap, note what was skipped, and wrap anyway. The sweep serves the wrap, not the reverse.
