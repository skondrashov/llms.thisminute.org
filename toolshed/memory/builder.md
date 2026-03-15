# Builder Memory

## 2026-03-14: JSON-LD Structured Data

### What was done
- Added JSON-LD generation to `build.py` (Output 7) -- generates `WebSite` + `CollectionPage`/`ItemList` with `SoftwareApplication` entries
- Uses marker-based injection (`<!-- JSONLD -->...<!-- /JSONLD -->`) in `index.html`, same pattern as noscript
- Sampled approach: all ~1,125 curated entries + up to 2 discovered per category (capped at 5 total per category)
- Result: 1,153 sampled entries, 455.6 KB JSON-LD block

### Key learnings
- Curated vs discovered tracking requires knowing the source filename during loading -- added `curated_ids` set and `is_discovered` flag based on `basename.startswith("discovered")`
- JSON-LD with `separators=(",",":")` (no whitespace) keeps size manageable -- indented JSON would be 2-3x larger
- The `numberOfItems` in `ItemList` reflects the full catalog count (15,803) while `itemListElement` only contains the sampled subset -- this is intentional to signal total catalog size to crawlers
- Schema.org `Offer` with empty `price` + `description` field is the correct way to represent freemium/paid/subscription pricing

### Files modified
- `build.py` -- added `curated_ids` tracking, JSON-LD generation section (Output 7)
- `index.html` -- added `<!-- JSONLD --><!-- /JSONLD -->` markers before `</head>`

### Current build outputs
1. `data.js` -- Frontend JS
2. `api/v1/catalog.json` -- Full catalog JSON
3. `api/v1/categories.json` -- Category counts
4. `llms.txt` -- Agent discovery manifest
5. `llms-full.txt` -- Full catalog plain text
6. `taxonomy.js` -- Tree navigation data
7. Noscript catalog -- injected into index.html
8. **JSON-LD structured data** -- injected into index.html (NEW)

### Stats
- 15,803 total entries, 123 populated categories, 67 tests passing
- JSON-LD: 1,153 sampled entries, 455.6 KB

## 2026-03-14: S37/S38 Fix -- Backend Frameworks & Tier 3 Hardening

### What was done
- Fixed Backend Frameworks inflation (453->205): tightened 6 section maps, added Backend Frameworks + Frontend Frameworks to TIER3_EXCLUDED, fixed "express" keyword false positive
- Raised Tier 3 confidence threshold from 0.15 to 0.20 (reduces low-confidence misassignments)
- Narrowed section map patterns: `router|middleware` -> Networking, `micro` -> `micro.?service`, `http|web.?framework` -> `web.?framework`, `framework|micro` -> `web.?framework|micro.?framework`, `dependency.?inject` -> Utilities, `serial` in microservices -> Data Validation & Serialization

### Key learnings
- The keyword "express" as a Tier 2 match is extremely dangerous -- the English word "expression" appears in hundreds of descriptions. Changed to "expressjs" to only match the actual framework name.
- Section maps with single broad words like `router`, `middleware`, `micro`, `http`, `framework` are magnets for false positives. Always require compound patterns or word boundaries.
- TIER3_EXCLUDED is the correct approach for categories whose curated entries share too many common English words with the general corpus. Tier 1/2 still work for entries with specific tags.
- The confidence threshold increase from 0.15 to 0.20 dropped ~436 entries that were being assigned to random categories with very low overlap scores.
- Routers and middleware are networking infrastructure, not backend frameworks. The awesome-go list had a massive "Routers" section (25 entries) and "Middleware" sections (20+ entries) all going to Backend Frameworks.

### Files modified
- `scrape/categorize.py` -- TIER3_EXCLUDED (added Backend Frameworks, Frontend Frameworks), threshold 0.15->0.20, "express"->"expressjs"
- `scrape/sources/awesome_registry.py` -- 8 section map changes across 6 awesome lists (awesome-go, awesome-php, awesome-java, awesome-kotlin, awesome-rust, awesome-microservices)

### Stats after fix
- 15,803 total entries, 123 populated categories, 67 tests passing
- Backend Frameworks: 453->205 (-55%), Frontend Frameworks: 396->326 (-18%), Networking: 284->328 (+16%)
- Stable categories confirmed: Static Analysis 526, Databases 398, iOS UI Components 699

## 2026-03-14: Quality Automation Tools

### What was done
- Created `scripts/find_duplicates.py` — detects exact name duplicates, URL duplicates, similar names (Levenshtein <= 2), version variants
- Created `scripts/check_urls.py` — URL health checker using stdlib urllib + ThreadPoolExecutor, configurable timeout/concurrency, curated-only by default with --all flag
- Added 2 tests to `tests/test_data.py`: `test_no_duplicate_urls_across_all_files`, `test_no_duplicate_names_in_curated_files`
- Fixed 4 duplicate curated entries (removed docusaurus-docs, mintlify-docs, wireguard-security, fish-shell)
- Fixed 5 URL collisions (jupyterlab, apple-notes, icloud-drive, libreoffice-cli, nix — gave each a distinct URL)

