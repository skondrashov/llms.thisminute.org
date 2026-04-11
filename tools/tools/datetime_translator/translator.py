"""
DateTime Format Translator — Cross-System Format String Converter for Agents

Translates date/time format strings between seven systems: Python (strftime),
JavaScript (date-fns), Go (reference-time), Java (SimpleDateFormat),
C# (.NET), Ruby (strftime), and moment.js.

Agents constantly wrangle format strings across languages. LLMs frequently
confuse Go's reference-time magic numbers (2006, 01, 02, 15:04:05) with
literal text, mix up Java's M (month) vs m (minute), or forget that moment.js
uses DD (day) while date-fns uses dd.

SUPPORTED SYSTEMS
=================
  python     — strftime/strptime (%Y, %m, %d, %H, %M, %S, etc.)
  javascript — date-fns (yyyy, MM, dd, HH, mm, ss, etc.)
  go         — time.Format reference time (2006-01-02 15:04:05 MST)
  java       — SimpleDateFormat (yyyy, MM, dd, HH, mm, ss, etc.)
  csharp     — .NET custom format (yyyy, MM, dd, HH, mm, ss, fff, tt, etc.)
  ruby       — strftime (very similar to Python, adds %k, %P, %L, %N, etc.)
  momentjs   — moment.js (YYYY, MM, DD, HH, mm, ss, etc.)

FEATURES
========
- Convert any format string between any two systems
- Canonical token layer ensures semantic fidelity
- Round-trip preservation (A->B->A keeps semantics)
- Unsupported token detection (warns when target lacks a concept)
- System aliases (py, js, golang, c#, dotnet, moment, rb, strftime)

Pure Python, no external dependencies.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


# ============================================================================
# Canonical tokens
# ============================================================================


class CanonicalToken(Enum):
    """Canonical date/time format components."""

    YEAR_4DIGIT = "year_4digit"
    YEAR_2DIGIT = "year_2digit"
    MONTH_ZERO_PAD = "month_zero_pad"
    MONTH_NO_PAD = "month_no_pad"
    MONTH_SPACE_PAD = "month_space_pad"
    MONTH_ABBR = "month_abbr"
    MONTH_FULL = "month_full"
    DAY_ZERO_PAD = "day_zero_pad"
    DAY_NO_PAD = "day_no_pad"
    DAY_SPACE_PAD = "day_space_pad"
    DAY_OF_YEAR = "day_of_year"
    DAY_OF_YEAR_NO_PAD = "day_of_year_no_pad"
    WEEKDAY_ABBR = "weekday_abbr"
    WEEKDAY_FULL = "weekday_full"
    WEEKDAY_NUM_SUNDAY = "weekday_num_sun"
    WEEKDAY_NUM_MONDAY = "weekday_num_mon"
    HOUR_24_ZERO_PAD = "hour_24_zero_pad"
    HOUR_24_NO_PAD = "hour_24_no_pad"
    HOUR_24_SPACE_PAD = "hour_24_space_pad"
    HOUR_12_ZERO_PAD = "hour_12_zero_pad"
    HOUR_12_NO_PAD = "hour_12_no_pad"
    MINUTE_ZERO_PAD = "minute_zero_pad"
    MINUTE_NO_PAD = "minute_no_pad"
    SECOND_ZERO_PAD = "second_zero_pad"
    SECOND_NO_PAD = "second_no_pad"
    MILLISECOND = "millisecond"
    MICROSECOND = "microsecond"
    NANOSECOND = "nanosecond"
    AMPM_UPPER = "ampm_upper"
    AMPM_LOWER = "ampm_lower"
    TZ_NAME = "tz_name"
    TZ_OFFSET = "tz_offset"
    TZ_OFFSET_COLON = "tz_offset_colon"
    TZ_OFFSET_SHORT = "tz_offset_short"
    TZ_Z_OR_OFFSET = "tz_z_or_offset"
    TZ_Z_OR_OFFSET_COLON = "tz_z_or_offset_colon"
    WEEK_NUM_SUNDAY = "week_num_sunday"
    WEEK_NUM_MONDAY = "week_num_monday"
    ISO_WEEK_NUM = "iso_week_num"
    ISO_YEAR_4DIGIT = "iso_year_4digit"
    ISO_YEAR_2DIGIT = "iso_year_2digit"
    UNIX_TIMESTAMP = "unix_timestamp"
    ERA_AD_BC = "era_ad_bc"
    CENTURY = "century"
    LITERAL_PERCENT = "literal_percent"


CT = CanonicalToken  # shorthand


# ============================================================================
# System definitions — each system is a dict with parse/render functions
# ============================================================================


def _make_system(name, token_to_canonical, canonical_to_token, parse_fn, render_fn):
    return {
        "SYSTEM_NAME": name,
        "TOKEN_TO_CANONICAL": token_to_canonical,
        "CANONICAL_TO_TOKEN": canonical_to_token,
        "parse": parse_fn,
        "render": render_fn,
    }


# --- Generic parser for strftime-style systems (Python, Ruby) ---

def _strftime_parse(format_string, sorted_tokens, token_map):
    result = []
    i = 0
    while i < len(format_string):
        if format_string[i] == "%":
            matched = False
            for token in sorted_tokens:
                if format_string[i:].startswith(token):
                    result.append((token, token_map[token]))
                    i += len(token)
                    matched = True
                    break
            if not matched:
                if i + 1 < len(format_string):
                    result.append((format_string[i:i+2], None))
                    i += 2
                else:
                    result.append((format_string[i], None))
                    i += 1
        else:
            result.append((format_string[i], None))
            i += 1
    return result


def _strftime_render(tokens, canonical_map):
    parts = []
    for canonical, literal in tokens:
        if canonical is None:
            parts.append(literal.replace("%", "%%") if "%" in literal else literal)
        elif canonical in canonical_map:
            parts.append(canonical_map[canonical])
        else:
            parts.append(f"[?{canonical.value}]")
    return "".join(parts)


# --- Generic parser for letter-token systems (JS, Java, moment, C#) ---

def _letter_parse_quoted(format_string, sorted_tokens, token_map, quote_char="'"):
    result = []
    i = 0
    n = len(format_string)
    while i < n:
        if format_string[i] == quote_char:
            j = i + 1
            raw = quote_char
            while j < n:
                if format_string[j] == quote_char:
                    raw += quote_char
                    if j + 1 < n and format_string[j + 1] == quote_char:
                        raw += quote_char
                        j += 2
                    else:
                        j += 1
                        break
                else:
                    raw += format_string[j]
                    j += 1
            result.append((raw, None))
            i = j
            continue
        matched = False
        for token in sorted_tokens:
            if format_string[i:i + len(token)] == token:
                result.append((token, token_map[token]))
                i += len(token)
                matched = True
                break
        if not matched:
            result.append((format_string[i], None))
            i += 1
    return result


def _letter_render(tokens, canonical_map, format_chars, quote_style="'"):
    parts = []
    for canonical, literal in tokens:
        if canonical is None:
            needs_quoting = any(c in format_chars for c in literal)
            if needs_quoting:
                if quote_style == "'":
                    escaped = literal.replace("'", "''")
                    parts.append(f"'{escaped}'")
                elif quote_style == "[":
                    parts.append(f"[{literal}]")
                else:
                    parts.append(f"'{literal}'")
            else:
                parts.append(literal)
        elif canonical in canonical_map:
            parts.append(canonical_map[canonical])
        else:
            parts.append(f"[?{canonical.value}]")
    return "".join(parts)


# ============================================================================
# Python system
# ============================================================================

_PY_T2C = {
    "%Y": CT.YEAR_4DIGIT, "%y": CT.YEAR_2DIGIT,
    "%m": CT.MONTH_ZERO_PAD, "%-m": CT.MONTH_NO_PAD,
    "%b": CT.MONTH_ABBR, "%B": CT.MONTH_FULL,
    "%d": CT.DAY_ZERO_PAD, "%-d": CT.DAY_NO_PAD, "%e": CT.DAY_SPACE_PAD,
    "%j": CT.DAY_OF_YEAR, "%-j": CT.DAY_OF_YEAR_NO_PAD,
    "%a": CT.WEEKDAY_ABBR, "%A": CT.WEEKDAY_FULL,
    "%w": CT.WEEKDAY_NUM_SUNDAY, "%u": CT.WEEKDAY_NUM_MONDAY,
    "%H": CT.HOUR_24_ZERO_PAD, "%-H": CT.HOUR_24_NO_PAD,
    "%I": CT.HOUR_12_ZERO_PAD, "%-I": CT.HOUR_12_NO_PAD,
    "%M": CT.MINUTE_ZERO_PAD, "%-M": CT.MINUTE_NO_PAD,
    "%S": CT.SECOND_ZERO_PAD, "%-S": CT.SECOND_NO_PAD,
    "%f": CT.MICROSECOND, "%p": CT.AMPM_UPPER,
    "%Z": CT.TZ_NAME, "%z": CT.TZ_OFFSET,
    "%U": CT.WEEK_NUM_SUNDAY, "%W": CT.WEEK_NUM_MONDAY,
    "%G": CT.ISO_YEAR_4DIGIT, "%g": CT.ISO_YEAR_2DIGIT, "%V": CT.ISO_WEEK_NUM,
    "%s": CT.UNIX_TIMESTAMP, "%C": CT.CENTURY, "%%": CT.LITERAL_PERCENT,
}
_PY_C2T = {
    CT.YEAR_4DIGIT: "%Y", CT.YEAR_2DIGIT: "%y",
    CT.MONTH_ZERO_PAD: "%m", CT.MONTH_NO_PAD: "%-m", CT.MONTH_SPACE_PAD: "%m",
    CT.MONTH_ABBR: "%b", CT.MONTH_FULL: "%B",
    CT.DAY_ZERO_PAD: "%d", CT.DAY_NO_PAD: "%-d", CT.DAY_SPACE_PAD: "%e",
    CT.DAY_OF_YEAR: "%j", CT.DAY_OF_YEAR_NO_PAD: "%-j",
    CT.WEEKDAY_ABBR: "%a", CT.WEEKDAY_FULL: "%A",
    CT.WEEKDAY_NUM_SUNDAY: "%w", CT.WEEKDAY_NUM_MONDAY: "%u",
    CT.HOUR_24_ZERO_PAD: "%H", CT.HOUR_24_NO_PAD: "%-H", CT.HOUR_24_SPACE_PAD: "%H",
    CT.HOUR_12_ZERO_PAD: "%I", CT.HOUR_12_NO_PAD: "%-I",
    CT.MINUTE_ZERO_PAD: "%M", CT.MINUTE_NO_PAD: "%-M",
    CT.SECOND_ZERO_PAD: "%S", CT.SECOND_NO_PAD: "%-S",
    CT.MILLISECOND: "%f", CT.MICROSECOND: "%f",
    CT.AMPM_UPPER: "%p", CT.AMPM_LOWER: "%p",
    CT.TZ_NAME: "%Z", CT.TZ_OFFSET: "%z", CT.TZ_OFFSET_COLON: "%z",
    CT.TZ_OFFSET_SHORT: "%z", CT.TZ_Z_OR_OFFSET: "%z", CT.TZ_Z_OR_OFFSET_COLON: "%z",
    CT.WEEK_NUM_SUNDAY: "%U", CT.WEEK_NUM_MONDAY: "%W",
    CT.ISO_WEEK_NUM: "%V", CT.ISO_YEAR_4DIGIT: "%G", CT.ISO_YEAR_2DIGIT: "%g",
    CT.UNIX_TIMESTAMP: "%s", CT.CENTURY: "%C", CT.LITERAL_PERCENT: "%%",
}
_PY_SORTED = sorted(_PY_T2C.keys(), key=len, reverse=True)

def _py_parse(fmt): return _strftime_parse(fmt, _PY_SORTED, _PY_T2C)
def _py_render(tokens): return _strftime_render(tokens, _PY_C2T)


# ============================================================================
# Ruby system
# ============================================================================

_RB_T2C = dict(_PY_T2C)
_RB_T2C.update({
    "%_m": CT.MONTH_SPACE_PAD, "%h": CT.MONTH_ABBR,
    "%k": CT.HOUR_24_SPACE_PAD, "%l": CT.HOUR_12_NO_PAD,
    "%P": CT.AMPM_LOWER, "%L": CT.MILLISECOND, "%N": CT.NANOSECOND,
    "%3N": CT.MILLISECOND, "%6N": CT.MICROSECOND, "%9N": CT.NANOSECOND,
    "%:z": CT.TZ_OFFSET_COLON, "%::z": CT.TZ_OFFSET_COLON,
})
_RB_C2T = dict(_PY_C2T)
_RB_C2T.update({
    CT.MONTH_SPACE_PAD: "%_m", CT.HOUR_24_SPACE_PAD: "%k",
    CT.HOUR_12_NO_PAD: "%-I", CT.AMPM_LOWER: "%P",
    CT.MILLISECOND: "%L", CT.MICROSECOND: "%6N", CT.NANOSECOND: "%N",
    CT.TZ_OFFSET_COLON: "%:z", CT.ERA_AD_BC: "[?era_ad_bc]",
})
_RB_SORTED = sorted(_RB_T2C.keys(), key=len, reverse=True)

def _rb_parse(fmt): return _strftime_parse(fmt, _RB_SORTED, _RB_T2C)
def _rb_render(tokens): return _strftime_render(tokens, _RB_C2T)


# ============================================================================
# Go system
# ============================================================================

_GO_T2C = {
    "2006": CT.YEAR_4DIGIT, "06": CT.YEAR_2DIGIT,
    "January": CT.MONTH_FULL, "Jan": CT.MONTH_ABBR,
    "01": CT.MONTH_ZERO_PAD, "1": CT.MONTH_NO_PAD,
    "02": CT.DAY_ZERO_PAD, "2": CT.DAY_NO_PAD, "_2": CT.DAY_SPACE_PAD,
    "002": CT.DAY_OF_YEAR, "__2": CT.DAY_OF_YEAR_NO_PAD,
    "Monday": CT.WEEKDAY_FULL, "Mon": CT.WEEKDAY_ABBR,
    "15": CT.HOUR_24_ZERO_PAD, "3": CT.HOUR_12_NO_PAD, "03": CT.HOUR_12_ZERO_PAD,
    "4": CT.MINUTE_NO_PAD, "04": CT.MINUTE_ZERO_PAD,
    "5": CT.SECOND_NO_PAD, "05": CT.SECOND_ZERO_PAD,
    ".000": CT.MILLISECOND, ".000000": CT.MICROSECOND, ".000000000": CT.NANOSECOND,
    "PM": CT.AMPM_UPPER, "pm": CT.AMPM_LOWER,
    "MST": CT.TZ_NAME, "-0700": CT.TZ_OFFSET, "-07:00": CT.TZ_OFFSET_COLON,
    "-07": CT.TZ_OFFSET_SHORT, "Z0700": CT.TZ_Z_OR_OFFSET, "Z07:00": CT.TZ_Z_OR_OFFSET_COLON,
}
_GO_C2T = {
    CT.YEAR_4DIGIT: "2006", CT.YEAR_2DIGIT: "06",
    CT.MONTH_ZERO_PAD: "01", CT.MONTH_NO_PAD: "1", CT.MONTH_SPACE_PAD: "01",
    CT.MONTH_ABBR: "Jan", CT.MONTH_FULL: "January",
    CT.DAY_ZERO_PAD: "02", CT.DAY_NO_PAD: "2", CT.DAY_SPACE_PAD: "_2",
    CT.DAY_OF_YEAR: "002", CT.DAY_OF_YEAR_NO_PAD: "__2",
    CT.WEEKDAY_ABBR: "Mon", CT.WEEKDAY_FULL: "Monday",
    CT.WEEKDAY_NUM_SUNDAY: "Mon", CT.WEEKDAY_NUM_MONDAY: "Mon",
    CT.HOUR_24_ZERO_PAD: "15", CT.HOUR_24_NO_PAD: "15", CT.HOUR_24_SPACE_PAD: "15",
    CT.HOUR_12_ZERO_PAD: "03", CT.HOUR_12_NO_PAD: "3",
    CT.MINUTE_ZERO_PAD: "04", CT.MINUTE_NO_PAD: "4",
    CT.SECOND_ZERO_PAD: "05", CT.SECOND_NO_PAD: "5",
    CT.MILLISECOND: ".000", CT.MICROSECOND: ".000000", CT.NANOSECOND: ".000000000",
    CT.AMPM_UPPER: "PM", CT.AMPM_LOWER: "pm",
    CT.TZ_NAME: "MST", CT.TZ_OFFSET: "-0700", CT.TZ_OFFSET_COLON: "-07:00",
    CT.TZ_OFFSET_SHORT: "-07", CT.TZ_Z_OR_OFFSET: "Z0700", CT.TZ_Z_OR_OFFSET_COLON: "Z07:00",
    CT.ISO_WEEK_NUM: "[?iso_week_num]", CT.ISO_YEAR_4DIGIT: "[?iso_year_4digit]",
    CT.LITERAL_PERCENT: "%",
}
_GO_SORTED = sorted(_GO_T2C.keys(), key=len, reverse=True)

def _go_parse(fmt):
    result = []
    i = 0
    n = len(fmt)
    while i < n:
        matched = False
        for token in _GO_SORTED:
            if fmt[i:i + len(token)] == token:
                result.append((token, _GO_T2C[token]))
                i += len(token)
                matched = True
                break
        if not matched:
            result.append((fmt[i], None))
            i += 1
    return result

def _go_render(tokens):
    parts = []
    for canonical, literal in tokens:
        if canonical is None:
            parts.append(literal)
        elif canonical in _GO_C2T:
            parts.append(_GO_C2T[canonical])
        else:
            parts.append(f"[?{canonical.value}]")
    return "".join(parts)


# ============================================================================
# JavaScript (date-fns) system
# ============================================================================

_JS_T2C = {
    "yyyy": CT.YEAR_4DIGIT, "yy": CT.YEAR_2DIGIT,
    "MMMM": CT.MONTH_FULL, "MMM": CT.MONTH_ABBR, "MM": CT.MONTH_ZERO_PAD, "M": CT.MONTH_NO_PAD,
    "dd": CT.DAY_ZERO_PAD, "d": CT.DAY_NO_PAD,
    "EEEE": CT.WEEKDAY_FULL, "EEE": CT.WEEKDAY_ABBR,
    "HH": CT.HOUR_24_ZERO_PAD, "H": CT.HOUR_24_NO_PAD,
    "hh": CT.HOUR_12_ZERO_PAD, "h": CT.HOUR_12_NO_PAD,
    "mm": CT.MINUTE_ZERO_PAD, "m": CT.MINUTE_NO_PAD,
    "ss": CT.SECOND_ZERO_PAD, "s": CT.SECOND_NO_PAD,
    "SSS": CT.MILLISECOND, "SSSSSS": CT.MICROSECOND, "SSSSSSSSS": CT.NANOSECOND,
    "a": CT.AMPM_LOWER, "aa": CT.AMPM_UPPER,
    "XXXX": CT.TZ_OFFSET, "XXX": CT.TZ_OFFSET_COLON, "XX": CT.TZ_OFFSET,
    "X": CT.TZ_OFFSET_SHORT,
    "xxxx": CT.TZ_OFFSET, "xxx": CT.TZ_OFFSET_COLON, "xx": CT.TZ_OFFSET, "x": CT.TZ_OFFSET_SHORT,
    "RRRR": CT.ISO_YEAR_4DIGIT, "RR": CT.ISO_YEAR_2DIGIT, "II": CT.ISO_WEEK_NUM,
    "e": CT.WEEKDAY_NUM_MONDAY, "DDD": CT.DAY_OF_YEAR, "D": CT.DAY_OF_YEAR_NO_PAD,
    "t": CT.UNIX_TIMESTAMP,
}
_JS_C2T = {
    CT.YEAR_4DIGIT: "yyyy", CT.YEAR_2DIGIT: "yy",
    CT.MONTH_ZERO_PAD: "MM", CT.MONTH_NO_PAD: "M", CT.MONTH_SPACE_PAD: "M",
    CT.MONTH_ABBR: "MMM", CT.MONTH_FULL: "MMMM",
    CT.DAY_ZERO_PAD: "dd", CT.DAY_NO_PAD: "d", CT.DAY_SPACE_PAD: "d",
    CT.DAY_OF_YEAR: "DDD", CT.DAY_OF_YEAR_NO_PAD: "D",
    CT.WEEKDAY_ABBR: "EEE", CT.WEEKDAY_FULL: "EEEE",
    CT.WEEKDAY_NUM_SUNDAY: "e", CT.WEEKDAY_NUM_MONDAY: "e",
    CT.HOUR_24_ZERO_PAD: "HH", CT.HOUR_24_NO_PAD: "H", CT.HOUR_24_SPACE_PAD: "H",
    CT.HOUR_12_ZERO_PAD: "hh", CT.HOUR_12_NO_PAD: "h",
    CT.MINUTE_ZERO_PAD: "mm", CT.MINUTE_NO_PAD: "m",
    CT.SECOND_ZERO_PAD: "ss", CT.SECOND_NO_PAD: "s",
    CT.MILLISECOND: "SSS", CT.MICROSECOND: "SSSSSS", CT.NANOSECOND: "SSSSSSSSS",
    CT.AMPM_UPPER: "aa", CT.AMPM_LOWER: "a",
    CT.TZ_NAME: "zzz", CT.TZ_OFFSET: "xx", CT.TZ_OFFSET_COLON: "xxx",
    CT.TZ_OFFSET_SHORT: "x", CT.TZ_Z_OR_OFFSET: "XX", CT.TZ_Z_OR_OFFSET_COLON: "XXX",
    CT.ISO_WEEK_NUM: "II", CT.ISO_YEAR_4DIGIT: "RRRR", CT.ISO_YEAR_2DIGIT: "RR",
    CT.UNIX_TIMESTAMP: "t", CT.LITERAL_PERCENT: "'%'",
    CT.WEEK_NUM_SUNDAY: "II", CT.WEEK_NUM_MONDAY: "II",
}
_JS_SORTED = sorted(_JS_T2C.keys(), key=len, reverse=True)
_JS_FORMAT_CHARS = set("yMdEHhmsSaXxRIeDtS")

def _js_parse(fmt): return _letter_parse_quoted(fmt, _JS_SORTED, _JS_T2C, "'")
def _js_render(tokens): return _letter_render(tokens, _JS_C2T, _JS_FORMAT_CHARS, "'")


# ============================================================================
# Java system
# ============================================================================

_JA_T2C = {
    "yyyy": CT.YEAR_4DIGIT, "yy": CT.YEAR_2DIGIT,
    "y": CT.YEAR_4DIGIT,  # single y = variable-width year, closest to 4-digit
    "MMMM": CT.MONTH_FULL, "MMM": CT.MONTH_ABBR, "MM": CT.MONTH_ZERO_PAD, "M": CT.MONTH_NO_PAD,
    "dd": CT.DAY_ZERO_PAD, "d": CT.DAY_NO_PAD,
    "DDD": CT.DAY_OF_YEAR, "D": CT.DAY_OF_YEAR_NO_PAD,
    "EEEE": CT.WEEKDAY_FULL, "EEE": CT.WEEKDAY_ABBR,
    "EE": CT.WEEKDAY_ABBR,  # same as EEE in practice
    "E": CT.WEEKDAY_ABBR,   # single E = abbreviated weekday
    "ee": CT.WEEKDAY_NUM_MONDAY, "e": CT.WEEKDAY_NUM_MONDAY,
    "HH": CT.HOUR_24_ZERO_PAD, "H": CT.HOUR_24_NO_PAD,
    "hh": CT.HOUR_12_ZERO_PAD, "h": CT.HOUR_12_NO_PAD,
    "mm": CT.MINUTE_ZERO_PAD, "m": CT.MINUTE_NO_PAD,
    "ss": CT.SECOND_ZERO_PAD, "s": CT.SECOND_NO_PAD,
    "SSSSSSSSS": CT.NANOSECOND, "SSSSSS": CT.MICROSECOND, "SSS": CT.MILLISECOND,
    "SS": CT.MILLISECOND,   # 2-digit fraction
    "S": CT.MILLISECOND,    # single S = fraction, closest to ms
    "a": CT.AMPM_UPPER,
    "z": CT.TZ_NAME, "zzzz": CT.TZ_NAME, "zzz": CT.TZ_NAME, "zz": CT.TZ_NAME,
    "Z": CT.TZ_OFFSET, "ZZ": CT.TZ_OFFSET, "ZZZ": CT.TZ_OFFSET,
    "ZZZZZ": CT.TZ_OFFSET_COLON,
    "XXX": CT.TZ_Z_OR_OFFSET_COLON, "XX": CT.TZ_Z_OR_OFFSET, "X": CT.TZ_OFFSET_SHORT,
    "YYYY": CT.ISO_YEAR_4DIGIT, "YY": CT.ISO_YEAR_2DIGIT,
    "ww": CT.ISO_WEEK_NUM, "w": CT.ISO_WEEK_NUM,
    "G": CT.ERA_AD_BC, "GG": CT.ERA_AD_BC, "GGG": CT.ERA_AD_BC, "GGGG": CT.ERA_AD_BC,
}
_JA_C2T = {
    CT.YEAR_4DIGIT: "yyyy", CT.YEAR_2DIGIT: "yy",
    CT.MONTH_ZERO_PAD: "MM", CT.MONTH_NO_PAD: "M", CT.MONTH_SPACE_PAD: "M",
    CT.MONTH_ABBR: "MMM", CT.MONTH_FULL: "MMMM",
    CT.DAY_ZERO_PAD: "dd", CT.DAY_NO_PAD: "d", CT.DAY_SPACE_PAD: "d",
    CT.DAY_OF_YEAR: "DDD", CT.DAY_OF_YEAR_NO_PAD: "D",
    CT.WEEKDAY_ABBR: "EEE", CT.WEEKDAY_FULL: "EEEE",
    CT.WEEKDAY_NUM_SUNDAY: "e", CT.WEEKDAY_NUM_MONDAY: "ee",
    CT.HOUR_24_ZERO_PAD: "HH", CT.HOUR_24_NO_PAD: "H", CT.HOUR_24_SPACE_PAD: "H",
    CT.HOUR_12_ZERO_PAD: "hh", CT.HOUR_12_NO_PAD: "h",
    CT.MINUTE_ZERO_PAD: "mm", CT.MINUTE_NO_PAD: "m",
    CT.SECOND_ZERO_PAD: "ss", CT.SECOND_NO_PAD: "s",
    CT.MILLISECOND: "SSS", CT.MICROSECOND: "SSSSSS", CT.NANOSECOND: "SSSSSSSSS",
    CT.AMPM_UPPER: "a", CT.AMPM_LOWER: "a",
    CT.TZ_NAME: "z", CT.TZ_OFFSET: "Z", CT.TZ_OFFSET_COLON: "ZZZZZ",
    CT.TZ_OFFSET_SHORT: "X", CT.TZ_Z_OR_OFFSET: "XX", CT.TZ_Z_OR_OFFSET_COLON: "XXX",
    CT.ISO_WEEK_NUM: "ww", CT.ISO_YEAR_4DIGIT: "YYYY", CT.ISO_YEAR_2DIGIT: "YY",
    CT.UNIX_TIMESTAMP: "[?unix_timestamp]", CT.ERA_AD_BC: "G",
    CT.CENTURY: "[?century]", CT.LITERAL_PERCENT: "'%'",
    CT.WEEK_NUM_SUNDAY: "ww", CT.WEEK_NUM_MONDAY: "ww",
}
_JA_SORTED = sorted(_JA_T2C.keys(), key=len, reverse=True)
_JA_PATTERN_LETTERS = set("GyYMwWDdFEuaHkKhmsSzZXn")

def _ja_parse(fmt): return _letter_parse_quoted(fmt, _JA_SORTED, _JA_T2C, "'")
def _ja_render(tokens): return _letter_render(tokens, _JA_C2T, _JA_PATTERN_LETTERS, "'")


# ============================================================================
# C# system
# ============================================================================

_CS_T2C = {
    "yyyy": CT.YEAR_4DIGIT, "yy": CT.YEAR_2DIGIT,
    "MMMM": CT.MONTH_FULL, "MMM": CT.MONTH_ABBR, "MM": CT.MONTH_ZERO_PAD, "M": CT.MONTH_NO_PAD,
    "dddd": CT.WEEKDAY_FULL, "ddd": CT.WEEKDAY_ABBR, "dd": CT.DAY_ZERO_PAD, "d": CT.DAY_NO_PAD,
    "HH": CT.HOUR_24_ZERO_PAD, "H": CT.HOUR_24_NO_PAD,
    "hh": CT.HOUR_12_ZERO_PAD, "h": CT.HOUR_12_NO_PAD,
    "mm": CT.MINUTE_ZERO_PAD, "m": CT.MINUTE_NO_PAD,
    "ss": CT.SECOND_ZERO_PAD, "s": CT.SECOND_NO_PAD,
    "fff": CT.MILLISECOND, "ffffff": CT.MICROSECOND, "fffffff": CT.NANOSECOND,
    "tt": CT.AMPM_UPPER, "t": CT.AMPM_UPPER,
    "zzz": CT.TZ_OFFSET_COLON, "zz": CT.TZ_OFFSET_SHORT, "z": CT.TZ_OFFSET_SHORT,
    "K": CT.TZ_Z_OR_OFFSET_COLON,
    "gg": CT.ERA_AD_BC, "g": CT.ERA_AD_BC,
}
_CS_C2T = {
    CT.YEAR_4DIGIT: "yyyy", CT.YEAR_2DIGIT: "yy",
    CT.MONTH_ZERO_PAD: "MM", CT.MONTH_NO_PAD: "M", CT.MONTH_SPACE_PAD: "M",
    CT.MONTH_ABBR: "MMM", CT.MONTH_FULL: "MMMM",
    CT.DAY_ZERO_PAD: "dd", CT.DAY_NO_PAD: "d", CT.DAY_SPACE_PAD: "d",
    CT.WEEKDAY_ABBR: "ddd", CT.WEEKDAY_FULL: "dddd",
    CT.WEEKDAY_NUM_SUNDAY: "[?weekday_num_sun]", CT.WEEKDAY_NUM_MONDAY: "[?weekday_num_mon]",
    CT.DAY_OF_YEAR: "[?day_of_year]", CT.DAY_OF_YEAR_NO_PAD: "[?day_of_year_no_pad]",
    CT.HOUR_24_ZERO_PAD: "HH", CT.HOUR_24_NO_PAD: "H", CT.HOUR_24_SPACE_PAD: "H",
    CT.HOUR_12_ZERO_PAD: "hh", CT.HOUR_12_NO_PAD: "h",
    CT.MINUTE_ZERO_PAD: "mm", CT.MINUTE_NO_PAD: "m",
    CT.SECOND_ZERO_PAD: "ss", CT.SECOND_NO_PAD: "s",
    CT.MILLISECOND: "fff", CT.MICROSECOND: "ffffff", CT.NANOSECOND: "fffffff",
    CT.AMPM_UPPER: "tt", CT.AMPM_LOWER: "tt",
    CT.TZ_NAME: "zzz", CT.TZ_OFFSET: "zzz", CT.TZ_OFFSET_COLON: "zzz",
    CT.TZ_OFFSET_SHORT: "zz", CT.TZ_Z_OR_OFFSET: "K", CT.TZ_Z_OR_OFFSET_COLON: "K",
    CT.ISO_WEEK_NUM: "[?iso_week_num]", CT.ISO_YEAR_4DIGIT: "[?iso_year_4digit]",
    CT.UNIX_TIMESTAMP: "[?unix_timestamp]", CT.ERA_AD_BC: "gg",
    CT.CENTURY: "[?century]", CT.LITERAL_PERCENT: "%",
}
_CS_SORTED = sorted(_CS_T2C.keys(), key=len, reverse=True)
_CS_FORMAT_CHARS = set("yMdHhmsfFtgzK")

def _cs_parse(fmt):
    result = []
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] == "\\" and i + 1 < n:
            result.append((fmt[i:i+2], None))
            i += 2
            continue
        if fmt[i] in ("'", '"'):
            quote = fmt[i]
            j = i + 1
            while j < n and fmt[j] != quote:
                j += 1
            if j < n:
                j += 1
            result.append((fmt[i:j], None))
            i = j
            continue
        matched = False
        for token in _CS_SORTED:
            if fmt[i:i + len(token)] == token:
                result.append((token, _CS_T2C[token]))
                i += len(token)
                matched = True
                break
        if not matched:
            result.append((fmt[i], None))
            i += 1
    return result

def _cs_render(tokens): return _letter_render(tokens, _CS_C2T, _CS_FORMAT_CHARS, "'")


# ============================================================================
# moment.js system
# ============================================================================

_MO_T2C = {
    "YYYY": CT.YEAR_4DIGIT, "YY": CT.YEAR_2DIGIT,
    "MMMM": CT.MONTH_FULL, "MMM": CT.MONTH_ABBR, "MM": CT.MONTH_ZERO_PAD, "M": CT.MONTH_NO_PAD,
    "DD": CT.DAY_ZERO_PAD, "D": CT.DAY_NO_PAD,
    "DDDD": CT.DAY_OF_YEAR, "DDD": CT.DAY_OF_YEAR_NO_PAD,
    "dddd": CT.WEEKDAY_FULL, "ddd": CT.WEEKDAY_ABBR, "dd": CT.WEEKDAY_ABBR,
    "d": CT.WEEKDAY_NUM_SUNDAY, "e": CT.WEEKDAY_NUM_SUNDAY, "E": CT.WEEKDAY_NUM_MONDAY,
    "HH": CT.HOUR_24_ZERO_PAD, "H": CT.HOUR_24_NO_PAD,
    "hh": CT.HOUR_12_ZERO_PAD, "h": CT.HOUR_12_NO_PAD,
    "mm": CT.MINUTE_ZERO_PAD, "m": CT.MINUTE_NO_PAD,
    "ss": CT.SECOND_ZERO_PAD, "s": CT.SECOND_NO_PAD,
    "SSS": CT.MILLISECOND, "SSSSSS": CT.MICROSECOND, "SSSSSSSSS": CT.NANOSECOND,
    "A": CT.AMPM_UPPER, "a": CT.AMPM_LOWER,
    "ZZ": CT.TZ_OFFSET, "Z": CT.TZ_OFFSET_COLON,
    "z": CT.TZ_NAME, "zz": CT.TZ_NAME,
    "gggg": CT.ISO_YEAR_4DIGIT, "gg": CT.ISO_YEAR_2DIGIT,
    "ww": CT.ISO_WEEK_NUM, "w": CT.ISO_WEEK_NUM, "X": CT.UNIX_TIMESTAMP,
}
_MO_C2T = {
    CT.YEAR_4DIGIT: "YYYY", CT.YEAR_2DIGIT: "YY",
    CT.MONTH_ZERO_PAD: "MM", CT.MONTH_NO_PAD: "M", CT.MONTH_SPACE_PAD: "M",
    CT.MONTH_ABBR: "MMM", CT.MONTH_FULL: "MMMM",
    CT.DAY_ZERO_PAD: "DD", CT.DAY_NO_PAD: "D", CT.DAY_SPACE_PAD: "D",
    CT.DAY_OF_YEAR: "DDDD", CT.DAY_OF_YEAR_NO_PAD: "DDD",
    CT.WEEKDAY_ABBR: "ddd", CT.WEEKDAY_FULL: "dddd",
    CT.WEEKDAY_NUM_SUNDAY: "d", CT.WEEKDAY_NUM_MONDAY: "E",
    CT.HOUR_24_ZERO_PAD: "HH", CT.HOUR_24_NO_PAD: "H", CT.HOUR_24_SPACE_PAD: "H",
    CT.HOUR_12_ZERO_PAD: "hh", CT.HOUR_12_NO_PAD: "h",
    CT.MINUTE_ZERO_PAD: "mm", CT.MINUTE_NO_PAD: "m",
    CT.SECOND_ZERO_PAD: "ss", CT.SECOND_NO_PAD: "s",
    CT.MILLISECOND: "SSS", CT.MICROSECOND: "SSSSSS", CT.NANOSECOND: "SSSSSSSSS",
    CT.AMPM_UPPER: "A", CT.AMPM_LOWER: "a",
    CT.TZ_NAME: "z", CT.TZ_OFFSET: "ZZ", CT.TZ_OFFSET_COLON: "Z",
    CT.TZ_OFFSET_SHORT: "ZZ", CT.TZ_Z_OR_OFFSET: "ZZ", CT.TZ_Z_OR_OFFSET_COLON: "Z",
    CT.ISO_WEEK_NUM: "ww", CT.ISO_YEAR_4DIGIT: "gggg", CT.ISO_YEAR_2DIGIT: "gg",
    CT.UNIX_TIMESTAMP: "X", CT.ERA_AD_BC: "[?era_ad_bc]",
    CT.CENTURY: "[?century]", CT.LITERAL_PERCENT: "%",
    CT.WEEK_NUM_SUNDAY: "ww", CT.WEEK_NUM_MONDAY: "ww",
}
_MO_SORTED = sorted(_MO_T2C.keys(), key=len, reverse=True)
_MO_FORMAT_CHARS = set("YMDdEeHhmmssSAaZzgwX")

def _mo_parse(fmt):
    result = []
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] == "[":
            j = i + 1
            while j < n and fmt[j] != "]":
                j += 1
            if j < n:
                j += 1
            result.append((fmt[i:j], None))
            i = j
            continue
        matched = False
        for token in _MO_SORTED:
            if fmt[i:i + len(token)] == token:
                result.append((token, _MO_T2C[token]))
                i += len(token)
                matched = True
                break
        if not matched:
            result.append((fmt[i], None))
            i += 1
    return result

def _mo_render(tokens): return _letter_render(tokens, _MO_C2T, _MO_FORMAT_CHARS, "[")


# ============================================================================
# System registry
# ============================================================================

SYSTEMS = {
    "python": {"parse": _py_parse, "render": _py_render, "CANONICAL_TO_TOKEN": _PY_C2T, "TOKEN_TO_CANONICAL": _PY_T2C, "SYSTEM_NAME": "Python (strftime)"},
    "javascript": {"parse": _js_parse, "render": _js_render, "CANONICAL_TO_TOKEN": _JS_C2T, "TOKEN_TO_CANONICAL": _JS_T2C, "SYSTEM_NAME": "JavaScript (date-fns)"},
    "go": {"parse": _go_parse, "render": _go_render, "CANONICAL_TO_TOKEN": _GO_C2T, "TOKEN_TO_CANONICAL": _GO_T2C, "SYSTEM_NAME": "Go (time.Format)"},
    "java": {"parse": _ja_parse, "render": _ja_render, "CANONICAL_TO_TOKEN": _JA_C2T, "TOKEN_TO_CANONICAL": _JA_T2C, "SYSTEM_NAME": "Java (SimpleDateFormat)"},
    "csharp": {"parse": _cs_parse, "render": _cs_render, "CANONICAL_TO_TOKEN": _CS_C2T, "TOKEN_TO_CANONICAL": _CS_T2C, "SYSTEM_NAME": "C# (.NET)"},
    "ruby": {"parse": _rb_parse, "render": _rb_render, "CANONICAL_TO_TOKEN": _RB_C2T, "TOKEN_TO_CANONICAL": _RB_T2C, "SYSTEM_NAME": "Ruby (strftime)"},
    "momentjs": {"parse": _mo_parse, "render": _mo_render, "CANONICAL_TO_TOKEN": _MO_C2T, "TOKEN_TO_CANONICAL": _MO_T2C, "SYSTEM_NAME": "moment.js"},
}

SYSTEM_ALIASES = {
    "py": "python", "strftime": "python",
    "js": "javascript", "date-fns": "javascript", "datefns": "javascript",
    "golang": "go",
    "simpledateformat": "java", "datetimeformatter": "java",
    "c#": "csharp", ".net": "csharp", "dotnet": "csharp",
    "moment": "momentjs", "moment.js": "momentjs", "rb": "ruby",
}


def resolve_system(name: str) -> dict:
    lower = name.lower().strip()
    if lower in SYSTEMS:
        return SYSTEMS[lower]
    if lower in SYSTEM_ALIASES:
        return SYSTEMS[SYSTEM_ALIASES[lower]]
    raise ValueError(f"Unknown system: {name!r}. Supported: {', '.join(sorted(SYSTEMS.keys()))}")


def resolve_system_name(name: str) -> str:
    lower = name.lower().strip()
    if lower in SYSTEMS:
        return lower
    if lower in SYSTEM_ALIASES:
        return SYSTEM_ALIASES[lower]
    raise ValueError(f"Unknown system: {name!r}. Supported: {', '.join(sorted(SYSTEMS.keys()))}")


# ============================================================================
# Converter
# ============================================================================


def _extract_literal(raw: str, system_name: str) -> str:
    name = resolve_system_name(system_name)
    if name in ("java",):
        if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
            inner = raw[1:-1]
            return inner.replace("''", "'")
        return raw
    if name in ("javascript",):
        if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
            inner = raw[1:-1]
            return inner.replace("''", "'")
        return raw
    if name in ("csharp",):
        if raw.startswith("\\") and len(raw) == 2:
            return raw[1]
        if (raw.startswith("'") and raw.endswith("'")) or \
           (raw.startswith('"') and raw.endswith('"')):
            if len(raw) >= 2:
                return raw[1:-1]
        return raw
    if name in ("momentjs",):
        if raw.startswith("[") and raw.endswith("]") and len(raw) >= 2:
            return raw[1:-1]
        return raw
    return raw


def convert(format_string: str, from_system: str, to_system: str) -> str:
    """Convert a format string from one system to another.

    Args:
        format_string: The format string in the source system's syntax
        from_system: Source system name (e.g., "python", "go", "java")
        to_system: Target system name

    Returns:
        The equivalent format string in the target system's syntax
    """
    source = resolve_system(from_system)
    target = resolve_system(to_system)

    parsed = source["parse"](format_string)

    render_tokens = []
    for raw, canonical in parsed:
        if canonical is None:
            literal = _extract_literal(raw, from_system)
            render_tokens.append((None, literal))
        else:
            render_tokens.append((canonical, raw))

    return target["render"](render_tokens)


def get_unsupported_tokens(
    format_string: str, from_system: str, to_system: str
) -> list[tuple[str, CanonicalToken]]:
    """Find tokens in the source format that have no equivalent in the target."""
    source = resolve_system(from_system)
    target = resolve_system(to_system)
    parsed = source["parse"](format_string)
    unsupported = []
    for raw, canonical in parsed:
        if canonical is not None:
            target_token = target["CANONICAL_TO_TOKEN"].get(canonical, "")
            if target_token.startswith("[?"):
                unsupported.append((raw, canonical))
    return unsupported


# ============================================================================
# CLI
# ============================================================================


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="datetime-translate",
        description="Translate date/time format strings between systems.",
    )
    parser.add_argument("format", help="Format string to translate")
    parser.add_argument("--from", dest="from_sys", required=True, help="Source system")
    parser.add_argument("--to", dest="to_sys", required=True, help="Target system")

    args = parser.parse_args()

    try:
        result = convert(args.format, args.from_sys, args.to_sys)
        print(f"Source ({args.from_sys}): {args.format}")
        print(f"Target ({args.to_sys}): {result}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
