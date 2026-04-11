"""
Tests for Shell Escape Quoter.

These tests ARE the spec -- if an LLM regenerates the quoter in any
language, these cases define correctness.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_TOOL_DIR = str(Path(__file__).parent)

from quoter import (
    SHELLS,
    AnalysisResult,
    CharFinding,
    ShellAnalysis,
    ShellDefinition,
    ShellType,
    SpecialChar,
    all_shells,
    analyze_string,
    escape,
    escape_all,
    escape_bash,
    escape_cmd,
    escape_fish,
    escape_powershell,
    escape_sh,
    escape_zsh,
    get_shell,
    shell_names,
)


# ============================================================
# 1. Shell definitions
# ============================================================


class TestShellLookup:
    def test_get_bash(self):
        sh = get_shell("bash")
        assert sh.shell_type == ShellType.BASH
        assert sh.name == "bash"

    def test_get_zsh(self):
        sh = get_shell("zsh")
        assert sh.shell_type == ShellType.ZSH

    def test_get_sh(self):
        sh = get_shell("sh")
        assert sh.shell_type == ShellType.SH

    def test_get_posix_alias(self):
        sh = get_shell("posix")
        assert sh.shell_type == ShellType.SH

    def test_get_fish(self):
        sh = get_shell("fish")
        assert sh.shell_type == ShellType.FISH

    def test_get_powershell(self):
        sh = get_shell("powershell")
        assert sh.shell_type == ShellType.POWERSHELL

    def test_get_pwsh_alias(self):
        sh = get_shell("pwsh")
        assert sh.shell_type == ShellType.POWERSHELL

    def test_get_cmd(self):
        sh = get_shell("cmd")
        assert sh.shell_type == ShellType.CMD

    def test_get_cmd_exe_alias(self):
        sh = get_shell("cmd.exe")
        assert sh.shell_type == ShellType.CMD

    def test_case_insensitive(self):
        sh = get_shell("BASH")
        assert sh.shell_type == ShellType.BASH

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown shell"):
            get_shell("fakeshell")

    def test_all_shells_returns_all(self):
        shells = all_shells()
        assert len(shells) == 6

    def test_shell_names(self):
        names = shell_names()
        assert "bash" in names
        assert "powershell" in names
        assert "cmd" in names


class TestShellDefinitions:
    def test_each_shell_has_special_chars(self):
        for shell_def in all_shells():
            assert len(shell_def.special_chars) > 0

    def test_bash_has_single_quote(self):
        sh = get_shell("bash")
        assert sh.is_special("'")

    def test_bash_has_dollar(self):
        sh = get_shell("bash")
        assert sh.is_special("$")

    def test_bash_has_backtick(self):
        sh = get_shell("bash")
        assert sh.is_special("`")

    def test_bash_has_semicolon(self):
        sh = get_shell("bash")
        assert sh.is_special(";")

    def test_bash_has_pipe(self):
        sh = get_shell("bash")
        assert sh.is_special("|")

    def test_bash_has_newline(self):
        sh = get_shell("bash")
        assert sh.is_special("\n")

    def test_bash_has_null(self):
        sh = get_shell("bash")
        assert sh.is_special("\x00")

    def test_cmd_has_percent(self):
        sh = get_shell("cmd")
        assert sh.is_special("%")

    def test_cmd_has_caret(self):
        sh = get_shell("cmd")
        assert sh.is_special("^")

    def test_cmd_no_single_quote(self):
        sh = get_shell("cmd")
        assert not sh.is_special("'")

    def test_powershell_has_backtick(self):
        sh = get_shell("powershell")
        assert sh.is_special("`")

    def test_powershell_has_at(self):
        sh = get_shell("powershell")
        assert sh.is_special("@")

    def test_fish_no_backtick(self):
        sh = get_shell("fish")
        assert not sh.is_special("`")

    def test_letter_not_special(self):
        for shell_def in all_shells():
            assert not shell_def.is_special("a")
            assert not shell_def.is_special("Z")
            assert not shell_def.is_special("5")

    def test_get_char_info_returns_special_char(self):
        sh = get_shell("bash")
        info = sh.get_char_info(";")
        assert info is not None
        assert info.name == "semicolon"
        assert info.danger_level == "high"

    def test_get_char_info_returns_none_for_safe(self):
        sh = get_shell("bash")
        assert sh.get_char_info("a") is None


# ============================================================
# 2. Escaping: safe strings pass through
# ============================================================


class TestSafeStrings:
    """Safe strings should pass through unchanged (no wrapping)."""

    SAFE_CASES = [
        "hello",
        "file.txt",
        "path/to/file",
        "some-flag",
        "key_value",
        "127.0.0.1:8080",
        "a,b,c",
        "foo+bar",
        "/usr/bin/python3",
    ]

    @pytest.mark.parametrize("s", SAFE_CASES)
    def test_bash_passthrough(self, s):
        assert escape_bash(s) == s

    @pytest.mark.parametrize("s", SAFE_CASES)
    def test_zsh_passthrough(self, s):
        assert escape_zsh(s) == s

    @pytest.mark.parametrize("s", SAFE_CASES)
    def test_sh_passthrough(self, s):
        assert escape_sh(s) == s

    @pytest.mark.parametrize("s", SAFE_CASES)
    def test_fish_passthrough(self, s):
        assert escape_fish(s) == s

    @pytest.mark.parametrize("s", SAFE_CASES)
    def test_powershell_passthrough(self, s):
        assert escape_powershell(s) == s

    @pytest.mark.parametrize("s", SAFE_CASES)
    def test_cmd_passthrough(self, s):
        assert escape_cmd(s) == s


# ============================================================
# 3. Escaping: empty string
# ============================================================


class TestEmptyString:
    def test_bash_empty(self):
        assert escape_bash("") == "''"

    def test_zsh_empty(self):
        assert escape_zsh("") == "''"

    def test_sh_empty(self):
        assert escape_sh("") == "''"

    def test_fish_empty(self):
        assert escape_fish("") == "''"

    def test_powershell_empty(self):
        assert escape_powershell("") == "''"

    def test_cmd_empty(self):
        assert escape_cmd("") == '""'


# ============================================================
# 4. Escaping: spaces
# ============================================================


class TestSpaces:
    def test_bash_space(self):
        result = escape_bash("hello world")
        assert result == "'hello world'"

    def test_sh_space(self):
        result = escape_sh("hello world")
        assert result == "'hello world'"

    def test_fish_space(self):
        result = escape_fish("hello world")
        assert result == "'hello world'"

    def test_powershell_space(self):
        result = escape_powershell("hello world")
        assert result == "'hello world'"

    def test_cmd_space(self):
        result = escape_cmd("hello world")
        assert result == '"hello world"'


# ============================================================
# 5. Escaping: single quotes
# ============================================================


class TestSingleQuotes:
    def test_bash_single_quote(self):
        result = escape_bash("it's")
        assert "$'" in result
        assert "\\'" in result

    def test_zsh_single_quote(self):
        result = escape_zsh("it's")
        assert "$'" in result

    def test_sh_single_quote(self):
        # sh uses the concatenation trick or $'...'
        result = escape_sh("it's")
        assert "'" in result  # Should handle the quote somehow

    def test_fish_single_quote(self):
        result = escape_fish("it's")
        assert "\\'" in result

    def test_powershell_single_quote(self):
        result = escape_powershell("it's")
        assert "''" in result  # doubled

    def test_cmd_single_quote_passthrough(self):
        # cmd doesn't treat single quotes as special
        result = escape_cmd("it's")
        assert "'" in result


# ============================================================
# 6. Escaping: double quotes
# ============================================================


class TestDoubleQuotes:
    def test_bash_double_quote(self):
        result = escape_bash('say "hello"')
        # In single quotes, double quotes are literal
        assert '"' in result or '\\"' in result

    def test_powershell_double_quote_in_control_context(self):
        result = escape_powershell('say "hi"\n')
        assert '`"' in result or "''" in result

    def test_cmd_double_quote(self):
        result = escape_cmd('say "hello"')
        assert '""' in result


# ============================================================
# 7. Escaping: dangerous injection strings
# ============================================================


class TestInjectionStrings:
    """Strings that would cause command injection if not escaped."""

    def test_semicolon_injection_bash(self):
        result = escape_bash("; rm -rf /")
        assert not result.startswith(";")
        assert "'" in result or "$'" in result

    def test_pipe_injection_bash(self):
        result = escape_bash("| cat /etc/passwd")
        assert not result.startswith("|")

    def test_backtick_injection_bash(self):
        result = escape_bash("`whoami`")
        # Backtick is not a control char or single quote, so it gets
        # simple single-quoted: '`whoami`' which is safe in bash
        # (single quotes are fully literal in POSIX shells)
        assert result == "'`whoami`'"

    def test_dollar_paren_injection_bash(self):
        result = escape_bash("$(rm -rf /)")
        # Wrapped in single quotes, $( is literal and safe
        assert result == "'$(rm -rf /)'"

    def test_newline_injection_bash(self):
        result = escape_bash("safe\nrm -rf /")
        assert "$'" in result  # ANSI-C quoting due to newline
        assert "\\n" in result

    def test_null_byte_bash(self):
        result = escape_bash("hello\x00world")
        assert "$'" in result
        assert "\\x00" in result

    def test_cmd_percent_injection(self):
        result = escape_cmd("%PATH%")
        assert "%%" in result

    def test_cmd_exclamation_injection(self):
        result = escape_cmd("!var!")
        assert "^!" in result

    def test_powershell_dollar_injection(self):
        result = escape_powershell("$env:PATH")
        # In single quotes, $ is literal in PowerShell
        assert result == "'$env:PATH'"

    def test_powershell_dollar_with_control(self):
        result = escape_powershell("$env\n")
        assert "`$" in result or "`n" in result


# ============================================================
# 8. Escaping: control characters
# ============================================================


class TestControlCharacters:
    def test_tab_bash(self):
        result = escape_bash("hello\tworld")
        assert "$'" in result
        assert "\\t" in result

    def test_carriage_return_bash(self):
        result = escape_bash("hello\rworld")
        assert "$'" in result
        assert "\\r" in result

    def test_bell_bash(self):
        result = escape_bash("hello\aworld")
        assert "$'" in result
        assert "\\a" in result

    def test_backspace_bash(self):
        result = escape_bash("hello\bworld")
        assert "$'" in result
        assert "\\b" in result

    def test_escape_char_bash(self):
        result = escape_bash("hello\x1bworld")
        assert "$'" in result
        assert "\\e" in result

    def test_tab_powershell(self):
        result = escape_powershell("hello\tworld")
        assert '"' in result  # double-quoted mode
        assert "`t" in result

    def test_newline_powershell(self):
        result = escape_powershell("line1\nline2")
        assert "`n" in result

    def test_null_powershell(self):
        result = escape_powershell("hello\x00")
        assert "`0" in result

    def test_tab_fish(self):
        result = escape_fish("hello\tworld")
        assert "\\x09" in result  # fish uses \xHH for control chars

    def test_newline_fish(self):
        result = escape_fish("line1\nline2")
        assert "\\x0a" in result


# ============================================================
# 9. Escaping: special characters per shell
# ============================================================


class TestSpecialCharsPerShell:
    """Each shell's special characters should be properly escaped."""

    def test_bash_glob_asterisk(self):
        result = escape_bash("*.txt")
        assert result == "'*.txt'"

    def test_bash_glob_question(self):
        result = escape_bash("file?.txt")
        assert result == "'file?.txt'"

    def test_bash_bracket(self):
        result = escape_bash("[abc].txt")
        assert "'" in result

    def test_bash_hash(self):
        result = escape_bash("# comment")
        assert "'" in result

    def test_bash_tilde(self):
        result = escape_bash("~/file")
        assert "'" in result

    def test_bash_redirect(self):
        result = escape_bash("> output.txt")
        assert "'" in result

    def test_bash_ampersand(self):
        result = escape_bash("cmd1 && cmd2")
        assert "'" in result

    def test_bash_backslash(self):
        result = escape_bash("path\\to\\file")
        # Backslash is not a control char, just put in single quotes
        assert "'" in result

    def test_fish_backslash(self):
        result = escape_fish("path\\to\\file")
        assert "\\\\" in result  # fish escapes backslash

    def test_cmd_redirect(self):
        result = escape_cmd("> output.txt")
        assert '"' in result  # wrapped in double quotes

    def test_cmd_pipe(self):
        result = escape_cmd("cmd1 | cmd2")
        assert '"' in result

    def test_cmd_ampersand(self):
        result = escape_cmd("cmd1 & cmd2")
        assert '"' in result

    def test_powershell_at_sign(self):
        result = escape_powershell("@array")
        assert "'" in result

    def test_powershell_braces(self):
        result = escape_powershell("{script}")
        assert "'" in result

    def test_zsh_equals(self):
        # = at word start is special in zsh, but escape_zsh uses same as posix
        result = escape_zsh("=ls")
        # The = is in _SAFE_CHARS, so it passes through
        assert result == "=ls"


