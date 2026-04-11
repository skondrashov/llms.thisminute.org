"""
Tests for Config File Converter.

These tests ARE the spec — format detection, parsing, serialization,
conversion between all 5 formats, comment preservation, edge cases.
"""

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from converter import (
    CommentMap, Format, detect_format, format_from_string,
    convert_string, convert_file,
    _parse_yaml, _parse_toml, _parse_json, _parse_ini, _parse_hcl,
    _serialize_yaml, _serialize_toml, _serialize_json, _serialize_ini, _serialize_hcl,
    _strip_jsonc_comments, _detect_from_content,
)


# ═══════════════════════════════════════════════════════════════════
# 1. CommentMap
# ═══════════════════════════════════════════════════════════════════

class TestCommentMap:
    def test_empty(self):
        cm = CommentMap()
        assert not cm
        assert cm.get("any") == []

    def test_add_and_get(self):
        cm = CommentMap()
        cm.add("key", "# comment")
        assert cm.get("key") == ["# comment"]

    def test_multiple_comments(self):
        cm = CommentMap()
        cm.add("key", "# line 1")
        cm.add("key", "# line 2")
        assert len(cm.get("key")) == 2

    def test_inline(self):
        cm = CommentMap()
        cm.add_inline("key", "# inline")
        assert cm.get_inline("key") == "# inline"
        assert cm.get_inline("missing") is None

    def test_file_comments(self):
        cm = CommentMap()
        cm.set_file_comments(["# File header"])
        assert cm.get_file_comments() == ["# File header"]

    def test_bool(self):
        cm = CommentMap()
        assert not cm
        cm.add("k", "# c")
        assert cm

    def test_repr(self):
        cm = CommentMap()
        cm.add("a", "# 1")
        assert "1 comment lines" in repr(cm)


# ═══════════════════════════════════════════════════════════════════
# 2. Format detection
# ═══════════════════════════════════════════════════════════════════

class TestFormatDetection:
    def test_yaml_ext(self):
        assert detect_format("config.yaml") == Format.YAML

    def test_yml_ext(self):
        assert detect_format("config.yml") == Format.YAML

    def test_toml_ext(self):
        assert detect_format("config.toml") == Format.TOML

    def test_json_ext(self):
        assert detect_format("config.json") == Format.JSON

    def test_ini_ext(self):
        assert detect_format("config.ini") == Format.INI

    def test_hcl_ext(self):
        assert detect_format("main.hcl") == Format.HCL

    def test_tf_ext(self):
        assert detect_format("main.tf") == Format.HCL

    def test_unknown_ext(self):
        assert detect_format("file.xyz") is None

    def test_json_content(self):
        assert _detect_from_content('{"key": "value"}') == Format.JSON

    def test_yaml_content(self):
        assert _detect_from_content("---\nkey: value") == Format.YAML

    def test_yaml_kv_content(self):
        assert _detect_from_content("host: localhost\nport: 8080") == Format.YAML

    def test_toml_content(self):
        assert _detect_from_content("[server]\nenabled = true") == Format.TOML

    def test_toml_array_of_tables(self):
        assert _detect_from_content('[[items]]\nname = "a"') == Format.TOML

    def test_hcl_content(self):
        assert _detect_from_content('provider "aws" {\n  region = "us-east-1"\n}') == Format.HCL

    def test_ini_content(self):
        assert _detect_from_content("[section]\nkey = value\nother = data") == Format.INI

    def test_empty(self):
        assert _detect_from_content("") is None

    def test_format_from_string(self):
        assert format_from_string("yaml") == Format.YAML
        assert format_from_string("TOML") == Format.TOML
        assert format_from_string(".json") == Format.JSON

    def test_format_from_string_error(self):
        with pytest.raises(ValueError):
            format_from_string("xml")


# ═══════════════════════════════════════════════════════════════════
# 3. YAML parser
# ═══════════════════════════════════════════════════════════════════

