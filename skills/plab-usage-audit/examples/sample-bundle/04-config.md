# Config - 2026-10-19 to 2026-10-25

## Findings

The `sonnet` alias in the global settings file is pinned to `claude-sonnet-4-5`, one release behind the family's current priced model, `claude-sonnet-5`. This is the same drift Y8 named two audits ago. The `gh pr create` permission entry that A2's predecessor added was reverted during the merge commit that closed PR #41 on 2026-10-21, and nothing restored it, which is this week's friction finding from `01-usage.md`.

## Settings against the change register

Two settings keys changed this week with no row in the change register: `permissions.allow` lost the `gh pr create` entry noted above, and `model` for the `sonnet` alias has carried `claude-sonnet-4-5` since 2026-09-12 with no register row at all, which means it predates this skill's first run and is being recorded for the first time here.

## Claude Code versions and changelog

The installed Claude Code version moved from 2.1.301 to 2.1.312 this week. The changelog between those versions lists one entry relevant to this plugin's own scripts: a fix to how `git check-ignore` exit codes are surfaced to a subprocess caller on Windows, which `check-placement.py` already treats as advisory rather than load-bearing, since it reads the exit code directly rather than any wrapped message.

## Credential presence by key name

A `.env` file for `alpha-app` carries one key, `ALPHA_APP_API_KEY`, present with a non-empty value as of 2026-10-23. No value is reported here, only the key name and the file's modification date, per the rule that this bundle never carries a credential value.

## Backup health

The transcript backup task last ran on 2026-10-24 and reports 2,114 session files archived, up from 2,098 the week before. No gap longer than 25 hours appears in its run log for this window.
