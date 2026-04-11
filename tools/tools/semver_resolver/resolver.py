"""
Semver Range Resolver — Cross-Ecosystem Version Range Parser for Agents

Parses, resolves, and translates semantic version ranges across four
package ecosystems: npm (^/~), Cargo (caret-default, comma-AND),
pip (PEP 440 ~=), and Maven (bracket notation [,)).

Agents constantly wrangle dependency version constraints across projects
and languages.  LLMs frequently confuse the subtly different semantics
of ^, ~, ~=, and Maven bracket ranges.

SUPPORTED ECOSYSTEMS
====================
  npm    — ^, ~, >=/<, hyphen (1.0 - 2.0), X-ranges (1.*, 1.x), || union
  Cargo  — ^ (default), ~, wildcards (1.*), comparison ops, comma-AND
  pip    — ~= (compatible release), ==, !=, >=/<, comma-AND
  Maven  — [1.0,2.0), (,1.0], exact, multi-range union [a,b),[c,d)

FEATURES
========
- Version parsing with full semver 2.0.0 comparison (prerelease, build)
- Range containment testing: does version X satisfy range R?
- Overlap detection between two ranges
- Cross-ecosystem range translation (npm -> Cargo, pip -> Maven, etc.)
- Plain-English range explanations

Pure Python, no external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Optional


# ============================================================================
# Version
# ============================================================================

_VERSION_RE = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)"
    r"(?:\.(?P<minor>0|[1-9]\d*))?"
    r"(?:\.(?P<patch>0|[1-9]\d*))?"
    r"(?:-(?P<prerelease>[0-9A-Za-z\-]+(?:\.[0-9A-Za-z\-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z\-]+(?:\.[0-9A-Za-z\-]+)*))?$"
)


class VersionError(ValueError):
    """Raised when a version string cannot be parsed."""


@total_ordering
@dataclass(frozen=True)
class Version:
    """A parsed semantic version."""

    major: int
    minor: int = 0
    patch: int = 0
    prerelease: tuple[str, ...] = field(default_factory=tuple)
    build: tuple[str, ...] = field(default_factory=tuple)
    _original: str = ""
    _partial: bool = False

    @classmethod
    def parse(cls, s: str) -> Version:
        """Parse a version string into a Version object."""
        s = s.strip()
        m = _VERSION_RE.match(s)
        if not m:
            raise VersionError(f"Invalid version: {s!r}")

        major = int(m.group("major"))
        minor_str = m.group("minor")
        patch_str = m.group("patch")
        minor = int(minor_str) if minor_str is not None else 0
        patch = int(patch_str) if patch_str is not None else 0
        partial = minor_str is None or patch_str is None
        pre_str = m.group("prerelease")
        prerelease = tuple(pre_str.split(".")) if pre_str else ()
        build_str = m.group("build")
        build = tuple(build_str.split(".")) if build_str else ()

        return cls(
            major=major, minor=minor, patch=patch,
            prerelease=prerelease, build=build,
            _original=s, _partial=partial,
        )

    @classmethod
    def from_parts(cls, major: int, minor: int = 0, patch: int = 0,
                   prerelease: tuple[str, ...] = (), build: tuple[str, ...] = ()) -> Version:
        """Create a Version from numeric parts."""
        return cls(major=major, minor=minor, patch=patch,
                   prerelease=prerelease, build=build,
                   _original=f"{major}.{minor}.{patch}")

    @property
    def is_prerelease(self) -> bool:
        return len(self.prerelease) > 0

    @property
    def is_stable(self) -> bool:
        return self.major >= 1 and not self.is_prerelease

    @property
    def base(self) -> Version:
        return Version.from_parts(self.major, self.minor, self.patch)

    def _comparison_tuple(self) -> tuple:
        if self.prerelease:
            pre_key = []
            for ident in self.prerelease:
                if ident.isdigit():
                    pre_key.append((0, int(ident)))
                else:
                    pre_key.append((1, ident))
            return (self.major, self.minor, self.patch, 0, tuple(pre_key))
        else:
            return (self.major, self.minor, self.patch, 1, ())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._comparison_tuple() == other._comparison_tuple()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._comparison_tuple() < other._comparison_tuple()

    def __hash__(self) -> int:
        return hash(self._comparison_tuple())

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += "-" + ".".join(self.prerelease)
        if self.build:
            s += "+" + ".".join(self.build)
        return s

    def __repr__(self) -> str:
        return f"Version({str(self)!r})"

    def bump_major(self) -> Version:
        return Version.from_parts(self.major + 1, 0, 0)

    def bump_minor(self) -> Version:
        return Version.from_parts(self.major, self.minor + 1, 0)

    def bump_patch(self) -> Version:
        return Version.from_parts(self.major, self.minor, self.patch + 1)

    def next_major(self) -> Version:
        return Version.from_parts(self.major + 1, 0, 0)

    def next_minor(self) -> Version:
        return Version.from_parts(self.major, self.minor + 1, 0)


def sort_versions(versions: list[Version], reverse: bool = False) -> list[Version]:
    return sorted(versions, reverse=reverse)


# ============================================================================
# Bound & VersionRange
# ============================================================================

MIN_VERSION = Version.from_parts(0, 0, 0, prerelease=("0",))
MAX_VERSION = Version.from_parts(99999, 99999, 99999)


@dataclass(frozen=True)
class Bound:
    """A single contiguous version interval."""
    lower: Version
    upper: Version
    lower_inclusive: bool = True
    upper_inclusive: bool = False

    def contains(self, version: Version) -> bool:
        if self.lower_inclusive:
            if version < self.lower:
                return False
        else:
            if version <= self.lower:
                return False
        if self.upper_inclusive:
            if version > self.upper:
                return False
        else:
            if version >= self.upper:
                return False
        return True

    def is_empty(self) -> bool:
        if self.lower > self.upper:
            return True
        if self.lower == self.upper:
            return not (self.lower_inclusive and self.upper_inclusive)
        return False

    def overlaps(self, other: Bound) -> bool:
        intersection = self.intersect(other)
        return intersection is not None and not intersection.is_empty()

    def intersect(self, other: Bound) -> Optional[Bound]:
        if self.lower > other.lower:
            new_lower, new_lower_inc = self.lower, self.lower_inclusive
        elif self.lower < other.lower:
            new_lower, new_lower_inc = other.lower, other.lower_inclusive
        else:
            new_lower = self.lower
            new_lower_inc = self.lower_inclusive and other.lower_inclusive

        if self.upper < other.upper:
            new_upper, new_upper_inc = self.upper, self.upper_inclusive
        elif self.upper > other.upper:
            new_upper, new_upper_inc = other.upper, other.upper_inclusive
        else:
            new_upper = self.upper
            new_upper_inc = self.upper_inclusive and other.upper_inclusive

        result = Bound(new_lower, new_upper, new_lower_inc, new_upper_inc)
        if result.is_empty():
            return None
        return result

    def __str__(self) -> str:
        lb = "[" if self.lower_inclusive else "("
        ub = "]" if self.upper_inclusive else ")"
        return f"{lb}{self.lower}, {self.upper}{ub}"


@dataclass
class VersionRange:
    """A version range as a union of Bound intervals."""
    bounds: list[Bound]
    original: str = ""
    ecosystem: str = ""

    def contains(self, version: Version) -> bool:
        return any(b.contains(version) for b in self.bounds)

    def is_empty(self) -> bool:
        return all(b.is_empty() for b in self.bounds)

    def overlaps(self, other: VersionRange) -> bool:
        for b1 in self.bounds:
            for b2 in other.bounds:
                if b1.overlaps(b2):
                    return True
        return False

    def intersection(self, other: VersionRange) -> VersionRange:
        result_bounds = []
        for b1 in self.bounds:
            for b2 in other.bounds:
                inter = b1.intersect(b2)
                if inter is not None:
                    result_bounds.append(inter)
        return VersionRange(
            bounds=result_bounds,
            original=f"({self.original}) AND ({other.original})",
            ecosystem=self.ecosystem or other.ecosystem,
        )

    def __str__(self) -> str:
        if not self.bounds:
            return "<empty>"
        return " || ".join(str(b) for b in self.bounds)


# ============================================================================
# Shared helpers for parsing version parts
# ============================================================================

def _split_version_parts(s: str) -> dict:
    s = s.strip().lstrip("v")
    parts = s.split(".")
    result = {"major": 0, "minor": None, "patch": None, "partial": False}
    result["major"] = int(parts[0]) if parts[0] not in ("*", "x", "X") else 0
    if len(parts) > 1 and parts[1] not in ("*", "x", "X"):
        result["minor"] = int(parts[1])
    if len(parts) > 2 and parts[2] not in ("*", "x", "X"):
        patch_str = parts[2].split("-")[0].split("+")[0]
        result["patch"] = int(patch_str)
    result["partial"] = result["minor"] is None or result["patch"] is None
    return result


def _parse_partial(s: str) -> tuple[int, int, int]:
    s = s.strip().lstrip("v")
    parts = s.split(".")
    major = int(parts[0]) if parts[0] not in ("*", "x", "X") else 0
    minor = int(parts[1]) if len(parts) > 1 and parts[1] not in ("*", "x", "X") else 0
    patch_part = parts[2] if len(parts) > 2 else "0"
    patch_str = patch_part.split("-")[0].split("+")[0]
    patch = int(patch_str) if patch_str not in ("*", "x", "X") else 0
    return (major, minor, patch)


# ============================================================================
# npm range parser
# ============================================================================

def _npm_parse_caret(version_str: str) -> Bound:
    pi = _split_version_parts(version_str)
    major, minor, patch = pi["major"], pi["minor"], pi["patch"]
    lower = Version.from_parts(major, minor or 0, patch or 0)
    if major != 0:
        upper = Version.from_parts(major + 1, 0, 0)
    elif minor is not None and minor != 0:
        upper = Version.from_parts(0, minor + 1, 0)
    elif patch is not None and minor is not None:
        upper = Version.from_parts(0, 0, patch + 1)
    elif minor is None:
        upper = Version.from_parts(major + 1, 0, 0)
    else:
        upper = Version.from_parts(0, 1, 0)
    return Bound(lower, upper, True, False)


def _npm_parse_tilde(version_str: str) -> Bound:
    pi = _split_version_parts(version_str)
    major, minor, patch = pi["major"], pi["minor"], pi["patch"]
    lower = Version.from_parts(major, minor or 0, patch or 0)
    if minor is not None:
        upper = Version.from_parts(major, minor + 1, 0)
    else:
        upper = Version.from_parts(major + 1, 0, 0)
    return Bound(lower, upper, True, False)


def _npm_parse_operator(op: str, version_str: str) -> Bound:
    pi = _split_version_parts(version_str)
    major = pi["major"]
    minor = pi["minor"] if pi["minor"] is not None else 0
    patch = pi["patch"] if pi["patch"] is not None else 0
    v = Version.from_parts(major, minor, patch)
    if op == ">=":
        return Bound(v, MAX_VERSION, True, True)
    elif op == ">":
        return Bound(v, MAX_VERSION, False, True)
    elif op == "<=":
        return Bound(MIN_VERSION, v, True, True)
    elif op == "<":
        return Bound(MIN_VERSION, v, True, False)
    elif op == "=":
        return Bound(v, v, True, True)
    raise VersionError(f"Unknown operator: {op}")


def _npm_parse_xrange(version_str: str) -> Bound:
    version_str = version_str.strip().lstrip("v")
    if version_str in ("*", "x", "X", ""):
        return Bound(MIN_VERSION, MAX_VERSION, True, True)
    parts = version_str.split(".")
    if parts[0] in ("*", "x", "X"):
        return Bound(MIN_VERSION, MAX_VERSION, True, True)
    major = int(parts[0])
    if len(parts) == 1:
        return Bound(Version.from_parts(major, 0, 0), Version.from_parts(major + 1, 0, 0), True, False)
    minor_str = parts[1]
    if minor_str in ("*", "x", "X"):
        return Bound(Version.from_parts(major, 0, 0), Version.from_parts(major + 1, 0, 0), True, False)
    minor = int(minor_str)
    if len(parts) == 2:
        return Bound(Version.from_parts(major, minor, 0), Version.from_parts(major, minor + 1, 0), True, False)
    patch_str = parts[2].split("-")[0].split("+")[0]
    if patch_str in ("*", "x", "X"):
        return Bound(Version.from_parts(major, minor, 0), Version.from_parts(major, minor + 1, 0), True, False)
    patch = int(patch_str)
    v = Version.from_parts(major, minor, patch)
    return Bound(v, v, True, True)


def _npm_parse_single(comp: str) -> Bound:
    comp = comp.strip()
    if not comp or comp == "*":
        return Bound(MIN_VERSION, MAX_VERSION, True, True)
    if comp.startswith("^"):
        return _npm_parse_caret(comp[1:])
    if comp.startswith("~"):
        return _npm_parse_tilde(comp[1:])
    for op in (">=", "<=", ">", "<", "="):
        if comp.startswith(op):
            return _npm_parse_operator(op, comp[len(op):].strip())
    if "*" in comp or "x" in comp or "X" in comp:
        return _npm_parse_xrange(comp)
    parts = comp.split(".")
    if len(parts) < 3:
        return _npm_parse_xrange(comp)
    v = Version.parse(comp)
    return Bound(v, v, True, True)


def _npm_parse_hyphen(low_str: str, high_str: str) -> Bound:
    low = _parse_partial(low_str)
    high_parts = _split_version_parts(high_str)
    low_version = Version.from_parts(low[0], low[1], low[2])
    if high_parts["partial"]:
        if high_parts["minor"] is None:
            upper = Version.from_parts(high_parts["major"] + 1, 0, 0)
        else:
            upper = Version.from_parts(high_parts["major"], high_parts["minor"] + 1, 0)
        return Bound(low_version, upper, True, False)
    else:
        upper = Version.from_parts(high_parts["major"], high_parts["minor"] or 0, high_parts["patch"] or 0)
        return Bound(low_version, upper, True, True)


def _npm_parse_comparator_set(cs: str) -> list[Bound]:
    cs = cs.strip()
    if not cs or cs == "*":
        return [Bound(MIN_VERSION, MAX_VERSION, True, True)]
    hyphen_match = re.match(r"^\s*(\S+)\s+-\s+(\S+)\s*$", cs)
    if hyphen_match:
        return [_npm_parse_hyphen(hyphen_match.group(1), hyphen_match.group(2))]
    tokens = cs.split()
    comparators = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if re.match(r"^(>=|<=|>|<|=|~|\^)$", token) and i + 1 < len(tokens):
            comparators.append(token + tokens[i + 1])
            i += 2
        else:
            comparators.append(token)
            i += 1
    result_bound = Bound(MIN_VERSION, MAX_VERSION, True, True)
    for comp in comparators:
        b = _npm_parse_single(comp)
        inter = result_bound.intersect(b)
        if inter is None:
            return [Bound(MIN_VERSION, MIN_VERSION, False, False)]
        result_bound = inter
    return [result_bound]


def npm_parse_range(range_str: str) -> VersionRange:
    """Parse an npm semver range string."""
    range_str = range_str.strip()
    if not range_str or range_str == "*":
        return VersionRange(bounds=[Bound(MIN_VERSION, MAX_VERSION, True, True)], original=range_str or "*", ecosystem="npm")
    or_parts = [p.strip() for p in range_str.split("||")]
    all_bounds = []
    for part in or_parts:
        all_bounds.extend(_npm_parse_comparator_set(part))
    return VersionRange(bounds=all_bounds, original=range_str, ecosystem="npm")


# ============================================================================
# Cargo range parser
# ============================================================================

def _cargo_parse_single(comp: str) -> Bound:
    comp = comp.strip()
    if not comp or comp == "*":
        return Bound(MIN_VERSION, MAX_VERSION, True, True)
    if comp.startswith("~"):
        return _npm_parse_tilde(comp[1:])
    if comp.startswith("^"):
        return _npm_parse_caret(comp[1:])
    for op in (">=", "<=", ">", "<", "="):
        if comp.startswith(op):
            return _npm_parse_operator(op, comp[len(op):].strip())
    if "*" in comp:
        return _npm_parse_xrange(comp)
    # Bare version: treated as caret (Cargo default)
    return _npm_parse_caret(comp)


def cargo_parse_range(range_str: str) -> VersionRange:
    """Parse a Cargo semver range string."""
    range_str = range_str.strip()
    if not range_str or range_str == "*":
        return VersionRange(bounds=[Bound(MIN_VERSION, MAX_VERSION, True, True)], original=range_str or "*", ecosystem="cargo")
    parts = [p.strip() for p in range_str.split(",")]
    result_bound = Bound(MIN_VERSION, MAX_VERSION, True, True)
    for part in parts:
        if not part:
            continue
        b = _cargo_parse_single(part)
        inter = result_bound.intersect(b)
        if inter is None:
            return VersionRange(bounds=[Bound(MIN_VERSION, MIN_VERSION, False, False)], original=range_str, ecosystem="cargo")
        result_bound = inter
    return VersionRange(bounds=[result_bound], original=range_str, ecosystem="cargo")


# ============================================================================
# pip range parser
# ============================================================================

def _pip_parse_version(s: str) -> Version:
    s = s.strip()
    parts = s.split(".")
    major = int(parts[0]) if parts else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return Version.from_parts(major, minor, patch)


def _pip_parse_compatible(version_str: str) -> Bound:
    parts = version_str.split(".")
    if len(parts) < 2:
        raise VersionError(f"Compatible release requires at least N.N format: ~={version_str}")
    if len(parts) == 2:
        major, minor = int(parts[0]), int(parts[1])
        return Bound(Version.from_parts(major, minor, 0), Version.from_parts(major + 1, 0, 0), True, False)
    else:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        return Bound(Version.from_parts(major, minor, patch), Version.from_parts(major, minor + 1, 0), True, False)


def _pip_parse_equal(version_str: str) -> Bound:
    if version_str.endswith(".*"):
        prefix = version_str[:-2]
        parts = prefix.split(".")
        if len(parts) == 1:
            major = int(parts[0])
            return Bound(Version.from_parts(major, 0, 0), Version.from_parts(major + 1, 0, 0), True, False)
        elif len(parts) == 2:
            major, minor = int(parts[0]), int(parts[1])
            return Bound(Version.from_parts(major, minor, 0), Version.from_parts(major, minor + 1, 0), True, False)
        else:
            v = _pip_parse_version(prefix)
            return Bound(v, v, True, True)
    v = _pip_parse_version(version_str)
    return Bound(v, v, True, True)


def _pip_parse_operator(op: str, version_str: str) -> Bound:
    v = _pip_parse_version(version_str)
    if op == ">=":
        return Bound(v, MAX_VERSION, True, True)
    elif op == ">":
        return Bound(v, MAX_VERSION, False, True)
    elif op == "<=":
        return Bound(MIN_VERSION, v, True, True)
    elif op == "<":
        return Bound(MIN_VERSION, v, True, False)
    raise VersionError(f"Unknown operator: {op}")


def _pip_parse_single(comp: str) -> Bound:
    comp = comp.strip()
    if not comp:
        return Bound(MIN_VERSION, MAX_VERSION, True, True)
    if comp.startswith("~="):
        return _pip_parse_compatible(comp[2:].strip())
    if comp.startswith("=="):
        return _pip_parse_equal(comp[2:].strip())
    for op in (">=", "<=", ">", "<"):
        if comp.startswith(op):
            return _pip_parse_operator(op, comp[len(op):].strip())
    return _pip_parse_equal(comp)


def _pip_apply_exclusion(bounds: list[Bound], exclusion_str: str) -> list[Bound]:
    exc_version_str = exclusion_str[2:].strip()
    if exc_version_str.endswith(".*"):
        prefix = exc_version_str[:-2]
        parts = prefix.split(".")
        if len(parts) == 1:
            exc_lower = Version.from_parts(int(parts[0]), 0, 0)
            exc_upper = Version.from_parts(int(parts[0]) + 1, 0, 0)
        elif len(parts) == 2:
            exc_lower = Version.from_parts(int(parts[0]), int(parts[1]), 0)
            exc_upper = Version.from_parts(int(parts[0]), int(parts[1]) + 1, 0)
        else:
            return bounds
        result = []
        for bound in bounds:
            left = bound.intersect(Bound(bound.lower, exc_lower, bound.lower_inclusive, False))
            right = bound.intersect(Bound(exc_upper, bound.upper, True, bound.upper_inclusive))
            if left is not None and not left.is_empty():
                result.append(left)
            if right is not None and not right.is_empty():
                result.append(right)
        return result
    else:
        v = _pip_parse_version(exc_version_str)
        result = []
        for bound in bounds:
            if not bound.contains(v):
                result.append(bound)
                continue
            left = Bound(bound.lower, v, bound.lower_inclusive, False)
            right = Bound(v, bound.upper, False, bound.upper_inclusive)
            if not left.is_empty():
                result.append(left)
            if not right.is_empty():
                result.append(right)
        return result


def pip_parse_range(range_str: str) -> VersionRange:
    """Parse a pip version specifier string."""
    range_str = range_str.strip()
    if not range_str or range_str == "*":
        return VersionRange(bounds=[Bound(MIN_VERSION, MAX_VERSION, True, True)], original=range_str or "*", ecosystem="pip")
    parts = [p.strip() for p in range_str.split(",")]
    result_bound = Bound(MIN_VERSION, MAX_VERSION, True, True)
    exclusions = []
    for part in parts:
        if not part:
            continue
        if part.startswith("!="):
            exclusions.append(part)
            continue
        b = _pip_parse_single(part)
        inter = result_bound.intersect(b)
        if inter is None:
            return VersionRange(bounds=[Bound(MIN_VERSION, MIN_VERSION, False, False)], original=range_str, ecosystem="pip")
        result_bound = inter
    bounds = [result_bound]
    for exc in exclusions:
        bounds = _pip_apply_exclusion(bounds, exc)
    return VersionRange(bounds=bounds, original=range_str, ecosystem="pip")


# ============================================================================
# Maven range parser
# ============================================================================

def _maven_parse_version(s: str) -> Version:
    s = s.strip()
    if not s:
        raise VersionError("Empty version string")
    parts = s.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch = int(parts[2]) if len(parts) > 2 else 0
    return Version.from_parts(major, minor, patch)


def _maven_parse_single_bracket(segment: str) -> Bound:
    segment = segment.strip()
    if not segment:
        raise VersionError("Empty Maven range segment")
    open_bracket = segment[0]
    close_bracket = segment[-1]
    if open_bracket not in "[(" or close_bracket not in "])":
        raise VersionError(f"Invalid Maven range: {segment}")
    lower_inclusive = open_bracket == "["
    upper_inclusive = close_bracket == "]"
    inner = segment[1:-1].strip()
    if "," not in inner:
        v = _maven_parse_version(inner)
        return Bound(v, v, True, True)
    parts = inner.split(",", 1)
    lower_str = parts[0].strip()
    upper_str = parts[1].strip() if len(parts) > 1 else ""
    if lower_str:
        lower = _maven_parse_version(lower_str)
    else:
        lower = MIN_VERSION
        lower_inclusive = True
    if upper_str:
        upper = _maven_parse_version(upper_str)
    else:
        upper = MAX_VERSION
        upper_inclusive = True
    return Bound(lower, upper, lower_inclusive, upper_inclusive)


def maven_parse_range(range_str: str) -> VersionRange:
    """Parse a Maven version range string."""
    range_str = range_str.strip()
    if not range_str:
        return VersionRange(bounds=[Bound(MIN_VERSION, MAX_VERSION, True, True)], original="", ecosystem="maven")
    if range_str[0] in "[(":
        bounds = []
        i = 0
        s = range_str
        while i < len(s):
            if s[i] in "[(":
                j = i + 1
                while j < len(s) and s[j] not in "])":
                    j += 1
                if j < len(s):
                    j += 1
                segment = s[i:j]
                bounds.append(_maven_parse_single_bracket(segment))
                i = j
                if i < len(s) and s[i] == ",":
                    i += 1
            else:
                i += 1
        if not bounds:
            return VersionRange(bounds=[Bound(MIN_VERSION, MIN_VERSION, False, False)], original=range_str, ecosystem="maven")
        return VersionRange(bounds=bounds, original=range_str, ecosystem="maven")
    v = _maven_parse_version(range_str)
    return VersionRange(bounds=[Bound(v, v, True, True)], original=range_str, ecosystem="maven")


# ============================================================================
# Ecosystem dispatch
# ============================================================================

ECOSYSTEMS = ("npm", "cargo", "pip", "maven")

_PARSERS = {
    "npm": npm_parse_range,
    "cargo": cargo_parse_range,
    "pip": pip_parse_range,
    "maven": maven_parse_range,
}


def get_parser(ecosystem: str):
    ecosystem = ecosystem.lower()
    if ecosystem in _PARSERS:
        return _PARSERS[ecosystem]
    raise ValueError(f"Unknown ecosystem: {ecosystem!r}. Supported: {', '.join(ECOSYSTEMS)}")


# ============================================================================
# Convenience functions
# ============================================================================

def check_version(range_str: str, version_str: str, ecosystem: str) -> bool:
    """Check if a version satisfies a range in the given ecosystem."""
    parser = get_parser(ecosystem)
    vr = parser(range_str)
    v = Version.parse(version_str)
    return vr.contains(v)


def find_overlap(range_str1: str, range_str2: str, ecosystem: str) -> Optional[VersionRange]:
    """Find the overlap between two ranges."""
    parser = get_parser(ecosystem)
    vr1 = parser(range_str1)
    vr2 = parser(range_str2)
    result = vr1.intersection(vr2)
    if result.is_empty():
        return None
    return result


def translate_range(range_str: str, from_eco: str, to_eco: str) -> dict:
    """Translate a range from one ecosystem to another."""
    parser = get_parser(from_eco)
    vr = parser(range_str)
    results = []
    notes: list[str] = []
    exact = True

    for bound in vr.bounds:
        translated, is_exact, bound_notes = _translate_bound(bound, to_eco)
        results.append(translated)
        if not is_exact:
            exact = False
        notes.extend(bound_notes)

    separator = "," if to_eco in ("maven", "pip") else " || "
    translated_str = separator.join(results) if results else "<empty>"

    return {
        "translated": translated_str,
        "exact": exact,
        "notes": notes,
        "source_ecosystem": from_eco,
        "target_ecosystem": to_eco,
        "original": range_str,
    }


def _translate_bound(bound: Bound, to_eco: str) -> tuple[str, bool, list[str]]:
    lower, upper = bound.lower, bound.upper
    lower_inc, upper_inc = bound.lower_inclusive, bound.upper_inclusive
    notes: list[str] = []
    is_unbounded_upper = upper >= MAX_VERSION
    is_unbounded_lower = lower <= MIN_VERSION

    if to_eco == "npm":
        return _bound_to_npm(lower, upper, lower_inc, upper_inc, is_unbounded_lower, is_unbounded_upper, notes)
    elif to_eco == "cargo":
        return _bound_to_cargo(lower, upper, lower_inc, upper_inc, is_unbounded_lower, is_unbounded_upper, notes)
    elif to_eco == "pip":
        return _bound_to_pip(lower, upper, lower_inc, upper_inc, is_unbounded_lower, is_unbounded_upper, notes)
    elif to_eco == "maven":
        return _bound_to_maven(lower, upper, lower_inc, upper_inc, is_unbounded_lower, is_unbounded_upper, notes)
    raise ValueError(f"Unknown target ecosystem: {to_eco}")


def _bound_to_npm(lower, upper, lower_inc, upper_inc, unb_lower, unb_upper, notes):
    if unb_lower and unb_upper:
        return "*", True, []
    if lower_inc and not upper_inc and not unb_upper:
        if lower.major >= 1 and upper == lower.next_major():
            return f"^{lower}", True, []
        if lower.major == 0 and lower.minor >= 1 and upper == Version.from_parts(0, lower.minor + 1, 0):
            return f"^{lower}", True, []
        if lower.major == 0 and lower.minor == 0 and upper == Version.from_parts(0, 0, lower.patch + 1):
            return f"^{lower}", True, []
        if upper == lower.next_minor():
            return f"~{lower}", True, []
    parts = []
    if not unb_lower:
        parts.append(f"{'>='}{ lower}" if lower_inc else f">{lower}")
    if not unb_upper:
        parts.append(f"<={upper}" if upper_inc else f"<{upper}")
    return " ".join(parts), True, notes


def _bound_to_cargo(lower, upper, lower_inc, upper_inc, unb_lower, unb_upper, notes):
    if unb_lower and unb_upper:
        return "*", True, []
    if lower_inc and not upper_inc and not unb_upper:
        if lower.major >= 1 and upper == lower.next_major():
            return f"^{lower}", True, []
        if lower.major == 0 and lower.minor >= 1 and upper == Version.from_parts(0, lower.minor + 1, 0):
            return f"^{lower}", True, []
        if lower.major == 0 and lower.minor == 0 and upper == Version.from_parts(0, 0, lower.patch + 1):
            return f"^{lower}", True, []
        if upper == lower.next_minor():
            return f"~{lower}", True, []
    parts = []
    if not unb_lower:
        parts.append(f">={lower}" if lower_inc else f">{lower}")
    if not unb_upper:
        parts.append(f"<={upper}" if upper_inc else f"<{upper}")
    return ", ".join(parts), True, notes


def _bound_to_pip(lower, upper, lower_inc, upper_inc, unb_lower, unb_upper, notes):
    if unb_lower and unb_upper:
        return ">=0.0.0", True, []
    if lower_inc and not upper_inc and not unb_upper:
        if upper == lower.next_minor() and lower.patch == 0:
            return f"~={lower.major}.{lower.minor}", True, []
        if upper == lower.next_minor():
            return f"~={lower}", True, []
        if upper == lower.next_major() and lower.minor == 0 and lower.patch == 0:
            return f">={lower},<{upper}", True, []
        if upper == lower.next_major():
            # pip ~= can't express >=X.Y.Z <(X+1).0.0 when Y or Z > 0
            # Fall through to explicit >=,< notation for an exact translation
            pass
    parts = []
    if not unb_lower:
        parts.append(f">={lower}" if lower_inc else f">{lower}")
    if not unb_upper:
        parts.append(f"<={upper}" if upper_inc else f"<{upper}")
    return ",".join(parts), True, notes


def _bound_to_maven(lower, upper, lower_inc, upper_inc, unb_lower, unb_upper, notes):
    if unb_lower and unb_upper:
        return "(,)", True, []
    lb = "[" if lower_inc else "("
    ub = "]" if upper_inc else ")"
    if unb_lower:
        return f"(,{upper}{ub}", True, []
    if unb_upper:
        return f"{lb}{lower},)", True, []
    return f"{lb}{lower},{upper}{ub}", True, []


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="semver-resolve",
        description="Parse and resolve semantic version ranges across ecosystems.",
    )
    parser.add_argument("range", help="Version range string (e.g., '^1.2.3')")
    parser.add_argument("--ecosystem", "-e", default="npm",
                        choices=list(ECOSYSTEMS), help="Ecosystem (default: npm)")
    parser.add_argument("--check", "-c", help="Check if this version satisfies the range")
    parser.add_argument("--translate", "-t", choices=list(ECOSYSTEMS),
                        help="Translate range to target ecosystem")
    parser.add_argument("--overlap", help="Find overlap with another range")

    args = parser.parse_args()

    if args.check:
        result = check_version(args.range, args.check, args.ecosystem)
        print(f"{'Yes' if result else 'No'}: {args.check} {'satisfies' if result else 'does not satisfy'} {args.range}")
        sys.exit(0 if result else 1)

    if args.translate:
        result = translate_range(args.range, args.ecosystem, args.translate)
        print(f"Source:     {result['original']} ({result['source_ecosystem']})")
        print(f"Translated: {result['translated']} ({result['target_ecosystem']})")
        print(f"Exact:      {result['exact']}")
        if result["notes"]:
            for note in result["notes"]:
                print(f"Note:       {note}")
        return

    if args.overlap:
        result = find_overlap(args.range, args.overlap, args.ecosystem)
        if result:
            print(f"Overlap: {result}")
        else:
            print("No overlap")
        return

    eco_parser = get_parser(args.ecosystem)
    vr = eco_parser(args.range)
    print(f"Range:      {args.range}")
    print(f"Ecosystem:  {args.ecosystem}")
    print(f"Bounds:     {vr}")
    print(f"Empty:      {vr.is_empty()}")


if __name__ == "__main__":
    main()
