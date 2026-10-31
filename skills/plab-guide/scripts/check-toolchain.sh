#!/usr/bin/env bash
# check-toolchain.sh
# Detect a Chromium-based browser without rendering anything.
# Used by plab-guide Phase 1 (intake) to surface a missing-browser
# warning early without blocking the run.
#
# Usage:
#   scripts/check-toolchain.sh
#
# Exit codes:
#   0 - browser found (path printed to stdout)
#   2 - no browser found (install hint printed to stderr)

set -euo pipefail

detect_browser() {
  local candidates=(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    "/Applications/Chromium.app/Contents/MacOS/Chromium"
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    "google-chrome"
    "google-chrome-stable"
    "chromium"
    "chromium-browser"
    "microsoft-edge"
    "microsoft-edge-stable"
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
  echo "  - Google Chrome:  https://www.google.com/chrome/" >&2
  echo "  - Chromium:       your package manager (apt/brew/choco)" >&2
  echo "  - Microsoft Edge: https://www.microsoft.com/edge" >&2
  echo "" >&2
  echo "without a browser, the skill still produces:" >&2
  echo "  - <slug>_guide-standard.md" >&2
  echo "  - <slug>_guide-adhd.md" >&2
  echo "  - <slug>_quick-reference.html" >&2
  echo "but skips:" >&2
  echo "  - <slug>_quick-reference.pdf" >&2
  exit 2
fi

echo "$BROWSER"

# Optional: report pdfinfo availability (poppler-utils) for G-8 enforcement
if command -v pdfinfo >/dev/null 2>&1; then
  echo "pdfinfo: $(command -v pdfinfo) (G-8 page-count enforcement enabled)" >&2
else
  echo "pdfinfo: not found (G-8 page-count enforcement will be skipped)" >&2
  echo "         install poppler-utils to enable" >&2
fi

# Optional: report mmdc availability (Mermaid CLI) for Phase 6.5 + G-18.
# Mermaid is optional content; warn-not-block is intentional.
if command -v mmdc >/dev/null 2>&1; then
  echo "mmdc:    $(command -v mmdc) (Phase 6.5 Mermaid pre-render enabled)" >&2
else
  echo "mmdc:    not found (Phase 6.5 Mermaid pre-render will degrade to warn)" >&2
  echo "         install with: npm install -g @mermaid-js/mermaid-cli" >&2
  echo "         only required if your bundle contains Mermaid diagrams" >&2
fi
