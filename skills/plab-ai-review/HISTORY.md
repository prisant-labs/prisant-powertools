# History - plab-ai-review

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.3.0 | 2026-10-15 | unreleased | added | Programmatic review dispatch (A-02): an opt-in `--dispatch` flag on `--review` submits the generated request to Codex as a background job through the `codex-companion` helper, and a new `--collect` mode (also reachable through the no-flag auto-detect) fetches the findings back into the same placeholders a manual paste would have filled. `argument-hint` now documents `--close`, which the skill already implemented but never advertised. |
| 1.2.1 | 2026-08-14 | v0.1.0 | migrated | First release in prisant-utilities. Migrated from a private upstream at version 1.2.1; prior history remains there. |

## 1.3.0 - 2026-10-15

Programmatic review dispatch (A-02, `docs/internal/release-plans/_unassigned/A-02_programmatic-review-dispatch/spec.md`). Without `--dispatch`, every mode behaves exactly as it did in 1.2.1 - this is a stated design constraint of the effort, not a leftover compatibility shim.

**`--dispatch` (new, on `--review`).** Submits the generated review request to Codex as a background job via the installed `codex-companion.mjs` helper's `task` subcommand (`skills/plab-ai-review/scripts/dispatch.py submit`), at `--effort high` with no model pinned. The job id is written into the document's frontmatter only once it exists, so a submission failure leaves the document exactly as the manual path would have: no frontmatter, every placeholder empty. The session is never blocked on the review completing.

**`--collect` (new mode).** Reads the job id back out of the document's own frontmatter - never asked of the maintainer - and, if the job has completed, writes its findings into the same Reviewer Assessment and per-dimension placeholders a manual paste would have filled, attributed to Codex. Also reachable through the no-flag auto-detect when a dispatched job is pending. `--respond` is unchanged and cannot tell a collected review apart from a hand-pasted one.

**Three-state failure reporting.** A reviewer that is unreachable, a job that is still running, or output that does not parse as findings each produce a distinct, reported state (`failed`, `running`, `unparseable`) rather than a document that silently looks like a completed, empty review. An unparseable job's raw output is saved to a sidecar file next to the document.

**`docs/internal/schemas/review.schema.json` (new).** The one frontmatter field this effort's spec allows (`dispatch-job`), plus the `type: review` tag `scripts/frontmatter-check.py` needs to recognize the block at all. Added to that script's `SCHEMA_FILES` map and self-test fixtures.

**`argument-hint` corrected.** Now lists `--close`, which the skill has implemented since before this release but never advertised, alongside the three new/changed entries (`--dispatch`, `--collect`, `--respond`).

## 1.2.1 - 2026-08-14

First public release. The skill is unchanged in behaviour from its last private version; this entry records the move, not a feature change.

**Migration provenance.** Zero recorded invocations in Claude Code, and 102 Codex sessions containing a review artifact in this skill's own naming convention, on the origin machine as of 2026-08-16.

Read those two numbers together. This skill exists to get a **second** model to review your work, so it runs in whichever harness is not the one that produced the document. A count scoped to a single harness reads as dormancy when the skill is in fact the most widely used of the five.

**On measuring this skill.** Codex transcripts carry no per-skill invocation record. Every occurrence of a skill's path sits inside the startup index Codex emits listing all installed skills, so counting mentions measures installation rather than use. An earlier draft of this entry cited such a count and overstated the figure. The artifact count above is the only Codex signal that proves work was done.

**Not carried over.** The prior HISTORY file is not reproduced here; it referenced private-repo layouts and planning folders that do not ship in this plugin.

**Bundled example.** `examples/v1.1.0-sample_reviewed-by-codex.md` is a complete worked review of a fictional API rate-limiting plan. It was read in full before publication and contains no real product, company, or person.
