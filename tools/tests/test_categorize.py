"""Tests for the categorization pipeline.

Validates that the categorizer correctly assigns categories
and doesn't produce known false positives.
"""
import pytest
from scrape.categorize import categorize, build_category_index, KEYWORD_TO_CATEGORY, STOP_WORDS
from scrape.config import VALID_CATEGORIES


@pytest.fixture(scope="module")
def category_index():
    return build_category_index()


class TestKeywordMapping:
    """Direct keyword → category mappings should be valid."""

    def test_all_keyword_categories_are_valid(self):
        invalid = {k: v for k, v in KEYWORD_TO_CATEGORY.items()
                   if v not in VALID_CATEGORIES}
        assert not invalid, f"Keywords map to invalid categories: {invalid}"


class TestStopWords:
    """Stop words should not appear in category index."""

    def test_stop_words_exist(self):
        assert len(STOP_WORDS) > 50

    def test_common_stop_words_present(self):
        for word in ["the", "and", "for", "with", "that", "this"]:
            assert word in STOP_WORDS


class TestTier1:
    """Tier 1: Direct topic/tag matching."""

    @pytest.mark.parametrize("tag,expected", [
        ("docker", "Container Orchestration"),
        ("kubernetes", "Container Orchestration"),
        ("vpn", "VPN"),
        ("chess", "Chess"),
        ("orm", "ORMs"),
        ("llm", "LLM Tools"),
        ("blockchain", "Blockchain & Web3"),
        ("tui", "Terminal UI"),
    ])
    def test_tier1_tag_match(self, tag, expected):
        entry = {"tags": [tag], "description": "A tool"}
        result = categorize(entry)
        assert result == expected


class TestTier2:
    """Tier 2: Description/name keyword matching."""

    @pytest.mark.parametrize("desc,expected", [
        ("A terminal-emulator for power users", "Terminal Emulators"),
        ("Password manager with browser integration", "Password Managers"),
        ("Machine learning framework", "AI/ML Libraries"),
    ])
    def test_tier2_description_match(self, desc, expected):
        entry = {"tags": [], "description": desc, "name": "TestTool"}
        result = categorize(entry)
        assert result == expected


class TestTier3:
    """Tier 3: Category index scoring."""

    def test_tier3_respects_excluded_categories(self, category_index):
        # An entry with generic words should NOT be categorized as
        # Desktop App Frameworks or Mobile IDE & Tools (both excluded)
        entry = {"tags": [], "description": "A desktop application for debugging iOS apps", "name": "DebugHelper"}
        result = categorize(entry, category_index)
        assert result != "Desktop App Frameworks"
        assert result != "Mobile IDE & Tools"

    def test_tier3_returns_none_for_garbage(self, category_index):
        # Very generic entry should get None (below confidence threshold)
        entry = {"tags": [], "description": "A thing", "name": "Thing"}
        result = categorize(entry, category_index)
        assert result is None


class TestKnownFalsePositives:
    """Entries that were historically miscategorized should now be correct."""

    def test_generic_tool_not_code_editor_via_tier3(self, category_index):
        """A tool with no editor-related keywords shouldn't land in Code Editors via Tier 3."""
        entry = {
            "tags": ["molecule", "chemistry"],
            "description": "Molecular structure visualizer for research",
            "name": "MolView",
        }
        result = categorize(entry, category_index)
        assert result != "Code Editors"

    def test_poker_app_not_ai_assistant(self, category_index):
        entry = {
            "tags": ["poker"],
            "description": "Poker HUD and analysis tool",
            "name": "Poker Copilot",
        }
        result = categorize(entry, category_index)
        assert result != "AI Assistants"

    def test_break_reminder_not_ai_assistant(self, category_index):
        entry = {
            "tags": ["health", "macos"],
            "description": "Break reminder assistant for macOS",
            "name": "MacBreakZ",
        }
        result = categorize(entry, category_index)
        assert result != "AI Assistants"

    def test_go_networking_lib_not_vpn(self, category_index):
        entry = {
            "tags": ["go", "tcp", "networking"],
            "description": "Go library for TCP/UDP packet processing",
            "name": "gopacket",
        }
        result = categorize(entry)
        assert result == "Networking"

    def test_zx_spectrum_emulator_not_cicd(self, category_index):
        entry = {
            "tags": ["emulator", "retro"],
            "description": "ZX Spectrum emulator written in Rust",
            "name": "rustzx",
        }
        result = categorize(entry, category_index)
        assert result != "CI/CD Tools"
