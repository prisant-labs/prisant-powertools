#!/usr/bin/env python3
"""Gather every fact a plab-org-profile-readme run needs about one GitHub organization, in one call.

USAGE
-----
  derive-profile-facts.py <org> [--fixture <dir>] [--json] [--out <facts.json>] [--save <dir>]

  --fixture <dir>  read every GitHub response from recorded files instead of `gh`
                   (see FIXTURES below), so tests and CI never touch the network
  --json           print the facts as JSON on stdout (the default prints a summary)
  --out <path>     also write the facts JSON to this file
  --save <dir>     also write the current page and standard, when present, to
                   <dir>/current-page.md and <dir>/standard.json, so the checker
                   can read them

EXIT-CODE CONTRACT
------------------
  0  CLEAN   the facts were gathered. A missing `.github` repository, page or
             standard is a fact, reported as `missing`, not an error (RM-01 AC-15)
  2  BROKEN  the owner is a user account, does not exist, or a GitHub call failed
             for a reason other than "not found"

There is no exit 1: this script reports facts and judges nothing. The checker,
profile-check.py, judges the page against them.

WHAT "COVERED" MEANS
--------------------
A covered repository is public, not a fork, not archived, and not the profile
repository `.github` itself (RM-01 requirement 3). Public forks and public
archived repositories are named in their own lists, because they are public and
a standard may include a fork by name. A private repository is never named: the
facts carry only the SHA-256 hex digest of its lowercased name, in
`private_digests`, so the checker can reject the name on a page without the
facts ever containing it (RM-01 requirement 4, AC-3).

FIXTURES
--------
Each GitHub path maps to one file in the fixture directory: the path with its
query string removed and every `/` replaced by `__`. A JSON response is
`<name>.json`; a raw file read through the contents API is `<name>.raw`. A
missing fixture file means GitHub answered 404. For example,
`repos/example-org/alpha/releases` is `repos__example-org__alpha__releases.json`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FORMAT = 1
PROFILE_REPO = ".github"
PAGE_PATH = "profile/README.md"
STANDARD_PATH = "profile/standard.json"
BRANCH_PREFIX = "plab-org-profile-readme/"


class Broken(Exception):
    """A fact could not be gathered; the run must stop with exit 2."""


class GitHub:
    """Every GitHub read goes through here, so a fixture can stand in for the network."""

    def __init__(self, fixture: Path | None):
        self.fixture = fixture

    @staticmethod
    def _fixture_name(path: str) -> str:
        return path.split("?", 1)[0].strip("/").replace("/", "__")

    def _gh(self, args: list[str]) -> str | None:
        try:
            proc = subprocess.run(["gh", "api", *args], capture_output=True, text=True, encoding="utf-8")
        except FileNotFoundError:
            raise Broken("the GitHub CLI `gh` is not installed or not on PATH")
        if proc.returncode == 0:
            return proc.stdout
        if "HTTP 404" in proc.stderr or "Not Found" in proc.stderr:
            return None
        raise Broken("`gh api %s` failed: %s" % (" ".join(args), proc.stderr.strip() or "exit %d" % proc.returncode))

    def json(self, path: str, paginate: bool = False):
        """Return the parsed JSON response, or None when GitHub answers 404."""
        if self.fixture is not None:
            f = self.fixture / (self._fixture_name(path) + ".json")
            if not f.is_file():
                return None
            return json.loads(f.read_text(encoding="utf-8"))
        if paginate:
            out = self._gh(["--paginate", path, "--jq", ".[]"])
            if out is None:
                return None
            return [json.loads(line) for line in out.splitlines() if line.strip()]
        out = self._gh([path])
        return None if out is None else json.loads(out)

    def raw(self, path: str) -> str | None:
        """Return a file's raw text through the contents API, or None when it is absent."""
        if self.fixture is not None:
            f = self.fixture / (self._fixture_name(path) + ".raw")
            if not f.is_file():
                return None
            return f.read_bytes().decode("utf-8").replace("\r\n", "\n")
        out = self._gh(["-H", "Accept: application/vnd.github.raw", path])
        return None if out is None else out.replace("\r\n", "\n")


def digest(name: str) -> str:
    return hashlib.sha256(name.lower().encode("utf-8")).hexdigest()


def newest(releases: list[dict], stable_only: bool) -> dict | None:
    """The newest non-draft release, optionally skipping prereleases. GitHub lists newest first."""
    for r in releases:
        if r.get("draft"):
            continue
        if stable_only and r.get("prerelease"):
            continue
        return {"tag": r["tag_name"], "published_at": r.get("published_at"), "prerelease": bool(r.get("prerelease"))}
    return None


def repo_facts(gh: GitHub, org: str, repo: dict) -> dict:
    name = repo["name"]
    releases = gh.json("repos/%s/%s/releases?per_page=10" % (org, name)) or []
    tags = gh.json("repos/%s/%s/tags?per_page=100" % (org, name), paginate=True) or []
    lic = repo.get("license") or {}
    return {
        "name": name,
        "description": repo.get("description") or "",
        "topics": repo.get("topics") or [],
        "default_branch": repo.get("default_branch") or "main",
        "created_at": repo.get("created_at"),
        "pushed_at": repo.get("pushed_at"),
        "html_url": repo.get("html_url") or "https://github.com/%s/%s" % (org, name),
        "license": lic.get("spdx_id"),
        "newest_release": newest(releases, stable_only=False),
        "latest_stable": newest(releases, stable_only=True),
        "releases": [
            {"tag": r["tag_name"], "published_at": r.get("published_at"), "prerelease": bool(r.get("prerelease"))}
            for r in releases if not r.get("draft")
        ][:5],
        "tags": [t["name"] for t in tags],
    }


