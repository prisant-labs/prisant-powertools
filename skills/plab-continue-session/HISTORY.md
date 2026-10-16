# History - plab-continue-session

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.6.0 | 2026-10-15 | unreleased | added | A new Phase 3 reconciles the log's claims against live repository state before anything is displayed, and leads the resumption context with what changed. |
| 1.5.0 | 2026-09-15 | v0.5.5 | changed | The continuation prompt is no longer dumped verbatim. Phase 3 renders the immediate action and gives the log path; verbatim is opt-in. |
| 1.4.0 | 2026-08-25 | v0.4.0 | added | Capture-lite orientation on the no-log and stale-log paths. |
| 1.3.0 | 2026-08-18 | v0.2.0 | added | Discovery reads `YYYY-MM/` month folders alongside the flat store. Empty-store message diagnoses version skew. |
| 1.2.1 | 2026-08-18 | v0.1.2 | fixed | Body trigger list aligned with the narrowed description. Records the 2026-08-17 description change that shipped un-versioned. |
| 1.2.0 | 2026-08-14 | v0.1.0 | migrated | First release in prisant-utilities. Migrated from a private upstream at version 1.2.0; prior history remains there. |

## 1.6.0 - 2026-10-15

**Added: a new Phase 3, "Reconcile against reality."** Before any of a session log's content is presented as though it were still current, the skill now derives live repository state and diffs it against what the log claimed, then leads the resumption display with that delta under a new "What changed since this log" section.

The delta covers five categories of drift: commits landed since the log was written, a release cut elsewhere, the log's branch no longer existing (locally or on origin, distinct from the existing branch-mismatch warning), a continuation-prompt file path missing or renamed, and an advisory when recent commits touch the same files the continuation prompt's next action names. Each check reports one of three states, ok, finding, or broken, and a check that cannot complete names itself rather than being folded into a silently clean result.

The mechanism is a script, `scripts/reconcile.py`, with a sibling test file, `scripts/test-reconcile.py`, on the same pattern `plab-wrap-session`'s `organize-logs.py` / `test-organize-logs.py` already use: stdlib-only, canary-tested, and run by the invoking agent rather than wired into CI.

This closes a named asymmetry: `plab-wrap-session` has run a pre-wrap hygiene sweep checking remote divergence and release state before writing a log since its own 1.5.0, and the read side had never run the equivalent check before acting on one.

Phases 3 through 5 of the prior workflow are renumbered 4 through 6 to make room; no other phase's content changed.

## 1.5.0 - 2026-09-15

**Changed: Phase 3 no longer dumps the continuation prompt.** It renders the prompt's immediate
action as ordinary markdown, gives the log path on one line, and prints the full prompt verbatim only
when the user asks for it.

The verbatim fenced block was the longest thing on screen and the least readable. Fenced, none of the
prompt's own markdown renders, so a reader gets `**bold**` and backtick noise as literal source for a
hundred lines or more.

**The rationale for verbatim display did not survive inspection.** It exists so a prompt can be pasted
into a **cold-start session that has not read the log**. Phase 3 is the opposite case by construction:
the skill has just read the entire log, so reprinting it carries no information the agent does not
already hold and none the user cannot `cat`. Verbatim stays available on request, because someone
resuming in a different tool still needs to copy it.

**Fixed: the display format had two sources of truth that disagreed.** `references/handoff-display.md`
specified a `### What's next (from last session)` section that the SKILL.md Phase 3 template omitted,
so an agent following SKILL.md silently dropped it. The template now carries it. Both files were
changed together, along with the Constraints line that independently mandated verbatim display; the
three had to move at once or the skill would contradict itself.

**Reported by the user**, who saw the raw markdown fill a terminal on a real resumption.

## 1.4.0 - 2026-08-25

**Added: capture-lite orientation.** On the no-log-found path and the stale-log path, when
`_local/_session-logs/_capture/` holds qualifying records, continue now surfaces one orientation line
before its existing message: branch, head, commits today and timestamp for the no-log case, or a
count of sessions since the stale log for the age-warning case. Silent when the directory is absent
or nothing qualifies.

The records already existed. A SessionEnd hook has been writing them with nothing reading them, which
is a producer with no consumer, the same defect class this plugin has shipped before.

