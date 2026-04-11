#!/usr/bin/env python3
"""Aggregate data/*.json into data.js, api/v1/catalog.json, api/v1/categories.json, llms.txt, llms-full.txt, inject noscript catalog and JSON-LD structured data into index.html."""
import argparse, json, glob, os, re, sys, html as html_mod
from itertools import groupby

script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(script_dir, "data")

# --- Parse arguments ---
parser = argparse.ArgumentParser(description="Build toolshed site data")
parser.add_argument("--strict", action="store_true",
                    help="Exclude low-confidence discovered entries (Tier 3 only)")
args = parser.parse_args()

entries = []
curated_ids = set()  # Track curated (non-discovered) entry IDs
discovered_ids = set()  # Track discovered entry IDs for strict filtering
seen_ids = set()
files = sorted(glob.glob(os.path.join(data_dir, "*.json")))

for path in files:
    basename = os.path.basename(path)
    is_discovered = basename.startswith("discovered")
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    for item in items:
        if "id" not in item:
            continue
        if item["id"] in seen_ids:
            print(f"  WARN: duplicate id '{item['id']}' in {basename}, skipping")
            continue
        seen_ids.add(item["id"])
        entries.append(item)
        if not is_discovered:
            curated_ids.add(item["id"])
        else:
            discovered_ids.add(item["id"])

# --- Strict mode: filter out low-confidence discovered entries ---
if args.strict:
    # Add scrape package to path so we can import categorize
    sys.path.insert(0, script_dir)
    from scrape.categorize import get_confidence_tier, build_category_index

    print("Strict mode: evaluating discovered entry confidence...")
    category_index = build_category_index()

    before_count = len(entries)
    tier_counts = {0: 0, 1: 0, 2: 0, 3: 0, None: 0}
    strict_excluded = 0
    kept_entries = []

    category_disagreements = 0

    for entry in entries:
        if entry["id"] not in discovered_ids:
            kept_entries.append(entry)
            continue
        tier, assigned_cat = get_confidence_tier(entry, category_index)
        tier_counts[tier] += 1
        if tier == 3 or tier is None:
            strict_excluded += 1
        elif assigned_cat and entry.get("category") != assigned_cat:
            # T1/T2 but keyword assigns a different category than stored
            category_disagreements += 1
            strict_excluded += 1
        else:
            kept_entries.append(entry)

    entries = kept_entries
    print(f"  Discovered tier distribution: T0={tier_counts[0]}, T1={tier_counts[1]}, "
          f"T2={tier_counts[2]}, T3={tier_counts[3]}, unmatched={tier_counts[None]}")
    print(f"  Strict filter: excluded {strict_excluded} (T3/unmatched: {strict_excluded - category_disagreements}, "
          f"category disagreement: {category_disagreements}), kept {before_count - strict_excluded} "
          f"(was {before_count})")

entries.sort(key=lambda e: (e.get("category", ""), e.get("name", "")))

categories = {}
for e in entries:
    cat = e.get("category", "Uncategorized")
    categories[cat] = categories.get(cat, 0) + 1

sorted_categories = sorted(categories.items(), key=lambda x: -x[1])

# --- Output 1: data.js (frontend) ---
out_path = os.path.join(script_dir, "data.js")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("window.SOFTWARE = ")
    json.dump(entries, f, indent=2, ensure_ascii=False)
    f.write(";\n")

# --- Output 2: api/v1/catalog.json (machine-readable catalog) ---
api_dir = os.path.join(script_dir, "api", "v1")
os.makedirs(api_dir, exist_ok=True)

