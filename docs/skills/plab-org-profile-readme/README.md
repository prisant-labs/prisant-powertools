# plab-org-profile-readme

**Version:** 1.1.0
**Source:** [`skills/plab-org-profile-readme/`](../../../skills/plab-org-profile-readme/)

Keep a GitHub organization's profile page to a standard you choose once, and true to the organization's public repositories. Each run opens or updates one pull request in the organization's `.github` repository, and you review and merge it. Manual invocation only.

The page is `profile/README.md` in `<org>/.github`, which GitHub shows on the organization's front page. Its standard is `profile/standard.json` beside it. User account pages are out of scope.

---

## Getting Started

### Before You Start

You need Python 3 and `gh`, signed in with access to the organization. The run reads every repository the organization has and writes only to `.github`, on a branch.

### Quick Start

```
/plab-org-profile-readme example-org --setup
```

Replace `example-org` with your organization. The first run establishes the standard. You pick one of three built-in standards, adopt the page you already have, or define your own, and set seven options such as badges and recent releases. The run then writes the page to that standard and opens a pull request carrying both files.

### Common Invocations

```
# Bring the page up to date with the repositories
/plab-org-profile-readme example-org

# Do that, and also carry out an instruction
/plab-org-profile-readme example-org "mark the new repository as experimental"

# Leave a repository off the page, with the reason recorded in the standard
/plab-org-profile-readme example-org "ignore scratch-repo: it holds experiments, not a project"

# Revise the standard: change an option, a category or an exclusion
/plab-org-profile-readme example-org --setup
```

### Installation

The skill ships with the plugin. See the [root README](../../../README.md) for installing it in Claude Code or Codex.

### Words Used Here

- **Standard:** the page's format, recorded in `profile/standard.json`: its sections in order, seven options, its categories, and the repositories it leaves out or adds, each with a reason.
- **Covered repository:** one the page must account for. It is public, not a fork, not archived, and not `.github`.
- **Entry:** a heading, list item or table row whose first link points at a repository.
- **Ignored repository:** a covered repository the page leaves out on purpose. It is recorded in the standard's `exclude` list with a reason, and the checker fails a page that lists it anyway.

---

## When to Use

- An organization's page has drifted: a missing repository, a stale release, a wrong count.
- You want an organization's page to follow a standard that a checker enforces.
- A refresh pull request is waiting for review and has gone stale.

## When NOT to Use

- To edit a repository's own README. This skill only reads those.
- For a user account's profile page, `<user>/<user>/README.md`.
- To merge the update. The skill never merges.

---

## The three built-in standards

| Standard | Shape | Suits |
|---|---|---|
| **Catalog** | A legend, an index by category, then a section per project with badges and recent releases | Many projects, browsed by kind |
| **Compact** | One table: project, description, status, latest release | A small organization, or one whose visitors want a list |
| **Showcase** | A few featured projects described at length, then a short list of the rest | Two or three flagship projects |

Each has a sample page under [`examples/standards/`](../../../skills/plab-org-profile-readme/examples/standards/), and a reference under [`references/standards/`](../../../skills/plab-org-profile-readme/references/standards/).

## How It Works

1. **One script call gathers the facts.** `derive-profile-facts.py` reads the organization: its covered repositories with their releases and tags, its public forks and archived repositories, the current page and standard, and any open pull request from an earlier run. A private repository appears only as a digest of its name, so its name never reaches the agent.
2. **The page is written to the standard.** With no page, a scaffold fills every fact and marks each sentence a person should write. With a page, only what the facts contradict or your instruction asks changes. When a covered repository is new to the page, the run asks you once whether to add or ignore each one before it writes anything. The question needs your answer: a run that cannot ask stops before it writes the page, and opens nothing.
3. **A checker decides when the page is done.** `profile-check.py` runs fourteen rules. Seven check facts: every covered repository is listed or excluded, and no excluded one is listed, no link points at a missing, archived or private repository, release links name real tags, and the newest release is the one shown. Six check the standard: sections in order, shared text, badges, recent changes, labels and featured order. One checks the pull request body.
4. **One pull request.** A pull request from an earlier run is updated in place instead of stopping the run, because the scheduled refresh jobs that kept these pages before this skill stopped whenever their last pull request was still waiting. When nothing changed, nothing is opened.

**When it stops early.** With no organization named, it asks which one, and never guesses from the folder you are in. With no `.github` repository, it asks you to create one. With no standard, it checks the page against the seven fact rules, opens nothing and suggests `--setup`; with no page either, it says there is nothing to check.

## Output

A branch named `plab-org-profile-readme/<YYYY-MM-DD>` in `<org>/.github`, with the page and, after `--setup`, the standard, and one pull request. Its body lists what changed from the repositories apart from what changed from your instructions, and anything noticed but not changed.

## Its Own Gate

Every checker run first proves its fourteen rules against the committed sample in [`examples/sample-run/`](../../../skills/plab-org-profile-readme/examples/sample-run/), one mutation per rule. Exit 2 means a rule could not fail its mutation, and the page is unchecked, never clean. CI runs the self-test and `test-profile-scripts.py` on every pull request.

## How to Tell It Worked

The run ends with a pull request link, or with "the page is current". To check a page yourself, gather the facts and run the checker on the branch's page and standard, from the plugin's `skills/plab-org-profile-readme/scripts/` folder:

```
python derive-profile-facts.py example-org --out facts.json
python profile-check.py --page README.md --facts facts.json --standard standard.json
```

Exit 0 and a line beginning `CLEAN: canary proved` mean every rule passed.

## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| The run stops at its first step and names a cause | The facts script could not read the organization: `gh` is not signed in, the owner does not exist, or it is a user account | Run `gh auth status`, sign in with `gh auth login` if needed, and check the organization's name |
| `FINDING` lines that remain at the end of a run | The run could not make the page satisfy a rule, often because a fact needs your call, such as a release to skip | Answer the finding: add the repository, ignore it, or skip the release with a reason, then run again |
| `BROKEN:` or exit 2 from the checker | The checker could not prove its own rules, or could not read an input. The page is unchecked, never clean | Run `python profile-check.py --self-test`; if it fails, the installed skill is damaged, so reinstall the plugin |
| The push or the pull request is refused | Your `gh` account cannot write to `<org>/.github` | Ask an organization owner for write access, then run again |