# ============================================================
# 10. escape() dispatch function
# ============================================================


class TestEscapeDispatch:
    def test_by_string_name(self):
        result = escape("hello world", "bash")
        assert result == "'hello world'"

    def test_by_shell_type(self):
        result = escape("hello world", ShellType.BASH)
        assert result == "'hello world'"

    def test_by_shell_definition(self):
        shell_def = get_shell("bash")
        result = escape("hello world", shell_def)
        assert result == "'hello world'"

    def test_unknown_shell_string_raises(self):
        with pytest.raises(ValueError):
            escape("hello", "fakeshell")


# ============================================================
# 11. escape_all()
# ============================================================


class TestEscapeAll:
    def test_returns_all_shells(self):
        result = escape_all("hello world")
        assert "bash" in result
        assert "zsh" in result
        assert "sh" in result
        assert "fish" in result
        assert "powershell" in result
        assert "cmd" in result
        assert len(result) == 6

    def test_values_are_strings(self):
        result = escape_all("hello world")
        for v in result.values():
            assert isinstance(v, str)

    def test_safe_string_all_same(self):
        result = escape_all("hello")
        assert all(v == "hello" for v in result.values())

    def test_dangerous_string_all_different_from_input(self):
        result = escape_all("; rm -rf /")
        for v in result.values():
            # None should start with bare semicolon
            assert not v.startswith(";") or v.startswith("';")


