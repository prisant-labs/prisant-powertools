# Plugin-Level Shared Scripts

Scripts shared across multiple skills in this plugin. Skills in `skills/plab-*/` invoke these via relative path (e.g., `../../lib/render-mermaid.py`).

This folder is a **plugin utility**, not a skill.

## Contents

| File | Purpose | Consumers | Since |
|------|---------|-----------|-------|
| `session-logs.py` | The session-log rules both session skills share: where the store is, including the main checkout's store from a linked worktree; which logs exist; which logs another session wrote while this one ran; which log a wrap carries Waiting on You items from; and which logs continue offers. Stdlib only, reads and never writes, loaded by file path through `importlib`. Its fixture suite is `test-session-logs.py` beside it | `plab-wrap-session`, `plab-continue-session` | plab-wrap-session 1.10.0 (W-07) |
| `render-mermaid.py` | Find Mermaid source blocks in HTML, render via `mmdc` to external `<slug>_diagram-N.svg` files referenced by `<img>` (in-place atomic write; external SVG as of plab-guide 2.1.0, was inline through 2.0.0); graceful degrade when `mmdc` is missing | `plab-guide` | plab-guide |

## Distinction from `scripts/`

- **`lib/`** holds scripts that **skills consume** during their pipelines (skill-time utilities).
- **`scripts/`** at the repo root holds **CI / validation** scripts (build-time / commit-time utilities). These are invoked by CI, not by skills.

If a script is invoked by a skill at runtime, it goes in `lib/`. If a script validates the repo or runs in CI, it goes in `scripts/`.

## When to add a file here

Add a shared script when:

- 2 or more skills would invoke the same logic
- The logic is deterministic build/render work (no LLM tokens)
- The logic doesn't fit naturally inside a single skill's `scripts/` because multiple skills need it

If only one skill consumes a script, keep it under that skill's `scripts/`.

## Toolchain dependencies

Some `lib/` scripts shell out to external CLIs. Document the dependency in the table above and gracefully degrade (warn, do not crash) when the tool is missing. The consuming skill is responsible for surfacing the install hint via its own toolchain check.

| Script | Required tool | Install |
|--------|---------------|---------|
| `render-mermaid.py` | `mmdc` (Mermaid CLI) | `npm install -g @mermaid-js/mermaid-cli` |
| `session-logs.py` | `git`, to find the main checkout from a worktree; without it the store is the checkout's own, and the result says so | ships with git |
