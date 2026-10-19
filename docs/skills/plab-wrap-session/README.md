# plab-wrap-session

**Version:** 1.8.1
**Source:** [`skills/plab-wrap-session/`](../../../skills/plab-wrap-session/)

Document and close agentic coding sessions with structured session logs. Deep mode is the default: a full log with evidence index, a verbose copy-paste-ready continuation prompt, a pre-wrap hygiene sweep (remote divergence, release state, doc drift, working-tree reconciliation with per-action confirmation), and a mandatory Waiting on You section listing everything blocked on the maintainer, with links.

---

## Getting Started

### Quick Start

At the end of any coding session:

```
/plab-wrap-session
```

The skill gathers evidence (git status, decisions, files changed), selects a mode, and writes a structured session log to `_local/_session-logs/` with a continuation prompt you can paste into the next session.

### Where Logs Go

```
_local/_session-logs/YYYY-MM-DD_HH-MM_<llm>_<brief-kebab-title>.md
```

All agents write to the same centralized directory. The LLM short name in the filename identifies who did the work. The skill creates the directory if it doesn't exist.

Once a month closes, `--organize` files its logs into a `YYYY-MM/` subfolder. New logs are always written flat at the top level, so the path above never changes.

### Installation

Install via the prisant-labs marketplace:

```bash
/plugin marketplace add prisant-labs/agent-plugins
/plugin install prisant-powertools@prisant-labs
```

---

## When to Use

- End of any coding session (the most common trigger)
- Switching tasks or contexts mid-work
- When you're blocked and need to capture the blocker for the next session
- When you say "wrap up", "end of session", "session log", or "close out"

## When NOT to Use

- Mid-session status checks (just ask "what have we done so far?")
- Documenting design decisions (use ADRs or decision logs)
- Writing project documentation (use docs/ directly)

---

## Four Modes

**Deep is the default.** Every wrap is deep unless the agent records a specific objection in the log justifying a lighter mode (the same comply-or-explain contract that governs continuation-prompt verbosity). You can always override in either direction.

### Quick

**When:** Downgrade with stated objection: short session (< 30 min), few files, trivial fix.

**Output:** Frontmatter + summary + files changed + Waiting on You + continuation prompt (verbose by default; agent may emit a lighter prompt only with a stated objection). No detailed body sections.

### Final

**When:** Downgrade with stated objection: mid-length, low-risk session with nothing autonomous.

**Output:** Full structured log with all sections:

| Section | Content |
|---------|---------|
| **Summary** | 2-4 sentences - what happened and why it matters |
| **Work Completed** | Bulleted accomplishments |
| **Decisions Made** | Each decision with rationale (scaled to significance) |
| **Files Changed** | From git, grouped by purpose |
| **Verification** | What was tested, assumed, or skipped |
| **Outstanding Issues** | Blockers, risks, unfinished work |
| **Hygiene Sweep** | Pre-wrap sweep findings: state found, actions proposed, taken vs declined |
| **Waiting on You** | Everything blocked on the maintainer, with reasons and file links; "Nothing pending." when empty |
| **What's Next** | Ordered list, most important first; names the single unlocking decision when one exists |
| **Continuation Prompt** | Copy-paste-ready for next session; carries the Waiting on You list |

### Deep (Default)

**When:** Every session, unless a downgrade objection is recorded.

**Output:** Full log + evidence index + detailed verification table. Everything in Final mode, plus forensic-level detail.

Before writing, deep and final modes run the **pre-wrap hygiene sweep** ([`references/hygiene-sweep.md`](../../../skills/plab-wrap-session/references/hygiene-sweep.md)). As of 1.8.0, one call to `scripts/derive-log-facts.py --fetch` returns the detection results for all five checks in a single pass: git fetch and remote comparison (catches parallel work from another checkout), working-tree and worktree state, release hygiene (pending CHANGELOG content, version-vs-tag consistency), documentation drift, and the session-log store. The repo's own validation scripts, when it has any, are still run as a separate step, chained into one shell command so their combined output is read in one call rather than one call per script, and reported, since the script has no way to know what those scripts are. Each finding becomes one concrete proposal executed only on your per-action confirmation; declined proposals are recorded and carried into the continuation prompt.

