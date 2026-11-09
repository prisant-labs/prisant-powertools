#!/usr/bin/env python3
"""Tests for plab-org-profile-readme's scripts: the facts, the standard writer, the scaffold, the checker and SKILL.md.

USAGE
-----
  test-profile-scripts.py

Exit 0 when every case passes and both canaries prove their tests can fail,
1 when a case fails, 2 when the tests could not run. No case touches the
network: the facts fixtures are built in a temporary folder from the recorded
responses below, in the file layout derive-profile-facts.py documents.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SAMPLE = SKILL / "examples" / "sample-run"
STANDARDS = SKILL / "examples" / "standards"
PY = sys.executable

# AC-11: the three branch rules SKILL.md must state, each as a sentence a test can find.
BRANCH_SENTENCES = [
    "Never commit to the default branch.",
    "When the facts report an open pull request from an earlier run, update that branch and rewrite its body instead of opening another.",
    "When the checked page is identical to the current one, make no branch and say the page is current.",
]

# 1.1.0: the input and mode rules SKILL.md must state, so a run never guesses an
# organization, never improvises when there is nothing to check, and never adds a
# new repository the maintainer meant to ignore.
RULE_SENTENCES = [
    "When no organization is given, ask for one, and never infer it from the working directory.",
    "When the facts report no `.github` repository, stop and ask the maintainer to create it, because this skill never creates a repository.",
    "When the facts report no page and no standard, say there is nothing to check, suggest `--setup`, and open nothing.",
    "When the facts cover a repository the page does not list, ask the maintainer whether to add it or ignore it before writing the page.",
]

failures: list[str] = []
passed = 0


def case(name: str, ok: bool, detail: str = "") -> None:
    global passed
    if ok:
        passed += 1
        print("PASS %s" % name)
    else:
        failures.append(name)
        print("FAIL %s%s" % (name, (": " + detail) if detail else ""))


def run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(HERE / script), *args], capture_output=True, text=True, encoding="utf-8")


# ---------------------------------------------------------------- fixtures


def fx_name(path: str) -> str:
    return path.split("?", 1)[0].strip("/").replace("/", "__")


def write_fixture(root: Path, responses: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for path, body in responses.items():
        if isinstance(body, str):
            (root / (fx_name(path) + ".raw")).write_text(body, encoding="utf-8")
        else:
            (root / (fx_name(path) + ".json")).write_text(json.dumps(body), encoding="utf-8")
    return root


def repo(name, **kw):
    r = {"name": name, "private": False, "fork": False, "archived": False, "description": "%s description" % name,
         "topics": [], "default_branch": "main", "created_at": "2026-01-01T00:00:00Z", "pushed_at": "2026-10-01T00:00:00Z",
         "html_url": "https://github.com/example-org/%s" % name, "license": {"spdx_id": "MIT"}}
    r.update(kw)
    return r


def org_fixture(root: Path) -> Path:
    return write_fixture(root, {
        "users/example-org": {"login": "example-org", "type": "Organization"},
        "orgs/example-org/repos": [
            repo("alpha-tool"), repo("a-fork", fork=True), repo("old-thing", archived=True),
            repo("hidden-project", private=True, visibility="private"), repo(".github"),
        ],
        "repos/example-org/alpha-tool/releases": [
            {"tag_name": "v1.1.0-rc.1", "published_at": "2026-10-02T00:00:00Z", "prerelease": True, "draft": False},
            {"tag_name": "v1.0.0", "published_at": "2026-09-01T00:00:00Z", "prerelease": False, "draft": False},
        ],
        "repos/example-org/alpha-tool/tags": [{"name": "v1.1.0-rc.1"}, {"name": "v1.0.0"}],
        "repos/example-org/a-fork": {"parent": {"full_name": "upstream-owner/a"}},
        "repos/example-org/.github": {"default_branch": "main"},
        "repos/example-org/.github/contents/profile/README.md": "# Example Org\n",
        "repos/example-org/.github/pulls": [
            {"number": 7, "head": {"ref": "plab-org-profile-readme/2026-11-01"}, "html_url": "https://example.invalid/7", "title": "Profile refresh"},
            {"number": 8, "head": {"ref": "someone/else"}, "title": "Other work"},
        ],
    })


# ---------------------------------------------------------------- cases


def test_facts(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    fx = org_fixture(tmp / "org")
    out = tmp / "facts.json"
    p = run("derive-profile-facts.py", "example-org", "--fixture", str(fx), "--out", str(out), "--save", str(tmp / "saved"))
    case("facts: an organization exits 0", p.returncode == 0, p.stderr)
    if p.returncode != 0:
        return
    text = out.read_text(encoding="utf-8")
    f = json.loads(text)
    case("facts: only the public, non-fork, non-archived repository is covered (AC-3)", [r["name"] for r in f["covered"]] == ["alpha-tool"], str(f["covered"]))
    case("facts: the private repository's name appears nowhere (AC-3)", "hidden-project" not in text.lower())
    case("facts: the private repository is carried as a digest (AC-3)", hashlib.sha256(b"hidden-project").hexdigest() in f["private_digests"])
    case("facts: public forks and archived repositories are named in their own lists",
         [r["name"] for r in f["public_forks"]] == ["a-fork"] and f["archived"] == ["old-thing"] and f["public_forks"][0]["parent"] == "upstream-owner/a")
    case("facts: the newest release counts a prerelease, the latest stable does not",
         f["covered"][0]["newest_release"]["tag"] == "v1.1.0-rc.1" and f["covered"][0]["latest_stable"]["tag"] == "v1.0.0")
    case("facts: the profile page is present and the standard is missing (AC-4, AC-15)",
         f["profile"]["page"] == "present" and f["profile"]["standard"] == "missing" and f["profile"]["page_path"] == "profile/README.md")
    case("facts: the open pull request from an earlier run is found by its branch prefix",
         (f["open_pr"] or {}).get("number") == 7 and [o["number"] for o in f["profile"]["other_open_prs"]] == [8])
    case("facts: --save writes the current page", (tmp / "saved" / "current-page.md").read_text(encoding="utf-8") == "# Example Org\n")

    user = write_fixture(tmp / "user", {"users/example-user": {"login": "example-user", "type": "User"}})
    p = run("derive-profile-facts.py", "example-user", "--fixture", str(user))
    case("facts: a user account exits 2 and says the skill covers organization pages (AC-15)",
         p.returncode == 2 and "covers organization profile pages" in p.stderr, p.stderr)

    nogh = write_fixture(tmp / "nogh", {
        "users/example-org": {"login": "example-org", "type": "Organization"},
        "orgs/example-org/repos": [repo("alpha-tool")],
    })
    p = run("derive-profile-facts.py", "example-org", "--fixture", str(nogh), "--json")
    ok = p.returncode == 0
    f = json.loads(p.stdout) if ok else {}
    case("facts: an organization with no .github repository reports the page missing and exits 0 (AC-15)",
         ok and f["profile"]["repo_state"] == "missing" and f["profile"]["page"] == "missing", p.stderr)

    none = write_fixture(tmp / "none", {})
    p = run("derive-profile-facts.py", "nobody", "--fixture", str(none))
    case("facts: an owner that does not exist exits 2", p.returncode == 2)


def check(page: Path, facts: Path, standard: Path | None = None, *extra: str) -> subprocess.CompletedProcess:
    args = ["--page", str(page), "--facts", str(facts)]
    if standard:
        args += ["--standard", str(standard)]
    return run("profile-check.py", *args, *extra)


def fill_markers(text: str) -> str:
    return re.sub(r"<!-- describe:[^>]*-->", "Fixed text for the test.", text)


def test_checker(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    p = run("profile-check.py", "--self-test")
    case("checker: the self-test proves all fourteen rules (AC-12)", p.returncode == 0 and "14 rules" in p.stdout, p.stdout + p.stderr)

    p = check(SAMPLE / "README.md", SAMPLE / "facts.json", SAMPLE / "standard.json", "--pr-body", str(SAMPLE / "pr-body.md"), "--instructions-given")
    case("checker: the committed sample is clean", p.returncode == 0, p.stdout)

    p = check(SAMPLE / "README.md", SAMPLE / "facts.json")
    case("checker: without a standard, R8 to R13 are skipped by name and --setup is suggested (AC-10)",
         "SKIPPED: R8, R9, R10, R11, R12, R13" in p.stdout and "--setup" in p.stdout, p.stdout)

    facts = json.loads((SAMPLE / "facts.json").read_text(encoding="utf-8"))
    alpha = facts["covered"][0]
    alpha["releases"].insert(0, {"tag": "v1.2.1", "published_at": "2026-11-01T00:00:00Z", "prerelease": False})
    alpha["tags"].insert(0, "v1.2.1")
    newer = tmp / "newer-facts.json"
    newer.write_text(json.dumps(facts), encoding="utf-8")
    p = check(SAMPLE / "README.md", newer, SAMPLE / "standard.json")
    case("checker: a newer release than the page names is an R3 finding", p.returncode == 1 and "R3:" in p.stdout, p.stdout)
    std = json.loads((SAMPLE / "standard.json").read_text(encoding="utf-8"))
    std["skip_releases"] = [{"repo": "alpha-tool", "tag": "v1.2.1", "reason": "a documentation-only release with no visible change"}]
    skipped = tmp / "skip-standard.json"
    skipped.write_text(json.dumps(std, ensure_ascii=False), encoding="utf-8")
    p = check(SAMPLE / "README.md", newer, skipped)
    case("checker: a release the standard skips with a reason does not count for R3", p.returncode == 0, p.stdout)

    page = (SAMPLE / "README.md").read_text(encoding="utf-8").replace(
        "?display_name=tag&style=flat-square) ![license]", "?display_name=tag&style=flat-square&link=%2Fsecret-project) ![license]", 1)
    leaky = tmp / "leaky.md"
    leaky.write_text(page, encoding="utf-8")
    p = check(leaky, SAMPLE / "facts.json", SAMPLE / "standard.json")
    case("checker: a private name inside a percent-encoded URL is an R7 finding (AC-7)",
         p.returncode == 1 and "R7:" in p.stdout and "secret-project" not in p.stdout, p.stdout)

    base_page = (SAMPLE / "README.md").read_text(encoding="utf-8")
    for label, target, want in (("private", "secret-project", "private repository (name withheld)"),
                                ("missing", "no-such-repo", "not a public repository")):
        linked = tmp / ("links-%s.md" % label)
        linked.write_text(base_page.replace("## At a glance", "See [it](https://github.com/example-org/%s).\n\n## At a glance" % target, 1), encoding="utf-8")
        p = check(linked, SAMPLE / "facts.json", SAMPLE / "standard.json")
        case("checker: a link to a %s repository is an R2 finding (AC-5)" % label,
             p.returncode == 1 and any(l.startswith("FINDING R2:") and want in l for l in p.stdout.splitlines()), p.stdout)

    off = tmp / "recent-off.json"
    off.write_text(json.dumps(dict(std, skip_releases=[], options=dict(std["options"], recent_changes=False)), ensure_ascii=False), encoding="utf-8")
    p = check(SAMPLE / "README.md", SAMPLE / "facts.json", off)
    case("checker: a recent-changes block when recent changes are off is an R11 finding (AC-19)",
         p.returncode == 1 and "turns them off" in p.stdout, p.stdout)

    # Ignoring a repository: an exclusion means the page does not list it.
    listed_anyway = tmp / "excluded-listed.md"
    listed_anyway.write_text(base_page.replace(
        "### 🔀 [delta-fork]",
        "### 🧪 [sandbox-placeholder](https://github.com/example-org/sandbox-placeholder)\n\nA placeholder.\n\n### 🔀 [delta-fork]", 1), encoding="utf-8")
    p = check(listed_anyway, SAMPLE / "facts.json", SAMPLE / "standard.json")
    case("checker: an excluded repository that the page still lists is an R1 finding",
         p.returncode == 1 and any(l.startswith("FINDING R1:") and "sandbox-placeholder" in l and "excluded" in l for l in p.stdout.splitlines()), p.stdout)

    # The standard is committed to a public repository, so R7 covers it too.
    priv_std = tmp / "private-exclude.json"
    priv_std.write_text(json.dumps(dict(std, skip_releases=[], exclude=std["exclude"] + [
        {"repo": "secret-project", "reason": "not ready to show anyone"}]), ensure_ascii=False), encoding="utf-8")
    p = check(SAMPLE / "README.md", SAMPLE / "facts.json", priv_std)
    case("checker: an exclusion that names a private repository is an R7 finding, name withheld",
         p.returncode == 1 and any(l.startswith("FINDING R7:") and "the standard" in l for l in p.stdout.splitlines())
         and "secret-project" not in p.stdout, p.stdout)

    stale_std = tmp / "stale-exclude.json"
    stale_std.write_text(json.dumps(dict(std, skip_releases=[], exclude=std["exclude"] + [
        {"repo": "long-gone", "reason": "an old experiment, since deleted"}]), ensure_ascii=False), encoding="utf-8")
    p = check(SAMPLE / "README.md", SAMPLE / "facts.json", stale_std)
    case("checker: an exclusion for a repository the facts do not cover is a note, not a finding",
         p.returncode == 0 and any(l.startswith("NOTE R1:") and "long-gone" in l for l in p.stdout.splitlines()), p.stdout)

    bad = tmp / "bad-standard.json"
    bad.write_text(json.dumps(dict(std, options=dict(std["options"], order="random"))), encoding="utf-8")
    p = check(SAMPLE / "README.md", SAMPLE / "facts.json", bad)
    case("checker: an invalid standard is broken input, exit 2", p.returncode == 2, p.stdout)

    crlf = tmp / "crlf.md"
    crlf.write_bytes((SAMPLE / "README.md").read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    p = check(crlf, SAMPLE / "facts.json", SAMPLE / "standard.json")
    case("checker: a page with Windows line endings checks the same", p.returncode == 0, p.stdout)


ANSWERS = {
    "catalog": {"categories": [{"name": "Tools", "repos": ["alpha-tool", "beta-kit"]},
                               {"name": "Utilities", "repos": ["gamma-notes", "delta-fork"]}]},
    "compact": {},
    "showcase": {"options": {"featured": ["beta-kit", "alpha-tool"]}},
    "custom": {"sections": [{"id": "header", "kind": "fixed", "heading": "# Example Org"},
                            {"id": "projects", "kind": "fixed", "heading": "## Projects"}]},
}


def test_standards(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    common = {"org": "example-org", "display_name": "Example Org",
              "exclude": [{"repo": "sandbox-placeholder", "reason": "a placeholder repository with no project"}],
              "include": [{"repo": "delta-fork", "reason": "a fork that publishes its own releases"}]}
    for base, extra in ANSWERS.items():
        answers = tmp / ("%s-answers.json" % base)
        answers.write_text(json.dumps(dict(common, **extra), ensure_ascii=False), encoding="utf-8")
        std = tmp / ("%s-standard.json" % base)
        p = run("write-standard.py", "--base", base, "--answers", str(answers), "--out", str(std))
        case("standard: --setup's %s path writes a standard (AC-17)" % base, p.returncode == 0, p.stderr)
        if p.returncode:
            continue
        page = tmp / ("%s-page.md" % base)
        p = run("scaffold-page.py", "--standard", str(std), "--facts", str(SAMPLE / "facts.json"), "--out", str(page))
        case("scaffold: a %s standard with no page writes a page (AC-18)" % base, p.returncode == 0, p.stderr)
        if p.returncode:
            continue
        p = check(page, SAMPLE / "facts.json", std)
        case("checker: an unfinished %s scaffold is rejected for its markers" % base, p.returncode == 1 and "scaffold marker" in p.stdout, p.stdout)
        page.write_text(fill_markers(page.read_text(encoding="utf-8")), encoding="utf-8")
        p = check(page, SAMPLE / "facts.json", std)
        case("checker: the %s scaffold, with its prose written, passes (AC-17, AC-18)" % base, p.returncode == 0, p.stdout)

    std = tmp / "adopted-standard.json"
    p = run("write-standard.py", "--base", "adopted", "--from-page", str(SAMPLE / "README.md"), "--facts", str(SAMPLE / "facts.json"), "--out", str(std))
    case("standard: --setup's adopted path writes a standard (AC-17)", p.returncode == 0, p.stderr)
    if p.returncode == 0:
        s = json.loads(std.read_text(encoding="utf-8"))
        case("standard: adoption finds the categories in order and records the exclusion and inclusion",
             [c["name"] for c in s["categories"]] == ["Tools", "Utilities"]
             and [e["repo"] for e in s["exclude"]] == ["sandbox-placeholder"] and [e["repo"] for e in s["include"]] == ["delta-fork"], json.dumps(s, ensure_ascii=False))
        p = check(SAMPLE / "README.md", SAMPLE / "facts.json", std)
        case("checker: the page passes the standard adopted from it (AC-17)", p.returncode == 0, p.stdout)

    for base in ("catalog", "compact", "showcase"):
        d = STANDARDS / base
        p = check(d / "README.md", SAMPLE / "facts.json", d / "standard.json")
        case("samples: the shipped %s sample passes its own standard (AC-16)" % base, p.returncode == 0, p.stdout)
        doc = SKILL / "references" / "standards" / ("%s.md" % base)
        case("samples: the %s standard has a reference document (AC-16)" % base, doc.is_file())

    std = json.loads((SAMPLE / "standard.json").read_text(encoding="utf-8"))
    std["categories"] = std["categories"][:1]
    nocat = tmp / "nocat.json"
    nocat.write_text(json.dumps(std, ensure_ascii=False), encoding="utf-8")
    p = run("scaffold-page.py", "--standard", str(nocat), "--facts", str(SAMPLE / "facts.json"), "--out", str(tmp / "x.md"))
    case("scaffold: a covered repository with no category is named, exit 2", p.returncode == 2 and "gamma-notes" in p.stderr, p.stderr)


# ---------------------------------------------------------------- AC-4 and AC-11


def forbidden_hits(root: Path, names: list[str]) -> list[str]:
    hits = []
    targets = [root / "SKILL.md", root / "README.md", root / "HISTORY.md"]
    for sub in ("references", "scripts", "examples", "agents"):
        targets += [p for p in (root / sub).rglob("*") if p.is_file()]
    for p in targets:
        if not p.is_file() or "fixtures" in p.relative_to(root).parts or p.suffix in (".pyc",):
            continue
        text = p.read_text(encoding="utf-8", errors="replace").lower()
        for n in names:
            if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(n.lower()), text):
                hits.append("%s names %s" % (p.relative_to(root), n))
    return hits


def test_names_and_sentences(tmp: Path) -> None:
    tmp.mkdir(parents=True, exist_ok=True)
    names = [l.strip() for l in (HERE / "fixtures" / "forbidden-names.txt").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    case("names: the forbidden-names list is not empty", len(names) >= 5)
    hits = forbidden_hits(SKILL, names)
    case("names: no skill file names a real owner or repository (AC-4)", not hits, "; ".join(hits))
    copy = tmp / "skill-copy"
    shutil.copytree(SKILL, copy, ignore=shutil.ignore_patterns("__pycache__"))
    (copy / "references" / "planted.md").write_text("See %s for details.\n" % names[0], encoding="utf-8")
    case("names: canary proved, a planted name is found", bool(forbidden_hits(copy, names)))

    skill_md = SKILL / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    missing = [s for s in BRANCH_SENTENCES if s not in text]
    case("skill: SKILL.md states all three branch rules (AC-11)", not missing, "; ".join(missing))
    front = text.split("---", 2)[1] if text.startswith("---") else ""
    case("skill: SKILL.md is manual-only (AC-1)", "disable-model-invocation: true" in front)
    yaml = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
    case("skill: the Codex policy is manual-only (AC-1)", "allow_implicit_invocation: false" in yaml)
    desc = re.search(r'^description:\s*"(.*)"\s*$', front, re.M)
    case("skill: the description is at most 600 characters", bool(desc) and len(desc.group(1)) <= 600)
    cut = text.replace(BRANCH_SENTENCES[1], "", 1)
    case("skill: canary proved, removing a branch rule is caught", any(s not in cut for s in BRANCH_SENTENCES))
    missing = [s for s in RULE_SENTENCES if s not in text]
    case("skill: SKILL.md states the organization, nothing-to-check and add-or-ignore rules", not missing, "; ".join(missing))
    cut = text.replace(RULE_SENTENCES[0], "", 1)
    case("skill: canary proved, removing an input rule is caught", any(s not in cut for s in RULE_SENTENCES))


def main() -> int:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        try:
            test_facts(tmp / "facts")
            test_checker(tmp / "check")
            test_standards(tmp / "std")
            test_names_and_sentences(tmp / "names")
        except (OSError, ValueError, KeyError) as e:
            print("BROKEN: the tests could not run: %r" % e)
            return 2
    if failures:
        print("FINDINGS: %d of %d cases failed: %s" % (len(failures), len(failures) + passed, ", ".join(failures)))
        return 1
    print("CLEAN: canary proved, %d cases passed." % passed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
