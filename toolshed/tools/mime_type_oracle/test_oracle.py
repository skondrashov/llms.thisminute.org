"""
Tests for MIME Type Oracle.

These tests ARE the spec — extension lookup, reverse lookup, ambiguous
extension handling, alias resolution, metadata accuracy, search, and
formatting.
"""

import json
import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from oracle import (
    MimeEntry, MIME_DATABASE,
    LookupResult, lookup_extension, lookup_mime_type, reverse_lookup,
    search_mime_types, is_ambiguous, get_ambiguous_extensions,
    get_all_extensions, get_all_mime_types,
    _normalize_ext, _normalize_mime,
    format_lookup_result, format_info, format_search_results,
    _entry_to_dict,
)


# ═══════════════════════════════════════════════════════════════════
# 1. Database Integrity
# ═══════════════════════════════════════════════════════════════════

class TestDatabaseIntegrity:
    def test_database_has_100_plus_entries(self):
        assert len(MIME_DATABASE) > 100

    def test_all_entries_are_mime_entries(self):
        for entry in MIME_DATABASE:
            assert isinstance(entry, MimeEntry)

    def test_all_mime_types_have_slash(self):
        for entry in MIME_DATABASE:
            assert "/" in entry.mime_type

    def test_all_extensions_start_with_dot(self):
        for entry in MIME_DATABASE:
            for ext in entry.extensions:
                assert ext.startswith(".")

    def test_kind_is_text_or_binary(self):
        for entry in MIME_DATABASE:
            assert entry.kind in ("text", "binary")

    def test_compressible_is_bool(self):
        for entry in MIME_DATABASE:
            assert isinstance(entry.compressible, bool)

    def test_all_have_descriptions(self):
        for entry in MIME_DATABASE:
            assert entry.description

    def test_no_duplicate_canonical_mime_types(self):
        seen = set()
        for entry in MIME_DATABASE:
            mt = entry.mime_type.lower()
            assert mt not in seen, f"Duplicate: {entry.mime_type}"
            seen.add(mt)

    def test_tuples_not_lists(self):
        for entry in MIME_DATABASE:
            assert isinstance(entry.extensions, tuple)
            assert isinstance(entry.aliases, tuple)
            assert isinstance(entry.rfcs, tuple)
            assert isinstance(entry.programs, tuple)

    def test_entries_are_frozen(self):
        entry = MIME_DATABASE[0]
        with pytest.raises(AttributeError):
            entry.mime_type = "changed"


# ═══════════════════════════════════════════════════════════════════
# 2. Normalization
# ═══════════════════════════════════════════════════════════════════

class TestNormalization:
    def test_normalize_ext_adds_dot(self):
        assert _normalize_ext("pdf") == ".pdf"

    def test_normalize_ext_keeps_dot(self):
        assert _normalize_ext(".pdf") == ".pdf"

    def test_normalize_ext_lowercases(self):
        assert _normalize_ext(".PDF") == ".pdf"

    def test_normalize_ext_strips_whitespace(self):
        assert _normalize_ext("  .json  ") == ".json"

    def test_normalize_mime_lowercases(self):
        assert _normalize_mime("APPLICATION/JSON") == "application/json"

    def test_normalize_mime_strips_whitespace(self):
        assert _normalize_mime("  text/html  ") == "text/html"


# ═══════════════════════════════════════════════════════════════════
# 3. Extension Lookup — Common Types
# ═══════════════════════════════════════════════════════════════════

