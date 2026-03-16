"""
Tests for Unicode Inspector.

These tests ARE the spec — character inspection, invisible detection,
normalization, and confusable detection.
"""

from __future__ import annotations

import unicodedata
import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from inspector import (
    CharInfo, CATEGORY_NAMES, get_codepoint_str, get_block, get_script,
    get_utf8_bytes, get_utf16_bytes, get_utf32_bytes,
    inspect_char, inspect_string, format_char_info, format_string_inspection,
    search_by_name, format_search_results,
    INVISIBLE_CHARS, InvisibleChar, is_invisible, detect_invisible,
    format_invisible_report,
    VALID_FORMS, NormalizationResult, normalize, normalize_all_forms,
    is_normalized, format_normalization_result, format_all_forms,
    CONFUSABLE_MAP, ConfusableMatch, LookalikeInfo,
    get_confusables, scan_confusables, detect_mixed_scripts,
    format_confusable_report, format_mixed_script_report,
)


# ═══════════════════════════════════════════════════════════════════
# 1. Character Inspection
# ═══════════════════════════════════════════════════════════════════

class TestGetCodepointStr:
    def test_ascii_a(self):
        assert get_codepoint_str(0x0041) == "U+0041"

    def test_supplementary(self):
        assert get_codepoint_str(0x1F600) == "U+01F600"

    def test_max_unicode(self):
        assert get_codepoint_str(0x10FFFF) == "U+10FFFF"


class TestGetBlock:
    def test_basic_latin(self):
        assert get_block(0x0041) == "Basic Latin"

    def test_cyrillic(self):
        assert get_block(0x0410) == "Cyrillic"

    def test_greek(self):
        assert get_block(0x0391) == "Greek and Coptic"

    def test_cjk(self):
        assert get_block(0x4E00) == "CJK Unified Ideographs"

    def test_hangul(self):
        assert get_block(0xAC00) == "Hangul Syllables"

    def test_hiragana(self):
        assert get_block(0x3042) == "Hiragana"

    def test_emoticons(self):
        assert get_block(0x1F600) == "Emoticons"

    def test_unknown_block(self):
        assert get_block(0x0870) == "Unknown"


class TestGetScript:
    def test_latin(self):
        assert get_script(0x0041) == "Latin"

    def test_cyrillic(self):
        assert get_script(0x0410) == "Cyrillic"

    def test_greek(self):
        assert get_script(0x0391) == "Greek"

    def test_han(self):
        assert get_script(0x4E00) == "Han"

    def test_devanagari(self):
        assert get_script(0x0905) == "Devanagari"

    def test_common_for_punctuation(self):
        assert get_script(0x2000) == "Common"


class TestUTFBytes:
    def test_utf8_ascii(self):
        assert get_utf8_bytes("A") == b"\x41"

    def test_utf8_two_byte(self):
        assert get_utf8_bytes("\u00e9") == b"\xc3\xa9"

    def test_utf8_three_byte(self):
        assert get_utf8_bytes("\u20ac") == b"\xe2\x82\xac"

    def test_utf8_four_byte(self):
        assert get_utf8_bytes("\U0001f600") == b"\xf0\x9f\x98\x80"

    def test_utf16_ascii(self):
        assert get_utf16_bytes("A") == b"\x00\x41"

    def test_utf16_supplementary(self):
        assert get_utf16_bytes("\U0001f600") == b"\xd8\x3d\xde\x00"

    def test_utf32_ascii(self):
        assert get_utf32_bytes("A") == b"\x00\x00\x00\x41"

    def test_utf32_supplementary(self):
        assert get_utf32_bytes("\U0001f600") == b"\x00\x01\xf6\x00"


