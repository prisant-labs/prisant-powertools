# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.1] - 2026-10-13

The patch release that the 0.7.0 entry promised. The live-walk trial that 0.7.0 shipped ahead of ran on 2026-10-12, against the fix below, and proved all 20 of the skill's acceptance criteria; its specification is now fulfilled.

### Fixed

- **`plab-resolve-open-items` 1.0.1: a walk with nothing open no longer searches for items.** The v0.7.0 install check gave the walk request to a fresh headless session that had read nothing. Instead of saying nothing was open, the skill listed `_local/` folders and read memory files, and ran out of turns still searching. The cause was the definition of a touched document, one the session "has read or written": reading a file while gathering made it a source. A document now counts only if the session read or wrote it before the walk was requested, gathering never lists a folder or opens a file to find items, and text injected by a hook or a memory file is not an item. The spec's Requirement 2 is amended to match.

## [0.7.0] - 2026-10-09

Adds a tenth skill, `plab-resolve-open-items`, and ships `plab-audit` 1.1.0. The new skill ships before its live-walk trial, by maintainer ruling of 2026-10-09: the plugin's only user chose to run that trial against the installed release. A defect it finds ships as a patch release, as 0.6.1 did for `plab-audit`.

### Added

- **`plab-audit` 1.1.0: every appraisal ends with a big-picture section, "Standing back".** By maintainer ruling of 2026-10-06, `appraise.md` gains a seventh, closing section that says what the repository is beyond its parts, what most distinguishes it and what most constrains it, and in a full run names the theme connecting the findings. `bundle-check.py` rule R8 fails an `appraise.md` that does not end with it. Before the committed sample was rewritten, R8 failed both that sample and the real bundle from the skill's 2026-10-06 run on `nonfiction-studio`, which is the canary.

- **`plab-resolve-open-items` 1.0.0: walk through what a session has left open, and write each answer back.** Ask "walk me through the pending questions and decisions" and the skill gathers the open items of the conversation, and of every document the session touched, or of one document you name. It presents them as D (a decision between lettered options, with a recommendation), Q (a question only you can answer, with the default it assumes if skipped) and T (a task only you can do), and takes one line such as `D1 A, Q1: the NAS, T1 later`.
  - Each answer is written to its item's one home document, on the three surfaces of `references/decisions-section.md`, with a `Follow-up` line naming the work the decision causes. Every other copy gets a pointer.
  - Silence is never acceptance: an omitted decision is left as found, and an omitted question proceeds on its default, recorded as assumed. A reply with doubt is recorded as `Provisional`. A reply that asks for more comes back in a further round.
  - A document on another branch is never written; the intended edit is printed instead.
  - `scripts/walk-check.py` checks every write-back and every walk record, and CI runs it against a committed sample. Sixteen canaries proved each rule can fail, two of them against a real spec rather than a synthetic one.
  - Not built yet: the `--backlog` sweep across every spec, plan and log, automatic GitHub filing, a GitHub Projects board, gathering across repositories, and a published web page.

### Changed

- **The shared decisions format has seven statuses, by maintainer ruling of 2026-10-08.** `references/decisions-section.md` now lists Open and Needs info before an answer, then Decided, Provisional, Deferred, Canceled and Superseded. `Canceled` replaces `Withdrawn`. It also defines the optional `Follow-up` line. Neither change alters any existing document: a search of every tracked Markdown file found no item using `Withdrawn`, and no skill restates the vocabulary.

### Fixed

- **`library.json` listed `plab-audit` at 1.0.1 after its `SKILL.md` moved to 1.1.0.** No gate reads per-skill versions in `library.json`, so the drift went unnoticed from PR #20 until the WD-01 implementation plan's parity loop flagged it.

## [0.6.1] - 2026-10-06

The patch release that the 0.6.0 entry promised. The first full run of `plab-audit` on another repository found three defects in the skill itself, and this release fixes them.

### Fixed

- **`plab-audit` 1.0.1: the default output folder could land inside the audited repository.** The default `_output/plab-audit/<repo>_<YYYY-MM-DD>/` is relative to the working directory, so an audit started from inside its target wrote its bundle there, against the skill's own read-only rule. The 2026-10-06 run on `nonfiction-studio` avoided this only because the operator redirected the bundle by hand. Step 1 now resolves the output folder before anything is written, and refuses a location inside the target unless `git -C <target> check-ignore -q <output-folder>/README.md` exits 0.

  **The check names a file inside the folder, not the folder itself.** For a folder that does not exist yet, `check-ignore` cannot tell that a directory pattern such as `_output*/` applies, so it returns 1 for a folder that would in fact be ignored. Canary: the file-path form exits 0 in this repository, which ignores `_output*/`, and 1 in `nonfiction-studio`, which does not.

- **`plab-audit` 1.0.1: the vendored-copy comparison asked one question and reported another.** Step 3 of the agent-plugin pack diffed the target against the toolkit's current files. That comparison measures how stale a vendored copy is, but the pack read its result as evidence of local edits. This is how the 2026-09-20 fixture audit's highest-ranked finding, "vendored spine modified", came to be wrong. The step now runs two labelled comparisons, each against its own baseline: against the pinned commit to find edits, and against upstream `HEAD` to measure staleness.

  **Canary.** Against its pin, `nonfiction-studio`'s vendored `checks/` and `lib/` folders show 0 content differences. Against `HEAD`, `checks/` shows 22. Without `--strip-trailing-cr`, the comparison against the pin reports 49 false differences on a Windows checkout, so the flag is part of the command.

