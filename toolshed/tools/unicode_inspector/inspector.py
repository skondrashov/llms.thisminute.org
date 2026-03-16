"""
Unicode Inspector — Inspect, detect, and normalize Unicode characters.

Character inspection, invisible character detection, normalization
comparison, and confusable/homoglyph detection. Pure Python, stdlib only.

CAPABILITIES
============
1. Character Inspection: codepoint, name, category, block, script, encoding bytes
2. Invisible Detection: zero-width, directional marks, control chars, BOMs
3. Normalization: NFC/NFD/NFKC/NFKD with before/after comparison
4. Confusables: cross-script lookalikes (Latin/Cyrillic/Greek), mixed-script detection
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════════
# Character inspection
# ═══════════════════════════════════════════════════════════════════

_BLOCKS: list[tuple[int, int, str]] = [
    (0x0000, 0x007F, "Basic Latin"),
    (0x0080, 0x00FF, "Latin-1 Supplement"),
    (0x0100, 0x017F, "Latin Extended-A"),
    (0x0180, 0x024F, "Latin Extended-B"),
    (0x0250, 0x02AF, "IPA Extensions"),
    (0x02B0, 0x02FF, "Spacing Modifier Letters"),
    (0x0300, 0x036F, "Combining Diacritical Marks"),
    (0x0370, 0x03FF, "Greek and Coptic"),
    (0x0400, 0x04FF, "Cyrillic"),
    (0x0500, 0x052F, "Cyrillic Supplement"),
    (0x0530, 0x058F, "Armenian"),
    (0x0590, 0x05FF, "Hebrew"),
    (0x0600, 0x06FF, "Arabic"),
    (0x0700, 0x074F, "Syriac"),
    (0x0900, 0x097F, "Devanagari"),
    (0x0980, 0x09FF, "Bengali"),
    (0x0A00, 0x0A7F, "Gurmukhi"),
    (0x0A80, 0x0AFF, "Gujarati"),
    (0x0B00, 0x0B7F, "Oriya"),
    (0x0B80, 0x0BFF, "Tamil"),
    (0x0C00, 0x0C7F, "Telugu"),
    (0x0C80, 0x0CFF, "Kannada"),
    (0x0D00, 0x0D7F, "Malayalam"),
    (0x0D80, 0x0DFF, "Sinhala"),
    (0x0E00, 0x0E7F, "Thai"),
    (0x0E80, 0x0EFF, "Lao"),
    (0x0F00, 0x0FFF, "Tibetan"),
    (0x1000, 0x109F, "Myanmar"),
    (0x10A0, 0x10FF, "Georgian"),
    (0x1100, 0x11FF, "Hangul Jamo"),
    (0x1200, 0x137F, "Ethiopic"),
    (0x13A0, 0x13FF, "Cherokee"),
    (0x1680, 0x169F, "Ogham"),
    (0x16A0, 0x16FF, "Runic"),
    (0x1780, 0x17FF, "Khmer"),
    (0x1800, 0x18AF, "Mongolian"),
    (0x1E00, 0x1EFF, "Latin Extended Additional"),
    (0x1F00, 0x1FFF, "Greek Extended"),
    (0x2000, 0x206F, "General Punctuation"),
    (0x2070, 0x209F, "Superscripts and Subscripts"),
    (0x20A0, 0x20CF, "Currency Symbols"),
    (0x2100, 0x214F, "Letterlike Symbols"),
    (0x2150, 0x218F, "Number Forms"),
    (0x2190, 0x21FF, "Arrows"),
    (0x2200, 0x22FF, "Mathematical Operators"),
    (0x2300, 0x23FF, "Miscellaneous Technical"),
    (0x2460, 0x24FF, "Enclosed Alphanumerics"),
    (0x2500, 0x257F, "Box Drawing"),
    (0x2580, 0x259F, "Block Elements"),
    (0x25A0, 0x25FF, "Geometric Shapes"),
    (0x2600, 0x26FF, "Miscellaneous Symbols"),
    (0x2700, 0x27BF, "Dingbats"),
    (0x2800, 0x28FF, "Braille Patterns"),
    (0x3000, 0x303F, "CJK Symbols and Punctuation"),
    (0x3040, 0x309F, "Hiragana"),
    (0x30A0, 0x30FF, "Katakana"),
    (0x3100, 0x312F, "Bopomofo"),
    (0x3130, 0x318F, "Hangul Compatibility Jamo"),
    (0x3400, 0x4DBF, "CJK Unified Ideographs Extension A"),
    (0x4E00, 0x9FFF, "CJK Unified Ideographs"),
    (0xAC00, 0xD7AF, "Hangul Syllables"),
    (0xE000, 0xF8FF, "Private Use Area"),
    (0xFE00, 0xFE0F, "Variation Selectors"),
    (0xFF00, 0xFFEF, "Halfwidth and Fullwidth Forms"),
    (0xFFF0, 0xFFFF, "Specials"),
    (0x1F300, 0x1F5FF, "Miscellaneous Symbols and Pictographs"),
    (0x1F600, 0x1F64F, "Emoticons"),
    (0x1F680, 0x1F6FF, "Transport and Map Symbols"),
    (0x1F900, 0x1F9FF, "Supplemental Symbols and Pictographs"),
    (0x1D400, 0x1D7FF, "Mathematical Alphanumeric Symbols"),
    (0xE0000, 0xE007F, "Tags"),
    (0xE0100, 0xE01EF, "Variation Selectors Supplement"),
    (0xF0000, 0xFFFFF, "Supplementary Private Use Area-A"),
    (0x100000, 0x10FFFF, "Supplementary Private Use Area-B"),
]

CATEGORY_NAMES: dict[str, str] = {
    "Lu": "Letter, uppercase", "Ll": "Letter, lowercase", "Lt": "Letter, titlecase",
    "Lm": "Letter, modifier", "Lo": "Letter, other",
    "Mn": "Mark, nonspacing", "Mc": "Mark, spacing combining", "Me": "Mark, enclosing",
    "Nd": "Number, decimal digit", "Nl": "Number, letter", "No": "Number, other",
    "Pc": "Punctuation, connector", "Pd": "Punctuation, dash",
    "Ps": "Punctuation, open", "Pe": "Punctuation, close",
    "Pi": "Punctuation, initial quote", "Pf": "Punctuation, final quote",
    "Po": "Punctuation, other",
    "Sm": "Symbol, math", "Sc": "Symbol, currency", "Sk": "Symbol, modifier", "So": "Symbol, other",
    "Zs": "Separator, space", "Zl": "Separator, line", "Zp": "Separator, paragraph",
    "Cc": "Other, control", "Cf": "Other, format", "Cs": "Other, surrogate",
    "Co": "Other, private use", "Cn": "Other, not assigned",
}


@dataclass
class CharInfo:
    char: str
    codepoint: int
    codepoint_str: str
    name: str
    category: str
    category_description: str
    block: str
    script: str
    utf8_bytes: bytes
    utf16_bytes: bytes
    utf32_bytes: bytes
    bidirectional: str
    combining_class: int
    decomposition: str
    is_printable: bool
    east_asian_width: str
    mirrored: bool


def get_codepoint_str(cp: int) -> str:
    return f"U+{cp:04X}" if cp <= 0xFFFF else f"U+{cp:06X}"


def get_block(cp: int) -> str:
    for start, end, name in _BLOCKS:
        if start <= cp <= end:
            return name
    return "Unknown"


def get_script(cp: int) -> str:
    block = get_block(cp)
    script_map = {
        "Basic Latin": "Latin", "Latin-1 Supplement": "Latin", "Latin Extended-A": "Latin",
        "Latin Extended-B": "Latin", "Latin Extended Additional": "Latin",
        "Greek and Coptic": "Greek", "Greek Extended": "Greek",
        "Cyrillic": "Cyrillic", "Cyrillic Supplement": "Cyrillic",
        "Armenian": "Armenian", "Hebrew": "Hebrew",
        "Arabic": "Arabic", "Syriac": "Syriac",
        "Devanagari": "Devanagari", "Bengali": "Bengali", "Tamil": "Tamil",
        "Telugu": "Telugu", "Kannada": "Kannada", "Malayalam": "Malayalam",
        "Thai": "Thai", "Lao": "Lao", "Tibetan": "Tibetan",
        "Georgian": "Georgian", "Myanmar": "Myanmar", "Sinhala": "Sinhala",
        "Khmer": "Khmer", "Mongolian": "Mongolian",
        "Hangul Jamo": "Hangul", "Hangul Syllables": "Hangul", "Hangul Compatibility Jamo": "Hangul",
        "Hiragana": "Hiragana", "Katakana": "Katakana",
        "CJK Unified Ideographs": "Han", "CJK Unified Ideographs Extension A": "Han",
        "Ethiopic": "Ethiopic", "Cherokee": "Cherokee", "Runic": "Runic", "Ogham": "Ogham",
        "Thaana": "Thaana", "NKo": "NKo", "Gurmukhi": "Gurmukhi", "Gujarati": "Gujarati",
        "Oriya": "Oriya",
    }
    return script_map.get(block, "Common")


def get_utf8_bytes(char: str) -> bytes:
    return char.encode("utf-8")


def get_utf16_bytes(char: str) -> bytes:
    return char.encode("utf-16-be")


def get_utf32_bytes(char: str) -> bytes:
    return char.encode("utf-32-be")


def inspect_char(char: str) -> CharInfo:
    if len(char) != 1:
        raise ValueError(f"Expected a single character, got {len(char)} characters")
    cp = ord(char)
    category = unicodedata.category(char)
    try:
        name = unicodedata.name(char)
    except ValueError:
        name = f"<{CATEGORY_NAMES.get(category, 'unknown')}>"
    return CharInfo(
        char=char, codepoint=cp, codepoint_str=get_codepoint_str(cp), name=name,
        category=category, category_description=CATEGORY_NAMES.get(category, "Unknown"),
        block=get_block(cp), script=get_script(cp),
        utf8_bytes=get_utf8_bytes(char), utf16_bytes=get_utf16_bytes(char),
        utf32_bytes=get_utf32_bytes(char),
        bidirectional=unicodedata.bidirectional(char),
        combining_class=unicodedata.combining(char),
        decomposition=unicodedata.decomposition(char),
        is_printable=char.isprintable(),
        east_asian_width=unicodedata.east_asian_width(char),
        mirrored=bool(unicodedata.mirrored(char)),
    )


def inspect_string(text: str) -> list[CharInfo]:
    return [inspect_char(c) for c in text]


def format_char_info(info: CharInfo) -> str:
    lines = []
    lines.append(f"  Character:    {info.char}" if info.is_printable else "  Character:    (non-printable)")
    lines.append(f"  Codepoint:    {info.codepoint_str}")
    lines.append(f"  Name:         {info.name}")
    lines.append(f"  Category:     {info.category} ({info.category_description})")
    lines.append(f"  Block:        {info.block}")
    lines.append(f"  Script:       {info.script}")
    lines.append(f"  UTF-8:        {' '.join(f'{b:02X}' for b in info.utf8_bytes)}")
    lines.append(f"  UTF-16:       {' '.join(f'{b:02X}' for b in info.utf16_bytes)}")
    lines.append(f"  UTF-32:       {' '.join(f'{b:02X}' for b in info.utf32_bytes)}")
    lines.append(f"  Bidi class:   {info.bidirectional}")
    lines.append(f"  Combining:    {info.combining_class}")
    if info.decomposition:
        lines.append(f"  Decomp:       {info.decomposition}")
    lines.append(f"  EA Width:     {info.east_asian_width}")
    lines.append(f"  Mirrored:     {'Yes' if info.mirrored else 'No'}")
    return "\n".join(lines)


def format_string_inspection(infos: list[CharInfo]) -> str:
    parts = []
    for i, info in enumerate(infos):
        parts.append(f"[{i}] {info.codepoint_str} {info.name}")
        parts.append(format_char_info(info))
        parts.append("")
    return "\n".join(parts)


def search_by_name(query: str, limit: int = 50) -> list[CharInfo]:
    query_upper = query.upper()
    results: list[CharInfo] = []
    ranges = [(0x0000, 0xD7FF), (0xE000, 0xFFFF),
              (0x10000, 0x1044F), (0x1D400, 0x1D7FF), (0x1F300, 0x1F9FF)]
    for start, end in ranges:
        if len(results) >= limit:
            break
        for cp in range(start, end + 1):
            if len(results) >= limit:
                break
            try:
                char = chr(cp)
                name = unicodedata.name(char)
                if query_upper in name:
                    results.append(inspect_char(char))
            except (ValueError, OverflowError):
                continue
    return results


def format_search_results(results: list[CharInfo]) -> str:
    if not results:
        return "No characters found."
    lines = [f"Found {len(results)} character(s):", ""]
    for info in results:
        display = info.char if info.is_printable else " "
        lines.append(f"  {display}  {info.codepoint_str}  {info.name}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Invisible character detection
# ═══════════════════════════════════════════════════════════════════

INVISIBLE_CHARS: dict[int, str] = {
    0x0000: "Null", 0x0001: "Start of Heading", 0x0007: "Bell",
    0x0008: "Backspace", 0x000B: "Vertical Tab", 0x000C: "Form Feed",
    0x000E: "Shift Out", 0x000F: "Shift In",
    0x001B: "Escape", 0x007F: "Delete",
    0x0080: "Padding Character", 0x0081: "High Octet Preset",
    0x0085: "Next Line", 0x008D: "Reverse Line Feed",
    0x008E: "Single Shift Two", 0x008F: "Single Shift Three",
    0x0090: "Device Control String", 0x009D: "Operating System Command",
    0x009F: "Application Program Command",
    0x00AD: "Soft Hyphen",
    0x061C: "Arabic Letter Mark",
    0x180E: "Mongolian Vowel Separator",
    0x200B: "Zero Width Space", 0x200C: "Zero Width Non-Joiner",
    0x200D: "Zero Width Joiner", 0x200E: "Left-to-Right Mark",
    0x200F: "Right-to-Left Mark",
    0x2028: "Line Separator", 0x2029: "Paragraph Separator",
    0x202A: "Left-to-Right Embedding", 0x202B: "Right-to-Left Embedding",
    0x202C: "Pop Directional Formatting",
    0x202D: "Left-to-Right Override", 0x202E: "Right-to-Left Override",
    0x2060: "Word Joiner",
    0x2061: "Function Application", 0x2062: "Invisible Times",
    0x2063: "Invisible Separator", 0x2064: "Invisible Plus",
    0x2066: "Left-to-Right Isolate", 0x2067: "Right-to-Left Isolate",
    0x2068: "First Strong Isolate", 0x2069: "Pop Directional Isolate",
    0x206A: "Inhibit Symmetric Swapping", 0x206F: "Nominal Digit Shapes",
    0xFEFF: "Byte Order Mark / Zero Width No-Break Space",
    0xFFF9: "Interlinear Annotation Anchor",
    0xFFFA: "Interlinear Annotation Separator",
    0xFFFB: "Interlinear Annotation Terminator",
    0xFFFC: "Object Replacement Character",
    0xFE00: "Variation Selector-1", 0xFE0F: "Variation Selector-16",
}


@dataclass
class InvisibleChar:
    char: str
    codepoint: int
    codepoint_str: str
    position: int
    description: str
    category: str


def is_invisible(char: str) -> bool:
    cp = ord(char)
    if cp in (0x0020, 0x0009, 0x000A, 0x000D):
        return False
    if cp in INVISIBLE_CHARS:
        return True
    cat = unicodedata.category(char)
    if cat in ("Cc", "Cf"):
        return True
    if cat == "Zs" and cp != 0x0020:
        return True
    if 0xE0020 <= cp <= 0xE007F:
        return True
    if 0xE0100 <= cp <= 0xE01EF:
        return True
    return False


def detect_invisible(text: str) -> list[InvisibleChar]:
    results: list[InvisibleChar] = []
    for i, char in enumerate(text):
        cp = ord(char)
        if is_invisible(char):
            if cp in INVISIBLE_CHARS:
                desc = INVISIBLE_CHARS[cp]
            else:
                try:
                    desc = unicodedata.name(char)
                except ValueError:
                    desc = f"Unknown ({unicodedata.category(char)})"
            results.append(InvisibleChar(
                char=char, codepoint=cp,
                codepoint_str=get_codepoint_str(cp),
                position=i, description=desc,
                category=unicodedata.category(char),
            ))
    return results


def format_invisible_report(text: str, invisibles: list[InvisibleChar]) -> str:
    if not invisibles:
        return f"No invisible characters found in the input ({len(text)} characters scanned)."
    lines = [f"Found {len(invisibles)} invisible character(s) in {len(text)} characters:", ""]
    for inv in invisibles:
        lines.append(f"  Position {inv.position}: {inv.codepoint_str} {inv.description} [{inv.category}]")
    lines.append("")
    lines.append("Annotated string:")
    inv_positions = {inv.position for inv in invisibles}
    annotated = []
    for i, char in enumerate(text):
        if i in inv_positions:
            annotated.append(f"[{get_codepoint_str(ord(char))}]")
        else:
            annotated.append(char)
    lines.append(f"  {''.join(annotated)}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Normalization
# ═══════════════════════════════════════════════════════════════════

VALID_FORMS = ("NFC", "NFD", "NFKC", "NFKD")


@dataclass
class NormalizationResult:
    original: str
    normalized: str
    form: str
    changed: bool
    original_length: int
    normalized_length: int
    original_codepoints: list[str]
    normalized_codepoints: list[str]


def normalize(text: str, form: str = "NFC") -> NormalizationResult:
    form = form.upper()
    if form not in VALID_FORMS:
        raise ValueError(f"Invalid normalization form: {form!r}. Must be one of {VALID_FORMS}")
    normalized = unicodedata.normalize(form, text)
    return NormalizationResult(
        original=text, normalized=normalized, form=form,
        changed=text != normalized,
        original_length=len(text), normalized_length=len(normalized),
        original_codepoints=[f"U+{ord(c):04X}" for c in text],
        normalized_codepoints=[f"U+{ord(c):04X}" for c in normalized],
    )


def normalize_all_forms(text: str) -> dict[str, NormalizationResult]:
    return {form: normalize(text, form) for form in VALID_FORMS}


def is_normalized(text: str, form: str = "NFC") -> bool:
    return not normalize(text, form).changed


def format_normalization_result(result: NormalizationResult) -> str:
    lines = [f"Normalization: {result.form}"]
    if not result.changed:
        lines.append(f"  String is already in {result.form} form.")
        lines.append(f"  Text:       {result.original}")
        lines.append(f"  Length:     {result.original_length} character(s)")
        lines.append(f"  Codepoints: {' '.join(result.original_codepoints)}")
        return "\n".join(lines)
    lines.append(f"  Original:    {result.original}")
    lines.append(f"  Normalized:  {result.normalized}")
    lines.append(f"  Length:      {result.original_length} -> {result.normalized_length}")
    lines.append(f"  Original:    {' '.join(result.original_codepoints)}")
    lines.append(f"  Normalized:  {' '.join(result.normalized_codepoints)}")
    if result.original_length != result.normalized_length:
        diff = result.normalized_length - result.original_length
        direction = "more" if diff > 0 else "fewer"
        lines.append(f"  Change:      {abs(diff)} {direction} character(s)")
    return "\n".join(lines)


def format_all_forms(results: dict[str, NormalizationResult]) -> str:
    return "\n\n".join(format_normalization_result(results[f]) for f in VALID_FORMS)


# ═══════════════════════════════════════════════════════════════════
# Confusables
# ═══════════════════════════════════════════════════════════════════

CONFUSABLE_MAP: dict[int, list[tuple[int, str]]] = {
    # Latin lowercase -> Cyrillic/Greek
    0x0061: [(0x0430, "Cyrillic")],
    0x0063: [(0x0441, "Cyrillic"), (0x03F2, "Greek")],
    0x0064: [(0x0501, "Cyrillic")],
    0x0065: [(0x0435, "Cyrillic"), (0x03B5, "Greek")],
    0x0068: [(0x04BB, "Cyrillic")],
    0x0069: [(0x0456, "Cyrillic"), (0x03B9, "Greek")],
    0x006A: [(0x0458, "Cyrillic")],
    0x006B: [(0x03BA, "Greek")],
    0x006C: [(0x04CF, "Cyrillic")],
    0x006E: [(0x03B7, "Greek")],
    0x006F: [(0x043E, "Cyrillic"), (0x03BF, "Greek")],
    0x0070: [(0x0440, "Cyrillic"), (0x03C1, "Greek")],
    0x0071: [(0x051B, "Cyrillic")],
    0x0073: [(0x0455, "Cyrillic")],
    0x0075: [(0x03C5, "Greek")],
    0x0076: [(0x03BD, "Greek")],
    0x0077: [(0x051D, "Cyrillic")],
    0x0078: [(0x0445, "Cyrillic"), (0x03C7, "Greek")],
    0x0079: [(0x0443, "Cyrillic"), (0x03B3, "Greek")],
    # Latin uppercase -> Cyrillic/Greek
    0x0041: [(0x0410, "Cyrillic"), (0x0391, "Greek")],
    0x0042: [(0x0412, "Cyrillic"), (0x0392, "Greek")],
    0x0043: [(0x0421, "Cyrillic")],
    0x0045: [(0x0415, "Cyrillic"), (0x0395, "Greek")],
    0x0048: [(0x041D, "Cyrillic"), (0x0397, "Greek")],
    0x0049: [(0x0406, "Cyrillic"), (0x0399, "Greek")],
    0x004A: [(0x0408, "Cyrillic")],
    0x004B: [(0x041A, "Cyrillic"), (0x039A, "Greek")],
    0x004D: [(0x041C, "Cyrillic"), (0x039C, "Greek")],
    0x004E: [(0x039D, "Greek")],
    0x004F: [(0x041E, "Cyrillic"), (0x039F, "Greek")],
    0x0050: [(0x0420, "Cyrillic"), (0x03A1, "Greek")],
    0x0053: [(0x0405, "Cyrillic")],
    0x0054: [(0x0422, "Cyrillic"), (0x03A4, "Greek")],
    0x0058: [(0x0425, "Cyrillic"), (0x03A7, "Greek")],
    0x0059: [(0x04AE, "Cyrillic"), (0x03A5, "Greek")],
    0x005A: [(0x0396, "Greek")],
    # Cyrillic -> Latin
    0x0430: [(0x0061, "Latin")], 0x0441: [(0x0063, "Latin")],
    0x0435: [(0x0065, "Latin")], 0x043E: [(0x006F, "Latin")],
    0x0440: [(0x0070, "Latin")], 0x0455: [(0x0073, "Latin")],
    0x0445: [(0x0078, "Latin")], 0x0443: [(0x0079, "Latin")],
    0x0410: [(0x0041, "Latin")], 0x0412: [(0x0042, "Latin")],
    0x0421: [(0x0043, "Latin")], 0x0415: [(0x0045, "Latin")],
    0x041D: [(0x0048, "Latin")], 0x0406: [(0x0049, "Latin")],
    0x0408: [(0x004A, "Latin")], 0x041A: [(0x004B, "Latin")],
    0x041C: [(0x004D, "Latin")], 0x041E: [(0x004F, "Latin")],
    0x0420: [(0x0050, "Latin")], 0x0405: [(0x0053, "Latin")],
    0x0422: [(0x0054, "Latin")], 0x0425: [(0x0058, "Latin")],
    0x04AE: [(0x0059, "Latin")],
    0x0501: [(0x0064, "Latin")], 0x04BB: [(0x0068, "Latin")],
    0x0456: [(0x0069, "Latin")], 0x0458: [(0x006A, "Latin")],
    0x04CF: [(0x006C, "Latin")], 0x051B: [(0x0071, "Latin")],
    0x051D: [(0x0077, "Latin")],
    # Greek -> Latin
    0x0391: [(0x0041, "Latin")], 0x0392: [(0x0042, "Latin")],
    0x0395: [(0x0045, "Latin")], 0x0397: [(0x0048, "Latin")],
    0x0399: [(0x0049, "Latin")], 0x039A: [(0x004B, "Latin")],
    0x039C: [(0x004D, "Latin")], 0x039D: [(0x004E, "Latin")],
    0x039F: [(0x004F, "Latin")], 0x03A1: [(0x0050, "Latin")],
    0x03A4: [(0x0054, "Latin")], 0x03A5: [(0x0059, "Latin")],
    0x03A7: [(0x0058, "Latin")], 0x0396: [(0x005A, "Latin")],
    0x03B5: [(0x0065, "Latin")], 0x03B9: [(0x0069, "Latin")],
    0x03BA: [(0x006B, "Latin")], 0x03B7: [(0x006E, "Latin")],
    0x03BF: [(0x006F, "Latin")], 0x03C1: [(0x0070, "Latin")],
    0x03C5: [(0x0075, "Latin")], 0x03BD: [(0x0076, "Latin")],
    0x03C7: [(0x0078, "Latin")], 0x03B3: [(0x0079, "Latin")],
    0x03F2: [(0x0063, "Latin")],
    # Digit confusables
    0x0030: [(0x041E, "Cyrillic"), (0x039F, "Greek")],
    0x0031: [(0x006C, "Latin"), (0x04CF, "Cyrillic"), (0x0399, "Greek")],
    # Fullwidth
    0xFF21: [(0x0041, "Latin")], 0xFF22: [(0x0042, "Latin")], 0xFF23: [(0x0043, "Latin")],
    0xFF41: [(0x0061, "Latin")], 0xFF42: [(0x0062, "Latin")], 0xFF43: [(0x0063, "Latin")],
}


@dataclass
class LookalikeInfo:
    char: str
    codepoint: int
    codepoint_str: str
    name: str
    script: str


@dataclass
class ConfusableMatch:
    char: str
    codepoint: int
    codepoint_str: str
    name: str
    script: str
    lookalikes: list[LookalikeInfo]


def _get_name(char: str) -> str:
    try:
        return unicodedata.name(char)
    except ValueError:
        return f"<U+{ord(char):04X}>"


def _get_script_for_cp(cp: int) -> str:
    if 0x0000 <= cp <= 0x024F or 0x1E00 <= cp <= 0x1EFF:
        return "Latin"
    if 0x0370 <= cp <= 0x03FF or 0x1F00 <= cp <= 0x1FFF:
        return "Greek"
    if 0x0400 <= cp <= 0x052F:
        return "Cyrillic"
    if 0xFF00 <= cp <= 0xFFEF:
        return "Fullwidth"
    return "Other"


def get_confusables(char: str) -> ConfusableMatch | None:
    if len(char) != 1:
        raise ValueError(f"Expected a single character, got {len(char)}")
    cp = ord(char)
    if cp not in CONFUSABLE_MAP:
        return None
    lookalikes = []
    for la_cp, script in CONFUSABLE_MAP[cp]:
        la_char = chr(la_cp)
        lookalikes.append(LookalikeInfo(
            char=la_char, codepoint=la_cp,
            codepoint_str=get_codepoint_str(la_cp),
            name=_get_name(la_char), script=script,
        ))
    return ConfusableMatch(
        char=char, codepoint=cp, codepoint_str=get_codepoint_str(cp),
        name=_get_name(char), script=_get_script_for_cp(cp),
        lookalikes=lookalikes,
    )


def scan_confusables(text: str) -> list[ConfusableMatch]:
    results = []
    seen: set[int] = set()
    for char in text:
        cp = ord(char)
        if cp in seen:
            continue
        seen.add(cp)
        match = get_confusables(char)
        if match is not None:
            results.append(match)
    return results


def detect_mixed_scripts(text: str) -> dict[str, list[str]]:
    scripts: dict[str, list[str]] = {}
    for char in text:
        cat = unicodedata.category(char)
        if cat.startswith(("Z", "P", "S", "C")):
            continue
        script = _get_script_for_cp(ord(char))
        if script not in scripts:
            scripts[script] = []
        if char not in scripts[script]:
            scripts[script].append(char)
    return scripts


def format_confusable_report(matches: list[ConfusableMatch]) -> str:
    if not matches:
        return "No confusable characters detected."
    lines = [f"Found {len(matches)} character(s) with known confusables:", ""]
    for match in matches:
        lines.append(f"  {match.char}  {match.codepoint_str}  {match.name} ({match.script})")
        for la in match.lookalikes:
            lines.append(f"    ~ {la.char}  {la.codepoint_str}  {la.name} ({la.script})")
        lines.append("")
    return "\n".join(lines)


def format_mixed_script_report(scripts: dict[str, list[str]]) -> str:
    if len(scripts) <= 1:
        if scripts:
            return f"Single script detected: {next(iter(scripts))}"
        return "No script-bearing characters found."
    lines = [
        f"WARNING: Mixed scripts detected ({len(scripts)} scripts):",
        "This could indicate a homoglyph attack.", "",
    ]
    for script, chars in sorted(scripts.items()):
        lines.append(f"  {script}: {' '.join(chars)}")
    return "\n".join(lines)
