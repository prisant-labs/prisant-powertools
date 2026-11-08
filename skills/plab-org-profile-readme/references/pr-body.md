# The pull request body

The body tells the maintainer what changed and why, so they can review it without rerunning anything. The checker's R14 requires the headings below. A section with nothing in it says "None."

```markdown
<one sentence: what this pull request does for the page>

## From the repositories

- New projects: each one added, with its category, listed first.
- <repository>: <what changed>, with the fact behind it, such as the release it now names.
- Releases skipped: each release added to `skip_releases`, with its reason.

## From your instructions

- <what changed>, and the instruction it carries out.

## Noticed but not changed

- Anything stale or odd left for the maintainer, and every NOTE from the checker.
```

Include "From your instructions" only when the run carried instructions; the checker requires it then. Name no private repository anywhere in the body.
