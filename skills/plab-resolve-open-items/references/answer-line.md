# Answer line: reading the maintainer's reply

How a one-line reply becomes one state per presented item. Steps 3 and 5 of `SKILL.md`.

The reply is read in two passes. The grammar decides, mechanically, which text belongs to which item and whether it starts with a choice. The meaning of anything left over is then interpreted by the agent, never guessed by the grammar.

## Pass 1: the grammar

1. **Split the reply at each item id.** An id is a series letter and a number, `Q1`, `D2` or `T3`, in either case, followed by a space, a colon, a period or a comma. Everything from one id up to the next id belongs to the first. "D7. A" and "D8 A" both split cleanly.
2. **Find the choice in each segment.**
   - **D:** a single letter `A` to `D`, as the first word after the id, is the option chosen. A letter the item did not offer is not a choice; treat the segment as a request for more (below).
   - **Q:** all text after the id, minus a leading colon, is the answer, kept verbatim. "Q1: the NAS" answers "the NAS".
   - **T:** the first word, `done`, `later` or `drop`, is the answer.
3. **Keep the remainder.** Any text in a segment after its choice goes to pass 2 verbatim.
4. **Find explicit acceptance.** A segment-free phrase such as `ok`, `accept all`, `yes to all`, `go with your recommendations` or `accept the rest` accepts every item not otherwise answered in the same reply, each at its recommendation or default. `Go with your recommendation` inside one item's segment accepts that item alone.
5. **Report unknown ids.** An id the walk did not present applies nothing; say so in the report.

## Pass 2: what the remainder means

Read the remainder of each segment, and a segment with no choice, for one of these meanings.

| The reply | Example | The result |
|---|---|---|
| Words of doubt beside a choice | "A, but I'm not sure"; "A i guess"; "A. However this feels a little incomplete and unsettled" | `provisional`. Keep the words verbatim; they go in the `Reasoning` line. |
| A question beside a choice | "A. Why wouldn't we add answers to documents?"; "A. Are there other types than Q and D?" | The choice stands. Answer the question in the same response. |
| A request for more, with no choice | "expand this"; "expand this and provide more context" | Unanswered this round. Re-present with more context. |
| Not understood, with no choice | "I don't understand this" | Unanswered this round. Re-present differently: show the concrete text it changes. |
| A question with no choice | "What is --backlog?" | Unanswered this round. Answer the question, then re-present. |
| An alternative proposed instead of a choice | "Why not use provisional instead of reservation?" | Unanswered this round. Re-present with the proposal as an option, completed if it has gaps. |
| A deferral of a D | "D3 later"; "defer D3 until the layout effort" | `deferred`. Record when to revisit, if given. |
| A cancellation of a D | "drop D3"; "D3 is no longer relevant" | `canceled`. |

The rule for a choice beside a question was confirmed by the maintainer on 2026-10-08: when one reply holds both a choice and a question, the choice wins, and only a reply with no choice comes back.

## States

Every presented item leaves the walk with one state.

| Series | States |
|---|---|
| D | `decided`, `provisional`, `deferred`, `canceled`, `unanswered` |
| Q | `decided`, `provisional`, `assumed` |
| T | `done`, `later`, `drop`, `open` |

## Skips

Silence is an answer, and it is never acceptance.

- An omitted **D** item is `unanswered`. Its home document is not written, and its status stays as found.
- An omitted **Q** item is `assumed`: the walk proceeds on its stated default, and the walk record marks the value as assumed, not decided. Its home document is not written.
- An omitted **T** item stays `open`.
- An item that was re-presented for more context and is then omitted again is asked about once more, by name, in the closing report. It is not re-presented a third time.
- **An omission does not close the item.** An item omitted in an earlier round can be answered in any later round of the same walk, whether or not it was re-presented in that round; omitting it once does not forfeit the chance to answer it later. The answer is applied in the round it was given, and the walk record's `Round` column shows that round, not the round of first presentation.

Explicit acceptance is different from silence. "Accept the rest" or "ok" makes each item it covers `decided` at its recommendation or default, and that Q item's default is recorded as decided, not assumed.

## Worked examples

**A plain line.** "D1 A, D2 B, Q1: the NAS". D1 is `decided` as option A, D2 is `decided` as option B, and Q1 is `decided` with the text "the NAS". No other item changes.

**Skips.** A walk presents D1 to D3 and Q1 and Q2; the reply is "D1 A, D2 B, Q1: the NAS". D3 is `unanswered` and its document is untouched. Q2 is `assumed` on its default.

**Explicit acceptance.** A walk presents D1 to D3 and Q1; the reply is "D2 B, Q1: the NAS, accept the rest". D1 and D3 are `decided` at their recommendations because the reply said so, not because the line left them out.

**Rounds.** The reply is "D1 A, but I'm not sure. D2: expand this. D3: I don't understand this". D1 is `provisional` as option A, with "but I'm not sure" kept verbatim. D2 and D3 are written nowhere; they are re-presented in round 2, D2 with more context and D3 with the concrete text it changes. The walk record keeps both rounds.

**Bare acceptance.** The reply is "ok". Every item is `decided` at its recommendation or default.

**The first design walk, round 1 (2026-10-06).** Seven reply shapes came back. "A" and "A i guess" are a choice, the second `provisional`. "A. However this feels a little incomplete and unsettled and I can't articulate why" is `provisional` with the words kept. "A. Are there other types than Q and D?" is `decided`, with the question answered. "expand this and provide more context" and "I don't understand this" are re-presented. A reply of four questions with no choice is re-presented after the questions are answered.

**The plan walk (2026-10-07 and 2026-10-08).** "D1. What are the 5 deferred features ... Go with your recommendation." is `decided` at the recommendation, with the questions answered. "D2. A. Why wouldn't we add conclusions / answers to documents?" is `decided` as A. "D3. I don't like reservation. Why not user the provisional language instead is reservation?" is an alternative with no choice, re-presented with the proposal as option A. "D4. I don't understand this" is re-presented with a before-and-after.
