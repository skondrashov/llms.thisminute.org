"""
Main scraping pipeline orchestrator.

Usage:
    python -m scrape.pipeline [--sources awesome,github] [--output discovered.json]
"""

import argparse
import sys
import re

from .config import VALID_CATEGORIES
from .dedup import build_dedup_index, is_duplicate, normalize_url, normalize_name
from .normalize import normalize_entry
from .categorize import categorize, build_category_index
from .validate import validate_entry
from .output import write_entries
from .sources.awesome_lists import scrape_awesome_list
from .sources.awesome_registry import AWESOME_LISTS, get_section_category
from .sources.github_search import scrape_github_search
from .sources.homebrew_cask import scrape_homebrew_casks
from .sources.flathub import scrape_flathub
from .sources.cncf_landscape import scrape_cncf_landscape

# Patterns that indicate non-software entries (meetups, guides, curated lists, etc.)
_NON_SOFTWARE_RE = re.compile(
    r'a curated list|awesome list|collection of resources|list of\b|'
    r'a guide to|cheat sheet|conference|meetup|workshop|tutorial series',
    re.IGNORECASE
)


def run_awesome_scrape():
    """Scrape all registered awesome lists."""
    all_raw = []

    for repo_slug, label, section_map in AWESOME_LISTS:
        if label == "meta-awesome":
            continue  # skip the meta list

        entries = scrape_awesome_list(repo_slug, source_label=label)

        # Apply section-to-category mapping
        for entry in entries:
            section = entry.get("section", "")
            if section and section_map:
                cat = get_section_category(section, section_map)
                if cat:
                    entry["category"] = cat

        all_raw.extend(entries)

    print(f"\nAwesome lists total: {len(all_raw)} raw entries")
    return all_raw


def run_homebrew_scrape():
    """Scrape Homebrew Cask API for macOS apps."""
    print("\n--- Homebrew Cask ---")
    return scrape_homebrew_casks()


def run_flathub_scrape():
    """Scrape Flathub API for Linux apps."""
    print("\n--- Flathub ---")
    return scrape_flathub()


def run_cncf_scrape():
    """Scrape CNCF Landscape for cloud-native projects."""
    print("\n--- CNCF Landscape ---")
    return scrape_cncf_landscape()


def run_github_scrape():
    """Scrape GitHub Search API."""
    print("\n--- GitHub Search API ---")
    return scrape_github_search()


def process_entries(raw_entries):
    """
    Normalize, categorize, dedup, and validate raw entries.
    Returns list of clean, schema-compliant entries.
    """
    print(f"\nProcessing {len(raw_entries)} raw entries...")

    # Build indices
    print("  Building dedup index...")
    known_ids, known_urls, known_names = build_dedup_index()
    print(f"  Known: {len(known_ids)} IDs, {len(known_urls)} URLs, {len(known_names)} names")

    print("  Building category index...")
    category_index = build_category_index()

    clean = []
    stats = {
        "normalized": 0,
        "categorized": 0,
        "quality_dropped": 0,
        "duplicate": 0,
        "invalid": 0,
        "accepted": 0,
    }

    for raw in raw_entries:
        # Normalize
        entry = normalize_entry(raw)
        if not entry:
            continue
        stats["normalized"] += 1

        # Categorize only if no valid category yet
        if not entry.get("category") or entry["category"] not in VALID_CATEGORIES:
            entry["category"] = categorize(entry, category_index)
        stats["categorized"] += 1

        # Quality gates: drop bad entries before dedup
        desc = entry.get("description", "")
        if len(desc) < 20:
            stats["quality_dropped"] += 1
            continue
        if not entry.get("category"):
            stats["quality_dropped"] += 1
            continue
        if _NON_SOFTWARE_RE.search(desc):
            stats["quality_dropped"] += 1
            continue

        # Tag as crawl-discovered
        if "crawl-discovered" not in entry.get("tags", []):
            entry.setdefault("tags", []).append("crawl-discovered")

        # Dedup
        if is_duplicate(entry, known_ids, known_urls, known_names):
            stats["duplicate"] += 1
            continue

        # Validate
        valid, errors = validate_entry(entry)
        if not valid:
            stats["invalid"] += 1
            continue

        # Accept
        clean.append(entry)
        stats["accepted"] += 1

        # Update dedup index with this entry
        known_ids.add(entry["id"])
        if entry.get("url"):
            known_urls.add(normalize_url(entry["url"]))
        if entry.get("source"):
            known_urls.add(normalize_url(entry["source"]))
        known_names.add(normalize_name(entry["name"]))

    print(f"\nPipeline stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    return clean


def main():
    parser = argparse.ArgumentParser(description="Scrape software tools from awesome lists and GitHub")
    parser.add_argument("--sources", default="awesome,homebrew,cncf",
                       help="Comma-separated sources: awesome, homebrew, flathub, cncf, github (default: awesome,homebrew,cncf)")
    parser.add_argument("--output", default=None,
                       help="Output filename (default: discovered_YYYYMMDD.json)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Process but don't write output")
    parser.add_argument("--github-only", action="store_true",
                       help="Shortcut for --sources github")
    parser.add_argument("--awesome-only", action="store_true",
                       help="Shortcut for --sources awesome")
    parser.add_argument("--all", action="store_true",
                       help="Run all sources including GitHub (needs GITHUB_TOKEN)")
    args = parser.parse_args()

    if args.all:
        sources = ["awesome", "homebrew", "flathub", "cncf", "github"]
    elif args.github_only:
        sources = ["github"]
    elif args.awesome_only:
        sources = ["awesome"]
    else:
        sources = [s.strip() for s in args.sources.split(",")]

    raw_entries = []

    if "awesome" in sources:
        print("=== Awesome Lists Scraping ===")
        raw_entries.extend(run_awesome_scrape())

    if "homebrew" in sources:
        print("\n=== Homebrew Cask Scraping ===")
        raw_entries.extend(run_homebrew_scrape())

    if "flathub" in sources:
        print("\n=== Flathub Scraping ===")
        raw_entries.extend(run_flathub_scrape())

    if "cncf" in sources:
        print("\n=== CNCF Landscape Scraping ===")
        raw_entries.extend(run_cncf_scrape())

    if "github" in sources:
        print("\n=== GitHub Search API Scraping ===")
        raw_entries.extend(run_github_scrape())

    if not raw_entries:
        print("No raw entries collected. Check your sources and API token.")
        sys.exit(1)

    # Process
    clean_entries = process_entries(raw_entries)

    if not clean_entries:
        print("No new entries after processing.")
        sys.exit(0)

    # Write
    if args.dry_run:
        print(f"\n[DRY RUN] Would write {len(clean_entries)} entries")
        # Print sample
        for e in clean_entries[:5]:
            print(f"  {e['id']}: {e['name']} [{e['category']}]")
        if len(clean_entries) > 5:
            print(f"  ... and {len(clean_entries) - 5} more")
    else:
        filepath = write_entries(clean_entries, filename=args.output)
        print(f"\nDone! {len(clean_entries)} new entries written to {filepath}")
        print("Run 'python build.py' to rebuild the site.")


if __name__ == "__main__":
    main()