- **`plab-audit` 1.0.1: `effectiveSeverity: "off"` was misattributed.** The pack called "off" a tier-ceiling marker, and a note added on 2026-10-05 said the marking varied with the toolkit version. Both claims are wrong. On one toolkit commit, `549eb32`, this repository returned its 35 above-tier findings at `"error"`, and `nonfiction-studio` returned 150 at `"off"`. The difference is the profile: `nonfiction-studio` sets `plain-plugin`, which switches the toolkit's house conventions off. The tier ceiling marks nothing per finding under either profile. The pack now says so, and the audit records `config.profile` from the JSON.

- **Seven `HISTORY.md` rows read "unreleased" for versions that had shipped.** Each now names the tag that shipped it, derived from `library.json` at every tag rather than recalled. `plab-release-plan` 1.4.0 never shipped under its own number, so its row reads `v0.5.0 (as 1.5.0)`. No script reads this column, which is how the drift built up across five skills.

### Added

- **`plab-audit` 1.0.1: the first-party plugin validator is agent-plugin pack tool 7.** `claude plugin validate --strict <target>` ships with Claude Code, so unlike the third-party validators the pack already names, it is a required step. The pack records that this validator does not read `settings.json`. That is how the run's F-01 (an unquoted plugin path in the status-line command) stayed invisible to it while the same pattern in `hooks.json` was caught.

### Verified

- **AU-01 (audit skill) Phase 7 steps 2 and 3, waived before 0.6.0, have now run.** The run on `nonfiction-studio` detected `agent-plugin` from `library.json` and `.claude-plugin/plugin.json` and wrote all five bundle files, and `bundle-check.py` reported the bundle clean. Compared with the hand-run Phase 2 fixture, the bundle has the same five files and every section the output specification requires. The degradation run with `cargo` hidden and the dogfood gate are still to come.

## [0.6.0] - 2026-10-06

### Added

- **`plab-audit` 1.0.0: audit a repository into a five-file bundle.** What it is and is worth, what is wrong with it with a file path on every finding, and what to do next ranked and traceable to those findings. Three composable modes (`--appraise`, `--audit`, `--roadmap`), repository type detected from disk with an override, and a coverage statement recording every command with its exit code so that a tool which is absent or fails becomes a recorded gap rather than a silence. Ships with `disable-model-invocation: true`, the second skill to do so; `/plab-audit` runs it.

  **The step that makes the output worth acting on is reconciliation.** The deterministic layer produces candidates, not findings. A candidate becomes a finding only after it has been checked against the repository's own recorded decisions. On the fixture audit that specified this skill, that step withdrew 7 of 15 candidates, including the two highest-ranked, and one of the withdrawn candidates recommended a change the target had already tested and rejected with measured evidence.

  **Validated against two bundles, both real.** The Phase 2 fixture is a hand-run audit of a working repository, produced before the skill existed and used as the output specification rather than written to match one. The committed sample under `skills/plab-audit/examples/sample-bundle/` is trimmed from it, genericized so that a public repository does not carry another repository's findings or machine-specific paths, and kept complete rather than minimal so that every rule stays exercised.

- **`skills/plab-audit/scripts/bundle-check.py`, run by CI.** Seven structural rules over a finished bundle, on the repository's three-state exit convention (`0` clean, `1` findings, `2` broken), with a self-test that runs on every invocation so a checker which cannot prove itself refuses to report. `.github/workflows/gate.yml` runs it against the committed sample, because the workflow enumerates its checks and globs nothing, so a script not named there never runs at all.

  **Rule R6 was wrong when it was written, and a canary is what found it.** It checked that every finding citation present in a roadmap resolves, which is a per-file property, where AC-9 states that every item above the break must carry one, which is a per-item property. Stripping a single item of its citation left seven valid siblings and the checker returned clean on a direct violation. The rule now slices each rank-numbered item and requires a resolvable citation inside it. **The embedded self-test passed throughout**, because its fixture was written by the same author at the same time against the same misreading of the criterion. That is the argument for canarying against a real artifact rather than a synthetic one, and it is recorded here rather than quietly fixed because the mistake is available to anyone extending the checker.

### Deliberately omitted

- **`--lens=publish-readiness`** was cut. Its source proposal is not in this repository, so the lens had no specification to build against.
- **`--deep` and `--ideate`** are deferred. Neither has an executable design yet, and a flag that cannot say what it does differently is a name rather than a feature.

### Not yet verified

- **Released without the planned dogfood runs.** Before release the skill was exercised in `--appraise` mode on this repository, where it wrote exactly two files and `bundle-check.py` reported the bundle clean. A full five-file audit of another repository, the shape comparison with the hand-run fixture, and the degradation run with `cargo` hidden (AC-12, honest degradation when a tool is missing) run after release against the installed version. A defect they find ships as a patch release.

## [0.5.5] - 2026-09-20

### Changed

- **`plab-continue-session` 1.5.0: Phase 3 no longer dumps the continuation prompt.** It renders the prompt's immediate action as ordinary markdown, gives the log path on one line, and prints the full prompt verbatim only when asked.

  **The rationale for verbatim display did not survive inspection.** The verbatim form exists so a prompt can be pasted into a cold-start session that has not read the log. Phase 3 is the opposite case by construction: the skill has just read the entire log, so reprinting it carries no information the agent does not already hold and none the user cannot `cat`. Meanwhile the cost is real, because inside a fenced block none of the prompt's own markdown renders, so a hundred lines or more of `**bold**` and backtick noise arrive as literal source. It was the longest thing on screen and the least readable. Verbatim stays available on request, because someone resuming in a different tool still needs to copy it.

  **A second defect is fixed in the same change: the display format had two sources of truth that disagreed.** `references/handoff-display.md` specified a `### What's next (from last session)` section that the SKILL.md Phase 3 template omitted, so an agent following SKILL.md silently dropped it. The template now carries it. Both files moved together along with the Constraints line that independently mandated verbatim display, because the three had to change at once or the skill would contradict itself.

  Reported by the maintainer, who watched raw markdown fill a terminal on a real resumption.

