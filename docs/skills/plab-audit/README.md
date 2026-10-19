# plab-audit

**Version:** 1.1.0
**Source:** [`skills/plab-audit/`](../../../skills/plab-audit/)

Audit a repository and produce a five-file bundle: what it is and is worth, what is wrong with it with a file path on every finding, and what to do next ranked and traceable to those findings. Manual invocation only.

---

## Getting Started

### Quick Start

```
/plab-audit path/to/repository
```

All three modes run by default and the bundle lands in `_output/plab-audit/<repo>_<YYYY-MM-DD>/`, relative to the folder you start from. Start from outside the repository being audited. If that default would put the bundle inside the audited repository and the repository does not gitignore it, the skill stops and asks for `--out` rather than write there.

### Common Invocations

```
# Everything: appraisal, findings, roadmap, evidence
/plab-audit ../some-repo

# Just the appraisal, when the question is "is this worth keeping"
/plab-audit ../some-repo --appraise

# Findings and a ranked roadmap, skipping the appraisal
/plab-audit ../some-repo --audit --roadmap

# Override type detection when the repository is unusual
/plab-audit ../some-repo --type=generic

# Documentation lens, and a chosen output directory
/plab-audit ../some-repo --lens=docs --out _output/review
```

### Installation

Ships with the `prisant-powertools` plugin. Nothing to install separately. Because it carries `disable-model-invocation: true`, it is absent from the auto-loaded skill listing and runs only when you type `/plab-audit`.

---

## When to Use

- You are deciding what to do next in a repository and want the queue ordered on evidence rather than on what is freshest in memory.
- You have inherited a repository, or come back to one after months, and need to know what it is and what is wrong with it.
- You want a second, structured opinion on a backlog you already have.

## When NOT to Use

- **Dependency scanning.** That is `cargo audit`, `npm audit` and their kin. This skill runs them where they exist and records their exit codes; it does not replace them.
- **Anything about an audit log or audit trail as a runtime feature.** Different meaning of the word entirely.
- **Reviewing a single document with a second model.** That is `/plab-ai-review`, and the two are different jobs.

---

## How It Works

### 1. Type detection

The repository type is detected from disk, not guessed from its name: `agent-plugin`, `tauri`, or `generic`. Each type has a pack under `references/type-packs/` naming the deterministic tools to run first. `--type=` overrides detection.

### 2. The deterministic layer runs first

Every command is recorded with its exit code in a coverage statement naming what was read, what was sampled, and what was skipped. **A tool that is absent, fails, or times out becomes a recorded coverage gap.** It never becomes a silence, and it never becomes generic advice standing in for a check that did not happen.

### 3. Reconciliation, which is the step that matters

**The deterministic layer produces candidates, not findings.** A candidate becomes a finding only after it has been checked against what the repository has already decided: its decision records, its stated design frame, its own recorded experiments.

This is not a formality. On the fixture run that specified this skill, reconciliation withdrew 7 of 15 candidates, including the two highest-ranked, and one of the withdrawn candidates recommended a change the repository had already tested and rejected with measured evidence. An audit that skips this step recommends work its target has already refused.

### 4. Ranking

Ranking follows the calibration in `references/calibration.md`: token economy, deterministic enforcement over remembering, documentation agents actually read, evidence and reversibility, cross-harness durability, session continuity. Contributor onboarding, community growth and external backwards compatibility are unweighted by standing decision.

### 5. The speculation break

`roadmap.md` carries exactly one horizontal break. Everything above it cites a finding. Nothing below it does. An idea that cannot trace to a finding is not suppressed, it is filed below the break and labelled as speculation.

---

## Output

| File | What it answers |
|------|-----------------|
| `appraise.md` | What this repository is, and what it is worth, ending with "Standing back", the big picture |
| `findings.md` | What is wrong, with severity and a file path on every finding |
| `roadmap.md` | What to do next, ranked, with the speculation break |
| `evidence.md` | Every command run with its exit code, plus coverage and decision records consulted |
| `README.md` | The bundle's own index |

Running a single mode produces a subset: `--appraise` alone yields `appraise.md` and `evidence.md` and no `findings.md`. `evidence.md` is produced in every mode without exception.

---

## Its Own Gate

`skills/plab-audit/scripts/bundle-check.py` enforces eight structural rules over a finished bundle:

| Rule | What it requires |
|------|------------------|
| R1 | `evidence.md` exists, in every mode |
| R2 | `evidence.md` carries a coverage statement |
| R3 | `evidence.md` names the decision records consulted |
| R4 | Every finding carries a file path |
| R5 | `roadmap.md` carries exactly one horizontal break |
| R6 | Every roadmap item above the break cites a real finding |
| R7 | No roadmap item below the break cites a finding |
| R8 | `appraise.md`, when present, ends with a non-empty "Standing back" section |

Run it directly:

```
python skills/plab-audit/scripts/bundle-check.py _output/plab-audit/<repo>_<date>/
```

Exit codes follow this repository's three-state convention: `0` clean, `1` findings, `2` broken. **Never read `2` as clean.** The self-test runs on every invocation, so a checker that cannot prove itself refuses to report on your bundle.

CI runs it against the committed sample at `skills/plab-audit/examples/sample-bundle/`, which is mutation-tested so that every rule is known to be able to fail.

---

## Hard Constraints

- **Read-only.** Nothing in the audited repository is modified.
- **No finding without a file path.** A claim that cannot be traced is not published as a finding.
- **No roadmap item above the break without a finding behind it.**
- **A missing tool is a recorded gap, never a pass.**
- **Manual invocation only.** It does not fire on its own.

---

## Tips

- Run `--appraise` alone first on an unfamiliar repository. It is cheap and it tells you whether the full audit is worth the tokens.
- If the repository has decision records, make sure they are readable from its root. Reconciliation is what makes the output worth acting on, and it can only reconcile against what it can find.
- A short bundle is a result, not a failure. The fixture run produced eight findings, all of them recording gaps rather than engineering defects, and that was the honest answer.
