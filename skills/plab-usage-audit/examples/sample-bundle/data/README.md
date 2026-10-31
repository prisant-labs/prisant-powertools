# Method notes - 2026-10-19 to 2026-10-25

This file explains how the rest of `data/` was produced and checked, in the order a reader would want to question it: what window was used, what was excluded before counting, whether the numbers reconcile, what commands produced them, what the ledger holds, which agents ran at which model, what the verifier found, and what this bundle does not measure at all.

## Windows

The focus week runs 2026-10-19 through 2026-10-25 in `America/Los_Angeles`, cut at 09:00 local time on 2026-10-25. The prior week, 2026-10-12 through 2026-10-18, is read for the reconciliation but not re-reported on its own.

## Exclusion method

Before any count is taken, `collect.py` drops task-notification records from `user_prompts`, folds a copied transcript folder into the session it duplicates, and excludes any response whose model id is missing from the price file, which it reports under `unpriced` rather than silently omitting.

## Reconciliation

This week's re-run of last week's cutoff reproduces last week's published total, $118.90, exactly. The sum of this week's per-workflow costs is $139.20 against a workflow lane total of $142.30, a $3.10 gap inside the configured $5.00 tolerance.

## Commands

`python collect.py --since 2026-10-19 --until 2026-10-25 --zone America/Los_Angeles` wrote `data/collector-output.json` and `data/digest.jsonl`. `python derive-audit-facts.py --json` wrote `data/audit-facts.json` from the collector output, the sweep, and the change register, with no credential value in its output.

## Ledger

This run appended one `audit_run` row for the week of 2026-10-19 to the ledger. The previous row for that week does not exist, so this is the first measurement rather than a supersession.

## Agents

| Agent | Model | Task |
|---|---|---|
| brief-alpha-app | sonnet-5 | draft the alpha-app lane of 01-usage.md and 02-shipped.md |
| brief-beta-lib | sonnet-5 | draft the beta-lib lane of 01-usage.md and 02-shipped.md |
| verifier | opus-5-5 | check every number against collector output and every approval claim against its record |

## Verification

The verifier (opus-5-5) checked every number in this bundle against `data/collector-output.json` and `data/audit-facts.json`, and every claim of an owner approval, choice, or decision against the record it cites.

Two corrections were made:

1. `brief-beta-lib`'s draft of the spend-by-project line in `01-usage.md` originally reported `beta-lib` at $18.40; `data/collector-output.json` shows $16.90, and the line was corrected before this bundle was finished.
2. `brief-alpha-app`'s draft of `03-scorecard.md` originally stated that the owner approved disabling `alpha-app`'s nightly workflow; no decision record names that approval, so the sentence was removed and the item was left as still open.

## Not measured

This bundle does not measure CI outcome for either project, nor the downstream effect of a shipped change on the repositories themselves; the former has no cheap reliable source yet, and the latter is `plab-project-pulse`'s question.
