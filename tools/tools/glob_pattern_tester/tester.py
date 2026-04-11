"""
Glob Pattern Tester & Explainer -- Pattern Verifier for Agents

Tests glob patterns against file paths, explains what each part matches in
plain English, shows which files in a directory tree would match, and supports
multiple glob flavors: Unix shell globs, .gitignore patterns, and Python
fnmatch.

Agents constantly generate glob patterns for .gitignore, CI configs, file
watchers, and build tools.  Glob syntax differs subtly between tools -- ** means
different things in bash vs gitignore, brace expansion works in some contexts
but not others, and negation patterns are gitignore-specific.  This tool lets
an agent verify a glob pattern before shipping it.

CAPABILITIES
============
  - parse_glob(pattern, flavor)          -> ParsedGlob         structured components
  - explain_glob(pattern, flavor)        -> str                 multi-line English
  - explain_brief(pattern, flavor)       -> str                 one-line summary
  - match_path(pattern, path, flavor)    -> MatchResult         test single path
  - match_paths(pattern, paths, flavor)  -> TreeMatchResult     test multiple paths
  - expand_braces(pattern)               -> list[str]           brace expansion
  - parse_gitignore(content)             -> GitignoreFile       parse .gitignore
  - check_gitignore(gitignore, path)     -> GitignoreResult     check against rules

SUPPORTED FLAVORS
=================
  - unix      : Shell glob (*, **, ?, [...], {a,b})
  - gitignore : .gitignore rules (negation, dir markers, anchoring, **)
  - fnmatch   : Python fnmatch (*, ?, [seq], [!seq] -- no ** or braces)

Pure Python, no external dependencies beyond the standard library.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ============================================================
# Enums and data classes
# ============================================================

class GlobFlavor(Enum):
    UNIX = "unix"
    GITIGNORE = "gitignore"
    FNMATCH = "fnmatch"


class ComponentKind(Enum):
    LITERAL = "literal"
    STAR = "star"
    DOUBLE_STAR = "double_star"
    QUESTION = "question"
    CHAR_CLASS = "char_class"
    BRACE = "brace"
    SEPARATOR = "separator"
    NEGATION = "negation"
    DIR_MARKER = "dir_marker"


@dataclass
class GlobComponent:
    kind: ComponentKind
    raw: str
    value: Any = None
    negated: bool = False


@dataclass
class ParsedGlob:
    pattern: str
    flavor: GlobFlavor
    components: list[GlobComponent] = field(default_factory=list)
    is_negated: bool = False
    is_dir_only: bool = False
    is_anchored: bool = False


@dataclass
class MatchResult:
    pattern: str
    path: str
    matched: bool
    flavor: str
    reason: str = ""


@dataclass
class TreeMatchResult:
    pattern: str
    flavor: str
    matched_paths: list[str] = field(default_factory=list)
    unmatched_paths: list[str] = field(default_factory=list)


@dataclass
class GitignoreRule:
    line_number: int
    pattern: str
    is_negated: bool = False
    is_comment: bool = False
    is_blank: bool = False
    is_dir_only: bool = False
    is_anchored: bool = False


@dataclass
class GitignoreResult:
    path: str
    is_ignored: bool
    matching_rule: GitignoreRule | None = None
    reason: str = ""


@dataclass
class GitignoreFile:
    rules: list[GitignoreRule] = field(default_factory=list)
    source: str = ""


# ============================================================
# Parser
# ============================================================

def _parse_char_class(pattern: str, pos: int) -> tuple[GlobComponent, int]:
    start = pos
    pos += 1
    negated = False
    if pos < len(pattern) and pattern[pos] in ("!", "^"):
        negated = True
        pos += 1

    chars: list[str | tuple[str, str]] = []
    if pos < len(pattern) and pattern[pos] == "]":
        chars.append("]")
        pos += 1

    while pos < len(pattern) and pattern[pos] != "]":
        ch = pattern[pos]
        if pos + 2 < len(pattern) and pattern[pos + 1] == "-" and pattern[pos + 2] != "]":
            chars.append((ch, pattern[pos + 2]))
            pos += 3
        else:
            chars.append(ch)
            pos += 1

    if pos >= len(pattern):
        return GlobComponent(kind=ComponentKind.LITERAL, raw=pattern[start:pos], value=pattern[start:pos]), pos

    raw = pattern[start:pos + 1]
    pos += 1
    return GlobComponent(kind=ComponentKind.CHAR_CLASS, raw=raw, value=chars, negated=negated), pos


def _parse_brace(pattern: str, pos: int) -> tuple[GlobComponent | list[GlobComponent], int]:
    start = pos
    pos += 1
    depth = 1
    options: list[str] = []
    current = ""

    while pos < len(pattern) and depth > 0:
        ch = pattern[pos]
        if ch == "{":
            depth += 1
            current += ch
            pos += 1
        elif ch == "}" and depth == 1:
            depth -= 1
            options.append(current)
            pos += 1
        elif ch == "}" and depth > 1:
            depth -= 1
            current += ch
            pos += 1
        elif ch == "," and depth == 1:
            options.append(current)
            current = ""
            pos += 1
        elif ch == "\\" and pos + 1 < len(pattern):
            current += pattern[pos + 1]
            pos += 2
        else:
            current += ch
            pos += 1

    if depth > 0 or len(options) < 2:
        literal_text = pattern[start:pos]
        return [GlobComponent(kind=ComponentKind.LITERAL, raw=ch, value=ch) for ch in literal_text], pos

    return GlobComponent(kind=ComponentKind.BRACE, raw=pattern[start:pos], value=options), pos


def parse_glob(pattern: str, flavor: GlobFlavor = GlobFlavor.UNIX) -> ParsedGlob:
    """Parse a glob pattern into structured components."""
    result = ParsedGlob(pattern=pattern, flavor=flavor)
    if not pattern:
        return result

    working = pattern

    if flavor == GlobFlavor.GITIGNORE and working.startswith("!"):
        result.is_negated = True
        result.components.append(GlobComponent(kind=ComponentKind.NEGATION, raw="!", value="!"))
        working = working[1:]

    if flavor == GlobFlavor.GITIGNORE and working.endswith("/") and len(working) > 1:
        result.is_dir_only = True
        working = working[:-1]

    if flavor == GlobFlavor.GITIGNORE and "/" in working:
        result.is_anchored = True

    pos = 0
    while pos < len(working):
        ch = working[pos]
        if ch == "\\" and pos + 1 < len(working):
            result.components.append(GlobComponent(kind=ComponentKind.LITERAL, raw=working[pos:pos+2], value=working[pos+1]))
            pos += 2
        elif ch == "/":
            result.components.append(GlobComponent(kind=ComponentKind.SEPARATOR, raw="/", value="/"))
            pos += 1
        elif ch == "*":
            if pos + 1 < len(working) and working[pos + 1] == "*":
                if flavor == GlobFlavor.FNMATCH:
                    result.components.append(GlobComponent(kind=ComponentKind.STAR, raw="**", value="*"))
                else:
                    result.components.append(GlobComponent(kind=ComponentKind.DOUBLE_STAR, raw="**", value="**"))
                pos += 2
            else:
                result.components.append(GlobComponent(kind=ComponentKind.STAR, raw="*", value="*"))
                pos += 1
        elif ch == "?":
            result.components.append(GlobComponent(kind=ComponentKind.QUESTION, raw="?", value="?"))
            pos += 1
        elif ch == "[":
            comp, pos = _parse_char_class(working, pos)
            result.components.append(comp)
        elif ch == "{" and flavor != GlobFlavor.FNMATCH:
            brace_result, pos = _parse_brace(working, pos)
            if isinstance(brace_result, list):
                result.components.extend(brace_result)
            else:
                result.components.append(brace_result)
        else:
            result.components.append(GlobComponent(kind=ComponentKind.LITERAL, raw=ch, value=ch))
            pos += 1

    if result.is_dir_only:
        result.components.append(GlobComponent(kind=ComponentKind.DIR_MARKER, raw="/", value="/"))

    return result


# ============================================================
# Matcher
# ============================================================

def _char_class_to_regex(comp: GlobComponent) -> str:
    inner = ""
    if comp.negated:
        inner += "^"
    for item in comp.value:
        if isinstance(item, tuple):
            inner += re.escape(item[0]) + "-" + re.escape(item[1])
        else:
            inner += re.escape(item)
    return f"[{inner}]"


def _brace_to_regex(comp: GlobComponent) -> str:
    options = [re.escape(o) for o in comp.value]
    return "(?:" + "|".join(options) + ")"


def _glob_to_regex(parsed: ParsedGlob) -> str:
    flavor = parsed.flavor
    parts: list[str] = []
    components = [c for c in parsed.components if c.kind not in (ComponentKind.NEGATION, ComponentKind.DIR_MARKER)]

    # Strip leading / in gitignore (anchor marker, not literal)
    if flavor == GlobFlavor.GITIGNORE and components and components[0].kind == ComponentKind.SEPARATOR:
        components = components[1:]

    i = 0
    while i < len(components):
        comp = components[i]
        kind = comp.kind
        if kind == ComponentKind.LITERAL:
            parts.append(re.escape(comp.value))
        elif kind == ComponentKind.STAR:
            parts.append("[^/]*")
        elif kind == ComponentKind.DOUBLE_STAR:
            prev_sep = (i == 0 or components[i-1].kind == ComponentKind.SEPARATOR)
            next_sep = (i+1 >= len(components) or components[i+1].kind == ComponentKind.SEPARATOR)
            if prev_sep and next_sep:
                if i+1 < len(components) and components[i+1].kind == ComponentKind.SEPARATOR:
                    parts.append("(?:.+/)?")
                    i += 1
                else:
                    parts.append(".*")
            else:
                parts.append("[^/]*")
        elif kind == ComponentKind.QUESTION:
            parts.append("[^/]")
        elif kind == ComponentKind.CHAR_CLASS:
            parts.append(_char_class_to_regex(comp))
        elif kind == ComponentKind.BRACE:
            parts.append(_brace_to_regex(comp))
        elif kind == ComponentKind.SEPARATOR:
            parts.append("/")
        i += 1
    return "".join(parts)


def _normalize_path(path: str) -> str:
    path = path.replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return path


def match_path(pattern: str, path: str, flavor: GlobFlavor = GlobFlavor.UNIX, is_dir: bool = False) -> MatchResult:
    """Test whether a glob pattern matches a file path."""
    parsed = parse_glob(pattern, flavor)
    norm_path = _normalize_path(path)

    if parsed.is_dir_only and not is_dir:
        return MatchResult(pattern=pattern, path=path, matched=False, flavor=flavor.value,
                           reason="Pattern has trailing / (directory only) but path is not a directory")

    regex_str = _glob_to_regex(parsed)

    if flavor == GlobFlavor.GITIGNORE and not parsed.is_anchored:
        regex_pattern = f"(?:^|.*/){regex_str}$"
    elif flavor == GlobFlavor.FNMATCH:
        regex_pattern = f"^{regex_str}$"
    else:
        regex_pattern = f"^{regex_str}$"

    try:
        matched = bool(re.match(regex_pattern, norm_path))
    except re.error as e:
        return MatchResult(pattern=pattern, path=path, matched=False, flavor=flavor.value,
                           reason=f"Regex compilation error: {e}")

    reason = "Pattern matches the path" if matched else "Pattern does not match the path"
    if matched and parsed.is_negated:
        reason = "Pattern negates (excludes) this path"
    return MatchResult(pattern=pattern, path=path, matched=matched, flavor=flavor.value, reason=reason)


def match_paths(pattern: str, paths: list[str], flavor: GlobFlavor = GlobFlavor.UNIX,
                is_dir_func=None) -> TreeMatchResult:
    """Test a glob pattern against multiple paths."""
    result = TreeMatchResult(pattern=pattern, flavor=flavor.value)
    for path in paths:
        is_dir = is_dir_func(path) if is_dir_func else path.endswith("/")
        mr = match_path(pattern, path, flavor, is_dir=is_dir)
        if mr.matched:
            result.matched_paths.append(path)
        else:
            result.unmatched_paths.append(path)
    return result


def expand_braces(pattern: str) -> list[str]:
    """Expand brace expressions, returning all variants."""
    depth = 0
    brace_start = -1
    for i, ch in enumerate(pattern):
        if ch == "\\" and i + 1 < len(pattern):
            continue
        if ch == "{":
            if depth == 0:
                brace_start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and brace_start >= 0:
                inner = pattern[brace_start + 1:i]
                options = _split_brace_options(inner)
                if len(options) < 2:
                    brace_start = -1
                    continue
                prefix = pattern[:brace_start]
                suffix = pattern[i + 1:]
                results = []
                for opt in options:
                    results.extend(expand_braces(prefix + opt + suffix))
                return results
    return [pattern]


def _split_brace_options(inner: str) -> list[str]:
    options, depth, current, i = [], 0, "", 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and i + 1 < len(inner):
            current += inner[i:i+2]
            i += 2
            continue
        if ch == "{":
            depth += 1
            current += ch
        elif ch == "}":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            options.append(current)
            current = ""
        else:
            current += ch
        i += 1
    options.append(current)
    return options


# ============================================================
# Explainer
# ============================================================

def _explain_component(comp: GlobComponent, flavor: GlobFlavor) -> str:
    kind = comp.kind
    if kind == ComponentKind.LITERAL:
        return f"literal character '{comp.value}'"
    elif kind == ComponentKind.STAR:
        return "any sequence of characters within a single directory (does not cross path separators)"
    elif kind == ComponentKind.DOUBLE_STAR:
        if flavor == GlobFlavor.FNMATCH:
            return "any sequence of characters (treated as single * in fnmatch)"
        return "zero or more directories (crosses path separators)"
    elif kind == ComponentKind.QUESTION:
        return "any single character (except path separator)"
    elif kind == ComponentKind.CHAR_CLASS:
        parts = []
        for item in comp.value:
            if isinstance(item, tuple):
                parts.append(f"'{item[0]}' through '{item[1]}'")
            else:
                parts.append(f"'{item}'")
        if comp.negated:
            return f"any single character NOT in: {', '.join(parts)}"
        return f"any single character in: {', '.join(parts)}"
    elif kind == ComponentKind.BRACE:
        return f"one of: {', '.join(repr(o) for o in comp.value)} (brace expansion)"
    elif kind == ComponentKind.SEPARATOR:
        return "path separator"
    elif kind == ComponentKind.NEGATION:
        return "negation: this pattern UN-ignores (re-includes) matching paths"
    elif kind == ComponentKind.DIR_MARKER:
        return "trailing slash: matches only directories, not files"
    return f"unknown component: {comp.raw}"


def explain_glob(pattern: str, flavor: GlobFlavor = GlobFlavor.UNIX) -> str:
    """Return a detailed plain English explanation of a glob pattern."""
    if not pattern:
        return "Empty pattern: matches nothing."
    parsed = parse_glob(pattern, flavor)
    lines: list[str] = [f"Pattern: {pattern}", f"Flavor:  {flavor.value}", ""]

    if flavor == GlobFlavor.GITIGNORE:
        if parsed.is_negated:
            lines.append("Negated: YES (this pattern re-includes previously ignored files)")
        if parsed.is_dir_only:
            lines.append("Directory only: YES (only matches directories, not files)")
        if parsed.is_anchored:
            lines.append("Anchored: YES (pattern contains / so matches relative to root)")
        else:
            lines.append("Anchored: NO (pattern matches anywhere in the directory tree)")
        lines.append("")

    lines.append("Components:")
    for i, comp in enumerate(parsed.components, 1):
        lines.append(f"  {i}. {comp.raw!r} -> {_explain_component(comp, flavor)}")

    lines.append("")
    lines.append("Summary: " + explain_brief(pattern, flavor))
    return "\n".join(lines)


def explain_brief(pattern: str, flavor: GlobFlavor = GlobFlavor.UNIX) -> str:
    """Return a single-line summary of a glob pattern."""
    if not pattern:
        return "Empty pattern: matches nothing."
    parsed = parse_glob(pattern, flavor)
    parts = []
    literal_run = ""
    for comp in parsed.components:
        if comp.kind == ComponentKind.LITERAL:
            literal_run += comp.value
            continue
        if literal_run:
            parts.append(f"'{literal_run}'")
            literal_run = ""
        kind = comp.kind
        if kind == ComponentKind.STAR:
            parts.append("(any)")
        elif kind == ComponentKind.DOUBLE_STAR:
            parts.append("(any directories)")
        elif kind == ComponentKind.QUESTION:
            parts.append("(any char)")
        elif kind == ComponentKind.CHAR_CLASS:
            parts.append("(char not in class)" if comp.negated else "(char in class)")
        elif kind == ComponentKind.BRACE:
            parts.append("{" + ",".join(comp.value) + "}")
        elif kind == ComponentKind.SEPARATOR:
            parts.append("/")
        elif kind == ComponentKind.NEGATION:
            parts.append("NOT")
        elif kind == ComponentKind.DIR_MARKER:
            parts.append("(dirs only)")
    if literal_run:
        parts.append(f"'{literal_run}'")
    summary = " ".join(parts) if parts else "(empty pattern)"

    modifiers = []
    if parsed.is_negated:
        modifiers.append("negated (re-includes)")
    if parsed.is_dir_only:
        modifiers.append("directories only")
    if parsed.is_anchored:
        modifiers.append("anchored to root")
    elif parsed.flavor == GlobFlavor.GITIGNORE and not parsed.is_anchored:
        modifiers.append("matches anywhere in tree")
    if modifiers:
        summary += f" [{', '.join(modifiers)}]"
    return summary


# ============================================================
# Gitignore
# ============================================================

def parse_gitignore(content: str, source: str = ".gitignore") -> GitignoreFile:
    """Parse a .gitignore file's content into rules."""
    result = GitignoreFile(source=source)
    for line_num, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.rstrip()
        if not line or line.isspace():
            result.rules.append(GitignoreRule(line_number=line_num, pattern="", is_blank=True))
            continue
        if line.startswith("#"):
            result.rules.append(GitignoreRule(line_number=line_num, pattern=line, is_comment=True))
            continue
        parsed = parse_glob(line, GlobFlavor.GITIGNORE)
        result.rules.append(GitignoreRule(
            line_number=line_num, pattern=line,
            is_negated=parsed.is_negated, is_dir_only=parsed.is_dir_only, is_anchored=parsed.is_anchored,
        ))
    return result


