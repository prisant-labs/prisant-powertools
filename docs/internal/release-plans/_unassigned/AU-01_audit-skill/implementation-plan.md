---
id: AU-01
title: "Implementation plan: plab-audit, repository appraisal, findings and roadmap"
type: implementation-plan
status: in-progress
created: 2026-09-19
updated: 2026-10-26
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 7
---

# Implementation plan: plab-audit

**For whoever executes this.** Steps use checkbox syntax and phases run in order. Where a step depends on a line number, re-verify it first; a sibling effort landing in between will have moved it.

**Goal:** `/plab-audit <path>` produces a five-file bundle appraising a repository, listing what is wrong with file-level citations, and ranking what to do next, with a coverage statement declaring what was and was not examined.

**How autonomous this actually is, stated plainly.** Phases 4 through 7 are mechanical: exact files, exact commands, exact before-and-after text. Phases 2 and 3 are **authoring work**, and no plan can make them mechanical.

That is deliberate rather than a gap. The parent brief's next step 2 says do not write `SKILL.md` before the hand-run fixture exists, because the fixture *is* the specification for the skill. Pre-writing the skill in the planning session would invert the evidence: the skill would specify the fixture instead of the other way round. So Phase 2 produces the specimen by hand, Phase 3 writes the skill from it, and only then does the plan become a sequence of copies and commands.

Budget accordingly: Phase 2 is a real audit of a 14-skill repository, and Phase 3 is authoring ten files. Expect those two to consume most of a session between them.

## Preconditions, verify before starting

- [x] **v0.5.5 has shipped**, 2026-09-20, merge commit `9acae7d`, tag `v0.5.5`, GitHub Release published automatically from the CHANGELOG section.
- [x] Working tree clean, `main` in sync with `origin/main`. Verified 2026-09-20.
- [x] A branch exists for this work: `feat/plab-audit`, first commit `9d0dfc3`.

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | Series letter registered, fixtures confirmed reachable | N/A (prerequisite) | agent | **Done** 2026-09-20, `9d0dfc3` |
| P2 | Hand-run fixture audit exists and is the output specification | N/A (produces the specimen) | agent | **Done** 2026-09-20, `_local/ideas/audit/draft/fixture/` |
| P3 | Draft skill tree authored under `_local/` | AC-1 to AC-15 authored | agent | **Done** 2026-09-20, 10 files |
| P4 | Skill installed and manifests regenerated | AC-1, AC-13 | agent | **Done** 2026-09-20 |
| P5 | Documentation wired | N/A (documentation) | agent | **Done** 2026-09-20 |
| P6 | Gates pass and the canary is proven to fail | AC-4, AC-5, AC-14, AC-15 | agent | **Done** 2026-09-20, sample committed and mutation-tested |
| P7 | Dogfood run, degradation test, release | AC-2, AC-3, AC-12 | agent | In progress: steps 1 to 4 and 7 to 10 done; step 5 waived and optional; step 6 waived permanently, 2026-10-06 |

---

## Phase 1: Series letter registered, fixtures confirmed

**Goal:** The effort ID `AU-01` is a legal identifier in this repository, and both fixture repositories are present and readable.

**Files:** `docs/internal/release-plans/README.md` (modify).

**Fulfills:** N/A (prerequisite).

**Steps:**

**Corrected on execution, 2026-09-20.** This phase named one file and needed two. The legend's only machine-readable home is `SERIES_LEGEND` in `scripts/gen-release-index.py`, which states at its own line 15 that the legend "is documented nowhere machine-readable except this script"; the README table is prose beside it. Editing only the README would have registered nothing, and this phase's stated verification, `frontmatter-check.py` and `doc-lifecycle-check.py` both exiting 0, would still have passed, because neither reads the legend. What proved it was `gen-release-index.py --check` going to exit 1 on the script edit and back to exit 0 after regeneration. The schema needed no change: `^[A-Z]{1,2}-\d{2,4}$` already accepts a two-letter series, with `CI-` as precedent.

1. [x] Open `docs/internal/release-plans/README.md` and find the series legend table under the heading `### The series legend`. It currently has six rows: `D-`, `W-`, `C-`, `CI-`, `A-`, `H-`.
2. [ ] Add one row to that table, after the `H-` row:

   ```
   | `AU-` | Audit-skill roadmap item | `_unassigned`, then a release folder |
   ```

   This must happen **before** any effort folder named `AU-01_*` exists. The index generator refuses to run rather than emit a blank cell for an unknown letter, as that README states directly.
3. [ ] Confirm both fixtures are present and are the expected type:
   - `E:/Projects/prisant-labs/Nonfiction` - expect `library.json` and `.claude-plugin/plugin.json` present, so type `agent-plugin`.
   - `E:/Projects/prisant-labs/repo-sync-tool` - expect `src-tauri/` or `tauri.conf.json` present, so type `tauri`.
