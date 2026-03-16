"""
Markdown Table Formatter — Parse, Format, Sort, and Convert Markdown Tables

Parses GFM pipe tables (including broken ones), aligns columns with
Unicode-aware width calculation, sorts rows by any column, and converts
between markdown, CSV, TSV, JSON, and HTML.

Handles:
- Missing leading/trailing pipes
- Inconsistent column counts (pads with empty cells)
- Alignment indicators (:---, :---:, ---:)
- Escaped pipes within cells
- CJK wide characters for correct alignment
- Numeric auto-detection for sorting and alignment

Pure Python, no external dependencies.

Usage:
    python formatter.py format [--auto-align] [--compact] [FILE]
    python formatter.py sort --by COLUMN [--desc] [FILE]
    python formatter.py convert --from FMT --to FMT [FILE]
    python formatter.py check [FILE]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from enum import Enum


# ===================================================================
# Parser — parse markdown pipe tables
# ===================================================================

class Alignment(Enum):
    """Column alignment."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    NONE = "none"


class Style(Enum):
    """Output formatting style."""
    PADDED = "padded"
    COMPACT = "compact"


class SortOrder(Enum):
    """Sort direction."""
    ASCENDING = "asc"
    DESCENDING = "desc"


@dataclass
class Table:
    """Parsed markdown table."""
    headers: list[str]
    rows: list[list[str]]
    alignments: list[Alignment]
    original_col_count: int = 0

    @property
    def col_count(self) -> int:
        return len(self.headers)

    @property
    def row_count(self) -> int:
        return len(self.rows)


@dataclass
class SortKey:
    """Specification for sorting by a column."""
    column: int | str
    order: SortOrder = SortOrder.ASCENDING
    numeric: bool | None = None


def parse(text: str) -> Table:
    """Parse a markdown pipe table from text.

    Handles standard GFM pipe tables and broken tables with missing
    pipes, inconsistent column counts, and escaped pipes.

    Args:
        text: Markdown text containing a pipe table.

    Returns:
        Parsed Table object.

    Raises:
        ValueError: If text does not contain a valid table.
    """
    lines = text.strip().splitlines()
    lines = [line.strip() for line in lines if line.strip()]

    if len(lines) < 2:
        raise ValueError(
            "A markdown table requires at least a header row and a separator row"
        )

    sep_idx = _find_separator(lines)
    if sep_idx is None:
        raise ValueError(
            "No separator row found. A valid markdown table needs a row like |---|---|"
        )

    header_line = lines[sep_idx - 1] if sep_idx > 0 else ""
    if not header_line:
        raise ValueError("No header row found before separator")

    headers = _split_row(header_line)
    alignments = _parse_alignments(lines[sep_idx])

    rows = []
    for i in range(sep_idx + 1, len(lines)):
        rows.append(_split_row(lines[i]))

    max_cols = max(
        len(headers),
        len(alignments),
        max((len(r) for r in rows), default=0),
    )

    headers = _pad_list(headers, max_cols)
    alignments = _pad_alignments(alignments, max_cols)
    rows = [_pad_list(row, max_cols) for row in rows]

    return Table(
        headers=headers, rows=rows, alignments=alignments,
        original_col_count=max_cols,
    )


def parse_multiple(text: str) -> list[Table]:
    """Parse all markdown tables from a text."""
    tables = []
    blocks = _extract_table_blocks(text)
    for block in blocks:
        try:
            tables.append(parse(block))
        except ValueError:
            continue
    return tables


