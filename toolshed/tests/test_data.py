"""Data integrity tests for the software catalog.

Validates that all entries in data/*.json conform to the schema
and have consistent, valid values.
"""
import json
import glob
import os
import re
import pytest

from scrape.config import (
    DATA_DIR, VALID_OS, VALID_PRICING, VALID_LANGUAGES,
    get_all_categories,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID_PATTERN = re.compile(r"^[a-z0-9-]+$")

# Convert lists to sets for O(1) membership checks in tests
VALID_OS = set(VALID_OS)
VALID_PRICING = set(VALID_PRICING)
VALID_LANGUAGES = set(VALID_LANGUAGES)


def load_all_entries():
    entries = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            item["_source_file"] = os.path.basename(path)
            entries.append(item)
    return entries


VALID_CATEGORIES = get_all_categories()
ALL_ENTRIES = load_all_entries()


class TestRequiredFields:
    """Every entry must have the required fields."""

    @pytest.fixture(params=["id", "name", "description", "url", "category", "os", "pricing"])
    def required_field(self, request):
        return request.param

    def test_required_fields_present(self, required_field):
        missing = []
        for e in ALL_ENTRIES:
            if required_field not in e or not e[required_field]:
                missing.append(f"{e.get('id', '???')} in {e['_source_file']}")
        assert not missing, f"{len(missing)} entries missing '{required_field}': {missing[:10]}"


class TestFieldValues:
    """Field values must conform to schema constraints."""

    def test_ids_are_kebab_case(self):
        bad = [(e["id"], e["_source_file"]) for e in ALL_ENTRIES
               if "id" in e and not ID_PATTERN.match(e["id"])]
        assert not bad, f"{len(bad)} entries with invalid IDs: {bad[:10]}"

    def test_descriptions_under_200_chars(self):
        long = [(e["id"], len(e["description"]), e["_source_file"])
                for e in ALL_ENTRIES
                if len(e.get("description", "")) > 200]
        assert not long, f"{len(long)} entries with descriptions > 200 chars: {long[:10]}"

    def test_os_values_valid(self):
        bad = []
        for e in ALL_ENTRIES:
            invalid_os = [o for o in e.get("os", []) if o not in VALID_OS]
            if invalid_os:
                bad.append((e["id"], invalid_os))
        assert not bad, f"{len(bad)} entries with invalid OS values: {bad[:10]}"

    def test_pricing_values_valid(self):
        bad = [(e["id"], e["pricing"]) for e in ALL_ENTRIES
               if e.get("pricing") and e["pricing"] not in VALID_PRICING]
        assert not bad, f"{len(bad)} entries with invalid pricing: {bad[:10]}"

    def test_language_values_valid(self):
        bad = [(e["id"], e["language"]) for e in ALL_ENTRIES
               if e.get("language") and e["language"] not in VALID_LANGUAGES]
        assert not bad, f"{len(bad)} entries with invalid language: {bad[:10]}"

    def test_categories_exist_in_taxonomy(self):
        bad = [(e["id"], e["category"]) for e in ALL_ENTRIES
               if e.get("category") and e["category"] not in VALID_CATEGORIES]
        assert not bad, f"{len(bad)} entries with categories not in taxonomy: {bad[:10]}"

    def test_urls_look_valid(self):
        bad = [(e["id"], e["url"]) for e in ALL_ENTRIES
               if e.get("url") and not e["url"].startswith(("http://", "https://"))]
        assert not bad, f"{len(bad)} entries with non-http URLs: {bad[:10]}"

    def test_source_urls_look_valid(self):
        bad = [(e["id"], e["source"]) for e in ALL_ENTRIES
               if e.get("source") and not e["source"].startswith(("http://", "https://"))]
        assert not bad, f"{len(bad)} entries with non-http source URLs: {bad[:10]}"


class TestNoDuplicates:
    """No duplicate IDs, URLs, or names across the catalog."""

    def test_no_duplicate_ids(self):
        seen = {}
        dupes = []
        for e in ALL_ENTRIES:
            eid = e.get("id", "")
            if eid in seen:
                dupes.append((eid, seen[eid], e["_source_file"]))
            else:
                seen[eid] = e["_source_file"]
        assert not dupes, f"{len(dupes)} duplicate IDs: {dupes[:10]}"

    def test_no_duplicate_urls_across_all_files(self):
        """No two entries should share the same normalized URL."""
        seen = {}
        dupes = []
        for e in ALL_ENTRIES:
            url = e.get("url", "").lower().rstrip("/")
            # Strip www. prefix for normalization
            url = re.sub(r"^(https?://)www\.", r"\1", url)
            # Strip URL fragments for curated entries (discovered entries
            # legitimately use fragments to distinguish sub-tools)
            is_discovered = e["_source_file"].startswith("discovered")
            if not is_discovered:
                url = url.split("#")[0]
            if not url:
                continue
            if url in seen:
                dupes.append((e["id"], seen[url], e["_source_file"], url))
            else:
                seen[url] = e["id"]
        assert not dupes, (
            f"{len(dupes)} duplicate URLs: "
            + "; ".join(f"{d[0]} & {d[1]} share {d[3]}" for d in dupes[:10])
        )

    def test_no_duplicate_names_in_curated_files(self):
        """No two curated entries should share the same name (case-insensitive)."""
        curated = [
            e for e in ALL_ENTRIES
            if not e["_source_file"].startswith("discovered")
        ]
        seen = {}
        dupes = []
        for e in curated:
            name_lower = e.get("name", "").strip().lower()
            if not name_lower:
                continue
            if name_lower in seen:
                dupes.append((
                    e["id"], seen[name_lower], e["_source_file"], name_lower
                ))
            else:
                seen[name_lower] = e["id"]
        assert not dupes, (
            f"{len(dupes)} duplicate names in curated files: "
            + "; ".join(
                f"{d[0]} & {d[1]} both named '{d[3]}'" for d in dupes[:10]
            )
        )


class TestCatalogHealth:
    """Overall catalog health checks."""

    def test_minimum_entry_count(self):
        assert len(ALL_ENTRIES) >= 1000, f"Only {len(ALL_ENTRIES)} entries — expected at least 1000"

    def test_minimum_category_count(self):
        cats = {e["category"] for e in ALL_ENTRIES if e.get("category")}
        assert len(cats) >= 50, f"Only {len(cats)} categories populated — expected at least 50"

    def test_no_empty_data_files(self):
        empty = []
        for path in glob.glob(os.path.join(DATA_DIR, "*.json")):
            with open(path, encoding="utf-8") as f:
                items = json.load(f)
            if not items:
                empty.append(os.path.basename(path))
        assert not empty, f"Empty data files: {empty}"

    def test_data_files_are_valid_json(self):
        bad = []
        for path in glob.glob(os.path.join(DATA_DIR, "*.json")):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                assert isinstance(data, list)
            except (json.JSONDecodeError, AssertionError):
                bad.append(os.path.basename(path))
        assert not bad, f"Invalid JSON files: {bad}"
