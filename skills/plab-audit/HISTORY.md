# History - plab-audit

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.1.1 | 2026-10-30 | unreleased | fixed | Codex now honors manual-only too: `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads in place of `disable-model-invocation`. |
| 1.1.0 | 2026-10-06 | v0.7.0 | added | Every appraisal now ends with a big-picture section, "Standing back", by maintainer ruling. `bundle-check.py` gains rule R8 to enforce its structure, and the committed sample is rewritten to the seven sections the skill writes. |
| 1.0.1 | 2026-10-06 | v0.6.1 | fixed | Its first full run on another repository found three defects in the skill: an output folder that could land inside the audited repository, a vendored-copy comparison that asked the wrong question, and a misattributed tier-ceiling marker. Also adds the first-party plugin validator to the agent-plugin pack. |
| 1.0.0 | 2026-09-20 | v0.6.0 | added | First version. Three composable modes, three type packs, one docs lens, a coverage statement, and a canary-proven bundle self-check. |

## 1.1.1 - 2026-10-30

**Fixed: manual-only in Codex.** Codex ignored the skill's manual-only flag. `disable-model-invocation: true` is a Claude Code field, so in Codex the skill sat in the model's skill list and could fire on its own. The 2026-08-29 audit found this for every manual-only skill here. The new `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads instead: it hides the skill from the model and keeps it callable by name. `scripts/codex-invocation-check.py` fails CI when a skill carries either flag without the other.

## 1.1.0 - 2026-10-06

**Added: a seventh, closing section in `appraise.md`, "Standing back".** The hand-made fixture audit of 2026-09-20 ended its appraisal with a synthesis of what the repository is and what constrains it. The specification defined six sections, so the skill's first full run, on `nonfiction-studio` on 2026-10-06, wrote six. The maintainer ruled the same day that every appraisal ends with the section, because it shows that the model saw the repository as a whole.

- **`references/output-bundle.md` defines it as section 7.** It says what the repository is beyond its parts, what most distinguishes it and what most constrains it. In a full run it names the theme connecting the findings by identifier; under `--appraise` alone it says what the appraisal implies and what a full audit would test first. A paragraph that could be pasted into a different repository's appraisal fails it.
- **Step 5 of `SKILL.md` writes it last** in a full run, after `findings.md`, because it cites the findings.
- **`bundle-check.py` rule R8 enforces the structure.** When `appraise.md` is present, a "Standing back" heading, numbered or not, must be its last level-2 section and must not be empty. R8 is skipped when `appraise.md` is absent. Canary: before the sample was rewritten, the committed sample and the real 1.0.1 bundle from the `nonfiction-studio` run both exited 1 on R8. Removing the rule from the checker's pipeline makes its self-test exit 2 on all three R8 canaries. The hand-made fixture, with its unnumbered heading, passes.
- **The committed sample's `appraise.md` is rewritten** to the seven numbered sections the skill writes. It previously carried four headings that matched none of the required six, which no rule could see.
- **The self-test's appraise-only anti-canary now writes the `appraise.md` its label names.** Before R8 it wrote `evidence.md` alone.

## 1.0.1 - 2026-10-06

**Fixed: three defects found by the skill's first full run on another repository.** The run audited `nonfiction-studio` on 2026-10-06, as step 2 of Phase 7 in AU-01 (audit skill). Its bundle passed `bundle-check.py`, and the run surfaced three places where the skill itself was wrong.

- **The default output folder could land inside the audited repository.** The default is relative to the working directory, so an audit started from inside its target wrote there, against the skill's own read-only rule. The run avoided it only because the operator redirected the bundle by hand. Step 1 now resolves the output folder first and refuses a location inside the target unless `git -C <target> check-ignore -q <output-folder>/README.md` exits 0. The check names a file inside the folder because, for a folder that does not exist yet, `check-ignore` on the folder itself returns 1 even when a directory pattern such as `_output*/` would ignore it. Canary: the check exits 0 in `prisant-utilities`, which ignores `_output*/`, and 1 in `nonfiction-studio`, which does not.
- **The agent-plugin pack's vendored-copy comparison asked one question and reported another.** It diffed the target against the toolkit's current files, which measures how stale a copy is, and read the result as evidence of local edits. That is how the 2026-09-20 fixture audit's highest-ranked finding, "vendored spine modified", came to be wrong. Step 3 now runs two labelled comparisons: against the pinned commit for edits, and against upstream `HEAD` for staleness. Canary: against its pin, `nonfiction-studio`'s vendored `checks/` and `lib/` folders show 0 content differences; against `HEAD`, `checks/` shows 22. Without `--strip-trailing-cr`, the comparison against the pin reports 49 false differences on a Windows checkout, so the flag is now part of the command.
- **The pack misattributed `effectiveSeverity: "off"`.** It called "off" a tier-ceiling marker, and its note said the marking varied with the toolkit version. Both are wrong. On one toolkit commit, `549eb32`, `prisant-utilities` returned its 35 above-tier findings at `"error"` and `nonfiction-studio` returned 150 at `"off"`. The difference is the profile: `nonfiction-studio` sets `plain-plugin`, which switches the toolkit's house conventions off. The tier ceiling marks nothing per finding under either profile. The pack now says so, and tells the audit to record `config.profile`.

