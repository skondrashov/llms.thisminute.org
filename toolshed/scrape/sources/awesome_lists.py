"""
Parser for awesome-list README.md files.

Handles three common formats:
  Format A (simple):     - [Name](url) - Description
  Format B (selfhosted): - [Name](url) - Description. `source` `license` `language`
  Format C (badges):     - [Name](url) ![badge] - Description
"""

import re
import time
import urllib.request
import urllib.error
from ..config import AWESOME_RATE_DELAY


def fetch_readme(repo_slug):
    """Fetch raw README.md from a GitHub repo (e.g. 'sindresorhus/awesome')."""
    urls = [
        f"https://raw.githubusercontent.com/{repo_slug}/main/README.md",
        f"https://raw.githubusercontent.com/{repo_slug}/master/README.md",
        f"https://raw.githubusercontent.com/{repo_slug}/main/readme.md",
        f"https://raw.githubusercontent.com/{repo_slug}/master/readme.md",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "toolshed-scraper/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
    return None


# Regex patterns for extracting entries from markdown list items
# Format A: - [Name](url) - Description
# Format B: - [Name](url) - Description. `source` `license` `lang`
# Format C: - [Name](url) ![badge]... - Description
ENTRY_RE = re.compile(
    r'^\s*[-*]\s+'                     # list bullet
    r'\[([^\]]+)\]'                    # [Name]
    r'\(([^)]+)\)'                     # (url)
    r'(?:\s*!\[[^\]]*\]\([^)]*\))*'   # optional badges
    r'\s*[-–—:]?\s*'                   # separator
    r'(.+)$',                          # description
    re.MULTILINE
)

# Selfhosted format extras: `source` `license` `language` at end
SELFHOSTED_SUFFIX_RE = re.compile(
    r'(?:\s*`[^`]+`)+\s*$'
)

# Section header
SECTION_RE = re.compile(r'^(#{1,4})\s+(.+)', re.MULTILINE)


def parse_readme(text, source_list=""):
    """
    Parse an awesome-list README and yield raw entry dicts.

    Yields dicts with keys:
      name, url, description, section, source_list, topics
    """
    if not text:
        return

    # Build section structure
    sections = []
    for m in SECTION_RE.finditer(text):
        level = len(m.group(1))
        title = m.group(2).strip()
        # Strip markdown links from section titles
        title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', title)
        sections.append((m.start(), level, title))

    def get_section(pos):
        """Find the nearest section header before this position."""
        best = ""
        for start, level, title in sections:
            if start < pos:
                best = title
            else:
                break
        return best

    for m in ENTRY_RE.finditer(text):
        name = m.group(1).strip()
        url = m.group(2).strip()
        desc = m.group(3).strip()

        # Skip non-software entries
        if _skip_entry(name, url, desc):
            continue

        # Clean selfhosted-style backtick suffixes from description
        desc = SELFHOSTED_SUFFIX_RE.sub('', desc).strip()
        # Remove trailing period
        desc = desc.rstrip('.')

        section = get_section(m.start())

        yield {
            "name": name,
            "url": url,
            "description": desc,
            "section": section,
            "source_list": source_list,
            "topics": _extract_topics(name, desc, section),
        }


def _skip_entry(name, url, desc):
    """Filter out non-software entries."""
    # Skip anchors, fragments, relative links
    if not url.startswith("http"):
        return True
    # Skip common non-tool links
    skip_domains = [
        "wikipedia.org", "medium.com", "dev.to", "stackoverflow.com",
        "reddit.com", "twitter.com", "x.com", "youtube.com",
        "arxiv.org", "papers.ssrn.com",
        "docs.google.com", "notion.so", "gitbook.io", "substack.com",
        "discord.gg", "slack.com", "linkedin.com", "goodreads.com",
        "amazon.com", "udemy.com", "coursera.org",
    ]
    url_lower = url.lower()
    for domain in skip_domains:
        if domain in url_lower:
            return True
    # Skip section links and meta entries
    skip_names = {"contents", "table of contents", "contributing", "license", "readme"}
    if name.lower() in skip_names:
        return True
    # Skip if description is too short to be useful
    if len(desc) < 15:
        return True
    # Skip non-software entries by description
    desc_lower = desc.lower()
    non_software_phrases = [
        "a curated list", "awesome list", "collection of resources",
        "list of ", "a guide to", "cheat sheet",
    ]
    if any(phrase in desc_lower for phrase in non_software_phrases):
        return True
    return False


def _extract_topics(name, desc, section):
    """Extract topic tags from name, description, and section."""
    topics = []
    section_lower = section.lower().replace(" ", "-") if section else ""
    if section_lower and section_lower not in ("contents", "related", "resources"):
        topics.append(section_lower)

    # Extract keywords from name
    name_parts = re.findall(r'[a-z]+', name.lower())
    for part in name_parts[:3]:
        if len(part) > 2 and part not in topics:
            topics.append(part)

    return topics[:5]


def scrape_awesome_list(repo_slug, source_label=None):
    """
    Scrape a single awesome list.
    Returns list of raw entry dicts.
    """
    label = source_label or repo_slug
    print(f"  Fetching {repo_slug}...")
    text = fetch_readme(repo_slug)
    if not text:
        print(f"  FAILED to fetch {repo_slug}")
        return []

    entries = list(parse_readme(text, source_list=label))
    print(f"  Parsed {len(entries)} entries from {label}")
    time.sleep(AWESOME_RATE_DELAY)
    return entries
