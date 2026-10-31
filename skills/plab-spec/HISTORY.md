# History - plab-spec

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.3.4 | 2026-10-30 | unreleased | fixed | Every reference example now uses the per-effort folder layout the skill writes. Twenty-four lines across six reference files still showed the retired `docs/internal/efforts/` layout, and `spec-template.md` still named the output `<id>_spec.md`. |
| 1.3.3 | 2026-09-01 | v0.5.3 | fixed | Removed every pointer to `/superpowers:writing-plans`. The implementation-plan stage is now an in-repo template, so the skill names no external plugin. |
| 1.3.2 | 2026-08-28 | v0.5.2 | changed | Supersession is documented as symmetric: `superseded-by` and `supersedes` are both written, and a cross-file gate enforces the pair. |
| 1.3.1 | 2026-08-28 | v0.5.1 | changed | `linked-effort` documented as a string, not a path. A tracked artifact must not cite an untracked one. |
| 1.3.0 | 2026-08-27 | v0.5.0 | changed | Removed `disable-model-invocation`. The skill is auto-discoverable; a do-NOT-fire clause in the description replaces the binary gate. |
| 1.2.1 | 2026-08-24 | v0.3.0 | migrated | First release in prisant-utilities. Migrated from a private upstream at version 1.2.1; prior history remains there. |



## 1.3.4 - 2026-10-30

Documentation only. The 2026-08-29 audit found that the skill writes `spec.md` into a per-effort folder, `docs/internal/release-plans/_unassigned/<id>_<slug>/` or `plan_NN_<slug>/<id>_<slug>/`, while its references still showed the layout it retired in v1.1.0. The references are loaded exactly when the agent needs the output's shape, so a stale example can override the workflow in practice. The audit's other half, the missing `docs/internal/planning-artifact-model.md`, was fixed on 2026-09-12.

- **`spec-template.md`** named the output `<id>_spec.md`; it now names `spec.md` inside `<id>_<slug>/`. Its `linked-effort` placeholder showed a path into `docs/internal/efforts/`; it now asks for a tracked path or a plain-language description, which is what `frontmatter-schema.md` already required.
- **`examples/example-spec-complex.md`** links its plan, strategy brief and reviewed copy inside one effort folder, `docs/internal/release-plans/plan_03_peer-review/S-04_ai-review/`, and gains the `linked-release` its `target-release` implies. **`examples/example-spec-simple.md`** describes its source instead of citing a path that never existed.
- **`frontmatter-schema.md`, `source-traceability.md` and `task-summary-block.md`** use the same layout. The source-priority table now names the `linked-effort` source and `<effort folder>/spec.md` instead of an effort-brief file the model no longer has.
- **Kept on purpose:** the legacy-path note in `SKILL.md` and the v1.1.0 note in `docs/skills/plab-spec/README.md`, both of which describe the old layout as history.

**Proof:** `grep -rn docs/internal/efforts skills/plab-spec`, excluding this file, returned 25 lines before this change: 24 in the six reference files and the legacy-path note in `SKILL.md`. After it, only the legacy-path note remains.

## 1.3.3 - 2026-09-01

**Documentation only. No behavior change.** The skill no longer depends on a plugin it does not ship with.

**Every reference to `/superpowers:writing-plans` is gone.** The description, the when-not-to-use list, and `references/task-summary-block.md` all pointed the reader at a skill from a separate plugin, on the assumption that plugin would be installed. That assumption held only on the maintainer's machine and only while that plugin was enabled; it broke on 2026-09-01, when it was disabled as a reversible experiment. A dangling pointer in a description is worse than no pointer, because an agent that follows it and finds nothing has no way to distinguish "this stage was skipped" from "this stage does not exist here".

The replacement is `docs/internal/release-plans/implementation-plan-template.md`, which is in this repository, is derived from the sixteen implementation plans already tracked here, and cannot be uninstalled.

Recorded because it is the general lesson rather than the specific fix: a sweep for external plugin references across the whole skills tree found `/superpowers:writing-plans` and nothing else, in fourteen live places across nine files. The coupling was a single point, but it reached into the description, both usage READMEs, the root README, `AGENTS.md`, the status page and the generated manifest. **A skill in this library should name no skill it does not ship beside.**

## 1.3.2 - 2026-08-28

**Documentation only. No behavior change.**

**Supersession is symmetric, and the second half of the pair is now named.** The schema documented `superseded-by` and nothing else, so a supersession could be declared from one end only. That is exactly the defect a manual review of this repository found on 2026-08-25: a relationship declared in one direction, invisible from whichever end you happened to open first. The optional-fields table now carries `supersedes` alongside `superseded-by`, and the validation rules state that both halves are written and that `scripts/doc-lifecycle-check.py` enforces the pair across files, which is something a per-file schema fundamentally cannot do.

