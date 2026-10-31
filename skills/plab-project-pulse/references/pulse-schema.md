# Pulse data files

The shapes every `plab-project-pulse` script reads and writes. `pulse-check.py` enforces `pulse.json` against this document; the other shapes are checked by the scripts' tests. Every file is UTF-8 JSON. Dates are local dates in the configured zone, `YYYY-MM-DD`; times are UTC ISO 8601 with a `Z`. A field marked optional may be absent; every other field is required and may be `null` only where its type says so.

## The flow

```
discover.py ─┐
sweep.py ────┼─> derive-pulse-facts.py ──> pulse-facts.json ─┐
gh (optional)┘                                                 │
log readers ──> digest.jsonl ──────────────────────────────────┤
scouts ──> scouts.json ────────────────────────────────────────┼─> build-pulse.py ──> pulse.json ──> render.py ──> dashboard.html
main loop ──> curation.json ───────────────────────────────────┘          │
                                                                          └──> state.json (updated after validation)
```

## `pulse-facts.json`, written by `derive-pulse-facts.py`

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-30T16:00:00Z",
  "mode": "week",
  "window": {"start": "2026-10-24", "end": "2026-10-30", "prior_start": "2026-10-17", "timezone": "America/Los_Angeles"},
  "roots": ["/abs/root"],
  "max_depth": 2,
  "repos": [
    {
      "repo": "group/name",
      "path": "/abs/root/group/name",
      "folder": "label",
      "alias_of": null,
      "sweep": { "...": "the C2 record, every field" },
      "gh": {"visibility": "private", "releases_in_window": [{"tag": "v1.2.0", "date": "2026-10-28"}], "open_prs": 2} ,
      "activity": "active",
      "logs_in_window": ["/abs/.../_local/_session-logs/2026-10-29_14-02_opus-5-5_x.md"],
      "snapshot": {"path": "/abs/.../_local/_status/2026-10-29_opus-5-5_x.md", "date": "2026-10-29", "head": "4f2a9c1", "fresh": true, "waiting_count": 2, "pending_decisions_count": 3, "next_count": 4,
                   "waiting_on_you": [{"text": "...", "source": "_local/_status/2026-10-29_opus-5-5_x.md"}],
                   "whats_next": [{"text": "...", "source": "..."}],
                   "pending_decisions": [{"id": "D1", "handle": "...", "home": "docs/...", "source": "..."}]},
      "status_source": "snapshot",
      "carried": null,
      "unprotected_work": [{"folder": "_local/notes", "files_changed": 3, "newest_mtime": "2026-10-29T21:14:00Z"}],
      "to_scout": false,
      "current_status_candidate": false
    }
  ],
  "logs": [{"file": "/abs/...", "repo": "group/name", "date": "2026-10-29", "time": "14-02", "nonstandard_name": false}],
  "gaps": [{"source": "gh", "detail": "gh not found on PATH"}],
  "timings": {"discover_seconds": 12.4, "sweep_seconds": 30.1}
}
```

- `gh` is `null` when enrichment is off or failed for that repository; the failure is in `gaps`.
- `activity` is `active` or `dormant` (spec Requirement 6).
- `snapshot`'s three counts come from the snapshot's frontmatter `waiting`, `pending-decisions` and `next`, renamed with a `_count` suffix so they never collide with the item lists.
- `snapshot` is `null` when the repository has no file matching `^\d{4}-\d{2}-\d{2}_[a-z0-9-]+_[a-z0-9]+(-[a-z0-9]+){1,5}\.md$` in `_local/_status/`. The item lists come from the snapshot's `## Waiting on You`, `## What's Next` and `## Pending Decisions` sections: one item per numbered line, text without the leading number and without the `Why here:` clause. `pending_decisions` items take `id` from the first token that looks like an id (`[A-Z]{1,3}-?\d+`), `handle` from the bold text or parenthesis after it, and `home` from the first backticked path; any of the three may be `null`.
- `status_source` is one of `snapshot` (a fresh snapshot), `scout` (active, to be scouted), `carried` (dormant with a previous state entry), `sweep-only` (dormant with none). An alias, a record with `alias_of` set, is always `sweep-only` and is never scouted.
- `carried` is `null` unless `status_source` is `carried`; then it is the previous entry's `status` object plus `"carried_from": "YYYY-MM-DD"`.
- `to_scout` is true exactly when `status_source` is `scout`.
- `current_status_candidate` is true when the repository is active and its snapshot is `null` or not fresh.

## `scouts.json`, written by the main loop from the scout agents' returns

A list of scout records, one per scouted repository:

