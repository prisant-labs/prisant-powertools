#!/usr/bin/env python3
"""Check an organization profile README against the repository facts and its standard, after proving every rule can fail.

USAGE
-----
  profile-check.py --page <README.md> --facts <facts.json> [--standard <standard.json>]
                   [--pr-body <file>] [--instructions-given]
  profile-check.py --self-test

It reads files only, never the network. The facts come from derive-profile-facts.py.

EXIT-CODE CONTRACT
------------------
  0  CLEAN     the self-test passed AND the page satisfies every rule that ran
  1  FINDINGS  the self-test passed AND at least one rule failed; each is named
  2  BROKEN    the self-test failed, or an input could not be read or is invalid

NEVER INTERPRET 2 AS CLEAN. Every run proves the rules first, against the
committed sample in examples/sample-run/ and one mutation per rule, so a rule
that has gone blind stops the run instead of passing everything. A NOTE line is
a finding the maintainer should see that does not fail the page.

THE RULES (RM-01, plab-org-profile-readme)
------------------------------------------
Factual rules, run with or without a standard:
  R1  every covered repository, and every fork the standard includes, has an
      entry on the page or is excluded by the standard with a reason (AC-5)
  R2  every repository the page links to is covered or an included fork; an
      archived, a not-included fork, a private or a missing one is named (AC-5)
  R3  the first release link for a repository names its newest release, not
      counting a release the standard's `skip_releases` lists with a reason,
      such as one that changed nothing a user would notice (AC-6)
  R4  every release link names a tag that exists in its repository (AC-6)
  R5  every shields badge names this organization and a repository the page
      lists, or the standard covers (AC-6)
  R6  a badge that reads a list by position, such as `$.plugins[1]`, is a NOTE,
      because adding an entry to that list changes what it shows (AC-6)
  R7  no word on the page or in the pull request body is a private
      repository's name, matched by digest (AC-7)
Standard rules, run only with a standard; skipped by name without one (AC-10):
  R8  every section of the standard is present and in order, every repository
      in a category sits under that category, and no scaffold marker is left
      (AC-8, AC-19)
  R9  every shared-text passage appears exactly (AC-8)
  R10 no badge when badges are off, and only the allowed kinds when on (AC-19)
  R11 no recent-changes block when recent changes are off, and none longer than
      the set count when on (AC-19)
  R12 every status label or tag comes from the vocabulary (AC-19)
  R13 the featured repositories are the first entries, in order (AC-19)
Pull request rule, run when a body is given:
  R14 the body has a "From the repositories" heading, and with
      --instructions-given also a "From your instructions" heading (AC-20)

WHAT AN ENTRY IS
----------------
A heading, list item or table row whose first link points at the root of one of
this organization's repositories, `https://github.com/<org>/<repo>`. A link to a
release, a file or an in-page anchor does not make an entry. This one shape
covers the Catalog project headings, the Compact table rows and the Showcase
headings and list items.

WHAT THIS DOES NOT PROVE
------------------------
That the prose is true or well written. The rules prove the page's facts and
its structure. The agent writes the prose from each repository's own README and
releases, and the maintainer reviews it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

SKILL_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = SKILL_DIR / "examples" / "sample-run"
RULE_IDS = ["R%d" % i for i in range(1, 15)]
STANDARD_RULES = ["R8", "R9", "R10", "R11", "R12", "R13"]

BASES = {"catalog", "compact", "showcase", "adopted", "custom"}
BADGE_KINDS = {"release", "license", "ci", "dynamic", "static", "other"}
ORDERS = {"category", "latest_release", "alphabetical"}
GROUPINGS = {"none", "category"}
SECTION_KINDS = {"fixed", "categories"}
MARKER = "<!-- describe:"
# An invented name. The sample facts carry only its digest, as real facts do;
# the self-test plants the name itself to prove R7 can find it.
SAMPLE_PRIVATE_NAME = "secret-project"

LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML_URL_RE = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.I)
IMG_MD_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?")
IMG_HTML_RE = re.compile(r"""<img\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.I)
GH_RE = re.compile(r"^https?://(?:www\.)?github\.com/([^/?#]+)/([^/?#]+)(/[^?#]*)?", re.I)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ENTRY_LINE_RE = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\|)")
RECENT_RE = re.compile(r"^\s*\*\*Recent [^*]*:\*\*\s*$")
BULLET_RE = re.compile(r"^\s*[-*+]\s")
TOKEN_RE = re.compile(r"[A-Za-z0-9._-]+")


