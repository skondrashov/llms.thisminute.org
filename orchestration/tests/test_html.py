"""Tests for HTML content — links, assets, and structural integrity."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_html(filename):
    with open(os.path.join(ROOT, filename), encoding="utf-8") as f:
        return f.read()


class TestIndexLinks:
    def test_cross_site_nav_via_shared_library(self):
        """Cross-site nav uses shared llms.js which injects nav with portal link."""
        html = _read_html("index.html")
        assert '/shared/llms.js' in html, "Missing shared llms.js include"
        assert '/shared/llms.css' in html, "Missing shared llms.css include"
        # Nav is now injected by llms.js (DRY pattern) — portal link lives there
        llms_js = os.path.join(ROOT, '..', 'shared', 'llms.js')
        assert os.path.isfile(llms_js), "shared/llms.js file not found"
        with open(llms_js, encoding='utf-8') as f:
            js = f.read()
        assert "href: '/'" in js, "Missing portal link in shared nav (llms.js)"

    def test_theme_key_is_unified(self):
        """Should use thisminute_theme, not orchestration_theme."""
        html = _read_html("index.html")
        assert "thisminute_theme" in html, "Unified theme key not found"
        assert "orchestration_theme" not in html, "Old orchestration_theme key still present"


class TestArchive:
    def test_archived_content_preserved(self):
        """Evolution and field notes content should exist in archive."""
        archive = os.path.join(ROOT, "archive")
        assert os.path.isfile(os.path.join(archive, "evolution.html"))
        assert os.path.isfile(os.path.join(archive, "fieldnotes.html"))
