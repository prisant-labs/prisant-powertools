---
name: plab-ship
description: "Ship finished branches: document them in depth across human, technical and agentic docs, verify them, screen them, merge what passes the merge check, clean up, and report what changed, with an optional release whose version the model decides. Writes one run record to _local/_shipped/. Explicit invocation only: run /plab-ship; it does not fire on its own."
argument-hint: "[<branch|PR> ...] [--release] [--no-fetch]"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.0.0"
  updated: 2026-11-06
---

# Ship

Carry finished branches over the line in one pass: documented, verified, screened, merged where the merge check allows, cleaned up and reported. Make one pass and stop. New work needs a new instruction. Stay in this repository.

## Input

| Input | Default | Notes |
|-------|---------|-------|
| `<branch\|PR> ...` | None | The branches to ship. With none named, list the candidates from the facts and ask which |
| `--release` | Off | The maintainer's approval, for this run only, to publish a new version of what reaches the main branch. It takes no number and no size: the model decides the version |
| `--no-fetch` | Fetch | Skip `git fetch`; the remote comparison then becomes a named gap |

Merging needs no flag. Whether a merge may happen without asking is decided by the maintainer's merge rule and its check, not by this skill.

## Output

- Merged branches, as the merge check permits, and a new version when `--release` was passed.
- One run record, `_local/_shipped/YYYY-MM-DD_<byline>.md`, in the format of `references/record-format.md`.
- A closing report, whose documents list follows step 9.

## Workflow

### 1. Gather the facts

Run, with a facts path in a temp folder outside the repository:

```bash
python <this skill's base directory>/scripts/derive-ship-facts.py --repo <project root> --json --out <temp folder>/ship-facts.json
```

Add `--no-fetch` when the maintainer passed it. On exit 2, report the named cause and stop. Every gap in the facts goes under Unverified in the record.

Read the latest version from `release.latest_version_tag` and never from `git describe`, which returns backup tags.

### 2. Open the record

If `record_dir_ignored` is false, ask before writing, and offer to add `_local/` to `.gitignore`. Create the record now, before any merge, with every section present and `release` set from the flag. Append each merge as it happens. A list held only in the conversation can be lost at compaction, and the record is what a later review of the merge rule reads.

Take the branch order from their dependencies: a branch built on another ships after it.

### 3. Document each branch, on the branch

Follow `references/documentation-standard.md`. This step comes before verification so that the verified commit is the one that merges.

- Fill all twelve cells for the branch: each of human, technical and agentic docs, at each of the discover, use, understand and trust depths. A cell records the file updated, the file already correct, or why it does not apply.
- Use the repository's documentation map from `doc_map`. When `doc_map.source` is `detected`, propose a map in the record's Unverified section.
- List every new flag, command, path and skill name on the block's `**New surface:**` line, each in backticks. Each must appear in a human-layer file.
- For a feature or a behaviour change, run the cold reader the standard describes, on Sonnet, and fix the gaps it reports. For a fix that changes no behaviour, record why it did not run.

Commit the documentation to the branch and push it.

### 4. Verify each branch

Run the tests, the build and the repository's own validation scripts, and read the results. Run any script the branch changed against the real checkout, because tests that use fixtures have missed real defects. A failure is reported as a failure, with its output, and the branch stays open.

### 5. Screen each branch

```bash
python <this skill's base directory>/scripts/screen-branch.py --repo <project root> --range <base>..<head>
```

Exit 0 is clean. Exit 1 names each finding by file and pattern: leave the branch open and report it. Exit 2 is not clean, so treat it the same way. Never print a matched value. Report that this is a pattern screen and does not prove a branch holds no secret.

### 6. Decide, and merge

For each branch, wait for its CI to finish, then run the merge check exactly as your solo-repo merge rule specifies. That rule holds the command, so this skill does not repeat it. If no such rule is in your instructions, or the check cannot run, do not merge: report why. A missing check is never a pass.

Merge only when all of these hold:

- The check ends in `VERDICT: merge`. Run it again before each merge, and once more if it reports the clean check as unknown.
- The documents match the change.
- The pull request has no unresolved review thread (`pull_requests[].unresolved_threads`).
- No pending decision blocks it. A decision in `pending_decisions` blocks a branch when its home document is in the branch's diff, or when it names the branch's work.

