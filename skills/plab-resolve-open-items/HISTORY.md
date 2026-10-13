# History - plab-resolve-open-items

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.1 | 2026-10-12 | unreleased | fixed | A walk in a session with nothing open listed `_local/` folders and read memory files, looking for items, instead of saying nothing was open. A document now counts as a source only if the session read or wrote it before the walk was requested, and gathering never searches. |
| 1.0.0 | 2026-10-08 | v0.7.0 | added | First version. Walks the open questions, decisions and tasks of the current session, or of one named document, takes a one-line answer, writes each answer back to its one home, and writes a walk record that `walk-check.py` verifies. |

## 1.0.1 - 2026-10-12

**Fixed: a walk with nothing open went looking for items.** The install check of v0.7.0 on 2026-10-09 gave the walk request to a fresh headless session that had read nothing. Instead of saying nothing was open, the skill listed `_local/`, `_local/status/`, the session-log store and `_local/decisions/`, read memory files, and ran out of turns still searching. That broke AC-1 (gathering limited to the conversation and touched documents) of WD-01 (resolve open items).

The cause was the definition of a touched document: one "this session has read or written". Reading a file while gathering made that file touched, so the search created its own sources.

- **`references/walk-format.md` anchors both sources to the walk request.** A document counts only if the session read or wrote it before the maintainer asked for the walk. A new rule, "Gathering never searches", forbids listing a folder, opening a file or reading a memory file to find items. Re-reading a document touched before the request is still allowed.
- **Injected text is not conversation.** Text that a hook, a system reminder or a memory file put into the session is not an item unless someone raised it in the conversation. The maintainer's own start-up hook injects overdue rows from another repository's tracker into every session, and that is the case this rule names.
- **An empty walk has a defined reply.** The skill says nothing is open in one sentence, notes that `--backlog` is not built, offers to walk one named document, and stops. `SKILL.md` step 1 carries the same rules in short form.
- **The spec's Requirement 2 is amended to match.** The definition was the spec's own judgment call, and the skill must not contradict its contract.

## 1.0.0 - 2026-10-08

**Added: the in-session walk.** A walk gathers open items from the conversation and from the "Open Questions / Decisions" sections of documents the session has touched, or from one document the maintainer names. It presents them as D (a decision between lettered options), Q (a question only the maintainer can answer) and T (a task only the maintainer can perform), and reads a one-line reply such as `D1 A, D2 B, Q1: the NAS`.

Silence is never acceptance. An omitted decision is left as found, an omitted question proceeds on its stated default and is recorded as assumed, and only an explicit `ok` or `accept the rest` applies recommendations. A reply with doubt is recorded as `Provisional`, with the maintainer's words verbatim. A reply that asks for more, or makes no choice, re-presents the item in a further round.

Each answer is written to its item's one home document, on the three surfaces `references/decisions-section.md` defines, with a `Follow-up` line naming the work the decision causes. Every other copy of the item gets a pointer to the home. A document on another branch is never written; the intended edit is printed instead.

`scripts/walk-check.py` checks each write-back and each walk record, and CI runs it against a committed sample.

Specified by WD-01 (resolve open items) in `docs/internal/release-plans/_unassigned/WD-01_resolve-open-items/spec.md`. The design came out of two hand-run walks, whose reply shapes are the worked examples in `references/answer-line.md`.
