"""
WCAG 2.1 Color Contrast Checker

Verifies that foreground/background color pairs meet WCAG 2.1 contrast
requirements. Parses hex, rgb(), bare-CSV, and CSS named colors. Calculates
relative luminance using the precise sRGB linearization specified in WCAG 2.1,
then derives contrast ratios and evaluates against AA/AAA thresholds for
normal text, large text, and UI components.

Palette mode checks every ordered pair in a list of colors and prints a matrix.
Suggestion mode proposes the minimal adjustment to reach a target level.

Usage:
    python checker.py <foreground> <background>
    python checker.py <foreground> <background> --level AA
    python checker.py <foreground> <background> --suggest
    python checker.py --palette <color1> <color2> <color3> ...
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# CSS named colors (the 17 original + extended set covering the 148 CSS4 names)
# ---------------------------------------------------------------------------

NAMED_COLORS: Dict[str, Tuple[int, int, int]] = {
    "aliceblue": (240, 248, 255),
    "antiquewhite": (250, 235, 215),
    "aqua": (0, 255, 255),
    "aquamarine": (127, 255, 212),
    "azure": (240, 255, 255),
    "beige": (245, 245, 220),
    "bisque": (255, 228, 196),
    "black": (0, 0, 0),
    "blanchedalmond": (255, 235, 205),
    "blue": (0, 0, 255),
    "blueviolet": (138, 43, 226),
    "brown": (165, 42, 42),
    "burlywood": (222, 184, 135),
    "cadetblue": (95, 158, 160),
    "chartreuse": (127, 255, 0),
    "chocolate": (210, 105, 30),
    "coral": (255, 127, 80),
    "cornflowerblue": (100, 149, 237),
    "cornsilk": (255, 248, 220),
    "crimson": (220, 20, 60),
    "cyan": (0, 255, 255),
    "darkblue": (0, 0, 139),
    "darkcyan": (0, 139, 139),
    "darkgoldenrod": (184, 134, 11),
    "darkgray": (169, 169, 169),
    "darkgreen": (0, 100, 0),
    "darkgrey": (169, 169, 169),
    "darkkhaki": (189, 183, 107),
    "darkmagenta": (139, 0, 139),
    "darkolivegreen": (85, 107, 47),
    "darkorange": (255, 140, 0),
    "darkorchid": (153, 50, 204),
    "darkred": (139, 0, 0),
    "darksalmon": (233, 150, 122),
    "darkseagreen": (143, 188, 143),
    "darkslateblue": (72, 61, 139),
    "darkslategray": (47, 79, 79),
    "darkslategrey": (47, 79, 79),
    "darkturquoise": (0, 206, 209),
    "darkviolet": (148, 0, 211),
    "deeppink": (255, 20, 147),
    "deepskyblue": (0, 191, 255),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
    "dodgerblue": (30, 144, 255),
    "firebrick": (178, 34, 34),
    "floralwhite": (255, 250, 240),
    "forestgreen": (34, 139, 34),
    "fuchsia": (255, 0, 255),
    "gainsboro": (220, 220, 220),
    "ghostwhite": (248, 248, 255),
    "gold": (255, 215, 0),
    "goldenrod": (218, 165, 32),
    "gray": (128, 128, 128),
    "green": (0, 128, 0),
    "greenyellow": (173, 255, 47),
    "grey": (128, 128, 128),
    "honeydew": (240, 255, 240),
    "hotpink": (255, 105, 180),
    "indianred": (205, 92, 92),
    "indigo": (75, 0, 130),
    "ivory": (255, 255, 240),
    "khaki": (240, 230, 140),
    "lavender": (230, 230, 250),
    "lavenderblush": (255, 240, 245),
    "lawngreen": (124, 252, 0),
    "lemonchiffon": (255, 250, 205),
    "lightblue": (173, 216, 230),
    "lightcoral": (240, 128, 128),
    "lightcyan": (224, 255, 255),
    "lightgoldenrodyellow": (250, 250, 210),
    "lightgray": (211, 211, 211),
    "lightgreen": (144, 238, 144),
    "lightgrey": (211, 211, 211),
    "lightpink": (255, 182, 193),
    "lightsalmon": (255, 160, 122),
    "lightseagreen": (32, 178, 170),
    "lightskyblue": (135, 206, 250),
    "lightslategray": (119, 136, 153),
    "lightslategrey": (119, 136, 153),
    "lightsteelblue": (176, 196, 222),
    "lightyellow": (255, 255, 224),
    "lime": (0, 255, 0),
    "limegreen": (50, 205, 50),
    "linen": (250, 240, 230),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "mediumaquamarine": (102, 205, 170),
    "mediumblue": (0, 0, 205),
    "mediumorchid": (186, 85, 211),
    "mediumpurple": (147, 111, 219),
    "mediumseagreen": (60, 179, 113),
    "mediumslateblue": (123, 104, 238),
    "mediumspringgreen": (0, 250, 154),
    "mediumturquoise": (72, 209, 204),
    "mediumvioletred": (199, 21, 133),
    "midnightblue": (25, 25, 112),
    "mintcream": (245, 255, 250),
    "mistyrose": (255, 228, 225),
    "moccasin": (255, 228, 181),
    "navajowhite": (255, 222, 173),
    "navy": (0, 0, 128),
    "oldlace": (253, 245, 230),
    "olive": (128, 128, 0),
    "olivedrab": (107, 142, 35),
    "orange": (255, 165, 0),
    "orangered": (255, 69, 0),
    "orchid": (218, 112, 214),
    "palegoldenrod": (238, 232, 170),
    "palegreen": (152, 251, 152),
    "paleturquoise": (175, 238, 238),
    "palevioletred": (219, 112, 147),
    "papayawhip": (255, 239, 213),
    "peachpuff": (255, 218, 185),
    "peru": (205, 133, 63),
    "pink": (255, 192, 203),
    "plum": (221, 160, 221),
    "powderblue": (176, 224, 230),
    "purple": (128, 0, 128),
    "rebeccapurple": (102, 51, 153),
    "red": (255, 0, 0),
    "rosybrown": (188, 143, 143),
    "royalblue": (65, 105, 225),
    "saddlebrown": (139, 69, 19),
    "salmon": (250, 128, 114),
    "sandybrown": (244, 164, 96),
    "seagreen": (46, 139, 87),
    "seashell": (255, 245, 238),
    "sienna": (160, 82, 45),
    "silver": (192, 192, 192),
    "skyblue": (135, 206, 235),
    "slateblue": (106, 90, 205),
    "slategray": (112, 128, 144),
    "slategrey": (112, 128, 144),
    "snow": (255, 250, 250),
    "springgreen": (0, 255, 127),
    "steelblue": (70, 130, 180),
    "tan": (210, 180, 140),
    "teal": (0, 128, 128),
    "thistle": (216, 191, 216),
    "tomato": (255, 99, 71),
    "turquoise": (64, 224, 208),
    "violet": (238, 130, 238),
    "wheat": (245, 222, 179),
    "white": (255, 255, 255),
    "whitesmoke": (245, 245, 245),
    "yellow": (255, 255, 0),
    "yellowgreen": (154, 205, 50),
}

# ---------------------------------------------------------------------------
# WCAG thresholds
# ---------------------------------------------------------------------------

WCAG_LEVELS: Dict[str, float] = {
    "AAA Normal text": 7.0,
    "AA Normal text": 4.5,
    "AAA Large text": 4.5,
    "AA Large text": 3.0,
    "AA UI components": 3.0,
}

# Short aliases accepted by --level
_LEVEL_ALIAS: Dict[str, List[str]] = {
    "AAA": ["AAA Normal text", "AAA Large text"],
    "AA": ["AA Normal text", "AA Large text", "AA UI components"],
}

# ---------------------------------------------------------------------------
# Color parsing
# ---------------------------------------------------------------------------


def parse_color(raw: str) -> Tuple[int, int, int]:
    """Parse a color string into an (R, G, B) tuple with values 0-255.

    Supported formats:
        #fff  /  #FFF            (3-digit hex)
        #ffffff  /  #FFFFFF      (6-digit hex)
        rgb(255, 255, 255)       (CSS rgb() function)
        255,255,255              (bare CSV)
        white                    (CSS named color)

    Raises ``ValueError`` on invalid input.
    """
    s = raw.strip()

    # --- hex ---------------------------------------------------------------
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            r, g, b = int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16)
            return (r, g, b)
        if len(h) == 6:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return (r, g, b)
        raise ValueError(f"Invalid hex color: {raw}")

    # --- rgb() -------------------------------------------------------------
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", s, re.IGNORECASE)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
            raise ValueError(f"RGB values out of range: {raw}")
        return (r, g, b)

    # --- bare CSV ----------------------------------------------------------
    m = re.match(r"(\d+)\s*,\s*(\d+)\s*,\s*(\d+)$", s)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
            raise ValueError(f"RGB values out of range: {raw}")
        return (r, g, b)

    # --- named color -------------------------------------------------------
    name = s.lower()
    if name in NAMED_COLORS:
        return NAMED_COLORS[name]

    raise ValueError(f"Unknown color: {raw}")


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Return ``#rrggbb`` for an (R, G, B) tuple."""
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# WCAG luminance & contrast
# ---------------------------------------------------------------------------