class TestExtensionLookup:
    @pytest.mark.parametrize("ext, expected_mime", [
        (".html", "text/html"),
        (".css", "text/css"),
        (".js", "text/javascript"),
        (".json", "application/json"),
        (".pdf", "application/pdf"),
        (".png", "image/png"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".gif", "image/gif"),
        (".svg", "image/svg+xml"),
        (".mp3", "audio/mpeg"),
        (".mp4", "video/mp4"),
        (".zip", "application/zip"),
        (".gz", "application/gzip"),
        (".tar", "application/x-tar"),
        (".csv", "text/csv"),
        (".xml", "text/xml"),
        (".py", "text/x-python"),
        (".rs", "text/x-rust"),
        (".go", "text/x-go"),
        (".java", "text/x-java-source"),
        (".rb", "text/x-ruby"),
        (".sh", "text/x-shellscript"),
        (".sql", "text/x-sql"),
        (".yaml", "text/x-yaml"),
        (".yml", "text/x-yaml"),
        (".toml", "text/x-toml"),
        (".webp", "image/webp"),
        (".webm", "video/webm"),
        (".woff2", "font/woff2"),
        (".ttf", "font/ttf"),
        (".otf", "font/otf"),
        (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        (".pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        (".epub", "application/epub+zip"),
        (".wav", "audio/wav"),
        (".flac", "audio/flac"),
        (".mkv", "video/x-matroska"),
        (".avi", "video/x-msvideo"),
        (".mov", "video/quicktime"),
        (".diff", "text/x-diff"),
        (".rtf", "text/rtf"),
        (".ics", "text/calendar"),
        (".vcf", "text/vcard"),
        (".bmp", "image/bmp"),
        (".tiff", "image/tiff"),
        (".ico", "image/x-icon"),
        (".heic", "image/heif"),
        (".7z", "application/x-7z-compressed"),
        (".rar", "application/x-rar-compressed"),
        (".ogg", "audio/ogg"),
        (".opus", "audio/opus"),
        (".mid", "audio/midi"),
        (".wma", "audio/x-ms-wma"),
        (".wmv", "video/x-ms-wmv"),
        (".flv", "video/x-flv"),
        (".3gp", "video/3gpp"),
        (".ogv", "video/ogg"),
        (".glb", "model/gltf-binary"),
        (".gltf", "model/gltf+json"),
        (".stl", "model/stl"),
        (".eml", "message/rfc822"),
        (".srt", "application/x-subrip"),
        (".vtt", "text/vtt"),
        (".wasm", "application/wasm"),
        (".ipynb", "application/x-ipynb+json"),
        (".graphql", "application/graphql"),
        (".jsonld", "application/ld+json"),
        (".geojson", "application/geo+json"),
        (".tex", "application/x-latex"),
        (".pem", "application/x-pem-file"),
        (".sqlite", "application/x-sqlite3"),
        (".apk", "application/vnd.android.package-archive"),
        (".iso", "application/x-iso9660-image"),
        (".deb", "application/x-deb"),
        (".rpm", "application/x-rpm"),
        (".bat", "application/x-bat"),
        (".ps1", "application/x-powershell"),
        (".kml", "application/vnd.google-earth.kml+xml"),
    ])
    def test_extension_lookup(self, ext, expected_mime):
        result = lookup_extension(ext)
        assert result.entries
        mime_types = [e.mime_type for e in result.entries]
        assert expected_mime in mime_types

    def test_lookup_without_dot(self):
        result = lookup_extension("pdf")
        assert result.primary is not None
        assert result.primary.mime_type == "application/pdf"

    def test_lookup_case_insensitive(self):
        result = lookup_extension(".PDF")
        assert result.primary is not None
        assert result.primary.mime_type == "application/pdf"

    def test_unknown_extension(self):
        result = lookup_extension(".xyz123unknown")
        assert not result.entries
        assert result.primary is None
        assert not result.is_ambiguous

    def test_empty_extension(self):
        result = lookup_extension("")
        assert not result.entries

    def test_jpeg_all_variants(self):
        for ext in [".jpg", ".jpeg", ".jpe", ".jfif"]:
            result = lookup_extension(ext)
            assert result.primary is not None
            assert result.primary.mime_type == "image/jpeg"


# ═══════════════════════════════════════════════════════════════════
# 4. Ambiguous Extensions
# ═══════════════════════════════════════════════════════════════════

class TestAmbiguousExtensions:
    def test_ts_is_ambiguous(self):
        result = lookup_extension(".ts")
        assert result.is_ambiguous
        assert len(result.entries) >= 2
        mime_types = {e.mime_type for e in result.entries}
        assert "video/mp2t" in mime_types
        assert "text/typescript" in mime_types

    def test_ts_has_different_kinds(self):
        result = lookup_extension(".ts")
        kinds = {e.kind for e in result.entries}
        assert "text" in kinds
        assert "binary" in kinds

    def test_mts_is_ambiguous(self):
        result = lookup_extension(".mts")
        assert result.is_ambiguous
        mime_types = {e.mime_type for e in result.entries}
        assert "video/mp2t" in mime_types
        assert "text/typescript" in mime_types

    def test_is_ambiguous_function(self):
        assert is_ambiguous(".ts")
        assert not is_ambiguous(".pdf")

    def test_get_ambiguous_extensions(self):
        ambiguous = get_ambiguous_extensions()
        assert isinstance(ambiguous, dict)
        assert ".ts" in ambiguous
        for ext, entries in ambiguous.items():
            assert len(entries) > 1

    def test_primary_is_first_entry(self):
        result = lookup_extension(".ts")
        assert result.primary == result.entries[0]


# ═══════════════════════════════════════════════════════════════════
# 5. Reverse Lookup
# ═══════════════════════════════════════════════════════════════════

class TestReverseLookup:
    def test_reverse_pdf(self):
        assert ".pdf" in reverse_lookup("application/pdf")

    def test_reverse_jpeg(self):
        exts = reverse_lookup("image/jpeg")
        assert ".jpg" in exts
        assert ".jpeg" in exts

    def test_reverse_html(self):
        exts = reverse_lookup("text/html")
        assert ".html" in exts
        assert ".htm" in exts

    def test_reverse_json(self):
        assert ".json" in reverse_lookup("application/json")

    def test_reverse_unknown(self):
        assert reverse_lookup("application/x-totally-made-up") == ()

    def test_reverse_case_insensitive(self):
        assert ".pdf" in reverse_lookup("APPLICATION/PDF")


# ═══════════════════════════════════════════════════════════════════
# 6. Alias Resolution
# ═══════════════════════════════════════════════════════════════════

class TestAliasResolution:
    @pytest.mark.parametrize("alias, canonical", [
        ("text/json", "application/json"),
        ("application/javascript", "text/javascript"),
        ("application/x-javascript", "text/javascript"),
        ("text/x-javascript", "text/javascript"),
        ("text/x-html", "text/html"),
        ("audio/x-wav", "audio/wav"),
        ("audio/wave", "audio/wav"),
        ("audio/x-midi", "audio/midi"),
        ("image/pjpeg", "image/jpeg"),
        ("image/vnd.microsoft.icon", "image/x-icon"),
        ("image/vnd.adobe.photoshop", "image/x-photoshop"),
        ("application/x-font-ttf", "font/ttf"),
        ("application/x-font-otf", "font/otf"),
        ("application/vnd.rar", "application/x-rar-compressed"),
        ("application/typescript", "text/typescript"),
        ("text/yaml", "text/x-yaml"),
        ("application/x-yaml", "text/x-yaml"),
        ("application/x-sh", "text/x-shellscript"),
        ("application/x-php", "text/x-php"),
        ("text/x-c++src", "text/x-c++"),
        ("application/jsonl", "application/x-ndjson"),
        ("application/exe", "application/x-msdownload"),
    ])
    def test_alias_resolves(self, alias, canonical):
        entry = lookup_mime_type(alias)
        assert entry is not None, f"Alias {alias} not found"
        assert entry.mime_type == canonical

    def test_alias_returns_same_object_as_canonical(self):
        via_alias = lookup_mime_type("text/json")
        via_canonical = lookup_mime_type("application/json")
        assert via_alias is via_canonical

    def test_unknown_returns_none(self):
        assert lookup_mime_type("application/x-does-not-exist") is None


# ═══════════════════════════════════════════════════════════════════
# 7. Metadata Accuracy
# ═══════════════════════════════════════════════════════════════════

class TestMetadata:
    def test_json_has_rfc_8259(self):
        entry = lookup_mime_type("application/json")
        assert "RFC 8259" in entry.rfcs

    def test_json_is_text(self):
        assert lookup_mime_type("application/json").kind == "text"

    def test_json_is_compressible(self):
        assert lookup_mime_type("application/json").compressible is True

    def test_json_has_alias(self):
        assert "text/json" in lookup_mime_type("application/json").aliases

    def test_pdf_is_binary(self):
        assert lookup_mime_type("application/pdf").kind == "binary"

    def test_pdf_not_compressible(self):
        assert lookup_mime_type("application/pdf").compressible is False

    def test_gzip_not_compressible(self):
        assert lookup_mime_type("application/gzip").compressible is False

    def test_tar_is_compressible(self):
        assert lookup_mime_type("application/x-tar").compressible is True

    def test_png_not_compressible(self):
        assert lookup_mime_type("image/png").compressible is False

    def test_bmp_is_compressible(self):
        assert lookup_mime_type("image/bmp").compressible is True

    def test_svg_is_text(self):
        assert lookup_mime_type("image/svg+xml").kind == "text"

    def test_wav_is_compressible(self):
        assert lookup_mime_type("audio/wav").compressible is True

    def test_mp3_not_compressible(self):
        assert lookup_mime_type("audio/mpeg").compressible is False

    def test_html_has_rfc(self):
        assert any("2854" in r for r in lookup_mime_type("text/html").rfcs)

    def test_html_has_programs(self):
        assert "web browsers" in lookup_mime_type("text/html").programs

    def test_javascript_has_multiple_aliases(self):
        assert len(lookup_mime_type("text/javascript").aliases) >= 2

    def test_compressed_formats_not_compressible(self):
        for mt in [
            "application/zip", "application/gzip", "application/x-bzip2",
            "application/x-xz", "application/zstd", "application/x-7z-compressed",
            "application/x-rar-compressed",
            "image/jpeg", "image/png", "image/gif", "image/webp", "image/avif",
            "audio/mpeg", "audio/ogg", "audio/flac", "audio/aac", "audio/opus",
            "video/mp4", "video/webm", "video/x-matroska",
            "font/woff", "font/woff2",
        ]:
            entry = lookup_mime_type(mt)
            assert entry is not None, f"Missing: {mt}"
            assert entry.compressible is False, f"{mt} should not be compressible"

    def test_text_types_compressible(self):
        for mt in [
            "text/plain", "text/html", "text/css", "text/javascript",
            "text/csv", "text/xml", "text/markdown", "application/json",
        ]:
            entry = lookup_mime_type(mt)
            assert entry is not None
            assert entry.compressible is True, f"{mt} should be compressible"


# ═══════════════════════════════════════════════════════════════════
# 8. Search
# ═══════════════════════════════════════════════════════════════════

class TestSearch:
    def test_search_video(self):
        assert len(search_mime_types("video")) >= 5

    def test_search_audio(self):
        assert len(search_mime_types("audio")) >= 5

    def test_search_image(self):
        assert len(search_mime_types("image")) >= 5

    def test_search_font(self):
        assert len(search_mime_types("font")) >= 3

    def test_search_by_program(self):
        assert len(search_mime_types("VLC")) >= 5

    def test_search_by_description(self):
        assert len(search_mime_types("spreadsheet")) >= 2

    def test_search_case_insensitive(self):
        assert len(search_mime_types("json")) == len(search_mime_types("JSON"))

    def test_search_empty(self):
        assert search_mime_types("") == []

    def test_search_no_results(self):
        assert search_mime_types("zzzznonexistent999") == []

    def test_search_no_duplicates(self):
        results = search_mime_types("text")
        types = [r.mime_type for r in results]
        assert len(types) == len(set(types))


# ═══════════════════════════════════════════════════════════════════
# 9. Utility Functions
# ═══════════════════════════════════════════════════════════════════

class TestUtilities:
    def test_get_all_extensions_count(self):
        assert len(get_all_extensions()) >= 100

    def test_get_all_extensions_sorted(self):
        exts = get_all_extensions()
        assert exts == sorted(exts)

    def test_get_all_extensions_have_dots(self):
        for ext in get_all_extensions():
            assert ext.startswith(".")

    def test_get_all_mime_types_count(self):
        assert len(get_all_mime_types()) >= 100

    def test_get_all_mime_types_sorted(self):
        types = get_all_mime_types()
        assert types == sorted(types)

    def test_get_all_mime_types_have_slash(self):
        for t in get_all_mime_types():
            assert "/" in t


# ═══════════════════════════════════════════════════════════════════
# 10. Formatting — Human Readable
# ═══════════════════════════════════════════════════════════════════

class TestFormatHuman:
    def test_format_single_match(self):
        output = format_lookup_result(lookup_extension(".pdf"))
        assert "application/pdf" in output
        assert ".pdf" in output

    def test_format_ambiguous(self):
        output = format_lookup_result(lookup_extension(".ts"))
        assert "AMBIGUOUS" in output

    def test_format_no_match(self):
        output = format_lookup_result(lookup_extension(".xyz123"))
        assert "No MIME type found" in output

    def test_format_info(self):
        entry = lookup_mime_type("application/json")
        output = format_info(entry)
        assert "application/json" in output
        assert "RFC 8259" in output

    def test_format_search(self):
        output = format_search_results(search_mime_types("video"), "video")
        assert "Found" in output

    def test_format_search_empty(self):
        output = format_search_results([], "zzz")
        assert "No MIME types matching" in output


# ═══════════════════════════════════════════════════════════════════
# 11. Formatting — JSON
# ═══════════════════════════════════════════════════════════════════

class TestFormatJSON:
    def test_lookup_json(self):
        data = json.loads(format_lookup_result(lookup_extension(".pdf"), as_json=True))
        assert data["extension"] == ".pdf"
        assert len(data["matches"]) == 1
        assert data["matches"][0]["mime_type"] == "application/pdf"

    def test_ambiguous_json(self):
        data = json.loads(format_lookup_result(lookup_extension(".ts"), as_json=True))
        assert data["ambiguous"] is True
        assert len(data["matches"]) >= 2

    def test_no_match_json(self):
        data = json.loads(format_lookup_result(lookup_extension(".xyz"), as_json=True))
        assert data["matches"] == []

    def test_info_json(self):
        data = json.loads(format_info(lookup_mime_type("image/png"), as_json=True))
        assert data["mime_type"] == "image/png"
        assert data["kind"] == "binary"
        assert ".png" in data["extensions"]

    def test_search_json(self):
        data = json.loads(format_search_results(search_mime_types("font"), "font", as_json=True))
        assert data["query"] == "font"
        assert data["count"] >= 3

    def test_json_aliases(self):
        data = json.loads(format_info(lookup_mime_type("application/json"), as_json=True))
        assert "text/json" in data["aliases"]

    def test_json_rfcs(self):
        data = json.loads(format_info(lookup_mime_type("application/json"), as_json=True))
        assert "RFC 8259" in data["rfcs"]

    def test_json_programs(self):
        data = json.loads(format_info(lookup_mime_type("text/html"), as_json=True))
        assert "web browsers" in data["programs"]

    def test_entry_to_dict_minimal(self):
        """Entry with no aliases/rfcs/programs should not include those keys."""
        entry = MimeEntry("test/minimal", (".test",), "text", True, "Test entry")
        d = _entry_to_dict(entry)
        assert "aliases" not in d
        assert "rfcs" not in d
        assert "programs" not in d


# ═══════════════════════════════════════════════════════════════════
# 12. Edge Cases
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_dot_only(self):
        assert not lookup_extension(".").entries

    def test_very_long_extension(self):
        assert not lookup_extension("." + "a" * 1000).entries

    def test_unicode_extension(self):
        result = lookup_extension(".日本語")
        assert isinstance(result, LookupResult)
        assert not result.entries

    def test_lookup_result_frozen(self):
        result = lookup_extension(".pdf")
        with pytest.raises(AttributeError):
            result.extension = "changed"

    def test_mime_entry_frozen(self):
        entry = lookup_mime_type("application/json")
        with pytest.raises(AttributeError):
            entry.mime_type = "changed"
