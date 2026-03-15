#!/usr/bin/env python3
"""Duplicate detection for the Main Menu software catalog.

Finds:
- Entries with the same name (case-insensitive) across or within data files
- Entries with the same URL (normalized: strip trailing slashes, www prefix, scheme)
- Entries with very similar names (Levenshtein distance <= 2, or same name with/without version numbers)

Exit code 0 if no duplicates found, 1 if duplicates found (CI-friendly).
"""

import json
import glob
import os
import re
import sys
from collections import defaultdict
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")


def load_all_entries():
    """Load all entries from data/*.json with source file tracking."""
    entries = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        basename = os.path.basename(path)
        for item in items:
            item["_source_file"] = basename
            entries.append(item)
    return entries


def normalize_url(url):
    """Normalize a URL for comparison: strip scheme, www prefix, trailing slashes."""
    if not url:
        return ""
    parsed = urlparse(url.lower().strip())
    host = parsed.netloc or ""
    # Strip www. prefix
    if host.startswith("www."):
        host = host[4:]
    # Strip port 80/443
    host = re.sub(r":(80|443)$", "", host)
    path = parsed.path.rstrip("/")
    # Include query and fragment (fragments can distinguish sub-resources)
    result = host + path
    if parsed.query:
        result += "?" + parsed.query
    if parsed.fragment:
        result += "#" + parsed.fragment
    return result


def levenshtein_distance(s1, s2):
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def strip_version(name):
    """Strip trailing version numbers/suffixes from a name.

    Examples: 'React 18' -> 'React', 'Vue.js 3' -> 'Vue.js', 'Angular 2+' -> 'Angular'
    """
    # Strip trailing version patterns like " 2", " v3", " 18.0", " 2+"
    stripped = re.sub(r"\s+v?\d+[\d.+]*\s*$", "", name, flags=re.IGNORECASE)
    return stripped


def find_exact_name_duplicates(entries):
    """Find entries with the same name (case-insensitive)."""
    by_name = defaultdict(list)
    for e in entries:
        name_lower = e.get("name", "").strip().lower()
        if name_lower:
            by_name[name_lower].append(e)

    duplicates = {}
    for name_lower, group in by_name.items():
        if len(group) > 1:
            duplicates[name_lower] = group
    return duplicates


def find_url_duplicates(entries):
    """Find entries with the same normalized URL."""
    by_url = defaultdict(list)
    for e in entries:
        norm = normalize_url(e.get("url", ""))
        if norm:
            by_url[norm].append(e)

    duplicates = {}
    for norm_url, group in by_url.items():
        if len(group) > 1:
            duplicates[norm_url] = group
    return duplicates


def find_similar_names(entries, max_distance=2):
    """Find entries with very similar names (Levenshtein distance <= max_distance).

    Also detects version variants (same name with/without version numbers).
    Skips pairs that are already exact duplicates (handled separately).
    Only checks names >= 4 chars to avoid false positives on short names.
    """
    MIN_NAME_LEN = 4
    similar_groups = []
    seen_pairs = set()

    # Build list of (name_lower, entry) for comparison
    name_entries = []
    for e in entries:
        name = e.get("name", "").strip()
        if len(name) >= MIN_NAME_LEN:
            name_entries.append((name.lower(), e))

    # Check version-stripped duplicates first
    by_stripped = defaultdict(list)
    for name_lower, e in name_entries:
        stripped = strip_version(e.get("name", "")).strip().lower()
        if stripped and stripped != name_lower:  # Only if stripping changed something
            by_stripped[stripped].append(e)
        # Also group the unversioned names
        by_stripped[name_lower].append(e)

    version_groups = {}
    for stripped, group in by_stripped.items():
        # Find entries with different actual names but same stripped name
        unique_names = set(e.get("name", "").strip().lower() for e in group)
        if len(unique_names) > 1:
            version_groups[stripped] = group

    # Levenshtein check — O(n^2) but filter by length difference first
    # Only compare entries whose names have similar lengths
    for i in range(len(name_entries)):
        name_i, entry_i = name_entries[i]
        for j in range(i + 1, len(name_entries)):
            name_j, entry_j = name_entries[j]
            # Skip exact matches (handled by exact duplicate check)
            if name_i == name_j:
                continue
            # Length difference filter: if lengths differ by more than max_distance, skip
            if abs(len(name_i) - len(name_j)) > max_distance:
                continue
            # Skip very short names to reduce false positives
            if len(name_i) < MIN_NAME_LEN or len(name_j) < MIN_NAME_LEN:
                continue
            pair_key = tuple(sorted([entry_i.get("id", ""), entry_j.get("id", "")]))
            if pair_key in seen_pairs:
                continue
            dist = levenshtein_distance(name_i, name_j)
            if dist <= max_distance:
                seen_pairs.add(pair_key)
                similar_groups.append({
                    "distance": dist,
                    "entries": [entry_i, entry_j],
                    "names": [entry_i.get("name", ""), entry_j.get("name", "")],
                })

    return similar_groups, version_groups


