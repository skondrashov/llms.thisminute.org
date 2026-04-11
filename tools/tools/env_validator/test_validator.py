"""
Tests for Environment File Validator.

These tests ARE the spec — if an LLM regenerates the validator in any
language, these cases define correctness.
"""

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from validator import (
    # Parser
    parse_env,
    EnvEntry,
    ParseResult,
    resolve_interpolation,
    # Template
    parse_template,
    TemplateEntry,
    TemplateResult,
    # Validator
    validate,
    validate_entry,
    Severity,
    ValidationIssue,
    ValidationResult,
    # Differ
    diff_envs,
    DiffEntry,
    DiffResult,
    # Generator
    infer_type,
    generate_template,
)


# ============================================================
# 1. .env Parsing — basic key=value
# ============================================================

class TestParseBasic:
    def test_simple_key_value(self):
        result = parse_env("FOO=bar")
        assert "FOO" in result.entries
        assert result.entries["FOO"].value == "bar"

    def test_multiple_entries(self):
        result = parse_env("FOO=bar\nBAZ=qux")
        assert len(result.entries) == 2
        assert result.entries["FOO"].value == "bar"
        assert result.entries["BAZ"].value == "qux"

    def test_empty_value(self):
        result = parse_env("FOO=")
        assert result.entries["FOO"].value == ""

    def test_value_with_equals(self):
        result = parse_env("FOO=bar=baz")
        assert result.entries["FOO"].value == "bar=baz"

    def test_whitespace_around_key(self):
        result = parse_env("  FOO  =bar")
        assert "FOO" in result.entries
        assert result.entries["FOO"].value == "bar"

    def test_whitespace_around_value(self):
        result = parse_env("FOO=  bar  ")
        assert result.entries["FOO"].value == "bar"

    def test_line_numbers(self):
        result = parse_env("\nFOO=bar\n\nBAZ=qux")
        assert result.entries["FOO"].line_number == 2
        assert result.entries["BAZ"].line_number == 4

    def test_numeric_value(self):
        result = parse_env("PORT=3000")
        assert result.entries["PORT"].value == "3000"

    def test_url_value(self):
        result = parse_env("URL=https://example.com")
        assert result.entries["URL"].value == "https://example.com"

    def test_underscore_key(self):
        result = parse_env("MY_VAR=value")
        assert "MY_VAR" in result.entries

    def test_key_starting_with_underscore(self):
        result = parse_env("_PRIVATE=secret")
        assert "_PRIVATE" in result.entries


# ============================================================
# 2. .env Parsing — quotes
# ============================================================

class TestParseQuotes:
    def test_double_quoted_value(self):
        result = parse_env('FOO="hello world"')
        assert result.entries["FOO"].value == "hello world"
        assert result.entries["FOO"].quote_style == "double"

    def test_single_quoted_value(self):
        result = parse_env("FOO='hello world'")
        assert result.entries["FOO"].value == "hello world"
        assert result.entries["FOO"].quote_style == "single"

    def test_backtick_quoted_value(self):
        result = parse_env("FOO=`hello world`")
        assert result.entries["FOO"].value == "hello world"
        assert result.entries["FOO"].quote_style == "backtick"

    def test_empty_double_quoted(self):
        result = parse_env('FOO=""')
        assert result.entries["FOO"].value == ""
        assert result.entries["FOO"].quote_style == "double"

    def test_empty_single_quoted(self):
        result = parse_env("FOO=''")
        assert result.entries["FOO"].value == ""
        assert result.entries["FOO"].quote_style == "single"

    def test_double_quoted_with_spaces(self):
        result = parse_env('FOO="  spaced  "')
        assert result.entries["FOO"].value == "  spaced  "

    def test_single_quoted_preserves_literal(self):
        result = parse_env("FOO='$NOT_INTERPOLATED'")
        assert result.entries["FOO"].value == "$NOT_INTERPOLATED"
        assert result.entries["FOO"].has_interpolation is False

    def test_unquoted_no_quote_style(self):
        result = parse_env("FOO=bar")
        assert result.entries["FOO"].quote_style is None


# ============================================================
# 3. .env Parsing — escape sequences in double quotes
# ============================================================

