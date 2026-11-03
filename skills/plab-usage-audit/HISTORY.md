# History - plab-usage-audit

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.1.0 | 2026-11-03 | v0.12.0 | changed | Recommendation ids are date-scoped, such as `2026-11-03 R2`, in place of a rotating letter. `bundle-check.py` rule R3 requires the new form and one date per bundle. Older letter ids map to their bundle's date plus the letter. UA-01 D1. |
| 1.0.0 | 2026-10-30 | v0.11.0 | added | First version, specified by UA-01 (usage audit skill). Runs the owner's weekly audit of their own Claude Code usage and writes a scrubbed, verified bundle. Manual invocation only. Built on six working-default decisions, D1 to D6 in the UA-01 spec, all still `Open` pending the maintainer's ratification. |

## 1.1.0 - 2026-11-03

**Changed: recommendation ids carry their audit's date.** An id is now the audit date, a space, `R` and a number, such as `2026-11-03 R2`. Through 1.0.0 each audit took the next letter of a rotating series stored in the state file, so ids repeated once the series wrapped, and an id could not be placed in time without a lookup. The maintainer chose date-scoped ids on 2026-11-01 (UA-01 D1): "D1 b actually makes sense, perhaps the year should also be a part of it." The full date carries the year.

- `scripts/derive-audit-facts.py` no longer computes `next_series_letter`. `--commit-state` drops a `recommendation_series` key that an earlier state file carries, and the settings key of the same name is no longer read.
- `scripts/bundle-check.py` rule R3 accepts only `## <YYYY-MM-DD> R<n> (<handle>): <title>`, reports a heading in the old letter form by name, and reports a bundle whose ids carry more than one date. Two new self-test mutations prove both findings, and each mutant now gets its own folder.
- `references/scorecard.md` says how to refer to an id from before this version: the date of the bundle that raised it plus its letter id, such as `2026-10-09 X3`, so an open ask keeps one id and its asked count across the change.
- The sample bundle uses the new ids, and its previous-audit ids use the mapped form.

Before the change, the self-test reported the converted sample as failing R3 and two `test-derive-audit-facts.py` checks failed. After it, the self-test passes with 11 mutations and the suite passes 55 of 55. Run against the real 2026-10-30 bundle, R3 names each of its letter ids.

## 1.0.0 - 2026-10-30

**Added: the skill.** Ten weekly audits between August and October 2026 were run by hand, reusing only the collector and spending about an hour of prompt edits each week. The maintainer asked on 2026-10-30 for the audit as a skill that expands substantially on `/usage`, `/insights` and the `session-report` plugin.

- **`scripts/collect.py`** measures the transcripts with fixture-proven accounting rules, reports responses by the model that actually ran, and flags a model family whose newest model never appears.
- **`scripts/derive-audit-facts.py`** gathers the reconciliation, workflow totals, versions, settings drift and credential presence in one call, reading credential files for key names and dates only.
- **`scripts/bundle-check.py`** enforces nine rules on the bundle, including a mandatory verification section and the rule that a claimed approval names its record; its self-test proves each rule fails on a mutation of the committed sample.
- **Every agent names a model and opens with a shared rules block** that forbids opening a credential file; `scripts/test-workflow-reference.py` proves it.
- **Manual-only** (`disable-model-invocation: true`), because a run launches up to nine agents and writes ledger rows.

**Also: manual-only in Codex.** `disable-model-invocation: true` is a Claude Code field that Codex ignores, so without more the skill would sit in the Codex model's skill list and could fire on its own. The 2026-08-29 audit found that gap in every manual-only skill that existed then. This skill's `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads instead: it hides the skill from the model and keeps it callable by name. `scripts/codex-invocation-check.py` fails CI when a skill carries either flag without the other.

