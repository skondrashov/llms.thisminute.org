"""
Tests for DateTime Format Translator.

These tests ARE the spec — if an LLM regenerates the translator in any
language, these cases define correctness.
"""

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from translator import (
    convert,
    get_unsupported_tokens,
    resolve_system,
    resolve_system_name,
    CanonicalToken,
    SYSTEMS,
)


# ============================================================================
# 1. All 7 system conversions: ISO date YYYY-MM-DD
# ============================================================================


class TestISODate:
    EQUIVALENTS = {
        "python": "%Y-%m-%d",
        "javascript": "yyyy-MM-dd",
        "go": "2006-01-02",
        "java": "yyyy-MM-dd",
        "csharp": "yyyy-MM-dd",
        "ruby": "%Y-%m-%d",
        "momentjs": "YYYY-MM-DD",
    }

    @pytest.mark.parametrize("from_sys", list(EQUIVALENTS.keys()))
    @pytest.mark.parametrize("to_sys", list(EQUIVALENTS.keys()))
    def test_iso_date(self, from_sys, to_sys):
        result = convert(self.EQUIVALENTS[from_sys], from_sys, to_sys)
        assert result == self.EQUIVALENTS[to_sys], \
            f"{from_sys}->{to_sys}: got {result!r}, expected {self.EQUIVALENTS[to_sys]!r}"


# ============================================================================
# 2. All 7 system conversions: ISO datetime YYYY-MM-DD HH:MM:SS
# ============================================================================


class TestISODateTime:
    EQUIVALENTS = {
        "python": "%Y-%m-%d %H:%M:%S",
        "javascript": "yyyy-MM-dd HH:mm:ss",
        "go": "2006-01-02 15:04:05",
        "java": "yyyy-MM-dd HH:mm:ss",
        "csharp": "yyyy-MM-dd HH:mm:ss",
        "ruby": "%Y-%m-%d %H:%M:%S",
        "momentjs": "YYYY-MM-DD HH:mm:ss",
    }

    @pytest.mark.parametrize("from_sys", list(EQUIVALENTS.keys()))
    @pytest.mark.parametrize("to_sys", list(EQUIVALENTS.keys()))
    def test_iso_datetime(self, from_sys, to_sys):
        result = convert(self.EQUIVALENTS[from_sys], from_sys, to_sys)
        assert result == self.EQUIVALENTS[to_sys]


# ============================================================================
# 3. All 7 system conversions: US date MM/DD/YYYY
# ============================================================================


class TestUSDate:
    EQUIVALENTS = {
        "python": "%m/%d/%Y",
        "javascript": "MM/dd/yyyy",
        "go": "01/02/2006",
        "java": "MM/dd/yyyy",
        "csharp": "MM/dd/yyyy",
        "ruby": "%m/%d/%Y",
        "momentjs": "MM/DD/YYYY",
    }

    @pytest.mark.parametrize("from_sys", list(EQUIVALENTS.keys()))
    @pytest.mark.parametrize("to_sys", list(EQUIVALENTS.keys()))
    def test_us_date(self, from_sys, to_sys):
        result = convert(self.EQUIVALENTS[from_sys], from_sys, to_sys)
        assert result == self.EQUIVALENTS[to_sys]


# ============================================================================
# 4. All 7 system conversions: European date DD/MM/YYYY
# ============================================================================


class TestEUDate:
    EQUIVALENTS = {
        "python": "%d/%m/%Y",
        "javascript": "dd/MM/yyyy",
        "go": "02/01/2006",
        "java": "dd/MM/yyyy",
        "csharp": "dd/MM/yyyy",
        "ruby": "%d/%m/%Y",
        "momentjs": "DD/MM/YYYY",
    }

    @pytest.mark.parametrize("from_sys", list(EQUIVALENTS.keys()))
    @pytest.mark.parametrize("to_sys", list(EQUIVALENTS.keys()))
    def test_eu_date(self, from_sys, to_sys):
        result = convert(self.EQUIVALENTS[from_sys], from_sys, to_sys)
        assert result == self.EQUIVALENTS[to_sys]


