"""
Tests for Encoding Detective.

These tests ARE the spec — BOM detection, UTF-8 validation, encoding
detection, mojibake detection/repair, and encoding conversion.
"""

import struct
import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from detective import (
    BOMInfo, detect_bom, strip_bom, get_bom_for_encoding, format_bom_report,
    EncodingResult, DetectionReport, detect_encoding, detect_encoding_from_file,
    ConversionResult, convert_bytes, convert_file, format_conversion_report,
    _normalize_encoding,
    MojibakeResult, detect_mojibake, detect_mojibake_bytes, fix_mojibake,
    _score_mojibake_likelihood, format_mojibake_report,
)


# ═══════════════════════════════════════════════════════════════════
# 1. BOM Detection
# ═══════════════════════════════════════════════════════════════════

class TestDetectBom:
    def test_utf8_bom(self):
        result = detect_bom(b"\xef\xbb\xbfHello")
        assert result is not None
        assert result.encoding == "utf-8-sig"
        assert result.bom_bytes == b"\xef\xbb\xbf"
        assert result.bom_length == 3

    def test_utf16_le_bom(self):
        result = detect_bom(b"\xff\xfeH\x00e\x00")
        assert result is not None
        assert result.encoding == "utf-16-le"
        assert result.bom_length == 2

    def test_utf16_be_bom(self):
        result = detect_bom(b"\xfe\xff\x00H\x00e")
        assert result is not None
        assert result.encoding == "utf-16-be"

    def test_utf32_le_bom(self):
        result = detect_bom(b"\xff\xfe\x00\x00H\x00\x00\x00")
        assert result is not None
        assert result.encoding == "utf-32-le"
        assert result.bom_length == 4

    def test_utf32_be_bom(self):
        result = detect_bom(b"\x00\x00\xfe\xff\x00\x00\x00H")
        assert result is not None
        assert result.encoding == "utf-32-be"

    def test_no_bom(self):
        assert detect_bom(b"Hello, world!") is None

    def test_empty_data(self):
        assert detect_bom(b"") is None

    def test_utf32_le_before_utf16_le(self):
        result = detect_bom(b"\xff\xfe\x00\x00")
        assert result.encoding == "utf-32-le"

    def test_utf16_le_not_utf32(self):
        result = detect_bom(b"\xff\xfe\x41\x00")
        assert result.encoding == "utf-16-le"

    def test_partial_utf8_bom(self):
        assert detect_bom(b"\xef\xbb") is None

    def test_bom_names(self):
        assert detect_bom(b"\xef\xbb\xbf").bom_name == "UTF-8 BOM"
        assert detect_bom(b"\xff\xfeAB").bom_name == "UTF-16 LE BOM"
        assert detect_bom(b"\xfe\xffAB").bom_name == "UTF-16 BE BOM"
        assert detect_bom(b"\xff\xfe\x00\x00").bom_name == "UTF-32 LE BOM"
        assert detect_bom(b"\x00\x00\xfe\xff").bom_name == "UTF-32 BE BOM"


class TestStripBom:
    def test_strip_utf8_bom(self):
        stripped, bom = strip_bom(b"\xef\xbb\xbfHello")
        assert stripped == b"Hello"
        assert bom is not None and bom.encoding == "utf-8-sig"

    def test_strip_utf16_le_bom(self):
        stripped, bom = strip_bom(b"\xff\xfeH\x00")
        assert stripped == b"H\x00"
        assert bom.encoding == "utf-16-le"

    def test_no_bom_to_strip(self):
        stripped, bom = strip_bom(b"Hello")
        assert stripped == b"Hello"
        assert bom is None

    def test_empty_data(self):
        stripped, bom = strip_bom(b"")
        assert stripped == b""
        assert bom is None


class TestGetBomForEncoding:
    def test_utf8_sig(self):
        assert get_bom_for_encoding("utf-8-sig") == b"\xef\xbb\xbf"

    def test_utf16_le(self):
        assert get_bom_for_encoding("utf-16-le") == b"\xff\xfe"

    def test_unknown_encoding(self):
        assert get_bom_for_encoding("utf-8") is None

    def test_case_insensitive(self):
        assert get_bom_for_encoding("UTF-8-sig") == b"\xef\xbb\xbf"

    def test_underscore_variant(self):
        assert get_bom_for_encoding("utf_8_sig") == b"\xef\xbb\xbf"


