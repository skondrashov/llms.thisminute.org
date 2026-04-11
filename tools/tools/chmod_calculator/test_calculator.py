"""
Tests for chmod Calculator.

These tests ARE the spec — if an LLM regenerates the calculator in any
language, these cases define correctness.
"""

import subprocess
import sys

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from calculator import (
    numeric_to_symbolic,
    symbolic_to_numeric,
    parse_mode,
    format_numeric,
    _looks_symbolic,
    _normalize_mode,
    _validate_mode,
    explain,
    explain_owner,
    explain_group,
    explain_others,
    get_permission_list,
    query,
    who_can,
    can_class,
    is_special_set,
    find_preset,
    get_presets,
    format_preset_table,
    COMMON_PRESETS,
    SETUID,
    SETGID,
    STICKY,
)


# ============================================================
# 1. All 4096 basic mode round-trips (000-777 octal)
# ============================================================

class TestAllBasicModeRoundTrips:
    """Verify numeric -> symbolic -> numeric is identity for all 4096 modes."""

    @pytest.mark.parametrize("mode", range(0o000, 0o1000))
    def test_round_trip(self, mode):
        symbolic = numeric_to_symbolic(mode)
        assert len(symbolic) == 9
        recovered = symbolic_to_numeric(symbolic)
        assert recovered == mode, (
            f"Round-trip failed: {oct(mode)} -> '{symbolic}' -> {oct(recovered)}"
        )


# ============================================================
# 2. Specific numeric -> symbolic conversions
# ============================================================

class TestNumericToSymbolic:
    def test_000(self):
        assert numeric_to_symbolic(0o000) == "---------"

    def test_644(self):
        assert numeric_to_symbolic(0o644) == "rw-r--r--"

    def test_755(self):
        assert numeric_to_symbolic(0o755) == "rwxr-xr-x"

    def test_777(self):
        assert numeric_to_symbolic(0o777) == "rwxrwxrwx"

    def test_700(self):
        assert numeric_to_symbolic(0o700) == "rwx------"

    def test_400(self):
        assert numeric_to_symbolic(0o400) == "r--------"

    def test_111(self):
        assert numeric_to_symbolic(0o111) == "--x--x--x"

    def test_222(self):
        assert numeric_to_symbolic(0o222) == "-w--w--w-"

    def test_444(self):
        assert numeric_to_symbolic(0o444) == "r--r--r--"

    def test_600(self):
        assert numeric_to_symbolic(0o600) == "rw-------"

    def test_750(self):
        assert numeric_to_symbolic(0o750) == "rwxr-x---"

    def test_664(self):
        assert numeric_to_symbolic(0o664) == "rw-rw-r--"

    def test_string_input(self):
        assert numeric_to_symbolic("755") == "rwxr-xr-x"

    def test_string_with_leading_zero(self):
        assert numeric_to_symbolic("0755") == "rwxr-xr-x"


# ============================================================
# 3. Symbolic -> numeric conversions
# ============================================================

class TestSymbolicToNumeric:
    def test_all_perms(self):
        assert symbolic_to_numeric("rwxrwxrwx") == 0o777

    def test_no_perms(self):
        assert symbolic_to_numeric("---------") == 0o000

    def test_standard_file(self):
        assert symbolic_to_numeric("rw-r--r--") == 0o644

    def test_executable(self):
        assert symbolic_to_numeric("rwxr-xr-x") == 0o755

    def test_owner_only(self):
        assert symbolic_to_numeric("rwx------") == 0o700

    def test_read_only(self):
        assert symbolic_to_numeric("r--r--r--") == 0o444

    def test_whitespace_stripped(self):
        assert symbolic_to_numeric("  rwxr-xr-x  ") == 0o755

    def test_invalid_length(self):
        with pytest.raises(ValueError, match="9 characters"):
            symbolic_to_numeric("rwx")

    def test_invalid_read_char(self):
        with pytest.raises(ValueError, match="read"):
            symbolic_to_numeric("xwxr-xr-x")

    def test_invalid_write_char(self):
        with pytest.raises(ValueError, match="write"):
            symbolic_to_numeric("rrxr-xr-x")

    def test_invalid_exec_char(self):
        with pytest.raises(ValueError, match="execute"):
            symbolic_to_numeric("rwrr-xr-x")


