# plab-strategy-brief

**Version:** 1.1.1
**Source:** [`skills/plab-strategy-brief/`](../../../skills/plab-strategy-brief/)

Transform messy, unstructured thinking into a structured, decision-ready analysis document with a consistent 7-section anatomy.

---

## Getting Started

### Quick Start

Paste your raw thinking into Claude and say something like:

```
Help me think through whether we should migrate from Postgres to DynamoDB.
Here's what I'm weighing: [paste brain dump]
```

Or explicitly:

```
/plab-strategy-brief
[paste your messy notes]
```

The skill produces a standalone markdown document - not inline chat. The output is designed to be saved, shared, and referenced later. See [Output Location](#output-location) for where it lands.

### What You'll Need

- Raw input with at least 2 substantive threads (the skill skips clarifying questions when input is sufficient)
- A problem worth analyzing (not a simple factual question)

### Installation

Install via the prisant-labs marketplace:

```bash
/plugin marketplace add prisant-labs/agent-plugins
/plugin install prisant-powertools@prisant-labs
```

---

## When to Use

- You have a brain dump, stream-of-consciousness notes, or scattered thoughts that need structure
- You want help thinking through a problem with pros/cons, approaches, and a recommendation
- You say things like "help me think through X", "summarize and expand", "what's the 80/20"
- You're combining multiple analytical requests ("give me pros/cons AND approaches AND next steps")
- You're tired or busy and want Claude to do the structural heavy lifting

## When NOT to Use

- Simple factual questions ("what's the syntax for X?")
- Editing or polishing already-structured documents
- Code review or debugging
- Quick yes/no decisions that don't need analysis

---

## The 7-Section Output

Every output follows this anatomy, scaled to input complexity:

### 1. What I Understand (Input Mirror)

Reflects your input back in organized form. Surfaces assumptions, sub-threads, and gaps. This is the most important validation step - if the mirror is wrong, the analysis will be wrong.

*100-300 words*

### 2. Problem Space (Expansion)

Expands beyond what you framed: why it matters now, desired outcomes, stakeholders, adjacent problems. Uses JTBD framing when applicable.

*200-500 words*

### 3. Analysis (Lenses)

Applies analytical frameworks to your problem. Always uses the 5 core lenses (Strengths, Weaknesses, Risks, Open Questions, Concerns) plus 2-4 situational lenses selected for relevance.

*300-800 words*

### 4. Approaches (Distinct Paths)

2-4 genuinely different paths. Each with pros, cons, risks, effort estimate, and commentary. No padding - if only 2 viable paths exist, present 2.

*400-1,200 words*

### 5. The 80/20 Recommendation

What gets 80% of the value for 20% of the effort. Opinionated, specific, actionable. This section must stand alone - some readers skip straight here.

*150-400 words*

### 6. Evidence & Source Map

Sources consulted, data points relied on, and gaps in sourcing. Honest about what's well-supported vs. inferred.

*Variable*

### 7. Uncertainties & Open Items

What's unsure, what needs human judgment, follow-up prompts for deeper exploration.

*100-300 words*

---

## Output Location

Briefs are written to `_output/plab-strategy-brief/<slug>-<YYYY-MM-DD>.md` relative to your working directory,
where `<slug>` is a 3-6 word kebab-case derivation of the topic. The `_output/` root is shared with the
plugin's other producing skills and is intended to be gitignored at the project level.

To override it, name a destination in the request or pass `--out`:

| You say | Result |
|---|---|
| `--out /path/to/brief.md` | Written to that exact file |
| `--out /path/to/dir` | Written to `<dir>/<slug>-<YYYY-MM-DD>.md` |
| "as a chat artifact only", "do not save" | No disk write |

---

## Examples

### Example 1: Simple Input

**Input:** "I'm thinking about switching from Notion to Todoist for task management. Notion is getting slow and I never check my tasks in it."

**Output:** ~1,000 words. Clarifies the real problem (friction, not "Notion is bad"), presents 2 approaches (switch vs. restructure Notion), recommends based on whether the core issue is discoverability or performance.

### Example 2: Medium Input

**Input:** A paragraph mixing tool evaluation concerns, organizational workflow gaps, and half-formed ideas about notification fatigue.

**Output:** ~2,000 words. Separates threads (tool, process, people), applies Friction Analysis and JTBD lenses, presents 3 approaches (change tool, change process, change both), recommends the 80/20 path.

### Example 3: Complex Input

**Input:** A long brain dump mixing technical architecture, organizational politics, stakeholder opinions, compliance constraints, and timeline pressure.

**Output:** ~3,500 words. Maps 4 stakeholder groups, applies Dependency Analysis and Second-Order Effects lenses, presents 4 distinct approaches with effort/risk matrices, gives a staged 80/20 recommendation with concrete first steps.

### What It Won't Do

- "Should I use tabs or spaces?" - Too trivial for structured analysis
- "Here's my polished proposal, make it better" - That's editing, not strategy
- "What's the best JavaScript framework?" - That's research, not thinking amplification

---

## Depth Scaling

The output scales automatically based on input complexity:

| Complexity | Signals | Total Length |
|------------|---------|-------------|
| Simple | 1 clear question, narrow scope | 800-1,500 words |
| Medium | 2-3 threads, some ambiguity | 1,500-2,500 words |
| Complex | 4+ threads, broad scope, many unknowns | 2,500-4,000 words |

---

## Reference Files

| File | Purpose | When to Read |
|------|---------|-------------|
| `references/section-guide.md` | Per-section authoring guidance with word counts, structure options, techniques | When customizing section behavior |
| `references/analysis-lenses.md` | Full catalog: 5 core + 10 situational + 3 domain-specific lenses | When understanding which analytical frameworks apply |
| `references/template.md` | Output skeleton with instructional comments | When examining the exact output structure |
| `references/examples.md` | 3 complexity-level examples + 3 anti-examples | When understanding what good vs. bad output looks like |

### Analysis Lenses

The skill draws from a catalog of analytical frameworks:

**Core (always applied):** Strengths, Weaknesses, Risks, Open Questions, Concerns

**Situational (pick 2-4 based on relevance):**
- JTBD (Jobs to Be Done)
- Stakeholder Mapping
- Opportunity Cost
- Reversibility
- Scalability
- Dependencies
- Constraint Analysis
- Second-Order Effects
- Build vs. Buy
- Effort-to-Value
- Time Horizon

**Domain-specific:**
- Product: MoSCoW, RICE
- Technical: Complexity Budget, Coupling Analysis
- Personal: Friction Analysis, Automation Readiness

---

## Skill Files

```
skills/plab-strategy-brief/
├── SKILL.md                        # Core instructions (~130 lines)
├── references/
│   ├── section-guide.md            # Per-section writing guidance
│   ├── analysis-lenses.md          # Full lens catalog
│   ├── template.md                 # Output skeleton
│   └── examples.md                 # Worked examples + anti-examples
```

---

## Tips

- **Section 5 is the most important section.** Some readers skip straight to the 80/20 recommendation. Make sure it stands alone.
- **Don't force 3 approaches.** If only 2 viable paths exist, present 2. A filler "hybrid" approach is padding.
- **The mirror step catches misunderstandings.** It might seem like wasted space, but surfacing assumptions before analysis prevents going deep on the wrong problem.
- **Use web search for current topics.** If the input involves current tools, market conditions, or verifiable facts, the skill should search before analyzing.
- **Follow-up artifacts are valuable.** After the brief, the skill can generate a spec, decision doc, or action plan as a logical next step.

---

## Improvement Ideas

- Add domain-specific output variants (product brief, technical brief, personal decision)
- Support collaborative mode where the user iterates on specific sections
- Track which lenses are most frequently useful (usage analytics)
- Add a "quick brief" mode (~500 words) for simpler decisions
- Support structured input (not just brain dumps) - e.g., pre-filled templates with constraints