# ============================================================
# 12. Analysis: safe strings
# ============================================================


class TestAnalysisSafe:
    def test_plain_alpha(self):
        result = analyze_string("hello")
        assert result.overall_risk == "safe"
        assert result.is_safe_everywhere is True

    def test_digits(self):
        result = analyze_string("12345")
        assert result.overall_risk == "safe"

    def test_safe_chars(self):
        result = analyze_string("file_name.txt")
        assert result.overall_risk == "safe"


# ============================================================
# 13. Analysis: dangerous strings
# ============================================================


class TestAnalysisDangerous:
    def test_semicolon_injection(self):
        result = analyze_string("; rm -rf /")
        assert result.overall_risk in ("high", "critical")

    def test_backtick_injection(self):
        result = analyze_string("`whoami`")
        assert result.overall_risk in ("high", "critical")

    def test_dollar_expansion(self):
        result = analyze_string("$HOME")
        assert result.overall_risk in ("medium", "high", "critical")

    def test_newline_injection(self):
        result = analyze_string("safe\nrm -rf /")
        assert result.overall_risk in ("high", "critical")

    def test_null_byte(self):
        result = analyze_string("hello\x00world")
        assert result.overall_risk in ("high", "critical")

    def test_pipe_injection(self):
        result = analyze_string("| cat /etc/passwd")
        assert result.overall_risk in ("high", "critical")


