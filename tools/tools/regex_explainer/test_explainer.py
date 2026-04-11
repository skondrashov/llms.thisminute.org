"""
Tests for Regex Explainer & Tester.

These tests ARE the spec -- if an LLM regenerates the tool in any
language, these cases define correctness.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

_TOOL_DIR = str(Path(__file__).parent)

from explainer import (
    RegexComponent,
    MatchResult,
    DebugResult,
    parse_regex,
    get_component_summary,
    explain_regex,
    explain_brief,
    check_regex,
    check_regex_multi,
    format_match_result,
    debug_match,
    format_debug_result,
)


# ============================================================
# 1. Parsing -- structure correctness
# ============================================================

class TestParseLiterals:
    def test_single_literal(self):
        comps = parse_regex("a")
        assert len(comps) == 1
        assert comps[0].kind == "literal"
        assert comps[0].value == "a"

    def test_multiple_literals(self):
        comps = parse_regex("abc")
        assert len(comps) == 3
        assert [c.value for c in comps] == ["a", "b", "c"]

    def test_digit_literal(self):
        comps = parse_regex("5")
        assert comps[0].kind == "literal"
        assert comps[0].value == "5"

    def test_escaped_special(self):
        comps = parse_regex(r"\.")
        assert comps[0].kind == "literal"
        assert comps[0].value == "."


class TestParseAnchors:
    def test_caret(self):
        comps = parse_regex("^a")
        assert comps[0].kind == "anchor"
        assert comps[0].value == "^"

    def test_dollar(self):
        comps = parse_regex("a$")
        assert comps[-1].kind == "anchor"
        assert comps[-1].value == "$"

    def test_word_boundary(self):
        comps = parse_regex(r"\bword\b")
        assert comps[0].kind == "anchor"
        assert comps[0].value == "\\b"
        assert comps[-1].kind == "anchor"
        assert comps[-1].value == "\\b"

    def test_absolute_start(self):
        comps = parse_regex(r"\Afoo")
        assert comps[0].kind == "anchor"
        assert comps[0].value == "\\A"

    def test_absolute_end(self):
        comps = parse_regex(r"foo\Z")
        assert comps[-1].kind == "anchor"
        assert comps[-1].value == "\\Z"

    def test_non_word_boundary(self):
        comps = parse_regex(r"\B")
        assert comps[0].kind == "anchor"
        assert comps[0].value == "\\B"


class TestParseCharClasses:
    def test_simple_class(self):
        comps = parse_regex("[abc]")
        assert len(comps) == 1
        assert comps[0].kind == "char_class"

    def test_range_class(self):
        comps = parse_regex("[a-z]")
        assert comps[0].kind == "char_class"
        assert "range" in str(comps[0].value)

    def test_negated_class(self):
        comps = parse_regex("[^0-9]")
        assert comps[0].kind == "char_class"
        assert comps[0].value["negate"] is True

    def test_shorthand_digit(self):
        comps = parse_regex(r"\d")
        assert comps[0].kind == "char_class"
        assert "digit" in comps[0].description

    def test_shorthand_word(self):
        comps = parse_regex(r"\w")
        assert comps[0].kind == "char_class"
        assert "word" in comps[0].description

    def test_shorthand_space(self):
        comps = parse_regex(r"\s")
        assert comps[0].kind == "char_class"
        assert "whitespace" in comps[0].description

    def test_negated_shorthand(self):
        comps = parse_regex(r"\D")
        assert "non-digit" in comps[0].description


class TestParseQuantifiers:
    def test_star(self):
        comps = parse_regex("a*")
        assert comps[0].quantifier == "*"
        assert comps[0].greedy is True

    def test_plus(self):
        comps = parse_regex("a+")
        assert comps[0].quantifier == "+"

    def test_question_mark(self):
        comps = parse_regex("a?")
        assert comps[0].quantifier == "?"

    def test_exact_count(self):
        comps = parse_regex("a{3}")
        assert comps[0].quantifier == "{3}"

    def test_range_count(self):
        comps = parse_regex("a{2,5}")
        assert comps[0].quantifier == "{2,5}"

    def test_lazy_star(self):
        comps = parse_regex("a*?")
        assert comps[0].quantifier == "*?"
        assert comps[0].greedy is False

    def test_lazy_plus(self):
        comps = parse_regex("a+?")
        assert comps[0].quantifier == "+?"
        assert comps[0].greedy is False

    def test_dot_star(self):
        comps = parse_regex(".*")
        assert comps[0].kind == "any"
        assert comps[0].quantifier == "*"


class TestParseGroups:
    def test_capturing_group(self):
        comps = parse_regex("(abc)")
        assert comps[0].kind == "group"
        assert comps[0].value["type"] == "capturing"
        assert len(comps[0].children) == 3

    def test_non_capturing_group(self):
        # Plain (?:abc) is inlined by sre_parse; use (?i:abc) which
        # generates a SUBPATTERN with group_id=None due to the flag
        comps = parse_regex("(?i:abc)")
        assert comps[0].kind == "group"
        assert comps[0].value["type"] == "non-capturing"

    def test_named_group(self):
        comps = parse_regex(r"(?P<name>\w+)")
        assert comps[0].kind == "group"
        assert comps[0].value["type"] == "named"
        assert comps[0].value["name"] == "name"

    def test_nested_groups(self):
        comps = parse_regex("((a)(b))")
        assert comps[0].kind == "group"
        assert len(comps[0].children) == 2
        assert comps[0].children[0].kind == "group"
        assert comps[0].children[1].kind == "group"


class TestParseAlternation:
    def test_simple_alternation(self):
        comps = parse_regex("cat|dog")
        assert comps[0].kind == "alternation"
        assert len(comps[0].children) == 2

    def test_three_way_alternation(self):
        # sre_parse optimizes single-char alternations like a|b|c into [abc]
        # Use multi-char branches to get a true alternation node
        comps = parse_regex("aa|bb|cc")
        assert comps[0].kind == "alternation"
        assert len(comps[0].children) == 3


class TestParseLookaround:
    def test_positive_lookahead(self):
        comps = parse_regex("foo(?=bar)")
        assert any(c.kind == "lookahead" for c in comps)

    def test_negative_lookahead(self):
        comps = parse_regex("foo(?!bar)")
        assert any(c.kind == "negative_lookahead" for c in comps)

    def test_positive_lookbehind(self):
        comps = parse_regex("(?<=foo)bar")
        assert any(c.kind == "lookbehind" for c in comps)

    def test_negative_lookbehind(self):
        comps = parse_regex("(?<!foo)bar")
        assert any(c.kind == "negative_lookbehind" for c in comps)


class TestParseBackreference:
    def test_backreference(self):
        comps = parse_regex(r"(a)\1")
        assert comps[1].kind == "backreference"
        assert comps[1].value == 1


class TestParseDotAny:
    def test_dot(self):
        comps = parse_regex(".")
        assert comps[0].kind == "any"
        assert "any character" in comps[0].description


class TestParseInvalid:
    def test_unbalanced_paren(self):
        with pytest.raises(re.error):
            parse_regex("(abc")

    def test_bad_quantifier(self):
        with pytest.raises(re.error):
            parse_regex("*abc")

    def test_bad_escape(self):
        # \k is not a valid Python regex escape at the top level
        with pytest.raises(re.error):
            parse_regex("\\k")


class TestComponentSummary:
    def test_simple_summary(self):
        comps = parse_regex("^abc$")
        summary = get_component_summary(comps)
        assert len(summary) == 5  # ^, a, b, c, $
        assert "start" in summary[0].lower()
        assert "end" in summary[4].lower()


# ============================================================
# 2. Explanation -- human-readable output
# ============================================================

class TestExplainRegex:
    def test_empty_pattern(self):
        result = explain_regex("")
        assert "empty string" in result.lower()

    def test_literal_explanation(self):
        result = explain_regex("hello")
        assert "Pattern: hello" in result
        assert "literal" in result.lower()

    def test_anchor_explanation(self):
        result = explain_regex("^hello$")
        assert "start of string" in result.lower()
        assert "end of string" in result.lower()

    def test_quantifier_explanation(self):
        result = explain_regex("a+")
        assert "one or more" in result.lower()

    def test_char_class_explanation(self):
        result = explain_regex("[a-z]")
        assert "character" in result.lower()

    def test_group_explanation(self):
        result = explain_regex("(abc)")
        assert "capturing group" in result.lower()

    def test_alternation_explanation(self):
        result = explain_regex("cat|dog")
        assert "either" in result.lower()

    def test_lookahead_explanation(self):
        result = explain_regex("foo(?=bar)")
        assert "lookahead" in result.lower()

    def test_summary_line(self):
        result = explain_regex("^abc$")
        assert "Summary:" in result

    def test_explanation_has_pattern_header(self):
        result = explain_regex("a+b*")
        assert "Pattern: a+b*" in result


class TestExplainBrief:
    def test_empty_pattern(self):
        result = explain_brief("")
        assert "empty string" in result.lower()

    def test_simple_pattern(self):
        result = explain_brief("abc")
        assert "'" in result  # contains quoted literals

    def test_anchor_pattern(self):
        result = explain_brief("^hello$")
        assert "beginning" in result.lower() or "start" in result.lower()
        assert "end" in result.lower()

    def test_returns_single_line(self):
        result = explain_brief(r"\d{3}-\d{4}")
        assert "\n" not in result


# ============================================================
# 3. Tester -- match correctness
# ============================================================

class TestCheckRegex:
    def test_full_match(self):
        result = check_regex(r"\d{3}", "123")
        assert result.full_match is True
        assert result.partial_match is True

    def test_partial_match(self):
        result = check_regex(r"\d+", "abc123def")
        assert result.full_match is False
        assert result.partial_match is True
        assert result.match_text == "123"

    def test_no_match(self):
        result = check_regex(r"\d+", "abcdef")
        assert result.full_match is False
        assert result.partial_match is False

    def test_groups(self):
        result = check_regex(r"(\d+)-(\d+)", "abc 12-34 def")
        assert result.groups == ("12", "34")

    def test_named_groups(self):
        result = check_regex(r"(?P<year>\d{4})-(?P<month>\d{2})", "2026-03")
        assert result.named_groups["year"] == "2026"
        assert result.named_groups["month"] == "03"

    def test_all_matches(self):
        result = check_regex(r"\d+", "abc 12 def 34 ghi 56")
        assert result.all_matches == ["12", "34", "56"]
        assert len(result.all_match_spans) == 3

    def test_match_positions(self):
        result = check_regex("hello", "say hello world")
        assert result.match_start == 4
        assert result.match_end == 9

    def test_invalid_pattern(self):
        result = check_regex("(unclosed", "test")
        assert result.error is not None

    def test_flags_ignorecase(self):
        result = check_regex("hello", "HELLO WORLD", flags=re.IGNORECASE)
        assert result.partial_match is True
        assert result.match_text == "HELLO"

    def test_empty_pattern_matches(self):
        result = check_regex("", "abc")
        assert result.full_match is False  # fullmatch("", "abc") is False
        assert result.partial_match is True  # search("", "abc") matches at pos 0

    def test_full_match_entire_string(self):
        result = check_regex(r"^\d{3}-\d{4}$", "555-1234")
        assert result.full_match is True

    def test_full_match_fails_on_extra(self):
        result = check_regex(r"^\d{3}$", "1234")
        assert result.full_match is False


class TestCheckRegexMulti:
    def test_batch_test(self):
        results = check_regex_multi(r"\d+", ["abc", "123", "a1b2"])
        assert len(results) == 3
        assert results[0].partial_match is False
        assert results[1].full_match is True
        assert results[2].partial_match is True
        assert results[2].all_matches == ["1", "2"]

    def test_empty_list(self):
        results = check_regex_multi(r"\d+", [])
        assert results == []


class TestFormatMatchResult:
    def test_format_full_match(self):
        result = check_regex(r"\d+", "42")
        text = format_match_result(result)
        assert "Full match: YES" in text

    def test_format_no_match(self):
        result = check_regex(r"\d+", "abc")
        text = format_match_result(result)
        assert "Full match: NO" in text
        assert "Partial match: NO" in text

    def test_format_error(self):
        result = check_regex("(bad", "test")
        text = format_match_result(result)
        assert "Error:" in text

    def test_format_groups(self):
        result = check_regex(r"(\w+)@(\w+)", "user@host")
        text = format_match_result(result)
        assert "Capture groups:" in text
        assert 'Group 1: "user"' in text
        assert 'Group 2: "host"' in text

    def test_format_multiple_matches(self):
        result = check_regex(r"\d+", "1 22 333")
        text = format_match_result(result)
        assert "3 found" in text


# ============================================================
# 4. Tester -- real-world patterns
# ============================================================

class TestRealWorldPatterns:
    def test_email_basic(self):
        pattern = r"[\w.+-]+@[\w-]+\.[\w.-]+"
        result = check_regex(pattern, "user@example.com")
        assert result.full_match is True

    def test_ipv4_address(self):
        pattern = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
        result = check_regex(pattern, "192.168.1.1")
        assert result.full_match is True

    def test_phone_number(self):
        pattern = r"\(\d{3}\)\s?\d{3}-\d{4}"
        result = check_regex(pattern, "(555) 123-4567")
        assert result.full_match is True

    def test_date_iso(self):
        pattern = r"\d{4}-\d{2}-\d{2}"
        result = check_regex(pattern, "2026-03-16")
        assert result.full_match is True

    def test_hex_color(self):
        pattern = r"#[0-9a-fA-F]{6}"
        result = check_regex(pattern, "#FF5733")
        assert result.full_match is True


# ============================================================
# 5. Debugger -- step-by-step trace
# ============================================================

class TestDebugMatch:
    def test_successful_match(self):
        result = debug_match(r"\d+", "abc123")
        assert result.overall_match is True
        assert result.match_text == "123"
        assert len(result.steps) > 0

    def test_failed_match(self):
        result = debug_match(r"\d+", "abcdef")
        assert result.overall_match is False

    def test_empty_pattern(self):
        result = debug_match("", "test")
        assert result.overall_match is True
        assert result.steps[0].success is True

    def test_invalid_pattern(self):
        result = debug_match("(bad", "test")
        assert result.error is not None

    def test_anchor_step(self):
        result = debug_match("^abc", "abc")
        # Should have an anchor step that notes it doesn't consume chars
        anchor_steps = [s for s in result.steps if s.component_kind == "anchor"]
        assert len(anchor_steps) > 0
        assert "anchor" in anchor_steps[0].note.lower() or anchor_steps[0].note == ""

    def test_steps_have_fragments(self):
        result = debug_match("abc", "abc")
        for step in result.steps:
            assert step.pattern_fragment != ""

    def test_step_numbering(self):
        result = debug_match("abc", "abc")
        for i, step in enumerate(result.steps):
            assert step.step_number == i + 1


class TestFormatDebugResult:
    def test_format_success(self):
        result = debug_match("abc", "abc")
        text = format_debug_result(result)
        assert "MATCH" in text
        assert "Step 1:" in text

    def test_format_failure(self):
        result = debug_match(r"\d+", "abc")
        text = format_debug_result(result)
        assert "NO MATCH" in text

    def test_format_error(self):
        result = debug_match("(bad", "test")
        text = format_debug_result(result)
        assert "Error:" in text


# ============================================================
# 6. Edge cases
# ============================================================

class TestEdgeCases:
    def test_unicode_literal(self):
        comps = parse_regex("cafe\\u0301")
        # Should parse without error
        assert len(comps) > 0

    def test_newline_in_class(self):
        result = check_regex(r"[\n]", "\n")
        assert result.full_match is True

    def test_dot_does_not_match_newline(self):
        result = check_regex(".", "\n")
        assert result.partial_match is False

    def test_dot_with_dotall(self):
        result = check_regex(".", "\n", flags=re.DOTALL)
        assert result.partial_match is True

    def test_very_long_alternation(self):
        # sre_parse factors out the common "word" prefix, leaving an
        # alternation of the numeric suffixes
        pattern = "|".join(f"word{i}" for i in range(50))
        comps = parse_regex(pattern)
        alt = [c for c in comps if c.kind == "alternation"]
        assert len(alt) == 1
        assert len(alt[0].children) == 50

    def test_nested_quantifiers_via_group(self):
        # (a+)+ -- valid but often a regex performance trap
        comps = parse_regex("(a+)+")
        assert comps[0].kind == "group"
        assert comps[0].quantifier == "+"

    def test_backreference_match(self):
        result = check_regex(r"(\w+)\s+\1", "hello hello")
        assert result.full_match is True
        assert result.groups == ("hello",)

    def test_backreference_no_match(self):
        result = check_regex(r"(\w+)\s+\1", "hello world")
        assert result.full_match is False

    def test_lookahead_zero_width(self):
        result = check_regex(r"foo(?=bar)", "foobar")
        assert result.partial_match is True
        assert result.match_text == "foo"  # lookahead doesn't consume "bar"

    def test_negative_lookahead(self):
        result = check_regex(r"foo(?!bar)", "foobaz")
        assert result.partial_match is True

    def test_negative_lookahead_fails(self):
        result = check_regex(r"foo(?!bar)", "foobar")
        assert result.partial_match is False

    def test_lookbehind(self):
        result = check_regex(r"(?<=@)\w+", "user@host")
        assert result.partial_match is True
        assert result.match_text == "host"

    def test_empty_alternation_branch(self):
        result = check_regex("a|", "")
        assert result.partial_match is True  # empty branch matches empty

    def test_optional_group(self):
        result = check_regex(r"(abc)?def", "def")
        assert result.full_match is True
        assert result.groups == (None,)


# ============================================================
# 7. CLI output format
# ============================================================

class TestCLI:
    def test_basic_explain(self):
        result = subprocess.run(
            [sys.executable, "explainer.py", r"\d+"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Pattern:" in result.stdout
        assert "Explanation:" in result.stdout
        assert "Summary:" in result.stdout

    def test_brief_mode(self):
        result = subprocess.run(
            [sys.executable, "explainer.py", r"\d+", "--brief"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "digit" in result.stdout.lower()
        # Brief mode should not have multi-line explanation header
        assert "Explanation:" not in result.stdout

    def test_test_mode(self):
        result = subprocess.run(
            [sys.executable, "explainer.py", r"\d+", "--test", "abc123", "hello"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Full match:" in result.stdout

    def test_debug_mode(self):
        result = subprocess.run(
            [sys.executable, "explainer.py", r"\d+", "--debug", "abc123"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Step-by-step:" in result.stdout

    def test_invalid_pattern_cli(self):
        result = subprocess.run(
            [sys.executable, "explainer.py", "(bad"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode != 0
        assert "Error" in result.stderr or "error" in result.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