# ============================================================
# 4. Special bits (setuid, setgid, sticky)
# ============================================================

class TestSpecialBits:
    def test_setuid_with_exec(self):
        # 4755 -> rwsr-xr-x
        sym = numeric_to_symbolic(0o4755)
        assert sym == "rwsr-xr-x"
        assert symbolic_to_numeric(sym) == 0o4755

    def test_setuid_without_exec(self):
        # 4644 -> rwSr--r--
        sym = numeric_to_symbolic(0o4644)
        assert sym == "rwSr--r--"
        assert symbolic_to_numeric(sym) == 0o4644

    def test_setgid_with_exec(self):
        # 2755 -> rwxr-sr-x
        sym = numeric_to_symbolic(0o2755)
        assert sym == "rwxr-sr-x"
        assert symbolic_to_numeric(sym) == 0o2755

    def test_setgid_without_exec(self):
        # 2644 -> rw-r-Sr--
        sym = numeric_to_symbolic(0o2644)
        assert sym == "rw-r-Sr--"
        assert symbolic_to_numeric(sym) == 0o2644

    def test_sticky_with_exec(self):
        # 1755 -> rwxr-xr-t
        sym = numeric_to_symbolic(0o1755)
        assert sym == "rwxr-xr-t"
        assert symbolic_to_numeric(sym) == 0o1755

    def test_sticky_without_exec(self):
        # 1644 -> rw-r--r-T
        sym = numeric_to_symbolic(0o1644)
        assert sym == "rw-r--r-T"
        assert symbolic_to_numeric(sym) == 0o1644

    def test_sticky_full_access(self):
        # 1777 -> rwxrwxrwt
        sym = numeric_to_symbolic(0o1777)
        assert sym == "rwxrwxrwt"
        assert symbolic_to_numeric(sym) == 0o1777

    def test_all_specials(self):
        # 7777 -> rwsrwsrwt
        sym = numeric_to_symbolic(0o7777)
        assert sym == "rwsrwsrwt"
        assert symbolic_to_numeric(sym) == 0o7777

    def test_all_specials_no_exec(self):
        # 7666 -> rwSrwSrwT
        sym = numeric_to_symbolic(0o7666)
        assert sym == "rwSrwSrwT"
        assert symbolic_to_numeric(sym) == 0o7666

    def test_setuid_only(self):
        # 4000 -> ---S------
        sym = numeric_to_symbolic(0o4000)
        assert sym == "--S------"
        assert symbolic_to_numeric(sym) == 0o4000

    def test_setgid_only(self):
        # 2000 -> owner(---) + group(--S) + other(---) = "-----S---"
        sym = numeric_to_symbolic(0o2000)
        assert sym == "-----S---"
        assert symbolic_to_numeric(sym) == 0o2000

    def test_sticky_only(self):
        # 1000 -> owner(---) + group(---) + other(--T) = "--------T"
        sym = numeric_to_symbolic(0o1000)
        assert sym == "--------T"
        assert symbolic_to_numeric(sym) == 0o1000

    def test_setuid_4711(self):
        sym = numeric_to_symbolic(0o4711)
        assert sym == "rws--x--x"
        assert symbolic_to_numeric(sym) == 0o4711


class TestSpecialBitRoundTrips:
    """All special bit combinations round-trip correctly."""

    @pytest.mark.parametrize("special", [0o1000, 0o2000, 0o4000,
                                          0o3000, 0o5000, 0o6000, 0o7000])
    @pytest.mark.parametrize("base", [0o000, 0o644, 0o755, 0o777, 0o711])
    def test_special_round_trip(self, special, base):
        mode = special | base
        symbolic = numeric_to_symbolic(mode)
        recovered = symbolic_to_numeric(symbolic)
        assert recovered == mode


# ============================================================
# 5. parse_mode — accepts both formats
# ============================================================

class TestParseMode:
    def test_numeric_string(self):
        assert parse_mode("755") == 0o755

    def test_numeric_with_leading_zero(self):
        assert parse_mode("0755") == 0o755

    def test_numeric_with_0o_prefix(self):
        assert parse_mode("0o755") == 0o755

    def test_symbolic_string(self):
        assert parse_mode("rwxr-xr-x") == 0o755

    def test_symbolic_with_specials(self):
        assert parse_mode("rwsr-xr-x") == 0o4755

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_mode("abc")

    def test_invalid_octal_digit(self):
        with pytest.raises(ValueError):
            parse_mode("899")