class TestParseEscapes:
    def test_escaped_newline(self):
        result = parse_env(r'FOO="hello\nworld"')
        assert result.entries["FOO"].value == "hello\nworld"

    def test_escaped_tab(self):
        result = parse_env(r'FOO="hello\tworld"')
        assert result.entries["FOO"].value == "hello\tworld"

    def test_escaped_carriage_return(self):
        result = parse_env(r'FOO="hello\rworld"')
        assert result.entries["FOO"].value == "hello\rworld"

    def test_escaped_double_quote(self):
        result = parse_env(r'FOO="say \"hello\""')
        assert result.entries["FOO"].value == 'say "hello"'

    def test_escaped_backslash(self):
        result = parse_env(r'FOO="path\\to\\file"')
        assert result.entries["FOO"].value == "path\\to\\file"

    def test_escaped_dollar(self):
        result = parse_env(r'FOO="cost \$5"')
        assert result.entries["FOO"].value == "cost $5"

    def test_single_quote_no_escapes(self):
        result = parse_env(r"FOO='hello\nworld'")
        assert result.entries["FOO"].value == r"hello\nworld"


# ============================================================
# 4. .env Parsing — multiline values
# ============================================================

class TestParseMultiline:
    def test_double_quoted_multiline(self):
        content = 'FOO="line1\nline2\nline3"'
        result = parse_env(content)
        assert "FOO" in result.entries
        # The \n is an escape in double quotes, processed to real newline
        assert "\n" in result.entries["FOO"].value or "line1" in result.entries["FOO"].value

    def test_single_quoted_multiline(self):
        content = "FOO='line1\nline2\nline3'"
        result = parse_env(content)
        assert "FOO" in result.entries


# ============================================================
# 5. .env Parsing — comments
# ============================================================

class TestParseComments:
    def test_full_line_comment(self):
        result = parse_env("# This is a comment\nFOO=bar")
        assert len(result.comments) == 1
        assert result.comments[0][1] == "This is a comment"
        assert "FOO" in result.entries

    def test_inline_comment(self):
        result = parse_env("FOO=bar # inline comment")
        assert result.entries["FOO"].value == "bar"

    def test_hash_in_double_quotes(self):
        result = parse_env('FOO="value # not a comment"')
        assert result.entries["FOO"].value == "value # not a comment"

    def test_hash_in_single_quotes(self):
        result = parse_env("FOO='value # not a comment'")
        assert result.entries["FOO"].value == "value # not a comment"

    def test_multiple_comments(self):
        content = "# First\n# Second\nFOO=bar"
        result = parse_env(content)
        assert len(result.comments) == 2

    def test_blank_lines_ignored(self):
        content = "\n\n\nFOO=bar\n\n"
        result = parse_env(content)
        assert len(result.entries) == 1
        assert "FOO" in result.entries


# ============================================================
# 6. .env Parsing — export prefix
# ============================================================

class TestParseExport:
    def test_export_prefix(self):
        result = parse_env("export FOO=bar")
        assert "FOO" in result.entries
        assert result.entries["FOO"].value == "bar"
        assert result.entries["FOO"].is_exported is True

    def test_export_with_tab(self):
        result = parse_env("export\tFOO=bar")
        assert "FOO" in result.entries
        assert result.entries["FOO"].is_exported is True

    def test_no_export(self):
        result = parse_env("FOO=bar")
        assert result.entries["FOO"].is_exported is False

    def test_export_with_quotes(self):
        result = parse_env('export FOO="bar"')
        assert result.entries["FOO"].value == "bar"
        assert result.entries["FOO"].is_exported is True


# ============================================================
# 7. .env Parsing — interpolation
# ============================================================

class TestParseInterpolation:
    def test_simple_interpolation(self):
        result = parse_env("FOO=$BAR")
        assert result.entries["FOO"].has_interpolation is True

    def test_braced_interpolation(self):
        result = parse_env("FOO=${BAR}")
        assert result.entries["FOO"].has_interpolation is True

    def test_no_interpolation(self):
        result = parse_env("FOO=plain_value")
        assert result.entries["FOO"].has_interpolation is False

    def test_single_quote_no_interpolation(self):
        result = parse_env("FOO='$BAR'")
        assert result.entries["FOO"].has_interpolation is False

    def test_resolve_simple(self):
        resolved = resolve_interpolation("$HOST:$PORT", {"HOST": "localhost", "PORT": "3000"})
        assert resolved == "localhost:3000"

    def test_resolve_braced(self):
        resolved = resolve_interpolation("${HOST}:${PORT}", {"HOST": "localhost", "PORT": "3000"})
        assert resolved == "localhost:3000"

    def test_resolve_unresolved_left_as_is(self):
        resolved = resolve_interpolation("$MISSING", {})
        assert resolved == "$MISSING"

    def test_resolve_mixed(self):
        resolved = resolve_interpolation("${HOST}:$PORT/path", {"HOST": "db.example.com", "PORT": "5432"})
        assert resolved == "db.example.com:5432/path"


