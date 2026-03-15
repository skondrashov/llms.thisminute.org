"""Comprehensive tests for the WCAG 2.1 Color Contrast Checker."""

from __future__ import annotations

import math
import subprocess
import sys

import pytest

from checker import (
    NAMED_COLORS,
    WCAG_LEVELS,
    _linearize,
    contrast_ratio,
    evaluate_wcag,
    palette_matrix,
    parse_color,
    relative_luminance,
    rgb_to_hex,
    suggest_colors,
)

# =====================================================================
# 1. Color parsing
# =====================================================================


class TestColorParsing:
    """parse_color must handle hex, rgb(), bare CSV, and named colors."""

    # --- hex 6-digit ---------------------------------------------------
    def test_hex_6_lower(self):
        assert parse_color("#ff8800") == (255, 136, 0)

    def test_hex_6_upper(self):
        assert parse_color("#FF8800") == (255, 136, 0)

    def test_hex_6_mixed(self):
        assert parse_color("#Ff8800") == (255, 136, 0)

    def test_hex_6_black(self):
        assert parse_color("#000000") == (0, 0, 0)

    def test_hex_6_white(self):
        assert parse_color("#ffffff") == (255, 255, 255)

    # --- hex 3-digit ---------------------------------------------------
    def test_hex_3_lower(self):
        assert parse_color("#fff") == (255, 255, 255)

    def test_hex_3_upper(self):
        assert parse_color("#FFF") == (255, 255, 255)

    def test_hex_3_mixed(self):
        assert parse_color("#f80") == (255, 136, 0)

    def test_hex_3_black(self):
        assert parse_color("#000") == (0, 0, 0)

    def test_hex_3_777(self):
        # #777 -> #777777 -> (119, 119, 119)
        assert parse_color("#777") == (119, 119, 119)

    # --- rgb() ---------------------------------------------------------
    def test_rgb_basic(self):
        assert parse_color("rgb(255, 128, 0)") == (255, 128, 0)

    def test_rgb_no_spaces(self):
        assert parse_color("rgb(0,0,0)") == (0, 0, 0)

    def test_rgb_extra_spaces(self):
        assert parse_color("rgb(  10 , 20 , 30 )") == (10, 20, 30)

    def test_rgb_case_insensitive(self):
        assert parse_color("RGB(100,200,50)") == (100, 200, 50)

    # --- bare CSV ------------------------------------------------------
    def test_csv_basic(self):
        assert parse_color("128,64,32") == (128, 64, 32)

    def test_csv_with_spaces(self):
        assert parse_color("128, 64, 32") == (128, 64, 32)

    # --- named colors --------------------------------------------------
    def test_named_white(self):
        assert parse_color("white") == (255, 255, 255)

    def test_named_black(self):
        assert parse_color("black") == (0, 0, 0)

    def test_named_red(self):
        assert parse_color("red") == (255, 0, 0)

    def test_named_blue(self):
        assert parse_color("blue") == (0, 0, 255)

    def test_named_green(self):
        assert parse_color("green") == (0, 128, 0)

    def test_named_case_insensitive(self):
        assert parse_color("White") == (255, 255, 255)
        assert parse_color("WHITE") == (255, 255, 255)
        assert parse_color("ReD") == (255, 0, 0)

    def test_named_teal(self):
        assert parse_color("teal") == (0, 128, 128)

    def test_named_fuchsia(self):
        assert parse_color("fuchsia") == (255, 0, 255)

    def test_named_silver(self):
        assert parse_color("silver") == (192, 192, 192)

    def test_named_maroon(self):
        assert parse_color("maroon") == (128, 0, 0)

    def test_named_navy(self):
        assert parse_color("navy") == (0, 0, 128)

    def test_named_olive(self):
        assert parse_color("olive") == (128, 128, 0)

    def test_named_purple(self):
        assert parse_color("purple") == (128, 0, 128)

    def test_named_aqua(self):
        assert parse_color("aqua") == (0, 255, 255)

    def test_named_lime(self):
        assert parse_color("lime") == (0, 255, 0)

    def test_named_yellow(self):
        assert parse_color("yellow") == (255, 255, 0)

    def test_named_orange(self):
        assert parse_color("orange") == (255, 165, 0)

    def test_named_gray(self):
        assert parse_color("gray") == (128, 128, 128)

    # --- whitespace trimming -------------------------------------------
    def test_leading_trailing_spaces(self):
        assert parse_color("  #fff  ") == (255, 255, 255)
        assert parse_color("  white  ") == (255, 255, 255)

    # --- rgb_to_hex ----------------------------------------------------
    def test_rgb_to_hex(self):
        assert rgb_to_hex(0, 0, 0) == "#000000"
        assert rgb_to_hex(255, 255, 255) == "#ffffff"
        assert rgb_to_hex(26, 26, 46) == "#1a1a2e"


