"""
Tests for CSV Dialect Detector.

These tests ARE the spec — if an LLM regenerates the detector in any
language, these cases define correctness.
"""

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from detector import (
    detect_dialect,
    detect_encoding,
    detect_line_terminator,
    detect_delimiter,
    detect_quotechar,
    detect_header,
    detect_fixed_width,
    _split_lines_preserve,
    _count_delimiter_in_line,
    _score_delimiter,
    DialectResult,
    parse_rows,
    format_table,
    preview,
    _truncate,
    generate_csv_reader,
    generate_pandas_reader,
    generate_code,
    _repr_str,
)


# ============================================================================
# 1. Encoding detection
# ============================================================================


class TestDetectEncoding:
    def test_utf8_no_bom(self):
        raw = "hello,world\n".encode("utf-8")
        enc, clean = detect_encoding(raw)
        assert enc == "utf-8"
        assert clean == raw

    def test_utf8_bom(self):
        raw = b"\xef\xbb\xbf" + "hello,world\n".encode("utf-8")
        enc, clean = detect_encoding(raw)
        assert enc == "utf-8-sig"
        assert clean == "hello,world\n".encode("utf-8")

    def test_utf16_le_bom(self):
        raw = b"\xff\xfe" + "hello".encode("utf-16-le")
        enc, clean = detect_encoding(raw)
        assert enc == "utf-16-le"

    def test_utf16_be_bom(self):
        raw = b"\xfe\xff" + "hello".encode("utf-16-be")
        enc, clean = detect_encoding(raw)
        assert enc == "utf-16-be"

    def test_latin1_fallback(self):
        raw = bytes([0xC0, 0xC1, 0xF5, 0xF6, 0xF7])
        enc, clean = detect_encoding(raw)
        assert enc in ("latin-1", "cp1252")

    def test_cp1252_detection(self):
        raw = bytes([0x80, 0x85, 0x93, 0x94])
        enc, clean = detect_encoding(raw)
        assert enc == "cp1252"

    def test_empty_bytes(self):
        enc, clean = detect_encoding(b"")
        assert enc == "utf-8"
        assert clean == b""

    def test_pure_ascii(self):
        raw = b"name,age,city\nAlice,30,NYC\n"
        enc, clean = detect_encoding(raw)
        assert enc == "utf-8"

    def test_utf8_with_multibyte(self):
        raw = "name,city\nAlice,Zurich\nBob,M\u00fcnchen\n".encode("utf-8")
        enc, clean = detect_encoding(raw)
        assert enc == "utf-8"

    def test_bom_removed_from_content(self):
        content = "a,b,c\n1,2,3\n"
        raw = b"\xef\xbb\xbf" + content.encode("utf-8")
        enc, clean = detect_encoding(raw)
        assert enc == "utf-8-sig"
        assert clean == content.encode("utf-8")


# ============================================================================
# 2. Delimiter detection
# ============================================================================


class TestDelimiterDetection:
    def test_comma_separated(self):
        lines = ["name,age,city", "Alice,30,NYC", "Bob,25,LA"]
        delim, score, cols = detect_delimiter(lines)
        assert delim == ","
        assert cols == 3

    def test_tab_separated(self):
        lines = ["name\tage\tcity", "Alice\t30\tNYC", "Bob\t25\tLA"]
        delim, score, cols = detect_delimiter(lines)
        assert delim == "\t"
        assert cols == 3

    def test_pipe_separated(self):
        lines = ["name|age|city", "Alice|30|NYC", "Bob|25|LA"]
        delim, score, cols = detect_delimiter(lines)
        assert delim == "|"
        assert cols == 3

    def test_semicolon_separated(self):
        lines = ["name;age;city", "Alice;30;NYC", "Bob;25;LA"]
        delim, score, cols = detect_delimiter(lines)
        assert delim == ";"
        assert cols == 3

    def test_colon_separated(self):
        lines = ["name:age:city", "Alice:30:NYC", "Bob:25:LA"]
        delim, score, cols = detect_delimiter(lines)
        assert delim == ":"
        assert cols == 3

    def test_empty_input(self):
        delim, score, cols = detect_delimiter([])
        assert delim == ","
        assert score == 0.0

    def test_single_column(self):
        lines = ["hello", "world", "foo"]
        delim, score, cols = detect_delimiter(lines)
        assert score == 0.0

    def test_quoted_field_not_counted(self):
        assert _count_delimiter_in_line('"a,b",c', ",") == 1

    def test_no_delimiter_present(self):
        lines = ["abc", "def", "ghi"]
        score, cols = _score_delimiter(lines, ",")
        assert score == 0.0


