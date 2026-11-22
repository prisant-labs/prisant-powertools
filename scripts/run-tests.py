#!/usr/bin/env python3
"""
The repository's one test command. Runs every check the Gate workflow's
`dash-check` and `document-gates` jobs run, and with `--check-gate` proves
that this script's list and those jobs still name the same commands.

USAGE
-----
  python3 scripts/run-tests.py                  run every command, report each
  python3 scripts/run-tests.py --check-gate     compare COMMANDS with gate.yml
  python3 scripts/run-tests.py --check-gate --workflow <path>

EXIT-CODE CONTRACT
------------------
  0  CLEAN    self-test proved AND every command passed (or, with
              --check-gate, the list and the workflow agree)
  1  FINDINGS self-test proved AND a command failed (or the two disagree)
  2  BROKEN   the self-test failed, the workflow could not be read, or a
              command uses shell syntax this runner does not support

NEVER INTERPRET 2 AS CLEAN.

WHY THIS EXISTS
---------------
The release-on-merge workflow (RL-01, release on merge) reruns the tests on
the merged commit before it tags. It must run what the pull request ran, no
less. Branch protection requires the gate's checks by job name, and the gate
names every check in its own `run:` step, so the list below is a copy of
those steps, and `--check-gate`, which runs in the `document-gates` job,
fails the pull request that lets the two drift apart.

WHAT IS LEFT OUT, AND WHY
-------------------------
- The `standard-gate` job. It grades the repository with the
  `product-on-purpose/agent-skills-toolkit` action, which the release workflow
  must not call (RL-01 AC-12), and the Gate workflow still runs it on every
  push to `main`, which includes the merge commit itself.
- Setup steps. A `run:` that does not begin with `python3 ` (installing
  ripgrep) is setup, not a test, by rule rather than by list.
- This script's own `--check-gate` step.

WHY NO SHELL
------------
Each command is split on `&&` and every part runs directly, with this
script's own interpreter in place of `python3`, so the runner works on a
machine where `python3` does not resolve and where a bare `bash` would be
WSL rather than Git Bash. Any other shell syntax (a pipe, `;`, a redirect,
`$`) is refused as BROKEN rather than guessed at; extend the runner first.

WHY NO YAML LIBRARY
-------------------
CI's setup-python ships without pyyaml. The parser reads only a job's
`run:` lines, finds the job by its two-space key, and refuses a block scalar
(`run: |`) in a job it reads, so a format it cannot read fails loudly.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "gate.yml"
JOBS = ("dash-check", "document-gates")
SELF = "python3 scripts/run-tests.py"

# The exact `run:` strings of the python3 steps in the dash-check and
# document-gates jobs of .github/workflows/gate.yml, in job order.
COMMANDS = [
    "python3 scripts/check-dashes.py",
    "python3 scripts/frontmatter-check.py",
    "python3 scripts/doc-lifecycle-check.py",
    "python3 scripts/gen-release-index.py --check",
    "python3 scripts/version-parity-check.py",
    "python3 scripts/skill-drift-check.py",
    "python3 scripts/codex-invocation-check.py",
    "python3 skills/plab-audit/scripts/bundle-check.py skills/plab-audit/examples/sample-bundle",
    "python3 skills/plab-resolve-open-items/scripts/walk-check.py record skills/plab-resolve-open-items/examples/sample-walk/walk-record.md",
    "python3 skills/plab-resolve-open-items/scripts/walk-check.py writeback skills/plab-resolve-open-items/examples/sample-walk/before.md skills/plab-resolve-open-items/examples/sample-walk/after.md",
    "python3 skills/plab-resolve-open-items/scripts/test-gather-backlog.py",
    "python3 skills/plab-current-status/scripts/status-check.py --self-test",
    "python3 skills/plab-current-status/scripts/test-derive-status-facts.py",
    "python3 -m pip install --quiet pyyaml && python3 skills/plab-guide/scripts/test-guide-scripts.py",
    "python3 skills/plab-usage-audit/scripts/bundle-check.py --self-test",
    "python3 skills/plab-usage-audit/scripts/test-collect.py",
    "python3 skills/plab-usage-audit/scripts/test-ledger.py",
    "python3 skills/plab-usage-audit/scripts/test-derive-audit-facts.py",
    "python3 skills/plab-usage-audit/scripts/test-scrub.py",
    "python3 skills/plab-usage-audit/scripts/test-shipped.py",
    "python3 skills/plab-usage-audit/scripts/test-workflow-reference.py",
    "python3 skills/plab-project-pulse/scripts/pulse-check.py --self-test",
    "python3 skills/plab-project-pulse/scripts/test-discover-sweep.py",
    "python3 skills/plab-project-pulse/scripts/test-derive-pulse-facts.py",
    "python3 skills/plab-project-pulse/scripts/test-build-render.py",
    "python3 skills/plab-project-pulse/scripts/test-workflow-reference.py",
    "python3 skills/plab-project-pulse/scripts/test-readiness.py",
    "python3 skills/plab-ship/scripts/ship-check.py --self-test",
    "python3 skills/plab-ship/scripts/test-ship-scripts.py",
    "python3 skills/plab-org-profile-readme/scripts/profile-check.py --self-test",
    "python3 skills/plab-org-profile-readme/scripts/test-profile-scripts.py",
    "python3 skills/plab-wrap-session/scripts/test-check-log.py",
    "python3 skills/plab-wrap-session/scripts/test-derive-log-facts.py",
    "python3 skills/plab-wrap-session/scripts/test-organize-logs.py",
    "python3 skills/plab-continue-session/scripts/test-reconcile.py",
    "python3 lib/test-session-logs.py",
    "python3 skills/plab-continue-session/scripts/test-list-candidates.py",
    "python3 skills/plab-ai-review/scripts/test-dispatch.py",
]


class Broken(Exception):
    """The input cannot be read or run faithfully. Exit 2, never clean."""


# ---------------------------------------------------------------- the workflow

def job_runs(text: str, job: str) -> list:
    """Every `run:` value inside one job, in file order."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^  %s:\s*(#.*)?$" % re.escape(job), line):
            start = i + 1
            break
    if start is None:
        raise Broken("job %r not found at two-space indent" % job)
    runs = []
    for line in lines[start:]:
        if re.match(r"^ {0,2}\S", line) and not line.lstrip().startswith("#"):
            break
        m = re.match(r"^\s+(?:-\s+)?run:\s*(.*?)\s*$", line)
        if not m:
            continue
        value = m.group(1)
        if value[:1] in ("|", ">"):
            raise Broken("job %r has a block-scalar run: step; this parser reads one-line steps only" % job)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        runs.append(value)
    return runs


