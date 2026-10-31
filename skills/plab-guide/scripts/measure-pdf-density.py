#!/usr/bin/env python3
"""Measure per-page ink density of a PDF (gate G-8 floor check).

Rasterizes each PDF page to a grayscale PPM via `pdftoppm` (poppler-utils, already
required for the page-count check), then counts pixels darker than a near-white
threshold to compute "ink ratio" per page.

Why pixel density instead of word count:
    Word count systematically penalizes visual content. A page with a Mermaid
    diagram filling the bottom half has many visible pixels but few words; the
    word-count proxy would call it "sparse" while ink density correctly counts
    the diagram pixels. Same applies to code blocks, tables, ASCII art, and
    SVG inserts.

Usage:
    scripts/measure-pdf-density.py <pdf-path> [--threshold FLOAT] [--dpi INT]

Defaults:
    --threshold 0.20   (each page must have >= 20% ink coverage; v1.5.0 recommended target 0.30;
                        Spike H reference benchmark hit 0.385 / 0.348 per page)
    --dpi 50           (rasterization DPI; trades accuracy vs speed)
    --ink-cutoff 240   (pixel value 0-255; values below this count as "ink")

Exit codes:
    0  - all pages meet the density floor (G-8 pass)
    1  - bad arguments
    2  - pdftoppm not found / PDF unreadable
    4  - one or more pages below the density floor (G-8 fail)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_ppm_header(data: bytes) -> tuple[int, int, int, int]:
    """Parse P5 (binary grayscale) PPM header. Returns (width, height, maxval, data_offset)."""
    pos = 0

    def read_token() -> tuple[bytes, int]:
        nonlocal pos
        # Skip whitespace and comments
        while pos < len(data):
            c = data[pos:pos + 1]
            if c in b" \t\n\r":
                pos += 1
            elif c == b"#":
                # Skip comment to end of line
                while pos < len(data) and data[pos:pos + 1] != b"\n":
                    pos += 1
            else:
                break
        # Read token until whitespace
        start = pos
        while pos < len(data) and data[pos:pos + 1] not in b" \t\n\r":
            pos += 1
        return data[start:pos], pos

    magic, _ = read_token()
    if magic != b"P5":
        raise ValueError(f"expected P5 (binary grayscale PPM), got {magic!r}")
    width_b, _ = read_token()
    height_b, _ = read_token()
    maxval_b, _ = read_token()
    # Single whitespace byte after maxval, then raw pixel data
    if pos < len(data) and data[pos:pos + 1] in b" \t\n\r":
        pos += 1
    return int(width_b), int(height_b), int(maxval_b), pos


def measure_ink_ratio(ppm_path: Path, ink_cutoff: int) -> tuple[float, int, int]:
    """Return (ink_ratio, inked_pixels, total_pixels) for a single PPM file."""
    data = ppm_path.read_bytes()
    width, height, maxval, offset = parse_ppm_header(data)
    if maxval > 255:
        raise ValueError(f"unsupported PPM maxval {maxval} (16-bit not handled)")
    pixels = data[offset:offset + width * height]
    if len(pixels) < width * height:
        raise ValueError(f"truncated PPM: expected {width * height} bytes, got {len(pixels)}")
    inked = sum(1 for b in pixels if b < ink_cutoff)
    return inked / (width * height), inked, width * height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pdf_path", type=Path, help="Path to the PDF to measure")
    parser.add_argument("--threshold", type=float, default=0.20, help="Minimum ink ratio per page (default 0.20; recommended target 0.25)")
    parser.add_argument("--dpi", type=int, default=50, help="Rasterization DPI (default 50)")
    parser.add_argument("--ink-cutoff", type=int, default=240, help="Pixel value below which counts as ink (0-255, default 240)")
    parser.add_argument("--quiet", action="store_true", help="Only print on failure")
    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"error: PDF not found: {args.pdf_path}", file=sys.stderr)
        return 1

    if not shutil.which("pdftoppm"):
        print("error: pdftoppm not found (install poppler-utils to enable G-8 density check)", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        out_prefix = tmp_dir / "page"
        # pdftoppm with -gray emits P5 (binary grayscale) PPM by default
        result = subprocess.run(
            ["pdftoppm", "-gray", "-r", str(args.dpi), str(args.pdf_path), str(out_prefix)],
            capture_output=True,
        )
        if result.returncode != 0:
            print(f"error: pdftoppm failed: {result.stderr.decode('utf-8', errors='replace')}", file=sys.stderr)
            return 2

        ppms = sorted(tmp_dir.glob("page-*.ppm")) + sorted(tmp_dir.glob("page-*.pgm"))
        if not ppms:
            print(f"error: pdftoppm produced no output files in {tmp_dir}", file=sys.stderr)
            return 2

        results = []
        for ppm in ppms:
            ratio, inked, total = measure_ink_ratio(ppm, args.ink_cutoff)
            page_num = int(ppm.stem.split("-")[-1])
            results.append((page_num, ratio, inked, total))

    failures = [r for r in results if r[1] < args.threshold]
    if not args.quiet or failures:
        for page_num, ratio, inked, total in results:
            status = "PASS" if ratio >= args.threshold else "FAIL"
            print(f"page {page_num}: ink_ratio={ratio:.3f} ({inked:,}/{total:,} pixels)  {status}")

    if failures:
        print("", file=sys.stderr)
        print(f"error: {len(failures)} page(s) below density floor ({args.threshold:.0%})", file=sys.stderr)
        print("", file=sys.stderr)
        print("fix candidates (in order of value):", file=sys.stderr)
        print("  1. add cards from the catalog (glossary, decision matrix, comparison table, edge-case grid)", file=sys.stderr)
        print("  2. expand short cards (more rows, more concept blurbs, more anti-patterns)", file=sys.stderr)
        print("  3. add a diagram if the topic has structural relationships worth showing", file=sys.stderr)
        print("  4. promote a span-3 card to span-6 if its content earns full width", file=sys.stderr)
        print("  5. surface caveats / gotchas / edge cases not yet captured", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())
