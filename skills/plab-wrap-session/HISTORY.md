# History - plab-wrap-session

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.8.1 | 2026-10-16 | unreleased | fixed | `scripts/check-log.py` collapses the whole Log Self-Check into one post-write call, `extract_waiting_on_you()` stops counting an indented sub-bullet as its own item, `frontmatter-schema.md` catches up with the two fields 1.8.0 added, and the hygiene sweep's own-validation-scripts step chains into one command. |
| 1.8.0 | 2026-10-15 | v0.8.0 | added | `derive-log-facts.py` derives frontmatter facts, the Evidence Gathering inputs, and the hygiene sweep's detection results from git and the environment, in place of model recall and one-at-a-time commands. |
| 1.7.0 | 2026-09-13 | v0.5.4 | added | Deep-mode logs carry an Uncertainty Ledger and a What You May Not Realize section. |
| 1.6.2 | 2026-08-28 | v0.5.2 | fixed | Path-citation gate: three false-positive classes removed, a line-anchor shape brought into scope, and the proof corpus grown from 11 entries to 40. |
| 1.6.1 | 2026-08-25 | v0.4.1 | fixed | Session-log body prose is not hard-wrapped. CI pin moved to the toolkit release that fixed the Action. |
| 1.6.0 | 2026-08-25 | v0.4.0 | fixed | Detector gates that could not fail open, plus the log-format and hygiene fixes batched with them. |
| 1.5.0 | 2026-08-18 | v0.2.0 | added | `--organize` files old logs into `YYYY-MM/` folders. Hygiene sweep gained Check 5. |
| 1.4.1 | 2026-08-18 | v0.1.2 | fixed | Dropped the "what did we do" trigger. Added `type:` to the frontmatter block and `machine:` to the Quick and Blocked templates. |
| 1.4.0 | 2026-08-14 | v0.1.0 | migrated | First release in prisant-utilities. Migrated from a private upstream at version 1.4.0; prior history remains there. |

## 1.8.1 - 2026-10-16

