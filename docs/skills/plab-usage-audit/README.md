# plab-usage-audit

**Version:** 1.0.0
**Source:** [`skills/plab-usage-audit/`](../../../skills/plab-usage-audit/)

Audit one week of your own Claude Code usage against the week before: what it cost by lane and by the model that actually ran, whether routing met your rules, whether last week's recommendations happened, what changed in your configuration, and the few changes worth making next. Every number comes from a script, and a verifier checks the bundle before you read it. Manual invocation only.

---

## Getting Started

### Quick Start

```
/plab-usage-audit
```

The bundle lands in `<output_dir>/YYYY-MM-DD_claude-usage/`, where `output_dir` comes from your settings file. Start with its `README.md`, which holds the five-minute version and the recommendations table.

### Common Invocations

```
# The week ending today
/plab-usage-audit

# The week ending on a given day
/plab-usage-audit --date 2026-11-06

# Reuse the session-log digest a pulse run already wrote for the same window
/plab-usage-audit --digest pulse/2026-11-06/digest.jsonl
```

### Setup

Copy the example in [`references/settings-example.md`](../../../skills/plab-usage-audit/references/settings-example.md) to `.claude/plab-usage-audit.local.md` in the repository you run the audit from, and keep it gitignored. It names your transcript folder, time zone, ledger, decision sources, change register, credential files (checked by key name only) and private patterns. Python 3.11 or later on PATH; no other dependency.

---

## When to Use

- Once a week, on a fixed day, to keep a history of what your agent usage cost and whether your changes worked.
- After changing settings, routing rules or models, to see the effect in the next week's numbers.

## When Not to Use

- **To see what you are spending right now.** Run `/usage`; it shows the current session and your plan limits live.
- **For per-prompt token forensics.** Run the `session-report` plugin.
- **For general advice on Claude Code features.** Run `/insights`.

[`references/positioning.md`](../../../skills/plab-usage-audit/references/positioning.md) compares the four in full.

---

## What a Run Does

1. Resolves the two weeks in your time zone and refuses to write into a folder git would track, unless you allowed it.
2. Asks once for the two plan-limit percentages `/usage` shows.
3. `collect.py` measures the transcripts; `derive-audit-facts.py` reconciles last week, checks workflow costs, versions, settings drift and credential presence; the sweep lists what shipped.
4. Reads the week's session logs for lessons, or takes a supplied digest.
5. Three brief workers write the usage, scorecard and config briefs.
6. The main loop writes the bundle, removing any claimed approval that no record supports.
7. A verifier checks every number and claim; each correction is listed under Verification.
8. `scrub.py` removes private paths; `bundle-check.py` checks the bundle.
9. The run records its own cost in the ledger.

## Safety

- No agent may open a credential file; only the facts script reads them, for key names and dates, and it never prints a value.
- Every agent names a model, Sonnet or Haiku by default.
- The skill never commits, pushes or publishes.

## Specification

[UA-01 (usage audit skill)](../../internal/release-plans/_unassigned/UA-01_usage-audit/spec.md). Its six design decisions are built on working defaults and await your ratification.
