#!/usr/bin/env python3
"""Write an organization's profile standard, profile/standard.json, from a base and a set of answers.

USAGE
-----
  write-standard.py --base catalog|compact|showcase|custom --answers <answers.json> --out <standard.json>
  write-standard.py --base adopted --from-page <README.md> --facts <facts.json> [--answers <answers.json>] --out <standard.json>

The answers are what the --setup interview established (references/setup-interview.md).
Every key is optional except `org` and `display_name`, which a built-in base needs
for its title, and `sections`, which a custom standard needs:

  {"org": "example-org", "display_name": "Example Org",
   "options": {"badges": false, ...},          # overrides the base's defaults
   "categories": [{"name": "Tools", "repos": ["alpha-tool"]}],
   "exclude": [{"repo": "x", "reason": "..."}], "include": [...],
   "skip_releases": [{"repo": "x", "tag": "v1.0.1", "reason": "..."}],
   "sections": [...]}                          # custom only

THE ADOPTED PATH
----------------
`--base adopted` reads an existing page and records what it already does: its
level-1 and level-2 headings as sections in order, a level-2 heading with entries
under it as a category holding those repositories, the badge kinds it uses, its
longest recent-changes block, and its status labels and tags. A covered
repository with no entry becomes an exclusion, and a fork with an entry becomes
an inclusion, each with a reason that asks the maintainer to confirm it. The
agent shows the result to the maintainer before it is used, because a page can
hold an accident that adoption would turn into a rule (RM-01 requirement 9).

EXIT-CODE CONTRACT
------------------
  0  the standard was written and passes the checker's format validation
  2  an input is missing or invalid, or the result would not validate; nothing is written
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("profile_check", HERE / "profile-check.py")
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

STATUS_VOCAB = ["🟢 Stable", "🟡 Beta", "🟠 Pre-release", "🟤 Maintenance"]
TAG_VOCAB = ["🚀 Start here", "🆕 New", "🧪 Experimental"]

BASE_DEFAULTS = {
    "catalog": {
        "sections": [
            {"id": "header", "kind": "fixed", "heading": "# {display_name}"},
            {"id": "glance", "kind": "fixed", "heading": "## At a glance"},
            {"id": "categories", "kind": "categories", "level": 2},
        ],
        "options": {
            "recent_changes": 3,
            "badges": ["release", "license"],
            "status_labels": STATUS_VOCAB + TAG_VOCAB,
            "grouping": "category",
            "featured": [],
            "order": "category",
            "shared_text": [],
        },
    },
    "compact": {
        "sections": [
            {"id": "header", "kind": "fixed", "heading": "# {display_name}"},
            {"id": "projects", "kind": "fixed", "heading": "## Projects"},
        ],
        "options": {
            "recent_changes": False,
            "badges": False,
            "status_labels": STATUS_VOCAB,
            "grouping": "none",
            "featured": [],
            "order": "alphabetical",
            "shared_text": [],
        },
    },
    "showcase": {
        "sections": [
            {"id": "header", "kind": "fixed", "heading": "# {display_name}"},
            {"id": "featured", "kind": "fixed", "heading": "## Featured"},
            {"id": "more", "kind": "fixed", "heading": "## More projects"},
        ],
        "options": {
            "recent_changes": False,
            "badges": ["release"],
            "status_labels": STATUS_VOCAB,
            "grouping": "none",
            "featured": [],
            "order": "latest_release",
            "shared_text": [],
        },
    },
    "custom": {
        "sections": None,
        "options": {
            "recent_changes": False,
            "badges": False,
            "status_labels": False,
            "grouping": "none",
            "featured": [],
            "order": "alphabetical",
            "shared_text": [],
        },
    },
}


class Broken(Exception):
    pass


def adopt(page_text: str, facts: dict) -> dict:
    page = pc.Page(page_text, facts["org"])
    raw_heads = []
    for line, level, _norm in page.headings:
        if level <= 2:
            text = pc.HEADING_RE.match(page.lines[line]).group(2)
            raw_heads.append((line, level, text))
    if not raw_heads:
        raise Broken("the page has no level-1 or level-2 heading to adopt")

    covered = {r["name"].lower(): r["name"] for r in facts["covered"]}
    forks = {r["name"].lower(): r["name"] for r in facts["public_forks"]}
    known = dict(covered)
    known.update(forks)

    # A level-2 heading with entries under it is a category.
    cats, kinds_order = [], []
    for idx, (line, level, text) in enumerate(raw_heads):
        end = next((ln for ln, lv, _ in raw_heads[idx + 1:] if lv <= 2), len(page.lines))
        repos = []
        for ln, repo in page.entries:
            if line < ln < end and repo in known and known[repo] not in repos:
                repos.append(known[repo])
        if level == 2 and repos:
            name = " ".join(pc.strip_md(text).split())
            while name and (pc.is_emoji(name[0]) or name[0] in "️ "):
                name = name[1:]
            cats.append({"name": name, "repos": repos, "_line": line})
            kinds_order.append("category")
        else:
            kinds_order.append("fixed")
    # Group by category only when the categories form one unbroken run of headings.
    shape = "".join("c" if k == "category" else "f" for k in kinds_order)
    grouped = bool(cats) and re.fullmatch(r"f*c+f*", shape) is not None

    sections = []
    placed = False
    for (line, level, text), kind in zip(raw_heads, kinds_order):
        if kind == "category" and grouped:
            if not placed:
                sections.append({"id": "categories", "kind": "categories", "level": 2})
                placed = True
            continue
        sections.append({"id": "s%d" % (len(sections) + 1), "kind": "fixed", "heading": "%s %s" % ("#" * level, text.strip())})

    kinds = []
    for _, url in page.badges():
        k = pc.badge_kind(url)
        if k not in kinds:
            kinds.append(k)
    longest = 0
    for i, line in enumerate(page.lines):
        if pc.RECENT_RE.match(line):
            count, j = 0, i + 1
            while j < len(page.lines) and (not page.lines[j].strip() or pc.BULLET_RE.match(page.lines[j])):
                if pc.BULLET_RE.match(page.lines[j]):
                    count += 1
                elif count:
                    break
                j += 1
            longest = max(longest, count)
    labels = []
    for _, seg in pc.label_segments(page):
        seg = " ".join(seg.split())
        if seg not in labels:
            labels.append(seg)

    listed = page.listed()
    exclude = [{"repo": covered[r], "reason": "not listed when the standard was adopted from the page; confirm"}
               for r in sorted(covered) if r not in listed]
    include = [{"repo": forks[r], "reason": "listed on the page when the standard was adopted; confirm"}
               for r in sorted(forks) if r in listed]
    title = next((t for _, lv, t in raw_heads if lv == 1), facts["org"])
    return {
        "display_name": " ".join(pc.strip_md(title).split()),
        "sections": sections,
        "options": {
            "recent_changes": longest or False,
            "badges": kinds or False,
            "status_labels": labels or False,
            "grouping": "category" if grouped else "none",
            "featured": [],
            "order": "category" if grouped else "alphabetical",
            "shared_text": [],
        },
        "categories": [{"name": c["name"], "repos": c["repos"]} for c in cats] if grouped else [],
        "exclude": exclude,
        "include": include,
    }


def build(base: str, answers: dict, page_text: str | None, facts: dict | None) -> dict:
    if base == "adopted":
        if page_text is None or facts is None:
            raise Broken("--base adopted needs --from-page and --facts")
        std = adopt(page_text, facts)
        std = {"format": 1, "org": facts["org"], "base": "adopted", **std}
    else:
        d = BASE_DEFAULTS[base]
        org = answers.get("org")
        display = answers.get("display_name")
        if not org or not display:
            raise Broken("the answers need `org` and `display_name`")
        if base == "custom":
            if not answers.get("sections"):
                raise Broken("a custom standard needs `sections` in the answers")
            sections = answers["sections"]
        else:
            sections = [dict(s, heading=s["heading"].format(display_name=display)) if "heading" in s else dict(s) for s in d["sections"]]
        std = {
            "format": 1,
            "org": org,
            "display_name": display,
            "base": base,
            "sections": sections,
            "options": json.loads(json.dumps(d["options"])),
            "categories": [],
            "exclude": [],
            "include": [],
        }
    for key in ("display_name", "categories", "exclude", "include", "skip_releases"):
        if key in answers:
            std[key] = answers[key]
    for k, v in (answers.get("options") or {}).items():
        if k not in std["options"]:
            raise Broken("unknown option `%s`; the options are %s" % (k, ", ".join(sorted(std["options"]))))
        std["options"][k] = v
    if base == "adopted" and answers.get("sections"):
        std["sections"] = answers["sections"]
    std.setdefault("skip_releases", [])
    if base == "showcase" and not std["options"]["featured"]:
        raise Broken("a Showcase standard needs at least one featured repository in options.featured")
    try:
        pc.validate_standard(std)
    except pc.Broken as e:
        raise Broken(str(e))
    return std


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--base", required=True, choices=sorted(pc.BASES))
    ap.add_argument("--answers", type=Path)
    ap.add_argument("--from-page", type=Path)
    ap.add_argument("--facts", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        answers = pc.read_json(a.answers) if a.answers else {}
        page = pc.read_text(a.from_page) if a.from_page else None
        facts = pc.read_json(a.facts) if a.facts else None
        std = build(a.base, answers, page, facts)
    except (Broken, pc.Broken) as e:
        print("BROKEN: %s" % e, file=sys.stderr)
        return 2
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(std, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("wrote %s (base %s, %d sections, %d categories, %d exclusions, %d inclusions)"
          % (a.out, std["base"], len(std["sections"]), len(std["categories"]), len(std["exclude"]), len(std["include"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
