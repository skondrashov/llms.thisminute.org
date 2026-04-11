"""Taxonomy integrity tests.

Validates taxonomy.json structure and consistency with data files.
"""
import json
import glob
import os
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAXONOMY_PATH = os.path.join(ROOT, "taxonomy.json")
DATA_DIR = os.path.join(ROOT, "data")


@pytest.fixture(scope="module")
def taxonomy():
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def taxonomy_categories(taxonomy):
    cats = set()
    def walk(node):
        if "categories" in node:
            cats.update(node["categories"])
        for child in node.get("children", []):
            walk(child)
    walk(taxonomy)
    return cats


@pytest.fixture(scope="module")
def data_categories():
    cats = set()
    for path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        with open(path, encoding="utf-8") as f:
            for entry in json.load(f):
                if entry.get("category"):
                    cats.add(entry["category"])
    return cats


class TestTaxonomyStructure:
    def test_has_root_name(self, taxonomy):
        assert "name" in taxonomy

    def test_has_children(self, taxonomy):
        assert "children" in taxonomy
        assert len(taxonomy["children"]) > 10

    def test_all_leaves_have_categories(self, taxonomy):
        """Every leaf node must have a categories array."""
        missing = []
        def walk(node, path=""):
            current = f"{path}/{node['name']}"
            if "children" not in node and "categories" not in node:
                missing.append(current)
            for child in node.get("children", []):
                walk(child, current)
        walk(taxonomy)
        assert not missing, f"Leaf nodes without categories: {missing}"

    def test_no_empty_category_arrays(self, taxonomy):
        empty = []
        def walk(node, path=""):
            current = f"{path}/{node['name']}"
            if "categories" in node and not node["categories"]:
                empty.append(current)
            for child in node.get("children", []):
                walk(child, current)
        walk(taxonomy)
        assert not empty, f"Nodes with empty categories: {empty}"

    def test_no_duplicate_categories(self, taxonomy):
        """Each category should appear in the taxonomy at most once."""
        seen = {}
        def walk(node, path=""):
            current = f"{path}/{node['name']}"
            for cat in node.get("categories", []):
                if cat in seen:
                    seen[cat].append(current)
                else:
                    seen[cat] = [current]
            for child in node.get("children", []):
                walk(child, current)
        walk(taxonomy)
        dupes = {cat: paths for cat, paths in seen.items() if len(paths) > 1}
        assert not dupes, f"Categories appearing in multiple places: {dupes}"


class TestTaxonomyDataConsistency:
    def test_data_categories_exist_in_taxonomy(self, taxonomy_categories, data_categories):
        """Every category used in data files should exist in taxonomy."""
        orphans = data_categories - taxonomy_categories
        assert not orphans, f"Data categories not in taxonomy: {orphans}"
