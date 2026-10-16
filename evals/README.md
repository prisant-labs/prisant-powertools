# Plugin eval suite (R5)

This is a `claude plugin eval` suite for `prisant-utilities`. It checks skill-trigger behavior, not skill output quality: does each auto-invocable skill fire on the phrasing its own description promises, and does it stay quiet on the phrasing its description rules out. It was built from the 2026-10-12 toolchain review's R5 recommendation (Option A: a local suite now; CI integration is a separate, later decision).

## What it covers

Nineteen cases under this directory, one per subdirectory:

- **Sixteen trigger cases**, one should-fire and one should-not-fire case for each of the eight auto-invocable skills: `plab-wrap-session`, `plab-continue-session`, `plab-strategy-brief`, `plab-guide`, `plab-ai-review`, `plab-spec`, `plab-release-plan`, `plab-resolve-open-items`. Each case has exactly one grader, a `tool_used` check on the `Skill` tool, scoped by name to the skill under test. A should-fire case asserts the skill was called at least once; a should-not-fire case asserts it was called zero times. Where a skill's description carries an explicit do-NOT-fire clause, the should-not-fire prompt comes from that clause. Three skills, `plab-wrap-session`, `plab-guide`, and `plab-ai-review`, carry no explicit do-NOT-fire clause in their description, so their should-not-fire prompts are a reasoned near-miss instead: a request close enough to be a plausible distractor (a code-review request for `plab-ai-review`, an ordinary bug-fix request for `plab-wrap-session`) but clearly not what the skill's own trigger phrases describe.
- **Two manual-only cases**, one each for `plab-init-project` and `plab-audit`, both of which carry `disable-model-invocation: true`. Each sends a natural prompt that could plausibly ask for the skill ("set up this repo for agents", "audit this repo") and asserts the skill was never called. Because `disable-model-invocation: true` removes the skill from the model's own skill list for the whole session, these two cases cannot fail: there is no description for the model to discriminate against. Treat them as a regression guard on the flag itself, not as evidence the skill's description avoids false triggers. If either ever starts failing, it means the flag stopped being honored, which is a more serious finding than a bad description.
- **One side-effect case**, `resolve-open-items-empty-walk`, covering the defect class the toolchain review named: an empty walk (nothing open) must not go hunting for items. `plab-resolve-open-items`'s own SKILL.md states the rule directly: "Never list a folder, open a file, or read a memory file to look for items." The case grants `Read`, `Glob`, `Grep`, and `Skill` (all read-only, so no `--allow-tools` grant is needed) and carries four graders: one `tool_used` check that the skill fired at all, two `tool_used` checks (`arm: both`, `min: 0`, `max: 0`) that `Glob` and `Grep` were never called, and one `llm` grader over the trace that distinguishes a legitimate read of the skill's own bundled reference files (under `plab-resolve-open-items/references/`) from reading any project file, memory file, or session log while hunting for items.

## Run it before a release

```
claude plugin eval . --no-publish --judge-model haiku --max-cost-usd 8 --trust-plugin --runs 1 --ablation none --json <path-outside-the-repo>.json
```

Run this from the repository root (or the worktree root under test), not from inside `evals/`. `--ablation none` is a deliberate choice, not an oversight: every grader in this suite is a question about the with-plugin arm only ("did the skill fire", "did it avoid this tool"), so the no-plugin baseline arm the default `--ablation with-without` would add is uninformative here (a skill plainly cannot fire without the plugin loaded) while doubling the number of paid agent runs. Drop `--ablation none` only if a future case is added that genuinely wants the `Δ` comparison.

`--runs 1` keeps a routine pre-release pass cheap. The eval tool's own default is 3 runs per case specifically to average out agent non-determinism (see "What is not covered" below); raise `--runs 3` for a case under active investigation rather than for the routine pass.

`--json` makes the run quiet (no progress lines, no summary table) and writes the full result document instead; point it somewhere outside the repository so a result file is never accidentally committed. `evals/results/` is gitignored for the same reason, in case you drop `--json` for an interactive run.

## Measured cost (first pass, 2026-10-15)

Full suite, nineteen cases, `--runs 1 --ablation none`, judge model haiku, Claude Code 2.1.301:

