"""
Tests for the SPDX License Compatibility Checker.

These test cases define the behavioral contract. If the checker is ported
to another language, these cases are the spec it must satisfy.
"""

import pytest
from checker import (
    LicenseType, classify, check_compatibility, compatibility_matrix,
    LICENSE_DB, main,
)


# ===================================================================
# 1. License classification — each license maps to the correct type
# ===================================================================

class TestClassification:
    @pytest.mark.parametrize("spdx_id,expected_type", [
        ("MIT",           LicenseType.PERMISSIVE),
        ("ISC",           LicenseType.PERMISSIVE),
        ("0BSD",          LicenseType.PERMISSIVE),
        ("BSD-2-Clause",  LicenseType.PERMISSIVE),
        ("BSD-3-Clause",  LicenseType.PERMISSIVE),
        ("Zlib",          LicenseType.PERMISSIVE),
        ("PostgreSQL",    LicenseType.PERMISSIVE),
        ("BSL-1.0",       LicenseType.PERMISSIVE),
        ("Artistic-2.0",  LicenseType.PERMISSIVE),
        ("Apache-2.0",    LicenseType.PERMISSIVE_PATENT),
        ("Unlicense",     LicenseType.PUBLIC_DOMAIN),
        ("CC0-1.0",       LicenseType.PUBLIC_DOMAIN),
        ("CC-BY-4.0",     LicenseType.CREATIVE_COMMONS),
        ("CC-BY-SA-4.0",  LicenseType.CC_COPYLEFT),
        ("LGPL-2.1-only",     LicenseType.WEAK_COPYLEFT),
        ("LGPL-2.1-or-later", LicenseType.WEAK_COPYLEFT),
        ("LGPL-3.0-only",     LicenseType.WEAK_COPYLEFT),
        ("LGPL-3.0-or-later", LicenseType.WEAK_COPYLEFT),
        ("MPL-2.0",       LicenseType.WEAK_COPYLEFT),
        ("EPL-2.0",       LicenseType.WEAK_COPYLEFT),
        ("GPL-2.0-only",      LicenseType.STRONG_COPYLEFT),
        ("GPL-2.0-or-later",  LicenseType.STRONG_COPYLEFT),
        ("GPL-3.0-only",      LicenseType.STRONG_COPYLEFT),
        ("GPL-3.0-or-later",  LicenseType.STRONG_COPYLEFT),
        ("AGPL-3.0-only",     LicenseType.NETWORK_COPYLEFT),
        ("AGPL-3.0-or-later", LicenseType.NETWORK_COPYLEFT),
    ])
    def test_license_type(self, spdx_id, expected_type):
        info = classify(spdx_id)
        assert info is not None, f"{spdx_id} should be in database"
        assert info.license_type == expected_type

    @pytest.mark.parametrize("spdx_id", [
        "GPL-2.0-or-later", "GPL-3.0-or-later",
        "LGPL-2.1-or-later", "LGPL-3.0-or-later",
        "AGPL-3.0-or-later",
    ])
    def test_or_later_flag(self, spdx_id):
        info = classify(spdx_id)
        assert info is not None
        assert info.or_later is True

    @pytest.mark.parametrize("spdx_id", [
        "MIT", "GPL-2.0-only", "GPL-3.0-only", "Apache-2.0",
    ])
    def test_not_or_later(self, spdx_id):
        info = classify(spdx_id)
        assert info is not None
        assert info.or_later is False

    def test_all_licenses_have_required_fields(self):
        for spdx_id, info in LICENSE_DB.items():
            assert info.spdx_id == spdx_id
            assert len(info.name) > 0
            assert isinstance(info.license_type, LicenseType)
            assert len(info.family) > 0


# ===================================================================
# 2. Known compatible pairs
# ===================================================================

