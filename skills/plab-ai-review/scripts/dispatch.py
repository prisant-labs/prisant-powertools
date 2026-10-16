#!/usr/bin/env python3
"""
plab-ai-review dispatch helper (A-02, programmatic review dispatch).

Two subcommands, `submit` and `collect`, that let `--dispatch` hand a generated
review request document to Codex through the installed `codex-companion.mjs`
helper's `task` subcommand instead of the maintainer pasting it by hand, and
later collect the findings back into the same document's reviewer placeholders.

  python dispatch.py submit  <review-request.md> [--companion <path>]
  python dispatch.py collect <review-request.md> [--companion <path>]

EXIT-CODE CONTRACT
------------------
  0  the requested action completed: the job was submitted, or a completed
     job's findings were parsed and written into the document
  1  the action produced a definite, reported non-success state: the job is
     still running, the reviewer could not be reached or failed, its output
     did not parse as findings, or the companion helper is not installed.
     This is a report, not a crash, and the document is left exactly as it
     was: a document with empty reviewer placeholders and a printed failure
     state is recoverable by the manual paste path; a document that silently
     looks like a completed, empty review is not, and this script never
     produces the second shape (AC-5 in A-02's spec).
  2  BROKEN - an exception this script did not anticipate reached main()

Every outcome, success or reported failure, is also printed to stdout as one
JSON object with a `state` field (`submitted`, `collected`, `running`,
`failed`, `unavailable`, `unparseable`), so the calling agent can read the
state without relying on the shell's exit code.

WHY SUBMIT AND COLLECT MUST RUN FROM THE SAME WORKSPACE ROOT
--------------------------------------------------------------
`codex-companion.mjs` keys its job store by workspace root
(`scripts/lib/state.mjs`'s `resolveStateDir`), and workspace root is resolved
by `scripts/lib/workspace.mjs`'s `resolveWorkspaceRoot`: `git rev-parse
--show-toplevel` from the given `--cwd` when that directory is inside a git
repository, falling back to the literal `--cwd` otherwise. Verified directly
(2026-10-15, this effort): a job submitted with `--cwd` inside this
repository's worktree is found under `result <id> --json` run from ANY
subdirectory of that same worktree (the git toplevel is identical), but is
NOT found when `--cwd` is a different, unrelated non-git directory, even
naming the same explicit job id. `resolve_cwd()` below reproduces the
companion's own resolution (git toplevel, else the document's own directory)
from the review document's path alone, so `submit` and `collect` agree on a
workspace root without either command needing to be told one, as long as the
review document itself does not move to a different repository (or a
different directory outside of any repository) between the two calls.

WHY CODEX_COMPANION_SESSION_ID IS LEFT ALONE ON SUBMIT BUT UNSET ON COLLECT
------------------------------------------------------------------------------
`codex-companion.mjs` sets this environment variable in Claude Code sessions
to the Claude session id, and stamps it onto every job the session creates
(`scripts/lib/tracked-jobs.mjs`). Leaving it set on submit means the job shows
up under that session's own `/codex:status`, which is desirable.  Read
directly (2026-10-15): `job-control.mjs`'s `resolveResultJob` filters by
session ONLY when no job id is given (`reference ? listJobs(...) :
filterJobsForCurrentSession(...)`); `buildSingleJobSnapshot`, which backs the
explicit-id `status` path, never filters at all. An explicit-id `result <id>
--json` lookup was re-verified here to succeed under the current session's
id, a foreign session id, and an unset session id alike - so unsetting the
variable before `collect`'s `result` call is NOT load-bearing against this
companion version. It is done anyway, defensively and cheaply (a lookup
creates no job record to pollute), in case a future companion version does
filter explicit lookups; see `references/dispatch.md` for the full
re-verification record, including where this differs from what an earlier
pass of this effort reported.

WHY THE OUTPUT FORMAT ASKED OF CODEX IS JSON, NOT MARKDOWN
--------------------------------------------------------------
`task` has no `--output-schema` path (that is `review`/`adversarial-review`
only, per `codex-companion.mjs`'s own usage text), so this script cannot
constrain Codex's output format at the transport level. Asking Codex to
return the whole filled-in markdown document back verbatim would make
`collect` trust a live model to reproduce every other section
(Non-Goals/Requestor Analysis/Decisions/Proposed Actions) byte-for-byte
unchanged, which is exactly the kind of silent drift AC-6 (same document
shape as the manual path) exists to rule out. Instead, the submit prompt (see
`build_submit_prompt`) asks for a small JSON object naming only the
Reviewer's own content - the assessment, severity counts, and one finding
per dimension - and `collect` does the splicing into the existing document
itself, deterministically, matching each dimension by the exact heading text
already present in the document (`extract_dimensions`). Any mismatch between
the dimensions Codex answered and the dimensions the document actually has is
the `unparseable` state, never a partial, silently-incomplete splice.

The one frontmatter field this effort's spec allows (`dispatch-job`, D2) is
written together with a `type: review` tag required for `scripts
/frontmatter-check.py` to recognize the block at all (see
`docs/internal/schemas/review.schema.json`); both are written together, only
once a job id exists, so the block is never present in a half-written state.
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
REVIEWER_ATTRIBUTION_RE = re.compile(r"(?m)^\*\*Reviewer\s*-.*:\*\*\s*$")
QUOTE_BLOCK_RE = re.compile(r"(\s*\n)((?:>.*(?:\n|\Z))+)")
HEADING_RE = re.compile(r"(?m)^#{2,3}\s+")

STATE_EXIT = {
    "submitted": 0,
    "collected": 0,
    "running": 1,
    "failed": 1,
    "unavailable": 1,
    "unparseable": 1,
}

SEVERITY_LABELS = (("Blocker", "blocker"), ("Major", "major"), ("Minor", "minor"), ("Note", "note"))


class SpliceError(Exception):
    """The document's structure did not match what the splice step expected."""


