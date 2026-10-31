# How this audit differs from the native tools

Claude Code ships three ways to look at usage. Each answers one question about the present. None keeps structured history across weeks, exports data for another tool, or checks whether a past change worked. That gap is this skill's reason to exist, and every section of the bundle must answer a question none of the three answers. Facts below were read from Claude Code's documentation and the installed `session-report` plugin on 2026-10-30; re-check them when Claude Code's changelog touches `/usage` or `/insights`.

| | `/usage` (also `/cost`, `/stats`) | `/insights` | `session-report` plugin | `plab-usage-audit` |
|---|---|---|---|---|
| Question | What am I spending now, and how close am I to plan limits? | How do I work, where does it go wrong, which features should I try? | Where did the tokens go in this window? | What did the week cost, did my last changes work, and what should change next? |
| Output | Terminal screen only | HTML in `~/.claude/usage-data/`, a dated copy per run | HTML in the current folder | A dated bundle and ledger rows |
| Window | Current session; last 24 hours or 7 days | Up to 200 sessions not analyzed before | Rolling, 7 days by default | Calendar weeks in local time, fixed cutoff |
| Dollars | Yes, list price | No | No, tokens only | Yes, by model and lane |
| By model | Current session only | Not documented | No | Yes, by the model that ran |
| Other breakdowns | Share by skill, subagent, plugin, MCP server | By project and usage pattern | By project, subagent type and skill; cache rebuilds; costliest prompts | By lane, project, model, population; advisor separate |
| Plan-limit use | Yes, from the server | No | No | Asked once per run and kept as history |
| History | 24-hour versus 7-day toggle | Dated copies, never compared | None | A ledger, re-measured and reconciled weekly |
| Recommendations | Rule-based, with an automatic-fix key | Model-written | Three to five findings | Owner, mechanism and evidence on each; scored the next week |
| Export | None | None | JSON from its analyzer | JSON and JSONL |

## What the bundle must not repeat

- **Live figures.** Current-session spend and plan-limit bars are `/usage`. The bundle keeps their weekly history instead.
- **Per-prompt token forensics.** `session-report` shows the costliest prompts and cache rebuilds; point to it when the depth section needs per-prompt detail.
- **General feature advice.** `/insights` suggests features to try; the practice lane reports which suggestions were adopted.

## What only this audit does

1. Prices every response by the model that actually ran, and flags a family whose newest model never appears (a pinned alias).
2. Splits the advisor from delegated executor spend, and scores routing against the owner's own rule.
3. Re-measures last week and reconciles it with the published figure, naming each cause of any difference.
4. Scores last week's recommendations against files on disk, and counts how many audits each open ask has waited.
5. Reports settings changed with no row in the owner's change register, including changes applied by `/usage`'s automatic fixes.
6. Reads the owner's own session logs for lessons, with a verifier checking every claim before the owner reads it.