def gate_tests(text: str) -> list:
    """The test commands the two jobs run: python3 steps, minus this script."""
    tests = []
    for job in JOBS:
        for run in job_runs(text, job):
            if run.startswith("python3 ") and not run.startswith(SELF):
                tests.append(run)
    return tests


def drift(commands: list, tests: list) -> list:
    """One line per command present on one side only, plus any duplicate."""
    out = []
    for c in commands:
        if c not in tests:
            out.append("in run-tests.py but not in the gate jobs: " + c)
    for t in tests:
        if t not in commands:
            out.append("in the gate jobs but not in run-tests.py: " + t)
    for c in sorted({c for c in commands if commands.count(c) > 1}):
        out.append("listed more than once in run-tests.py: " + c)
    return out


# ------------------------------------------------------------------ the runner

def parts(command: str) -> list:
    """Split one command on && into argument lists; refuse other shell syntax."""
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        tokens = list(lex)
    except ValueError as e:
        raise Broken("cannot tokenize %r: %s" % (command, e))
    groups, current = [], []
    for tok in tokens:
        if tok == "&&":
            groups.append(current)
            current = []
        elif tok and all(ch in "();<>|&" for ch in tok):
            raise Broken("unsupported shell syntax %r in: %s" % (tok, command))
        elif "$" in tok or "`" in tok:
            raise Broken("unsupported shell expansion in: %s" % command)
        else:
            current.append(tok)
    groups.append(current)
    for g in groups:
        if not g or g[0] != "python3":
            raise Broken("every part must start with python3: %s" % command)
    return groups