# ============================================================================
# 5. All 7 system conversions: Full month date "January 15, 2024"
# ============================================================================


class TestFullMonthDate:
    EQUIVALENTS = {
        "python": "%B %d, %Y",
        "javascript": "MMMM dd, yyyy",
        "go": "January 02, 2006",
        "java": "MMMM dd, yyyy",
        "csharp": "MMMM dd, yyyy",
        "ruby": "%B %d, %Y",
        "momentjs": "MMMM DD, YYYY",
    }

    @pytest.mark.parametrize("from_sys", list(EQUIVALENTS.keys()))
    @pytest.mark.parametrize("to_sys", list(EQUIVALENTS.keys()))
    def test_full_month(self, from_sys, to_sys):
        result = convert(self.EQUIVALENTS[from_sys], from_sys, to_sys)
        assert result == self.EQUIVALENTS[to_sys]


# ============================================================================
# 6. All 7 system conversions: abbreviated date "Mon Jan 15"
# ============================================================================


class TestAbbrDate:
    EQUIVALENTS = {
        "python": "%a %b %d",
        "javascript": "EEE MMM dd",
        "go": "Mon Jan 02",
        "java": "EEE MMM dd",
        "csharp": "ddd MMM dd",
        "ruby": "%a %b %d",
        "momentjs": "ddd MMM DD",
    }

    @pytest.mark.parametrize("from_sys", list(EQUIVALENTS.keys()))
    @pytest.mark.parametrize("to_sys", list(EQUIVALENTS.keys()))
    def test_abbr_date(self, from_sys, to_sys):
        result = convert(self.EQUIVALENTS[from_sys], from_sys, to_sys)
        assert result == self.EQUIVALENTS[to_sys]


# ============================================================================
# 7. All 7 system conversions: 12-hour time HH:MM AM/PM
# ============================================================================


class TestTime12Hour:
    EQUIVALENTS = {
        "python": "%I:%M %p",
        "go": "03:04 PM",
        "java": "hh:mm a",
        "csharp": "hh:mm tt",
        "ruby": "%I:%M %p",
        "momentjs": "hh:mm A",
    }

    @pytest.mark.parametrize("from_sys", list(EQUIVALENTS.keys()))
    @pytest.mark.parametrize("to_sys", list(EQUIVALENTS.keys()))
    def test_12hour_time(self, from_sys, to_sys):
        result = convert(self.EQUIVALENTS[from_sys], from_sys, to_sys)
        assert result == self.EQUIVALENTS[to_sys]


# ============================================================================
# 8. Round-trips: A -> B -> A preserves semantic tokens
# ============================================================================


class TestRoundTripPythonGo:
    @pytest.mark.parametrize("py_fmt,go_fmt", [
        ("%Y-%m-%d", "2006-01-02"),
        ("%Y-%m-%d %H:%M:%S", "2006-01-02 15:04:05"),
        ("%m/%d/%Y", "01/02/2006"),
        ("%I:%M %p", "03:04 PM"),
        ("%B %d, %Y", "January 02, 2006"),
    ])
    def test_python_to_go_and_back(self, py_fmt, go_fmt):
        assert convert(py_fmt, "python", "go") == go_fmt
        assert convert(go_fmt, "go", "python") == py_fmt


class TestRoundTripPythonJava:
    @pytest.mark.parametrize("py_fmt,java_fmt", [
        ("%Y-%m-%d", "yyyy-MM-dd"),
        ("%Y-%m-%d %H:%M:%S", "yyyy-MM-dd HH:mm:ss"),
        ("%m/%d/%Y", "MM/dd/yyyy"),
        ("%B %d, %Y", "MMMM dd, yyyy"),
    ])
    def test_python_to_java_and_back(self, py_fmt, java_fmt):
        assert convert(py_fmt, "python", "java") == java_fmt
        assert convert(java_fmt, "java", "python") == py_fmt