class TestInspectChar:
    def test_latin_a(self):
        info = inspect_char("A")
        assert info.codepoint == 0x41
        assert info.name == "LATIN CAPITAL LETTER A"
        assert info.category == "Lu"
        assert info.block == "Basic Latin"
        assert info.script == "Latin"

    def test_e_acute(self):
        info = inspect_char("\u00e9")
        assert info.name == "LATIN SMALL LETTER E WITH ACUTE"
        assert info.block == "Latin-1 Supplement"

    def test_combining_accent(self):
        info = inspect_char("\u0301")
        assert info.combining_class == 230

    def test_cyrillic_a(self):
        info = inspect_char("\u0430")
        assert info.script == "Cyrillic"

    def test_emoji(self):
        info = inspect_char("\U0001f600")
        assert info.name == "GRINNING FACE"

    def test_control_char(self):
        info = inspect_char("\x00")
        assert info.category == "Cc"
        assert info.is_printable is False

    def test_mirrored_parenthesis(self):
        assert inspect_char("(").mirrored is True
        assert inspect_char(")").mirrored is True

    def test_decomposition(self):
        assert inspect_char("\u00e9").decomposition != ""
        assert inspect_char("A").decomposition == ""

    def test_east_asian_width(self):
        assert inspect_char("A").east_asian_width == "Na"
        assert inspect_char("\u4e00").east_asian_width == "W"

    def test_error_on_empty(self):
        with pytest.raises(ValueError, match="Expected a single character"):
            inspect_char("")

    def test_error_on_multiple(self):
        with pytest.raises(ValueError, match="Expected a single character"):
            inspect_char("AB")


class TestInspectString:
    def test_empty(self):
        assert inspect_string("") == []

    def test_hello(self):
        result = inspect_string("hello")
        assert len(result) == 5
        assert result[0].name == "LATIN SMALL LETTER H"

    def test_mixed_scripts(self):
        result = inspect_string("A\u03b1")
        assert result[0].script == "Latin"
        assert result[1].script == "Greek"


class TestFormatCharInfo:
    def test_printable_included(self):
        output = format_char_info(inspect_char("A"))
        assert "A" in output and "U+0041" in output
        assert "UTF-8" in output and "UTF-16" in output

    def test_non_printable_marker(self):
        assert "(non-printable)" in format_char_info(inspect_char("\x00"))


class TestSearchByName:
    def test_search_latin_a(self):
        results = search_by_name("LATIN SMALL LETTER A", limit=5)
        names = [r.name for r in results]
        assert "LATIN SMALL LETTER A" in names

    def test_no_results(self):
        assert search_by_name("XYZZY NONEXISTENT") == []

    def test_limit(self):
        assert len(search_by_name("LATIN", limit=3)) <= 3


class TestCategoryNames:
    def test_all_major_categories(self):
        for cat in ["Lu", "Ll", "Nd", "Po", "Sm", "Sc", "Cc", "Cf", "Zs"]:
            assert cat in CATEGORY_NAMES


# ═══════════════════════════════════════════════════════════════════
# 2. Invisible Character Detection
# ═══════════════════════════════════════════════════════════════════

class TestIsInvisible:
    @pytest.mark.parametrize("char", [
        "\u200B", "\u200C", "\u200D",  # zero-width
        "\u200E", "\u200F",            # directional marks
        "\u202A", "\u202E",            # directional overrides
        "\u2066", "\u2069",            # directional isolates
        "\u00AD",                       # soft hyphen
        "\uFEFF",                       # BOM
        "\x00", "\x07", "\x08", "\x1B", "\x7F",  # C0 controls
        "\x80", "\x85", "\x9F",        # C1 controls
        "\u2060",                       # word joiner
        "\u2061", "\u2062", "\u2063",   # invisible math
        "\u2028", "\u2029",            # line/paragraph sep
        "\u180E",                       # Mongolian vowel sep
        "\u061C",                       # Arabic letter mark
        "\uFE00", "\uFE0F",           # variation selectors
        "\uFFF9", "\uFFFA", "\uFFFB",  # interlinear annotations
        "\u00A0", "\u2002", "\u2003", "\u2009", "\u200A", "\u3000",  # special spaces
    ])
    def test_invisible_chars(self, char):
        assert is_invisible(char) is True

    @pytest.mark.parametrize("char", [
        " ", "\t", "\n", "\r",  # common whitespace
        "A", "1", ".", "-",     # visible chars
        "\u00e9", "\u4e00", "\U0001f600",  # printable non-ASCII
    ])
    def test_not_invisible(self, char):
        assert is_invisible(char) is False


class TestDetectInvisible:
    def test_clean_string(self):
        assert len(detect_invisible("hello world")) == 0

    def test_single_zws(self):
        result = detect_invisible("hello\u200Bworld")
        assert len(result) == 1
        assert result[0].codepoint == 0x200B
        assert result[0].position == 5

    def test_multiple_invisible(self):
        result = detect_invisible("\u200Bhello\u200Cworld\u200D")
        assert len(result) == 3

    def test_positions_correct(self):
        result = detect_invisible("a\u200Bb\u200Cc")
        assert result[0].position == 1 and result[1].position == 3

    def test_bom_at_start(self):
        result = detect_invisible("\uFEFFhello")
        assert len(result) == 1 and "Byte Order Mark" in result[0].description

    def test_invisible_char_fields(self):
        inv = detect_invisible("\u200B")[0]
        assert inv.char == "\u200B" and inv.codepoint == 0x200B
        assert inv.codepoint_str == "U+200B" and inv.category == "Cf"