def run_one(command: str, cwd: Path, python: str):
    """Run one command's parts in order, stopping at the first failure."""
    output = []
    for argv in parts(command):
        proc = subprocess.run([python] + argv[1:], cwd=str(cwd), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        output.append(proc.stdout)
        if proc.returncode != 0:
            return proc.returncode, "".join(output)
    return 0, "".join(output)


def run_all(commands: list, cwd: Path, python: str, echo=print) -> list:
    """Run every command, even after a failure. Returns (command, code) pairs."""
    results = []
    for command in commands:
        code, output = run_one(command, cwd, python)
        results.append((command, code))
        if code == 0:
            echo("PASS  " + command)
        else:
            echo("FAIL  " + command + "  (exit %d)" % code)
            tail = output.rstrip().splitlines()[-30:]
            for line in tail:
                echo("      | " + line)
    return results


# ------------------------------------------------------------------- self-test

FIXTURE = """\
jobs:
  standard-gate:
    steps:
      - run: python3 ignored/because/wrong-job.py
  dash-check:
    steps:
      - name: Install ripgrep
        run: sudo apt-get install -y ripgrep
      - name: Dash
        run: python3 a.py
  document-gates:
    steps:
      # a comment at step indent
      - name: B
        if: always()
        run: python3 b.py --flag
      - name: C
        run: "python3 c.py"
      - name: Self
        run: python3 scripts/run-tests.py --check-gate
  after-job:
    steps:
      - run: python3 also/ignored.py
"""


def self_test() -> list:
    """Return a list of failures; empty means every rule was proved."""
    fails = []

    tests = gate_tests(FIXTURE)
    if tests != ["python3 a.py", "python3 b.py --flag", "python3 c.py"]:
        fails.append("parser: expected a, b and c from the two jobs only; got %r" % tests)

    if drift(["python3 a.py", "python3 b.py --flag", "python3 c.py"], tests):
        fails.append("drift: an identical list reported drift")
    got = drift(["python3 a.py", "python3 b.py --flag", "python3 extra.py"], tests)
    want = ["in run-tests.py but not in the gate jobs: python3 extra.py",
            "in the gate jobs but not in run-tests.py: python3 c.py"]
    if got != want:
        fails.append("drift: one extra and one missing command; expected %r, got %r" % (want, got))
    if not drift(["python3 a.py", "python3 a.py", "python3 b.py --flag", "python3 c.py"], tests):
        fails.append("drift: a duplicate entry went unreported")

    unreadable = (
        "jobs:\n  dash-check:\n    steps:\n      - run: |\n          python3 x.py\n  document-gates:\n    steps: []\n",
        "jobs:\n  other:\n    steps: []\n",
    )
    for bad in unreadable:
        try:
            gate_tests(bad)
            fails.append("parser: accepted a workflow it cannot read: %r" % bad)
        except Broken:
            pass

    for bad in ("python3 a.py | tee x", "python3 a.py; ls", "python3 a.py > out", "python3 $X", "ls && python3 a.py"):
        try:
            parts(bad)
            fails.append("parts: accepted unsupported syntax: %r" % bad)
        except Broken:
            pass
    if parts("python3 -c 'a;b' && python3 b.py") != [["python3", "-c", "a;b"], ["python3", "b.py"]]:
        fails.append("parts: a quoted ; or the && split was mishandled")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        marker = tmp / "ran-after-failure"
        late = tmp / "ran-past-and"
        commands = [
            'python3 -c "pass"',
            'python3 -c "raise SystemExit(1)"',
            'python3 -c "raise SystemExit(3)" && python3 -c "open(%r, \'w\').close()"' % late.name,
            'python3 -c "open(%r, \'w\').close()"' % marker.name,
        ]
        results = run_all(commands, tmp, sys.executable, echo=lambda _line: None)
        codes = [code for _c, code in results]
        if codes != [0, 1, 3, 0]:
            fails.append("runner: expected exit codes [0, 1, 3, 0]; got %r" % codes)
        if not marker.exists():
            fails.append("runner: stopped after a failure instead of running every command")
        if late.exists():
            fails.append("runner: ran past a failed && part")
        if not any(code != 0 for code in codes):
            fails.append("runner: a failing command did not register as a failure")

    return fails


# ------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check-gate", action="store_true", help="compare COMMANDS with the gate jobs and run nothing")
    ap.add_argument("--workflow", default=str(WORKFLOW), help="the Gate workflow to compare against")
    args = ap.parse_args()

    fails = self_test()
    if fails:
        for f in fails:
            print("self-test: " + f, file=sys.stderr)
        print("BROKEN: run-tests self-test failed, its results are not trustworthy.", file=sys.stderr)
        return 2
    print("run-tests self-test: PASS (job scoping, setup and self steps skipped, drift both ways and duplicates, block scalars and shell syntax refused, every command runs after a failure, && stops at the first failure)")

    try:
        for command in COMMANDS:
            parts(command)
        if args.check_gate:
            path = Path(args.workflow)
            if not path.is_file():
                raise Broken("workflow not found: %s" % path)
            tests = gate_tests(path.read_text(encoding="utf-8"))
    except Broken as e:
        print("BROKEN: %s" % e, file=sys.stderr)
        return 2

    if args.check_gate:
        if not tests:
            print("BROKEN: no python3 steps found in %s; the comparison would be vacuous." % ", ".join(JOBS), file=sys.stderr)
            return 2
        found = drift(COMMANDS, tests)
        if found:
            for f in found:
                print("FINDING: " + f)
            print("FINDINGS: run-tests.py lists %d command(s), the gate jobs run %d, and %d differ." % (len(COMMANDS), len(tests), len(found)))
            return 1
        print("CLEAN: run-tests.py and the %s jobs name the same %d command(s)." % (" and ".join(JOBS), len(COMMANDS)))
        return 0

    results = run_all(COMMANDS, ROOT, sys.executable)
    failed = [c for c, code in results if code != 0]
    if failed:
        print("FINDINGS: %d of %d command(s) failed." % (len(failed), len(results)))
        return 1
    print("CLEAN: all %d command(s) passed." % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
