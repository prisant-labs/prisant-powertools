#!/usr/bin/env python3
"""
Skill version-bump gate: a skill whose folder changed since the last tag must have bumped its
own version and recorded that version in its own HISTORY.md.

EXIT-CODE CONTRACT
------------------
  0  CLEAN      self-test passed AND no skill changed without a matching bump, OR self-test
                passed AND every finding is ADVISORY (see MODE below)
  1  FINDINGS   self-test passed AND at least one finding exists AND the mode is ENFORCED
  2  BROKEN     the detector could not prove itself, `git describe --tags --abbrev=0` found no
                tag at all, a skill directory has no SKILL.md or no HISTORY.md, a version string
                could not be parsed, or any other exception reached the top level

NEVER INTERPRET 2 AS CLEAN. Same contract as `scripts/version-parity-check.py` and
`scripts/doc-lifecycle-check.py`: an empty or unparseable input is BROKEN, never read as a clean
tree.

WHY THIS SCRIPT EXISTS
-----------------------
`skills/plab-wrap-session/references/hygiene-sweep.md`, Check 4, carries a bash recipe (delivered
by D-03) that answers exactly this question: for each skill directory with content changed since
the last tag, did `metadata.version` move, and does `HISTORY.md` have a row for the version
currently shipping. Until this script, that recipe lived only inside a skill reference document,
run by an agent during a session wrap, so CI never ran it: a version could go unbumped through any
number of green pull requests, found only if and when someone happened to wrap a session. This
script mechanizes the same recipe as a committed, CI-wired gate. It answers the same question
Check 4 always asked ("should this version have been bumped, judged against the last tag") and
deliberately NOT the question `scripts/version-parity-check.py` asks ("does the version written in
the documentation agree with what the repository declares right now"); those two gates read
disjoint evidence and neither one substitutes for the other.

MODE: ADVISORY VS ENFORCED, AND WHY
------------------------------------
This repository deliberately lets effort pull requests land with skill content changed and no
version bump at all, and does every version-bookkeeping decision in one closing release pull
request instead (`docs/internal/release-plans/release-checklist.yaml`). A gate that always failed
on an unbumped version would fight that convention on every ordinary effort PR. So this script
reads `library.json`'s own top-level `version` at HEAD and at the latest tag:

  equal      no release is in progress (the plugin version has not moved since the tag). Findings
             are printed labelled ADVISORY and the script exits 0. This is the common case: most
             pull requests land here, and effort PRs are expected to carry unbumped skills.
  different  a release is in progress (something, somewhere, already bumped the plugin version).
             Findings are enforced: printed plainly and the script exits 1, because the closing
             release PR is exactly the moment this repository's own convention says the bumping
             should have already happened.

`--strict` forces ENFORCED regardless of the comparison, for a maintainer who wants this gate to
block on demand rather than warn.

WHY A NEW SKILL SINCE THE TAG IS SKIPPED, NOT A FINDING
----------------------------------------------------------
A skill that did not exist at the latest tag has no prior `metadata.version` to differ from; there
is nothing to bump away from. This mirrors the hygiene-sweep recipe's own
`git cat-file -e "$LAST_TAG:$skill_file" 2>/dev/null || continue` branch exactly: a skill new since
the last tag is skipped, silently and correctly, not flagged.

WHY `git describe --tags --abbrev=0` AND NOT `git tag -l`
--------------------------------------------------------------
`scripts/doc-lifecycle-check.py`'s invariant 4 and 10 only need to know WHICH tags exist, so a set
from `git tag -l` is enough. This script needs the ONE tag to diff against, the same tag the
hygiene-sweep recipe names `LAST_TAG`, so it uses the same command the recipe uses:
`git describe --tags --abbrev=0`. An empty result (no tag reachable from HEAD at all) is BROKEN,
for the same reason `doc-lifecycle-check.py` treats an empty `git tag -l` as BROKEN: a shallow or
tag-less checkout produces the same empty result as a repository that has genuinely never tagged a
release, and this gate cannot tell the two apart, so it refuses to report CLEAN by construction.

WHY EVERY SUBPROCESS BOUNDARY PINS encoding="utf-8"
-----------------------------------------------------
Same failure this repository has already been bitten by twice (`scripts/check-dashes.py`,
`scripts/doc-lifecycle-check.py`): Python's subprocess text mode defaults to the locale encoding,
cp1252 on this maintainer's machine, which can silently fail to decode what git actually wrote.
Every subprocess call below pins `encoding="utf-8"` explicitly.

WHY THE SELF-TEST BUILDS REAL GIT REPOSITORIES
-------------------------------------------------
Every other fixture-based gate in this repository builds a plain directory tree, because none of
them need git history. This script's entire subject IS git history (a tag, a diff since that tag,
a file's content at that tag), so its self-test runs real `git init` / `commit` / `tag` sequences
inside `tempfile.TemporaryDirectory()`, with the identity pinned by `-c user.name=` / `-c
user.email=` on every invocation so it never depends on the machine's own git config. Each fixture
is torn down with `ignore_cleanup_errors=True`, because Windows can raise `PermissionError` when a
`TemporaryDirectory` tries to delete `.git`'s read-only pack files, which is a cleanup artifact and
not a self-test failure.

WHAT THIS SCRIPT DELIBERATELY DOES NOT CHECK
------------------------------------------------
Whether the version written in `README.md`, `docs/status-skills.md`, or a usage README agrees with
`skills/<name>/SKILL.md` (`scripts/version-parity-check.py`'s job). Whether a release plan's
bookkeeping fields agree with its effort folders (`scripts/doc-lifecycle-check.py`'s job). Whether
an unbumped version is semantically the right increment. And any skill whose folder has no diff at
all since the latest tag, which is presumed correctly unbumped.
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile

LIBRARY_REL = "library.json"
SKILLS_REL = "skills"

SEMVER = re.compile(r'^\d+\.\d+\.\d+$')
METADATA_VERSION_LINE = re.compile(r'^\s+version:\s*"?(\d+\.\d+\.\d+)"?\s*$')
METADATA_BLOCK = re.compile(r'^metadata:\s*$')

GIT_IDENTITY = ["-c", "user.name=Skill Drift Fixture", "-c", "user.email=fixture@example.invalid"]


class Broken(Exception):
    """Raised for anything that means this detector cannot prove what it claims to prove. Always
    becomes exit 2, never exit 1."""


def read_text(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        raise Broken("expected file is missing: %s" % path)
    except UnicodeDecodeError as exc:
        raise Broken("%s is not valid UTF-8: %s" % (path, exc))


def parse_skill_version(text, where):
    """Read `metadata.version` out of a SKILL.md's frontmatter block, the same shape
    `scripts/version-parity-check.py`'s `declared_skill_versions()` reads. Deliberately read from
    inside the `metadata:` block specifically, not the first `version:`-shaped line anywhere in the
    file, for the same reason that function gives: a body section that happens to contain the word
    `version:` before the metadata block would otherwise give the wrong answer silently."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise Broken("%s does not open with a frontmatter fence" % where)
    in_metadata = False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if METADATA_BLOCK.match(line):
            in_metadata = True
            continue
        if in_metadata:
            if line and not line[0].isspace():
                in_metadata = False
                continue
            m = METADATA_VERSION_LINE.match(line)
            if m:
                return m.group(1)
    raise Broken("%s has no metadata.version line this script can read" % where)


