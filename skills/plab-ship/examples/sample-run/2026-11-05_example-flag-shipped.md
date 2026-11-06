---
type: ship-record
date: 2026-11-05
repo: example-owner/example-repo
release: approved
version: v1.1.0
model: opus-5-5
---

# Ship record: example flag shipped

This is an invented run, kept as the worked example of the format and as the sample `ship-check.py` proves its rules against.

## In Plain English

**End-user value:** You can now turn on the example behaviour with one option instead of editing a settings file by hand, and the guide explains what it does and what it defaults to. It is live in the new release. The half-finished export is not included, so exports work as they did before.

**Technical value:** The new option is covered by the existing test suite and described in the design notes, so a later change that breaks it fails a test rather than reaching a user. Every merge has a recorded way back, and a check confirmed that the documents named in this record really changed.

## Merged

| Branch | PR | Commit | Undo point | Merge check |
|---|---|---|---|---|
| `feat/example-flag` | #71 (add the example flag) | 0123abc | pre-merge/2026-11-05-feat-example-flag | VERDICT: merge, 7 checks passed |

## Left Open

- `feat/half-done` (PR #72, a draft of the export): CI failed on its build check, so it stayed open. Next action: fix the failing build.

## Needs Your Decision

- D1 (export file format), home `docs/internal/spec.md`: the export branch cannot finish until you choose a format.

## Documents

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

## Release

Released v1.1.0 from v1.0.0.

**Why:** the branch adds a flag and removes nothing, so existing use still works and the minor number rises.

Tag pushed; the publish workflow created the GitHub release. Steps only you can do: none.

## Cleanup

- Deleted `feat/example-flag` locally with `git branch -d`, and on GitHub with the merge.
- This repository has no open-items file.
- The working tree is clean on `main`.

## Unverified

- `screen-branch.py` is a pattern screen, so a clean result does not prove the branch holds no secret.
