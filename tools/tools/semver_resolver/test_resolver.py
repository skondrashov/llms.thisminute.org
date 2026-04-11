"""
Tests for Semver Range Resolver.

These tests ARE the spec — if an LLM regenerates the resolver in any
language, these cases define correctness.
"""

import pytest
from pathlib import Path

_TOOL_DIR = str(Path(__file__).parent)

from resolver import (
    Version, VersionError, sort_versions,
    Bound, VersionRange, MIN_VERSION, MAX_VERSION,
    npm_parse_range, cargo_parse_range, pip_parse_range, maven_parse_range,
    check_version, find_overlap, translate_range,
    get_parser,
)


# ============================================================================
# 1. Version parsing and comparison
# ============================================================================


class TestVersionParsing:
    def test_parse_full(self):
        v = Version.parse("1.2.3")
        assert v.major == 1 and v.minor == 2 and v.patch == 3

    def test_parse_with_v_prefix(self):
        v = Version.parse("v1.2.3")
        assert v.major == 1

    def test_parse_zeros(self):
        v = Version.parse("0.0.0")
        assert v.major == 0 and v.minor == 0 and v.patch == 0

    def test_parse_prerelease(self):
        v = Version.parse("1.2.3-alpha.1")
        assert v.prerelease == ("alpha", "1")

    def test_parse_build_metadata(self):
        v = Version.parse("1.2.3+build.42")
        assert v.build == ("build", "42")

    def test_parse_partial_major_only(self):
        v = Version.parse("1")
        assert v.major == 1 and v.minor == 0 and v.patch == 0

    def test_parse_partial_major_minor(self):
        v = Version.parse("1.2")
        assert v.major == 1 and v.minor == 2 and v.patch == 0

    def test_parse_invalid_empty(self):
        with pytest.raises(VersionError):
            Version.parse("")

    def test_parse_invalid_letters(self):
        with pytest.raises(VersionError):
            Version.parse("abc")

    def test_parse_invalid_leading_zeros(self):
        with pytest.raises(VersionError):
            Version.parse("01.2.3")


class TestVersionComparison:
    def test_equal(self):
        assert Version.parse("1.2.3") == Version.parse("1.2.3")

    def test_equal_ignores_build(self):
        assert Version.parse("1.2.3+build1") == Version.parse("1.2.3+build2")

    def test_less_than_major(self):
        assert Version.parse("1.0.0") < Version.parse("2.0.0")

    def test_less_than_minor(self):
        assert Version.parse("1.0.0") < Version.parse("1.1.0")

    def test_less_than_patch(self):
        assert Version.parse("1.0.0") < Version.parse("1.0.1")

    def test_prerelease_less_than_release(self):
        assert Version.parse("1.0.0-alpha") < Version.parse("1.0.0")

    def test_prerelease_ordering(self):
        assert Version.parse("1.0.0-alpha") < Version.parse("1.0.0-beta")

    def test_prerelease_numeric_less_than_alpha(self):
        assert Version.parse("1.0.0-1") < Version.parse("1.0.0-alpha")

    def test_is_prerelease(self):
        assert Version.parse("1.0.0-alpha").is_prerelease
        assert not Version.parse("1.0.0").is_prerelease

    def test_is_stable(self):
        assert Version.parse("1.0.0").is_stable
        assert not Version.parse("0.1.0").is_stable
        assert not Version.parse("1.0.0-alpha").is_stable

    def test_str(self):
        assert str(Version.parse("1.2.3")) == "1.2.3"
        assert str(Version.parse("1.2.3-alpha.1")) == "1.2.3-alpha.1"


class TestVersionSorting:
    def test_sort_basic(self):
        versions = [Version.parse("2.0.0"), Version.parse("1.0.0"), Version.parse("3.0.0")]
        result = sort_versions(versions)
        assert result == [Version.parse("1.0.0"), Version.parse("2.0.0"), Version.parse("3.0.0")]

    def test_sort_with_prerelease(self):
        versions = [Version.parse("1.0.0"), Version.parse("1.0.0-alpha"), Version.parse("1.0.0-beta")]
        result = sort_versions(versions)
        assert result == [Version.parse("1.0.0-alpha"), Version.parse("1.0.0-beta"), Version.parse("1.0.0")]

    def test_hash_equal_versions(self):
        v1 = Version.parse("1.2.3")
        v2 = Version.parse("1.2.3")
        assert hash(v1) == hash(v2)

    def test_hash_in_set(self):
        s = {Version.parse("1.0.0"), Version.parse("1.0.0"), Version.parse("2.0.0")}
        assert len(s) == 2


