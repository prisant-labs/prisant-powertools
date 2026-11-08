# Compact

A header and one table of projects. It suits a small organization, or one whose visitors want a list rather than a tour. Sample: `examples/standards/compact/`.

## Sections

1. **Header.** A level-1 heading with the organization's name, one intro sentence, and any shared text.
2. **Projects.** `## Projects`, then one table:

   ```
   | Project | Description | Status | Latest release |
   |---|---|---|---|
   | [<repo>](https://github.com/<org>/<repo>) | <one line> | <status> | [<tag>](<release url>) |
   ```

   A project with no release says "None yet" in the last column.

## Options it uses

| Option | Default |
|---|---|
| `recent_changes` | `false` |
| `badges` | `false` |
| `status_labels` | 🟢 Stable, 🟡 Beta, 🟠 Pre-release, 🟤 Maintenance |
| `grouping` | `none` |
| `order` | `alphabetical` |

The latest-release cell is the version the page states, so rule R3 checks it against the newest release. The status labels follow Catalog's rules.
