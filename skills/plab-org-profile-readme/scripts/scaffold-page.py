#!/usr/bin/env python3
"""Write a first profile README from a standard and the facts, with every fact filled and every prose slot marked.

USAGE
-----
  scaffold-page.py --standard <standard.json> --facts <facts.json> --out <README.md>

Used when an organization has a standard and no page (RM-01 AC-18), and at the
end of --setup when no page exists. Every heading, entry, status label, badge
and recent-release link is filled from the facts. Every sentence a person should
write is a marker, `<!-- describe: <what> -->`, which the agent replaces from the
repository's own README and releases. The checker's R8 rejects a page that still
holds a marker, so a scaffold can never be opened as a pull request unfinished.

Status labels follow Catalog's rule: Stable when the newest stable release is
1.0 or later, Beta when the repository has any release, Pre-release otherwise.
A label is written only when the standard's vocabulary holds it.

EXIT-CODE CONTRACT
------------------
  0  the page was written
  2  an input is missing or invalid, or a covered repository has no category in
     a standard that groups by category; the repository is named and nothing is written
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("profile_check", HERE / "profile-check.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


class Broken(Exception):
    pass


def major(tag: str) -> int:
    m = re.search(r"(\d+)", tag or "")
    return int(m.group(1)) if m else 0


def status(repo: dict, vocab) -> str | None:
    if repo.get("latest_stable") and major(repo["latest_stable"]["tag"]) >= 1:
        want = "Stable"
    elif repo.get("releases"):
        want = "Beta"
    else:
        want = "Pre-release"
    for v in vocab or []:
        if v.split(None, 1)[-1] == want:
            return v
    return None


def month(iso: str | None) -> str:
    if not iso:
        return "date unknown"
    return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %Y")


def badges(org: str, repo: dict, kinds) -> str:
    out = []
    name = repo["name"]
    if kinds and "release" in kinds and repo.get("releases"):
        out.append("![release](https://img.shields.io/github/v/release/%s/%s?display_name=tag&style=flat-square)" % (org, name))
    if kinds and "license" in kinds and repo.get("license") and repo["license"] != "NOASSERTION":
        out.append("![license](https://img.shields.io/github/license/%s/%s?style=flat-square)" % (org, name))
    return " ".join(out)


def ordered(repos: list[dict], order: str, featured: list[str]) -> list[dict]:
    if order == "latest_release":
        key = lambda r: ((r.get("newest_release") or {}).get("published_at") or "")
        repos = sorted(repos, key=key, reverse=True)
    elif order == "alphabetical":
        repos = sorted(repos, key=lambda r: r["name"].lower())
    feat = [f.lower() for f in featured]
    first = [r for f in feat for r in repos if r["name"].lower() == f]
    return first + [r for r in repos if r["name"].lower() not in feat]


def project_block(org: str, repo: dict, o: dict, level: int) -> list[str]:
    url = "https://github.com/%s/%s" % (org, repo["name"])
    lines = ["%s [%s](%s)" % ("#" * level, repo["name"], url), ""]
    label = status(repo, o["status_labels"])
    if label:
        lines += ["*%s*" % label, ""]
    b = badges(org, repo, o["badges"])
    if b:
        lines += [b, ""]
    lines += ["<!-- describe: %s -->" % repo["name"], ""]
    if o["recent_changes"] and repo.get("releases"):
        lines += ["**Recent releases:**", ""]
        for r in repo["releases"][: o["recent_changes"]]:
            lines.append("- [%s](%s/releases/tag/%s) (%s): <!-- describe: %s %s -->" % (r["tag"], url, r["tag"], month(r["published_at"]), repo["name"], r["tag"]))
        lines.append("")
    return lines


def scaffold(std: dict, facts: dict) -> str:
    org = facts["org"]
    o = std["options"]
    excluded = {e["repo"].lower() for e in std.get("exclude", [])}
    included = {e["repo"].lower() for e in std.get("include", [])}
    repos = [r for r in facts["covered"] if r["name"].lower() not in excluded]
    repos += [r for r in facts["public_forks"] if r["name"].lower() in included and r["name"].lower() not in excluded]
    by_name = {r["name"].lower(): r for r in repos}
    repos = ordered(repos, o["order"], o["featured"])

    cats = []
    if o["grouping"] == "category":
        placed = set()
        for c in std["categories"]:
            members = [by_name[n.lower()] for n in c["repos"] if n.lower() in by_name]
            placed |= {m["name"].lower() for m in members}
            cats.append((c["name"], members))
        missing = [r["name"] for r in repos if r["name"].lower() not in placed]
        if missing:
            raise Broken("these covered repositories have no category in the standard: %s. Add each to a category, or exclude it with a reason" % ", ".join(missing))

    out = []
    for sec in std["sections"]:
        if sec["kind"] == "categories":
            lvl = int(sec.get("level", 2))
            for name, members in cats:
                out += ["---", "", "%s %s" % ("#" * lvl, name), "", "<!-- describe: category %s -->" % name, ""]
                for r in members:
                    out += project_block(org, r, o, lvl + 1)
            continue
        heading = sec["heading"]
        out += [heading, ""]
        norm = pc.norm_heading(pc.HEADING_RE.match(heading).group(2))
        if heading.startswith("# "):
            out += ["<!-- describe: what %s makes, in one sentence -->" % std.get("display_name", org), ""]
            for passage in o["shared_text"]:
                out += [passage["text"], ""]
        elif norm == "at a glance":
            for name, members in cats or [(None, repos)]:
                if name:
                    out += ["### %s" % name, ""]
                for r in members:
                    label = status(r, o["status_labels"])
                    out += ["- **[%s](#%s)**%s<br><!-- describe: %s, one line -->" % (r["name"], r["name"].lower(), " · %s" % label if label else "", r["name"]), ""]
        elif norm == "projects":
            out += ["| Project | Description | Status | Latest release |", "|---|---|---|---|"]
            for r in repos:
                url = "https://github.com/%s/%s" % (org, r["name"])
                rel = r.get("newest_release")
                rel_cell = "[%s](%s/releases/tag/%s)" % (rel["tag"], url, rel["tag"]) if rel else "None yet"
                out.append("| [%s](%s) | <!-- describe: %s, one line --> | %s | %s |" % (r["name"], url, r["name"], status(r, o["status_labels"]) or "", rel_cell))
            out.append("")
        elif norm == "featured":
            for r in repos[: len(o["featured"])]:
                out += project_block(org, r, o, 3)
        elif norm == "more projects":
            for r in repos[len(o["featured"]):]:
                out += ["- [%s](https://github.com/%s/%s): <!-- describe: %s, one line -->" % (r["name"], org, r["name"], r["name"]), ""]
        else:
            out += ["<!-- describe: section %s -->" % sec.get("id", heading), ""]
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--standard", type=Path, required=True)
    ap.add_argument("--facts", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        std = pc.read_json(a.standard)
        pc.validate_standard(std)
        facts = pc.read_json(a.facts)
        pc.validate_facts(facts)
        text = scaffold(std, facts)
    except (Broken, pc.Broken) as e:
        print("BROKEN: %s" % e, file=sys.stderr)
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s with %d prose markers to replace" % (a.out, text.count(pc.MARKER)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
