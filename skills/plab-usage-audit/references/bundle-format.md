# Bundle format

The files a `plab-usage-audit` weekly run writes, and the rules `scripts/bundle-check.py` enforces. The committed sample under `examples/sample-bundle/` follows every rule and is the worked example.

## Folder

One folder per run, named `YYYY-MM-DD_claude-usage`, where the date is the audit day. It holds:

| Path | Contents |
|---|---|
| `README.md` | The window, whether there was enough history, the five-minute version, the recommendations table, the reading order |
| `01-usage.md` | Numbers by lane, the reconciliation, the advisor, workflows, depth, the automated population, routing, the model that ran, friction, spend by project |
| `02-shipped.md` | Tags and commits from the sweep. Status beyond git belongs to `plab-project-pulse` |
| `03-scorecard.md` | The previous recommendations scored, decision records, due and overdue open items, the decision pattern, the smallest set of asks |
| `04-config.md` | Findings, settings against the change register, Claude Code versions and changelog entries, credential presence by key name, backup health when configured |
| `05-recommendations.md` | The recommendations, the practice lessons, and one to-do list |
| `data/README.md` | The method notes, with the required sections below |
| `data/*.json`, `data/*.jsonl` | The collector output, the audit facts, the sweep, the digest and the briefs' inputs |
| `data/briefs/*.md` | The brief workers' returns, kept for the verifier |

## Rules

**R1, files.** Every file in the table above exists. `data/` holds at least one `.json` file.

**R2, the five-minute version.** `README.md` has a level-2 heading that starts with `Five-minute version`, and a table whose header row contains `ID` and `Who acts`.

**R3, recommendations.** `05-recommendations.md` has at least one recommendation. A recommendation is a level-2 heading of the form `## <ID> (<handle>): <title>`, where `<ID>` is one letter followed by digits, such as `A1`, and `<handle>` is non-empty. Inside each recommendation's section:

- a line starting `**Who acts:**` whose value is one of `owner decides`, `owner acts`, `agent`, `agent after a yes`;
- a line starting `**Mechanism:**` whose value is one of `setting`, `rule`, `hook`, `skill`, `script`, `decision`, `habit`.

Sections whose heading does not match the id form, such as `## What the session logs taught`, are not recommendations and carry no tags.

**R4, method notes.** `data/README.md` has these level-2 headings, in this order: `## Windows`, `## Exclusion method`, `## Reconciliation`, `## Commands`, `## Ledger`, `## Agents`, `## Verification`, `## Not measured`.

**R5, routing table.** The `## Agents` section holds a table whose header row contains `Model`, and every data row has a non-empty model cell.

**R6, verification.** The `## Verification` section is non-empty: it lists each correction the verifier raised, applied or rejected with a reason, or states `No corrections.` with the verifier's model named.

**R7, JSON.** Every `.json` file under the bundle parses, and every line of every `.jsonl` file parses.

**R8, privacy.** No file under the bundle contains a configured private pattern, the home path, or a drive-letter path (`[A-Za-z]:[\\/]`). The patterns come from `--private-pattern` arguments, repeatable; the home path is checked always. This rule runs after `scrub.py`.

**R9, approvals.** In `03-scorecard.md` and `05-recommendations.md`, any sentence that says the owner `approved`, `chose`, `decided`, `declined` or `said yes` also contains a backticked path or a quotation in double quotes, which names the record. A claim of approval with no record is the error the verifier exists to catch.

## Exit codes

`bundle-check.py <bundle>` exits 0 when every rule passes, 1 when any rule fails (each failure printed as `R<n>: <file>: <message>`), and 2 when the bundle folder does not exist or `data/` is absent.

`bundle-check.py --self-test` runs every rule against `examples/sample-bundle/` and requires a pass, then for each rule applies one mutation to a temporary copy of the sample and requires that rule to fail. It exits 0 when every mutation is caught, and 2 naming the rule whose mutation passed. A gate that cannot fail is not a gate.