class TestYamlParse:
    def test_simple(self):
        data, _ = _parse_yaml("key: value")
        assert data == {"key": "value"}

    def test_integer(self):
        data, _ = _parse_yaml("port: 8080")
        assert data["port"] == 8080

    def test_boolean(self):
        data, _ = _parse_yaml("flag: true")
        assert data["flag"] is True

    def test_null(self):
        data, _ = _parse_yaml("val: null")
        assert data["val"] is None

    def test_nested(self):
        data, _ = _parse_yaml("db:\n  host: localhost\n  port: 5432")
        assert data["db"]["host"] == "localhost"

    def test_list(self):
        data, _ = _parse_yaml("items:\n  - a\n  - b")
        assert data["items"] == ["a", "b"]

    def test_empty(self):
        data, _ = _parse_yaml("")
        assert data == {}

    def test_comment_extraction(self):
        _, comments = _parse_yaml("# DB\ndatabase:\n  host: localhost")
        assert "# DB" in comments.get("database")


class TestYamlSerialize:
    def test_simple(self):
        assert "key: value" in _serialize_yaml({"key": "value"}, CommentMap())

    def test_nested(self):
        result = _serialize_yaml({"db": {"host": "localhost"}}, CommentMap())
        assert "db:" in result
        assert "  host: localhost" in result

    def test_with_comments(self):
        cm = CommentMap()
        cm.add("key", "# comment")
        assert "# comment" in _serialize_yaml({"key": "val"}, cm)

    def test_boolean(self):
        assert "flag: true" in _serialize_yaml({"flag": True}, CommentMap())

    def test_null(self):
        assert "null" in _serialize_yaml({"val": None}, CommentMap())


# ═══════════════════════════════════════════════════════════════════
# 4. TOML parser
# ═══════════════════════════════════════════════════════════════════

class TestTomlParse:
    def test_simple(self):
        data, _ = _parse_toml('title = "app"')
        assert data == {"title": "app"}

    def test_section(self):
        data, _ = _parse_toml('[db]\nhost = "localhost"')
        assert data["db"]["host"] == "localhost"

    def test_integer(self):
        data, _ = _parse_toml("port = 8080")
        assert data["port"] == 8080

    def test_boolean(self):
        data, _ = _parse_toml("flag = true")
        assert data["flag"] is True

    def test_array(self):
        data, _ = _parse_toml("ports = [80, 443]")
        assert data["ports"] == [80, 443]

    def test_array_of_tables(self):
        data, _ = _parse_toml('[[items]]\nname = "a"\n\n[[items]]\nname = "b"')
        assert len(data["items"]) == 2

    def test_comment_extraction(self):
        _, comments = _parse_toml('# Title\ntitle = "app"')
        assert "# Title" in comments.get("title")


class TestTomlSerialize:
    def test_simple(self):
        assert 'title = "app"' in _serialize_toml({"title": "app"}, CommentMap())

    def test_section(self):
        result = _serialize_toml({"db": {"host": "localhost"}}, CommentMap())
        assert "[db]" in result

    def test_boolean(self):
        assert "flag = true" in _serialize_toml({"flag": True}, CommentMap())

    def test_array(self):
        assert "[80, 443]" in _serialize_toml({"ports": [80, 443]}, CommentMap())


# ═══════════════════════════════════════════════════════════════════
# 5. JSON parser
# ═══════════════════════════════════════════════════════════════════

class TestJsonParse:
    def test_simple(self):
        data, _ = _parse_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_nested(self):
        data, _ = _parse_json('{"a": {"b": 1}}')
        assert data["a"]["b"] == 1

    def test_array(self):
        data, _ = _parse_json('{"items": [1, 2]}')
        assert data["items"] == [1, 2]

    def test_null(self):
        data, _ = _parse_json('{"val": null}')
        assert data["val"] is None

    def test_no_comments(self):
        _, comments = _parse_json('{"key": "value"}')
        assert not comments

    def test_jsonc_line_comment(self):
        data, _ = _parse_json('{"key": "value"} // comment')
        assert data["key"] == "value"

    def test_jsonc_block_comment(self):
        data, _ = _parse_json('{"key": /* c */ "value"}')
        assert data["key"] == "value"