class TestFormatBomReport:
    def test_report_with_bom(self):
        report = format_bom_report(b"\xef\xbb\xbfHello")
        assert "UTF-8 BOM" in report
        assert "BOM found" in report

    def test_report_without_bom(self):
        report = format_bom_report(b"Hello")
        assert "No BOM detected" in report
        assert "First bytes (hex):" in report

    def test_report_shows_content_length(self):
        report = format_bom_report(b"\xef\xbb\xbfHello")
        assert "Content after BOM: 5 bytes" in report


# ═══════════════════════════════════════════════════════════════════
# 2. Encoding Detection
# ═══════════════════════════════════════════════════════════════════

class TestEmptyAndAscii:
    def test_empty_bytes(self):
        report = detect_encoding(b"")
        assert report.best.encoding == "ascii"
        assert report.best.confidence == 1.0

    def test_simple_ascii(self):
        report = detect_encoding(b"Hello, world!")
        assert report.best.encoding == "ascii"
        assert report.best.confidence == 1.0

    def test_ascii_json(self):
        report = detect_encoding(b'{"key": "value", "number": 42}')
        assert report.best.encoding == "ascii"


class TestBomDetection:
    def test_utf8_bom(self):
        report = detect_encoding(b"\xef\xbb\xbfHello")
        assert report.best.encoding == "utf-8-sig"
        assert report.best.confidence == 1.0
        assert report.best.method == "bom"

    def test_utf16_le_bom(self):
        report = detect_encoding(b"\xff\xfeH\x00e\x00l\x00l\x00o\x00")
        assert report.best.encoding == "utf-16-le"

    def test_utf32_le_bom(self):
        report = detect_encoding(b"\xff\xfe\x00\x00H\x00\x00\x00")
        assert report.best.encoding == "utf-32-le"

    def test_bom_overrides_content(self):
        report = detect_encoding(b"\xef\xbb\xbfpure ascii here")
        assert report.best.encoding == "utf-8-sig"


class TestUtf8Detection:
    def test_two_byte_sequence(self):
        report = detect_encoding("cafe\u0301".encode("utf-8"))
        assert report.best.encoding == "utf-8"

    def test_three_byte_sequence(self):
        report = detect_encoding("\u4e16\u754c".encode("utf-8"))
        assert report.best.encoding == "utf-8"

    def test_four_byte_sequence(self):
        report = detect_encoding("Hello \U0001f30d".encode("utf-8"))
        assert report.best.encoding == "utf-8"

    def test_french_text(self):
        data = "Les caracteres speciaux: e\u0301, e\u0300, e\u0302".encode("utf-8")
        report = detect_encoding(data)
        assert report.best.encoding == "utf-8"

    def test_german_text(self):
        report = detect_encoding("\u00c4ndere die Gr\u00f6\u00dfe".encode("utf-8"))
        assert report.best.encoding == "utf-8"

    def test_russian_text(self):
        report = detect_encoding("\u041f\u0440\u0438\u0432\u0435\u0442, \u043c\u0438\u0440!".encode("utf-8"))
        assert report.best.encoding == "utf-8"

    def test_overlong_rejected(self):
        report = detect_encoding(b"\xc0\x80")
        assert report.best.encoding != "utf-8"

    def test_surrogate_rejected(self):
        report = detect_encoding(b"\xed\xa0\x80")
        assert report.best.encoding != "utf-8"

    def test_truncated_two_byte(self):
        report = detect_encoding(b"\xc3")
        assert report.best.encoding != "utf-8"


class TestWindows1252Detection:
    def test_smart_quotes(self):
        report = detect_encoding(b"He said \x93hello\x94 to her.")
        assert report.best.encoding == "windows-1252"

    def test_em_dash(self):
        report = detect_encoding(b"Something \x97 something else")
        assert report.best.encoding == "windows-1252"

    def test_undefined_cp1252_byte_excludes(self):
        report = detect_encoding(b"test\x81test")
        cp1252_candidates = [c for c in report.candidates if c.encoding == "windows-1252"]
        assert len(cp1252_candidates) == 0


class TestCjkDetection:
    def test_shift_jis(self):
        data = "\u65e5\u672c\u8a9e".encode("shift_jis")
        report = detect_encoding(data)
        sjis = [c for c in report.candidates if c.encoding == "shift_jis"]
        assert len(sjis) > 0

    def test_euc_jp(self):
        data = "\u65e5\u672c\u8a9e".encode("euc-jp")
        report = detect_encoding(data)
        eucjp = [c for c in report.candidates if c.encoding == "euc-jp"]
        assert len(eucjp) > 0

    def test_gb2312(self):
        data = "\u4e2d\u6587\u6d4b\u8bd5".encode("gb2312")
        report = detect_encoding(data)
        gb = [c for c in report.candidates if c.encoding == "gb2312"]
        assert len(gb) > 0

    def test_big5(self):
        data = "\u4e2d\u6587\u6e2c\u8a66".encode("big5")
        report = detect_encoding(data)
        big5 = [c for c in report.candidates if c.encoding == "big5"]
        assert len(big5) > 0


