# History - plab-org-profile-readme

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.0.0 | 2026-11-08 | Unreleased | added | First version, specified by RM-01 (the org profile README skill). Sets a standard for a GitHub organization's profile README and keeps the page true to it and to the public repositories, through one pull request it never merges. Manual invocation only. |

## 1.0.0 - 2026-11-08

**Added: the skill.** Two weekly routines kept two organization pages current, and they stalled whenever their last pull request was still open, so the pages drifted for weeks. The skill replaces them with one standard per organization and one checked pull request that a later run updates in place instead of stopping.

It ships three built-in standards, Catalog, Compact and Showcase, and seven options, chosen through `--setup`, which can also adopt an organization's existing page as its standard. A facts script reads the organization in one call and carries each private repository only as a digest of its name. A checker with fourteen rules proves each one can fail against a committed sample before it checks anything.

**Found by running against a real page before release.** Three things the specification did not anticipate came from checking a real organization page with live facts, before any pull request:

- The page lists a public fork that publishes its own releases. Covered repositories exclude forks, so the standard gained `include`, a list of forks the page shows, each with a reason.
- The page leaves off two releases that changed nothing a user would see, as its old routine's rules required. A strict newest-release rule would have rejected a correct page, so the standard gained `skip_releases`, each with a reason, and rule R3 compares against the newest release not skipped.
- Two badges read a marketplace list by position. Rule R6 reports that as a note rather than a failure, because the badges are deliberate and correct today.
