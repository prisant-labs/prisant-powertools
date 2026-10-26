---
id: D-12
title: Narrow the path-existence gate to real path citations
type: spec
status: fulfilled
created: 2026-08-23
updated: 2026-08-24
linked-effort: the maintainer's private defect record for the wrap/continue pair, 2026-08-18
linked-plan: implementation-plan.md
ac-count: 6
source-count: 4
requires-human-review: true
target-release: v0.4.0
linked-release: docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/plan.md
priority: P2
---

# Spec: Narrow the path-existence gate to real path citations

## Task Summary

**Status:** Fulfilled
**Last updated:** 2026-08-24
**Linked plan:** implementation-plan.md
**Open questions:** 1 open, see Open Questions / Decisions
**Revisions:** Initial draft

### Acceptance Criteria Fulfillment

- [x] AC-1: ~~A citation containing a path separator is checked for existence and flagged when missing~~ (SUPERSEDED 2026-08-25 by AC-6; see Revisions)
- [x] AC-6: A citation containing a path separator is checked for existence and flagged when missing, except where it carries a URI scheme, a drive-letter absolute prefix, a glob character, a template placeholder, a single leading slash segment, or no file extension on its final component
- [x] AC-2: A backtick-wrapped citation with no separator is tested against the repo root; non-resolution is not reported as a finding
- [x] AC-3: A bare word with a file extension, carrying neither signal, is not evaluated at all
- [x] AC-4: The scoping rule is stated as an explicit test in the SKILL.md gate line itself
- [x] AC-5: A genuine missing path-separator citation is still flagged after the narrowing

### Currently In Progress

None.

## Purpose

The wrap skill's Log Self-Check gate "Every file path and link named in the log exists"
(`skills/plab-wrap-session/SKILL.md:194`) resolves any citation as if it were a repo-relative path. In
the 2026-08-23 10:27 wrap it flagged 7 of 21 citations, and 6 of the 7 were bare filenames or document
titles mentioned in prose, not path claims. This effort narrows the gate's subject to citations that
actually assert a location, so the check stops crying wolf while still catching the one genuine defect
class it exists for. D-12 is the roadmap's own numbering already; both digits are needed regardless of
padding, so no zero-padding transformation applies here (unlike D-1 through D-9 elsewhere in this
release).

This effort touches the same SKILL.md section as D-11 (three-state gate canaries) [S1], see the coupling
note in Requirements below: this effort's rule change must land before D-11 wraps the same gate in
canary-verified three-state reporting.

## Scope

### In Scope

- The subject-matching rule for the path-existence Log Self-Check gate: which citations in a drafted
  session log are evaluated for existence.
- The wording of the SKILL.md gate bullet that states that rule.

### Non-Goals

- Does not touch the em-dash or en-dash gate bullet (`SKILL.md:195`). That bullet, and the canary
  mechanism generally, belong to D-11 (three-state gate canaries).
- Does not add canary self-verification to this gate. This effort narrows *what* is checked; D-11 adds
  *proof the checker still works* on top of the narrowed rule.
- Does not change `plab-continue-session`. The Log Self-Check gate is wrap-only; nothing here touches
  the session-log format continue parses.
- Does not attempt a recursive or fuzzy search for a bare filename's true location elsewhere in the
  repo tree. A citation with no path separator that fails to resolve at the repo root is excluded from
  the check, not chased down.
- Does not change `references/frontmatter-schema.md`'s existing "cite session logs by filename only"
  convention. That convention already produces separator-free citations, which this rule already
  excludes; the two are compatible without an edit.

## Users / Actors

| Actor | Role | Interaction |
|---|---|---|
| Maintainer | Sole user of the wrap skill; reads Log Self-Check output as a trust signal | Decides whether a flagged citation is worth investigating, based on how often flags turn out to be real |
| Wrapping agent | Runs the Log Self-Check gate before writing a session log | Applies the narrowed rule to decide which citations get an existence check |

## Requirements

