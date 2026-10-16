# History - plab-resolve-open-items

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.2 | 2026-10-15 | unreleased | fixed | Three defects recorded against WD-01's (resolve open items) Phase 6 live trial. `walk-check.py` now accepts the numbered and `&`/`and` heading variants the skill itself gathers from. One handle is chosen once per walk, from the first filled maintainer block in gathering order, and recorded in the walk record. An item omitted in one round can still be answered in a later round. |
| 1.0.1 | 2026-10-12 | v0.7.1 | fixed | A walk in a session with nothing open listed `_local/` folders and read memory files, looking for items, instead of saying nothing was open. A document now counts as a source only if the session read or wrote it before the walk was requested, and gathering never searches. |
| 1.0.0 | 2026-10-08 | v0.7.0 | added | First version. Walks the open questions, decisions and tasks of the current session, or of one named document, takes a one-line answer, writes each answer back to its one home, and writes a walk record that `walk-check.py` verifies. |

## 1.0.2 - 2026-10-15

**Fixed: three findings from WD-01's (resolve open items) Phase 6 live trial,** recorded in the trial's results under "Findings for a later fix" and not yet released under any version.

1. **`walk-check.py` could not read a section the skill gathers from.** The trial's brief was headed `## 7. Open Questions & Decisions`; the skill gathered from it correctly, but the checker required `## Open Questions / Decisions` exactly and exited 2. `references/walk-format.md` now names, in one place, the exact heading variants this walk gathers from: an optional numbered prefix, and `&` or `and` standing in for the slash. `scripts/walk-check.py`'s `SECTION_RE` matches that same definition, so a heading the skill gathers from is a heading the checker can verify, and nothing wider than that is accepted.
2. **One walk wrote two maintainer handles.** Where a document had no filled maintainer block to copy from, the session fell back to `git config user.name`, while other documents in the same walk used a different handle. `references/write-back.md` now chooses the handle once per walk, before the first write, from the first filled maintainer block found among the walk's gathered documents in gathering order, falling back to `git config user.name` only when none has one. `references/walk-record.md` gains `handle` and `handle-source` frontmatter fields recording the choice.
3. **The answer rules were silent on a round-2 answer to a round-1 omission.** `references/answer-line.md`'s Skips section now states that an item omitted in an earlier round can be answered in any later round of the same walk, applied in the round it was given.

## 1.0.1 - 2026-10-12

**Fixed: a walk with nothing open went looking for items.** The install check of v0.7.0 on 2026-10-09 gave the walk request to a fresh headless session that had read nothing. Instead of saying nothing was open, the skill listed `_local/`, `_local/status/`, the session-log store and `_local/decisions/`, read memory files, and ran out of turns still searching. That broke AC-1 (gathering limited to the conversation and touched documents) of WD-01 (resolve open items).

The cause was the definition of a touched document: one "this session has read or written". Reading a file while gathering made that file touched, so the search created its own sources.

- **`references/walk-format.md` anchors both sources to the walk request.** A document counts only if the session read or wrote it before the maintainer asked for the walk. A new rule, "Gathering never searches", forbids listing a folder, opening a file or reading a memory file to find items. Re-reading a document touched before the request is still allowed.
- **Injected text is not conversation.** Text that a hook, a system reminder or a memory file put into the session is not an item unless someone raised it in the conversation. The maintainer's own start-up hook injects overdue rows from another repository's tracker into every session, and that is the case this rule names.
- **An empty walk has a defined reply.** The skill says nothing is open in one sentence, notes that `--backlog` is not built, offers to walk one named document, and stops. `SKILL.md` step 1 carries the same rules in short form.
- **The spec's Requirement 2 is amended to match.** The definition was the spec's own judgment call, and the skill must not contradict its contract.

**Canary.** Each arm ran the same headless prompt from the same clean `main` checkout, with the installed plugin and auto-memory switched off for that invocation, through a `.claude/skills/` junction. Only the skill text differed. Under 1.0.0 the session listed `_local/` and `_local/decisions/` and globbed the release plans for WD-01 documents before replying. Under 1.0.1, in two runs, it read only its own `walk-format.md` and replied that nothing was open. Memory had to be off because this project's own memory describes the defect and its fix: with memory on, a 1.0.0 run read that memory and avoided the search by hand.

## 1.0.0 - 2026-10-08

**Added: the in-session walk.** A walk gathers open items from the conversation and from the "Open Questions / Decisions" sections of documents the session has touched, or from one document the maintainer names. It presents them as D (a decision between lettered options), Q (a question only the maintainer can answer) and T (a task only the maintainer can perform), and reads a one-line reply such as `D1 A, D2 B, Q1: the NAS`.

Silence is never acceptance. An omitted decision is left as found, an omitted question proceeds on its stated default and is recorded as assumed, and only an explicit `ok` or `accept the rest` applies recommendations. A reply with doubt is recorded as `Provisional`, with the maintainer's words verbatim. A reply that asks for more, or makes no choice, re-presents the item in a further round.

Each answer is written to its item's one home document, on the three surfaces `references/decisions-section.md` defines, with a `Follow-up` line naming the work the decision causes. Every other copy of the item gets a pointer to the home. A document on another branch is never written; the intended edit is printed instead.

`scripts/walk-check.py` checks each write-back and each walk record, and CI runs it against a committed sample.

Specified by WD-01 (resolve open items) in `docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md`. The design came out of two hand-run walks, whose reply shapes are the worked examples in `references/answer-line.md`.