# ============================================================
# 6. format_numeric
# ============================================================

class TestFormatNumeric:
    def test_basic_mode(self):
        assert format_numeric(0o755) == "755"

    def test_zero_padded(self):
        assert format_numeric(0o007) == "007"

    def test_special_bits(self):
        assert format_numeric(0o4755) == "4755"

    def test_zero_mode(self):
        assert format_numeric(0o000) == "000"

    def test_sticky(self):
        assert format_numeric(0o1777) == "1777"


# ============================================================
# 7. Explainer — plain English output
# ============================================================

class TestExplainer:
    def test_explain_755(self):
        result = explain(0o755)
        assert "755" in result
        assert "rwxr-xr-x" in result
        assert "read, write, and execute" in result
        assert "read and execute" in result

    def test_explain_644(self):
        result = explain(0o644)
        assert "644" in result
        assert "rw-r--r--" in result
        assert "read and write" in result
        assert "read" in result

    def test_explain_000(self):
        result = explain(0o000)
        assert "no permissions" in result

    def test_explain_777(self):
        result = explain(0o777)
        assert "read, write, and execute" in result

    def test_explain_setuid(self):
        result = explain(0o4755)
        assert "setuid" in result.lower()

    def test_explain_setgid(self):
        result = explain(0o2755)
        assert "setgid" in result.lower()

    def test_explain_sticky(self):
        result = explain(0o1777)
        assert "sticky" in result.lower()

    def test_explain_from_string(self):
        result = explain("755")
        assert "755" in result

    def test_explain_from_symbolic(self):
        result = explain("rwxr-xr-x")
        assert "755" in result

    def test_explain_owner_755(self):
        assert explain_owner(0o755) == "read, write, and execute"

    def test_explain_group_755(self):
        assert explain_group(0o755) == "read and execute"

    def test_explain_others_755(self):
        assert explain_others(0o755) == "read and execute"

    def test_explain_owner_000(self):
        assert explain_owner(0o000) == "no permissions"

    def test_get_permission_list(self):
        assert get_permission_list(7) == ["read", "write", "execute"]
        assert get_permission_list(6) == ["read", "write"]
        assert get_permission_list(5) == ["read", "execute"]
        assert get_permission_list(4) == ["read"]
        assert get_permission_list(0) == []


# ============================================================
# 8. Permission description exhaustive check
# ============================================================

class TestPermissionDescriptions:
    """All 8 permission triplet values produce correct descriptions."""

    def test_000_no_permissions(self):
        assert explain_owner(0o000) == "no permissions"

    def test_100_execute(self):
        assert explain_owner(0o100) == "execute"

    def test_200_write(self):
        assert explain_owner(0o200) == "write"

    def test_300_write_execute(self):
        assert explain_owner(0o300) == "write and execute"

    def test_400_read(self):
        assert explain_owner(0o400) == "read"

    def test_500_read_execute(self):
        assert explain_owner(0o500) == "read and execute"

    def test_600_read_write(self):
        assert explain_owner(0o600) == "read and write"

    def test_700_read_write_execute(self):
        assert explain_owner(0o700) == "read, write, and execute"


# ============================================================
# 9. Query — natural language questions
# ============================================================

class TestQueryWhoCanRead:
    def test_755_who_can_read(self):
        result = query(0o755, "who can read?")
        assert "Owner" in result
        assert "group" in result
        assert "others" in result

    def test_700_who_can_read(self):
        result = query(0o700, "who can read?")
        assert "Owner" in result
        assert "group" not in result.lower() or "cannot" in result.lower()

    def test_000_who_can_read(self):
        result = query(0o000, "who can read?")
        assert "No one" in result


class TestQueryWhoCanWrite:
    def test_755_who_can_write(self):
        result = query(0o755, "who can write?")
        assert "Owner" in result
        # group and others cannot write in 755
        assert "group" not in result.lower().split("can write")[0] or len(result.split("can write")) == 1

    def test_777_who_can_write(self):
        result = query(0o777, "who can write?")
        assert "Owner" in result
        assert "group" in result
        assert "others" in result