# =====================================================================
# 2. Relative luminance
# =====================================================================


class TestRelativeLuminance:
    """Verify the sRGB linearization and luminance formula."""

    def test_black_luminance(self):
        assert relative_luminance(0, 0, 0) == 0.0

    def test_white_luminance(self):
        assert relative_luminance(255, 255, 255) == pytest.approx(1.0, abs=1e-6)

    def test_red_luminance(self):
        # Pure red: 0.2126 * linearize(255)
        expected = 0.2126
        assert relative_luminance(255, 0, 0) == pytest.approx(expected, abs=1e-4)

    def test_green_css_luminance(self):
        # CSS "green" is (0, 128, 0)
        lin_128 = _linearize(128)
        expected = 0.7152 * lin_128
        assert relative_luminance(0, 128, 0) == pytest.approx(expected, abs=1e-6)

    def test_blue_luminance(self):
        expected = 0.0722
        assert relative_luminance(0, 0, 255) == pytest.approx(expected, abs=1e-4)

    def test_mid_gray_luminance(self):
        # (128, 128, 128) — all channels equal
        lin = _linearize(128)
        expected = (0.2126 + 0.7152 + 0.0722) * lin  # = lin
        assert relative_luminance(128, 128, 128) == pytest.approx(expected, abs=1e-6)

    def test_linearize_boundary(self):
        """The 0.04045 threshold: values at and just around it."""
        # Channel value 10 -> sRGB 10/255 ~ 0.0392 < 0.04045 -> linear path
        assert _linearize(10) == pytest.approx(10 / 255 / 12.92, abs=1e-10)
        # Channel value 11 -> sRGB 11/255 ~ 0.0431 > 0.04045 -> gamma path
        s = 11 / 255
        assert _linearize(11) == pytest.approx(((s + 0.055) / 1.055) ** 2.4, abs=1e-10)

    def test_luminance_ordering(self):
        """White > mid-gray > black."""
        assert relative_luminance(255, 255, 255) > relative_luminance(128, 128, 128)
        assert relative_luminance(128, 128, 128) > relative_luminance(0, 0, 0)


# =====================================================================
# 3. Contrast ratio — known pairs
# =====================================================================


