---
id: RL-01
title: "Implementation plan: release on merge"
type: implementation-plan
status: draft
created: 2026-11-21
updated: 2026-11-21
linked-spec: spec.md
linked-release: null
ac-coverage: complete
phase-count: 8
---

# Implementation plan: release on merge

Steps use checkbox syntax and phases run in order. A phase is done when every step is ticked and its Verification command has been run and its output quoted. **Stop and ask the maintainer before starting Phase 1.** This plan was written on request; building it was not yet approved.

**Goal:** a merged pull request that carries a new version releases itself. Before the merge, pull request checks prove that the version surfaces agree, that the bump size matches what merged since the last tag, that the CHANGELOG has the section, that every `Unreleased` release cell is filled, and that a skill change carries its eval result. After the merge, `.github/workflows/release-on-merge.yml` reruns the full tests on the merged commit, creates the tag and the GitHub Release in one job, and sends one repin request to the marketplace. `/plab-ship` decides whether and how much to bump, and pushes no tag. A repository without `RELEASING.md` and `.github/release-on-merge.json` behaves exactly as today.

**Spec:** `spec.md`

**Target versions:** the scripts and workflows are repository tooling and carry no version of their own. `plab-ship` goes from 1.1.0 to 1.2.0 in Phase 5. The plugin's own release of that change, in Phase 6, is the last one made by hand.

**Global constraints:**
- No em-dashes (U+2014) or en-dashes (U+2013) in any file this plan touches. One paragraph per line.
- Every new script is stdlib-only Python and follows the repository's exit contract: 0 clean, 1 a rule failed, 2 broken. Every run begins with its own self-test, and a self-test failure is exit 2, never read as clean.
- Every subprocess call pins `encoding="utf-8"`. The latest version tag is found with the glob `v[0-9]*.[0-9]*`, never a bare `git describe --tags`, because backup refs and floating tags sit nearer HEAD.
- Pull request titles and bodies reach a script through `env:`, never through `${{ }}` interpolation inside a `run:` line, because a title is attacker-shaped text.
- `gh release create` stays written out in the workflow YAML. The decision and the extraction live in scripts, the publishing call does not, so that the merge check's `release` rule can see it. Moving that call into a script to get a merge through would defeat the check, and the solo-repo merge rule forbids it.
- No tracked file cites a `_local/` path. The token is created and stored by the maintainer only; no step here creates, reads or prints it.

**What this plan settles that the spec left open (its Gaps):**
- **How the size check reads titles.** With git alone. This repository merges with merge commits, and a GitHub merge commit carries the pull request title as the first line of its body (for example `a9baf0c`, body `docs(rl-01): spec and ADR-3 for release on merge`). For each first-parent commit since the latest version tag, the title is the body's first line of a merge commit, and the subject of any other commit. The current pull request's title comes from the event. No API call is needed.
- **The token's permission.** GitHub's fine-grained permission reference lists `POST /repos/{owner}/{repo}/dispatches` under the Contents permission at write level. Medium-high confidence: that page was read through a summarizing fetcher, not verbatim. Phase 8 proves it with the first real dispatch, a 204 against a 403.
- **The names.** The configuration file is `.github/release-on-merge.json`. It is not `.github/release.yml`, which GitHub reads as its own release-notes configuration. The secret is `MARKETPLACE_REPIN_TOKEN`. The dispatch event type is `repin-plugin`, with a `client_payload` of four properties (`plugin`, `version`, `tag`, `sha`), within GitHub's limit of ten.
- **Codex updates.** Still unverified and out of scope, as the spec says.

**Choices this plan makes on [model-inference] ground, flagged for review:**
- A title with no recognised conventional type counts as a patch and is named in the check's output, rather than failing the check. Failing would block on any old untyped title since the tag.
- `perf` and `revert` count as patches, as Conventional Commits treats them. `build` and `style` join the spec's sizeless types.
- When the repin fails or the token is missing, the release job fails red after the Release exists. Recovery is the manual repin, documented in `RELEASING.md`. There is no automatic retry, because AC-9 forbids a rerun from sending a request once the tag and Release exist.

