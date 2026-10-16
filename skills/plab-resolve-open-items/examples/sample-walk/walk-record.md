---
type: walk-record
date: 2026-10-07
repo: prisant-labs/prisant-utilities
rounds: 3
handle: jp
handle-source: git config user.name (this walk predates the skill and its write-back automation)
---

# Walk record: designing plab-resolve-open-items

The first walk of this skill's design, run by hand on 2026-10-06 and 2026-10-07 before the skill existed, rewritten into the format of `references/walk-record.md`. It is the committed sample that CI checks with `scripts/walk-check.py record`. The hand-written original kept each reply per item rather than as whole reply lines, so the rounds below quote the replies item by item.

Under this skill's rules, two answers read differently from the hand record: "A i guess" (D6) and D4's stated doubt are `provisional`. The hand record called both decided.

## Items, answers, and where each landed

| Walk ID | Home | Answer | State | Round | Follow-up | Landed |
|---|---|---|---|---|---|---|
| D1 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D1 | "resolve-open seems even more succinct? 'items' doesn't really add much value does it?", then chose `plab-resolve-open-items` | decided | 3 | Rename the effort folder and the spec title; tracked in the WD-01 spec | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D2 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D2 | "C, but record these other options in a backlog for this skill" | decided | 2 | Add a Backlog section to the WD-01 spec holding options A and B | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D3 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D3 | "A. Are there other types than Q and D?" | decided | 1 | None needed; the question back became D11 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D4 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D4 | "A. However this feels a little incomplete and unsettled and I can't articulate why" | provisional | 1 | Propose answer rules that would settle the doubt, as D10 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D5 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D5 | "outcome is tracked, the conversation local is a good rule of thumb", choosing A | decided | 2 | Move the four layout questions to a separate layout effort | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D6 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D6 | "A i guess" | provisional | 1 | Keep option B in the spec's Backlog until the Decision issue type is tested | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D7 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D7 | "A" | decided | 1 | Write the do-NOT-fire clauses into the skill's description | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D8 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md D8 | Round 1: "I don't understand this". Round 3: deferred to the backlog mode | deferred | 3 | Revisit when the --backlog mode is specified | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md (three surfaces); the design brief (pointer) |
| D9 | none (merge PR #20) | "A" | decided | 1 | None needed | walk record only |
| D10 | none (answer rules, raised by D4) | "I don't quite know what to do with D10-13?" | unanswered | - | - | not written: parked in the WD-01 spec for a later walk |
| D11 | none (a T series, raised by D3) | "I don't quite know what to do with D10-13?" | unanswered | - | - | not written: parked in the WD-01 spec for a later walk |
| D12 | none (an architecture decision record for decision 21) | "I don't quite know what to do with D10-13?" | unanswered | - | - | not written: first item of the layout effort |
| D13 | none (a strategy brief on autonomy) | "I don't quite know what to do with D10-13?" | unanswered | - | - | not written: noted for the session log |
| Q1 | docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md Q1 | default: answers mattered later at least some of the time, so write-back stays in the first slice | assumed | - | - | not written |

## Round 1

Presented 2026-10-06: D1 (skill name), D2 (first slice), D3 (numbering), D4 (where answers go), D5 (walk record location), D6 (GitHub issues), D7 (invocation), D8 (overlap with the options board), D9 (merge PR #20) and Q1 (past walk answers). Replies, verbatim, by item:

> D1: I dint like 'sitting' ... not a big fan of walk decisions, but that can work
> D2: expand this and provide more context. J don't like 'sitting'
> D3: A. Are there other types than Q and D?
> D4: A. However this feels a little incomplete and unsettled and I can't articulate why
> D5: (four questions, not kept verbatim: on architecture decision records, tracked against local records, effort association, and folder layout)
> D6: A i guess
> D7: A
> D8: I don't understand this
> D9: A

## Round 2

Presented 2026-10-07: D1, D2, D5 and D8 again with more context, and D10 to D13, which round 1 produced. Replies, verbatim, by item:

> D1: I like open-items what about resolve-open-items?
> D2: C, but record these other options in a backlog for this skill
> D5: outcome is tracked, the conversation local is a good rule of thumb
> D10 to D13: I don't quite know what to do with D10-13?

D8 went unmentioned, so it was asked about again rather than recorded.

## Round 3

Presented 2026-10-07: D1 and D8. Replies, verbatim, by item:

> D1: resolve-open seems even more succinct? 'items' doesn't really add much value does it?
> D8: (deferred to the backlog mode, after a plain-language re-explanation; the words were not kept)

## What the walk taught

1. **A walk is rounds, not a form.** Round 1 drew seven reply shapes, and the design at the time handled two of them.
2. **Silence was not taken as acceptance.** D8 went unmentioned in round 2 and was asked again.
3. **One item had several homes.** The design brief and the spec held the same items; the spec became the home and the brief points to it.
4. **Items generate items.** Answers produced D10 to D13.