# ============================================================================
# 3. Quote character and escaping detection
# ============================================================================


class TestQuoteDetection:
    def test_double_quotes(self):
        text = '"name","age"\n"Alice","30"\n'
        qc, dq, esc = detect_quotechar(text, ",")
        assert qc == '"'

    def test_single_quotes(self):
        text = "'name','age'\n'Alice','30'\n"
        qc, dq, esc = detect_quotechar(text, ",")
        assert qc == "'"

    def test_doubled_quote_escaping(self):
        text = '"has ""quotes""","normal"\n'
        qc, dq, esc = detect_quotechar(text, ",")
        assert qc == '"'
        assert dq is True
        assert esc is None

    def test_backslash_escaping(self):
        text = '"has \\"quotes\\"","normal"\n'
        qc, dq, esc = detect_quotechar(text, ",")
        assert qc == '"'
        assert dq is False
        assert esc == "\\"

    def test_no_quotes_defaults_to_double(self):
        text = "name,age\nAlice,30\n"
        qc, dq, esc = detect_quotechar(text, ",")
        assert qc == '"'


# ============================================================================
# 4. Header detection
# ============================================================================


class TestHeaderDetection:
    def test_header_with_numeric_data(self):
        lines = ["name,age,salary", "Alice,30,50000", "Bob,25,60000"]
        assert detect_header(lines, ",", '"') is True

    def test_no_header_all_numeric(self):
        lines = ["1,2,3", "4,5,6", "7,8,9"]
        assert detect_header(lines, ",", '"') is False

    def test_header_alpha_vs_mixed(self):
        lines = ["Name,Age,City", "Alice,30,NYC", "Bob,25,LA"]
        assert detect_header(lines, ",", '"') is True

    def test_single_line_no_header(self):
        lines = ["name,age,city"]
        assert detect_header(lines, ",", '"') is False

    def test_empty_no_header(self):
        assert detect_header([], ",", '"') is False

    def test_header_with_tab_delimiter(self):
        lines = ["name\tage\tsalary", "Alice\t30\t50000", "Bob\t25\t60000"]
        assert detect_header(lines, "\t", '"') is True


# ============================================================================
# 5. Full dialect detection with code generation
# ============================================================================


class TestFullDialect:
    def test_simple_csv(self):
        data = "name,age,city\nAlice,30,NYC\nBob,25,LA\n"
        result = detect_dialect(data)
        assert result.delimiter == ","
        assert result.num_columns == 3
        assert result.has_header is True

    def test_tsv(self):
        data = "name\tage\tcity\nAlice\t30\tNYC\nBob\t25\tLA\n"
        result = detect_dialect(data)
        assert result.delimiter == "\t"
        assert result.num_columns == 3

    def test_pipe_delimited(self):
        data = "name|age|city\nAlice|30|NYC\nBob|25|LA\n"
        result = detect_dialect(data)
        assert result.delimiter == "|"

    def test_semicolon_european(self):
        data = "name;price;quantity\nWidget;9,99;100\nGadget;4,50;200\n"
        result = detect_dialect(data)
        assert result.delimiter == ";"

    def test_windows_line_endings(self):
        data = "name,age\r\nAlice,30\r\nBob,25\r\n"
        result = detect_dialect(data)
        assert result.lineterminator == "\r\n"

    def test_empty_string(self):
        result = detect_dialect("")
        assert result.confidence == 0.0

    def test_bytes_utf8(self):
        data = b"name,age\nAlice,30\nBob,25\n"
        result = detect_dialect(data)
        assert result.encoding == "utf-8"
        assert result.delimiter == ","

    def test_bytes_utf8_bom(self):
        data = b"\xef\xbb\xbfname,age\nAlice,30\nBob,25\n"
        result = detect_dialect(data)
        assert result.encoding == "utf-8-sig"

    def test_confidence_bounded(self):
        data = "a,b,c\n1,2,3\n4,5,6\n7,8,9\n10,11,12\n"
        result = detect_dialect(data)
        assert 0.0 <= result.confidence <= 1.0

    def test_no_header_all_numeric(self):
        data = "1,2,3\n4,5,6\n7,8,9\n"
        result = detect_dialect(data)
        assert result.has_header is False

    def test_escaped_quotes_doubled(self):
        data = 'name,desc\nAlice,"She said ""hello"""\nBob,"He said ""bye"""\n'
        result = detect_dialect(data)
        assert result.doublequote is True


