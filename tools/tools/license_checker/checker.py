"""
SPDX License Compatibility Checker

Determines whether two or more SPDX-licensed components can coexist in a
single project. Agents regularly need this when evaluating dependency trees,
and LLMs frequently hallucinate license compatibility -- this tool encodes
the actual rules.

Usage:
    python checker.py MIT Apache-2.0 GPL-3.0-only     # Full compatibility matrix
    python checker.py --check MIT GPL-2.0-only         # Quick yes/no for a pair
    python checker.py --classify Apache-2.0            # Show license type/permissions
    python checker.py --list                           # List all known licenses

Pure Python, no external dependencies.
"""

from __future__ import annotations

import argparse
import sys
from enum import Enum
from typing import NamedTuple

# ---------------------------------------------------------------------------
# License taxonomy
# ---------------------------------------------------------------------------

class LicenseType(Enum):
    PERMISSIVE = "permissive"
    PERMISSIVE_PATENT = "permissive-patent"  # Apache-2.0 -- patent clause
    WEAK_COPYLEFT = "weak-copyleft"
    STRONG_COPYLEFT = "strong-copyleft"
    NETWORK_COPYLEFT = "network-copyleft"
    PUBLIC_DOMAIN = "public-domain"
    CREATIVE_COMMONS = "creative-commons"
    CC_COPYLEFT = "creative-commons-copyleft"  # CC-BY-SA


class LicenseInfo(NamedTuple):
    spdx_id: str
    name: str
    license_type: LicenseType
    family: str           # e.g. "GPL", "LGPL", "MPL", "BSD", "CC", ...
    or_later: bool        # True for -or-later variants


# ---------------------------------------------------------------------------
# License database
# ---------------------------------------------------------------------------

LICENSE_DB: dict[str, LicenseInfo] = {}


def _reg(spdx_id: str, name: str, lt: LicenseType, family: str,
         or_later: bool = False) -> None:
    LICENSE_DB[spdx_id] = LicenseInfo(spdx_id, name, lt, family, or_later)


# Permissive
_reg("MIT",            "MIT License",                    LicenseType.PERMISSIVE, "MIT")
_reg("ISC",            "ISC License",                    LicenseType.PERMISSIVE, "ISC")
_reg("0BSD",           "Zero-Clause BSD",                LicenseType.PERMISSIVE, "BSD")
_reg("BSD-2-Clause",   "BSD 2-Clause",                   LicenseType.PERMISSIVE, "BSD")
_reg("BSD-3-Clause",   "BSD 3-Clause",                   LicenseType.PERMISSIVE, "BSD")
_reg("Unlicense",      "The Unlicense",                  LicenseType.PUBLIC_DOMAIN, "PD")
_reg("Zlib",           "zlib License",                   LicenseType.PERMISSIVE, "Zlib")
_reg("PostgreSQL",     "PostgreSQL License",             LicenseType.PERMISSIVE, "PostgreSQL")
_reg("BSL-1.0",        "Boost Software License 1.0",     LicenseType.PERMISSIVE, "Boost")
_reg("Artistic-2.0",   "Artistic License 2.0",           LicenseType.PERMISSIVE, "Artistic")

# Permissive with patent clause
_reg("Apache-2.0",     "Apache License 2.0",             LicenseType.PERMISSIVE_PATENT, "Apache")

# Public domain / CC0
_reg("CC0-1.0",        "CC0 1.0 Universal",              LicenseType.PUBLIC_DOMAIN, "CC")

# Creative Commons
_reg("CC-BY-4.0",      "Creative Commons Attribution 4.0", LicenseType.CREATIVE_COMMONS, "CC")
_reg("CC-BY-SA-4.0",   "Creative Commons Attribution-ShareAlike 4.0", LicenseType.CC_COPYLEFT, "CC")

# Weak copyleft
_reg("LGPL-2.1-only",      "GNU LGPL v2.1 only",         LicenseType.WEAK_COPYLEFT, "LGPL")
_reg("LGPL-2.1-or-later",  "GNU LGPL v2.1 or later",     LicenseType.WEAK_COPYLEFT, "LGPL", or_later=True)
_reg("LGPL-3.0-only",      "GNU LGPL v3.0 only",         LicenseType.WEAK_COPYLEFT, "LGPL")
_reg("LGPL-3.0-or-later",  "GNU LGPL v3.0 or later",     LicenseType.WEAK_COPYLEFT, "LGPL", or_later=True)
_reg("MPL-2.0",        "Mozilla Public License 2.0",     LicenseType.WEAK_COPYLEFT, "MPL")
_reg("EPL-2.0",        "Eclipse Public License 2.0",     LicenseType.WEAK_COPYLEFT, "EPL")

