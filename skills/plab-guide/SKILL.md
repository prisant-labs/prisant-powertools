---
name: plab-guide
description: Generate a paired guide bundle (standard MD + ADHD MD + quick-reference HTML + 1-2 page PDF) for any topic. Use when the user provides a GitHub URL, a tool name, or a concept and wants a structured explanatory document plus a printable operator card. Triggers on "create a guide", "build a cheat sheet", "explain X with a quick reference", "/plab-guide".
argument-hint: "<topic-or-repo-url> [--type repo-url|tool|concept] [--out <dir>] [--force]"
license: MIT
metadata:
  version: "2.2.3"
  updated: 2026-10-30
---

# plab-guide

Generate a four-artifact guide bundle for a topic, with strict structural contracts and zero LLM tokens spent on PDF rendering.

## When to use this skill

Use when the user invokes `/plab-guide <topic>` or asks for a "guide", "cheat sheet", "explanatory + quick reference" pair, or "summary plus operator card" for a topic.

Three input types:
- `repo-url` - a GitHub URL like `https://github.com/owner/repo`
- `tool` - a CLI tool or library name like `jq` or `pandas`
- `concept` - an idea, methodology, or pattern like `eventual consistency` or `CAP theorem`

Detection is automatic; the skill asks for confirmation if the classification is ambiguous unless `--type` is passed.

## What this skill produces

Four artifacts in a dated output directory (default `_output/plab-guide/<slug>-<YYYY-MM-DD>/`, relative to the current working directory; user can override by passing `output to <path>` or similar in the invocation):

| File | Description |
|------|-------------|
| `<slug>_guide-standard.md` | 12-section explanatory guide (technical reference style) |
| `<slug>_guide-adhd.md` | Same content with ADHD-optimized scaffolding (numbered headings, [TL;DR]/[BOTTOM LINE], emoji callouts, clickable QUICK NAV) |
| `<slug>_quick-reference.html` | 1-2 page operator card (HTML+CSS, 6-column grid, semantic backgrounds; natural-flow layout, auto-fit to 1 or 2 dense pages) |
| `<slug>_quick-reference.pdf` | Rendered locally via headless Chrome / Chromium / Edge |

Plus `MANIFEST.yaml` (machine-readable manifest) and `_work/` (intermediate artifacts: intake, research, outline). Diagrammed bundles (built with `--diagram`) also include one or more `<slug>_diagram-N.svg` files - auxiliary artifacts that the quick-reference HTML references via `<img>` (see Phase 6.5).

## Pipeline (8 phases + Phase 6.5)