class TestDetectionReport:
    def test_report_format(self):
        text = detect_encoding(b"Hello").format_report()
        assert "Encoding Detection Report" in text
        assert "ascii" in text

    def test_candidates_sorted(self):
        report = detect_encoding("\u041f\u0440\u0438\u0432\u0435\u0442".encode("utf-8"))
        if len(report.candidates) > 1:
            for i in range(len(report.candidates) - 1):
                assert report.candidates[i].confidence >= report.candidates[i + 1].confidence

    def test_candidates_unique(self):
        report = detect_encoding("cafe\u0301 re\u0301sume\u0301".encode("utf-8"))
        encodings = [c.encoding for c in report.candidates]
        assert len(encodings) == len(set(encodings))


class TestFileDetection:
    def test_detect_file(self, tmp_path):
        fp = tmp_path / "test.txt"
        fp.write_bytes("cafe\u0301".encode("utf-8"))
        report = detect_encoding_from_file(str(fp))
        assert report.best.encoding == "utf-8"

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            detect_encoding_from_file("/nonexistent/path/file.txt")


# ═══════════════════════════════════════════════════════════════════
# 3. Encoding Conversion
# ═══════════════════════════════════════════════════════════════════

class TestBasicConversion:
    def test_latin1_to_utf8(self):
        result = convert_bytes("caf\u00e9".encode("iso-8859-1"), "iso-8859-1", "utf-8")
        assert result.data == "caf\u00e9".encode("utf-8")

    def test_utf8_to_latin1(self):
        result = convert_bytes("caf\u00e9".encode("utf-8"), "utf-8", "iso-8859-1")
        assert result.data == "caf\u00e9".encode("iso-8859-1")

    def test_windows1252_to_utf8(self):
        result = convert_bytes(b"\x93hello\x94", "windows-1252", "utf-8")
        text = result.data.decode("utf-8")
        assert "\u201c" in text and "\u201d" in text

    def test_utf8_to_shift_jis(self):
        data = "\u65e5\u672c\u8a9e".encode("utf-8")
        result = convert_bytes(data, "utf-8", "shift_jis")
        assert result.data == "\u65e5\u672c\u8a9e".encode("shift_jis")

    def test_empty_data(self):
        result = convert_bytes(b"", "utf-8", "iso-8859-1")
        assert result.data == b""


class TestRoundTrip:
    def test_roundtrip_utf8_latin1(self):
        original = "caf\u00e9 r\u00e9sum\u00e9 na\u00efve".encode("utf-8")
        step1 = convert_bytes(original, "utf-8", "iso-8859-1")
        step2 = convert_bytes(step1.data, "iso-8859-1", "utf-8")
        assert step2.data == original

    def test_roundtrip_utf8_shift_jis(self):
        original = "\u65e5\u672c\u8a9e\u30c6\u30b9\u30c8".encode("utf-8")
        step1 = convert_bytes(original, "utf-8", "shift_jis")
        step2 = convert_bytes(step1.data, "shift_jis", "utf-8")
        assert step2.data == original

    def test_roundtrip_utf8_koi8r(self):
        original = "\u041f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440".encode("utf-8")
        step1 = convert_bytes(original, "utf-8", "koi8-r")
        step2 = convert_bytes(step1.data, "koi8-r", "utf-8")
        assert step2.data == original


class TestConversionErrors:
    def test_strict_mode_raises(self):
        data = "Hello \U0001f30d".encode("utf-8")
        with pytest.raises(UnicodeEncodeError):
            convert_bytes(data, "utf-8", "iso-8859-1", error_strategy="strict")

    def test_replace_mode(self):
        data = "Hello \U0001f30d".encode("utf-8")
        result = convert_bytes(data, "utf-8", "iso-8859-1", error_strategy="replace")
        assert b"?" in result.data

    def test_ignore_mode(self):
        data = "Hello \U0001f30d".encode("utf-8")
        result = convert_bytes(data, "utf-8", "iso-8859-1", error_strategy="ignore")
        assert b"Hello " in result.data

    def test_unknown_encoding(self):
        with pytest.raises(LookupError):
            convert_bytes(b"test", "not-an-encoding", "utf-8")


