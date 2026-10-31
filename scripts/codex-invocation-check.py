#!/usr/bin/env python3
"""
Manual-only parity gate between Claude Code and Codex. Invoked by CI, not by a skill.

EXIT-CODE CONTRACT
------------------
  0  CLEAN    canary proved AND every skill says the same thing to both harnesses
  1  FINDINGS canary proved AND at least one skill disagrees
  2  BROKEN   the canary failed, or no skill was found to check

NEVER INTERPRET 2 AS CLEAN.

WHY THIS EXISTS
---------------
A skill is made manual-only twice, once per harness. Claude Code reads
`disable-model-invocation: true` in the SKILL.md frontmatter. Codex ignores
that field; it reads `policy.allow_implicit_invocation: false` in the skill's
`agents/openai.yaml`, and hides a skill with that policy from the model while
keeping it callable by name. The 2026-08-29 audit found the Codex half missing
for every manual-only skill here, so each one could fire on its own in Codex.
This gate fails when a skill carries either flag without the other.

WHY NO YAML LIBRARY
-------------------
CI's setup-python ships without pyyaml, and both flags are single scalar lines.
The parser reads only the frontmatter block of SKILL.md and only the `policy:`
block of openai.yaml, and the self-test proves it on both spellings it accepts.
"""

import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def claude_manual_only(skill_md: Path) -> bool:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return False
    return re.search(r"^disable-model-invocation:\s*true\s*$", m.group(1), re.M) is not None


def codex_manual_only(skill_dir: Path) -> bool:
    cfg = skill_dir / "agents" / "openai.yaml"
    if not cfg.is_file():
        return False
    in_policy = False
    for line in cfg.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\S", line):
            in_policy = line.split("#", 1)[0].strip() == "policy:"
            continue
        if in_policy and re.match(r"^\s+allow_implicit_invocation:\s*false\s*(#.*)?$", line):
            return True
    return False


def check(skills_root: Path):
    findings, count = [], 0
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        count += 1
        name = skill_md.parent.name
        claude, codex = claude_manual_only(skill_md), codex_manual_only(skill_md.parent)
        if claude and not codex:
            findings.append("%s: manual-only in Claude Code but not in Codex; add agents/openai.yaml with policy.allow_implicit_invocation: false" % name)
        elif codex and not claude:
            findings.append("%s: manual-only in Codex but not in Claude Code; add disable-model-invocation: true to SKILL.md, or remove the Codex policy" % name)
    return count, findings


def make_skill(root: Path, name: str, claude: bool, codex: str):
    d = root / name
    d.mkdir(parents=True)
    front = "---\nname: %s\ndescription: x\n%s---\n\nbody\n" % (name, "disable-model-invocation: true\n" if claude else "")
    (d / "SKILL.md").write_text(front, encoding="utf-8")
    if codex:
        (d / "agents").mkdir()
        (d / "agents" / "openai.yaml").write_text(codex, encoding="utf-8")


def self_test() -> bool:
    gated = "policy:\n  allow_implicit_invocation: false\n"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        make_skill(root, "both", True, gated)
        make_skill(root, "both-commented", True, "# note\ninterface:\n  display_name: x\npolicy:  # gate\n  allow_implicit_invocation: false  # why\n")
        make_skill(root, "neither", False, "")
        make_skill(root, "claude-only", True, "")
        make_skill(root, "codex-only", False, gated)
        # The key outside the policy block, and the policy set to true, must not count.
        make_skill(root, "wrong-block", True, "interface:\n  allow_implicit_invocation: false\n")
        make_skill(root, "policy-true", True, "policy:\n  allow_implicit_invocation: true\n")
        # A disable line in the body, not the frontmatter, must not count.
        d = root / "body-only"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: body-only\ndescription: x\n---\n\ndisable-model-invocation: true\n", encoding="utf-8")
        count, findings = check(root)
        flagged = {f.split(":", 1)[0] for f in findings}
    want = {"claude-only", "codex-only", "wrong-block", "policy-true"}
    ok = count == 8 and flagged == want
    if not ok:
        print("self-test: expected 8 skills and findings for %s; got %d skills and %s" % (sorted(want), count, sorted(flagged)), file=sys.stderr)
    return ok


def main() -> int:
    if not self_test():
        print("BROKEN: gate self-test failed, the detector is not trustworthy.", file=sys.stderr)
        return 2
    print("gate self-test: PASS (two agreeing skills, one with comments and an interface block, and one ungated skill ignored; Claude-only, Codex-only, key-outside-policy and policy-true flagged; a disable line outside the frontmatter ignored)")
    count, findings = check(ROOT / "skills")
    if count == 0:
        print("BROKEN: no skills/*/SKILL.md found under %s." % ROOT, file=sys.stderr)
        return 2
    if findings:
        for f in findings:
            print("FINDING: " + f)
        print("FINDINGS: canary proved, %d skill(s) checked, %d disagree between Claude Code and Codex." % (count, len(findings)))
        return 1
    gated = sum(1 for p in (ROOT / "skills").glob("*/SKILL.md") if claude_manual_only(p))
    print("CLEAN: canary proved, %d skill(s) checked, %d manual-only in both Claude Code and Codex, the rest in neither." % (count, gated))
    return 0


if __name__ == "__main__":
    sys.exit(main())
