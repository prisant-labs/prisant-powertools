#!/usr/bin/env python3
"""
Path-citation gate for a drafted plab-wrap-session log.

EXIT-CODE CONTRACT
------------------
  0  CLEAN    self-test passed AND every in-scope citation resolves
  1  FINDINGS self-test passed AND at least one in-scope citation is missing
  2  BROKEN   the detector could not prove itself, or the log could not be
              read, or anything else unanticipated went wrong

NEVER INTERPRET 2 AS CLEAN. See the sibling `dash-check.py` docstring and
`docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-11_three-state-gate-canaries/spec.md`.

Exit 1 means, and only means, that the detector ran to completion and proved
a real problem. Any exception this module did not anticipate is caught at
the top level (see the `__main__` guard at the bottom of this file) and
reported as BROKEN with exit 2, never allowed to fall through to Python's
default uncaught-exception exit status.

THE SUBJECT-MATCHING RULE
-------------------------
Only citations that assert a location are evaluated. The base rule comes from
`docs/internal/release-plans/plan_04_gates-that-cannot-fail-open/D-12_path-citation-precision/spec.md`:

  (a) contains a path separator      -> must exist, flagged when missing
  (b) backtick-wrapped, no separator -> resolved against the repo root;
                                        non-resolution is NOT a finding
  (c) neither signal                 -> prose, never evaluated at all

Branch (b) can never produce a finding by design. Naming a file is not the
same as claiming where it lives.

A citation is normalized before branch (a)/(b)/(c) is decided and before
resolution is attempted: a trailing line anchor (`:42`, `:42-50`) is
stripped, a leading elision of three or more dots is stripped, surrounding
sentence punctuation is stripped, and a trailing possessive (`'s` or the
typographic right single quote plus `s`) is stripped. What is being decided
is always "what file does this text name", not "what does this text look
like verbatim in the log".

WHY BRANCH (a) NEEDED NARROWING AGAIN (spec Revision 2, 2026-08-25)
-------------------------------------------------------------------
"Contains a path separator" survives as prose because a reader applies
judgment. A script has none. Measured against a real session log while
implementing this gate:

  old gate, pre-D-12                    7 flags, 6 false
  D-12's rule mechanized as written    13 flags, 11 false
  this file's rule                      4 flags, 2 false

Separators appear in many things that make no claim about a file's location:
slash commands (`/plab-wrap-session`), repository slugs
(`prisant-labs/agent-plugins`), git refs (`origin/main`), globs
(`docs/skills/*/README.md`), template placeholders (`_inbox/<skill>.md`), and
URLs. Shipping the unnarrowed rule would have put a detector that fails loud
into a release themed on detectors that fail open, at a worse false-positive
rate than the gate it replaces.

`is_path_claim()` below is the resulting test. Every exclusion is mechanical,
with no per-citation judgment. See D-12 spec Revisions for the superseded
criterion and the maintainer decision authorising this.

WHY THE MATCHER NEEDED THREE MORE FIXES (BUG-2, 2026-08-28)
-------------------------------------------------------------
Three false positives survived the D-12 narrowing, each caught by running
this gate against a real session log and reading every flag by hand:

  1. Leading dot stripped. `tok.strip(STRIP_CHARS)` strips from both ends,
     and STRIP_CHARS contains ".". A bare citation to a dotfile directory
     such as `.github/workflows/gate.yml` had its leading dot removed before
     resolution was even attempted, so a real path was flagged as missing.
     A leading dot is load-bearing (dotfiles, dotdirs); a trailing dot is
     almost always sentence punctuation. The fix strips those two ends with
     different character sets instead of one shared one.

  2. Version-numbered branch names read as file paths. The extension test
     was "does the basename contain a dot", which a version number also
     satisfies: `fix/v0.4.3-marketplace-rename` has a dot-bearing basename
     with no file extension anywhere in it. The fix adds a second, narrower
     positive test (does the text after the final dot look like a short
     alphanumeric extension) and a shape-based negative test for a
     version-number basename, so a real extension still qualifies while a
     branch name that merely contains dots does not.

  3. Possessives not stripped. STRIP_CHARS strips a trailing apostrophe, but
     the plain "s" that follows a possessive is not punctuation, so it
     blocked the strip and `scripts/check-dashes.py's` never resolved. The
     fix strips a trailing `'s` (ASCII or the typographic right single
     quote) as its own step before the general punctuation strip runs.

WHY THE MATCHER NEEDED REPAIR AGAIN THE SAME DAY (defects A through F,
2026-08-28, second pass)
-----------------------------------------------------------------------
The BUG-2 fixes above were themselves reviewed against a real session log
and found to have introduced one regression and left several rules with no
canary coverage at all, meaning any of them could be silently deleted or
weakened while the self-test still printed PASS.

  A. Regression. BUG-2 fix 2's extension test rejected anything after the
     final dot that was not a short alphanumeric run, which also rejects a
     line-number anchor: `path/file.md:42` has "md:42" after the final dot,
     not "md", so it silently left the D-12 rule's scope and a genuinely
     missing citation of that exact shape stopped being flagged. The fix is
     `strip_line_anchor()`: a trailing `:N` or `:N-M` is removed from the
     citation before the path-claim decision and before resolution, so
     `file.md:42` and `file.md:42-50` both reduce to `file.md`. A line
     anchor requires a digit immediately after the colon; a Windows drive
     letter's colon is always followed by `\\` or `/`, so the two shapes
     cannot be confused by this rule.

  B. The extension test from BUG-2 fix 2 had no canary that would fail if
     the test were deleted or neutered: every existing MUST_NOT_MATCH
     canary that exercised it had a fallback reason to be excluded (no
     separator, a real extension) even with the test gone. New MUST_NOT_MATCH
     canaries below use a genuinely missing path whose trailing dot-segment
     is extension-shaped only if the test is doing its job (too long, or
     containing a character the test rejects), so removing the test flips
     them from correctly-ignored to incorrectly-flagged.

  C. The typographic right single quote half of the possessive fix, and the
     ordering that lets a possessive still be found under trailing sentence
     punctuation (`SKILL.md's,`), had no canary in either direction.

  D. The version-number exclusion only recognised a hyphenated qualifier
     made of letters and digits (`-rc1`, `-codeql-v4`). A release-candidate
     qualifier that instead uses a dot (`v0.5.1-rc.2`) or is glued on
     without a hyphen (`v0.5.1rc1`) fell through to the extension test,
     which read the digit after the final dot as a one-character extension
     and produced exactly the false positive BUG-2 fix 2 was meant to kill.
     The version-shape regex now accepts both qualifier forms.

  E. A leading elision of three or more dots (`...skills/plab-guide/SKILL.md`,
     a reader's convention for "some path above here") was not being
     stripped, so the literal three-dot directory it named was checked for
     existence and never found. `./` and `../` are real relative-path
     prefixes and must never be touched; only a run of three or more
     leading dots is elision. `strip_ellipsis_prefix()` implements exactly
     that boundary and only that boundary.

  F. A non-UTF-8 byte, or a byte sequence a UTF-8 decoder rejects, in the
     log crashed with an uncaught UnicodeDecodeError, which Python turns
     into exit code 1, indistinguishable from FINDINGS. The general rule
     applies: unanticipated exceptions must exit 2, never 1. The log is
     now opened with the utf-8-sig codec (so a UTF-8 byte-order mark scans
     cleanly instead of attaching itself to the first token) and both the
     open and the read are wrapped to catch UnicodeDecodeError alongside
     OSError; the top-level `__main__` guard is the backstop for anything
     still unanticipated.

WHY THE MATCHER NEEDED FIVE MORE FIXES (defects G through K, 2026-11-07)
--------------------------------------------------------------------------
Session-log self-checks failed on path citations in six sessions between
2026-10-05 and 2026-11-04, and reading the flags by hand found five shapes
that make no claim about a file inside the repo:

  G. A backtick span with whitespace is usually a command. The whole span,
     such as `python tools/run-gate.py`, was joined to the repo root as one
     filename and flagged even when the script existed. A command with
     trailing arguments was the opposite blind spot: the last word's text
     after the final dot ("py --check") failed the extension test, so the
     path inside was never checked at all. A spaced span is now split, and
     each plain path-shaped word is checked as a bare token would be. Words
     carrying braces, quotes, "$", ":" or "=" are code (a brace expansion, a
     git object path, a variable), and a word with "\\." is an escaped regex,
     so neither is checked. The span is not split in three cases: it names a
     real path that contains a space; its first word, or any later word,
     points outside the repo root (a spaced Windows or home path, quoted or
     not); or its first word is a path and the whole span still reads as a
     file claim, which is a filename with spaces in it. A replay over 750
     real logs showed each of these cases was needed.

  H. A home-relative path (`~/.codex/config.toml`) is outside the repo root,
     like a drive-letter path, and is now excluded the same way. Only a
     leading `~/` or `~\\` counts.

  I. A git tag whose basename ends in a version number
     (`pre-merge/2026-11-04-release-3.12.0.0`) read its last digit as a file
     extension. VERSION_NUMBER only matched a basename that starts with the
     version. Two or more dot-separated digit groups at the end of a basename
     now mark a version tail. One number after a non-digit (`man/page.1`)
     stays an extension.

  J. Git range syntax (`origin/develop...HEAD`) read "HEAD" as an extension.
     Two or more dots inside a basename are never a file name.

  K. A leading `/` with more than one segment (`/resources/plugins/`) is an
     absolute POSIX path or a site route, outside the repo root.

These fixes recognise shapes by text alone and never ask git. A ref lookup
would make the result depend on what the repo holds at check time, and the
self-test could no longer prove the matcher without --repo-root.

Each fix, old and new, is mechanical and each has a paired canary and
anti-canary below: one proving the false positive is gone or never existed,
one proving the citation shape is still evaluated and would be flagged if it
were genuinely missing. An anti-canary alone can be satisfied by silently
excluding a whole citation shape from checking, which is a blind spot, not a
fix, which is why every rule in this file has both.

CITATION SHAPES: WHAT IS IN SCOPE AND WHAT IS DELIBERATELY OUT
----------------------------------------------------------------
In scope, and therefore flagged when the named file does not exist: a
citation carrying a path separator, or ending in `/` or `\\`, once normalized
(sentence punctuation trimmed, a trailing possessive removed, a trailing
line anchor removed, a leading three-or-more-dot elision removed), whose
basename either ends in `/` or `\\` (a directory claim) or has a final
dot-segment that looks like a real file extension: one to ten alphanumeric
characters, no hyphens, no embedded dots.

Out of scope, and therefore never flagged even when nothing resolves: a URI
with a scheme (`https://...`), a Windows absolute path (`C:\\...`), a
home-relative path (`~/...`), an absolute POSIX path or site route with more
than one segment (`/resources/plugins/`), git range syntax
(`origin/develop...HEAD`), a basename ending in a version number
(`pre-merge/2026-11-04-release-3.12.0.0`), a glob
(`docs/skills/*/README.md`), a template placeholder (`_inbox/<skill>.md`), a
one-segment slash command (`/plab-wrap-session`), a basename shaped like a
version number with an optional hyphenated-and-or-dotted or glued-on
qualifier (`v0.4.3`, `v0.4.2-codeql-v4`, `v0.5.1-rc.2`, `v0.5.1rc1`), a
basename whose final dot-segment does not look like a real extension (too
long, contains a hyphen, or otherwise fails the extension shape test), and
any token that never carried a path separator to begin with (backtick-
wrapped or not: prose that merely names a bare filename never enters branch
(a); a bare filename with a separator prefix does).

--repo-root IS THE PROJECT BEING WRAPPED
----------------------------------------
Not this skill's installed location. Same contract as `organize-logs.py`'s
store argument (SKILL.md:91): "the store argument is relative to the project
being wrapped. Do not assume the two share a root."

The self-test never touches --repo-root. It builds a throwaway fixture and
resolves every canary against that instead, so the gate's trustworthiness does
not depend on which project happens to be under the cursor.
"""

