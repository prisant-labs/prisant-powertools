# Shipped - 2026-10-19 to 2026-10-25

This section reports only what the git sweep found: tags and commits. Whether a shipped change actually works in the live repository is `plab-project-pulse`'s question, not this one.

## Tags

`alpha-app` cut `v2.3.0` on 2026-10-22, the first tag since the release-plan build this week's spend-by-project section covers. `beta-lib` cut no tag this week; its last tag, `v0.9.4`, was 2026-09-30.

## Commits

`alpha-app` carries 11 commits this week across two branches, merged to `main` by pull request on 2026-10-22 and 2026-10-24. `beta-lib` carries 3 commits, all on `main` directly, which is allowed there because that repository has no branch protection yet.

## What the sweep could not see

Neither repository's CI status is read here; the sweep records tags and commits only. A later audit should add CI outcome once a cheap, reliable source for it exists, which `data/README.md`'s "Not measured" section already flags as a known gap rather than a silent omission.