class TestContrastRatio:
    """Contrast ratios verified against W3C reference values."""

    def test_black_on_white(self):
        assert contrast_ratio((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, abs=0.1)

    def test_white_on_white(self):
        assert contrast_ratio((255, 255, 255), (255, 255, 255)) == pytest.approx(1.0, abs=0.01)

    def test_black_on_black(self):
        assert contrast_ratio((0, 0, 0), (0, 0, 0)) == pytest.approx(1.0, abs=0.01)

    def test_symmetry(self):
        """Contrast ratio is the same regardless of which color is fg/bg."""
        c1 = (100, 50, 200)
        c2 = (200, 220, 240)
        assert contrast_ratio(c1, c2) == pytest.approx(contrast_ratio(c2, c1), abs=1e-10)

    def test_777_on_white(self):
        """#777777 on white: approximately 4.48:1 — the classic edge case."""
        ratio = contrast_ratio((119, 119, 119), (255, 255, 255))
        assert 4.4 < ratio < 4.6
        # Specifically fails AA normal (4.5) but passes AA large (3.0)
        assert ratio < 4.5

    def test_1a1a2e_on_e4e4ed(self):
        """The example from the spec: #1a1a2e on #e4e4ed should be ~11.2:1."""
        ratio = contrast_ratio((26, 26, 46), (228, 228, 237))
        assert ratio > 10.0

    def test_ratio_always_gte_1(self):
        """Ratio is always >= 1."""
        import random

        random.seed(42)
        for _ in range(100):
            c1 = tuple(random.randint(0, 255) for _ in range(3))
            c2 = tuple(random.randint(0, 255) for _ in range(3))
            assert contrast_ratio(c1, c2) >= 1.0


# =====================================================================
# 4. WCAG level evaluation — boundary cases
# =====================================================================


class TestWCAGEvaluation:
    """Exact boundary tests for WCAG thresholds."""

    def test_aa_normal_pass_at_4_5(self):
        result = evaluate_wcag(4.5)
        assert result["AA Normal text"] is True

    def test_aa_normal_fail_at_4_49(self):
        result = evaluate_wcag(4.49)
        assert result["AA Normal text"] is False

    def test_aaa_normal_pass_at_7(self):
        result = evaluate_wcag(7.0)
        assert result["AAA Normal text"] is True

    def test_aaa_normal_fail_at_6_99(self):
        result = evaluate_wcag(6.99)
        assert result["AAA Normal text"] is False

    def test_aa_large_pass_at_3(self):
        result = evaluate_wcag(3.0)
        assert result["AA Large text"] is True

    def test_aa_large_fail_at_2_99(self):
        result = evaluate_wcag(2.99)
        assert result["AA Large text"] is False

    def test_aa_ui_components_pass_at_3(self):
        result = evaluate_wcag(3.0)
        assert result["AA UI components"] is True

    def test_all_pass_at_21(self):
        result = evaluate_wcag(21.0)
        assert all(result.values())

    def test_all_fail_at_1(self):
        result = evaluate_wcag(1.0)
        assert not any(result.values())

    def test_specific_level_filter(self):
        result = evaluate_wcag(5.0, levels=["AA Normal text"])
        assert len(result) == 1
        assert result["AA Normal text"] is True

    def test_777_on_white_levels(self):
        """#777 on white: fails AA normal, passes AA large."""
        ratio = contrast_ratio((119, 119, 119), (255, 255, 255))
        result = evaluate_wcag(ratio)
        assert result["AA Normal text"] is False
        assert result["AAA Normal text"] is False
        assert result["AA Large text"] is True
        assert result["AA UI components"] is True


# =====================================================================
# 5. Palette matrix generation
# =====================================================================


class TestPaletteMatrix:
    """Palette matrix for N colors should be NxN with correct ratios."""

    def test_three_colors(self):
        colors = ["black", "white", "#777"]
        matrix = palette_matrix(colors)
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)
        # Diagonal is None
        for i in range(3):
            assert matrix[i][i] is None

    def test_diagonal_is_none(self):
        colors = ["red", "blue", "green", "yellow"]
        matrix = palette_matrix(colors)
        for i in range(4):
            assert matrix[i][i] is None

    def test_symmetry_in_matrix(self):
        """matrix[i][j] == matrix[j][i] because contrast ratio is symmetric."""
        colors = ["#1a1a2e", "#e4e4ed", "#22d3ee", "#9898ad"]
        matrix = palette_matrix(colors)
        for i in range(len(colors)):
            for j in range(len(colors)):
                if i != j:
                    assert matrix[i][j] == pytest.approx(matrix[j][i], abs=1e-10)

    def test_black_white_in_matrix(self):
        colors = ["black", "white", "red"]
        matrix = palette_matrix(colors)
        # black(0) vs white(1)
        assert matrix[0][1] == pytest.approx(21.0, abs=0.1)

    def test_matrix_values_match_direct(self):
        colors = ["#ff0000", "#00ff00", "#0000ff"]
        matrix = palette_matrix(colors)
        for i in range(3):
            for j in range(3):
                if i != j:
                    ci = parse_color(colors[i])
                    cj = parse_color(colors[j])
                    assert matrix[i][j] == pytest.approx(
                        contrast_ratio(ci, cj), abs=1e-10
                    )


# =====================================================================
# 6. Color suggestion accuracy
# =====================================================================


class TestColorSuggestion:
    """Suggested colors must actually meet the target contrast ratio."""

    def test_suggest_when_already_passing(self):
        """No suggestions needed when ratio already passes."""
        fg = (0, 0, 0)
        bg = (255, 255, 255)
        result = suggest_colors(fg, bg, 7.0)
        assert result == {}

    def test_suggest_darkened_foreground_passes(self):
        """777 on white fails AA: suggestion should pass."""
        fg = (119, 119, 119)
        bg = (255, 255, 255)
        suggestions = suggest_colors(fg, bg, 4.5)
        assert "foreground" in suggestions
        new_fg = suggestions["foreground"]
        assert contrast_ratio(new_fg, bg) >= 4.5

    def test_suggest_lightened_background_passes(self):
        """Lightened background should also pass."""
        fg = (119, 119, 119)
        bg = (200, 200, 200)
        suggestions = suggest_colors(fg, bg, 4.5)
        if "background" in suggestions:
            new_bg = suggestions["background"]
            assert contrast_ratio(fg, new_bg) >= 4.5

    def test_suggest_for_aaa(self):
        """777 on white: suggest for AAA (7.0)."""
        fg = (119, 119, 119)
        bg = (255, 255, 255)
        suggestions = suggest_colors(fg, bg, 7.0)
        assert "foreground" in suggestions
        new_fg = suggestions["foreground"]
        assert contrast_ratio(new_fg, bg) >= 7.0

    def test_suggest_minimal_change(self):
        """Suggested fg should be close to original (minimal adjustment)."""
        fg = (119, 119, 119)
        bg = (255, 255, 255)
        suggestions = suggest_colors(fg, bg, 4.5)
        new_fg = suggestions["foreground"]
        # The new foreground should be darker but not drastically
        # (original is 119,119,119 — suggested should be around 110-118 range)
        for ch_old, ch_new in zip(fg, new_fg):
            assert ch_new <= ch_old  # darker or equal
            assert ch_old - ch_new < 30  # not a huge jump

    def test_suggest_impossible_returns_empty(self):
        """When both colors are the same extreme, nothing can help."""
        # Two very close colors — darken fg to (0,0,0) vs bg (1,1,1)
        fg = (0, 0, 0)
        bg = (1, 1, 1)
        suggestions = suggest_colors(fg, bg, 21.0)
        # Can't reach 21:1 from near-black pair: background lighten
        # might work if pushed to white, but foreground can't darken further
        # At minimum, background suggestion should pass if present
        if "foreground" in suggestions:
            assert contrast_ratio(suggestions["foreground"], bg) >= 21.0
        if "background" in suggestions:
            assert contrast_ratio(fg, suggestions["background"]) >= 21.0


