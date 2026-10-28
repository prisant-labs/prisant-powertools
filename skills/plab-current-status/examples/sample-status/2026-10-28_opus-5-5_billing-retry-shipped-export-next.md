---
type: status-snapshot
date: 2026-10-28
model: opus-5-5
repo: example-app
branch: main
head: 4f2a9c1
level: decisions
previous: 2026-10-14_opus-5-5_billing-retry-in-review.md
waiting: 2
pending-decisions: 3
next: 3
---

# Status: example-app, 2026-10-28

**As of 2026-10-28.** `main` is at `4f2a9c1`, level with `origin/main` after a fetch, with a clean tree. The newest tag is v1.4.0, and one pull request is open, #88 (CSV export). **Sources read:** the facts script's output, the two session logs written since the previous snapshot, and the decisions sections of `docs/specs/EX-02_csv-export/spec.md` and `docs/specs/BR-01_billing-retry/spec.md`. **Confidence key:** high means checked against a file or a command's output; medium means a reasonable reading of one; low means my judgment.

## The Answer

Billing retry shipped in v1.4.0, so the project's main thread is now CSV export, open as PR #88. Two answers from you unblock it: the column order (EX-02 D1) and whether exports include archived rows (EX-02 D2). Everything else can wait a week. Confidence: high, from the tag, the pull request and the spec.

## Changed Since Last Status

Compared with `2026-10-14_opus-5-5_billing-retry-in-review.md`:

- **Shipped:** billing retry, tagged v1.4.0 on 2026-10-20. It was in review at the previous snapshot.
- **Opened:** PR #88 (CSV export), on 2026-10-24.
- **Decided:** BR-01 D3 (retry ceiling), on 2026-10-18. It was pending at the previous snapshot.
- **Still waiting:** the staging credentials request, now 21 days old.

## Waiting on You

1. **Answer EX-02 D1 (column order) and D2 (archived rows).** PR #88 cannot be finished until both are set, and each is a one-line answer. Why here: it is the only item blocking work in flight.
2. **Renew the staging credentials.** The deploy check has been skipped since 2026-10-07. Why here: it blocks nothing today, but the next release cannot be verified on staging without it.

## What's Next

1. **Finish PR #88 (CSV export) once D1 and D2 are answered.** Why here: it is the open pull request and the release's main feature.
2. **Add the retry metrics dashboard that BR-01 deferred.** Why here: it is the only BR-01 follow-up left, and it needs no decision.
3. **Retire the v1.2 import path.** Why here: it has no deadline and depends on nothing above.

## Pending Decisions

1. **EX-02 D1 (column order)** in `docs/specs/EX-02_csv-export/spec.md`. Waited 6 days. Recommendation: match the on-screen table. Why here: it blocks PR #88.
2. **EX-02 D2 (archived rows)** in `docs/specs/EX-02_csv-export/spec.md`. Waited 6 days. Recommendation: exclude archived rows by default. Why here: it also blocks PR #88, but either answer is cheap to change later.
3. **BR-01 D4 (retry alerting channel)** in `docs/specs/BR-01_billing-retry/spec.md`. Waited 19 days. Recommendation: the existing on-call channel. Why here: it blocks nothing until the metrics dashboard exists.

## Recent Decisions

- **BR-01 D3 (retry ceiling):** five attempts over 24 hours. Decided by the maintainer on 2026-10-18, recorded in `docs/specs/BR-01_billing-retry/spec.md`.

## Accomplished

- **Billing retry shipped** as v1.4.0 on 2026-10-20, through PRs #84 and #86.
- **The export spec was written,** `docs/specs/EX-02_csv-export/spec.md`, with five acceptance criteria.

## Where the Project Is

- **Billing retry:** shipped in v1.4.0. One deferred follow-up, the metrics dashboard.
- **CSV export:** in progress as PR #88, blocked on two decisions.
- **Import path cleanup:** not started.

## What I Don't Know

- **Pull requests merged before 2026-10-14** were not read, because the window starts at the previous snapshot.
- **Unrecognised statuses:** one decision row in an older spec carries the status "Resolved", which is outside the vocabulary. I did not read it as pending or answered.
- **Whether the staging credentials were renewed outside the repository.** Nothing in the logs says so. Confidence: low.