def parse_library_version(text, where):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Broken("%s is not valid JSON: %s" % (where, exc))
    version = data.get("version")
    if not isinstance(version, str) or not SEMVER.match(version):
        raise Broken("%s has no usable top-level 'version' string, got %r" % (where, version))
    return version


def _run_git(repo_root, *args):
    try:
        return subprocess.run(["git"] + list(args), cwd=repo_root, capture_output=True,
                              text=True, encoding="utf-8")
    except OSError as exc:
        raise Broken("could not invoke git: %s" % exc)


def get_latest_tag(repo_root):
    """The one tag this gate diffs against, read the same way the hygiene-sweep Check 4 recipe
    reads it (`LAST_TAG=$(git describe --tags --abbrev=0 ...)`), not the unordered set
    `scripts/doc-lifecycle-check.py` reads via `git tag -l` for existence checks."""
    proc = _run_git(repo_root, "describe", "--tags", "--abbrev=0")
    if proc.returncode != 0 or not proc.stdout.strip():
        raise Broken(
            "git describe --tags --abbrev=0 found no tag reachable from HEAD. Likely cause: a "
            "shallow or tag-less checkout (this job needs fetch-depth: 0), or a repository that "
            "has genuinely never tagged a release. Either way this gate has nothing to diff "
            "against and cannot run, so it refuses to report CLEAN.")
    return proc.stdout.strip()


