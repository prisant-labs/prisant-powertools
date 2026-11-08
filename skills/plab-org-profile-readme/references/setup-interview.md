# The --setup interview

`--setup` establishes what the organization's standard records. This document says what to establish, not how to ask, because Claude Code and Codex ask differently. Ask in as few turns as the harness allows. When the organization already has a standard, offer each current value as the default, so a revision changes only what the maintainer names.

## What to establish

1. **The path.** One of three:
   - **Built-in:** Catalog, Compact or Showcase. Show each one's sample page from `examples/standards/<base>/README.md` and its reference from `references/standards/`, so the maintainer chooses by looking.
   - **Adopted:** the organization's current page becomes the standard. Offer this first when a page exists.
   - **Custom:** the maintainer names the sections, in order.
2. **The title.** The organization's display name, for the page's level-1 heading.
3. **Each option** of `references/standard-format.md`: recent changes and their count, badges and their kinds, status labels and their vocabulary, grouping, featured repositories, order, and any shared text.
4. **The categories**, when grouping by category: their names, in order, and which covered repositories each holds. Every covered repository that is not excluded needs a category.
5. **The exclusions**, each with a reason of at least three words, for covered repositories the page leaves out.
6. **The inclusions**, each with a reason, for public forks the page shows.

## How it ends

Write the answers to a JSON file and run `scripts/write-standard.py`. For the adopted path, show every exclusion and inclusion the script recorded, because each carries "confirm" in its reason until the maintainer confirms or corrects it. Then write the page to the standard, as step 4 of `SKILL.md` describes, and put the standard and the page on one branch.
