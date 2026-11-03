# Session Log Template

Adapt section depth to the selected mode. Remove instructional comments before delivery.

Body prose is not hard-wrapped: one paragraph is one line. See `SKILL.md`'s Session Log Output section for why.

---

## Final Mode

```markdown
---
date:
type: session-log
machine: # hostname
repo:
branch:
summary: # ≤ 120 chars
files-changed: []
session-type:
model: # full model name, e.g. "claude opus 4.6"
model-settings: # e.g. "extended-thinking max"
agent:
status:
decisions-count:
skills-used: []
resumed-from: # log filename if this session resumed from one. Filename only, never a path: archiving moves logs into YYYY-MM/ folders. Same rule for every log reference in the body.
---

# Session: [Brief Title]

## Summary

<!-- 2-4 sentences. What happened and why it matters. -->

## Work Completed

<!-- Bulleted list of accomplishments. Be specific. -->

## Decisions Made

<!-- Scale verbosity to significance:
  Minor: one-liner
  Significant: 2-3 sentences with reasoning
  Architectural: full alternatives analysis + ADR reference (e.g., "See ADR-0008")
  If an ADR was created, reference it: "Created docs/decisions/0008-title.md" -->

## Files Changed

<!-- From git. Group by purpose if many. -->

## Gitignored Outputs

<!-- Work products git cannot see: path + one-liner each
  (e.g. _local/audit/..., _local/reference/...). Omit only if none. -->

## Verification

<!-- Checklist format:
  - [x] Tests passing for X
  - [x] Manual check: Y works as expected
  - [ ] Not verified: Z (reason)
-->

## Outstanding Issues

<!-- Blockers, risks, unfinished work. If none, omit section. -->

## Hygiene Sweep

<!-- Findings from the sweep (see references/hygiene-sweep.md): state found,
  then one line per auto action, then one line per numbered proposal, written
  before the question is asked and amended after the answer:
  - auto: merged-branch. `git branch -d feat/x` -> Deleted branch feat/x (was 1a2b3c4).
  - **H1** Push 2 unpushed commits on `main` to `origin/main`. Status: unanswered
  The status becomes done or failed with the result, or declined.
  Include the skip note if checks were skipped. -->

## Waiting on You

<!-- REQUIRED in every mode. Only items blocked on the maintainer's decision or
  action belong here: what is awaited, why it blocks, a (blocked since YYYY-MM-DD)
  marker, and links to relevant files. Optional or nice-to-have items go in the
  Parked list below, never here.
  Write "Nothing pending." explicitly when empty; never omit this section.
  Mirror the list inside the continuation prompt. -->

## Parked

<!-- Optional or nice-to-have context that does not meet the Waiting on You bar:
  smoke tests never run, cosmetic cleanups, ideas worth remembering but nobody
  is blocked on. One bullet each. Omit the section entirely when there is
  nothing to park. -->

## What's Next

<!-- Ordered list. Most important action first.
  When one decision unlocks the rest, name it as the single unlocking decision. -->

1.
2.
3.

## Continuation Prompt

```text
[Copy-paste-ready prompt for the next session.
Must include: task context, current state, immediate next action,
key constraints, relevant file paths, branch name.]
```
```

---

## Quick Mode

```markdown
---
date:
type: session-log
machine: # hostname
repo:
branch:
summary:
files-changed: []
session-type:
model:
model-settings:
status: completed
---

# Session: [Brief Title]

[1-3 sentence summary of what happened.]

## Waiting on You

[One bullet per item blocked on the maintainer, each with a (blocked since YYYY-MM-DD) marker and file links, or "Nothing pending." Optional items do not belong here.]

## Continuation Prompt

```text
[Copy-paste-ready prompt, or "No continuation needed."]
```
```

---

## Blocked Mode