import argparse
import os
import re
import sys
import tempfile

BACKTICK_SPAN = re.compile(r"`([^`\n]+)`")
URI_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.]*://")
WINDOWS_ABS = re.compile(r"^[A-Za-z]:[\\/]")
STRIP_CHARS = ".,;:!?()[]{}\"'<>"
# Leading punctuation is stripped with everything except ".": a leading dot
# is load-bearing on a dotfile or dotdir citation (.github/, .gitignore).
LEADING_STRIP_CHARS = STRIP_CHARS.replace(".", "")
# A trailing possessive is not part of the path. STRIP_CHARS alone cannot
# remove it because the "s" after the apostrophe is not itself punctuation,
# so it is stripped as its own step, ASCII apostrophe or typographic quote.
POSSESSIVE_SUFFIX = re.compile("(?:'s|" + chr(0x2019) + "s)$")
# A short alphanumeric tail after the final dot is what a real file
# extension looks like: .yml, .md, .py, .gitignore. No hyphens, no digits
# strung together with more dots after it.
FILE_EXTENSION = re.compile(r"^[A-Za-z0-9]{1,10}$")
# An optional leading "v", two or more dot-separated digit groups, and then
# either a hyphenated qualifier (itself optionally dotted: -rc, -codeql-v4,
# -rc.2) or a qualifier glued straight on with no hyphen (rc1). This is what
# a version number or a release-candidate-style build tag looks like, not
# what a file extension looks like, even though both contain dots in a
# basename.
VERSION_NUMBER = re.compile(
    r"^v?\d+(\.\d+){1,}"
    r"(?:(?:-[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*)*|[A-Za-z]+\d*)$"
)
# A trailing line or line-range anchor, e.g. ":42" or ":42-50", stripped
# from a citation before the path-claim decision and before resolution. A
# Windows drive letter's colon is always followed by "\" or "/", never a
# digit, so this can never mistake a drive prefix for a line anchor.
LINE_ANCHOR = re.compile(r":\d+(-\d+)?$")
# A leading run of three or more dots is an elision convention ("some path
# above here"), not a real relative-path prefix. "." and ".." are real
# prefixes and must never match this.
ELLIPSIS_PREFIX = re.compile(r"^\.{3,}")
# A leading "~/" or "~\" names the user's home folder, which is outside the
# repo root just as a drive-letter path is. A tilde anywhere else is literal.
HOME_RELATIVE = re.compile(r"^~[\\/]")
# Two or more dot-separated digit groups at the end of a basename are a
# version number, as in the tag pre-merge/2026-11-04-release-3.12.0.0. A real
# file extension is never the last group of a version. One group after a
# non-digit (man/page.1) does not match, so that stays an extension.
VERSION_TAIL = re.compile(r"\d+(\.\d+)+$")
# The words of a backticked command that are checked as paths: letters,
# digits, underscore, dot, hyphen, tilde and the two separators, nothing else.
PLAIN_WORD = re.compile(r"^[\w.~/\\-]+$")


