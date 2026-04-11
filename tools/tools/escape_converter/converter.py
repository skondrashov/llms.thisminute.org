"""
Escape & Encoding Converter -- Format Translation for Agents

Encodes and decodes strings across 9 escape/encoding formats, auto-detects
which format a string uses (including double-encoding), and converts between
any two formats in a single call.  Agents constantly move data across
boundaries (URLs, HTML, JSON, shell commands, databases) and need reliable
encoding/decoding -- LLMs frequently get edge cases wrong.

SUPPORTED FORMATS (10)
======================
  url             Percent-encoding (RFC 3986)
  html            HTML entities (named + numeric character references)
  unicode_escape  \\uXXXX / \\UXXXXXXXX sequences
  json            JSON string escapes (\\n, \\t, \\uXXXX, etc.)
  c_escape        C-style escapes (\\n, \\xHH, \\OOO, etc.)
  xml             XML predefined entities + numeric character references
  base64          Base64 (RFC 4648), tolerates missing padding
  base64url       Base64url (RFC 4648 section 5), URL-safe alphabet, no padding
  hex             Lowercase hex pairs
  octal           \\OOO byte sequences

DETECTION
=========
  detect(text)       -> list[Detection]   all possible formats, sorted by confidence
  detect_best(text)  -> Detection | None  highest-confidence guess
  is_double_encoded(text) -> bool         e.g. %2520 or &amp;amp;

CONVERSION
==========
  convert(text, from_format, to_format)   decode then re-encode
  convert_bulk(texts, from_fmt, to_fmt)   batch conversion

Pure Python, no external dependencies.
"""

from __future__ import annotations

import base64 as b64
import html as html_mod
import json as json_mod
import re
import urllib.parse
from dataclasses import dataclass, field


# ============================================================
# Constants
# ============================================================

FORMATS = (
    "url",
    "html",
    "unicode_escape",
    "json",
    "c_escape",
    "xml",
    "base64",
    "base64url",
    "hex",
    "octal",
)


# ============================================================
# Encoders
# ============================================================

def encode_url(text: str) -> str:
    """URL-encode (percent-encoding, RFC 3986). All chars except unreserved."""
    return urllib.parse.quote(text, safe="")


def encode_html(text: str) -> str:
    """HTML-encode: &, <, >, \", ' to entities; non-ASCII to &#NNN;."""
    result = html_mod.escape(text, quote=True)
    out: list[str] = []
    for ch in result:
        if ord(ch) > 127:
            out.append(f"&#{ord(ch)};")
        else:
            out.append(ch)
    return "".join(out)


def encode_unicode_escape(text: str) -> str:
    r"""Encode as \\uXXXX / \\UXXXXXXXX. ASCII printable left as-is."""
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0x20 <= cp <= 0x7E:
            out.append(ch)
        elif cp <= 0xFFFF:
            out.append(f"\\u{cp:04x}")
        else:
            out.append(f"\\U{cp:08x}")
    return "".join(out)


def encode_json(text: str) -> str:
    r"""JSON-encode (inner string, no surrounding quotes). Non-ASCII preserved."""
    encoded = json_mod.dumps(text, ensure_ascii=False)
    return encoded[1:-1]


def encode_json_ascii(text: str) -> str:
    r"""JSON-encode with all non-ASCII escaped as \\uXXXX."""
    encoded = json_mod.dumps(text, ensure_ascii=True)
    return encoded[1:-1]


def encode_c_escape(text: str) -> str:
    r"""C-style escape: \\n, \\t, \\xHH; non-ASCII as UTF-8 \\xHH bytes."""
    _c_escapes = {
        "\n": "\\n", "\t": "\\t", "\r": "\\r", "\\": "\\\\",
        '"': '\\"', "\0": "\\0", "\a": "\\a", "\b": "\\b",
        "\f": "\\f", "\v": "\\v",
    }
    out: list[str] = []
    for ch in text:
        if ch in _c_escapes:
            out.append(_c_escapes[ch])
        elif 0x20 <= ord(ch) <= 0x7E:
            out.append(ch)
        elif ord(ch) < 0x80:
            out.append(f"\\x{ord(ch):02x}")
        else:
            for byte in ch.encode("utf-8"):
                out.append(f"\\x{byte:02x}")
    return "".join(out)