```
overallScore: 0.947  (18 / 19 cases passed at threshold 1.0)
costUsd: 2.10
durationSeconds: 315  (about 5 minutes 15 seconds)
```

One case, `ai-review-fires`, scored 0 on this pass (`Skill called 0x`, two turns, 11 seconds) and is the one real finding from this run; see below. All eighteen other cases scored 1.00. Budget headroom: this pass used about $2.10 of the $8 ceiling, so raising `--runs 3` for the full suite (roughly 3x the cost) still fits comfortably under the ceiling if a future pass wants the steadier signal.

### The one real finding: `plab-ai-review`'s trigger is non-deterministic on "second opinion" + a named reviewer

`ai-review-fires` sends "Can you get a second opinion on this plan from Codex?", which reuses the description's own trigger phrase ("get a second opinion") and its own example reviewer ("review this with codex"). On the recorded full-suite run it scored 0: the agent answered directly in two turns without calling the `Skill` tool. A same-case, `--runs 1` re-run immediately afterward (not part of the recorded cost above; it cost an additional $0.10) scored 1: the skill fired normally. This is flakiness in the with-arm, not a reproducible misfire: the agent sometimes reads "a second opinion from Codex" as a request it can satisfy inline rather than as a request to generate the cross-LLM review document the skill produces. The case prompt was left unchanged, since it faithfully uses the skill's own trigger language; tuning the prompt to force a pass would have hidden a real signal instead of fixing a bad test. A future pass that wants to confirm whether this is simple single-run noise (the kind `--runs 3` exists to average over) or a genuine soft spot in `plab-ai-review`'s description should run `--case ai-review-fires --runs 3 --ablation none` on its own and look at the pass rate, not just the aggregate score.

### `plab-guide`'s should-fire case usually exceeds its own timeout, harmlessly

`guide-fires` ("Can you build a cheat sheet for the jq command-line tool?") called the `Skill` tool on turn 1 as expected, then kept working through the skill's multi-phase pipeline (research, outline, render) until it hit the case's 90-second `timeout_seconds`. The run is still graded on what it produced before the timeout, per the eval tool's own documented behavior, and the `tool_used: Skill` grader had already seen what it needed, so the case scores 1.00 regardless. This is expected for a skill this heavy when the case's tools are deliberately kept to the read-only set; it does not indicate a problem with the plugin or the case.

## What is not covered

- **Skill output quality.** Every grader in this suite is a trigger check (`tool_used` on `Skill`, or on `Glob`/`Grep` for the side-effect case). None of them check whether a fired skill produced a correct spec, guide bundle, or release-readiness report. That is a different, larger effort (a correctness suite per skill, likely needing fixture files via `context.scaffold_script` and real write access), deliberately out of scope for this first pass.
- **A `Bash`-based hunt in the side-effect case.** `resolve-open-items-empty-walk` grants only read-only tools (`Read`, `Glob`, `Grep`, `Skill`), so it cannot detect a hunt carried out through a shell command such as `ls` or `find`. Granting `Bash` to a case requires Claude Code's OS-level sandbox, which has no backend on native Windows; running a `Bash`-granting suite needs WSL2 or a Linux host with `bubblewrap` and `socat`. This repository's WSL2 default distribution is `podman-machine-default`, which is not a general-purpose Linux shell, so a `Bash`-granting variant of this case cannot run on this machine as currently configured. The chosen design (no `Bash` grant) sidesteps the problem entirely and runs natively here, at the cost of only covering the `Glob`/`Grep`/`Read` channel of the forbidden behavior, not a shell-based equivalent. If a `Bash`-granting variant is ever wanted, write it as a second case tagged to exclude it from the default local run (for example `--tag native` on every other case, with the `Bash` variant left untagged), and run it from a real Linux host or a properly configured WSL2 distribution.
- **The two manual-only cases discriminate nothing**, as noted above; they only confirm `disable-model-invocation: true` is still honored.
- **CI integration.** This is Option A from the toolchain review (a local suite, run by hand before release). Option B, wiring this into `.github/workflows/gate.yml` or a dedicated workflow, is explicitly deferred until a month of local runs shows the real cost and failure rate.