def has_separator(cite):
    return "/" in cite or "\\" in cite


def outside_repo_reason(cite):
    """Name why a citation points outside the repo root, or return None.

    These citations make a claim about a location, but not one --repo-root
    can check, so they are out of scope rather than missing.
    """
    if URI_SCHEME.match(cite):
        return "uri scheme"
    if WINDOWS_ABS.match(cite):
        return "absolute path outside the repo root"
    if HOME_RELATIVE.match(cite):
        return "home-relative path outside the repo root"
    if cite.startswith("/") and cite.count("/") > 1:
        return "absolute POSIX path or site route outside the repo root"
    return None


def strip_line_anchor(cite):
    """Remove a trailing ':N' or ':N-M' line anchor from a citation."""
    return LINE_ANCHOR.sub("", cite)


def strip_ellipsis_prefix(cite):
    """Remove a leading elision of three or more dots from a citation."""
    return ELLIPSIS_PREFIX.sub("", cite)


def is_path_claim(cite):
    """Does this citation assert where a file lives? Returns (bool, reason).

    `cite` is assumed already normalized (line anchor and ellipsis prefix
    stripped). Every branch here is mechanical. Nothing inspects meaning.
    """
    outside = outside_repo_reason(cite)
    if outside:
        return False, outside
    if "*" in cite or "?" in cite:
        return False, "glob"
    if "<" in cite or ">" in cite:
        return False, "template placeholder"
    if cite.startswith("/") and cite.count("/") == 1:
        return False, "slash command"
    if not has_separator(cite):
        return False, "no separator"
    if cite.endswith("/") or cite.endswith("\\"):
        return True, "directory claim"
    base = os.path.basename(cite.rstrip("/\\").replace("\\", "/"))
    if "." not in base:
        return False, "no file extension"
    if ".." in base:
        return False, "git revision range, not a file name"
    if VERSION_NUMBER.match(base):
        return False, "version number, not a file extension"
    if VERSION_TAIL.search(base):
        return False, "basename ends in a version number, not a file extension"
    ext = base.rsplit(".", 1)[1]
    if not FILE_EXTENSION.match(ext):
        return False, "trailing dot-segment does not look like a file extension"
    return True, "path claim"