4. [ ] Record whether `cargo` is on PATH. Both outcomes are usable: present means Phase 7 runs the real Tauri pack, absent means Phase 7 is the degradation test for AC-12. Do not install it to force one path.

**Verification:**

```bash
python scripts/frontmatter-check.py && python scripts/doc-lifecycle-check.py
```

Both exit 0. The legend addition touches no frontmatter, so a non-zero exit here means something unrelated is already broken and must be resolved before continuing.

---

## Phase 2: Hand-run the fixture audit

**Goal:** A complete audit of nonfiction-studio exists, produced by hand. It is the specification and the test fixture for everything built afterwards.

**Files:** `_local/ideas/audit/draft/fixture/` (create): `README.md`, `appraise.md`, `findings.md`, `roadmap.md`, `evidence.md`.

**Fulfills:** N/A, but it is the specimen every acceptance criterion is later checked against.

**Do not skip or shorten this phase.** The parent brief says explicitly: do not write `SKILL.md` before this exists. Both hand-run audits that preceded it changed a real decision, and the method they used is what is being codified. Writing the skill first inverts the evidence.

**Steps:**

1. [ ] Read `_local/audits/2029-08-29_sol-xhigh/` in full, all four files. That is the closest existing specimen. Note the folder slug says 2029 where the body says 2026-08-29; the slug is a typo, do not propagate it.
2. [ ] Audit `E:/Projects/prisant-labs/Nonfiction` by hand, deterministic layer first:
   - Run the toolkit conformance gate against it, and this repository's own scripts where they apply.
   - Record every command and its exit code as you go. This becomes `evidence.md` and is not reconstructable afterwards.
3. [ ] Write `appraise.md` carrying all six sections the spec requires: what this is, a current-status table, recent history, what it is good at, what the repository's own planning artifacts declare as next, and a declared-plans-versus-actual-state comparison.
4. [ ] Write `findings.md`, severity-ranked, every entry carrying a file path and a line number where line-scoped.
5. [ ] Write `roadmap.md` with the labelled break: evidenced items above, each citing a finding identifier and naming a mechanization rung, and a section below headed so it plainly states nothing beneath it traces to evidence.
6. [ ] Write `evidence.md` from the running record: repository snapshot, every command with its exit code, what was read in full, what was sampled, what was skipped and why, and a limits-and-confidence closing section.
7. [ ] Write `README.md` as the index and executive verdict.
8. [ ] Record the wall-clock time and rough context consumption of this run in `evidence.md`. This is the measured cost ceiling the spec's non-functional requirement refers to, replacing the parent brief's unmeasurable "minutes and pennies".

**Verification:**

Open `_local/ideas/audit/draft/fixture/roadmap.md` and confirm by reading: every item above the break cites a finding identifier that resolves to a real entry in `findings.md`, and no item below the break cites one. Then confirm `evidence.md` names at least one thing that was skipped, with a reason. A coverage statement that claims total coverage on a 14-skill repository is not credible and means the audit was not honest about sampling.

---

## Phase 3: Author the draft skill tree

**Goal:** A complete `plab-audit` skill exists under `_local/`, reviewable as files before anything is installed.

**Files:** create, all under `_local/ideas/audit/draft/skills/plab-audit/`:

```
SKILL.md
HISTORY.md
references/output-bundle.md
references/coverage-statement.md
references/calibration.md
references/type-packs/agent-plugin.md
references/type-packs/tauri.md
references/type-packs/generic.md
references/lenses/docs.md
scripts/bundle-check.py
```

**Fulfills:** AC-1 through AC-15, as authored content.

**AC-15 was added to the spec on 2026-09-20**, after Phase 2, as revision R-1. It requires that every finding be reconciled against the audited repository's recorded decisions before publication, and that the coverage statement name which decision records were read. It exists because the Phase 2 fixture withdrew 7 of 15 candidates at exactly that step, including the two highest-ranked, one of which recommended a change the audited repository had already tested and rejected with measured evidence. Three artifacts below change shape because of it: `SKILL.md` gains the reconciliation step, `references/coverage-statement.md` gains the decision-records section, and `scripts/bundle-check.py` gains an assertion that the section exists and is non-empty.

**Steps:**

