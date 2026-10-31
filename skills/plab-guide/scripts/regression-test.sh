#!/usr/bin/env bash
# regression-test.sh
#
# Runs the locked baseline quick-reference HTMLs through the PDF renderer
# and verifies each still renders at 1 or 2 pages. Smoke-tests the end-to-end
# template + script pipeline against the locked examples.
#
# This does NOT regenerate the MD guides (those are produced by an LLM run
# and are not deterministic). It checks the deterministic part of the
# pipeline: HTML -> PDF rendering, page count, and gate G-8.
#
# Usage:
#   scripts/regression-test.sh
#
# Exit codes:
#   0 - all baselines pass
#   1 - one or more baselines failed
#   2 - prerequisite missing (browser not found, examples folder missing), or
#       nothing was verified (every bundle skipped, or pdfinfo missing)
#
# A bundle whose page count could not be checked is reported as SKIP, never as
# PASS, and a run that passes no bundle exits 2 rather than 0.

set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Baseline bundles are NOT shipped with this plugin; they live in the author's
# private development repository. Point this at your own baselines to use the
# suite, or set PLAB_GUIDE_EXAMPLES_DIR.
EXAMPLES_DIR="${PLAB_GUIDE_EXAMPLES_DIR:-${SKILL_DIR}/examples}"

if [[ ! -d "$EXAMPLES_DIR" ]]; then
  echo "error: examples directory not found at $EXAMPLES_DIR" >&2
  exit 2
fi

if ! "${SKILL_DIR}/scripts/check-toolchain.sh" >/dev/null 2>&1; then
  echo "error: no Chromium-based browser found; cannot render PDFs" >&2
  echo "run scripts/check-toolchain.sh for install hints" >&2
  exit 2
fi

# Bundles to test: locked baselines + recent calibration runs.
# Each entry: <subdir>/<slug>_quick-reference.html
BUNDLES=(
  "superpowers/superpowers_quick-reference.html"
  "memsearch/memsearch_quick-reference.html"
  "glow-2026-04-30/glow_quick-reference.html"
  "okrs-2026-05-01/okrs_quick-reference.html"
  "bullet-journaling-2026-05-01/bullet-journaling_quick-reference.html"
  "systems-thinking-2026-05-01/systems-thinking_quick-reference.html"
  "jq-2026-05-01/jq_quick-reference.html"
)

PASS=0
FAIL=0
SKIP=0
FAILED_BUNDLES=()

echo "=== plab-guide regression test ==="
echo "examples dir: $EXAMPLES_DIR"
echo

for bundle in "${BUNDLES[@]}"; do
  html="$EXAMPLES_DIR/$bundle"
  if [[ ! -f "$html" ]]; then
    echo "[SKIP] $bundle (file not found)"
    SKIP=$((SKIP + 1))
    continue
  fi

  # Render to a temp PDF so we don't clobber the committed PDF.
  tmp_pdf=$(mktemp -t plab-guide-regression-XXXXXX.pdf 2>/dev/null || mktemp /tmp/plab-guide-regression-XXXXXX.pdf)

  if "${SKILL_DIR}/scripts/render-pdf.sh" "$html" "$tmp_pdf" >/dev/null 2>&1; then
    # Page count check (gate G-8)
    if command -v pdfinfo >/dev/null 2>&1; then
      pages=$(pdfinfo "$tmp_pdf" 2>/dev/null | awk '/^Pages:/ {print $2}')
      if [[ "${pages:-0}" -ge 1 && "${pages:-0}" -le 2 ]]; then
        echo "[PASS] $bundle ($pages page(s))"
        PASS=$((PASS + 1))
      else
        echo "[FAIL] $bundle (rendered ${pages:-?} pages, expected 1 or 2)"
        FAIL=$((FAIL + 1))
        FAILED_BUNDLES+=("$bundle")
      fi
    else
      # No pdfinfo: the page count is unchecked, so this is not a pass.
      echo "[SKIP] $bundle (rendered, but pdfinfo is not installed, so the page count is unchecked)"
      SKIP=$((SKIP + 1))
    fi
  else
    echo "[FAIL] $bundle (render failed)"
    FAIL=$((FAIL + 1))
    FAILED_BUNDLES+=("$bundle")
  fi

  # Clean up
  rm -f "$tmp_pdf" 2>/dev/null || true
done

echo
echo "=== summary ==="
echo "passed: $PASS"
echo "failed: $FAIL"
echo "skipped: $SKIP"

if [[ $FAIL -gt 0 ]]; then
  echo
  echo "failed bundles:"
  for b in "${FAILED_BUNDLES[@]}"; do
    echo "  - $b"
  done
  echo
  echo "investigate: re-render manually with scripts/render-pdf.sh"
  echo "  (the bundle's HTML may have been edited and now overflows 2 pages)"
  exit 1
fi

if [[ $PASS -eq 0 ]]; then
  echo
  echo "error: no bundle was verified, so this run proves nothing" >&2
  echo "  install poppler-utils for pdfinfo, or point PLAB_GUIDE_EXAMPLES_DIR at your baselines" >&2
  exit 2
fi

echo
echo "all baselines passed."
exit 0
