# History - plab-project-pulse

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.1.0 | 2026-11-03 | v0.12.0 | added | `--week` ranks the active repositories' work by readiness for a long autonomous run. `scripts/readiness.py` scores three of seven criteria from the sweep and the file system, one Sonnet judge scores the other four, and `pulse-check.py` rule R11 checks `readiness.json`. The dashboard and readout show the ranking. PP-01 D2. |
| 1.0.1 | 2026-10-31 | v0.11.1 | fixed | `scripts/test-derive-pulse-facts.py` pins its AC-15 fixture files inside the test window. It wrote them at the real time of the run, so from 2026-10-31 on the unprotected-work check failed and the session-log exclusion check passed without testing anything. No change to the skill's behaviour. |
| 1.0.0 | 2026-10-30 | v0.11.0 | added | First version, specified by PP-01 (project pulse skill). Rolls every repository under the configured roots into one private weekly pulse, reusing fresh `plab-current-status` snapshots. Manual invocation only. Built on five working-default decisions, D1 to D5 in the PP-01 spec, all still `Open` pending the maintainer's ratification. |

## 1.1.0 - 2026-11-03

**Added: a readiness ranking in `--week`.** The owner ranked work for long autonomous runs by hand on 2026-10-09 and 2026-10-28, each time with a judge agent. The maintainer chose on 2026-11-01 to build that ranking into the weekly run (PP-01 D2, Option B). A new stage runs after `build-pulse.py`, because it reads `pulse.json`, and before `render.py`, so the dashboard carries it.

- `scripts/readiness.py candidates` picks at most eight active repositories, those with an agent-actionable What's Next item first, and scores three criteria without a model: a GitHub remote, an `AGENTS.md` or `CLAUDE.md` at the root, and a branch with no modified or staged file.
- One Sonnet judge at high effort reads at most four files per candidate and scores the other four: passing tests, a spec with acceptance criteria, checkpointed stages, and tests without destructive side effects. A missing return is re-run once on Opus. The agent cap stays at ten, now counting the judge.
- `scripts/readiness.py build` merges both halves into `readiness.json`, levels each item (`high` at seven met, `medium` at five or six, `low` below), ranks by met count, and exits 1 naming any candidate the judge left unscored.
- `pulse-check.py` rule R11 requires `readiness.json` in a week run and checks its shape, its ranks, its criteria and its levels. Two self-test mutations prove it fails.
- `render.py --readiness` adds a "Ready for a Long Autonomous Run" section; its items are not `repo-card` elements, so R10's count is unchanged. The readout lists the top three.
- The sample pulse gains a hand-authored `readiness.json`, and its dashboard is re-rendered with the new section.

`scripts/test-readiness.py` adds 23 checks, including a canary that disables the level rule and sees a two-met item read `high`. CI runs it.

## 1.0.1 - 2026-10-31

**Fixed: the AC-15 fixture no longer depends on the date the test runs.** The test fixes its window at 2026-10-24 to 2026-10-30, and `derive-pulse-facts.py` counts an unprotected file only when its modification date falls inside the window. The fixture wrote its four files without setting their modification times, so they carried the real time of the run. On 2026-10-30 that was inside the window; from 2026-10-31 on it was after it, and CI failed on every pull request. The same drift made the neighbouring check, that a `_local/_session-logs/` change is never reported, pass without exercising the exclusion. The fixture now pins all four files to 2026-10-26. A canary that drops `_session-logs` from `STATUS_PROTECTED` makes both AC-15 checks fail (28/30); the restored script passes 30/30. The skill's own behaviour is unchanged.

## 1.0.0 - 2026-10-30

**Added: the skill.** The maintainer's weekly project review was run by hand four times in October 2026 and broke on dates, paths, a junction and a timed-out search. The maintainer asked on 2026-10-30 for it as a skill clearly distinct from `plab-current-status`.

- **`scripts/derive-pulse-facts.py`** runs discovery, the read-only sweep, optional `gh` enrichment, activity classification, carry-forward, snapshot reading, waiting-item ages and the unprotected-work check in one call.
- **`scripts/build-pulse.py`** assembles `pulse.json` and writes the state file only after validation; **`scripts/render.py`** writes a self-contained dashboard.
- **`scripts/pulse-check.py`** enforces the schema, the coverage headings and the dashboard card count; its self-test proves each of its ten rules fails on a mutation of the committed sample.
- **Manual-only** (`disable-model-invocation: true`), because "what's next?" is a status question two other skills answer directly.

**Also: manual-only in Codex.** `disable-model-invocation: true` is a Claude Code field that Codex ignores, so without more the skill would sit in the Codex model's skill list and could fire on its own. The 2026-08-29 audit found that gap in every manual-only skill that existed then. This skill's `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads instead: it hides the skill from the model and keeps it callable by name. `scripts/codex-invocation-check.py` fails CI when a skill carries either flag without the other.

