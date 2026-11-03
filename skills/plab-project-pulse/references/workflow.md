# Agent stages

The agents a `--week` run launches, their models, and the prompt each receives. `--quick` launches none. Launch every agent with the Agent tool (or the harness's equivalent) and an explicit model.

## Routing

| Stage | Agents | Model | Effort, where the harness takes one | Escalation |
|---|---|---|---|---|
| Log readers | 0 to 2 | sonnet | medium | Missing records re-run once on opus |
| Heavy scout | 0 to 1 | sonnet | medium | Missing repositories re-run once on opus |
| Light scouts | 0 to 3 | haiku | low | Missing repositories re-run once on sonnet |
| Readiness judge | 0 to 1 | sonnet | high | Missing candidates re-run once on opus |

At most ten agents per run, including escalations and the readiness judge. The heavy scout takes the `heavy_rule.top_by_commits` repositories to scout with the most focus-week commits (default six); light scouts take the rest in groups of at most eight. Record every agent in `curation.json`'s `agents` list.

## The rules every agent receives

Paste this block, unchanged, at the top of every agent prompt.

```text
RULES FOR THIS TASK
1. CREDENTIAL FILES ARE OFF LIMITS. Never open, Read, cat, head, grep, search or filter these files in any way: ~/.codex/config.toml, ~/.codex/auth.json, ~/.npmrc, ~/.claude/.credentials.json, any .env file, any file whose name contains "secret" or "token", and every file listed under credential_files in the owner's settings.
2. Never run a command that changes a repository: no git fetch, pull, checkout, commit, stash, reset or branch change. Reading files and running git log or git status is fine.
3. Use only the repositories and files this prompt names.
4. Every next step, waiting item, decision and risk you return carries the path it came from, relative to the repository root. An item without a source is not returned.
5. Git facts in this prompt outrank documents, and documents outrank session logs. When a document or log contradicts a git fact, return a conflict quoting both instead of choosing.
6. Write plain sentences under 25 words. No em-dashes or en-dashes.
```

## Log readers

**Input:** the session-log paths from `pulse-facts.json`'s `logs`, at most 20 per reader.

**Prompt:** the rules block, then:

```text
Read each session log in this list and return one JSON object per log, one per line, with exactly the fields of PP-01 contract C3 as listed in references/pulse-schema.md under digest.jsonl. Empty lists are fine. Return exactly one object per log you were given, and nothing else. Do not quote passwords, tokens, keys or personal details that appear in a log.
LOGS:
<paths>
```

## Scouts

**Input:** for each assigned repository, its `repo`, `path`, its C2 sweep record from `pulse-facts.json`, and its digest records for the window when there are any.

**Prompt:** the rules block, then:

```text
For each repository below, read its status documents: README.md, AGENTS.md or CLAUDE.md, any ROADMAP, TODO, STATUS or OPEN file at the root, the newest file under docs/internal/release-plans/ or docs/plans/ when present, and the newest session log under _local/_session-logs/. Read at most eight files per repository. Return a JSON list with one object per repository, in the scouts.json shape of references/pulse-schema.md: repo, scouted_by, summary (one or two sentences), whats_next, waiting_on_you (with since when the source states a date), pending_decisions (id, handle, home), risks, conflicts. Return one object for every repository you were given, even when you found nothing; then summary says what you could not find.
REPOSITORIES:
<repo, path, sweep record, digest records>
```

**Check:** the returned `repo` names equal the assigned names. Missing ones re-run once on the next tier, with the prompt saying which were missing and why that matters. Anything still missing goes into `curation.json`'s agents row as `returned` below `assigned`, and `build-pulse.py` records the gap.

## Readiness judge

Runs once per `--week` run, after `build-pulse.py` and before `render.py`, because it reads `pulse.json` (PP-01 D2). `--quick` launches no judge and writes no `readiness.json`.

**The seven criteria.** A work item is ready for an hours-long unattended run that ends in a reviewable pull request when all seven hold. They are the criteria of the owner's hand-run rankings of 2026-10-09 and 2026-10-28.

| Key | Criterion | Scored by |
|---|---|---|
| `github_pr_flow` | A GitHub remote and a pull-request flow | `readiness.py`, from the sweep's remote |
| `tests_pass` | A test command, with evidence that it passes | the judge |
| `spec_with_acs` | A spec with acceptance criteria for this work item | the judge |
| `agent_instructions` | Agent instructions: `AGENTS.md` or `CLAUDE.md` at the root | `readiness.py`, from the file system |
| `checkpointed_stages` | Work that splits into stages, each ending in a commit | the judge |
| `safe_tests` | Tests with no destructive side effects | the judge |
| `clean_branch` | A clean branch: no modified and no staged file | `readiness.py`, from the sweep |

A level is `high` at seven met, `medium` at five or six, and `low` below five.

**Input:** `readiness-candidates.json` from `readiness.py candidates`: at most eight active repositories, each with its path, its What's Next items, and the three criteria the script has scored.

**Prompt:** the rules block, then:

```text
For each repository below, choose the one work item from its list that best suits an hours-long unattended run ending in a reviewable pull request. Score that item against four criteria. Read at most four files per repository: the README or AGENTS.md for the test command, the CI workflow, the spec or plan the item cites, and the newest session log under _local/_session-logs/. Return one JSON object: {"results": [...]}, one entry per repository, each with repo, work_item {text, source}, and criteria holding exactly these four keys, each {"met": true or false, "evidence": one sentence naming the file it came from}:
tests_pass: a test command exists, and a file shows it passing.
spec_with_acs: a spec with numbered acceptance criteria covers this work item.
checkpointed_stages: the work splits into stages that can each end in a commit.
safe_tests: running the tests writes nothing outside the repository or a temporary folder, and touches no shared state.
Do not score the other three criteria; a script has. Return an entry for every repository, even when no item qualifies.
REPOSITORIES:
<readiness-candidates.json>
```

**Check:** the main loop writes the return to `readiness-judge.json` with an `agent` record naming the model, then runs `readiness.py build`. Exit 1 names each candidate with no usable judgement; re-run the judge once on opus for those, merge the returns, and build again. A candidate still unjudged stays in `readiness.json`'s `gaps`, and `coverage.md` names it under Agents.
