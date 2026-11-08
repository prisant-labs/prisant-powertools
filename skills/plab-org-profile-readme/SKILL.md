---
name: plab-org-profile-readme
description: "Keep a GitHub organization's profile README, <org>/.github/profile/README.md, to a standard and true to its public repositories. Use when an organization page has drifted from its repositories, needs a standard format, or has a stale refresh pull request. --setup picks Catalog, Compact or Showcase, adopts the existing page, or defines a custom standard. Each run updates the page from repository facts or a quoted instruction, checks it, and opens or updates one pull request. Never merges. Explicit invocation only: run /plab-org-profile-readme."
argument-hint: "<org> [--setup] [\"<instructions>\"]"
disable-model-invocation: true
license: MIT
metadata:
  version: "1.0.0"
  updated: 2026-11-08
---

# Organization Profile README

Keep one GitHub organization's profile page to its standard and true to its public repositories, then open or update one pull request for the maintainer to review. The page is `profile/README.md` in the organization's `.github` repository. Its standard is `profile/standard.json` beside it.

## Input

| Input | Default | Notes |
|-------|---------|-------|
| `<org>` | Required | A GitHub organization. A user account is refused: this skill covers organization pages |
| `--setup` | Off | Establish or revise the organization's standard, then write the page to it |
| `"<instructions>"` | None | Free text, such as "add a Start here section". Applied on top of what the facts require |

## Output

- A branch and one pull request in `<org>/.github`, or nothing when the page is current.
- With `--setup`, a `profile/standard.json` on that branch as well.
- A short report: the pull request, what changed and why, and anything unverified.

## Workflow

### 1. Gather the facts

Work in a temp folder outside every repository. Run:

```bash
python <this skill's base directory>/scripts/derive-profile-facts.py <org> --out <temp>/facts.json --save <temp>
```

On exit 2, report the named cause and stop. A user account, an owner that does not exist and a failed GitHub call all stop the run here.

The facts name every covered repository: public, not a fork, not archived, and not `.github`. They name public forks and archived repositories in their own lists. They carry each private repository only as a digest of its name, so no private name can reach you through them. `references/facts-format.md` lists every field.

Read `profile.other_open_prs`. When it holds a pull request that edits the page, such as one from an older automation, name it and ask the maintainer how to proceed, because this run would otherwise open a second pull request beside it.

### 2. Choose the mode

| State in the facts | Mode |
|---|---|
| `--setup` was passed | Set up (step 3), then write the page (step 4) |
| `profile.standard` is `missing` | Check only: run the checker without a standard, report its findings and the rules it skipped, and suggest `--setup`. Open nothing |
| `profile.standard` is `present` and `profile.page` is `missing` | Scaffold the page (step 4) |
| Both are `present` | Refresh the page (step 4) |

### 3. Set up the standard, only with `--setup`

Follow `references/setup-interview.md`. It lists what the interview must establish, not how to ask, because Claude Code and Codex ask differently. When the organization already has a standard, its values are the defaults.

Write the answers to `<temp>/answers.json`, then run:

```bash
python <this skill's base directory>/scripts/write-standard.py --base <base> --answers <temp>/answers.json --out <temp>/standard.json
```

For the adopted path, pass `--base adopted --from-page <temp>/current-page.md --facts <temp>/facts.json` instead. Show the maintainer the standard it wrote, especially every exclusion and inclusion it recorded with "confirm" in the reason, and change what they correct before you go on. Adoption turns whatever the page does now into a rule, including an accident.

### 4. Write the page

Read the reference for the standard's base in `references/standards/`, and `references/standard-format.md` for what each option means.

- **No page yet:** run `scripts/scaffold-page.py --standard <standard> --facts <temp>/facts.json --out <temp>/README.md`. Replace every `<!-- describe: ... -->` marker with prose drawn from that repository's own README and release notes.
- **A page exists:** start from `<temp>/current-page.md`. Change what the facts contradict and what the instructions ask, and nothing else. Keep the page's voice and its hand-written lines.

For every repository the page covers:

- Base every claim on the repository's README, its release notes or its changelog. Write for a person using the tool, and drop internal reference ids.
- Never name a private repository, on the page or in the pull request body, even when an instruction asks for it.
- Add a repository the facts cover and the page lacks, in the place its standard gives it. List it first in the pull request body.
- When a newer release changed nothing a user would notice, you may leave it off the page. Add it to the standard's `skip_releases` with that reason, and list it in the pull request body.

### 5. Check the page

Write the pull request body first, in the shape of `references/pr-body.md`. Then run:

```bash
python <this skill's base directory>/scripts/profile-check.py --page <temp>/README.md --facts <temp>/facts.json --standard <standard> --pr-body <temp>/pr-body.md [--instructions-given]
```

Pass `--instructions-given` when the run carried instructions. Exit 0 means every rule passed. Exit 1 names each finding: fix the page or the body and run it again. Exit 2 means the checker could not prove itself or could not read an input: report the page as unchecked and stop, because exit 2 is never clean. A NOTE line does not fail the page; repeat it in the body under "Noticed but not changed".

### 6. Branch, commit, and open or update the pull request

Never commit to the default branch. When the checked page is identical to the current one, make no branch and say the page is current. When the facts report an open pull request from an earlier run, update that branch and rewrite its body instead of opening another.

Otherwise, clone `<org>/.github` into the temp folder, create a branch named `plab-org-profile-readme/<YYYY-MM-DD>`, write the page and any standard, commit, push, and open the pull request with the checked body. The branch prefix is how a later run recognises the pull request as its own. Never merge it: the maintainer reviews and merges.

### 7. Report

Report the pull request link, or that the page is current. Then list what changed from the facts, what changed from the instructions, every NOTE, and anything you could not verify.

## Instructions

A quoted instruction changes the page beyond what the facts require, for example "mark the new repository as experimental". Apply it within the standard. When the instruction needs the standard itself to change, such as a new section, change the standard on the same branch and say so. List the instruction's changes under "From your instructions" in the body, apart from the fact-driven changes. Refuse an instruction that would name a private repository, commit to the default branch or merge, and say why.

## Constraints

- **The checker decides, not confidence.** A page is done when `profile-check.py` exits 0, never because it looks right.
- **One repository is written.** The skill reads every other repository and writes only `<org>/.github`, on a branch.
- **Never merge.** The maintainer reviews and merges every pull request.
- **No private names.** Not on the page, not in the body, not in the standard, whatever the instruction.
- **Ids carry handles.** Never write a bare reference id; pair it with a short handle on first use.

## References

| File | Load when |
|------|-----------|
| `references/facts-format.md` | Step 1 |
| `references/setup-interview.md` | Step 3 |
| `references/standard-format.md` | Steps 3 and 4 |
| `references/standards/catalog.md`, `compact.md`, `showcase.md` | Step 4, for the standard's base |
| `references/pr-body.md` | Step 5 |