def clean_token(tok):
    """Strip the punctuation a bare word picks up from surrounding prose.

    Order matters. Trailing sentence punctuation comes off first (a period,
    a comma, a closing paren). Only then is a trailing line anchor checked,
    because `made-up.md:42,` has a real sentence comma after the digits
    that would otherwise block LINE_ANCHOR's end anchor. Only then is a
    trailing possessive checked, because `check-dashes.py's.` has a real
    sentence period after the "s" that would otherwise block
    POSSESSIVE_SUFFIX's end anchor. Leading punctuation comes off next, and
    never a leading dot: `(.github/foo.yml)` must lose the parenthesis and
    keep the dot that makes it a dotdir path. A leading three-or-more-dot
    elision comes off last, after any wrapping punctuation around it has
    already been stripped.
    """
    c = tok.rstrip(STRIP_CHARS)
    c = strip_line_anchor(c)
    c = POSSESSIVE_SUFFIX.sub("", c)
    # A possessive can sit on top of a line anchor: `made-up.md:42's` reaches
    # the first anchor strip with the "s" still blocking LINE_ANCHOR's end
    # anchor, so the anchor survives into the extension test and the whole
    # citation drops out of scope. One more pass after the possessive comes
    # off closes that, and the strips are idempotent so a second pass is free
    # for every other shape.
    c = strip_line_anchor(c)
    c = c.lstrip(LEADING_STRIP_CHARS)
    c = strip_ellipsis_prefix(c)
    return c