class TestRoundTripPythonMoment:
    @pytest.mark.parametrize("py_fmt,moment_fmt", [
        ("%Y-%m-%d", "YYYY-MM-DD"),
        ("%Y-%m-%d %H:%M:%S", "YYYY-MM-DD HH:mm:ss"),
        ("%m/%d/%Y", "MM/DD/YYYY"),
        ("%B %d, %Y", "MMMM DD, YYYY"),
        ("%I:%M %p", "hh:mm A"),
    ])
    def test_python_to_moment_and_back(self, py_fmt, moment_fmt):
        assert convert(py_fmt, "python", "momentjs") == moment_fmt
        assert convert(moment_fmt, "momentjs", "python") == py_fmt


class TestRoundTripGoJava:
    @pytest.mark.parametrize("go_fmt,java_fmt", [
        ("2006-01-02", "yyyy-MM-dd"),
        ("2006-01-02 15:04:05", "yyyy-MM-dd HH:mm:ss"),
        ("01/02/2006", "MM/dd/yyyy"),
        ("January 02, 2006", "MMMM dd, yyyy"),
    ])
    def test_go_to_java_and_back(self, go_fmt, java_fmt):
        assert convert(go_fmt, "go", "java") == java_fmt
        assert convert(java_fmt, "java", "go") == go_fmt


class TestRoundTripPythonRuby:
    @pytest.mark.parametrize("fmt", [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%a %b %d %Y",
        "%I:%M %p",
    ])
    def test_python_ruby_identity(self, fmt):
        assert convert(fmt, "python", "ruby") == fmt
        assert convert(fmt, "ruby", "python") == fmt


class TestRoundTripJavaCSharp:
    @pytest.mark.parametrize("java_fmt,csharp_fmt", [
        ("yyyy-MM-dd", "yyyy-MM-dd"),
        ("yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd HH:mm:ss"),
        ("MM/dd/yyyy", "MM/dd/yyyy"),
    ])
    def test_java_to_csharp_and_back(self, java_fmt, csharp_fmt):
        assert convert(java_fmt, "java", "csharp") == csharp_fmt
        assert convert(csharp_fmt, "csharp", "java") == java_fmt


class TestRoundTripMomentCSharp:
    @pytest.mark.parametrize("moment_fmt,csharp_fmt", [
        ("YYYY-MM-DD", "yyyy-MM-dd"),
        ("YYYY-MM-DD HH:mm:ss", "yyyy-MM-dd HH:mm:ss"),
        ("MM/DD/YYYY", "MM/dd/yyyy"),
        ("DD/MM/YYYY", "dd/MM/yyyy"),
    ])
    def test_moment_to_csharp_and_back(self, moment_fmt, csharp_fmt):
        assert convert(moment_fmt, "momentjs", "csharp") == csharp_fmt
        assert convert(csharp_fmt, "csharp", "momentjs") == moment_fmt


# ============================================================================
# 9. Go reference-time handling
# ============================================================================


