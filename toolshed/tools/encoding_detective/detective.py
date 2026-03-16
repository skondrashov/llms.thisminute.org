"""
Encoding Detective — Detect text file encoding without chardet.

BOM analysis, byte pattern heuristics, confidence scoring, encoding
conversion, and mojibake detection/repair. Pure Python, no external
dependencies.

CAPABILITIES
============
1. BOM Detection: UTF-8, UTF-16 LE/BE, UTF-32 LE/BE
2. Encoding Detection: UTF-8 validation, CJK (Shift-JIS, EUC-JP, GB2312,
   Big5), single-byte (Windows-1252, ISO-8859-1/15, KOI8-R)
3. Encoding Conversion: any-to-any with configurable error strategies
4. Mojibake Detection: identifies garbled text from wrong-encoding decode
5. Mojibake Repair: reverses common misinterpretation chains
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════
# BOM (Byte Order Mark) analysis
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class BOMInfo:
    """Information about a detected BOM."""
    encoding: str
    bom_bytes: bytes
    bom_name: str
    bom_length: int
    description: str


# Ordered by length (longest first) so UTF-32 is checked before UTF-16.
BOMS: list[tuple[bytes, str, str, str]] = [
    (b"\x00\x00\xfe\xff", "utf-32-be", "UTF-32 BE BOM", "UTF-32 Big Endian"),
    (b"\xff\xfe\x00\x00", "utf-32-le", "UTF-32 LE BOM", "UTF-32 Little Endian"),
    (b"\xef\xbb\xbf", "utf-8-sig", "UTF-8 BOM", "UTF-8 with BOM"),
    (b"\xfe\xff", "utf-16-be", "UTF-16 BE BOM", "UTF-16 Big Endian"),
    (b"\xff\xfe", "utf-16-le", "UTF-16 LE BOM", "UTF-16 Little Endian"),
]


def detect_bom(data: bytes) -> BOMInfo | None:
    """Detect BOM at the start of byte data."""
    if not data:
        return None
    for bom_bytes, encoding, bom_name, description in BOMS:
        if data.startswith(bom_bytes):
            return BOMInfo(
                encoding=encoding,
                bom_bytes=bom_bytes,
                bom_name=bom_name,
                bom_length=len(bom_bytes),
                description=description,
            )
    return None


def strip_bom(data: bytes) -> tuple[bytes, BOMInfo | None]:
    """Remove BOM from data if present."""
    bom_info = detect_bom(data)
    if bom_info is not None:
        return data[bom_info.bom_length:], bom_info
    return data, None


def get_bom_for_encoding(encoding: str) -> bytes | None:
    """Get the BOM bytes for a given encoding."""
    enc_lower = encoding.lower().replace("_", "-")
    for bom_bytes, enc, _, _ in BOMS:
        if enc_lower == enc:
            return bom_bytes
    return None


def format_bom_report(data: bytes) -> str:
    """Generate a human-readable BOM analysis report."""
    bom_info = detect_bom(data)
    lines: list[str] = ["BOM Analysis", "=" * 40]
    if bom_info is None:
        lines.append("No BOM detected.")
        lines.append("")
        lines.append("First bytes (hex): " + _hex_preview(data, 16))
        lines.append("")
        lines.append(
            "Note: Many valid text files have no BOM. "
            "Use byte pattern analysis for encoding detection."
        )
    else:
        lines.append(f"BOM found: {bom_info.bom_name}")
        lines.append(f"Encoding: {bom_info.description}")
        lines.append(f"BOM bytes: {_format_bytes(bom_info.bom_bytes)}")
        lines.append(f"BOM length: {bom_info.bom_length} bytes")
        lines.append("")
        lines.append(f"Content after BOM: {len(data) - bom_info.bom_length} bytes")
    return "\n".join(lines)


def _hex_preview(data: bytes, max_bytes: int = 16) -> str:
    if not data:
        return "(empty)"
    preview = data[:max_bytes]
    hex_str = " ".join(f"{b:02X}" for b in preview)
    if len(data) > max_bytes:
        hex_str += " ..."
    return hex_str


def _format_bytes(data: bytes) -> str:
    return " ".join(f"0x{b:02X}" for b in data)


# ═══════════════════════════════════════════════════════════════════
# Encoding detection
# ═══════════════════════════════════════════════════════════════════

@dataclass
class EncodingResult:
    """Result of encoding detection."""
    encoding: str
    confidence: float
    method: str
    details: str
    bom_info: BOMInfo | None = None


@dataclass
class DetectionReport:
    """Full detection report with all candidates."""
    best: EncodingResult
    candidates: list[EncodingResult] = field(default_factory=list)
    file_size: int = 0
    sample_size: int = 0

    def format_report(self) -> str:
        lines: list[str] = [
            "Encoding Detection Report",
            "=" * 50,
            f"File size: {self.file_size} bytes",
            f"Sample size: {self.sample_size} bytes",
            "",
            f"Detected encoding: {self.best.encoding}",
            f"Confidence: {self.best.confidence:.0%}",
            f"Method: {self.best.method}",
            f"Details: {self.best.details}",
        ]
        if self.best.bom_info:
            lines.append(f"BOM: {self.best.bom_info.bom_name}")
        if len(self.candidates) > 1:
            lines.append("")
            lines.append("All candidates:")
            for i, c in enumerate(self.candidates, 1):
                lines.append(f"  {i}. {c.encoding} ({c.confidence:.0%}) — {c.method}")
        return "\n".join(lines)


MAX_SAMPLE_SIZE = 65536


def detect_encoding(data: bytes, sample_size: int = MAX_SAMPLE_SIZE) -> DetectionReport:
    """Detect the encoding of byte data."""
    if not data:
        return DetectionReport(
            best=EncodingResult(encoding="ascii", confidence=1.0, method="empty",
                                details="Empty input — defaulting to ASCII."),
            candidates=[], file_size=0, sample_size=0,
        )
    file_size = len(data)
    sample = data[:sample_size]
    candidates: list[EncodingResult] = []

    # Step 1: BOM
    bom_info = detect_bom(sample)
    if bom_info is not None:
        result = EncodingResult(encoding=bom_info.encoding, confidence=1.0,
                                method="bom", details=f"Detected {bom_info.bom_name}.",
                                bom_info=bom_info)
        candidates.append(result)
        return DetectionReport(best=result, candidates=candidates,
                               file_size=file_size, sample_size=len(sample))

    # Step 2: ASCII
    if _is_ascii(sample):
        result = EncodingResult(encoding="ascii", confidence=1.0, method="ascii",
                                details="All bytes are in the ASCII range (0x00-0x7F).")
        candidates.append(result)
        return DetectionReport(best=result, candidates=candidates,
                               file_size=file_size, sample_size=len(sample))

    # Step 3: UTF-8
    utf8_result = _check_utf8(sample)
    if utf8_result is not None:
        candidates.append(utf8_result)

    # Step 4: CJK
    for check_fn in [_check_shift_jis, _check_euc_jp, _check_gb2312, _check_big5]:
        result = check_fn(sample)
        if result is not None:
            candidates.append(result)

    # Step 5: Single-byte
    for check_fn_sb in [_check_windows_1252, _check_iso_8859_15, _check_koi8_r]:
        result = check_fn_sb(sample)
        if result is not None:
            candidates.append(result)

    # Step 6: Latin-1 fallback
    candidates.append(EncodingResult(
        encoding="iso-8859-1", confidence=0.1, method="fallback",
        details="Latin-1 is valid for any byte sequence (fallback).",
    ))

    candidates.sort(key=lambda c: c.confidence, reverse=True)

    # Deduplicate
    seen: set[str] = set()
    deduped: list[EncodingResult] = []
    for c in candidates:
        if c.encoding not in seen:
            seen.add(c.encoding)
            deduped.append(c)
    candidates = deduped

    return DetectionReport(best=candidates[0], candidates=candidates,
                           file_size=file_size, sample_size=len(sample))


def detect_encoding_from_file(filepath: str, sample_size: int = MAX_SAMPLE_SIZE) -> DetectionReport:
    """Detect encoding of a file."""
    with open(filepath, "rb") as f:
        data = f.read(sample_size)
    report = detect_encoding(data, sample_size)
    report.file_size = os.path.getsize(filepath)
    return report


def _is_ascii(data: bytes) -> bool:
    return all(b < 0x80 for b in data)


def _check_utf8(data: bytes) -> EncodingResult | None:
    i = 0
    length = len(data)
    multibyte_count = 0
    two_byte = 0
    three_byte = 0
    four_byte = 0
    total_non_ascii = 0

    while i < length:
        b = data[i]
        if b < 0x80:
            i += 1
            continue
        total_non_ascii += 1
        if 0xC2 <= b <= 0xDF:
            if i + 1 >= length:
                return None
            if not (0x80 <= data[i + 1] <= 0xBF):
                return None
            two_byte += 1
            multibyte_count += 1
            i += 2
        elif 0xE0 <= b <= 0xEF:
            if i + 2 >= length:
                return None
            b1, b2 = data[i + 1], data[i + 2]
            if not (0x80 <= b1 <= 0xBF and 0x80 <= b2 <= 0xBF):
                return None
            if b == 0xE0 and b1 < 0xA0:
                return None
            if b == 0xED and b1 > 0x9F:
                return None
            three_byte += 1
            multibyte_count += 1
            i += 3
        elif 0xF0 <= b <= 0xF4:
            if i + 3 >= length:
                return None
            b1, b2, b3 = data[i + 1], data[i + 2], data[i + 3]
            if not (0x80 <= b1 <= 0xBF and 0x80 <= b2 <= 0xBF and 0x80 <= b3 <= 0xBF):
                return None
            if b == 0xF0 and b1 < 0x90:
                return None
            if b == 0xF4 and b1 > 0x8F:
                return None
            four_byte += 1
            multibyte_count += 1
            i += 4
        else:
            return None

    if multibyte_count == 0:
        return None

    ratio = multibyte_count / max(total_non_ascii, 1)
    confidence = min(0.95, 0.7 + 0.25 * ratio)
    details_parts = [f"Valid UTF-8: {multibyte_count} multi-byte sequences"]
    if two_byte:
        details_parts.append(f"{two_byte} two-byte")
    if three_byte:
        details_parts.append(f"{three_byte} three-byte")
    if four_byte:
        details_parts.append(f"{four_byte} four-byte")
    return EncodingResult(encoding="utf-8", confidence=confidence,
                          method="utf8-validation", details=", ".join(details_parts) + ".")


def _check_shift_jis(data: bytes) -> EncodingResult | None:
    i, length = 0, len(data)
    double_byte_count = half_width_katakana = invalid = 0
    while i < length:
        b = data[i]
        if b < 0x80:
            i += 1; continue
        if 0xA1 <= b <= 0xDF:
            half_width_katakana += 1; i += 1; continue
        if (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xEF):
            if i + 1 >= length:
                invalid += 1; break
            trail = data[i + 1]
            if (0x40 <= trail <= 0x7E) or (0x80 <= trail <= 0xFC):
                double_byte_count += 1; i += 2; continue
            else:
                invalid += 1; i += 1; continue
        invalid += 1; i += 1
    total_special = double_byte_count + half_width_katakana
    if total_special == 0 or invalid > total_special * 0.1:
        return None
    confidence = min(0.85, 0.5 + 0.35 * (total_special / max(total_special + invalid, 1)))
    return EncodingResult(encoding="shift_jis", confidence=confidence, method="shift-jis-patterns",
                          details=f"{double_byte_count} double-byte sequences, {half_width_katakana} half-width katakana, {invalid} invalid bytes.")


def _check_euc_jp(data: bytes) -> EncodingResult | None:
    i, length = 0, len(data)
    double_byte_count = cs2_count = cs3_count = invalid = 0
    while i < length:
        b = data[i]
        if b < 0x80:
            i += 1; continue
        if 0xA1 <= b <= 0xFE:
            if i + 1 >= length:
                invalid += 1; break
            if 0xA1 <= data[i + 1] <= 0xFE:
                double_byte_count += 1; i += 2; continue
            else:
                invalid += 1; i += 1; continue
        if b == 0x8E:
            if i + 1 >= length:
                invalid += 1; break
            if 0xA1 <= data[i + 1] <= 0xDF:
                cs2_count += 1; i += 2; continue
            else:
                invalid += 1; i += 1; continue
        if b == 0x8F:
            if i + 2 >= length:
                invalid += 1; break
            if 0xA1 <= data[i + 1] <= 0xFE and 0xA1 <= data[i + 2] <= 0xFE:
                cs3_count += 1; i += 3; continue
            else:
                invalid += 1; i += 1; continue
        invalid += 1; i += 1
    total_special = double_byte_count + cs2_count + cs3_count
    if total_special == 0 or invalid > total_special * 0.1:
        return None
    confidence = min(0.85, 0.5 + 0.35 * (total_special / max(total_special + invalid, 1)))
    return EncodingResult(encoding="euc-jp", confidence=confidence, method="euc-jp-patterns",
                          details=f"{double_byte_count} double-byte, {cs2_count} katakana, {cs3_count} JIS X 0212, {invalid} invalid.")


def _check_gb2312(data: bytes) -> EncodingResult | None:
    i, length = 0, len(data)
    double_byte_count = invalid = 0
    while i < length:
        b = data[i]
        if b < 0x80:
            i += 1; continue
        if 0x81 <= b <= 0xFE:
            if i + 1 >= length:
                invalid += 1; break
            trail = data[i + 1]
            if (0x40 <= trail <= 0xFE) and trail != 0x7F:
                double_byte_count += 1; i += 2; continue
            else:
                invalid += 1; i += 1; continue
        invalid += 1; i += 1
    if double_byte_count == 0 or invalid > double_byte_count * 0.1:
        return None
    confidence = min(0.80, 0.45 + 0.35 * (double_byte_count / max(double_byte_count + invalid, 1)))
    return EncodingResult(encoding="gb2312", confidence=confidence, method="gb2312-patterns",
                          details=f"{double_byte_count} double-byte sequences, {invalid} invalid bytes.")


def _check_big5(data: bytes) -> EncodingResult | None:
    i, length = 0, len(data)
    double_byte_count = invalid = 0
    while i < length:
        b = data[i]
        if b < 0x80:
            i += 1; continue
        if 0x81 <= b <= 0xFE:
            if i + 1 >= length:
                invalid += 1; break
            trail = data[i + 1]
            if (0x40 <= trail <= 0x7E) or (0xA1 <= trail <= 0xFE):
                double_byte_count += 1; i += 2; continue
            else:
                invalid += 1; i += 1; continue
        invalid += 1; i += 1
    if double_byte_count == 0 or invalid > double_byte_count * 0.1:
        return None
    confidence = min(0.80, 0.45 + 0.35 * (double_byte_count / max(double_byte_count + invalid, 1)))
    return EncodingResult(encoding="big5", confidence=confidence, method="big5-patterns",
                          details=f"{double_byte_count} double-byte sequences, {invalid} invalid bytes.")


def _check_windows_1252(data: bytes) -> EncodingResult | None:
    high_byte_count = cp1252_range_count = 0
    cp1252_printable = {0x80, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B, 0x8C,
                        0x8E, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B,
                        0x9C, 0x9E, 0x9F}
    cp1252_undefined = {0x81, 0x8D, 0x8F, 0x90, 0x9D}
    for b in data:
        if b >= 0x80:
            high_byte_count += 1
            if b in cp1252_printable:
                cp1252_range_count += 1
            elif b in cp1252_undefined:
                return None
    if high_byte_count == 0 or cp1252_range_count == 0:
        return None
    ratio = cp1252_range_count / high_byte_count
    confidence = min(0.85, 0.5 + 0.35 * ratio)
    return EncodingResult(encoding="windows-1252", confidence=confidence, method="cp1252-heuristic",
                          details=f"{cp1252_range_count} Windows-1252-specific bytes in 0x80-0x9F range out of {high_byte_count} high bytes.")


def _check_iso_8859_15(data: bytes) -> EncodingResult | None:
    iso_8859_15_specific = {0xA4, 0xA6, 0xA8, 0xB4, 0xB8, 0xBC, 0xBD, 0xBE}
    high_byte_count = iso15_specific_count = 0
    for b in data:
        if b >= 0x80:
            high_byte_count += 1
            if b in iso_8859_15_specific:
                iso15_specific_count += 1
    if high_byte_count == 0 or iso15_specific_count == 0:
        return None
    confidence = min(0.4, 0.2 + 0.1 * iso15_specific_count)
    return EncodingResult(encoding="iso-8859-15", confidence=confidence, method="iso-8859-15-heuristic",
                          details=f"{iso15_specific_count} bytes at ISO-8859-15/Latin-1 divergence points out of {high_byte_count} high bytes.")


def _check_koi8_r(data: bytes) -> EncodingResult | None:
    high_byte_count = koi8_cyrillic_count = 0
    for b in data:
        if b >= 0x80:
            high_byte_count += 1
            if 0xC0 <= b <= 0xFF:
                koi8_cyrillic_count += 1
    if high_byte_count == 0 or koi8_cyrillic_count == 0:
        return None
    ratio = koi8_cyrillic_count / high_byte_count
    if ratio < 0.7:
        return None
    confidence = min(0.7, 0.4 + 0.3 * ratio)
    return EncodingResult(encoding="koi8-r", confidence=confidence, method="koi8-r-heuristic",
                          details=f"{koi8_cyrillic_count} bytes in KOI8-R Cyrillic range (0xC0-0xFF) out of {high_byte_count} high bytes.")


# ═══════════════════════════════════════════════════════════════════
# Encoding conversion
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ConversionResult:
    """Result of an encoding conversion."""
    source_encoding: str
    target_encoding: str
    original_size: int
    converted_size: int
    errors: list[str]
    data: bytes


def convert_bytes(
    data: bytes,
    source_encoding: str,
    target_encoding: str,
    error_strategy: str = "strict",
) -> ConversionResult:
    """Convert bytes from one encoding to another."""
    errors: list[str] = []
    original_size = len(data)
    source_enc = _normalize_encoding(source_encoding)
    target_enc = _normalize_encoding(target_encoding)

    stripped_data, bom_info = strip_bom(data)
    if bom_info:
        bom_enc = bom_info.encoding.lower().replace("-", "_")
        src_norm = source_enc.lower().replace("-", "_")
        if bom_enc.startswith(src_norm) or src_norm.startswith(bom_enc.replace("_sig", "")):
            data = stripped_data

    text = data.decode(source_enc, errors=error_strategy)
    converted = text.encode(target_enc, errors=error_strategy)

    target_bom = get_bom_for_encoding(target_enc)
    if target_bom is not None:
        converted = target_bom + converted

    return ConversionResult(source_encoding=source_enc, target_encoding=target_enc,
                            original_size=original_size, converted_size=len(converted),
                            errors=errors, data=converted)


def convert_file(
    source_path: str,
    target_path: str | None = None,
    source_encoding: str | None = None,
    target_encoding: str = "utf-8",
    error_strategy: str = "strict",
) -> ConversionResult:
    """Convert a file from one encoding to another."""
    source = Path(source_path)
    data = source.read_bytes()
    if source_encoding is None:
        report = detect_encoding(data)
        source_encoding = report.best.encoding
    result = convert_bytes(data, source_encoding, target_encoding, error_strategy)
    if target_path is not None:
        Path(target_path).write_bytes(result.data)
    return result


def _normalize_encoding(encoding: str) -> str:
    enc = encoding.lower().strip()
    aliases: dict[str, str] = {
        "latin1": "iso-8859-1", "latin-1": "iso-8859-1", "iso8859-1": "iso-8859-1",
        "iso_8859_1": "iso-8859-1", "iso88591": "iso-8859-1",
        "latin9": "iso-8859-15", "latin-9": "iso-8859-15", "iso8859-15": "iso-8859-15",
        "iso_8859_15": "iso-8859-15",
        "cp1252": "windows-1252", "cp-1252": "windows-1252", "win1252": "windows-1252",
        "utf8": "utf-8", "utf-8-bom": "utf-8-sig", "utf8bom": "utf-8-sig", "utf8-bom": "utf-8-sig",
        "utf16": "utf-16", "utf-16le": "utf-16-le", "utf-16be": "utf-16-be",
        "utf16le": "utf-16-le", "utf16be": "utf-16-be",
        "utf32": "utf-32", "utf-32le": "utf-32-le", "utf-32be": "utf-32-be",
        "utf32le": "utf-32-le", "utf32be": "utf-32-be",
        "sjis": "shift_jis", "shift-jis": "shift_jis", "shiftjis": "shift_jis",
        "eucjp": "euc-jp", "euc_jp": "euc-jp",
        "gb2312": "gb2312", "gbk": "gbk",
        "koi8r": "koi8-r", "koi8_r": "koi8-r",
        "ascii": "ascii", "us-ascii": "ascii",
    }
    return aliases.get(enc, enc)


def format_conversion_report(result: ConversionResult) -> str:
    lines = ["Encoding Conversion Report", "=" * 40,
             f"Source encoding: {result.source_encoding}",
             f"Target encoding: {result.target_encoding}",
             f"Original size: {result.original_size} bytes",
             f"Converted size: {result.converted_size} bytes"]
    if result.errors:
        lines.append("")
        lines.append("Warnings:")
        for error in result.errors:
            lines.append(f"  - {error}")
    else:
        lines.append("Status: Success (no errors)")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Mojibake detection and repair
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MojibakeResult:
    """Result of mojibake analysis."""
    is_mojibake: bool
    original_text: str
    fixed_text: str | None
    encoding_chain: list[str]
    confidence: float
    explanation: str


COMMON_CHAINS: list[tuple[str, str, list[str]]] = [
    ("utf-8", "iso-8859-1", ["Text was UTF-8, decoded as Latin-1"]),
    ("utf-8", "windows-1252", ["Text was UTF-8, decoded as Windows-1252"]),
    ("utf-8", "iso-8859-15", ["Text was UTF-8, decoded as ISO-8859-15"]),
]


def detect_mojibake(text: str) -> MojibakeResult:
    """Detect if text appears to be mojibake and try to fix it."""
    if not text:
        return MojibakeResult(is_mojibake=False, original_text=text, fixed_text=None,
                              encoding_chain=[], confidence=0.0, explanation="Empty input.")

    double_result = _check_double_encoding(text)
    if double_result is not None:
        return double_result

    for correct_enc, wrong_enc, chain_desc in COMMON_CHAINS:
        result = _try_fix_chain(text, wrong_enc, correct_enc, chain_desc)
        if result is not None:
            return result

    mojibake_score = _score_mojibake_likelihood(text)
    if mojibake_score > 0.5:
        return MojibakeResult(is_mojibake=True, original_text=text, fixed_text=None,
                              encoding_chain=[], confidence=mojibake_score,
                              explanation="Text appears garbled but the encoding chain could not be determined.")

    return MojibakeResult(is_mojibake=False, original_text=text, fixed_text=None,
                          encoding_chain=[], confidence=0.0,
                          explanation="Text does not appear to be mojibake.")


def detect_mojibake_bytes(data: bytes) -> MojibakeResult:
    """Detect mojibake from raw bytes."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("iso-8859-1")
        except UnicodeDecodeError:
            return MojibakeResult(is_mojibake=False, original_text="", fixed_text=None,
                                  encoding_chain=[], confidence=0.0,
                                  explanation="Could not decode bytes with UTF-8 or Latin-1.")
    return detect_mojibake(text)


