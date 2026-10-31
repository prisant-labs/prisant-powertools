# plab-project-pulse

**Version:** 1.0.0
**Source:** [`skills/plab-project-pulse/`](../../../skills/plab-project-pulse/)

Roll every repository you keep into one private weekly pulse: what shipped, what each project says is next, and what waits on you, ranked across projects with the age of each waiting item. It reuses fresh `plab-current-status` snapshots instead of re-reading those repositories, and writes a self-contained dashboard. Manual invocation only.

---

## Getting Started

### Quick Start

```
/plab-project-pulse
```

The run lands in `<output_dir>/YYYY-MM-DD/`. Open `dashboard.html` in a browser, or read `readout.md`.

### Common Invocations

```
# The full weekly run: facts, log readers and scouts for active repositories
/plab-project-pulse

# No agents at all: facts, snapshots and carried entries only
/plab-project-pulse --quick

# Reuse the digest the usage audit already wrote for the same week
/plab-project-pulse --digest audits/2026-11-06_claude-usage/data/digest.jsonl
```

### Setup

Copy the example in [`references/settings-example.md`](../../../skills/plab-project-pulse/references/settings-example.md) to `.claude/plab-project-pulse.local.md` in the repository you run it from, and keep it gitignored. It names your roots, depth, author pattern, time zone, output folder and state file. Python 3.11 or later and git on PATH; `gh` optional.

---

## How It Differs From plab-current-status

| | `plab-current-status` | `plab-project-pulse` |
|---|---|---|
| Question | Where does this project stand, and what do I do next in it? | Where does everything stand, and what waits on me? |
| Scope | The one repository you are in | Every repository under your roots |
| Depth | Deep | One entry per repository |
| Output | A Markdown file in that repository's `_local/_status/` | A private folder with data, a readout and a dashboard |

"Where is this project?" runs `/plab-current-status`. "Where is everything?" runs the pulse. A repository with a snapshot newer than its last commit costs the pulse no agent, and the readout lists the active repositories whose snapshot is missing or stale, so running `/plab-current-status` there makes the next pulse cheaper and deeper.

## What a Run Does

1. `derive-pulse-facts.py` finds every repository, sweeps git read-only, optionally asks `gh`, classifies each repository as active or dormant, carries dormant entries forward, reads fresh snapshots, ages waiting items and finds recent work in folders git does not protect.
2. In `--week`, log readers and scouts read only the active repositories without a fresh snapshot, and each scout's count is checked.
3. The main loop picks at most ten next steps across everything.
4. `build-pulse.py` writes `pulse.json` and `coverage.md`, and updates the state only after validation; `render.py` writes the dashboard; `pulse-check.py` checks all of it.

## Safety

- No command changes a repository: no fetch, pull, checkout or commit.
- No agent may open a credential file.
- All output is private, and the skill never commits, pushes or publishes.

## Specification

[PP-01 (project pulse skill)](../../internal/release-plans/_unassigned/PP-01_project-pulse/spec.md). Its five design decisions are built on working defaults and await your ratification.