class TestGoReferenceTime:
    def test_go_full_reference_to_python(self):
        result = convert("2006-01-02 15:04:05", "go", "python")
        assert result == "%Y-%m-%d %H:%M:%S"

    def test_go_12h_to_python(self):
        result = convert("03:04:05 PM", "go", "python")
        assert result == "%I:%M:%S %p"

    def test_python_to_go_with_ampm(self):
        result = convert("%I:%M:%S %p", "python", "go")
        assert result == "03:04:05 PM"

    def test_go_tz_name(self):
        result = convert("MST", "go", "python")
        assert result == "%Z"

    def test_go_tz_offset(self):
        result = convert("-0700", "go", "python")
        assert result == "%z"

    def test_go_tz_offset_colon(self):
        result = convert("-07:00", "go", "python")
        assert result == "%z"

    def test_go_millisecond(self):
        result = convert(".000", "go", "java")
        assert result == "SSS"

    def test_go_microsecond(self):
        result = convert(".000000", "go", "python")
        assert result == "%f"

    def test_go_parse_iso(self):
        system = resolve_system("go")
        result = system["parse"]("2006-01-02")
        assert len(result) == 5
        assert result[0] == ("2006", CanonicalToken.YEAR_4DIGIT)
        assert result[2] == ("01", CanonicalToken.MONTH_ZERO_PAD)
        assert result[4] == ("02", CanonicalToken.DAY_ZERO_PAD)

    def test_go_parse_full_reference(self):
        system = resolve_system("go")
        result = system["parse"]("Mon Jan 2 15:04:05 MST 2006")
        tokens = [r[1] for r in result if r[1] is not None]
        assert CanonicalToken.WEEKDAY_ABBR in tokens
        assert CanonicalToken.MONTH_ABBR in tokens
        assert CanonicalToken.DAY_NO_PAD in tokens
        assert CanonicalToken.HOUR_24_ZERO_PAD in tokens
        assert CanonicalToken.MINUTE_ZERO_PAD in tokens
        assert CanonicalToken.SECOND_ZERO_PAD in tokens
        assert CanonicalToken.TZ_NAME in tokens
        assert CanonicalToken.YEAR_4DIGIT in tokens


# ============================================================================
# 10. Fractional seconds across systems
# ============================================================================


class TestFractionalSeconds:
    @pytest.mark.parametrize("from_sys,fmt,to_sys,expected", [
        ("go", ".000", "java", "SSS"),
        ("go", ".000", "csharp", "fff"),
        ("go", ".000000", "python", "%f"),
        ("java", "SSS", "go", ".000"),
        ("java", "SSS", "csharp", "fff"),
        ("csharp", "fff", "java", "SSS"),
        ("csharp", "fff", "go", ".000"),
        ("python", "%f", "java", "SSSSSS"),
        ("python", "%f", "csharp", "ffffff"),
        ("python", "%f", "go", ".000000"),
        ("momentjs", "SSS", "java", "SSS"),
        ("momentjs", "SSS", "go", ".000"),
    ])
    def test_fractional_seconds(self, from_sys, fmt, to_sys, expected):
        assert convert(fmt, from_sys, to_sys) == expected


# ============================================================================
# 11. Weekday and AM/PM variations
# ============================================================================


class TestWeekdayVariations:
    @pytest.mark.parametrize("from_sys,fmt,to_sys,expected", [
        ("python", "%a", "java", "EEE"),
        ("python", "%a", "go", "Mon"),
        ("python", "%a", "momentjs", "ddd"),
        ("python", "%a", "csharp", "ddd"),
        ("python", "%A", "java", "EEEE"),
        ("python", "%A", "go", "Monday"),
        ("python", "%A", "momentjs", "dddd"),
        ("python", "%A", "csharp", "dddd"),
    ])
    def test_weekday(self, from_sys, fmt, to_sys, expected):
        assert convert(fmt, from_sys, to_sys) == expected


class TestAMPM:
    @pytest.mark.parametrize("from_sys,fmt,to_sys,expected", [
        ("python", "%p", "java", "a"),
        ("python", "%p", "go", "PM"),
        ("python", "%p", "momentjs", "A"),
        ("python", "%p", "csharp", "tt"),
        ("java", "a", "python", "%p"),
        ("go", "PM", "python", "%p"),
        ("momentjs", "A", "python", "%p"),
        ("csharp", "tt", "python", "%p"),
    ])
    def test_ampm(self, from_sys, fmt, to_sys, expected):
        assert convert(fmt, from_sys, to_sys) == expected


# ============================================================================
# 12. System aliases
# ============================================================================


