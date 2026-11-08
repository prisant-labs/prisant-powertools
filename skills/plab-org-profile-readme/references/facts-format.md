# Facts format

`scripts/derive-profile-facts.py` writes one JSON object. Every later step reads it, and nothing else about GitHub, so a run's facts come from one call.

| Field | Meaning |
|---|---|
| `format` | The format version, `1` |
| `org` | The organization's login, as GitHub spells it |
| `owner_type` | Always `Organization`; a user account stops the script with exit 2 |
| `generated_at` | When the facts were gathered, in UTC |
| `profile.repo_state` | `present` or `missing`: whether `<org>/.github` exists |
| `profile.page`, `profile.standard` | `present` or `missing`, for `profile/README.md` and `profile/standard.json` |
| `profile.default_branch` | The `.github` repository's default branch |
| `profile.other_open_prs` | Open pull requests in `.github` that this skill did not open: number, branch and title |
| `open_pr` | The open pull request from an earlier run of this skill, found by its branch prefix `plab-org-profile-readme/`, or `null` |
| `covered` | Every public repository that is not a fork, not archived and not `.github`, with the fields below |
| `public_forks` | Every public fork, with the same fields and `parent`. A standard lists the ones the page shows under `include` |
| `archived` | The names of the public archived repositories |
| `counts` | How many repositories are public, private, forks and archived |
| `private_digests` | The SHA-256 hex digest of each private repository's lowercased name. The name itself never appears |

Each repository in `covered` and `public_forks` carries:

| Field | Meaning |
|---|---|
| `name`, `description`, `topics`, `default_branch`, `html_url`, `license` | As GitHub reports them; `license` is the SPDX id or `null` |
| `created_at`, `pushed_at` | When the repository was created, and last pushed |
| `newest_release` | The newest release that is not a draft, prereleases included: `tag`, `published_at`, `prerelease`. `null` when there is none |
| `latest_stable` | The newest release that is neither a draft nor a prerelease, or `null` |
| `releases` | Up to five releases, newest first |
| `tags` | Every tag name, for checking release links |

## Why a private name is a digest

The page and its pull requests are public. A run's credentials can often see private repositories, and anything in the facts can end up in prose. Carrying a digest instead of the name keeps the name out of the agent's context entirely, while the checker can still hash each word of a page and reject a match (rule R7).