1. [ ] Write `SKILL.md` frontmatter. It must carry `disable-model-invocation: true` (AC-1, maintainer ruling 2026-09-19) and `argument-hint: "<path> [--appraise|--audit|--roadmap] [--type=agent-plugin|tauri|generic] [--lens=docs] [--out <path>]"`.
2. [ ] Write the description. **This is the highest-stakes single artifact in the effort.** It must state what the skill does and when to use it, and carry do-NOT-fire clauses for: `cargo audit` and `npm audit` (dependency scanning), "audit log" and "audit trail" (unrelated sense), and "review this document" (that is `plab-ai-review`, and the maintainer ruled on 2026-09-18 that they are different jobs). Note that `disable-model-invocation: true` means the description no longer drives triggering, but it still drives the skill listing the maintainer reads.
3. [ ] Write `references/coverage-statement.md` **before** the pack files. The parent brief's next step 3 says design it first, and retrofitting it is painful. Its format is the Phase 2 fixture's `evidence.md`, generalized: repository snapshot, commands with exit codes, read versus sampled versus skipped, limits and confidence.
4. [ ] Write `references/output-bundle.md` defining the five files and, critically, the `roadmap.md` break: exactly one horizontal rule, a heading naming the section as questions the audit cannot answer, and an explicit sentence stating nothing below traces to evidence (AC-10).
5. [ ] Write `references/calibration.md` carrying the six weighted factors and the three explicitly unweighted ones, plus the mechanization ladder with its four rungs (AC-11).
6. [ ] Write `references/type-packs/agent-plugin.md`. Name **this repository's own scripts first** and third-party plugins only as optional accelerators with a stated fallback. The exact paths, verified 2026-09-19, because two similarly-named scripts live in different places and citing the wrong one stalls a run:
   - `scripts/check-dashes.py` - repo-wide dash policy, the one CI runs
   - `scripts/frontmatter-check.py`
   - `scripts/doc-lifecycle-check.py`
   - `scripts/version-parity-check.py`
   - `scripts/gen-release-index.py --check`
   - `check.mjs` and `description-score.mjs` from the toolkit at `E:/Projects/product-on-purpose/agent-skills-toolkit/`
   - `skills/plab-wrap-session/scripts/dash-check.py` and `skills/plab-wrap-session/scripts/path-citation-check.py` are **skill-scoped, not repo-scoped**. Do not invoke `path-citation-check.py`: it false-positives on every markdown inline link and its fix is an open item awaiting maintainer approval. Note it in the pack as unavailable-pending-fix rather than running it and recording noise.

   Record the ADR 0049 caveat beside the description score: a description whose `WHEN` pattern the English lexicon cannot match caps at 0.65 and cannot pass at any quality, so a 0.65 is checked before it is called a defect.
7. [ ] Write `references/type-packs/tauri.md` as a **full pack**, not a stub (maintainer ruling 2026-09-19): `cargo clippy`, `cargo audit`, `npm audit`, `tauri.conf.json` capabilities and CSP review, updater and signing configuration, icon and bundle assets. Each entry names the command, what a finding looks like, and what to record when the tool is unavailable.
8. [ ] Write `references/type-packs/generic.md`: git history and bus-factor statistics, structure, LICENSE and gitignore hygiene, manifest sanity.
9. [ ] Write `references/lenses/docs.md` bounded by AD-3 (docs lens boundary): onboarding path exists and is current, standards in force are recorded and recorded standards are still in force, examples exist for each public surface, human-facing documents judged on structure and wording while agent-facing documents are judged on token economy and load-bearing accuracy, release discipline documented. **Explicitly excluded:** version parity and drift, which stay in `plab-wrap-session` and the deterministic gates.
10. [ ] Write `scripts/bundle-check.py`, the skill's self-check. This is the artifact Phase 6 tests, and nothing else in the repository does its job. Model it on the existing three-state gates: **exit 0 clean, exit 1 findings, exit 2 broken**, because two states cannot distinguish a clean tree from a check that has stopped working. It takes a bundle directory and asserts:
    - all five files exist
    - every entry in `findings.md` carries a file path (AC-4)
    - `evidence.md` contains a coverage section (AC-5, AC-14)
    - `roadmap.md` contains exactly one horizontal break introducing the speculation section (AC-10)
    - every roadmap item above the break cites a finding identifier that resolves to a real entry in `findings.md` (AC-9)
    - no item below the break cites one (AC-10)
11. [ ] Write `HISTORY.md` with a single `1.0.0` row dated the execution date.
12. [ ] Confirm no em-dash or en-dash appears in any file. **The repo-wide script is `scripts/check-dashes.py`**; `dash-check.py` is a different, skill-scoped script under `skills/plab-wrap-session/scripts/`.

**Verification:**

```bash
python scripts/check-dashes.py
python _local/ideas/audit/draft/skills/plab-audit/scripts/bundle-check.py _local/ideas/audit/draft/fixture/
```

The first exits 0. The second exits 0 against the Phase 2 fixture, which is the proof that the self-check and the specimen agree before either is trusted. Then confirm by reading that `SKILL.md` frontmatter contains `disable-model-invocation: true`, and that `references/lenses/docs.md` contains an explicit exclusion sentence naming drift and version parity as out of scope.

