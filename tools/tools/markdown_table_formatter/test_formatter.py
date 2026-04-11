"""
Tests for Markdown Table Formatter.

These tests ARE the spec — if an LLM regenerates the formatter in any
language, these cases define correctness.
"""

import json
import subprocess
import sys

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from formatter import (
    parse,
    parse_multiple,
    format_table,
    normalize,
    sort_table,
    sort_table_multi,
    csv_to_table,
    csv_to_markdown,
    table_to_csv,
    markdown_to_csv,
    tsv_to_table,
    table_to_tsv,
    json_to_table,
    table_to_json,
    markdown_to_json,
    table_to_html,
    markdown_to_html,
    html_to_table,
    html_to_markdown,
    Table,
    Alignment,
    Style,
    SortOrder,
    SortKey,
    _display_width,
    _is_numeric,
    _is_separator,
    _split_row,
    _try_parse_number,
)


# ============================================================
# 1. Parsing — standard tables
# ============================================================

class TestParsing:
    def test_basic_table(self):
        text = "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |"
        t = parse(text)
        assert t.headers == ["Name", "Age"]
        assert t.rows == [["Alice", "30"], ["Bob", "25"]]
        assert t.col_count == 2
        assert t.row_count == 2

    def test_single_row(self):
        text = "| A |\n|---|\n| 1 |"
        t = parse(text)
        assert t.row_count == 1

    def test_no_data_rows(self):
        text = "| A | B |\n|---|---|"
        t = parse(text)
        assert t.row_count == 0

    def test_whitespace_stripped(self):
        text = "|  Name  |  Age  |\n|--------|-------|\n|  Alice |  30   |"
        t = parse(text)
        assert t.headers == ["Name", "Age"]
        assert t.rows[0] == ["Alice", "30"]


# ============================================================
# 2. Parsing — broken tables
# ============================================================

class TestBrokenParsing:
    def test_missing_leading_pipe(self):
        text = "Name | Age |\n------|-----|\nAlice | 30 |"
        t = parse(text)
        assert t.headers == ["Name", "Age"]

    def test_missing_trailing_pipe(self):
        text = "| Name | Age\n|------|-----\n| Alice | 30"
        t = parse(text)
        assert t.rows[0] == ["Alice", "30"]

    def test_inconsistent_columns(self):
        text = "| A | B | C |\n|---|---|---|\n| 1 | 2 |\n| 3 | 4 | 5 | 6 |"
        t = parse(text)
        assert t.col_count == 4
        assert t.rows[0][2] == ""
        assert t.rows[1] == ["3", "4", "5", "6"]

    def test_escaped_pipe(self):
        text = "| Expr | Result |\n|------|--------|\n| a \\| b | true |"
        t = parse(text)
        assert t.rows[0][0] == "a | b"


# ============================================================
# 3. Alignment detection
# ============================================================

class TestAlignment:
    def test_left(self):
        text = "| A |\n|:---|\n| 1 |"
        assert parse(text).alignments[0] == Alignment.LEFT

    def test_right(self):
        text = "| A |\n|---:|\n| 1 |"
        assert parse(text).alignments[0] == Alignment.RIGHT

    def test_center(self):
        text = "| A |\n|:---:|\n| 1 |"
        assert parse(text).alignments[0] == Alignment.CENTER

    def test_none(self):
        text = "| A |\n|---|\n| 1 |"
        assert parse(text).alignments[0] == Alignment.NONE

    def test_mixed(self):
        text = "| L | C | R | N |\n|:---|:---:|---:|---|\n| 1 | 2 | 3 | 4 |"
        t = parse(text)
        assert t.alignments == [
            Alignment.LEFT, Alignment.CENTER, Alignment.RIGHT, Alignment.NONE,
        ]


# ============================================================
# 4. Formatting output
# ============================================================