### Key learnings
- Curated data had 3 exact name duplicates and 8 URL collisions — duplicates entered by different curators into different data files
- The similar-name detector (Levenshtein) finds 25K+ pairs across 16K entries — useful for spot-checks, not for CI blocking
- URL normalization must strip scheme, www prefix, trailing slashes, and fragments to catch real collisions
- The tests now act as a CI gate — any future duplicate will fail the test suite

### Files created
- `scripts/find_duplicates.py` — standalone duplicate detector (exit code 0/1)
- `scripts/check_urls.py` — URL health checker (HEAD→GET fallback, concurrent)

### Files modified
- `tests/test_data.py` — added TestNoDuplicates.test_no_duplicate_urls_across_all_files, test_no_duplicate_names_in_curated_files
- `data/productivity.json` — removed docusaurus-docs and mintlify-docs entries, fixed apple-notes and icloud-drive URLs
- `data/security.json` — removed wireguard-security entry
- `data/system_desktop.json` — removed fish-shell entry
- `data/ai_science.json` — fixed jupyterlab URL to jupyterlab.readthedocs.io
- `data/cli_utilities.json` — fixed libreoffice-cli URL to help.libreoffice.org
- `data/system_tools.json` — fixed nix URL to nixos.org/nix

### Stats after fix
- 16,243 total entries, 123 populated categories, 67 tests passing
- Remaining discovered-only URL dupes: 3 groups (SwiftGen, go vet, Segger)

## 2026-03-14: Categorization Quality Fix (S22/S23)

### What was done
- Fixed Code Editors false positives (279->147): tightened 5 section maps that used overly broad patterns (`develop`, `program`, `developer.?tool`), added Code Editors to TIER3_EXCLUDED
- Fixed Data Analysis false positives (159->92): added missing awesome-swift chart mapping, added typography/graphics section maps to awesome-javascript, narrowed JS Data Analysis pattern, strengthened Tier 3 penalty to 0.3x
- Added transition/modal/popup/alert section maps for awesome-ios, awesome-swift, awesome-javascript
- Rerouted awesome-react DevTools to Logging & Diagnostics, JS WYSIWYG editors to Frontend Frameworks

### Key learnings
- Entries from awesome-swift Charts section had NO mapping, causing iOS chart libs to fall through to categorizer where they matched Data Analysis via Tier 3
- Section maps with `develop|program` are too broad -- match any developer tool, not just editors
- TIER3_EXCLUDED is the right fix when a category's keywords overlap too much with generic English (Code Editors + "editor")
- Always check section map ordering in awesome_registry.py -- first match wins

### Files modified
- `scrape/categorize.py` — TIER3_EXCLUDED (added Code Editors), Data Analysis penalty 0.5->0.3
- `scrape/sources/awesome_registry.py` — 14 section map changes across 7 awesome lists

### Stats after fix
- 16,247 total entries, 123 populated categories, 65 tests passing
- Discovered file: `data/discovered_20260314.json` (15,055 entries)

## 2026-03-12: Agent Discoverability Implementation

### What was done
- Extended `build.py` to generate `api/v1/catalog.json`, `api/v1/categories.json`, and `llms.txt`
- All three files are auto-generated from data, so counts stay current when entries are added
- `api/v1/` directory is created by build script if it doesn't exist

### Current build outputs
1. `data.js` — Frontend JS (`window.SOFTWARE = [...]`)
2. `api/v1/catalog.json` — Pure JSON array of all entries
3. `api/v1/categories.json` — Category name to count mapping
4. `llms.txt` — AI agent manifest with site description, API endpoints, entry format, categories

### Stats at time of implementation
- 290 entries, 54 categories, 6 data files

## 2026-03-12: Tree Drill-Down Navigation

### What was done
- Replaced flat card grid + sidebar with tree-based drill-down UI in `index.html`
- Tree structure loaded from `taxonomy.json` via `fetch()` at startup
- 14 top-level nodes, 2-3 levels deep, all 54 categories map to unique leaf nodes
- Added breadcrumb navigation (clickable, accent-colored current node)
- Removed: sidebar, mobile filter bar (peek-bar)
- Kept: search (skips tree, shows all matching entries), OS filters, detail panel, sort controls (leaf only), hash deep-linking

### Key design decisions
- Tiles use `minmax(240px, 1fr)` grid — responsive for any number of tiles (3 to 14)
- Sort controls hidden when viewing tree tiles, shown at leaf nodes and during search
- Breadcrumb hidden during search mode
- Graceful fallback: if `taxonomy.json` fetch fails, all entries shown as cards
- `countEntries()` recursively counts entries under any node by collecting category names

### Files modified
- `index.html` — complete rewrite of layout section and JavaScript

### Things to watch
- `taxonomy.json` must be co-located with `index.html` for fetch to work (same directory or configured server)
- If new categories are added to data, they must also be added to `taxonomy.json` leaf nodes
- The `collectCategories()` function traverses the tree on every tile render — fine for 54 categories, but would need caching if taxonomy grew very large