def changed_paths_since(repo_root, tag):
    proc = _run_git(repo_root, "diff", "--name-only", "%s..HEAD" % tag, "--", SKILLS_REL)
    if proc.returncode != 0:
        raise Broken("git diff --name-only %s..HEAD -- %s failed: %s"
                     % (tag, SKILLS_REL, proc.stderr.strip()))
    return [p.strip() for p in proc.stdout.split("\n") if p.strip()]


def file_at_tag(repo_root, tag, rel_path):
    """The file's text content at `tag`, or None if it did not exist there (a new file, or a new
    skill folder, added after that tag)."""
    proc = _run_git(repo_root, "show", "%s:%s" % (tag, rel_path.replace(os.sep, "/")))
    if proc.returncode != 0:
        return None
    return proc.stdout


class CheckResult:
    def __init__(self, tag, head_lib_version, tag_lib_version, findings):
        self.tag = tag
        self.head_lib_version = head_lib_version
        self.tag_lib_version = tag_lib_version
        self.findings = findings
        self.mode = None  # set by decide_mode() via run_check()


def decide_mode(head_lib_version, tag_lib_version, strict):
    """Pure decision logic, no I/O, so the self-test can drive all branches directly. 'advisory'
    only when library.json's plugin version is unchanged since the latest tag AND --strict was not
    passed; 'enforced' otherwise."""
    if strict:
        return "enforced"
    return "advisory" if head_lib_version == tag_lib_version else "enforced"


def evaluate(repo_root):
    """The one top-level entry point both the real run and the self-test drive. Raises Broken for
    anything this detector cannot prove; otherwise returns a CheckResult with `mode` still unset."""
    skills_dir = os.path.join(repo_root, SKILLS_REL)
    if not os.path.isdir(skills_dir):
        raise Broken("no skills/ directory under %s; nothing for this gate to check" % repo_root)

    names = sorted(n for n in os.listdir(skills_dir)
                   if os.path.isdir(os.path.join(skills_dir, n)))
    if not names:
        raise Broken("skills/ contains no skill directories; nothing for this gate to check")

    tag = get_latest_tag(repo_root)
    changed = changed_paths_since(repo_root, tag)
    changed_by_skill = {}
    for p in changed:
        parts = p.split("/")
        if len(parts) >= 2 and parts[0] == SKILLS_REL:
            changed_by_skill.setdefault(parts[1], []).append(p)

    findings = []
    for name in names:
        skill_file = os.path.join(skills_dir, name, "SKILL.md")
        if not os.path.isfile(skill_file):
            raise Broken("skills/%s has no SKILL.md; this gate cannot read its version" % name)
        history_file = os.path.join(skills_dir, name, "HISTORY.md")
        if not os.path.isfile(history_file):
            raise Broken("skills/%s has no HISTORY.md; this gate cannot check for a version row" % name)

        history_rel = "%s/%s/HISTORY.md" % (SKILLS_REL, name)
        own_changes = [p for p in changed_by_skill.get(name, []) if p != history_rel]
        if not own_changes:
            continue  # nothing but (at most) HISTORY.md changed, or nothing changed at all

        head_version = parse_skill_version(read_text(skill_file), skill_file)

        tag_rel = "%s/%s/SKILL.md" % (SKILLS_REL, name)
        tag_text = file_at_tag(repo_root, tag, tag_rel)
        if tag_text is None:
            continue  # new skill since the tag: no prior version to have bumped away from
        tag_version = parse_skill_version(tag_text, "%s at %s" % (tag_rel, tag))

        if head_version == tag_version:
            findings.append(
                "skills/%s changed since %s (e.g. %s) but metadata.version is still %s"
                % (name, tag, own_changes[0], head_version))

        history_text = read_text(history_file)
        if re.search(r'^\|\s*%s\s*\|' % re.escape(head_version), history_text, re.MULTILINE) is None:
            findings.append(
                "skills/%s/HISTORY.md has no row for version %s, its metadata.version as of this change"
                % (name, head_version))

    lib_path = os.path.join(repo_root, LIBRARY_REL)
    head_lib_version = parse_library_version(read_text(lib_path), LIBRARY_REL)
    tag_lib_text = file_at_tag(repo_root, tag, LIBRARY_REL)
    if tag_lib_text is None:
        raise Broken("%s could not be read at %s; cannot establish the advisory/enforced mode"
                     % (LIBRARY_REL, tag))
    tag_lib_version = parse_library_version(tag_lib_text, "%s at %s" % (LIBRARY_REL, tag))

    return CheckResult(tag, head_lib_version, tag_lib_version, findings)


