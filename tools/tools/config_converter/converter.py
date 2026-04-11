"""
Config File Converter — Convert between YAML, TOML, JSON, INI, and HCL.

Bidirectional conversion with comment preservation, nested structure handling,
automatic format detection. Pure Python, minimal dependencies (PyYAML only).

CAPABILITIES
============
1. Format Detection: auto-detect from extension and content heuristics
2. YAML: parse/serialize with comment extraction (via PyYAML)
3. TOML: read via tomllib (stdlib 3.11+), custom writer
4. JSON: stdlib json, JSONC comment stripping
5. INI: configparser with nested key flattening/unflattening
6. HCL: custom tokenizer+parser for Terraform-style configs
7. Comment Preservation: sidecar structure survives cross-format conversion
"""

from __future__ import annotations

import configparser
import enum
import io
import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import yaml


# ═══════════════════════════════════════════════════════════════════
# Comment sidecar structure
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CommentMap:
    """Stores comments keyed by dotted config path."""
    comments: dict[str, list[str]] = field(default_factory=dict)

    def add(self, path: str, comment: str) -> None:
        if path not in self.comments:
            self.comments[path] = []
        self.comments[path].append(comment)

    def add_inline(self, path: str, comment: str) -> None:
        self.add(f"inline:{path}", comment)

    def get(self, path: str) -> list[str]:
        return self.comments.get(path, [])

    def get_inline(self, path: str) -> str | None:
        lines = self.comments.get(f"inline:{path}", [])
        return lines[0] if lines else None

    def get_file_comments(self) -> list[str]:
        return self.comments.get("", [])

    def set_file_comments(self, comments: list[str]) -> None:
        self.comments[""] = comments

    def has_comments(self) -> bool:
        return bool(self.comments)

    def __bool__(self) -> bool:
        return self.has_comments()

    def __repr__(self) -> str:
        count = sum(len(v) for v in self.comments.values())
        return f"CommentMap({count} comment lines across {len(self.comments)} paths)"


# ═══════════════════════════════════════════════════════════════════
# Format enum and detection
# ═══════════════════════════════════════════════════════════════════

class Format(enum.Enum):
    YAML = "yaml"
    TOML = "toml"
    JSON = "json"
    INI = "ini"
    HCL = "hcl"

    def __str__(self) -> str:
        return self.value


_EXTENSION_MAP: dict[str, Format] = {
    ".yaml": Format.YAML, ".yml": Format.YAML,
    ".toml": Format.TOML,
    ".json": Format.JSON,
    ".ini": Format.INI, ".cfg": Format.INI, ".conf": Format.INI,
    ".hcl": Format.HCL, ".tf": Format.HCL, ".tfvars": Format.HCL,
}


def detect_format(source: str | Path, content: str | None = None) -> Format | None:
    ext = os.path.splitext(str(source))[1].lower()
    if ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext]
    if content is None:
        path = Path(source)
        if path.exists() and path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return None
        else:
            return None
    return _detect_from_content(content)


def _detect_from_content(content: str) -> Format | None:
    s = content.strip()
    if not s:
        return None
    if s.startswith("[["):
        if _looks_like_toml(s):
            return Format.TOML
    if s[0] in "{[":
        if s[0] == "{" and re.search(r'"[^"]*"\s*:', s[:500]):
            return Format.JSON
        if s[0] == "[" and re.search(r'[\[\{"\d]', s[1:100].strip()[:1] if s[1:100].strip() else ""):
            return Format.JSON
    lines = s.split("\n", 20)
    if lines[0].strip() == "---":
        return Format.YAML
    colon_count = equals_count = 0
    for line in lines[:20]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^[\w][\w\s.-]*:\s", line):
            colon_count += 1
        if re.match(r"^[\w][\w\s.-]*\s*=", line):
            equals_count += 1
        if line.startswith("- "):
            colon_count += 1
    if colon_count > 0 and colon_count > equals_count:
        return Format.YAML
    if _looks_like_toml(s):
        return Format.TOML
    if re.search(r'^\w+\s+(?:"[^"]*"\s+)*\{', s, re.MULTILINE):
        return Format.HCL
    if re.search(r'^(resource|variable|output|data|provider|terraform|locals|module)\s', s, re.MULTILINE):
        return Format.HCL
    has_section = has_kvp = False
    for line in s.split("\n", 30):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if re.match(r"^\[[^\]]+\]$", stripped):
            has_section = True
        if re.match(r"^[\w.-]+\s*=", stripped):
            has_kvp = True
    if has_section and has_kvp:
        return Format.INI
    if re.search(r"^\w[\w\s]*:", s, re.MULTILINE):
        return Format.YAML
    return None


