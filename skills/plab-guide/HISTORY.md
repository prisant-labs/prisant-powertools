# History - plab-guide

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 2.2.3 | 2026-10-30 | v0.11.0 | fix | Five defects from the 2026-08-29 audit. `render-pdf.sh` no longer reports success without a PDF, `regression-test.sh` no longer passes a page count it could not check, and `validate-manifest.py` accepts `low-confidence draft`. `SKILL.md` stops claiming four templates and stops requiring an unshipped `CREATION_NOTES.md`. A `.gitattributes` keeps shell scripts LF, and every script is now executable in git. |
| 2.2.2 | 2026-08-23 | v0.3.0 | fix | Three internal contradictions with the v2.0.0 one-or-two-page contract, plus vestigial em-dash-sweep wording. |
| 2.2.1 | 2026-08-14 | v0.1.0 | migrated | First release in prisant-utilities. Migrated from a private upstream at version 2.2.1; prior history remains there. |

## 2.2.3 - 2026-10-30

Correctness only. All five defects were found by the 2026-08-29 audit and re-confirmed against the files on 2026-10-30. No behavior a working run depends on changes.

- **`scripts/render-pdf.sh` could report success with no PDF.** `render_scale()` ended the browser call with `|| true` and always returned 0, so the script's verdict never depended on a file existing. Every render now removes any earlier PDF at the output path, then requires a non-empty file that starts with `%PDF-`, and exits 5 when there is none. The file is the proof, not the browser's exit code: a browser that exits non-zero but writes a PDF gets a note on stderr, not a failure. Exit code 5 is new and documented in the header and in `references/pdf-toolchain.md`.
- **`scripts/regression-test.sh` passed what it had not checked.** Without `pdfinfo` it printed `[PASS]` for a bundle whose page count it never read, and a run in which every bundle was missing printed "all baselines passed" and exited 0. An unchecked bundle is now `[SKIP]`, the summary counts skips, and a run that passes no bundle exits 2.
- **The confidence value did not match.** `SKILL.md`, both guide templates and three references tell the agent to write `low-confidence draft` for a guide with no sources, and `scripts/validate-manifest.py` accepted only `low-confidence`, so such a guide failed its own validator. The validator now accepts `low-confidence draft`, and still accepts `low-confidence` so that older manifests keep validating.
- **`SKILL.md` said "Four templates".** Three ship, and three have shipped since the migration in 2.2.1. The text now says three.
- **Acceptance item 5 required `CREATION_NOTES.md`.** The 2.2.1 entry below records that the file deliberately does not ship. The item is removed.
- **Line endings.** The repository gains a `.gitattributes` that pins `*.sh` to LF. The scripts were already LF in git, but a Windows checkout with `core.autocrlf` set turned them CRLF on disk, and bash fails on the stray carriage returns.
- **No script was executable in git.** All nine files in `scripts/` were stored as mode 100644, so on Linux and macOS `regression-test.sh` could not run `check-toolchain.sh` or `render-pdf.sh`, and the direct calls the docs show, such as `skills/plab-guide/scripts/render-pdf.sh <file>`, failed with "permission denied". Windows never shows this, which is how it survived; CI found it the first time it ran the new test. All nine are now 100755.

**Tests:** the new `scripts/test-guide-scripts.py` runs both shell scripts against a fake browser and a fake `pdfinfo` placed first on `PATH`, and runs the validator against fixture manifests: 13 of 13 checks pass, and CI runs it. The empty-run case requires the script's own "no bundle was verified" message, because a missing browser or a non-executable helper also exits 2. Canary: with `|| true`, `return 0` and the stale-file removal restored in `render_scale()`, and the no-bundle exit removed from `regression-test.sh`, six checks fail by name (7 of 13 pass).

## 2.2.2 - 2026-08-23

Correctness only. No behavior added, and nothing about how a guide is authored changes.

v2.0.0 made a dense single page legal and gave `render-pdf.sh` an auto-fit step, but three places in
the skill were never updated to match, so the skill contradicted itself:

- `scripts/regression-test.sh` asserted `pages -eq 2` and would have failed a legitimate 1-page
  baseline, against the contract its own renderer documents in its header. It now accepts 1 or 2 and
  reports the actual count. The comparison is also guarded with `${pages:-0}`, so a missing `pdfinfo`
  reading falls through to the failure branch instead of erroring under `set -u`.
- `references/quick-ref-html-patterns.md` repeated "exactly 2 pages" in its G-8 row, and its
  anti-pattern table listed a 1-page result as a "page-count floor failure". The ink floor is the
  real gate; page count alone is not.
- `SKILL.md`'s failure table still said "Em-dash leaks past sweep". There is no sweep: G-11 is a
  written-discipline rule verified by grep, which the same table's own gate list already said.

Found while reconciling the public docs READMEs against shipped skill versions. The docs half of that
work is separate and touches no skill. The version line drift was the visible symptom; these were the
defect underneath it.

## 2.2.1 - 2026-08-14

First public release. The skill is unchanged in behaviour from its last private version; this entry records the move, not a feature change.

**Migration provenance.** 2 recorded invocations via the Skill tool and 2 typed slash invocations in Claude Code on the origin machine, as of 2026-08-14. The low Claude Code count understates real use: this skill's output bundles were produced across several sessions and the count reflects only invocations captured in local transcripts on one machine.

**Not carried over, and why.** The prior HISTORY file is deliberately not reproduced. It contained absolute machine paths to a personal knowledge vault on the author's disk, which is precisely the class of content this plugin exists to avoid publishing. The version numbering continues unbroken; only the narrative was dropped.

**Also not carried over.** `CREATION_NOTES.md`, 137 lines of internal build narrative keyed to private planning folders, does not ship. It was development workshop material, not documentation.

**Changed for public release.** The default output root moved from a brand-named folder to `_output/plab-guide/`. A worked example inside `assets/templates/guide-template_standard.md` was genericised: it had named a private library as a community example and attributed a fictional plugin to a real, named person. Both are now neutral placeholders.

**Dependencies.** This skill loads `lib/render-mermaid.py` and `references/diagrams.md` from the plugin root. Toolchain requirements (headless Chrome, `pdfinfo`, `mmdc`) are reported by `scripts/check-toolchain.sh` and degrade gracefully when absent.