# ============================================================
# 8. .env Parsing — BOM and Windows line endings
# ============================================================

class TestParseBOM:
    def test_bom_stripped(self):
        content = "\ufeffFOO=bar"
        result = parse_env(content)
        assert "FOO" in result.entries

    def test_windows_line_endings(self):
        content = "FOO=bar\r\nBAZ=qux\r\n"
        result = parse_env(content)
        assert result.entries["FOO"].value == "bar"
        assert result.entries["BAZ"].value == "qux"


# ============================================================
# 9. .env Parsing — error cases
# ============================================================

class TestParseErrors:
    def test_no_equals(self):
        result = parse_env("INVALID_LINE")
        assert len(result.errors) == 1
        assert "No '='" in result.errors[0]

    def test_empty_key(self):
        result = parse_env("=value")
        assert len(result.errors) == 1
        assert "Empty key" in result.errors[0]

    def test_invalid_key_name(self):
        result = parse_env("123BAD=value")
        assert len(result.errors) == 1
        assert "Invalid key" in result.errors[0]

    def test_key_with_spaces(self):
        result = parse_env("BAD KEY=value")
        assert len(result.errors) == 1

    def test_empty_content(self):
        result = parse_env("")
        assert len(result.entries) == 0
        assert len(result.errors) == 0

    def test_only_comments(self):
        result = parse_env("# comment\n# another")
        assert len(result.entries) == 0
        assert len(result.errors) == 0


# ============================================================
# 10. Template parsing — types
# ============================================================

class TestTemplateTypes:
    def test_string_type(self):
        result = parse_template("NAME=string")
        assert result.entries["NAME"].var_type == "string"

    def test_int_type(self):
        result = parse_template("COUNT=int")
        assert result.entries["COUNT"].var_type == "int"

    def test_float_type(self):
        result = parse_template("RATE=float")
        assert result.entries["RATE"].var_type == "float"

    def test_bool_type(self):
        result = parse_template("DEBUG=bool")
        assert result.entries["DEBUG"].var_type == "bool"

    def test_url_type(self):
        result = parse_template("API_URL=url")
        assert result.entries["API_URL"].var_type == "url"

    def test_email_type(self):
        result = parse_template("ADMIN_EMAIL=email")
        assert result.entries["ADMIN_EMAIL"].var_type == "email"

    def test_port_type(self):
        result = parse_template("PORT=port")
        assert result.entries["PORT"].var_type == "port"

    def test_path_type(self):
        result = parse_template("DATA_DIR=path")
        assert result.entries["DATA_DIR"].var_type == "path"

    def test_enum_type(self):
        result = parse_template("LOG_LEVEL=enum(debug,info,warn,error)")
        entry = result.entries["LOG_LEVEL"]
        assert entry.var_type == "enum"
        assert entry.enum_values == ["debug", "info", "warn", "error"]

    def test_empty_type_defaults_to_string(self):
        result = parse_template("NAME=")
        assert result.entries["NAME"].var_type == "string"

    def test_unknown_type_error(self):
        result = parse_template("FOO=foobar")
        assert len(result.errors) == 1
        assert "Unknown type" in result.errors[0]


# ============================================================
# 11. Template parsing — required/optional
# ============================================================

class TestTemplateRequired:
    def test_required_by_default(self):
        result = parse_template("NAME=string")
        assert result.entries["NAME"].required is True

    def test_optional_marker(self):
        result = parse_template("NAME=?string")
        assert result.entries["NAME"].required is False

    def test_optional_with_default(self):
        result = parse_template("LOG_LEVEL=?string:info")
        entry = result.entries["LOG_LEVEL"]
        assert entry.required is False
        assert entry.default == "info"

    def test_required_with_default(self):
        result = parse_template("PORT=int:3000")
        entry = result.entries["PORT"]
        assert entry.required is True
        assert entry.default == "3000"

    def test_optional_enum_with_default(self):
        result = parse_template("LEVEL=?enum(debug,info,warn,error):info")
        entry = result.entries["LEVEL"]
        assert entry.required is False
        assert entry.var_type == "enum"
        assert entry.enum_values == ["debug", "info", "warn", "error"]
        assert entry.default == "info"


# ============================================================
# 12. Template parsing — descriptions from comments
# ============================================================

class TestTemplateDescriptions:
    def test_preceding_comment_as_description(self):
        content = "# The database URL\nDATABASE_URL=url"
        result = parse_template(content)
        assert result.entries["DATABASE_URL"].description == "The database URL"

    def test_blank_line_resets_description(self):
        content = "# Orphan comment\n\nDATABASE_URL=url"
        result = parse_template(content)
        assert result.entries["DATABASE_URL"].description is None

    def test_no_description(self):
        result = parse_template("FOO=string")
        assert result.entries["FOO"].description is None


