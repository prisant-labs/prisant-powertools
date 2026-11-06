#!/usr/bin/env python3
"""Tests for derive-ship-facts.py and screen-branch.py, against throwaway repositories, plus a check of SKILL.md.

Exit 0 when every check passes, 1 when one fails, and 2 when the test itself could not run.
These never touch GitHub: `gh` is named as an absent executable.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
FACTS = HERE / "derive-ship-facts.py"
SCREEN = HERE / "screen-branch.py"
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "  (%s)" % detail))


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    if r.returncode != 0:
        raise RuntimeError("git %s: %s" % (args[0], r.stderr))
    return r.stdout.strip()


def write(repo, rel, content):
    p = Path(repo) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def commit(repo, message):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def facts(repo, *extra):
    r = subprocess.run([sys.executable, "-B", str(FACTS), "--repo", str(repo), "--no-fetch", "--gh", "no-such-gh", *extra],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    return r.returncode, r.stdout


def screen(repo, rng):
    r = subprocess.run([sys.executable, "-B", str(SCREEN), "--repo", str(repo), "--range", rng],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    return r.returncode, r.stdout


def tree_hash(repo):
    digest = hashlib.sha256()
    for path in sorted(Path(repo).rglob("*")):
        if path.is_file() and ".git" not in path.parts:
            digest.update(path.as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_facts():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        write(repo, "README.md", "# Example\n")
        write(repo, "CHANGELOG.md", "# Changelog\n\n## [Unreleased]\n\n- A change.\n\n## [0.9.0]\n\n- Old.\n")
        write(repo, ".gitignore", "_local/\n")
        write(repo, ".github/workflows/publish.yml", "on:\n  push:\n    tags:\n      - 'v*'\n")
        write(repo, "library.json", "{}\n")
        write(repo, "OPEN.md", "# Open\n")
        write(repo, "docs/internal/spec.md", "# Spec\n")
        write(repo, "AGENTS.md", "# Agents\n")
        first = commit(repo, "base")
        git(repo, "tag", "v0.9.0", first)
        second = commit_empty(repo, "feat: second")
        git(repo, "tag", "v0.10.0", second)
        third = commit_empty(repo, "fix: third")
        # The nearest tags on purpose: neither may be read as the latest version.
        git(repo, "tag", "pre-merge/2026-11-05-demo", third)
        git(repo, "tag", "v1", third)

        before_status = git(repo, "status", "--porcelain")
        before_hash = tree_hash(repo)
        rc, out = facts(repo)
        check("facts exit 0", rc == 0, out[:200])
        data = json.loads(out)
        check("the facts write nothing in the working tree",
              git(repo, "status", "--porcelain") == before_status and tree_hash(repo) == before_hash)
        release = data["release"]
        check("a backup tag and a floating major tag are not the latest version",
              release["latest_version_tag"] == "v0.10.0", release["latest_version_tag"])
        check("versions sort by number, so 0.10.0 outranks 0.9.0", release["latest_version_tag"] != "v0.9.0")
        check("ignored tags are counted", release["other_tags_ignored"] == 2, release["other_tags_ignored"])
        check("the tag shape is reported", release["tag_prefix"] == "v" and release["tag_parts"] == 3)
        check("commits since the version tag are listed",
              [c["subject"] for c in release["commits_since_tag"]] == ["fix: third"], release["commits_since_tag"])
        check("the CHANGELOG's Unreleased section is measured", release["changelog"]["unreleased_lines"] == 1, release["changelog"])
        check("a tag-triggered workflow is named", release["tag_workflows"] == [".github/workflows/publish.yml"])
        check("a plugin repository is recognised", release["plugin_repo"] is True)
        check("an open-items file is named", data["open_item_files"] == ["OPEN.md"])
        check("the record folder is reported as ignored", data["record_dir_ignored"] is True)
        check("nothing under _local/ is tracked", data["tracked_local_files"] == [])
        sources = [g["source"] for g in data["gaps"]]
        check("an absent gh is a named gap, never an empty list", "pull requests" in sources, sources)
        check("no remote is a named gap", "remote" in sources, sources)
        counts = data["doc_map"]["tracked_counts"]
        check("internal docs count as technical, not human", counts["technical"] == 1 and counts["human"] == 2, counts)
        check("a detected map says so", data["doc_map"]["source"] == "detected")

        write(repo, ".claude/plab-ship.local.md", "---\nhuman: README.md\nnot-docs: CHANGELOG.md\n---\n")
        data = json.loads(facts(repo)[1])
        check("a settings file overrides the detected map",
              data["doc_map"]["source"] == "settings" and data["doc_map"]["globs"]["human"] == ["README.md"],
              data["doc_map"]["globs"])

    with tempfile.TemporaryDirectory() as tmp:
        rc, out = facts(tmp)
        check("a folder that is not a repository exits 2", rc == 2 and "BROKEN" in out, out[:200])


def commit_empty(repo, message):
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def test_screen():
    # Built by concatenation so that no credential shape sits in this file, which the screen also reads.
    fake_github = "gh" + "p_" + "a1B2" * 9
    fake_key_line = "api_key = " + '"' + "z9Y8" * 6 + '"\n'
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        git(repo, "init", "-q", "-b", "main")
        write(repo, "README.md", "# Example\n")
        base = commit(repo, "base")

        write(repo, "clean.py", "print('nothing to see')\n")
        clean = commit(repo, "clean")
        rc, out = screen(repo, "%s..%s" % (base, clean))
        check("a clean branch exits 0", rc == 0 and out.startswith("CLEAN"), out)
        check("a clean result names its limit", "not proof" in out, out)

        write(repo, "config.py", "TOKEN = '%s'\n" % fake_github)
        hit = commit(repo, "token")
        rc, out = screen(repo, "%s..%s" % (clean, hit))
        check("a credential shape exits 1 and names the file", rc == 1 and "config.py" in out and "github-token" in out, out)
        check("the value itself is never printed", fake_github not in out, out)

        write(repo, "settings.ini", fake_key_line)
        hit2 = commit(repo, "assigned")
        rc, out = screen(repo, "%s..%s" % (hit, hit2))
        check("an assigned secret is found", rc == 1 and "assigned-secret" in out, out)
        check("an assigned value is never printed", "z9Y8" not in out, out)

        write(repo, ".env", "HARMLESS=1\n")
        write(repo, ".env.example", "HARMLESS=1\n")
        env = commit(repo, "env")
        rc, out = screen(repo, "%s..%s" % (hit2, env))
        check("a sensitive file name is found", rc == 1 and "sensitive-name: .env " in out, out)
        check("an example env file is not", ".env.example" not in out, out)

        write(repo, "_local/notes.md", "private\n")
        git(repo, "add", "-A", "-f")
        git(repo, "commit", "-q", "-m", "local")
        rc, out = screen(repo, "%s..HEAD" % env)
        check("a tracked _local/ file is found", rc == 1 and "tracked-local: _local/notes.md" in out, out)

        rc, out = screen(repo, "no-such-ref..HEAD")
        check("an unreadable range exits 2, never clean", rc == 2 and "BROKEN" in out, out)
        rc, out = screen(repo, "HEAD")
        check("a value that is not a range exits 2", rc == 2, out)


def test_skill_text():
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    all_text = text + "".join(p.read_text(encoding="utf-8") for p in sorted((SKILL_DIR / "references").glob("*.md")))
    check("SKILL.md and the references hold no machine path",
          not re.search(r"\b[A-Za-z]:[/\\]|/Users/|/home/", all_text), re.findall(r"\b[A-Za-z]:[/\\]\S*", all_text)[:3])
    fm = text.split("---")[1]
    check("the skill is manual-only", "disable-model-invocation: true" in fm)
    description = re.search(r'^description: "(.*)"$', fm, re.M).group(1)
    check("the description stays within its 600-character budget", len(description) <= 600, len(description))
    check("the flag takes no number and no size", 'argument-hint: "[<branch|PR> ...] [--release] [--no-fetch]"' in fm, fm)
    check("the skill names the merge rule rather than a path to the check", "solo-repo merge rule" in text)
    check("a missing check fails closed", "never a pass" in text)
    check("the cold reader names a model", re.search(r"cold reader[^\n]*Sonnet|Sonnet[^\n]*cold reader", all_text, re.I))
    for name in ("derive-ship-facts.py", "screen-branch.py", "ship-check.py"):
        check("the workflow runs %s" % name, name in text)


def main():
    try:
        test_facts()
        test_screen()
        test_skill_text()
    except (RuntimeError, OSError, ValueError, KeyError, AttributeError) as exc:
        print("BROKEN: %s" % exc)
        return 2
    failed = [name for name, ok in results if not ok]
    print("%d checks, %d failed" % (len(results), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
