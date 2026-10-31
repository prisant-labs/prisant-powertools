# Recommendations - 2026-10-19 to 2026-10-25

## A1 (routing-pin): decide whether to unpin the sonnet alias

The `sonnet` alias has drifted one release behind the family's current model for six weeks running, per `04-config.md`. The owner declined to pin it last cycle, a decision recorded at `docs/internal/decisions/sonnet-alias.md`, and asked to watch one more drift cycle before deciding again. This is that next data point.

**Who acts:** owner decides
**Mechanism:** setting

## A2 (brief-citations): refuse an uncited approval claim before it reaches the bundle

A brief worker's draft for this week again attributed an undocumented sign-off to the owner, the same failure class Y3's write-up first caught. The fix is mechanical: the main-loop assembly step already strips any sentence claiming an approval, a choice, or a decision that carries no backticked path or quotation, so this is a tightening of an existing check rather than a new one.

**Who acts:** agent
**Mechanism:** skill

## B1 (digest-reuse): skip the reader when the pulse already produced a digest

This week's practice lane launched a full reader even though the pulse had already written `data/digest.jsonl` for both projects earlier the same day. Wiring the lane to check for a same-day digest first removes a redundant pass with no loss of signal.

**Who acts:** agent after a yes
**Mechanism:** skill

## B2 (backup-check): wire the backup health line into this bundle automatically

Backup health is currently typed into `04-config.md` by hand from the backup task's own log, which is the same manual-population failure mode this skill otherwise eliminated. A small script reading that log directly would close the gap Y5 is still open on.

**Who acts:** owner acts
**Mechanism:** script

## Practice lessons

The pattern in `03-scorecard.md` holds again this week: A1 is the only item that needs the owner's judgment, and it is framed as a single yes-or-no rather than an open brainstorm, which is what let Y3 and Y4 close in one cycle each. A2 and B1 need no owner input at all, only an agent fix, and B2 needs one short act from the owner rather than a decision.

## One to-do list

1. Owner: answer A1 (routing-pin), either pin the alias or explicitly decide again not to, with the decision recorded.
2. Agent: tighten the uncited-approval strip per A2 (brief-citations); no owner input needed.
3. Agent, after a yes: wire B1 (digest-reuse) into the practice lane.
4. Owner: run the one script B2 (backup-check) names, once it exists.
