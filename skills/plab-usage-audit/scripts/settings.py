"""
Shared settings loader for plab-usage-audit's collector and ledger scripts.

Owner-specific values (automated-session folder patterns, project display
aliases, the time zone, the transcript root) never live in the shipped
code. They live in a settings file the owner points at with --config:

  .claude/plab-usage-audit.local.md

That file is Markdown with a YAML frontmatter block. The standard library
has no YAML parser, so this module implements a small, documented subset
rather than depending on one. It supports exactly:

- a scalar: `key: value`, where value is unquoted, single-quoted, or
  double-quoted
- a null: `key:` with nothing after it, or `key: null` / `key: ~`
- a boolean: `key: true` / `key: false` (case-insensitive)
- a number: a value that parses as an int or a float
- a block list, one level, under a key with nothing after the colon:
    key:
      - first
      - second
- a block mapping, one level, under a key with nothing after the colon:
    key:
      subkey: value
      other: value

- a flow list of scalars on one line: `key: [a, "b c", 3]`
- an inline comment: ` # ...` after a value, outside quotes

Nothing else. No flow mappings (`{a: b}`), no nested flow lists, no multi-line
scalars, no anchors, no second level of nesting under a list or mapping
entry, no tags. A settings file that needs more than this subset is
out of scope by design: the subset exists to carry a short list of
owner values, not to be a YAML engine.

A line is a comment, and ignored, when its first non-space character is
`#`. Blank lines are ignored. Indentation is measured in leading spaces;
a line belongs to the block opened by the nearest preceding line with
strictly less indentation.
"""
import re

_BOOL = {"true": True, "false": False}


def _unquote_key(s):
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _strip_comment(s):
    """Drop an inline comment: a `#` preceded by whitespace and outside quotes."""
    quote = None
    for idx, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "#" and (idx == 0 or s[idx - 1] in " \t"):
            return s[:idx].rstrip()
    return s


def _split_flow(inner):
    """Split the inside of a flow list on commas that are outside quotes."""
    items, buf, quote = [], "", None
    for ch in inner:
        if quote:
            buf += ch
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf += ch
        elif ch == ",":
            items.append(buf)
            buf = ""
        else:
            buf += ch
    if buf.strip():
        items.append(buf)
    return [i for i in items if i.strip()]


def _scalar(raw):
    """Parse one value: a one-level flow list `[a, b]`, or a scalar with quotes stripped,
    else coerced to bool/null/number/string."""
    s = _strip_comment(raw.strip())
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(item) for item in _split_flow(s[1:-1])]
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    if s == "" or s in ("null", "~"):
        return None
    low = s.lower()
    if low in _BOOL:
        return _BOOL[low]
    if re.fullmatch(r"[+-]?\d+", s):
        return int(s)
    if re.fullmatch(r"[+-]?\d+\.\d+", s):
        return float(s)
    return s


def parse_yaml_subset(text):
    """Parse the documented subset into a plain dict. Raises ValueError on anything
    outside the subset (a second level of nesting, a flow collection, a tab)."""
    lines = []
    for raw in text.split("\n"):
        if "\t" in raw:
            raise ValueError("tabs are not part of the supported subset: " + raw)
        stripped = raw.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        lines.append(raw.rstrip())

    result = {}
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        indent = _indent(line)
        if indent != 0:
            raise ValueError("unexpected indentation at top level: " + line)
        body = line.strip()
        if body.startswith("- "):
            raise ValueError("a list cannot appear at the top level: " + line)
        m = re.match(r"^([^:#]+):\s*(.*)$", body)
        if not m:
            raise ValueError("not a key: value line: " + line)
        key = _unquote_key(m.group(1).strip())
        rest = _strip_comment(m.group(2).strip())
        i += 1
        if rest != "":
            result[key] = _scalar(rest)
            continue
        # a block follows: gather every line more indented than this key
        block = []
        while i < n and _indent(lines[i]) > 0:
            block.append(lines[i])
            i += 1
        if not block:
            result[key] = None
            continue
        block_indent = _indent(block[0])
        for bl in block:
            if _indent(bl) != block_indent:
                raise ValueError("the subset supports exactly one level of nesting: " + bl)
        first_body = block[0].strip()
        if first_body.startswith("- "):
            items = []
            for bl in block:
                bbody = bl.strip()
                if not bbody.startswith("- "):
                    raise ValueError("mixed list and mapping under one key: " + bl)
                items.append(_scalar(bbody[2:]))
            result[key] = items
        else:
            sub = {}
            for bl in block:
                bm = re.match(r"^([^:#]+):\s*(.*)$", bl.strip())
                if not bm:
                    raise ValueError("not a key: value line inside a mapping block: " + bl)
                skey = _unquote_key(bm.group(1).strip())
                sval = _strip_comment(bm.group(2).strip())
                sub[skey] = _scalar(sval)
            result[key] = sub
    return result


def extract_frontmatter(text):
    """Return the text between the first two `---` lines, or '' if there is none."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[1:idx])
    return ""


def load_settings_file(path):
    """Read a .local.md settings file and return its frontmatter as a dict.
    Returns {} if the file does not exist or has no frontmatter."""
    import os
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm = extract_frontmatter(text)
    if not fm.strip():
        return {}
    return parse_yaml_subset(fm)


# ---------------------------------------------------------------- resolved settings
# A tiny holder: explicit CLI values win, then the settings file, then a generic
# built-in default that carries no owner-specific value.
class Settings:
    def __init__(self, config_path=None, cli=None):
        self.raw = load_settings_file(config_path) if config_path else {}
        self.cli = cli or {}

    def _resolve(self, key, default=None):
        if self.cli.get(key) is not None:
            return self.cli[key]
        if key in self.raw and self.raw[key] is not None:
            return self.raw[key]
        return default

    @property
    def timezone(self):
        return self._resolve("timezone", None)

    @property
    def transcript_root(self):
        return self._resolve("transcript_root", None)

    @property
    def noise_patterns(self):
        # The documented key is `automated.dir_patterns` (references/settings-example.md);
        # the flat `noise_patterns` key is accepted too.
        automated = self.raw.get("automated")
        v = automated.get("dir_patterns") if isinstance(automated, dict) else None
        if v is None:
            v = self.raw.get("noise_patterns")
        return list(v) if isinstance(v, list) else []

    @property
    def aliases(self):
        # The documented key is `project_aliases`; the short `aliases` key is accepted too.
        v = self.raw.get("project_aliases")
        if v is None:
            v = self.raw.get("aliases")
        return dict(v) if isinstance(v, dict) else {}