# ============================================================================
# 2. npm ranges: caret, tilde, comparators, hyphen, X-range, OR
# ============================================================================


class TestNpmCaret:
    def test_caret_stable(self):
        vr = npm_parse_range("^1.2.3")
        assert vr.contains(Version.parse("1.2.3"))
        assert vr.contains(Version.parse("1.9.9"))
        assert not vr.contains(Version.parse("2.0.0"))
        assert not vr.contains(Version.parse("1.2.2"))

    def test_caret_zero_major(self):
        vr = npm_parse_range("^0.2.3")
        assert vr.contains(Version.parse("0.2.3"))
        assert vr.contains(Version.parse("0.2.9"))
        assert not vr.contains(Version.parse("0.3.0"))

    def test_caret_zero_minor(self):
        vr = npm_parse_range("^0.0.3")
        assert vr.contains(Version.parse("0.0.3"))
        assert not vr.contains(Version.parse("0.0.4"))

    def test_caret_partial(self):
        vr = npm_parse_range("^1.2")
        assert vr.contains(Version.parse("1.9.0"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_caret_zero(self):
        vr = npm_parse_range("^0")
        assert vr.contains(Version.parse("0.99.99"))
        assert not vr.contains(Version.parse("1.0.0"))


class TestNpmTilde:
    def test_tilde_full(self):
        vr = npm_parse_range("~1.2.3")
        assert vr.contains(Version.parse("1.2.3"))
        assert vr.contains(Version.parse("1.2.99"))
        assert not vr.contains(Version.parse("1.3.0"))

    def test_tilde_partial(self):
        vr = npm_parse_range("~1.2")
        assert vr.contains(Version.parse("1.2.0"))
        assert not vr.contains(Version.parse("1.3.0"))

    def test_tilde_major_only(self):
        vr = npm_parse_range("~1")
        assert vr.contains(Version.parse("1.99.99"))
        assert not vr.contains(Version.parse("2.0.0"))


class TestNpmComparators:
    def test_gte(self):
        vr = npm_parse_range(">=1.0.0")
        assert vr.contains(Version.parse("1.0.0"))
        assert not vr.contains(Version.parse("0.99.99"))

    def test_gt(self):
        vr = npm_parse_range(">1.0.0")
        assert not vr.contains(Version.parse("1.0.0"))
        assert vr.contains(Version.parse("1.0.1"))

    def test_lte(self):
        vr = npm_parse_range("<=2.0.0")
        assert vr.contains(Version.parse("2.0.0"))
        assert not vr.contains(Version.parse("2.0.1"))

    def test_lt(self):
        vr = npm_parse_range("<2.0.0")
        assert not vr.contains(Version.parse("2.0.0"))
        assert vr.contains(Version.parse("1.99.99"))

    def test_compound_gte_lt(self):
        vr = npm_parse_range(">=1.0.0 <2.0.0")
        assert vr.contains(Version.parse("1.0.0"))
        assert not vr.contains(Version.parse("2.0.0"))


class TestNpmHyphen:
    def test_full_hyphen(self):
        vr = npm_parse_range("1.2.3 - 2.3.4")
        assert vr.contains(Version.parse("1.2.3"))
        assert vr.contains(Version.parse("2.3.4"))
        assert not vr.contains(Version.parse("2.3.5"))

    def test_partial_upper(self):
        vr = npm_parse_range("1.2.3 - 2.3")
        assert vr.contains(Version.parse("2.3.99"))
        assert not vr.contains(Version.parse("2.4.0"))


class TestNpmXRanges:
    def test_star(self):
        vr = npm_parse_range("*")
        assert vr.contains(Version.parse("99.99.99"))

    def test_major_star(self):
        vr = npm_parse_range("1.*")
        assert vr.contains(Version.parse("1.99.99"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_major_minor_star(self):
        vr = npm_parse_range("1.2.*")
        assert vr.contains(Version.parse("1.2.99"))
        assert not vr.contains(Version.parse("1.3.0"))

    def test_partial_major_only(self):
        vr = npm_parse_range("1")
        assert vr.contains(Version.parse("1.99.99"))
        assert not vr.contains(Version.parse("2.0.0"))


class TestNpmOr:
    def test_simple_or(self):
        vr = npm_parse_range(">=1.0.0 <2.0.0 || >=3.0.0 <4.0.0")
        assert vr.contains(Version.parse("1.5.0"))
        assert vr.contains(Version.parse("3.5.0"))
        assert not vr.contains(Version.parse("2.5.0"))

    def test_caret_or(self):
        vr = npm_parse_range("^1.2.3 || ^2.0.0")
        assert vr.contains(Version.parse("1.5.0"))
        assert vr.contains(Version.parse("2.5.0"))
        assert not vr.contains(Version.parse("3.0.0"))


# ============================================================================
# 3. Cargo ranges
# ============================================================================


class TestCargoRanges:
    def test_bare_version_is_caret(self):
        vr = cargo_parse_range("1.2.3")
        assert vr.contains(Version.parse("1.2.3"))
        assert vr.contains(Version.parse("1.9.9"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_explicit_caret(self):
        vr = cargo_parse_range("^0.2.3")
        assert vr.contains(Version.parse("0.2.3"))
        assert not vr.contains(Version.parse("0.3.0"))

    def test_tilde(self):
        vr = cargo_parse_range("~1.2.3")
        assert vr.contains(Version.parse("1.2.5"))
        assert not vr.contains(Version.parse("1.3.0"))

    def test_comma_and(self):
        vr = cargo_parse_range(">=1.0, <3.0")
        assert vr.contains(Version.parse("2.0.0"))
        assert not vr.contains(Version.parse("3.0.0"))

    def test_wildcard(self):
        vr = cargo_parse_range("1.*")
        assert vr.contains(Version.parse("1.5.0"))
        assert not vr.contains(Version.parse("2.0.0"))


# ============================================================================
# 4. pip ranges (PEP 440)
# ============================================================================


class TestPipRanges:
    def test_compatible_release_3part(self):
        vr = pip_parse_range("~=1.4.2")
        assert vr.contains(Version.parse("1.4.2"))
        assert vr.contains(Version.parse("1.4.5"))
        assert not vr.contains(Version.parse("1.5.0"))

    def test_compatible_release_2part(self):
        vr = pip_parse_range("~=1.4")
        assert vr.contains(Version.parse("1.4.0"))
        assert vr.contains(Version.parse("1.99.0"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_exact_version(self):
        vr = pip_parse_range("==1.0.0")
        assert vr.contains(Version.parse("1.0.0"))
        assert not vr.contains(Version.parse("1.0.1"))

    def test_wildcard_equal(self):
        vr = pip_parse_range("==1.*")
        assert vr.contains(Version.parse("1.5.0"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_gte_lt_compound(self):
        vr = pip_parse_range(">=1.0,<2.0")
        assert vr.contains(Version.parse("1.5.0"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_exclusion(self):
        vr = pip_parse_range(">=1.0,!=1.5.0,<2.0")
        assert vr.contains(Version.parse("1.4.0"))
        assert not vr.contains(Version.parse("1.5.0"))
        assert vr.contains(Version.parse("1.6.0"))


# ============================================================================
# 5. Maven ranges (bracket notation)
# ============================================================================


class TestMavenRanges:
    def test_closed_open(self):
        vr = maven_parse_range("[1.0,2.0)")
        assert vr.contains(Version.parse("1.0.0"))
        assert vr.contains(Version.parse("1.5.0"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_exact_bracket(self):
        vr = maven_parse_range("[1.0]")
        assert vr.contains(Version.parse("1.0.0"))
        assert not vr.contains(Version.parse("1.0.1"))

    def test_open_closed(self):
        vr = maven_parse_range("(1.0,2.0]")
        assert not vr.contains(Version.parse("1.0.0"))
        assert vr.contains(Version.parse("2.0.0"))

    def test_unbounded_upper(self):
        vr = maven_parse_range("[1.0,)")
        assert vr.contains(Version.parse("1.0.0"))
        assert vr.contains(Version.parse("99.0.0"))

    def test_unbounded_lower(self):
        vr = maven_parse_range("(,2.0)")
        assert vr.contains(Version.parse("1.0.0"))
        assert not vr.contains(Version.parse("2.0.0"))

    def test_multi_range_union(self):
        vr = maven_parse_range("[1.0,2.0),[3.0,4.0)")
        assert vr.contains(Version.parse("1.5.0"))
        assert not vr.contains(Version.parse("2.5.0"))
        assert vr.contains(Version.parse("3.5.0"))

    def test_bare_version_exact(self):
        vr = maven_parse_range("1.5")
        assert vr.contains(Version.parse("1.5.0"))
        assert not vr.contains(Version.parse("1.5.1"))


# ============================================================================
# 6. Bound operations
# ============================================================================


class TestBound:
    def test_contains_inclusive_both(self):
        b = Bound(Version.parse("1.0.0"), Version.parse("2.0.0"), True, True)
        assert b.contains(Version.parse("1.0.0"))
        assert b.contains(Version.parse("2.0.0"))
        assert not b.contains(Version.parse("2.0.1"))

    def test_contains_exclusive_both(self):
        b = Bound(Version.parse("1.0.0"), Version.parse("2.0.0"), False, False)
        assert not b.contains(Version.parse("1.0.0"))
        assert not b.contains(Version.parse("2.0.0"))
        assert b.contains(Version.parse("1.5.0"))

    def test_is_empty_inverted(self):
        b = Bound(Version.parse("2.0.0"), Version.parse("1.0.0"), True, False)
        assert b.is_empty()

    def test_intersect_overlapping(self):
        b1 = Bound(Version.parse("1.0.0"), Version.parse("3.0.0"), True, False)
        b2 = Bound(Version.parse("2.0.0"), Version.parse("4.0.0"), True, False)
        result = b1.intersect(b2)
        assert result is not None
        assert result.lower == Version.parse("2.0.0")
        assert result.upper == Version.parse("3.0.0")

    def test_intersect_non_overlapping(self):
        b1 = Bound(Version.parse("1.0.0"), Version.parse("2.0.0"), True, False)
        b2 = Bound(Version.parse("3.0.0"), Version.parse("4.0.0"), True, False)
        assert b1.intersect(b2) is None

    def test_overlaps(self):
        b1 = Bound(Version.parse("1.0.0"), Version.parse("3.0.0"), True, False)
        b2 = Bound(Version.parse("2.0.0"), Version.parse("4.0.0"), True, False)
        assert b1.overlaps(b2)

    def test_str(self):
        b = Bound(Version.parse("1.0.0"), Version.parse("2.0.0"), True, False)
        assert str(b) == "[1.0.0, 2.0.0)"


# ============================================================================
# 7. Overlap detection
# ============================================================================


class TestOverlap:
    def test_npm_overlap(self):
        result = find_overlap("^1.2", "~1.5", "npm")
        assert result is not None
        assert result.contains(Version.parse("1.5.0"))
        assert not result.contains(Version.parse("1.6.0"))

    def test_npm_no_overlap(self):
        result = find_overlap("^1.0.0", "^2.0.0", "npm")
        assert result is None

    def test_cargo_overlap(self):
        result = find_overlap(">=1.0, <3.0", ">=2.0, <4.0", "cargo")
        assert result is not None
        assert result.contains(Version.parse("2.5.0"))

    def test_pip_overlap(self):
        result = find_overlap(">=1.0,<3.0", ">=2.0,<4.0", "pip")
        assert result is not None
        assert result.contains(Version.parse("2.5.0"))

    def test_maven_overlap(self):
        result = find_overlap("[1.0,3.0)", "[2.0,4.0)", "maven")
        assert result is not None
        assert result.contains(Version.parse("2.5.0"))


# ============================================================================
# 8. Cross-ecosystem translation
# ============================================================================


class TestTranslation:
    def test_npm_to_cargo_caret(self):
        result = translate_range("^1.2.3", "npm", "cargo")
        assert result["translated"] == "^1.2.3"
        assert result["exact"]

    def test_npm_to_maven_caret(self):
        result = translate_range("^1.2.3", "npm", "maven")
        assert "[1.2.3,2.0.0)" in result["translated"]

    def test_cargo_to_npm_caret(self):
        result = translate_range("^1.2.3", "cargo", "npm")
        assert result["translated"] == "^1.2.3"

    def test_npm_to_pip_tilde(self):
        result = translate_range("~1.2.3", "npm", "pip")
        assert "1.2.3" in result["translated"]

    def test_pip_to_cargo(self):
        result = translate_range("~=1.4.2", "pip", "cargo")
        assert "1.4.2" in result["translated"]

    def test_maven_to_npm(self):
        result = translate_range("[1.0,2.0)", "maven", "npm")
        assert "1.0.0" in result["translated"]

    def test_translate_preserves_metadata(self):
        result = translate_range("^1.0.0", "npm", "cargo")
        assert result["source_ecosystem"] == "npm"
        assert result["target_ecosystem"] == "cargo"
        assert result["original"] == "^1.0.0"

    def test_star_to_maven(self):
        result = translate_range("*", "npm", "maven")
        assert result["translated"] is not None

    def test_npm_caret_to_pip_exact(self):
        """npm ^1.2.3 -> pip must produce >=1.2.3,<2.0.0, not ~=1.2 (lossy)."""
        result = translate_range("^1.2.3", "npm", "pip")
        assert result["translated"] == ">=1.2.3,<2.0.0"
        assert result["exact"]

    def test_npm_caret_to_pip_minor_nonzero(self):
        """npm ^1.4.0 -> pip must be >=1.4.0,<2.0.0 (not ~=1.4)."""
        result = translate_range("^1.4.0", "npm", "pip")
        assert result["translated"] == ">=1.4.0,<2.0.0"
        assert result["exact"]

    def test_npm_caret_to_pip_major_zero(self):
        """npm ^1.0.0 -> pip must be >=1.0.0,<2.0.0."""
        result = translate_range("^1.0.0", "npm", "pip")
        assert result["translated"] == ">=1.0.0,<2.0.0"
        assert result["exact"]

    def test_npm_tilde_to_pip_exact(self):
        """npm ~1.2.3 -> pip ~=1.2.3 (tilde maps directly)."""
        result = translate_range("~1.2.3", "npm", "pip")
        assert result["translated"] == "~=1.2.3"
        assert result["exact"]

    def test_npm_tilde_to_pip_zero_patch(self):
        """npm ~1.2.0 -> pip ~=1.2 (when patch=0, use 2-part form)."""
        result = translate_range("~1.2.0", "npm", "pip")
        assert result["translated"] == "~=1.2"
        assert result["exact"]

    def test_cargo_caret_to_pip(self):
        """Cargo ^2.1.5 -> pip >=2.1.5,<3.0.0."""
        result = translate_range("^2.1.5", "cargo", "pip")
        assert result["translated"] == ">=2.1.5,<3.0.0"
        assert result["exact"]


# ============================================================================
# 9. check_version convenience
# ============================================================================


class TestCheckVersion:
    def test_npm_caret_match(self):
        assert check_version("^1.2.3", "1.5.0", "npm")

    def test_npm_caret_no_match(self):
        assert not check_version("^1.2.3", "2.0.0", "npm")

    def test_cargo_tilde_match(self):
        assert check_version("~1.2.3", "1.2.5", "cargo")

    def test_cargo_tilde_no_match(self):
        assert not check_version("~1.2.3", "1.3.0", "cargo")

    def test_pip_compatible_match(self):
        assert check_version("~=1.4.2", "1.4.5", "pip")

    def test_pip_compatible_no_match(self):
        assert not check_version("~=1.4.2", "1.5.0", "pip")

    def test_maven_range_match(self):
        assert check_version("[1.0,2.0)", "1.5.0", "maven")

    def test_maven_range_no_match(self):
        assert not check_version("[1.0,2.0)", "2.0.0", "maven")


# ============================================================================
# 10. Edge cases
# ============================================================================


class TestEdgeCases:
    def test_impossible_npm_range(self):
        vr = npm_parse_range(">=2.0.0 <1.0.0")
        assert vr.is_empty()

    def test_empty_version_range_str(self):
        vr = VersionRange(bounds=[])
        assert str(vr) == "<empty>"

    def test_unknown_ecosystem(self):
        with pytest.raises(ValueError, match="Unknown ecosystem"):
            get_parser("unknown")

    def test_version_bump_major(self):
        assert Version.parse("1.2.3").bump_major() == Version.parse("2.0.0")

    def test_version_bump_minor(self):
        assert Version.parse("1.2.3").bump_minor() == Version.parse("1.3.0")

    def test_version_bump_patch(self):
        assert Version.parse("1.2.3").bump_patch() == Version.parse("1.2.4")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
