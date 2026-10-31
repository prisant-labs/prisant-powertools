#!/usr/bin/env python3
"""Measure visible body text in a quick-reference HTML file (gate G-19, v1.5.2+).

ADVISORY as of plab-guide v2.0.0:
    This gate is no longer hard. render-pdf.sh warns on a low body-char count
    but does NOT fail the build on it. The per-page ink ratio (G-8, floor 0.20,
    target 0.30) is the hard density gate. With the v2.0.0 natural-flow template
    + auto-fit renderer, the PDF may legitimately be 1 OR 2 pages, so a low char
    count no longer reliably means "under-delivered". The thresholds and exit
    codes below are retained for the advisory warning and for direct callers; the
    code logic is unchanged.

Why this gate exists:
    v1.5.0's Phase 6 contract said "target 18-20 cards / ~12-13k chars body
    content for a 2-page bundle". That's a recommendation. Compliant agents
    may hit the card count but author thin cards (~8-9k chars), producing a
    PDF that passes G-8's pixel density floor (0.20) but misses the v1.5.0
    target (0.30) and feels half-empty by comparison to the Spike H reference
    (16.6k chars, 0.385 ink ratio).

    G-19 makes the contract a hard floor. The render fails fast - before
    Chrome runs - if the produced HTML has insufficient body content. The
    agent gets specific feedback about how much to expand by.

Algorithm:
    1. Read the HTML file.
    2. Extract the <body>...</body> region (everything else is structural).
    3. Remove <script> and <style> blocks (their content is not visible body text).
    4. Strip HTML tags.
    5. Decode HTML entities.
    6. Collapse whitespace.
    7. Count characters.

Usage:
    scripts/measure-html-body-chars.py <html-path> [--threshold INT]

Defaults:
    --threshold 11000  (Spike H reference is 12,144; codex sparse case 8,837;
                        12-13k is the v1.5.0 Phase 6 target; 11k is the floor
                        with ~1k of grace below the lower target bound)

Exit codes:
    0  - body content meets or exceeds threshold (G-19 pass)
    1  - bad arguments
    2  - file not found or unreadable
    5  - body content below threshold (G-19 fail)

Calibration evidence (recorded in HISTORY.md v1.5.2):
    - codex/ai-coding-cli-trio bundle (sparse):  8,837 chars  -> FAIL
    - Original git-concepts v1.4.0 baseline:     6,671 chars  -> FAIL
    - Spike H git-concepts (canonical v1.5.0):  12,144 chars  -> PASS
    - Locked template (v1.5.0 sample):          ~5,500 chars  -> exempt
                                                                  (the template
                                                                   is a pattern
                                                                   catalog, not
                                                                   a produced
                                                                   guide)
"""
from __future__ import annotations

import argparse
import re
import sys
from html import unescape
from pathlib import Path


def measure_body_chars(html: str) -> int:
    """Return the number of visible body characters in an HTML document.

    Strips <script> and <style> blocks (their content is invisible to the
    reader), all remaining HTML tags, decodes HTML entities, and collapses
    whitespace. Counts the resulting visible characters.
    """
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    if body_match:
        body = body_match.group(1)
    else:
        body = html

    # Remove non-visible blocks
    body = re.sub(r"<script[^>]*>.*?</script>", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"<style[^>]*>.*?</style>", "", body, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML comments
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    # Strip all remaining tags
    body = re.sub(r"<[^>]+>", " ", body)
    # Decode HTML entities (&amp;, &lt;, &nbsp;, etc.)
    body = unescape(body)
    # Collapse whitespace
    body = re.sub(r"\s+", " ", body).strip()
    return len(body)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure visible body text in a quick-reference HTML file.",
    )
    parser.add_argument("html_path", help="path to the HTML file")
    parser.add_argument(
        "--threshold",
        type=int,
        default=11000,
        help="minimum visible body characters required (default: 11000)",
    )
    args = parser.parse_args()

    path = Path(args.html_path)
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        html = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: could not read {path}: {e}", file=sys.stderr)
        return 2

    chars = measure_body_chars(html)
    print(f"body chars: {chars:,}  (threshold: {args.threshold:,})")

    if chars < args.threshold:
        deficit = args.threshold - chars
        print("", file=sys.stderr)
        print(
            f"error: body content {chars:,} chars is below the floor "
            f"({args.threshold:,}); short by {deficit:,}",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print("fix candidates (in order of value):", file=sys.stderr)
        print(
            "  1. expand short cards: more rows in step-row / status-row cards, "
            "more H3 blurbs in concept cards, more anti-pattern rows, "
            "more vocabulary entries",
            file=sys.stderr,
        )
        print(
            "  2. add cards from the catalog: glossary, decision matrix, "
            "comparison table, edge-case grid, recovery cookbook, "
            "inspecting-state, anti-patterns",
            file=sys.stderr,
        )
        print(
            "  3. promote a span-3 card to span-6 (full row) if the content "
            "earns full width OR if it is a horizontal diagram",
            file=sys.stderr,
        )
        print(
            "  4. revisit research: surface caveats, gotchas, edge cases, "
            "common misconceptions, performance notes not yet captured",
            file=sys.stderr,
        )
        print(
            "  5. add a See Also / Glossary / Vocabulary card if the topic "
            "has terminology worth defining",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print(
            f"target: ~12,000-13,000 chars (Phase 6 contract); Spike H "
            f"reference is 16,585. Aim for the target, not the floor.",
            file=sys.stderr,
        )
        return 5

    return 0


if __name__ == "__main__":
    sys.exit(main())
