# Showcase

A header, a few featured projects with longer descriptions, and a short list of the rest. It suits an organization with two or three flagship projects. Sample: `examples/standards/showcase/`.

## Sections

1. **Header.** A level-1 heading with the organization's name, one intro sentence, and any shared text.
2. **Featured.** `## Featured`, then one block per featured repository, in the standard's `featured` order: a level-3 heading linking the repository, an italic status line, a release badge, and a paragraph that leads with the problem it solves.
3. **More projects.** `## More projects`, then one bullet per remaining repository: `- [<repo>](https://github.com/<org>/<repo>): <one line>`.

## Options it uses

| Option | Default |
|---|---|
| `recent_changes` | `false` |
| `badges` | `release` |
| `status_labels` | 🟢 Stable, 🟡 Beta, 🟠 Pre-release, 🟤 Maintenance |
| `grouping` | `none` |
| `featured` | Set in `--setup`; Showcase needs at least one |
| `order` | `latest_release`, for the projects after the featured ones |

Rule R13 checks that the featured repositories are the page's first entries, in order. Versions appear only through release badges, which update themselves.
