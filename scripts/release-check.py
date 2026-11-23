#!/usr/bin/env python3
"""
Release checks for a pull request (RL-01, release on merge): the rules that must hold BEFORE a pull request that carries a new version is merged.

USAGE
-----
  python3 scripts/release-check.py                 run the self-test, then the checks on this repository
  python3 scripts/release-check.py --self-test     run the self-test only
  python3 scripts/release-check.py --repo <path>   check another checkout

A pull request reaches the script through the environment, never through the command line, because a title is attacker-shaped text:

  PR_TITLE   the pull request title        (absent on a push event)
  PR_BODY    the pull request body         (may be empty)
  BASE_SHA   the pull request's base commit (absent on a push event)
  HEAD_SHA   the pull request's head commit (lets the check drop the merge preview from the titles it reads)

EXIT-CODE CONTRACT
------------------
  0  CLEAN    self-test passed AND (the repository has not opted in, OR every rule held)
  1  FINDINGS self-test passed AND at least one rule failed
  2  BROKEN   the self-test failed, a file or a git answer could not be read, or any other exception reached the top level

NEVER INTERPRET 2 AS CLEAN. `scripts/version-parity-check.py`, `scripts/doc-lifecycle-check.py` and `scripts/run-tests.py` carry the same contract.

OPT-IN (AC-1)
-------------
A repository opts in by carrying `RELEASING.md` AND `.github/release-on-merge.json`. When either is absent the script prints `NOT OPTED IN`, names which file is missing so that a half-done opt-in stays visible, and exits 0 without reading anything else.

THE RULES
---------
  Configuration (AC-2)  `surfaces` is a non-empty list, `test_command` a non-empty string, and `plugin` is `{"repin": true|false, "marketplace": "<owner/name>"}` with `marketplace` required when `repin` is true.
  Bump                  `library.json`'s version against the version of the latest version tag. Equal means no bump, and the size, CHANGELOG and `Unreleased` rules are skipped. A version below the tag is a finding.
  Size (AC-4)           The version must be the one the largest change since the tag calls for, reading the first-parent titles since the tag plus the pull request's own title. `!` or a `BREAKING CHANGE` footer is a major; `feat` a minor; `fix`, `perf` and `revert` a patch; `docs`, `chore`, `refactor`, `test`, `ci`, `build` and `style` carry no size; a title with no conventional type counts as a patch and is named. Below 1.0.0 a major raises the minor. With only sizeless types and a bump the expected size is a patch.
  CHANGELOG (AC-5)      `scripts/release-notes-from-changelog.py <version>` must find a section. Its exit 1 is this rule's finding; its exit 2 is this script's exit 2.
  Unreleased (AC-17)    With a bump, no `skills/*/HISTORY.md` row may read `Unreleased` in its Release column.
  Eval line (AC-6)      A skill whose `description` or whose `SKILL.md` body changed between the merge base and the head needs a `Behaviour evals: N/M passed` line in the pull request body. A change confined to `metadata` does not. A new `SKILL.md` counts as changed. A deleted one does not.

Without PR_TITLE the size rule is skipped, and without BASE_SHA the eval rule is skipped, each with a line saying so, so the push-to-main run stays meaningful and quiet. The configuration, CHANGELOG and `Unreleased` rules still run.

HOW THE TITLES ARE READ
-----------------------
This repository merges with merge commits, and GitHub puts the pull request title on the first line of a merge commit's body. For each first-parent commit in `<latest tag>..HEAD` the title is that first body line when the commit is a merge and has a body, and the subject otherwise. In CI the checkout is the merge preview: HEAD is a merge whose second parent is HEAD_SHA, and that one commit is excluded, because PR_TITLE already speaks for it. No API call is needed.

THE LATEST TAG
--------------
`git describe --tags --abbrev=0 --match 'v[0-9]*.[0-9]*'`, never a bare `git describe --tags`. The merge check writes `pre-merge/*` backup tags nearer HEAD than the last release, and a floating tag such as `v1` is moved on each release; the glob drops both. `scripts/skill-drift-check.py` records the failure this prevents.

WHY THE SELF-TEST BUILDS GIT REPOSITORIES
-----------------------------------------
Five of the rules read commits. Each is proved on a throwaway repository with a pinned identity, pinned dates and the machine's git configuration switched off, and the rule functions take the pull request as arguments, never from the environment, so the real PR_TITLE of the pull request now running cannot leak into a fixture.

ENCODING IS PINNED. Every subprocess call and every read passes encoding="utf-8"; see `scripts/check-dashes.py` for why.
"""

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NOTES_SCRIPT = HERE / "release-notes-from-changelog.py"

RELEASING = "RELEASING.md"
CONFIG = ".github/release-on-merge.json"
TAG_GLOB = "v[0-9]*.[0-9]*"
TAG_SHAPE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
EVAL_LINE = re.compile(r"^Behaviour evals: \d+/\d+ passed", re.MULTILINE)
CONVENTIONAL = re.compile(r"^(?P<type>[A-Za-z]+)(?:\([^)]*\))?(?P<bang>!)?:\s")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE:", re.MULTILINE)
SKILL_FILE = re.compile(r"^skills/[^/]+/SKILL\.md$")
MARKETPLACE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