def extract_citations(text):
    """Return [(citation, was_backtick_wrapped), ...] for one log's text.

    Bare tokens are only candidates when they carry a separator; a bare word
    with an extension and no separator is branch (c) and never enters the
    set. Backtick-wrapped spans skip the prose-punctuation stripping (the
    author deliberately delimited the span) but still get the same line-
    anchor and ellipsis-prefix normalization as a bare token, since those
    are about what file the text names, not about surrounding prose.
    """
    cites = []
    for m in BACKTICK_SPAN.finditer(text):
        c = m.group(1).strip()
        if not c:
            continue
        c = strip_line_anchor(c)
        c = strip_ellipsis_prefix(c)
        cites.append((c, True))
    # Blank out backtick spans so a wrapped citation is not counted twice.
    outside = BACKTICK_SPAN.sub(" ", text)
    for tok in outside.split():
        c = clean_token(tok)
        if c and has_separator(c):
            cites.append((c, False))
    return cites


def spaced_span_findings(cite, root):
    """Findings for a backtick span that contains whitespace.

    Such a span is usually a command (`python tools/run-gate.py --check`), so
    the whole span is not a filename and its path words are what get checked.
    Two cases keep the span whole: it names a real path that contains a
    space, or its first word points outside the repo root (a spaced Windows
    or home path), which is out of scope as a whole.
    """
    if os.path.exists(os.path.join(root, cite)):
        return []
    words = cite.split()
    if outside_repo_reason(words[0].lstrip(LEADING_STRIP_CHARS)):
        return []
    # A quoted Windows path with a space ("C:\Program Files\...") splits into
    # a drive-letter word and a tail that looks repo-relative. Any
    # drive-letter word marks the span as outside the repo root.
    if any(WINDOWS_ABS.match(w.lstrip(LEADING_STRIP_CHARS)) for w in words):
        return []
    # A span whose first word is already a path, and which as a whole still
    # reads as a file claim, is a filename with spaces in it, not a command.
    if has_separator(words[0]):
        claim, _reason = is_path_claim(cite)
        if claim:
            return [cite]
    out = []
    for word in words:
        c = clean_token(word)
        if not c or not has_separator(c):
            continue
        # Inside a command only a plain path-shaped word is checked. Braces,
        # quotes, "$", ":" and "=" mark code (a brace expansion, a git object
        # path, a variable), and "\." marks an escaped regex.
        if not PLAIN_WORD.match(c) or "\\." in c:
            continue
        claim, _reason = is_path_claim(c)
        if claim and not os.path.exists(os.path.join(root, c)):
            out.append(c)
    return out


def findings_for(text, root):
    """Return the citations that assert a location and do not resolve."""
    out = []
    for cite, backticked in extract_citations(text):
        if backticked and len(cite.split()) > 1:
            out.extend(spaced_span_findings(cite, root))
            continue
        claim, _reason = is_path_claim(cite)
        if not claim:
            continue
        if not os.path.exists(os.path.join(root, cite)):
            out.append(cite)
    return out