---

## Phase 4: Install the skill and regenerate manifests

**Goal:** `plab-audit` is a real skill in this repository and the generated manifests agree.

**Files:** `skills/plab-audit/**` (create, copied from draft), `library.json` (modify), `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (regenerate, never hand-edit).

**Fulfills:** AC-1, AC-13.

**Steps:**

1. [ ] Copy the tree: every file from `_local/ideas/audit/draft/skills/plab-audit/` to `skills/plab-audit/`, preserving structure.
2. [ ] Add the skill to `library.json`. Match the shape of an existing entry exactly; `plab-init-project` is the right model because it is the other skill carrying `disable-model-invocation: true`. Bump the plugin `version` field from `0.5.5` to `0.6.0`.
3. [ ] Regenerate the native manifests:

   ```bash
   node E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/generators/gen-manifest.mjs . --write --target=all
   ```

4. [ ] Confirm `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` changed and that neither was edited by hand.

**Verification:**

```bash
node E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/check.mjs .
```

Reports 0 errors, 0 warnings, exit 0. **Expect eleven advisory lines beginning `[error/house]` before that summary.** Those are house-tier findings above the Universal tier this repository is graded at, they predate this effort, and the gate is passing despite them. Do not try to fix them here.

**Executed 2026-09-20. The gate failed on its first run, with a real defect.** `skills/plab-audit/SKILL.md` carried a 1,039-character `description` against the Universal-tier limit of 1,024 (`frontmatter-valid (U3)`), so the tier came back `None (Universal blocked: 1 issue)` and the exit code was 1. Twenty-one characters of provenance were cut from the do-NOT-use clause (`, and the two are different jobs by maintainer ruling` became `, a different job`), which is recorded in the spec at AC-1's source line and did not need to be in the description. Final length 1,003, headroom 21. No acceptance criterion governs the description text, so this was a trim rather than a specification change.

**The transferable part is why it surfaced this late.** The toolkit gate grades `skills/`. Phase 3 authored the tree in `_local/ideas/audit/draft/skills/plab-audit/`, which is gitignored and outside the graded surface, so ten files were written, reviewed and canary-tested without the conformance gate ever seeing them. An over-length description is exactly the class of defect that gate exists to catch in seconds. **Drafting a skill outside `skills/` defers every conformance check to install time**, and the advisory `[error/house]` count went from eleven to twelve for the same reason: the new skill directory immediately picked up the pre-existing `folder-readme (G8)` finding that every sibling already carries. Anyone repeating this shape should run `check.mjs` against a temporary copy placed inside `skills/` before declaring an authoring phase done.

---

## Phase 5: Documentation wiring

**Goal:** Every human-facing file that must mention a new skill does.

**Files:** `README.md`, `docs/status-skills.md`, `AGENTS.md`, `CHANGELOG.md` (all modify), `docs/skills/plab-audit/README.md` (create).

**Fulfills:** N/A (documentation).

**Steps:**

1. [ ] `AGENTS.md`: the opening line reads "Eight general-purpose agent skills". Change to "Nine".
2. [ ] `AGENTS.md`: the paragraph beginning "One of the eight ships with `disable-model-invocation: true`" is now false, because there are two. Rewrite it to name both `plab-init-project` and `plab-audit`, and give `plab-audit`'s reason: the maintainer ruled on 2026-09-19 that audits are occasional and explicit, and the recorded counter-argument from the parent brief is that a manual-only skill cannot displace a manual habit.
3. [ ] `AGENTS.md`: add a `### plab-audit` section to the Skills list, matching the shape of its siblings, with an **Invocation:** line rather than a **Trigger:** line, as `plab-init-project` has.
4. [ ] `README.md`: add a row for `plab-audit` to the skills table.
5. [ ] `docs/status-skills.md`: two edits, not one. Add a row for `plab-audit`, **and** update the header line, which currently reads:

   `**Plugin version:** 0.5.4 **Skills:** 8 (7 auto-discoverable, 1 explicit-invocation only) **Verified against:** ... **As of:** 2026-09-15`

   It becomes `**Plugin version:** 0.6.0 **Skills:** 9 (7 auto-discoverable, 2 explicit-invocation only)` with the `As of` date set to the execution date. Re-read the line first: v0.5.5 will have moved the version field since this plan was written.
