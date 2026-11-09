# Standard format

An organization's standard is one JSON file, `profile/standard.json`, beside the page in its `.github` repository. GitHub renders only `profile/README.md` on the organization page, so the standard does not appear there. Anyone who browses the `.github` repository can read it, so it never names a private repository. JSON keeps every script stdlib-only.

`scripts/write-standard.py` writes it, and `scripts/profile-check.py` validates it before every check. A standard that breaks this format is broken input, exit 2, and never a finding against the page.

## Fields

| Field | Meaning |
|---|---|
| `format` | `1` |
| `org`, `display_name` | The organization's login, and the name its page's title shows |
| `base` | `catalog`, `compact` or `showcase` for a built-in standard, `adopted` for one read from an existing page, or `custom` |
| `sections` | The page's headings, in order. Each is `{id, kind, heading}` with kind `fixed`, a heading the page must carry such as `"## Projects"`, or `{id, kind: "categories", level}`, which stands for one heading per category at that level |
| `options` | The seven options below |
| `categories` | Ordered `{name, repos}`. Each repository sits under its category's heading |
| `exclude` | `{repo, reason}` for a covered repository the page leaves out, which is how a repository is ignored. The reason is at least three words. R1 fails a page that still lists an excluded repository, and notes an exclusion the facts no longer cover |
| `include` | `{repo, reason}` for a public fork the page shows. Forks are left out unless included |
| `skip_releases` | `{repo, tag, reason}` for a release the page leaves out because it changed nothing a user would notice |

## Options

| Option | Values | Checked by |
|---|---|---|
| `recent_changes` | `false`, or the most entries one recent-changes block may hold | R11 |
| `badges` | `false`, or the kinds allowed: `release`, `license`, `ci`, `dynamic`, `static`, `other` | R10 |
| `status_labels` | `false`, or the vocabulary of labels and tags, each written as it appears, such as `"🟢 Stable"` | R12 |
| `grouping` | `none`, or `category` to group entries under the standard's categories | R8 |
| `featured` | The repositories shown first, in order, as a "start here" list | R13 |
| `order` | `category`, `latest_release` or `alphabetical`: how the scaffold orders entries. Not checked, because a hand-ordered page is often deliberate | None |
| `shared_text` | `{id, text}` passages that must appear exactly, which keeps sibling organization pages aligned | R9 |

## How the checker reads a page

An **entry** is a heading, list item or table row whose first link points at the root of one of the organization's repositories. A **recent-changes block** starts at a bold line beginning `**Recent` and ending `:**`, and holds the bullets under it. A **label** is a short segment that starts with an emoji, in a line split on ` · ` or in a table cell.

The version a page states is its first release link for a repository: the first bullet of Catalog's recent-releases block, or Compact's latest-release cell. Rule R3 requires it to name the newest release, not counting one in `skip_releases`. Showcase states versions only through release badges, which update themselves, so R3 has nothing to compare there.
