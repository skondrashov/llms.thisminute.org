"""
Regex Explainer & Tester -- Pattern Verifier for Agents

Parses regular expressions into structured components using Python's sre_parse,
explains them in plain English, tests them against strings with full match
details (groups, spans, multiple matches), and provides step-by-step debug
traces showing which part of the pattern matches which part of the input.

Agents constantly generate and review regexes -- LLMs frequently produce
patterns that *look* right but fail on edge cases.  This tool lets an agent
verify a regex before shipping it.

CAPABILITIES
============
  - parse_regex(pattern)      -> list[RegexComponent]   structured parse tree
  - explain_regex(pattern)    -> str                    multi-line English explanation
  - explain_brief(pattern)    -> str                    one-line summary
  - check_regex(pattern, s)   -> MatchResult            full/partial match + groups
  - check_regex_multi(p, ss)  -> list[MatchResult]      batch test
  - debug_match(pattern, s)   -> DebugResult            step-by-step trace

SUPPORTED CONSTRUCTS
====================
Literals, character classes ([a-z], \\d, \\w, \\s and negations), anchors
(^, $, \\b, \\B, \\A, \\Z), quantifiers (*, +, ?, {n}, {n,m}, lazy
variants), groups (capturing, non-capturing, named), alternation (|),
backreferences (\\1), lookahead/lookbehind (positive and negative),
conditionals, and the dot (.).

Pure Python, no external dependencies beyond the standard library.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass, field
from typing import Any

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import sre_parse


# ============================================================
# Data classes
# ============================================================

@dataclass
class RegexComponent:
    """A single component of a parsed regular expression."""

    kind: str  # e.g., "literal", "char_class", "quantifier", "group", "anchor"
    description: str
    value: Any = None
    children: list["RegexComponent"] = field(default_factory=list)
    quantifier: str | None = None  # e.g., "+", "*", "?", "{2,5}"
    greedy: bool = True


@dataclass
class MatchResult:
    """Result of testing a regex against a single string."""

    pattern: str
    test_string: str
    full_match: bool = False
    partial_match: bool = False
    match_text: str | None = None
    match_start: int | None = None
    match_end: int | None = None
    groups: tuple = ()
    named_groups: dict = field(default_factory=dict)
    all_matches: list[str] = field(default_factory=list)
    all_match_spans: list[tuple[int, int]] = field(default_factory=list)
    error: str | None = None


@dataclass
class DebugStep:
    """A single step in the regex debug trace."""

    step_number: int
    component_description: str
    component_kind: str
    pattern_fragment: str
    matched_text: str | None
    position_start: int
    position_end: int
    success: bool
    note: str = ""


@dataclass
class DebugResult:
    """Full debug trace for a regex match attempt."""

    pattern: str
    test_string: str
    steps: list[DebugStep] = field(default_factory=list)
    overall_match: bool = False
    match_text: str | None = None
    error: str | None = None


# ============================================================
# sre_parse opcode constants
# ============================================================

_LITERAL = sre_parse.LITERAL
_NOT_LITERAL = sre_parse.NOT_LITERAL
_AT = sre_parse.AT
_IN = sre_parse.IN
_ANY = sre_parse.ANY
_BRANCH = sre_parse.BRANCH
_SUBPATTERN = sre_parse.SUBPATTERN
_GROUPREF = sre_parse.GROUPREF
_GROUPREF_EXISTS = sre_parse.GROUPREF_EXISTS
_ASSERT = sre_parse.ASSERT
_ASSERT_NOT = sre_parse.ASSERT_NOT
_AT_BEGINNING = sre_parse.AT_BEGINNING
_AT_BEGINNING_STRING = sre_parse.AT_BEGINNING_STRING
_AT_END = sre_parse.AT_END
_AT_END_STRING = sre_parse.AT_END_STRING
_AT_BOUNDARY = sre_parse.AT_BOUNDARY
_AT_NON_BOUNDARY = sre_parse.AT_NON_BOUNDARY
_CATEGORY = sre_parse.CATEGORY
_CATEGORY_DIGIT = sre_parse.CATEGORY_DIGIT
_CATEGORY_NOT_DIGIT = sre_parse.CATEGORY_NOT_DIGIT
_CATEGORY_WORD = sre_parse.CATEGORY_WORD
_CATEGORY_NOT_WORD = sre_parse.CATEGORY_NOT_WORD
_CATEGORY_SPACE = sre_parse.CATEGORY_SPACE
_CATEGORY_NOT_SPACE = sre_parse.CATEGORY_NOT_SPACE
_MAX_REPEAT = sre_parse.MAX_REPEAT
_MIN_REPEAT = sre_parse.MIN_REPEAT
_RANGE = sre_parse.RANGE
_NEGATE = sre_parse.NEGATE
_MAXREPEAT = sre_parse.MAXREPEAT


# ============================================================
# Parser -- pattern string -> list[RegexComponent]
# ============================================================

def _chr_safe(code: int) -> str:
    """Convert a character code to a printable representation."""
    c = chr(code)
    if c.isprintable() and not c.isspace():
        return c
    if c == "\n":
        return "\\n"
    if c == "\r":
        return "\\r"
    if c == "\t":
        return "\\t"
    if c == " ":
        return " "
    return f"\\x{code:02x}"


def _describe_category(cat_code: int) -> tuple[str, str]:
    """Return (kind, description) for a category code."""
    if cat_code == _CATEGORY_DIGIT:
        return ("char_class", "any digit (0-9)")
    elif cat_code == _CATEGORY_NOT_DIGIT:
        return ("char_class", "any non-digit")
    elif cat_code == _CATEGORY_WORD:
        return ("char_class", "any word character (letter, digit, or underscore)")
    elif cat_code == _CATEGORY_NOT_WORD:
        return ("char_class", "any non-word character")
    elif cat_code == _CATEGORY_SPACE:
        return ("char_class", "any whitespace character")
    elif cat_code == _CATEGORY_NOT_SPACE:
        return ("char_class", "any non-whitespace character")
    else:
        return ("char_class", "unknown character category")


def _describe_in_set(items: list) -> tuple[str, Any]:
    """Describe a character class [...] from its sre_parse items."""
    negate = False
    parts: list[str] = []
    raw_parts: list[dict] = []

    for item_type, item_val in items:
        if item_type == _NEGATE:
            negate = True
        elif item_type == _LITERAL:
            ch = _chr_safe(item_val)
            parts.append(f"'{ch}'")
            raw_parts.append({"type": "literal", "value": ch})
        elif item_type == _RANGE:
            lo, hi = item_val
            lo_ch = _chr_safe(lo)
            hi_ch = _chr_safe(hi)
            parts.append(f"'{lo_ch}' to '{hi_ch}'")
            raw_parts.append({"type": "range", "from": lo_ch, "to": hi_ch})
        elif item_type == _CATEGORY:
            _, cat_desc = _describe_category(item_val)
            parts.append(cat_desc)
            raw_parts.append({"type": "category", "description": cat_desc})

    if not parts:
        desc = "any character in set"
    elif negate:
        desc = "any character NOT in: " + ", ".join(parts)
    else:
        desc = "any character in: " + ", ".join(parts)

    return desc, {"negate": negate, "parts": raw_parts}


def _describe_quantifier(min_count: int, max_count: int) -> str:
    """Return a human-readable quantifier description."""
    if min_count == 0 and max_count == _MAXREPEAT:
        return "zero or more"
    elif min_count == 1 and max_count == _MAXREPEAT:
        return "one or more"
    elif min_count == 0 and max_count == 1:
        return "optionally"
    elif min_count == max_count:
        return f"exactly {min_count}"
    elif max_count == _MAXREPEAT:
        return f"{min_count} or more"
    else:
        return f"between {min_count} and {max_count}"


def _quantifier_symbol(min_count: int, max_count: int, greedy: bool) -> str:
    """Return the regex quantifier symbol."""
    suffix = "" if greedy else "?"
    if min_count == 0 and max_count == _MAXREPEAT:
        return f"*{suffix}"
    elif min_count == 1 and max_count == _MAXREPEAT:
        return f"+{suffix}"
    elif min_count == 0 and max_count == 1:
        return f"?{suffix}"
    elif min_count == max_count:
        return f"{{{min_count}}}"
    elif max_count == _MAXREPEAT:
        return f"{{{min_count},}}{suffix}"
    else:
        return f"{{{min_count},{max_count}}}{suffix}"


def _parse_items(items: list, group_names: dict | None = None) -> list[RegexComponent]:
    """Convert sre_parse items into a list of RegexComponent objects."""
    if group_names is None:
        group_names = {}

    components: list[RegexComponent] = []

    for item_type, item_val in items:
        if item_type == _LITERAL:
            ch = _chr_safe(item_val)
            components.append(RegexComponent(
                kind="literal",
                description=f"literal '{ch}'",
                value=ch,
            ))

        elif item_type == _NOT_LITERAL:
            ch = _chr_safe(item_val)
            components.append(RegexComponent(
                kind="not_literal",
                description=f"any character except '{ch}'",
                value=ch,
            ))

        elif item_type == _ANY:
            components.append(RegexComponent(
                kind="any",
                description="any character (except newline)",
                value=".",
            ))

        elif item_type == _AT:
            if item_val == _AT_BEGINNING:
                components.append(RegexComponent(kind="anchor", description="start of string", value="^"))
            elif item_val == _AT_BEGINNING_STRING:
                components.append(RegexComponent(kind="anchor", description="absolute start of string", value="\\A"))
            elif item_val == _AT_END:
                components.append(RegexComponent(kind="anchor", description="end of string", value="$"))
            elif item_val == _AT_END_STRING:
                components.append(RegexComponent(kind="anchor", description="absolute end of string", value="\\Z"))
            elif item_val == _AT_BOUNDARY:
                components.append(RegexComponent(kind="anchor", description="word boundary", value="\\b"))
            elif item_val == _AT_NON_BOUNDARY:
                components.append(RegexComponent(kind="anchor", description="non-word boundary", value="\\B"))

        elif item_type == _IN:
            desc, val = _describe_in_set(item_val)
            components.append(RegexComponent(kind="char_class", description=desc, value=val))

        elif item_type == _BRANCH:
            branches = item_val[1]
            branch_components = [_parse_items(branch, group_names) for branch in branches]
            components.append(RegexComponent(
                kind="alternation",
                description="either " + " or ".join(f"option {i + 1}" for i in range(len(branches))),
                value=len(branches),
                children=[
                    RegexComponent(kind="branch", description=f"option {i + 1}", children=bc)
                    for i, bc in enumerate(branch_components)
                ],
            ))

        elif item_type == _SUBPATTERN:
            group_id = item_val[0]
            sub_items = item_val[3]
            children = _parse_items(sub_items, group_names)

            if group_id is None:
                components.append(RegexComponent(
                    kind="group", description="non-capturing group",
                    value={"type": "non-capturing"}, children=children,
                ))
            elif group_id in group_names:
                name = group_names[group_id]
                components.append(RegexComponent(
                    kind="group", description=f"named capturing group '{name}' (group {group_id})",
                    value={"type": "named", "name": name, "id": group_id}, children=children,
                ))
            else:
                components.append(RegexComponent(
                    kind="group", description=f"capturing group {group_id}",
                    value={"type": "capturing", "id": group_id}, children=children,
                ))

        elif item_type == _GROUPREF:
            components.append(RegexComponent(
                kind="backreference", description=f"backreference to group {item_val}", value=item_val,
            ))

        elif item_type == _GROUPREF_EXISTS:
            group_id = item_val[0]
            yes_items = item_val[1]
            no_items = item_val[2] if len(item_val) > 2 and item_val[2] else []
            yes_children = _parse_items(yes_items, group_names)
            no_children = _parse_items(no_items, group_names) if no_items else []
            components.append(RegexComponent(
                kind="conditional",
                description=f"if group {group_id} matched then match first option, else match second option",
                value=group_id, children=yes_children + no_children,
            ))

        elif item_type == _ASSERT:
            direction = item_val[0]
            children = _parse_items(item_val[1], group_names)
            if direction == 1:
                components.append(RegexComponent(
                    kind="lookahead", description="followed by (lookahead)",
                    value={"direction": "ahead"}, children=children,
                ))
            else:
                components.append(RegexComponent(
                    kind="lookbehind", description="preceded by (lookbehind)",
                    value={"direction": "behind"}, children=children,
                ))

        elif item_type == _ASSERT_NOT:
            direction = item_val[0]
            children = _parse_items(item_val[1], group_names)
            if direction == 1:
                components.append(RegexComponent(
                    kind="negative_lookahead", description="not followed by (negative lookahead)",
                    value={"direction": "ahead"}, children=children,
                ))
            else:
                components.append(RegexComponent(
                    kind="negative_lookbehind", description="not preceded by (negative lookbehind)",
                    value={"direction": "behind"}, children=children,
                ))

        elif item_type in (_MAX_REPEAT, _MIN_REPEAT):
            min_count, max_count, sub_items = item_val
            greedy = item_type == _MAX_REPEAT
            children = _parse_items(sub_items, group_names)
            quant_desc = _describe_quantifier(min_count, max_count)
            quant_sym = _quantifier_symbol(min_count, max_count, greedy)
            lazy_note = "" if greedy else " (lazy)"

            if len(children) == 1:
                child = children[0]
                child.quantifier = quant_sym
                child.greedy = greedy
                child.description = f"{quant_desc}{lazy_note} {child.description}"
                components.append(child)
            else:
                components.append(RegexComponent(
                    kind="quantified_group",
                    description=f"{quant_desc}{lazy_note}",
                    quantifier=quant_sym, greedy=greedy, children=children,
                ))

    return components


def _extract_group_names(pattern: str) -> dict[int, str]:
    """Extract named group mappings from a pattern string by parsing (?P<name>...)."""
    names: dict[int, str] = {}
    group_id = 0
    i = 0
    while i < len(pattern):
        if pattern[i] == "\\" and i + 1 < len(pattern):
            i += 2
            continue
        if pattern[i] == "(":
            if i + 1 < len(pattern) and pattern[i + 1] == "?":
                if (i + 2 < len(pattern) and pattern[i + 2] == "P"
                        and i + 3 < len(pattern) and pattern[i + 3] == "<"):
                    end = pattern.index(">", i + 4)
                    name = pattern[i + 4 : end]
                    group_id += 1
                    names[group_id] = name
            else:
                group_id += 1
            i += 1
        else:
            i += 1
    return names


def parse_regex(pattern: str) -> list[RegexComponent]:
    """Parse a regex pattern string into a list of RegexComponent objects.

    Raises re.error (via sre_parse) if the pattern is invalid.
    """
    parsed = sre_parse.parse(pattern)

    group_names: dict[int, str] = {}
    if hasattr(parsed, "state"):
        state = parsed.state  # type: ignore[attr-defined]
        if hasattr(state, "groupdict"):
            for name, gid in state.groupdict.items():
                group_names[gid] = name

    if not group_names:
        group_names = _extract_group_names(pattern)

    return _parse_items(list(parsed), group_names)


def get_component_summary(components: list[RegexComponent]) -> list[str]:
    """Return a flat list of human-readable descriptions for each component."""
    result: list[str] = []
    for comp in components:
        result.append(comp.description)
        if comp.children:
            if comp.kind == "alternation":
                for branch in comp.children:
                    child_descs = get_component_summary(branch.children)
                    result.append(f"  {branch.description}: " + ", ".join(child_descs))
            else:
                child_descs = get_component_summary(comp.children)
                for cd in child_descs:
                    result.append(f"  {cd}")
    return result


# ============================================================
# Explainer -- pattern string -> plain English
# ============================================================

def _explain_component(comp: RegexComponent, depth: int = 0) -> str:
    """Generate a plain English explanation for a single component."""
    kind = comp.kind

    if kind == "literal":
        return comp.description if comp.quantifier else f"literal '{comp.value}'"

    elif kind == "not_literal":
        return comp.description

    elif kind == "any":
        return comp.description if comp.quantifier else "any character (except newline)"

    elif kind == "anchor":
        return comp.description

    elif kind == "char_class":
        return comp.description

    elif kind == "alternation":
        branch_explanations = []
        for branch in comp.children:
            parts = [_explain_component(c, depth + 1) for c in branch.children]
            branch_explanations.append(" then ".join(parts) if parts else "empty")
        return "either " + " or ".join(branch_explanations)

    elif kind == "group":
        val = comp.value or {}
        group_type = val.get("type", "capturing")
        children_text = _explain_children(comp.children, depth + 1)

        if group_type == "non-capturing":
            if comp.quantifier:
                return f"{comp.description}: {children_text}"
            return f"non-capturing group containing: {children_text}"
        elif group_type == "named":
            name = val.get("name", "?")
            gid = val.get("id", "?")
            if comp.quantifier:
                return f"{comp.description}: {children_text}"
            return f"named capturing group '{name}' (group {gid}) containing: {children_text}"
        else:
            gid = val.get("id", "?")
            if comp.quantifier:
                return f"{comp.description}: {children_text}"
            return f"capturing group {gid} containing: {children_text}"

    elif kind == "backreference":
        return f"backreference to group {comp.value} (matches same text as group {comp.value})"

    elif kind == "conditional":
        return comp.description

    elif kind == "lookahead":
        return f"followed by (lookahead): {_explain_children(comp.children, depth + 1)}"

    elif kind == "lookbehind":
        return f"preceded by (lookbehind): {_explain_children(comp.children, depth + 1)}"

    elif kind == "negative_lookahead":
        return f"not followed by (negative lookahead): {_explain_children(comp.children, depth + 1)}"

    elif kind == "negative_lookbehind":
        return f"not preceded by (negative lookbehind): {_explain_children(comp.children, depth + 1)}"

    elif kind == "quantified_group":
        return f"{comp.description} of: {_explain_children(comp.children, depth + 1)}"

    return comp.description


def _explain_children(children: list[RegexComponent], depth: int = 0) -> str:
    """Explain a list of child components joined together."""
    parts = [_explain_component(c, depth) for c in children]
    return ", then ".join(parts)


def _build_summary(components: list[RegexComponent]) -> str:
    """Build a one-line summary of the regex."""
    parts = [_summarize_component(comp) for comp in components]
    if not parts:
        return "matches empty string"
    return ", ".join(parts) + "."


def _summarize_component(comp: RegexComponent) -> str:
    """Return a brief summary phrase for a component."""
    kind = comp.kind

    if kind == "literal":
        ch = comp.value
        if comp.quantifier:
            quant_desc = comp.description.split("literal")[0].strip() if "literal" in comp.description else ""
            return f"{quant_desc} '{ch}'" if quant_desc else f"'{ch}'"
        return f"'{ch}'"

    elif kind == "not_literal":
        return comp.description

    elif kind == "any":
        return comp.description if comp.quantifier else "any character"

    elif kind == "anchor":
        val = comp.value
        if val == "^":
            return "starts at beginning of string"
        elif val == "$":
            return "ends at end of string"
        elif val == "\\b":
            return "at a word boundary"
        elif val == "\\B":
            return "not at a word boundary"
        elif val == "\\A":
            return "at absolute start of string"
        elif val == "\\Z":
            return "at absolute end of string"
        return comp.description

    elif kind == "char_class":
        return comp.description

    elif kind == "alternation":
        branch_summaries = []
        for branch in comp.children:
            parts = [_summarize_component(c) for c in branch.children]
            branch_summaries.append(" then ".join(parts) if parts else "empty")
        return "either " + " or ".join(branch_summaries)

    elif kind == "group":
        val = comp.value or {}
        group_type = val.get("type", "capturing")
        children_summary = ", ".join(_summarize_component(c) for c in comp.children)
        if group_type == "named":
            name = val.get("name", "?")
            if comp.quantifier:
                quant_desc = comp.description.split("named")[0].strip()
                return f"{quant_desc} group '{name}': ({children_summary})" if quant_desc else f"group '{name}': ({children_summary})"
            return f"captured as '{name}': ({children_summary})"
        elif group_type == "non-capturing":
            if comp.quantifier:
                quant_desc = comp.description.split("non-capturing")[0].strip()
                return f"{quant_desc} ({children_summary})" if quant_desc else f"({children_summary})"
            return f"({children_summary})"
        else:
            gid = val.get("id", "?")
            if comp.quantifier:
                quant_desc = comp.description.split("capturing")[0].strip()
                return f"{quant_desc} group {gid}: ({children_summary})" if quant_desc else f"group {gid}: ({children_summary})"
            return f"captured as group {gid}: ({children_summary})"

    elif kind == "backreference":
        return f"same text as group {comp.value}"

    elif kind == "lookahead":
        return f"followed by {', '.join(_summarize_component(c) for c in comp.children)}"

    elif kind == "lookbehind":
        return f"preceded by {', '.join(_summarize_component(c) for c in comp.children)}"

    elif kind == "negative_lookahead":
        return f"not followed by {', '.join(_summarize_component(c) for c in comp.children)}"

    elif kind == "negative_lookbehind":
        return f"not preceded by {', '.join(_summarize_component(c) for c in comp.children)}"

    elif kind == "quantified_group":
        return f"{comp.description} ({', '.join(_summarize_component(c) for c in comp.children)})"

    return comp.description


def explain_regex(pattern: str) -> str:
    """Return a plain English explanation of a regex pattern.

    Args:
        pattern: A regular expression pattern string.

    Returns:
        A multi-line plain English explanation.

    Raises:
        re.error: If the pattern is invalid.
    """
    if pattern == "":
        return "Matches the empty string (matches any position in any string)."

    components = parse_regex(pattern)
    if not components:
        return "Empty pattern: matches any position in any string."

    lines: list[str] = []
    lines.append(f"Pattern: {pattern}")
    lines.append("")
    lines.append("Explanation:")

    for i, comp in enumerate(components):
        explanation = _explain_component(comp)
        lines.append(f"  {i + 1}. {explanation}")

        if comp.kind == "alternation" and comp.children:
            for branch in comp.children:
                branch_parts = [_explain_component(c, 1) for c in branch.children]
                branch_text = ", then ".join(branch_parts) if branch_parts else "empty"
                lines.append(f"       - {branch.description}: {branch_text}")

    lines.append("")
    lines.append("Summary: " + _build_summary(components))
    return "\n".join(lines)


def explain_brief(pattern: str) -> str:
    """Return a single-line summary of a regex pattern.

    Args:
        pattern: A regular expression pattern string.

    Returns:
        A one-line plain English summary.

    Raises:
        re.error: If the pattern is invalid.
    """
    if pattern == "":
        return "Matches the empty string."

    components = parse_regex(pattern)
    if not components:
        return "Matches the empty string."

    return _build_summary(components)


# ============================================================
# Tester -- match regex against strings
# ============================================================

def check_regex(pattern: str, test_string: str, flags: int = 0) -> MatchResult:
    """Test a regex pattern against a string.

    Args:
        pattern: The regex pattern string.
        test_string: The string to test against.
        flags: Optional re module flags (e.g., re.IGNORECASE).

    Returns:
        A MatchResult with all match details.
    """
    result = MatchResult(pattern=pattern, test_string=test_string)

    try:
        compiled = re.compile(pattern, flags)
    except re.error as e:
        result.error = str(e)
        return result

    full = compiled.fullmatch(test_string)
    result.full_match = full is not None

    search = compiled.search(test_string)
    if search:
        result.partial_match = True
        result.match_text = search.group(0)
        result.match_start = search.start()
        result.match_end = search.end()
        result.groups = search.groups()
        result.named_groups = search.groupdict()

    for m in compiled.finditer(test_string):
        result.all_matches.append(m.group(0))
        result.all_match_spans.append((m.start(), m.end()))

    return result


def check_regex_multi(pattern: str, test_strings: list[str], flags: int = 0) -> list[MatchResult]:
    """Test a regex pattern against multiple strings."""
    return [check_regex(pattern, s, flags) for s in test_strings]


def format_match_result(result: MatchResult) -> str:
    """Format a MatchResult as a human-readable string."""
    lines: list[str] = []

    if result.error:
        lines.append(f"Error: {result.error}")
        return "\n".join(lines)

    lines.append(f"Pattern: {result.pattern}")
    lines.append(f'String:  "{result.test_string}"')
    lines.append("")

    if result.full_match:
        lines.append("Full match: YES (entire string matches)")
    else:
        lines.append("Full match: NO")

    if result.partial_match:
        lines.append(f"Partial match: YES")
        lines.append(f'  Matched: "{result.match_text}"')
        lines.append(f"  Position: {result.match_start} to {result.match_end}")
    else:
        lines.append("Partial match: NO")

    if result.groups:
        lines.append("")
        lines.append("Capture groups:")
        for i, g in enumerate(result.groups, 1):
            if g is not None:
                lines.append(f'  Group {i}: "{g}"')
            else:
                lines.append(f"  Group {i}: (no match)")

    if result.named_groups:
        lines.append("")
        lines.append("Named groups:")
        for name, val in result.named_groups.items():
            if val is not None:
                lines.append(f'  {name}: "{val}"')
            else:
                lines.append(f"  {name}: (no match)")

    if len(result.all_matches) > 1:
        lines.append("")
        lines.append(f"All matches ({len(result.all_matches)} found):")
        for i, (match_text, (start, end)) in enumerate(
            zip(result.all_matches, result.all_match_spans), 1
        ):
            lines.append(f'  {i}. "{match_text}" at position {start}-{end}')
    elif len(result.all_matches) == 1:
        lines.append("")
        lines.append("All matches (1 found):")
        lines.append(
            f'  1. "{result.all_matches[0]}" at position '
            f"{result.all_match_spans[0][0]}-{result.all_match_spans[0][1]}"
        )
    else:
        lines.append("")
        lines.append("All matches: none")

    return "\n".join(lines)


# ============================================================
# Debugger -- step-by-step match trace
# ============================================================

def _component_to_pattern_fragment(comp: RegexComponent) -> str:
    """Reconstruct an approximate regex fragment from a component."""
    kind = comp.kind
    quant = comp.quantifier or ""

    if kind == "literal":
        ch = comp.value
        special = r"\.^$*+?{}[]|()"
        if ch in special:
            return f"\\{ch}{quant}"
        return f"{ch}{quant}"

    elif kind == "not_literal":
        return f"[^{comp.value}]{quant}"

    elif kind == "any":
        return f".{quant}"

    elif kind == "anchor":
        return comp.value or ""

    elif kind == "char_class":
        val = comp.value
        if val is None:
            return f"[...]{quant}"
        negate = val.get("negate", False)
        parts = val.get("parts", [])
        inner = ""
        for part in parts:
            if part["type"] == "literal":
                ch = part["value"]
                inner += f"\\{ch}" if ch in r"\]-^" else ch
            elif part["type"] == "range":
                inner += f"{part['from']}-{part['to']}"
            elif part["type"] == "category":
                desc = part.get("description", "")
                if "digit" in desc and "non" not in desc:
                    inner += "\\d"
                elif "non-digit" in desc:
                    inner += "\\D"
                elif "word" in desc and "non" not in desc:
                    inner += "\\w"
                elif "non-word" in desc:
                    inner += "\\W"
                elif "whitespace" in desc and "non" not in desc:
                    inner += "\\s"
                elif "non-whitespace" in desc:
                    inner += "\\S"
        prefix = "^" if negate else ""
        return f"[{prefix}{inner}]{quant}"

    elif kind == "group":
        val = comp.value or {}
        group_type = val.get("type", "capturing")
        children_pattern = "".join(_component_to_pattern_fragment(c) for c in comp.children)
        if group_type == "non-capturing":
            return f"(?:{children_pattern}){quant}"
        elif group_type == "named":
            name = val.get("name", "?")
            return f"(?P<{name}>{children_pattern}){quant}"
        else:
            return f"({children_pattern}){quant}"

    elif kind == "alternation":
        branches = []
        for branch in comp.children:
            bp = "".join(_component_to_pattern_fragment(c) for c in branch.children)
            branches.append(bp)
        return "|".join(branches)

    elif kind == "backreference":
        return f"\\{comp.value}"

    elif kind == "lookahead":
        cp = "".join(_component_to_pattern_fragment(c) for c in comp.children)
        return f"(?={cp})"

    elif kind == "lookbehind":
        cp = "".join(_component_to_pattern_fragment(c) for c in comp.children)
        return f"(?<={cp})"

    elif kind == "negative_lookahead":
        cp = "".join(_component_to_pattern_fragment(c) for c in comp.children)
        return f"(?!{cp})"

    elif kind == "negative_lookbehind":
        cp = "".join(_component_to_pattern_fragment(c) for c in comp.children)
        return f"(?<!{cp})"

    elif kind == "quantified_group":
        cp = "".join(_component_to_pattern_fragment(c) for c in comp.children)
        return f"(?:{cp}){quant}"

    return "?"


def debug_match(pattern: str, test_string: str) -> DebugResult:
    """Produce a step-by-step debug trace of matching a pattern against a string.

    Parses the pattern into components, then builds up partial patterns from
    left to right and checks how far each one matches.

    Args:
        pattern: The regex pattern.
        test_string: The string to match against.

    Returns:
        A DebugResult with step-by-step trace.
    """
    result = DebugResult(pattern=pattern, test_string=test_string)

    try:
        components = parse_regex(pattern)
    except Exception as e:
        result.error = f"Failed to parse pattern: {e}"
        return result

    if not components:
        result.overall_match = True
        result.match_text = ""
        result.steps.append(DebugStep(
            step_number=1, component_description="empty pattern",
            component_kind="empty", pattern_fragment="",
            matched_text="", position_start=0, position_end=0,
            success=True, note="Empty pattern matches any position.",
        ))
        return result

    try:
        full_re = re.compile(pattern)
        full_match = full_re.search(test_string)
    except re.error as e:
        result.error = str(e)
        return result

    result.overall_match = full_match is not None
    result.match_text = full_match.group(0) if full_match else None

    cumulative_pattern = ""
    prev_end = full_match.start() if full_match else 0
    step_num = 0

    for comp in components:
        step_num += 1
        fragment = _component_to_pattern_fragment(comp)
        new_pattern = cumulative_pattern + fragment
        is_anchor = comp.kind == "anchor"

        try:
            partial_re = re.compile(new_pattern)
            partial_match = partial_re.search(test_string)
        except re.error:
            result.steps.append(DebugStep(
                step_number=step_num, component_description=comp.description,
                component_kind=comp.kind, pattern_fragment=fragment,
                matched_text=None, position_start=prev_end, position_end=prev_end,
                success=False, note="Could not evaluate partial pattern.",
            ))
            cumulative_pattern = new_pattern
            continue

        if partial_match:
            new_end = partial_match.end()
            if is_anchor:
                matched_text = None
                note = "Anchor assertion (does not consume characters)."
            else:
                matched_text = test_string[prev_end:new_end] if new_end > prev_end else ""
                note = ""

            result.steps.append(DebugStep(
                step_number=step_num, component_description=comp.description,
                component_kind=comp.kind, pattern_fragment=fragment,
                matched_text=matched_text, position_start=prev_end,
                position_end=new_end, success=True, note=note,
            ))
            prev_end = new_end
        else:
            result.steps.append(DebugStep(
                step_number=step_num, component_description=comp.description,
                component_kind=comp.kind, pattern_fragment=fragment,
                matched_text=None, position_start=prev_end, position_end=prev_end,
                success=False, note="No match at this point.",
            ))

        cumulative_pattern = new_pattern

    return result


def format_debug_result(result: DebugResult) -> str:
    """Format a DebugResult as a human-readable string."""
    lines: list[str] = []

    if result.error:
        lines.append(f"Error: {result.error}")
        return "\n".join(lines)

    lines.append(f"Pattern: {result.pattern}")
    lines.append(f'String:  "{result.test_string}"')
    lines.append("")

    if result.overall_match:
        lines.append(f'Overall: MATCH (matched "{result.match_text}")')
    else:
        lines.append("Overall: NO MATCH")
    lines.append("")

    lines.append("Step-by-step:")
    for step in result.steps:
        status = "OK" if step.success else "FAIL"
        lines.append(f"  Step {step.step_number}: [{status}] {step.component_description}")
        lines.append(f"    Pattern fragment: {step.pattern_fragment}")
        if step.matched_text is not None:
            if step.matched_text:
                lines.append(f'    Matched: "{step.matched_text}" (position {step.position_start}-{step.position_end})')
            else:
                lines.append(f"    Matched: (empty) at position {step.position_start}")
        if step.note:
            lines.append(f"    Note: {step.note}")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def main():
    """CLI entry point for regex explanation, testing, and debugging."""
    import argparse
    import sys

    parser_cli = argparse.ArgumentParser(
        description="Explain, test, and debug regular expressions.",
        usage="python explainer.py PATTERN [options]",
    )
    parser_cli.add_argument("pattern", help="Regex pattern to analyze")
    parser_cli.add_argument(
        "--test", "-t", dest="test_strings", nargs="+", default=[],
        help="Test strings to match against",
    )
    parser_cli.add_argument(
        "--debug", "-d", dest="debug_string", default=None,
        help="String to debug-trace against",
    )
    parser_cli.add_argument(
        "--brief", "-b", action="store_true",
        help="Show only the one-line summary",
    )

    args = parser_cli.parse_args()

    if args.brief:
        try:
            print(explain_brief(args.pattern))
        except re.error as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Always show explanation
    try:
        print(explain_regex(args.pattern))
    except re.error as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Test against strings if provided
    if args.test_strings:
        print()
        print("=" * 40)
        for s in args.test_strings:
            result = check_regex(args.pattern, s)
            print()
            print(format_match_result(result))

    # Debug trace if requested
    if args.debug_string is not None:
        print()
        print("=" * 40)
        print()
        dr = debug_match(args.pattern, args.debug_string)
        print(format_debug_result(dr))


if __name__ == "__main__":
    main()