class TestSystemAliases:
    def test_py_alias(self):
        assert convert("%Y", "py", "java") == "yyyy"

    def test_js_alias(self):
        assert convert("yyyy", "js", "python") == "%Y"

    def test_golang_alias(self):
        assert convert("2006", "golang", "python") == "%Y"

    def test_moment_alias(self):
        assert convert("YYYY", "moment", "python") == "%Y"

    def test_csharp_hash_alias(self):
        assert convert("yyyy", "c#", "python") == "%Y"

    def test_dotnet_alias(self):
        assert convert("yyyy", "dotnet", "python") == "%Y"

    def test_rb_alias(self):
        assert convert("%Y", "rb", "python") == "%Y"

    def test_strftime_alias(self):
        assert convert("%Y", "strftime", "java") == "yyyy"


# ============================================================================
# 13. Error handling
# ============================================================================


class TestErrorHandling:
    def test_unknown_from_system(self):
        with pytest.raises(ValueError, match="Unknown system"):
            convert("%Y", "unknown", "python")

    def test_unknown_to_system(self):
        with pytest.raises(ValueError, match="Unknown system"):
            convert("%Y", "python", "unknown")

    def test_empty_format_string(self):
        result = convert("", "python", "java")
        assert result == ""


# ============================================================================
# 14. Unsupported token detection
# ============================================================================


class TestUnsupportedTokens:
    def test_no_unsupported_for_basic_date(self):
        unsupported = get_unsupported_tokens("%Y-%m-%d", "python", "java")
        assert len(unsupported) == 0

    def test_unix_timestamp_unsupported_in_java(self):
        unsupported = get_unsupported_tokens("%s", "python", "java")
        assert len(unsupported) == 1
        assert unsupported[0][1] == CanonicalToken.UNIX_TIMESTAMP


# ============================================================================
# 15. Complex format strings
# ============================================================================


class TestComplexFormats:
    def test_python_to_java_datetime_with_tz(self):
        result = convert("%Y-%m-%d %H:%M:%S %Z", "python", "java")
        assert result == "yyyy-MM-dd HH:mm:ss z"

    def test_java_to_momentjs_full(self):
        result = convert("yyyy-MM-dd HH:mm:ss", "java", "momentjs")
        assert result == "YYYY-MM-DD HH:mm:ss"

    def test_csharp_to_python_full(self):
        result = convert("yyyy-MM-dd HH:mm:ss", "csharp", "python")
        assert result == "%Y-%m-%d %H:%M:%S"

    def test_momentjs_to_go_full(self):
        result = convert("YYYY-MM-DD HH:mm:ss", "momentjs", "go")
        assert result == "2006-01-02 15:04:05"

    def test_ruby_to_javascript_full(self):
        result = convert("%Y-%m-%d %H:%M:%S", "ruby", "javascript")
        assert result == "yyyy-MM-dd HH:mm:ss"


# ============================================================================
# 16. System interface verification
# ============================================================================


class TestAllSystemsInterface:
    @pytest.mark.parametrize("system_name", list(SYSTEMS.keys()))
    def test_has_required_keys(self, system_name):
        system = SYSTEMS[system_name]
        assert "SYSTEM_NAME" in system
        assert "TOKEN_TO_CANONICAL" in system
        assert "CANONICAL_TO_TOKEN" in system
        assert "parse" in system
        assert "render" in system
        assert callable(system["parse"])
        assert callable(system["render"])

    @pytest.mark.parametrize("system_name", list(SYSTEMS.keys()))
    def test_all_tokens_map_to_canonical(self, system_name):
        system = SYSTEMS[system_name]
        for token, canonical in system["TOKEN_TO_CANONICAL"].items():
            assert isinstance(canonical, CanonicalToken), \
                f"{system_name}: {token} maps to {canonical}, not a CanonicalToken"

    @pytest.mark.parametrize("system_name", list(SYSTEMS.keys()))
    def test_canonical_to_token_values_are_strings(self, system_name):
        system = SYSTEMS[system_name]
        for canonical, token in system["CANONICAL_TO_TOKEN"].items():
            assert isinstance(token, str), \
                f"{system_name}: {canonical} maps to {token}, not a string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