6. [ ] `docs/skills/plab-audit/README.md`: create, matching the structure of `docs/skills/plab-continue-session/README.md`.
7. [ ] `CHANGELOG.md`: add a `## [0.6.0]` section above `## [0.5.5]`, describing the skill, naming the two fixtures it was validated against, and recording the two deliberate omissions with reasons: `--lens=publish-readiness` cut because S-22 (the plab-audit backlog proposal) is not in this repository, and `--deep` and `--ideate` deferred because neither has an executable design.
8. [ ] `.github/workflows/gate.yml`: add a step running `python3 skills/plab-audit/scripts/bundle-check.py` against a committed sample bundle. **This is required, not optional.** See the CI section below for why.

**Verification:**

```bash
node E:/Projects/product-on-purpose/agent-skills-toolkit/scripts/check.mjs . && python scripts/check-dashes.py
```

Both exit 0. The drift check compares skill content against these files, so an omission here surfaces as a gate failure rather than as silence.

---

## Phase 6: Gates and the canary

**Goal:** The skill's own self-check exists, and it has been proven to fail when the rule it guards is removed.

**Files:** `_local/ideas/audit/draft/canary/` (create, throwaway).

**Fulfills:** AC-4, AC-5, AC-14.

**A gate that cannot be shown failing is not a gate.** This phase is where that discipline is satisfied, and it is the phase most likely to be skipped under time pressure. Do not skip it.

**Steps:**

The self-check under test is `skills/plab-audit/scripts/bundle-check.py`, written in Phase 3. Invoke it as `python skills/plab-audit/scripts/bundle-check.py <bundle-dir>` throughout.

1. [ ] Copy the Phase 2 fixture bundle to `_local/ideas/audit/draft/canary/` as a scratch copy.
2. [ ] Run `bundle-check.py` against the unmodified copy. It must exit 0.
3. [ ] Delete the entire coverage section from `canary/evidence.md`. Run it again. **It must exit 1** (AC-14). If it exits 0, the self-check is not checking, and it must be corrected before proceeding.
4. [ ] Restore the coverage section. Instead, edit one entry in `canary/findings.md` to remove its file citation. Run it. **It must exit 1** (AC-4).
5. [ ] Restore. Remove the finding citation from one item above the break in `canary/roadmap.md`. Run it. **It must exit 1** (AC-9).
6. [ ] Point it at a directory that does not exist. **It must exit 2**, the broken state, not 1. A check that reports "findings" when it could not run is the failure mode the three-state convention exists to prevent.
7. [ ] Record all four canary results, pass and fail states with their exact output and exit codes, in `_local/ideas/audit/draft/canary/RESULTS.md`.
8. [x] Commit a minimal sample bundle to `skills/plab-audit/examples/sample-bundle/` so CI has something to run `bundle-check.py` against. Without it the Phase 5 workflow step has no target.

   **The sample must exercise every rule, AC-15 included.** `bundle-check.py` R3 requires `evidence.md` to carry a `Decision records consulted` section, so a sample cut down to the bare minimum will fail CI on the sample rather than on any real output, which trains everyone to ignore the job. The cheapest correct sample is a trimmed copy of the Phase 2 fixture, which already satisfies all seven rules; trim the prose, keep every required section, and keep at least two rank-numbered roadmap items so the per-item half of R6 is exercised.

   **Resolved 2026-09-20 at copy time.** `references/type-packs/agent-plugin.md` wrote the toolkit as `<toolkit>` in five commands; all five now read `<agent-skills-toolkit>`, matching `AGENTS.md`. **The absolute-path half of this trap was already stale when Phase 4 ran:** the draft's provenance note carried no machine path, so the warning as written sent the executor looking for something that was not there. Recorded rather than deleted, because the trap that did bite was in a file this note never mentioned: the Phase 2 fixture carried seven absolute paths under `E:/Projects/`, and the sample bundle is trimmed from that fixture. A warning scoped to one file missed the file that actually mattered.
9. [ ] Delete the canary scratch copy, keeping `RESULTS.md`.

**Verification:**

`_local/ideas/audit/draft/canary/RESULTS.md` contains three proven exit-1 cases and one proven exit-2 case, each with quoted output, plus one proven-passing baseline. A phase that produces only passing results has not tested anything.

**Executed 2026-09-20, ahead of Phases 4 and 5**, because the canaries need only the script and the fixture, not an installed skill. Five exit-1 cases, one exit-2, two passing baselines. Steps 1 to 7 and 9 are done; **step 8 is not**, because committing a sample bundle to `skills/plab-audit/examples/sample-bundle/` requires Phase 4 to have created `skills/plab-audit/` first. Do not add the `gate.yml` step in Phase 5 before that directory exists, or every CI run fails on a missing target.

**Canary 4 failed on its first run and the rule was wrong.** Stripping one roadmap item of its finding citation produced exit 0. R6 had been written to check that every citation present resolves, which is a per-file property; AC-9 states a per-item one, and seven valid sibling citations kept the file passing. The rule now slices each rank-numbered item and requires a resolvable citation inside it. The embedded self-test passed throughout, because its own R6 fixture reproduced the same misunderstanding of the criterion. That is the argument for canarying against a real bundle rather than a synthetic one, and it is the single most transferable result of this phase.

