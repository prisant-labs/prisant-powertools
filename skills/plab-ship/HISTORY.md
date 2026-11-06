# History - plab-ship

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.0 | 2026-11-06 | unreleased | added | First version, specified by SH-01 (the ship skill). Documents, verifies, screens and merges finished branches in one pass, with an optional `--release` whose version the model decides, and writes a checked run record to `_local/_shipped/`. Manual invocation only. |

## 1.0.0 - 2026-11-06

**Added: the skill.** The maintainer had been pasting one prompt to close out work, in 8 sessions across 6 repositories between 2026-10-28 and 2026-11-05, and asked for it to become a skill. A measurement of those sessions shaped three departures from the prompt: the secret and `_local/` checks became a script that runs before the merge, because a scanner ran in 0 of 8 sessions and a `_local/` check in 1 of 8; the session-long approval became one pass, because two sessions ran about 40 hours through 3 compactions; and the merge list moved to a record written as merges happen, because a list held in the conversation does not survive compaction.

The maintainer also ruled that `--release` takes no number and no size, and that the model decides patch, minor and major itself, so a major version does not stop to ask.

The closing report opens with a plain-English account of everything the session accomplished and the ship delivered, split into end-user value and technical value, at the maintainer's request of 2026-11-06. The record carries it too, and rule R11 rejects a record without both lines, or one naming files, flags, ids or commits.

**Fixed before release: a quoted flag read as a new flag.** The first real run of `ship-check.py --repo`, on the delivery of this skill, failed R9 on `--example-flag`, which is text inside the self-test's own fixture and defines nothing. Fixture runs had missed it, because no fixture held a flag quoted in a string. The pattern now anchors to the start of the statement, and the fixture holds a quoted flag as an anti-canary, which broke the self-test before the fix. The version stays 1.0.0, because 1.0.0 has not been released.
