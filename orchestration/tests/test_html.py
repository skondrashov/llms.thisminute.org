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

    def test_cross_site_nav_via_shared_library(self):
        """Cross-site nav uses shared forge.js which injects nav with portal link."""
        html = _read_html("index.html")
        assert '/shared/forge.js' in html, "Missing shared forge.js include"
        assert '/shared/forge.css' in html, "Missing shared forge.css include"
        # Nav is now injected by forge.js (DRY pattern) — portal link lives there
        forge_js = os.path.join(ROOT, '..', 'shared', 'forge.js')
        assert os.path.isfile(forge_js), "shared/forge.js file not found"
        with open(forge_js, encoding='utf-8') as f:
            js = f.read()
        assert "href: '/'" in js, "Missing portal link in shared nav (forge.js)"

    def test_fieldnotes_inline_trigger_exists(self):
        """There should be an inline field notes trigger near the intro blurb."""
        html = _read_html("index.html")
        assert 'id="fieldnotes-inline"' in html, "Inline field notes trigger not found"

    def test_fieldnotes_overlay_exists(self):
        """The field notes overlay/modal should exist."""
        html = _read_html("index.html")
        assert 'id="fieldnotes-overlay"' in html, "Field notes overlay not found"

    def test_theme_key_is_unified(self):
        """Should use thisminute_theme, not orchestration_theme."""
        html = _read_html("index.html")
        assert "thisminute_theme" in html, "Unified theme key not found"
        assert "orchestration_theme" not in html, "Old orchestration_theme key still present"


class TestEvolutionPage:
    def test_evolution_html_exists(self):
        assert os.path.isfile(os.path.join(ROOT, "evolution.html"))

    def test_evolution_theme_key_is_unified(self):
        """evolution.html should also use thisminute_theme."""
        html = _read_html("evolution.html")
        assert "thisminute_theme" in html, "Unified theme key not found in evolution.html"
        assert "orchestration_theme" not in html, "Old orchestration_theme key still in evolution.html"