# ============================================================
# 13. Template parsing — edge cases
# ============================================================

class TestTemplateEdgeCases:
    def test_export_prefix(self):
        result = parse_template("export FOO=string")
        assert "FOO" in result.entries

    def test_multiple_entries(self):
        content = "FOO=string\nBAR=int\nBAZ=bool"
        result = parse_template(content)
        assert len(result.entries) == 3

    def test_line_numbers(self):
        content = "# comment\nFOO=string\n\nBAR=int"
        result = parse_template(content)
        assert result.entries["FOO"].line_number == 2
        assert result.entries["BAR"].line_number == 4


# ============================================================
# 14. Validation — all types
# ============================================================

class TestValidateInt:
    def test_valid_int(self):
        env = parse_env("COUNT=42")
        tmpl = parse_template("COUNT=int")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_negative_int(self):
        env = parse_env("COUNT=-1")
        tmpl = parse_template("COUNT=int")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_invalid_int(self):
        env = parse_env("COUNT=abc")
        tmpl = parse_template("COUNT=int")
        result = validate(env, tmpl)
        assert not result.is_valid
        assert any("int" in i.message for i in result.errors)

    def test_float_not_valid_int(self):
        env = parse_env("COUNT=3.14")
        tmpl = parse_template("COUNT=int")
        result = validate(env, tmpl)
        assert not result.is_valid


class TestValidateFloat:
    def test_valid_float(self):
        env = parse_env("RATE=3.14")
        tmpl = parse_template("RATE=float")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_integer_is_valid_float(self):
        env = parse_env("RATE=42")
        tmpl = parse_template("RATE=float")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_scientific_notation(self):
        env = parse_env("RATE=1e10")
        tmpl = parse_template("RATE=float")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_invalid_float(self):
        env = parse_env("RATE=abc")
        tmpl = parse_template("RATE=float")
        result = validate(env, tmpl)
        assert not result.is_valid


class TestValidateBool:
    @pytest.mark.parametrize("value", ["true", "false", "yes", "no", "1", "0", "on", "off"])
    def test_valid_bool(self, value):
        env = parse_env(f"DEBUG={value}")
        tmpl = parse_template("DEBUG=bool")
        result = validate(env, tmpl)
        assert result.is_valid

    @pytest.mark.parametrize("value", ["TRUE", "FALSE", "Yes", "No", "ON", "OFF"])
    def test_case_insensitive_bool(self, value):
        env = parse_env(f"DEBUG={value}")
        tmpl = parse_template("DEBUG=bool")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_invalid_bool(self):
        env = parse_env("DEBUG=maybe")
        tmpl = parse_template("DEBUG=bool")
        result = validate(env, tmpl)
        assert not result.is_valid
        assert any("bool" in i.message for i in result.errors)


class TestValidateUrl:
    def test_valid_http_url(self):
        env = parse_env("API=https://example.com/api")
        tmpl = parse_template("API=url")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_valid_http_url_without_s(self):
        env = parse_env("API=http://example.com")
        tmpl = parse_template("API=url")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_invalid_url_no_scheme(self):
        env = parse_env("API=example.com")
        tmpl = parse_template("API=url")
        result = validate(env, tmpl)
        assert not result.is_valid

    def test_valid_url_ftp(self):
        """Any scheme is accepted — postgres://, redis://, ftp://, etc."""
        env = parse_env("API=ftp://example.com")
        tmpl = parse_template("API=url")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_valid_url_postgres(self):
        env = parse_env("DB=postgres://user:pass@localhost:5432/mydb")
        tmpl = parse_template("DB=url")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_valid_url_redis(self):
        env = parse_env("CACHE=redis://localhost:6379")
        tmpl = parse_template("CACHE=url")
        result = validate(env, tmpl)
        assert result.is_valid


class TestValidateEmail:
    def test_valid_email(self):
        env = parse_env("ADMIN=user@example.com")
        tmpl = parse_template("ADMIN=email")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_invalid_email_no_at(self):
        env = parse_env("ADMIN=userexample.com")
        tmpl = parse_template("ADMIN=email")
        result = validate(env, tmpl)
        assert not result.is_valid

    def test_invalid_email_no_domain(self):
        env = parse_env("ADMIN=user@")
        tmpl = parse_template("ADMIN=email")
        result = validate(env, tmpl)
        assert not result.is_valid


