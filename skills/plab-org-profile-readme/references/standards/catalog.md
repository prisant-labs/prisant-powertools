# Catalog

A full catalog: a header, a legend, an index by category, then a section per project with its status, badges, summary and recent releases. It suits an organization with many projects that visitors browse by kind. Sample: `examples/standards/catalog/`.

## Sections

1. **Header.** A level-1 heading with the organization's name, an intro sentence, and any shared text. A status legend and a tag legend, as two bulleted lists, may follow; they are shared text when sibling organizations' pages must match.
2. **At a glance.** `## At a glance`, then one level-3 heading per category holding only its name, and under each a bulleted list with a blank line after every entry. An entry is `- <emoji> **[<repo>](#<anchor>)** · <status>[ · <tag>]<br><one-line description>`. The description never holds a version number.
3. **One section per category,** in the standard's order. Each starts with a `---` rule, then `## <emoji> <category>`, then one sentence that names its start-here project.
4. **One block per project** inside its category. A `---` rule above every project except the first in its category, then:
   - a heading, `### <emoji> [<repo>](https://github.com/<org>/<repo>)`;
   - an italic line, `*<status> · <tags> · <platform>*`, holding no count and no version;
   - a row of badges that update themselves, release badges with `display_name=tag`;
   - an install line, a code block when installing is a command;
   - a summary that leads with the problem the project solves, and an optional "What's inside" list;
   - a recent-changes block (below);
   - a hand-written `**Status:**` line.
5. **Footer.** A license note naming every license other than the usual one, and a back-to-top link.

## Options it uses

| Option | Default |
|---|---|
| `recent_changes` | 3 |
| `badges` | `release`, `license` |
| `status_labels` | 🟢 Stable, 🟡 Beta, 🟠 Pre-release, 🟤 Maintenance, and the tags 🚀 Start here, 🆕 New, 🧪 Experimental |
| `grouping` | `category` |
| `order` | `category` |

## Rules for its labels and blocks

- **🟢 Stable:** the newest stable release is 1.0 or later, or the project is a live service. **🟡 Beta:** released, but below 1.0, or only a prerelease. **🟠 Pre-release:** no release, so readers build from source. **🟤 Maintenance:** only when the project's own README says development has stopped.
- **🆕 New:** a project created in the last 30 days; remove it after that. **🚀 Start here:** one per category, and the skill never moves it itself; suggest a change in the pull request body instead. **🧪 Experimental:** never added or removed by the skill.
- When a label changes, change it in both the italic line and the At a glance entry.
- A released project's block is `**Recent releases:**`, one bullet per release, newest first: `- [<tag>](<release url>) (<Mon YYYY>): <one or two sentences>.` The first bullet is the newest release, unless the standard skips a newer one in `skip_releases`.
- A project with no release uses `**Recent changes (unreleased):**`, with each bullet linking one version section of its changelog.
- Leave a release that changed nothing a user would notice off the block, and record it in `skip_releases`. Never pad a block.
- Every emoji is a single Unicode code point, never one holding U+FE0F, because the invisible character ends up in the heading's anchor and breaks links. GitHub drops an emoji from a heading's anchor and keeps the space after it, so an emoji heading's anchor starts with a hyphen, such as `#-alpha-tool`.
- Leave a blank line above and below every `---`. A `---` directly under a line of text turns that text into a heading.