1. **Intake & Classify** - detect input type, derive slug, determine output directory, run `scripts/check-toolchain.sh` to surface missing-browser / missing-mmdc warnings early.
2. **Research & Cite** - WebFetch (repo-url) or WebSearch (tool/concept). Build `_work/research.md` with credibility-classified sources. Read `references/research-and-citation.md`.
3. **Outline & IA** - build the 12-section outline + the quick-ref card plan in `_work/outline.yaml`. Read `references/progressive-disclosure.md` and `references/faq-generation.md`.
4. **Standard MD Fill** - copy `assets/templates/guide-template_standard.md`, fill. Read `references/guide-structure-standard.md` and `references/voice-and-style.md` (em-dash discipline lives there; gate G-11 verifies via grep, not via auto-rewrite). Do not add Mermaid diagrams unless `--diagram` was explicitly requested; when requested, authoring guidance is at `../../references/diagrams.md`.
5. **ADHD MD Fill (derive from standard; do not regenerate)** - mechanically transform the Phase-4 standard MD (`<slug>_guide-standard.md`) into the ADHD variant: keep the prose verbatim and layer on the scaffolding (numbered headings with `.` separators, `[TL;DR]`/`[BOTTOM LINE]` callouts, `[QUICK NAV]` for sections with >=4 sub-sections, tagged callouts, confidence emojis) per the section-transformation table in `references/guide-structure-adhd.md`. The ADHD variant carries the SAME content as the standard, so content parity is guaranteed and Phase 5 costs ~30-50% less than regenerating from scratch (the standard MD has already passed gate G-1 by this point). `assets/templates/guide-template_adhd.md` is the locked scaffolding baseline. Use the `[DIAGRAM]` marker only when `--diagram` was explicitly requested.
6. **Quick-Reference HTML Fill** - **first action MUST be** `cp assets/templates/quick-reference-template_v1-technical-white.html <output>.html` so the locked template structure exists on disk before any LLM editing. Then edit in place: replace sample cards with topic-specific cards using ONLY the locked classes (`.card`, `.span-N`, `.card.ref`, `.card.summary`, `.card.diagram`, `.card.diagram.span-6`), the locked masthead pattern, and the locked `:root` CSS variables. **Author to density (v2.0.0 natural-flow):** author enough cards to fill 1-2 pages at the v1.5.0 ink-ratio target of >= 0.30 per page; the renderer auto-fits any overflow (see Phase 7). Gate G-19 is advisory (v2.0.0): it warns before Chrome runs if the body content looks thin, but the per-page ink ratio (G-8) is the hard density gate. Do not add diagram cards (`.card.diagram`, `.card.diagram.span-6`) unless `--diagram` was explicitly requested. When requested: portrait diagrams use `.card.diagram` (max-height 1.8in); landscape diagrams use `.card.diagram.span-6` (max-height 2.2in); diagram body is a fenced ` ```mermaid ` block (Phase 6.5 will render it to an external SVG and swap in an `<img>` reference). Do NOT rewrite the CSS or invent new class names. Read `references/quick-ref-html-patterns.md`. Gate G-17 verifies the locked template fingerprint survives.
6.5. **Mermaid Pre-Render** *(skip entirely unless `--diagram` was requested)* - run `python ../../lib/render-mermaid.py <output>.html` to find Mermaid source blocks (fenced ` ```mermaid `, `<pre><code class="language-mermaid">`, or `<div class="mermaid">`) and render each one with `mmdc` to an external `<slug>_diagram-N.svg` file written next to the HTML, then replace the source block with an `<img src="<slug>_diagram-N.svg">` reference. Atomic in-place edit. Keeping the SVG out of line keeps the HTML small (~30KB vs ~350KB if the SVG were inlined), so the Phase 7 fit loop edits a light file. Degrades gracefully if `mmdc` is missing (warns, exits 0); the bundle then fails Gate G-18. **Zero LLM tokens.**
7. **Local PDF Render** - call `scripts/render-pdf.sh <input.html> <output.pdf>`. **Zero LLM tokens.** Auto-fits to 1-2 pages and validates per-page ink density (gate G-8): renders at `--fit-scale` 1.00 and, if the PDF overflows 2 pages, steps the scale down (1.00 -> 0.95 -> 0.90 -> 0.85, into a throwaway copy) until it fits 2 pages; fails (exit 3) only if still overflowing at 0.85. Headless Chrome embeds the external SVG natively in the print pipeline, so diagrams ride through without further work.
8. **Bundle & Manifest** - write `MANIFEST.yaml`, validate with `scripts/validate-manifest.py`. Run `scripts/validate-no-mermaid-fences.py <output>.html` (gate G-18) to confirm Phase 6.5 left no surviving Mermaid source blocks.

## Required reading (before any action)

These four references encode the cross-cutting rules and must be read before drafting any content:

- `references/voice-and-style.md` - DO/DON'T, em-dash ban, paragraph length, citation patterns
- `references/research-and-citation.md` - source classes A/B/C, citation markers, manifest format
- `references/progressive-disclosure.md` - the 4 layers (Surface/Structural/Mechanical/Expert)
- `references/faq-generation.md` - category derivation, banned shapes, quality rubric

## Topic-specific reading

Read during the matching phase:

- Phase 4 (Standard MD): `references/guide-structure-standard.md`
- Phase 5 (ADHD MD): `references/guide-structure-adhd.md`
- Phase 6 (HTML): `references/quick-ref-html-patterns.md`; for visual style edits, `references/quick-ref-theme.md`
- Phase 6.5 (Mermaid): `../../references/diagrams.md` (when to use a diagram, type selection, syntax validity, quality checklist)
- Phase 7 (PDF): `references/pdf-toolchain.md`