NONE, PATCH, MINOR, MAJOR = 0, 1, 2, 3
LEVEL_NAME = {NONE: "no size", PATCH: "a patch", MINOR: "a minor", MAJOR: "a major"}
SIZES = {
    "feat": MINOR,
    "fix": PATCH, "perf": PATCH, "revert": PATCH,
    "docs": NONE, "chore": NONE, "refactor": NONE, "test": NONE, "ci": NONE, "build": NONE, "style": NONE,
}


class Broken(Exception):
    """The input cannot be read or run faithfully. Exit 2, never clean."""


# ------------------------------------------------------------------------ git

_GIT_STRIP = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR", "GIT_PREFIX")


def git(repo, *args, check=True, env=None):
    """Run git in `repo` and return the finished process. A git that will not start, or a failure when `check` is set, is BROKEN."""
    full = {k: v for k, v in os.environ.items() if k not in _GIT_STRIP}
    if env:
        full.update(env)
    try:
        proc = subprocess.run(["git"] + list(args), cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8", errors="replace", env=full)
    except OSError as exc:
        raise Broken("could not run git: %s" % exc)
    if check and proc.returncode != 0:
        raise Broken("git %s failed (exit %d): %s" % (" ".join(args), proc.returncode, proc.stderr.strip()))
    return proc


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")
    except FileNotFoundError:
        raise Broken("expected file is missing: %s" % path)
    except (OSError, UnicodeDecodeError) as exc:
        raise Broken("could not read %s: %s" % (path, exc))


def parse_version(text):
    m = SEMVER.match(text or "")
    return tuple(int(x) for x in m.groups()) if m else None


def fmt(version):
    return "%d.%d.%d" % version


def library_version(repo):
    path = Path(repo) / "library.json"
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Broken("%s is not valid JSON: %s" % (path, exc))
    version = parse_version(data.get("version") if isinstance(data, dict) else None)
    if version is None:
        raise Broken("%s has no top-level 'version' of the form X.Y.Z" % path)
    return version


def latest_tag(repo):
    """The nearest version tag reachable from HEAD, as (name, version tuple)."""
    proc = git(repo, "describe", "--tags", "--abbrev=0", "--match", TAG_GLOB, "HEAD", check=False)
    name = proc.stdout.strip()
    if proc.returncode != 0 or not name:
        raise Broken("git describe --tags --abbrev=0 --match '%s' found no version tag reachable from HEAD. "
                     "A shallow or tag-less checkout (this needs fetch-depth: 0) looks the same as a repository "
                     "that has never released, so the check refuses to report CLEAN." % TAG_GLOB)
    m = TAG_SHAPE.match(name)
    if not m:
        raise Broken("the latest version tag %r is not of the form vX.Y.Z, so the bump cannot be measured" % name)
    return name, tuple(int(x) for x in m.groups())


def resolve_commit(repo, ref):
    proc = git(repo, "rev-parse", "--verify", "--quiet", ref + "^{commit}", check=False)
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else None


# --------------------------------------------------------------- the rules

def missing_opt_in(repo):
    return [rel for rel in (RELEASING, CONFIG) if not (Path(repo) / rel).is_file()]


def check_config(repo):
    """AC-2. Returns a list of findings, each naming the field that is missing or malformed."""
    findings = []
    try:
        cfg = json.loads(read_text(Path(repo) / CONFIG))
    except json.JSONDecodeError as exc:
        return ["%s is not valid JSON: %s" % (CONFIG, exc)]
    if not isinstance(cfg, dict):
        return ["%s must hold a JSON object" % CONFIG]
    surfaces = cfg.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        findings.append("%s: 'surfaces' must be a non-empty list" % CONFIG)
    command = cfg.get("test_command")
    if not isinstance(command, str) or not command.strip():
        findings.append("%s: 'test_command' must be a non-empty string" % CONFIG)
    plugin = cfg.get("plugin")
    if not isinstance(plugin, dict):
        findings.append("%s: 'plugin' must be an object with 'repin' and, when repin is true, 'marketplace'" % CONFIG)
    else:
        if not isinstance(plugin.get("repin"), bool):
            findings.append("%s: 'plugin.repin' must be true or false" % CONFIG)
        elif plugin["repin"]:
            marketplace = plugin.get("marketplace")
            if not isinstance(marketplace, str) or not MARKETPLACE.match(marketplace):
                findings.append("%s: 'plugin.marketplace' must be an owner/name repository when 'plugin.repin' is true" % CONFIG)
    return findings


def classify(title, body):
    """Return (level, named) for one change: its size, and whether its type was unrecognised."""
    breaking = bool(BREAKING_FOOTER.search(body or ""))
    m = CONVENTIONAL.match(title)
    named = False
    if m:
        if m.group("bang"):
            breaking = True
        level = SIZES.get(m.group("type").lower())
        if level is None:
            level, named = PATCH, True
    else:
        level, named = PATCH, True
    if breaking:
        level = MAJOR
    return level, named and not breaking


def expected_version(tag_version, level):
    major, minor, patch = tag_version
    if level == NONE:
        level = PATCH
    if level == MAJOR:
        return (major + 1, 0, 0) if major >= 1 else (0, minor + 1, 0)
    if level == MINOR:
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def preview_head(repo, head_sha):
    """HEAD's sha when HEAD is a merge preview of the pull request (second parent equals HEAD_SHA), else None."""
    if not head_sha:
        return None
    full = resolve_commit(repo, head_sha)
    if not full:
        return None
    parts = git(repo, "rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
    if len(parts) == 3 and parts[2] == full:
        return parts[0]
    return None


def titles_since(repo, tag, head_sha):
    """(title, body) for every first-parent commit in <tag>..HEAD, the merge preview excluded."""
    skip = preview_head(repo, head_sha)
    out = git(repo, "log", "--first-parent", "--format=%H%x1f%P%x1f%s%x1f%b%x1e", "%s..HEAD" % tag).stdout
    titles = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        fields = record.split("\x1f")
        if len(fields) != 4:
            raise Broken("could not read a commit record from git log: %r" % record[:80])
        sha, parents, subject, body = fields[0].strip(), fields[1].split(), fields[2], fields[3]
        if sha == skip:
            continue
        title = subject
        if len(parents) > 1:
            first = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
            title = first or subject
        titles.append((title, body))
    return titles


def check_size(repo, tag, tag_version, version, pr_title, pr_body, head_sha, lines):
    """AC-4. Returns a list of findings."""
    changes = titles_since(repo, tag, head_sha) + [(pr_title, pr_body or "")]
    best, driver = NONE, None
    for title, body in changes:
        level, named = classify(title, body)
        if named:
            lines.append('size: "%s" has no recognised conventional type and counts as a patch' % title[:80])
        if driver is None or level > best:
            best, driver = level, title
    want = expected_version(tag_version, best)
    lines.append('size: the largest change since %s is %s ("%s"), so the version should be %s'
                 % (tag, LEVEL_NAME[best], driver[:80], fmt(want)))
    if want != version:
        return ["library.json is %s but the changes since %s call for %s: expected %s"
                % (fmt(version), tag, LEVEL_NAME[best], fmt(want))]
    return []


def check_changelog(repo, version):
    """AC-5. The CHANGELOG section is found by the repository's own extractor."""
    try:
        proc = subprocess.run([sys.executable, str(NOTES_SCRIPT), fmt(version), "--root", str(repo)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace")
    except OSError as exc:
        raise Broken("could not run %s: %s" % (NOTES_SCRIPT, exc))
    if proc.returncode == 0:
        return []
    if proc.returncode == 1:
        first = proc.stderr.strip().splitlines()[0] if proc.stderr.strip() else "no section"
        return [first.replace("FINDING: ", "")]
    raise Broken("release-notes-from-changelog.py exited %d: %s" % (proc.returncode, proc.stderr.strip()))


def unreleased_rows(text):
    """(rows, saw_release_column): the first cell of every table row whose Release cell reads Unreleased."""
    column, rows, saw = None, [], False
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            column = None
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        lowered = [c.lower() for c in cells]
        if "release" in lowered:
            column, saw = lowered.index("release"), True
            continue
        if column is None or all(set(c) <= set("-: ") for c in cells):
            continue
        if len(cells) > column and cells[column].strip("`*_ ").lower() == "unreleased":
            rows.append(cells[0])
    return rows, saw


def check_unreleased(repo):
    """AC-17. Returns (findings, count of HISTORY.md files read)."""
    findings = []
    files = sorted((Path(repo) / "skills").glob("*/HISTORY.md"))
    for path in files:
        rel = path.relative_to(repo).as_posix()
        rows, saw = unreleased_rows(read_text(path))
        if not saw:
            raise Broken("%s has no table with a Release column, so the Unreleased rule cannot read it. "
                         "A silent pass here would let an unreleased row ship." % rel)
        for version in rows:
            findings.append("%s: the row for %s still reads Unreleased in its Release column" % (rel, version))
    return findings, len(files)


def skill_parts(text):
    """(description, body) of a SKILL.md: the description value through the next column-0 key, and the text after the frontmatter."""
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return "", text
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return "", text
    description, capture = [], False
    for ln in lines[1:end]:
        if capture:
            if ln.strip() == "" or ln[0] in " \t":
                description.append(ln.strip())
                continue
            capture = False
        m = re.match(r"^description:\s*(.*)$", ln)
        if m:
            capture, description = True, [m.group(1).strip()]
    return " ".join(description).strip(), "\n".join(lines[end + 1:])


def file_at(repo, rev, rel):
    proc = git(repo, "show", "%s:%s" % (rev, rel), check=False)
    return proc.stdout if proc.returncode == 0 else None


def check_eval(repo, base_sha, head_sha, pr_body):
    """AC-6. Returns a list of findings."""
    head = (resolve_commit(repo, head_sha) if head_sha else None) or "HEAD"
    base = git(repo, "merge-base", base_sha, head, check=False).stdout.strip()
    if not base:
        raise Broken("no merge base between BASE_SHA %s and %s; the checkout needs fetch-depth: 0" % (base_sha, head))
    names = git(repo, "diff", "--name-only", "--diff-filter=ACMR", base, head).stdout.split("\n")
    changed = []
    for rel in sorted(n.strip() for n in names if SKILL_FILE.match(n.strip())):
        new = file_at(repo, head, rel)
        old = file_at(repo, base, rel)
        if new is None:
            continue
        if old is None or skill_parts(old) != skill_parts(new):
            changed.append(rel)
    if changed and not EVAL_LINE.search((pr_body or "").replace("\r\n", "\n")):
        return ["%s: the description or the body changed, and the pull request body has no line "
                "'Behaviour evals: N/M passed'" % ", ".join(changed)]
    return []


def run_checks(repo, pr_title=None, pr_body="", base_sha=None, head_sha=None):
    """Every rule, against one repository. Takes the pull request as arguments. Returns (lines, findings)."""
    repo = Path(repo)
    missing = missing_opt_in(repo)
    if missing:
        return ["NOT OPTED IN: %s missing, so release-on-merge checks nothing here" % " and ".join(missing)], []
    lines, findings = ["opted in: %s and %s found" % (RELEASING, CONFIG)], []

    findings += check_config(repo)
    version = library_version(repo)
    tag, tag_version = latest_tag(repo)

    if version == tag_version:
        lines.append("version: library.json %s equals %s: no bump, so the size, CHANGELOG and Unreleased rules are skipped"
                     % (fmt(version), tag))
    elif version < tag_version:
        lines.append("version: library.json %s is below %s" % (fmt(version), tag))
        findings.append("library.json is %s, which is below the latest version tag %s" % (fmt(version), tag))
    else:
        lines.append("version: library.json %s is above %s: a bump" % (fmt(version), tag))
        if pr_title:
            findings += check_size(repo, tag, tag_version, version, pr_title, pr_body, head_sha, lines)
        else:
            lines.append("size: skipped, no PR_TITLE (a push event)")
        findings += check_changelog(repo, version)
        unreleased, count = check_unreleased(repo)
        findings += unreleased
        lines.append("unreleased: %d HISTORY.md file(s) read" % count)

    if base_sha:
        findings += check_eval(repo, base_sha, head_sha, pr_body)
    else:
        lines.append("eval line: skipped, no BASE_SHA (a push event)")
    return lines, findings


# ------------------------------------------------------------------ self-test

PIN = "2026-01-01T00:00:00+0000"
PIN_ENV = {"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid", "GIT_AUTHOR_DATE": PIN,
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid", "GIT_COMMITTER_DATE": PIN,
           "GIT_CONFIG_NOSYSTEM": "1"}

SKILL = ("---\nname: plab-a\ndescription: \"%s\"\nmetadata:\n  version: \"%s\"\n  updated: 2026-01-01\n---\n\n%s\n")
HISTORY_HEAD = "# History\n\n| Version | Date | Release | Type | Summary |\n|---|---|---|---|---|\n"
GOOD_CONFIG = {"surfaces": [{"path": "library.json", "json": "version"}], "test_command": "true",
               "plugin": {"repin": True, "marketplace": "o/m"}}


class Fixtures:
    """Throwaway repositories with a pinned identity and dates and the machine's git configuration switched off."""

    def __init__(self, tmp):
        self.tmp = Path(tmp)
        self.count = 0
        self.bases = {}
        self.gitconfig = self.tmp / "empty.gitconfig"
        self.gitconfig.write_text("", encoding="utf-8")
        self.env = dict(PIN_ENV, GIT_CONFIG_GLOBAL=str(self.gitconfig))

    def g(self, repo, *args):
        return git(repo, *args, env=self.env).stdout.strip()

    def write(self, repo, rel, text):
        path = Path(repo) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def commit(self, repo, message, body=None):
        self.g(repo, "add", "-A")
        args = ["-c", "commit.gpgsign=false", "commit", "-q", "-m", message]
        if body:
            args += ["-m", body]
        self.g(repo, *args)
        return self.g(repo, "rev-parse", "HEAD")

    def base(self, version, opted_in=True):
        """A repository at `version`, tagged v<version>, with one skill, a CHANGELOG, a HISTORY and (optionally) the opt-in files. An older tag v0.9.0 sits on the commit before."""
        self.count += 1
        repo = self.tmp / ("base-%d" % self.count)
        repo.mkdir()
        self.g(repo, "init", "-q")
        self.g(repo, "symbolic-ref", "HEAD", "refs/heads/main")
        self.write(repo, "README.md", "root\n")
        self.commit(repo, "chore: root")
        self.g(repo, "tag", "v0.9.0")
        self.write_state(repo, version, section=False, history=[("1.0.0", "v%s" % version)])
        self.write(repo, "CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n## [%s] - 2026-01-01\n\nOld.\n" % version)
        self.write(repo, "skills/plab-a/SKILL.md", SKILL % ("Does a thing", "1.0.0", "# A\n\nBody."))
        if opted_in:
            self.write(repo, RELEASING, "# Releasing\n")
            self.write(repo, CONFIG, json.dumps(GOOD_CONFIG))
        self.commit(repo, "chore: base")
        self.g(repo, "tag", "v%s" % version)
        return repo

    def fresh(self, version):
        """A private copy of the base repository for `version`, built once and copied after."""
        if version not in self.bases:
            self.bases[version] = self.base(version)
        return self.copy(self.bases[version])

    def copy(self, base):
        self.count += 1
        dest = self.tmp / ("work-%d" % self.count)
        shutil.copytree(str(base), str(dest))
        return dest

    def write_state(self, repo, version, section=True, history=None):
        """Working-tree state the rules read: the version, whether the CHANGELOG has the section, the HISTORY rows (version, release cell)."""
        self.write(repo, "library.json", json.dumps({"name": "t", "version": version}))
        path = Path(repo) / "CHANGELOG.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            text = re.sub(r"## \[%s\][^\n]*\n\n?[^\n]*\n\n?" % re.escape(version), "", text) if not section else text
            if section and ("## [%s]" % version) not in text:
                text = text.replace("## [Unreleased]\n", "## [Unreleased]\n\n## [%s] - 2026-01-02\n\nChange.\n" % version, 1)
            path.write_text(text, encoding="utf-8", newline="\n")
        if history is not None:
            rows = "".join("| %s | 2026-01-01 | %s | fixed | x |\n" % (v, r) for v, r in history)
            self.write(repo, "skills/plab-a/HISTORY.md", HISTORY_HEAD + rows)

    def merged(self, repo, title, body_extra=None, files=None):
        """Merge a branch into main with a GitHub-shaped merge commit whose body's first line is `title`."""
        self.count += 1
        branch = "p%d" % self.count
        self.g(repo, "checkout", "-q", "-b", branch)
        for rel, text in (files or {"notes/%d.txt" % self.count: "x\n"}).items():
            self.write(repo, rel, text)
        tip = self.commit(repo, "wip: branch commit %d" % self.count)
        self.g(repo, "checkout", "-q", "main")
        body = title if not body_extra else title + "\n\n" + body_extra
        self.g(repo, "-c", "commit.gpgsign=false", "merge", "--no-ff", "-q", "-m",
               "Merge pull request #%d from x/%s" % (self.count, branch), "-m", body, branch)
        return tip

    def preview(self, repo, files, body="Merge preview"):
        """A pull request branch off main merged into main the way CI's merge preview is. Returns (base sha, head sha)."""
        self.count += 1
        base_sha = self.g(repo, "rev-parse", "main")
        branch = "pr%d" % self.count
        self.g(repo, "checkout", "-q", "-b", branch)
        for rel, text in files.items():
            self.write(repo, rel, text)
        head = self.commit(repo, "wip: the pull request's own commit")
        self.g(repo, "checkout", "-q", "main")
        self.g(repo, "-c", "commit.gpgsign=false", "merge", "--no-ff", "-q", "-m", "Merge %s into main" % branch,
               "-m", body, branch)
        return base_sha, head


def _rmtree(path):
    def retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)


def self_test():
    """Return a list of failures; empty means every rule was proved to pass and to fail."""
    fails = []
    tmp = tempfile.mkdtemp(prefix="release-check-")
    try:
        _self_test(Fixtures(tmp), fails)
    except Broken as exc:
        fails.append("fixture could not be built: %s" % exc)
    finally:
        _rmtree(tmp)
    return fails


def _self_test(fx, fails):
    def expect(label, result, want_clean=None, has=None, lacks=None, line=None):
        lines, findings = result
        joined = "\n".join(findings)
        if want_clean is True and findings:
            fails.append("%s: expected no finding, got %r" % (label, findings))
        if want_clean is False and not findings:
            fails.append("%s: expected a finding, got none (lines %r)" % (label, lines))
        if has and has not in joined:
            fails.append("%s: expected a finding naming %r, got %r" % (label, has, findings))
        if lacks and lacks in joined:
            fails.append("%s: finding must not name %r, got %r" % (label, lacks, findings))
        if line and not any(line in ln for ln in lines):
            fails.append("%s: expected an output line containing %r, got %r" % (label, line, lines))

    def broken(label, func):
        try:
            func()
        except Broken:
            return
        fails.append("%s: expected BROKEN (exit 2), the rule went quiet instead" % label)

    # AC-1: not opted in. A plain folder, not a git repository: nothing else may be read.
    for present, label in (((), "neither file"), ((CONFIG,), "only the configuration"), ((RELEASING,), "only RELEASING.md")):
        bare = Path(fx.tmp) / ("bare-%s" % label.replace(" ", "-"))
        bare.mkdir()
        for rel in present:
            fx.write(bare, rel, "{}" if rel == CONFIG else "x")
        lines, findings = run_checks(bare, pr_title="fix: x", base_sha="deadbeef")
        if findings or not any("NOT OPTED IN" in ln for ln in lines):
            fails.append("AC-1 (%s): expected NOT OPTED IN and no finding, got %r %r" % (label, lines, findings))
        absent = [rel for rel in (RELEASING, CONFIG) if rel not in present]
        if not all(any(rel in ln for ln in lines) for rel in absent):
            fails.append("AC-1 (%s): the output must name the missing file(s) %r, got %r" % (label, absent, lines))

    # AC-2: the configuration, field by field.
    def with_cfg(cfg):
        d = Path(fx.tmp) / ("cfg-%d" % fx.count)
        fx.count += 1
        d.mkdir()
        fx.write(d, CONFIG, cfg if isinstance(cfg, str) else json.dumps(cfg))
        return check_config(d)

    def cfg_without(key, value="__drop__"):
        cfg = json.loads(json.dumps(GOOD_CONFIG))
        if value == "__drop__":
            del cfg[key]
        else:
            cfg[key] = value
        return cfg

    if with_cfg(GOOD_CONFIG):
        fails.append("AC-2: a complete configuration must pass, got %r" % with_cfg(GOOD_CONFIG))
    if with_cfg({"surfaces": [{"path": "library.json", "json": "version"}], "test_command": "true",
                 "plugin": {"repin": False}}):
        fails.append("AC-2: repin false needs no marketplace")
    for label, cfg, field in (
        ("surfaces missing", cfg_without("surfaces"), "'surfaces' must"),
        ("surfaces empty", cfg_without("surfaces", []), "'surfaces' must"),
        ("test_command missing", cfg_without("test_command"), "'test_command' must"),
        ("test_command blank", cfg_without("test_command", "  "), "'test_command' must"),
        ("plugin missing", cfg_without("plugin"), "'plugin' must"),
        ("repin not a boolean", cfg_without("plugin", {"repin": "yes", "marketplace": "o/m"}), "'plugin.repin' must be true or false"),
        ("repin true without a marketplace", cfg_without("plugin", {"repin": True}), "'plugin.marketplace' must"),
        ("not JSON", "{nope", "not valid JSON"),
    ):
        got = with_cfg(cfg)
        if not any(field in f for f in got):
            fails.append("AC-2 (%s): expected a finding naming %r, got %r" % (label, field, got))

    # Size classification, type by type.
    for title, level in (("feat: a", MINOR), ("fix: a", PATCH), ("perf: a", PATCH), ("revert: a", PATCH),
                         ("docs: a", NONE), ("chore: a", NONE), ("refactor: a", NONE), ("test: a", NONE),
                         ("ci: a", NONE), ("build: a", NONE), ("style: a", NONE), ("feat(scope): a", MINOR),
                         ("feat!: a", MAJOR), ("fix(scope)!: a", MAJOR)):
        if classify(title, "")[0] != level:
            fails.append("classify: %r should be level %d, got %d" % (title, level, classify(title, "")[0]))
    if classify("fix: a", "text\n\nBREAKING CHANGE: b")[0] != MAJOR:
        fails.append("classify: a BREAKING CHANGE footer must make a major")
    if classify("Update stuff", "") != (PATCH, True):
        fails.append("classify: an untyped title is a patch and is named, got %r" % (classify("Update stuff", ""),))
    if classify("wibble: a", "") != (PATCH, True):
        fails.append("classify: an unknown type is a patch and is named")
    for tag, level, want in (((0, 14, 1), PATCH, (0, 14, 2)), ((0, 14, 1), MINOR, (0, 15, 0)),
                             ((0, 14, 1), MAJOR, (0, 15, 0)), ((1, 2, 3), MAJOR, (2, 0, 0)),
                             ((1, 2, 3), MINOR, (1, 3, 0)), ((1, 2, 3), NONE, (1, 2, 4))):
        if expected_version(tag, level) != want:
            fails.append("expected_version: %r with level %d should be %r, got %r"
                         % (tag, level, want, expected_version(tag, level)))

    # The plain repository at 0.14.1: AC-4, AC-5, AC-17 and the bump rule.
    plain = fx.fresh("0.14.1")
    ok_history = [("1.0.1", "v0.14.2"), ("1.0.0", "v0.14.1")]

    fx.write_state(plain, "0.14.2", history=ok_history)
    expect("Example 1: a fix and 0.14.2", run_checks(plain, pr_title="fix(plab-a): x"), want_clean=True,
           line="should be 0.14.2")
    fx.write_state(plain, "0.15.0", history=[("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("AC-4: a fix and 0.15.0", run_checks(plain, pr_title="fix(plab-a): x"), want_clean=False, has="expected 0.14.2")
    expect("AC-4: a feat and 0.15.0", run_checks(plain, pr_title="feat(plab-a): x"), want_clean=True)
    fx.write_state(plain, "0.14.2", history=ok_history)
    expect("AC-4: a feat and 0.14.2", run_checks(plain, pr_title="feat(plab-a): x"), want_clean=False, has="expected 0.15.0")
    expect("AC-4: a sizeless docs title with a bump expects a patch", run_checks(plain, pr_title="docs: x"), want_clean=True)
    fx.write_state(plain, "0.15.0", history=[("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("AC-4: a sizeless docs title and 0.15.0", run_checks(plain, pr_title="docs: x"), want_clean=False, has="expected 0.14.2")
    fx.write_state(plain, "0.14.2", history=ok_history)
    expect("AC-4: a breaking title below 1.0.0 raises the minor", run_checks(plain, pr_title="feat!: x"),
           want_clean=False, has="expected 0.15.0")
    expect("AC-4: a BREAKING CHANGE footer in the PR body", run_checks(plain, pr_title="fix: x", pr_body="BREAKING CHANGE: y"),
           want_clean=False, has="expected 0.15.0")
    expect("AC-4: an untyped title counts as a patch and is named", run_checks(plain, pr_title="Update stuff"),
           want_clean=True, line="no recognised conventional type")
    expect("AC-4: perf counts as a patch", run_checks(plain, pr_title="perf: x"), want_clean=True)

    fx.write_state(plain, "0.14.2", section=False, history=ok_history)
    expect("AC-5: a bump with no CHANGELOG section", run_checks(plain, pr_title="fix: x"), want_clean=False, has="CHANGELOG.md")

    nochangelog = fx.fresh("0.14.1")
    fx.write_state(nochangelog, "0.14.2", history=ok_history)
    (nochangelog / "CHANGELOG.md").unlink()
    broken("AC-5: CHANGELOG.md missing, so the extractor exits 2", lambda: run_checks(nochangelog, pr_title="fix: x"))

    fx.write_state(plain, "0.14.2", history=[("1.0.1", "Unreleased"), ("1.0.0", "v0.14.1")])
    expect("AC-17: a bump with an Unreleased row", run_checks(plain, pr_title="fix: x"), want_clean=False,
           has="skills/plab-a/HISTORY.md: the row for 1.0.1")
    fx.write_state(plain, "0.14.1", history=[("1.0.1", "Unreleased"), ("1.0.0", "v0.14.1")])
    expect("AC-17: no bump, an Unreleased row is allowed", run_checks(plain, pr_title="fix: x"), want_clean=True, line="no bump")
    fx.write(plain, "skills/plab-a/HISTORY.md", "# History\n\nno table here\n")
    fx.write_state(plain, "0.14.2", history=None)
    broken("AC-17: a HISTORY.md with no Release column", lambda: run_checks(plain, pr_title="fix: x"))
    fx.write_state(plain, "0.14.0", history=ok_history)
    expect("bump: a version below the tag", run_checks(plain, pr_title="fix: x"), want_clean=False, has="below the latest version tag")

    fx.write_state(plain, "0.15.0", history=[("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("push event: no PR_TITLE skips the size rule and says so", run_checks(plain), want_clean=True, line="size: skipped")
    expect("push event: no BASE_SHA skips the eval rule and says so", run_checks(plain), want_clean=True, line="eval line: skipped")
    fx.write_state(plain, "0.15.0", section=False, history=[("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("push event: the CHANGELOG rule still runs", run_checks(plain), want_clean=False, has="CHANGELOG.md")

    # Example 3: a held-back feat, released through a later fix.
    held = fx.fresh("0.14.1")
    fx.merged(held, "feat(plab-a): held back")
    fx.write_state(held, "0.14.2", history=[("1.1.0", "v0.14.2"), ("1.0.1", "v0.14.2"), ("1.0.0", "v0.14.1")])
    expect("Example 3: 0.14.2 fails after a held-back feat", run_checks(held, pr_title="fix(plab-a): y"),
           want_clean=False, has="expected 0.15.0")
    fx.write_state(held, "0.15.0", history=[("1.1.0", "v0.15.0"), ("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("Example 3: 0.15.0 passes with both cells filled", run_checks(held, pr_title="fix(plab-a): y"), want_clean=True)
    fx.write_state(held, "0.15.0", history=[("1.1.0", "Unreleased"), ("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("Example 3: a still-Unreleased held-back cell fails", run_checks(held, pr_title="fix(plab-a): y"),
           want_clean=False, has="the row for 1.1.0")

    # A BREAKING CHANGE footer carried by an earlier merge, and a plain (non-merge) commit title.
    footer = fx.fresh("0.14.1")
    fx.merged(footer, "fix(plab-a): y", body_extra="BREAKING CHANGE: z")
    fx.write_state(footer, "0.15.0", history=[("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("AC-4: a footer on an earlier merge makes it a major", run_checks(footer, pr_title="docs: x"), want_clean=True)
    plaincommit = fx.fresh("0.14.1")
    fx.write(plaincommit, "notes/direct.txt", "x\n")
    fx.commit(plaincommit, "feat(plab-a): a direct commit, not a merge")
    fx.write_state(plaincommit, "0.15.0", history=[("1.0.1", "v0.15.0"), ("1.0.0", "v0.14.1")])
    expect("AC-4: a plain commit's subject is its title", run_checks(plaincommit, pr_title="docs: x"), want_clean=True)

    # A repository already at 1.2.3.
    major = fx.fresh("1.2.3")
    fx.write_state(major, "2.0.0", history=[("1.0.1", "v2.0.0"), ("1.0.0", "v1.2.3")])
    expect("AC-4: a breaking change at 1.2.3 expects 2.0.0", run_checks(major, pr_title="feat!: x"), want_clean=True)
    fx.write_state(major, "1.3.0", history=[("1.0.1", "v1.3.0"), ("1.0.0", "v1.2.3")])
    expect("AC-4: a breaking change at 1.2.3 does not accept 1.3.0", run_checks(major, pr_title="feat!: x"),
           want_clean=False, has="expected 2.0.0")

    # The latest tag is the version tag, not a backup tag or a floating tag nearer HEAD.
    tagged = fx.fresh("0.14.1")
    fx.merged(tagged, "docs: later")
    fx.g(tagged, "tag", "pre-merge/2026-01-01-x")
    fx.g(tagged, "tag", "v1")
    name, ver = latest_tag(tagged)
    if (name, ver) != ("v0.14.1", (0, 14, 1)):
        fails.append("latest tag: a backup tag and a floating v1 nearer HEAD must be ignored, got %r" % (name,))
    notag = fx.fresh("0.14.1")
    fx.g(notag, "tag", "-d", "v0.14.1")
    fx.g(notag, "tag", "-d", "v0.9.0")
    fx.g(notag, "tag", "pre-merge/only-a-backup")
    broken("latest tag: only a backup tag", lambda: run_checks(notag, pr_title="fix: x"))
    nolib = fx.fresh("0.14.1")
    (nolib / "library.json").unlink()
    broken("version: library.json missing", lambda: run_checks(nolib, pr_title="fix: x"))

    # The merge preview: HEAD is a merge of the pull request, and PR_TITLE already speaks for it.
    pv = fx.fresh("0.14.1")
    base_sha, head_sha = fx.preview(pv, {"notes/pr.txt": "x\n"}, body="feat: the preview must not count")
    fx.write_state(pv, "0.14.2", history=ok_history)
    expect("preview: the merge preview is excluded from the titles", run_checks(pv, pr_title="fix: y", head_sha=head_sha),
           want_clean=True)
    expect("preview: without HEAD_SHA it is read as a title", run_checks(pv, pr_title="fix: y"), want_clean=False,
           has="expected 0.15.0")

    # AC-6: the eval line, each case on its own pull request branch off the base.
    def eval_case(files, pr_body):
        repo = fx.copy(base_for_eval)
        base_sha, head_sha = fx.preview(repo, files)
        return run_checks(repo, pr_title="fix: x", pr_body=pr_body, base_sha=base_sha, head_sha=head_sha)

    base_for_eval = fx.base("0.14.1")
    desc_change = {"skills/plab-a/SKILL.md": SKILL % ("Does another thing", "1.0.0", "# A\n\nBody.")}
    body_change = {"skills/plab-a/SKILL.md": SKILL % ("Does a thing", "1.0.0", "# A\n\nA new body.")}
    meta_change = {"skills/plab-a/SKILL.md": (SKILL % ("Does a thing", "1.0.1", "# A\n\nBody.")).replace("2026-01-01", "2026-02-02")}
    new_skill = {"skills/plab-b/SKILL.md": SKILL % ("A new skill", "1.0.0", "# B\n\nBody.")}
    line = "Behaviour evals: 12/12 passed"
    expect("AC-6: a description change without the line", eval_case(desc_change, "no line"), want_clean=False,
           has="skills/plab-a/SKILL.md")
    expect("AC-6: a description change with the line", eval_case(desc_change, "Intro\r\n%s\r\n" % line), want_clean=True)
    expect("AC-6: a body change without the line", eval_case(body_change, ""), want_clean=False, has="skills/plab-a/SKILL.md")
    expect("AC-6: a body change with the line", eval_case(body_change, line), want_clean=True)
    expect("AC-6: a metadata-only change needs no line", eval_case(meta_change, ""), want_clean=True)
    expect("AC-6: a new skill needs the line", eval_case(new_skill, ""), want_clean=False, has="skills/plab-b/SKILL.md")
    expect("AC-6: a line in the wrong shape does not count", eval_case(desc_change, "Behaviour evals: all passed"),
           want_clean=False)
    expect("AC-6: a change outside skills needs no line", eval_case({"docs/x.md": "x\n"}, ""), want_clean=True)

    folded = SKILL.replace('description: "%s"', 'description: >\n  %s\n  and more')
    fold_old = {"skills/plab-a/SKILL.md": folded % ("Folded", "1.0.0", "# A\n\nBody.")}
    fold_new = {"skills/plab-a/SKILL.md": folded % ("Folded and changed", "1.0.0", "# A\n\nBody.")}
    base_fold = fx.copy(base_for_eval)
    fx.write(base_fold, "skills/plab-a/SKILL.md", fold_old["skills/plab-a/SKILL.md"])
    fx.commit(base_fold, "chore: fold the description")
    sha_b, sha_h = fx.preview(base_fold, fold_new)
    expect("AC-6: a continued description is read through its continuation lines",
           run_checks(base_fold, pr_title="fix: x", pr_body="", base_sha=sha_b, head_sha=sha_h), want_clean=False,
           has="skills/plab-a/SKILL.md")


# ------------------------------------------------------------------------ main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    ap.add_argument("--self-test", action="store_true", help="run the self-test and exit")
    ap.add_argument("--repo", default=str(ROOT), help="the checkout to check (default: this repository)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    try:
        fails = self_test()
    except Exception as exc:  # noqa: BLE001
        fails = ["unanticipated %s: %s" % (type(exc).__name__, exc)]
    if fails:
        for f in fails:
            print("self-test: " + f, file=sys.stderr)
        print("BROKEN: release-check self-test failed, its results are not trustworthy. Do NOT read this as clean.",
              file=sys.stderr)
        return 2
    print("release-check self-test: PASS (opt-in, configuration fields, every title type and size, "
          "the bump size for patch, minor, major and below 1.0.0, the CHANGELOG section, Unreleased cells, "
          "the eval line, the merge preview, push events and the latest tag)", flush=True)
    if args.self_test:
        return 0

    try:
        lines, findings = run_checks(args.repo, pr_title=os.environ.get("PR_TITLE") or None,
                                     pr_body=os.environ.get("PR_BODY") or "",
                                     base_sha=os.environ.get("BASE_SHA") or None,
                                     head_sha=os.environ.get("HEAD_SHA") or None)
    except Broken as exc:
        print("BROKEN: %s\nDo NOT read this as clean." % exc, file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print("BROKEN: unanticipated %s: %s\nDo NOT read this as clean." % (type(exc).__name__, exc), file=sys.stderr)
        return 2

    for ln in lines:
        print(ln, flush=True)
    if lines and lines[0].startswith("NOT OPTED IN"):
        return 0
    if findings:
        for f in findings:
            print("FINDING: " + f)
        print("FINDINGS: %d release rule(s) failed." % len(findings), flush=True)
        return 1
    print("CLEAN: every release rule held.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
