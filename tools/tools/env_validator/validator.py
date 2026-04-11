"""
Environment File Validator — Validate .env Files Against Type-Annotated Templates

Parses .env files handling all common quirks (quoted values, multiline, comments,
export prefix, interpolation, BOM, Windows line endings). Parses .env.template
files with type annotations. Validates .env entries against template constraints.
Compares two .env files. Generates templates from existing .env files.

Supported template types:
    string  — any string value
    int     — integer (decimal)
    float   — floating point number
    bool    — true/false/yes/no/1/0/on/off (case-insensitive)
    url     — URL format (any scheme: http://, https://, postgres://, redis://, etc.)
    email   — email format (contains @)
    port    — integer 1-65535
    path    — filesystem path
    enum(a,b,c) — one of the listed values

Template syntax:
    TYPE                    -> required, no default
    ?TYPE                   -> optional, no default
    ?TYPE:DEFAULT           -> optional, with default value

Pure Python, no external dependencies.

Usage:
    python validator.py check .env --template .env.template
    python validator.py init .env
    python validator.py diff .env.local .env.production
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ===================================================================
# .env Parser
# ===================================================================

@dataclass
class EnvEntry:
    """A single entry from a .env file."""

    key: str
    value: str
    raw_value: str
    line_number: int
    is_exported: bool = False
    has_interpolation: bool = False
    quote_style: Optional[str] = None  # None, 'single', 'double', 'backtick'


@dataclass
class ParseResult:
    """Result of parsing a .env file."""

    entries: dict[str, EnvEntry] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    comments: list[tuple[int, str]] = field(default_factory=list)


# Escape sequences recognized in double-quoted values
_DOUBLE_QUOTE_ESCAPES = {
    "\\n": "\n",
    "\\r": "\r",
    "\\t": "\t",
    '\\"': '"',
    "\\\\": "\\",
    "\\$": "$",
}

# Pattern for interpolation references
_INTERPOLATION_SIMPLE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_INTERPOLATION_BRACED = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _strip_bom(text: str) -> str:
    """Remove UTF-8 BOM if present."""
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def _process_double_quote_escapes(value: str) -> str:
    """Process escape sequences in a double-quoted value."""
    result = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            two_char = value[i : i + 2]
            if two_char in _DOUBLE_QUOTE_ESCAPES:
                result.append(_DOUBLE_QUOTE_ESCAPES[two_char])
                i += 2
                continue
        result.append(value[i])
        i += 1
    return "".join(result)


def _has_interpolation(value: str) -> bool:
    """Check if a value contains interpolation references."""
    return bool(_INTERPOLATION_SIMPLE.search(value) or _INTERPOLATION_BRACED.search(value))


def resolve_interpolation(value: str, env: dict[str, str]) -> str:
    """Resolve $VAR and ${VAR} references in a value."""

    def replace_braced(match: re.Match) -> str:
        var_name = match.group(1)
        return env.get(var_name, match.group(0))

    def replace_simple(match: re.Match) -> str:
        var_name = match.group(1)
        return env.get(var_name, match.group(0))

    result = _INTERPOLATION_BRACED.sub(replace_braced, value)
    result = _INTERPOLATION_SIMPLE.sub(replace_simple, result)
    return result


def _extract_quoted_value(
    line: str, start: int, quote_char: str
) -> tuple[str, str, int]:
    """Extract a quoted value from a line starting at position start.

    Returns (raw_value, processed_value, end_position).
    """
    i = start
    raw_chars = []
    while i < len(line):
        if line[i] == "\\" and quote_char == '"' and i + 1 < len(line):
            raw_chars.append(line[i])
            raw_chars.append(line[i + 1])
            i += 2
            continue
        if line[i] == quote_char:
            raw = "".join(raw_chars)
            if quote_char == '"':
                processed = _process_double_quote_escapes(raw)
            else:
                processed = raw
            return raw, processed, i + 1
        raw_chars.append(line[i])
        i += 1

    raw = "".join(raw_chars)
    if quote_char == '"':
        processed = _process_double_quote_escapes(raw)
    else:
        processed = raw
    return raw, processed, i


def _extract_multiline_value(
    lines: list[str], line_idx: int, col: int, quote_char: str
) -> tuple[str, str, int, str]:
    """Extract a multiline quoted value spanning multiple lines.

    Returns (raw_value, processed_value, ending_line_index, quote_style).
    """
    current_line = lines[line_idx]
    raw_parts = []
    first_part = current_line[col:]
    raw, processed, end_pos = _extract_quoted_value(
        first_part, 0, quote_char
    )
    if end_pos >= len(first_part) and (
        not first_part or first_part[-1] != quote_char
    ):
        raw_parts.append(first_part)
        idx = line_idx + 1
        while idx < len(lines):
            raw_parts.append(lines[idx])
            if quote_char in lines[idx]:
                qpos = lines[idx].index(quote_char)
                raw_parts[-1] = lines[idx][:qpos]
                full_raw = "\n".join(raw_parts)
                if quote_char == '"':
                    full_processed = _process_double_quote_escapes(full_raw)
                else:
                    full_processed = full_raw
                quote_style = (
                    "double"
                    if quote_char == '"'
                    else "single" if quote_char == "'" else "backtick"
                )
                return full_raw, full_processed, idx, quote_style
            idx += 1
        full_raw = "\n".join(raw_parts)
        if quote_char == '"':
            full_processed = _process_double_quote_escapes(full_raw)
        else:
            full_processed = full_raw
        quote_style = (
            "double"
            if quote_char == '"'
            else "single" if quote_char == "'" else "backtick"
        )
        return full_raw, full_processed, len(lines) - 1, quote_style
    else:
        quote_style = (
            "double"
            if quote_char == '"'
            else "single" if quote_char == "'" else "backtick"
        )
        return raw, processed, line_idx, quote_style


def parse_env(content: str) -> ParseResult:
    """Parse a .env file content string into structured entries."""
    content = _strip_bom(content)
    result = ParseResult()
    lines = content.splitlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        line_number = i + 1

        line = line.rstrip()

        if not line.strip():
            i += 1
            continue

        stripped = line.lstrip()
        if stripped.startswith("#"):
            result.comments.append((line_number, stripped[1:].strip()))
            i += 1
            continue

        is_exported = False
        working = stripped
        if working.startswith("export "):
            is_exported = True
            working = working[7:].lstrip()
        elif working.startswith("export\t"):
            is_exported = True
            working = working[7:].lstrip()

        eq_pos = working.find("=")
        if eq_pos == -1:
            result.errors.append(
                f"Line {line_number}: No '=' found in '{line.strip()}'"
            )
            i += 1
            continue

        key = working[:eq_pos].strip()

        if not key:
            result.errors.append(
                f"Line {line_number}: Empty key in '{line.strip()}'"
            )
            i += 1
            continue

        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            result.errors.append(
                f"Line {line_number}: Invalid key name '{key}'"
            )
            i += 1
            continue

        value_part = working[eq_pos + 1 :]
        value_stripped = value_part.lstrip()

        if not value_stripped:
            entry = EnvEntry(
                key=key,
                value="",
                raw_value="",
                line_number=line_number,
                is_exported=is_exported,
                quote_style=None,
            )
            result.entries[key] = entry
            i += 1
            continue

        first_char = value_stripped[0]
        if first_char in ('"', "'", "`"):
            quote_char = first_char
            after_quote = value_stripped[1:]

            raw, processed, end_pos = _extract_quoted_value(
                after_quote, 0, quote_char
            )

            if end_pos < len(after_quote) or (
                after_quote and after_quote[end_pos - 1 : end_pos] == quote_char
            ):
                quote_style = (
                    "double"
                    if quote_char == '"'
                    else "single" if quote_char == "'" else "backtick"
                )
                has_interp = (
                    _has_interpolation(processed)
                    if quote_style != "single"
                    else False
                )
                entry = EnvEntry(
                    key=key,
                    value=processed,
                    raw_value=raw,
                    line_number=line_number,
                    is_exported=is_exported,
                    has_interpolation=has_interp,
                    quote_style=quote_style,
                )
                result.entries[key] = entry
                i += 1
                continue
            else:
                col = len(lines[i]) - len(lines[i].rstrip()) + len(stripped) - len(value_stripped) + 1
                raw, processed, end_line, quote_style = (
                    _extract_multiline_value(lines, i, col, quote_char)
                )
                has_interp = (
                    _has_interpolation(processed)
                    if quote_style != "single"
                    else False
                )
                entry = EnvEntry(
                    key=key,
                    value=processed,
                    raw_value=raw,
                    line_number=line_number,
                    is_exported=is_exported,
                    has_interpolation=has_interp,
                    quote_style=quote_style,
                )
                result.entries[key] = entry
                i = end_line + 1
                continue

        comment_match = re.search(r"\s+#", value_stripped)
        if comment_match:
            value_final = value_stripped[: comment_match.start()].rstrip()
        else:
            value_final = value_stripped.rstrip()

        has_interp = _has_interpolation(value_final)
        entry = EnvEntry(
            key=key,
            value=value_final,
            raw_value=value_final,
            line_number=line_number,
            is_exported=is_exported,
            has_interpolation=has_interp,
            quote_style=None,
        )
        result.entries[key] = entry
        i += 1

    return result


def parse_env_file(path: str) -> ParseResult:
    """Parse a .env file from a file path."""
    with open(path, "r", encoding="utf-8-sig") as f:
        content = f.read()
    return parse_env(content)


# ===================================================================
# Template Parser
# ===================================================================

@dataclass
class TemplateEntry:
    """A single entry from a .env.template file."""

    key: str
    var_type: str  # string, int, float, bool, url, email, port, path, enum
    required: bool = True
    default: Optional[str] = None
    enum_values: list[str] = field(default_factory=list)
    line_number: int = 0
    description: Optional[str] = None


@dataclass
class TemplateResult:
    """Result of parsing a .env.template file."""

    entries: dict[str, TemplateEntry] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


# Pattern for enum type: enum(val1,val2,val3)
_ENUM_PATTERN = re.compile(r"^enum\(([^)]+)\)$")

# Valid type names
_VALID_TYPES = {"string", "int", "float", "bool", "url", "email", "port", "path"}


def _parse_type_spec(spec: str) -> tuple[str, bool, Optional[str], list[str]]:
    """Parse a type specification string.

    Returns (type_name, required, default_value, enum_values).
    """
    required = True
    working = spec.strip()

    if working.startswith("?"):
        required = False
        working = working[1:]

    default = None
    paren_depth = 0
    colon_pos = -1
    for idx, ch in enumerate(working):
        if ch == "(":
            paren_depth += 1
        elif ch == ")":
            paren_depth -= 1
        elif ch == ":" and paren_depth == 0:
            colon_pos = idx
            break

    if colon_pos >= 0:
        default = working[colon_pos + 1:]
        working = working[:colon_pos]

    enum_match = _ENUM_PATTERN.match(working)
    if enum_match:
        values_str = enum_match.group(1)
        enum_values = [v.strip() for v in values_str.split(",")]
        return "enum", required, default, enum_values

    type_name = working.lower()
    if not type_name:
        type_name = "string"

    return type_name, required, default, []


def parse_template(content: str) -> TemplateResult:
    """Parse a .env.template file content string."""
    result = TemplateResult()
    lines = content.splitlines()
    pending_comment: Optional[str] = None

    for i, line in enumerate(lines):
        line_number = i + 1
        stripped = line.strip()

        if not stripped:
            pending_comment = None
            continue

        if stripped.startswith("#"):
            pending_comment = stripped[1:].strip()
            continue

        working = stripped
        if working.startswith("export "):
            working = working[7:].lstrip()
        elif working.startswith("export\t"):
            working = working[7:].lstrip()

        eq_pos = working.find("=")
        if eq_pos == -1:
            result.errors.append(
                f"Line {line_number}: No '=' found in '{stripped}'"
            )
            pending_comment = None
            continue

        key = working[:eq_pos].strip()

        if not key:
            result.errors.append(
                f"Line {line_number}: Empty key in '{stripped}'"
            )
            pending_comment = None
            continue

        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
            result.errors.append(
                f"Line {line_number}: Invalid key name '{key}'"
            )
            pending_comment = None
            continue

        type_spec = working[eq_pos + 1:].strip()

        if not type_spec:
            type_name, required, default, enum_values = "string", True, None, []
        else:
            type_name, required, default, enum_values = _parse_type_spec(type_spec)

        if type_name not in _VALID_TYPES and type_name != "enum":
            result.errors.append(
                f"Line {line_number}: Unknown type '{type_name}' for key '{key}'"
            )
            pending_comment = None
            continue

        entry = TemplateEntry(
            key=key,
            var_type=type_name,
            required=required,
            default=default,
            enum_values=enum_values,
            line_number=line_number,
            description=pending_comment,
        )
        result.entries[key] = entry
        pending_comment = None

    return result


def parse_template_file(path: str) -> TemplateResult:
    """Parse a .env.template file from a file path."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return parse_template(content)