---

## Phase 7: Dogfood, degradation test, and release

**Goal:** The skill has been run for real on two repositories of different types, and one of those runs proves it degrades honestly.

**Files:** `_output/plab-audit/**` (generated, gitignored).

**Fulfills:** AC-2, AC-3, AC-12.

**Steps:**

1. [x] **Solve skill loading before anything else in this phase.** The skill lives in `skills/plab-audit/` but the installed plugin is loaded from the marketplace cache, so the repository copy is not what runs. There is no `.claude/` directory in this project today. Try in this order and record which worked:
   - Copy `skills/plab-audit/` to `.claude/skills/plab-audit/` in this repository and start a fresh session. If the project-level skills directory is honoured, this is the cheapest path. Add `.claude/skills/` to `.gitignore` if it is not already covered, so the test copy cannot be committed.
   - If that does not load, cut a pre-release tag and repin the marketplace.
   - **Verify by behaviour, not by a cache listing and not by the description.** Confirm a behaviour only the new skill has, per the standing lesson that merged is not installed.

   **Result, 2026-10-05: the first option worked, through a directory junction rather than a copy.** `.claude/skills/plab-audit` was created on 2026-09-27 as a Windows directory junction to `skills/plab-audit/` (commit `ff000a9` gitignores `.claude/skills/`). The departure from "copy" is deliberate: fixes made in `skills/plab-audit/` during this phase reach the test copy at once, where a copy would silently keep testing the pre-fix version. The maintainer typed `/plab-audit . --appraise` in a fresh session. The skill reported its base directory as `.claude/skills/plab-audit`, and `diff -rq` against `skills/plab-audit/` showed identical trees. The installed plugin was 0.5.4, which has no `plab-audit`, so nothing else could have answered. In the same session `plab-audit` was absent from the model-invocable skill list while loaded, which is the Claude Code half of AC-1; Codex was not tested. That run also met step 4's condition, writing only `appraise.md` and `evidence.md`, and `bundle-check.py` exited 0 on the result. This first real run found two defects in the skill, both fixed on this branch the same day. Pack step 4's description-score command was inert (`b7f12fe`), and the skill's reconciliation search could not see gitignored records (`8f696b7`).
