"""
Scraper for Homebrew Cask API — macOS desktop applications.
Endpoint: https://formulae.brew.sh/api/cask.json (no auth needed)
"""

import json
import urllib.request


CASK_API_URL = "https://formulae.brew.sh/api/cask.json"


def fetch_casks():
    """Fetch all Homebrew Cask entries."""
    print("  Fetching Homebrew Cask API...")
    req = urllib.request.Request(CASK_API_URL, headers={
        "User-Agent": "mainmenu-scraper/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        print(f"  Got {len(data)} casks")
        return data
    except Exception as e:
        print(f"  Failed to fetch casks: {e}")
        return []


def _cask_to_raw(cask):
    """Convert a Homebrew Cask entry to our raw format."""
    name = cask.get("name", [])
    if isinstance(name, list):
        name = name[0] if name else cask.get("token", "")

    desc = cask.get("desc") or ""
    homepage = cask.get("homepage") or ""
    token = cask.get("token", "")

    # Build topics from cask metadata
    topics = []
    if token:
        # Extract keywords from token (e.g., "visual-studio-code" -> ["visual", "studio", "code"])
        parts = token.split("-")
        topics.extend(p for p in parts if len(p) > 2)

    return {
        "name": name,
        "description": desc,
        "url": homepage,
        "homepage": homepage,
        "source_list": "homebrew-cask",
        "topics": topics[:5],
    }


def scrape_homebrew_casks():
    """Scrape Homebrew Cask and return raw entry dicts."""
    casks = fetch_casks()
    results = []
    for cask in casks:
        raw = _cask_to_raw(cask)
        if raw["name"] and raw["url"]:
            results.append(raw)
    print(f"  Homebrew Cask: {len(results)} valid entries")
    return results