def _find_separator(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if _is_separator(line):
            return i
    return None


def _is_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped or "-" not in stripped:
        return False
    return all(c in "|-: " for c in stripped)


def _split_row(line: str) -> list[str]:
    placeholder = "\x00PIPE\x00"
    line = line.replace("\\|", placeholder)
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    cells = stripped.split("|")
    return [cell.replace(placeholder, "|").strip() for cell in cells]


def _parse_alignments(sep_line: str) -> list[Alignment]:
    cells = _split_row(sep_line)
    alignments = []
    for cell in cells:
        cell = cell.strip().replace(" ", "")
        if not cell:
            alignments.append(Alignment.NONE)
            continue
        starts = cell.startswith(":")
        ends = cell.endswith(":")
        if starts and ends:
            alignments.append(Alignment.CENTER)
        elif starts:
            alignments.append(Alignment.LEFT)
        elif ends:
            alignments.append(Alignment.RIGHT)
        else:
            alignments.append(Alignment.NONE)
    return alignments


def _pad_list(lst: list[str], target: int) -> list[str]:
    if len(lst) >= target:
        return lst[:target]
    return lst + [""] * (target - len(lst))


def _pad_alignments(aligns: list[Alignment], target: int) -> list[Alignment]:
    if len(aligns) >= target:
        return aligns[:target]
    return aligns + [Alignment.NONE] * (target - len(aligns))


def _extract_table_blocks(text: str) -> list[str]:
    lines = text.splitlines()
    blocks = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if ("|" in stripped) or _is_separator(stripped):
            current.append(line)
        else:
            if current and any(_is_separator(l.strip()) for l in current):
                blocks.append("\n".join(current))
            current = []
    if current and any(_is_separator(l.strip()) for l in current):
        blocks.append("\n".join(current))
    return blocks


# ===================================================================
# Formatter — align, pad, normalize
# ===================================================================

def format_table(
    table: Table,
    style: Style = Style.PADDED,
    auto_align: bool = False,
) -> str:
    """Format a table as a markdown pipe table string."""
    alignments = list(table.alignments)
    if auto_align:
        alignments = _auto_detect_alignments(table)

    col_widths = _calculate_col_widths(table)
    col_widths = [max(w, 3) for w in col_widths]

    lines = []
    lines.append(_format_row(table.headers, col_widths, alignments, style))
    lines.append(_format_separator(col_widths, alignments, style))
    for row in table.rows:
        lines.append(_format_row(row, col_widths, alignments, style))
    return "\n".join(lines)


def normalize(text: str, style: Style = Style.PADDED, auto_align: bool = False) -> str:
    """Parse and reformat a markdown table in one step."""
    return format_table(parse(text), style=style, auto_align=auto_align)


def _format_row(cells, widths, alignments, style):
    parts = []
    for i, cell in enumerate(cells):
        width = widths[i] if i < len(widths) else 3
        alignment = alignments[i] if i < len(alignments) else Alignment.NONE
        padded = _pad_cell(cell, width, alignment)
        if style == Style.PADDED:
            parts.append(f" {padded} ")
        else:
            parts.append(padded)
    return "|" + "|".join(parts) + "|"


def _format_separator(widths, alignments, style):
    parts = []
    for i, width in enumerate(widths):
        alignment = alignments[i] if i < len(alignments) else Alignment.NONE
        if alignment == Alignment.LEFT:
            sep = ":" + "-" * (width - 1)
        elif alignment == Alignment.CENTER:
            sep = ":" + "-" * (width - 2) + ":"
        elif alignment == Alignment.RIGHT:
            sep = "-" * (width - 1) + ":"
        else:
            sep = "-" * width
        if style == Style.PADDED:
            parts.append(f" {sep} ")
        else:
            parts.append(sep)
    return "|" + "|".join(parts) + "|"


def _pad_cell(cell, width, alignment):
    cell_width = _display_width(cell)
    padding = width - cell_width
    if padding <= 0:
        return cell
    if alignment in (Alignment.LEFT, Alignment.NONE):
        return cell + " " * padding
    elif alignment == Alignment.RIGHT:
        return " " * padding + cell
    elif alignment == Alignment.CENTER:
        left = padding // 2
        right = padding - left
        return " " * left + cell + " " * right
    return cell + " " * padding


def _calculate_col_widths(table):
    widths = [_display_width(h) for h in table.headers]
    for row in table.rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], _display_width(cell))
            else:
                widths.append(_display_width(cell))
    return widths


def _display_width(text: str) -> int:
    """Calculate display width, accounting for CJK wide characters."""
    width = 0
    for char in text:
        eaw = unicodedata.east_asian_width(char)
        cat = unicodedata.category(char)
        if cat.startswith("M"):
            continue
        elif eaw in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def _auto_detect_alignments(table):
    alignments = []
    for col_idx in range(table.col_count):
        if col_idx < len(table.alignments) and table.alignments[col_idx] == Alignment.CENTER:
            alignments.append(Alignment.CENTER)
            continue
        non_empty = [
            row[col_idx].strip()
            for row in table.rows
            if col_idx < len(row) and row[col_idx].strip()
        ]
        if non_empty and all(_is_numeric(c) for c in non_empty):
            alignments.append(Alignment.RIGHT)
        else:
            alignments.append(Alignment.LEFT)
    return alignments


