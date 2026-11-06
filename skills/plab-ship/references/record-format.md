# Run record format

One file per run, at `_local/_shipped/YYYY-MM-DD_<byline>.md`, with a byline of two to six lowercase kebab-case words. Never overwrite an existing file: choose another byline. The worked example is `examples/sample-run/`, and `scripts/ship-check.py` enforces everything below.

The record is not a session log, so it does not live in `_local/_session-logs/`, where `plab-continue-session` would read it as one. It is written first and appended as each merge lands, because two past runs compacted three times each, and a merge list held only in the conversation does not survive that.

## Frontmatter

```yaml
---
type: ship-record
date: 2026-11-05
repo: owner/name
release: approved          # or: not approved
version: v1.1.0            # or: none
model: opus-5-5
---
```

`version` may name a version only when `release` is `approved`. It stays `none` when the flag was passed and no release happened, and the Release section says why.

## Sections

The level-2 sections are exactly these, in this order. A section with nothing to say holds the word "None." rather than being omitted.

| Section | Holds |
|---|---|
| `## Merged` | One table row per merge: branch, pull request with a short handle, commit, undo point, what the merge check said |
| `## Left Open` | Each branch that did not merge, why, and the next action |
| `## Needs Your Decision` | Each decision a person must make, with its id, a short handle and its home document |
| `## Documents` | One `### <branch>` block per merged branch, described below |
| `## Release` | The version, with a `**Why:**` line giving the reason, the tag and the state of its workflows, and the steps only the maintainer can do. Without the flag, the words "Not approved for this run." |
| `## Cleanup` | Branches and worktrees removed, open items re-dated, and the final state of the tree |
| `## Unverified` | What was not checked, every gap from the facts, and any proposed documentation map |

## A Documents block

```markdown
### feat/example-flag

| Layer | Depth | State | File or reason |
|---|---|---|---|
| Human | Discover | updated | `README.md`, `CHANGELOG.md` |
| Human | Use | updated | `docs/guide.md` |
| Human | Understand | updated | `docs/guide.md` |
| Human | Trust | n/a | The flag has no failure mode of its own |
| Technical | Discover | correct | `docs/index.md` |
| Technical | Use | n/a | Build and release commands did not change |
| Technical | Understand | updated | `docs/internal/spec.md` |
| Technical | Trust | n/a | The test suite covers the flag already |
| Agentic | Discover | updated | `AGENTS.md` |
| Agentic | Use | updated | `AGENTS.md` |
| Agentic | Understand | n/a | No new rule or trap for agents |
| Agentic | Trust | n/a | No new eval or check script is needed |

**New surface:** `--example-flag`

**Cold reader:** read `README.md` and `docs/guide.md` only and ran the quick start; it could not tell what the flag defaults to, and `docs/guide.md` now says.

**Verification:** `pytest` passed 41 tests; CI green on the merge's head commit.

**Screen:** `screen-branch.py` CLEAN.
```

All twelve rows are required. `New surface` holds each token in backticks, or the word "none". `Cold reader` holds the result, or why it did not run.

## How it is checked

`ship-check.py <record> --repo <root>` compares the record with the commits it names, using the undo point and the commit in each Merged row.

| Rule | Fails when |
|---|---|
| R1 | The file is not `_local/_shipped/YYYY-MM-DD_<byline>.md` |
| R2 | A frontmatter field is missing or wrong, or a version is recorded without approval |
| R3 | A section is missing, renamed or out of order |
| R4 | A Merged row has no branch, commit hash or undo point |
| R5 | A merged branch has no block, a cell is missing, a state is unknown, or a cell lacks its path or reason |
| R6 | A block has no `**Cold reader:**` or `**New surface:**` line |
| R7 | A version is not named in the Release section with a `**Why:**` line, or an unapproved release is not stated |
| R8 | A file listed as `updated` did not change in that merge, a changed document is not listed, or a `correct` file does not exist |
| R9 | A new-surface token appears in no Human-layer file named by the record |
| R10 | A recorded version has no tag |

Rules R8 to R10 need `--repo`. Without it they are skipped, and the result line says so. A document here is a file ending in `.md`, `.mdx`, `.rst`, `.adoc` or `.txt`, outside `evals/`, `tests/`, `test/`, `fixtures/`, and any `examples/` or `fixtures/` folder.