# ===================================================================
# Validator
# ===================================================================

class Severity(Enum):
    """Severity level for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    key: str
    message: str
    severity: Severity
    expected: Optional[str] = None
    actual: Optional[str] = None
    fix_suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating a .env file against a template."""

    issues: list[ValidationIssue] = field(default_factory=list)
    checked_count: int = 0
    passed_count: int = 0
    missing_count: int = 0
    extra_vars: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no errors were found."""
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        """All error-level issues."""
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """All warning-level issues."""
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def to_dict(self) -> dict:
        """Convert to a JSON-serializable dict."""
        return {
            "valid": self.is_valid,
            "checked": self.checked_count,
            "passed": self.passed_count,
            "missing": self.missing_count,
            "extra_vars": self.extra_vars,
            "issues": [
                {
                    "key": issue.key,
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "expected": issue.expected,
                    "actual": issue.actual,
                    "fix_suggestion": issue.fix_suggestion,
                }
                for issue in self.issues
            ],
        }


# URL pattern — accepts any standard scheme (RFC 3986)
_URL_PATTERN = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9+\-.]*://"  # scheme (RFC 3986)
    r"[^\s]"                           # at least one char after scheme
    r"[^\s]*$",                        # rest of URL
    re.IGNORECASE,
)

# Email pattern
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# Boolean values recognized
_BOOL_TRUE = {"true", "yes", "1", "on"}
_BOOL_FALSE = {"false", "no", "0", "off"}
_BOOL_ALL = _BOOL_TRUE | _BOOL_FALSE

# Patterns that suggest a value contains a secret
_SECRET_PATTERNS = [
    re.compile(r"^[A-Za-z0-9+/]{32,}={0,2}$"),  # base64-like, 32+ chars
    re.compile(r"^[0-9a-f]{32,}$", re.IGNORECASE),  # hex string, 32+ chars
    re.compile(r"^ghp_[A-Za-z0-9]{36}$"),  # GitHub personal access token
    re.compile(r"^sk-[A-Za-z0-9]{32,}$"),  # OpenAI/Stripe secret key
    re.compile(r"^AKIA[A-Z0-9]{16}$"),  # AWS access key ID
    re.compile(r"^-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),  # Private key
]

# Key names that typically hold secrets
_SECRET_KEY_PATTERNS = re.compile(
    r"(SECRET|PASSWORD|PASSWD|TOKEN|API_KEY|PRIVATE_KEY|ACCESS_KEY|AUTH)",
    re.IGNORECASE,
)


def _validate_int(value: str) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False


def _validate_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _validate_bool(value: str) -> bool:
    return value.lower() in _BOOL_ALL


def _validate_url(value: str) -> bool:
    return bool(_URL_PATTERN.match(value))


def _validate_email(value: str) -> bool:
    return bool(_EMAIL_PATTERN.match(value))


def _validate_port(value: str) -> bool:
    try:
        port = int(value)
        return 1 <= port <= 65535
    except ValueError:
        return False


def _validate_path(value: str, check_exists: bool = False) -> bool:
    if not value:
        return False
    if check_exists:
        return os.path.exists(value)
    return True


def _validate_enum(value: str, allowed: list[str]) -> bool:
    return value in allowed


def _suggest_fix(key: str, value: str, type_name: str, template: TemplateEntry) -> Optional[str]:
    """Generate a fix suggestion for a validation error."""
    if type_name == "int":
        try:
            float(value)
            return f"Value '{value}' looks like a float. Use an integer instead, e.g., {key}={int(float(value))}"
        except ValueError:
            pass
        stripped = value.strip('"').strip("'")
        if stripped != value:
            try:
                int(stripped)
                return f"Remove quotes around the value: {key}={stripped}"
            except ValueError:
                pass
        return f"Set {key} to a whole number, e.g., {key}=42"

    if type_name == "float":
        return f"Set {key} to a number, e.g., {key}=3.14"

    if type_name == "bool":
        lower = value.lower()
        if lower in ("y", "n"):
            suggested = "yes" if lower == "y" else "no"
            return f"Did you mean '{suggested}'? Use: {key}={suggested}"
        if lower in ("t", "f"):
            suggested = "true" if lower == "t" else "false"
            return f"Did you mean '{suggested}'? Use: {key}={suggested}"
        if lower in ("enabled", "disabled"):
            suggested = "true" if lower == "enabled" else "false"
            return f"Use 'true' or 'false' instead: {key}={suggested}"
        return f"Use one of: true, false, yes, no, 1, 0, on, off"

    if type_name == "url":
        if "://" not in value and ("." in value or "localhost" in value):
            return f"Missing scheme. Try: {key}=https://{value}"
        return f"Set {key} to a valid URL, e.g., {key}=https://example.com"

    if type_name == "email":
        if "@" not in value:
            return f"Missing '@'. A valid email looks like: user@example.com"
        return f"Set {key} to a valid email, e.g., {key}=user@example.com"

    if type_name == "port":
        try:
            port = int(value)
            if port <= 0:
                return f"Port must be between 1 and 65535. Common ports: 80, 443, 3000, 5432, 8080"
            if port > 65535:
                return f"Port {port} is too high. Maximum is 65535. Common ports: 80, 443, 3000, 5432, 8080"
        except ValueError:
            return f"Set {key} to a number between 1 and 65535, e.g., {key}=3000"

    if type_name == "enum":
        allowed = template.enum_values
        lower_map = {v.lower(): v for v in allowed}
        if value.lower() in lower_map:
            correct = lower_map[value.lower()]
            return f"Case mismatch. Use: {key}={correct}"
        return f"Valid values are: {', '.join(allowed)}"

    return None


def _detect_secret(key: str, value: str) -> bool:
    """Detect if a value looks like it contains a secret."""
    if not value or len(value) < 8:
        return False

    has_secret_key = bool(_SECRET_KEY_PATTERNS.search(key))

    for pattern in _SECRET_PATTERNS:
        if pattern.search(value):
            return True

    if has_secret_key and len(value) >= 16:
        placeholders = {
            "changeme", "change-me", "your-secret-here", "xxx",
            "placeholder", "todo", "fixme", "replace-me",
        }
        if value.lower() not in placeholders:
            return True

    return False


def validate_entry(
    entry: EnvEntry,
    template: TemplateEntry,
    check_path_exists: bool = False,
) -> list[ValidationIssue]:
    """Validate a single .env entry against its template constraint."""
    issues: list[ValidationIssue] = []
    value = entry.value

    if not value and template.required and template.default is None:
        issues.append(
            ValidationIssue(
                key=entry.key,
                message=f"Required variable '{entry.key}' is empty",
                severity=Severity.ERROR,
                expected=template.var_type,
                actual="(empty)",
                fix_suggestion=f"Set a value: {entry.key}=<{template.var_type}>",
            )
        )
        return issues

    if not value:
        return issues

    type_name = template.var_type

    if type_name == "string":
        pass

    elif type_name == "int":
        if not _validate_int(value):
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=f"'{entry.key}' expected int, got '{value}'",
                    severity=Severity.ERROR,
                    expected="int",
                    actual=value,
                    fix_suggestion=_suggest_fix(entry.key, value, "int", template),
                )
            )

    elif type_name == "float":
        if not _validate_float(value):
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=f"'{entry.key}' expected float, got '{value}'",
                    severity=Severity.ERROR,
                    expected="float",
                    actual=value,
                    fix_suggestion=_suggest_fix(entry.key, value, "float", template),
                )
            )

    elif type_name == "bool":
        if not _validate_bool(value):
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=(
                        f"'{entry.key}' expected bool "
                        f"(true/false/yes/no/1/0/on/off), got '{value}'"
                    ),
                    severity=Severity.ERROR,
                    expected="bool",
                    actual=value,
                    fix_suggestion=_suggest_fix(entry.key, value, "bool", template),
                )
            )

    elif type_name == "url":
        if not _validate_url(value):
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=f"'{entry.key}' expected URL, got '{value}'",
                    severity=Severity.ERROR,
                    expected="url",
                    actual=value,
                    fix_suggestion=_suggest_fix(entry.key, value, "url", template),
                )
            )

    elif type_name == "email":
        if not _validate_email(value):
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=f"'{entry.key}' expected email, got '{value}'",
                    severity=Severity.ERROR,
                    expected="email",
                    actual=value,
                    fix_suggestion=_suggest_fix(entry.key, value, "email", template),
                )
            )

    elif type_name == "port":
        if not _validate_port(value):
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=f"'{entry.key}' expected port (1-65535), got '{value}'",
                    severity=Severity.ERROR,
                    expected="port (1-65535)",
                    actual=value,
                    fix_suggestion=_suggest_fix(entry.key, value, "port", template),
                )
            )

    elif type_name == "path":
        if not _validate_path(value, check_exists=check_path_exists):
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=f"'{entry.key}' path does not exist: '{value}'",
                    severity=Severity.ERROR
                    if check_path_exists
                    else Severity.WARNING,
                    expected="path",
                    actual=value,
                    fix_suggestion=f"Create the path or update the value: {entry.key}=<valid-path>",
                )
            )

    elif type_name == "enum":
        if not _validate_enum(value, template.enum_values):
            allowed = ", ".join(template.enum_values)
            issues.append(
                ValidationIssue(
                    key=entry.key,
                    message=(
                        f"'{entry.key}' expected one of [{allowed}], "
                        f"got '{value}'"
                    ),
                    severity=Severity.ERROR,
                    expected=f"enum({allowed})",
                    actual=value,
                    fix_suggestion=_suggest_fix(entry.key, value, "enum", template),
                )
            )

    return issues


def validate(
    env: ParseResult,
    template: TemplateResult,
    strict: bool = False,
    check_path_exists: bool = False,
    detect_secrets: bool = False,
) -> ValidationResult:
    """Validate a parsed .env against a parsed template."""
    result = ValidationResult()

    for key, tmpl_entry in template.entries.items():
        result.checked_count += 1

        if key not in env.entries:
            if tmpl_entry.required:
                result.missing_count += 1
                result.issues.append(
                    ValidationIssue(
                        key=key,
                        message=f"Required variable '{key}' is missing",
                        severity=Severity.ERROR,
                        fix_suggestion=f"Add to your .env file: {key}=<{tmpl_entry.var_type}>",
                    )
                )
            else:
                result.issues.append(
                    ValidationIssue(
                        key=key,
                        message=f"Optional variable '{key}' is not set (default: {tmpl_entry.default})",
                        severity=Severity.INFO,
                    )
                )
                result.passed_count += 1
            continue

        env_entry = env.entries[key]
        issues = validate_entry(
            env_entry, tmpl_entry, check_path_exists=check_path_exists
        )

        if strict:
            for issue in issues:
                if issue.severity == Severity.WARNING:
                    issue.severity = Severity.ERROR

        result.issues.extend(issues)

        if not any(i.severity == Severity.ERROR for i in issues):
            result.passed_count += 1

    for key in env.entries:
        if key not in template.entries:
            result.extra_vars.append(key)
            severity = Severity.ERROR if strict else Severity.WARNING
            result.issues.append(
                ValidationIssue(
                    key=key,
                    message=f"Variable '{key}' is not defined in template",
                    severity=severity,
                    fix_suggestion=f"Add '{key}' to your .env.template, or remove it from .env",
                )
            )

    # Secret detection
    if detect_secrets:
        for key, entry in env.entries.items():
            if _detect_secret(key, entry.value):
                result.issues.append(
                    ValidationIssue(
                        key=key,
                        message=f"Variable '{key}' appears to contain a secret value",
                        severity=Severity.WARNING,
                        fix_suggestion=(
                            f"Avoid committing secrets. Use a .env.local file "
                            f"(added to .gitignore) or an environment variable manager."
                        ),
                    )
                )

    return result


# ===================================================================
# Differ
# ===================================================================

@dataclass
class DiffEntry:
    """A single diff entry between two .env files."""

    key: str
    status: str  # 'only_a', 'only_b', 'different', 'same'
    value_a: str | None = None
    value_b: str | None = None


@dataclass
class DiffResult:
    """Result of comparing two .env files."""

    only_in_a: list[DiffEntry] = field(default_factory=list)
    only_in_b: list[DiffEntry] = field(default_factory=list)
    different: list[DiffEntry] = field(default_factory=list)
    same: list[DiffEntry] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.only_in_a or self.only_in_b or self.different)

    @property
    def total_keys(self) -> int:
        return (
            len(self.only_in_a)
            + len(self.only_in_b)
            + len(self.different)
            + len(self.same)
        )

    def to_dict(self) -> dict:
        return {
            "has_differences": self.has_differences,
            "total_keys": self.total_keys,
            "only_in_a": [
                {"key": e.key, "value": e.value_a} for e in self.only_in_a
            ],
            "only_in_b": [
                {"key": e.key, "value": e.value_b} for e in self.only_in_b
            ],
            "different": [
                {"key": e.key, "value_a": e.value_a, "value_b": e.value_b}
                for e in self.different
            ],
            "same": [{"key": e.key, "value": e.value_a} for e in self.same],
        }


def diff_envs(a: ParseResult, b: ParseResult) -> DiffResult:
    """Compare two parsed .env files."""
    result = DiffResult()
    all_keys = sorted(set(a.entries.keys()) | set(b.entries.keys()))

    for key in all_keys:
        in_a = key in a.entries
        in_b = key in b.entries

        if in_a and not in_b:
            result.only_in_a.append(
                DiffEntry(key=key, status="only_a", value_a=a.entries[key].value)
            )
        elif in_b and not in_a:
            result.only_in_b.append(
                DiffEntry(key=key, status="only_b", value_b=b.entries[key].value)
            )
        elif a.entries[key].value == b.entries[key].value:
            result.same.append(
                DiffEntry(
                    key=key, status="same",
                    value_a=a.entries[key].value, value_b=b.entries[key].value,
                )
            )
        else:
            result.different.append(
                DiffEntry(
                    key=key, status="different",
                    value_a=a.entries[key].value, value_b=b.entries[key].value,
                )
            )

    return result


# ===================================================================
# Generator — infer template from .env
# ===================================================================

# URL pattern for type inference — accepts any scheme
_INFER_URL_PATTERN = re.compile(
    r"^[a-zA-Z][a-zA-Z0-9+\-.]*://[^\s]+$", re.IGNORECASE
)

# Email pattern for type inference
_INFER_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# Boolean values for inference
_BOOL_WORD_VALUES = {"true", "false", "yes", "no", "on", "off"}

# Common port-related key patterns
_PORT_KEY_PATTERNS = re.compile(r"port", re.IGNORECASE)


def infer_type(key: str, value: str) -> str:
    """Infer the template type from a variable name and value."""
    if not value:
        return "string"

    if _INFER_URL_PATTERN.match(value):
        return "url"

    if _INFER_EMAIL_PATTERN.match(value):
        return "email"

    if value.lower() in _BOOL_WORD_VALUES:
        return "bool"

    try:
        int_val = int(value)
        if _PORT_KEY_PATTERNS.search(key) and 1 <= int_val <= 65535:
            return "port"
        return "int"
    except ValueError:
        pass

    try:
        float(value)
        if "." in value or "e" in value.lower():
            return "float"
    except ValueError:
        pass

    return "string"


def generate_template(env: ParseResult, include_values_as_comments: bool = True) -> str:
    """Generate a .env.template string from a parsed .env file."""
    lines: list[str] = []
    entries = list(env.entries.values())

    groups: dict[str, list[EnvEntry]] = {}
    ungrouped: list[EnvEntry] = []

    for entry in entries:
        parts = entry.key.split("_")
        if len(parts) >= 2:
            prefix = parts[0]
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(entry)
        else:
            ungrouped.append(entry)

    real_groups: dict[str, list[EnvEntry]] = {}
    for prefix, members in groups.items():
        if len(members) >= 2:
            real_groups[prefix] = members
        else:
            ungrouped.extend(members)

    def _format_entry(entry: EnvEntry) -> list[str]:
        result_lines = []
        inferred = infer_type(entry.key, entry.value)
        if include_values_as_comments and entry.value:
            result_lines.append(f"# Current: {entry.value}")
        result_lines.append(f"{entry.key}={inferred}")
        return result_lines

    for prefix in sorted(real_groups.keys()):
        if lines:
            lines.append("")
        lines.append(f"# {prefix} configuration")
        for entry in real_groups[prefix]:
            lines.extend(_format_entry(entry))

    if ungrouped:
        if lines:
            lines.append("")
        for entry in ungrouped:
            lines.extend(_format_entry(entry))

    lines.append("")
    return "\n".join(lines)


def generate_template_file(
    env: ParseResult,
    output_path: str,
    include_values_as_comments: bool = True,
) -> str:
    """Generate and write a .env.template file."""
    content = generate_template(env, include_values_as_comments)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return content


# ===================================================================
# CLI
# ===================================================================

def _cmd_check(args: argparse.Namespace) -> int:
    """Run the check command."""
    try:
        env_result = parse_env_file(args.env_file)
    except FileNotFoundError:
        print(f"Error: .env file not found: {args.env_file}", file=sys.stderr)
        return 2

    if env_result.errors:
        print("Parse errors in .env file:", file=sys.stderr)
        for err in env_result.errors:
            print(f"  {err}", file=sys.stderr)

    try:
        tmpl_result = parse_template_file(args.template)
    except FileNotFoundError:
        print(
            f"Error: Template file not found: {args.template}", file=sys.stderr
        )
        return 2

    if tmpl_result.errors:
        print("Parse errors in template file:", file=sys.stderr)
        for err in tmpl_result.errors:
            print(f"  {err}", file=sys.stderr)
        return 2

    result = validate(
        env_result,
        tmpl_result,
        strict=args.strict,
        check_path_exists=args.check_paths,
        detect_secrets=getattr(args, "detect_secrets", False),
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_validation_result(result)

    return 0 if result.is_valid else 1


def _print_validation_result(result: ValidationResult) -> None:
    """Print validation result in human-readable format."""
    errors = result.errors
    warnings = result.warnings
    info = [i for i in result.issues if i.severity == Severity.INFO]

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for issue in errors:
            print(f"  x {issue.message}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for issue in warnings:
            print(f"  ! {issue.message}")

    if info:
        print(f"\nInfo ({len(info)}):")
        for issue in info:
            print(f"  - {issue.message}")

    print(
        f"\nSummary: {result.passed_count}/{result.checked_count} checks passed"
    )
    if result.missing_count:
        print(f"  Missing: {result.missing_count} required variable(s)")
    if result.extra_vars:
        print(
            f"  Extra: {len(result.extra_vars)} variable(s) not in template"
        )

    if result.is_valid:
        print("\nResult: PASS")
    else:
        print("\nResult: FAIL")


def _cmd_init(args: argparse.Namespace) -> int:
    """Run the init command."""
    try:
        env_result = parse_env_file(args.env_file)
    except FileNotFoundError:
        print(f"Error: .env file not found: {args.env_file}", file=sys.stderr)
        return 2

    if env_result.errors:
        print("Parse warnings in .env file:", file=sys.stderr)
        for err in env_result.errors:
            print(f"  {err}", file=sys.stderr)

    if not env_result.entries:
        print("No variables found in .env file.", file=sys.stderr)
        return 1

    no_comments = getattr(args, "no_comments", False)
    content = generate_template(
        env_result, include_values_as_comments=not no_comments
    )

    output = args.output
    if output == "-":
        print(content, end="")
    else:
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Template written to {output}")

    return 0


def _cmd_diff(args: argparse.Namespace) -> int:
    """Run the diff command."""
    try:
        a_result = parse_env_file(args.file_a)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file_a}", file=sys.stderr)
        return 2

    try:
        b_result = parse_env_file(args.file_b)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file_b}", file=sys.stderr)
        return 2

    result = diff_envs(a_result, b_result)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_diff_result(result, args.file_a, args.file_b, args.values)

    return 0 if not result.has_differences else 1


def _print_diff_result(
    result: DiffResult, file_a: str, file_b: str, show_values: bool
) -> None:
    """Print diff result in human-readable format."""
    if result.only_in_a:
        print(f"\nOnly in {file_a} ({len(result.only_in_a)}):")
        for entry in result.only_in_a:
            if show_values:
                print(f"  + {entry.key}={entry.value_a}")
            else:
                print(f"  + {entry.key}")

    if result.only_in_b:
        print(f"\nOnly in {file_b} ({len(result.only_in_b)}):")
        for entry in result.only_in_b:
            if show_values:
                print(f"  + {entry.key}={entry.value_b}")
            else:
                print(f"  + {entry.key}")

    if result.different:
        print(f"\nDifferent values ({len(result.different)}):")
        for entry in result.different:
            if show_values:
                print(f"  ~ {entry.key}")
                print(f"    A: {entry.value_a}")
                print(f"    B: {entry.value_b}")
            else:
                print(f"  ~ {entry.key}")

    if result.same:
        print(f"\nSame ({len(result.same)}):")
        for entry in result.same:
            print(f"  = {entry.key}")

    print(
        f"\nSummary: {result.total_keys} total keys, "
        f"{len(result.only_in_a)} only in A, "
        f"{len(result.only_in_b)} only in B, "
        f"{len(result.different)} different, "
        f"{len(result.same)} same"
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="env-validate",
        description="Validate .env files against type-annotated templates.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    check_parser = subparsers.add_parser(
        "check", help="Validate .env file against a template",
    )
    check_parser.add_argument("env_file", help="Path to the .env file to validate")
    check_parser.add_argument(
        "--template", "-t", default=".env.template",
        help="Path to the template file (default: .env.template)",
    )
    check_parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    check_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    check_parser.add_argument(
        "--check-paths", action="store_true",
        help="Verify that path-typed values exist on disk",
    )
    check_parser.add_argument(
        "--detect-secrets", action="store_true",
        help="Warn about values that look like committed secrets",
    )

    init_parser = subparsers.add_parser(
        "init", help="Generate a template from an existing .env file",
    )
    init_parser.add_argument("env_file", help="Path to the .env file to analyze")
    init_parser.add_argument(
        "--output", "-o", default=".env.template",
        help="Output path for the template (default: .env.template, use - for stdout)",
    )
    init_parser.add_argument(
        "--no-comments", action="store_true",
        help="Don't include current values as comments",
    )

    diff_parser = subparsers.add_parser(
        "diff", help="Compare two .env files",
    )
    diff_parser.add_argument("file_a", help="First .env file")
    diff_parser.add_argument("file_b", help="Second .env file")
    diff_parser.add_argument("--json", action="store_true", help="Output results as JSON")
    diff_parser.add_argument("--values", action="store_true", help="Show variable values in diff output")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 2

    commands = {
        "check": _cmd_check,
        "init": _cmd_init,
        "diff": _cmd_diff,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 2

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