Use the merge command the check prints, which carries `--match-head-commit`, with the merge method the repository's history shows. Anything else stays open, and the record says why. A verdict that asks the maintainer is reported with the check that asked and what it said.

The one exception: with `--release`, a verdict whose only ask is the `release` check may proceed if your merge rule says `--release` answers it. If your rule does not say that, stop and name the ask.

Append the row to the record's Merged table as soon as the merge lands: branch, pull request, commit, undo point.

### 7. Release, only with `--release`

Without the flag, create no version, tag or release. Write that the release was not approved in the record's Release section, and go to step 8.

With the flag, decide the version yourself by reading what changed since `release.latest_version_tag`. Read the diff and the CHANGELOG, not only the commit prefixes.

| What the changes do to someone already using this repository | Raise |
|---|---|
| Fix behaviour or change documents only | Patch |
| Add something, and existing use still works | Minor |
| Break existing use, such as a renamed command, a removed flag or a changed file format | Major |

- **A repository below 1.0.0:** a breaking change raises the minor number, which is the Semantic Versioning convention. Move to 1.0.0 only if the repository's own documents say its interface is stable.
- **Follow the tag shape** in `release.tag_prefix` and `release.tag_parts`.
- **A version already bumped on a merged branch:** keep it if your reading of the changes agrees. If it disagrees, use your own and say so.
- **A major version does not stop to ask.** The decision is yours, and it carries the reason. State the version and the reason before tagging, and record them under a `**Why:**` line.
- **Stop and ask only when the repository has no version tag at all.** A first release also decides whether the repository versions at all, and the changes cannot answer that.

Then release through the repository's own path:

1. Bump the version files and write the CHANGELOG entry through a pull request if the main branch is protected. Title it `chore(release): release vX.Y.Z`, so that the merge check recognises it as a release. It goes through steps 4 to 6 like any other branch.
2. Create and push the tag. `release.tag_workflows` names any workflow the tag triggers: confirm that each one succeeded.
3. Finish the remaining steps the repository documents, using `release.release_docs` and the repository's agent instructions. Name any step only the maintainer can do. When `release.plugin_repo` is true, merged is not installed: say what still has to happen before the new version loads.

### 8. Clean up

- Re-date or close the entries in `open_item_files` that this work touched, or say the repository has no such file.
- Delete merged branches with `git branch -d`. Use `-D` only after `gh pr view` shows the pull request as merged, which is the normal case after a squash merge.
- Remove a worktree only if it is clean and no live session holds it.
- Confirm the working tree is clean and that `tracked_local_files` is still empty.

### 9. Check the record, and report

```bash
python <this skill's base directory>/scripts/ship-check.py <record> --repo <project root>
```

Exit 0 means the record satisfies every rule, and that its documents list matches the real commits. Exit 1 names each failure: fix the record, or fix the documents through a new branch, and run it again. Exit 2 means the checker could not prove itself: report the record as unverified, never as checked.

Then report, in this order:

1. What merged, each with its undo point.
2. What stayed open, and why.
3. What needs the maintainer's decision.
4. The release: the version and why, or that none was approved.
5. **Documents updated.** One table per merged branch, with a row for each layer and columns for updated, already correct, and does not apply with the reason. Link each file, so it can be opened. Add the cold reader's result on one line.
6. What is unverified, and the checker's result line.

List every merge in the session's final message: the repository, the pull request or branch, and the undo point.

## Constraints

- **The merge check decides, not confidence.** An agent feels sure whether or not a merge is safe, so a feeling never substitutes for `VERDICT: merge`.
- **One pass.** Report and stop. Never start new work this run did not name.
- **The flag covers one run.** `--release` approves this run's release and answers only the `release` check. Failing tests, conflicts, deleted files, outside authors and repositories off the solo list still stop a merge.
- **No version without the flag.** A merge never creates a tag or a release on its own.
- **Facts, not recall.** Repository state comes from the facts script, and the documents list is checked against the real commits.
- **Ids carry handles.** Never write a bare reference id such as `D1` or `PR #88`; pair it with a short handle on first use.
- **This skill never rewrites history.** No force-push, and no edit to the merge rule or its repository list to get a merge through.

## References

| File | Load when |
|------|-----------|
| `references/documentation-standard.md` | Step 3 |
| `references/record-format.md` | Steps 2, 6 and 9 |