class TestFormatInvisibleReport:
    def test_no_invisible(self):
        report = format_invisible_report("hello", [])
        assert "No invisible characters found" in report

    def test_with_invisible(self):
        text = "hello\u200Bworld"
        report = format_invisible_report(text, detect_invisible(text))
        assert "Found 1 invisible character" in report
        assert "U+200B" in report

    def test_annotated_string(self):
        text = "a\u200Bb"
        report = format_invisible_report(text, detect_invisible(text))
        assert "[U+200B]" in report


class TestInvisibleCharsTable:
    def test_key_entries(self):
        for cp in [0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x00AD, 0xFEFF, 0x0000]:
            assert cp in INVISIBLE_CHARS

    def test_all_have_descriptions(self):
        for cp, desc in INVISIBLE_CHARS.items():
            assert isinstance(desc, str) and len(desc) > 0


# ═══════════════════════════════════════════════════════════════════
# 3. Normalization
# ═══════════════════════════════════════════════════════════════════

class TestNormalize:
    def test_nfc_e_acute(self):
        result = normalize("e\u0301", "NFC")
        assert result.normalized == "\u00e9" and result.changed is True

    def test_nfd_e_acute(self):
        result = normalize("\u00e9", "NFD")
        assert result.normalized == "e\u0301" and result.changed is True

    def test_nfkc_fi_ligature(self):
        result = normalize("\uFB01", "NFKC")
        assert result.normalized == "fi"

    def test_already_normalized(self):
        assert normalize("\u00e9", "NFC").changed is False

    def test_ascii_unchanged(self):
        assert normalize("hello", "NFC").changed is False

    def test_empty_string(self):
        r = normalize("", "NFC")
        assert r.changed is False and r.original_length == 0

    def test_invalid_form(self):
        with pytest.raises(ValueError, match="Invalid normalization form"):
            normalize("hello", "INVALID")

    def test_form_case_insensitive(self):
        assert normalize("e\u0301", "nfc").form == "NFC"

    def test_length_changes(self):
        r = normalize("e\u0301", "NFC")
        assert r.original_length == 2 and r.normalized_length == 1

    def test_codepoints_tracked(self):
        r = normalize("e\u0301", "NFC")
        assert r.original_codepoints == ["U+0065", "U+0301"]
        assert r.normalized_codepoints == ["U+00E9"]


class TestSpecificNormalizations:
    def test_angstrom_nfc(self):
        assert normalize("\u212B", "NFC").normalized == "\u00C5"

    def test_ohm_nfc(self):
        assert normalize("\u2126", "NFC").normalized == "\u03A9"

    def test_superscript_2_nfkc(self):
        assert normalize("\u00B2", "NFKC").normalized == "2"

    def test_fullwidth_a_nfkc(self):
        assert normalize("\uFF21", "NFKC").normalized == "A"

    def test_cafe_nfc(self):
        assert normalize("cafe\u0301", "NFC").normalized == "caf\u00e9"

    def test_cafe_nfd(self):
        assert normalize("caf\u00e9", "NFD").normalized == "cafe\u0301"


class TestHangulNormalization:
    def test_hangul_nfd(self):
        assert normalize("\uAC00", "NFD").changed is True

    def test_hangul_round_trip(self):
        nfd = normalize("\uAC00", "NFD").normalized
        assert normalize(nfd, "NFC").normalized == "\uAC00"


class TestNormalizeAllForms:
    def test_returns_all_forms(self):
        assert set(normalize_all_forms("e\u0301").keys()) == {"NFC", "NFD", "NFKC", "NFKD"}


class TestIsNormalized:
    def test_precomposed_is_nfc(self):
        assert is_normalized("\u00e9", "NFC") is True

    def test_decomposed_is_not_nfc(self):
        assert is_normalized("e\u0301", "NFC") is False

    def test_ascii_is_all_forms(self):
        for form in VALID_FORMS:
            assert is_normalized("hello", form) is True