def run_check(repo_root, strict):
    result = evaluate(repo_root)
    result.mode = decide_mode(result.head_lib_version, result.tag_lib_version, strict)
    return result


# ---------------------------------------------------------------------------
# Self-test. Builds real throwaway git repositories, because this script's
# entire subject is git history. See "WHY THE SELF-TEST BUILDS REAL GIT
# REPOSITORIES" in the module docstring.
# ---------------------------------------------------------------------------

def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _git(cwd, *args):
    return subprocess.run(["git"] + GIT_IDENTITY + list(args), cwd=cwd, capture_output=True,
                          text=True, encoding="utf-8")


def _git_ok(cwd, *args):
    proc = _git(cwd, *args)
    if proc.returncode != 0:
        raise AssertionError("git %s failed in %s: %s" % (" ".join(args), cwd, proc.stderr))
    return proc.stdout


def _write_skill(tmp, name, version):
    _write(os.path.join(tmp, "skills", name, "SKILL.md"),
          "---\nname: %s\ndescription: \"test skill %s\"\nlicense: MIT\nmetadata:\n"
          "  version: \"%s\"\n  updated: 2026-01-01\n---\n\n# %s\n" % (name, name, version, name))


def _write_history(tmp, name, rows):
    lines = ["# History - %s" % name, "", "| Version | Date | Release | Type | Summary |",
             "|---|---|---|---|---|"]
    for v in rows:
        lines.append("| %s | 2026-01-01 | v1.0.0 | added | test row |" % v)
    _write(os.path.join(tmp, "skills", name, "HISTORY.md"), "\n".join(lines) + "\n")


def _write_library(tmp, version):
    _write(os.path.join(tmp, LIBRARY_REL), json.dumps({"name": "fixture", "version": version}))


def _init_and_tag(tmp, tag):
    _git_ok(tmp, "init", "-q", "-b", "main")
    _git_ok(tmp, "add", "-A")
    _git_ok(tmp, "commit", "-q", "-m", "initial")
    _git_ok(tmp, "tag", tag)


def _self_test_decide_mode(failures):
    """Invariant mode switch as a pure function, no git, no filesystem, driven on all four branches."""
    if decide_mode("0.8.0", "0.8.0", strict=False) != "advisory":
        failures.append("decide_mode: equal versions without --strict must be 'advisory'")
    if decide_mode("0.9.0", "0.8.0", strict=False) != "enforced":
        failures.append("decide_mode: differing versions must be 'enforced'")
    if decide_mode("0.8.0", "0.8.0", strict=True) != "enforced":
        failures.append("decide_mode: --strict must force 'enforced' even when versions are equal")
    if decide_mode("0.9.0", "0.8.0", strict=True) != "enforced":
        failures.append("decide_mode: --strict must force 'enforced' when versions already differ")