Recorded because it shaped the change: requiring the back-pointer without permitting it would have made the workflow impossible. Adversarial review caught that the two new gates, each correct alone, jointly rejected every possible shape of a supersession, since one demanded a field the other forbade. The JSON Schemas under `docs/internal/schemas/` now permit both fields on all three document types, and this reference is what they agree with.

## 1.3.1 - 2026-08-28

**Documentation only. No behavior change.**

`references/frontmatter-schema.md` previously typed `linked-effort` as a path and gave a tracked path as its only example. In practice every spec in this repository set it to a file under gitignored `_local/`, which meant 16 tracked artifacts each carried a link that resolved for nobody who cloned the repository, and for the author only on one machine.

The field is now typed as a string, and the schema states the rule that was previously only implicit: **a tracked artifact must not cite an untracked one.** When the source is private, name it descriptively and summarize its substance into the spec's own Sources and Evidence section, which is the convention Kubernetes KEPs, Rust RFCs and Python PEPs all share.

This is a patch rather than a minor because no skill behavior changes: `plab-spec` never validated the field's contents, and specs written before this entry remain valid.

## 1.3.0 - 2026-08-27

**`disable-model-invocation` removed. This is a behavior change and it reverses a decision made at
1.2.1.**

The 1.2.1 entry below justified the flag on the grounds that "superpowers owns the default
spec-writing triggers on the maintainer's machine, and a second skill competing for the same phrases
would fire unpredictably." **That justification does not survive inspection.** The installed
superpowers plugin ships seventeen skills and none of them is a spec skill; "Spec" is a phase inside
`brainstorming`, not a separate trigger surface. The real overlap is with `brainstorming` alone, and
it is narrower than the original reasoning assumed.

**What replaces the flag.** The description now carries explicit trigger phrases ("write the spec",
"spec this effort", "turn this into acceptance criteria") and an explicit do-NOT-fire clause naming
the three ways the word "spec" appears without being a request: a passing mention, a question about
an existing spec, and a request to implement one. This is the instrument that took
`plab-continue-session` from over-triggering to firing correctly, and it is strictly more
expressive than a boolean, because it can distinguish a request from a mention where a flag cannot.

**Why the change was made.** The flag has a measured cost. On 2026-08-27 an agent was asked to run
this skill, the action was approved by the maintainer, and the invocation was still refused, twice
in one session. A guard that blocks an approved action is paying a real price to prevent a
hypothetical one. The skill had also never run in this repository, so the misfire risk the flag
guarded against was never observed.

**What did not change.** Typing `/plab-spec` still works and is still the precise way to invoke it.
The skill body, the eleven mandatory sections, the frontmatter contract, and the refusal to invent
acceptance criteria are all untouched. `plab-init-project` keeps its flag: it writes into a
repository root and its triggers ("init", "set up") are genuinely ambiguous.

**The honest risk.** This is a bet that a narrowed description fires correctly, and it is not yet
tested. If `plab-spec` starts firing on conversation about specs rather than requests to write one,
narrow the description further; do not restore the flag without first trying that.

## 1.2.1 - 2026-08-24

First public release. The skill's behavior is unchanged from its last private version: the same
eleven mandatory sections, the same frontmatter contract, the same refusal to invent acceptance
criteria. This entry records the move and the reference repointing it required, not a feature
change.

**Why it moved.** This repository already contains the artifact this skill produces. The sixteen
effort folders under `docs/internal/release-plans/` were authored to this skill's spec format while
the skill itself lived in a private plugin, so a reader of the public repo could see the output and
not the tool. The move closes that gap.

**Invocation is manual only.** The skill ships with `disable-model-invocation: true`. It does not
auto-trigger on "write a spec" or "create spec"; it runs when invoked as `/plab-spec`. This is
deliberate. `superpowers` owns the default spec-writing triggers on the maintainer's machine, and a
second skill competing for the same phrases would fire unpredictably. The private version already
carried this flag and it is preserved here rather than introduced.

**References repointed.** The skill previously positioned itself against siblings in the private
library. Those references now name what actually exists:

- `/jp-implementation-plan` was retired upstream with no successor in this plugin. Every reference
  now names `/superpowers:writing-plans`, which produces the `implementation-plan.md` this skill's
  specs sit beside.
- `/jp-skill-builder` was retired upstream. The one routing reference now names `/skill-creator`.
- `/jp-strategy-brief`, `/jp-ai-review` and `/jp-release-plan` now name their `plab-` twins in this
  plugin.

**Not carried over.** The prior HISTORY file is not reproduced here; it referenced private-repo
layouts and planning folders that do not ship in this plugin. `CREATION_NOTES.md` is also dropped:
it was a build diary from the private library recording friction points from skills that no longer
exist, and no skill in this plugin ships one.

**Example content genericised.** The bundled examples cited a private repository's GitHub issues as
sample source citations. The citation *form* is what the examples teach, so the URLs were replaced
with neutral placeholders rather than repointed at another real repository.