### Fixed

- **Two stale version headings in `docs/status-skills.md`.** The `plab-wrap-session` section heading read 1.6.2 and the `plab-continue-session` section heading read 1.4.0, two bumps and one bump behind what those skills declare in their own `SKILL.md` metadata, which is 1.7.0 and 1.5.0. Both drifted the same way: the change that bumped each skill updated the At a glance table and the usage README and left the section heading alone.

  **`scripts/version-parity-check.py` passes on both, by design.** It checks four locations and a section heading is not one of them, because version-shaped strings outside those four are presumed historical, which is the rule that keeps it from firing on every HISTORY row. These two headings are the counter-example: the convention in this file is that the heading states the current version, so a stale one is a false claim rather than a historical record. Whether to add a fifth location is a gate change and is left to its own decision rather than folded into a release.

## [0.5.4] - 2026-09-15

### Added

- **`.github/workflows/publish-release.yml`, and `scripts/release-notes-from-changelog.py` behind it.** Pushing a `v*` tag now publishes the GitHub Release for it, with the notes taken from that version's section of this file. Thirteen tags existed with zero Releases before this, because a hand-cut tag is only a git ref and nothing was promoting it; those thirteen were backfilled by hand on 2026-09-14 and this stops the gap reopening on the next tag.

  **It does not weaken `AGENTS.md`'s "CI reports; it never fixes, bumps, or tags".** The workflow chooses no version, writes no file, and creates no tag. The tag is its trigger rather than its product, and the notes are the entry the maintainer already wrote.

  Extraction lives in a committed script rather than inline in the workflow, matching the rule `gate.yml` states in its own header, which also makes any version dry-runnable locally. Three-state like every other script in `scripts/`: 0 printed, 1 no section for that version, 2 broken. A self-test proves five properties against a fixture and the workflow runs it **before** extracting, so nothing is published under the maintainer's name on the word of an unproven script. A tag whose version has no section here **fails the run**, because a release with no notes reads as a release that had nothing to say rather than one whose extraction broke. Fenced blocks are dropped whole and inline code spans become plain text, because release notes are read on a web page and in the GitHub mobile app where monospace wraps badly.

- **`plab-wrap-session` 1.7.0: deep-mode logs now record what they do not know.** Two sections, placed immediately after Verification Detail so that what was proven is followed at once by what was not.

  **The Uncertainty Ledger merges two questions that turn out to be one list sorted two ways.** "What am I least confident about" sorts by confidence; "which assumption would change the outcome most if wrong" sorts by blast radius. Those orderings disagree, and the row that matters most sits exactly where they do: high confidence and high blast radius, an assumption comfortable enough that nobody thought to check it. Asked as two separate questions those rows fall into the gap, because they neither feel uncertain nor read as remarkable. One table carrying both axes forces them into view, marked `(!)`.

  The failure mode is this repository's own. C-1, C-2 and C-4 were each held confidently, were each load-bearing, and were each wrong; every one would have been a `(!)` row before it was found.

  **What You May Not Realize is separate because its source differs, not its items.** It records the asymmetry between what a session saw, meaning every file read and command output, and what the maintainer saw, meaning the conversation. Every item must cite a source from that session; an item with no source is dropped rather than softened. That rule is what keeps the section from becoming a horoscope.

  Both are uncapped by an explicit decision rather than an oversight: nothing has measured how long either runs, and pre-constraining an unmeasured thing inverts the pruning rule of removing what went unconsulted. Both require "Nothing material." or "Nothing surfaced." to be written rather than the section omitted, because an empty section and a skipped one are indistinguishable. Two Log Self-Check items enforce presence and the source rule. Deep mode only.

- **Lifecycle invariant 9: a spec's `status` and its acceptance-criteria checkboxes must agree.** A `fulfilled` spec must have every AC checkbox ticked, and a `draft` spec must have none. `scripts/doc-lifecycle-check.py` now enforces mechanically what the corpus had been maintaining by discipline alone: measured immediately before the rule was written, 8 fulfilled specs stood at 52 of 52 ticked and 8 draft specs at 0 of 61. The record was already perfect and guarded by nothing, which is the reason to build the fixture while it still is rather than after the first drift.

  `committed` and `superseded` are deliberately unchecked. `committed` is the one status a spec legitimately holds while its implementation plan is mid-execution, so a partial tick count there is the correct state and not a defect; a rule that flagged it would fire falsely on the first effort that ticks a criterion before flipping status, and would be removed the week it shipped.

  Invariants 8 and 9 share one regex rather than two. The checkbox pattern gained a capture group for the state character, so invariant 8 counts the lines and invariant 9 reads their state, and the two cannot drift into disagreeing about what an acceptance criterion is.

  Proved the way this repository requires: dropping the check from `run_all_checks()` makes the wiring self-test fail naming the missing marker, unticking one criterion in a real fulfilled spec makes the gate exit 1 naming that spec, and ticking one in a real draft spec does the same. A gate that cannot fail is not a gate.

