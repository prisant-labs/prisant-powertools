#!/usr/bin/env python3
"""Render pulse.json into the self-contained dashboard.html.

USAGE
-----
  render.py --pulse pulse.json --out dashboard.html [--template assets/dashboard.html]

EXIT-CODE CONTRACT
------------------
  0  CLEAN   dashboard.html written
  2  BROKEN  pulse.json or the template could not be read, or was malformed

NEVER INTERPRET 2 AS CLEAN.

WHY THE CARDS ARE WRITTEN HERE, NOT BY THE PAGE'S OWN SCRIPT
-----------------------------------------------------------------
`pulse-check.py`'s R10 counts `class="repo-card"` elements with
`html.parser`, never a browser, so a card that only exists after a
`<script>` runs would be invisible to that count and the rule would prove
nothing (AC-22). Every piece of content the schema asks the dashboard to
show (the window label, totals, What's Next, Waiting on You, the
folder-grouped cards) is therefore rendered to static HTML here, from
`pulse.json`, with no literal date or week label living in the template
itself (AC-21). The embedded `<script type="application/json"
id="pulse-data">` block still carries the full `pulse.json`, and the
template's own `<script>` reads it, but only to drive the active-only,
has-waiting-items and folder filters over the cards that already exist;
it creates nothing.

WHY TOKEN SUBSTITUTION, NOT A TEMPLATE ENGINE
-----------------------------------------------
Stdlib only (spec Non-Functional Requirements, Portability). Each `__TOKEN__`
in `assets/dashboard.html` is replaced exactly once with `str.replace`;
an unmatched token is a build error, not a silently empty section, so a
mismatch between this script and the template fails loudly.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from pathlib import Path

DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "dashboard.html"

STATUS_LABELS = {
    "snapshot": "snapshot",
    "scout": "scouted",
    "carried": "carried",
    "sweep-only": "sweep-only",
}


class Broken(Exception):
    pass


def esc(text):
    return html.escape("" if text is None else str(text), quote=True)


def month_day(iso_date):
    try:
        d = dt.date.fromisoformat(iso_date)
    except (TypeError, ValueError):
        return esc(iso_date)
    return d.strftime("%b %-d") if sys.platform != "win32" else d.strftime("%b %#d")


def window_label(window):
    start = month_day(window.get("start"))
    end_date = window.get("end")
    try:
        end_dt = dt.date.fromisoformat(end_date)
        end = end_dt.strftime("%b %-d, %Y") if sys.platform != "win32" else end_dt.strftime("%b %#d, %Y")
    except (TypeError, ValueError):
        end = esc(end_date)
    return "%s to %s (%s)" % (start, end, esc(window.get("timezone", "")))


def totals_html(totals):
    order = [
        ("repos", "Repositories"), ("active", "Active"), ("dormant", "Dormant"),
        ("aliases", "Aliases"), ("commits_focus", "Commits"), ("tags_in_window", "Tags"),
        ("waiting_on_you", "Waiting on you"), ("snapshots_fresh", "Fresh snapshots"),
    ]
    rows = []
    for key, label in order:
        rows.append('      <li><strong>%s</strong>%s</li>' % (esc(totals.get(key, 0)), esc(label)))
    return "\n".join(rows)


def whats_next_html(items):
    if not items:
        return '      <li class="empty">Nothing ranked this window.</li>'
    rows = []
    for item in items:
        rows.append(
            '      <li>%s <span class="badge">%s</span> <span class="meta">%s - %s</span></li>'
            % (esc(item.get("item")), esc(item.get("who")), esc(item.get("repo")), esc(item.get("source")))
        )
    return "\n".join(rows)


def waiting_on_you_html(items):
    if not items:
        return '      <li class="empty">Nothing is waiting on you.</li>'
    rows = []
    for item in items:
        rows.append(
            '      <li>%s <span class="age-badge">%s day(s)</span> '
            '<span class="meta">%s - %s</span></li>'
            % (esc(item.get("item")), esc(item.get("age_days")), esc(item.get("repo")), esc(item.get("source")))
        )
    return "\n".join(rows)


def folder_options_html(folders):
    return "\n".join('        <option value="%s">%s</option>' % (esc(f), esc(f)) for f in folders)


def status_source_detail(repo):
    source = repo.get("status_source")
    label = STATUS_LABELS.get(source, esc(source))
    if source == "snapshot":
        snap_date = ((repo.get("sweep") or {}).get("snapshot_utc") or "")[:10]
        return "%s (%s)" % (label, esc(snap_date)) if snap_date else label
    if source == "carried":
        carried_from = repo.get("carried_from")
        return "%s since %s" % (label, esc(carried_from)) if carried_from else label
    return label


def render_card(repo):
    sweep = repo.get("sweep") or {}
    status = repo.get("status") or {}
    waiting = status.get("waiting_on_you") or []
    tags = sweep.get("tags_in_window") or []
    tags_label = ", ".join("%s (%s)" % (t.get("tag"), t.get("date")) for t in tags) if tags else "none"
    activity = repo.get("activity") or "dormant"
    activity_class = "badge-active" if activity == "active" else "badge-dormant"

    markers = []
    if repo.get("alias_of"):
        markers.append('<span class="marker marker-alias">alias of %s</span>' % esc(repo["alias_of"]))
    if repo.get("conflicts"):
        markers.append('<span class="marker marker-conflict">%d conflict(s)</span>' % len(repo["conflicts"]))
    if repo.get("unprotected_work"):
        markers.append('<span class="marker marker-unprotected">unprotected work</span>')
    markers_html = ('<p class="markers">%s</p>' % "".join(markers)) if markers else ""

    hint_html = ""
    if repo.get("current_status_candidate"):
        hint_html = '<p class="hint">Run /plab-current-status here.</p>'

    short_name = repo.get("repo", "").split("/")[-1]

    return (
        '<article class="repo-card" data-repo="%s" data-activity="%s" data-folder="%s" data-waiting-count="%d">\n'
        '  <h4>%s <span class="badge %s">%s</span></h4>\n'
        '  <dl>\n'
        '    <dt>Commits</dt><dd>%s</dd>\n'
        '    <dt>Tags</dt><dd>%s</dd>\n'
        '    <dt>Ahead / behind</dt><dd>%s / %s</dd>\n'
        '    <dt>Dirty files</dt><dd>%s</dd>\n'
        '    <dt>Status source</dt><dd>%s</dd>\n'
        '  </dl>\n'
        '  %s\n'
        '  %s\n'
        '</article>'
    ) % (
        esc(repo.get("repo")), esc(activity), esc(repo.get("folder")), len(waiting),
        esc(short_name), activity_class, esc(activity),
        esc(sweep.get("commits_focus", 0)), tags_label,
        esc(sweep.get("ahead", 0)), esc(sweep.get("behind", 0)),
        esc(sweep.get("dirty_files", 0)), status_source_detail(repo),
        markers_html, hint_html,
    )


def cards_html(repos):
    folders = {}
    order = []
    for repo in repos:
        folder = repo.get("folder") or ""
        if folder not in folders:
            folders[folder] = []
            order.append(folder)
        folders[folder].append(repo)

    blocks = []
    for folder in order:
        cards = "\n".join(render_card(r) for r in folders[folder])
        blocks.append(
            '<div class="folder-group" data-folder="%s">\n'
            '  <h3>%s</h3>\n'
            '  <div class="card-row">\n%s\n  </div>\n'
            '</div>' % (esc(folder), esc(folder), cards)
        )
    return "\n".join(blocks)


def embed_json(pulse):
    # </script> inside the JSON payload would close the embedding tag early;
    # escape the two characters that make that string.
    return json.dumps(pulse, ensure_ascii=False).replace("</", "<\\/")


def render(pulse, template_text):
    folders = sorted({r.get("folder") or "" for r in pulse.get("repos", [])})
    replacements = {
        "__TITLE__": "Project Pulse",
        "__WINDOW_LABEL__": window_label(pulse.get("window", {})),
        "__TOTALS__": totals_html(pulse.get("totals", {})),
        "__WHATS_NEXT__": whats_next_html(pulse.get("whats_next", [])),
        "__WAITING_ON_YOU__": waiting_on_you_html(pulse.get("waiting_on_you", [])),
        "__FOLDER_OPTIONS__": folder_options_html(folders),
        "__CARDS__": cards_html(pulse.get("repos", [])),
        "__PULSE_JSON__": embed_json(pulse),
    }
    out = template_text
    for token, value in replacements.items():
        if token not in out:
            raise Broken("template is missing the token %s" % token)
        out = out.replace(token, value)
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Render pulse.json into dashboard.html.")
    parser.add_argument("--pulse", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    args = parser.parse_args(argv)

    try:
        pulse = json.loads(Path(args.pulse).read_text(encoding="utf-8-sig"))
        template_text = Path(args.template).read_text(encoding="utf-8-sig")
        output = render(pulse, template_text)
        Path(args.out).write_text(output, encoding="utf-8")
    except (OSError, ValueError, Broken) as exc:
        print("BROKEN: %s" % exc)
        return 2
    print("CLEAN: wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
