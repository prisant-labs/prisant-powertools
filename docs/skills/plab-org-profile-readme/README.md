# plab-org-profile-readme

**Version:** 1.0.0
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

# Revise the standard: change an option, a category or an exclusion
/plab-org-profile-readme example-org --setup
```

### Installation

The skill ships with the plugin. See the [root README](../../../README.md) for installing it in Claude Code or Codex.

### Words Used Here

- **Standard:** the page's format, recorded in `profile/standard.json`: its sections in order, seven options, its categories, and the repositories it leaves out or adds, each with a reason.
- **Covered repository:** one the page must account for. It is public, not a fork, not archived, and not `.github`.
- **Entry:** a heading, list item or table row whose first link points at a repository.

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
2. **The page is written to the standard.** With no page, a scaffold fills every fact and marks each sentence a person should write. With a page, only what the facts contradict or your instruction asks changes.
3. **A checker decides when the page is done.** `profile-check.py` runs fourteen rules. Seven check facts: every covered repository is listed or excluded, no link points at a missing, archived or private repository, release links name real tags, and the newest release is the one shown. Six check the standard: sections in order, shared text, badges, recent changes, labels and featured order. One checks the pull request body.
4. **One pull request.** A pull request from an earlier run is updated in place instead of stopping the run, which is how the old weekly routines stalled. When nothing changed, nothing is opened.

## Output

A branch named `plab-org-profile-readme/<YYYY-MM-DD>` in `<org>/.github`, with the page and, after `--setup`, the standard, and one pull request. Its body lists what changed from the repositories apart from what changed from your instructions, and anything noticed but not changed.

## Its Own Gate

Every checker run first proves its fourteen rules against the committed sample in [`examples/sample-run/`](../../../skills/plab-org-profile-readme/examples/sample-run/), one mutation per rule. Exit 2 means a rule could not fail its mutation, and the page is unchecked, never clean. CI runs the self-test and `test-profile-scripts.py` on every pull request.

## How to Tell It Worked

The run ends with a pull request link, or with "the page is current". Run the checker yourself on the branch's page with the run's facts and standard: exit 0 and a line beginning `CLEAN: canary proved` mean every rule passed.