### Blocked

**When:** Session ended by an unresolved blocker.

**Output:** Frontmatter + summary + blocker details + continuation prompt. Focuses on capturing the blocker clearly so the next session can resolve it.

---

## Organizing the log store (`--organize`)

A flat session-log directory grows without bound. At roughly four logs a week it passes a hundred files inside a year, and browsing it by hand stops being pleasant.

```
/plab-wrap-session --organize
```

This runs **instead of** a wrap. No session log is written, no hygiene sweep runs. It files logs from closed months into `YYYY-MM/` subfolders:

```
_local/_session-logs/
  2026-05/
    2026-05-19_14-30_claude_skill-audit.md
  2026-06/
    2026-06-02_11-15_codex_guide-pdf-toolchain.md
    2026-06-30_09-40_claude_capture-lite-hook.md
  2026-07-21_16-05_claude_release-v011.md          <- hot, previous month
  2026-08-18_13-44_claude_marketplace-ssh-to-https-fix.md   <- hot, current month
  _capture/                                        <- never touched
```

**The current month and the previous month are never filed.** Recent logs stay flat, which is where resume reads them first. On 2026-08-18 that means 2026-08 and 2026-07 stay put, and 2026-06 and older get filed.

**Nothing moves without your say-so.** The skill runs the organizer in dry run, shows you exactly which files would move where, and asks once. Declining changes nothing.

**Resume is unaffected.** `/plab-continue-session` 1.3.0+ reads the flat store and the month folders as one pooled set, sorted by filename, so an archived log and a hot log order correctly against each other. Filenames never change when a log is filed.

**You do not have to remember this exists.** Deep and final wraps run hygiene Check 5, which reports unfiled logs and offers to file them:

> Log store: 14 logs from 3 closed months (2026-05, 2026-06, 2026-07) are unfiled.
> File them into month folders? (y/n)

### Guarantees

| Situation | Behavior |
|---|---|
| Current or previous month | Never filed |
| Target filename already exists | Skipped and reported, nothing overwritten |
| File that is not a session log | Left in place and reported |
| Subdirectory other than `YYYY-MM` | Never entered |
| Legacy log directories | Never touched |
| Anything | Never deleted; moves only |

Run it twice and the second run does nothing. A full worked example with real command output: [`skills/plab-wrap-session/examples/organize-logs-walkthrough.md`](../../../skills/plab-wrap-session/examples/organize-logs-walkthrough.md).

---

## Output Shape

The skill writes one session log to `_local/_session-logs/YYYY-MM-DD_HH-MM_<llm>_<brief-kebab-title>.md`. Section depth scales to the selected mode (quick / final / deep / blocked); the table below shows the full Final-mode shape:

| Section / Element | Purpose |
|-------------------|---------|
| YAML frontmatter | Machine-readable metadata across 3 tiers (date, machine, repo, branch, summary, files-changed always; session-type, model, status, decisions-count, skills-used, resumed-from when available) for indexing and tooling |
| `## Summary` | 2-4 sentences: what happened and why it matters |
| `## Work Completed` | Bulleted, specific list of accomplishments |
| `## Decisions Made` | Each decision with rationale, scaled from one-liner to full alternatives analysis |
| `## Files Changed` | From git, grouped by purpose |
| `## Gitignored Outputs` | Work products git cannot see (`_local/` and kin): path + one-liner each |
| `## Verification` | Checklist of what was tested, assumed, or skipped (never conflates completed with verified) |
| `## Outstanding Issues` | Blockers, risks, unfinished work |
| `## Hygiene Sweep` | Sweep findings and the fate of each proposal |
| `## Waiting on You` | Items blocked on the maintainer, with links; required in every mode |
| `## What's Next` | Ordered list, most important action first |
| `## Continuation Prompt` | Copy-paste-ready fenced block: task context, current state, immediate next action, file paths, branch, and the Waiting on You list. Verbose by default in every mode |

Quick mode trims to summary + files + waiting-on + continuation prompt; blocked mode swaps in a `## Blocker` (what / who can unblock / impact); deep mode adds an `## Evidence Index` and a `## Verification Detail` table. Per-mode skeletons live in [`references/session-log-template.md`](../../../skills/plab-wrap-session/references/session-log-template.md).

