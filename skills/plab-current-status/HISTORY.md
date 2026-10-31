# History - plab-current-status

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.1 | 2026-10-30 | unreleased | fixed | Codex now honors manual-only too: `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads in place of `disable-model-invocation`. |
| 1.0.0 | 2026-10-28 | v0.10.0 | added | First version, specified by CS-01 (current status skill). Writes a dated, ranked status snapshot of any git repository to `_local/_status/YYYY-MM-DD_<model>_<byline>.md`, from one facts-script call, and checks it with a self-testing checker. Manual invocation only. Built on four working-default decisions, D1 to D4 in the CS-01 spec, all still `Open` pending the maintainer's ratification. |

## 1.0.1 - 2026-10-30

**Fixed: manual-only in Codex.** Codex ignored the skill's manual-only flag. `disable-model-invocation: true` is a Claude Code field, so in Codex the skill sat in the model's skill list and could fire on its own. The 2026-08-29 audit found this for every manual-only skill here. The new `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads instead: it hides the skill from the model and keeps it callable by name. `scripts/codex-invocation-check.py` fails CI when a skill carries either flag without the other.

## 1.0.0 - 2026-10-28

**Added: the skill.** The maintainer had written this document by hand at least twice, on 2026-10-05 and 2026-10-25, and asked on 2026-10-28 for a skill that writes it, standalone and usable in any repository.

- **`scripts/derive-status-facts.py`** gathers branch, head, tree, upstream after `git fetch --no-prune origin --tags`, tag, commits, pull requests through `gh`, session logs, the previous snapshot and the decisions sweep in one call. It reports a level (`git-only`, `logs`, `decisions`) and names every missing source as a gap. Tests: `test-derive-status-facts.py`, 31 checks over eight fixture repositories. Canary: with the level forced to `git-only`, the two level checks fail by name.
- **`scripts/status-check.py`** enforces eight rules on a written snapshot. Every run first proves each rule fails on a mutation of the committed sample, so it exits 2 rather than reporting clean when a rule has gone blind. Canary: disabling R1, R4, R6 or R8 makes the self-test exit 2 and name that rule.
- **The decisions sweep is `plab-resolve-open-items`'s `gather-backlog.py`,** called by its plugin path with the new `--answered-since` argument from that skill's 1.2.0, rather than a second parser (CS-01's D1, where the decisions sweep lives).
- **Manual-only** (`disable-model-invocation: true`), because `plab-continue-session` and `plab-resolve-open-items` both answer status questions directly, and a status skill that fired on "where are we" would break that contract.