def encode_xml(text: str) -> str:
    """XML-encode: 5 predefined entities + non-ASCII as &#NNN;."""
    replacements = [
        ("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"),
        ('"', "&quot;"), ("'", "&apos;"),
    ]
    result = text
    for old, new in replacements:
        result = result.replace(old, new)
    out: list[str] = []
    for ch in result:
        if ord(ch) > 127:
            out.append(f"&#{ord(ch)};")
        else:
            out.append(ch)
    return "".join(out)


def encode_base64(text: str, encoding: str = "utf-8") -> str:
    """Base64-encode a string's bytes."""
    return b64.b64encode(text.encode(encoding)).decode("ascii")


def encode_base64url(text: str, encoding: str = "utf-8") -> str:
    """Base64url-encode a string (RFC 4648 section 5).

    Uses URL-safe alphabet (- instead of +, _ instead of /) and
    strips padding (=). Used by JWTs and many web APIs.
    """
    return b64.urlsafe_b64encode(text.encode(encoding)).decode("ascii").rstrip("=")


def encode_hex(text: str, encoding: str = "utf-8") -> str:
    """Hex-encode a string's bytes as lowercase hex pairs."""
    return text.encode(encoding).hex()


def encode_octal(text: str, encoding: str = "utf-8") -> str:
    r"""Octal-encode: ASCII printable as-is, others as \\OOO."""
    data = text.encode(encoding)
    out: list[str] = []
    for byte in data:
        if 0x20 <= byte <= 0x7E:
            out.append(chr(byte))
        else:
            out.append(f"\\{byte:03o}")
    return "".join(out)


ENCODERS: dict[str, callable] = {
    "url": encode_url,
    "html": encode_html,
    "unicode_escape": encode_unicode_escape,
    "json": encode_json,
    "c_escape": encode_c_escape,
    "xml": encode_xml,
    "base64": encode_base64,
    "base64url": encode_base64url,
    "hex": encode_hex,
    "octal": encode_octal,
}


def encode(text: str, fmt: str) -> str:
    """Encode text using the specified format.

    Raises ValueError if the format is not recognized.
    """
    encoder = ENCODERS.get(fmt)
    if encoder is None:
        raise ValueError(f"Unknown encoding format: {fmt!r}. Valid formats: {', '.join(FORMATS)}")
    return encoder(text)


# ============================================================
# Decoders
# ============================================================

def decode_url(text: str) -> str:
    """Decode URL percent-encoding."""
    return urllib.parse.unquote(text)


def decode_html(text: str) -> str:
    """Decode HTML entities (named, decimal &#NNN;, hex &#xHHH;)."""
    return html_mod.unescape(text)


def decode_unicode_escape(text: str) -> str:
    r"""Decode \\uXXXX and \\UXXXXXXXX sequences."""
    _pat = re.compile(r"\\U([0-9a-fA-F]{8})|\\u([0-9a-fA-F]{4})")

    def _repl(m: re.Match) -> str:
        if m.group(1) is not None:
            return chr(int(m.group(1), 16))
        return chr(int(m.group(2), 16))

    return _pat.sub(_repl, text)


def decode_json(text: str) -> str:
    r"""Decode JSON escapes. Input is the inner string (no surrounding quotes)."""
    try:
        return json_mod.loads(f'"{text}"')
    except json_mod.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON escape sequence: {e}") from e


