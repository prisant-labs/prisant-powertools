#!/usr/bin/env bash
# render-pdf.sh (plab-guide v2.0.0)
# Render <input.html> -> <output.pdf> via local headless Chrome / Chromium / Edge.
# No LLM tokens used.
#
# v2.0.0 changes (natural-flow template + auto-fit):
#   - The PDF may be 1 OR 2 pages. A dense small topic legitimately fits 1 page;
#     page 2 is no longer forced to exist.
#   - Auto-fit: if content would overflow to 3+ pages, the renderer steps the
#     template's --fit-scale down (1.00 -> 0.85) until it fits within 2 pages,
#     rendering into a throwaway copy so the authored HTML is never mutated.
#   - The per-page ink-density floor (G-8) is the real density gate and applies
#     to whatever pages exist (1 or 2).
#   - The body-char count (G-19) is advisory in v2.0.0 (a warning, not a failure),
#     because a dense 1-page card legitimately has fewer characters.
#
# Usage:
#   scripts/render-pdf.sh <input.html> [output.pdf]
#
# Exit codes:
#   0 - success (1 or 2 pages, density floor met)
#   1 - bad arguments / input missing
#   2 - no Chrome / Chromium / Edge binary found
#   3 - content overflows 2 pages even at the minimum fit-scale (genuinely too much)
#   4 - one or more pages below the ink-density floor (G-8)
#   5 - the browser produced no PDF at the output path
#
# Page-count + density checks require pdfinfo + pdftoppm (poppler-utils) and Python 3.

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <input.html> [output.pdf]" >&2
  exit 1
fi

INPUT="$1"
OUTPUT="${2:-${INPUT%.html}.pdf}"

if [[ ! -f "$INPUT" ]]; then
  echo "error: input file not found: $INPUT" >&2
  exit 1
fi

detect_browser() {
  local candidates=(
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    # Linux (PATH)
    "google-chrome"
    "google-chrome-stable"
    "chromium"
    "chromium-browser"
    "microsoft-edge"
    "microsoft-edge-stable"
    # Windows (Git Bash / WSL absolute paths)
    "/c/Program Files/Google/Chrome/Application/chrome.exe"
    "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
  )
  local c
  for c in "${candidates[@]}"; do
    if [[ -x "$c" ]]; then
      echo "$c"
      return 0
    fi
    if command -v "$c" >/dev/null 2>&1; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

BROWSER="$(detect_browser || true)"
if [[ -z "$BROWSER" ]]; then
  echo "error: no Chrome / Chromium / Edge binary found" >&2
  echo "install one of:" >&2
  echo "  - Google Chrome:    https://www.google.com/chrome/" >&2
  echo "  - Chromium:         your package manager (apt/brew/choco)" >&2
  echo "  - Microsoft Edge:   https://www.microsoft.com/edge" >&2
  exit 2
fi

# Cross-platform path helpers.
to_file_url() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      local abs; abs="$(cygpath -w "$(realpath "$1")")"; echo "file:///${abs//\\//}" ;;
    *)
      echo "file://$(realpath "$1")" ;;
  esac
}
to_out_arg() {
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*) cygpath -w "$(realpath -m "$1")" ;;
    *) realpath -m "$1" ;;
  esac
}

echo "browser: $BROWSER"
echo "input:   $(to_file_url "$INPUT")"
echo "output:  $(to_out_arg "$OUTPUT")"

# G-19 (v2.0.0: advisory). Warn if body content looks genuinely thin, but never
# fail: a dense 1-page card legitimately has fewer characters than a 2-page one.
# The ink-density floor (G-8) below is the real density gate.
# Skip for the locked template (its sample content is a pattern catalog).
if [[ "$INPUT" != *"quick-reference-template_v1-technical-white.html" ]]; then
  if ! python3 "$(dirname "$0")/measure-html-body-chars.py" "$INPUT" --threshold 6000 >/dev/null 2>&1; then
    echo "note: body content is on the thin side (G-19 advisory). Fine if the result is a dense 1-page card; otherwise add cards from the catalog." >&2
  fi