class TestAnalysisInjectionDetection:
    def test_semicolon_plus_quote_is_critical(self):
        result = analyze_string("'; DROP TABLE users; --")
        for sa in result.shell_analyses:
            if sa.shell_name in ("bash", "zsh", "sh", "fish"):
                assert sa.injection_possible is True

    def test_safe_string_not_injectable(self):
        result = analyze_string("hello_world")
        for sa in result.shell_analyses:
            assert sa.injection_possible is False


class TestAnalysisPerShell:
    def test_percent_only_dangerous_in_cmd(self):
        result = analyze_string("%PATH%")
        for sa in result.shell_analyses:
            if sa.shell_name == "cmd":
                assert any(f.char == "%" for f in sa.findings)
            elif sa.shell_name == "bash":
                # % is not special in bash
                assert not any(f.char == "%" for f in sa.findings)

    def test_backtick_not_special_in_fish(self):
        result = analyze_string("`cmd`")
        for sa in result.shell_analyses:
            if sa.shell_name == "fish":
                assert not any(f.char == "`" for f in sa.findings)
            elif sa.shell_name == "bash":
                assert any(f.char == "`" for f in sa.findings)

    def test_at_sign_special_in_powershell(self):
        result = analyze_string("@args")
        for sa in result.shell_analyses:
            if sa.shell_name == "powershell":
                assert any(f.char == "@" for f in sa.findings)
            elif sa.shell_name == "bash":
                assert not any(f.char == "@" for f in sa.findings)

    def test_caret_special_in_cmd(self):
        result = analyze_string("hello^world")
        for sa in result.shell_analyses:
            if sa.shell_name == "cmd":
                assert any(f.char == "^" for f in sa.findings)

    def test_exclamation_special_in_bash(self):
        result = analyze_string("hello!")
        for sa in result.shell_analyses:
            if sa.shell_name == "bash":
                assert any(f.char == "!" for f in sa.findings)