def decode_c_escape(text: str) -> str:
    r"""Decode C-style escapes: \\n, \\xHH, \\OOO. UTF-8 byte assembly."""
    _named = {
        "n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"',
        "'": "'", "0": "\0", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
    }
    result: list[str] = []
    pending_bytes: list[int] = []
    i = 0

    def _flush_bytes() -> None:
        if pending_bytes:
            try:
                result.append(bytes(pending_bytes).decode("utf-8"))
            except UnicodeDecodeError:
                result.append(bytes(pending_bytes).decode("latin-1"))
            pending_bytes.clear()

    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            next_ch = text[i + 1]
            if next_ch in _named:
                _flush_bytes()
                result.append(_named[next_ch])
                i += 2
            elif next_ch == "x" and i + 3 < len(text):
                hex_str = text[i + 2 : i + 4]
                try:
                    byte_val = int(hex_str, 16)
                    if byte_val > 0x7F:
                        pending_bytes.append(byte_val)
                    else:
                        _flush_bytes()
                        result.append(chr(byte_val))
                    i += 4
                except ValueError:
                    _flush_bytes()
                    result.append(text[i])
                    i += 1
            elif next_ch in "01234567":
                _flush_bytes()
                end = i + 2
                while end < len(text) and end < i + 4 and text[end] in "01234567":
                    end += 1
                octal_str = text[i + 1 : end]
                result.append(chr(int(octal_str, 8)))
                i = end
            else:
                _flush_bytes()
                result.append(text[i])
                i += 1
        else:
            _flush_bytes()
            result.append(text[i])
            i += 1

    _flush_bytes()
    return "".join(result)


def decode_xml(text: str) -> str:
    """Decode XML entities (&amp; &lt; &gt; &quot; &apos; &#NNN; &#xHHH;)."""
    return html_mod.unescape(text)


def _pad_base64(text: str) -> str:
    """Add missing padding to a base64 string if needed."""
    missing = len(text) % 4
    if missing:
        text += "=" * (4 - missing)
    return text


def decode_base64(text: str, encoding: str = "utf-8") -> str:
    """Decode base64 to a string. Tolerates missing padding."""
    try:
        data = b64.b64decode(_pad_base64(text))
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {e}") from e
    return data.decode(encoding)


def decode_base64url(text: str, encoding: str = "utf-8") -> str:
    """Decode base64url (RFC 4648 section 5). Tolerates missing padding.

    Uses URL-safe alphabet (- instead of +, _ instead of /).
    Used by JWTs and many web APIs.
    """
    try:
        data = b64.urlsafe_b64decode(_pad_base64(text))
    except Exception as e:
        raise ValueError(f"Invalid base64url data: {e}") from e
    return data.decode(encoding)


def decode_hex(text: str, encoding: str = "utf-8") -> str:
    """Decode hex pairs to a string."""
    try:
        data = bytes.fromhex(text)
    except ValueError as e:
        raise ValueError(f"Invalid hex data: {e}") from e
    return data.decode(encoding)


def decode_octal(text: str) -> str:
    r"""Decode \\OOO octal sequences. Non-escaped chars pass through."""
    result: list[str] = []
    pending_bytes: list[int] = []
    i = 0
    pat = re.compile(r"\\([0-7]{1,3})")

    def _flush_bytes() -> None:
        if pending_bytes:
            try:
                result.append(bytes(pending_bytes).decode("utf-8"))
            except UnicodeDecodeError:
                result.append(bytes(pending_bytes).decode("latin-1"))
            pending_bytes.clear()

    while i < len(text):
        m = pat.match(text, i)
        if m:
            byte_val = int(m.group(1), 8)
            if byte_val > 0x7F:
                pending_bytes.append(byte_val)
            else:
                _flush_bytes()
                result.append(chr(byte_val))
            i = m.end()
        else:
            _flush_bytes()
            result.append(text[i])
            i += 1

    _flush_bytes()
    return "".join(result)


DECODERS: dict[str, callable] = {
    "url": decode_url,
    "html": decode_html,
    "unicode_escape": decode_unicode_escape,
    "json": decode_json,
    "c_escape": decode_c_escape,
    "xml": decode_xml,
    "base64": decode_base64,
    "base64url": decode_base64url,
    "hex": decode_hex,
    "octal": decode_octal,
}


def decode(text: str, fmt: str) -> str:
    """Decode text using the specified format.

    Raises ValueError if the format is not recognized.
    """
    decoder = DECODERS.get(fmt)
    if decoder is None:
        raise ValueError(f"Unknown decoding format: {fmt!r}. Valid formats: {', '.join(FORMATS)}")
    return decoder(text)


# ============================================================
# Detector -- auto-detect encoding format
# ============================================================