1. The gate evaluates a citation for existence when it contains a path separator (`/` or `\`),
   regardless of backtick-wrapping. [S1]
2. The gate also evaluates a backtick-wrapped citation with no path separator by attempting to resolve
   it against the repo root; if that resolution fails, the gate does not report a finding for it. This
   is the specific reading adopted for the source phrase "wrapped in backticks and resolve against the
   repo root are subject to existence checking" [S1], recorded as [model-inference] because the source
   sentence is compatible with more than one operational reading; see Open Questions.
3. A bare word carrying a file extension, with neither a path separator nor backtick-wrapping, is not a
   path claim and is excluded from evaluation entirely. [S1]
4. The rule is stated as an explicit, unambiguous test in the SKILL.md gate line itself, not left to
   agent judgment at check time, because agent-judgment resolution is what produced the six false
   positives in the 2026-08-23 10:27 wrap. [S1]
5. This effort lands before D-11 (three-state gate canaries). D-11's canary suite for this same gate
   needs a known-not-flagged example shaped like a bare, separator-free citation; authoring that canary
   against the pre-narrowing (unfixed) gate would encode the false-positive behavior D-12 removes, and
   the canary would need rewriting the moment D-12 landed anyway. Landing D-12 first means D-11's canary
   is authored once, against final behavior. [model-inference: the source document states both defects
   independently and does not itself sequence them; this ordering is derived by combining D-11's own
   canary-plus-anti-canary precedent (`pii-gate.py`) with D-12's mechanism, not stated verbatim in
   either roadmap entry.]

## Acceptance Criteria

**AC-1:** Given a drafted log citation containing a path separator, when the Log Self-Check path gate
runs, then the citation is checked for existence and flagged if the path does not exist in the repo.
[S1]

**AC-2:** Given a drafted log citation wrapped in backticks with no path separator, when the gate
resolves it against the repo root, then a successful resolution produces no finding and a failed
resolution also produces no finding (the gate never reports "missing" for a separator-free citation).
[S1][model-inference]

**AC-3:** Given a drafted log citation that is a bare word carrying a file extension, with no path
separator and no backtick-wrapping, when the gate runs, then the citation is not evaluated at all (it
does not appear in the gate's input set). [S1]

**AC-4:** Given the SKILL.md Log Self-Check section, when a reader looks at the path-existence gate
bullet, then the bullet states the separator-or-backtick-resolves rule as an explicit test rather than
generic language like "exists," so two different readers applying it to the same citation reach the
same in-scope decision. [S1]

**AC-5:** Given a drafted log citation shaped like `scripts/em-dash-sweep.sh` (path separator present,
file does not exist in the repository), when the gate runs after this effort lands, then the citation is
still flagged as missing. [S1][S2]

## Behavior / Examples

Worked examples, drawn from citations that actually appear in the 2026-08-23 10:27 wrap log
(the session log of 2026-08-23 10:27, maintainer-local),
illustrating the shape of the defect and the fix rather than reproducing that wrap's exact flagged list.

**Example 1: genuine finding, preserved.**
Given: the log line 52 citation `scripts/em-dash-sweep.sh` (contains a path separator).
When: the gate runs.
Then: `skills/plab-guide/scripts/em-dash-sweep.sh` does not exist in the repository (verified: the
`scripts/` directory under `plab-guide` does not contain this file), so the citation is flagged.
[S2][S3]

**Example 2: false positive, eliminated.**
Given: the log line 119 citation `` `test-organize-logs.py` `` (backtick-wrapped, no path separator,
appears as a results-table label: "`test-organize-logs.py` | 34 of 34").
When: the gate runs.
Then: resolving `test-organize-logs.py` against the repo root finds nothing (the real file is
`skills/plab-wrap-session/scripts/test-organize-logs.py`, not a repo-root file), but per Requirement 2
this produces no finding. Before this effort, the same citation was one of the false-positive shapes
the gate could flag. [S1][S3]

**Example 3: backtick-wrapped bare name that happens to resolve.**
Given: the log line 97 citation `` `README.md` `` (backtick-wrapped, no path separator).
When: the gate runs.
Then: `README.md` exists at the repo root, so resolution succeeds and no finding is produced (same
observable outcome as Example 2, silence, but for a different reason: this one resolves and passes,
Example 2 does not resolve and is excluded). [S3]

**Example 4: bare word with no backticks at all.**
Given: a citation like "the source-of-truth ruling" or a bare mention of a script name with no
backtick-wrapping and no separator.
When: the gate runs.
Then: the citation is never in the gate's input set (Requirement 3); it is not a borderline pass, it is
never considered. [S1]

## Non-Functional Requirements

| Category | Requirement | Source |
|---|---|---|
| Precision | False-positive rate on a repeat of the observed 21-citation, 7-flag sample drops from 6-in-7 to the single genuine finding | [S1] |
| Non-regression | Every citation that was a genuine finding before this effort (path separator present, does not exist) remains a finding after | [S1] |
| Token cost | The change is a rewrite of one existing bullet line in SKILL.md body text, not the frontmatter description; zero always-on session cost since body text loads only when the skill is invoked | design frame, conventions section 3 |

## Revisions

| Date | Change |
|---|---|
| 2026-08-23 | Initial draft created |
| 2026-08-25 | AC-1 superseded by AC-6. Mechanizing AC-1 in D-11 measured 13 flags / 11 false on a real log, against the pre-D-12 gate's 7 / 6. "Contains a path separator" holds as prose because a reader applies judgment; a script has none. AC-6 adds the mechanical exclusions. Maintainer decision 2026-08-25. |

## Sources & Evidence

- **[S1]** the maintainer's private defect record for the wrap/continue pair, 2026-08-18, "D-12. The path-existence gate treats bare
  filenames as repo-relative paths" (lines 211-222). Maintainer-local, gitignored. Credibility A: primary
  planning artifact, evidence drawn directly from an actual wrap run and independently reviewed by a
  second model per the document's own methodology note.
- **[S2]** `skills/plab-wrap-session/SKILL.md:194`, the current gate bullet text ("Every file path and
  link named in the log exists"). Credibility A: shipped skill file, verified by direct read.
- **[S3]** the session log of 2026-08-23 10:27, lines 52,
  97, and 119. Maintainer-local, gitignored. Credibility A: the actual session log this effort's evidence
  is drawn from, verified by direct read; the specific citations quoted in Behavior/Examples were
  confirmed to exist at those line numbers and their real repo locations were confirmed with `find`.
- **[S4]** `skills/plab-wrap-session/references/frontmatter-schema.md:98-107`, "Citing another session
  log" (session logs are cited by filename only, never by directory-qualified path). Credibility A:
  shipped reference file, verified by direct read; cited to support the Non-Goals claim that this rule
  does not conflict with the existing session-log citation convention.

### Unverified Claims

- **Requirement 2 / AC-2** ([model-inference]): the source sentence "wrapped in backticks and resolve
  against the repo root are subject to existence checking" is read here as: resolution success means
  silent pass, resolution failure means silent exclusion (never a "missing" finding for a separator-free
  citation). An equally plausible alternative reading would drop this branch entirely, since it can never
  produce an observable finding either way, leaving "contains a path separator" as the sole scoping test.
  Both readings produce identical externally-observable gate behavior in every example checked in this
  spec. Flagged for the maintainer to confirm the branch is worth implementing as literal logic (matching
  the source text closely) versus simplified away (fewer lines, same behavior). See Open Questions.
- **Requirement 5** ([model-inference]): the "D-12 before D-11" sequencing is this author's inference,
  not a statement in either roadmap entry. Reasoning is given in Requirement 5 and repeated more fully in
  the D-11 spec's Open Questions. Flagged for the maintainer to confirm before either effort is promoted
  to `committed`.

## Open Questions / Decisions

| ID | Title | Resolution | Status | Updated |
|---|---|---|---|---|
| D1 | Implement the backtick-resolves branch literally, or simplify to separator-only | Option A: both branches implemented | Decided | 2026-10-26 |

### D1: Implement the backtick-resolves branch literally, or simplify to separator-only (Decided)

**Summary.** Requirement 2 describes a scoping branch for backtick-wrapped, separator-free citations
that, by construction, can never produce a "missing" finding (a resolution failure is excluded, not
flagged). Implementing it costs a few lines and changes no observable behavior versus dropping it.

**Context.** The source mechanism [S1] states the rule with two branches ("contains a path separator, or
... wrapped in backticks and resolve against the repo root"). A literal implementation keeps faith with
the source text. A simplified implementation (drop the second branch, use only "has a separator" as the
scoping test) produces the same pass/fail outcomes on every example in this spec, because the second
branch's failure case is defined to be silent.

**Desired outcome.** Whichever the implementation plan encodes, the maintainer has confirmed it is the
intended reading rather than an unreviewed inference.

**Options / approaches.**

- **Option A:** Implement both branches as described in Requirement 2. Matches the source text most
  closely; a few extra lines in the checker script with no behavioral payoff beyond documentation value.
- **Option B:** Simplify to "has a path separator" as the sole scoping test. Fewer lines, identical
  observable behavior on every example examined here, but departs from the source document's literal
  wording.

**Recommendation.** Option A, for this draft: implement both branches literally in
`implementation-plan.md`, because "do not redesign it" argues for keeping the stated mechanism even where
one branch is currently degenerate. Revisit as Option B if, once implemented, the second branch proves to
add real maintenance cost for zero behavioral value.

---

> **Maintainer decision:** Decided 2026-10-26 by JP
>
> * **Status:** Decided
> * **Choice:** Option A, both branches as written.
> * **Reasoning:** The working default shipped and still holds. `skills/plab-wrap-session/scripts/path-citation-check.py` implements both scoping branches: a token with a path separator, and a backtick-wrapped token with no separator, resolved against the repository root.
> * **Follow-up:** None needed.
> * **Decided by / date:** JP / 2026-10-26, approving a batch of closures after a read-only check on 2026-10-25 confirmed that the working default shipped and still holds.