def _linearize(v: int) -> float:
    """Convert an 8-bit sRGB channel value to linear light per WCAG 2.1."""
    s = v / 255.0
    if s <= 0.04045:
        return s / 12.92
    return ((s + 0.055) / 1.055) ** 2.4


def relative_luminance(r: int, g: int, b: int) -> float:
    """Relative luminance of an sRGB color, per WCAG 2.1 definition."""
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def contrast_ratio(color1: Tuple[int, int, int], color2: Tuple[int, int, int]) -> float:
    """WCAG contrast ratio between two sRGB colors (always >= 1.0)."""
    l1 = relative_luminance(*color1)
    l2 = relative_luminance(*color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ---------------------------------------------------------------------------
# WCAG evaluation
# ---------------------------------------------------------------------------


def evaluate_wcag(ratio: float, levels: Optional[List[str]] = None) -> Dict[str, bool]:
    """Evaluate a contrast ratio against WCAG thresholds.

    Returns a dict mapping level names to pass/fail booleans.
    If *levels* is provided, only those levels are checked; otherwise all are.
    """
    if levels is None:
        levels = list(WCAG_LEVELS.keys())
    return {name: ratio >= WCAG_LEVELS[name] for name in levels if name in WCAG_LEVELS}


# ---------------------------------------------------------------------------
# Color suggestion
# ---------------------------------------------------------------------------


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def suggest_colors(
    fg: Tuple[int, int, int],
    bg: Tuple[int, int, int],
    target_ratio: float,
) -> Dict[str, Tuple[int, int, int]]:
    """Suggest minimal adjustments so that fg/bg reach *target_ratio*.

    Strategy: try darkening the foreground first, then lightening the
    background.  Each adjustment moves along the luminance axis uniformly
    (scales all channels toward 0 or 255).

    Returns a dict with keys ``"foreground"`` and/or ``"background"`` mapping
    to suggested (R, G, B) tuples.  A key is omitted when no change is needed
    on that side, or when no solution was found within the sRGB gamut.
    """
    current = contrast_ratio(fg, bg)
    if current >= target_ratio:
        return {}

    suggestions: Dict[str, Tuple[int, int, int]] = {}

    # --- darken foreground -------------------------------------------------
    best_fg = _adjust_towards(fg, bg, target_ratio, darken=True)
    if best_fg is not None:
        suggestions["foreground"] = best_fg

    # --- lighten background ------------------------------------------------
    best_bg = _adjust_towards(bg, fg, target_ratio, darken=False)
    if best_bg is not None:
        suggestions["background"] = best_bg

    return suggestions


def _adjust_towards(
    color: Tuple[int, int, int],
    other: Tuple[int, int, int],
    target_ratio: float,
    darken: bool,
) -> Optional[Tuple[int, int, int]]:
    """Binary-search for the minimal channel scale that achieves *target_ratio*.

    When *darken* is True, channels are scaled toward 0; otherwise toward 255.
    """
    lo, hi = 0.0, 1.0  # interpolation parameter

    def _interp(t: float) -> Tuple[int, int, int]:
        if darken:
            return (
                _clamp(round(color[0] * (1 - t))),
                _clamp(round(color[1] * (1 - t))),
                _clamp(round(color[2] * (1 - t))),
            )
        else:
            return (
                _clamp(round(color[0] + (255 - color[0]) * t)),
                _clamp(round(color[1] + (255 - color[1]) * t)),
                _clamp(round(color[2] + (255 - color[2]) * t)),
            )

    # Check if extreme is achievable
    extreme = _interp(1.0)
    if darken:
        ratio_at_extreme = contrast_ratio(extreme, other)
    else:
        ratio_at_extreme = contrast_ratio(other, extreme)
    if ratio_at_extreme < target_ratio:
        return None  # not possible within gamut

    for _ in range(64):  # plenty of precision
        mid = (lo + hi) / 2
        candidate = _interp(mid)
        if darken:
            r = contrast_ratio(candidate, other)
        else:
            r = contrast_ratio(other, candidate)
        if r >= target_ratio:
            hi = mid
        else:
            lo = mid

    result = _interp(hi)
    # Final verification
    if darken:
        if contrast_ratio(result, other) >= target_ratio:
            return result
    else:
        if contrast_ratio(other, result) >= target_ratio:
            return result
    return None


# ---------------------------------------------------------------------------
# Palette matrix
# ---------------------------------------------------------------------------


def palette_matrix(
    colors: List[str],
) -> List[List[Optional[float]]]:
    """Compute a contrast-ratio matrix for every ordered (fg, bg) pair.

    Returns a list-of-lists where ``matrix[i][j]`` is the contrast ratio of
    ``colors[i]`` (foreground) on ``colors[j]`` (background), or ``None`` on
    the diagonal.
    """
    parsed = [parse_color(c) for c in colors]
    n = len(parsed)
    matrix: List[List[Optional[float]]] = []
    for i in range(n):
        row: List[Optional[float]] = []
        for j in range(n):
            if i == j:
                row.append(None)
            else:
                row.append(contrast_ratio(parsed[i], parsed[j]))
        matrix.append(row)
    return matrix


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------


def _format_ratio(ratio: float) -> str:
    """Format a contrast ratio like ``4.5:1``."""
    if ratio >= 10:
        return f"{ratio:.1f}:1"
    return f"{ratio:.2f}:1"


def _pass_symbol(passed: bool) -> str:
    return "\u2713" if passed else "\u2717"


def _format_check_line(name: str, threshold: float, passed: bool) -> str:
    sym = _pass_symbol(passed)
    # Pad name to align thresholds
    return f"{sym} WCAG {name:<20s}(\u2265 {threshold:.1f}:1)"


def print_pair_report(
    fg_raw: str,
    bg_raw: str,
    levels: Optional[List[str]] = None,
    suggest: bool = False,
) -> None:
    """Print a full report for one foreground/background pair."""
    fg = parse_color(fg_raw)
    bg = parse_color(bg_raw)
    ratio = contrast_ratio(fg, bg)

    print(f"Foreground: {rgb_to_hex(*fg)} (rgb {fg[0]}, {fg[1]}, {fg[2]})")
    print(f"Background: {rgb_to_hex(*bg)} (rgb {bg[0]}, {bg[1]}, {bg[2]})")
    print(f"Contrast ratio: {_format_ratio(ratio)}")
    print()

    results = evaluate_wcag(ratio, levels)
    for name, passed in results.items():
        print(_format_check_line(name, WCAG_LEVELS[name], passed))

    if suggest:
        # Determine target: highest failing threshold
        failing = [
            WCAG_LEVELS[name] for name, passed in results.items() if not passed
        ]
        if failing:
            target = max(failing)
            suggestions = suggest_colors(fg, bg, target)
            print()
            print(f"Suggestions to reach {_format_ratio(target)}:")
            if "foreground" in suggestions:
                sf = suggestions["foreground"]
                print(f"  Darken foreground to {rgb_to_hex(*sf)} (rgb {sf[0]}, {sf[1]}, {sf[2]})")
            if "background" in suggestions:
                sb = suggestions["background"]
                print(f"  Lighten background to {rgb_to_hex(*sb)} (rgb {sb[0]}, {sb[1]}, {sb[2]})")
            if not suggestions:
                print("  No suggestion found within sRGB gamut.")
        else:
            print()
            print("All checked levels pass — no suggestions needed.")


def print_palette_report(color_args: List[str]) -> None:
    """Print the contrast matrix for a palette of 3+ colors."""
    if len(color_args) < 3:
        print("Palette mode requires at least 3 colors.", file=sys.stderr)
        sys.exit(1)

    parsed = [parse_color(c) for c in color_args]
    labels = [rgb_to_hex(*p) for p in parsed]
    matrix = palette_matrix(color_args)
    n = len(labels)

    # Column width
    cw = 12

    # Header row
    header = " " * cw + "".join(lab.ljust(cw) for lab in labels)
    print(header)

    for i in range(n):
        row_parts = [labels[i].ljust(cw)]
        for j in range(n):
            if matrix[i][j] is None:
                cell = "---"
            else:
                ratio = matrix[i][j]
                results = evaluate_wcag(ratio)
                if results.get("AAA Normal text"):
                    grade = "AAA"
                elif results.get("AA Normal text"):
                    grade = "AA"
                elif results.get("AA Large text"):
                    grade = "AA-lg"
                else:
                    grade = "FAIL"
                cell = f"{_format_ratio(ratio)} {grade}"
            row_parts.append(cell.ljust(cw))
        print("".join(row_parts))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="WCAG 2.1 Color Contrast Checker",
    )
    parser.add_argument(
        "colors",
        nargs="*",
        help="Foreground and background colors (2 args), or use --palette for 3+.",
    )
    parser.add_argument(
        "--palette",
        nargs="+",
        metavar="COLOR",
        help="Check all pairs in a palette of 3+ colors.",
    )
    parser.add_argument(
        "--level",
        choices=["AA", "AAA"],
        default=None,
        help="Check only AA or AAA levels.",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Suggest nearest passing colors when a pair fails.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.palette:
        print_palette_report(args.palette)
        return

    if len(args.colors) != 2:
        parser.error("Provide exactly 2 colors (foreground and background), or use --palette.")

    levels: Optional[List[str]] = None
    if args.level:
        levels = _LEVEL_ALIAS.get(args.level)

    print_pair_report(args.colors[0], args.colors[1], levels=levels, suggest=args.suggest)


if __name__ == "__main__":
    main()