# Strong copyleft
_reg("GPL-2.0-only",       "GNU GPL v2.0 only",          LicenseType.STRONG_COPYLEFT, "GPL")
_reg("GPL-2.0-or-later",   "GNU GPL v2.0 or later",      LicenseType.STRONG_COPYLEFT, "GPL", or_later=True)
_reg("GPL-3.0-only",       "GNU GPL v3.0 only",          LicenseType.STRONG_COPYLEFT, "GPL")
_reg("GPL-3.0-or-later",   "GNU GPL v3.0 or later",      LicenseType.STRONG_COPYLEFT, "GPL", or_later=True)

# Network copyleft
_reg("AGPL-3.0-only",      "GNU AGPL v3.0 only",         LicenseType.NETWORK_COPYLEFT, "AGPL")
_reg("AGPL-3.0-or-later",  "GNU AGPL v3.0 or later",     LicenseType.NETWORK_COPYLEFT, "AGPL", or_later=True)


# ---------------------------------------------------------------------------
# Helpers to extract a "major version" for GPL-family comparison
# ---------------------------------------------------------------------------

_GPL_FAMILY_VERSIONS: dict[str, int] = {
    "GPL-2.0-only": 2,  "GPL-2.0-or-later": 2,
    "GPL-3.0-only": 3,  "GPL-3.0-or-later": 3,
    "LGPL-2.1-only": 2, "LGPL-2.1-or-later": 2,
    "LGPL-3.0-only": 3, "LGPL-3.0-or-later": 3,
    "AGPL-3.0-only": 3, "AGPL-3.0-or-later": 3,
}


def _gpl_version(spdx_id: str) -> int:
    return _GPL_FAMILY_VERSIONS.get(spdx_id, 0)


def _is_permissive_or_pd(lt: LicenseType) -> bool:
    return lt in (LicenseType.PERMISSIVE, LicenseType.PERMISSIVE_PATENT,
                  LicenseType.PUBLIC_DOMAIN, LicenseType.CREATIVE_COMMONS)


# ---------------------------------------------------------------------------
# Compatibility result
# ---------------------------------------------------------------------------

class CompatResult(NamedTuple):
    compatible: bool
    a_can_include_b: bool   # Can a project under license A include code under B?
    b_can_include_a: bool   # Vice versa
    explanation: str


# ---------------------------------------------------------------------------
# Core compatibility engine
# ---------------------------------------------------------------------------

def classify(spdx_id: str) -> LicenseInfo | None:
    """Return the LicenseInfo for a known SPDX identifier, or None."""
    return LICENSE_DB.get(spdx_id)


def check_compatibility(id_a: str, id_b: str) -> CompatResult:
    """
    Determine license compatibility between two SPDX identifiers.

    Returns a CompatResult with directional information:
    - a_can_include_b: project licensed under A can include component under B
    - b_can_include_a: project licensed under B can include component under A
    - compatible: True if at least one direction works
    """
    info_a = classify(id_a)
    info_b = classify(id_b)

    if info_a is None:
        return CompatResult(False, False, False, f"Unknown license: {id_a}")
    if info_b is None:
        return CompatResult(False, False, False, f"Unknown license: {id_b}")

    # Same license is always compatible
    if id_a == id_b:
        return CompatResult(True, True, True, "Same license -- always compatible.")

    a_can_b = _can_include(info_a, info_b)
    b_can_a = _can_include(info_b, info_a)

    compatible = a_can_b[0] or b_can_a[0]

    # Build explanation from both directions
    parts = []
    if a_can_b[0] and b_can_a[0]:
        parts.append(f"Bidirectionally compatible. {a_can_b[1]}")
    elif a_can_b[0]:
        parts.append(f"{id_a} project CAN include {id_b} code. {a_can_b[1]}")
        parts.append(f"{id_b} project CANNOT include {id_a} code. {b_can_a[1]}")
    elif b_can_a[0]:
        parts.append(f"{id_b} project CAN include {id_a} code. {b_can_a[1]}")
        parts.append(f"{id_a} project CANNOT include {id_b} code. {a_can_b[1]}")
    else:
        parts.append(f"Incompatible. {a_can_b[1]}")

    return CompatResult(compatible, a_can_b[0], b_can_a[0], " ".join(parts))


