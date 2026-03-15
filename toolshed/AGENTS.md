# Main Menu

If told to go, start, or begin — you are the **orchestrator**. See `agents/orchestrator.md`.

For agent startup protocol, communication rules, and forum voting, see `PROTOCOL.md`.

## Overview

Universal software directory at main.menu. Browse apps, libraries, protocols, and platforms across 128 categories in a tree hierarchy, filterable by OS. Static site — no backend.

## Stack

- **Frontend**: Single `index.html` (vanilla HTML/CSS/JS, no frameworks, no build tools)
- **Data**: JSON files in `data/` → `build.py` aggregates into `data.js`
- **Scraping**: `python -m scrape` fetches from awesome lists, Homebrew, CNCF → `data/discovered_*.json`
- **Taxonomy**: `taxonomy.json` defines the tree hierarchy → `build.py` generates `taxonomy.js`
- **Categorization**: `scrape/categorize.py` (keyword mapping), `scrape/sources/awesome_registry.py` (section maps)
- **Schema**: `schema.json` (JSON Schema draft-07) defines entry shape
- **Deploy**: `bash deploy.sh` → gcloud scp to thisminute.org/mainmenu

## Key Files

| File | Purpose |
|------|---------|
| `index.html` | Entire frontend — tree nav, search, OS filters, detail panel |
| `data.js` | Generated. `window.SOFTWARE` array of all entries |
| `taxonomy.js` | Generated. `window.TAXONOMY` tree for drill-down navigation |
| `taxonomy.json` | Tree hierarchy definition — 22 top-level groups, 124 leaf categories |
| `build.py` | Aggregates `data/*.json`, deduplicates, generates data.js, taxonomy.js, api/, llms.txt, noscript HTML |
| `schema.json` | Defines entry shape |
| `data/*.json` | Source data files (22 files including discovered scrape data) |
| `scrape/categorize.py` | Keyword-to-category mapping and Tier 1/2/3 scoring |
| `scrape/sources/awesome_registry.py` | Section-to-category maps for 22 awesome lists |
| `scrape/pipeline.py` | Scrape pipeline: normalize → categorize → quality gate → dedup → validate |
| `deploy.sh` | Upload to thisminute.org via gcloud compute scp |

## Entry Schema (abbreviated)

Each entry has: `id` (kebab-case), `name`, `description` (~200 chars), `url`, `category` (one of 128), `os[]` (windows/macos/linux/web/ios/android), `pricing` (free/freemium/paid/subscription), `tags[]`, optional `source` (repo URL if open-source), optional `language`.

## Current State

- 15,803 entries across 123 populated categories (124 in taxonomy) in 22 top-level groups
- ~336 curated + ~15,467 discovered entries across 22 data files
- 67 tests passing (test_categorize, test_data, test_taxonomy)
- Tree drill-down navigation (taxonomy.json → taxonomy.js)
- Dark/light mode toggle with `prefers-color-scheme` support + `matchMedia` listener
- Warm amber color scheme, category-colored card borders
- Cmd/Ctrl+K search shortcut, live result count, search highlighting
- Search across names, descriptions, categories, tags
- OS filtering, sort by category/A-Z/shuffle
- Detail panel with website + source code links, "See Also" (4 shuffled same-category entries), "Copy Link" button
- Mobile: floating "Categories" button with bottom-sheet taxonomy panel (<=900px)
- API endpoint at api/v1/catalog.json, llms.txt for agent discovery
- JSON-LD structured data (schema.org SoftwareApplication, 1,153 sampled entries)
- Noscript fallback with full catalog HTML
- Live at https://thisminute.org/mainmenu
- Cross-links to sister projects (Rhizome, Agent Forge) in header

## Deploying & Pushing

**Deploys and git pushes are handled by the ops steward** (see `~/projects/ops/agents/steward.md`). Do not deploy or push directly.

To request a deploy: add an entry to `~/projects/ops/DEPLOY_QUEUE.md` with scope (push/deploy/both), changed files, and any notes. The steward runs tests, pushes to GitHub, deploys via `bash deploy.sh`, cache-busts `?v=` on `data.js` and `taxonomy.js`, and verifies health — on a 60-minute cycle.

## Commands

- **Build**: `python build.py`
- **Scrape**: `python -m scrape` (default: awesome,homebrew,cncf sources)
- **Dry-run scrape**: `python -m scrape --dry-run`
- **Local dev**: Open `index.html` in a browser (file:// works for basic testing, but taxonomy.json fetch needs a server)

## Quality Signals

- Are entry descriptions accurate and informative?
- Are URLs correct and not dead?
- Are OS tags accurate?
- Are pricing models current?
- Is every leaf category well-represented (30-200 entries)?
- Does the UI work on mobile?
- Do filters compose correctly (category + OS + search)?
- Are scrape section maps routing entries to the correct categories?
- Is the taxonomy tree intuitive to navigate?

## Recent Major Changes (2026-03-14)

- **Cycles 10-11**: Fixed S22/S23 categorization (Code Editors 279->147, Data Analysis 159->92). Built quality automation scripts (`scripts/find_duplicates.py`, `scripts/check_urls.py`). Fixed 4 duplicate entries, 5 URL collisions.
- **Cycle 12**: Skeptic review found S37-S49. Orchestrator fixed dead URLs (S44-S47), script bugs (S39, S42), test gap (S48), removed 3 dead entries (HitFilm, Around, BlueJeans).
- **Cycle 13**: Fixed Backend Frameworks inflation (453->205). Raised Tier 3 threshold 0.15->0.20. Tightened section maps across 6 awesome lists.
- **Cycle 14**: Added JSON-LD structured data (schema.org SoftwareApplication, 1,153 sampled entries, 455.6 KB).
- **Cycles 8-9**: +46 curated entries across 10 categories. Dark/light toggle, "See Also", "Copy Link", mobile taxonomy panel, search highlighting. 67 tests passing.

### Earlier changes (2026-03-13)

- **Taxonomy restructure**: 105 -> 124 categories. Networking, Blockchain & Web3, Terminal UI, NLP & Text AI, LLM Tools, and more.
- **Categorizer hardening**: 3 rounds of fixes. Stop-word filter, Tier 3 penalties, 30+ section map tightening.
- **Design UX**: Cmd/Ctrl+K search shortcut, live result count, category-colored card borders.