- **`scripts/version-parity-check.py`, and a CI step that runs it.** Every version a tracked document claims must equal the version the repository declares: a skill's `metadata.version` in `skills/<name>/SKILL.md`, and the plugin's `version` in `library.json`. Four structured claim locations are read, and only those four: the root `README.md` Skills table, the `docs/status-skills.md` At a glance table, each `docs/skills/<skill>/README.md` `**Version:**` line, and the `**Plugin version:**` line on the status page.

  This closes the gap v0.5.3 exposed, and the gap was wider than the record of it suggested. The "bidirectional drift check" believed to cover this is Check 4 of `skills/plab-wrap-session/references/hygiene-sweep.md`, a bash recipe inside a skill reference. **CI has never run it**, because it is not a committed script and no workflow invokes it, so a stale version reference could sit on `main` through any number of green pull requests until somebody happened to wrap a session. And it asks a different question anyway: it compares each skill's own version against its value at the last tag, and never reads the version numbers written in the documentation. Check 4 is unchanged and still useful; this gate covers what Check 4 was mistakenly believed to cover.

  Deliberately structural rather than a version-string sweep. D-12 (path-citation precision) measured what happens when a prose rule is mechanized literally: 13 flags, 11 false positives. Version-shaped strings in these documents are overwhelmingly historical and correct precisely because they do not match the current version, so a fixture asserts that a `0.9.0` in a history table is ignored.

  A claim location that yields no claims at all is **BROKEN**, not clean. If the table shape or the `**Version:**` label changes, the matcher goes blind, and a gate that reports clean because it can no longer see is the failure this repository has already hit twice, with the empty `git tag -l` in v0.5.2 and with `AGENTS.md` never loading.

  Proved against the real defect: bumping `plab-spec`'s `metadata.version` and touching no documentation makes the gate exit 1 naming all three stale claims, which is the v0.5.3 defect verbatim. Blinding the README table makes it exit 2 rather than 0. Dropping a check from `run_all_checks()` makes the self-test fail naming the dropped location.

### Fixed

- **Four dangling citations in two shipped skills.** `skills/plab-spec/SKILL.md` lines 71 and 73, and `skills/plab-init-project/references/folder-spine.md` lines 35 and 123, all pointed at `docs/internal/planning-artifact-model.md`, which did not exist in this repository. The document had been written in a private library and never migrated, and the broken pointers survived the migration unnoticed. It is recovered here and amended for this repository rather than copied: every path, skill name and layout that described the old library is corrected, the HOW stage is named as the implementation-plan template rather than a skill that does not exist here, and D1 gains an as-built table recording three implementation notes that describe a flat `specs/` split superseded by per-effort folders. The decision itself is unchanged and the table is appended rather than edited, because a decided record is append-only.

  Landing the file at the cited path makes all four citations resolve **without editing any file under `skills/`**, so no skill version moved and no drift check was tripped.

- **The series legend did not say that three things are numbered with a D.** `D-07` is an effort, `D1` is a decision record inside `planning-artifact-model.md`, and MADR records scaffolded by `/plab-init-project` are numbered separately again. One line in `docs/internal/release-plans/README.md` now distinguishes them: an effort ID always carries a hyphen and a slug, an in-document decision never does.

- **The spec frontmatter reference omitted a field the gate enforces, and two things claimed to be authoritative.** `skills/plab-spec/references/frontmatter-schema.md` did not document `linked-release`, which is in `docs/internal/schemas/spec.schema.json` and therefore checked by CI, and its `linked-plan` example still used the pre-D1 `docs/internal/efforts/` path. Both corrected. The implementation-plan template called the prose file "the authoritative field list" while CI validates against the JSON Schema; the template now names the schema as authoritative and the prose file as its human-readable companion, so only one thing claims the title.

### Changed

- **`main` is protected, so the branch rule is now a mechanism rather than a discipline.** `AGENTS.md` has always said work happens on a branch and never commit to `main` directly. That is now enforced: a pull request is required, the Standard and Document-lifecycle checks must pass, the branch must be up to date, force pushes and deletions are blocked, and the rules apply to administrators.

  Worth recording precisely, because the obvious description of the gap is wrong: **CI was never bypassed by a direct push.** The Gate workflow already triggered on `push: branches: [main]`, so it ran either way. It simply ran after the commit had landed, which made it a report on something that had already happened rather than a gate on something about to. Protection is what converts it.

  Approvals are set to zero, because a single-maintainer repository requiring one would be unmergeable. Linear history is deliberately **not** required: PR #8 used a merge commit on purpose so `scripts/doc-lifecycle-check.py` could keep citing `b6c173a` for invariant 9's ninth canary, and requiring linear history would have quietly outlawed that.

## [0.5.3] - 2026-09-01

### Fixed

- **The library no longer references a plugin it does not ship with.** `plab-spec` (1.3.3) and `plab-release-plan` (1.5.1) both pointed at `/superpowers:writing-plans` for the implementation-plan stage, on the assumption that a separate plugin would be installed. A sweep found fourteen live pointers across nine files: both skills' descriptions and when-not-to-use lists, `plab-spec`'s task-summary reference, `plab-release-plan`'s stale-plan gate **failure message**, `AGENTS.md`, the root `README.md`, both usage READMEs, `docs/status-skills.md`, and the generated manifest.

  All now name `docs/internal/release-plans/implementation-plan-template.md`, which is in this repository. The failure-message instance was the worst of them: a gate that fires and then instructs the reader to run a command that does not exist has not really fired.

  The same sweep confirmed `/superpowers:writing-plans` was the **only** external plugin referenced anywhere in the library, so this closes the category rather than one instance of it. The standing rule it establishes: a skill here names no skill it does not ship beside.

- **A retracted rationale removed from `docs/skills/plab-spec/README.md`.** It still claimed `superpowers` owns the default spec-writing triggers, a justification `skills/plab-spec/HISTORY.md` recorded as not surviving inspection when 1.3.0 removed the flag it was defending. The sentence also sat directly beneath a paragraph explaining that the flag was gone.

### Added

- **`docs/internal/release-plans/implementation-plan-template.md`.** The shape all sixteen tracked implementation plans already share, written down: `Completion Status`, numbered phases, `CI and Documentation Coverage`, `Rollback`. Derived by counting sections across the sixteen rather than by preference. Its frontmatter block is fenced so the schema gate skips the template rather than validating it as a document.

- **An `Engineering discipline` section in `AGENTS.md`,** and a one-line `CLAUDE.md` importing it. `AGENTS.md` is the cross-harness convention but Claude Code does not read it, so the repository's own working rules were reaching Codex and not Claude.