class TestAnalysisShellFilter:
    def test_analyze_single_shell(self):
        result = analyze_string("hello world", shells=["bash"])
        assert len(result.shell_analyses) == 1
        assert result.shell_analyses[0].shell_name == "bash"

    def test_analyze_two_shells(self):
        result = analyze_string("hello world", shells=["bash", "cmd"])
        assert len(result.shell_analyses) == 2

    def test_analyze_by_shell_type(self):
        result = analyze_string("hello world", shells=[ShellType.FISH])
        assert len(result.shell_analyses) == 1
        assert result.shell_analyses[0].shell_name == "fish"


# ============================================================
# 14. Analysis result properties
# ============================================================


class TestAnalysisProperties:
    def test_input_length(self):
        result = analyze_string("abc")
        assert result.input_length == 3

    def test_input_repr(self):
        result = analyze_string("hello\n")
        assert "\\n" in result.input_repr

    def test_shell_analysis_unique_chars(self):
        result = analyze_string("a;b;c")
        for sa in result.shell_analyses:
            if sa.shell_name == "bash":
                # ; appears twice, but unique count should be 1
                assert sa.unique_special_chars >= 1
                assert sa.total_special_chars >= 2

    def test_dangerous_chars_property(self):
        result = analyze_string("; `whoami`")
        for sa in result.shell_analyses:
            if sa.shell_name == "bash":
                dangerous = sa.dangerous_chars
                assert len(dangerous) > 0

    def test_has_injection_chars(self):
        result = analyze_string("'injection")
        for sa in result.shell_analyses:
            if sa.shell_name == "bash":
                assert sa.has_injection_chars is True

    def test_has_expansion_chars(self):
        result = analyze_string("$HOME")
        for sa in result.shell_analyses:
            if sa.shell_name == "bash":
                assert sa.has_expansion_chars is True


# ============================================================
# 15. Escaping: every dangerous char in every shell
# ============================================================