class TestCompatiblePairs:
    @pytest.mark.parametrize("a,b", [
        ("MIT", "Apache-2.0"),
        ("MIT", "BSD-2-Clause"),
        ("MIT", "ISC"),
        ("MIT", "0BSD"),
        ("MIT", "Unlicense"),
        ("BSD-3-Clause", "Apache-2.0"),
        ("CC0-1.0", "MIT"),
        ("MIT", "Zlib"),
        ("BSL-1.0", "MIT"),
    ])
    def test_permissive_pairs_compatible(self, a, b):
        result = check_compatibility(a, b)
        assert result.compatible is True
        assert result.a_can_include_b is True
        assert result.b_can_include_a is True

    @pytest.mark.parametrize("a,b", [
        ("MIT", "GPL-3.0-only"),
        ("BSD-2-Clause", "GPL-3.0-only"),
        ("ISC", "GPL-2.0-only"),
        ("Apache-2.0", "GPL-3.0-only"),
    ])
    def test_permissive_into_gpl(self, a, b):
        """GPL project CAN include permissive code."""
        result = check_compatibility(a, b)
        assert result.compatible is True
        assert result.b_can_include_a is True  # GPL project includes permissive

    def test_apache2_gpl3_compatible(self):
        """Apache-2.0 and GPL-3.0 are compatible (resolved patent clause issue)."""
        result = check_compatibility("Apache-2.0", "GPL-3.0-only")
        assert result.compatible is True

    def test_gpl3_agpl3_compatible(self):
        """GPL-3.0 and AGPL-3.0 can be combined."""
        result = check_compatibility("GPL-3.0-only", "AGPL-3.0-only")
        assert result.compatible is True

    def test_gpl2_or_later_gpl3(self):
        """GPL-2.0-or-later bridges to GPL-3.0."""
        result = check_compatibility("GPL-2.0-or-later", "GPL-3.0-only")
        assert result.compatible is True

    def test_same_license(self):
        result = check_compatibility("MIT", "MIT")
        assert result.compatible is True
        assert result.a_can_include_b is True
        assert result.b_can_include_a is True


# ===================================================================
# 3. Known incompatible pairs
# ===================================================================

class TestIncompatiblePairs:
    def test_apache2_gpl2_incompatible(self):
        """The famous Apache-2.0 / GPL-2.0 patent clause conflict."""
        result = check_compatibility("Apache-2.0", "GPL-2.0-only")
        assert result.compatible is False

    def test_gpl2_only_gpl3_only_incompatible(self):
        """GPL-2.0-only and GPL-3.0-only are NOT compatible."""
        result = check_compatibility("GPL-2.0-only", "GPL-3.0-only")
        assert result.compatible is False

    def test_gpl2_agpl3_incompatible(self):
        """AGPL-3.0 is not compatible with GPL-2.0."""
        result = check_compatibility("GPL-2.0-only", "AGPL-3.0-only")
        assert result.compatible is False

    def test_cc_by_sa_not_with_mit(self):
        """CC-BY-SA share-alike cannot be included in an MIT project and vice versa."""
        result = check_compatibility("MIT", "CC-BY-SA-4.0")
        assert result.a_can_include_b is False


# ===================================================================
# 4. Directionality
# ===================================================================

class TestDirectionality:
    def test_gpl_can_include_mit(self):
        """GPL project CAN include MIT code."""
        result = check_compatibility("GPL-3.0-only", "MIT")
        assert result.a_can_include_b is True

    def test_mit_cannot_include_gpl(self):
        """MIT project CANNOT include GPL code without relicensing."""
        result = check_compatibility("MIT", "GPL-3.0-only")
        assert result.a_can_include_b is False

    def test_gpl3_can_include_lgpl3(self):
        result = check_compatibility("GPL-3.0-only", "LGPL-3.0-only")
        assert result.a_can_include_b is True

    def test_mit_can_include_lgpl_as_library(self):
        """MIT project can include LGPL as a dynamically-linked library."""
        result = check_compatibility("MIT", "LGPL-3.0-only")
        assert result.a_can_include_b is True

    def test_agpl_can_include_gpl3(self):
        result = check_compatibility("AGPL-3.0-only", "GPL-3.0-only")
        assert result.a_can_include_b is True

    def test_gpl3_can_include_agpl3(self):
        """Per GPLv3 section 13, GPL-3.0 can include AGPL-3.0 code."""
        result = check_compatibility("GPL-3.0-only", "AGPL-3.0-only")
        assert result.a_can_include_b is True

    def test_permissive_cannot_include_agpl(self):
        result = check_compatibility("MIT", "AGPL-3.0-only")
        assert result.a_can_include_b is False

    def test_gpl2_cannot_include_agpl3(self):
        result = check_compatibility("GPL-2.0-only", "AGPL-3.0-only")
        assert result.a_can_include_b is False

    def test_apache2_into_gpl2_blocked(self):
        """GPL-2.0-only project CANNOT include Apache-2.0 (patent conflict)."""
        result = check_compatibility("GPL-2.0-only", "Apache-2.0")
        assert result.a_can_include_b is False

    def test_gpl3_can_include_apache2(self):
        """GPL-3.0 project CAN include Apache-2.0 code."""
        result = check_compatibility("GPL-3.0-only", "Apache-2.0")
        assert result.a_can_include_b is True


# ===================================================================
# 5. Multi-license compatibility matrix
# ===================================================================