def _self_test_real_repo_scenarios(failures):
    """One fixture repository covering every rule and every anti-canary at once: an unbumped
    version, a bumped version with a missing HISTORY.md row, a correctly bumped skill, an untouched
    skill, and a skill whose only change is its own HISTORY.md (excluded, so still clean). Then the
    same repository proves the advisory/enforced mode switch by moving library.json's version."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            _write_skill(tmp, "plab-a", "1.0.0"); _write_history(tmp, "plab-a", ["1.0.0"])
            _write_skill(tmp, "plab-b", "1.0.0"); _write_history(tmp, "plab-b", ["1.0.0"])
            _write_skill(tmp, "plab-c", "1.0.0"); _write_history(tmp, "plab-c", ["1.0.0"])
            _write_skill(tmp, "plab-d", "1.0.0"); _write_history(tmp, "plab-d", ["1.0.0"])
            _write_skill(tmp, "plab-e", "1.0.0"); _write_history(tmp, "plab-e", ["1.0.0"])
            _write_library(tmp, "1.0.0")
            _init_and_tag(tmp, "v1.0.0")

            # plab-a: a reference file changes, version NOT bumped. Canary.
            _write(os.path.join(tmp, "skills", "plab-a", "references", "new.md"), "note\n")
            # plab-b: a reference file changes, version IS bumped, but HISTORY.md keeps only the
            # old row. Canary.
            _write(os.path.join(tmp, "skills", "plab-b", "references", "new.md"), "note\n")
            _write_skill(tmp, "plab-b", "1.1.0")
            # plab-c: version bumped AND a HISTORY.md row added. Anti-canary: must stay clean.
            _write(os.path.join(tmp, "skills", "plab-c", "references", "new.md"), "note\n")
            _write_skill(tmp, "plab-c", "1.1.0")
            _write_history(tmp, "plab-c", ["1.0.0", "1.1.0"])
            # plab-d: untouched since the tag. Anti-canary.
            # plab-e: only HISTORY.md changes. Anti-canary: the excluded file.
            _write_history(tmp, "plab-e", ["1.0.0", "1.0.0-note"])
            _git_ok(tmp, "add", "-A")
            _git_ok(tmp, "commit", "-q", "-m", "second commit, no new tag")
        except AssertionError as exc:
            failures.append("real-repo fixture setup failed: %s" % exc)
            return

        try:
            result = run_check(tmp, strict=False)
        except Broken as exc:
            failures.append("real-repo advisory-mode run must not be BROKEN, got %r" % exc)
            return

        if result.mode != "advisory":
            failures.append("expected advisory mode (library.json unchanged since v1.0.0), got %r"
                            % result.mode)

        a_hits = [f for f in result.findings if "plab-a" in f and "still 1.0.0" in f]
        b_hits = [f for f in result.findings if "plab-b" in f and "no row for version 1.1.0" in f]
        c_hits = [f for f in result.findings if "plab-c" in f]
        d_hits = [f for f in result.findings if "plab-d" in f]
        e_hits = [f for f in result.findings if "plab-e" in f]

        if len(a_hits) != 1:
            failures.append("expected exactly one unbumped-version finding for plab-a, got %r" % result.findings)
        if len(b_hits) != 1:
            failures.append("expected exactly one missing-HISTORY.md-row finding for plab-b, got %r" % result.findings)
        if c_hits:
            failures.append("plab-c bumped its version and added a HISTORY.md row; must be clean (anti-canary), got %r" % c_hits)
        if d_hits:
            failures.append("plab-d has no diff since the tag; must be clean (anti-canary), got %r" % d_hits)
        if e_hits:
            failures.append("plab-e's only change since the tag is its own HISTORY.md, which is excluded; must be clean (anti-canary), got %r" % e_hits)
        if len(result.findings) != 2:
            failures.append("expected exactly 2 findings total (plab-a, plab-b), got %r" % result.findings)

        # Now bump the plugin version: a release is in progress, so the SAME findings must switch
        # from advisory to enforced.
        _write_library(tmp, "2.0.0")
        _git_ok(tmp, "add", "-A")
        _git_ok(tmp, "commit", "-q", "-m", "bump plugin version")
        try:
            result2 = run_check(tmp, strict=False)
        except Broken as exc:
            failures.append("real-repo enforced-mode run must not be BROKEN, got %r" % exc)
            return
        if result2.mode != "enforced":
            failures.append("expected enforced mode once library.json's version moved away from "
                            "its value at v1.0.0, got %r" % result2.mode)
        if len(result2.findings) != 2:
            failures.append("bumping library.json must not change WHICH skills are findings, got %r"
                            % result2.findings)

        # --strict forces enforced even back when the comparison alone said advisory would apply.
        result3 = CheckResult(result.tag, result.head_lib_version, result.tag_lib_version, result.findings)
        result3.mode = decide_mode(result.head_lib_version, result.tag_lib_version, strict=True)
        if result3.mode != "enforced":
            failures.append("--strict must force enforced mode even when the plugin version is "
                            "unchanged, got %r" % result3.mode)


def _self_test_new_skill_since_tag_is_skipped(failures):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            _write_skill(tmp, "plab-a", "1.0.0"); _write_history(tmp, "plab-a", ["1.0.0"])
            _write_library(tmp, "1.0.0")
            _init_and_tag(tmp, "v1.0.0")

            _write_skill(tmp, "plab-z", "1.0.0"); _write_history(tmp, "plab-z", ["1.0.0"])
            _git_ok(tmp, "add", "-A")
            _git_ok(tmp, "commit", "-q", "-m", "add a brand-new skill")
        except AssertionError as exc:
            failures.append("new-skill fixture setup failed: %s" % exc)
            return

        try:
            result = run_check(tmp, strict=False)
        except Broken as exc:
            failures.append("a brand-new skill since the tag must not be BROKEN, got %r" % exc)
            return
        z_hits = [f for f in result.findings if "plab-z" in f]
        if z_hits:
            failures.append("plab-z did not exist at the tag and must be skipped entirely "
                            "(anti-canary: no prior version to have bumped away from), got %r" % z_hits)


def _self_test_no_tags_is_broken(failures):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            _write_skill(tmp, "plab-a", "1.0.0"); _write_history(tmp, "plab-a", ["1.0.0"])
            _write_library(tmp, "1.0.0")
            _git_ok(tmp, "init", "-q", "-b", "main")
            _git_ok(tmp, "add", "-A")
            _git_ok(tmp, "commit", "-q", "-m", "initial, deliberately no tag")
        except AssertionError as exc:
            failures.append("no-tags fixture setup failed: %s" % exc)
            return
        try:
            run_check(tmp, strict=False)
        except Broken:
            pass
        else:
            failures.append("a repository with no tag reachable from HEAD must raise Broken, not pass silently")


def _self_test_missing_skill_md_is_broken(failures):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            os.makedirs(os.path.join(tmp, "skills", "plab-broken"), exist_ok=True)
            _write(os.path.join(tmp, "skills", "plab-broken", "README.md"), "no SKILL.md here\n")
            _write_library(tmp, "1.0.0")
            _init_and_tag(tmp, "v1.0.0")
        except AssertionError as exc:
            failures.append("missing-SKILL.md fixture setup failed: %s" % exc)
            return
        try:
            run_check(tmp, strict=False)
        except Broken:
            pass
        else:
            failures.append("a skills/ directory with no SKILL.md must raise Broken, not pass silently")


def _self_test_missing_history_md_is_broken(failures):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            _write_skill(tmp, "plab-a", "1.0.0")  # no HISTORY.md written at all
            _write_library(tmp, "1.0.0")
            _init_and_tag(tmp, "v1.0.0")
        except AssertionError as exc:
            failures.append("missing-HISTORY.md fixture setup failed: %s" % exc)
            return
        try:
            run_check(tmp, strict=False)
        except Broken:
            pass
        else:
            failures.append("a skills/ directory with no HISTORY.md must raise Broken, not pass silently")


def _self_test_unparseable_version_is_broken(failures):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        try:
            _write_skill(tmp, "plab-a", "1.0.0"); _write_history(tmp, "plab-a", ["1.0.0"])
            _write_library(tmp, "1.0.0")
            _init_and_tag(tmp, "v1.0.0")

            _write(os.path.join(tmp, "skills", "plab-a", "SKILL.md"),
                  "---\nname: plab-a\nmetadata:\n  version: not-a-semver\n  updated: 2026-01-01\n"
                  "---\n\n# plab-a\n")
            _git_ok(tmp, "add", "-A")
            _git_ok(tmp, "commit", "-q", "-m", "write an unparseable version")
        except AssertionError as exc:
            failures.append("unparseable-version fixture setup failed: %s" % exc)
            return
        try:
            run_check(tmp, strict=False)
        except Broken:
            pass
        else:
            failures.append("an unparseable metadata.version must raise Broken, not pass silently")


def self_test():
    failures = []
    _self_test_decide_mode(failures)
    _self_test_real_repo_scenarios(failures)
    _self_test_new_skill_since_tag_is_skipped(failures)
    _self_test_no_tags_is_broken(failures)
    _self_test_missing_skill_md_is_broken(failures)
    _self_test_missing_history_md_is_broken(failures)
    _self_test_unparseable_version_is_broken(failures)
    if failures:
        print("BROKEN: gate self-test failed, the detector is not trustworthy.", file=sys.stderr)
        for f in failures:
            print("  " + f, file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        return False
    print("gate self-test: PASS (the advisory/enforced mode switch proved on all four branches, one "
          "real-git fixture proving an unbumped version, a bumped version with a missing HISTORY.md "
          "row, a correctly bumped skill, an untouched skill and a HISTORY.md-only change as "
          "anti-canaries, a new-skill-since-the-tag skip, and four BROKEN cases: no tag at all, no "
          "SKILL.md, no HISTORY.md, and an unparseable version)")
    return True


def main():
    ap = argparse.ArgumentParser(
        description="Skill version-bump gate: a skill changed since the latest tag must bump its "
                    "own version and record it in HISTORY.md.")
    ap.add_argument("--repo-root", default=os.getcwd(),
                    help="repository root to scan (default: cwd)")
    ap.add_argument("--self-test-only", action="store_true",
                    help="prove the detector and exit, scanning nothing")
    ap.add_argument("--strict", action="store_true",
                    help="force ENFORCED mode (exit 1 on any finding) even when library.json's "
                         "version has not moved since the latest tag")
    args = ap.parse_args()

    try:
        if not self_test():
            sys.exit(2)
        if args.self_test_only:
            sys.exit(0)

        result = run_check(args.repo_root, args.strict)

        relation = "equals" if result.head_lib_version == result.tag_lib_version else "differs from"
        evidence = ("library.json's version %s %s its value %s at %s"
                   % (result.head_lib_version, relation, result.tag_lib_version, result.tag))

        if result.mode == "advisory":
            print("ADVISORY MODE: %s (no release in progress). Findings below are reported, not "
                  "enforced; this repository deliberately lets effort pull requests land with an "
                  "unbumped skill and does all version bookkeeping in one closing release PR. Pass "
                  "--strict to enforce them anyway." % evidence)
        else:
            print("ENFORCED MODE: %s. Findings below block." % evidence)

        if result.findings:
            prefix = "ADVISORY: " if result.mode == "advisory" else ""
            for f in result.findings:
                print(prefix + f)
            if result.mode == "advisory":
                print("\nADVISORY: %d skill(s) changed since %s without a matching version bump "
                      "or HISTORY.md row. Not enforced; no release is in progress."
                      % (len(result.findings), result.tag))
                sys.exit(0)
            print("\nFINDINGS: %d skill(s) changed since %s without a matching version bump or "
                  "HISTORY.md row, and a release is in progress." % (len(result.findings), result.tag))
            sys.exit(1)

        print("CLEAN: canary proved, no skill changed since %s without a matching version bump "
              "and HISTORY.md row." % result.tag)
        sys.exit(0)
    except SystemExit:
        raise
    except Broken as exc:
        print("BROKEN: %s" % exc, file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:                                     # noqa: BLE001
        print("BROKEN: unanticipated %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        print("\nExiting 2. Do NOT read this as a clean tree.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