class TestQueryWhoCanExecute:
    def test_755_who_can_execute(self):
        result = query(0o755, "who can execute?")
        assert "Owner" in result
        assert "group" in result
        assert "others" in result

    def test_644_who_can_execute(self):
        result = query(0o644, "who can execute?")
        assert "No one" in result


class TestQueryCanClass:
    def test_can_owner_read_755(self):
        result = query(0o755, "can owner read?")
        assert "Yes" in result

    def test_can_owner_write_755(self):
        result = query(0o755, "can owner write?")
        assert "Yes" in result

    def test_can_group_write_755(self):
        result = query(0o755, "can group write?")
        assert "No" in result

    def test_can_others_execute_644(self):
        result = query(0o644, "can others execute?")
        assert "No" in result

    def test_can_others_read_644(self):
        result = query(0o644, "can others read?")
        assert "Yes" in result

    def test_can_other_read(self):
        # "other" (singular) should also work
        result = query(0o644, "can other read?")
        assert "Yes" in result


class TestQuerySpecialBits:
    def test_is_setuid_set(self):
        result = query(0o4755, "is setuid set?")
        assert "Yes" in result

    def test_is_setuid_not_set(self):
        result = query(0o755, "is setuid set?")
        assert "No" in result

    def test_is_setgid_set(self):
        result = query(0o2755, "is setgid set?")
        assert "Yes" in result

    def test_is_sticky_set(self):
        result = query(0o1777, "is sticky set?")
        assert "Yes" in result

    def test_is_sticky_not_set(self):
        result = query(0o777, "is sticky set?")
        assert "No" in result

    def test_is_suid_alias(self):
        result = query(0o4755, "is suid set?")
        assert "Yes" in result

    def test_is_sgid_alias(self):
        result = query(0o2755, "is sgid set?")
        assert "Yes" in result

    def test_query_from_string_mode(self):
        result = query("755", "who can read?")
        assert "Owner" in result

    def test_query_from_symbolic_mode(self):
        result = query("rwxr-xr-x", "who can read?")
        assert "Owner" in result


class TestQueryUnrecognized:
    def test_unknown_question(self):
        result = query(0o755, "what color is it?")
        assert "didn't understand" in result.lower() or "try" in result.lower()


# ============================================================
# 10. Programmatic query functions
# ============================================================

class TestWhoCanFunction:
    def test_who_can_read_755(self):
        assert who_can(0o755, "read") == ["owner", "group", "others"]

    def test_who_can_write_755(self):
        assert who_can(0o755, "write") == ["owner"]

    def test_who_can_execute_644(self):
        assert who_can(0o644, "execute") == []

    def test_who_can_read_000(self):
        assert who_can(0o000, "read") == []

    def test_invalid_permission(self):
        with pytest.raises(ValueError):
            who_can(0o755, "delete")


class TestCanClassFunction:
    def test_owner_can_read_755(self):
        assert can_class(0o755, "owner", "read") is True

    def test_group_cannot_write_755(self):
        assert can_class(0o755, "group", "write") is False

    def test_others_can_read_644(self):
        assert can_class(0o644, "others", "read") is True

    def test_others_cannot_execute_644(self):
        assert can_class(0o644, "others", "execute") is False

    def test_invalid_class(self):
        with pytest.raises(ValueError):
            can_class(0o755, "nobody", "read")

    def test_invalid_permission(self):
        with pytest.raises(ValueError):
            can_class(0o755, "owner", "delete")

    def test_exec_alias(self):
        assert can_class(0o755, "owner", "exec") is True


class TestIsSpecialSet:
    def test_setuid_set(self):
        assert is_special_set(0o4755, "setuid") is True

    def test_setuid_not_set(self):
        assert is_special_set(0o755, "setuid") is False

    def test_setgid_set(self):
        assert is_special_set(0o2755, "setgid") is True

    def test_sticky_set(self):
        assert is_special_set(0o1777, "sticky") is True

    def test_suid_alias(self):
        assert is_special_set(0o4755, "suid") is True

    def test_sgid_alias(self):
        assert is_special_set(0o2755, "sgid") is True

    def test_invalid_special(self):
        with pytest.raises(ValueError):
            is_special_set(0o755, "unknown")


