# History - plab-project-pulse

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.1 | 2026-10-31 | unreleased | fixed | `scripts/test-derive-pulse-facts.py` pins its AC-15 fixture files inside the test window. It wrote them at the real time of the run, so from 2026-10-31 on the unprotected-work check failed and the session-log exclusion check passed without testing anything. No change to the skill's behaviour. |
| 1.0.0 | 2026-10-30 | v0.11.0 | added | First version, specified by PP-01 (project pulse skill). Rolls every repository under the configured roots into one private weekly pulse, reusing fresh `plab-current-status` snapshots. Manual invocation only. Built on five working-default decisions, D1 to D5 in the PP-01 spec, all still `Open` pending the maintainer's ratification. |

## 1.0.1 - 2026-10-31

**Fixed: the AC-15 fixture no longer depends on the date the test runs.** The test fixes its window at 2026-10-24 to 2026-10-30, and `derive-pulse-facts.py` counts an unprotected file only when its modification date falls inside the window. The fixture wrote its four files without setting their modification times, so they carried the real time of the run. On 2026-10-30 that was inside the window; from 2026-10-31 on it was after it, and CI failed on every pull request. The same drift made the neighbouring check, that a `_local/_session-logs/` change is never reported, pass without exercising the exclusion. The fixture now pins all four files to 2026-10-26. A canary that drops `_session-logs` from `STATUS_PROTECTED` makes both AC-15 checks fail (28/30); the restored script passes 30/30. The skill's own behaviour is unchanged.

## 1.0.0 - 2026-10-30

**Added: the skill.** The maintainer's weekly project review was run by hand four times in October 2026 and broke on dates, paths, a junction and a timed-out search. The maintainer asked on 2026-10-30 for it as a skill clearly distinct from `plab-current-status`.

- **`scripts/derive-pulse-facts.py`** runs discovery, the read-only sweep, optional `gh` enrichment, activity classification, carry-forward, snapshot reading, waiting-item ages and the unprotected-work check in one call.
- **`scripts/build-pulse.py`** assembles `pulse.json` and writes the state file only after validation; **`scripts/render.py`** writes a self-contained dashboard.
- **`scripts/pulse-check.py`** enforces the schema, the coverage headings and the dashboard card count; its self-test proves each of its ten rules fails on a mutation of the committed sample.
- **Manual-only** (`disable-model-invocation: true`), because "what's next?" is a status question two other skills answer directly.

**Also: manual-only in Codex.** `disable-model-invocation: true` is a Claude Code field that Codex ignores, so without more the skill would sit in the Codex model's skill list and could fire on its own. The 2026-08-29 audit found that gap in every manual-only skill that existed then. This skill's `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads instead: it hides the skill from the model and keeps it callable by name. `scripts/codex-invocation-check.py` fails CI when a skill carries either flag without the other.

