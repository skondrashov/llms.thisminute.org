#!/usr/bin/env python3
"""URL health checker for the Toolshed software catalog.

Checks each entry's URL with HTTP HEAD (fallback to GET). Reports:
- Dead links (4xx/5xx)
- Redirects (3xx — shows redirect target)
- Timeouts
- Connection errors

Usage:
    python scripts/check_urls.py                  # Check curated entries only
    python scripts/check_urls.py --all            # Check all entries including discovered
    python scripts/check_urls.py --timeout 15     # Custom timeout (default 10s)
    python scripts/check_urls.py --concurrency 20 # Parallel requests (default 10)
    python scripts/check_urls.py --output report.json  # Save JSON report
"""

import argparse
import json
import glob
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import ssl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

# User-Agent to avoid being blocked by servers that reject default Python UA
USER_AGENT = (
    "Mozilla/5.0 (compatible; ToolshedBot/1.0; "
    "+https://forge.thisminute.org/toolshed)"
)

# Default: use standard SSL verification; override with --no-verify-ssl
SSL_CONTEXT = None


def load_entries(include_discovered=False):
    """Load entries from data/*.json files.

    By default, only loads curated entries (files NOT named discovered_*.json).
    With include_discovered=True, loads all entries.
    """
    entries = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        basename = os.path.basename(path)
        if not include_discovered and basename.startswith("discovered"):
            continue
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            item["_source_file"] = basename
            entries.append(item)
    return entries


def check_url(entry, timeout=10, max_redirects=3):
    """Check a single URL. Returns a result dict.

    Tries HEAD first, falls back to GET if HEAD returns 405 or fails.
    Follows redirects manually to track the chain (up to max_redirects).
    """
    url = entry.get("url", "")
    entry_id = entry.get("id", "???")
    name = entry.get("name", "???")
    source_file = entry.get("_source_file", "???")

    result = {
        "id": entry_id,
        "name": name,
        "url": url,
        "category": entry.get("category", "???"),
        "source_file": source_file,
        "status": None,
        "status_code": None,
        "redirect_chain": [],
        "final_url": url,
        "error": None,
    }

    if not url or not url.startswith(("http://", "https://")):
        result["status"] = "invalid"
        result["error"] = "Invalid or missing URL"
        return result

    current_url = url
    redirect_chain = []

    for redirect_count in range(max_redirects + 1):
        for method in ["HEAD", "GET"]:
            try:
                req = Request(
                    current_url,
                    method=method,
                    headers={"User-Agent": USER_AGENT},
                )
                response = urlopen(
                    req, timeout=timeout, context=SSL_CONTEXT
                )
                code = response.getcode()
                final_url = response.geturl()

                # Check if we were redirected
                if final_url != current_url:
                    redirect_chain.append(final_url)
                    if redirect_count < max_redirects:
                        current_url = final_url
                        break  # Follow redirect
                    else:
                        result["status"] = "too_many_redirects"
                        result["redirect_chain"] = redirect_chain
                        result["final_url"] = final_url
                        return result

                result["status_code"] = code
                result["final_url"] = final_url
                if redirect_chain:
                    result["status"] = "redirect"
                    result["redirect_chain"] = redirect_chain
                elif 200 <= code < 300:
                    result["status"] = "ok"
                else:
                    result["status"] = "error"
                return result

            except HTTPError as e:
                code = e.code
                # If HEAD returned 405 Method Not Allowed, try GET
                if method == "HEAD" and code == 405:
                    continue
                # If HEAD returned 403/406, some servers block HEAD — try GET
                if method == "HEAD" and code in (403, 406):
                    continue

                result["status_code"] = code
                if 300 <= code < 400:
                    # Redirect via error (some servers do this)
                    location = e.headers.get("Location", "")
                    if location:
                        redirect_chain.append(location)
                        if redirect_count < max_redirects:
                            current_url = location
                            break  # Follow redirect
                    result["status"] = "redirect"
                    result["redirect_chain"] = redirect_chain
                elif 400 <= code < 500:
                    result["status"] = "client_error"
                    result["error"] = f"HTTP {code}"
                elif code >= 500:
                    result["status"] = "server_error"
                    result["error"] = f"HTTP {code}"
                else:
                    result["status"] = "error"
                    result["error"] = f"HTTP {code}"
                return result

            except URLError as e:
                if method == "HEAD":
                    continue  # Try GET
                result["status"] = "connection_error"
                result["error"] = str(e.reason)
                return result

            except TimeoutError:
                if method == "HEAD":
                    continue
                result["status"] = "timeout"
                result["error"] = f"Timed out after {timeout}s"
                return result

            except OSError as e:
                if method == "HEAD":
                    continue
                result["status"] = "connection_error"
                result["error"] = str(e)
                return result

            except Exception as e:
                if method == "HEAD":
                    continue
                result["status"] = "error"
                result["error"] = f"{type(e).__name__}: {e}"
                return result
        else:
            # Both HEAD and GET failed for this redirect step — already returned
            break

    return result