## [0.5.2] - 2026-08-28

### Added

- **Document lifecycle gates, the half nothing checked before.** Three deterministic checks now run in CI, cost nothing per run, and report `clean`, `findings`, or `broken` rather than passing quietly when they cannot do their job.

  `scripts/frontmatter-check.py` validates every spec, implementation plan, and release plan against a committed JSON Schema. The schemas live in `docs/internal/schemas/` and are plain draft 2020-12 documents, so they are the durable artifact: any conforming validator can read them, and the Python checker is replaceable without touching them.

  `scripts/doc-lifecycle-check.py` covers the eight invariants a per-file schema fundamentally cannot see, because they need two or more files or the git state: supersession symmetry, target-version and sequence uniqueness, a spec still unfinished for a version that already shipped, link resolution, folder-to-id agreement, release-plan counts, and acceptance-criteria counts.

  `scripts/gen-release-index.py` generates `docs/internal/release-plans/INDEX.md`, the first view of every effort across every release. It is derived from frontmatter and never authored, and CI fails if the committed copy is stale.

- **An effort-series legend** in `docs/internal/release-plans/README.md`. Six series letters had been in use with nothing anywhere saying what any of them meant, which is the most likely thing "the folder is hard to navigate" actually referred to. A new letter must be registered there before use; the index generator refuses to emit a blank legend cell.

### Fixed

- `plab-wrap-session` 1.6.2: three false-positive classes in the path-citation gate, plus line-anchored citations such as `file.md:42`, which are now stripped to the underlying path before resolution. The proof corpus grew from 11 entries to 40. Against a real session log the gate reports 9 findings where it reported 13, and all 9 are genuine.

### Changed

- `plab-spec` 1.3.2: supersession is documented as symmetric. A superseded spec carries `superseded-by`, the replacing spec carries `supersedes` pointing back, and the new cross-file gate enforces the pair. Documentation only; no skill behavior changes.

### Notes

Every gate added here was built, then attacked by independent reviewers, then repaired. That pass found a blocker worth naming: the released-but-unfulfilled check was silently vacuous whenever `git tag -l` returned nothing, which is exactly what a default `actions/checkout` produces. It would have passed in CI forever while looking healthy locally. The check now refuses to run against an empty tag list unless `--allow-no-tags` is passed, and the CI job fetches full history for the same reason.

## [0.5.1] - 2026-08-28

### Fixed

- **Tracked specs no longer cite gitignored files.** Every spec pointed at working notes under `_local/`, which is never committed, so 102 links across 21 files resolved for nobody who cloned the repository and for the author only on one machine. Each citation is replaced by a plain-language description of what the source was and what it said, following the convention Kubernetes KEPs, Rust RFCs and Python PEPs share: the rationale lives inside the document. The Sources and Evidence entries already carried that substance; they simply also carried a path.

  Runtime paths are deliberately untouched. `_local/_session-logs/`, its `_capture/` and `_superseded/` subdirectories, and the capture filename pattern are the product's own interface rather than private content, and a spec about session-log archiving has to name the directory it archives into. 54 such references remain and are correct.

- **A machine path containing the maintainer's username** was published in `CI-01`'s spec. Replaced with a description of the hook it named. Found by the repository's own PII gate.

- `plab-spec` 1.3.1: `linked-effort` is documented as a string rather than a path, and the schema now states the rule that was previously only implicit: a tracked artifact must not cite an untracked one. Documentation only; no skill behavior changes.

## [0.5.0] - 2026-08-27

### Changed

- **`plab-spec` (1.3.0) and `plab-release-plan` (1.5.0) no longer carry `disable-model-invocation`.** Both are now auto-discoverable. Their descriptions carry explicit trigger phrases and explicit do-NOT-fire clauses in place of the binary gate, which is the mechanism that took `plab-continue-session` from over-triggering to firing correctly. A description can distinguish a request from a passing mention; a boolean cannot.

  The flag had a measured cost: an approved invocation was refused twice in one session, and because neither skill had ever run in this repository, the misfire risk the flag guarded against was never actually observed. `plab-spec` 1.2.1's stated rationale also did not survive inspection: it cited superpowers owning the spec-writing triggers, but the installed superpowers plugin ships seventeen skills and none of them is a spec skill.

  **`plab-init-project` keeps its flag.** It writes into a repository root and its triggers ("init", "set up") are genuinely ambiguous.

  Typing `/plab-spec` or `/plab-release-plan` still works and is still the precise way to invoke either. No skill body, subcommand, gate, or contract changed. Always-on description cost rises by roughly 385 tokens per session, the price of two descriptions that were previously not loaded.

- **Release-plan folders are named by sequence and theme, not by version** (`plab-release-plan` 1.5.0). `plan_v0.5.0/plan_v0.5.0.md` becomes `plan_05_reconcile-at-resume/plan.md`; the version moves to a `target-version:` frontmatter field beside a new immutable `sequence:`. A version in a path is a prediction semver is free to invalidate: two unplanned minors in eight releases each forced a folder rename plus a cascade of rewrites, 358 references then 140. Under the new scheme both are a one-line edit. The CLI is unchanged: `--create vX.Y.Z --theme "..."` still takes a version and now derives the folder from it, and every subcommand still resolves `vX.Y.Z` by reading `target-version:`. Two new refusals guard the invariant: `--create` refuses a version another plan already claims, and resolution refuses a version matching more than one folder.

- **The no-hard-wrap rule now covers every document class, not just session logs** (`AGENTS.md`). Measured: a one-word edit inside a 75-column hard-wrapped paragraph produces a 4-line diff against 1 for either one-paragraph-per-line or one-sentence-per-line, because the reflow cascades, and any grep for a phrase crossing the wrap boundary returns nothing. Fixed-width wrapping loses on the only argument made for it. `docs/status-skills.md` is unwrapped to match.