# ---------------------------------------------------------------------------
# Small I/O helpers
# ---------------------------------------------------------------------------

def read_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def report(state, message, **extra):
    payload = {"state": state, "message": message}
    payload.update(extra)
    print(json.dumps(payload, indent=2))
    return STATE_EXIT.get(state, 2)


# ---------------------------------------------------------------------------
# Frontmatter: deliberately a tiny hand-rolled reader/writer, not a YAML
# library and not a copy of frontmatter-check.py's parser. The review
# document carries at most two fields (type, dispatch-job; see
# docs/internal/schemas/review.schema.json), so a general parser would be
# more machinery than the contract needs.
# ---------------------------------------------------------------------------

def split_frontmatter(text):
    """Return (fm_dict, body). fm_dict is {} and body is the whole text when
    there is no frontmatter block at all - the case for every undispatched
    review document, and for a dispatched one before its first `submit`."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fm[key.strip()] = value.strip()
    return fm, text[m.end():]


def join_frontmatter(fm, body):
    if not fm:
        return body
    lines = ["---"]
    for key, value in fm.items():
        lines.append("%s: %s" % (key, value))
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


# ---------------------------------------------------------------------------
# Companion discovery and invocation
# ---------------------------------------------------------------------------

def discover_companion(override=None):
    """The highest installed codex-companion.mjs version, or None if dispatch
    is unavailable on this machine (the portability fallback named in A-02's
    spec Non-Functional Requirements)."""
    if override:
        return override if os.path.isfile(override) else None

    pattern = os.path.join(
        os.path.expanduser("~"), ".claude", "plugins", "cache",
        "openai-codex", "codex", "*", "scripts", "codex-companion.mjs",
    )
    candidates = glob.glob(pattern)
    if not candidates:
        return None

    def version_key(path):
        version = os.path.basename(os.path.dirname(os.path.dirname(path)))
        try:
            return tuple(int(part) for part in version.split("."))
        except ValueError:
            return (0,)

    candidates.sort(key=version_key)
    return candidates[-1]


def resolve_cwd(doc_path):
    """Reproduce codex-companion's own resolveWorkspaceRoot from the document's
    path alone: the document directory's git toplevel, or that directory
    itself when it is not inside a git repository. See the module docstring's
    'WHY SUBMIT AND COLLECT MUST RUN FROM THE SAME WORKSPACE ROOT' section."""
    doc_dir = os.path.dirname(os.path.abspath(doc_path)) or "."
    try:
        result = subprocess.run(
            ["git", "-C", doc_dir, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, encoding="utf-8",
        )
    except OSError:
        return doc_dir
    if result.returncode == 0:
        top = result.stdout.strip()
        if top:
            return top
    return doc_dir


def run_companion(companion_path, args, cwd, env=None):
    # encoding="utf-8" is pinned on every subprocess call in this script, for
    # the reason scripts/doc-lifecycle-check.py's docstring records: Python's
    # subprocess text mode otherwise defaults to the locale encoding (cp1252
    # on this maintainer's machine), which can silently mis-decode output.
    run_env = os.environ.copy() if env is None else env
    return subprocess.run(
        ["node", companion_path] + args,
        cwd=cwd, env=run_env, capture_output=True, text=True, encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Reading the document's own structure
# ---------------------------------------------------------------------------

def extract_dimensions(body):
    """The exact '### <dimension>' heading text of every review dimension
    under '## Findings', in document order. These strings are both what the
    submit prompt asks Codex to answer against and what collect's splice
    matches findings back onto - never a paraphrase of either."""
    lines = body.splitlines()
    dims = []
    in_findings = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## Findings":
            in_findings = True
            continue
        if not in_findings:
            continue
        if line.startswith("## ") and stripped != "## Findings":
            break
        if line.startswith("### "):
            dims.append(line[4:].strip())
    return dims


# ---------------------------------------------------------------------------
# Submit: build the prompt, invoke `task --background --json`, write the
# frontmatter field only once a job id is actually in hand.
# ---------------------------------------------------------------------------

def build_submit_prompt(doc_text, dimensions):
    numbered = "\n".join("- %s" % d for d in dimensions)
    return (
        "You are the Reviewer in a structured, self-contained cross-LLM peer review.\n"
        "Read the complete review request document below in full, including "
        "\"## Instructions for Reviewer\" and \"## Document Under Review\". Then write "
        "your independent review as the Reviewer.\n"
        "\n"
        "Respond with ONLY a single JSON object - no markdown code fences, no prose "
        "before or after it - matching exactly this shape:\n"
        "\n"
        "{\n"
        "  \"assessment\": \"<2-3 sentence independent assessment: key strengths, most "
        "important concerns, headline recommendation>\",\n"
        "  \"severityCounts\": {\"blocker\": <int>, \"major\": <int>, \"minor\": <int>, "
        "\"note\": <int>},\n"
        "  \"findings\": [\n"
        "    {\"dimension\": \"<exact dimension name from the list below>\", "
        "\"finding\": \"<your findings for this dimension, using the Finding format from "
        "the Instructions section: one or more lines shaped like "
        "'- [Severity | Confidence] Description... -> Recommendation.', "
        "newline-separated>\"}\n"
        "  ]\n"
        "}\n"
        "\n"
        "Cover every one of these dimensions, exactly once each, using these exact "
        "strings for \"dimension\":\n"
        "%s\n"
        "\n"
        "Do not write Requestor Analysis, Decisions, or Proposed Actions content - none "
        "of that is your responsibility as Reviewer.\n"
        "\n"
        "--- REVIEW REQUEST DOCUMENT FOLLOWS ---\n"
        "\n"
        "%s\n" % (numbered, doc_text)
    )


def cmd_submit(doc_path, companion_override=None):
    doc_path = os.path.abspath(doc_path)
    if not os.path.isfile(doc_path):
        return report("failed", "Review document not found: %s" % doc_path)

    companion = discover_companion(companion_override)
    if not companion:
        return report(
            "unavailable",
            "No codex-companion.mjs found under "
            "~/.claude/plugins/cache/openai-codex/codex/*/scripts/. Dispatch is "
            "unavailable on this machine; use the manual paste path instead.",
        )

    doc_text = read_text(doc_path)
    _fm, body = split_frontmatter(doc_text)
    dimensions = extract_dimensions(body)
    if not dimensions:
        return report(
            "failed",
            "Could not find any '### <dimension>' heading under '## Findings' in "
            "the document; there is nothing to ask the reviewer to cover.",
        )

    prompt = build_submit_prompt(doc_text, dimensions)
    cwd = resolve_cwd(doc_path)

    prompt_fd, prompt_path = tempfile.mkstemp(suffix=".txt", prefix="plab-ai-review-dispatch-")
    try:
        with os.fdopen(prompt_fd, "w", encoding="utf-8") as fh:
            fh.write(prompt)
        result = run_companion(
            companion,
            ["task", "--background", "--json", "--effort", "high",
             "--prompt-file", prompt_path, "--cwd", cwd],
            cwd=cwd,
        )
    finally:
        try:
            os.unlink(prompt_path)
        except OSError:
            pass

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "no output"
        return report("failed", "codex-companion could not submit the task: %s" % detail)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return report("failed", "codex-companion's submit output did not parse as JSON: %s" % exc)

    job_id = payload.get("jobId")
    if not job_id:
        return report("failed", "codex-companion's task output carried no jobId.")

    new_text = join_frontmatter({"type": "review", "dispatch-job": job_id}, body)
    write_text(doc_path, new_text)
    return report("submitted", "Submitted to Codex as %s." % job_id, jobId=job_id, document=doc_path)


# ---------------------------------------------------------------------------
# Collect: resolve the job, parse its output, splice findings in. Any
# structural surprise is the unparseable state, never a partial write.
# ---------------------------------------------------------------------------

def parse_findings_json(raw_output):
    """Best-effort extraction of the findings JSON object from a task's raw
    output text, tolerating a surrounding markdown code fence or stray prose
    (there is no --output-schema path for `task`; see the module docstring).
    Returns a normalized dict, or None if the content cannot be trusted as
    the expected shape."""
    text = (raw_output or "").strip()
    if not text:
        return None

    fence = re.match(r"^```(?:json)?\s*\n(.*)\n```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    assessment = data.get("assessment")
    severity = data.get("severityCounts")
    findings = data.get("findings")
    if not isinstance(assessment, str) or not assessment.strip():
        return None
    if not isinstance(severity, dict):
        return None
    for _label, key in SEVERITY_LABELS:
        if not isinstance(severity.get(key), int) or isinstance(severity.get(key), bool):
            return None
    if not isinstance(findings, list) or not findings:
        return None

    normalized = []
    for item in findings:
        if not isinstance(item, dict):
            return None
        dimension, finding = item.get("dimension"), item.get("finding")
        if not isinstance(dimension, str) or not dimension.strip():
            return None
        if not isinstance(finding, str) or not finding.strip():
            return None
        normalized.append({"dimension": dimension.strip(), "finding": finding.strip()})

    return {"assessment": assessment.strip(), "severityCounts": severity, "findings": normalized}


def set_severity_row(body, label, value):
    pattern = re.compile(r"(?m)^(\|\s*%s\s*\|\s*)(\S+)(\s*\|)" % re.escape(label))
    new_body, count = pattern.subn(lambda m: m.group(1) + str(value) + m.group(3), body, count=1)
    if count != 1:
        raise SpliceError("could not find the '%s' row in the Reviewer Assessment severity table" % label)
    return new_body


def set_reviewer_assessment(body, assessment, reviewer_name, date_str):
    m = re.search(r"(?ms)^##\s+Reviewer Assessment\s*\n(.*?)(?=^##\s+)", body)
    if not m:
        raise SpliceError("could not find the '## Reviewer Assessment' section")
    section = m.group(1)
    new_line = "> **Reviewer - %s (%s):** %s" % (reviewer_name, date_str, assessment)
    new_section, count = re.subn(r"(?m)^>\s*\*\*Reviewer\s*-.*$", new_line, section, count=1)
    if count != 1:
        raise SpliceError("could not find the Reviewer attribution line in '## Reviewer Assessment'")
    return body[:m.start(1)] + new_section + body[m.end(1):]


def set_dimension_finding(body, dimension, finding_text, reviewer_name, date_str):
    header = re.compile(r"(?m)^###\s+%s\s*$" % re.escape(dimension))
    hm = header.search(body)
    if not hm:
        raise SpliceError("could not find a '### %s' heading" % dimension)

    rest = body[hm.end():]
    next_heading = HEADING_RE.search(rest)
    section_end = hm.end() + (next_heading.start() if next_heading else len(rest))
    section = body[hm.end():section_end]

    attr = REVIEWER_ATTRIBUTION_RE.search(section)
    if not attr:
        raise SpliceError("could not find the Reviewer attribution line under '### %s'" % dimension)
    new_attr = "**Reviewer - %s (%s):**" % (reviewer_name, date_str)

    after_attr = section[attr.end():]
    quote = QUOTE_BLOCK_RE.match(after_attr)
    if not quote:
        raise SpliceError("could not find the reviewer findings placeholder under '### %s'" % dimension)

    quote_lines = ["> " + line for line in finding_text.strip().splitlines()] or ["> (no findings)"]
    new_quote_block = quote.group(1) + "\n".join(quote_lines) + "\n"

    new_section = (
        section[:attr.start()] + new_attr + after_attr[:quote.start()]
        + new_quote_block + after_attr[quote.end():]
    )
    return body[:hm.end()] + new_section + body[section_end:]


def splice_findings(body, dimensions, parsed, reviewer_name, date_str):
    findings_by_dim = {f["dimension"]: f["finding"] for f in parsed["findings"]}
    doc_dims, parsed_dims = set(dimensions), set(findings_by_dim)
    if doc_dims != parsed_dims:
        missing = sorted(doc_dims - parsed_dims)
        extra = sorted(parsed_dims - doc_dims)
        parts = []
        if missing:
            parts.append("missing from the reviewer's output: %s" % missing)
        if extra:
            parts.append("not a dimension in this document: %s" % extra)
        raise SpliceError("the reviewer's dimensions do not match the document's (%s)" % "; ".join(parts))

    new_body = set_reviewer_assessment(body, parsed["assessment"], reviewer_name, date_str)
    counts = parsed["severityCounts"]
    for label, key in SEVERITY_LABELS:
        new_body = set_severity_row(new_body, label, counts[key])
    for dim in dimensions:
        new_body = set_dimension_finding(new_body, dim, findings_by_dim[dim], reviewer_name, date_str)
    return new_body


def save_raw_output(doc_path, job_id, raw_output):
    base, _ext = os.path.splitext(doc_path)
    raw_path = "%s.dispatch-raw-%s.txt" % (base, job_id)
    write_text(raw_path, raw_output)
    return raw_path


def cmd_collect(doc_path, companion_override=None):
    doc_path = os.path.abspath(doc_path)
    if not os.path.isfile(doc_path):
        return report("failed", "Review document not found: %s" % doc_path)

    doc_text = read_text(doc_path)
    fm, body = split_frontmatter(doc_text)
    job_id = fm.get("dispatch-job")
    if not job_id:
        return report(
            "failed",
            "No 'dispatch-job' field in this document's frontmatter; nothing to "
            "collect. Was it dispatched with 'submit'?",
        )

    companion = discover_companion(companion_override)
    if not companion:
        return report(
            "unavailable",
            "No codex-companion.mjs found; cannot collect job %s. The job id is "
            "preserved in the document's frontmatter for a later attempt." % job_id,
        )

    cwd = resolve_cwd(doc_path)
    env = os.environ.copy()
    env.pop("CODEX_COMPANION_SESSION_ID", None)  # defensive; see module docstring
    result = run_companion(companion, ["result", job_id, "--json", "--cwd", cwd], cwd=cwd, env=env)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or "no output"
        return report("failed", "codex-companion could not resolve job %s: %s" % (job_id, detail), jobId=job_id)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return report("failed", "codex-companion's result output did not parse as JSON: %s" % exc, jobId=job_id)

    job = payload.get("job") or {}
    status = job.get("status")

    if status in ("queued", "running"):
        return report("running", "Job %s is still %s. Try again once it finishes." % (job_id, status), jobId=job_id)

    if status in ("failed", "cancelled"):
        message = (payload.get("storedJob") or {}).get("errorMessage") or ("Job %s ended as %s." % (job_id, status))
        return report("failed", message, jobId=job_id)

    if status != "completed":
        return report("failed", "Job %s reported an unrecognized status %r." % (job_id, status), jobId=job_id)

    raw_output = (((payload.get("storedJob") or {}).get("result") or {}).get("rawOutput")) or ""
    parsed = parse_findings_json(raw_output)
    if parsed is None:
        raw_path = save_raw_output(doc_path, job_id, raw_output)
        return report(
            "unparseable",
            "Job %s completed but its output did not parse as the expected findings "
            "JSON. Raw output saved to %s." % (job_id, raw_path),
            jobId=job_id, rawOutputPath=raw_path,
        )

    dimensions = extract_dimensions(body)
    today = date.today().isoformat()
    try:
        new_body = splice_findings(body, dimensions, parsed, reviewer_name="Codex", date_str=today)
    except SpliceError as exc:
        raw_path = save_raw_output(doc_path, job_id, raw_output)
        return report(
            "unparseable",
            "Job %s completed and parsed as JSON, but %s. Raw output saved to %s." % (job_id, exc, raw_path),
            jobId=job_id, rawOutputPath=raw_path,
        )

    write_text(doc_path, join_frontmatter(fm, new_body))
    return report("collected", "Findings from %s written into the reviewer placeholders." % job_id,
                   jobId=job_id, document=doc_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("action", choices=["submit", "collect"])
    parser.add_argument("document", help="Path to the <basename>_reviewed-by-<reviewer>.md review request document.")
    parser.add_argument("--companion", default=None,
                         help="Override path to codex-companion.mjs. For tests; normal use discovers it.")
    args = parser.parse_args(argv)

    if args.action == "submit":
        return cmd_submit(args.document, args.companion)
    return cmd_collect(args.document, args.companion)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - see module EXIT-CODE CONTRACT: never exit 1 on a crash
        print(json.dumps({"state": "broken", "message": "%s: %s" % (type(exc).__name__, exc)}))
        sys.exit(2)