catalog_path = os.path.join(api_dir, "catalog.json")
with open(catalog_path, "w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2, ensure_ascii=False)
    f.write("\n")

# --- Output 3: api/v1/categories.json (category counts) ---
categories_path = os.path.join(api_dir, "categories.json")
with open(categories_path, "w", encoding="utf-8") as f:
    json.dump(dict(sorted_categories), f, indent=2, ensure_ascii=False)
    f.write("\n")

# --- Output 4: llms.txt (AI agent discovery manifest) ---
llms_lines = []
llms_lines.append("# toolshed")
llms_lines.append(f"> Universal software directory with {len(entries)} entries across {len(categories)} categories. Structured data for AI agents and developers.")
llms_lines.append("")
llms_lines.append("## Endpoints")
llms_lines.append("- Full catalog (JSON): /api/v1/catalog.json")
llms_lines.append("- Categories with counts: /api/v1/categories.json")
llms_lines.append("- Entry schema: /schema.json")
llms_lines.append("- Full text catalog: /llms-full.txt")
llms_lines.append("- Human browsable: /")
llms_lines.append("")
llms_lines.append("## Entry Schema")
llms_lines.append("{ id, name, description, url, category, os[], pricing, tags[], source?, language?, triage? }")
llms_lines.append("")
llms_lines.append("## Triage (ideas only)")
llms_lines.append("Ideas (status: idea/in-progress) have a triage object: { impact: high|medium|low, buildability: straightforward|moderate|hard, alternatives: none|partial|covered, alternatives_note: string }")
llms_lines.append("Filter out covered, sort by impact desc then buildability asc.")
llms_lines.append("")
llms_lines.append("Pricing: free | freemium | paid | subscription")
llms_lines.append("OS: windows | macos | linux | web | ios | android")
llms_lines.append("")
llms_lines.append("## Categories")
for cat, count in sorted_categories:
    llms_lines.append(f"- {cat}: {count}")
llms_lines.append("")
llms_lines.append("## Querying")
llms_lines.append("Download /api/v1/catalog.json and filter by:")
llms_lines.append("- category: exact match on category field")
llms_lines.append("- os: check if desired OS is in the os[] array")
llms_lines.append("- pricing: exact match (free, freemium, paid, subscription)")
llms_lines.append("- tags: check if desired tag is in tags[] array")
llms_lines.append("- language: filter libraries by ecosystem (python, rust, go, javascript, etc.)")
llms_lines.append("- status: idea (unfulfilled request), submitted (built by AI forge), or absent (existing software)")
llms_lines.append("- text search: match against name, description, tags")
llms_lines.append("")
llms_lines.append("## Example Queries")
llms_lines.append('- "Find free image editors for Linux": filter pricing=free, os contains "linux", category="Image Editors"')
llms_lines.append('- "Python HTTP libraries": filter language="python", category="HTTP Libraries"')
llms_lines.append('- "All database tools": filter category in ["Databases", "Database Tools", "ORMs"]')

llms_path = os.path.join(script_dir, "llms.txt")
with open(llms_path, "w", encoding="utf-8") as f:
    f.write("\n".join(llms_lines))
    f.write("\n")

# --- Output 4b: llms-full.txt (complete catalog in plain text) ---
full_lines = []
full_lines.append("# toolshed — Full Catalog")
full_lines.append(f"> {len(entries)} entries across {len(categories)} categories")
full_lines.append("")

for cat, group in groupby(entries, key=lambda e: e.get("category", "Uncategorized")):
    cat_entries = list(group)
    full_lines.append(f"## {cat} ({len(cat_entries)})")
    full_lines.append("")
    for entry in cat_entries:
        full_lines.append(f"### {entry['name']}")
        full_lines.append(f"- URL: {entry.get('url', '')}")
        full_lines.append(f"- Description: {entry.get('description', '')}")
        os_list = entry.get("os", [])
        if os_list:
            full_lines.append(f"- OS: {', '.join(os_list)}")
        full_lines.append(f"- Pricing: {entry.get('pricing', '')}")
        tags = entry.get("tags", [])
        if tags:
            full_lines.append(f"- Tags: {', '.join(tags)}")
        source = entry.get("source")
        if source:
            full_lines.append(f"- Source: {source}")
        language = entry.get("language")
        if language:
            full_lines.append(f"- Language: {language}")
        triage = entry.get("triage")
        if triage:
            full_lines.append(f"- Triage: impact={triage.get('impact','?')}, buildability={triage.get('buildability','?')}, alternatives={triage.get('alternatives','?')}")
            alt_note = triage.get("alternatives_note")
            if alt_note:
                full_lines.append(f"- Alternatives note: {alt_note}")
        full_lines.append("")

llms_full_path = os.path.join(script_dir, "llms-full.txt")
with open(llms_full_path, "w", encoding="utf-8") as f:
    f.write("\n".join(full_lines))

# --- Output 5: taxonomy.js (tree navigation data) ---
taxonomy_path_src = os.path.join(script_dir, "taxonomy.json")
if os.path.exists(taxonomy_path_src):
    with open(taxonomy_path_src, encoding="utf-8") as f:
        taxonomy = json.load(f)
    taxonomy_js_path = os.path.join(script_dir, "taxonomy.js")
    with open(taxonomy_js_path, "w", encoding="utf-8") as f:
        f.write("window.TAXONOMY = ")
        json.dump(taxonomy, f, indent=2, ensure_ascii=False)
        f.write(";\n")
    print(f"Built taxonomy.js from taxonomy.json")

# --- Output 6: inject noscript catalog into index.html ---
index_path = os.path.join(script_dir, "index.html")
if os.path.exists(index_path):
    with open(index_path, encoding="utf-8") as f:
        index_html = f.read()

    marker_pattern = re.compile(
        r"(<!-- NOSCRIPT_CATALOG -->).*?(<!-- /NOSCRIPT_CATALOG -->)",
        re.DOTALL,
    )

    if marker_pattern.search(index_html):
        # Group entries by category (preserving sorted order)
        cats_ordered = []
        cats_entries = {}
        for e in entries:
            cat = e.get("category", "Uncategorized")
            if cat not in cats_entries:
                cats_ordered.append(cat)
                cats_entries[cat] = []
            cats_entries[cat].append(e)

        # Build noscript HTML
        h = html_mod.escape
        lines = []
        lines.append("")
        lines.append("  <noscript>")
        lines.append(f"  <h1>Toolshed — Software for Everything</h1>")
        lines.append(f"  <p>{len(entries)} entries across {len(categories)} categories.</p>")
        for cat in cats_ordered:
            cat_entries = cats_entries[cat]
            lines.append(f"  <h2>{h(cat)}</h2>")
            for e in cat_entries:
                name = h(e.get("name", ""))
                url = h(e.get("url", ""))
                desc = h(e.get("description", ""))
                os_list = ", ".join(e.get("os", []))
                pricing = e.get("pricing", "")
                tags = ", ".join(e.get("tags", []))
                meta_parts = []
                if os_list:
                    meta_parts.append(f"OS: {h(os_list)}")
                if pricing:
                    meta_parts.append(f"Pricing: {h(pricing)}")
                if tags:
                    meta_parts.append(f"Tags: {h(tags)}")
                meta_str = " | ".join(meta_parts)
                lines.append(f"  <article>")
                lines.append(f"    <h3><a href=\"{url}\">{name}</a></h3>")
                lines.append(f"    <p>{desc}</p>")
                if meta_str:
                    lines.append(f"    <small>{meta_str}</small>")
                lines.append(f"  </article>")
        lines.append("  </noscript>")
        lines.append("  ")

        noscript_block = "\n".join(lines)
        # Build replacement: keep both marker comments with generated content between them
        def _replace_markers(m):
            return m.group(1) + noscript_block + m.group(2)
        index_html = marker_pattern.sub(_replace_markers, index_html)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)
        print(f"Injected noscript catalog into index.html ({len(entries)} entries)")
    else:
        print("WARN: noscript markers not found in index.html, skipping injection")

    # --- Output 7: inject JSON-LD structured data into index.html ---
    # Re-read index.html in case noscript injection modified it
    with open(index_path, encoding="utf-8") as f:
        index_html = f.read()

    jsonld_marker = re.compile(
        r"(<!-- JSONLD -->).*?(<!-- /JSONLD -->)",
        re.DOTALL,
    )

    if jsonld_marker.search(index_html):
        # --- Build sampled entry list ---
        # Strategy: all curated entries + up to 3 entries per category from discovered
        # to keep the JSON-LD block under ~500KB
        cats_entries_map = {}
        for e in entries:
            cat = e.get("category", "Uncategorized")
            if cat not in cats_entries_map:
                cats_entries_map[cat] = {"curated": [], "discovered": []}
            if e["id"] in curated_ids:
                cats_entries_map[cat]["curated"].append(e)
            else:
                cats_entries_map[cat]["discovered"].append(e)

        sampled_entries = []
        for cat in sorted(cats_entries_map.keys()):
            bucket = cats_entries_map[cat]
            # Include all curated entries
            sampled_entries.extend(bucket["curated"])
            # Include up to 2 discovered entries per category for representation
            # This keeps the JSON-LD block near the ~500KB target
            remaining_slots = max(0, 5 - len(bucket["curated"]))
            sampled_entries.extend(bucket["discovered"][:min(2, remaining_slots)])

        # --- Map OS values to schema.org operatingSystem ---
        OS_MAP = {
            "windows": "Windows",
            "macos": "macOS",
            "linux": "Linux",
            "web": "Web",
            "ios": "iOS",
            "android": "Android",
        }

        def entry_to_schema(entry):
            """Convert a catalog entry to a schema.org SoftwareApplication dict."""
            app = {
                "@type": "SoftwareApplication",
                "name": entry.get("name", ""),
                "url": entry.get("url", ""),
                "applicationCategory": entry.get("category", ""),
            }
            desc = entry.get("description", "")
            if desc:
                app["description"] = desc
            os_list = entry.get("os", [])
            if os_list:
                mapped = [OS_MAP.get(o, o) for o in os_list]
                app["operatingSystem"] = ", ".join(mapped)
            pricing = entry.get("pricing", "")
            if pricing == "free":
                app["offers"] = {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "USD",
                }
            elif pricing in ("freemium", "paid", "subscription"):
                app["offers"] = {
                    "@type": "Offer",
                    "price": "",
                    "priceCurrency": "USD",
                    "description": pricing.capitalize(),
                }
            return app

        # --- Build JSON-LD graph ---
        jsonld_graph = [
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Toolshed",
                "url": "https://forge.thisminute.org/toolshed",
                "description": f"Universal software directory. Browse apps, libraries, protocols, and platforms across {len(categories)}+ categories.",
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": "https://forge.thisminute.org/tools/#search={search_term_string}",
                    "query-input": "required name=search_term_string",
                },
            },
            {
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": "Toolshed Software Directory",
                "url": "https://forge.thisminute.org/toolshed",
                "description": f"Curated software directory with {len(entries)} entries across {len(categories)} categories.",
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(entries),
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": i + 1,
                            "item": entry_to_schema(e),
                        }
                        for i, e in enumerate(sampled_entries)
                    ],
                },
            },
        ]

        jsonld_str = json.dumps(jsonld_graph, indent=None, ensure_ascii=False, separators=(",", ":"))
        jsonld_block = f'\n  <script type="application/ld+json">{jsonld_str}</script>\n  '
        jsonld_size_kb = len(jsonld_block.encode("utf-8")) / 1024

        def _replace_jsonld(m):
            return m.group(1) + jsonld_block + m.group(2)

        index_html = jsonld_marker.sub(_replace_jsonld, index_html)

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)
        print(f"Injected JSON-LD into index.html ({len(sampled_entries)} sampled entries, {jsonld_size_kb:.1f} KB)")
    else:
        print("WARN: JSONLD markers not found in index.html, skipping JSON-LD injection")
else:
    print("WARN: index.html not found, skipping noscript and JSON-LD injection")

# --- Summary ---
print(f"Built data.js with {len(entries)} entries from {len(files)} files")
print(f"Built api/v1/catalog.json ({len(entries)} entries)")
print(f"Built api/v1/categories.json ({len(categories)} categories)")
print(f"Built llms.txt ({len(entries)} entries, {len(categories)} categories)")
print(f"Built llms-full.txt ({len(entries)} entries, {len(categories)} categories)")
for cat, count in sorted_categories:
    print(f"  {cat}: {count}")
