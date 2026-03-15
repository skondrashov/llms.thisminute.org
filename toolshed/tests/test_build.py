"""Build output tests.

Runs build.py and validates that all expected output files
are generated with correct structure.
"""
import json
import os
import subprocess
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def build_output():
    """Run build.py once and return its exit code + stdout."""
    result = subprocess.run(
        ["python", "build.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result


class TestBuildRuns:
    def test_build_exits_cleanly(self, build_output):
        assert build_output.returncode == 0, f"build.py failed:\n{build_output.stderr}"

    def test_build_reports_entry_count(self, build_output):
        assert "Built data.js with" in build_output.stdout


class TestDataJs:
    def test_data_js_exists(self, build_output):
        assert os.path.exists(os.path.join(ROOT, "data.js"))

    def test_data_js_starts_with_window_software(self, build_output):
        with open(os.path.join(ROOT, "data.js"), encoding="utf-8") as f:
            content = f.read(30)
        assert content.startswith("window.SOFTWARE = ")

    def test_data_js_is_valid_json_payload(self, build_output):
        with open(os.path.join(ROOT, "data.js"), encoding="utf-8") as f:
            content = f.read()
        # Strip the wrapper
        assert content.startswith("window.SOFTWARE = ")
        assert content.rstrip().endswith(";")
        json_str = content[len("window.SOFTWARE = "):-2]
        entries = json.loads(json_str)
        assert isinstance(entries, list)
        assert len(entries) > 100


class TestApiCatalog:
    def test_catalog_json_exists(self, build_output):
        assert os.path.exists(os.path.join(ROOT, "api", "v1", "catalog.json"))

    def test_catalog_json_is_valid(self, build_output):
        with open(os.path.join(ROOT, "api", "v1", "catalog.json"), encoding="utf-8") as f:
            entries = json.load(f)
        assert isinstance(entries, list)
        assert len(entries) > 100

    def test_catalog_entries_have_required_fields(self, build_output):
        with open(os.path.join(ROOT, "api", "v1", "catalog.json"), encoding="utf-8") as f:
            entries = json.load(f)
        required = {"id", "name", "description", "url", "category", "os", "pricing"}
        for e in entries[:50]:  # spot-check first 50
            missing = required - set(e.keys())
            assert not missing, f"Entry {e.get('id')} missing: {missing}"


class TestCategoriesJson:
    def test_categories_json_exists(self, build_output):
        assert os.path.exists(os.path.join(ROOT, "api", "v1", "categories.json"))

    def test_categories_json_is_dict(self, build_output):
        with open(os.path.join(ROOT, "api", "v1", "categories.json"), encoding="utf-8") as f:
            cats = json.load(f)
        assert isinstance(cats, dict)
        assert len(cats) > 50


class TestTaxonomyJs:
    def test_taxonomy_js_exists(self, build_output):
        assert os.path.exists(os.path.join(ROOT, "taxonomy.js"))

    def test_taxonomy_js_has_valid_structure(self, build_output):
        with open(os.path.join(ROOT, "taxonomy.js"), encoding="utf-8") as f:
            content = f.read()
        assert content.startswith("window.TAXONOMY = ")
        json_str = content[len("window.TAXONOMY = "):-2]
        tax = json.loads(json_str)
        assert "children" in tax
        assert len(tax["children"]) > 10


class TestLlmsTxt:
    def test_llms_txt_exists(self, build_output):
        assert os.path.exists(os.path.join(ROOT, "llms.txt"))

    def test_llms_txt_has_header(self, build_output):
        with open(os.path.join(ROOT, "llms.txt"), encoding="utf-8") as f:
            content = f.read()
        assert "# main.menu" in content
        assert "/api/v1/catalog.json" in content

    def test_llms_full_txt_exists(self, build_output):
        assert os.path.exists(os.path.join(ROOT, "llms-full.txt"))


class TestNoscript:
    def test_noscript_injected(self, build_output):
        assert "Injected noscript catalog into index.html" in build_output.stdout

    def test_index_has_noscript_block(self, build_output):
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
            content = f.read()
        assert "<!-- NOSCRIPT_CATALOG -->" in content
        assert "<noscript>" in content


class TestDataJsMatchesCatalog:
    """data.js and catalog.json should have the same entries."""

    def test_entry_counts_match(self, build_output):
        with open(os.path.join(ROOT, "data.js"), encoding="utf-8") as f:
            content = f.read()
        js_entries = json.loads(content[len("window.SOFTWARE = "):-2])

        with open(os.path.join(ROOT, "api", "v1", "catalog.json"), encoding="utf-8") as f:
            api_entries = json.load(f)

        assert len(js_entries) == len(api_entries)
