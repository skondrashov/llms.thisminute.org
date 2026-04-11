"""
Scraper for CNCF Landscape data — cloud-native projects.
Source: https://landscape.cncf.io/ (JSON data available on GitHub)
"""

import json
import urllib.request


# The CNCF landscape publishes its full dataset
LANDSCAPE_URL = "https://raw.githubusercontent.com/cncf/landscape/master/landscape.yml"
# But the processed JSON is easier to parse
LANDSCAPE_JSON_URL = "https://landscape.cncf.io/data/items.json"


def fetch_landscape():
    """Fetch CNCF Landscape items as JSON."""
    print("  Fetching CNCF Landscape data...")
    req = urllib.request.Request(LANDSCAPE_JSON_URL, headers={
        "User-Agent": "toolshed-scraper/1.0",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list):
            print(f"  Got {len(data)} CNCF items")
            return data
        elif isinstance(data, dict):
            # Might be wrapped in a key
            for key in ("items", "data", "entries"):
                if key in data and isinstance(data[key], list):
                    print(f"  Got {len(data[key])} CNCF items")
                    return data[key]
            print(f"  Got CNCF data (dict with {len(data)} keys)")
            return [data]
    except Exception as e:
        print(f"  Failed to fetch {LANDSCAPE_JSON_URL}: {e}")

    return []


# CNCF category -> our category mapping
CNCF_CATEGORY_MAP = {
    "app definition and development": "CI/CD Tools",
    "orchestration & management": "Container Orchestration",
    "runtime": "Container Orchestration",
    "provisioning": "Infrastructure as Code",
    "observability and analysis": "Monitoring & Metrics",
    "platform": "Cloud SDKs & CLIs",
    "serverless": "Cloud SDKs & CLIs",
    "wasm": "Web Frameworks",
    "database": "Databases",
    "streaming & messaging": "Data Pipelines",
    "key management": "Secrets Management",
    "container security": "Security Scanning",
    "security & compliance": "Security Scanning",
    "api gateway": "API Clients",
    "service mesh": "Container Orchestration",
    "service proxy": "VPN",
    "automation & configuration": "Infrastructure as Code",
    "container registry": "Container Orchestration",
    "continuous integration & delivery": "CI/CD Tools",
    "logging": "Log Management",
    "monitoring": "Monitoring & Metrics",
    "tracing": "Monitoring & Metrics",
    "chaos engineering": "Load & Performance Testing",
}


def _item_to_raw(item):
    """Convert a CNCF Landscape item to our raw format."""
    name = item.get("name", "")
    desc = item.get("description", "") or item.get("extra", {}).get("summary", "")
    homepage = item.get("homepage_url", "") or item.get("homepage", "")
    repo_url = item.get("repo_url", "") or item.get("github_url", "")

    # Category from CNCF
    cncf_cat = (item.get("category", "") or item.get("subcategory", "")).lower()
    our_cat = None
    for pattern, cat in CNCF_CATEGORY_MAP.items():
        if pattern in cncf_cat:
            our_cat = cat
            break

    topics = ["cloud-native", "cncf"]
    if cncf_cat:
        topics.append(cncf_cat.replace(" ", "-"))

    raw = {
        "name": name,
        "description": desc,
        "url": homepage or repo_url,
        "homepage": homepage,
        "source_url": repo_url,
        "source_list": "cncf-landscape",
        "topics": topics[:5],
    }
    if our_cat:
        raw["category"] = our_cat

    return raw


def scrape_cncf_landscape():
    """Scrape CNCF Landscape and return raw entry dicts."""
    items = fetch_landscape()
    results = []
    for item in items:
        raw = _item_to_raw(item)
        if raw["name"] and raw["url"]:
            results.append(raw)
    print(f"  CNCF Landscape: {len(results)} valid entries")
    return results