def check_gitignore(gitignore: GitignoreFile, path: str, is_dir: bool = False) -> GitignoreResult:
    """Check whether a path is ignored by .gitignore rules."""
    ignored = False
    matching_rule: GitignoreRule | None = None
    reason = "No rule matched"

    for rule in gitignore.rules:
        if rule.is_blank or rule.is_comment:
            continue
        match_pattern = rule.pattern[1:] if rule.is_negated else rule.pattern
        result = match_path(match_pattern, path, flavor=GlobFlavor.GITIGNORE, is_dir=is_dir)
        if result.matched:
            if rule.is_negated:
                ignored = False
                matching_rule = rule
                reason = f"Re-included by negation pattern at line {rule.line_number}: {rule.pattern}"
            else:
                ignored = True
                matching_rule = rule
                reason = f"Ignored by pattern at line {rule.line_number}: {rule.pattern}"

    return GitignoreResult(path=path, is_ignored=ignored, matching_rule=matching_rule, reason=reason)


# ============================================================
# CLI
# ============================================================

def main():
    """CLI entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Test glob patterns against file paths, explain matches, support multiple flavors.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # test
    tp = subparsers.add_parser("test", help="Test paths against a glob pattern")
    tp.add_argument("pattern")
    tp.add_argument("paths", nargs="+")
    tp.add_argument("--flavor", "-f", default="unix")
    tp.add_argument("--verbose", "-v", action="store_true")

    # explain
    ep = subparsers.add_parser("explain", help="Explain a glob pattern")
    ep.add_argument("pattern")
    ep.add_argument("--flavor", "-f", default="unix")
    ep.add_argument("--brief", "-b", action="store_true")

    # parse
    pp = subparsers.add_parser("parse", help="Show parsed components")
    pp.add_argument("pattern")
    pp.add_argument("--flavor", "-f", default="unix")

    args = parser.parse_args()
    flavors = {"unix": GlobFlavor.UNIX, "gitignore": GlobFlavor.GITIGNORE, "fnmatch": GlobFlavor.FNMATCH}

    if args.command == "test":
        flavor = flavors.get(args.flavor, GlobFlavor.UNIX)
        for path in args.paths:
            r = match_path(args.pattern, path, flavor, is_dir=path.endswith("/"))
            status = "MATCH" if r.matched else "NO MATCH"
            print(f"  {status}  {path}")
            if args.verbose:
                print(f"    Reason: {r.reason}")

    elif args.command == "explain":
        flavor = flavors.get(args.flavor, GlobFlavor.UNIX)
        if args.brief:
            print(explain_brief(args.pattern, flavor))
        else:
            print(explain_glob(args.pattern, flavor))

    elif args.command == "parse":
        flavor = flavors.get(args.flavor, GlobFlavor.UNIX)
        parsed = parse_glob(args.pattern, flavor)
        print(f"Pattern: {args.pattern}")
        print(f"Flavor:  {flavor.value}")
        print()
        print("Components:")
        for i, comp in enumerate(parsed.components, 1):
            print(f"  {i}. [{comp.kind.value}] {comp.raw!r} -> {_explain_component(comp, flavor)}")
        if "{" in args.pattern:
            expanded = expand_braces(args.pattern)
            if len(expanded) > 1:
                print(f"\nBrace expansion ({len(expanded)} variants):")
                for v in expanded:
                    print(f"  - {v}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
