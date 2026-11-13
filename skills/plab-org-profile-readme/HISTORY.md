# History - plab-org-profile-readme

| Version | Date | Release | Type | Summary |
|---|---|---|---|---|
| 1.1.0 | 2026-11-08 | v0.14.0 | changed | Ignoring a repository is reachable from any run: the skill asks add or ignore for each repository new to the page, takes an instruction such as "ignore scratch-repo", and the checker enforces it. A run with no organization asks for one, and a run with no `.github` repository or nothing to check stops cleanly. |
| 1.0.0 | 2026-11-08 | v0.14.0 | added | First version, specified by RM-01 (the org profile README skill). Sets a standard for a GitHub organization's profile README and keeps the page true to it and to the public repositories, through one pull request it never merges. Manual invocation only. |

## 1.1.0 - 2026-11-08

**Changed: ignoring a repository.** The standard's `exclude` list could leave a repository off the page, but only the `--setup` interview reached it, and a refresh added every repository new to the page without asking. A public scratch repository would land on the organization's front page in the next pull request. Now each run asks, once for all of them, whether to add or ignore every repository the page does not list. An instruction such as "ignore scratch-repo: it holds experiments, not a project" records the exclusion with its reason, on the same branch as the page.

**The checker enforces it.** Rule R1 now fails a page that still lists a repository the standard excludes, because an exclusion that the page ignores means nothing. It notes an exclusion for a repository the facts no longer cover. Rule R7 now scans the standard as well as the page and the pull request body, because the standard is committed to the same public repository and an ignore instruction is how a private name could reach it.

**Fixed: three runs the instructions did not cover.** With no organization given, the skill asks for one and never infers it from the working directory, where a git remote would name the wrong thing. With no `.github` repository, it stops and asks the maintainer to create it, because the skill never creates a repository. With no page and no standard, it says there is nothing to check, because the checker needs a page.

## 1.0.0 - 2026-11-08

**Added: the skill.** Two weekly routines kept two organization pages current, and they stalled whenever their last pull request was still open, so the pages drifted for weeks. The skill replaces them with one standard per organization and one checked pull request that a later run updates in place instead of stopping.

It ships three built-in standards, Catalog, Compact and Showcase, and seven options, chosen through `--setup`, which can also adopt an organization's existing page as its standard. A facts script reads the organization in one call and carries each private repository only as a digest of its name. A checker with fourteen rules proves each one can fail against a committed sample before it checks anything.

**Found by running against a real page before release.** Three things the specification did not anticipate came from checking a real organization page with live facts, before any pull request:

- The page lists a public fork that publishes its own releases. Covered repositories exclude forks, so the standard gained `include`, a list of forks the page shows, each with a reason.
- The page leaves off two releases that changed nothing a user would see, as its old routine's rules required. A strict newest-release rule would have rejected a correct page, so the standard gained `skip_releases`, each with a reason, and rule R3 compares against the newest release not skipped.
- Two badges read a marketplace list by position. Rule R6 reports that as a note rather than a failure, because the badges are deliberate and correct today.