class TestValidatePort:
    def test_valid_port(self):
        env = parse_env("PORT=3000")
        tmpl = parse_template("PORT=port")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_min_port(self):
        env = parse_env("PORT=1")
        tmpl = parse_template("PORT=port")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_max_port(self):
        env = parse_env("PORT=65535")
        tmpl = parse_template("PORT=port")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_port_zero_invalid(self):
        env = parse_env("PORT=0")
        tmpl = parse_template("PORT=port")
        result = validate(env, tmpl)
        assert not result.is_valid

    def test_port_too_high(self):
        env = parse_env("PORT=65536")
        tmpl = parse_template("PORT=port")
        result = validate(env, tmpl)
        assert not result.is_valid

    def test_port_not_number(self):
        env = parse_env("PORT=abc")
        tmpl = parse_template("PORT=port")
        result = validate(env, tmpl)
        assert not result.is_valid

    def test_negative_port(self):
        env = parse_env("PORT=-1")
        tmpl = parse_template("PORT=port")
        result = validate(env, tmpl)
        assert not result.is_valid


class TestValidatePath:
    def test_valid_path_no_check(self):
        env = parse_env("DATA=/some/path")
        tmpl = parse_template("DATA=path")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_empty_path_not_valid(self):
        # A required path that is empty
        env = parse_env("DATA=")
        tmpl = parse_template("DATA=path")
        result = validate(env, tmpl)
        assert not result.is_valid


class TestValidateEnum:
    def test_valid_enum_value(self):
        env = parse_env("LEVEL=info")
        tmpl = parse_template("LEVEL=enum(debug,info,warn,error)")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_invalid_enum_value(self):
        env = parse_env("LEVEL=trace")
        tmpl = parse_template("LEVEL=enum(debug,info,warn,error)")
        result = validate(env, tmpl)
        assert not result.is_valid
        assert any("enum" in i.message.lower() or "one of" in i.message.lower() for i in result.errors)

    def test_enum_case_sensitive(self):
        env = parse_env("LEVEL=INFO")
        tmpl = parse_template("LEVEL=enum(debug,info,warn,error)")
        result = validate(env, tmpl)
        assert not result.is_valid


class TestValidateString:
    def test_any_string_valid(self):
        env = parse_env("NAME=anything goes here")
        tmpl = parse_template("NAME=string")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_empty_string_required(self):
        env = parse_env("NAME=")
        tmpl = parse_template("NAME=string")
        result = validate(env, tmpl)
        assert not result.is_valid


# ============================================================
# 15. Validation — missing and extra variables
# ============================================================

class TestValidateMissing:
    def test_missing_required(self):
        env = parse_env("")
        tmpl = parse_template("REQUIRED_VAR=string")
        result = validate(env, tmpl)
        assert not result.is_valid
        assert result.missing_count == 1
        assert any("missing" in i.message.lower() for i in result.errors)

    def test_missing_optional(self):
        env = parse_env("")
        tmpl = parse_template("OPT_VAR=?string:default")
        result = validate(env, tmpl)
        assert result.is_valid  # optional missing is not an error
        assert any(i.severity == Severity.INFO for i in result.issues)

    def test_extra_vars_warning(self):
        env = parse_env("EXTRA=value")
        tmpl = parse_template("EXPECTED=string")
        result = validate(env, tmpl)
        assert "EXTRA" in result.extra_vars
        assert any(i.severity == Severity.WARNING and "EXTRA" in i.key for i in result.issues)


class TestValidateStrict:
    def test_strict_extra_vars_are_errors(self):
        env = parse_env("EXTRA=value\nFOO=bar")
        tmpl = parse_template("FOO=string")
        result = validate(env, tmpl, strict=True)
        assert not result.is_valid
        assert any(
            i.severity == Severity.ERROR and "EXTRA" in i.key
            for i in result.issues
        )

    def test_non_strict_extra_vars_are_warnings(self):
        env = parse_env("EXTRA=value\nFOO=bar")
        tmpl = parse_template("FOO=string")
        result = validate(env, tmpl, strict=False)
        assert result.is_valid
        assert any(
            i.severity == Severity.WARNING and "EXTRA" in i.key
            for i in result.issues
        )


# ============================================================
# 16. Validation — counts and properties
# ============================================================

