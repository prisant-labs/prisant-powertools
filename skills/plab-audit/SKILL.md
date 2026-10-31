---
name: plab-audit
description: "Audit a repository and produce a five-file bundle: what it is and is worth, what is
  wrong with it with a file path on every finding, and what to do next ranked and traceable. Three
  composable modes, --appraise, --audit and --roadmap, defaulting to all three. Detects repository
  type from disk (agent-plugin, tauri, generic) and runs that type's deterministic tools first,
  recording every command and exit code in a coverage statement that names what was read, sampled
  and skipped. Every candidate finding is reconciled against the repository's own recorded decisions
  before it is published. Use when you want a repository appraised, audited, or its backlog
  reordered on evidence. Explicit invocation only: run /plab-audit; it does not fire on its own. Do
  NOT use for dependency scanning (that is cargo audit, npm audit and their kin), for anything
  concerning an audit log or audit trail as a runtime feature, or to review a single document with a
  second model (that is /plab-ai-review, a different job)."
argument-hint: "<path> [--appraise|--audit|--roadmap] [--type=agent-plugin|tauri|generic] [--lens=docs] [--out <path>]"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.1.1"
  updated: 2026-10-30
---

# Audit

Point this at a repository and get back a document that reorders the maintainer's queue: what the repository is worth, what is wrong with it, and what to do next, with every claim traceable to a file.

## Input

| Input | Default | Options |
|-------|---------|---------|
| Repository path | Required | Any readable directory |
| Modes | all three | `--appraise`, `--audit`, `--roadmap`, composable |
| Type | detected from disk | `agent-plugin`, `tauri`, `generic` |
| Lens | none | `--lens=docs` |
| Output | `_output/plab-audit/<repo>_<YYYY-MM-DD>/` | `--out <path>` |

## The one rule that matters most

**The deterministic layer produces candidates, not findings.**

A candidate becomes a finding only after it has been checked against what the repository has already decided. That step is not optional and it is not a formality. On the fixture run that specified this skill, it withdrew 7 of 15 candidates, including the two highest-ranked, and one of the withdrawn candidates recommended a change the repository had already tested and rejected with measured evidence.

An audit that skips reconciliation reports things the maintainer already decided, citing evidence they already weighed, recommending a fix they already tried. That is worse than reporting nothing, because it costs the reader the time to re-refute their own reasoning.

## Workflow

### 1. Resolve the target and the type

Resolve the path. Refuse to continue if it is not a readable directory.

Detect type from disk unless `--type` overrides:

| Marker on disk | Type |
|---|---|
| `library.json` or `.claude-plugin/plugin.json` | `agent-plugin` |
| `src-tauri/` or `tauri.conf.json` | `tauri` |
| neither | `generic` |

Load the matching pack from `references/type-packs/`. The pack names the deterministic tools, the type-specific judgment questions, and what complete documentation means for that type.

**Resolve the output folder before writing anything, and refuse to write inside the target unless the target ignores it.** The default output folder is relative to the working directory, so an audit started from inside the repository it audits would write its bundle into that repository. If the resolved output folder lies inside the target, run `git -C <target> check-ignore -q <output-folder>/README.md`. Exit 0 means the target ignores the folder and the default stands. Any other exit, including 128 for a target that is not a git repository, means stop and ask for `--out`. Check a file path inside the folder, not the folder itself: for a folder that does not exist yet, `check-ignore` cannot tell that a directory pattern such as `_output*/` applies, and returns 1 for a folder that would in fact be ignored.

Prefer starting the audit from outside the target altogether, because the harness writes into the working directory too. On the nonfiction-studio run of 2026-10-06, the bundle was redirected by hand, but `/plugin` commands run in that session still created `.claude/settings.json` inside the audited repository.

### 2. Snapshot, then run the deterministic layer

Take the repository snapshot the pack specifies: version, branch, HEAD, tags, commit count and span, authorship, branches in flight, tracked file count, component counts.

Then run the pack's tools **in order, recording each command and its exit code as you go**, into a running record. This record becomes `evidence.md` and it is not reconstructable afterwards. Do not batch the recording to the end.

**A tool that is absent, fails, or times out is a coverage gap, never a silence.** Record the command, the exit code and what could not be assessed because of it. Never pad a missing tool with generic advice about the language or framework it would have checked; a finding with no tool behind it and no file behind it is an opinion wearing a severity label.

**Record your own operator errors too.** A command invoked wrongly produces a real exit code that is not the repository's fault. Keep it, mark it as yours, and record the corrected run beside it. An audit that silently deletes its own mistakes is indistinguishable from one that made none.

### 3. Read, and say what you read

You will not read everything, and the coverage statement exists so that nobody has to guess which parts. As you go, keep three lists: read in full, sampled, skipped with a reason.