class TestJsonSerialize:
    def test_simple(self):
        assert '"key": "value"' in _serialize_json({"key": "value"}, CommentMap())

    def test_comments_ignored(self):
        cm = CommentMap()
        cm.add("key", "# comment")
        result = _serialize_json({"key": "val"}, cm)
        assert "#" not in result


# ═══════════════════════════════════════════════════════════════════
# 6. INI parser
# ═══════════════════════════════════════════════════════════════════

class TestIniParse:
    def test_section(self):
        data, _ = _parse_ini("[server]\nhost = localhost\nport = 8080")
        assert data["server"]["host"] == "localhost"
        assert data["server"]["port"] == 8080

    def test_boolean(self):
        data, _ = _parse_ini("[s]\nflag = true")
        assert data["s"]["flag"] is True

    def test_csv_list(self):
        data, _ = _parse_ini("[s]\nhosts = a, b, c")
        assert data["s"]["hosts"] == ["a", "b", "c"]

    def test_dotted_unflatten(self):
        data, _ = _parse_ini("[db]\npool.size = 10")
        assert data["db"]["pool"]["size"] == 10

    def test_comment_extraction(self):
        _, comments = _parse_ini("# Server\n[server]\nhost = localhost")
        assert "# Server" in comments.get("server")


class TestIniSerialize:
    def test_section(self):
        result = _serialize_ini({"server": {"host": "localhost"}}, CommentMap())
        assert "[server]" in result
        assert "host = localhost" in result

    def test_nested_flattened(self):
        result = _serialize_ini({"db": {"pool": {"size": 10}}}, CommentMap())
        assert "pool.size = 10" in result

    def test_with_comments(self):
        cm = CommentMap()
        cm.add("server", "# Server")
        result = _serialize_ini({"server": {"host": "localhost"}}, cm)
        assert "# Server" in result


# ═══════════════════════════════════════════════════════════════════
# 7. HCL parser
# ═══════════════════════════════════════════════════════════════════

class TestHclParse:
    def test_attribute(self):
        data, _ = _parse_hcl('region = "us-east-1"')
        assert data["region"] == "us-east-1"

    def test_integer(self):
        data, _ = _parse_hcl("count = 3")
        assert data["count"] == 3

    def test_boolean(self):
        data, _ = _parse_hcl("enabled = true")
        assert data["enabled"] is True

    def test_block(self):
        data, _ = _parse_hcl('server {\n  port = 8080\n}')
        assert data["server"]["port"] == 8080

    def test_labeled_block(self):
        data, _ = _parse_hcl('provider "aws" {\n  region = "us-east-1"\n}')
        assert data["provider"]["aws"]["region"] == "us-east-1"

    def test_double_label(self):
        data, _ = _parse_hcl('resource "aws_instance" "web" {\n  ami = "ami-123"\n}')
        assert data["resource"]["aws_instance"]["web"]["ami"] == "ami-123"

    def test_list(self):
        data, _ = _parse_hcl("ports = [80, 443]")
        assert data["ports"] == [80, 443]

    def test_map(self):
        data, _ = _parse_hcl('tags = {\n  Name = "web"\n}')
        assert data["tags"]["Name"] == "web"

    def test_heredoc(self):
        data, _ = _parse_hcl("policy = <<EOF\nallow all\nEOF")
        assert "allow all" in data["policy"]

    def test_comment(self):
        _, comments = _parse_hcl('# Region\nregion = "us-east-1"')
        assert "# Region" in comments.get("region")


class TestHclSerialize:
    def test_attribute(self):
        assert 'region = "us-east-1"' in _serialize_hcl({"region": "us-east-1"}, CommentMap())

    def test_block(self):
        result = _serialize_hcl({"server": {"port": 8080}}, CommentMap())
        assert "server" in result
        assert "port = 8080" in result

    def test_boolean(self):
        assert "enabled = true" in _serialize_hcl({"enabled": True}, CommentMap())


# ═══════════════════════════════════════════════════════════════════
# 8. Cross-format conversions
# ═══════════════════════════════════════════════════════════════════