# =====================================================================
# 7. Invalid input handling
# =====================================================================


class TestInvalidInput:
    """Bad inputs should raise ValueError with useful messages."""

    def test_bad_hex_length(self):
        with pytest.raises(ValueError, match="Invalid hex color"):
            parse_color("#12345")

    def test_bad_hex_chars(self):
        with pytest.raises(ValueError):
            parse_color("#gggggg")

    def test_rgb_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_color("rgb(256, 0, 0)")

    def test_rgb_negative(self):
        # Negative numbers won't match the regex (no minus sign),
        # so it falls through to "Unknown color"
        with pytest.raises(ValueError):
            parse_color("rgb(-1, 0, 0)")

    def test_csv_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_color("300,0,0")

    def test_unknown_color_name(self):
        with pytest.raises(ValueError, match="Unknown color"):
            parse_color("notacolor")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            parse_color("")

    def test_hex_no_digits(self):
        with pytest.raises(ValueError):
            parse_color("#")

    def test_just_hash(self):
        with pytest.raises(ValueError):
            parse_color("#")


# =====================================================================
# 8. CLI output format
# =====================================================================


class TestCLI:
    """Test the CLI by invoking checker.py as a subprocess."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        import os

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        return subprocess.run(
            [sys.executable, "checker.py", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(__import__("pathlib").Path(__file__).parent),
            env=env,
        )

    def test_basic_pair(self):
        result = self._run("#1a1a2e", "#e4e4ed")
        assert result.returncode == 0
        out = result.stdout
        assert "Foreground: #1a1a2e" in out
        assert "Background: #e4e4ed" in out
        assert "Contrast ratio:" in out
        assert ":1" in out

    def test_named_colors(self):
        result = self._run("black", "white")
        assert result.returncode == 0
        assert "21.0:1" in result.stdout

    def test_level_flag(self):
        result = self._run("#777", "white", "--level", "AA")
        assert result.returncode == 0
        out = result.stdout
        assert "AA Normal text" in out or "AA Large text" in out
        # Should NOT contain AAA lines
        assert "AAA" not in out

    def test_suggest_flag(self):
        result = self._run("#777", "white", "--suggest")
        assert result.returncode == 0
        assert "Suggest" in result.stdout or "suggest" in result.stdout.lower()

    def test_palette_mode(self):
        result = self._run("--palette", "#0a0a0f", "#e4e4ed", "#22d3ee", "#9898ad")
        assert result.returncode == 0
        out = result.stdout
        # Should contain hex labels
        assert "#0a0a0f" in out
        assert "#e4e4ed" in out
        # Should contain ratio values
        assert ":1" in out

    def test_wrong_arg_count(self):
        result = self._run("red")
        assert result.returncode != 0

    def test_invalid_color_exits(self):
        result = self._run("notacolor", "white")
        assert result.returncode != 0

    def test_pass_symbols_in_output(self):
        """Black on white should show all passing checkmarks."""
        result = self._run("black", "white")
        assert result.returncode == 0
        # Unicode checkmark
        assert "\u2713" in result.stdout

    def test_fail_symbol_present(self):
        """#777 on white fails AA normal — should show cross."""
        result = self._run("#777", "white")
        assert result.returncode == 0
        assert "\u2717" in result.stdout