---

## Examples

### Example 1: Quick Wrap After a Bug Fix

```
/plab-wrap-session
```

**Output:** (~30 lines)

Filename: `_local/_session-logs/2026-04-08_16-45_claude_fix-null-pointer.md`

```yaml
---
date: 2026-04-08T16:45:00-07:00
repo: my-project
branch: fix/null-check
summary: "Fix null pointer in user lookup when email is missing"
files-changed:
  - src/users/lookup.ts
session-type: bugfix
model: claude opus 4.6
model-settings: extended-thinking max
status: completed
---
```

Summary, one file changed, continuation prompt: "The fix is committed but not pushed. Push and verify in staging."

### Example 2: Final Wrap After Feature Work

```
/plab-wrap-session
```

**Output:** (~80 lines) Full log with 6 files changed across 3 commits, 2 decisions documented, verification checklist (tests passing, linting clean, manual QA not done), and a specific continuation prompt naming the next file to implement.

### Example 3: Blocked Wrap

```
/plab-wrap-session
```

**Output:** (~40 lines) Captures the blocker ("CI fails on node 18 - the sharp dependency requires node 20, but the CI image is pinned to 18"), what was tried, and a continuation prompt focused on resolving the blocker.

---

## The Continuation Prompt

This is the single most important output. Requirements:

- **Copy-paste ready** - wrapped in a fenced code block
- **Specific** - names exact files, branches, and next actions
- **Bounded** - one clear immediate action, then ordered secondary steps
- **Self-contained** - readable without the original session

A continuation prompt that says "continue where we left off" has **failed**. It must include enough context for a cold-start session.

### Verbose by default (v1.1.0)

The continuation prompt defaults to the verbose / deep form **in every mode**, including quick. The only path to a lighter prompt is for the agent to state a specific objection in the session log (e.g., "trivial typo fix; no context to carry forward"). This is a comply-or-explain rule: produce the verbose form, or produce a lighter form with the explicit reason recorded.

### Good Example

```
Continue work on acme-service (~/code/acme-service).

Last session deployed the ai-review skill v1.0.0 and pushed to origin.

Current state:
- 4 deployed skills (plab-guide, plab-strategy-brief, plab-wrap-session, plab-ai-review)
- Retry-policy plan doc written with 9 open decisions

Immediate next action:
1. Resolve the retry-policy decisions (D1-D9 in plan_v1_retry-policy.md)
2. Build the retry middleware from the resolved plan
```

### Bad Example

```
Continue where we left off on the project.
```

---

## YAML Frontmatter

Every log includes metadata for indexing and future tooling:

| Tier | Fields | When |
|------|--------|------|
| **1 (always)** | date, type, machine, repo, branch, summary, files-changed, commit-range, latest-tag | Every log |
| **2 (when available)** | session-type, parent-session, model, model-settings, agent, status, decisions-count | Most logs |
| **3 (when applicable)** | duration-minutes, tokens-used, commit-sha, tags, related-issues | Complex sessions |

Since 1.8.0, `derive-log-facts.py` also always returns two further Tier 1 fields, `commit-range` (the `base..HEAD` short-SHA range the script diffed) and `latest-tag` (the nearest reachable tag, distinct from the topic-keyword `tags` field above). `decisions-count` is filled in by the agent once the Decisions Made section is drafted, then checked mechanically by `check-log.py` (1.8.1) before the wrap is done, rather than shipping as an uncorrected model estimate.

See `references/frontmatter-schema.md` for the field-by-field specification (25 fields as that file currently lists them, including `commit-range` and `latest-tag`).

### Session Types

`bugfix` | `feature` | `refactor` | `research` | `planning` | `review` | `docs` | `autonomous` | `exploration`

---

## Surrounding Document Updates

After writing the log, the skill checks if changes warrant updates to README, CHANGELOG, or active plans. Rules:

- **README:** Only when user-facing capabilities changed
- **CHANGELOG:** Only when release-worthy (new feature, visible bugfix, breaking change)
- **Plans:** Only when sequence, scope, or assumptions changed