def _can_include(project: LicenseInfo, dep: LicenseInfo) -> tuple[bool, str]:
    """
    Can a project under `project` license include a dependency under `dep`?

    Returns (allowed, reason).
    """
    p_type = project.license_type
    d_type = dep.license_type

    # --- dependency is public domain or permissive (no patent issue) ---------
    if d_type in (LicenseType.PUBLIC_DOMAIN, LicenseType.PERMISSIVE,
                  LicenseType.CREATIVE_COMMONS):
        return True, f"{dep.spdx_id} is {d_type.value} -- can be included in any project."

    # --- dependency is Apache-2.0 (permissive-patent) ------------------------
    if d_type == LicenseType.PERMISSIVE_PATENT:
        # Apache-2.0 into GPL-2.0-only is the famous incompatibility
        if project.family == "GPL" and _gpl_version(project.spdx_id) == 2 and not project.or_later:
            return False, ("Apache-2.0 patent clause conflicts with GPL-2.0-only. "
                           "The FSF considers them incompatible.")
        return True, f"{dep.spdx_id} is permissive (with patent grant) -- generally includable."

    # --- dependency is CC-BY-SA (copyleft creative commons) ------------------
    if d_type == LicenseType.CC_COPYLEFT:
        if p_type == LicenseType.CC_COPYLEFT and project.family == dep.family:
            return True, "Same CC-SA family."
        if _is_permissive_or_pd(p_type):
            return False, f"{dep.spdx_id} share-alike requires derivative works use the same license."
        return False, f"{dep.spdx_id} share-alike is not compatible with {project.spdx_id}."

    # --- dependency is weak copyleft (LGPL, MPL, EPL) ------------------------
    if d_type == LicenseType.WEAK_COPYLEFT:
        # Permissive project can include weak-copyleft as a separate component
        if _is_permissive_or_pd(p_type):
            return True, (f"{dep.spdx_id} is weak copyleft -- can be included as a library/component "
                          f"in a {project.spdx_id} project.")
        # Same family weak copyleft
        if d_type == p_type and dep.family == project.family:
            return True, "Same weak-copyleft family."
        # Strong/network copyleft can include weak copyleft (with conditions)
        if p_type in (LicenseType.STRONG_COPYLEFT, LicenseType.NETWORK_COPYLEFT):
            # GPL-3.0 can include LGPL-3.0; GPL-2.0 can include LGPL-2.1
            if dep.family == "LGPL":
                return True, f"{dep.spdx_id} can be included in a {project.spdx_id} project."
            # MPL-2.0 has a secondary license provision allowing GPL compatibility
            if dep.spdx_id == "MPL-2.0":
                return True, ("MPL-2.0 has a secondary-license clause allowing combination "
                              "with GPL-family licenses.")
            # EPL-2.0 has optional secondary license for GPL
            if dep.spdx_id == "EPL-2.0":
                return True, ("EPL-2.0 optionally allows secondary licensing, "
                              "permitting combination with GPL-family licenses.")
        # Weak copyleft from different families
        if p_type == LicenseType.WEAK_COPYLEFT and dep.family != project.family:
            return False, (f"{dep.spdx_id} ({dep.family}) and {project.spdx_id} ({project.family}) "
                           f"are different weak-copyleft families -- not directly compatible.")
        return False, f"{dep.spdx_id} weak-copyleft terms conflict with {project.spdx_id}."

    # --- dependency is strong copyleft (GPL) ---------------------------------
    if d_type == LicenseType.STRONG_COPYLEFT:
        # Same family and compatible version?
        if p_type == LicenseType.STRONG_COPYLEFT and project.family == "GPL":
            return _gpl_version_compat(project, dep)
        if p_type == LicenseType.NETWORK_COPYLEFT:
            # AGPL-3.0 can include GPL-3.0 code
            if _gpl_version(dep.spdx_id) == 3 or dep.or_later:
                return True, f"AGPL-3.0 can include {dep.spdx_id} code (both v3-compatible)."
            return False, f"AGPL-3.0 cannot include {dep.spdx_id} (version incompatibility)."
        # Permissive project CANNOT include GPL dependency (would need relicensing)
        if _is_permissive_or_pd(p_type):
            return False, (f"{dep.spdx_id} is strong copyleft -- a {project.spdx_id} project "
                           f"cannot include it without adopting GPL terms.")
        # Weak copyleft project cannot include GPL
        if p_type == LicenseType.WEAK_COPYLEFT:
            return False, (f"{dep.spdx_id} is strong copyleft -- cannot be included in a "
                           f"{project.spdx_id} project without adopting GPL terms.")
        return False, f"{dep.spdx_id} strong copyleft is incompatible with {project.spdx_id}."

    # --- dependency is network copyleft (AGPL) -------------------------------
    if d_type == LicenseType.NETWORK_COPYLEFT:
        # Only AGPL or GPL-3.0 (or-later) projects can include AGPL
        if p_type == LicenseType.NETWORK_COPYLEFT:
            return True, "Both are AGPL -- compatible."
        if p_type == LicenseType.STRONG_COPYLEFT:
            # GPL-3.0 can include AGPL per GPLv3 section 13
            if _gpl_version(project.spdx_id) == 3 or project.or_later:
                return True, ("GPL-3.0 can include AGPL-3.0 code per section 13 "
                              "of the GPLv3.")
            return False, f"{project.spdx_id} cannot include AGPL-3.0 (version incompatibility)."
        if _is_permissive_or_pd(p_type):
            return False, (f"{dep.spdx_id} is network copyleft -- a {project.spdx_id} project "
                           f"cannot include it without adopting AGPL terms.")
        return False, f"{dep.spdx_id} network copyleft is incompatible with {project.spdx_id}."

    return False, f"No known compatibility rule for {project.spdx_id} + {dep.spdx_id}."