2. [x] Run `/plab-audit E:/Projects/prisant-labs/nonfiction-studio`. Confirm it detects `agent-plugin` (AC-3) and emits all five files (AC-2).

   **Result, 2026-10-06: met, after release, against the installed 0.6.0.** The bundle's header records `agent-plugin`, "detected from `library.json` and `.claude-plugin/plugin.json`", and the run wrote all five files. `bundle-check.py` reported the bundle `CLEAN`, exit 0. The run audited branch `feat/adopt-existing-book` at `1e81907`. It found three defects in the skill, fixed in 1.0.1: the default output folder could land inside the audited repository, the pack's vendored-copy comparison measured staleness but reported edits, and the pack misattributed `effectiveSeverity: "off"` to the tier ceiling when it comes from the `plain-plugin` profile. The bundle stays local and gitignored under `_output/plab-audit/`, because its findings belong to that repository.

   **The path changed after the fixture run, and so did the repository.** Found 2026-09-27. The folder was renamed from `Nonfiction` to `nonfiction-studio` by 2026-09-25, and its history was rewritten when it was republished as a public repository: the fixture's `a2a1f56` (2026-09-05) is on no branch, it descends from root `84454ef` where today's `main` descends from `8276f13`, and pull-request numbering restarted (the fixture's history reached #17, today's `main` is at #4). The repository also gained a root `AGENTS.md` and `CLAUDE.md` on 2026-09-23, in a commit preparing it for public release, which resolves the fixture's F-02 (no root agent instructions). So the live run audits a materially different repository than the fixture did. Step 3 already compares shape rather than content; expect the content, including the ranking, to diverge, and do not read that divergence as a defect in the skill. The fixture's own citations now point at a commit that no branch reaches, so they can no longer be reproduced from `main`.
3. [x] Diff the generated bundle against the Phase 2 hand-run fixture. They will not match exactly, and should not. What must match is the **shape**: same five files, same required sections, same citation discipline. Record any place the skill omitted a section the hand-run produced, and fix the skill rather than lowering the bar.

   **Result, 2026-10-06: the shape matches, with one open question.** Both bundles have the same five files, and the skill's bundle carries every section `references/output-bundle.md` requires; `bundle-check.py` enforces that, and it passed. The headings were compared file by file. Three differences are by design: the evidence file tabulates its commands where the fixture used one subsection per tool, the README adds the specification's "Recommended sequencing", and the README drops the fixture's own section about the method, which only a fixture needs. The README heading reads "Verdict" where the specification says "Executive verdict", a wording difference the checker tolerates. **The open question:** the fixture's `appraise.md` ends with a seventh section, "Standing back", a synthesis of what the repository is and what constrains it. The specification defines six sections and the skill wrote six, so nothing was omitted against the specification. Whether the specification should gain that seventh section is a maintainer decision, and it is left open here rather than settled by either adding the section or dropping the observation.

   **Decided, 2026-10-06: add the section (option B).** The maintainer ruled that every appraisal ends with "Standing back", because it shows that the model saw the repository as a whole. `plab-audit` 1.1.0 adds it as section 7 of `skills/plab-audit/references/output-bundle.md`, the spec's AC-7 is amended in its revision R-2, and `bundle-check.py` rule R8 fails an `appraise.md` that does not end with it. Against R8, the committed sample bundle and this step's real 1.0.1 bundle both exited 1 before the sample was rewritten.
4. [x] Run `/plab-audit . --appraise` against this repository. Confirm only `appraise.md` and `evidence.md` are written (AC-2).

   **Result, 2026-10-05: met.** The run that proved step 1 was this one. It wrote exactly two files, `appraise.md` and `evidence.md`, to `_output/plab-audit/prisant-utilities_2026-10-05/`, and `skills/plab-audit/scripts/bundle-check.py` reports that bundle `CLEAN: canary proved, ... satisfies every structural rule`, exit 0.
5. [ ] Run `/plab-audit E:/Projects/prisant-labs/repo-sync-tool`. Confirm type `tauri` is detected (AC-3).
   - If `cargo` is on PATH, the full Tauri pack runs and produces real Rust findings.
   - If it is not, this is the AC-12 degradation test: `evidence.md` must record each failed command with its outcome, `findings.md` must contain no Rust-specific finding asserted without tool backing, and `appraise.md` must state that the Rust surface was not assessed. **Padding with generic Rust advice is a failure of this criterion, not a partial pass.**
   - If `cargo` is present, force the degradation case deliberately by running with a temporarily altered PATH, so AC-12 is proven either way.
6. [ ] **Apply the dogfood gate honestly.** Read the nonfiction-studio roadmap. Did it change what you would do next in that repository? Record the answer in `_local/ideas/audit/draft/DOGFOOD.md`, including a "no" if that is the truth. The gate is that one output reorders the maintainer's queue, not that the skill ran.

   **Steps 2, 3, 5 and 6 waived before release, by maintainer ruling on 2026-10-06.** The maintainer is the plugin's only user and chose to ship v0.6.0 without them. What was proven before release: the skill loads (step 1), `--appraise` writes exactly two files that `bundle-check.py` reports clean (step 4), and CI runs `bundle-check.py` against the committed sample bundle on every pull request. What was not: a full five-file run on another repository, the shape comparison with the Phase 2 fixture, the AC-12 degradation run with cargo hidden, and the dogfood gate. These steps now run after release against the installed version, and a defect they find ships as a patch release. Their boxes stay unticked because they have not happened.

   **Update, 2026-10-06: steps 2 and 3 have run, and 1.0.1 ships what they found.** Steps 5 and 6 remain waived and unticked: the degradation run against `repo-sync-tool` with `cargo` hidden, and the dogfood gate.

   **Step 6 is waived permanently, by maintainer ruling on 2026-10-06.** The maintainer called the dogfood gate "irrelevant for my current purpose": the plugin is built for its maintainer's own use, so whether one output reorders the queue is not a release condition. Its box stays unticked because the gate never ran, and no `DOGFOOD.md` will be written. Step 5 stays waived and optional, with its procedure in the maintainer's local verification note of 2026-10-05.
7. [x] Open the pull request. Merge when the Standard and Document-lifecycle checks are green.
8. [x] **Correct the `## [0.6.0]` date in `CHANGELOG.md` before tagging.** Phase 5 wrote it as `2026-09-20`, the authoring date, which is a prediction rather than a record: Keep a Changelog dates the release, and step 6's dogfood gate can legitimately answer "no" and stop this version from shipping at all. Set it to the actual tag date. `scripts/release-notes-from-changelog.py 0.6.0` reads the section by version and is indifferent to the date, so this is a correctness fix rather than a blocker discovered at tag time.
9. [x] Tag `v0.6.0` after merge. The publish workflow creates the GitHub Release from the CHANGELOG section written in Phase 5, so that section must exist or the run fails rather than publishing an empty release.

   **Result, 2026-10-06: done.** `v0.6.0` was tagged on the merge of PR #15, and the publish workflow created the GitHub Release at 16:05 UTC.
10. [x] Repin the marketplace, then verify the installed skill by behaviour.

   **Result, 2026-10-06: done.** `prisant-labs/agent-plugins` commit `ec3c550` repinned the plugin to `v0.6.0`. After the marketplace and plugin updates, a fresh headless session loaded skills from the `0.6.0` cache, which the old version could not have done, and the step 2 run used the installed `plab-audit` 1.0.0.

**Expected between Phase 5 and the tag, and not a defect.** `library.json` now declares 0.6.0 while the newest tag is v0.5.5, so the hygiene sweep's Check 3 version-parity question reports a mismatch until step 9 tags. `scripts/version-parity-check.py` is a different check and passes, because it compares documents against what the repository declares rather than against tags.

**Verification:**

```bash
ls _output/plab-audit/
```

Shows three run folders: nonfiction-studio, prisant-utilities, repo-sync-tool. `_local/ideas/audit/draft/DOGFOOD.md` contains a direct answer to whether the output changed a decision.

As of 2026-10-06, two of the three folders exist, and the `DOGFOOD.md` half no longer applies, because step 6 is waived permanently.

---

## CI and Documentation Coverage

**CI changes, and the first draft of this plan was wrong about it.**

`.github/workflows/gate.yml` was read on 2026-09-19. It **enumerates** its Python checks as individual named `run:` steps. It does not glob `scripts/*.py`:

```
python3 scripts/check-dashes.py
python3 scripts/frontmatter-check.py
python3 scripts/doc-lifecycle-check.py
python3 scripts/gen-release-index.py --check
python3 scripts/version-parity-check.py
```

Two consequences:

1. The Standard gate and the Document-lifecycle check **are** directory-scoped, so the new skill is graded and its planning documents are checked the moment they land. No change needed for those.
2. `skills/plab-audit/scripts/bundle-check.py` is **not** covered by any of the above and will never run in CI unless Phase 5 step 8 adds it. A check that only ever runs locally is one forgetting away from not running at all, which is the exact failure this repository's gate discipline exists to prevent.

**Documentation.** Phase 5 covers `README.md`, `docs/status-skills.md`, `AGENTS.md`, `CHANGELOG.md`, and the new `docs/skills/plab-audit/README.md`. `skills/plab-audit/HISTORY.md` is created in Phase 3.

## Rollback

No schema change and no data migration to unwind. Concretely:

- Delete `skills/plab-audit/` (which carries `scripts/bundle-check.py` and `examples/sample-bundle/`) and `docs/skills/plab-audit/`.
- Remove the `bundle-check.py` step from `.github/workflows/gate.yml`. Leaving it behind fails every future run, because its target directory is gone.
- Remove the `plab-audit` entry from `library.json` and restore the plugin `version` field to `0.5.5`.
- Regenerate both native manifests with the same `gen-manifest.mjs` command from Phase 4. Do not hand-edit them back.
- `AGENTS.md`: restore "Nine" to "Eight" and restore the original paragraph beginning "One of the eight ships with `disable-model-invocation: true`", including its original singular phrasing.
- Remove the `plab-audit` rows from `README.md` and `docs/status-skills.md`, restore that file's header line to `**Skills:** 8 (7 auto-discoverable, 1 explicit-invocation only)` with the prior version, and remove the `## [0.6.0]` section from `CHANGELOG.md`.
- Delete `_output/plab-audit/` and, if it was created in Phase 7, `.claude/skills/`.

**Leave the `AU-` series legend row in place.** It is additive, it breaks nothing, and removing it would strand this folder's `spec.md` and this plan if they have already been promoted to `docs/internal/release-plans/_unassigned/AU-01_*/`.

**Partial-rollback hazard:** reverting Phase 4 without Phase 5 leaves `AGENTS.md` claiming nine skills over a manifest carrying eight, which the drift check will fail on. Revert both together or neither.

## Before opening the pull request

- [ ] `phase-count` equals the number of `## Phase` sections (7)
- [ ] Every acceptance criterion in `spec.md` appears in the Completion Status table
- [ ] No acceptance criterion appears here that is not in the spec
- [ ] `python scripts/frontmatter-check.py` exits 0
- [ ] `python scripts/doc-lifecycle-check.py` exits 0
- [ ] `python scripts/check-dashes.py` exits 0 (note: repo-wide script is `check-dashes.py`, not `dash-check.py`)
- [ ] `python scripts/version-parity-check.py` exits 0
- [ ] `node <toolkit>/scripts/check.mjs .` exits 0
- [ ] `.github/workflows/gate.yml` contains a step invoking `bundle-check.py`
- [ ] Phase 6 canary results show three proven exit-1 failures and one exit-2, not five passes
