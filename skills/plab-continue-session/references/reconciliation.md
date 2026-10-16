# Reconciliation Against Repository Reality

How the new resumption phase checks a session log's claims against the repository's current state before any of the log's content is presented as though it were still current. The mechanism itself lives in `scripts/reconcile.py`, proven by its sibling `scripts/test-reconcile.py`; this file documents how to invoke it and read its output. It does not restate what the script already implements and tests, the same relationship `skills/plab-wrap-session/references/hygiene-sweep.md` Check 5 has to `organize-logs.py`.

## Why a script, not a documented convention

An earlier version of this effort's plan made reconciliation a rung-3 documented convention, reasoning that `plab-continue-session` "has no independent execution runtime ... so there is no standalone script for a canary to test against." That reasoning no longer holds: `plab-wrap-session` already ships agent-run scripts with sibling test files (`organize-logs.py` / `test-organize-logs.py`, `path-citation-check.py`), and a 2026-10-01 measurement found that the number of tool calls, not the amount of text, drives a wrap's or resume's cost. `reconcile.py` follows the same pattern: it is canary-tested, but it stays out of CI, exactly like `test-organize-logs.py`. See the C-02 spec's OQ4 for the full record of this decision.

## Invocation

This script's own path resolves against this skill's own directory, wherever the plugin is installed, exactly the convention `organize-logs.py` documents in `skills/plab-wrap-session/SKILL.md`. Unlike that script's session-log store argument, both the project root and the log path are given explicitly here, since `plab-continue-session` has no single fixed path to resolve a log against the way the wrap skill's store is fixed.

```bash
python scripts/reconcile.py <project_root> <log_path>
```

`<project_root>` is the repository being resumed in (the current working directory in the normal case). `<log_path>` is the log file Phase 1 selected. Pass `--fetch-timeout <seconds>` to override the default 20-second budget for the network checks (the fetch and all three `ls-remote` calls); see spec.md OQ3 for why 20 was chosen. Pass `--json` for the full structured report (used by `test-reconcile.py`); omit it for the Markdown rendering meant to be pasted directly under the `### What changed since this log` heading (see `references/handoff-display.md`).

## Reading the output

The script's default (non-`--json`) output is already shaped to paste under the delta heading. Paste it verbatim; do not re-summarize it, since re-summarizing risks silently dropping a broken check (AC-8).

Each of the nine checks the script runs reports one of three states:

| State | Meaning |
|-------|---------|
| `ok` | The check ran to completion and found no drift. |
| `finding` (`FINDING` in the Markdown output) | The check ran to completion and found real drift: commits landed, a tag was cut, the log's branch is gone, a cited path is missing or was renamed, or recent commits overlap the continuation prompt's next action. |
| `broken` (`BROKEN` in the Markdown output) | The check could not complete (the network was unreachable, a fetch or `ls-remote` timed out, the log's branch no longer exists so the comparison base is in question, or the log itself could not be read). |

The script's own exit code mirrors the worst state across all nine checks: `0` only when every check is `ok`, `1` when every check completed and at least one is a `finding`, `2` when at least one check is `broken`. A `broken` check is never silently folded into a clean result; the Markdown output names which check failed and what it could still verify, and the agent presenting the delta should say the same thing rather than omitting the section.

## What each check covers

- **Remote fetch and ahead/behind** (AC-2): the same command sequence `skills/plab-wrap-session/references/hygiene-sweep.md` Check 1 defines, with one deliberate deviation: `git fetch --no-prune origin --tags`, not a plain fetch. A plain fetch prunes whenever `fetch.prune` is set in git config, and a pruning fetch deleted a remote-tracking ref without confirmation on 2026-09-25 (sibling spec W-02 (derived log facts), decision D4). If the fetch itself did not succeed, this check goes broken rather than reporting ahead/behind off a potentially stale `@{u}`.
- **Remote branches without a local counterpart** (AC-2): the rest of Check 1's literal command set, `git ls-remote --heads origin` (unscoped, unlike AC-5's branch-existence check below) and `git tag -l` (the last five taken in Python). Flags exactly the drift Check 1 itself names; a one-maintainer repo with several short-lived feature branches should expect this often, the same as at wrap time.
- **Commits since the log** (AC-3): via the log's `commit-sha` frontmatter field when present, via a date comparison against the log's `date` field otherwise. The date comparison is done commit-by-commit in Python, not with `git log --since=`, because that flag's boundary proved inclusive against a fixture, double-counting the exact commit a wrap session logs against whenever the log's timestamp and that commit's timestamp coincide to the second.
- **Release cut since the log** (AC-4): each tag's creation date (`creatordate:iso-strict`, not the date-only `:short` form) against the log's `date` field.
- **The log's branch, locally and on origin** (AC-5): additive to, not a replacement for, the existing current-branch-mismatch warning in `references/handoff-display.md`.
- **Continuation-prompt file paths** (AC-6): scoped using D-12's (path-citation precision) three-way rule, mirrored minimally from `skills/plab-wrap-session/scripts/path-citation-check.py` (a comment in `reconcile.py` names that file as the rule's source). A missing path gets a rename-hint attempt that scans every rename record in the repository's history with no pathspec restriction, because the literal `git log --follow --diff-filter=R -- <path>` this effort originally proposed finds nothing for a path missing at HEAD.
- **Next action vs. recent commits** (AC-7): advisory only. States that the named next action may already be complete when recently touched files overlap the continuation prompt's citations; never asserts completion as fact.

## No command here mutates repository state (AC-9)

Every command `reconcile.py` runs is read-only: `fetch`, `status`, `log`, `diff`, `diff-tree`, `branch --list`, `ls-remote`, `tag -l`, `for-each-ref`, `rev-list`, and `rev-parse` in verification form. None of `pull`, `merge`, `checkout`, `reset`, or `push` appears anywhere in the script as a command it runs; `test-reconcile.py` asserts this against the script's own recorded command list at runtime, not only by reading the source.