class TestValidationResult:
    def test_checked_count(self):
        env = parse_env("FOO=bar\nBAZ=42")
        tmpl = parse_template("FOO=string\nBAZ=int")
        result = validate(env, tmpl)
        assert result.checked_count == 2

    def test_passed_count(self):
        env = parse_env("FOO=bar\nBAZ=42")
        tmpl = parse_template("FOO=string\nBAZ=int")
        result = validate(env, tmpl)
        assert result.passed_count == 2

    def test_is_valid_true(self):
        env = parse_env("FOO=bar")
        tmpl = parse_template("FOO=string")
        result = validate(env, tmpl)
        assert result.is_valid is True

    def test_is_valid_false(self):
        env = parse_env("FOO=abc")
        tmpl = parse_template("FOO=int")
        result = validate(env, tmpl)
        assert result.is_valid is False

    def test_to_dict(self):
        env = parse_env("FOO=bar")
        tmpl = parse_template("FOO=string")
        result = validate(env, tmpl)
        d = result.to_dict()
        assert d["valid"] is True
        assert d["checked"] == 1
        assert d["passed"] == 1
        assert isinstance(d["issues"], list)

    def test_errors_property(self):
        env = parse_env("FOO=abc")
        tmpl = parse_template("FOO=int")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert result.errors[0].severity == Severity.ERROR

    def test_warnings_property(self):
        env = parse_env("FOO=bar\nEXTRA=x")
        tmpl = parse_template("FOO=string")
        result = validate(env, tmpl)
        assert len(result.warnings) >= 1


# ============================================================
# 17. Diff — comparing two .env files
# ============================================================

class TestDiff:
    def test_identical_files(self):
        a = parse_env("FOO=bar\nBAZ=qux")
        b = parse_env("FOO=bar\nBAZ=qux")
        result = diff_envs(a, b)
        assert not result.has_differences
        assert len(result.same) == 2

    def test_only_in_a(self):
        a = parse_env("FOO=bar\nEXTRA=val")
        b = parse_env("FOO=bar")
        result = diff_envs(a, b)
        assert result.has_differences
        assert len(result.only_in_a) == 1
        assert result.only_in_a[0].key == "EXTRA"

    def test_only_in_b(self):
        a = parse_env("FOO=bar")
        b = parse_env("FOO=bar\nNEW=val")
        result = diff_envs(a, b)
        assert result.has_differences
        assert len(result.only_in_b) == 1
        assert result.only_in_b[0].key == "NEW"

    def test_different_values(self):
        a = parse_env("FOO=bar")
        b = parse_env("FOO=baz")
        result = diff_envs(a, b)
        assert result.has_differences
        assert len(result.different) == 1
        assert result.different[0].value_a == "bar"
        assert result.different[0].value_b == "baz"

    def test_total_keys(self):
        a = parse_env("A=1\nB=2\nC=3")
        b = parse_env("B=2\nC=99\nD=4")
        result = diff_envs(a, b)
        assert result.total_keys == 4  # A, B, C, D

    def test_mixed_diff(self):
        a = parse_env("SAME=val\nDIFF=old\nONLY_A=a")
        b = parse_env("SAME=val\nDIFF=new\nONLY_B=b")
        result = diff_envs(a, b)
        assert len(result.same) == 1
        assert len(result.different) == 1
        assert len(result.only_in_a) == 1
        assert len(result.only_in_b) == 1

    def test_to_dict(self):
        a = parse_env("FOO=bar")
        b = parse_env("FOO=baz")
        result = diff_envs(a, b)
        d = result.to_dict()
        assert d["has_differences"] is True
        assert d["total_keys"] == 1
        assert len(d["different"]) == 1

    def test_empty_files(self):
        a = parse_env("")
        b = parse_env("")
        result = diff_envs(a, b)
        assert not result.has_differences
        assert result.total_keys == 0


# ============================================================
# 18. Generator — type inference
# ============================================================

class TestInferType:
    def test_url(self):
        assert infer_type("API_URL", "https://example.com") == "url"

    def test_http_url(self):
        assert infer_type("URL", "http://localhost:3000") == "url"

    def test_email(self):
        assert infer_type("ADMIN", "user@example.com") == "email"

    def test_bool_true(self):
        assert infer_type("DEBUG", "true") == "bool"

    def test_bool_false(self):
        assert infer_type("ENABLED", "false") == "bool"

    def test_bool_yes(self):
        assert infer_type("FLAG", "yes") == "bool"

    def test_bool_on(self):
        assert infer_type("FEATURE", "on") == "bool"

    def test_int(self):
        assert infer_type("COUNT", "42") == "int"

    def test_negative_int(self):
        assert infer_type("OFFSET", "-5") == "int"

    def test_port_with_key_hint(self):
        assert infer_type("PORT", "3000") == "port"
        assert infer_type("DB_PORT", "5432") == "port"

    def test_float(self):
        assert infer_type("RATE", "3.14") == "float"

    def test_scientific_float(self):
        assert infer_type("THRESHOLD", "1e-5") == "float"

    def test_string_default(self):
        assert infer_type("NAME", "hello world") == "string"

    def test_empty_value(self):
        assert infer_type("FOO", "") == "string"

    def test_0_is_int_not_bool(self):
        # 0 and 1 are ambiguous; infer_type prefers int
        assert infer_type("COUNT", "0") == "int"

    def test_1_is_int_not_bool(self):
        assert infer_type("COUNT", "1") == "int"