---

## Completion Status

| Phase | Goal | Fulfills AC | Owner | Status |
|---|---|---|---|---|
| P1 | One test command runs every check the gate job runs, and CI fails when the two drift | N/A (prerequisite for AC-2's test command and AC-7) | agent | Not started |
| P2 | The version-parity gate checks every surface the configuration lists | AC-3 | agent | Not started |
| P3 | The pull request checks exist, run in the gate job, and rerun on title and body edits | AC-1, AC-2, AC-4, AC-5, AC-6, AC-17 | agent | Not started |
| P4 | The release decision and the workflow's shape are scripts with self-tests | AC-7, AC-9, AC-10, AC-11, AC-12 (by fixture) | agent | Not started |
| P5 | `plab-ship` 1.2.0 states the bump rule and the tag owner, and the repository's rule texts agree | AC-14, AC-15, AC-16 | agent | Not started |
| P6 | The last manual release ships P1 to P5, and the installs carry `plab-ship` 1.2.0 | N/A (release bookkeeping) | agent; maintainer installs | Not started |
| P7 | This repository opts in: `RELEASING.md`, the configuration and the release workflow land together | AC-1, AC-9, AC-12, AC-13 (live) | agent; blocked on maintainer: D6 rule amendment, token | Not started |
| P8 | The first release through the pipeline, with the maintainer's go-ahead | AC-7, AC-8, AC-11 (live) | agent; maintainer go-ahead | Not started |

Pull request grouping: P1 to P3 in one pull request, P4 and P5 in a second, P6 is the release pull request, and P7 is the opt-in pull request. P7 must be last, because the release workflow and the opt-in files switch the pipeline on together (see Rollback).

---

## Phase 1: One test command, with a drift check

**Goal:** `python3 scripts/run-tests.py` runs, in order, every check that the `dash-check` and `document-gates` jobs of `gate.yml` run, and exits non-zero when any fails. `--check-gate` fails when the script's list and the jobs' `run:` lines differ, so the release workflow can never test less than the pull request did.

**Files:**
- Create `scripts/run-tests.py`
- Modify `.github/workflows/gate.yml` (one step added to `document-gates`)

**Fulfills:** N/A (prerequisite for AC-2's test command and AC-7)

**Steps:**
- [ ] `run-tests.py` holds `COMMANDS`, a list of the exact `run:` strings of the `python3 ...` steps in the `dash-check` and `document-gates` jobs, in job order. It runs each through `bash -c`, runs every one even after a failure, and prints one PASS or FAIL line per command and a summary. Exit 1 when any command exits non-zero.
- [ ] Setup lines are excluded by rule, not by list: a `run:` that does not start with `python3 ` (the `apt-get install ripgrep` step) is not a test. The `run-tests.py --check-gate` step excludes itself.
- [ ] `--check-gate [--workflow .github/workflows/gate.yml]` parses the two jobs' `run:` lines without a YAML library: find `  <job-id>:` at two-space indent, then each `run: ` value inside it until the next two-space key. Compare the sets. Exit 1 naming each command present on one side only.
- [ ] The toolkit grading in `standard-gate` is deliberately not in the list. It is a `product-on-purpose` action, AC-12 bars it from the release workflow, and `gate.yml` still runs it on every push to `main`, which includes the merge commit.
- [ ] Self-test, run first on every invocation: a fixture workflow with one extra and one missing command must make `--check-gate` fail; a fixture where one command exits 1 must make the runner exit 1.
- [ ] Add to `document-gates`, after the existing steps: `- name: The release test command matches this job` / `if: always()` / `run: python3 scripts/run-tests.py --check-gate`.

**Verification:** `python3 scripts/run-tests.py --check-gate` exits 0 and prints the command count. Deleting one entry from `COMMANDS` makes it exit 1 and name that command. `python3 scripts/run-tests.py` exits 0 on a clean checkout, after `pip install pyyaml` and with `rg` on the path.

---

## Phase 2: The version-parity gate checks the configured surfaces

**Goal:** `scripts/version-parity-check.py` gains location L7, read only when `.github/release-on-merge.json` exists. Every surface the configuration lists must carry `library.json`'s version, and a disagreement is a finding naming the file. This extends the existing gate, as the spec's Requirement 2 proposes, rather than adding a second one.

**Files:**
- Modify `scripts/version-parity-check.py`

**Fulfills:** AC-3

**Steps:**
- [ ] Add L7 to the docstring's location list: "`.github/release-on-merge.json`'s `surfaces`. Read only when that file exists. Each entry is `{\"path\": ..., \"json\": \"<dotted key>\"}` or `{\"path\": ..., \"pattern\": \"<regex with one group>\"}`; each must yield exactly one version equal to `library.json`'s." Remove the docstring's sentence that manifests are the toolkit's job only, and say they are now read when configured.
- [ ] A surface whose file is missing, whose key is absent, or whose pattern matches zero or several times is BROKEN (exit 2), for the same reason an empty location is BROKEN today: a matcher that has gone blind must not read as clean.
- [ ] L7 runs on every pull request, not only bumping ones. Surfaces that must always agree should agree between releases too, which is stricter than AC-3 and does not contradict it.
- [ ] The CHANGELOG heading and the `HISTORY.md` Release cells are not L7 surfaces: they hold many versions by design. P3 checks them.
- [ ] Self-test cases: no configuration file (L7 silent), all surfaces agree, one JSON surface disagrees (finding names the file), one pattern matches twice (BROKEN).

**Verification:** `python3 scripts/version-parity-check.py` exits 0 on this repository, which has no configuration yet. With a temporary configuration listing `.claude-plugin/plugin.json` and its `version` edited to `9.9.9`, it exits 1 and names `.claude-plugin/plugin.json`.

---

## Phase 3: The pull request checks

**Goal:** `scripts/release-check.py` enforces the spec's before-merge rules on a pull request, and does nothing in a repository that has not opted in. It runs in the `document-gates` job, so branch protection gates it, and the gate reruns when a title or body is edited.

**Files:**
- Create `scripts/release-check.py`
- Modify `.github/workflows/gate.yml` (the `pull_request` trigger and two steps in `document-gates`)

**Fulfills:** AC-1, AC-2, AC-4, AC-5, AC-6, AC-17

**Steps:**
- [ ] **Opt-in (AC-1).** When `RELEASING.md` or `.github/release-on-merge.json` is absent, print `NOT OPTED IN` with which file is missing, and exit 0 without reading anything else. Printing which file is missing keeps a half-done opt-in visible.
- [ ] **Configuration (AC-2).** The file must hold a non-empty `surfaces` list, a non-empty `test_command` string, and `plugin` as `{"repin": true|false, "marketplace": "<owner/name>"}`, with `marketplace` required when `repin` is true. A missing or malformed field is exit 1 naming the field.
- [ ] **Bump detection.** The bump is `library.json`'s version at HEAD against the latest version tag's version. Equal means no bump, and the size, CHANGELOG and `Unreleased` rules are skipped with a `no bump` line.
- [ ] **Size (AC-4).** Titles are the first-parent commits in `<tag>..HEAD`, excluding the pull request's own merge (in CI the checkout is the merge preview, so exclude `HEAD` itself when it is a merge whose second parent is the head SHA), read as the merge commit's body first line or a plain commit's subject, plus `PR_TITLE`. Parse `type(scope)!: ...`. A `!` or a `BREAKING CHANGE` footer is major; `feat` is minor; `fix`, `perf` and `revert` are patch; `docs`, `chore`, `refactor`, `test`, `ci`, `build` and `style` carry no size; anything else counts as a patch and is named. Below 1.0.0 a major raises the minor. With only sizeless types and a bump, the expected size is a patch. A version that is not the expected one fails with `expected <version>`.
- [ ] **CHANGELOG (AC-5).** Run `scripts/release-notes-from-changelog.py <version>` as a subprocess. Its exit 1 is this rule's failure, and its exit 2 is this script's exit 2.
- [ ] **`Unreleased` cells (AC-17).** With a bump, any row in any `skills/*/HISTORY.md` table whose Release column reads `Unreleased` is a failure naming the file and the row's version.
- [ ] **Eval line (AC-6).** For each `skills/*/SKILL.md` changed in `BASE_SHA...HEAD`, compare the `description` value and the text after the closing frontmatter line at both commits. A change to either requires a line in `PR_BODY` matching `^Behaviour evals: \d+/\d+ passed`. A change confined to `metadata` (such as `version` and `updated`) does not.
- [ ] **Push events.** Without `PR_TITLE` and `BASE_SHA`, the size and eval rules are skipped with a line saying so; the configuration, CHANGELOG and `Unreleased` rules still run. That keeps the push-to-`main` run meaningful and quiet.
- [ ] **Self-test**, run first: build throwaway git repositories with a pinned identity, and prove each rule fails on its own mutation. The cases are: spec Examples 1 and 3; the AC-4 Given/When/Then (`v0.14.1`, a `fix` title, `0.15.0` fails and names `0.14.2`); a metadata-only SKILL.md change needing no eval line; a body change without the line; one `Unreleased` row; the missing configuration field; and a repository with neither opt-in file.
- [ ] In `gate.yml`, change `on: pull_request:` to `pull_request:` with `types: [opened, synchronize, reopened, edited]`, so an edited title or body reruns AC-4 and AC-6.
- [ ] Add to `document-gates`: `- name: The release checks prove themselves` / `if: always()` / `run: python3 scripts/release-check.py --self-test`, then `- name: The release checks, against this pull request` / `if: always() && github.event_name == 'pull_request'` / `env:` `PR_TITLE: ${{ github.event.pull_request.title }}`, `PR_BODY: ${{ github.event.pull_request.body }}`, `BASE_SHA: ${{ github.event.pull_request.base.sha }}`, `HEAD_SHA: ${{ github.event.pull_request.head.sha }}` / `run: python3 scripts/release-check.py`. Add both `run:` strings to `COMMANDS` in `run-tests.py`, or `--check-gate` fails, which is the point of Phase 1.
- [ ] Touch no step in `standard-gate`. Its two `uses:` lines are not owned by the `actions` organization, and changing that job would bring them into AC-12's scope.

**Verification:** `python3 scripts/release-check.py --self-test` exits 0. Then `python3 scripts/release-check.py` on this repository prints `NOT OPTED IN` and exits 0. Then, with the bump-size comparison replaced by `True`, the self-test exits 2 and names the AC-4 case.

---

## Phase 4: The release decision and the workflow shape, as scripts

**Goal:** `scripts/release-on-merge.py` holds every decision the release workflow makes, proven by fixtures and a fake `gh`, so that AC-7 to AC-12 are tested before any live release. The workflow YAML itself lands in Phase 7.

**Files:**
- Create `scripts/release-on-merge.py`
- Modify `.github/workflows/gate.yml` (one step in `document-gates`), `scripts/run-tests.py` (`COMMANDS`)

**Fulfills:** AC-7, AC-9, AC-10, AC-11, AC-12 (by fixture; live proof in P7 and P8)

**Steps:**
- [ ] `decide [--gh <path>]` writes `key=value` lines to `$GITHUB_OUTPUT` when it is set, and to stdout always. It reads the opt-in files, `library.json`'s version, whether tag `v<version>` exists (`git tag -l` after a full fetch), and whether its Release exists (`gh release view v<version>`, exit 0 or not). The decision table:

  | Opted in | Tag | Release | `action` | `repin` |
  |---|---|---|---|---|
  | no | any | any | `none` | false |
  | yes | yes | yes | `none` | false |
  | yes | no | no | `tag-and-release` | the configuration's `plugin.repin` |
  | yes | yes | no | `release-only` | the configuration's `plugin.repin` |
  | yes | no | yes | exit 2, a Release without its tag is a state no step here creates | |

  It also outputs `version`, `tag`, `marketplace` and `test_command`.
- [ ] `workflow-check [<file>]` reads `.github/workflows/release-on-merge.yml` and `gate.yml`'s `document-gates` job as text and fails when: any `uses:` names an owner other than `actions` (AC-12); any step containing `gh release create` comes before the step that runs the test command, or carries an `if:` with `always()` or `failure()` (AC-7); the file has no `concurrency:` group with `cancel-in-progress: false` (the spec's reliability requirement); or a `run:` line interpolates `${{ github.event`.
- [ ] Self-test, run first: the five table rows with a fake `gh` script that answers `release view` from a fixture; `workflow-check` against a correct fixture workflow and against four mutations (a third-party `uses:`, publish before test, `if: always()` on publish, no concurrency), each of which must fail.
- [ ] Add `- name: The release workflow decision and shape prove themselves` / `if: always()` / `run: python3 scripts/release-on-merge.py --self-test` to `document-gates`, and to `COMMANDS`.

**Verification:** `python3 scripts/release-on-merge.py --self-test` exits 0, and `python3 scripts/release-on-merge.py decide` on this repository prints `action=none`. Removing the tag-exists branch makes the self-test exit 2 and name the `release-only` row.

---

## Phase 5: `plab-ship` 1.2.0 and the repository's rule texts

**Goal:** `plab-ship` knows when a repository releases on merge, states the default bump rule, carries the release in the branch's own pull request there, and pushes no tag. The rule sentences in `AGENTS.md` and `plab-ship` no longer forbid what the pipeline does in an opted-in repository. Line numbers below are from `main` at `a9baf0c`; re-verify them before editing.

**Files:**
- Modify `skills/plab-ship/scripts/derive-ship-facts.py`, `skills/plab-ship/scripts/test-ship-scripts.py`, `skills/plab-ship/scripts/ship-check.py` (rule R7 only, if needed)
- Modify `skills/plab-ship/SKILL.md`, `skills/plab-ship/HISTORY.md`, `docs/skills/plab-ship/README.md`
- Modify `AGENTS.md`, `library.json`, `docs/status-skills.md`, and regenerate the manifests

**Fulfills:** AC-14, AC-15, AC-16

**Steps:**
- [ ] `derive-ship-facts.py`: add `"on_merge": (repo / "RELEASING.md").is_file() and (repo / ".github/release-on-merge.json").is_file()` to the `release` facts beside `plugin_repo` (line 427). Add a test for both values.
- [ ] `SKILL.md` line 92, heading. Before: `### 7. Release, only with `--release``. After: `### 7. Release`.
- [ ] `SKILL.md` line 94. Before: "Without the flag, create no version, tag or release. Write that the release was not approved in the record's Release section, and go to step 8." After, as two paragraphs ahead of it:

  "**When `release.on_merge` is true**, the repository releases on merge and needs no flag. Decide for each branch, before it is verified, whether it releases, because the bump is part of the branch. Bump for a change to what users run: a skill's `SKILL.md`, its scripts, its references, or `lib/`. Do not bump for internal material only: CI, internal documents, release plans or tests. You may hold a bump back to group several pull requests into one release; name every held-back bump in the report. When the branch releases, size the version with the table below against everything merged since `release.latest_version_tag`, set it in every surface `.github/release-on-merge.json` lists, fill every `Unreleased` Release cell in `skills/*/HISTORY.md` with the new tag, add the CHANGELOG section, and, when the branch changes a skill's description or body, put a `Behaviour evals: N/M passed` line from a local `claude plugin eval . --no-publish` run in the pull request body. Push no tag and create no GitHub Release: after the merge, the release workflow reruns the tests, tags and publishes. Confirm that its run succeeded, and record the version, its `**Why:**` line and the run's result in the Release section."

  "**Otherwise, release only with `--release`.** Without the flag, create no version, tag or release. Write that the release was not approved in the record's Release section, and go to step 8."
- [ ] `SKILL.md` line 157. Before: "- **No version without the flag.** A merge never creates a tag or a release on its own." After: "- **No version without the flag, except where the repository releases on merge.** Elsewhere a merge never creates a tag or a release on its own. Where `release.on_merge` is true, the version travels in the pull request, and the release workflow, never this skill, creates the tag and the Release."
- [ ] `ship-check.py` R7 (line 277 onward) accepts a version with `Why:`, or `not approved`. Check that a held-back bump, recorded as `none: held back` with a `Why:`, passes or fails as intended; if R7 rejects it, extend R7 and its self-test mutation. Bump `plab-ship` to 1.2.0 either way.
- [ ] `AGENTS.md` line 186. Before: "CI reports; it never fixes, bumps, or tags." After: "CI reports; it never fixes or bumps. One workflow tags: in a repository that carries `RELEASING.md` and `.github/release-on-merge.json`, `.github/workflows/release-on-merge.yml` tags and publishes a version that a merged pull request already carries, after rerunning the tests on the merged commit."
- [ ] `AGENTS.md`, the `publish-release.yml` paragraph. Before: "**This does not weaken the line above.** It chooses no version, writes no file, and creates no tag;". After: "It chooses no version, writes no file, and creates no tag, and it now serves only a tag the maintainer pushes by hand;".
- [ ] `AGENTS.md`, the `plab-ship` entry: add one sentence after "merge only on `VERDICT: merge` from the maintainer's merge check.": "In a repository that releases on merge, the version travels in the branch's own pull request and the release workflow tags it, so the skill pushes no tag."
- [ ] `docs/skills/plab-ship/README.md`: the `--release` table (line 88) gains a row for an opted-in repository; line 238 "No version, tag or release without `--release`." gains "outside a repository that releases on merge".
- [ ] Bump `plab-ship` to 1.2.0 in `SKILL.md` `metadata.version` and `updated`, `library.json`, `docs/status-skills.md` and the usage README; add a `HISTORY.md` row reading `Unreleased` in its Release cell; regenerate the manifests.
- [ ] The body change needs an eval run under decision D3 (evals run locally), and the pipeline is not on yet, so run `claude plugin eval . --no-publish` with the flags in `evals/README.md`, at least the `ship-manual-no-fire` case, and quote the result in the pull request body as `Behaviour evals: N/M passed`.

**Verification:** `python3 skills/plab-ship/scripts/test-ship-scripts.py` and `python3 skills/plab-ship/scripts/ship-check.py --self-test` exit 0; `python3 scripts/version-parity-check.py` exits 0; and `grep -n "never fixes, bumps, or tags\|No version without the flag\.\*\*" AGENTS.md skills/plab-ship/SKILL.md` prints nothing (AC-14).

---

## Phase 6: The last manual release

**Goal:** P1 to P5 are released as one minor version through today's path, and both installs carry `plab-ship` 1.2.0 before the pipeline switches on. Without this, the installed `plab-ship` 1.1.0 would still open a `chore(release)` pull request and push a tag, racing the workflow.

**Files:** the version surfaces, `CHANGELOG.md`, and every `HISTORY.md` row reading `Unreleased`, through a `chore(release): release vX.Y.Z` pull request.

**Fulfills:** N/A (release bookkeeping)

**Steps:**
- [ ] Run `/plab-ship --release`. The tag and the Release need the maintainer's yes, which `--release` gives for that run.
- [ ] Repin `prisant-labs/agent-plugins` (pre-approved), and ask the maintainer to update the Claude Code and Codex installs.
- [ ] Prove the install with a behaviour only 1.2.0 has: the facts report `release.on_merge`.

**Verification:** `gh release view vX.Y.Z -R prisant-labs/prisant-powertools` shows the Release, and a fresh session's `derive-ship-facts.py` output contains `"on_merge": false`.

---

## Phase 7: This repository opts in

**Goal:** `RELEASING.md`, `.github/release-on-merge.json` and `.github/workflows/release-on-merge.yml` land in one pull request, and the merge's own workflow run finds the version already released and does nothing. **Blocked until** the maintainer has amended the solo-repo merge rule and its check for opted-in repositories (decision D6, rules amended for opted-in repositories only) and stored the token (decision D2, a fine-grained token on the marketplace repository). Until D6 is amended, the merge check asks the maintainer on this pull request and every one after it, because the new workflow contains `gh release create`. The maintainer may instead merge this pull request by hand.

**Files:**
- Create `RELEASING.md`, `.github/release-on-merge.json`, `.github/workflows/release-on-merge.yml`
- Modify `.github/workflows/publish-release.yml` (header only), `docs/internal/release-plans/release-checklist.yaml` (header only), `README.md` if it describes releasing

**Fulfills:** AC-1, AC-9, AC-12, AC-13 (live; the workflow also carries AC-8, which Phase 8 proves live)

**Steps:**
- [ ] `.github/release-on-merge.json`: `surfaces` for `library.json` (`version`), `.claude-plugin/plugin.json` (`version`), `.codex-plugin/plugin.json` (`version`), `manifest.generated.json` (its version key, read the file first), and `docs/status-skills.md` (pattern `^\*\*Plugin version:\*\* (\d+\.\d+\.\d+)`); `test_command` `python3 scripts/run-tests.py`; `plugin` `{"repin": true, "marketplace": "prisant-labs/agent-plugins"}`.
- [ ] `release-on-merge.yml`: `on: push: branches: [main]`; `permissions: contents: write`; `concurrency: { group: release-on-merge, cancel-in-progress: false }`; one job. Steps: `actions/checkout` with `fetch-depth: 0`; `actions/setup-python`; `python3 scripts/release-on-merge.py decide` (id `decide`, `GH_TOKEN: ${{ github.token }}`); when `action` is not `none`: install `ripgrep` and `pyyaml`, run the test command through `env: TEST_COMMAND` and `bash -c "$TEST_COMMAND"`, extract the notes with `scripts/release-notes-from-changelog.py`, then publish. For `tag-and-release`, `gh release create "$TAG" --target "$GITHUB_SHA" --title "$TAG" --notes-file release-notes.md`, which creates the tag and the Release in one call (AC-8). For `release-only`, the same with `--verify-tag` in place of `--target` (AC-10). Then, when `repin` is true, `gh api "repos/$MARKETPLACE/dispatches" -f event_type=repin-plugin -f "client_payload[plugin]=prisant-powertools" -f "client_payload[version]=$VERSION" -f "client_payload[tag]=$TAG" -f "client_payload[sha]=$GITHUB_SHA"` with `GH_TOKEN: ${{ secrets.MARKETPLACE_REPIN_TOKEN }}`, failing with a named message when the secret is empty.
- [ ] A tag created with the default workflow token starts no other workflow, so `publish-release.yml` does not fire twice. Its header gains: "In a repository that releases on merge, `release-on-merge.yml` creates the tag and the Release together; this workflow serves only a tag pushed by hand."
- [ ] `RELEASING.md`, three sections (AC-13): **What a merge does** (the decision table in plain English, and that a merge without a version bump releases nothing); **How to stop it** (disable the workflow in the repository's Actions settings, or delete `.github/release-on-merge.json`, which turns every check and the workflow into no-ops); **Undoing a bad release** (publish a new patch release; a published version is never withdrawn by deleting its tag, because installs and the marketplace may already point at it). Add **When the repin fails**: the Release exists, the job is red, and the repin is done by hand in `prisant-labs/agent-plugins` as before; until that repository's receiver exists, every repin is by hand and the dispatch only proves the token.
- [ ] `release-checklist.yaml` header: the paragraph saying "Nothing else changes. The workflow chooses no version and writes no file; every row below is still a human edit." gains "In this repository, which releases on merge, these rows are edited in the pull request that carries the release, and `release-on-merge.yml` tags it."
- [ ] Run `python3 scripts/release-on-merge.py workflow-check` and `python3 scripts/release-check.py` (which no longer prints `NOT OPTED IN`) before opening the pull request.

**Verification:** after the merge, the workflow's run on the merge commit shows `action=none`, because the Phase 6 version already has its tag and Release (AC-9, live), and `gh release list -L 1` still shows the Phase 6 Release only.

---

## Phase 8: The first release through the pipeline

**Goal:** the next user-facing change releases with no step beyond `/plab-ship`. This is the pilot, run only with the maintainer's go-ahead.

**Files:** whatever that change is, plus its version surfaces and CHANGELOG section.

**Fulfills:** AC-7, AC-8, AC-11 (live)

**Steps:**
- [ ] With the maintainer's go-ahead, ship one small user-facing fix through `/plab-ship` without `--release`. The pull request carries the bump and passes the P3 checks.
- [ ] After the merge, read the release workflow's run: tests passed, then the tag and the Release appeared in the same job, then the dispatch returned 204. A 403 from the dispatch means the token's permission is wrong: report it to the maintainer, and repin by hand.
- [ ] Record the result in this phase as the CS-01 plan records its live runs.

**Verification:** `gh run list -w release-on-merge.yml -L 1` shows success; `gh release view vX.Y.Z` shows the CHANGELOG section as notes; and the run log shows one `dispatches` call with status 204.

---

## CI and Documentation Coverage

**CI.** `gate.yml` changes in two ways. Its `pull_request` trigger adds the `edited` type. Its `document-gates` job gains four steps: the test-command drift check, the release checks' self-test, the release checks against the pull request, and the decision and shape self-test. Every new step stays in `document-gates`, because branch protection requires checks by job name, and that job uses only `actions/checkout` and `actions/setup-python`. `standard-gate` and `dash-check` are unchanged. One new workflow, `release-on-merge.yml`, lands in Phase 7. `publish-release.yml` changes only in its header.

**Documentation.** `CHANGELOG.md` under Unreleased in each pull request; `plab-ship`'s `HISTORY.md` and usage README; `AGENTS.md` (the CI clause, the `publish-release.yml` paragraph, the `plab-ship` entry); the new `RELEASING.md`; the headers of `publish-release.yml` and `release-checklist.yaml`; `docs/status-skills.md` for the version. The `gate.yml` header line "CI reports. It does not release, auto-fix, bump, or tag" stays true of that file and is left alone. The spec's Task Summary and `linked-plan` point at this plan from the pull request that adds it.

## Rollback

**The partial-rollback hazard.** The opt-in files and the release workflow must stay together. Removing the workflow while `RELEASING.md` and `.github/release-on-merge.json` remain leaves `plab-ship` bumping versions that nothing tags. Removing the configuration while the workflow remains is safe, because `decide` then reports `action=none`. So the first and safest stop is to delete `.github/release-on-merge.json`, which turns P3's checks, P2's L7 and the workflow into no-ops in one commit.

**Full rollback.** Delete `.github/workflows/release-on-merge.yml`, `.github/release-on-merge.json`, `RELEASING.md`, `scripts/release-on-merge.py`, `scripts/release-check.py` and `scripts/run-tests.py`. Remove their steps from `document-gates` and the `edited` type from the trigger. Remove L7 and its self-test cases from `version-parity-check.py`. Restore the `AGENTS.md` sentences quoted as "Before" in Phase 5. Release `plab-ship` with the opted-in branch removed, or leave it, because without the opt-in files `release.on_merge` is false and 1.2.0 behaves as 1.1.0. Restore the two workflow and checklist header sentences.

**What does not unwind.** A Release the pipeline published stays published; undo it with a new patch release, as `RELEASING.md` says. A repin already merged in `prisant-labs/agent-plugins` is undone there. The maintainer's D6 amendment of the merge rule lives in the maintainer's own configuration repository and is reverted there, by the maintainer. There is no schema change and no data migration.