# Canaries are log-line fragments, evaluated against a throwaway fixture that
# self_test() builds, never against --repo-root.
MUST_MATCH = [
    "the file `missing/canary-target.md` was updated this session",
    # BUG-2 defect 1 (leading dot stripped): a bare dotted path that is
    # genuinely missing must still be flagged, not silently excluded.
    "bare dotted path, missing: .github/workflows/missing-canary.yml is not tracked",
    # BUG-2 defect 2 (version numbers read as extensions): a real,
    # genuinely-missing filename that happens to embed a version number
    # must stay in scope, proving the version exclusion is shape-based
    # and not "any dot near a digit gets a pass".
    "versioned filename, missing: docs/CHANGELOG-v0.4.3.md tracks releases",
    # BUG-2 defect 3 (possessives not stripped): a possessive citing a path
    # that genuinely does not exist must still be flagged.
    "possessive on a missing path: real/missing-possessive.py's docstring is unwritten",
    # Defect A (line-anchor regression): the exact shape that stopped being
    # flagged this morning. If strip_line_anchor() is removed, the leftover
    # "md:42" fails the extension test and this citation silently drops out
    # of scope instead of being flagged, so this is the canary that proves
    # the regression is closed.
    "line-anchored missing path: docs/internal/made-up.md:42 is cited here",
    # Defect A, range form: "file.md:42-50" must reduce the same way.
    "line-anchored range on a missing path: docs/internal/other-made-up.md:42-50 is cited here",
    # A possessive stacked on a line anchor. Found by adversarial review as a
    # narrowing against the pre-fix gate: the trailing "s" blocked the anchor
    # strip, the anchor then failed the extension test, and the citation left
    # scope entirely. Both strips now run to a fixed point.
    "possessive on an anchored missing path: docs/internal/made-up.md:42's header was rewritten",
    # Defect C (curly possessive): the typographic right single quote half
    # of the possessive fix, on a citation that genuinely does not exist.
    "curly possessive on a missing path: real/missing-possessive-curly.py" + chr(0x2019) + "s docstring is unwritten",
    # Defect C (possessive followed by punctuation): a possessive citation
    # trailed by a comma, genuinely missing, proving the rstrip-before-
    # possessive ordering is what makes this resolve at all, not an
    # accident of no punctuation being present in the corpus.
    "comma after possessive on a missing path: missing/comma-possessive.md's, docstring is unwritten",
    # Defect E: "./" and "../" are real relative-path prefixes, never
    # elision, so a genuinely missing target behind either one must still
    # be flagged, proving ELLIPSIS_PREFIX's {3,} bound was not loosened to
    # also eat one or two leading dots.
    "single-dot prefix, missing: ./missing/dotslash-canary.md was never written",
    "double-dot prefix, missing: ../missing/dotdotslash-canary.md was never written",
    # Defect E: an ellipsis-elided citation to a target that genuinely does
    # not exist, even after the elision is stripped, must still be flagged.
    "elided path, missing: ...missing/ellipsis-canary.md was never added",
    # Defect G (commands in backticks): splitting a command span must still
    # check the path inside it. If the split drops the span instead of
    # evaluating its words, this missing script stops being flagged.
    "command on a missing script: `python missing/run-gate.py --check` failed",
    # Defect G: a filename with spaces whose first word is already a path is
    # still one path claim. If the span were always split, this missing
    # file would break into words that each look like prose and drop out.
    "spaced filename, missing: `notes/B-03. Lock the contract.md` was moved",
    # Defect H (home-relative paths): the exclusion is anchored to a leading
    # "~/" or "~\". A tilde anywhere else in a missing path stays in scope.
    "tilde inside a path, missing: missing/notes~/tilde-canary.md was never written",
    # Defect I (version tails): the exclusion needs two or more dot-separated
    # digit groups at the end of the basename. A one-number extension, such
    # as a man page's, is still a file extension.
    "one-number extension, missing: man/missing-page.1 was never written",
]