**Added: `scripts/check-log.py`, one post-write call for the whole Log Self-Check.** A clean 1.8.0 wrap still ran `derive-log-facts.py`, the repository's own validation scripts one at a time, the write, `--count-decisions`, and then `path-citation-check.py` and `dash-check.py` as two more separate calls, six to nine calls before any fix. `check-log.py` runs the two existing detector scripts exactly as they are, keeping their own canaries and three-state contracts, compares `decisions-count` against a mechanical count of the Decisions Made section by importing `derive-log-facts.py`'s own counting function rather than copying it, checks summary length, Tier 1 frontmatter completeness including `machine:`, every Waiting on You rule, and, in deep mode, that the Uncertainty Ledger and What You May Not Realize sections are present. A broken detector makes the whole result broken. `scripts/test-check-log.py` proves it against 36 fixture checks, including a canary removed and restored to confirm it actually fails when its rule is gone (quoted in this release's pull request, not restated here). `SKILL.md`'s Log Self-Check section now runs this one command after writing the log, rather than listing each gate as its own step before writing; `--count-decisions` keeps working directly for compatibility, but is no longer the step a wrap takes on its own.

**Fixed: `references/frontmatter-schema.md` never caught up with 1.8.0's two new fields.** `commit-range` and `latest-tag` joined Tier 1 in `SKILL.md`'s own frontmatter block when 1.8.0 shipped, but the schema reference, the one document meant to be the complete field-by-field specification, still listed only the original seven. Both fields are now documented in Tier 1, with the same non-collision note `derive-log-facts.py`'s docstring already carries.

**Fixed: the hygiene sweep's Check 3 ran the repository's own validation scripts one call per script.** `SKILL.md` now says to chain them into one shell command and read the combined output, the same step-reduction principle 1.8.0 already applied to Evidence Gathering and the other four checks.

**Fixed: a 1.8.0 carry-forward defect, an indented sub-bullet counted as its own Waiting on You item.** `extract_waiting_on_you()` matched any line whose stripped text started with `- `, so a top-level item's own indented sub-bullets, prose elaborating on what the item would do, were extracted as separate items. Found on a real log where one item, "Approve starting the layout effort", carried six such sub-bullets: the carry-forward handed all six to the next wrap as undated items, and `check-log.py` flagged each one for missing its `(blocked since YYYY-MM-DD)` marker. The fix requires a top-level list item, `-` or `*`, with no leading indentation, the same rule `count_decisions()` already applies to Decisions Made. `check-log.py`'s `normalize_waiting_item()` now strips a leading `* ` bullet the same way it already stripped `- `. Proven with a failing-then-passing fixture in both `test-derive-log-facts.py` (the carry-forward) and `test-check-log.py` (the gate).

**Fixed: `derive-log-facts.py --help` described `--base`'s default as "upstream, then latest tag, then none", which was the pre-1.8.0 D7 decision.** The shipped code tries the current session's transcript-derived start commit first (spec D7's revision, same day as the first build), and the help text had never been updated to say so.

## 1.8.0 - 2026-10-15

**Added: `scripts/derive-log-facts.py`, implementing W-02 (derive session-log facts from git instead of model recall).** The script replaces model-recalled transcription of `machine`, `repo`, `branch`, `date`, `files-changed`, commit range, and the latest tag with values read directly from git and the environment, under the new frontmatter fields `commit-range` and `latest-tag` (confirmed not to collide with the existing `commit-sha` and `tags` fields). `decisions-count` moves from a model estimate to a mechanical count of the drafted Decisions Made section's own entries, via the script's `--count-decisions` mode, run once that section exists.

**The same single invocation also returns what Evidence Gathering and the Pre-Wrap Hygiene Sweep used to gather one command at a time.** A 2026-10-01 measurement found a wrap's cost dominated by its number of assistant API calls rather than by the length of the log it writes, because each call re-reads the whole session; collapsing several one-at-a-time commands into one script call attacks that directly. The output carries the newest existing log's filename and its Waiting on You items verbatim with their original `(blocked since ...)` dates, any qualifying capture-lite record count, the gitignored-file inventory Evidence Gathering starts from, and the five hygiene checks' detection results (remote reconciliation, working-tree and worktree state, release and repo hygiene, documentation drift, and the session-log store). `references/hygiene-sweep.md` now points each check at the output field that carries it rather than restating the commands as the thing to run; the commands stay in that file as the recipe the field is a direct port of.

**Verification-relevant facts are derived only from a live transcript, never from capture-lite.** A `SessionEnd`-triggered capture-lite record describes a prior, already-closed session, and cannot describe the session still being wrapped. When `CLAUDE_CODE_SESSION_ID` and a matching transcript are both available, the script streams it line by line and surfaces which test, gate, and check commands ran this session and whether each one errored. When no record is available, the Verification section stays exactly as model-authored as it was before this version, and the script says so explicitly rather than reporting an empty success.

**The script's only write path is an explicit, non-pruning fetch.** By default it writes nothing at all; `--fetch` runs exactly `git fetch --no-prune origin --tags`. The explicit flag matters: a plain `git fetch` prunes whenever `fetch.prune` or a remote's own prune setting is configured, which is exactly what deleted a remote-tracking ref without confirmation on 2026-09-25. The sibling `test-derive-log-facts.py` proves both halves of that contract with canaries: a byte-for-byte hash of the fixture tree across a no-`--fetch` run, and a fixture clone with `fetch.prune=true` whose stale ref must survive `--fetch`, which was confirmed to fail when `--no-prune` is removed from the fetch call.

**Evidence Gathering, the Pre-Wrap Hygiene Sweep, and the Frontmatter block in `SKILL.md` are rewired to call the script and use its output**, replacing the manual per-field derivation prose they carried before. Summary, Decisions Made, Waiting on You, and the Continuation Prompt are untouched - the explicit point of this split is that judgment over those four sections remains agent work, while everything mechanically derivable moves to the script.

## 1.7.0 - 2026-09-13

**Added: two deep-mode sections that record what the log does not know.** Placed immediately after Verification Detail, so what was proven is followed at once by what was not.

**The Uncertainty Ledger merges two questions that are one list sorted two ways.** "What am I least confident about" sorts by confidence; "which assumption would change the outcome most if wrong" sorts by blast radius. They return different orderings of the same set, and the row that matters most sits exactly where the two orderings disagree: **high confidence and high blast radius**, an assumption comfortable enough that nobody thought to check it. Asked as two separate sections, those rows fall into the gap, because they do not feel uncertain and they do not read as remarkable. One table with both axes forces them into view, and they are marked `(!)`.

That failure mode is not hypothetical in this repository. C-1 (the discipline text was not loading), C-2 (fourteen pointers to a plugin the library does not ship with) and C-4 (v0.5.3 installed while the session loaded v0.5.2) were each held confidently, were each load-bearing, and were each wrong. Every one would have been a `(!)` row before it was found.

**What You May Not Realize is a separate section because its source is different, not because its items are.** It records the asymmetry between what a session saw, meaning every file read and every command output, and what the maintainer saw, meaning the conversation. **Every item must cite a source from that session.** An item with no source is speculation wearing the clothes of insight, and is dropped rather than softened into a hedge. That single rule is what separates the section from a horoscope, and it is the reason it earns its always-on cost.

**Both sections are uncapped, deliberately, and the decision is recorded rather than assumed.** A three-item cap was proposed and declined: there is no evidence yet about how long either runs in practice, and pre-constraining an unmeasured thing is the opposite of the pruning rule this portfolio already follows, which is to remove what went unconsulted after two or three real uses. Revisit once there is a run of logs to measure.

**Both follow the repository's fail-open rule.** "Nothing material." and "Nothing surfaced." must be written explicitly. An empty section and a skipped section are indistinguishable to a reader, which is the omission every detector here exists to close. Two Log Self-Check items enforce presence and the source rule.

Deep mode only. Quick, final and blocked are unchanged.

## 1.6.2 - 2026-08-28

**Fixed: three false-positive classes in the path-citation gate.** The gate fired on things that make no claim about where a file lives, and a gate that cries wolf trains you to skim its output, which is how a real finding gets missed. All three were confirmed by reproduction before being fixed, not taken on report.

A leading dot was stripped from bare tokens, so `.github/workflows/gate.yml` was evaluated as `github/workflows/gate.yml` and could never resolve. The backticked form of the same path was unaffected, which is what localized the bug. A trailing possessive survived the punctuation strip, because the `s` in `check-dashes.py's` blocked the apostrophe from coming off. And a version-numbered branch name such as `fix/v0.4.3-marketplace-rename` read as a path claim, because the check for "does this basename have a file extension" was a test for a dot, and a version number supplies one. The dot-free branch names in the same list always passed, which is the control that proves the fix had to target the version shape specifically rather than anything containing a slash.

**Fixed: line-anchored citations are in scope again.** The narrowing above initially removed `path/file.md:42` from checking altogether, because `md:42` is not extension-shaped. That was a regression: a citation to a file that does not exist stopped being reported. A trailing `:42` or `:42-50` anchor is now stripped before the path-claim decision and before resolution, which is strictly better than either earlier behavior: the missing file is caught again, and `AGENTS.md:42` on a file that does exist no longer produces a false positive the way it used to. A possessive stacked on an anchor is handled by running both strips to a fixed point.

**The proof corpus grew from 11 entries to 40**, from 1 canary and 10 anti-canaries to 12 and 28. Every rule the fixes introduced is paired with a canary proving the citation is still in scope and an anti-canary proving the false positive is gone. That pairing is the point: an anti-canary alone can be satisfied by accidentally excluding a whole shape from checking, which is precisely how the line-anchor blind spot was created in the first place. Each new canary was verified to fail when the rule it guards is removed.

Read against a real session log, the gate now reports 9 findings where it reported 13, and all 9 are genuine.

## 1.6.1 - 2026-08-25

**Fixed: body prose is not hard-wrapped.** Nothing ever told the skill to wrap, and it drifted into
doing so anyway: logs written a week apart went from 800-character paragraphs to a hard wrap near 100
columns, with no rule anywhere in the skill, the template, or the repository asking for it.

Hard wrapping is right for source that gets diffed line by line and wrong for a document that gets
read rendered. It costs three things here. Editing one sentence reflows the paragraph, so a diff
shows paragraph-sized churn instead of the changed line. The continuation prompt arrives ragged when
pasted into a chat box, which is exactly how it is meant to be used. And a grep for any phrase longer
than the wrap width silently fails, which breaks the one operation a session log exists to support.

The rule is stated once and is deliberately not a Log Self-Check gate: nothing can mechanically
distinguish a wrapped line from a short sentence, so such a gate would either flag ordinary prose or
pass everything. Adding a check that cannot do what it claims would contradict the release this
skill just shipped in.

## 1.6.0 - 2026-08-25

**Fixed: the path-existence gate stopped flagging prose.** The Log Self-Check gate "Every file path
and link named in the log exists" resolved any citation as if it were a repo-relative path. In the
2026-08-23 10:27 wrap it flagged 7 of 21 citations and 6 of the 7 were false positives: bare
filenames and document titles mentioned in running prose, not claims about where a file lives.

The gate now tests what a citation actually asserts. A citation containing a path separator is a
location claim and must exist as written. A backtick-wrapped citation with no separator is resolved
against the repo root and passes silently when it does not resolve, because naming a file is not the
same as saying where it is. A bare word with a file extension and neither signal is prose and is not
evaluated at all.

A gate that cries wolf six times out of seven trains its reader to skim the output, which is how the
one real finding in that wrap nearly went unread.

**Added: both detector gates became canary-verified scripts.** The dash gate and the path-citation
gate now run `scripts/dash-check.py` and `scripts/path-citation-check.py`. Each proves its detector
against a canary corpus before scanning anything and reports clean, findings, or broken. Broken
blocks the log exactly as findings does, because a check that cannot prove it still works is not a
passing check.

This exists because the same failure happened three times in one week: a dash sweep written as a
shell escape that expanded to a literal string, a replacement sweep in Perl that read undecoded bytes
and could never match, and a path gate that produced six false positives out of seven. All three
reported success. A two-state gate cannot tell "found nothing" from "never ran".

Mechanizing the path rule also revealed that it was under-specified. Applied literally to a real log
it produced 13 flags, 11 of them false, against the pre-D-12 gate's 7 and 6: separators appear in
slash commands, repository slugs, git refs, globs, template placeholders and URLs, none of which
claim where a file lives. The script excludes all six mechanically and lands at 4 flags. See the
D-12 spec's Revisions entry for the superseded criterion.

**Fixed: hygiene Check 4 now looks both ways.** It caught a version bumped with a stale usage doc,
but not the inverse: content changed with no version bump. The inverse is the one that actually
shipped in this repository. Check 4 gained a recipe that walks every skill directory with a diff
since the last tag and reports two findings: a `metadata.version` identical to the tagged one, and a
`HISTORY.md` with no entry for the version currently shipping. A skill with no diff, or one that did
not exist at the tag, is skipped silently rather than reported.

The recipe proved itself during its own implementation. Run against this working tree it reported
`plab-wrap-session changed since v0.3.0 but metadata.version is still 1.5.0`, which was true at that
moment and is what the bump in this entry resolves.

**Fixed: `resumed-from` semantics.** The field now means "consumed via an in-session
`/plab-continue-session` resume", stated once in `references/frontmatter-schema.md` and mirrored in
the frontmatter comment. It is never back-filled from narrative memory, and is omitted, not guessed,
when no resume occurred. Both real logs in this repository previously carried a value pointing at an
unresolvable cross-repo filename because the field had been back-filled. No repo qualifier was added,
since continue already refuses cross-repo resumption, which makes a bare filename always resolvable.

**Added: capture-lite consumption, wrap side.** In deep and final modes, when
`_local/_session-logs/_capture/` holds `.jsonl` records newer than the last existing log, Outstanding
Issues now states how many sessions since then were never wrapped, with the earliest-to-latest head.
Records with a null `session_id` are skipped. Silent when the directory is absent or nothing
qualifies. No new script: the hook that writes these records lives outside this repository, under the
user's home directory, and was already producing them with nothing reading them.

**Added: same-arc log supersession.** When the newest existing log covers the same arc as the session
being wrapped, the new log declares the supersession in Summary and proposes archiving the older file
to `_local/_session-logs/_superseded/` under per-action confirmation. This closes the gap that let two
real logs five hours apart cover the same work with nothing noticing.

No `supersedes:` frontmatter field was added. It would have had zero consumers today, which is the
same producer-with-no-consumer shape that capture-lite was already in. The declaration lives in prose,
where a reader actually encounters it.

**Fixed: Waiting on You is an enforced contract again.** The section had diluted into a suggestion
list. One real log carried five items, four prefixed "Optional:", with a genuine blocker open since
July camouflaged among them, and the log passed every Log Self-Check gate.

Only items actually blocked on the maintainer belong there now, each carrying a
`(blocked since YYYY-MM-DD)` marker. Two new gates make the observed failure mechanically rejectable:
no item may begin with "Optional", and every item must carry the marker. Optional context moved to a
new Parked section in the template, which exists so demoted items have a named destination rather
than being deleted.

A carry-forward step reads the previous log's Waiting on You section and brings unresolved items
forward with their original dates, never today's, so a blocker's age survives across wraps instead of
resetting every session. That age is what made the July item visible once it was finally displayed.

## 1.5.0 - 2026-08-18

**Added: `--organize`.** A flat session-log store grows without bound. `--organize` files logs older
than the current and previous month into `YYYY-MM/` subdirectories, driven by
`scripts/organize-logs.py`: dry run by default, idempotent, move-only, never deleting. The month
comes from the filename prefix rather than mtime, because mtime is wrong after any copy or restore
and the filename is the log's identity. Collisions skip the file and exit non-zero rather than
overwriting. It runs instead of a wrap, so no log is written and no sweep fires.

**Added: hygiene sweep Check 5.** Deep and final wraps now report how many logs could be filed and
offer to file them under the existing per-action confirmation protocol. The sweep's read-only
detection phase is exactly the script's dry run, so one code path serves both and the check cannot
drift from the operation it proposes.

**Added: cite session logs by filename, never by path.** A directory-qualified reference to another
log breaks the moment that log is archived. The filename is stable identity, so a move needs no
rewrite step and therefore has no rewrite bugs. `resumed-from:` already worked this way; the rule now
covers prose references too.

**The write path is unchanged.** New logs are still written flat to
`_local/_session-logs/YYYY-MM-DD_HH-MM_<llm>_<title>.md`. Archiving is a separate, confirmed
operation, and nothing that documents the write path needed to change.

**Requires `plab-continue-session` 1.3.0.** The reader must understand month folders before anything
is filed into one, or the first archival makes the store read as empty. Both ship in plugin v0.2.0.

## 1.4.1 - 2026-08-18

**Fixed: a status question was listed as a trigger.** The description fired on "what did we do", which is
a request for an answer, not a request to write a session log. This is the same over-trigger class that
`/plab-continue-session` narrowed out of its own description on 2026-08-17, so the lesson had been applied
to one half of the pair and not the other. The phrase is removed and nothing replaces it: "wrap up",
"wrap session", "end of session", "session log", "close out", and "document this session" carry the load.
The description gets shorter, so always-on context cost falls rather than rising.

Usage documentation carried the same contradiction more starkly, listing "what did we do" as a trigger at
line 46 and "what have we done so far?" as an anti-trigger at line 50. Both now agree.

**Fixed: the skill failed its own gate.** The Log Self-Check requires Tier 1 frontmatter complete in every
mode, and `references/frontmatter-schema.md` places both `type` and `machine` in Tier 1. The Quick and
Blocked templates in `references/session-log-template.md` omitted `machine:`, so an agent following either
one produced a log this skill rejects. The frontmatter block in SKILL.md omitted `type:`, which the schema
and the Final Mode template both carry. Four lines added. The schema was correct throughout; the other two
surfaces had drifted from it.

**Not changed.** The description still fires on the bare phrase "session log", which is arguably the same
over-trigger class: a mention of a session log is not a request to write one. There is no misfire evidence
for it in transcripts, so it stays and gets watched rather than guessed at.

## 1.4.0 - 2026-08-14

First public release. The skill is unchanged in behaviour from its last private version; this entry records the move, not a feature change.

**Migration provenance.** 158 recorded invocations via the Skill tool and 20 typed slash invocations in Claude Code, plus 86 Codex sessions referencing the skill, on the origin machine as of 2026-08-14. Counts come from local transcripts on one machine and are bounded by local retention. Claude Code stores no per-skill counter, so this snapshot is the only surviving record of pre-migration usage.

**Not carried over.** The prior HISTORY file is not reproduced here. It documented an internal path migration across three private-repo layouts and referenced skills that do not ship in this plugin.

**Renamed references.** `/plab-continue-session` is the read-side companion. Legacy session-log locations (`_agent-context/session-log/`, `AGENTS/session-log/`) are still recognised for backward compatibility; only the writing skill's name changed.