```json
[{"repo": "group/name", "scouted_by": {"model": "sonnet", "agent": "scout-1"},
  "summary": "one or two sentences",
  "whats_next": [{"text": "...", "source": "docs/plan.md"}],
  "waiting_on_you": [{"text": "...", "source": "_local/_session-logs/2026-10-29_...md", "since": "2026-10-20"}],
  "pending_decisions": [{"id": "D2", "handle": "...", "home": "docs/spec.md", "source": "docs/spec.md"}],
  "risks": [{"text": "...", "source": "..."}],
  "conflicts": [{"fact": "branch feat/x", "git_says": "merged into main", "doc_says": "blocked", "source": "_local/_session-logs/...md"}]}]
```

`since` is optional. Every `source` is a path relative to the repository root, never empty.

## `curation.json`, written by the main loop

```json
{"whats_next": [{"rank": 1, "repo": "group/name", "item": "...", "who": "owner", "why": "...", "source": "..."}],
 "readout_notes": ["one line per cross-repository pattern"],
 "agents": [{"stage": "scout", "label": "scout-1", "model": "sonnet", "assigned": 4, "returned": 4, "escalated": false}]}
```

`who` is one of `owner`, `agent`, `agent-after-yes`. At most ten `whats_next` items.

## `pulse.json`, written by `build-pulse.py`

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-30T16:20:00Z",
  "mode": "week",
  "window": {"start": "2026-10-24", "end": "2026-10-30", "prior_start": "2026-10-17", "timezone": "America/Los_Angeles"},
  "totals": {"repos": 70, "active": 15, "dormant": 55, "aliases": 1, "commits_focus": 211, "tags_in_window": 16, "waiting_on_you": 23, "snapshots_fresh": 4},
  "repos": [
    {
      "repo": "group/name", "path": "/abs/...", "folder": "label", "alias_of": null,
      "activity": "active", "status_source": "scout", "carried_from": null,
      "sweep": { "...": "the C2 record" },
      "gh": null,
      "status": {
        "summary": "one or two sentences, or null",
        "whats_next": [{"text": "...", "source": "..."}],
        "waiting_on_you": [{"text": "...", "source": "...", "since": "2026-10-20", "first_seen": "2026-10-23", "age_days": 10}],
        "pending_decisions": [{"id": "D2", "handle": "...", "home": "...", "source": "..."}],
        "risks": [{"text": "...", "source": "..."}]
      },
      "conflicts": [],
      "unprotected_work": [],
      "current_status_candidate": true,
      "spend_usd": null
    }
  ],
  "whats_next": [{"rank": 1, "repo": "group/name", "item": "...", "who": "owner", "why": "...", "source": "..."}],
  "waiting_on_you": [{"rank": 1, "repo": "group/name", "item": "...", "age_days": 10, "source": "..."}],
  "agents": [{"stage": "scout", "label": "scout-1", "model": "sonnet", "assigned": 4, "returned": 4, "escalated": false}],
  "gaps": [{"source": "gh", "detail": "..."}]
}
```

Rules `pulse-check.py` enforces:

1. Every top-level key above is present, and every repository record carries every key above.
2. `activity` is `active` or `dormant`; `status_source` is one of the four values; `carried_from` is a date exactly when `status_source` is `carried`.
3. Every item under `status.whats_next`, `status.waiting_on_you`, `status.pending_decisions`, `status.risks`, the top-level `whats_next` and `waiting_on_you`, has a non-empty `source`.
4. Every `status.waiting_on_you` item has an integer `age_days` of zero or more, and a `first_seen` date.
5. The top-level `whats_next` has at most ten items, ranked 1 to n without gaps, and each `who` is one of the three values.
6. The top-level `waiting_on_you` is every repository's waiting items, ranked by `age_days` descending, so its length equals the sum of the repositories' `status.waiting_on_you` lengths.
7. `totals.repos` equals the number of repository records, and `totals.active` plus `totals.dormant` equals it.
8. Every agent in `agents` names a `model`; `returned` is at most `assigned`.

A repository whose status is unknown, `sweep-only`, has `status.summary` null and empty lists.

## `state.json`, the carry-forward store

```json
{"schema_version": 1, "updated_at": "2026-10-30T16:20:00Z",
 "repos": {"group/name": {"status": { "...": "as in pulse.json" }, "refreshed": "2026-10-30", "head": "4f2a9c1"}},
 "first_seen": {"group/name::normalized waiting text": "2026-10-23"}}
```

The normalized text is lowercase, with runs of whitespace collapsed and leading and trailing punctuation removed. `build-pulse.py` writes the state file only after `pulse.json` validates.

## `digest.jsonl`

One line per session log, contract C3 of the PP-01 spec. Every record carries every field; lists may be empty.

```json
{"file": "...", "repo": "group/name", "date": "2026-10-29", "time": "14-02", "harness": "claude", "model": "opus-5-5", "nonstandard_name": false,
 "summary": "...", "shipped": [], "decisions": [{"text": "...", "recorded_in": "...", "by": "owner"}], "waiting_on_owner": [{"text": "...", "since": null}], "next_action": "...",
 "tooling_friction": [{"what": "...", "tool": "...", "impact": "..."}], "practice_lessons": [], "global_setup_items": [], "scale_notes": []}
```
