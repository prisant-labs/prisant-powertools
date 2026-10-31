# PDF Toolchain Reference

Browser detection, install hints, and troubleshooting for the local headless-Chrome PDF rendering pipeline. Used by `scripts/render-pdf.sh` and `scripts/check-toolchain.sh`.

## Use when

- Phase 1 (intake) - surfacing missing-toolchain warnings early
- Phase 7 (PDF render) - actually rendering
- Triaging "PDF didn't render" or "wrong page count" complaints

## The contract

The skill spends **zero LLM tokens** rendering the PDF. `scripts/render-pdf.sh` invokes a local browser binary directly and validates the output. If no browser is found, the skill emits an install hint and skips Phase 7; the other three artifacts (standard MD, ADHD MD, HTML) are still produced.

## Supported browsers

In detection order (first match wins):

| Browser | macOS | Linux (PATH) | Windows (Git Bash / WSL) |
|---------|-------|--------------|--------------------------|
| Google Chrome | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` | `google-chrome`, `google-chrome-stable` | `/c/Program Files/Google/Chrome/Application/chrome.exe` |
| Chromium | `/Applications/Chromium.app/Contents/MacOS/Chromium` | `chromium`, `chromium-browser` | (typically not pre-installed) |
| Microsoft Edge | `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge` | `microsoft-edge`, `microsoft-edge-stable` | `/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe` |

All three accept `--headless=new --print-to-pdf=...` and produce identical-quality PDFs from the same HTML.

## Install hints

### macOS

```bash
# Google Chrome (recommended)
brew install --cask google-chrome

# Chromium (open-source, no Google account)
brew install --cask chromium

# Microsoft Edge
brew install --cask microsoft-edge
```

### Linux (Debian/Ubuntu)

```bash
# Chromium (smallest, fully open-source)
sudo apt update && sudo apt install -y chromium

# Google Chrome (download .deb from chrome.google.com)
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

### Linux (Fedora/RHEL)

```bash
sudo dnf install -y chromium
```

### Windows

```powershell
# via winget
winget install Google.Chrome
winget install Microsoft.Edge

# or download from
# https://www.google.com/chrome/
# https://www.microsoft.com/edge
```

### WSL

If you're running the skill from WSL, install a browser inside WSL (Linux-side) for cleanest behavior. Calling out to Windows-side Chrome from WSL is technically possible but adds path-conversion friction.

## Optional: pdfinfo (poppler-utils) for G-8 enforcement

`pdfinfo` is used to count pages and enforce the 2-page contract (gate G-8). Without it, the script renders successfully but skips page-count verification.

| Platform | Install |
|----------|---------|
| macOS | `brew install poppler` |
| Linux (Debian/Ubuntu) | `sudo apt install -y poppler-utils` |
| Linux (Fedora/RHEL) | `sudo dnf install -y poppler-utils` |
| Windows | Bundled with MiKTeX or via `choco install poppler`; commonly already installed |

## Render invocation

`scripts/render-pdf.sh` calls:

```
<browser> --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf=<output> file://<input>
```

Flag explanations:
- `--headless=new` - the modern (post-2022) headless mode; renders the same as visible Chrome
- `--disable-gpu` - avoids GPU-related render errors in headless contexts
- `--no-pdf-header-footer` - critical: without this, Chrome adds default page headers/footers that distort the layout

## Troubleshooting

### "no Chrome / Chromium / Edge binary found"

Run `scripts/check-toolchain.sh` to see the exact paths searched. Install one of the three browsers above. The skill auto-detects after install.

### "the browser exited N and produced no PDF" (exit 5)

The browser ran but left no PDF at the output path, or left a file that is empty or is not a PDF. `scripts/render-pdf.sh` removes any earlier PDF at that path before each render, so an old file cannot pass for a new one. Run the browser command from the section above by hand and read its stderr.

### "PDF rendered N pages; expected 2"

Page count exceeded the contract. Check `scripts/render-pdf.sh`'s overflow report (printed on stderr). Fix order:
1. Tighten the longest card on the overflowing page
2. Drop a low-value card
3. Reduce card padding by 1-2px in the HTML
4. Reduce grid gap by 1px
5. Trim masthead margin-bottom

The two locked references (`superpowers`, `memsearch`) converged at `padding: 5px 8px 5px 8px` and `gap: 5px`. Going below those values is possible but reduces breathing room.

### PDF renders blank or with rendering glitches

- Verify the HTML opens correctly in a normal browser. If the browser shows the same glitches, fix them in the HTML before re-rendering.
- Check that `--no-pdf-header-footer` is in the command. Without it, Chrome adds page headers that can compress content.
- Try a different browser (Chrome -> Edge or vice versa). They use the same engine but bundle different defaults.

### PDF has wrong fonts

The HTML template uses `"Segoe UI", "Helvetica Neue", Arial, sans-serif`. Chrome substitutes locally-available fonts. On bare-bones Linux containers, install `fonts-noto` or similar to ensure UTF-8 rendering.

### `pdfinfo: command not found`

Optional dependency. The skill renders without it but skips page-count validation. Install poppler-utils to enable G-8 enforcement.

### MiKTeX deprecation warning

If `pdfinfo` is bundled with MiKTeX (common on Windows), recent versions print a deprecation notice on stderr. Harmless; ignore. If it gets noisy, install poppler-utils separately.

## Cross-platform path handling

`scripts/render-pdf.sh` handles three path conventions:

| Platform | uname output | Path conversion |
|----------|-------------|-----------------|
| macOS | `Darwin` | direct (`realpath`) |
| Linux | `Linux` | direct (`realpath`) |
| Git Bash on Windows | `MINGW*` / `MSYS*` / `CYGWIN*` | `cygpath -w` to convert to Windows form, then forward-slash the result for `file:///` URL |

The `file://` URL must be absolute (with three slashes on Windows: `file:///C:/...`). The script handles this; consumers should not need to.

## Anti-patterns

| Anti-pattern | Symptom | Fix |
|-------------|---------|-----|
| Calling Chrome via `&` (background) | PDF write race | Always synchronous (no `&`) |
| Re-using a browser process across renders | Stale caches | Each invocation spawns a fresh headless process |
| Spending tokens on PDF generation | Misuses the LLM as a renderer | Always shell out to `scripts/render-pdf.sh` |
| Hardcoding a single browser path | Breaks on other machines | Use `detect_browser` (the script does this) |
| Skipping `--no-pdf-header-footer` | Default Chrome page headers ruin the layout | Always include this flag |