class Broken(Exception):
    """An input could not be read, or the checker could not prove itself."""


# ---------------------------------------------------------------- reading


def read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    except OSError as e:
        raise Broken("cannot read %s: %s" % (path, e))
    except UnicodeDecodeError as e:
        raise Broken("%s is not UTF-8: %s" % (path, e))


def read_json(path: Path) -> dict:
    try:
        return json.loads(read_text(path))
    except ValueError as e:
        raise Broken("%s is not valid JSON: %s" % (path, e))


def validate_facts(f: dict) -> None:
    for key in ("org", "covered", "public_forks", "archived", "private_digests"):
        if key not in f:
            raise Broken("the facts have no `%s`; produce them with derive-profile-facts.py" % key)


def validate_standard(s: dict) -> None:
    """A standard that breaks its own format is broken input, not a finding against the page."""
    if s.get("base") not in BASES:
        raise Broken("standard: `base` must be one of %s" % ", ".join(sorted(BASES)))
    sections = s.get("sections")
    if not isinstance(sections, list) or not sections:
        raise Broken("standard: `sections` must be a non-empty list")
    for sec in sections:
        if sec.get("kind") not in SECTION_KINDS:
            raise Broken("standard: section %r has kind %r, not one of %s" % (sec.get("id"), sec.get("kind"), ", ".join(sorted(SECTION_KINDS))))
        if sec["kind"] == "fixed" and not HEADING_RE.match(sec.get("heading") or ""):
            raise Broken("standard: fixed section %r needs a `heading` such as \"## Projects\"" % sec.get("id"))
    o = s.get("options")
    if not isinstance(o, dict):
        raise Broken("standard: `options` must be an object")
    rc = o.get("recent_changes")
    if not (rc is False or (isinstance(rc, int) and not isinstance(rc, bool) and rc >= 1)):
        raise Broken("standard: options.recent_changes must be false or a count of at least 1")
    b = o.get("badges")
    if not (b is False or (isinstance(b, list) and b and set(b) <= BADGE_KINDS)):
        raise Broken("standard: options.badges must be false or a list of kinds from %s" % ", ".join(sorted(BADGE_KINDS)))
    sl = o.get("status_labels")
    if not (sl is False or (isinstance(sl, list) and sl and all(isinstance(x, str) and x.strip() for x in sl))):
        raise Broken("standard: options.status_labels must be false or a list of labels")
    if o.get("grouping") not in GROUPINGS:
        raise Broken("standard: options.grouping must be one of %s" % ", ".join(sorted(GROUPINGS)))
    if not isinstance(o.get("featured"), list):
        raise Broken("standard: options.featured must be a list of repository names")
    if o.get("order") not in ORDERS:
        raise Broken("standard: options.order must be one of %s" % ", ".join(sorted(ORDERS)))
    st = o.get("shared_text")
    if not isinstance(st, list) or not all(isinstance(x, dict) and x.get("id") and isinstance(x.get("text"), str) and x["text"] for x in st):
        raise Broken("standard: options.shared_text must be a list of {id, text}")
    cats = s.get("categories", [])
    if not isinstance(cats, list) or not all(isinstance(c, dict) and c.get("name") and isinstance(c.get("repos"), list) for c in cats):
        raise Broken("standard: `categories` must be a list of {name, repos}")
    if o["grouping"] == "category" and not cats:
        raise Broken("standard: grouping by category needs at least one category")
    for key in ("exclude", "include"):
        items = s.get(key, [])
        if not isinstance(items, list):
            raise Broken("standard: `%s` must be a list" % key)
        for it in items:
            if not (isinstance(it, dict) and it.get("repo") and len(str(it.get("reason", "")).split()) >= 3):
                raise Broken("standard: every `%s` entry needs a repo and a reason of at least three words" % key)
    skips = s.get("skip_releases", [])
    if not isinstance(skips, list) or not all(
        isinstance(it, dict) and it.get("repo") and it.get("tag") and len(str(it.get("reason", "")).split()) >= 3 for it in skips
    ):
        raise Broken("standard: every `skip_releases` entry needs a repo, a tag and a reason of at least three words")


# ---------------------------------------------------------------- parsing


def strip_md(text: str) -> str:
    text = LINK_RE.sub(lambda m: m.group(1), text)
    text = re.sub(r"<[^>]+>", " ", text)
    return text