## [0.4.3] - 2026-08-26

### Changed

- Install instructions in the root README and all eight skill usage docs now name the marketplace
  `prisant-labs` rather than `agent-plugins`. The marketplace manifest at
  `prisant-labs/agent-plugins` was renamed so its registered name matches the organisation instead
  of the repository, which is the convention the sibling `product-on-purpose` marketplace already
  used. The repository slug is unchanged, so `/plugin marketplace add prisant-labs/agent-plugins`
  still reads the same; only the install target changes, to
  `/plugin install prisant-utilities@prisant-labs`. An existing install registered under the old
  name must be removed and reinstalled, because a marketplace is keyed by its manifest name.

### Added

- `docs/status-skills.md`, a status reference covering all eight skills: version, invocation mode,
  argument hint, default behaviour, output location, and the setup each one requires, plus the
  shared plugin-root dependencies and the conventions in force. Every value is derived from
  `library.json`, `manifest.generated.json`, and skill frontmatter rather than authored, so the
  file is regenerable and should not be hand-maintained.

## [0.4.2] - 2026-08-25

### Fixed

- CI's SARIF upload step moved from `github/codeql-action/upload-sarif@v3` to `@v4`. The v3 action
  targets Node 20, which GitHub runners now force onto Node 24 with a deprecation warning, and the v3
  line itself is scheduled for deprecation in December 2026. Both warnings appeared on this
  repository's first successful CI run. No skill changes; the plugin surface is untouched.

## [0.4.1] - 2026-08-25

### Fixed

- Session-log body prose is no longer hard-wrapped. Nothing ever asked for it: no rule existed in the
  skill, the template, or the repository, and logs written a week apart drifted from 800-character
  paragraphs to a hard wrap near 100 columns. Hard wrapping makes an edit reflow the whole paragraph
  so diffs show paragraph-sized churn, makes the continuation prompt arrive ragged when pasted into a
  chat box, and makes any grep for a phrase longer than the wrap width silently fail. The rule is
  stated once and is deliberately not a self-check gate, because nothing can mechanically tell a
  wrapped line from a short sentence.
- The CI pin moved from `agent-skills-toolkit@v1.16.1` to `v1.16.2`. The v1.16.1 Action failed before
  it graded anything: its `Set up Node` step pointed `cache-dependency-path` at an absolute path
  outside the workspace, which `setup-node` treats as an error, so the composite step failed and
  skipped the gate. The first CI run this repository ever made hit it. Fixed upstream in v1.16.2.

## [0.4.0] - 2026-08-25

### Added

- The repository has continuous integration for the first time. `.github/workflows/gate.yml` runs on
  every pull request and every push to `main`, grading against the Advanced Skill Library Standard
  via the pinned toolkit Action (with SARIF uploaded to the Security tab) and running a repo-wide
  em-dash and en-dash check. Until now the conformance gate was a command in `AGENTS.md` that a human
  had to remember, and the dash rule was enforced only by a hook on one machine, which a copy-based
  migration bypassed once at 31 dashes. CI reports; it never fixes, bumps, or tags.
- `plab-wrap-session` now notices when the newest existing log covers the same arc as the session
  being wrapped. The new log declares the supersession in Summary and offers to archive the older
  file to `_local/_session-logs/_superseded/`, under the same per-action confirmation the hygiene
  sweep uses. Two real logs five hours apart previously covered the same work with nothing noticing.
  Discovery already excluded the directory, so resume is unaffected.
- Capture-lite records are now read, not just written. A SessionEnd hook has been writing JSONL
  records that nothing consumed. `plab-wrap-session` now reports how many sessions since the last log
  were never wrapped, in Outstanding Issues; `plab-continue-session` surfaces a one-line orientation
  on its no-log-found and stale-log paths. Both stay silent when the capture store is absent, which
  it will be on any machine without the optional hook.
- Both detector-backed `plab-wrap-session` Log Self-Check gates now run committed, canary-verified
  scripts that report one of three states: clean, findings, or broken. `scripts/dash-check.py` and
  `scripts/path-citation-check.py` each prove their detector against a canary corpus before scanning,
  and a gate reporting broken blocks the log exactly as findings does. They replace improvised checks
  that silently failed open three times in one week, each reporting success while structurally
  incapable of detecting anything.

### Fixed

- The Waiting on You section is an enforced contract again. It had diluted into a suggestion list:
  one real log carried five items, four prefixed "Optional:", with a genuine blocker open since July
  hidden among them, and it passed every self-check. Only items blocked on the maintainer belong
  there now, each carrying a `(blocked since YYYY-MM-DD)` marker, with two new gates rejecting the
  observed failure. Optional context moves to a new Parked section. Unresolved items carry forward
  across wraps with their original dates, so a blocker's age no longer resets every session, and
  `plab-continue-session` displays them oldest-blocked-first.
- `plab-wrap-session` `resumed-from:` is now written only when `/plab-continue-session` performed the
  resume in the current session, never back-filled from memory, and omitted rather than guessed when
  no resume occurred. Both real logs in this repository carried an unresolvable cross-repo value from
  back-filling.
- The `plab-wrap-session` pre-wrap hygiene sweep's documentation-drift check now looks in both
  directions. It caught a version bumped with a stale usage doc, but not the inverse, content changed
  with no version bump, which is the drift that actually shipped in this repository. It now also
  reports a skill whose `HISTORY.md` has no entry for the version it currently ships.
- The `plab-wrap-session` path-existence Log Self-Check gate flagged bare filenames mentioned in
  prose as missing paths. In one observed wrap 6 of its 7 flags were false positives. It now checks
  only citations that assert a location: one carrying a path separator must exist as written, and a
  backtick-wrapped citation with no separator is resolved against the repo root and passes silently
  when it does not resolve.

## [0.3.0] - 2026-08-24