MUST_NOT_MATCH = [
    "the run wrote results.json into the output folder",
    "the helper `bare-nonexistent-canary.py` covers this case",
    "see `real/canary-target.md` for the worked example",
    "published at https://github.com/prisant-labs/prisant-utilities for reference",
    "type `/plab-wrap-session` to close the session",
    "the marketplace lives at prisant-labs/agent-plugins today",
    "rebased onto origin/main before pushing",
    "swept `docs/skills/*/README.md` for stale version lines",
    "the intake path is `_local/roadmaps/_inbox/<skill>.md` per convention",
    r"read C:\Users\someone\notes\scratch.md on the other machine",
    # BUG-2 defect 1 anti-canary: the leading dot must survive so this
    # existing dotdir path resolves instead of being flagged as missing.
    "bare token with a leading dot: .github/workflows/gate.yml exists",
    # BUG-2 defect 2 anti-canaries: a version-numbered branch name is not a
    # path claim, bare or with a trailing hyphenated remainder, or on its own.
    "version branch: fix/v0.4.3-marketplace-rename was merged",
    "version branch with two remainders: fix/v0.4.2-codeql-v4 landed",
    "bare version number: fix/v0.4.3 shipped",
    # Control for defect 2: a dot-free basename was never a claim and must
    # keep behaving that way after the extension test gets narrower.
    "dot-free control: docs/wrap-continue-release-plans was the topic",
    # BUG-2 defect 3 anti-canary: the possessive suffix must come off so
    # this existing file resolves instead of being flagged as missing.
    "possessive on a real path: real/possessive-target.py's docstring explains the canary",
    # Defect A anti-canaries: a line anchor on a citation to a real file
    # must not block resolution, bare digit or a hyphenated range.
    "line-anchored real path: real/canary-target.md:42 is the anchor",
    "line-anchored range on a real path: real/canary-target.md:42-50 is the anchor",
    # Defect A: a Windows drive-letter path followed by what looks like a
    # line anchor must still be excluded as a Windows absolute path once
    # the anchor is stripped, never mistaken for anything else.
    r"windows drive with anchor: C:\Users\someone\notes\scratch.md:42 was referenced",
    # Defect B: a trailing dot-segment that fails the extension shape test
    # (a hyphen inside it) must stay out of scope even though the target
    # does not exist. If FILE_EXTENSION is removed or neutered this
    # citation starts being treated as a claim and gets flagged, failing
    # this canary.
    "malformed extension: notes/handoff.docx-final was attached",
    # Defect B: a trailing dot-segment that fails the extension shape test
    # (too long) must stay out of scope for the same reason, exercising the
    # length bound rather than the character-class bound.
    "long extension: notes/archive.longextensionname was attached",
    # Defect C anti-canary: the curly possessive suffix must come off so
    # this existing file resolves instead of being flagged as missing.
    "curly possessive on a real path: real/possessive-target.py" + chr(0x2019) + "s docstring explains the canary",
    # Defect C anti-canary: a possessive followed by a trailing comma, on a
    # citation to a file that exists, must resolve.
    "comma after possessive on a real path: real/SKILL.md's, guidance stands",
    # Defect D: a release-candidate qualifier joined with a dot, and one
    # glued on with no hyphen at all, are both version shapes, not file
    # extensions, and must not be flagged.
    "release candidate, dotted qualifier: release/v0.5.1-rc.2 is in progress",
    "release candidate, glued qualifier: release/v0.5.1rc1 is in progress",
    # Defect E anti-canaries: "./" and "../" are real prefixes, so a target
    # that genuinely exists behind either one must resolve, proving the
    # ellipsis rule does not over-strip and turn a real prefix into a
    # broken one.
    "single-dot prefix, real: ./real/canary-target.md is the anchor",
    "double-dot prefix, real: ../shared/up-target.md is the anchor",
    # Defect E anti-canary: the original false positive, an ellipsis-elided
    # citation to a target that genuinely exists once the elision is
    # stripped.
    "elided path, real: ...skills/plab-guide/SKILL.md documents the workflow",
    # Defect G anti-canaries: a backtick span with whitespace is usually a
    # command, and its path words are what get checked. The whole span is
    # not a filename. A span that names a real file whose path contains a
    # space still resolves as one path, and a spaced absolute path stays
    # excluded as a whole.
    "command on a real script: `python real/possessive-target.py` ran clean",
    "command with arguments on a real script: `python real/possessive-target.py --check` ran clean",
    "spaced path, real: `real/spaced dir/target.md` holds the notes",
    r"spaced windows path: `C:\Users\some one\notes\scratch.md` was read",
    r'quoted spaced windows path: `"C:\Program Files\Git\bin\bash.exe" -lc ls` ran',
    r'windows path after a command word: `cd "C:\Program Files\Tools\notes.md"` failed',
    "spaced home path: `~/some one/notes.md` holds the draft",
    "script path with arguments, real: `./real/possessive-target.py --check` ran",
    # Defect G anti-canaries: code inside a command is not a path claim. A
    # git object path, a brace expansion and an escaped regex each carry a
    # separator and an extension-shaped tail, so each would be flagged if
    # every word with a separator were checked.
    "git object path: `git show origin/main:missing/object.md | head` printed it",
    "brace expansion: `ls missing/public/{catalog.json, llms.txt}` listed them",
    r"escaped regex: `grep -E v0\.6\.0 notes.txt` matched",
    # Defect H anti-canaries: a home-relative path is outside the repo root,
    # like a drive-letter path, backtick-wrapped or bare.
    "home path in backticks: `~/.codex/config.toml` holds the setting",
    "bare home path: ~/.claude/skills/ was swept",
    # Defect I anti-canary: a tag whose basename ends in a version number is
    # a git ref, not a file with an extension of "0".
    "tag with a version tail: pre-merge/2026-11-04-release-3.12.0.0 is the undo point",
    # Defect J anti-canary: two or more dots inside a basename are git range
    # syntax, never a file name.
    "git range: `origin/develop...HEAD` counts the commits",
    # Defect K anti-canary: a leading "/" with more than one segment is an
    # absolute POSIX path or a site route, outside the repo root.
    "site route: `/resources/plugins/` is the page",
]