@dataclass
class Detection:
    """Result of format detection on a string."""

    format: str
    confidence: float  # 0.0 to 1.0
    description: str
    is_double_encoded: bool = False
    inner_format: str | None = None

    def __repr__(self) -> str:
        double = f", double-encoded ({self.inner_format})" if self.is_double_encoded else ""
        return f"Detection({self.format}, confidence={self.confidence:.2f}{double})"


_URL_PATTERN = re.compile(r"%[0-9A-Fa-f]{2}")
_HTML_NAMED_PATTERN = re.compile(
    r"&(amp|lt|gt|quot|apos|nbsp|copy|reg|trade|mdash|ndash|hellip|laquo|raquo"
    r"|bull|euro|pound|yen|cent|sect|deg|micro|para|middot|cedil|sup1|sup2|sup3"
    r"|frac14|frac12|frac34|iexcl|iquest|times|divide);"
)
_HTML_NUMERIC_PATTERN = re.compile(r"&#(\d+|x[0-9A-Fa-f]+);")
_UNICODE_ESCAPE_PATTERN = re.compile(r"\\u[0-9A-Fa-f]{4}|\\U[0-9A-Fa-f]{8}")
_JSON_ESCAPE_PATTERN = re.compile(r'\\[nrtbf\\"/]|\\u[0-9A-Fa-f]{4}')
_C_ESCAPE_PATTERN = re.compile(r"\\[nrtbfav0\\\"]|\\x[0-9A-Fa-f]{2}|\\[0-7]{1,3}")
_XML_PATTERN = re.compile(r"&(amp|lt|gt|quot|apos);|&#(\d+|x[0-9A-Fa-f]+);")
_BASE64_PATTERN = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_BASE64URL_PATTERN = re.compile(r"^[A-Za-z0-9\-_]+={0,2}$")
_HEX_PATTERN = re.compile(r"^[0-9A-Fa-f]+$")
_OCTAL_PATTERN = re.compile(r"\\[0-7]{3}")
_DOUBLE_URL_PATTERN = re.compile(r"%25[0-9A-Fa-f]{2}")
_DOUBLE_HTML_PATTERN = re.compile(r"&amp;(amp|lt|gt|quot|apos|#\d+|#x[0-9A-Fa-f]+);")


def _count_matches(pattern: re.Pattern, text: str) -> int:
    return len(pattern.findall(text))


def _ratio_encoded(pattern: re.Pattern, text: str) -> float:
    if not text:
        return 0.0
    total_matched = sum(len(m.group()) for m in pattern.finditer(text))
    return total_matched / len(text)


def detect_url(text: str) -> Detection | None:
    count = _count_matches(_URL_PATTERN, text)
    if count == 0:
        return None
    ratio = _ratio_encoded(_URL_PATTERN, text)
    confidence = min(0.5 + ratio * 0.5, 1.0)
    if count >= 3:
        confidence = min(confidence + 0.1, 1.0)
    return Detection("url", confidence, f"Found {count} percent-encoded sequence(s)")


def detect_html(text: str) -> Detection | None:
    named_count = _count_matches(_HTML_NAMED_PATTERN, text)
    numeric_count = _count_matches(_HTML_NUMERIC_PATTERN, text)
    total = named_count + numeric_count
    if total == 0:
        return None
    confidence = min(0.6 + total * 0.1, 1.0)
    parts = []
    if named_count:
        parts.append(f"{named_count} named")
    if numeric_count:
        parts.append(f"{numeric_count} numeric")
    desc = f"Found {' and '.join(parts)} HTML entit{'y' if total == 1 else 'ies'}"
    return Detection("html", confidence, desc)


def detect_unicode_escape(text: str) -> Detection | None:
    count = _count_matches(_UNICODE_ESCAPE_PATTERN, text)
    if count == 0:
        return None
    ratio = _ratio_encoded(_UNICODE_ESCAPE_PATTERN, text)
    confidence = min(0.7 + ratio * 0.3, 1.0)
    return Detection("unicode_escape", confidence, f"Found {count} Unicode escape(s)")