Three skills arrive from a private library, and the documentation correctness pass that preceded them.

**What changes for you.** The plugin now covers the whole path from an empty repository to a taggable
release. `plab-init-project` 1.3.0 scaffolds agent infrastructure into a repo, `plab-spec` 1.2.1
writes the acceptance criteria a feature is judged against, and `plab-release-plan` 1.3.0 aggregates
effort folders into a release and decides whether it can ship. All three were previously private, so
`docs/internal/release-plans/` in this repository documented a skill nobody could install; that is now
fixed. Five skills becomes eight.

**All three are manual-invocation only.** They ship with `disable-model-invocation: true` and never
fire on their own: type `/plab-spec`, `/plab-release-plan` or `/plab-init-project`. Two of them
auto-triggered in the private library and no longer do, which is a deliberate behavior change.
"spec", "init", "set up project" and "plan the release" are ordinary words in conversation about a
repository, and all three skills write files into it.

**What does not change.** The five existing skills are untouched by the migration. No skill gained or
lost a capability, and `plab-guide` 2.2.2 remains correctness only.

### Added

- `plab-spec` 1.2.1, migrated from a private upstream. Writes a `spec.md` into a per-effort folder
  under `docs/internal/release-plans/`, with frontmatter, an agent-updated Task Summary block,
  numbered acceptance criteria each cited to a source, and an append-only Revisions section.
- `plab-release-plan` 1.3.0, migrated from a private upstream. Five subcommands (`--create`,
  `--promote`, `--demote`, `--update`, `--gate`) over a release folder whose aggregation table is
  generated from disk rather than hand-edited. Refuses to add or modify acceptance criteria.
- `plab-init-project` 1.3.0, migrated from a private upstream. Three profiles (`minimal`, `standard`,
  `public`), non-destructive and idempotent. Pairs with the session skills already in this plugin:
  it scaffolds the `_local/_session-logs/` that `plab-wrap-session` writes and `plab-continue-session`
  reads.

### Changed

- References inside the three migrated skills now name what exists in this environment. The retired
  `jp-implementation-plan` becomes `/superpowers:writing-plans` in nine places, the retired
  `jp-skill-builder` becomes `/skill-creator`, and sibling references name their `plab-` twins.
  `plab-init-project`'s AGENTS.md and CLAUDE.md seed templates named session skills that a reader
  outside the maintainer's machine could not install; they now name `plab-wrap-session` and
  `plab-continue-session`.
- `docs/internal/release-plans/README.md` and `release-checklist.yaml` pointed at `/jp-release-plan`,
  a skill no reader of this public repository could install. Both now name `/plab-release-plan`.
- The plugin description in `library.json` enumerated four capability areas and now covers
  specification, release planning, and project scaffolding as well.

### Fixed

- `plab-guide` 2.2.2: `scripts/regression-test.sh` asserted a 2-page render and would have failed a
  legitimate 1-page baseline, contradicting the one-or-two-page contract `render-pdf.sh` has enforced
  since v2.0.0. It now accepts 1 or 2 pages and reports the actual count.
- `plab-guide` 2.2.2: `references/quick-ref-html-patterns.md` repeated "exactly 2 pages" in its G-8
  row and listed a 1-page result as a page-count failure. The per-page ink floor is the gate; page
  count alone is not.
- `plab-guide` 2.2.2: `SKILL.md`'s failure table said "Em-dash leaks past sweep". There is no sweep.
  G-11 is a written-discipline rule verified by grep, as the same file's gate list already stated.
- Usage docs for all five skills carried stale version lines, by as much as three minor versions
  (`plab-guide` read 1.6.0 against a shipped 2.2.1). The root README table was stale for the two
  skills v0.2.0 bumped.
- `plab-ai-review` usage docs documented two modes. `--close` shipped in 1.2.1 and was undocumented,
  along with its `--backlog` flag, its confirmation gate, and its refusal to overwrite an existing
  archive.
- `plab-guide` usage docs documented `scripts/em-dash-sweep.sh`, which does not exist in this
  repository and described an auto-rewrite that gate G-11 explicitly rejects. Replaced with the grep
  check the gate actually uses. Six further places claimed a fixed 2-page output.
- `plab-strategy-brief` usage docs did not mention output location anywhere, though
  `_output/plab-strategy-brief/` has been the default since v1.0.1.
- The root README's session-log section did not mention that `--organize` files closed months into
  `YYYY-MM/` subfolders, or that resume reads the flat store and those folders as one set.


## [0.2.0] - 2026-08-18

Session-log stores can now be archived by month without breaking resume.

**What changes for you.** `/plab-wrap-session --organize` files logs from closed months into
`YYYY-MM/` subfolders, so a store that has been running for a year is browsable again. The current
and previous month stay flat, nothing moves without your confirmation on that specific plan, and
nothing is ever deleted. You do not have to remember the command exists: deep and final wraps now
report unfiled logs and offer to file them, the same way they already offer to push a commit or fix
a stale version line. Resume keeps working throughout, because `/plab-continue-session` reads the
flat store and the month folders as one set ordered by filename.

**What does not change.** New logs are still written flat to
`_local/_session-logs/YYYY-MM-DD_HH-MM_<llm>_<title>.md`. No mode, section, template, or frontmatter
field moved, and nothing you have already written needs migrating. Archiving is opt-in and
reversible: the organizer only ever moves files.

**One ordering note.** The reader had to learn month folders before anything could be filed into
one, so both skills ship together in this release. A store organized by this version and opened by an
older install would read as empty; that case now reports the version skew and points at
`/plugin update` rather than offering to start fresh.

### Added