class TestFormatting:
    def test_basic_format(self):
        t = Table(
            headers=["Name", "Age"], rows=[["Alice", "30"]],
            alignments=[Alignment.NONE, Alignment.NONE],
        )
        result = format_table(t)
        lines = result.splitlines()
        assert len(lines) == 3
        for line in lines:
            assert line.startswith("|") and line.endswith("|")

    def test_columns_aligned(self):
        t = Table(
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
            alignments=[Alignment.NONE, Alignment.NONE],
        )
        result = format_table(t)
        lines = result.splitlines()
        lens = [len(l) for l in lines]
        assert len(set(lens)) == 1  # all same length

    def test_right_alignment_in_separator(self):
        t = Table(
            headers=["Price"], rows=[["9.99"]],
            alignments=[Alignment.RIGHT],
        )
        sep = format_table(t).splitlines()[1]
        content = sep.strip("|").strip()
        assert content.endswith(":")
        assert not content.startswith(":")

    def test_center_alignment_in_separator(self):
        t = Table(
            headers=["Status"], rows=[["OK"]],
            alignments=[Alignment.CENTER],
        )
        sep = format_table(t).splitlines()[1]
        content = sep.strip("|").strip()
        assert content.startswith(":") and content.endswith(":")

    def test_compact_style(self):
        t = Table(headers=["A"], rows=[["1"]], alignments=[Alignment.NONE])
        result = format_table(t, style=Style.COMPACT)
        assert result.startswith("|")


# ============================================================
# 5. Auto-alignment
# ============================================================

class TestAutoAlign:
    def test_numeric_right_aligns(self):
        t = Table(
            headers=["Score"], rows=[["95"], ["87"]],
            alignments=[Alignment.NONE],
        )
        result = format_table(t, auto_align=True)
        sep = result.splitlines()[1]
        assert sep.strip("|").strip().endswith(":")

    def test_text_left_aligns(self):
        t = Table(
            headers=["Name"], rows=[["Alice"], ["Bob"]],
            alignments=[Alignment.NONE],
        )
        result = format_table(t, auto_align=True)
        sep = result.splitlines()[1]
        assert sep.strip("|").strip().startswith(":")

    def test_currency_right_aligns(self):
        t = Table(
            headers=["Cost"], rows=[["$100"], ["$50"]],
            alignments=[Alignment.NONE],
        )
        result = format_table(t, auto_align=True)
        sep = result.splitlines()[1]
        assert sep.strip("|").strip().endswith(":")


# ============================================================
# 6. Unicode width
# ============================================================

class TestUnicodeWidth:
    def test_ascii(self):
        assert _display_width("hello") == 5

    def test_cjk(self):
        assert _display_width("\u4e16\u754c") == 4

    def test_mixed(self):
        assert _display_width("A\u4e16B") == 4

    def test_empty(self):
        assert _display_width("") == 0


# ============================================================
# 7. Sorting
# ============================================================