# ============================================================
# 19. Generator — template generation
# ============================================================

class TestGenerateTemplate:
    def test_basic_generation(self):
        env = parse_env("NAME=hello\nCOUNT=42")
        tmpl = generate_template(env)
        assert "NAME=string" in tmpl
        assert "COUNT=int" in tmpl

    def test_url_inference_in_template(self):
        env = parse_env("API_URL=https://example.com")
        tmpl = generate_template(env)
        assert "API_URL=url" in tmpl

    def test_comments_included(self):
        env = parse_env("FOO=bar")
        tmpl = generate_template(env, include_values_as_comments=True)
        assert "# Current: bar" in tmpl

    def test_comments_excluded(self):
        env = parse_env("FOO=bar")
        tmpl = generate_template(env, include_values_as_comments=False)
        assert "# Current:" not in tmpl

    def test_grouping_by_prefix(self):
        env = parse_env("DB_HOST=localhost\nDB_PORT=5432\nDB_NAME=mydb\nSINGLE=val")
        tmpl = generate_template(env)
        assert "# DB configuration" in tmpl

    def test_trailing_newline(self):
        env = parse_env("FOO=bar")
        tmpl = generate_template(env)
        assert tmpl.endswith("\n")

    def test_port_inference(self):
        env = parse_env("PORT=3000")
        tmpl = generate_template(env)
        assert "PORT=port" in tmpl


# ============================================================
# 20. Integration — full validation flow
# ============================================================

class TestIntegration:
    def test_full_valid_flow(self):
        env_content = """
DATABASE_URL=https://db.example.com/mydb
PORT=5432
DEBUG=true
LOG_LEVEL=info
ADMIN_EMAIL=admin@example.com
"""
        tmpl_content = """
DATABASE_URL=url
PORT=port
DEBUG=bool
LOG_LEVEL=enum(debug,info,warn,error)
ADMIN_EMAIL=email
"""
        env = parse_env(env_content)
        tmpl = parse_template(tmpl_content)
        result = validate(env, tmpl)
        assert result.is_valid
        assert result.checked_count == 5
        assert result.passed_count == 5

    def test_full_invalid_flow(self):
        env_content = """
PORT=abc
DEBUG=maybe
"""
        tmpl_content = """
PORT=port
DEBUG=bool
API_KEY=string
"""
        env = parse_env(env_content)
        tmpl = parse_template(tmpl_content)
        result = validate(env, tmpl)
        assert not result.is_valid
        assert result.missing_count == 1  # API_KEY
        assert len(result.errors) == 3  # PORT invalid, DEBUG invalid, API_KEY missing

    def test_optional_missing_is_ok(self):
        env_content = "FOO=bar"
        tmpl_content = "FOO=string\nOPTIONAL=?string:default"
        env = parse_env(env_content)
        tmpl = parse_template(tmpl_content)
        result = validate(env, tmpl)
        assert result.is_valid

    def test_enum_validation(self):
        env = parse_env("ENV=staging")
        tmpl = parse_template("ENV=enum(development,staging,production)")
        result = validate(env, tmpl)
        assert result.is_valid

    def test_round_trip_generate_validate(self):
        """Generate a template from .env, then validate the same .env against it."""
        env_content = "NAME=hello\nCOUNT=42\nDEBUG=true"
        env = parse_env(env_content)
        tmpl_str = generate_template(env, include_values_as_comments=False)
        tmpl = parse_template(tmpl_str)
        result = validate(env, tmpl)
        assert result.is_valid


# ============================================================
# 21. Fix suggestions
# ============================================================