# ============================================================
# 11. Common presets
# ============================================================

class TestPresets:
    def test_presets_exist(self):
        presets = get_presets()
        assert len(presets) >= 14

    def test_find_755(self):
        preset = find_preset(0o755)
        assert preset is not None
        assert preset.name == "Standard executable"
        assert preset.numeric == "755"
        assert preset.symbolic == "rwxr-xr-x"

    def test_find_644(self):
        preset = find_preset(0o644)
        assert preset is not None
        assert preset.name == "Standard file"

    def test_find_777(self):
        preset = find_preset(0o777)
        assert preset is not None
        assert "full" in preset.name.lower() or "Full" in preset.name

    def test_find_nonexistent(self):
        assert find_preset(0o123) is None

    def test_find_1777(self):
        preset = find_preset(0o1777)
        assert preset is not None
        assert "sticky" in preset.name.lower()

    def test_find_4755(self):
        preset = find_preset(0o4755)
        assert preset is not None
        assert "setuid" in preset.name.lower()

    def test_preset_table(self):
        table = format_preset_table()
        assert "Mode" in table
        assert "755" in table
        assert "644" in table
        assert "rwxr-xr-x" in table

    def test_all_presets_have_valid_modes(self):
        for preset in COMMON_PRESETS:
            assert 0 <= preset.mode <= 0o7777
            # numeric and symbolic should round-trip
            sym = numeric_to_symbolic(preset.mode)
            assert symbolic_to_numeric(sym) == preset.mode

    def test_all_presets_have_descriptions(self):
        for preset in COMMON_PRESETS:
            assert preset.name
            assert preset.description
            assert preset.use_case


# ============================================================
# 12. Edge cases and validation
# ============================================================

class TestEdgeCases:
    def test_mode_0o0000(self):
        assert numeric_to_symbolic(0o0000) == "---------"

    def test_mode_0o7777(self):
        sym = numeric_to_symbolic(0o7777)
        assert sym == "rwsrwsrwt"

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            numeric_to_symbolic(0o10000)

    def test_negative_mode_raises(self):
        with pytest.raises(ValueError):
            numeric_to_symbolic(-1)

    def test_normalize_int(self):
        assert _normalize_mode(0o755) == 0o755

    def test_normalize_string_octal(self):
        assert _normalize_mode("755") == 0o755

    def test_normalize_string_0o(self):
        assert _normalize_mode("0o755") == 0o755

    def test_normalize_invalid_string(self):
        with pytest.raises(ValueError):
            _normalize_mode("abc")

    def test_normalize_non_octal_digit(self):
        with pytest.raises(ValueError):
            _normalize_mode("899")

    def test_looks_symbolic_valid(self):
        assert _looks_symbolic("rwxr-xr-x") is True

    def test_looks_symbolic_too_short(self):
        assert _looks_symbolic("rwx") is False

    def test_looks_symbolic_invalid_chars(self):
        assert _looks_symbolic("rwxr-xr-9") is False

    def test_looks_symbolic_with_specials(self):
        assert _looks_symbolic("rwsr-sr-t") is True


# ============================================================
# 13. CLI output
# ============================================================

class TestCLI:
    def test_convert_numeric(self):
        result = subprocess.run(
            [sys.executable, "calculator.py", "convert", "755"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "755" in result.stdout
        assert "rwxr-xr-x" in result.stdout

    def test_convert_symbolic(self):
        result = subprocess.run(
            [sys.executable, "calculator.py", "convert", "rwxr-xr-x"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "755" in result.stdout

    def test_explain(self):
        result = subprocess.run(
            [sys.executable, "calculator.py", "explain", "755"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Owner" in result.stdout
        assert "Group" in result.stdout

    def test_query(self):
        result = subprocess.run(
            [sys.executable, "calculator.py", "query", "755", "who can read?"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "Owner" in result.stdout

    def test_common(self):
        result = subprocess.run(
            [sys.executable, "calculator.py", "common"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "755" in result.stdout
        assert "644" in result.stdout

    def test_invalid_mode(self):
        result = subprocess.run(
            [sys.executable, "calculator.py", "convert", "abc"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode != 0

    def test_no_command(self):
        result = subprocess.run(
            [sys.executable, "calculator.py"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0  # prints help


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