## Locked templates

Three templates in `assets/templates/`. **Treat as locked**; any change is a breaking change to the skill's output and triggers a version bump.

| Template | Purpose |
|----------|---------|
| `guide-template_standard.md` | Skeleton + inline guidance for the 12-section standard MD |
| `guide-template_adhd.md` | Skeleton + inline guidance for the ADHD-scaffolded variant |
| `quick-reference-template_v1-technical-white.html` | HTML+CSS template with the card pattern catalog |

## Scripts

| Script | Purpose | When |
|--------|---------|------|
| `scripts/check-toolchain.sh` | Detect Chrome / Chromium / Edge / pdfinfo / mmdc; print install hints | Phase 1 |
| `scripts/render-pdf.sh` | HTML to PDF via headless browser; auto-fits overflow via `--fit-scale` and enforces G-8 (1-2 page count + per-page ink ratio) | Phase 7 |
| `scripts/measure-pdf-density.py` | Pixel-based ink-ratio measurement per page (called by render-pdf.sh) | Phase 7 (G-8 floor) |
| `scripts/measure-html-body-chars.py` | Visible-body-char count check (called by render-pdf.sh before Chrome runs); advisory as of v2.0.0, warns only | Phase 7 (G-19 advisory) |
| `scripts/validate-template-fingerprint.py` | Verify quick-ref HTML uses the locked template (gate G-17) | Phase 6 (after fill) |
| `scripts/validate-no-mermaid-fences.py` | Verify Phase 6.5 left no surviving Mermaid source blocks (gate G-18) | Phase 8 (post-render gate) |
| `scripts/validate-manifest.py` | Validate MANIFEST.yaml against schema | Phase 8 |
| `../../lib/render-mermaid.py` | Plugin utility: render Mermaid source blocks via `mmdc` to external `<slug>_diagram-N.svg` files and swap in `<img>` references | Phase 6.5 |

All scripts are local-only; none spend LLM tokens.

## Quality gates (19 total)

The skill runs gates G-1 through G-19 before MANIFEST write. Critical-gate failure blocks output.

| Gate | Check |
|------|-------|
| G-1 | Standard guide has every required H2 section in the required order |
| G-2 | ADHD guide has standard structure plus ADHD scaffolding (numbered, [TL;DR], [BOTTOM LINE], emoji callouts, clickable QUICK NAV) |
| G-3 | FAQ has >=3 categories and >=8 Q/A pairs in both variants |
| G-4 | Sources section lists every `[S<n>]` cited in body |
| G-7 | Quick-ref HTML contains no banned content (no install walkthroughs, no "what is X" entries, no marketing prose) |
| G-8 | PDF renders at 1 or 2 pages (auto-fit; never 3+) AND each page ink ratio >= 0.20 (target >= 0.30) (pixel-based density via `pdftoppm`; v1.5.0 recommended target >= 0.30 for "dense cheat sheet" feel; Spike H reference bundle hit 0.385 / 0.348) |
| G-11 | Zero em-dashes (U+2014) or en-dashes (U+2013) in any artifact (verified by grep; written-discipline rule, no auto-rewrite) |
| G-12 | ADHD variant uses `.` (not `/`) as numbering separator |
| G-13 | ADHD variant has horizontal rules ONLY before `##` headings |
| G-14 | ADHD QUICK NAV blocks are clickable markdown links |
| G-15 | No 2-row tables in any artifact |
| G-16 | All tables have column headers |
| G-17 | Quick-ref HTML uses the locked template (presence of `:root` with `--accent` and `--font-body` declarations, plus `class="masthead"`, `class="grid"`, and `class="card`) |
| G-18 | Quick-ref HTML has no surviving Mermaid source blocks after Phase 6.5 (verified by `validate-no-mermaid-fences.py`; catches the case where `mmdc` was missing or rendering silently failed) |
| G-19 | Advisory (v2.0.0): warns if body content looks thin before Chrome runs, but does not fail the build; the per-page ink ratio (G-8) is the hard density gate; locked template exempt. |

