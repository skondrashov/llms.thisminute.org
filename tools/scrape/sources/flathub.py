"""
Scraper for Flathub API — Linux desktop applications.
Endpoint: https://flathub.org/api/v2/appstream (no auth needed)
"""

import json
import urllib.request


FLATHUB_API = "https://flathub.org/api/v2/appstream"


def fetch_apps():
    """Fetch all Flathub app IDs then fetch details."""
    print("  Fetching Flathub app list...")
    req = urllib.request.Request(FLATHUB_API, headers={
        "User-Agent": "toolshed-scraper/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            app_ids = json.loads(resp.read().decode("utf-8"))
        print(f"  Got {len(app_ids)} app IDs")
        return app_ids
    except Exception as e:
        print(f"  Failed to fetch Flathub apps: {e}")
        return []


def fetch_app_details(app_id):
    """Fetch details for a single Flathub app."""
    url = f"{FLATHUB_API}/{app_id}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "toolshed-scraper/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _app_to_raw(app_data, app_id):
    """Convert a Flathub app entry to our raw format."""
    name = app_data.get("name", "")
    summary = app_data.get("summary", "")
    # Flathub uses app IDs like "org.gnome.Calculator"
    homepage = app_data.get("urls", {}).get("homepage", "")
    if not homepage:
        homepage = f"https://flathub.org/apps/{app_id}"

    # Categories from Flathub
    categories = app_data.get("categories", [])
    topics = [c.lower().replace(" ", "-") for c in categories[:5]]

    return {
        "name": name,
        "description": summary,
        "url": homepage,
        "homepage": homepage,
        "source_list": "flathub",
        "topics": topics,
    }


def scrape_flathub(max_apps=2000):
    """
    Scrape Flathub apps. Fetches the app list then individual details.
    Limited to max_apps to avoid hammering the API.
    """
    app_ids = fetch_apps()
    if not app_ids:
        return []

    # The appstream endpoint returns a list of app IDs
    # We need to fetch each one individually or use a bulk endpoint
    # Try the summary endpoint first
    results = []
    count = 0

    for app_id in app_ids[:max_apps]:
        if not isinstance(app_id, str):
            continue
        details = fetch_app_details(app_id)
        if not details:
            continue

        raw = _app_to_raw(details, app_id)
        if raw["name"] and raw["url"]:
            results.append(raw)

        count += 1
        if count % 100 == 0:
            print(f"  Flathub: fetched {count}/{min(len(app_ids), max_apps)}...")

    print(f"  Flathub: {len(results)} valid entries")
    return results