def detect_json(text: str) -> Detection | None:
    count = _count_matches(_JSON_ESCAPE_PATTERN, text)
    if count == 0:
        return None
    ratio = _ratio_encoded(_JSON_ESCAPE_PATTERN, text)
    confidence = min(0.5 + ratio * 0.5, 1.0)
    return Detection("json", confidence, f"Found {count} JSON escape(s)")


def detect_c_escape(text: str) -> Detection | None:
    count = _count_matches(_C_ESCAPE_PATTERN, text)
    if count == 0:
        return None
    ratio = _ratio_encoded(_C_ESCAPE_PATTERN, text)
    confidence = min(0.5 + ratio * 0.5, 1.0)
    if re.search(r"\\x[0-9A-Fa-f]{2}", text):
        confidence = min(confidence + 0.1, 1.0)
    return Detection("c_escape", confidence, f"Found {count} C escape(s)")


def detect_xml(text: str) -> Detection | None:
    count = _count_matches(_XML_PATTERN, text)
    if count == 0:
        return None
    confidence = min(0.6 + count * 0.1, 1.0)
    return Detection("xml", confidence, f"Found {count} XML entit{'y' if count == 1 else 'ies'}")


def detect_base64(text: str) -> Detection | None:
    stripped = text.strip()
    if len(stripped) < 4:
        return None
    if not _BASE64_PATTERN.match(stripped):
        return None
    if len(stripped) % 4 != 0:
        return None
    try:
        b64.b64decode(stripped, validate=True)
    except Exception:
        return None
    confidence = 0.3
    if stripped.endswith("="):
        confidence = 0.6
    if stripped.endswith("=="):
        confidence = 0.7
    if len(stripped) >= 20:
        confidence = min(confidence + 0.1, 0.9)
    if "+" in stripped or "/" in stripped:
        confidence = min(confidence + 0.2, 0.95)
    return Detection("base64", confidence, f"Valid base64 ({len(stripped)} chars)")


def detect_base64url(text: str) -> Detection | None:
    """Detect base64url encoding (RFC 4648 section 5).

    Uses - instead of + and _ instead of /. May or may not have padding.
    """
    stripped = text.strip()
    if len(stripped) < 4:
        return None
    if not _BASE64URL_PATTERN.match(stripped):
        return None
    has_url_chars = "-" in stripped or "_" in stripped
    if not has_url_chars:
        return None
    try:
        padded = stripped + "=" * (4 - len(stripped) % 4) if len(stripped) % 4 else stripped
        b64.urlsafe_b64decode(padded)
    except Exception:
        return None
    confidence = 0.5
    if len(stripped) >= 20:
        confidence = 0.6
    if len(stripped) >= 40:
        confidence = 0.7
    return Detection("base64url", confidence, f"Valid base64url ({len(stripped)} chars)")


def detect_hex(text: str) -> Detection | None:
    stripped = text.strip()
    if len(stripped) < 2:
        return None
    if not _HEX_PATTERN.match(stripped):
        return None
    if len(stripped) % 2 != 0:
        return None
    confidence = 0.3
    if len(stripped) >= 6:
        confidence = 0.4
    if len(stripped) >= 20:
        confidence = 0.5
    if re.search(r"[a-fA-F]", stripped):
        confidence = min(confidence + 0.1, 0.7)
    return Detection("hex", confidence, f"Valid hex ({len(stripped)} chars)")


def detect_octal(text: str) -> Detection | None:
    count = _count_matches(_OCTAL_PATTERN, text)
    if count == 0:
        return None
    ratio = _ratio_encoded(_OCTAL_PATTERN, text)
    confidence = min(0.6 + ratio * 0.4, 1.0)
    return Detection("octal", confidence, f"Found {count} octal escape(s)")


def detect_double_url(text: str) -> Detection | None:
    count = _count_matches(_DOUBLE_URL_PATTERN, text)
    if count == 0:
        return None
    return Detection(
        "url", 0.9, f"Found {count} double-encoded URL sequence(s) (e.g., %25XX)",
        is_double_encoded=True, inner_format="url",
    )


def detect_double_html(text: str) -> Detection | None:
    count = _count_matches(_DOUBLE_HTML_PATTERN, text)
    if count == 0:
        return None
    return Detection(
        "html", 0.95, f"Found {count} double-encoded HTML entit{'y' if count == 1 else 'ies'}",
        is_double_encoded=True, inner_format="html",
    )


