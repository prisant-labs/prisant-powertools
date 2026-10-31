# History - plab-project-pulse

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.0 | 2026-10-30 | unreleased | added | First version, specified by PP-01 (project pulse skill). Rolls every repository under the configured roots into one private weekly pulse, reusing fresh `plab-current-status` snapshots. Manual invocation only. Built on five working-default decisions, D1 to D5 in the PP-01 spec, all still `Open` pending the maintainer's ratification. |

## 1.0.0 - 2026-10-30

**Added: the skill.** The maintainer's weekly project review was run by hand four times in October 2026 and broke on dates, paths, a junction and a timed-out search. The maintainer asked on 2026-10-30 for it as a skill clearly distinct from `plab-current-status`.

- **`scripts/derive-pulse-facts.py`** runs discovery, the read-only sweep, optional `gh` enrichment, activity classification, carry-forward, snapshot reading, waiting-item ages and the unprotected-work check in one call.
- **`scripts/build-pulse.py`** assembles `pulse.json` and writes the state file only after validation; **`scripts/render.py`** writes a self-contained dashboard.
- **`scripts/pulse-check.py`** enforces the schema, the coverage headings and the dashboard card count; its self-test proves each of its ten rules fails on a mutation of the committed sample.
- **Manual-only** (`disable-model-invocation: true`), because "what's next?" is a status question two other skills answer directly.
