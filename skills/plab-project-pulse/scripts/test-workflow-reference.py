#!/usr/bin/env python3
"""Check references/workflow.md: every agent stage names a model, the shared rules block carries the
credential rule, and every prompt section tells the agent to receive that block (PP-01 AC-16).

Exit 0 when every check passes and every canary is caught; 1 when a check fails; 2 when a canary
passes, which means a check has gone blind.
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
WORKFLOW = HERE.parent / "references" / "workflow.md"
MODELS = {"haiku", "sonnet", "opus"}
CREDENTIAL_MARKERS = ["CREDENTIAL FILES ARE OFF LIMITS", ".env", "secret", "token", "credential_files"]


def routing_rows(text):
    """Return (stage, model) pairs from the table under '## Routing'."""
    section = text.split("## Routing", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("Stage", "") or set(cells[0]) <= set("-: "):
            continue
        rows.append((cells[0], cells[2].lower()))
    return rows


def rules_block(text):
    section = text.split("## The rules every agent receives", 1)
    if len(section) < 2:
        return ""
    match = re.search(r"```text\n(.*?)```", section[1], re.S)
    return match.group(1) if match else ""


def prompt_sections(text):
    """Every stage section (### ... under the agent stages) that defines a Prompt."""
    out = []
    for block in re.split(r"\n## ", text):
        if "**Prompt:**" in block:
            out.append(block.split("\n", 1)[0].strip())
            if not re.search(r"\*\*Prompt:\*\*\s*the rules block", block):
                out[-1] = "MISSING:" + out[-1]
    return out


def check(text):
    failures = []
    rows = routing_rows(text)
    if not rows:
        failures.append("routing: no stage rows found")
    for stage, model in rows:
        if model not in MODELS:
            failures.append(f"routing: stage '{stage}' names no model (got '{model}')")
    block = rules_block(text)
    for marker in CREDENTIAL_MARKERS:
        if marker not in block:
            failures.append(f"rules: the shared block lacks '{marker}'")
    prompts = prompt_sections(text)
    if len(prompts) < 2:
        failures.append(f"prompts: expected at least 2 prompt sections, found {len(prompts)}")
    for name in prompts:
        if name.startswith("MISSING:"):
            failures.append(f"prompts: '{name[8:]}' does not open with the rules block")
    return failures


def canaries(text):
    """Each mutation must make check() fail."""
    mutations = {
        "model removed": re.sub(r"(\| Heavy scout \| 0 to 1 \| )sonnet", r"\1", text),
        "credential rule removed": text.replace("CREDENTIAL FILES ARE OFF LIMITS", "FILES"),
        "rules block dropped from a prompt": text.replace("**Prompt:** the rules block, then:", "**Prompt:**", 1),
    }
    blind = [name for name, mutated in mutations.items() if mutated == text or not check(mutated)]
    return blind


def main():
    if not WORKFLOW.is_file():
        print(f"BROKEN: {WORKFLOW} not found")
        return 2
    text = WORKFLOW.read_text(encoding="utf-8")
    blind = canaries(text)
    if blind:
        print("BROKEN: canary passed, check is blind: " + ", ".join(blind))
        return 2
    failures = check(text)
    for f in failures:
        print("FAIL: " + f)
    if failures:
        return 1
    print(f"CLEAN: canary proved, {len(routing_rows(text))} stages name a model, the credential rule is in the shared block, every prompt opens with it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