def format_entry(e):
    """Format an entry for display."""
    return (
        f"  ID: {e.get('id', '???')}  |  Name: {e.get('name', '???')}  |  "
        f"Category: {e.get('category', '???')}  |  File: {e.get('_source_file', '???')}  |  "
        f"URL: {e.get('url', '???')}"
    )


def main():
    entries = load_all_entries()
    print(f"Loaded {len(entries)} entries from {len(set(e['_source_file'] for e in entries))} files\n")

    # 1. Exact name duplicates
    name_dupes = find_exact_name_duplicates(entries)
    if name_dupes:
        print(f"=== EXACT NAME DUPLICATES ({len(name_dupes)} groups) ===\n")
        for name_lower, group in sorted(name_dupes.items()):
            print(f"  Name: \"{group[0].get('name', '')}\" ({len(group)} entries)")
            for e in group:
                print(format_entry(e))
            print()
    else:
        print("=== EXACT NAME DUPLICATES: None found ===\n")

    # 2. URL duplicates
    url_dupes = find_url_duplicates(entries)
    if url_dupes:
        print(f"=== URL DUPLICATES ({len(url_dupes)} groups) ===\n")
        for norm_url, group in sorted(url_dupes.items()):
            print(f"  Normalized URL: {norm_url} ({len(group)} entries)")
            for e in group:
                print(format_entry(e))
            print()
    else:
        print("=== URL DUPLICATES: None found ===\n")

    # 3. Similar names (informational only — does not affect exit code)
    similar_groups, version_groups = find_similar_names(entries)

    if version_groups:
        print(f"=== VERSION VARIANT DUPLICATES ({len(version_groups)} groups) [informational] ===\n")
        for stripped, group in sorted(version_groups.items()):
            names = sorted(set(e.get("name", "") for e in group))
            print(f"  Base name: \"{stripped}\" — Variants: {names}")
            for e in group:
                print(format_entry(e))
            print()
    else:
        print("=== VERSION VARIANT DUPLICATES: None found ===\n")

    if similar_groups:
        print(f"=== SIMILAR NAMES (Levenshtein distance <= 2) ({len(similar_groups)} pairs) [informational] ===\n")
        for sg in sorted(similar_groups, key=lambda x: x["distance"]):
            print(f"  \"{sg['names'][0]}\" <-> \"{sg['names'][1]}\" (distance: {sg['distance']})")
            for e in sg["entries"]:
                print(format_entry(e))
            print()
    else:
        print("=== SIMILAR NAMES: None found ===\n")

    # Summary — only exact name and URL duplicates affect exit code
    print("=" * 60)
    hard_dupes = len(name_dupes) + len(url_dupes)
    total = hard_dupes + len(similar_groups) + len(version_groups)
    if total:
        print(f"RESULT: {total} duplicate groups found")
        print(f"  - Exact name duplicates: {len(name_dupes)}")
        print(f"  - URL duplicates: {len(url_dupes)}")
        print(f"  - Version variants: {len(version_groups)} (informational)")
        print(f"  - Similar names: {len(similar_groups)} (informational)")
    else:
        print("RESULT: No duplicates found")

    if hard_dupes:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