def _is_numeric(text: str) -> bool:
    text = text.strip().lstrip("$+-").rstrip("%").strip().replace(",", "")
    if not text:
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


# ===================================================================
# Sorter — sort table rows
# ===================================================================

def sort_table(
    table: Table,
    column: int | str,
    order: SortOrder = SortOrder.ASCENDING,
    numeric: bool | None = None,
) -> Table:
    """Sort table rows by a single column."""
    col_idx = _resolve_column(table, column)
    use_numeric = _should_sort_numeric(table, col_idx) if numeric is None else numeric

    non_empty = []
    empty = []
    for row in table.rows:
        cell = row[col_idx].strip() if col_idx < len(row) else ""
        if cell:
            non_empty.append(row)
        else:
            empty.append(row)

    non_empty.sort(
        key=lambda row: _sort_key_value(row, col_idx, use_numeric),
        reverse=(order == SortOrder.DESCENDING),
    )

    return Table(
        headers=list(table.headers),
        rows=non_empty + empty,
        alignments=list(table.alignments),
        original_col_count=table.original_col_count,
    )


def sort_table_multi(table: Table, keys: list[SortKey]) -> Table:
    """Sort table rows by multiple columns."""
    if not keys:
        return table

    sorted_rows = list(table.rows)
    for key in reversed(keys):
        col_idx = _resolve_column(table, key.column)
        use_numeric = (
            _should_sort_numeric(table, col_idx) if key.numeric is None else key.numeric
        )
        non_empty = []
        empty = []
        for row in sorted_rows:
            cell = row[col_idx].strip() if col_idx < len(row) else ""
            if cell:
                non_empty.append(row)
            else:
                empty.append(row)
        non_empty.sort(
            key=lambda row, ci=col_idx, un=use_numeric: _sort_key_value(row, ci, un),
            reverse=(key.order == SortOrder.DESCENDING),
        )
        sorted_rows = non_empty + empty

    return Table(
        headers=list(table.headers), rows=sorted_rows,
        alignments=list(table.alignments),
        original_col_count=table.original_col_count,
    )


def _resolve_column(table, column):
    if isinstance(column, int):
        if column < 0 or column >= table.col_count:
            raise ValueError(
                f"Column index {column} out of range (0-{table.col_count - 1})"
            )
        return column
    if isinstance(column, str):
        lower = column.lower().strip()
        for i, h in enumerate(table.headers):
            if h.lower().strip() == lower:
                return i
        raise ValueError(f"Column '{column}' not found")
    raise TypeError(f"Column must be int or str, got {type(column).__name__}")


def _should_sort_numeric(table, col_idx):
    non_empty = [
        row[col_idx].strip()
        for row in table.rows
        if col_idx < len(row) and row[col_idx].strip()
    ]
    if not non_empty:
        return False
    return all(_try_parse_number(c) is not None for c in non_empty)


def _sort_key_value(row, col_idx, numeric):
    cell = row[col_idx].strip() if col_idx < len(row) else ""
    if numeric:
        num = _try_parse_number(cell)
        if num is not None:
            return (0, num)
        return (1, cell.lower())
    return cell.lower()


def _try_parse_number(text):
    text = text.strip().lstrip("$")
    is_negative = text.startswith("-") or text.startswith("(")
    text = text.lstrip("+-").rstrip("%").rstrip(")").lstrip("(").strip().replace(",", "")
    if not text:
        return None
    try:
        value = float(text)
        return -value if is_negative else value
    except ValueError:
        return None


# ===================================================================
# Converter — CSV, TSV, JSON, HTML
# ===================================================================

def csv_to_table(text: str, delimiter: str = ",", has_header: bool = True) -> Table:
    """Parse CSV text into a Table."""
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    all_rows = list(reader)
    if not all_rows:
        raise ValueError("CSV contains no data")
    if has_header:
        headers = all_rows[0]
        rows = all_rows[1:]
    else:
        max_cols = max(len(r) for r in all_rows)
        headers = [f"Column {i + 1}" for i in range(max_cols)]
        rows = all_rows
    max_cols = max(len(headers), max((len(r) for r in rows), default=0))
    return Table(
        headers=_pad_list(headers, max_cols),
        rows=[_pad_list(r, max_cols) for r in rows],
        alignments=[Alignment.NONE] * max_cols,
        original_col_count=max_cols,
    )