class TestBomHandling:
    def test_strip_bom_on_source(self):
        result = convert_bytes(b"\xef\xbb\xbfHello", "utf-8-sig", "utf-8")
        assert not result.data.startswith(b"\xef\xbb\xbf")

    def test_add_bom_for_target(self):
        result = convert_bytes(b"Hello", "utf-8", "utf-8-sig")
        assert result.data.startswith(b"\xef\xbb\xbf")

    def test_utf16_le_bom_added(self):
        result = convert_bytes(b"Hello", "ascii", "utf-16-le")
        assert result.data.startswith(b"\xff\xfe")


class TestEncodingNormalization:
    def test_latin1_alias(self):
        assert _normalize_encoding("latin1") == "iso-8859-1"

    def test_cp1252_alias(self):
        assert _normalize_encoding("cp1252") == "windows-1252"

    def test_utf8_alias(self):
        assert _normalize_encoding("utf8") == "utf-8"

    def test_utf8_bom_alias(self):
        assert _normalize_encoding("utf-8-bom") == "utf-8-sig"

    def test_sjis_alias(self):
        assert _normalize_encoding("sjis") == "shift_jis"

    def test_unknown_passes_through(self):
        assert _normalize_encoding("some-encoding") == "some-encoding"


class TestFileConversion:
    def test_convert_file_auto_detect(self, tmp_path):
        source = tmp_path / "source.txt"
        target = tmp_path / "target.txt"
        source.write_bytes("caf\u00e9".encode("utf-8"))
        convert_file(str(source), str(target), target_encoding="iso-8859-1")
        assert target.read_bytes() == "caf\u00e9".encode("iso-8859-1")

    def test_convert_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            convert_file("/nonexistent/file.txt")


class TestFormatConversionReport:
    def test_basic_report(self):
        result = convert_bytes(b"Hello", "utf-8", "iso-8859-1")
        report = format_conversion_report(result)
        assert "Source encoding: utf-8" in report
        assert "Success" in report


# ═══════════════════════════════════════════════════════════════════
# 4. Mojibake Detection
# ═══════════════════════════════════════════════════════════════════

class TestUtf8AsLatin1:
    @pytest.mark.parametrize("original", [
        "caf\u00e9", "p\u00e8re", "\u00c4rger", "sch\u00f6n",
        "\u00fcber", "ni\u00f1o", "fran\u00e7ais",
        "r\u00e9sum\u00e9 na\u00efve caf\u00e9",
    ])
    def test_detect_and_fix(self, original):
        mangled = original.encode("utf-8").decode("iso-8859-1")
        result = detect_mojibake(mangled)
        assert result.is_mojibake
        assert result.fixed_text == original


class TestUtf8AsWindows1252:
    def test_e_acute_cp1252(self):
        original = "caf\u00e9"
        mangled = original.encode("utf-8").decode("windows-1252")
        result = detect_mojibake(mangled)
        assert result.is_mojibake
        assert result.fixed_text == original


class TestDoubleEncoding:
    def test_double_encoded_gets_fixed(self):
        original = "caf\u00e9"
        step1 = original.encode("utf-8")
        step2 = step1.decode("iso-8859-1")
        step3 = step2.encode("utf-8")
        double_mangled = step3.decode("iso-8859-1")
        result = detect_mojibake(double_mangled)
        assert result.is_mojibake
        assert result.fixed_text == original


class TestNonMojibake:
    @pytest.mark.parametrize("text", [
        "Hello, world!", "", "caf\u00e9 r\u00e9sum\u00e9 na\u00efve",
        "\u65e5\u672c\u8a9e\u306e\u30c6\u30ad\u30b9\u30c8",
        "\u4e2d\u6587\u6d4b\u8bd5",
        "\ud55c\uad6d\uc5b4 \ud14c\uc2a4\ud2b8",
        "Hello \U0001f30d\U0001f389",
    ])
    def test_not_flagged(self, text):
        result = detect_mojibake(text)
        assert not result.is_mojibake


class TestFixMojibake:
    def test_fix_utf8_as_latin1(self):
        original = "caf\u00e9"
        garbled = original.encode("utf-8").decode("iso-8859-1")
        assert fix_mojibake(garbled, "iso-8859-1", "utf-8") == original

    def test_fix_invalid_chain_raises(self):
        with pytest.raises((UnicodeDecodeError, UnicodeEncodeError)):
            fix_mojibake("Hello \U0001f30d", "ascii", "utf-8")