fi

OUTPUT_ABS="$(to_out_arg "$OUTPUT")"

# The file, not the browser's exit code, is the proof of a render. A missing, empty
# or non-PDF file exits 5, whatever the browser returned. A non-zero exit that still
# wrote a PDF is reported and not treated as a failure.
require_pdf() {
  local rc="$1"
  if [[ ! -s "$OUTPUT" || "$(head -c 5 "$OUTPUT")" != "%PDF-" ]]; then
    echo "error: the browser exited $rc and produced no PDF at $OUTPUT_ABS" >&2
    exit 5
  fi
  if [[ "$rc" -ne 0 ]]; then
    echo "note: the browser exited $rc but wrote a PDF; continuing" >&2
  fi
}

# Render the input at a given --fit-scale into $OUTPUT. For scale 1.00 the authored
# HTML is rendered directly; for any smaller scale a throwaway copy is made with a
# :root override injected before </head> so the authored file is never mutated.
# Any earlier PDF at the output path is removed first, so a stale file cannot pass.
render_scale() {
  local scale="$1" src="$INPUT" tmp="" rc=0
  if [[ "$scale" != "1.00" ]]; then
    tmp="$(mktemp).html"
    awk -v s="$scale" '/<\/head>/{print "<style>:root{--fit-scale:" s ";}</style>"} {print}' "$INPUT" > "$tmp"
    src="$tmp"
  fi
  rm -f "$OUTPUT"
  "$BROWSER" \
    --headless=new \
    --disable-gpu \
    --no-pdf-header-footer \
    "--print-to-pdf=$(to_out_arg "$OUTPUT")" \
    "$(to_file_url "$src")" >/dev/null 2>&1 || rc=$?
  if [[ -n "$tmp" ]]; then rm -f "$tmp"; fi
  require_pdf "$rc"
}

if command -v pdfinfo >/dev/null 2>&1; then
  USED_SCALE=""
  PAGES=""
  # Auto-fit: try decreasing scales until the PDF fits within 2 pages.
  for scale in 1.00 0.95 0.90 0.85; do
    render_scale "$scale"
    PAGES="$(pdfinfo "$OUTPUT_ABS" 2>/dev/null | awk '/^Pages:/ {print $2}')"
    echo "render @ fit-scale $scale -> ${PAGES:-?} page(s)"
    if [[ "${PAGES:-9}" -le 2 && "${PAGES:-0}" -ge 1 ]]; then
      USED_SCALE="$scale"
      break
    fi
  done
  if [[ -z "$USED_SCALE" ]]; then
    echo "" >&2
    echo "error: content still exceeds 2 pages at the minimum fit-scale (0.85)" >&2
    echo "       there is genuinely too much content to fit 2 pages, even scaled." >&2
    echo "" >&2
    echo "fix candidates (in order of value):" >&2
    echo "  1. drop the lowest-value cards entirely" >&2
    echo "  2. shorten the longest cards (fewer rows, tighter prose)" >&2
    echo "  3. move depth out of the card and into the standard MD guide" >&2
    exit 3
  fi
  echo "pages:   $PAGES (fit-scale $USED_SCALE)"
else
  echo "note: pdfinfo not found; rendering at fit-scale 1.00 without auto-fit." >&2
  echo "      install poppler-utils to enable auto-fit + G-8 page enforcement." >&2
  render_scale "1.00"
fi

# Density floor (G-8): pixel-based ink ratio per page; applies to whatever pages
# exist (1 or 2). A 1-page card must still be dense.
if command -v pdftoppm >/dev/null 2>&1; then
  python3 "$(dirname "$0")/measure-pdf-density.py" "$OUTPUT_ABS" --threshold 0.20 || exit 4
else
  echo "note: pdftoppm not found; skipping G-8 density verification" >&2
fi

echo "ok"