def norm_heading(text: str) -> str:
    text = strip_md(text)
    text = "".join(ch if (ch.isalnum() or ch in " -'.&") else " " for ch in text)
    return " ".join(text.lower().split())


def is_emoji(ch: str) -> bool:
    return ord(ch) >= 0x2190 and unicodedata.category(ch) in ("So", "Sk", "Cn")


class Page:
    def __init__(self, text: str, org: str):
        self.text = text
        self.lines = text.split("\n")
        self.org = org.lower()
        self.headings = []  # (line, level, norm)
        self.entries = []  # (line, repo_lower)
        in_code = False
        for i, line in enumerate(self.lines):
            if line.lstrip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            h = HEADING_RE.match(line)
            if h:
                self.headings.append((i, len(h.group(1)), norm_heading(h.group(2))))
            if ENTRY_LINE_RE.match(line):
                m = LINK_RE.search(line)
                if m:
                    repo = self.repo_root(m.group(2))
                    if repo:
                        self.entries.append((i, repo))

    def repo_root(self, url: str) -> str | None:
        m = GH_RE.match(url)
        if not m or m.group(1).lower() != self.org:
            return None
        rest = (m.group(3) or "").strip("/")
        if rest:
            return None
        return m.group(2).lower().removesuffix(".git")

    def gh_links(self):
        """(line, repo_lower, rest_of_path) for every link into this organization."""
        for i, line in enumerate(self.lines):
            urls = [m.group(2) for m in LINK_RE.finditer(line)] + HTML_URL_RE.findall(line)
            for u in urls:
                m = GH_RE.match(u)
                if m and m.group(1).lower() == self.org:
                    yield i, m.group(2).lower().removesuffix(".git"), unquote(m.group(3) or "")

    def badges(self):
        """(line, url) for every shields or badgen image."""
        for i, line in enumerate(self.lines):
            for u in IMG_MD_RE.findall(line) + IMG_HTML_RE.findall(line):
                host = urlparse(u).netloc.lower()
                if "shields.io" in host or "badgen" in host:
                    yield i, u

    def listed(self) -> set:
        return {r for _, r in self.entries}


def badge_kind(url: str) -> str:
    path = unquote(urlparse(url).path).lower()
    if path.startswith(("/github/v/release", "/github/v/tag", "/github/release", "/github/tag")):
        return "release"
    if path.startswith("/github/license"):
        return "license"
    if path.startswith(("/github/actions/", "/github/workflow/", "/github/checks-status")):
        return "ci"
    if path.startswith("/badge/dynamic/"):
        return "dynamic"
    if path.startswith("/badge/") or path.startswith("/static/"):
        return "static"
    return "other"


def label_segments(page: Page):
    """(line, segment) for every short emoji-led segment: Catalog's ` · ` lines and table cells."""
    for i, line in enumerate(page.lines):
        parts = []
        stripped = line.strip()
        if stripped.startswith("|"):
            if re.fullmatch(r"\|?[\s:|-]+\|?", stripped):
                continue
            parts = stripped.strip("|").split("|")
        elif " · " in line:
            parts = re.split(r"<br\s*/?>", line, maxsplit=1)[0].split(" · ")
        for p in parts:
            seg = strip_md(p).strip().strip("*_").strip()
            if seg and is_emoji(seg[0]) and len(seg.split()) <= 5:
                yield i, seg


# ---------------------------------------------------------------- rules


