# History - plab-ship

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.1.0 | 2026-11-15 | v0.14.1 | fixed | A pending decision blocks a branch only when the branch changes that decision's own entry. The facts report `decisions_in_diff` on each local branch and pull request, with `touched` true or false. |
| 1.0.0 | 2026-11-06 | v0.13.0 | added | First version, specified by SH-01 (the ship skill). Documents, verifies, screens and merges finished branches in one pass, with an optional `--release` whose version the model decides, and writes a checked run record to `_local/_shipped/`. Manual invocation only. |

## 1.1.0 - 2026-11-15

**Fixed: a count line no longer stops a merge.** Through 1.0.0, a pending decision blocked any branch whose diff held the decision's home document. On 2026-11-15 that stopped a merge in a template library that every check had passed: the branch added four decision records, so it moved the decision-record count in the project plan, and the plan is also where four unrelated open decisions live. The maintainer approved the merge and asked for the rule to be narrowed.

`derive-ship-facts.py` now diffs each local branch and each pull request against its base, restricted to the home documents of pending decisions. A changed line touches a decision when it holds the decision's id as a whole word, or its full title, which is how a decisions-table row or a waiting bullet reads. Each branch and pull request carries `decisions_in_diff`, one entry per decision whose home it changes, with `touched` true or false. The skill blocks only on `touched: true`, and treats a branch that could not be diffed (`null`) as touching every such decision.

**What it does not catch.** An edit to prose about a decision that names neither its id nor its title, such as a paragraph below the table, reads as untouched. The skill therefore still asks the agent to read the home document's hunks once before merging through a `touched: false`.

**Proof.** A new test builds three branches over one decisions table: a count edit, an edit to the decision's row, and a README edit. It failed with all three cases before the change and passes after. On the real repository, the 2026-11-15 merge range reports its four decisions untouched, and the commit that first wrote those decision rows reports all four touched.

## 1.0.0 - 2026-11-06

**Added: the skill.** The maintainer had been pasting one prompt to close out work, in 8 sessions across 6 repositories between 2026-10-28 and 2026-11-05, and asked for it to become a skill. A measurement of those sessions shaped three departures from the prompt: the secret and `_local/` checks became a script that runs before the merge, because a scanner ran in 0 of 8 sessions and a `_local/` check in 1 of 8; the session-long approval became one pass, because two sessions ran about 40 hours through 3 compactions; and the merge list moved to a record written as merges happen, because a list held in the conversation does not survive compaction.

The maintainer also ruled that `--release` takes no number and no size, and that the model decides patch, minor and major itself, so a major version does not stop to ask.

The closing report opens with a plain-English account of everything the session accomplished and the ship delivered, split into end-user value and technical value, at the maintainer's request of 2026-11-06. The record carries it too, and rule R11 rejects a record without both lines, or one naming files, flags, ids or commits.

**Fixed before release: a quoted flag read as a new flag.** The first real run of `ship-check.py --repo`, on the delivery of this skill, failed R9 on `--example-flag`, which is text inside the self-test's own fixture and defines nothing. Fixture runs had missed it, because no fixture held a flag quoted in a string. The pattern now anchors to the start of the statement, and the fixture holds a quoted flag as an anti-canary, which broke the self-test before the fix. The version stays 1.0.0, because 1.0.0 has not been released.