**Added: the first-party plugin validator as pack tool 7.** `claude plugin validate --strict <target>` ships with Claude Code, so unlike the third-party validators the pack already names, it can be a required step. The pack records that it does not read `settings.json`, which is how the run's F-01 (an unquoted status-line path) stayed invisible to it.

## 1.0.0 - 2026-09-20

**Added: the skill, specified by a hand-run audit rather than by a design.**

The workflow this codifies had been run by hand at least four times before it became a skill, most recently against `prisant-utilities` on 2026-08-29 and against `nonfiction-studio` on 2026-09-20. Each run re-derived the method from nothing, which is the signal that a workflow is ready to become a skill.

The parent brief, `docs/internal/ideas/plab-audit-skill-2026-08-15.md`, stalled at its own step 1 for 35 days: whether audit was a skill or a mode of `plab-ai-review`. The maintainer closed it on 2026-09-19 in these words: "plab-ai-review is more about a general review that an ai writes. my audit goal is a more holistic audit."

**What ships:** three modes, `--appraise`, `--audit` and `--roadmap`, composable and defaulting to all three. Three type packs, `agent-plugin`, `tauri` and `generic`, detected from disk with a `--type` override. One lens, `--lens=docs`. A five-file output bundle to a gitignored per-run folder. A coverage statement on every run, in every mode. A labelled break in `roadmap.md` separating evidenced items from speculation.

**The one rule the skill is built around, and the reason it exists:** the deterministic layer produces candidates, not findings. A candidate becomes a finding only after being reconciled against what the audited repository has already decided, in its decision records, suppression configuration, release notes, changelog and any prior audit.

That rule was not in the original specification. It was added as AC-15 on 2026-09-20, after the fixture run that specified this skill produced 15 candidates and published 8. All seven withdrawals came from that single step. Two were the highest-ranked findings of the first draft. One of them recommended converting a manifest's component list to a different shape, which the audited repository's own suppression config records as already tested and rejected, with the measured result: it clears the warnings and produces 28 errors from a competing check that requires the opposite shape.

A skill built without that step would have shipped that recommendation, with a severity label on it.

**Explicit invocation only,** by maintainer ruling of 2026-09-19. This makes `plab-audit` the second skill carrying `disable-model-invocation: true`, alongside `plab-init-project`. The parent brief argued the opposite, on the grounds that a skill built to displace a working manual habit cannot displace it if it only runs when named. That argument is recorded rather than re-fought, with one consequence noted: if the skill goes unused, a weak description is no longer a candidate cause, so the dogfood gate becomes the only adoption signal available.

**`scripts/bundle-check.py` is the skill's own gate.** Three states, 0 clean, 1 findings, 2 broken, because two states cannot distinguish a well-formed bundle from a checker that has stopped working. Seven rules, each proved against a canary that must fail, plus a well-formed anti-canary, a legitimate appraise-only partial, and an absent-directory case that must report broken rather than findings.

Two corrections to its specification were made while writing it. The plan said it should assert that all five bundle files exist; that is wrong for a mode-composable skill, because `--appraise` legitimately writes two, so the mode is inferred from what is present and each file is checked against its own rules. And rule 6 resolves a cited finding identifier against the headings in `findings.md` rather than pattern-matching something finding-shaped, because a roadmap citing `F-12` in a bundle whose findings stop at `F-08` is precisely the defect the rule exists to catch.

**Deliberately not in 1.0.0**, each with its reason:

- **`--lens=publish-readiness`**, cut on 2026-09-19. Both design briefs attribute it to a backlog proposal whose source document is not in this repository and was not located. Building it would mean guessing at a design from a second-hand summary.
- **`--deep` multi-agent fan-out**, described in the parent brief and never designed to an executable specification.
- **`--ideate` as a formal chain** to `plab-strategy-brief`. The mechanism exists and was verified, but it requires a scope amendment to that skill. Speculation ships instead as a labelled section at the foot of `roadmap.md`, which preserves the epistemic separation without the amendment.
- **A persistent committed audit file that diffs across runs.** A v2 candidate.