def format_result(r):
    """Format a single result for display."""
    lines = [f"  {r['name']} ({r['id']})"]
    lines.append(f"    URL: {r['url']}")
    lines.append(f"    Category: {r['category']}  |  File: {r['source_file']}")
    if r["status_code"]:
        lines.append(f"    Status: HTTP {r['status_code']}")
    if r["error"]:
        lines.append(f"    Error: {r['error']}")
    if r["redirect_chain"]:
        lines.append(f"    Redirects to: {r['final_url']}")
        if len(r["redirect_chain"]) > 1:
            lines.append(f"    Chain: {' -> '.join(r['redirect_chain'])}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check URL health for Toolshed catalog entries"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Check all entries including discovered (default: curated only)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent requests (default: 10)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write JSON report to this file (e.g., --output report.json)",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification (not recommended)",
    )
    args = parser.parse_args()

    # Override SSL context if requested
    global SSL_CONTEXT
    if args.no_verify_ssl:
        SSL_CONTEXT = ssl.create_default_context()
        SSL_CONTEXT.check_hostname = False
        SSL_CONTEXT.verify_mode = ssl.CERT_NONE

    entries = load_entries(include_discovered=args.all)
    scope = "all" if args.all else "curated"
    print(f"Checking {len(entries)} {scope} entries (timeout={args.timeout}s, concurrency={args.concurrency})")
    print()

    # Deduplicate by URL to avoid hitting the same URL multiple times
    seen_urls = set()
    unique_entries = []
    for e in entries:
        url = e.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_entries.append(e)
        # Still keep all entries in results, just check URL once

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        future_to_entry = {
            executor.submit(check_url, entry, args.timeout): entry
            for entry in unique_entries
        }
        completed = 0
        total = len(unique_entries)
        for future in as_completed(future_to_entry):
            result = future.result()
            results.append(result)
            completed += 1
            if completed % 50 == 0 or completed == total:
                elapsed = time.time() - start_time
                print(f"  Progress: {completed}/{total} checked ({elapsed:.1f}s elapsed)", flush=True)

    elapsed = time.time() - start_time
    print(f"\nCompleted in {elapsed:.1f}s\n")

    # Categorize results
    ok = [r for r in results if r["status"] == "ok"]
    redirects = [r for r in results if r["status"] == "redirect"]
    dead = [r for r in results if r["status"] in ("client_error", "server_error")]
    timeouts = [r for r in results if r["status"] == "timeout"]
    conn_errors = [r for r in results if r["status"] == "connection_error"]
    too_many = [r for r in results if r["status"] == "too_many_redirects"]
    invalid = [r for r in results if r["status"] == "invalid"]
    other_errors = [r for r in results if r["status"] == "error"]

    # Print summary
    print("=" * 60)
    print(f"SUMMARY ({len(results)} URLs checked)")
    print(f"  OK (2xx):            {len(ok)}")
    print(f"  Redirects (3xx):     {len(redirects)}")
    print(f"  Client errors (4xx): {len(dead)}")
    # Separate 4xx and 5xx in dead list
    client_errs = [r for r in dead if r.get("status_code") and 400 <= r["status_code"] < 500]
    server_errs = [r for r in dead if r.get("status_code") and r["status_code"] >= 500]
    if client_errs:
        print(f"    4xx breakdown:     " + ", ".join(
            f"{code}: {count}" for code, count in
            sorted(defaultdict(int, {r["status_code"]: sum(1 for x in client_errs if x["status_code"] == r["status_code"]) for r in client_errs}).items())
        ))
    print(f"  Server errors (5xx): {len(server_errs)}")
    print(f"  Timeouts:            {len(timeouts)}")
    print(f"  Connection errors:   {len(conn_errors)}")
    print(f"  Too many redirects:  {len(too_many)}")
    print(f"  Invalid URLs:        {len(invalid)}")
    print(f"  Other errors:        {len(other_errors)}")
    print("=" * 60)

    # Print details for problematic URLs
    problems = dead + timeouts + conn_errors + too_many + invalid + other_errors
    if problems:
        print(f"\n--- DEAD / ERROR URLS ({len(problems)}) ---\n")
        for r in sorted(problems, key=lambda x: x["status"]):
            print(f"  [{r['status'].upper()}] {format_result(r)}")
            print()

    if redirects:
        print(f"\n--- REDIRECTS ({len(redirects)}) ---\n")
        for r in sorted(redirects, key=lambda x: x["name"]):
            print(f"  {r['name']} ({r['id']})")
            print(f"    {r['url']}  ->  {r['final_url']}")
            print()

    # Write JSON report if requested
    if args.output:
        report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "scope": scope,
            "total_checked": len(results),
            "summary": {
                "ok": len(ok),
                "redirects": len(redirects),
                "client_errors": len(client_errs),
                "server_errors": len(server_errs),
                "timeouts": len(timeouts),
                "connection_errors": len(conn_errors),
                "too_many_redirects": len(too_many),
                "invalid": len(invalid),
                "other_errors": len(other_errors),
            },
            "problems": [
                {k: v for k, v in r.items() if not k.startswith("_")}
                for r in problems
            ],
            "redirects": [
                {k: v for k, v in r.items() if not k.startswith("_")}
                for r in redirects
            ],
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nJSON report written to: {args.output}")

    # Exit code
    if problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
