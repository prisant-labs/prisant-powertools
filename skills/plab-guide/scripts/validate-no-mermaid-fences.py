#!/usr/bin/env python3
"""Validate that no unrendered Mermaid source blocks remain in the HTML (gate G-18).

Phase 6.5 calls `lib/render-mermaid.py` to replace Mermaid source blocks with
inline SVG. If `mmdc` is missing or fails, that script degrades gracefully
(warns and exits 0) rather than crashing. This gate enforces the contract
on the resulting HTML: any surviving Mermaid block means the bundle was
authored with diagrams but the toolchain did not render them, which would
ship to PDF as raw source text.

Three block shapes are detected, matching `lib/render-mermaid.py`:

    1. ```mermaid ... ``` markdown fenced blocks
    2. <pre><code class="language-mermaid">...</code></pre>
    3. <div class="mermaid">...</div>

Usage:
    scripts/validate-no-mermaid-fences.py <quick-reference.html>

Exit codes:
    0 - no surviving Mermaid blocks (G-18 pass)
    1 - bad arguments
    2 - input file missing
    3 - one or more Mermaid blocks remain unrendered (G-18 fail)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS = [
    ("markdown fenced ```mermaid block", re.compile(r"```mermaid\s", re.IGNORECASE)),
    (
        '<pre><code class="language-mermaid">',
        re.compile(r'<pre>\s*<code\s+class="language-mermaid"', re.IGNORECASE | re.DOTALL),
    ),
    ('<div class="mermaid">', re.compile(r'<div\s+class="mermaid"', re.IGNORECASE)),
]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <quick-reference.html>", file=sys.stderr)
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    html = path.read_text(encoding="utf-8")

    findings = []
    for label, pattern in PATTERNS:
        matches = pattern.findall(html)
        if matches:
            findings.append((label, len(matches)))

    if findings:
        total = sum(n for _, n in findings)
        print(
            f"error: {path} has {total} unrendered Mermaid block(s) (G-18 fail)",
            file=sys.stderr,
        )
        print("", file=sys.stderr)
        print("surviving block shapes:", file=sys.stderr)
        for label, count in findings:
            print(f"  - {count}x {label}", file=sys.stderr)
        print("", file=sys.stderr)
        print("fix:", file=sys.stderr)
        print("  1. confirm mmdc is installed: npm install -g @mermaid-js/mermaid-cli", file=sys.stderr)
        print("  2. re-run Phase 6.5: python lib/render-mermaid.py <html-path>", file=sys.stderr)
        print("  3. if a block fails to render, paste it into mermaid.live to debug syntax", file=sys.stderr)
        print("  4. re-run this gate to verify", file=sys.stderr)
        return 3

    print(f"ok: {path} has no unrendered Mermaid blocks (G-18 pass)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