def _looks_like_toml(content: str) -> bool:
    has_section = has_toml_feature = False
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^\[\[[\w.]+\]\]$", stripped):
            return True
        if re.match(r"^\[[\w.]+\]$", stripped):
            has_section = True
            if "." in stripped[1:-1]:
                has_toml_feature = True
        m = re.match(r'^[\w.-]+\s*=\s*(.+)$', stripped)
        if m:
            val = m.group(1).strip()
            if val.startswith("[") or val.startswith("{") or val in ("true", "false"):
                has_toml_feature = True
            if val.startswith('"""') or val.startswith("'''"):
                has_toml_feature = True
            if re.match(r'\d{4}-\d{2}-\d{2}[T ]', val):
                has_toml_feature = True
    return has_section and has_toml_feature


def format_from_string(name: str) -> Format:
    name = name.lower().strip().lstrip(".")
    aliases = {
        "yaml": Format.YAML, "yml": Format.YAML,
        "toml": Format.TOML, "json": Format.JSON,
        "ini": Format.INI, "cfg": Format.INI, "conf": Format.INI,
        "hcl": Format.HCL, "tf": Format.HCL, "tfvars": Format.HCL,
    }
    if name in aliases:
        return aliases[name]
    raise ValueError(f"Unknown format: {name!r}")


# ═══════════════════════════════════════════════════════════════════
# YAML format
# ═══════════════════════════════════════════════════════════════════

def _parse_yaml(content: str) -> tuple[dict, CommentMap]:
    comments = CommentMap()
    _extract_yaml_comments(content, comments)
    data = yaml.safe_load(content)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        data = {"_value": data}
    return data, comments