class TestMatrix:
    def test_three_license_matrix(self):
        ids = ["MIT", "Apache-2.0", "GPL-3.0-only"]
        matrix = compatibility_matrix(ids)
        assert len(matrix) == 3  # C(3,2) = 3 pairs

        # MIT + Apache-2.0: compatible both ways
        r = matrix[("MIT", "Apache-2.0")]
        assert r.compatible is True
        assert r.a_can_include_b is True
        assert r.b_can_include_a is True

        # MIT + GPL-3.0-only: GPL can include MIT, not other way
        r = matrix[("MIT", "GPL-3.0-only")]
        assert r.compatible is True
        assert r.b_can_include_a is True
        assert r.a_can_include_b is False

        # Apache-2.0 + GPL-3.0-only: compatible
        r = matrix[("Apache-2.0", "GPL-3.0-only")]
        assert r.compatible is True

    def test_four_license_matrix_pair_count(self):
        ids = ["MIT", "GPL-2.0-only", "GPL-3.0-only", "AGPL-3.0-only"]
        matrix = compatibility_matrix(ids)
        assert len(matrix) == 6  # C(4,2) = 6

    def test_matrix_includes_incompatible(self):
        ids = ["Apache-2.0", "GPL-2.0-only", "GPL-3.0-only"]
        matrix = compatibility_matrix(ids)
        # Apache-2.0 + GPL-2.0-only should be incompatible
        assert matrix[("Apache-2.0", "GPL-2.0-only")].compatible is False
        # GPL-2.0-only + GPL-3.0-only should be incompatible
        assert matrix[("GPL-2.0-only", "GPL-3.0-only")].compatible is False
        # Apache-2.0 + GPL-3.0-only should be compatible
        assert matrix[("Apache-2.0", "GPL-3.0-only")].compatible is True


# ===================================================================
# 6. Edge cases
# ===================================================================

class TestEdgeCases:
    def test_unknown_license(self):
        result = check_compatibility("MIT", "WTFPL")
        assert result.compatible is False
        assert "Unknown license" in result.explanation

    def test_both_unknown(self):
        result = check_compatibility("FAKE-1.0", "FAKE-2.0")
        assert result.compatible is False

    def test_classify_unknown(self):
        assert classify("NONESUCH") is None

    def test_or_later_bridges_version_gap(self):
        """GPL-2.0-or-later + GPL-3.0-only works because dep can upgrade."""
        r = check_compatibility("GPL-3.0-only", "GPL-2.0-or-later")
        assert r.compatible is True
        assert r.a_can_include_b is True

    def test_or_later_both_sides(self):
        r = check_compatibility("GPL-2.0-or-later", "GPL-3.0-or-later")
        assert r.compatible is True

    def test_same_license_twice(self):
        r = check_compatibility("Apache-2.0", "Apache-2.0")
        assert r.compatible is True
        assert r.a_can_include_b is True
        assert r.b_can_include_a is True

    def test_lgpl_21_or_later_with_gpl3(self):
        """LGPL-2.1-or-later can be included in GPL-3.0 project."""
        r = check_compatibility("GPL-3.0-only", "LGPL-2.1-or-later")
        assert r.a_can_include_b is True

    def test_mpl2_with_gpl3(self):
        """MPL-2.0 secondary-license clause allows combination with GPL."""
        r = check_compatibility("GPL-3.0-only", "MPL-2.0")
        assert r.a_can_include_b is True

    def test_epl2_with_gpl3(self):
        """EPL-2.0 optional secondary license allows GPL combination."""
        r = check_compatibility("GPL-3.0-only", "EPL-2.0")
        assert r.a_can_include_b is True


# ===================================================================
# 7. CLI output format
# ===================================================================

class TestCLI:
    def test_matrix_output(self, capsys):
        main(["MIT", "Apache-2.0", "GPL-3.0-only"])
        out = capsys.readouterr().out
        assert "Compatibility Matrix" in out
        assert "MIT" in out
        assert "Apache-2.0" in out
        assert "GPL-3.0-only" in out
        assert "COMPATIBLE" in out or "INCOMPATIBLE" in out

    def test_check_output(self, capsys):
        main(["--check", "MIT", "GPL-2.0-only"])
        out = capsys.readouterr().out
        assert "MIT + GPL-2.0-only:" in out
        assert "YES" in out  # compatible (GPL can include MIT)

    def test_check_incompatible_output(self, capsys):
        main(["--check", "Apache-2.0", "GPL-2.0-only"])
        out = capsys.readouterr().out
        assert "NO" in out

    def test_classify_output(self, capsys):
        main(["--classify", "Apache-2.0"])
        out = capsys.readouterr().out
        assert "Apache-2.0" in out
        assert "permissive-patent" in out
        assert "Apache" in out

    def test_list_output(self, capsys):
        main(["--list"])
        out = capsys.readouterr().out
        assert "Known SPDX Licenses" in out
        assert "MIT" in out
        assert "GPL-3.0-only" in out
        assert "permissive" in out

    def test_classify_unknown(self, capsys):
        main(["--classify", "FAKE-LICENSE"])
        out = capsys.readouterr().out
        assert "Unknown" in out
