# Settings file

The owner's machine-specific values live in `.claude/plab-project-pulse.local.md` in the repository the pulse runs from, as YAML frontmatter. Keep it gitignored. The scripts parse a small YAML subset: scalars, quoted strings, lists, and one level of mapping. Copy this example and edit every value.

```yaml
---
roots:                        # folders to search; a root may itself be a repository
  - ~/src
max_depth: 2                  # stop at a repository; never deeper than this
extra_repos: []               # repositories outside the roots
exclude: ["_delete", "_temp", "*_worktrees"]
author_pattern: "owner|noreply@anthropic"
timezone: America/Los_Angeles # IANA name; never a fixed offset
output_dir: pulse             # each run writes <output_dir>/YYYY-MM-DD/
state_path: pulse/state.json
gh:
  enabled: true
  timeout_seconds: 20
heavy_rule:
  top_by_commits: 6
unprotected_globs: ["_working/**", "_history/**"]
credential_files: [~/.npmrc, ~/.codex/config.toml]
usage_projects_json: null     # optional: plab-usage-audit's projects.json, for spend per repository
---
```

Every path may start with `~`. A relative path resolves from the repository the pulse runs from. The output folder must be outside any repository or ignored by it.