def csv_to_markdown(text, delimiter=",", has_header=True, style=Style.PADDED):
    return format_table(csv_to_table(text, delimiter, has_header), style=style)


def table_to_csv(table: Table, delimiter: str = ",") -> str:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
    writer.writerow(table.headers)
    for row in table.rows:
        writer.writerow(row)
    return output.getvalue()


def markdown_to_csv(text, delimiter=","):
    return table_to_csv(parse(text), delimiter)


def tsv_to_table(text, has_header=True):
    return csv_to_table(text, delimiter="\t", has_header=has_header)


def tsv_to_markdown(text, has_header=True, style=Style.PADDED):
    return csv_to_markdown(text, delimiter="\t", has_header=has_header, style=style)


def table_to_tsv(table):
    return table_to_csv(table, delimiter="\t")


def markdown_to_tsv(text):
    return markdown_to_csv(text, delimiter="\t")


def json_to_table(text: str) -> Table:
    """Parse JSON (list of objects) into a Table."""
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of objects")
    if not data:
        raise ValueError("JSON list is empty")
    if not isinstance(data[0], dict):
        raise ValueError("JSON list must contain objects (dicts)")
    seen: dict[str, None] = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("All items in JSON list must be objects")
        for key in item:
            if key not in seen:
                seen[key] = None
    headers = list(seen.keys())
    rows = [[str(item.get(key, "")) for key in headers] for item in data]
    return Table(
        headers=headers, rows=rows,
        alignments=[Alignment.NONE] * len(headers),
        original_col_count=len(headers),
    )


def json_to_markdown(text, style=Style.PADDED):
    return format_table(json_to_table(text), style=style)


def table_to_json(table: Table, indent: int = 2) -> str:
    data = []
    for row in table.rows:
        obj = {table.headers[i]: (row[i] if i < len(row) else "") for i in range(len(table.headers))}
        data.append(obj)
    return json.dumps(data, indent=indent, ensure_ascii=False)


def markdown_to_json(text, indent=2):
    return table_to_json(parse(text), indent)


def table_to_html(table: Table, class_name: str | None = None) -> str:
    parts = []
    if class_name:
        parts.append(f'<table class="{_escape_html(class_name)}">')
    else:
        parts.append("<table>")
    parts.append("  <thead>")
    parts.append("    <tr>")
    for i, h in enumerate(table.headers):
        attr = _html_align(table.alignments[i] if i < len(table.alignments) else Alignment.NONE)
        parts.append(f"      <th{attr}>{_escape_html(h)}</th>")
    parts.append("    </tr>")
    parts.append("  </thead>")
    parts.append("  <tbody>")
    for row in table.rows:
        parts.append("    <tr>")
        for i, cell in enumerate(row):
            attr = _html_align(table.alignments[i] if i < len(table.alignments) else Alignment.NONE)
            parts.append(f"      <td{attr}>{_escape_html(cell)}</td>")
        parts.append("    </tr>")
    parts.append("  </tbody>")
    parts.append("</table>")
    return "\n".join(parts)


def markdown_to_html(text, class_name=None):
    return table_to_html(parse(text), class_name)