class TestSorting:
    def test_alphabetical_ascending(self):
        t = Table(
            headers=["Name"], rows=[["Carol"], ["Alice"], ["Bob"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0)
        assert [r[0] for r in s.rows] == ["Alice", "Bob", "Carol"]

    def test_alphabetical_descending(self):
        t = Table(
            headers=["Name"], rows=[["Alice"], ["Carol"], ["Bob"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0, order=SortOrder.DESCENDING)
        assert [r[0] for r in s.rows] == ["Carol", "Bob", "Alice"]

    def test_numeric_auto_detect(self):
        t = Table(
            headers=["Score"], rows=[["10"], ["2"], ["30"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0)
        assert [r[0] for r in s.rows] == ["2", "10", "30"]

    def test_numeric_descending(self):
        t = Table(
            headers=["Score"], rows=[["10"], ["2"], ["30"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0, order=SortOrder.DESCENDING)
        assert [r[0] for r in s.rows] == ["30", "10", "2"]

    def test_currency_sort(self):
        t = Table(
            headers=["Price"], rows=[["$10"], ["$2"], ["$30"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0)
        assert [r[0] for r in s.rows] == ["$2", "$10", "$30"]

    def test_empty_cells_sort_last_ascending(self):
        t = Table(
            headers=["Name"], rows=[["Bob"], [""], ["Alice"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0)
        assert [r[0] for r in s.rows] == ["Alice", "Bob", ""]

    def test_empty_cells_sort_last_descending(self):
        t = Table(
            headers=["Name"], rows=[["Bob"], [""], ["Alice"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0, order=SortOrder.DESCENDING)
        assert [r[0] for r in s.rows] == ["Bob", "Alice", ""]

    def test_sort_by_header_name(self):
        t = Table(
            headers=["Name", "Age"],
            rows=[["Bob", "25"], ["Alice", "30"]],
            alignments=[Alignment.NONE, Alignment.NONE],
        )
        s = sort_table(t, "Name")
        assert [r[0] for r in s.rows] == ["Alice", "Bob"]

    def test_case_insensitive(self):
        t = Table(
            headers=["Name"], rows=[["bob"], ["Alice"], ["CAROL"]],
            alignments=[Alignment.NONE],
        )
        s = sort_table(t, 0)
        assert [r[0] for r in s.rows] == ["Alice", "bob", "CAROL"]

    def test_multi_key_sort(self):
        t = Table(
            headers=["City", "Name"],
            rows=[["NYC", "Bob"], ["LA", "Alice"], ["NYC", "Alice"], ["LA", "Bob"]],
            alignments=[Alignment.NONE, Alignment.NONE],
        )
        s = sort_table_multi(t, [SortKey(column="City"), SortKey(column="Name")])
        assert s.rows == [
            ["LA", "Alice"], ["LA", "Bob"], ["NYC", "Alice"], ["NYC", "Bob"],
        ]

    def test_invalid_column_raises(self):
        t = Table(headers=["A"], rows=[["1"]], alignments=[Alignment.NONE])
        with pytest.raises(ValueError):
            sort_table(t, 5)

    def test_invalid_column_name_raises(self):
        t = Table(headers=["A"], rows=[["1"]], alignments=[Alignment.NONE])
        with pytest.raises(ValueError):
            sort_table(t, "Z")


# ============================================================
# 8. Number parsing
# ============================================================

class TestNumberParsing:
    def test_integer(self):
        assert _try_parse_number("42") == 42.0

    def test_float(self):
        assert _try_parse_number("3.14") == pytest.approx(3.14)

    def test_negative(self):
        assert _try_parse_number("-7") == -7.0

    def test_currency(self):
        assert _try_parse_number("$1,234") == 1234.0

    def test_percentage(self):
        assert _try_parse_number("95%") == 95.0

    def test_text_none(self):
        assert _try_parse_number("hello") is None

    def test_empty_none(self):
        assert _try_parse_number("") is None


# ============================================================
# 9. CSV conversion
# ============================================================

class TestCSV:
    def test_csv_to_table(self):
        t = csv_to_table("Name,Age\nAlice,30\n")
        assert t.headers == ["Name", "Age"]
        assert t.rows == [["Alice", "30"]]

    def test_csv_with_quotes(self):
        t = csv_to_table('Name,Bio\nAlice,"Has a cat, dog"\n')
        assert t.rows[0][1] == "Has a cat, dog"

    def test_csv_no_header(self):
        t = csv_to_table("Alice,30\n", has_header=False)
        assert "Column" in t.headers[0]
        assert t.rows[0] == ["Alice", "30"]

    def test_table_to_csv(self):
        t = Table(
            headers=["Name", "Age"], rows=[["Alice", "30"]],
            alignments=[Alignment.NONE, Alignment.NONE],
        )
        result = table_to_csv(t)
        assert "Name,Age" in result
        assert "Alice,30" in result

    def test_csv_round_trip(self):
        original = "Name,Age\nAlice,30\nBob,25\n"
        t = csv_to_table(original)
        csv2 = table_to_csv(t)
        t2 = csv_to_table(csv2)
        assert t2.headers == t.headers
        assert t2.rows == t.rows

    def test_markdown_csv_round_trip(self):
        md = "| Name | Age |\n|------|-----|\n| Alice | 30 |"
        csv_text = markdown_to_csv(md)
        md2 = csv_to_markdown(csv_text)
        t1, t2 = parse(md), parse(md2)
        assert t1.headers == t2.headers
        assert t1.rows == t2.rows

    def test_empty_csv_raises(self):
        with pytest.raises(ValueError):
            csv_to_table("")


# ============================================================
# 10. TSV conversion
# ============================================================

class TestTSV:
    def test_tsv_to_table(self):
        t = tsv_to_table("Name\tAge\nAlice\t30\n")
        assert t.headers == ["Name", "Age"]

    def test_table_to_tsv(self):
        t = Table(
            headers=["Name"], rows=[["Alice"]],
            alignments=[Alignment.NONE],
        )
        assert "\t" not in table_to_tsv(t) or "Name" in table_to_tsv(t)

    def test_tsv_round_trip(self):
        original = "A\tB\n1\t2\n"
        t = tsv_to_table(original)
        tsv2 = table_to_tsv(t)
        t2 = tsv_to_table(tsv2)
        assert t2.headers == t.headers
        assert t2.rows == t.rows


# ============================================================
# 11. JSON conversion
# ============================================================

class TestJSON:
    def test_json_to_table(self):
        t = json_to_table('[{"name": "Alice", "age": "30"}]')
        assert t.headers == ["name", "age"]
        assert t.rows == [["Alice", "30"]]

    def test_json_missing_keys(self):
        t = json_to_table('[{"a": "1", "b": "2"}, {"a": "3", "c": "4"}]')
        assert "a" in t.headers and "b" in t.headers and "c" in t.headers

    def test_table_to_json(self):
        t = Table(
            headers=["name"], rows=[["Alice"]],
            alignments=[Alignment.NONE],
        )
        data = json.loads(table_to_json(t))
        assert data[0]["name"] == "Alice"

    def test_json_round_trip(self):
        original = '[{"name": "Alice", "age": "30"}]'
        t = json_to_table(original)
        j2 = table_to_json(t)
        t2 = json_to_table(j2)
        assert t2.headers == t.headers
        assert t2.rows == t.rows

    def test_json_not_list_raises(self):
        with pytest.raises(ValueError):
            json_to_table('{"key": "value"}')

    def test_json_empty_raises(self):
        with pytest.raises(ValueError):
            json_to_table("[]")


# ============================================================
# 12. HTML conversion
# ============================================================

class TestHTML:
    def test_table_to_html(self):
        t = Table(
            headers=["Name"], rows=[["Alice"]],
            alignments=[Alignment.NONE],
        )
        html = table_to_html(t)
        assert "<table>" in html
        assert "<th>" in html
        assert "Alice" in html

    def test_html_escapes(self):
        t = Table(
            headers=["X"], rows=[["<b>hi</b>"]],
            alignments=[Alignment.NONE],
        )
        html = table_to_html(t)
        assert "&lt;b&gt;" in html

    def test_html_to_table(self):
        html = "<table><thead><tr><th>Name</th></tr></thead><tbody><tr><td>Alice</td></tr></tbody></table>"
        t = html_to_table(html)
        assert t.headers == ["Name"]
        assert t.rows == [["Alice"]]

    def test_html_round_trip(self):
        t = Table(
            headers=["A", "B"], rows=[["1", "2"]],
            alignments=[Alignment.NONE, Alignment.NONE],
        )
        html = table_to_html(t)
        t2 = html_to_table(html)
        assert t2.headers == t.headers
        assert t2.rows == t.rows

    def test_html_no_table_raises(self):
        with pytest.raises(ValueError):
            html_to_table("<p>no table</p>")


# ============================================================
# 13. normalize() convenience
# ============================================================

class TestNormalize:
    def test_normalizes_messy_table(self):
        text = "|Name|Age|\n|---|---|\n|Alice|30|\n|Bob|25|"
        result = normalize(text)
        lines = result.splitlines()
        assert len(lines) == 4
        for line in lines:
            assert line.startswith("|") and line.endswith("|")

    def test_normalize_auto_align(self):
        text = "| Name | Score |\n|------|-------|\n| Alice | 95 |"
        result = normalize(text, auto_align=True)
        sep = result.splitlines()[1]
        cells = sep.strip("|").split("|")
        assert cells[1].strip().endswith(":")


# ============================================================
# 14. parse_multiple
# ============================================================

class TestParseMultiple:
    def test_two_tables(self):
        text = "| A |\n|---|\n| 1 |\n\nSome text\n\n| X |\n|---|\n| 2 |"
        tables = parse_multiple(text)
        assert len(tables) == 2

    def test_no_tables(self):
        assert len(parse_multiple("Just text.")) == 0


# ============================================================
# 15. Separator detection
# ============================================================

class TestSeparator:
    def test_valid(self):
        assert _is_separator("|---|---|") is True

    def test_with_colons(self):
        assert _is_separator("|:---|---:|") is True

    def test_no_dashes(self):
        assert _is_separator("| a | b |") is False

    def test_empty(self):
        assert _is_separator("") is False


# ============================================================
# 16. Row splitting
# ============================================================

class TestSplitRow:
    def test_standard(self):
        assert _split_row("| a | b | c |") == ["a", "b", "c"]

    def test_no_outer_pipes(self):
        assert _split_row("a | b | c") == ["a", "b", "c"]

    def test_empty_cells(self):
        assert _split_row("| | b | |") == ["", "b", ""]


# ============================================================
# 17. is_numeric
# ============================================================

class TestIsNumeric:
    def test_integer(self):
        assert _is_numeric("42") is True

    def test_currency(self):
        assert _is_numeric("$1,234") is True

    def test_percentage(self):
        assert _is_numeric("95%") is True

    def test_text(self):
        assert _is_numeric("hello") is False

    def test_empty(self):
        assert _is_numeric("") is False


# ============================================================
# 18. Error handling
# ============================================================

class TestErrors:
    def test_too_few_lines(self):
        with pytest.raises(ValueError):
            parse("| just one |")

    def test_no_separator(self):
        with pytest.raises(ValueError):
            parse("| a |\n| b |")


# ============================================================
# 19. Content preservation
# ============================================================

class TestContentPreservation:
    def test_special_chars(self):
        text = "| Sym |\n|-----|\n| < |\n| > |\n| & |"
        t = parse(text)
        assert t.rows[0][0] == "<"
        assert t.rows[1][0] == ">"
        assert t.rows[2][0] == "&"

    def test_url_preserved(self):
        text = "| Link |\n|------|\n| https://example.com?q=1&r=2 |"
        t = parse(text)
        assert t.rows[0][0] == "https://example.com?q=1&r=2"


# ============================================================
# 20. CLI
# ============================================================

class TestCLI:
    def test_format(self):
        result = subprocess.run(
            [sys.executable, "formatter.py", "format"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
            input="| Name | Age |\n|------|-----|\n| Alice | 30 |",
        )
        assert result.returncode == 0
        assert "Name" in result.stdout

    def test_sort(self):
        result = subprocess.run(
            [sys.executable, "formatter.py", "sort", "--by", "0"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
            input="| Name |\n|------|\n| Carol |\n| Alice |\n| Bob |",
        )
        assert result.returncode == 0
        lines = result.stdout.strip().splitlines()
        names = [l.split("|")[1].strip() for l in lines[2:]]
        assert names == ["Alice", "Bob", "Carol"]

    def test_convert_csv_to_md(self):
        result = subprocess.run(
            [sys.executable, "formatter.py", "convert", "--from", "csv", "--to", "markdown"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
            input="Name,Age\nAlice,30\n",
        )
        assert result.returncode == 0
        assert "|" in result.stdout

    def test_convert_md_to_csv(self):
        result = subprocess.run(
            [sys.executable, "formatter.py", "convert", "--from", "markdown", "--to", "csv"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
            input="| Name | Age |\n|------|-----|\n| Alice | 30 |",
        )
        assert result.returncode == 0
        assert "Name,Age" in result.stdout

    def test_convert_md_to_json(self):
        result = subprocess.run(
            [sys.executable, "formatter.py", "convert", "--from", "markdown", "--to", "json"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
            input="| name |\n|------|\n| Alice |",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data[0]["name"] == "Alice"

    def test_check_valid(self):
        result = subprocess.run(
            [sys.executable, "formatter.py", "check"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
            input="| A | B |\n|---|---|\n| 1 | 2 |",
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_check_broken(self):
        result = subprocess.run(
            [sys.executable, "formatter.py", "check"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
            input="Name | Age\n------|-----\nAlice | 30",
        )
        assert result.returncode != 0

    def test_no_command(self):
        result = subprocess.run(
            [sys.executable, "formatter.py"],
            capture_output=True, text=True, cwd=_TOOL_DIR,
        )
        assert result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