class TestEveryDangerousChar:
    """For every high-danger character in each shell, verify escaping wraps it."""

    @pytest.mark.parametrize("shell_name", shell_names())
    def test_high_danger_chars_escaped(self, shell_name):
        shell_def = get_shell(shell_name)
        for sc in shell_def.special_chars:
            if sc.danger_level == "high":
                char = sc.char
                test_str = f"a{char}b"
                escaped = escape(test_str, shell_name)
                # The escaped string should NOT equal the raw string
                # (it must be quoted/escaped somehow)
                assert escaped != test_str, (
                    f"Shell {shell_name}: high-danger char {sc.name!r} ({repr(char)}) "
                    f"was not escaped in {test_str!r} -> {escaped!r}"
                )


# ============================================================
# 16. Round-trip: POSIX shells (if available)
# ============================================================


class TestRoundTrip:
    """Verify that escaped strings round-trip correctly.

    We test this structurally: the escaped output, when parsed by the
    shell's rules, should yield the original string.
    """

    def test_bash_roundtrip_simple_quote(self):
        # 'hello world' in bash yields: hello world
        escaped = escape_bash("hello world")
        assert escaped == "'hello world'"

    def test_bash_roundtrip_with_single_quote(self):
        escaped = escape_bash("it's")
        # $'it\'s' in bash yields: it's
        assert escaped == "$'it\\'s'"

    def test_sh_roundtrip_with_single_quote(self):
        escaped = escape_sh("it's")
        # Should use concatenation: 'it'"'"'s'
        assert escaped == "'it'\"'\"'s'"

    def test_bash_roundtrip_with_newline(self):
        escaped = escape_bash("line1\nline2")
        assert "\\n" in escaped

    def test_powershell_roundtrip_single_quote(self):
        escaped = escape_powershell("it's")
        assert escaped == "'it''s'"

    def test_cmd_roundtrip_double_quote(self):
        escaped = escape_cmd('say "hi"')
        assert '""' in escaped


# ============================================================
# 17. Edge cases
# ============================================================


class TestEdgeCases:
    def test_only_single_quote_bash(self):
        result = escape_bash("'")
        assert "$'" in result

    def test_only_double_quote_bash(self):
        result = escape_bash('"')
        assert "'" in result

    def test_only_space_bash(self):
        result = escape_bash(" ")
        assert result == "' '"

    def test_only_newline_bash(self):
        result = escape_bash("\n")
        assert "$'" in result

    def test_only_null_bash(self):
        result = escape_bash("\x00")
        assert "$'" in result

    def test_very_long_string(self):
        long_str = "a" * 10000
        result = escape_bash(long_str)
        assert result == long_str  # safe chars pass through

    def test_mixed_quotes_bash(self):
        result = escape_bash("""it's a "test" string""")
        # Has single quote -> needs ANSI-C quoting
        assert "$'" in result

    def test_unicode_passes_through(self):
        result = escape_bash("hello")
        assert "hello" in result

    def test_multiple_control_chars(self):
        result = escape_bash("\t\n\r\x00")
        assert "$'" in result
        assert "\\t" in result
        assert "\\n" in result
        assert "\\r" in result
        assert "\\x00" in result


# ============================================================
# 18. cmd.exe specific edge cases
# ============================================================


class TestCmdSpecific:
    def test_percent_doubled(self):
        result = escape_cmd("100%")
        assert "%%" in result

    def test_exclamation_escaped(self):
        result = escape_cmd("hello!")
        assert "^!" in result

    def test_double_quote_doubled(self):
        result = escape_cmd('say "hello"')
        assert '""' in result

    def test_newline_in_cmd(self):
        result = escape_cmd("line1\nline2")
        assert "^\n" in result

    def test_combined_cmd_dangers(self):
        result = escape_cmd('echo "hello" & del %TEMP%\\*')
        assert '"' in result  # wrapped
        assert '""' in result  # internal quotes escaped
        assert "%%" in result  # percent doubled