def check(page_text: str, facts: dict, standard: dict | None, pr_body: str | None, instructions_given: bool):
    """Return (findings, notes). Each finding starts with its rule id."""
    findings, notes = [], []
    org = facts["org"]
    page = Page(page_text, org)
    covered = {r["name"].lower(): r for r in facts["covered"]}
    forks = {r["name"].lower(): r for r in facts["public_forks"]}
    archived = {n.lower() for n in facts["archived"]}
    digests = set(facts["private_digests"])
    excluded = {e["repo"].lower() for e in (standard or {}).get("exclude", [])}
    included = {e["repo"].lower() for e in (standard or {}).get("include", [])}
    universe = dict(covered)
    universe.update({k: v for k, v in forks.items() if k in included})
    listed = page.listed()

    def where(i):
        return "line %d" % (i + 1)

    # R1
    for name in sorted(universe):
        if name not in listed and name not in excluded:
            findings.append("R1: %s is covered but has no entry on the page and is not excluded" % universe[name]["name"])

    # R2
    seen = set()
    for i, repo, _rest in list(page.gh_links()) + [(i, r, "") for i, r in page.entries]:
        if repo in seen or repo == ".github" or repo in universe:
            continue
        seen.add(repo)
        if hashlib.sha256(repo.encode("utf-8")).hexdigest() in digests:
            findings.append("R2: %s links to a private repository (name withheld)" % where(i))
        elif repo in archived:
            findings.append("R2: %s links to %s, which is archived" % (where(i), repo))
        elif repo in forks:
            findings.append("R2: %s links to %s, a fork the standard does not include" % (where(i), repo))
        else:
            findings.append("R2: %s links to %s, which is not a public repository of %s" % (where(i), repo, org))

    # R3 and R4
    first_release = {}
    for i, repo, rest in page.gh_links():
        m = re.match(r"^/releases/tag/(.+?)/?$", rest)
        if not m or repo not in universe:
            continue
        tag = m.group(1)
        if repo not in first_release:
            first_release[repo] = (i, tag)
        if tag not in universe[repo]["tags"]:
            findings.append("R4: %s links to release %s of %s, a tag that does not exist" % (where(i), tag, repo))
    skipped = {(s["repo"].lower(), s["tag"]) for s in (standard or {}).get("skip_releases", [])}
    for repo, (i, tag) in sorted(first_release.items()):
        newest = next((r["tag"] for r in universe[repo].get("releases", []) if (repo, r["tag"]) not in skipped), None)
        if newest and newest != tag:
            findings.append("R3: %s names %s as the newest release of %s; the newest is %s (skip it in the standard, with a reason, only if it changed nothing a user would notice)"
                            % (where(i), tag, repo, newest))

    # R5 and R6
    badges = list(page.badges())
    for i, url in badges:
        decoded = unquote(url)
        if re.search(r"\[\d+\]", decoded):
            notes.append("R6: %s has a badge that reads a list by position (%s); adding an entry to that list changes what it shows"
                         % (where(i), re.search(r"[\w$.]*\[\d+\][\w.]*", decoded).group(0)))
        parsed = urlparse(url)
        path = unquote(parsed.path)
        segs = [s for s in path.split("/") if s]
        if segs and segs[0].lower() == "github":
            low = [s.lower() for s in segs]
            if page.org not in low:
                findings.append("R5: %s has a badge that names another owner" % where(i))
                continue
            k = low.index(page.org)
            repo = low[k + 1] if k + 1 < len(low) else ""
            if repo not in listed and repo not in universe:
                findings.append("R5: %s has a badge for %s, which the page does not list" % (where(i), repo or "no repository"))
        for target in parse_qs(parsed.query).get("url", []):
            t = urlparse(target)
            if "githubusercontent.com" in t.netloc or t.netloc.endswith("github.com"):
                tsegs = [s.lower() for s in t.path.split("/") if s]
                if len(tsegs) < 2 or tsegs[0] != page.org:
                    findings.append("R5: %s has a badge that reads from another owner" % where(i))
                elif tsegs[1] not in universe and tsegs[1] not in listed:
                    findings.append("R5: %s has a badge that reads from %s, which is not covered" % (where(i), tsegs[1]))

    # R7
    for label, text in (("the page", page_text), ("the pull request body", pr_body or "")):
        hits = set()
        for n, line in enumerate(text.split("\n")):
            for variant in (line, unquote(line)):
                for tok in TOKEN_RE.findall(variant):
                    tok = tok.strip("._-").lower()
                    if tok and hashlib.sha256(tok.encode("utf-8")).hexdigest() in digests:
                        hits.add(n + 1)
        for n in sorted(hits):
            findings.append("R7: %s names a private repository at line %d (name withheld)" % (label, n))

    # R8 to R13
    if standard is not None:
        o = standard["options"]
        # R8: sections in order
        expected = []
        for sec in standard["sections"]:
            if sec["kind"] == "fixed":
                h = HEADING_RE.match(sec["heading"])
                expected.append((len(h.group(1)), norm_heading(h.group(2)), sec["heading"], None))
            else:
                lvl = int(sec.get("level", 2))
                for c in standard.get("categories", []):
                    expected.append((lvl, norm_heading(c["name"]), "%s %s" % ("#" * lvl, c["name"]), c))
        pos = 0
        cat_lines = {}
        for lvl, want, shown, cat in expected:
            hit = None
            for j in range(pos, len(page.headings)):
                line, hl, hn = page.headings[j]
                if hl == lvl and (hn == want or (cat is not None and hn.endswith(want))):
                    hit = j
                    break
            if hit is None:
                findings.append("R8: section `%s` is missing or out of order" % shown)
                continue
            pos = hit + 1
            if cat is not None:
                cat_lines[cat["name"]] = (page.headings[hit][0], lvl)
        if o["grouping"] == "category":
            for c in standard.get("categories", []):
                if c["name"] not in cat_lines:
                    continue
                start, lvl = cat_lines[c["name"]]
                end = next((ln for ln, hl, _ in page.headings if ln > start and hl <= lvl), len(page.lines))
                inside = {r for ln, r in page.entries if start < ln < end}
                for repo in c["repos"]:
                    r = repo.lower()
                    if r in excluded or r not in universe:
                        continue
                    if r in listed and r not in inside:
                        findings.append("R8: %s is listed outside its category, %s" % (repo, c["name"]))
        for i, line in enumerate(page.lines):
            if MARKER in line:
                findings.append("R8: %s still holds a scaffold marker" % where(i))
        # R9
        for passage in o["shared_text"]:
            if passage["text"].replace("\r\n", "\n") not in page_text:
                findings.append("R9: shared text `%s` is missing or differs from the standard" % passage["id"])
        # R10
        for i, url in badges:
            kind = badge_kind(url)
            if o["badges"] is False:
                findings.append("R10: %s has a badge, and the standard turns badges off" % where(i))
            elif kind not in o["badges"]:
                findings.append("R10: %s has a %s badge, which the standard does not allow" % (where(i), kind))
        # R11
        for i, line in enumerate(page.lines):
            if not RECENT_RE.match(line):
                continue
            if o["recent_changes"] is False:
                findings.append("R11: %s starts a recent-changes block, and the standard turns them off" % where(i))
                continue
            count, j = 0, i + 1
            while j < len(page.lines) and (not page.lines[j].strip() or BULLET_RE.match(page.lines[j])):
                if BULLET_RE.match(page.lines[j]):
                    count += 1
                elif count:
                    break
                j += 1
            if count > o["recent_changes"]:
                findings.append("R11: the recent-changes block at %s has %d entries; the standard allows %d" % (where(i), count, o["recent_changes"]))
        # R12
        vocab = {" ".join(v.split()) for v in (o["status_labels"] or [])}
        for i, seg in label_segments(page):
            seg = " ".join(seg.split())
            if o["status_labels"] is False:
                findings.append("R12: %s has the label `%s`, and the standard turns status labels off" % (where(i), seg))
            elif seg not in vocab:
                findings.append("R12: %s has the label `%s`, which is not in the vocabulary" % (where(i), seg))
        # R13
        featured = [f.lower() for f in o["featured"] if f.lower() not in excluded]
        order = []
        for _, r in page.entries:
            if r not in order:
                order.append(r)
        if featured and order[: len(featured)] != featured:
            findings.append("R13: the first entries are %s; the featured repositories are %s"
                            % (", ".join(order[: len(featured)]) or "none", ", ".join(featured)))

    # R14
    if pr_body is not None:
        heads = {norm_heading(m.group(2)) for m in (HEADING_RE.match(l) for l in pr_body.split("\n")) if m}
        if "from the repositories" not in heads:
            findings.append("R14: the pull request body has no `From the repositories` heading")
        if instructions_given and "from your instructions" not in heads:
            findings.append("R14: instructions were given, and the pull request body has no `From your instructions` heading")

    return findings, notes