**Always asks for confirmation** before editing any surrounding document.

---

## Reference Files

| File | Purpose | When to Read |
|------|---------|-------------|
| `references/frontmatter-schema.md` | Complete 25-field metadata specification (3 tiers) | When customizing frontmatter or building tooling |
| `references/session-log-template.md` | Output skeletons for all 4 modes | When examining exact output structure per mode |
| `references/hygiene-sweep.md` | The five pre-wrap checks, their commands, and the per-action confirmation protocol | When understanding what the sweep inspects and proposes |
| `references/doc-update-rules.md` | When/how to update README, CHANGELOG, plans, and ADRs | When understanding the surrounding document update rules |
| `scripts/derive-log-facts.py` | One call gathers the frontmatter facts, the Waiting on You carry-forward, and the detection results of all five hygiene checks | Run once per wrap, before drafting the log |
| `scripts/check-log.py` | Log Self-Check: one call runs the decisions-count, summary-length, Tier 1, Waiting on You, and deep-mode-section checks, plus the two detector scripts below | After writing the log |
| `scripts/dash-check.py` | No em-dash or en-dash in the drafted log, detector-backed and canary-proven; called by `check-log.py` | After writing |
| `scripts/path-citation-check.py` | Path citations in the drafted log resolve, detector-backed and canary-proven; called by `check-log.py` | After writing |
| `scripts/organize-logs.py` | Files logs from closed months into `YYYY-MM/` folders; dry run by default | Run by `--organize` and by hygiene Check 5 |
| `examples/organize-logs-walkthrough.md` | A worked `--organize` run with real captured output | When you want to see exactly what filing does before running it |

---

## Skill Files

```
skills/plab-wrap-session/
├── SKILL.md                        # Core instructions
├── HISTORY.md                      # Per-version change record
├── references/
│   ├── frontmatter-schema.md       # 25-field metadata reference (3 tiers)
│   ├── session-log-template.md     # Output templates for all 4 modes
│   ├── hygiene-sweep.md            # The 5 pre-wrap checks and the confirmation protocol
│   └── doc-update-rules.md         # README/CHANGELOG/plan/ADR update rules
├── scripts/
│   ├── check-log.py                # Log Self-Check: one call for every mechanical gate
│   ├── dash-check.py               # No em-dash or en-dash, canary-proven; called by check-log.py
│   ├── derive-log-facts.py         # One call: frontmatter facts, Waiting on You, all 5 hygiene checks
│   ├── organize-logs.py            # Files logs into YYYY-MM/ folders (--organize, Check 5)
│   ├── path-citation-check.py      # Path citations resolve, canary-proven; called by check-log.py
│   ├── test-check-log.py           # Fixture checks for check-log.py
│   ├── test-derive-log-facts.py    # Fixture checks for derive-log-facts.py
│   └── test-organize-logs.py       # 34 fixture checks for the organizer
└── examples/
    └── organize-logs-walkthrough.md  # Worked --organize run with real output
```

---

## Constraints

- Never embeds full transcripts (references the transcript path only)
- Never conflates "completed" with "verified"
- Never auto-commits or pushes
- Never updates surrounding docs without confirmation
- Summary must be 120 characters or less
- Session log must be self-contained

---

## Tips

- **The continuation prompt is worth the entire skill.** If wrap-session did nothing else, a good continuation prompt would justify its existence.
- **Quick mode is fine for most sessions.** Don't over-document trivial work. A typo fix needs a quick wrap, not a deep forensic record.
- **Verification honesty matters.** "Tests not run" is more useful than silence. Future-you needs to know what was assumed.
- **Let git be the source of truth for files.** The skill runs git commands to ground file changes in reality rather than relying on session memory.
- **Use blocked mode proactively.** When you hit a wall, wrap immediately while the blocker is fresh. Don't try to push through and then forget the details.

---

## Improvement Ideas

- Automatic session duration tracking (start/end timestamps)
- Session log search/index tool across all session logs
- Session chains - link parent/child sessions for multi-session work
- Template customization per project (some projects need different sections)
- Integration with GitHub Issues (auto-link session work to open issues)
- Aggregation view - weekly/monthly summary across all session logs