# ============================================================
# 19. PowerShell specific edge cases
# ============================================================


class TestPowerShellSpecific:
    def test_single_quote_doubled(self):
        result = escape_powershell("it's here's")
        assert "''" in result

    def test_dollar_in_single_quotes(self):
        # In PowerShell single quotes, $ is literal
        result = escape_powershell("$variable")
        assert result == "'$variable'"

    def test_control_char_uses_double_quotes(self):
        result = escape_powershell("hello\tworld")
        assert result.startswith('"')
        assert result.endswith('"')
        assert "`t" in result

    def test_backtick_in_control_context(self):
        result = escape_powershell("`\t")
        assert "``" in result  # backtick escaped
        assert "`t" in result  # tab escaped

    def test_at_sign_quoted(self):
        result = escape_powershell("@args")
        assert result == "'@args'"


# ============================================================
# 20. Fish specific edge cases
# ============================================================


class TestFishSpecific:
    def test_single_quote_escaped(self):
        result = escape_fish("it's")
        assert "\\'" in result

    def test_backslash_escaped(self):
        result = escape_fish("path\\to")
        assert "\\\\" in result

    def test_control_char_hex_escape(self):
        result = escape_fish("hello\tworld")
        assert "\\x09" in result

    def test_mixed_control_and_quotes(self):
        result = escape_fish("it's\n")
        assert "\\'" in result
        assert "\\x0a" in result


# ============================================================
# 21. CLI output
# ============================================================


class TestCLI:
    def test_escape_all_shells(self):
        result = subprocess.run(
            [sys.executable, "quoter.py", "hello world", "--all"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "bash" in result.stdout
        assert "powershell" in result.stdout
        assert "cmd" in result.stdout

    def test_escape_single_shell(self):
        result = subprocess.run(
            [sys.executable, "quoter.py", "hello world", "--shell", "bash"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "'hello world'" in result.stdout

    def test_analyze_mode(self):
        result = subprocess.run(
            [sys.executable, "quoter.py", "; rm -rf /", "--analyze"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "risk" in result.stdout.lower()

    def test_analyze_single_shell(self):
        result = subprocess.run(
            [sys.executable, "quoter.py", "$HOME", "--analyze", "--shell", "bash"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Bash" in result.stdout


# ============================================================
# 22. Exploit examples in shell definitions
# ============================================================


class TestExploitExamples:
    """All high-danger special chars should have exploit_example."""

    def test_all_high_danger_chars_have_exploit_examples(self):
        for shell_def in all_shells():
            for sc in shell_def.special_chars:
                if sc.danger_level == "high":
                    assert sc.exploit_example, (
                        f"Shell {shell_def.name}: high-danger char {sc.name!r} "
                        f"({repr(sc.char)}) has no exploit_example"
                    )

    def test_bash_semicolon_exploit_example(self):
        sh = get_shell("bash")
        info = sh.get_char_info(";")
        assert info is not None
        assert info.exploit_example
        assert "rm" in info.exploit_example.lower() or "inject" in info.exploit_example.lower()

    def test_cmd_percent_exploit_example(self):
        sh = get_shell("cmd")
        info = sh.get_char_info("%")
        assert info is not None
        assert info.exploit_example
        assert "%" in info.exploit_example

    def test_powershell_dollar_exploit_example(self):
        sh = get_shell("powershell")
        info = sh.get_char_info("$")
        assert info is not None
        assert info.exploit_example


# ============================================================
# 23. --explain rendering in CLI
# ============================================================


class TestExplainCLI:
    def test_explain_shows_exploit_examples(self):
        result = subprocess.run(
            [sys.executable, "quoter.py", "; rm -rf /", "--analyze", "--explain"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "->" in result.stdout  # exploit examples are shown with ->

    def test_analyze_without_explain_no_exploit(self):
        result = subprocess.run(
            [sys.executable, "quoter.py", "hello world", "--analyze"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        # Should NOT show exploit examples without --explain
        assert "->" not in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
