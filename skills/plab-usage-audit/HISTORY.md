# History - plab-usage-audit

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.0 | 2026-10-30 | unreleased | added | First version, specified by UA-01 (usage audit skill). Runs the owner's weekly audit of their own Claude Code usage and writes a scrubbed, verified bundle. Manual invocation only. Built on six working-default decisions, D1 to D6 in the UA-01 spec, all still `Open` pending the maintainer's ratification. |

## 1.0.0 - 2026-10-30

**Added: the skill.** Ten weekly audits between August and October 2026 were run by hand, reusing only the collector and spending about an hour of prompt edits each week. The maintainer asked on 2026-10-30 for the audit as a skill that expands substantially on `/usage`, `/insights` and the `session-report` plugin.

- **`scripts/collect.py`** measures the transcripts with fixture-proven accounting rules, reports responses by the model that actually ran, and flags a model family whose newest model never appears.
- **`scripts/derive-audit-facts.py`** gathers the reconciliation, workflow totals, versions, settings drift and credential presence in one call, reading credential files for key names and dates only.
- **`scripts/bundle-check.py`** enforces nine rules on the bundle, including a mandatory verification section and the rule that a claimed approval names its record; its self-test proves each rule fails on a mutation of the committed sample.
- **Every agent names a model and opens with a shared rules block** that forbids opening a credential file; `scripts/test-workflow-reference.py` proves it.
- **Manual-only** (`disable-model-invocation: true`), because a run launches up to nine agents and writes ledger rows.

**Also: manual-only in Codex.** `disable-model-invocation: true` is a Claude Code field that Codex ignores, so without more the skill would sit in the Codex model's skill list and could fire on its own. The 2026-08-29 audit found that gap in every manual-only skill that existed then. This skill's `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads instead: it hides the skill from the model and keeps it callable by name. `scripts/codex-invocation-check.py` fails CI when a skill carries either flag without the other.