- `plab-wrap-session` 1.5.0: `--organize` mode, backed by
  `skills/plab-wrap-session/scripts/organize-logs.py`. Dry run by default, idempotent, move-only,
  never deleting. The month comes from the filename prefix rather than mtime, because mtime is wrong
  after any copy or restore and the filename is the log's identity. Collisions skip the file and exit
  non-zero instead of overwriting.
- `plab-wrap-session` 1.5.0: hygiene sweep Check 5 reports unfiled logs and proposes filing them
  under the existing per-action confirmation protocol. The check calls the organizer in dry run, so
  the sweep's read-only detection phase and the operation it proposes are one code path.
- `plab-wrap-session` 1.5.0: `skills/plab-wrap-session/scripts/test-organize-logs.py`, 34 fixture
  checks with a pinned date covering dry-run inertness, the hot window across a year boundary,
  idempotence, `_capture/` isolation, collision safety, a missing store, and the discovery contract
  itself.
- `plab-wrap-session` 1.5.0: a worked example with real captured output at
  `skills/plab-wrap-session/examples/organize-logs-walkthrough.md`.
- `plab-continue-session` 1.3.0: discovery reads `YYYY-MM/` month folders alongside the flat store as
  one pooled corpus. It is a date-shaped allowlist exactly one level deep, never a recursive walk, so
  `_capture/` and any future deliberately-hidden subdirectory stay outside the corpus.
- `plab-continue-session` 1.3.0: an empty top level with month folders present is now reported as
  version skew, naming `/plugin update`, instead of "no prior session log found".

### Fixed

- `plab-continue-session` 1.3.0: a stray Markdown file in the log store could be resumed from.
  Selection globbed `*.md` and took the lexically last name, so a `README.md` or `notes.md` outranked
  every dated log. Both shell pipelines now match the `YYYY-MM-DD_` prefix. Latent until now;
  `--organize` makes it reachable by establishing that the store may hold non-log Markdown.

### Changed

- `plab-wrap-session` 1.5.0: session logs are cited by filename, never by directory-qualified path,
  in `resumed-from:` and in prose alike. A path-qualified reference breaks when the log is archived;
  a filename does not, which is why archiving needs no link-rewriting step.

## [0.1.2] - 2026-08-18

Correctness and bookkeeping. No new capability, but two of these change day-to-day behaviour.

**What changes for you.** Asking "what did we do?" or "where were we?" no longer risks launching a
session-log write or a resume ritual. Both skills listed those status questions as triggers, so a request
for an answer could be answered with a procedure instead. You now get the answer. Separately, quick-mode
and blocked-mode wraps stop producing logs that the wrap skill's own self-check rejects, so the fast path
is usable rather than quietly emitting output that fails its own gate. The wrap skill's description is 34
characters shorter, which is context you stop paying for in every session.

**What does not change.** No mode, section, template structure, or output format moved. A log written by
1.4.0 reads identically to one written by 1.4.1, and `/plab-continue-session` parses both the same way.
Nothing you have already written needs migrating.

### Fixed

- `plab-continue-session` 1.2.1: the skill body listed "where were we" and "what were we doing" as
  triggers, contradicting its own description, which refuses to fire on status questions. A narrowed
  description stops the skill firing; a stale body told it to proceed once it had. Both now agree.
- `plab-wrap-session` 1.4.1: dropped "what did we do" from the trigger list. It is a request for an
  answer, not a request to write a session log, and it is the same over-trigger class already removed
  from `plab-continue-session`. The description is shorter as a result.
- `plab-wrap-session` 1.4.1: the Quick and Blocked session-log templates omitted `machine:`, and the
  SKILL.md frontmatter block omitted `type:`, both of which the frontmatter schema places in Tier 1 and
  the skill's own self-check requires in every mode. An agent following either light template produced a
  log the skill would reject.
- Usage documentation for `plab-continue-session` opened with a description two rewrites out of date and
  documented a field list that predated the 1.2.0 extraction changes.
- Removed ten dangling references to `/jp-init-project`, `jp-implementation-plan`, and `jp-skill-builder`
  across both skills' usage docs. None of the three ships in this plugin. The v0.1.1 sweep looked for
  private folder paths and did not look for private skill names.

### Notes

`plab-continue-session`'s description was rewritten on 2026-08-17 in commit `38a75f0` and shipped inside
v0.1.1 with no version bump, no history entry, and no changelog line. Its 1.2.1 history entry records that
retroactively. The hygiene check that would have caught it is one-directional and is scheduled for a
later release.

## [0.1.1] - 2026-08-17

### Fixed

- Removed four dangling references to a private development folder (`docs/internal/agent-skills-published/...`) that the migration's mechanical rename had rewritten rather than deleted. Affected `plab-guide`'s theme reference and regression script, and the `plab-guide` and `plab-ai-review` usage docs.
- `scripts/regression-test.sh` no longer points at a path that cannot exist in this repository. Baseline bundles are not shipped; the script now accepts your own via `PLAB_GUIDE_EXAMPLES_DIR` and exits 2 with a clear message when absent.
- `references/quick-ref-theme.md` described two source-of-truth templates kept in sync, when only one ships here.

## [0.1.0] - 2026-08-17

### Added

- Initial public release with five skills: `plab-wrap-session` 1.4.0, `plab-continue-session` 1.2.0, `plab-strategy-brief` 1.1.1, `plab-guide` 2.2.1, `plab-ai-review` 1.2.1.
- Shared plugin-root utilities: `lib/render-mermaid.py`, `references/diagrams.md`, `references/decisions-section.md`.
- Per-skill usage documentation under `docs/skills/`.
- `library.json` as the canonical manifest, with native Claude Code and Codex manifests generated from it.

### Notes

Skills were previously developed in a private library and carry their version numbers forward unchanged. Per-skill `HISTORY.md` files start at the migrated version and record what changed for public release; earlier history remains private.

The default output root for generated artifacts is `_output/<skill-name>/`, replacing a brand-named folder used privately.