A coverage statement claiming total coverage of a repository of any size is not credible and means the audit was not honest about sampling.

### 4. Reconcile every candidate before publishing it

For each candidate the deterministic layer or your reading produced, find out whether the repository has already answered it. Read, at minimum:

- **Architecture decision records**, usually `docs/adr/` or `docs/decisions/`
- **Suppression and gate configuration**, for example `askit.config.json`, `.eslintrc` overrides, a `# noqa` with a reason
- **Release notes and changelog**, including entries about what has deliberately not happened yet
- **Any prior audit in the tree**, including gitignored ones under `_local/`
- **The repository's own instruction files**, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`
- **Gitignored working records**, such as a decisions register or open-questions file, and the newest session log's list of what is waiting on the maintainer. These often hold the most recent decisions of all

**Search the gitignored record explicitly, because a repository-wide search skips it.** ripgrep, and the Grep tool built on it, honour `.gitignore` by default. On this skill's first real run, `rg -l 'v0\.6\.0' .` matched 0 files under `_local/`, while `--no-ignore` matched 57. That audit never opened the gitignored decisions register, and reported the record silent on a problem it was recording. Pass the gitignored folder as the search path, or add `--no-ignore`. A search that returns nothing has answered only for the paths it could see.

Then do one of three things with the candidate, and record which:

| Outcome | When |
|---|---|
| **Publish** | Nothing in the record answers it |
| **Narrow** | The record answers part of it. Publish only the part left open, and say what the record settled |
| **Withdraw** | The record answers it. Report the withdrawal in the findings file, with where the answer was |

**Withdrawals are output, not waste.** They tell the maintainer their reasoning was found and understood, and they are the strongest evidence the audit was performed rather than generated. Never delete one silently.

**Verify a tool's stated consequence before repeating it.** A check that says a defect makes something "invisible to installers" is asserting a consequence, and consequences are testable, often against a control repository known to work. On the fixture run, the highest-severity tool claim in the whole audit was false, and a single comparison against a working repository established it.

### 5. Write the bundle

Five files, defined in `references/output-bundle.md`. Write `evidence.md` from the running record first, because the others cite it. In a full run, write the last section of `appraise.md`, "Standing back", after `findings.md`, because it names the theme connecting the findings by identifier.

Modes select which files are written:

| Mode | Files written |
|---|---|
| `--appraise` | `appraise.md`, `evidence.md` |
| `--audit` | `findings.md`, `evidence.md` |
| `--roadmap` | `roadmap.md`, `evidence.md`, and `findings.md` because roadmap items must cite findings |
| none given | all five, including `README.md` |

`evidence.md` is written in every mode. An audit output with no coverage statement is not an audit output.

### 6. Rank, and separate what you know from what you wonder

Rank roadmap items by the calibration in `references/calibration.md`. Every item above the speculation break cites a finding identifier and names a mechanization rung. Everything below the break cites nothing and says so in its own heading.

### 7. Check the bundle before handing it over

```bash
python scripts/bundle-check.py <output-dir>
```

Exit 0 clean, 1 findings, 2 broken. Fix what it reports rather than explaining it away. If it exits 2, the checker could not run and its silence means nothing.

## Constraints

- **Read-only on the target.** Write only inside the output folder. Never modify the repository under audit, including to fix something trivial you noticed. The output folder itself may sit inside the target only when the target ignores it, as step 1 checks.
- **Every finding carries a file path**, and a line number where the finding is line-scoped.
- **No finding without evidence.** If the only support is that something seems unwise, it belongs below the speculation break, not in `findings.md`.
- **Severity is about consequence, not effort.** A one-character fix that silently disables a gate outranks a large refactor that would be tidier.
- **Do not audit the audit tooling into the findings.** Where a tool's own behaviour shaped the audit, record it, and say plainly that it belongs to the tool's maintainer rather than to the repository under audit.
- **Never invoke `path-citation-check.py`** from any pack. It false-positives on every markdown inline link and its fix is an open item awaiting maintainer approval.

## References

| File | Purpose | Load when |
|------|---------|-----------|
| `references/coverage-statement.md` | The shape of `evidence.md`, including the decision-records section | Step 2, and again at step 5 |
| `references/output-bundle.md` | The five files, their required sections, and the speculation break | Step 5 |
| `references/calibration.md` | Ranking weights and the mechanization ladder | Step 6 |
| `references/type-packs/agent-plugin.md` | Tools and questions for a skills or plugin repository | Step 1, when detected |
| `references/type-packs/tauri.md` | Tools and questions for a Tauri application | Step 1, when detected |
| `references/type-packs/generic.md` | Fallback pack when no type is detected | Step 1, when detected |
| `references/lenses/docs.md` | The documentation lens, and what it deliberately excludes | Only with `--lens=docs` |
