#!/usr/bin/env python3
"""Fixture tests for render-pdf.sh, regression-test.sh and validate-manifest.py.

Run: python skills/plab-guide/scripts/test-guide-scripts.py

No real browser runs. Each render case puts a fake `google-chrome` first on
PATH, which both shell scripts find before any installed browser, and the fake
either writes a PDF or does not. A fake `pdfinfo` reports one page, so the
cases behave the same whether or not poppler is installed.

The canaries are not automated here, because they edit the scripts under test
rather than their input. To prove the render cases can fail, restore
`|| true` and `return 0` in render_scale(), rerun, and confirm the "no PDF"
cases fail by name; for regression-test.sh, delete its `PASS -eq 0` block and
confirm the empty-run case fails; then restore both.

Exit codes: 0 every case passed, 1 a case failed, 2 the test could not run
(no bash, or pyyaml missing).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDER = HERE / "render-pdf.sh"
REGRESSION = HERE / "regression-test.sh"
VALIDATE = HERE / "validate-manifest.py"

FAKE_BROWSER = """#!/usr/bin/env bash
# Fake browser. FAKE_MODE: none = write nothing; pdf = write a PDF;
# pdf-fail = write a PDF and exit 1.
out=""
for a in "$@"; do
  case "$a" in --print-to-pdf=*) out="${a#--print-to-pdf=}" ;; esac
done
case "${FAKE_MODE:-none}" in
  pdf) printf '%%PDF-1.4\\n%%%%EOF\\n' > "$out"; exit 0 ;;
  pdf-fail) printf '%%PDF-1.4\\n%%%%EOF\\n' > "$out"; exit 1 ;;
  *) exit 0 ;;
esac
"""

FAKE_PDFINFO = """#!/usr/bin/env bash
echo "Pages:          1"
"""

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def find_bash() -> str | None:
    found = shutil.which("bash")
    if os.name == "nt" and (found is None or "system32" in found.lower()):
        # System32's bash.exe is WSL, which cannot see this checkout's paths.
        for cand in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
            if Path(cand).is_file():
                return cand
        return None
    return found


def make_shims(root: Path) -> Path:
    shims = root / "shims"
    shims.mkdir()
    for name, body in (("google-chrome", FAKE_BROWSER), ("pdfinfo", FAKE_PDFINFO)):
        p = shims / name
        p.write_text(body, encoding="utf-8", newline="\n")
        p.chmod(0o755)
    return shims


def run(bash: str, script: Path, args: list[str], shims: Path, cwd: Path, extra: dict[str, str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PATH"] = str(shims) + os.pathsep + env.get("PATH", "")
    env.update(extra)
    return subprocess.run(
        [bash, script.as_posix(), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def render_cases(bash: str, root: Path, shims: Path) -> None:
    html = root / "card.html"
    html.write_text("<html><head></head><body>card</body></html>", encoding="utf-8")

    # A browser that exits 0 but writes nothing must not be reported as success.
    out = root / "none.pdf"
    r = run(bash, RENDER, ["card.html", "none.pdf"], shims, root, {"FAKE_MODE": "none"})
    check("no PDF written: exit 5", r.returncode == 5, f"exit {r.returncode}; stderr tail: {r.stderr.strip()[-160:]}")
    check("no PDF written: names the missing PDF", "produced no PDF" in r.stderr, r.stderr.strip()[-160:])
    check("no PDF written: no 'ok' line", "\nok" not in "\n" + r.stdout, r.stdout.strip()[-160:])

    # A PDF left by an earlier run must not stand in for this run's output.
    out.write_bytes(b"%PDF-1.4\n%%EOF\n")
    r = run(bash, RENDER, ["card.html", "none.pdf"], shims, root, {"FAKE_MODE": "none"})
    check("stale PDF at the output path: exit 5", r.returncode == 5, f"exit {r.returncode}")

    # Anti-canary: a browser that writes a PDF but exits 1 passes the existence check.
    # The exit code may still be 4 if a real pdftoppm judges the fake PDF's density,
    # so the assertion is only that the existence check did not fire.
    r = run(bash, RENDER, ["card.html", "fail.pdf"], shims, root, {"FAKE_MODE": "pdf-fail"})
    check("PDF written, browser exit 1: not exit 5", r.returncode != 5, f"exit {r.returncode}; stderr tail: {r.stderr.strip()[-160:]}")
    check("PDF written, browser exit 1: reported as a note", "exited 1 but wrote a PDF" in r.stderr, r.stderr.strip()[-160:])


def regression_cases(bash: str, root: Path, shims: Path) -> None:
    # No baseline bundle present: nothing is verified, so the run must not exit 0.
    empty = root / "no-baselines"
    empty.mkdir()
    r = run(bash, REGRESSION, [], shims, root, {"PLAB_GUIDE_EXAMPLES_DIR": str(empty)})
    check("regression run that verifies nothing: exit 2", r.returncode == 2, f"exit {r.returncode}; stdout tail: {r.stdout.strip()[-160:]}")
    check("regression run that verifies nothing: counts skips", "skipped: 7" in r.stdout, r.stdout.strip()[-160:])


def manifest_cases(root: Path) -> bool:
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("BROKEN: pyyaml is not installed, so validate-manifest.py cannot be tested (pip install pyyaml)")
        return False
    bundle = root / "bundle"
    bundle.mkdir()
    names = {
        "explanatory-standard": "t_guide.md",
        "explanatory-adhd": "t_guide-adhd.md",
        "quick-reference-html": "t_quick-reference.html",
        "quick-reference-pdf": "t_quick-reference.pdf",
    }
    for n in names.values():
        (bundle / n).write_text("x", encoding="utf-8")

    def manifest(conf: str) -> Path:
        lines = [
            "schema: plab-guide/v1",
            "topic: T",
            "slug: t",
            "input_type: concept",
            "generated: 2026-10-30",
            "generator_version: 2.2.3",
            "input: T",
            "research:",
            "  source_count: 0",
            "  sources_by_class: {A: 0, B: 0, C: 0}",
            f"  confidence: {conf}",
            "artifacts:",
        ]
        for t, n in names.items():
            lines.append(f"  - {{type: {t}, path: {n}{', pages: 1' if t == 'quick-reference-pdf' else ''}}}")
        p = bundle / "MANIFEST.yaml"
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p

    for conf, want in (("low-confidence draft", 0), ("low-confidence", 0), ("medium", 0), ("guesswork", 1)):
        r = subprocess.run([sys.executable, str(VALIDATE), str(manifest(conf))], capture_output=True, text=True)
        check(f"manifest confidence {conf!r}: exit {want}", r.returncode == want, f"exit {r.returncode}; {r.stderr.strip()[-160:]}")
    return True


def main() -> int:
    bash = find_bash()
    if bash is None:
        print("BROKEN: no POSIX bash found, so the shell scripts cannot be tested")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shims = make_shims(root)
        render_cases(bash, root, shims)
        regression_cases(bash, root, shims)
        if not manifest_cases(root):
            return 2
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if ok else f" :: {detail}"))
    print(f"{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
