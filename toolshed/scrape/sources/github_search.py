"""
GitHub Search API client for discovering software tools.

Shards queries by topic + star ranges to work around the 1000-result limit.
Requires GITHUB_TOKEN env var for authenticated rate limits (30 search/min).
"""

import json
import time
import urllib.request
import urllib.error
from ..config import GITHUB_TOKEN, SEARCH_RATE_DELAY, CORE_RATE_DELAY


GITHUB_API = "https://api.github.com"

# Search queries: (query_string, min_stars)
# Each yields repos matching the topic with enough stars to be notable
SEARCH_QUERIES = [
    # Dev tools
    ("topic:cli tool", 500),
    ("topic:terminal", 500),
    ("topic:editor", 1000),
    ("topic:ide", 1000),
    ("topic:devtools", 500),
    ("topic:developer-tools", 500),

    # Web
    ("topic:web-framework", 500),
    ("topic:static-site-generator", 300),
    ("topic:cms", 500),
    ("topic:http-client", 300),
    ("topic:graphql", 500),
    ("topic:websocket", 300),
    ("topic:api", 1000),

    # Data & databases
    ("topic:database", 1000),
    ("topic:orm", 300),
    ("topic:search-engine", 500),
    ("topic:data-visualization", 500),
    ("topic:data-pipeline", 300),
    ("topic:etl", 300),

    # AI/ML
    ("topic:machine-learning", 2000),
    ("topic:deep-learning", 2000),
    ("topic:llm", 1000),
    ("topic:nlp", 1000),

    # DevOps
    ("topic:docker", 1000),
    ("topic:kubernetes", 1000),
    ("topic:ci-cd", 500),
    ("topic:monitoring", 500),
    ("topic:infrastructure-as-code", 300),

    # Security
    ("topic:security", 1000),
    ("topic:password-manager", 200),
    ("topic:encryption", 500),
    ("topic:authentication", 500),

    # Desktop apps
    ("topic:desktop-app", 500),
    ("topic:electron", 500),

    # Mobile
    ("topic:react-native", 1000),
    ("topic:flutter", 1000),
    ("topic:ios", 1000),
    ("topic:android", 1000),

    # Testing
    ("topic:testing", 500),
    ("topic:testing-framework", 300),
    ("topic:e2e-testing", 200),
    ("topic:load-testing", 200),

    # Productivity
    ("topic:note-taking", 200),
    ("topic:project-management", 300),
    ("topic:calendar", 200),
    ("topic:email-client", 200),

    # System
    ("topic:file-manager", 200),
    ("topic:window-manager", 200),
    ("topic:shell", 500),
    ("topic:operating-system", 500),

    # Creative
    ("topic:image-processing", 300),
    ("topic:video-editing", 200),
    ("topic:music", 300),
    ("topic:game-engine", 500),
    ("topic:3d", 500),

    # Selfhosted
    ("topic:self-hosted", 500),
    ("topic:selfhosted", 500),
]


def _headers():
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "mainmenu-scraper/1.0",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _api_get(url, params=None):
    """Make a GET request to GitHub API with rate limiting."""
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"

    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Rate limited — check reset time
            reset = e.headers.get("X-RateLimit-Reset")
            if reset:
                wait = max(1, int(reset) - int(time.time()) + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(min(wait, 60))
                return _api_get(url)  # retry once
            print(f"  Rate limited (no reset header), waiting 60s...")
            time.sleep(60)
            return _api_get(url)
        elif e.code == 422:
            print(f"  Unprocessable query: {url}")
            return None
        else:
            print(f"  GitHub API error {e.code}: {e.reason}")
            return None
    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def search_repos(query, min_stars=500, max_results=100):
    """
    Search GitHub repos by query string.
    Returns list of raw repo dicts.
    """
    results = []
    per_page = min(100, max_results)
    pages = (max_results + per_page - 1) // per_page

    full_query = f"{query} stars:>={min_stars}"

    for page in range(1, pages + 1):
        print(f"  Searching: {full_query} (page {page})...")
        data = _api_get(f"{GITHUB_API}/search/repositories", {
            "q": full_query,
            "sort": "stars",
            "order": "desc",
            "per_page": per_page,
            "page": page,
        })

        if not data or "items" not in data:
            break

        for repo in data["items"]:
            results.append(_repo_to_raw(repo))

        if len(data["items"]) < per_page:
            break  # no more pages

        time.sleep(SEARCH_RATE_DELAY)

    return results


def _repo_to_raw(repo):
    """Convert a GitHub API repo object to our raw entry format."""
    return {
        "name": repo.get("name", ""),
        "description": repo.get("description") or "",
        "url": repo.get("homepage") or repo.get("html_url", ""),
        "homepage": repo.get("homepage") or "",
        "source_url": repo.get("html_url", ""),
        "github_url": repo.get("html_url", ""),
        "language": repo.get("language") or "",
        "topics": repo.get("topics", []),
        "license": (repo.get("license") or {}).get("spdx_id", ""),
        "stars": repo.get("stargazers_count", 0),
        "source_list": "github-search",
    }


def scrape_github_search(queries=None, max_per_query=100):
    """
    Run all search queries and collect results.
    Returns list of raw entry dicts.
    """
    if queries is None:
        queries = SEARCH_QUERIES

    all_results = []
    seen_urls = set()

    for query_str, min_stars in queries:
        results = search_repos(query_str, min_stars=min_stars, max_results=max_per_query)

        for entry in results:
            url = entry.get("source_url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(entry)

        time.sleep(SEARCH_RATE_DELAY)

    print(f"  GitHub search total: {len(all_results)} unique repos")
    return all_results
