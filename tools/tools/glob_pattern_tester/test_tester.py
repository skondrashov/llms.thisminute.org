"""
Tests for Glob Pattern Tester & Explainer.

These tests ARE the spec -- if an LLM regenerates the tool in any
language, these cases define correctness.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_TOOL_DIR = str(Path(__file__).parent)

from tester import (
    GlobFlavor,
    ComponentKind,
    ParsedGlob,
    MatchResult,
    TreeMatchResult,
    GitignoreFile,
    GitignoreResult,
    parse_glob,
    match_path,
    match_paths,
    expand_braces,
    explain_glob,
    explain_brief,
    parse_gitignore,
    check_gitignore,
)


# ============================================================
# 1. Parsing -- structure correctness
# ============================================================

class TestParseLiterals:
    def test_single_char(self):
        p = parse_glob("a")
        assert len(p.components) == 1
        assert p.components[0].kind == ComponentKind.LITERAL
        assert p.components[0].value == "a"

    def test_multiple_chars(self):
        p = parse_glob("hello")
        assert "".join(c.value for c in p.components) == "hello"

    def test_escaped_star(self):
        p = parse_glob("\\*")
        assert p.components[0].kind == ComponentKind.LITERAL
        assert p.components[0].value == "*"


class TestParseWildcards:
    def test_star(self):
        p = parse_glob("*")
        assert p.components[0].kind == ComponentKind.STAR

    def test_double_star(self):
        p = parse_glob("**")
        assert p.components[0].kind == ComponentKind.DOUBLE_STAR

    def test_question(self):
        p = parse_glob("?")
        assert p.components[0].kind == ComponentKind.QUESTION

    def test_double_star_fnmatch_is_star(self):
        p = parse_glob("**", GlobFlavor.FNMATCH)
        assert p.components[0].kind == ComponentKind.STAR


class TestParseCharClasses:
    def test_simple_class(self):
        p = parse_glob("[abc]")
        assert p.components[0].kind == ComponentKind.CHAR_CLASS
        assert p.components[0].value == ["a", "b", "c"]

    def test_negated_class(self):
        p = parse_glob("[!abc]")
        assert p.components[0].negated is True

    def test_range_class(self):
        p = parse_glob("[a-z]")
        assert p.components[0].value == [("a", "z")]

    def test_unclosed_is_literal(self):
        p = parse_glob("[abc")
        assert p.components[0].kind == ComponentKind.LITERAL


class TestParseBraces:
    def test_simple_brace(self):
        p = parse_glob("{a,b,c}")
        assert p.components[0].kind == ComponentKind.BRACE
        assert p.components[0].value == ["a", "b", "c"]

    def test_single_option_not_brace(self):
        p = parse_glob("{alone}")
        assert all(c.kind == ComponentKind.LITERAL for c in p.components)

    def test_brace_ignored_in_fnmatch(self):
        p = parse_glob("{a,b}", GlobFlavor.FNMATCH)
        assert all(c.kind == ComponentKind.LITERAL for c in p.components)


class TestParseGitignore:
    def test_negation(self):
        p = parse_glob("!*.py", GlobFlavor.GITIGNORE)
        assert p.is_negated is True

    def test_dir_only(self):
        p = parse_glob("build/", GlobFlavor.GITIGNORE)
        assert p.is_dir_only is True

    def test_anchored(self):
        p = parse_glob("src/*.py", GlobFlavor.GITIGNORE)
        assert p.is_anchored is True

    def test_unanchored(self):
        p = parse_glob("*.py", GlobFlavor.GITIGNORE)
        assert p.is_anchored is False


# ============================================================
# 2. Matching -- correctness
# ============================================================

class TestUnixStarMatch:
    def test_matches_filename(self):
        assert match_path("*.py", "main.py").matched is True

    def test_no_match(self):
        assert match_path("*.py", "main.js").matched is False

    def test_does_not_cross_slash(self):
        assert match_path("*.py", "src/main.py").matched is False

    def test_matches_empty_prefix(self):
        assert match_path("*.py", ".py").matched is True

    def test_star_in_middle(self):
        assert match_path("file*.txt", "file123.txt").matched is True

    def test_multiple_stars(self):
        assert match_path("*.*", "file.txt").matched is True

    def test_no_extension_no_match(self):
        assert match_path("*.*", "Makefile").matched is False


class TestDoubleStarMatch:
    def test_matches_directories(self):
        assert match_path("**/*.py", "src/main.py").matched is True

    def test_deep_path(self):
        assert match_path("**/*.py", "a/b/c/d/main.py").matched is True

    def test_at_root(self):
        assert match_path("**/*.py", "main.py").matched is True

    def test_at_end(self):
        assert match_path("src/**", "src/a/b/c.py").matched is True

    def test_in_middle(self):
        assert match_path("src/**/test.py", "src/pkg/test.py").matched is True

    def test_zero_dirs(self):
        assert match_path("src/**/test.py", "src/test.py").matched is True

    def test_no_match(self):
        assert match_path("src/**/*.py", "lib/main.py").matched is False


class TestQuestionMatch:
    def test_single_char(self):
        assert match_path("file?.txt", "file1.txt").matched is True

    def test_no_match_empty(self):
        assert match_path("file?.txt", "file.txt").matched is False

    def test_no_match_multi(self):
        assert match_path("file?.txt", "file12.txt").matched is False


class TestCharClassMatch:
    def test_match(self):
        assert match_path("[abc].txt", "a.txt").matched is True

    def test_no_match(self):
        assert match_path("[abc].txt", "d.txt").matched is False

    def test_range(self):
        assert match_path("[a-z].txt", "m.txt").matched is True

    def test_negated(self):
        assert match_path("[!abc].txt", "d.txt").matched is True

    def test_negated_no_match(self):
        assert match_path("[!abc].txt", "a.txt").matched is False


class TestBraceMatch:
    def test_first_option(self):
        assert match_path("*.{py,js}", "main.py").matched is True

    def test_second_option(self):
        assert match_path("*.{py,js}", "main.js").matched is True

    def test_no_match(self):
        assert match_path("*.{py,js}", "main.rs").matched is False


class TestFnmatchMatch:
    def test_star_match(self):
        assert match_path("*.py", "main.py", GlobFlavor.FNMATCH).matched is True

    def test_star_stops_at_slash(self):
        assert match_path("*.py", "src/main.py", GlobFlavor.FNMATCH).matched is False

    def test_no_brace_support(self):
        assert match_path("{a,b}.py", "a.py", GlobFlavor.FNMATCH).matched is False


class TestGitignoreMatch:
    def test_unanchored_matches_deep(self):
        assert match_path("*.py", "src/main.py", GlobFlavor.GITIGNORE).matched is True

    def test_anchored_at_root(self):
        assert match_path("src/*.py", "src/main.py", GlobFlavor.GITIGNORE).matched is True

    def test_anchored_no_deep_match(self):
        assert match_path("src/*.py", "lib/src/main.py", GlobFlavor.GITIGNORE).matched is False

    def test_dir_only_matches_dir(self):
        assert match_path("build/", "build", GlobFlavor.GITIGNORE, is_dir=True).matched is True

    def test_dir_only_ignores_file(self):
        assert match_path("build/", "build", GlobFlavor.GITIGNORE, is_dir=False).matched is False

    def test_leading_slash_anchor(self):
        assert match_path("/build", "build", GlobFlavor.GITIGNORE).matched is True

    def test_leading_slash_no_deep(self):
        assert match_path("/build", "src/build", GlobFlavor.GITIGNORE).matched is False

    def test_directory_name_anywhere(self):
        assert match_path("node_modules", "frontend/node_modules", GlobFlavor.GITIGNORE).matched is True


# ============================================================
# 3. Batch matching
# ============================================================

class TestMatchPaths:
    def test_batch(self):
        result = match_paths("*.py", ["main.py", "test.js", "lib.py"])
        assert result.matched_paths == ["main.py", "lib.py"]
        assert result.unmatched_paths == ["test.js"]

    def test_empty(self):
        result = match_paths("*.py", [])
        assert result.matched_paths == []


# ============================================================
# 4. Brace expansion
# ============================================================

class TestExpandBraces:
    def test_simple(self):
        assert sorted(expand_braces("{a,b}")) == ["a", "b"]

    def test_with_context(self):
        assert sorted(expand_braces("*.{py,js}")) == ["*.js", "*.py"]

    def test_no_braces(self):
        assert expand_braces("plain.txt") == ["plain.txt"]

    def test_multiple_groups(self):
        assert sorted(expand_braces("{a,b}.{x,y}")) == ["a.x", "a.y", "b.x", "b.y"]


# ============================================================
# 5. Explanation
# ============================================================

class TestExplainGlob:
    def test_empty(self):
        assert "nothing" in explain_glob("").lower() or "empty" in explain_glob("").lower()

    def test_star(self):
        result = explain_glob("*.py")
        assert "Pattern:" in result
        assert "Components:" in result

    def test_double_star(self):
        assert "director" in explain_glob("**/*.py").lower()

    def test_gitignore_negation(self):
        result = explain_glob("!*.py", GlobFlavor.GITIGNORE)
        assert "negate" in result.lower() or "re-include" in result.lower()


class TestExplainBrief:
    def test_empty(self):
        assert "nothing" in explain_brief("").lower() or "empty" in explain_brief("").lower()

    def test_single_line(self):
        assert "\n" not in explain_brief("src/**/*.py")

    def test_gitignore_modifiers(self):
        result = explain_brief("*.py", GlobFlavor.GITIGNORE)
        assert "anywhere" in result.lower()


# ============================================================
# 6. Gitignore file handling
# ============================================================

class TestParseGitignoreFile:
    def test_empty(self):
        gi = parse_gitignore("")
        assert len(gi.rules) == 0

    def test_comments_and_blanks(self):
        gi = parse_gitignore("# comment\n\n*.py")
        assert gi.rules[0].is_comment is True
        assert gi.rules[1].is_blank is True
        assert gi.rules[2].pattern == "*.py"

    def test_negation_rule(self):
        gi = parse_gitignore("*.log\n!important.log")
        active = [r for r in gi.rules if not r.is_blank and not r.is_comment]
        assert active[1].is_negated is True


class TestCheckGitignore:
    def test_simple_ignore(self):
        gi = parse_gitignore("*.pyc")
        assert check_gitignore(gi, "module.pyc").is_ignored is True

    def test_no_match(self):
        gi = parse_gitignore("*.pyc")
        assert check_gitignore(gi, "module.py").is_ignored is False

    def test_deep_match(self):
        gi = parse_gitignore("*.pyc")
        assert check_gitignore(gi, "src/pkg/module.pyc").is_ignored is True

    def test_negation_overrides(self):
        gi = parse_gitignore("*.log\n!important.log")
        assert check_gitignore(gi, "debug.log").is_ignored is True
        assert check_gitignore(gi, "important.log").is_ignored is False

    def test_dir_only(self):
        gi = parse_gitignore("logs/")
        assert check_gitignore(gi, "logs", is_dir=True).is_ignored is True
        assert check_gitignore(gi, "logs", is_dir=False).is_ignored is False

    def test_later_rule_wins(self):
        gi = parse_gitignore("!*.py\n*.py")
        assert check_gitignore(gi, "main.py").is_ignored is True


class TestRealWorldGitignore:
    def test_python_gitignore(self):
        content = "__pycache__/\n*.py[cod]\nvenv/\n.env"
        gi = parse_gitignore(content)
        assert check_gitignore(gi, "__pycache__", is_dir=True).is_ignored is True
        assert check_gitignore(gi, "module.pyc").is_ignored is True
        assert check_gitignore(gi, ".env").is_ignored is True
        assert check_gitignore(gi, "main.py").is_ignored is False

    def test_negation_re_include(self):
        content = "*.log\n!important.log"
        gi = parse_gitignore(content)
        assert check_gitignore(gi, "debug.log").is_ignored is True
        assert check_gitignore(gi, "important.log").is_ignored is False


# ============================================================
# 7. Edge cases
# ============================================================

class TestEdgeCases:
    def test_dot_files(self):
        assert match_path(".*", ".gitignore").matched is True

    def test_unicode_path(self):
        assert match_path("*.py", "caf\u00e9.py").matched is True

    def test_deeply_nested(self):
        assert match_path("**/test_*.py", "a/b/c/d/e/test_main.py").matched is True

    def test_case_sensitive(self):
        assert match_path("*.py", "Main.PY").matched is False

    def test_exact_match(self):
        assert match_path("Makefile", "Makefile").matched is True

    def test_path_normalization_backslash(self):
        assert match_path("src/*.py", "src\\main.py").matched is True

    def test_path_normalization_dot_slash(self):
        assert match_path("*.py", "./main.py").matched is True


# ============================================================
# 8. CLI
# ============================================================

class TestCLI:
    def test_explain(self):
        r = subprocess.run(
            [sys.executable, "tester.py", "explain", "*.py"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "Pattern:" in r.stdout
        assert "Components:" in r.stdout

    def test_explain_brief(self):
        r = subprocess.run(
            [sys.executable, "tester.py", "explain", "*.py", "--brief"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "Components:" not in r.stdout

    def test_test_command(self):
        r = subprocess.run(
            [sys.executable, "tester.py", "test", "*.py", "main.py", "test.js"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "MATCH" in r.stdout
        assert "NO MATCH" in r.stdout

    def test_parse_command(self):
        r = subprocess.run(
            [sys.executable, "tester.py", "parse", "*.{py,js}"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert r.returncode == 0
        assert "Brace expansion" in r.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