def fix_mojibake(text: str, wrong_encoding: str, correct_encoding: str) -> str:
    """Fix mojibake by re-encoding with the wrong encoding and decoding with the correct one."""
    raw = text.encode(wrong_encoding)
    return raw.decode(correct_encoding)


def _try_fix_chain(text: str, wrong_enc: str, correct_enc: str,
                   chain_desc: list[str]) -> MojibakeResult | None:
    try:
        raw_bytes = text.encode(wrong_enc)
        fixed = raw_bytes.decode(correct_enc)
    except (UnicodeDecodeError, UnicodeEncodeError):
        return None
    original_score = _score_mojibake_likelihood(text)
    fixed_score = _score_mojibake_likelihood(fixed)
    if original_score >= 0.2 and fixed_score < original_score * 0.7:
        return MojibakeResult(
            is_mojibake=True, original_text=text, fixed_text=fixed,
            encoding_chain=chain_desc, confidence=min(0.95, original_score + 0.2),
            explanation=(f"Text appears to be {correct_enc} data that was decoded as {wrong_enc}. "
                         f"Re-encoding as {wrong_enc} and decoding as {correct_enc} produces readable text."),
        )
    return None


def _check_double_encoding(text: str) -> MojibakeResult | None:
    try:
        step1 = text.encode("iso-8859-1")
    except UnicodeEncodeError:
        try:
            step1 = text.encode("windows-1252")
        except UnicodeEncodeError:
            return None
    try:
        step2 = step1.decode("utf-8")
    except UnicodeDecodeError:
        return None
    try:
        step3_bytes = step2.encode("iso-8859-1")
        step3 = step3_bytes.decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return None
    fixed_score = _score_mojibake_likelihood(step3)
    if step3 != text and fixed_score < 0.2:
        return MojibakeResult(
            is_mojibake=True, original_text=text, fixed_text=step3,
            encoding_chain=["UTF-8 text was decoded as Latin-1, then re-encoded as UTF-8 (double-encoding)"],
            confidence=0.90,
            explanation=("Text is double-encoded UTF-8: the original UTF-8 bytes were misread as Latin-1 "
                         "and then re-encoded as UTF-8. Fixed by reversing both layers."),
        )
    return None


