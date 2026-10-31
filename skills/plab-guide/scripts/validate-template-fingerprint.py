#!/usr/bin/env python3
"""Validate that a quick-reference HTML uses the locked template (gate G-17).

The locked template is `assets/templates/quick-reference-template_v1-technical-white.html`.
Codex (and any other agent) sometimes regenerates the HTML from scratch instead of
copying and populating the template. This check fingerprints the structural and
visual contract of the locked template and fails if the produced HTML does not
carry it.

Usage:
    scripts/validate-template-fingerprint.py <quick-reference.html>

Exit codes:
    0 - HTML carries the locked template fingerprint (G-17 pass)
    1 - bad arguments
    2 - input file missing
    3 - fingerprint missing (G-17 fail)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Each fingerprint is (label, pattern, hint).
# Patterns are regexes that must match somewhere in the file.
FINGERPRINTS = [
    (
        ":root variable block with --accent",
        re.compile(r":root\s*\{[^}]*?--accent\s*:", re.DOTALL),
        "the locked template defines all theme variables in a single :root block",
    ),
    (
        "--font-body declaration",
        re.compile(r"--font-body\s*:"),
        "font stack must be controlled via the locked CSS variable, not hardcoded",
    ),
    (
        "masthead class on header",
        re.compile(r'class\s*=\s*"[^"]*\bmasthead\b'),
        "header must use the locked masthead pattern, not a bespoke <header>",
    ),
    (
        "grid container",
        re.compile(r'class\s*=\s*"[^"]*\bgrid\b'),
        "card grid must use the locked .grid class",
    ),
    (
        "card class on grid items",
        re.compile(r'class\s*=\s*"[^"]*\bcard\b'),
        "grid items must use the locked .card class (with span-N modifier)",
    ),
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

    missing = []
    for label, pattern, hint in FINGERPRINTS:
        if not pattern.search(html):
            missing.append((label, hint))

    if missing:
        print(f"error: {path} does not carry the locked template fingerprint", file=sys.stderr)
        print("", file=sys.stderr)
        print("missing markers:", file=sys.stderr)
        for label, hint in missing:
            print(f"  - {label}", file=sys.stderr)
            print(f"      {hint}", file=sys.stderr)
        print("", file=sys.stderr)
        print("fix:", file=sys.stderr)
        print("  1. cp assets/templates/quick-reference-template_v1-technical-white.html <output>.html", file=sys.stderr)
        print("  2. edit in place: replace sample cards with topic content", file=sys.stderr)
        print("  3. preserve the :root, .masthead, .grid, .card class system", file=sys.stderr)
        print("  4. re-run this script to verify", file=sys.stderr)
        return 3

    print(f"ok: {path} carries the locked template fingerprint (5/5 markers present)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