class TestYamlConversions:
    def test_yaml_to_json(self):
        result = convert_string("name: myapp\nport: 8080", "yaml", "json")
        assert '"name": "myapp"' in result
        assert '"port": 8080' in result

    def test_yaml_to_toml(self):
        result = convert_string("name: myapp\nport: 8080", "yaml", "toml")
        assert 'name = "myapp"' in result
        assert "port = 8080" in result

    def test_yaml_to_ini(self):
        result = convert_string("server:\n  host: localhost", "yaml", "ini")
        assert "[server]" in result
        assert "host = localhost" in result

    def test_yaml_to_hcl(self):
        result = convert_string("name: myapp", "yaml", "hcl")
        assert '"myapp"' in result


class TestTomlConversions:
    def test_toml_to_yaml(self):
        result = convert_string('name = "myapp"', "toml", "yaml")
        assert "name: myapp" in result

    def test_toml_to_json(self):
        result = convert_string('name = "myapp"', "toml", "json")
        assert '"name": "myapp"' in result

    def test_toml_to_ini(self):
        result = convert_string('[db]\nhost = "localhost"', "toml", "ini")
        assert "[db]" in result

    def test_toml_to_hcl(self):
        result = convert_string('name = "myapp"', "toml", "hcl")
        assert "myapp" in result


class TestJsonConversions:
    def test_json_to_yaml(self):
        result = convert_string('{"name": "myapp"}', "json", "yaml")
        assert "name: myapp" in result

    def test_json_to_toml(self):
        result = convert_string('{"name": "myapp"}', "json", "toml")
        assert 'name = "myapp"' in result

    def test_json_to_ini(self):
        result = convert_string('{"server": {"host": "localhost"}}', "json", "ini")
        assert "[server]" in result

    def test_json_to_hcl(self):
        result = convert_string('{"name": "myapp"}', "json", "hcl")
        assert "myapp" in result


class TestIniConversions:
    def test_ini_to_yaml(self):
        result = convert_string("[s]\nhost = localhost", "ini", "yaml")
        assert "host: localhost" in result

    def test_ini_to_json(self):
        result = convert_string("[s]\nhost = localhost", "ini", "json")
        assert '"host": "localhost"' in result

    def test_ini_to_toml(self):
        result = convert_string("[s]\nhost = localhost", "ini", "toml")
        assert 'host = "localhost"' in result

    def test_ini_to_hcl(self):
        result = convert_string("[s]\nhost = localhost", "ini", "hcl")
        assert "localhost" in result


class TestHclConversions:
    def test_hcl_to_yaml(self):
        result = convert_string('name = "myapp"', "hcl", "yaml")
        assert "name: myapp" in result

    def test_hcl_to_json(self):
        result = convert_string('name = "myapp"', "hcl", "json")
        assert '"name": "myapp"' in result

    def test_hcl_to_toml(self):
        result = convert_string('name = "myapp"', "hcl", "toml")
        assert 'name = "myapp"' in result

    def test_hcl_to_ini(self):
        result = convert_string('server {\n  host = "localhost"\n}', "hcl", "ini")
        assert "[server]" in result


# ═══════════════════════════════════════════════════════════════════
# 9. Round-trips
# ═══════════════════════════════════════════════════════════════════

class TestRoundTrips:
    def test_yaml_json_yaml(self):
        original = "name: myapp\nversion: 1"
        mid = convert_string(original, "yaml", "json")
        result = convert_string(mid, "json", "yaml")
        assert "name: myapp" in result

    def test_toml_json_toml(self):
        original = 'name = "myapp"\nversion = 1'
        mid = convert_string(original, "toml", "json")
        result = convert_string(mid, "json", "toml")
        assert 'name = "myapp"' in result

    def test_yaml_toml_yaml(self):
        original = "name: myapp\nversion: 1"
        mid = convert_string(original, "yaml", "toml")
        result = convert_string(mid, "toml", "yaml")
        assert "name: myapp" in result

    def test_json_ini_json(self):
        original = '{"server": {"host": "localhost", "port": 8080}}'
        mid = convert_string(original, "json", "ini")
        result = convert_string(mid, "ini", "json")
        assert '"host": "localhost"' in result