_DETECTORS = [
    detect_url, detect_html, detect_unicode_escape, detect_json,
    detect_c_escape, detect_xml, detect_base64, detect_base64url,
    detect_hex, detect_octal,
]

_DOUBLE_DETECTORS = [detect_double_url, detect_double_html]


def detect(text: str) -> list[Detection]:
    """Auto-detect which encoding format(s) a string uses.

    Returns a list of Detection objects sorted by confidence (highest first).
    Also checks for double-encoding.
    """
    results: list[Detection] = []

    for detector in _DOUBLE_DETECTORS:
        detection = detector(text)
        if detection is not None:
            results.append(detection)

    for detector in _DETECTORS:
        detection = detector(text)
        if detection is not None:
            results.append(detection)

    results.sort(key=lambda d: d.confidence, reverse=True)
    return results


def detect_best(text: str) -> Detection | None:
    """Return the most likely encoding format. None if nothing detected."""
    results = detect(text)
    return results[0] if results else None


def is_double_encoded(text: str) -> bool:
    """Check if a string appears to be double-encoded."""
    return any(d.is_double_encoded for d in detect(text))


# ============================================================
# Converter -- decode + re-encode
# ============================================================

def convert(text: str, from_format: str, to_format: str) -> str:
    """Convert a string from one escape format to another.

    Decodes from ``from_format``, then encodes to ``to_format``.

    Raises ValueError if either format is not recognized or if decoding fails.
    """
    if from_format not in DECODERS:
        raise ValueError(f"Unknown source format: {from_format!r}. Valid formats: {', '.join(FORMATS)}")
    if to_format not in ENCODERS:
        raise ValueError(f"Unknown target format: {to_format!r}. Valid formats: {', '.join(FORMATS)}")

    decoded = decode(text, from_format)
    return encode(decoded, to_format)


def convert_bulk(texts: list[str], from_format: str, to_format: str) -> list[str]:
    """Convert multiple strings between formats."""
    return [convert(text, from_format, to_format) for text in texts]


def list_formats() -> list[str]:
    """Return the list of supported format names."""
    return list(FORMATS)


# ============================================================
# CLI
# ============================================================

def main():
    """CLI entry point for encoding, decoding, detection, and conversion."""
    import argparse
    import sys

    parser_cli = argparse.ArgumentParser(
        description="Encode, decode, detect, and convert escape formats.",
        usage="python converter.py [command] [options]",
    )
    sub = parser_cli.add_subparsers(dest="command")

    # encode
    enc = sub.add_parser("encode", help="Encode text")
    enc.add_argument("format", choices=FORMATS, help="Target format")
    enc.add_argument("text", help="Text to encode")

    # decode
    dec = sub.add_parser("decode", help="Decode text")
    dec.add_argument("format", choices=FORMATS, help="Source format")
    dec.add_argument("text", help="Text to decode")

    # detect
    det = sub.add_parser("detect", help="Auto-detect encoding format")
    det.add_argument("text", help="Text to analyze")

    # convert
    conv = sub.add_parser("convert", help="Convert between formats")
    conv.add_argument("from_format", choices=FORMATS, help="Source format")
    conv.add_argument("to_format", choices=FORMATS, help="Target format")
    conv.add_argument("text", help="Text to convert")

    # formats
    sub.add_parser("formats", help="List supported formats")

    args = parser_cli.parse_args()

    if args.command == "encode":
        print(encode(args.text, args.format))
    elif args.command == "decode":
        try:
            print(decode(args.text, args.format))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "detect":
        detections = detect(args.text)
        if not detections:
            print("No encoding detected.")
        else:
            for d in detections:
                double = " [DOUBLE-ENCODED]" if d.is_double_encoded else ""
                print(f"  {d.format}: {d.confidence:.0%} - {d.description}{double}")
    elif args.command == "convert":
        try:
            print(convert(args.text, args.from_format, args.to_format))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.command == "formats":
        for fmt in FORMATS:
            print(f"  {fmt}")
    else:
        parser_cli.print_help()


if __name__ == "__main__":
    main()
