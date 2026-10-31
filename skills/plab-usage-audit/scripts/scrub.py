#!/usr/bin/env python3
"""
scrub.py - redact private patterns and the home path from a usage-audit bundle, before
`bundle-check.py`'s R8 privacy rule runs against it (Requirement 30, AC-20).

USAGE
-----
  scrub.py <bundle> [--private-pattern P [--private-pattern P2 ...]]

Every occurrence of a configured `--private-pattern` is replaced with `<private>`, and
every form of the current machine's home path is replaced with `~`. A `.json` file is
decoded, every string in it is redacted, and it is re-encoded, so a redaction can never
corrupt an escaped quote or backslash the way a blind text replace could. A `.jsonl` file
is handled the same way, one line at a time. Every other file is redacted as plain text.

A drive-letter absolute path (a drive letter, a colon, then a backslash- or forward-slash-
separated path) that contains a configured private pattern is redacted as a whole token,
not just at the matching substring, so a path whose middle segment matches the pattern
comes out as `<private>` rather than a half-redacted path that still shows its own shape.

EXIT CODES
----------
  0  ok       every readable file was scrubbed (even if nothing needed redacting)
  2  broken   the bundle directory does not exist

This script does not implement R8 itself; it is the thing R8 checks the *absence* of.
`bundle-check.py` still has to be run after this to prove the redaction actually worked,
including the drive-letter check that catches a path scrub.py was not told to look for.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

PRIVATE_PLACEHOLDER = "<private>"
HOME_PLACEHOLDER = "~"

# A drive-letter path token: a drive letter, a colon, a separator, then anything up to
# whitespace or a quoting character. This mirrors the regex bundle-format.md's R8 uses
# to flag any surviving drive-letter path, so what this script removes is what that rule
# would otherwise catch.
DRIVE_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s\"'<>]*")


def home_path_forms(home: str) -> list[str]:
    """The backslash, forward-slash, and JSON-escaped double-backslash forms of `home`,
    longest first so the escaped form is matched before its un-escaped substring is."""
    backslash = home.replace("/", "\\")
    forward = home.replace("\\", "/")
    escaped = backslash.replace("\\", "\\\\")
    forms = []
    for form in (escaped, backslash, forward):
        if form and form not in forms:
            forms.append(form)
    forms.sort(key=len, reverse=True)
    return forms


def redact_drive_paths(text: str, pattern: str) -> tuple[str, int]:
    """Replace each drive-letter path token containing `pattern` with the placeholder,
    leaving every other drive-letter token (one that does not match this pattern) alone."""
    count = 0
    out = []
    last = 0
    for m in DRIVE_PATH_RE.finditer(text):
        token = m.group(0)
        if pattern in token:
            out.append(text[last:m.start()])
            out.append(PRIVATE_PLACEHOLDER)
            count += 1
            last = m.end()
    out.append(text[last:])
    return "".join(out), count


def redact_string(text: str, patterns: list[str], home_forms: list[str]) -> tuple[str, int]:
    """Redact one string: home-path forms first, then each private pattern, drive-letter
    paths wholesale before the leftover plain substring. Returns (new_text, count)."""
    count = 0
    for form in home_forms:
        if form in text:
            count += text.count(form)
            text = text.replace(form, HOME_PLACEHOLDER)
    for pattern in patterns:
        if not pattern:
            continue
        text, drive_count = redact_drive_paths(text, pattern)
        count += drive_count
        if pattern in text:
            count += text.count(pattern)
            text = text.replace(pattern, PRIVATE_PLACEHOLDER)
    return text, count


def walk_json(value, patterns: list[str], home_forms: list[str], counter: list[int]):
    """Redact every string in a decoded JSON value, keys included, recursively."""
    if isinstance(value, dict):
        new = {}
        for key, sub in value.items():
            if isinstance(key, str):
                new_key, key_count = redact_string(key, patterns, home_forms)
                counter[0] += key_count
            else:
                new_key = key
            new[new_key] = walk_json(sub, patterns, home_forms, counter)
        return new
    if isinstance(value, list):
        return [walk_json(item, patterns, home_forms, counter) for item in value]
    if isinstance(value, str):
        new_value, string_count = redact_string(value, patterns, home_forms)
        counter[0] += string_count
        return new_value
    return value


def scrub_json_file(path: str, patterns: list[str], home_forms: list[str]) -> int:
    with io.open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    counter = [0]
    redacted = walk_json(data, patterns, home_forms, counter)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(redacted, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    return counter[0]


def scrub_jsonl_file(path: str, patterns: list[str], home_forms: list[str]) -> int:
    with io.open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    counter = [0]
    out_lines = []
    for line in lines:
        if not line.strip():
            out_lines.append(line)
            continue
        record = json.loads(line)
        redacted = walk_json(record, patterns, home_forms, counter)
        out_lines.append(json.dumps(redacted, ensure_ascii=False))
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        for line in out_lines:
            fh.write(line + "\n")
    return counter[0]


def scrub_text_file(path: str, patterns: list[str], home_forms: list[str]) -> int:
    with io.open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    redacted, count = redact_string(text, patterns, home_forms)
    if count:
        with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(redacted)
    return count


def scrub_bundle(bundle: str, patterns: list[str]) -> int:
    home_forms = home_path_forms(os.path.expanduser("~"))
    total = 0
    for root, _dirs, files in os.walk(bundle):
        for name in sorted(files):
            path = os.path.join(root, name)
            ext = os.path.splitext(name)[1].lower()
            try:
                if ext == ".json":
                    count = scrub_json_file(path, patterns, home_forms)
                elif ext == ".jsonl":
                    count = scrub_jsonl_file(path, patterns, home_forms)
                else:
                    count = scrub_text_file(path, patterns, home_forms)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                print("%s: could not scrub (%s)" % (path, exc))
                continue
            print("%s: %d redaction(s)" % (path, count))
            total += count
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Redact private patterns and the home path from a bundle.")
    parser.add_argument("bundle", help="the bundle directory to scrub in place")
    parser.add_argument("--private-pattern", action="append", default=[], dest="private_patterns",
                         help="a string to redact to <private>; repeatable")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.bundle):
        print("BROKEN: %s is not a directory" % args.bundle)
        return 2

    total = scrub_bundle(args.bundle, args.private_patterns)
    print("TOTAL: %d redaction(s) across %s" % (total, args.bundle))
    return 0


if __name__ == "__main__":
    sys.exit(main())