# ============================================================================
# 6. Preview (table formatting)
# ============================================================================


class TestPreview:
    def test_basic_preview(self):
        text = "name,age\nAlice,30\nBob,25\n"
        dialect = DialectResult(delimiter=",", has_header=True, num_columns=2)
        result = preview(text, dialect, max_rows=3)
        assert "name" in result
        assert "Alice" in result

    def test_preview_no_header(self):
        text = "1,2,3\n4,5,6\n"
        dialect = DialectResult(delimiter=",", has_header=False, num_columns=3)
        result = preview(text, dialect, max_rows=5)
        assert "Col 1" in result

    def test_empty_table(self):
        result = format_table([], has_header=True)
        assert result == "(empty)"

    def test_truncation(self):
        assert _truncate("hello", 40) == "hello"
        long = "a" * 50
        result = _truncate(long, 40)
        assert len(result) == 40
        assert result.endswith("...")

    def test_control_chars_replaced(self):
        assert _truncate("hello\nworld", 40) == "hello\\nworld"

    def test_parse_rows_csv(self):
        text = "name,age\nAlice,30\nBob,25\n"
        dialect = DialectResult(delimiter=",", has_header=True, num_columns=2)
        rows = parse_rows(text, dialect)
        assert rows == [["name", "age"], ["Alice", "30"], ["Bob", "25"]]

    def test_parse_rows_escaped_quotes(self):
        text = 'name,desc\nAlice,"She said ""hi"""\n'
        dialect = DialectResult(delimiter=",", doublequote=True, has_header=True, num_columns=2)
        rows = parse_rows(text, dialect)
        assert rows[1][1] == 'She said "hi"'


# ============================================================================
# 7. Code generation
# ============================================================================


class TestCodegen:
    def test_default_csv_reader(self):
        dialect = DialectResult()
        code = generate_csv_reader(dialect)
        assert "import csv" in code
        assert "csv.reader(f)" in code
        assert "data.csv" in code

    def test_tab_delimiter(self):
        dialect = DialectResult(delimiter="\t")
        code = generate_csv_reader(dialect)
        assert 'delimiter="\\t"' in code

    def test_header_present(self):
        dialect = DialectResult(has_header=True)
        code = generate_csv_reader(dialect)
        assert "header = next(reader)" in code

    def test_no_header(self):
        dialect = DialectResult(has_header=False)
        code = generate_csv_reader(dialect)
        assert "header = next(reader)" not in code

    def test_encoding_latin1(self):
        dialect = DialectResult(encoding="latin-1")
        code = generate_csv_reader(dialect)
        assert 'encoding="latin-1"' in code

    def test_encoding_utf8_no_explicit(self):
        dialect = DialectResult(encoding="utf-8")
        code = generate_csv_reader(dialect)
        assert "encoding" not in code

    def test_escapechar(self):
        dialect = DialectResult(escapechar="\\")
        code = generate_csv_reader(dialect)
        assert "escapechar" in code

    def test_code_is_valid_python(self):
        dialect = DialectResult(delimiter="\t", encoding="latin-1", has_header=True)
        code = generate_csv_reader(dialect, "test.csv")
        compile(code, "<test>", "exec")

    def test_pandas_reader(self):
        dialect = DialectResult()
        code = generate_pandas_reader(dialect)
        assert "import pandas as pd" in code
        assert "pd.read_csv" in code

    def test_pandas_tab_delimiter(self):
        dialect = DialectResult(delimiter="\t")
        code = generate_pandas_reader(dialect)
        assert 'sep="\\t"' in code

    def test_pandas_no_header(self):
        dialect = DialectResult(has_header=False)
        code = generate_pandas_reader(dialect)
        assert "header=None" in code

    def test_generate_code_csv_style(self):
        dialect = DialectResult()
        code = generate_code(dialect, style="csv")
        assert "csv.reader" in code

    def test_generate_code_pandas_style(self):
        dialect = DialectResult()
        code = generate_code(dialect, style="pandas")
        assert "pd.read_csv" in code

    def test_fixed_width_csv_reader(self):
        dialect = DialectResult(is_fixed_width=True, column_widths=[10, 5, 8])
        code = generate_csv_reader(dialect)
        assert "Fixed-width" in code
        assert "[10, 5, 8]" in code

    def test_fixed_width_pandas(self):
        dialect = DialectResult(is_fixed_width=True, column_widths=[10, 5, 8])
        code = generate_pandas_reader(dialect)
        assert "pd.read_fwf" in code

    def test_repr_str_tab(self):
        assert _repr_str("\t") == '"\\t"'

    def test_repr_str_backslash(self):
        assert _repr_str("\\") == '"\\\\"'


