"""
Tests for Escape & Encoding Converter.

These tests ARE the spec -- if an LLM regenerates the converter in any
language, these cases define correctness.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_TOOL_DIR = str(Path(__file__).parent)

from converter import (
    FORMATS,
    encode, decode, convert, convert_bulk, list_formats,
    encode_url, encode_html, encode_unicode_escape, encode_json,
    encode_c_escape, encode_xml, encode_base64, encode_base64url,
    encode_hex, encode_octal,
    decode_url, decode_html, decode_unicode_escape, decode_json,
    decode_c_escape, decode_xml, decode_base64, decode_base64url,
    decode_hex, decode_octal,
    detect, detect_best, is_double_encoded,
    Detection,
)


# ============================================================
# 1. URL encoding/decoding
# ============================================================

class TestURL:
    def test_encode_space(self):
        assert encode_url("hello world") == "hello%20world"

    def test_encode_special_chars(self):
        result = encode_url("a&b=c")
        assert "%26" in result
        assert "%3D" in result

    def test_encode_unicode(self):
        result = encode_url("caf\u00e9")
        assert "%C3%A9" in result

    def test_encode_already_safe(self):
        assert encode_url("hello") == "hello"

    def test_decode_space(self):
        assert decode_url("hello%20world") == "hello world"

    def test_decode_plus_stays(self):
        # urllib.parse.unquote does NOT decode + as space (that's unquote_plus)
        assert decode_url("hello+world") == "hello+world"

    def test_roundtrip(self):
        original = "hello world! @#$%^&*()"
        assert decode_url(encode_url(original)) == original

    def test_roundtrip_unicode(self):
        original = "\u00e9\u00e8\u00ea"
        assert decode_url(encode_url(original)) == original


# ============================================================
# 2. HTML encoding/decoding
# ============================================================

class TestHTML:
    def test_encode_ampersand(self):
        assert encode_html("a & b") == "a &amp; b"

    def test_encode_angle_brackets(self):
        assert encode_html("<p>") == "&lt;p&gt;"

    def test_encode_quote(self):
        result = encode_html('"hello"')
        assert "&quot;" in result

    def test_encode_non_ascii(self):
        result = encode_html("caf\u00e9")
        assert "&#233;" in result

    def test_decode_named(self):
        assert decode_html("&amp;") == "&"
        assert decode_html("&lt;") == "<"
        assert decode_html("&gt;") == ">"

    def test_decode_numeric_decimal(self):
        assert decode_html("&#233;") == "\u00e9"

    def test_decode_numeric_hex(self):
        assert decode_html("&#xe9;") == "\u00e9"

    def test_roundtrip(self):
        original = '<script>alert("xss")</script>'
        assert decode_html(encode_html(original)) == original

    def test_roundtrip_unicode(self):
        original = "caf\u00e9 \u2603"
        assert decode_html(encode_html(original)) == original


# ============================================================
# 3. Unicode escape encoding/decoding
# ============================================================

class TestUnicodeEscape:
    def test_encode_ascii_passthrough(self):
        assert encode_unicode_escape("hello") == "hello"

    def test_encode_non_ascii(self):
        assert encode_unicode_escape("\u00e9") == "\\u00e9"

    def test_encode_astral(self):
        # Emoji (U+1F600)
        result = encode_unicode_escape("\U0001f600")
        assert "\\U0001f600" in result

    def test_decode_bmp(self):
        assert decode_unicode_escape("caf\\u00e9") == "caf\u00e9"

    def test_decode_astral(self):
        assert decode_unicode_escape("\\U0001f600") == "\U0001f600"

    def test_decode_passthrough(self):
        assert decode_unicode_escape("hello") == "hello"

    def test_roundtrip(self):
        original = "caf\u00e9 \u2603 \U0001f600"
        assert decode_unicode_escape(encode_unicode_escape(original)) == original


# ============================================================
# 4. JSON encoding/decoding
# ============================================================

class TestJSON:
    def test_encode_newline(self):
        assert encode_json("hello\nworld") == "hello\\nworld"

    def test_encode_tab(self):
        assert encode_json("a\tb") == "a\\tb"

    def test_encode_backslash(self):
        assert encode_json("a\\b") == "a\\\\b"

    def test_encode_quote(self):
        assert encode_json('say "hi"') == 'say \\"hi\\"'

    def test_encode_plain_text(self):
        assert encode_json("hello") == "hello"

    def test_decode_newline(self):
        assert decode_json("hello\\nworld") == "hello\nworld"

    def test_decode_tab(self):
        assert decode_json("a\\tb") == "a\tb"

    def test_decode_unicode_escape(self):
        assert decode_json("caf\\u00e9") == "caf\u00e9"

    def test_decode_invalid(self):
        with pytest.raises(ValueError):
            decode_json("bad\\qescape")

    def test_roundtrip(self):
        original = 'line1\nline2\t"quoted"\\'
        assert decode_json(encode_json(original)) == original


# ============================================================
# 5. C escape encoding/decoding
# ============================================================

class TestCEscape:
    def test_encode_newline(self):
        assert encode_c_escape("a\nb") == "a\\nb"

    def test_encode_tab(self):
        assert encode_c_escape("a\tb") == "a\\tb"

    def test_encode_null(self):
        assert encode_c_escape("\0") == "\\0"

    def test_encode_backslash(self):
        assert encode_c_escape("\\") == "\\\\"

    def test_encode_non_ascii(self):
        result = encode_c_escape("\u00e9")  # e-acute, UTF-8: c3 a9
        assert "\\xc3" in result
        assert "\\xa9" in result

    def test_decode_named(self):
        assert decode_c_escape("a\\nb") == "a\nb"
        assert decode_c_escape("a\\tb") == "a\tb"
        assert decode_c_escape("\\0") == "\0"

    def test_decode_hex(self):
        assert decode_c_escape("\\x41") == "A"

    def test_decode_utf8_bytes(self):
        # e-acute in UTF-8
        assert decode_c_escape("\\xc3\\xa9") == "\u00e9"

    def test_roundtrip(self):
        original = "hello\nworld\t\0"
        assert decode_c_escape(encode_c_escape(original)) == original

    def test_roundtrip_unicode(self):
        original = "caf\u00e9"
        assert decode_c_escape(encode_c_escape(original)) == original


# ============================================================
# 6. XML encoding/decoding
# ============================================================

class TestXML:
    def test_encode_ampersand(self):
        assert encode_xml("a & b") == "a &amp; b"

    def test_encode_angle_brackets(self):
        assert encode_xml("<tag>") == "&lt;tag&gt;"

    def test_encode_apos(self):
        result = encode_xml("it's")
        assert "&apos;" in result

    def test_encode_non_ascii(self):
        result = encode_xml("\u00e9")
        assert "&#233;" in result

    def test_decode_entities(self):
        assert decode_xml("&amp;") == "&"
        assert decode_xml("&lt;") == "<"
        assert decode_xml("&gt;") == ">"
        assert decode_xml("&quot;") == '"'
        assert decode_xml("&apos;") == "'"

    def test_decode_numeric(self):
        assert decode_xml("&#233;") == "\u00e9"

    def test_roundtrip(self):
        original = '<tag attr="it\'s a & b">'
        assert decode_xml(encode_xml(original)) == original


# ============================================================
# 7. Base64 encoding/decoding
# ============================================================

class TestBase64:
    def test_encode(self):
        assert encode_base64("hello") == "aGVsbG8="

    def test_encode_empty(self):
        assert encode_base64("") == ""

    def test_encode_unicode(self):
        # UTF-8 bytes of e-acute
        result = encode_base64("\u00e9")
        assert result == "w6k="

    def test_decode(self):
        assert decode_base64("aGVsbG8=") == "hello"

    def test_decode_invalid(self):
        with pytest.raises(ValueError):
            decode_base64("not!valid!base64!!!")

    def test_roundtrip(self):
        original = "hello world 123 !@#"
        assert decode_base64(encode_base64(original)) == original

    def test_roundtrip_unicode(self):
        original = "caf\u00e9 \u2603"
        assert decode_base64(encode_base64(original)) == original


# ============================================================
# 8. Hex encoding/decoding
# ============================================================

class TestHex:
    def test_encode(self):
        assert encode_hex("AB") == "4142"

    def test_encode_empty(self):
        assert encode_hex("") == ""

    def test_decode(self):
        assert decode_hex("4142") == "AB"

    def test_decode_invalid_chars(self):
        with pytest.raises(ValueError):
            decode_hex("ZZZZ")

    def test_decode_odd_length(self):
        with pytest.raises(ValueError):
            decode_hex("414")

    def test_roundtrip(self):
        original = "hello world"
        assert decode_hex(encode_hex(original)) == original

    def test_roundtrip_unicode(self):
        original = "caf\u00e9"
        assert decode_hex(encode_hex(original)) == original


# ============================================================
# 9. Octal encoding/decoding
# ============================================================

class TestOctal:
    def test_encode_ascii_passthrough(self):
        assert encode_octal("hello") == "hello"

    def test_encode_newline(self):
        result = encode_octal("\n")
        assert result == "\\012"

    def test_encode_null(self):
        result = encode_octal("\0")
        assert result == "\\000"

    def test_decode_passthrough(self):
        assert decode_octal("hello") == "hello"

    def test_decode_sequences(self):
        assert decode_octal("\\101") == "A"  # 101 octal = 65 decimal = 'A'

    def test_decode_newline(self):
        assert decode_octal("\\012") == "\n"

    def test_roundtrip(self):
        original = "hello\n\t\0world"
        assert decode_octal(encode_octal(original)) == original


# ============================================================
# 10. Cross-format round-trips
# ============================================================

class TestRoundTrips:
    """Every format pair: encode in A, convert A->B->A, verify identity."""

    @pytest.mark.parametrize("fmt", list(FORMATS))
    def test_encode_decode_identity(self, fmt):
        """encode then decode returns original for every format."""
        original = "hello world"
        encoded = encode(original, fmt)
        decoded = decode(encoded, fmt)
        assert decoded == original, f"{fmt}: {original!r} -> {encoded!r} -> {decoded!r}"

    @pytest.mark.parametrize("fmt", list(FORMATS))
    def test_encode_decode_special_chars(self, fmt):
        """Encode/decode special chars through every format."""
        original = '<a href="x">&amp;\n\t'
        encoded = encode(original, fmt)
        decoded = decode(encoded, fmt)
        assert decoded == original, f"{fmt} failed on special chars"

    def test_url_to_html_convert(self):
        encoded = encode_url("hello world")
        result = convert(encoded, "url", "html")
        # "hello world" in HTML is just "hello world" (no special chars)
        assert result == "hello world"

    def test_html_to_url_convert(self):
        encoded = encode_html("<p>")
        result = convert(encoded, "html", "url")
        assert decode_url(result) == "<p>"

    def test_json_to_c_escape_convert(self):
        encoded = encode_json("line1\nline2")
        result = convert(encoded, "json", "c_escape")
        assert decode_c_escape(result) == "line1\nline2"

    def test_base64_to_hex_convert(self):
        encoded = encode_base64("hello")
        result = convert(encoded, "base64", "hex")
        assert decode_hex(result) == "hello"

    def test_convert_chain(self):
        """A -> B -> C -> A should return original."""
        original = "test data 123"
        step1 = convert(encode(original, "url"), "url", "base64")
        step2 = convert(step1, "base64", "hex")
        step3 = convert(step2, "hex", "url")
        final = decode(step3, "url")
        assert final == original


class TestConvertBulk:
    def test_bulk(self):
        texts = [encode_url("a b"), encode_url("c d"), encode_url("e f")]
        results = convert_bulk(texts, "url", "html")
        assert results == ["a b", "c d", "e f"]

    def test_bulk_empty(self):
        assert convert_bulk([], "url", "html") == []


class TestConvertErrors:
    def test_unknown_source(self):
        with pytest.raises(ValueError, match="Unknown source format"):
            convert("test", "nonexistent", "url")

    def test_unknown_target(self):
        with pytest.raises(ValueError, match="Unknown target format"):
            convert("test", "url", "nonexistent")


# ============================================================
# 11. Detection
# ============================================================

class TestDetectURL:
    def test_detect_percent_encoded(self):
        results = detect("hello%20world%21")
        formats = [d.format for d in results]
        assert "url" in formats

    def test_detect_no_encoding(self):
        results = detect("hello world")
        url_results = [d for d in results if d.format == "url"]
        assert len(url_results) == 0


class TestDetectHTML:
    def test_detect_named_entities(self):
        results = detect("&amp; &lt; &gt;")
        formats = [d.format for d in results]
        assert "html" in formats or "xml" in formats

    def test_detect_numeric_entities(self):
        results = detect("&#233;")
        formats = [d.format for d in results]
        assert "html" in formats or "xml" in formats


class TestDetectJSON:
    def test_detect_json_escapes(self):
        results = detect('hello\\nworld\\ttab')
        formats = [d.format for d in results]
        assert "json" in formats or "c_escape" in formats


class TestDetectBase64:
    def test_detect_base64_padded(self):
        b64_text = encode_base64("hello world, this is a test")
        results = detect(b64_text)
        formats = [d.format for d in results]
        assert "base64" in formats

    def test_short_string_not_base64(self):
        # Very short strings shouldn't confidently detect as base64
        results = detect("ab")
        base64_results = [d for d in results if d.format == "base64"]
        assert len(base64_results) == 0


class TestDetectHex:
    def test_detect_hex_string(self):
        hex_text = encode_hex("hello world test data!!")
        results = detect(hex_text)
        formats = [d.format for d in results]
        assert "hex" in formats


class TestDetectOctal:
    def test_detect_octal(self):
        results = detect("\\110\\145\\154\\154\\157")
        formats = [d.format for d in results]
        assert "octal" in formats


class TestDetectUnicodeEscape:
    def test_detect_unicode_escapes(self):
        results = detect("caf\\u00e9")
        formats = [d.format for d in results]
        assert "unicode_escape" in formats


class TestDetectBest:
    def test_best_url(self):
        detection = detect_best("hello%20world%20foo%20bar")
        assert detection is not None
        assert detection.format == "url"

    def test_best_none(self):
        detection = detect_best("plain text")
        # May or may not detect anything for plain text
        # Just ensure it doesn't crash


class TestDetectConfidence:
    def test_sorted_by_confidence(self):
        results = detect("hello%20world")
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].confidence >= results[i + 1].confidence

    def test_confidence_range(self):
        results = detect("hello%20world%21%3F")
        for d in results:
            assert 0.0 <= d.confidence <= 1.0


# ============================================================
# 12. Double-encoding detection
# ============================================================

class TestDoubleEncoding:
    def test_double_url_detected(self):
        # %2520 = double-encoded space (%20 -> %2520)
        assert is_double_encoded("%2520") is True

    def test_double_html_detected(self):
        # &amp;amp; = double-encoded &
        assert is_double_encoded("&amp;amp;") is True

    def test_single_url_not_double(self):
        assert is_double_encoded("%20") is False

    def test_single_html_not_double(self):
        assert is_double_encoded("&amp;") is False

    def test_plain_text_not_double(self):
        assert is_double_encoded("hello world") is False

    def test_double_url_detection_details(self):
        results = detect("%2520%253D")
        double_results = [d for d in results if d.is_double_encoded]
        assert len(double_results) > 0
        assert double_results[0].inner_format == "url"

    def test_double_html_detection_details(self):
        results = detect("&amp;lt;")
        double_results = [d for d in results if d.is_double_encoded]
        assert len(double_results) > 0
        assert double_results[0].inner_format == "html"

    def test_decode_double_url(self):
        """Decoding a double-URL-encoded string twice recovers original."""
        original = "hello world"
        single = encode_url(original)          # hello%20world
        double = encode_url(single)            # hello%2520world
        once = decode_url(double)              # hello%20world
        twice = decode_url(once)               # hello world
        assert twice == original


# ============================================================
# 13. Encode/decode dispatchers
# ============================================================

class TestDispatcher:
    @pytest.mark.parametrize("fmt", list(FORMATS))
    def test_encode_dispatch(self, fmt):
        """encode() dispatches correctly for every format."""
        result = encode("hello", fmt)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.parametrize("fmt", list(FORMATS))
    def test_decode_dispatch(self, fmt):
        """decode(encode(x)) returns x for every format."""
        original = "hello"
        assert decode(encode(original, fmt), fmt) == original

    def test_encode_bad_format(self):
        with pytest.raises(ValueError, match="Unknown encoding format"):
            encode("hello", "bogus")

    def test_decode_bad_format(self):
        with pytest.raises(ValueError, match="Unknown decoding format"):
            decode("hello", "bogus")


class TestListFormats:
    def test_all_ten_formats(self):
        fmts = list_formats()
        assert len(fmts) == 10
        for f in FORMATS:
            assert f in fmts


# ============================================================
# 14. CLI output format
# ============================================================

class TestCLI:
    def test_encode_command(self):
        result = subprocess.run(
            [sys.executable, "converter.py", "encode", "url", "hello world"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "hello%20world" in result.stdout

    def test_decode_command(self):
        result = subprocess.run(
            [sys.executable, "converter.py", "decode", "url", "hello%20world"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "hello world" in result.stdout

    def test_detect_command(self):
        result = subprocess.run(
            [sys.executable, "converter.py", "detect", "hello%20world"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "url" in result.stdout.lower()

    def test_convert_command(self):
        result = subprocess.run(
            [sys.executable, "converter.py", "convert", "url", "base64", "hello%20world"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        # Result should be base64 of "hello world"
        assert result.stdout.strip() == "aGVsbG8gd29ybGQ="

    def test_formats_command(self):
        result = subprocess.run(
            [sys.executable, "converter.py", "formats"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0
        assert "url" in result.stdout
        assert "html" in result.stdout
        assert "base64" in result.stdout

    def test_no_command_shows_help(self):
        result = subprocess.run(
            [sys.executable, "converter.py"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        # Should print help, not crash
        assert result.returncode == 0


# ============================================================
# 15. Base64url encoding/decoding
# ============================================================

class TestBase64URL:
    def test_encode(self):
        result = encode_base64url("hello")
        assert result == "aGVsbG8"  # no padding
        assert "=" not in result

    def test_encode_with_url_unsafe_chars(self):
        """Strings that produce + or / in standard base64 use - and _ in base64url."""
        result = encode_base64url("subjects?_d")
        assert "+" not in result
        assert "/" not in result

    def test_decode(self):
        assert decode_base64url("aGVsbG8") == "hello"

    def test_decode_with_padding(self):
        """Tolerates padding even though base64url typically omits it."""
        assert decode_base64url("aGVsbG8=") == "hello"

    def test_roundtrip(self):
        original = "hello world 123 !@#"
        assert decode_base64url(encode_base64url(original)) == original

    def test_roundtrip_unicode(self):
        original = "caf\u00e9 \u2603"
        assert decode_base64url(encode_base64url(original)) == original

    def test_encode_decode_dispatch(self):
        """base64url works through the encode/decode dispatchers."""
        original = "hello world"
        encoded = encode(original, "base64url")
        decoded = decode(encoded, "base64url")
        assert decoded == original

    def test_convert_base64_to_base64url(self):
        """Convert standard base64 to base64url."""
        b64_text = encode_base64("hello world")
        result = convert(b64_text, "base64", "base64url")
        assert decode_base64url(result) == "hello world"


# ============================================================
# 16. Base64 padding tolerance
# ============================================================

class TestBase64PaddingTolerance:
    def test_decode_missing_one_pad(self):
        """Base64 'aGVsbG8' is 'hello' without the trailing =."""
        assert decode_base64("aGVsbG8") == "hello"

    def test_decode_missing_two_pads(self):
        """Base64 'YQ' is 'a' without the trailing ==."""
        assert decode_base64("YQ") == "a"

    def test_decode_with_padding_still_works(self):
        assert decode_base64("aGVsbG8=") == "hello"
        assert decode_base64("YQ==") == "a"


# ============================================================
# 17. Base64url detection
# ============================================================

class TestDetectBase64URL:
    def test_detect_base64url(self):
        """Strings with - or _ should detect as base64url."""
        # A JWT-like token segment
        text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        # This contains letters that overlap with base64url
        # but the test is for when - or _ are present
        b64url_text = encode_base64url("subjects?_d/with+slash")
        if "-" in b64url_text or "_" in b64url_text:
            results = detect(b64url_text)
            formats = [d.format for d in results]
            assert "base64url" in formats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
