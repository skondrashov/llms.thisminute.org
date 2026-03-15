"""Tests for HTML content — links, assets, and structural integrity."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_html(filename):
    with open(os.path.join(ROOT, filename), encoding="utf-8") as f:
        return f.read()


class TestIndexLinks:
    def test_evolution_link_resolves(self):
        """The 'case' link should point to a file that exists."""
        html = _read_html("index.html")
        match = re.search(r'href="([^"]*evolution[^"]*)"', html)
        assert match, "No evolution link found in index.html"
        href = match.group(1)
        target = os.path.join(ROOT, href)
        assert os.path.isfile(target), f"Evolution link target '{href}' does not exist"

    def test_cross_site_links_have_trailing_slashes(self):
        """Cross-site nav links should use trailing slashes."""
        html = _read_html("index.html")
        for path in ["/toolshed/", "/forge/"]:
            assert f'href="{path}"' in html, f"Missing or malformed link to {path}"

    def test_fieldnotes_inline_trigger_exists(self):
        """There should be an inline field notes trigger near the intro blurb."""
        html = _read_html("index.html")
        assert 'id="fieldnotes-inline"' in html, "Inline field notes trigger not found"

    def test_fieldnotes_overlay_exists(self):
        """The field notes overlay/modal should exist."""
        html = _read_html("index.html")
        assert 'id="fieldnotes-overlay"' in html, "Field notes overlay not found"

    def test_theme_key_is_unified(self):
        """Should use thisminute_theme, not rhizome_theme."""
        html = _read_html("index.html")
        assert "thisminute_theme" in html, "Unified theme key not found"
        assert "rhizome_theme" not in html, "Old rhizome_theme key still present"


class TestEvolutionPage:
    def test_evolution_html_exists(self):
        assert os.path.isfile(os.path.join(ROOT, "evolution.html"))

    def test_evolution_theme_key_is_unified(self):
        """evolution.html should also use thisminute_theme."""
        html = _read_html("evolution.html")
        assert "thisminute_theme" in html, "Unified theme key not found in evolution.html"
        assert "rhizome_theme" not in html, "Old rhizome_theme key still in evolution.html"