def _extract_yaml_comments(content: str, comments: CommentMap) -> None:
    lines = content.split("\n")
    pending: list[str] = []
    indent_stack: list[tuple[int, str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            pending.append(stripped)
            continue
        if stripped in ("---", "..."):
            pending.clear()
            continue
        indent = len(line) - len(line.lstrip())
        key_match = re.match(r'^(\s*)([\w][\w\s.-]*?):\s*(.*)?$', line)
        if not key_match:
            pending.clear()
            continue
        key = key_match.group(2).strip()
        while indent_stack and indent_stack[-1][0] >= indent:
            indent_stack.pop()
        indent_stack.append((indent, key))
        path = ".".join(k for _, k in indent_stack)
        if pending:
            while pending and pending[-1] == "":
                pending.pop()
            for c in pending:
                if c:
                    comments.add(path, c)
            pending.clear()


def _serialize_yaml(data: dict, comments: CommentMap) -> str:
    lines: list[str] = []
    for c in comments.get_file_comments():
        lines.append(c)
    _yaml_dict(data, comments, lines, 0, "")
    result = "\n".join(lines)
    if result and not result.endswith("\n"):
        result += "\n"
    return result


def _yaml_dict(data: dict, comments: CommentMap, lines: list[str], indent: int, prefix: str) -> None:
    pfx = "  " * indent
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        for c in comments.get(path):
            if c:
                lines.append(f"{pfx}{c}")
        if isinstance(value, dict):
            lines.append(f"{pfx}{key}:")
            _yaml_dict(value, comments, lines, indent + 1, path)
        elif isinstance(value, list):
            lines.append(f"{pfx}{key}:")
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for k, v in item.items():
                        if first:
                            lines.append(f"{pfx}  - {k}: {_yaml_scalar(v)}")
                            first = False
                        else:
                            lines.append(f"{pfx}    {k}: {_yaml_scalar(v)}")
                else:
                    lines.append(f"{pfx}  - {_yaml_scalar(item)}")
        elif isinstance(value, bool):
            lines.append(f"{pfx}{key}: {str(value).lower()}")
        elif isinstance(value, (int, float)):
            lines.append(f"{pfx}{key}: {value}")
        elif value is None:
            lines.append(f"{pfx}{key}: null")
        elif isinstance(value, str):
            if "\n" in value:
                lines.append(f"{pfx}{key}: |")
                for vline in value.split("\n"):
                    lines.append(f"{pfx}  {vline}")
            elif _needs_yaml_quoting(value):
                lines.append(f'{pfx}{key}: "{value}"')
            else:
                lines.append(f"{pfx}{key}: {value}")
        else:
            lines.append(f"{pfx}{key}: {value}")


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if _needs_yaml_quoting(value):
            return f'"{value}"'
        return value
    return str(value)


def _needs_yaml_quoting(s: str) -> bool:
    if not s:
        return True
    if s.lower() in ("true", "false", "yes", "no", "on", "off", "null", "~"):
        return True
    if s[0] in ("@", "`", "&", "*", "!", "%", "{", "[", "|", ">", "'", '"', ",", "#"):
        return True
    if ": " in s or s.endswith(":"):
        return True
    try:
        float(s)
        return True
    except ValueError:
        pass
    return False


# ═══════════════════════════════════════════════════════════════════
# TOML format
# ═══════════════════════════════════════════════════════════════════

def _parse_toml(content: str) -> tuple[dict, CommentMap]:
    comments = CommentMap()
    _extract_toml_comments(content, comments)
    data = tomllib.loads(content)
    return data, comments


def _extract_toml_comments(content: str, comments: CommentMap) -> None:
    pending: list[str] = []
    current_section = ""
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            pending.append(stripped)
            continue
        section_match = re.match(r'^\[{1,2}([^\]]+)\]{1,2}$', stripped)
        if section_match:
            current_section = section_match.group(1).strip()
            if pending:
                for c in pending:
                    if c:
                        comments.add(current_section, c)
                pending.clear()
            continue
        key_match = re.match(r'^([\w".-]+)\s*=', stripped)
        if key_match:
            key = key_match.group(1).strip().strip('"')
            path = f"{current_section}.{key}" if current_section else key
            if pending:
                for c in pending:
                    if c:
                        comments.add(path, c)
                pending.clear()
            continue
        pending.clear()


def _serialize_toml(data: dict, comments: CommentMap) -> str:
    lines: list[str] = []
    for c in comments.get_file_comments():
        lines.append(c)
    simple, tables = {}, {}
    for key, value in data.items():
        if isinstance(value, dict):
            tables[key] = value
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            tables[key] = value
        else:
            simple[key] = value
    for key, value in simple.items():
        for c in comments.get(key):
            if c:
                lines.append(c)
        lines.append(f"{key} = {_toml_value(value)}")
    for key, value in tables.items():
        if lines and lines[-1] != "":
            lines.append("")
        if isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                for c in comments.get(key):
                    if c:
                        lines.append(c)
                lines.append(f"[[{key}]]")
                _toml_table(item, comments, lines, key)
        else:
            _toml_section(key, value, comments, lines, key)
    result = "\n".join(lines)
    if result and not result.endswith("\n"):
        result += "\n"
    return result


def _toml_section(name: str, data: dict, comments: CommentMap, lines: list[str], prefix: str) -> None:
    for c in comments.get(prefix):
        if c:
            lines.append(c)
    lines.append(f"[{name}]")
    _toml_table(data, comments, lines, prefix)


def _toml_table(data: dict, comments: CommentMap, lines: list[str], prefix: str) -> None:
    simple, sub = {}, {}
    for key, value in data.items():
        if isinstance(value, dict):
            sub[key] = value
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            sub[key] = value
        else:
            simple[key] = value
    for key, value in simple.items():
        path = f"{prefix}.{key}"
        for c in comments.get(path):
            if c:
                lines.append(c)
        lines.append(f"{key} = {_toml_value(value)}")
    for key, value in sub.items():
        full = f"{prefix}.{key}"
        if lines and lines[-1] != "":
            lines.append("")
        if isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                lines.append(f"[[{full}]]")
                _toml_table(item, comments, lines, full)
        else:
            _toml_section(full, value, comments, lines, full)


def _toml_value(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, str):
        if "\n" in value:
            return f'"""\n{value}"""'
        return f'"{value}"'
    if isinstance(value, list):
        items = [_toml_value(v) for v in value]
        return f"[{', '.join(items)}]"
    if isinstance(value, dict):
        items = [f"{k} = {_toml_value(v)}" for k, v in value.items()]
        return "{" + ", ".join(items) + "}"
    return str(value)


# ═══════════════════════════════════════════════════════════════════
# JSON format
# ═══════════════════════════════════════════════════════════════════

class _ConfigEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        return super().default(obj)


def _parse_json(content: str) -> tuple[dict, CommentMap]:
    cleaned = _strip_jsonc_comments(content)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        data = {"_value": data}
    return data, CommentMap()


def _strip_jsonc_comments(content: str) -> str:
    result: list[str] = []
    i = 0
    in_string = False
    while i < len(content):
        ch = content[i]
        if in_string:
            result.append(ch)
            if ch == "\\" and i + 1 < len(content):
                result.append(content[i + 1])
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            result.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < len(content) and content[i + 1] == "/":
            while i < len(content) and content[i] != "\n":
                i += 1
            continue
        if ch == "/" and i + 1 < len(content) and content[i + 1] == "*":
            i += 2
            while i < len(content):
                if content[i] == "*" and i + 1 < len(content) and content[i + 1] == "/":
                    i += 2
                    break
                i += 1
            continue
        result.append(ch)
        i += 1
    return "".join(result)


def _serialize_json(data: dict, comments: CommentMap) -> str:
    result = json.dumps(data, indent=2, cls=_ConfigEncoder, ensure_ascii=False)
    if not result.endswith("\n"):
        result += "\n"
    return result


# ═══════════════════════════════════════════════════════════════════
# INI format
# ═══════════════════════════════════════════════════════════════════

def _parse_ini(content: str) -> tuple[dict, CommentMap]:
    comments = CommentMap()
    _extract_ini_comments(content, comments)
    parser = configparser.ConfigParser(
        interpolation=None,
        comment_prefixes=("#", ";"),
        inline_comment_prefixes=("#", ";"),
        allow_no_value=True,
    )
    parser.read_string(content)
    data: dict[str, Any] = {}
    for section in parser.sections():
        section_data: dict[str, Any] = {}
        for key, raw in parser.items(section):
            val = _parse_ini_value(raw) if raw is not None else None
            _set_nested(section_data, key.split("."), val)
        data[section] = section_data
    return data, comments


def _parse_ini_value(raw: str) -> Any:
    s = raw.strip()
    if s.lower() in ("true", "yes", "on"):
        return True
    if s.lower() in ("false", "no", "off"):
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    if "," in s and not s.startswith('"'):
        parts = [p.strip() for p in s.split(",")]
        if all(parts):
            return [_parse_ini_value(p) for p in parts]
    if s.lower() in ("none", "null", ""):
        return None
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _set_nested(data: dict, keys: list[str], value: Any) -> None:
    for key in keys[:-1]:
        if key not in data or not isinstance(data[key], dict):
            data[key] = {}
        data = data[key]
    data[keys[-1]] = value


def _extract_ini_comments(content: str, comments: CommentMap) -> None:
    pending: list[str] = []
    current_section = ""
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith(";"):
            pending.append(stripped)
            continue
        section_match = re.match(r'^\[([^\]]+)\]$', stripped)
        if section_match:
            current_section = section_match.group(1).strip()
            if pending:
                for c in pending:
                    comments.add(current_section, c)
                pending.clear()
            continue
        key_match = re.match(r'^([\w.-]+)\s*[=:]', stripped)
        if key_match:
            key = key_match.group(1).strip()
            path = f"{current_section}.{key}" if current_section else key
            if pending:
                for c in pending:
                    comments.add(path, c)
                pending.clear()
            continue
        pending.clear()


def _serialize_ini(data: dict, comments: CommentMap) -> str:
    lines: list[str] = []
    for c in comments.get_file_comments():
        lines.append(c)
    top_scalars, sections = {}, {}
    for key, value in data.items():
        if isinstance(value, dict):
            sections[key] = value
        else:
            top_scalars[key] = value
    if top_scalars:
        lines.append("[DEFAULT]")
        for key, value in top_scalars.items():
            lines.append(f"{key} = {_ini_value(value)}")
    for section_name, section_data in sections.items():
        if lines and lines[-1] != "":
            lines.append("")
        for c in comments.get(section_name):
            if c:
                lines.append(c)
        lines.append(f"[{section_name}]")
        flat: dict[str, Any] = {}
        _flatten_dict(section_data, flat, "")
        for key, value in flat.items():
            path = f"{section_name}.{key}"
            for c in comments.get(path):
                if c:
                    lines.append(c)
            lines.append(f"{key} = {_ini_value(value)}")
    result = "\n".join(lines)
    if result and not result.endswith("\n"):
        result += "\n"
    return result


def _flatten_dict(data: dict, result: dict, prefix: str) -> None:
    for key, value in data.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            _flatten_dict(value, result, full)
        else:
            result[full] = value


def _ini_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ", ".join(_ini_value(v) for v in value)
    return str(value)


# ═══════════════════════════════════════════════════════════════════
# HCL format
# ═══════════════════════════════════════════════════════════════════

class _Token:
    __slots__ = ("kind", "value", "line")
    def __init__(self, kind: str, value: str, line: int = 0):
        self.kind = kind
        self.value = value
        self.line = line


def _tokenize_hcl(content: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    line_num = 1
    length = len(content)
    while i < length:
        ch = content[i]
        if ch in (" ", "\t", "\r"):
            i += 1
            continue
        if ch == "\n":
            tokens.append(_Token("NEWLINE", "\n", line_num))
            line_num += 1
            i += 1
            continue
        if ch == "#" or (ch == "/" and i + 1 < length and content[i + 1] == "/"):
            start = i
            while i < length and content[i] != "\n":
                i += 1
            tokens.append(_Token("COMMENT", content[start:i].strip(), line_num))
            continue
        if ch == "/" and i + 1 < length and content[i + 1] == "*":
            start = i
            i += 2
            while i < length:
                if content[i] == "*" and i + 1 < length and content[i + 1] == "/":
                    i += 2
                    break
                if content[i] == "\n":
                    line_num += 1
                i += 1
            tokens.append(_Token("COMMENT", content[start:i].strip(), line_num))
            continue
        if ch == "<" and i + 1 < length and content[i + 1] == "<":
            i += 2
            strip_indent = False
            if i < length and content[i] == "-":
                strip_indent = True
                i += 1
            delim_start = i
            while i < length and content[i] not in ("\n", "\r"):
                i += 1
            delimiter = content[delim_start:i].strip().strip('"')
            if i < length and content[i] == "\n":
                i += 1
                line_num += 1
            heredoc_lines: list[str] = []
            while i < length:
                line_start = i
                while i < length and content[i] != "\n":
                    i += 1
                cur = content[line_start:i]
                if cur.strip() == delimiter:
                    if i < length:
                        i += 1
                        line_num += 1
                    break
                heredoc_lines.append(cur)
                if i < length:
                    i += 1
                    line_num += 1
            text = "\n".join(heredoc_lines)
            if strip_indent and heredoc_lines:
                mi = min((len(l) - len(l.lstrip()) for l in heredoc_lines if l.strip()), default=0)
                text = "\n".join(l[mi:] for l in heredoc_lines)
            tokens.append(_Token("STRING", text, line_num))
            continue
        if ch == '"':
            i += 1
            chars: list[str] = []
            while i < length and content[i] != '"':
                if content[i] == "\\" and i + 1 < length:
                    nc = content[i + 1]
                    chars.append({"n": "\n", "t": "\t", "\\": "\\", '"': '"'}.get(nc, nc))
                    i += 2
                    continue
                chars.append(content[i])
                i += 1
            if i < length:
                i += 1
            tokens.append(_Token("STRING", "".join(chars), line_num))
            continue
        if ch == "{":
            tokens.append(_Token("LBRACE", ch, line_num)); i += 1; continue
        if ch == "}":
            tokens.append(_Token("RBRACE", ch, line_num)); i += 1; continue
        if ch == "[":
            tokens.append(_Token("LBRACKET", ch, line_num)); i += 1; continue
        if ch == "]":
            tokens.append(_Token("RBRACKET", ch, line_num)); i += 1; continue
        if ch == "=":
            tokens.append(_Token("EQUALS", ch, line_num)); i += 1; continue
        if ch == ",":
            tokens.append(_Token("COMMA", ch, line_num)); i += 1; continue
        if ch == ":":
            tokens.append(_Token("COLON", ch, line_num)); i += 1; continue
        if ch.isdigit() or (ch == "-" and i + 1 < length and content[i + 1].isdigit()):
            start = i
            if ch == "-":
                i += 1
            while i < length and (content[i].isdigit() or content[i] in ".eE+-"):
                i += 1
            tokens.append(_Token("NUMBER", content[start:i], line_num))
            continue
        if ch.isalpha() or ch == "_":
            start = i
            while i < length and (content[i].isalnum() or content[i] in "_-"):
                i += 1
            word = content[start:i]
            if word in ("true", "false"):
                tokens.append(_Token("BOOL", word, line_num))
            elif word == "null":
                tokens.append(_Token("NULL", word, line_num))
            else:
                tokens.append(_Token("IDENT", word, line_num))
            continue
        i += 1
    return tokens


class _HclParser:
    def __init__(self, tokens: list[_Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> _Token | None:
        self._skip()
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self) -> _Token | None:
        self._skip()
        if self.pos < len(self.tokens):
            t = self.tokens[self.pos]
            self.pos += 1
            return t
        return None

    def expect(self, kind: str) -> _Token:
        t = self.next()
        if t is None or t.kind != kind:
            raise ValueError(f"Expected {kind}")
        return t

    def _skip(self) -> None:
        while self.pos < len(self.tokens) and self.tokens[self.pos].kind == "NEWLINE":
            self.pos += 1

    def collect_comments(self) -> list[str]:
        comments: list[str] = []
        while self.pos < len(self.tokens):
            t = self.tokens[self.pos]
            if t.kind == "COMMENT":
                comments.append(t.value)
                self.pos += 1
            elif t.kind == "NEWLINE":
                self.pos += 1
            else:
                break
        return comments


def _parse_hcl(content: str) -> tuple[dict, CommentMap]:
    comments = CommentMap()
    tokens = _tokenize_hcl(content)
    p = _HclParser(tokens)
    data = _hcl_body(p, comments, "", True)
    return data, comments


def _hcl_body(p: _HclParser, comments: CommentMap, prefix: str, top: bool) -> dict:
    data: dict[str, Any] = {}
    while True:
        preceding = p.collect_comments()
        tok = p.peek()
        if tok is None:
            break
        if tok.kind == "RBRACE" and not top:
            break
        if tok.kind != "IDENT":
            p.next()
            continue
        ident = p.next()
        assert ident is not None
        name = ident.value
        nxt = p.peek()
        if nxt is None:
            break
        path = f"{prefix}.{name}" if prefix else name
        for c in preceding:
            comments.add(path, c)
        if nxt.kind == "EQUALS":
            p.next()
            data[name] = _hcl_value(p)
        elif nxt.kind == "LBRACE":
            p.next()
            body = _hcl_body(p, comments, path, False)
            p.expect("RBRACE")
            if name in data:
                if isinstance(data[name], list):
                    data[name].append(body)
                else:
                    data[name] = [data[name], body]
            else:
                data[name] = body
        elif nxt.kind in ("STRING", "IDENT"):
            labels: list[str] = []
            while True:
                lt = p.peek()
                if lt is None or lt.kind == "LBRACE":
                    break
                if lt.kind in ("STRING", "IDENT"):
                    labels.append(p.next().value)  # type: ignore
                else:
                    break
            p.expect("LBRACE")
            body = _hcl_body(p, comments, path, False)
            p.expect("RBRACE")
            if labels:
                bd = body
                for lb in reversed(labels):
                    bd = {lb: bd}
                if name in data and isinstance(data[name], dict):
                    _deep_merge(data[name], bd)
                else:
                    data[name] = bd
            else:
                data[name] = body
        else:
            p.next()
    return data


def _hcl_value(p: _HclParser) -> Any:
    tok = p.peek()
    if tok is None:
        return None
    if tok.kind == "STRING":
        p.next(); return tok.value
    if tok.kind == "NUMBER":
        p.next()
        return float(tok.value) if ("." in tok.value or "e" in tok.value.lower()) else int(tok.value)
    if tok.kind == "BOOL":
        p.next(); return tok.value == "true"
    if tok.kind == "NULL":
        p.next(); return None
    if tok.kind == "LBRACKET":
        p.expect("LBRACKET")
        items: list[Any] = []
        while True:
            t = p.peek()
            if t is None or t.kind == "RBRACKET":
                p.next(); break
            if t.kind == "COMMA":
                p.next(); continue
            items.append(_hcl_value(p))
        return items
    if tok.kind == "LBRACE":
        p.expect("LBRACE")
        data: dict[str, Any] = {}
        while True:
            p.collect_comments()
            t = p.peek()
            if t is None or t.kind == "RBRACE":
                p.next(); break
            if t.kind == "COMMA":
                p.next(); continue
            if t.kind in ("IDENT", "STRING"):
                key = p.next().value  # type: ignore
                sep = p.peek()
                if sep and sep.kind in ("EQUALS", "COLON"):
                    p.next()
                data[key] = _hcl_value(p)
            else:
                p.next()
        return data
    if tok.kind == "IDENT":
        p.next(); return tok.value
    p.next(); return tok.value


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _serialize_hcl(data: dict, comments: CommentMap) -> str:
    lines: list[str] = []
    for c in comments.get_file_comments():
        lines.append(c)
    _hcl_body_out(data, comments, lines, 0, "")
    result = "\n".join(lines)
    if result and not result.endswith("\n"):
        result += "\n"
    return result


def _hcl_body_out(data: dict, comments: CommentMap, lines: list[str], indent: int, prefix: str) -> None:
    pfx = "  " * indent
    first = True
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if not first and indent == 0:
            lines.append("")
        first = False
        for c in comments.get(path):
            if c:
                lines.append(f"{pfx}{c}")
        if isinstance(value, dict):
            if all(isinstance(v, dict) for v in value.values()):
                # Labeled block
                for label, inner in value.items():
                    if isinstance(inner, dict) and all(isinstance(v, dict) for v in inner.values()):
                        for label2, body in inner.items():
                            if isinstance(body, dict):
                                lines.append(f'{pfx}{key} "{label}" "{label2}" {{')
                                _hcl_body_out(body, comments, lines, indent + 1, path)
                                lines.append(f"{pfx}}}")
                            else:
                                lines.append(f'{pfx}{key} "{label}" {{')
                                lines.append(f"{pfx}  {label2} = {_hcl_scalar(body)}")
                                lines.append(f"{pfx}}}")
                    elif isinstance(inner, dict):
                        lines.append(f'{pfx}{key} "{label}" {{')
                        _hcl_body_out(inner, comments, lines, indent + 1, path)
                        lines.append(f"{pfx}}}")
            else:
                lines.append(f"{pfx}{key} {{")
                _hcl_body_out(value, comments, lines, indent + 1, path)
                lines.append(f"{pfx}}}")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                lines.append(f"{pfx}{key} {{")
                _hcl_body_out(item, comments, lines, indent + 1, path)
                lines.append(f"{pfx}}}")
        else:
            lines.append(f"{pfx}{key} = {_hcl_scalar(value)}")


def _hcl_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        if "\n" in value:
            return f"<<-EOF\n{value}\nEOF"
        return f'"{value}"'
    if isinstance(value, list):
        return f"[{', '.join(_hcl_scalar(v) for v in value)}]"
    return str(value)


# ═══════════════════════════════════════════════════════════════════
# Central converter
# ═══════════════════════════════════════════════════════════════════

_PARSERS = {
    Format.YAML: _parse_yaml,
    Format.TOML: _parse_toml,
    Format.JSON: _parse_json,
    Format.INI: _parse_ini,
    Format.HCL: _parse_hcl,
}

_SERIALIZERS = {
    Format.YAML: _serialize_yaml,
    Format.TOML: _serialize_toml,
    Format.JSON: _serialize_json,
    Format.INI: _serialize_ini,
    Format.HCL: _serialize_hcl,
}


def _transform(data: Any, target: Format) -> Any:
    if isinstance(data, dict):
        return {k: _transform(v, target) for k, v in data.items()}
    if isinstance(data, list):
        return [_transform(v, target) for v in data]
    if isinstance(data, (datetime, date, time)):
        if target != Format.TOML:
            return data.isoformat()
    if data is None and target == Format.INI:
        return ""
    return data


def convert_string(content: str, source: Format | str, target: Format | str) -> str:
    if isinstance(source, str):
        source = format_from_string(source)
    if isinstance(target, str):
        target = format_from_string(target)
    data, comments = _PARSERS[source](content)
    data = _transform(data, target)
    return _SERIALIZERS[target](data, comments)


def convert_file(input_path: str | Path, target: Format | str,
                 output_path: str | Path | None = None,
                 source: Format | str | None = None) -> str:
    input_path = Path(input_path)
    if isinstance(target, str):
        target = format_from_string(target)
    if source is None:
        detected = detect_format(input_path)
        if detected is None:
            raise ValueError(f"Cannot detect format of {input_path}")
        source = detected
    elif isinstance(source, str):
        source = format_from_string(source)
    content = input_path.read_text(encoding="utf-8")
    result = convert_string(content, source, target)
    if output_path is not None:
        Path(output_path).write_text(result, encoding="utf-8")
    return result