def _score_mojibake_likelihood(text: str) -> float:
    if not text:
        return 0.0
    score = 0.0
    length = len(text)
    mojibake_chars = control_chars = replacement_chars = 0
    mojibake_patterns = [
        "\u00c3\u00a9", "\u00c3\u00a8", "\u00c3\u00a0", "\u00c3\u00b6", "\u00c3\u00bc",
        "\u00c3\u00a4", "\u00c3\u00b1", "\u00c3\u00a7", "\u00c3\u00ad", "\u00c3\u00b3",
        "\u00c3\u00ba", "\u00c3\u00ab", "\u00c3\u00af", "\u00c3\u00bf",
        "\u00c3\u0089", "\u00c3\u0080", "\u00c3\u0096", "\u00c3\u009c",
        "\u00c3\u0084", "\u00c3\u0091",
        "\u00c2\u00a0", "\u00c2\u00ab", "\u00c2\u00bb", "\u00c2\u00b0",
        "\u00e2\u0080\u0099", "\u00e2\u0080\u009c", "\u00e2\u0080\u009d",
        "\u00e2\u0080\u0093", "\u00e2\u0080\u0094", "\u00e2\u0080\u00a6",
        "\u00e2\u0082\u00ac",
    ]
    pattern_hits = sum(text.count(p) for p in mojibake_patterns)
    for ch in text:
        cp = ord(ch)
        if cp == 0xFFFD:
            replacement_chars += 1
        elif cp < 0x20 and cp not in (0x09, 0x0A, 0x0D):
            control_chars += 1
        elif 0x80 <= cp <= 0x9F:
            mojibake_chars += 1
    if length > 0:
        if pattern_hits > 0:
            score += min(0.7, 0.4 + 0.15 * (pattern_hits - 1))
        if replacement_chars > 0:
            score += min(0.3, 0.15 * replacement_chars)
        if mojibake_chars > 0:
            score += min(0.3, 0.15 * mojibake_chars / max(1, length / 5))
        if control_chars > 0:
            score += min(0.2, 0.05 * control_chars)
    return min(1.0, score)