class TestDetectMojibakeBytes:
    def test_utf8_bytes_not_mojibake(self):
        assert not detect_mojibake_bytes("caf\u00e9".encode("utf-8")).is_mojibake

    def test_garbled_bytes(self):
        garbled_bytes = "caf\u00e9".encode("utf-8").decode("iso-8859-1").encode("utf-8")
        assert detect_mojibake_bytes(garbled_bytes).is_mojibake

    def test_empty_bytes(self):
        assert not detect_mojibake_bytes(b"").is_mojibake


class TestMojibakeScoring:
    def test_clean_text_low_score(self):
        assert _score_mojibake_likelihood("Hello, world!") < 0.1

    def test_garbled_text_high_score(self):
        garbled = "caf\u00e9".encode("utf-8").decode("iso-8859-1")
        assert _score_mojibake_likelihood(garbled) > 0.3

    def test_empty_text_zero(self):
        assert _score_mojibake_likelihood("") == 0.0


class TestSpecificGarbledStrings:
    def test_classic_a_tilde_copyright(self):
        result = detect_mojibake("\u00c3\u00a9")
        assert result.is_mojibake
        assert result.fixed_text == "\u00e9"

    def test_o_umlaut_garbled(self):
        result = detect_mojibake("\u00c3\u00b6")
        assert result.is_mojibake
        assert result.fixed_text == "\u00f6"


class TestFormatMojibakeReport:
    def test_clean_text_report(self):
        report = format_mojibake_report(detect_mojibake("Hello"))
        assert "No mojibake detected" in report

    def test_garbled_text_report(self):
        garbled = "caf\u00e9".encode("utf-8").decode("iso-8859-1")
        report = format_mojibake_report(detect_mojibake(garbled))
        assert "MOJIBAKE DETECTED" in report
        assert "Fixed text:" in report
        assert "What happened:" in report


# ═══════════════════════════════════════════════════════════════════
# 5. Integration: detect then convert, mojibake detect then fix
# ═══════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_detect_and_convert_windows1252(self):
        data = b"He said \x93hello\x94"
        report = detect_encoding(data)
        assert report.best.encoding == "windows-1252"
        result = convert_bytes(data, report.best.encoding, "utf-8")
        decoded = result.data.decode("utf-8")
        assert "\u201c" in decoded

    def test_detect_and_fix_french(self):
        original = "Les \u00e9l\u00e8ves \u00e9tudient \u00e0 l'\u00e9cole fran\u00e7aise."
        garbled = original.encode("utf-8").decode("iso-8859-1")
        result = detect_mojibake(garbled)
        assert result.is_mojibake and result.fixed_text == original

    @pytest.mark.parametrize("text", [
        "caf\u00e9", "na\u00efve", "r\u00e9sum\u00e9", "\u00fcber",
        "\u00c4rger", "ni\u00f1o", "fran\u00e7ais",
    ])
    def test_utf8_texts_detected(self, text):
        report = detect_encoding(text.encode("utf-8"))
        assert report.best.encoding == "utf-8"

    @pytest.mark.parametrize("bom,encoding", [
        (b"\xef\xbb\xbf", "utf-8-sig"),
        (b"\xff\xfe", "utf-16-le"),
        (b"\xfe\xff", "utf-16-be"),
        (b"\xff\xfe\x00\x00", "utf-32-le"),
        (b"\x00\x00\xfe\xff", "utf-32-be"),
    ])
    def test_bom_texts(self, bom, encoding):
        report = detect_encoding(bom + b"Hello")
        assert report.best.encoding == encoding
        assert report.best.confidence == 1.0

    @pytest.mark.parametrize("text,src,dst", [
        ("Hello", "ascii", "utf-8"),
        ("caf\u00e9", "utf-8", "iso-8859-1"),
        ("caf\u00e9", "iso-8859-1", "utf-8"),
        ("\u65e5\u672c\u8a9e", "utf-8", "shift_jis"),
        ("\u65e5\u672c\u8a9e", "shift_jis", "utf-8"),
        ("\u4e2d\u6587", "utf-8", "gb2312"),
        ("\u041f\u0440\u0438\u0432\u0435\u0442", "utf-8", "koi8-r"),
    ])
    def test_conversion_pair(self, text, src, dst):
        data = text.encode(src)
        result = convert_bytes(data, src, dst)
        expected = text.encode(dst)
        actual = result.data
        if dst == "utf-16-le" and actual.startswith(b"\xff\xfe"):
            actual = actual[2:]
        elif dst == "utf-16-be" and actual.startswith(b"\xfe\xff"):
            actual = actual[2:]
        assert actual == expected
