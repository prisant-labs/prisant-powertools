---
type: llm
focus: trace
weight: 2
---

The session started with no prior conversation and no document already read or written, so nothing is open.

PASS if the transcript shows no attempt to open, list, or search any file in order to look for pending questions, decisions, or tasks. Reading this skill's own bundled reference files (paths containing "plab-resolve-open-items/references/") to learn its own procedure is fine and does not fail this check. Saying in the reply that nothing is open, and offering to walk one named document, is the correct behavior.

FAIL if the transcript shows a Read, Glob, or Grep call aimed at a project file, a memory file, a session log, or any other document outside this skill's own reference files, used to go hunting for items that might be open.