class TestFormatNormalization:
    def test_unchanged(self):
        assert "already in NFC form" in format_normalization_result(normalize("hello", "NFC"))

    def test_changed(self):
        output = format_normalization_result(normalize("e\u0301", "NFC"))
        assert "Original" in output and "Normalized" in output

    def test_length_change_fewer(self):
        assert "fewer" in format_normalization_result(normalize("e\u0301", "NFC"))

    def test_length_change_more(self):
        assert "more" in format_normalization_result(normalize("\u00e9", "NFD"))

    def test_all_forms_output(self):
        output = format_all_forms(normalize_all_forms("e\u0301"))
        for form in VALID_FORMS:
            assert form in output


# ═══════════════════════════════════════════════════════════════════
# 4. Confusables
# ═══════════════════════════════════════════════════════════════════

class TestGetConfusables:
    def test_latin_a_has_cyrillic(self):
        match = get_confusables("a")
        assert match is not None
        assert "Cyrillic" in [la.script for la in match.lookalikes]

    def test_latin_o_has_both(self):
        match = get_confusables("o")
        scripts = [la.script for la in match.lookalikes]
        assert "Cyrillic" in scripts and "Greek" in scripts

    def test_latin_A_has_cyrillic_and_greek(self):
        match = get_confusables("A")
        cps = [la.codepoint for la in match.lookalikes]
        assert 0x0410 in cps and 0x0391 in cps

    def test_cyrillic_a_has_latin(self):
        match = get_confusables("\u0430")
        assert 0x0061 in [la.codepoint for la in match.lookalikes]

    def test_greek_alpha_has_latin(self):
        match = get_confusables("\u0391")
        assert 0x0041 in [la.codepoint for la in match.lookalikes]

    def test_no_confusable_for_z(self):
        assert get_confusables("z") is None

    def test_no_confusable_for_cjk(self):
        assert get_confusables("\u4e00") is None

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            get_confusables("")

    def test_match_fields(self):
        match = get_confusables("a")
        assert match.char == "a" and match.codepoint == 0x0061
        assert match.script == "Latin"


class TestScanConfusables:
    def test_deduplicates(self):
        result = scan_confusables("aaa")
        assert [m.char for m in result].count("a") == 1

    def test_empty_string(self):
        assert scan_confusables("") == []

    def test_mixed_script_attack(self):
        assert len(scan_confusables("p\u0430ypal")) >= 1


class TestDetectMixedScripts:
    def test_pure_latin(self):
        result = detect_mixed_scripts("hello world")
        assert len(result) == 1 and "Latin" in result

    def test_mixed_latin_cyrillic(self):
        result = detect_mixed_scripts("h\u0435llo")
        assert len(result) == 2
        assert "Latin" in result and "Cyrillic" in result

    def test_only_punctuation(self):
        assert len(detect_mixed_scripts("!@#$%")) == 0

    def test_empty(self):
        assert len(detect_mixed_scripts("")) == 0


class TestFormatConfusableReport:
    def test_no_confusables(self):
        assert "No confusable characters" in format_confusable_report([])

    def test_shows_lookalikes(self):
        match = get_confusables("a")
        assert "~" in format_confusable_report([match])


class TestFormatMixedScriptReport:
    def test_single_script(self):
        assert "Single script" in format_mixed_script_report({"Latin": ["h", "e"]})

    def test_mixed_scripts_warning(self):
        output = format_mixed_script_report({"Latin": ["h"], "Cyrillic": ["\u0435"]})
        assert "WARNING" in output and "homoglyph" in output.lower()

    def test_no_scripts(self):
        assert "No script-bearing" in format_mixed_script_report({})


class TestConfusableMapCompleteness:
    def test_latin_lowercase_coverage(self):
        for char in "aceiopsx":
            assert ord(char) in CONFUSABLE_MAP

    def test_bidirectional_mappings(self):
        assert 0x0061 in CONFUSABLE_MAP and 0x0430 in CONFUSABLE_MAP
        assert 0x0430 in [la[0] for la in CONFUSABLE_MAP[0x0061]]
        assert 0x0061 in [la[0] for la in CONFUSABLE_MAP[0x0430]]

    def test_all_entries_valid(self):
        for cp, lookalikes in CONFUSABLE_MAP.items():
            assert 0 <= cp <= 0x10FFFF
            chr(cp)
            for la_cp, script in lookalikes:
                assert 0 <= la_cp <= 0x10FFFF
                chr(la_cp)
