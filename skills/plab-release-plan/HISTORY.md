# History - plab-release-plan

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.6.1 | 2026-10-30 | unreleased | fixed | Codex now honors manual-only too: `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads in place of `disable-model-invocation`. |
| 1.6.0 | 2026-10-19 | v0.8.1 | changed | Restored `disable-model-invocation: true`. The skill runs only when typed as `/plab-release-plan`, by the maintainer's provisional ruling of 2026-10-17. |
| 1.5.1 | 2026-09-01 | v0.5.3 | fixed | Removed every pointer to `/superpowers:writing-plans`, including the stale-plan gate's failure message. The skill names no external plugin. |
| 1.5.0 | 2026-08-27 | v0.5.0 | changed | Release folders are named by sequence and theme, not by version. The version moves to `target-version:` frontmatter. |
| 1.4.0 | 2026-08-27 | v0.5.0 (as 1.5.0) | changed | Removed `disable-model-invocation`. The skill is auto-discoverable; a do-NOT-fire clause in the description replaces the binary gate. |
| 1.3.0 | 2026-08-24 | v0.3.0 | migrated | First release in prisant-utilities. Migrated from a private upstream at version 1.3.0; prior history remains there. |



## 1.6.1 - 2026-10-30

**Fixed: manual-only in Codex.** Codex ignored the skill's manual-only flag. `disable-model-invocation: true` is a Claude Code field, so in Codex the skill sat in the model's skill list and could fire on its own. The 2026-08-29 audit found this for every manual-only skill here. The new `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`, which Codex reads instead: it hides the skill from the model and keeps it callable by name. `scripts/codex-invocation-check.py` fails CI when a skill carries either flag without the other.

## 1.6.0 - 2026-10-19

**The skill is manual-only again.** `disable-model-invocation: true` is back in the frontmatter, so the skill is absent from the auto-loaded skill listing and runs only when typed as `/plab-release-plan`. The description says so in the same words `plab-audit` uses. Nothing else about the skill changed.

**Why.** 1.4.0 replaced the flag with a do-NOT-fire clause on the argument that a narrowed description beats a binary gate. That argument assumed a skill in active use, and this one has never been run: no session log lists it, and the v0.5.x logs told agents not to run its `--gate`. Two further reasons make auto-invocation a liability rather than a convenience. The skill was built for release plans numbered in advance, and versions are now assigned at ship time. And its hygiene gate (f) cites two files this repository does not have, `validate-plugin-manifests.py` and `pin-marketplace.yml`, so a readiness check it ran unprompted would fail for a reason unrelated to the release.

**Provisional.** The maintainer ruled on 2026-10-17 to make the skill manual-only, with the words "I still need to review the wider plan in this". A `--ship` mode that would cut a release end to end stays deferred until that review. If the review keeps the skill, the flag can come off again; if it retires the skill, this release has already stopped it firing.

## 1.5.1 - 2026-09-01

**Documentation only. No behavior change.** The skill no longer depends on a plugin it does not ship with.

**Every reference to `/superpowers:writing-plans` is gone.** Two sat in `SKILL.md`, in the when-not-to-use list and in the pipeline description. The third is the one that mattered most: `references/hygiene-gates.md` used it inside the **failure message** of the stale-plan gate, so a maintainer whose spec had drifted ahead of its plan was told to run a command that, on any machine without that plugin, does not exist. A gate whose remediation instruction cannot be followed has not really fired.

All three now name `docs/internal/release-plans/implementation-plan-template.md`, which lives in this repository and is derived from the sixteen implementation plans already tracked here.

See `plab-spec` 1.3.3 for the sweep that found these: fourteen live pointers across nine files, all to the same external skill, and no other external plugin referenced anywhere in the library.

## 1.5.0 - 2026-08-27

**Release folders are no longer named by version.** `plan_vX.Y.Z/plan_vX.Y.Z.md` becomes `plan_NN_<slug>/plan.md`, where `NN` is a two-digit sequence and `<slug>` is the kebab-cased theme. The version moves into `target-version:` frontmatter alongside a new immutable `sequence:` field.

**Why.** A version in a path is a prediction, and semver is free to invalidate it. Any unplanned minor consumes the number a later plan reserved. That happened twice in eight releases here: the 2026-08-24 skill migration took v0.3.0 and forced 358 reference rewrites across five folders, and the 2026-08-27 auto-invocation change took v0.5.0 and forced 140 more. Under the new scheme both would have been a one-line frontmatter edit. This is the reasoning `_unassigned/` already embodied: when a fact is not yet known, do not encode it in a path.

**The CLI surface is unchanged.** `--create vX.Y.Z --theme "..."` still takes a version; it now stores it rather than naming the folder with it, and derives the folder from the next sequence plus the theme. `--promote --to`, `--demote --from`, `--update`, and `--gate` still take `vX.Y.Z` and resolve it by reading `target-version:` from each plan. A sequence or a folder name is also accepted.

**Two new refusals.** `--create` refuses when another plan already claims the same `target-version`, and version resolution refuses when a version matches more than one folder. Two plans claiming one version is exactly the defect this scheme exists to prevent, so it must never be silently disambiguated.

**`--theme` is now required in practice.** The folder slug derives from it, and inventing a theme to name a folder would be the skill making a decision that belongs to the maintainer.

## 1.4.0 - 2026-08-27

**`disable-model-invocation` removed. This is a behavior change.**

The flag was set because "plan the release" is a common phrase. That remains true, and it is now
handled in the description rather than by a gate: explicit triggers ("create the release plan",
"promote these efforts into v0.5.0", "can we tag yet", "check release readiness") paired with an
explicit do-NOT-fire clause for general planning talk, release-notes or changelog requests, and
questions about what already shipped. Those three are the realistic false positives, and naming them
is something a boolean cannot do.

**Why now.** The flag was refusing approved invocations. It also meant the skill had never run in
this repository, so its own hygiene gates and doc-update checklist have never been exercised against
a real release, which is a worse state than an occasional misfire.

**What did not change.** `/plab-release-plan` with a subcommand still works. The five subcommands,
the six hygiene gates, the generated aggregation table, and the refusal to invent or modify
acceptance criteria are untouched.

**Note on `--gate`.** It is read-only and reports readiness. A misfire on `--gate` costs a report
nobody asked for. A misfire on `--create` or `--promote` would move folders, so those remain the ones
worth watching if the description turns out to be too broad.

## 1.3.0 - 2026-08-24

First public release. All five subcommands behave as they did privately: `--create`, `--promote`,
`--demote`, `--update`, `--gate`. The aggregation table is still generated rather than hand-edited,
and the skill still refuses to add or modify acceptance criteria. This entry records the move, not a
feature change.

**Why it moved.** `docs/internal/release-plans/` in this repository is the folder structure this
skill owns, and that folder's own README said so while naming a skill no reader could install. The
five release plans and sixteen effort folders committed there were produced against this skill's
contract. Tool and output now live together.

**Invocation is manual only, and this is a behavior change.** The skill ships with
`disable-model-invocation: true`. Privately it auto-triggered on "create release plan", "promote to
release" and "check release readiness". It no longer does. It runs when invoked as
`/plab-release-plan` with a subcommand. The always-on description budget in this plugin is paid by
one person in every session, and a release-management skill is reached for deliberately, on the
handful of days a release is actually being cut, rather than discovered mid-sentence.

**References repointed.** `/jp-spec` becomes `/plab-spec`. `/jp-implementation-plan` was retired
upstream with no successor here; the two places that named it as the producer of
`implementation-plan.md` now name `/superpowers:writing-plans`.

**Default checklist rows are unchanged.** The eight built-in doc-update rows were derived from the
private library's release contract, but they describe a conventional plugin layout and apply here
unmodified. This repository's `docs/internal/release-plans/release-checklist.yaml` already extends
them with five project-specific rows and marks one built-in (`docs/skills/README.md`, which does not
exist here) as not applicable. That is the extension mechanism working as designed, so the hardcoded
defaults were left alone; editing them would duplicate the YAML and collide with the documented
"built-in wins" merge rule. Only the prose attributing the defaults to a specific private repository
was neutralised.

**Not carried over.** The prior HISTORY file is not reproduced here; it referenced private-repo
layouts and planning folders that do not ship in this plugin.

**Example content genericised.** The worked examples in the reference files and usage docs used
effort folder names drawn from the private library's own backlog, including skills that have since
been retired. They now use neutral placeholder names, since what the examples teach is the folder
shape and the promotion ceremony, not the specific efforts.