**Added: `_superseded/` named in the discovery allowlist.** `plab-wrap-session` 1.6.0 can archive a
same-arc superseded log to `_local/_session-logs/_superseded/`. The existing one-level-deep allowlist
already excluded it, so this only documents the name. No pipeline change.

**Changed: Waiting-on items display oldest-blocked-first.** The handoff now sorts them by each item's
`(blocked since YYYY-MM-DD)` marker, so the longest-open obligation leads. The new `## Parked` section
is elided from the display like the other optional sections, rather than being left silently
undocumented.

## 1.3.0 - 2026-08-18

**Added: month-folder discovery.** The session-log store can now be archived into `YYYY-MM/`
subdirectories by `/plab-wrap-session --organize`. Discovery reads those folders and the flat top
level as one pooled corpus, so archiving never removes a log from resume.

Discovery is a date-shaped allowlist exactly one level deep, not a recursive walk. Only `YYYY-MM`
subdirectories are read, which keeps `_capture/` outside the corpus and preserves the mechanism that
any deliberately-hidden subdirectory depends on. The basename sort is unchanged, so ordering remains
provably independent of where a log is filed: an archived log with a newer filename still beats a hot
log with an older one.

**Changed: the empty-store message diagnoses version skew.** A store organized by a newer plugin than
the one installed reads as empty to older discovery. The message now checks for month folders before
reporting nothing found, and names `/plugin update` as the fix rather than offering to start fresh on
top of work sitting one directory down.

**Fixed: a stray Markdown file could be resumed from.** Discovery selected on `*.md` and took the
lexically last name, so a `README.md` or `notes.md` sitting in the store outranked every `2026-...`
log and would be resumed from as though it were the latest session. Both pipelines now match the
`YYYY-MM-DD_` date prefix. This was always latent; `--organize` makes it reachable by reporting
non-log Markdown as "left in place", which establishes that the store may legitimately hold it.

**Pairs with `plab-wrap-session` 1.5.0.** This reader change ships first by construction: both are in
plugin v0.2.0, so no install can archive logs it cannot then find.

## 1.2.1 - 2026-08-18

**Fixed: the body contradicted the description.** The When to Use list still named "where were we" and
"what were we doing" as triggers, eighteen lines below a description that explicitly refuses to fire on
status questions. The description is the router and the body is the program. Narrowing only the router
reduced the frequency of a mis-fire without removing it, because once the skill loaded, its own
instructions authorised the resumption ritual anyway. The list now names explicit resume intent only, and
When NOT to Use carries the status-question case as a named entry rather than leaving it implied.

**Erratum: 1.2.0 shipped a behaviour change undocumented.** Commit `38a75f0` (2026-08-17) rewrote this
skill's description, narrowing it to explicit resume intent and adding the do-not-fire clause. Transcript
evidence had shown every sampled invocation following a status question rather than a request to resume.
That change shipped inside plugin v0.1.1 with no version bump and no history entry, which means the 1.2.0
entry below, stating the skill was unchanged in behaviour from its last private version, was true when
written and false by the time v0.1.1 was tagged. This entry records the change retroactively rather than
amending the record.

The gap that allowed it sits on the writing side: `plab-wrap-session`'s pre-wrap hygiene sweep checks
documentation drift in one direction only, catching a version bump with a stale doc but not content
changed with no version bump. Closing that is scheduled, not shipped.

**Also corrected.** `docs/skills/plab-continue-session/README.md` still opened with the pre-narrowing
description, two rewrites stale, and pointed readers three times at `/jp-init-project`, which does not
ship in this plugin. Its Phase 2 field list had also not been updated for the Waiting on You and Hygiene
Sweep extraction that 1.2.0 added.

## 1.2.0 - 2026-08-14

First public release. The skill is unchanged in behaviour from its last private version; this entry records the move, not a feature change.

**Migration provenance.** 85 recorded invocations via the Skill tool and 8 typed slash invocations in Claude Code on the origin machine, as of 2026-08-14. Counts come from local transcripts on one machine and are bounded by local retention.

**Not carried over.** The prior HISTORY file is not reproduced here; it referenced private-repo layouts and skills that do not ship in this plugin.

**Pairing contract.** This skill reads what `/plab-wrap-session` writes. The two move and version together; a change to the session-log format in one requires a matching change in the other. Legacy locations (`_agent-context/session-log/`, `AGENTS/session-log/`) are still searched so projects on an older layout keep working.
