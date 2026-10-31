# Settings file

The owner's machine-specific values live in `.claude/plab-usage-audit.local.md` in the repository the audit runs from, as YAML frontmatter. Keep it gitignored. The scripts parse a small YAML subset: scalars, quoted strings, lists, and one level of mapping. Copy this example and edit every value.

```yaml
---
transcript_root: ~/.claude/projects
timezone: America/Los_Angeles        # IANA name; never a fixed offset
cutoff_local: "09:00"                # local time on the audit day
output_dir: audits                    # the bundle is <output_dir>/YYYY-MM-DD_claude-usage/
allow_tracked_output: false           # true only for a private repository (UA-01 D5)
ledger_path: reference/kpi-ledger.jsonl
ledger_mapping: null                  # a JSON file mapping older rows to period dates
state_path: reference/usage-audit-state.json
price_file: null                      # null uses the skill's references/pricing.json
claude_settings: ~/.claude/settings.json
change_register: config-changes.md    # rows of dated configuration changes
workflow_tolerance_usd: 1.0           # per-workflow costs may exceed the lane by this much
automated:
  entrypoints: [sdk-cli]
  dir_patterns: [bench-, tmp-]         # transcript folder fragments for test sessions
project_aliases:                       # turn transcript folder names into short labels
  "^home-owner-src-": ""
decision_sources:
  - audits/*_claude-usage/05-recommendations.md
  - OPEN.md
  - decisions/*.md
credential_files:                      # checked by key name and date only; agents never open them
  - ~/.npmrc
  - ~/.codex/config.toml
private_patterns: ["_local/", "_session-logs/"]
sweep:
  roots: [~/src]
  max_depth: 2
  exclude: ["_delete", "_temp", "*_worktrees"]
  author_pattern: "owner|noreply@anthropic"
recommendation_series:
  next: A
  skip: [D, K, O, Q, S, T]
---
```

Every path may start with `~`. A relative path resolves from the repository the audit runs from.
