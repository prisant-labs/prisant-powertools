# Document Update Rules

When to update surrounding documents after a session, and how.

---

## General Principle

Most sessions don't warrant updating surrounding docs. Only update when the session produced a change that someone reading that document would need to know about. When in doubt, don't update.

**Always confirm before editing.** State what you intend to change and why. Never edit silently.

---

## README.md

**Update when:**
- New user-facing capability added (new skill, new command)
- Existing capability changed in a way users would notice
- Installation or usage instructions changed
- Project structure changed significantly

**Don't update when:**
- Internal refactor with no user-visible change
- Documentation or research work
- CI/infrastructure changes
- Bug fixes that don't change documented behavior

---

## CHANGELOG.md

**Update when (add to [Unreleased]):**
- New feature or skill added
- User-visible bug fixed
- Breaking change made
- Dependency added or removed
- Significant documentation added

**Don't update when:**
- Internal notes, research, or planning work
- Typo fixes in non-user-facing files
- Session logs or status documents created
- CI tweaks

**Format:** Follow [Keep a Changelog](https://keepachangelog.com/). Use Added/Changed/Removed/Fixed sections.

---

## Active Plans / Roadmaps

**Update when:**
- A planned item was completed
- Sequence or priority changed based on session findings
- New blocker discovered that affects the plan
- Scope changed (items added or removed)
- Assumptions invalidated

**Don't update when:**
- Work progressed normally without changing the plan
- The session was exploratory with no plan impact

---

## AGENTS.md

**Update when:**
- New skill or command added
- Existing skill renamed or removed
- Trigger phrases changed

**Don't update when:**
- Skill internals changed without affecting the entry
- Reference files updated

---

## Architecture Decision Records (`docs/internal/decisions/`)

**Create a new ADR when:**
- An architectural or structural decision was made during the session
- Multiple alternatives were seriously considered
- The decision is hard to reverse or looks wrong without context
- The user confirms (always ask - never auto-create ADRs)

**Don't create an ADR for:**
- Minor implementation choices (variable names, formatting)
- Trivially reversible decisions
- Decisions already captured in an existing ADR

**Format:** Use MADR v4 minimal template in `docs/internal/decisions/nnnn-title.md`. Include `decision-makers` in frontmatter to distinguish human vs. agent decisions. Reference the ADR in the session log's "Decisions Made" section.

**How to suggest:** When the "Decisions Made" section includes a decision with alternatives considered, trade-offs, or architectural impact, ask:
> "This decision is significant enough for an ADR. Want me to create `docs/internal/decisions/nnnn-title.md`?"

---

## How to Confirm

Each intended edit is one numbered proposal in the wrap's hygiene batch, asked after the log is written (`SKILL.md`, Wrap Order):

> **H3** This session [added/changed/fixed X]. Update [DOCUMENT] to [specific change].

Edit only when its number is approved. If declined, record it and move on.