def format_mojibake_report(result: MojibakeResult) -> str:
    lines = ["Mojibake Analysis", "=" * 40, f"Input: {_truncate(result.original_text, 80)}", ""]
    if not result.is_mojibake:
        lines.append("Result: No mojibake detected.")
        lines.append(f"Confidence: {result.confidence:.0%}")
    else:
        lines.append("Result: MOJIBAKE DETECTED")
        lines.append(f"Confidence: {result.confidence:.0%}")
        lines.append("")
        if result.encoding_chain:
            lines.append("What happened:")
            for step in result.encoding_chain:
                lines.append(f"  - {step}")
            lines.append("")
        lines.append(f"Explanation: {result.explanation}")
        if result.fixed_text is not None:
            lines.append("")
            lines.append(f"Fixed text: {_truncate(result.fixed_text, 80)}")
            lines.append("")
            lines.append("Byte comparison:")
            lines.append(f"  Original bytes: {_hex_str(result.original_text, 32)}")
            if result.fixed_text:
                lines.append(f"  Fixed bytes:    {_hex_str(result.fixed_text, 32)}")
        else:
            lines.append("")
            lines.append("Could not determine the correct encoding to fix this.")
    return "\n".join(lines)


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return repr(text)
    return repr(text[:max_len]) + "..."


def _hex_str(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    preview = encoded[:max_bytes]
    hex_str = " ".join(f"{b:02X}" for b in preview)
    if len(encoded) > max_bytes:
        hex_str += " ..."
    return hex_str