```markdown
---
date:
type: session-log
machine: # hostname
repo:
branch:
summary:
files-changed: []
session-type:
model:
model-settings:
status: blocked
---

# Session: [Brief Title]

## Summary

[What was attempted and why it's blocked.]

## Blocker

**What:** [Description of the blocker]
**Who can unblock:** [Person or action needed]
**Impact:** [What can't proceed until this is resolved]

## Waiting on You

[One bullet per item blocked on the maintainer, each with a (blocked since YYYY-MM-DD) marker and file links; the blocker itself belongs here when the maintainer is the unblocker.]

## Continuation Prompt

```text
[What to do when the blocker is resolved.
Include: how to verify the blocker is cleared,
then the next action to take.]
```
```

---

## Deep Mode (Default)

The default mode for every wrap since v1.3.0. Use the full Final Mode template, plus:

```markdown
## Evidence Index

<!-- Link to specific evidence for key claims:
  - "Tests pass" → link to test output or commit
  - "Performance improved" → link to benchmark
  - "Design reviewed" → link to review document
  Workflow runs, one row each when the session used multi-agent workflows:
  - run ID, agent count, token total, journal/transcript path -->

## Verification Detail

<!-- Expanded verification with method and result:
  | Check | Method | Result | Notes |
  |-------|--------|--------|-------|
  | Unit tests | `npm test` | 47/47 pass | - |
  | Manual smoke test | Opened app, tested flow | Works | Edge case X not tested |
-->

## Uncertainty Ledger

<!-- Placed immediately after Verification Detail on purpose: what was proven, followed
  at once by what was not. Deep mode only.

  This merges two questions that are one list sorted two ways - "what am I least confident
  about" sorts by confidence, "which assumption would change the outcome most if wrong"
  sorts by blast radius. The row that matters most is HIGH confidence AND HIGH blast
  radius: an assumption comfortable enough that nobody thought to check it. Asked as two
  separate sections, those rows fall into the gap between them, because they do not feel
  uncertain and they do not read as remarkable.

  RULES
  - Sort by blast radius descending, never by confidence.
  - No cap on row count. Uncapped deliberately as of 1.7.0; revisit once there is
    evidence about how long the table actually runs, per the pruning rule of removing
    what was never consulted rather than pre-constraining what has never been measured.
  - Confidence and blast radius are High / Medium / Low. Never a percentage: false
    precision is worse than a band.
  - Every row names what would settle it. An uncertainty with no route to resolution is
    anxiety, not a finding.
  - Mark any row that is High confidence AND High blast radius with (!) in the # column.
    That is the dangerous cell and it is why the two questions were merged.

  | # | Claim or assumption | Confidence | Blast radius | Verified? | What would settle it |
  |---|---|---|---|---|---|
  | 1 (!) | The runtime contract from three weeks ago still holds | High | High | code-read only | Run the canary against the live binary |
  | 2 | The gate covers this document type | Medium | High | no | `python scripts/frontmatter-check.py` with such a file present |
  | 3 | The reviewer's findings parse as expected | Low | Low | no | One dispatched review, end to end |

  Write "Nothing material." explicitly when the table would be empty; never omit the
  section. An empty section and a skipped section are indistinguishable to a reader,
  which is the fail-open-by-omission every detector in this repository exists to close. -->

## What You May Not Realize

<!-- Deep mode only. Structurally different from the ledger above and therefore a separate
  section rather than more rows: it is not about the work, it is about the ASYMMETRY
  between what this session saw - every file read, every command output, every document
  opened - and what the maintainer saw, which is the conversation.

  RULES
  - EVERY item cites a source from this session: a file path and line, a command and its
    output, a corpus document, a verified API response. An item with no source is
    speculation wearing the clothes of insight; drop it rather than soften it. This rule
    is the whole reason the section is worth having.
  - No cap on item count, same revisit trigger as the ledger.
  - Each item carries a confidence marker.
  - Do not repeat a ledger row here. If it belongs in the table, it is not an asymmetry.

  - **High** - The corpus already specifies the thing being re-derived. Source:
    `_local/toolchain/10_...md` section 7.5, read this session.
  - **Medium** - The label taxonomy contradicts a field discovered later. Source: the
    org field listing returned by the GraphQL query quoted above.

  Write "Nothing surfaced." explicitly when there is nothing; never omit the section. -->
```