def gather(org: str, gh: GitHub) -> tuple[dict, str | None, str | None]:
    owner = gh.json("users/%s" % org)
    if owner is None:
        raise Broken("no GitHub account named %s" % org)
    if owner.get("type") != "Organization":
        raise Broken("plab-org-profile-readme covers organization profile pages; %s is a user account" % org)
    org_login = owner.get("login") or org

    repos = gh.json("orgs/%s/repos?per_page=100&type=all" % org_login, paginate=True)
    if repos is None:
        raise Broken("could not list the repositories of %s" % org_login)

    covered, forks, archived, digests = [], [], [], []
    counts = {"public": 0, "private": 0, "forks": 0, "archived": 0}
    for r in sorted(repos, key=lambda r: r["name"].lower()):
        if r.get("private") or r.get("visibility") in ("private", "internal"):
            counts["private"] += 1
            digests.append(digest(r["name"]))
            continue
        counts["public"] += 1
        if r["name"].lower() == PROFILE_REPO:
            continue
        if r.get("archived"):
            counts["archived"] += 1
            archived.append(r["name"])
            continue
        if r.get("fork"):
            counts["forks"] += 1
            f = repo_facts(gh, org_login, r)
            full = gh.json("repos/%s/%s" % (org_login, r["name"])) or {}
            f["parent"] = (full.get("parent") or {}).get("full_name")
            forks.append(f)
            continue
        covered.append(repo_facts(gh, org_login, r))

    profile_repo = gh.json("repos/%s/%s" % (org_login, PROFILE_REPO))
    page = standard = None
    open_pr = None
    profile = {
        "repo": PROFILE_REPO,
        "repo_state": "missing" if profile_repo is None else "present",
        "default_branch": (profile_repo or {}).get("default_branch") or "main",
        "page_path": PAGE_PATH,
        "page": "missing",
        "standard_path": STANDARD_PATH,
        "standard": "missing",
    }
    if profile_repo is not None:
        page = gh.raw("repos/%s/%s/contents/%s" % (org_login, PROFILE_REPO, PAGE_PATH))
        standard = gh.raw("repos/%s/%s/contents/%s" % (org_login, PROFILE_REPO, STANDARD_PATH))
        profile["page"] = "present" if page is not None else "missing"
        profile["standard"] = "present" if standard is not None else "missing"
        pulls = gh.json("repos/%s/%s/pulls?state=open&per_page=100" % (org_login, PROFILE_REPO), paginate=True) or []
        mine = [p for p in pulls if (p.get("head") or {}).get("ref", "").startswith(BRANCH_PREFIX)]
        others = [p for p in pulls if p not in mine]
        if mine:
            p = mine[0]
            open_pr = {"number": p["number"], "branch": p["head"]["ref"], "url": p.get("html_url")}
        profile["other_open_prs"] = [
            {"number": p["number"], "branch": (p.get("head") or {}).get("ref"), "title": p.get("title")} for p in others
        ]
    if standard is not None:
        try:
            json.loads(standard)
        except ValueError as e:
            raise Broken("%s in %s/%s is not valid JSON: %s" % (STANDARD_PATH, org_login, PROFILE_REPO, e))

    facts = {
        "format": FORMAT,
        "org": org_login,
        "owner_type": "Organization",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "profile": profile,
        "open_pr": open_pr,
        "covered": covered,
        "public_forks": forks,
        "archived": archived,
        "counts": counts,
        "private_digests": sorted(digests),
    }
    return facts, page, standard


def summary(f: dict) -> str:
    p = f["profile"]
    lines = [
        "org %s: %d covered, %d public forks, %d archived, %d private (digests only)"
        % (f["org"], len(f["covered"]), len(f["public_forks"]), len(f["archived"]), f["counts"]["private"]),
        "profile repository %s: %s; page %s; standard %s" % (p["repo"], p["repo_state"], p["page"], p["standard"]),
        "open pull request from an earlier run: %s" % (("#%d (%s)" % (f["open_pr"]["number"], f["open_pr"]["branch"])) if f["open_pr"] else "none"),
    ]
    for o in p.get("other_open_prs", []):
        lines.append("other open pull request: #%d (%s) %s" % (o["number"], o["branch"], o["title"]))
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("org")
    ap.add_argument("--fixture", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--save", type=Path)
    a = ap.parse_args(argv)
    if a.fixture is not None and not a.fixture.is_dir():
        print("BROKEN: fixture directory %s does not exist" % a.fixture, file=sys.stderr)
        return 2
    try:
        facts, page, standard = gather(a.org, GitHub(a.fixture))
    except Broken as e:
        print("BROKEN: %s" % e, file=sys.stderr)
        return 2
    text = json.dumps(facts, indent=2, ensure_ascii=False) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8", newline="\n")
    if a.save:
        a.save.mkdir(parents=True, exist_ok=True)
        if page is not None:
            (a.save / "current-page.md").write_text(page, encoding="utf-8", newline="\n")
        if standard is not None:
            (a.save / "standard.json").write_text(standard, encoding="utf-8", newline="\n")
    if a.json:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
    else:
        print(summary(facts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