# ═══════════════════════════════════════════════════════════════════
# 10. Comment preservation across formats
# ═══════════════════════════════════════════════════════════════════

class TestCommentPreservation:
    def test_yaml_to_toml(self):
        result = convert_string("# Config\nname: myapp", "yaml", "toml")
        assert "# Config" in result

    def test_yaml_to_hcl(self):
        result = convert_string("# Setting\nname: myapp", "yaml", "hcl")
        assert "# Setting" in result

    def test_toml_to_yaml(self):
        result = convert_string('# Title\ntitle = "app"', "toml", "yaml")
        assert "# Title" in result

    def test_hcl_to_yaml(self):
        result = convert_string('# Region\nregion = "us-east-1"', "hcl", "yaml")
        assert "# Region" in result

    def test_yaml_to_json_drops(self):
        result = convert_string("# Lost\nkey: val", "yaml", "json")
        assert "#" not in result

    def test_comment_roundtrip(self):
        yaml_in = "# Important\nname: myapp"
        toml = convert_string(yaml_in, "yaml", "toml")
        assert "# Important" in toml
        yaml_out = convert_string(toml, "toml", "yaml")
        assert "# Important" in yaml_out


# ═══════════════════════════════════════════════════════════════════
# 11. Edge cases
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_yaml(self):
        result = convert_string("", "yaml", "json")
        assert "{}" in result

    def test_deeply_nested(self):
        result = convert_string("a:\n  b:\n    c:\n      d: deep", "yaml", "json")
        assert '"d": "deep"' in result

    def test_special_chars(self):
        result = convert_string('{"url": "https://example.com:8080"}', "json", "yaml")
        assert "example.com" in result

    def test_unicode(self):
        result = convert_string('name: caf\u00e9', "yaml", "json")
        assert "caf" in result

    def test_large_array(self):
        import json as j
        items = list(range(50))
        result = convert_string(j.dumps({"items": items}), "json", "yaml")
        assert "- 0" in result and "- 49" in result

    def test_null_to_toml(self):
        result = convert_string('{"val": null}', "json", "toml")
        assert 'val = ""' in result

    def test_multiline_yaml_to_toml(self):
        result = convert_string('desc: "line1\\nline2"', "yaml", "toml")
        assert "desc" in result

    def test_hcl_heredoc_to_json(self):
        result = convert_string("policy = <<EOF\nallow\nEOF", "hcl", "json")
        assert "allow" in result

    def test_ini_boolean_variants(self):
        for val in ["true", "yes", "on"]:
            data, _ = _parse_ini(f"[s]\nflag = {val}")
            assert data["s"]["flag"] is True
        for val in ["false", "no", "off"]:
            data, _ = _parse_ini(f"[s]\nflag = {val}")
            assert data["s"]["flag"] is False

    def test_format_enum_accepted(self):
        result = convert_string('{"k": "v"}', Format.JSON, Format.YAML)
        assert "k:" in result

    def test_convert_file(self, tmp_path):
        f = tmp_path / "input.yaml"
        f.write_text("key: value\n")
        result = convert_file(str(f), "json")
        assert '"key": "value"' in result

    def test_convert_file_output(self, tmp_path):
        f = tmp_path / "in.yaml"
        o = tmp_path / "out.json"
        f.write_text("key: value\n")
        convert_file(str(f), "json", output_path=str(o))
        assert o.exists()


# ═══════════════════════════════════════════════════════════════════
# 12. JSONC stripping
# ═══════════════════════════════════════════════════════════════════

class TestJsoncStripping:
    def test_line_comment(self):
        result = _strip_jsonc_comments('{"key": "value"} // comment')
        assert "comment" not in result

    def test_block_comment(self):
        result = _strip_jsonc_comments('{"key": /* c */ "value"}')
        assert "/* c */" not in result

    def test_url_in_string(self):
        result = _strip_jsonc_comments('{"url": "http://example.com"}')
        assert "http://example.com" in result

    def test_no_comments(self):
        original = '{"key": "value"}'
        assert _strip_jsonc_comments(original) == original