# ---------------------------------------------------------------- self-test


def _once(text: str, old: str, new: str) -> str:
    if text.count(old) < 1:
        raise Broken("self-test: the sample no longer contains %r, so a mutation cannot be applied" % old)
    return text.replace(old, new, 1)


def self_test() -> int:
    for name in ("facts.json", "standard.json", "README.md", "pr-body.md"):
        if not (SAMPLE_DIR / name).is_file():
            raise Broken("self-test: the sample %s is missing" % (SAMPLE_DIR / name))
    facts = read_json(SAMPLE_DIR / "facts.json")
    standard = read_json(SAMPLE_DIR / "standard.json")
    validate_facts(facts)
    validate_standard(standard)
    page = read_text(SAMPLE_DIR / "README.md")
    body = read_text(SAMPLE_DIR / "pr-body.md")
    findings, notes = check(page, facts, standard, body, True)
    if findings or notes:
        raise Broken("self-test: the committed sample fails its own checker: %s" % "; ".join(findings + notes))

    org = facts["org"]
    priv = SAMPLE_PRIVATE_NAME
    if hashlib.sha256(priv.encode("utf-8")).hexdigest() not in facts["private_digests"]:
        raise Broken("self-test: the sample facts do not carry the digest of the invented private name")
    s_off = json.loads(json.dumps(standard))
    s_off["options"]["badges"] = False
    mutations = [
        ("R1", _once(page, "### 🧰 [beta-kit](https://github.com/%s/beta-kit)" % org, "### 🧰 beta-kit"), standard, body, False),
        ("R2", _once(page, "## At a glance", "See [old-thing](https://github.com/%s/old-thing).\n\n## At a glance" % org), standard, body, False),
        ("R3", _once(page, "releases/tag/v1.2.0)", "releases/tag/v1.1.0)").replace("[v1.2.0]", "[v1.1.0]", 1), standard, body, False),
        ("R4", _once(page, "releases/tag/v1.1.0)", "releases/tag/v1.0.9)"), standard, body, False),
        ("R5", _once(page, "license/%s/alpha-tool" % org, "license/someone-else/alpha-tool"), standard, body, False),
        ("R6", _once(page, "![release](https://img.shields.io/github/v/release/%s/alpha-tool" % org,
                     "![pin](https://img.shields.io/badge/dynamic/json?url=https://raw.githubusercontent.com/%s/alpha-tool/main/list.json&query=%%24.items%%5B1%%5D.version)"
                     " ![release](https://img.shields.io/github/v/release/%s/alpha-tool" % (org, org)), standard, body, False),
        ("R7", page, standard, _once(body, "## From the repositories", "## From the repositories\n\nSee https://github.com/%s/%s for more." % (org, priv)), False),
        ("R8", _once(page, "## 🧹 Utilities", "## 🧹 Odds and ends"), standard, body, False),
        ("R9", _once(page, "Every project is built for daily use.", "Every project is built for weekly use."), standard, body, False),
        ("R10", page, s_off, body, False),
        ("R11", _once(page, "- [v1.0.0]", "- [v1.0.0](https://github.com/%s/alpha-tool/releases/tag/v1.0.0) (Jan 2026): An extra entry.\n- [v1.0.0]" % org), standard, body, False),
        ("R12", _once(page, "*🟢 Stable · Claude Code*", "*🔵 Gold · Claude Code*"), standard, body, False),
        ("R13", page, dict(standard, options=dict(standard["options"], featured=["beta-kit"])), body, False),
        ("R14", page, standard, body.replace("## From your instructions", "## Other changes"), True),
    ]
    proved = set()
    for rule, p, s, b, instr in mutations:
        f, n = check(p, facts, s, b, instr)
        if not [x for x in f + n if x.startswith(rule + ":")]:
            raise Broken("self-test: rule %s did not fail its mutation, so it cannot be trusted" % rule)
        proved.add(rule)
    if proved != set(RULE_IDS):
        raise Broken("self-test: rules without a mutation: %s" % ", ".join(sorted(set(RULE_IDS) - proved)))
    return len(proved)