# ============================================================================
# 8. DialectResult serialization
# ============================================================================


class TestDialectResult:
    def test_default_values(self):
        r = DialectResult()
        assert r.delimiter == ","
        assert r.quotechar == '"'
        assert r.escapechar is None
        assert r.doublequote is True
        assert r.encoding == "utf-8"
        assert r.has_header is True
        assert r.confidence == 0.0

    def test_to_dict(self):
        r = DialectResult(delimiter="\t", encoding="latin-1", confidence=0.85)
        d = r.to_dict()
        assert d["delimiter"] == "\\t"
        assert d["encoding"] == "latin-1"
        assert d["confidence"] == 0.85

    def test_to_dict_with_escapechar(self):
        r = DialectResult(escapechar="\\")
        d = r.to_dict()
        assert "escapechar" in d

    def test_to_dict_no_escapechar(self):
        r = DialectResult()
        d = r.to_dict()
        assert "escapechar" not in d

    def test_to_dict_confidence_rounded(self):
        r = DialectResult(confidence=0.33333333)
        d = r.to_dict()
        assert d["confidence"] == 0.333

    def test_to_dict_fixed_width(self):
        r = DialectResult(is_fixed_width=True, column_widths=[10, 5, 8])
        d = r.to_dict()
        assert d["is_fixed_width"] is True
        assert d["column_widths"] == [10, 5, 8]


# ============================================================================
# 9. Fixed-width detection
# ============================================================================


class TestFixedWidth:
    def test_fixed_width_data(self):
        lines = [
            "Name      Age City      ",
            "Alice      30 NYC       ",
            "Bob        25 LA        ",
            "Carol      35 Chicago   ",
        ]
        is_fw, widths = detect_fixed_width(lines)
        assert is_fw is True
        assert len(widths) >= 2

    def test_single_line_not_fixed(self):
        is_fw, widths = detect_fixed_width(["hello world"])
        assert is_fw is False

    def test_empty_not_fixed(self):
        is_fw, widths = detect_fixed_width([])
        assert is_fw is False


# ============================================================================
# 10. Line splitting
# ============================================================================


class TestLineSplitting:
    def test_unix(self):
        assert _split_lines_preserve("a\nb\nc") == ["a", "b", "c"]

    def test_windows(self):
        assert _split_lines_preserve("a\r\nb\r\nc") == ["a", "b", "c"]

    def test_old_mac(self):
        assert _split_lines_preserve("a\rb\rc") == ["a", "b", "c"]

    def test_trailing_newline(self):
        assert _split_lines_preserve("a\nb\n") == ["a", "b"]

    def test_empty_string(self):
        assert _split_lines_preserve("") == []


# ============================================================================
# 11. Line terminator detection
# ============================================================================


class TestLineTerminator:
    def test_unix_lf(self):
        assert detect_line_terminator("a\nb\nc\n") == "\n"

    def test_windows_crlf(self):
        assert detect_line_terminator("a\r\nb\r\nc\r\n") == "\r\n"

    def test_old_mac_cr(self):
        assert detect_line_terminator("a\rb\rc\r") == "\r"

    def test_empty_defaults_to_lf(self):
        assert detect_line_terminator("") == "\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
