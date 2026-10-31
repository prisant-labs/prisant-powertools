# Carry-forward

A dormant repository costs the pulse nothing: it keeps the entry it had when last refreshed, stamped with that date.

## The rule

1. A repository is **active** when it has an own commit or a new session log in the window. Every other repository is **dormant**.
2. A dormant repository with an entry in the state file keeps that entry. `pulse.json` marks it `status_source: "carried"` with `carried_from` set to the date it was last refreshed.
3. A dormant repository with no entry gets sweep facts only: `status_source: "sweep-only"`, an empty status, and no agent.
4. An active repository is refreshed the same run: from its snapshot when one is fresh, otherwise by a scout.
5. The state file is written only after `pulse.json` validates, so a failed run never replaces a good entry with a bad one.

## Waiting-item ages

Every waiting item carries `first_seen` and `age_days`. When its source states a since date, the age counts from that date. Otherwise the state file's `first_seen` map supplies the date the pulse first saw the same item, matched by repository and normalized text (lowercase, whitespace collapsed, leading and trailing punctuation removed). A new item starts at age zero. An item whose wording changes between runs restarts its age; that is a known limit.

## A carried entry that is too old

A carried entry may describe a state months old. The dashboard shows each carried card's `carried_from` date. A later `--full` mode will re-scout every repository; until then, a repository becomes fresh again the moment it is active.