class TestFixSuggestions:
    def test_int_fix_suggestion(self):
        env = parse_env("COUNT=abc")
        tmpl = parse_template("COUNT=int")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert result.errors[0].fix_suggestion is not None
        assert "42" in result.errors[0].fix_suggestion

    def test_int_float_fix_suggestion(self):
        env = parse_env("COUNT=3.14")
        tmpl = parse_template("COUNT=int")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert result.errors[0].fix_suggestion is not None
        assert "3" in result.errors[0].fix_suggestion

    def test_bool_fix_suggestion(self):
        env = parse_env("DEBUG=maybe")
        tmpl = parse_template("DEBUG=bool")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert result.errors[0].fix_suggestion is not None

    def test_bool_y_fix_suggestion(self):
        env = parse_env("DEBUG=y")
        tmpl = parse_template("DEBUG=bool")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert "yes" in result.errors[0].fix_suggestion

    def test_url_no_scheme_fix_suggestion(self):
        env = parse_env("API=example.com")
        tmpl = parse_template("API=url")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert "https://" in result.errors[0].fix_suggestion

    def test_email_no_at_fix_suggestion(self):
        env = parse_env("ADMIN=userexample.com")
        tmpl = parse_template("ADMIN=email")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert "@" in result.errors[0].fix_suggestion

    def test_enum_case_mismatch_fix_suggestion(self):
        env = parse_env("LEVEL=INFO")
        tmpl = parse_template("LEVEL=enum(debug,info,warn,error)")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert result.errors[0].fix_suggestion is not None
        assert "info" in result.errors[0].fix_suggestion

    def test_missing_var_has_fix_suggestion(self):
        env = parse_env("")
        tmpl = parse_template("REQUIRED=string")
        result = validate(env, tmpl)
        assert len(result.errors) == 1
        assert result.errors[0].fix_suggestion is not None
        assert "REQUIRED" in result.errors[0].fix_suggestion


# ============================================================
# 22. Secret detection
# ============================================================

class TestSecretDetection:
    def test_no_secrets_when_disabled(self):
        env = parse_env("API_KEY=sk-1234567890abcdef1234567890abcdef12")
        tmpl = parse_template("API_KEY=string")
        result = validate(env, tmpl, detect_secrets=False)
        assert not any("secret" in i.message.lower() for i in result.issues)

    def test_openai_key_detected(self):
        env = parse_env("API_KEY=sk-1234567890abcdef1234567890abcdef12")
        tmpl = parse_template("API_KEY=string")
        result = validate(env, tmpl, detect_secrets=True)
        secret_warnings = [i for i in result.issues if "secret" in i.message.lower()]
        assert len(secret_warnings) >= 1
        assert secret_warnings[0].fix_suggestion is not None

    def test_github_token_detected(self):
        env = parse_env("TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij")
        tmpl = parse_template("TOKEN=string")
        result = validate(env, tmpl, detect_secrets=True)
        secret_warnings = [i for i in result.issues if "secret" in i.message.lower()]
        assert len(secret_warnings) >= 1

    def test_aws_key_detected(self):
        env = parse_env("AWS_KEY=AKIAIOSFODNN7EXAMPLE")
        tmpl = parse_template("AWS_KEY=string")
        result = validate(env, tmpl, detect_secrets=True)
        secret_warnings = [i for i in result.issues if "secret" in i.message.lower()]
        assert len(secret_warnings) >= 1

    def test_short_value_not_secret(self):
        env = parse_env("SECRET_KEY=short")
        tmpl = parse_template("SECRET_KEY=string")
        result = validate(env, tmpl, detect_secrets=True)
        secret_warnings = [i for i in result.issues if "secret" in i.message.lower()]
        assert len(secret_warnings) == 0

    def test_placeholder_not_secret(self):
        env = parse_env("SECRET_KEY=changeme")
        tmpl = parse_template("SECRET_KEY=string")
        result = validate(env, tmpl, detect_secrets=True)
        secret_warnings = [i for i in result.issues if "secret" in i.message.lower()]
        assert len(secret_warnings) == 0

    def test_secret_key_name_with_long_value(self):
        env = parse_env("API_SECRET_TOKEN=abcdefghijklmnop1234")
        tmpl = parse_template("API_SECRET_TOKEN=string")
        result = validate(env, tmpl, detect_secrets=True)
        secret_warnings = [i for i in result.issues if "secret" in i.message.lower()]
        assert len(secret_warnings) >= 1


# ============================================================
# 23. URL scheme validation (postgres://, redis://)
# ============================================================

class TestURLSchemeValidation:
    def test_postgres_url_inferred(self):
        assert infer_type("DATABASE_URL", "postgres://user:pass@localhost/db") == "url"

    def test_redis_url_inferred(self):
        assert infer_type("REDIS_URL", "redis://localhost:6379") == "url"

    def test_amqp_url_inferred(self):
        assert infer_type("BROKER_URL", "amqp://guest:guest@localhost") == "url"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