def _gpl_version_compat(project: LicenseInfo, dep: LicenseInfo) -> tuple[bool, str]:
    """GPL-family version compatibility."""
    p_ver = _gpl_version(project.spdx_id)
    d_ver = _gpl_version(dep.spdx_id)

    # Exact same version -- always OK
    if p_ver == d_ver:
        return True, f"Both are GPL v{p_ver} -- compatible."

    # -or-later can bridge versions upward
    if dep.or_later and d_ver <= p_ver:
        return True, (f"{dep.spdx_id} allows upgrading to v{p_ver}, "
                      f"compatible with {project.spdx_id}.")
    if project.or_later and p_ver <= d_ver:
        return True, (f"{project.spdx_id} allows upgrading to v{d_ver}, "
                      f"compatible with {dep.spdx_id}.")

    # GPL-2.0-only vs GPL-3.0-only -- incompatible
    return False, (f"{project.spdx_id} and {dep.spdx_id} are different GPL versions "
                   f"without -or-later -- incompatible.")


# ---------------------------------------------------------------------------
# Multi-license compatibility matrix
# ---------------------------------------------------------------------------

def compatibility_matrix(ids: list[str]) -> dict[tuple[str, str], CompatResult]:
    """Check all pairs and return a mapping from (A, B) -> CompatResult."""
    results: dict[tuple[str, str], CompatResult] = {}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            results[(a, b)] = check_compatibility(a, b)
    return results


# ---------------------------------------------------------------------------
# CLI formatting
# ---------------------------------------------------------------------------

def _format_matrix(ids: list[str],
                   matrix: dict[tuple[str, str], CompatResult]) -> str:
    lines: list[str] = []
    lines.append(f"License Compatibility Matrix ({len(ids)} licenses)")
    lines.append("=" * 60)

    for (a, b), result in matrix.items():
        status = "COMPATIBLE" if result.compatible else "INCOMPATIBLE"
        direction = ""
        if result.compatible:
            if result.a_can_include_b and result.b_can_include_a:
                direction = " [bidirectional]"
            elif result.a_can_include_b:
                direction = f" [{a} can include {b}]"
            else:
                direction = f" [{b} can include {a}]"

        lines.append(f"\n  {a}  +  {b}")
        lines.append(f"  => {status}{direction}")
        lines.append(f"     {result.explanation}")

    return "\n".join(lines)


def _format_classify(spdx_id: str) -> str:
    info = classify(spdx_id)
    if info is None:
        return f"Unknown license: {spdx_id}"
    lines = [
        f"License:  {info.spdx_id}",
        f"Name:     {info.name}",
        f"Type:     {info.license_type.value}",
        f"Family:   {info.family}",
        f"Or-later: {info.or_later}",
    ]
    return "\n".join(lines)


def _format_list() -> str:
    lines = ["Known SPDX Licenses", "=" * 40]
    by_type: dict[str, list[str]] = {}
    for info in LICENSE_DB.values():
        by_type.setdefault(info.license_type.value, []).append(info.spdx_id)
    for lt, ids in by_type.items():
        lines.append(f"\n  {lt}:")
        for sid in sorted(ids):
            lines.append(f"    {sid}")
    return "\n".join(lines)


def _format_check(id_a: str, id_b: str) -> str:
    result = check_compatibility(id_a, id_b)
    status = "YES" if result.compatible else "NO"
    return f"{id_a} + {id_b}: {status}\n{result.explanation}"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="SPDX License Compatibility Checker")
    parser.add_argument("licenses", nargs="*",
                        help="SPDX license identifiers to check")
    parser.add_argument("--check", nargs=2, metavar="LICENSE",
                        help="Quick yes/no check for two licenses")
    parser.add_argument("--classify", metavar="LICENSE",
                        help="Show license type and permissions")
    parser.add_argument("--list", action="store_true",
                        help="List all known licenses")

    args = parser.parse_args(argv)

    if args.list:
        print(_format_list())
    elif args.classify:
        print(_format_classify(args.classify))
    elif args.check:
        print(_format_check(args.check[0], args.check[1]))
    elif args.licenses:
        if len(args.licenses) < 2:
            parser.error("Provide at least two license identifiers for a matrix.")
        matrix = compatibility_matrix(args.licenses)
        print(_format_matrix(args.licenses, matrix))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