def html_to_table(text: str) -> Table:
    """Parse an HTML table into a Table."""
    match = re.search(r"<table[^>]*>(.*?)</table>", text, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError("No HTML table found")
    content = match.group(1)
    row_pat = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
    cell_pat = re.compile(r"<(th|td)[^>]*>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
    all_rows, is_header = [], []
    for rm in row_pat.finditer(content):
        cells, has_th = [], False
        for cm in cell_pat.finditer(rm.group(1)):
            cells.append(re.sub(r"<[^>]+>", "", cm.group(2)).strip())
            if cm.group(1).lower() == "th":
                has_th = True
        if cells:
            all_rows.append(cells)
            is_header.append(has_th)
    if not all_rows:
        raise ValueError("HTML table contains no rows")
    if is_header[0]:
        headers, rows = all_rows[0], all_rows[1:]
    else:
        max_c = max(len(r) for r in all_rows)
        headers = [f"Column {i+1}" for i in range(max_c)]
        rows = all_rows
    max_c = max(len(headers), max((len(r) for r in rows), default=0))
    return Table(
        headers=_pad_list(headers, max_c),
        rows=[_pad_list(r, max_c) for r in rows],
        alignments=[Alignment.NONE] * max_c,
        original_col_count=max_c,
    )


def html_to_markdown(text, style=Style.PADDED):
    return format_table(html_to_table(text), style=style)


def _escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _html_align(alignment):
    if alignment == Alignment.LEFT:
        return ' style="text-align: left"'
    if alignment == Alignment.CENTER:
        return ' style="text-align: center"'
    if alignment == Alignment.RIGHT:
        return ' style="text-align: right"'
    return ""


# ===================================================================
# CLI
# ===================================================================

def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser_arg = argparse.ArgumentParser(
        prog="mdtable",
        description="Parse, format, sort, and convert markdown tables.",
    )
    subs = parser_arg.add_subparsers(dest="command", help="Available commands")

    # format
    fmt = subs.add_parser("format", help="Reformat a markdown table")
    fmt.add_argument("file", nargs="?", default="-")
    fmt.add_argument("--auto-align", action="store_true")
    fmt.add_argument("--compact", action="store_true")

    # sort
    srt = subs.add_parser("sort", help="Sort table rows by a column")
    srt.add_argument("file", nargs="?", default="-")
    srt.add_argument("--by", required=True)
    srt.add_argument("--desc", action="store_true")
    srt.add_argument("--numeric", action="store_true", default=None)
    srt.add_argument("--alpha", action="store_true")

    # convert
    cnv = subs.add_parser("convert", help="Convert between table formats")
    cnv.add_argument("file", nargs="?", default="-")
    cnv.add_argument("--from", dest="from_fmt", required=True,
                     choices=["markdown", "csv", "tsv", "json", "html"])
    cnv.add_argument("--to", dest="to_fmt", required=True,
                     choices=["markdown", "csv", "tsv", "json", "html"])
    cnv.add_argument("--no-header", action="store_true")

    # check
    chk = subs.add_parser("check", help="Check if a table is well-formed")
    chk.add_argument("file", nargs="?", default="-")

    args = parser_arg.parse_args(argv)
    if args.command is None:
        parser_arg.print_help()
        return 0

    try:
        text = sys.stdin.read() if getattr(args, "file", "-") == "-" else open(args.file, encoding="utf-8").read()

        if args.command == "format":
            style = Style.COMPACT if args.compact else Style.PADDED
            print(format_table(parse(text), style=style, auto_align=args.auto_align))

        elif args.command == "sort":
            table = parse(text)
            try:
                col = int(args.by)
            except ValueError:
                col = args.by
            order = SortOrder.DESCENDING if args.desc else SortOrder.ASCENDING
            num = True if args.numeric else (False if args.alpha else None)
            print(format_table(sort_table(table, col, order, num)))

        elif args.command == "convert":
            has_hdr = not args.no_header
            if args.from_fmt == "markdown":
                tbl = parse(text)
            elif args.from_fmt == "csv":
                tbl = csv_to_table(text, has_header=has_hdr)
            elif args.from_fmt == "tsv":
                tbl = tsv_to_table(text, has_header=has_hdr)
            elif args.from_fmt == "json":
                tbl = json_to_table(text)
            elif args.from_fmt == "html":
                tbl = html_to_table(text)
            else:
                return 1

            if args.to_fmt == "markdown":
                print(format_table(tbl))
            elif args.to_fmt == "csv":
                sys.stdout.write(table_to_csv(tbl))
            elif args.to_fmt == "tsv":
                sys.stdout.write(table_to_tsv(tbl))
            elif args.to_fmt == "json":
                print(table_to_json(tbl))
            elif args.to_fmt == "html":
                print(table_to_html(tbl))

        elif args.command == "check":
            try:
                tbl = parse(text)
            except ValueError as e:
                print(f"INVALID: {e}")
                return 1
            issues = []
            lines = text.strip().splitlines()
            for line in lines:
                s = line.strip()
                if "|" in s and not s.startswith("|"):
                    issues.append("Missing leading pipe")
                    break
            for line in lines:
                s = line.strip()
                if "|" in s and not s.endswith("|"):
                    issues.append("Missing trailing pipe")
                    break
            if issues:
                print("ISSUES FOUND:")
                for issue in issues:
                    print(f"  - {issue}")
                return 1
            print(f"OK: {tbl.col_count} columns, {tbl.row_count} rows")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
