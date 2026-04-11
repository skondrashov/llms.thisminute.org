"""
CSV Dialect Detector — Multi-Signal CSV Format Analyzer for Agents

Detects delimiter, quoting, escaping, line terminator, encoding, header
presence, and fixed-width format using frequency analysis and hypothesis
scoring.  More reliable than Python's csv.Sniffer for real-world files
with mixed quoting, European semicolons, pipe-delimited data, and
encoding variations.

SUPPORTED DELIMITERS
====================
Comma (,), tab (\t), semicolon (;), pipe (|), colon (:).

SUPPORTED ENCODINGS
===================
UTF-8, UTF-8 with BOM, UTF-16 LE/BE (with and without BOM),
CP1252, Latin-1.  BOM detection is automatic.

FEATURES
========
- Delimiter detection with consistency scoring across lines
- Quote character detection (double vs single quotes)
- Escape style detection (doubled quotes vs backslash)
- Header row detection via type-signature comparison
- Fixed-width format detection with column-width extraction
- Code generation for csv.reader() and pandas.read_csv()
- Table-formatted data preview
- Dialect-aware format conversion

Pure Python, no external dependencies.
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


# Candidate delimiters in preference order (used to break ties)
CANDIDATE_DELIMITERS = [",", "\t", ";", "|", ":"]

# Candidate quote characters
CANDIDATE_QUOTES = ['"', "'"]

# BOM signatures (bytes -> encoding name)
BOM_MAP = {
    b"\xef\xbb\xbf": "utf-8-sig",
    b"\xff\xfe": "utf-16-le",
    b"\xfe\xff": "utf-16-be",
}


@dataclass
class DialectResult:
    """Result of dialect detection."""

    delimiter: str = ","
    quotechar: str = '"'
    escapechar: Optional[str] = None
    doublequote: bool = True
    lineterminator: str = "\r\n"
    encoding: str = "utf-8"
    has_header: bool = True
    confidence: float = 0.0
    num_columns: int = 0
    is_fixed_width: bool = False
    column_widths: list[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = {
            "delimiter": _repr_char(self.delimiter),
            "quotechar": self.quotechar,
            "doublequote": self.doublequote,
            "lineterminator": _repr_terminator(self.lineterminator),
            "encoding": self.encoding,
            "has_header": self.has_header,
            "confidence": round(self.confidence, 3),
            "num_columns": self.num_columns,
            "is_fixed_width": self.is_fixed_width,
        }
        if self.escapechar is not None:
            d["escapechar"] = self.escapechar
        if self.is_fixed_width:
            d["column_widths"] = self.column_widths
        return d


def _repr_char(c: str) -> str:
    """Human-readable representation of a character."""
    if c == "\t":
        return "\\t"
    if c == "|":
        return "|"
    return c


def _repr_terminator(t: str) -> str:
    """Human-readable representation of a line terminator."""
    return t.replace("\r", "\\r").replace("\n", "\\n")


# ============================================================================
# Encoding detection
# ============================================================================


def detect_encoding(raw: bytes) -> tuple[str, bytes]:
    """Detect encoding from raw bytes.

    Returns (encoding_name, content_bytes_without_bom).
    """
    for bom, encoding in BOM_MAP.items():
        if raw.startswith(bom):
            return encoding, raw[len(bom):]

    try:
        raw.decode("utf-8")
        return "utf-8", raw
    except UnicodeDecodeError:
        pass

    if len(raw) >= 4:
        null_odd = sum(1 for i in range(1, min(len(raw), 200), 2) if raw[i] == 0)
        null_even = sum(1 for i in range(0, min(len(raw), 200), 2) if raw[i] == 0)
        sample_len = min(len(raw), 200) // 2
        if sample_len > 0:
            if null_odd / sample_len > 0.5:
                return "utf-16-le", raw
            if null_even / sample_len > 0.5:
                return "utf-16-be", raw

    high_bytes = [b for b in raw if b >= 0x80]
    if high_bytes:
        cp1252_specific = [b for b in high_bytes if 0x80 <= b <= 0x9F]
        if cp1252_specific:
            return "cp1252", raw

    return "latin-1", raw


# ============================================================================
# Line terminator detection
# ============================================================================


def detect_line_terminator(text: str) -> str:
    """Detect the dominant line terminator in text."""
    crlf = text.count("\r\n")
    lf_only = text.count("\n") - crlf
    cr_only = text.count("\r") - crlf

    if crlf == 0 and lf_only == 0 and cr_only == 0:
        return "\n"

    counts = {"\r\n": crlf, "\n": lf_only, "\r": cr_only}
    return max(counts, key=counts.get)


def _split_lines_preserve(text: str) -> list[str]:
    """Split text into lines, splitting on any line ending."""
    lines = re.split(r"\r\n|\r|\n", text)
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


# ============================================================================
# Delimiter detection
# ============================================================================


def _count_delimiter_in_line(line: str, delimiter: str, quotechar: str = '"') -> int:
    """Count occurrences of delimiter outside quoted fields."""
    count = 0
    in_quotes = False
    for c in line:
        if c == quotechar:
            in_quotes = not in_quotes
        elif c == delimiter and not in_quotes:
            count += 1
    return count


def _score_delimiter(lines: list[str], delimiter: str) -> tuple[float, int]:
    """Score a candidate delimiter based on consistency across lines.

    Returns (score, expected_columns).
    """
    if not lines:
        return 0.0, 0

    nonempty = [line for line in lines if line.strip()]
    if not nonempty:
        return 0.0, 0

    counts = [_count_delimiter_in_line(line, delimiter) for line in nonempty]

    if all(c == 0 for c in counts):
        return 0.0, 0

    count_freq = Counter(counts)
    expected_count = count_freq.most_common(1)[0][0]

    if expected_count == 0:
        return 0.0, 0

    matching = sum(1 for c in counts if c == expected_count)
    consistency = matching / len(nonempty)
    column_bonus = min(expected_count / 10, 0.1)
    score = consistency + column_bonus

    return min(score, 1.0), expected_count + 1


def detect_delimiter(lines: list[str]) -> tuple[str, float, int]:
    """Detect the most likely delimiter.

    Returns (delimiter, confidence, num_columns).
    """
    if not lines:
        return ",", 0.0, 0

    best_delim = ","
    best_score = 0.0
    best_cols = 0

    for delim in CANDIDATE_DELIMITERS:
        score, cols = _score_delimiter(lines, delim)
        if score > best_score or (score == best_score and cols > best_cols):
            best_score = score
            best_delim = delim
            best_cols = cols

    return best_delim, best_score, best_cols


# ============================================================================
# Quote character detection
# ============================================================================


def detect_quotechar(text: str, delimiter: str) -> tuple[str, bool, Optional[str]]:
    """Detect quote character and escaping style.

    Returns (quotechar, doublequote, escapechar).
    """
    lines = _split_lines_preserve(text)

    best_quote = '"'
    best_count = 0

    for qc in CANDIDATE_QUOTES:
        count = 0
        for line in lines:
            fields = line.split(delimiter)
            for f in fields:
                f = f.strip()
                if len(f) >= 2 and f.startswith(qc) and f.endswith(qc):
                    count += 1
        if count > best_count:
            best_count = count
            best_quote = qc

    doubled_pattern = best_quote + best_quote
    backslash_pattern = "\\" + best_quote

    doubled_count = text.count(doubled_pattern)
    backslash_count = text.count(backslash_pattern)

    if backslash_count > doubled_count and backslash_count > 0:
        return best_quote, False, "\\"
    else:
        return best_quote, True, None


# ============================================================================
# Header detection
# ============================================================================


def detect_header(lines: list[str], delimiter: str, quotechar: str) -> bool:
    """Detect whether the first row is a header."""
    if len(lines) < 2:
        return False

    def parse_row(line: str) -> list[str]:
        reader = csv.reader(io.StringIO(line), delimiter=delimiter, quotechar=quotechar)
        try:
            return next(reader)
        except StopIteration:
            return []

    def is_numeric(val: str) -> bool:
        val = val.strip()
        if not val:
            return False
        try:
            float(val.replace(",", ""))
            return True
        except ValueError:
            return False

    first_row = parse_row(lines[0])
    if not first_row:
        return False

    first_row_numeric = [is_numeric(v) for v in first_row]

    data_lines = lines[1:min(21, len(lines))]
    if not data_lines:
        return False

    data_numeric_counts = [0] * len(first_row)
    data_row_count = 0

    for line in data_lines:
        row = parse_row(line)
        if len(row) != len(first_row):
            continue
        data_row_count += 1
        for i, val in enumerate(row):
            if is_numeric(val):
                data_numeric_counts[i] += 1

    if data_row_count == 0:
        return False

    if not any(first_row_numeric) and any(c > 0 for c in data_numeric_counts):
        return True

    if not any(first_row_numeric):
        first_set = set(v.strip().lower() for v in first_row)
        data_values: set[str] = set()
        for line in data_lines:
            row = parse_row(line)
            for v in row:
                data_values.add(v.strip().lower())

        overlap = first_set & data_values
        if len(overlap) <= len(first_set) * 0.2:
            return True

    first_all_alpha = all(
        v.strip().replace(" ", "").replace("_", "").isalpha()
        for v in first_row if v.strip()
    )
    data_has_nonalpha = any(
        not v.strip().replace(" ", "").replace("_", "").isalpha()
        for line in data_lines
        for v in parse_row(line)
        if v.strip()
    )

    if first_all_alpha and data_has_nonalpha:
        return True

    return False


# ============================================================================
# Fixed-width detection
# ============================================================================


def detect_fixed_width(lines: list[str]) -> tuple[bool, list[int]]:
    """Detect if the data is fixed-width format.

    Returns (is_fixed_width, column_widths).
    """
    if len(lines) < 2:
        return False, []

    nonempty = [line for line in lines if line.strip()]
    if len(nonempty) < 2:
        return False, []

    max_len = max(len(line) for line in nonempty)
    if max_len < 4:
        return False, []

    min_len = min(len(line) for line in nonempty)

    boundary_candidates: list[int] = [0]

    for pos in range(1, min_len):
        space_count = sum(
            1 for line in nonempty
            if pos < len(line) and line[pos - 1] == " " and line[pos] != " "
        )
        if space_count / len(nonempty) >= 0.8:
            if not boundary_candidates or pos - boundary_candidates[-1] >= 2:
                boundary_candidates.append(pos)

    if len(boundary_candidates) < 2:
        return False, []

    widths = []
    for i in range(len(boundary_candidates) - 1):
        widths.append(boundary_candidates[i + 1] - boundary_candidates[i])
    widths.append(max_len - boundary_candidates[-1])

    if len(widths) < 2:
        return False, []

    return True, widths


# ============================================================================
# Full dialect detection
# ============================================================================


def detect_dialect(
    source: str | bytes,
    *,
    sample_lines: int = 100,
) -> DialectResult:
    """Detect the CSV dialect of the given data.

    Args:
        source: Either a string of CSV text, or raw bytes.
        sample_lines: Maximum number of lines to analyze.

    Returns:
        A DialectResult describing the detected dialect.
    """
    result = DialectResult()

    if isinstance(source, bytes):
        encoding, clean_bytes = detect_encoding(source)
        result.encoding = encoding
        text = clean_bytes.decode(encoding if encoding != "utf-8-sig" else "utf-8")
    else:
        text = source
        result.encoding = "utf-8"

    if not text.strip():
        result.confidence = 0.0
        return result

    result.lineterminator = detect_line_terminator(text)

    lines = _split_lines_preserve(text)
    sample = lines[:sample_lines]

    if not sample:
        result.confidence = 0.0
        return result

    delimiter, delim_score, num_cols = detect_delimiter(sample)
    result.delimiter = delimiter
    result.num_columns = num_cols

    if delim_score < 0.5:
        is_fw, widths = detect_fixed_width(sample)
        if is_fw:
            result.is_fixed_width = True
            result.column_widths = widths
            result.num_columns = len(widths)
            result.delimiter = ""
            result.confidence = 0.7
            result.has_header = False
            return result

    quotechar, doublequote, escapechar = detect_quotechar(text, delimiter)
    result.quotechar = quotechar
    result.doublequote = doublequote
    result.escapechar = escapechar

    result.has_header = detect_header(sample, delimiter, quotechar)

    confidence = delim_score
    if num_cols >= 2:
        confidence = min(confidence + 0.05, 1.0)
    if len(sample) >= 5:
        confidence = min(confidence + 0.05, 1.0)

    result.confidence = round(min(confidence, 1.0), 3)

    return result


# ============================================================================
# Previewer: parse and format CSV data as a table
# ============================================================================


def parse_rows(
    text: str,
    dialect: DialectResult,
    *,
    max_rows: Optional[int] = None,
) -> list[list[str]]:
    """Parse CSV text using the detected dialect."""
    if dialect.is_fixed_width:
        return _parse_fixed_width(text, dialect, max_rows=max_rows)

    kwargs: dict = {
        "delimiter": dialect.delimiter,
        "quotechar": dialect.quotechar,
        "doublequote": dialect.doublequote,
    }
    if dialect.escapechar is not None:
        kwargs["escapechar"] = dialect.escapechar

    reader = csv.reader(io.StringIO(text), **kwargs)
    rows = []
    for i, row in enumerate(reader):
        if max_rows is not None and i >= max_rows:
            break
        rows.append(row)
    return rows


def _parse_fixed_width(
    text: str,
    dialect: DialectResult,
    *,
    max_rows: Optional[int] = None,
) -> list[list[str]]:
    """Parse fixed-width formatted text."""
    lines = _split_lines_preserve(text)
    rows = []
    for i, line in enumerate(lines):
        if max_rows is not None and i >= max_rows:
            break
        if not line.strip():
            continue
        row = []
        pos = 0
        for width in dialect.column_widths:
            f = line[pos:pos + width].strip()
            row.append(f)
            pos += width
        if pos < len(line):
            row[-1] = line[pos - dialect.column_widths[-1]:].strip() if row else line[pos:].strip()
        rows.append(row)
    return rows


def _truncate(s: str, max_width: int) -> str:
    """Truncate a string, adding ellipsis if needed."""
    s = s.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    if len(s) > max_width:
        return s[:max_width - 3] + "..."
    return s


def format_table(
    rows: list[list[str]],
    *,
    has_header: bool = True,
    max_col_width: int = 40,
) -> str:
    """Format rows as a text table."""
    if not rows:
        return "(empty)"

    num_cols = max(len(row) for row in rows)
    col_widths = [0] * num_cols

    for row in rows:
        for i, val in enumerate(row):
            display = _truncate(val, max_col_width)
            col_widths[i] = max(col_widths[i], len(display))

    col_widths = [max(w, 3) for w in col_widths]

    def _format_row(row, col_widths, max_col_width):
        cells = []
        for i, width in enumerate(col_widths):
            val = row[i] if i < len(row) else ""
            display = _truncate(val, max_col_width)
            cells.append(f" {display:<{width}} ")
        return "|" + "|".join(cells) + "|"

    out_lines = []

    if has_header and rows:
        header = rows[0]
        header_line = _format_row(header, col_widths, max_col_width)
        out_lines.append(header_line)
        separator = "+".join("-" * (w + 2) for w in col_widths)
        out_lines.append(f"+{separator}+")
        data_rows = rows[1:]
    else:
        header = [f"Col {i+1}" for i in range(num_cols)]
        header_line = _format_row(header, col_widths, max_col_width)
        out_lines.append(header_line)
        separator = "+".join("-" * (w + 2) for w in col_widths)
        out_lines.append(f"+{separator}+")
        data_rows = rows

    for row in data_rows:
        out_lines.append(_format_row(row, col_widths, max_col_width))

    border = "+".join("-" * (w + 2) for w in col_widths)
    border = f"+{border}+"

    return "\n".join([border] + out_lines + [border])


def preview(
    text: str,
    dialect: DialectResult,
    *,
    max_rows: int = 10,
    max_col_width: int = 40,
) -> str:
    """Parse and format a preview of CSV data."""
    fetch_rows = max_rows + (1 if dialect.has_header else 0)
    rows = parse_rows(text, dialect, max_rows=fetch_rows)
    return format_table(rows, has_header=dialect.has_header, max_col_width=max_col_width)


# ============================================================================
# Code generation
# ============================================================================


def _repr_str(s: str) -> str:
    """Return a Python repr of a string, preferring readable forms."""
    if s == "\t":
        return '"\\t"'
    if s == "\\":
        return '"\\\\"'
    return repr(s)


def generate_csv_reader(dialect: DialectResult, filepath: str = "data.csv") -> str:
    """Generate Python code using csv.reader() with the detected dialect."""
    if dialect.is_fixed_width:
        widths = dialect.column_widths
        lines = []
        lines.append(f"# Fixed-width format detected (column widths: {widths})")
        lines.append("")
        encoding = dialect.encoding
        open_kwargs = f'"{filepath}"'
        if encoding != "utf-8":
            open_kwargs += f', encoding="{encoding}"'
        lines.append(f"with open({open_kwargs}) as f:")
        lines.append("    for line in f:")
        lines.append("        fields = []")
        lines.append("        pos = 0")
        lines.append(f"        widths = {widths}")
        lines.append("        for w in widths:")
        lines.append("            fields.append(line[pos:pos + w].strip())")
        lines.append("            pos += w")
        lines.append("        print(fields)")
        return "\n".join(lines) + "\n"

    lines = []
    lines.append("import csv")
    lines.append("")

    encoding = dialect.encoding
    open_kwargs = f'"{filepath}", newline=""'
    if encoding != "utf-8":
        open_kwargs += f', encoding="{encoding}"'

    lines.append(f'with open({open_kwargs}) as f:')

    reader_kwargs = []
    if dialect.delimiter != ",":
        reader_kwargs.append(f"delimiter={_repr_str(dialect.delimiter)}")
    if dialect.quotechar != '"':
        reader_kwargs.append(f"quotechar={_repr_str(dialect.quotechar)}")
    if not dialect.doublequote:
        reader_kwargs.append("doublequote=False")
    if dialect.escapechar is not None:
        reader_kwargs.append(f"escapechar={_repr_str(dialect.escapechar)}")

    if reader_kwargs:
        kwargs_str = ", ".join(reader_kwargs)
        lines.append(f"    reader = csv.reader(f, {kwargs_str})")
    else:
        lines.append("    reader = csv.reader(f)")

    if dialect.has_header:
        lines.append("    header = next(reader)")
    lines.append("    for row in reader:")
    lines.append("        print(row)")

    return "\n".join(lines) + "\n"


def generate_pandas_reader(dialect: DialectResult, filepath: str = "data.csv") -> str:
    """Generate Python code using pandas.read_csv() with the detected dialect."""
    if dialect.is_fixed_width:
        widths = dialect.column_widths
        lines = []
        lines.append("import pandas as pd")
        lines.append("")
        lines.append(f"# Fixed-width format detected (column widths: {widths})")
        kwargs = []
        kwargs.append(f'"{filepath}"')
        kwargs.append(f"widths={widths}")
        encoding = dialect.encoding
        if encoding != "utf-8":
            kwargs.append(f'encoding="{encoding}"')
        if not dialect.has_header:
            kwargs.append("header=None")
        kwargs_str = ",\n    ".join(kwargs)
        lines.append(f"df = pd.read_fwf(\n    {kwargs_str},\n)")
        lines.append("print(df.head())")
        return "\n".join(lines) + "\n"

    lines = []
    lines.append("import pandas as pd")
    lines.append("")

    kwargs = []
    kwargs.append(f'"{filepath}"')
    if dialect.delimiter != ",":
        kwargs.append(f"sep={_repr_str(dialect.delimiter)}")
    if dialect.quotechar != '"':
        kwargs.append(f"quotechar={_repr_str(dialect.quotechar)}")
    if dialect.escapechar is not None:
        kwargs.append(f"escapechar={_repr_str(dialect.escapechar)}")
    if not dialect.doublequote:
        kwargs.append("doublequote=False")
    encoding = dialect.encoding
    if encoding != "utf-8":
        kwargs.append(f'encoding="{encoding}"')
    if not dialect.has_header:
        kwargs.append("header=None")

    kwargs_str = ",\n    ".join(kwargs)
    lines.append(f"df = pd.read_csv(\n    {kwargs_str},\n)")
    lines.append("print(df.head())")

    return "\n".join(lines) + "\n"


def generate_code(
    dialect: DialectResult,
    filepath: str = "data.csv",
    *,
    style: str = "csv",
) -> str:
    """Generate Python code for the given dialect.

    Args:
        style: Either "csv" for csv.reader() or "pandas" for pandas.read_csv().
    """
    if style == "pandas":
        return generate_pandas_reader(dialect, filepath)
    return generate_csv_reader(dialect, filepath)


# ============================================================================
# CLI
# ============================================================================


def main():
    """CLI entry point."""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        prog="csv-detect",
        description="Detect CSV dialect more reliably than Python's csv.Sniffer.",
    )
    parser.add_argument("file", help="CSV file to analyze (use - for stdin)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--preview", action="store_true", help="Show data preview")
    parser.add_argument("--rows", type=int, default=10, help="Preview rows (default: 10)")
    parser.add_argument("--code", action="store_true", help="Generate csv.reader() code")
    parser.add_argument("--pandas", action="store_true", help="Generate pandas code")

    args = parser.parse_args()

    if args.file == "-":
        raw = sys.stdin.buffer.read()
    else:
        with open(args.file, "rb") as f:
            raw = f.read()

    dialect = detect_dialect(raw)
    name = args.file if args.file != "-" else "<stdin>"

    if args.json:
        result = dialect.to_dict()
        result["file"] = name
        print(json.dumps(result, indent=2))
    elif args.code or args.pandas:
        style = "pandas" if args.pandas else "csv"
        display_path = name if name != "<stdin>" else "data.csv"
        code = generate_code(dialect, display_path, style=style)
        print(code, end="")
    elif args.preview:
        encoding = dialect.encoding
        if encoding == "utf-8-sig":
            if raw.startswith(b"\xef\xbb\xbf"):
                raw = raw[3:]
            encoding = "utf-8"
        text = raw.decode(encoding)
        table = preview(text, dialect, max_rows=args.rows)
        print(table)
    else:
        delim_display = {
            ",": "comma (,)", "\t": "tab (\\t)", ";": "semicolon (;)",
            "|": "pipe (|)", ":": "colon (:)",
        }.get(dialect.delimiter, repr(dialect.delimiter))
        term_display = {
            "\r\n": "\\r\\n (Windows)", "\n": "\\n (Unix)", "\r": "\\r (old Mac)",
        }.get(dialect.lineterminator, repr(dialect.lineterminator))

        print(f"File:            {name}")
        if dialect.is_fixed_width:
            print(f"Format:          Fixed-width")
            print(f"Column widths:   {dialect.column_widths}")
        else:
            print(f"Delimiter:       {delim_display}")
            print(f"Quote char:      {dialect.quotechar}")
            if dialect.escapechar:
                print(f"Escape char:     {dialect.escapechar}")
            else:
                print(f"Double-quote:    {dialect.doublequote}")
        print(f"Columns:         {dialect.num_columns}")
        print(f"Line ending:     {term_display}")
        print(f"Encoding:        {dialect.encoding}")
        print(f"Has header:      {dialect.has_header}")
        print(f"Confidence:      {dialect.confidence:.1%}")


if __name__ == "__main__":
    main()