# ---------------------------------------------------------------- main


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--page", type=Path)
    ap.add_argument("--facts", type=Path)
    ap.add_argument("--standard", type=Path)
    ap.add_argument("--pr-body", type=Path)
    ap.add_argument("--instructions-given", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    try:
        n = self_test()
        if a.self_test:
            print("CLEAN: canary proved, %d rules (%s) each fail their mutation of the committed sample." % (n, ", ".join(RULE_IDS)))
            return 0
        if not a.page or not a.facts:
            print("BROKEN: --page and --facts are required unless --self-test is given", file=sys.stderr)
            return 2
        facts = read_json(a.facts)
        validate_facts(facts)
        standard = None
        if a.standard:
            standard = read_json(a.standard)
            validate_standard(standard)
        page = read_text(a.page)
        body = read_text(a.pr_body) if a.pr_body else None
        findings, notes = check(page, facts, standard, body, a.instructions_given)
    except Broken as e:
        print("BROKEN: %s" % e)
        return 2
    for x in findings:
        print("FINDING %s" % x)
    for x in notes:
        print("NOTE %s" % x)
    if standard is None:
        print("SKIPPED: %s, because there is no standard. Run with --setup to establish one." % ", ".join(STANDARD_RULES))
    if findings:
        print("FINDINGS: canary proved, %d finding(s) against %s." % (len(findings), a.page))
        return 1
    print("CLEAN: canary proved, %s satisfies every rule that ran%s." % (a.page, " (%d note(s))" % len(notes) if notes else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
