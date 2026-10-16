# Walk format: gathering and presenting

How a walk finds its items, sorts them into series, gives each one home, and shows them to the maintainer. Steps 1 and 2 of `SKILL.md`.

## Sources

A walk gathers from exactly two sources, and both are fixed at the moment the maintainer asks for the walk.

1. **This conversation.** An item is open here when the agent asked the maintainer something that got no answer, proposed a choice the maintainer did not rule on, said a choice needs the maintainer, or named a task only the maintainer can do. A question the agent could answer by reading a file is not an item; answer it instead. Text that a hook, a system reminder or a memory file injected into the session is not conversation for this purpose: nothing in it is an item unless the maintainer or the agent raised it in the conversation itself.
2. **Documents this session touched before the walk was requested.** A document is touched when this session read it or wrote to it before the maintainer asked for the walk. Its items are the entries in its "Open Questions / Decisions" section whose status is `Open` or `Needs info`. Items already `Decided`, `Provisional`, `Deferred`, `Canceled` or `Superseded` are settled and are not gathered. An item whose status is none of the seven, such as `Proposed`, `Ratified` or `Needs ruling`, is not silently skipped: present it as open, and name its unrecognized status in the source line, so the maintainer can settle the item and its status together.

**Heading variants this walk gathers from.** `references/decisions-section.md` names the section `## Open Questions / Decisions`. This walk also gathers from two variations on that heading, because other documents in this plugin number their sections: a numbered prefix before the words, such as `## 7. Open Questions / Decisions`, and `&` or `and` standing in for the slash, such as `## Open Questions & Decisions` or `## Open Questions and Decisions`. The two combine, as in `## 7. Open Questions & Decisions`. No other wording, punctuation or word order counts; a section headed anything else is not a source, even if it plainly holds the same kind of items. `scripts/walk-check.py`'s `SECTION_RE` matches exactly this definition, so a heading this walk gathers from is a heading the checker can verify, and a heading it does not gather from is still rejected by the checker.

**Gathering never searches.** Do not list a folder, open a file, or read a memory file in order to find items. A file read during gathering is not touched, because the definition above is anchored to the walk request so that the set of sources cannot grow while the walk runs. Re-reading a document that was touched before the request, to get the current text of its section, is allowed.

Nothing else is a source: not a document the session never opened, not a memory file, not a decision register or status document the session did not open before the request, not another repository, and not the session-log store. Sweeping those is the `--backlog` mode, which is not built.

**Nothing open.** When neither source holds an open item, say so in one sentence, note that the `--backlog` sweep across the repository is not built, offer to walk one document the maintainer names, and stop. Write no walk record for an empty walk.

**Named-document mode.** When the maintainer names one document ("resolve the open items in `<path>`"), the walk gathers from that document's section alone, and the conversation is not a source. If that document has no section in the format of `references/decisions-section.md`, say so. Offer to walk its items anyway, with every answer landing in the walk record only, because write-back needs the format.

## Series

Every item belongs to exactly one series.

| Series | What it is | Its answer |
|---|---|---|
| **D** | A decision between two to four lettered options, with exactly one recommendation and a stated confidence | An option letter, or a deferral, or a cancellation |
| **Q** | A question whose answer only the maintainer has, such as a fact, a preference or a constraint | Free text. Every Q states the default the walk assumes if it is skipped |
| **T** | A task only the maintainer can perform, such as restarting the harness or deleting a folder | `done`, `later` or `drop` |

An approval of an outward action, such as merging a pull request, is a D item with two options. A clarification the agent needs is a Q item.

**Numbering.** Walk IDs are local to the walk: `D1`, `D2` and so on, numbered in presentation order within each series. An item keeps its walk ID in every round. Options are uppercase `A` to `D`. When more than four options exist, group them into families first. The series letters Q, D and T do not collide with the option letters A to D.

## One home per item

Some items appear in more than one document, such as a decision recorded in an effort's spec and copied into a private brief. Present such an item once, and give it one home.

1. The home is the tracked document closest to the work: an effort's spec or plan wins over a release plan or README, and any tracked document wins over an untracked one, such as a brief or a register.
2. When two tracked documents tie, ask which is the home, as a Q item, and present the item itself after that is answered.
3. The answer is written only to the home. Every other copy receives a pointer to the home, as `references/write-back.md` describes.

Treat two entries as one item only when a document says so, with a pointer or a "mirrors" note, or when their titles and questions match. When unsure, present both and ask whether they are the same item.

## Presentation

Present D items first, then Q, then T. Within a series, group items by home document. Use plain language: say what the item decides and why it matters now, before any identifier. Pair every reference ID with a short handle, such as "AC-18 (rounds)", because the maintainer does not keep ID meanings between sessions.

**A D item:**

```markdown
### D1: <handle> (from <home document>, <its own id>)

<What this decides and why it matters now, in two to four plain sentences.>

- **Option A:** <the option, with its most important trade-off>
- **Option B:** <the option, with its most important trade-off>

**Recommendation:** A. <Why, in one to three sentences.> Confidence: <high | medium | low>.
```

**A Q item:**

```markdown
### Q1: <handle> (no source document)

<The question, and why only the maintainer can answer it.>

**Default if skipped:** <the value the walk assumes, and what it causes>.
```

**A T item:**

```markdown
### T1: <handle> (no source document)

<What the task is, and the exact command or place, if there is one.>

Answer `done`, `later` or `drop`.
```

**The source line.** A sourced item names its home and its own id there, for example "D4, from the WD-01 spec's D1". An item from the conversation reads "no source document"; never invent one. An item with copies elsewhere names them after its home: "from the WD-01 spec's Q1, also in the design brief".

**Show, do not describe.** When a D item decides a format or a wording, include a short before-and-after of the text it would change. In the first two walks of this skill's design, every "I don't understand this" came after an abstract description, and every second presentation that showed the concrete text was answered.

**Close with the answer line.** End the presentation with one line saying how to answer, for example: "Answer in one line, such as `D1 A, D2 B, Q1: the NAS, T1 later`, or `ok` to accept every recommendation and default."