def self_test():
    """Prove the matcher works before trusting a clean result."""
    failures = []
    with tempfile.TemporaryDirectory() as fixture:
        # The fixture root citations resolve against sits one level below
        # the tempdir. That leaves a sibling directory available so a
        # genuine "../" prefix (Defect E) has something real to climb to,
        # proving it survives normalization rather than getting eaten by
        # the elision rule that strips three-or-more leading dots.
        root = os.path.join(fixture, "proj")

        def write_fixture(rel_path, content):
            path = os.path.join(root, rel_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)

        write_fixture(
            os.path.join("real", "canary-target.md"),
            "fixture canary target\n")
        # BUG-2 defect 1 fixture: a dotted directory, so a bare citation
        # that keeps its leading dot has something real to resolve against.
        write_fixture(
            os.path.join(".github", "workflows", "gate.yml"),
            "fixture dotdir canary target\n")
        # BUG-2 defect 3 fixture: a real file for the possessive anti-canary
        # to resolve against once the trailing "'s" is stripped.
        write_fixture(
            os.path.join("real", "possessive-target.py"),
            "fixture possessive canary target\n")
        # Defect C fixture: a real file for the comma-after-possessive
        # anti-canary.
        write_fixture(
            os.path.join("real", "SKILL.md"),
            "fixture comma-possessive canary target\n")
        # Defect E fixture: the real target an ellipsis-elided citation
        # names once the leading "..." is stripped.
        write_fixture(
            os.path.join("skills", "plab-guide", "SKILL.md"),
            "fixture ellipsis canary target\n")
        # Defect G fixture: a real file whose path contains a space, so the
        # spaced-path anti-canary has something to resolve against.
        write_fixture(
            os.path.join("real", "spaced dir", "target.md"),
            "fixture spaced-path canary target\n")

        # Defect E fixture: a target reachable only through a genuine ".."
        # prefix, one level above root.
        shared_dir = os.path.join(fixture, "shared")
        os.makedirs(shared_dir, exist_ok=True)
        with open(os.path.join(shared_dir, "up-target.md"), "w", encoding="utf-8") as fh:
            fh.write("fixture parent-dir canary target\n")

        for s in MUST_MATCH:
            if not findings_for(s, root):
                failures.append("  should have been flagged but was not: %r" % s)
        for s in MUST_NOT_MATCH:
            got = findings_for(s, root)
            if got:
                failures.append(
                    "  should NOT have been flagged but was: %r -> %r" % (s, got))

    if failures:
        print("GATE SELF-TEST FAILED - the matcher is not trustworthy.",
              file=sys.stderr)
        print("\n".join(failures), file=sys.stderr)
        print("\nExiting 2 (broken). Do NOT read this as a clean log.",
              file=sys.stderr)
        return False
    print("gate self-test: PASS (%d canaries flagged, "
          "%d anti-canaries correctly ignored)"
          % (len(MUST_MATCH), len(MUST_NOT_MATCH)))
    return True


def main():
    ap = argparse.ArgumentParser(
        description="Canary-verified path-citation gate for a drafted session log.")
    ap.add_argument("log_path", nargs="?",
                    help="the drafted log file to scan (omit with --self-test-only)")
    ap.add_argument("--repo-root", default=os.getcwd(),
                    help="the project being wrapped (default: cwd), not this skill's location")
    ap.add_argument("--self-test-only", action="store_true",
                    help="prove the detector and exit, scanning nothing")
    args = ap.parse_args()

    if not self_test():
        sys.exit(2)

    if args.self_test_only:
        sys.exit(0)

    if not args.log_path:
        print("BROKEN: no log_path given and --self-test-only not set.",
              file=sys.stderr)
        sys.exit(2)

    try:
        # utf-8-sig so a UTF-8 byte-order mark is consumed instead of being
        # left attached to the first token on line 1.
        with open(args.log_path, encoding="utf-8-sig") as fh:
            lines = fh.readlines()
    except (OSError, UnicodeDecodeError) as exc:
        print("BROKEN: could not read %s as UTF-8: %s: %s"
              % (args.log_path, type(exc).__name__, exc),
              file=sys.stderr)
        sys.exit(2)

    hits = []
    for n, line in enumerate(lines, 1):
        for cite in findings_for(line, args.repo_root):
            hits.append((n, cite))

    if hits:
        for n, cite in hits:
            print("%s:%d: does not resolve under %s: %s"
                  % (args.log_path, n, args.repo_root, cite))
        print("FINDINGS: %d citation(s) assert a location that does not exist."
              % len(hits), file=sys.stderr)
        sys.exit(1)

    print("CLEAN: canary proved, every in-scope citation in %s resolves"
          % args.log_path)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        # main()'s own sys.exit() calls carry the real exit-code contract;
        # let them pass through untouched.
        raise
    except Exception as exc:
        # The general rule: no unexpected exception may ever surface as
        # exit 1, which this exit-code contract reserves for "the detector
        # ran and found a real problem". Anything this module did not
        # anticipate is BROKEN, not FINDINGS.
        print("BROKEN: unexpected %s: %s" % (type(exc).__name__, exc),
              file=sys.stderr)
        sys.exit(2)