(Other gates are warnings: G-5 exec-summary length, G-6 layer length budgets, G-9 source count, G-10 directory collision.)

## Failure modes

| Failure | Behavior |
|---------|----------|
| Browser writes no PDF | `scripts/render-pdf.sh` exits 5 whatever the browser's own exit code was, because the file is the proof of a render. Phase 7 fails; the other three artifacts are still produced. |
| No browser found | Phase 7 emits an install hint; the other three artifacts are still produced. |
| Content overflows 2 pages | Phase 7 auto-fits: it steps `--fit-scale` down (1.00 -> 0.95 -> 0.90 -> 0.85, into a throwaway copy) until the PDF fits 2 pages. It fails only if the content still overflows at fit-scale 0.85 (exit 3), with a fix list (trim longest card, drop low-value card). Stepping the scale down also raises ink density, so a fitted overflow tends to read denser. |
| Single dense page | A small, dense topic that legitimately fits 1 page is accepted as of v2.0.0; page 2 is no longer forced. G-19 may warn that body content looks thin, but the build still passes as long as the page clears the G-8 ink floor. |
| Page below ink-ratio 0.20 | Phase 7 fails G-8 (exit 4); fix list (add cards from the catalog, expand short cards, rebalance, surface gotchas). Aim for the 0.30 target / Spike H-style density (~0.35 ink ratio per page). |
| Fewer than 3 sources | Mark `confidence: medium` (1-2 sources) or `low-confidence draft` (0 sources, model knowledge only). |
| Em-dash found in an artifact | Gate G-11 fails the run; rewrite the sentence before unblocking. There is no auto-rewrite. |
| `mmdc` missing during Phase 6.5 | `lib/render-mermaid.py` warns and exits 0; surviving Mermaid blocks then fail Gate G-18 with the install hint. Either install mmdc or remove the diagram cards. |
| Mermaid block fails to render (syntax error) | `lib/render-mermaid.py` prints the mmdc stderr for that block and continues; Gate G-18 then fails on the surviving block. Fix the syntax (paste into mermaid.live to debug) and re-run Phase 6.5. |
| Existing output directory | Append `-<n>` suffix; never overwrite without `--force`. |
| Network unavailable | Build all artifacts from model knowledge with prominent unverified markers and a confidence banner. |

## Topic-type adapters

Each phase adapts slightly per input type. Inline guidance in the templates and the structure references covers the differences.

| Layer / section | repo-url | tool | concept |
|-----------------|----------|------|---------|
| At a Glance rows | Repo URL, license, maintainer | Package + version + install | Origin (paper/spec) + adjacent concepts |
| Getting Started > First Step | `pip install <pkg>` etc. | `<tool> --help` | Mental model paragraph instead of command |
| Surface Layer | What + audience + license | What + category | What + origin + adjacent concepts |
| Structural Layer | Directory layout + components | Subsystems + flags | Sub-concepts + relationships |
| Mechanical Layer | How the runtime works | Invocation lifecycle | How the concept applies in practice |
| Expert Layer | Edge cases + maintainer wisdom | Performance gotchas + idioms | Subtle distinctions + common misapplications |

## Defaults

- Output directory: `_output/plab-guide/<slug>-<YYYY-MM-DD>/` (relative to CWD; override by passing an explicit destination path in the invocation)
- Confidence: derived from source count and class (high / medium / low-confidence draft)
- Variant: produces both `standard` and `adhd` MDs unless `--variant` specifies otherwise
- PDF: produces unless `--no-pdf` or no browser is found
- Diagram: off by default; opt in with `--diagram` in the invocation or by saying "with a diagram" / "include a diagram" in the request. Detection of explicit diagram requests happens in Phase 1.
- Intermediate artifacts: kept in `_work/` unless `--clean` is passed

## Acceptance

The skill is complete for a topic when:
1. All artifacts in the output directory exist and pass their gates.
2. `MANIFEST.yaml` validates via `scripts/validate-manifest.py`.
3. `<slug>_quick-reference.pdf` is 1 or 2 dense pages (auto-fit; never 3+).
4. `_work/research.md` lists real, reachable URLs (no fabrication).
