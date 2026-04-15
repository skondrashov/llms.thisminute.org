# Toolshed

If told to go, start, or begin — you are the **orchestrator**. See `agents/orchestrator.md`.

For agent startup protocol, communication rules, and forum voting, see `PROTOCOL.md`.

## Overview

Universal software directory at thisminute.org/toolshed. Browse apps, libraries, protocols, and platforms across 124 categories in a tree hierarchy, filterable by OS. Static site — no backend.

The toolshed has both **filled slots** (existing software) and **unfilled slots** (software that should exist but doesn't). Every category is conceptually a set of slots — some filled by real tools, some empty. The empty ones are the interesting signal: they show where the software landscape has genuine gaps. Examples of unfilled slots: tools that don't exist yet because the problem is unsolved, tools for emerging domains, tools that would exist if someone bothered to build them.

## Stack

- **Frontend**: Single `index.html` (vanilla HTML/CSS/JS, no frameworks, no build tools)
- **Data**: JSON files in `data/` → `build.py` aggregates into `data.js`
- **Scraping**: `python -m scrape` fetches from awesome lists, Homebrew, CNCF → `data/discovered_*.json`
- **Taxonomy**: `taxonomy.json` defines the tree hierarchy → `build.py` generates `taxonomy.js`
- **Categorization**: `scrape/categorize.py` (keyword mapping), `scrape/sources/awesome_registry.py` (section maps)
- **Schema**: `schema.json` (JSON Schema draft-07) defines entry shape
- **Deploy**: `bash deploy.sh` → gcloud scp to thisminute.org/toolshed
- **Executable tools**: `tools/` directory for standalone tools (e.g., `tools/balatro_scorer/`)

## Key Files

| File | Purpose |
|------|---------|
| `index.html` | Entire frontend — tree nav, search, OS filters, detail panel |
| `data.js` | Generated. `window.SOFTWARE` array of all entries |
| `taxonomy.js` | Generated. `window.TAXONOMY` tree for drill-down navigation |
| `taxonomy.json` | Tree hierarchy definition — 22 top-level groups, 124 leaf categories |
| `build.py` | Aggregates `data/*.json`, deduplicates, generates data.js, taxonomy.js, api/, llms.txt, noscript HTML, JSON-LD |
| `schema.json` | Defines entry shape |
| `data/*.json` | Source data files (22 files including discovered scrape data) |
| `scrape/categorize.py` | Keyword-to-category mapping and Tier 1/2/3 scoring |
| `scrape/sources/awesome_registry.py` | Section-to-category maps for 22 awesome lists |
| `scrape/pipeline.py` | Scrape pipeline: normalize → categorize → quality gate → dedup → validate |
| `deploy.sh` | Upload to thisminute.org via gcloud compute scp |
| `tools/` | Standalone executable tools (not part of the catalog site) |

## Entry Schema (abbreviated)

Each entry has: `id` (kebab-case), `name`, `description` (~200 chars), `url`, `category` (one of 124), `os[]` (windows/macos/linux/web/ios/android), `pricing` (free/freemium/paid/subscription), `tags[]`, optional `source` (repo URL if open-source), optional `language`.

**Unfilled slot entries** (in `ideas.js`) follow the same schema plus `complexity`, `capability`, `approach`, `agentArchitecture`, and `triage` fields. These represent genuine gaps in the software landscape — software that should exist but doesn't, or where existing tools leave real needs unmet. CLI tools built from unfilled slots live in the `tools/` directory as standalone Python packages (e.g., `tools/balatro_scorer/`). These are precision tools where lookup beats reasoning — 300-600 LOC, tagged `precision-tool`.

## Unfilled Slot Triage

Every unfilled slot in `ideas.js` must have a `triage` object with three scored criteria. These scores determine priority and whether the slot represents a genuine gap or an already-solved problem.

| Field | Values | Meaning |
|-------|--------|---------|
| `impact` | high / medium / low | How helpful is this tool to users? |
| `buildability` | straightforward / moderate / hard | How feasible is it for AI agents to build? |
| `alternatives` | none / partial / covered | Do existing tools already fill this need? |

Plus `alternatives_note` (free text) naming the specific tools and what gap remains.

**Priority order:** Filter out `covered`, then sort by impact (high first), then by buildability (straightforward first). A slot with `high` impact + `straightforward` buildability + `none` alternatives is the most interesting gap. A slot with `covered` alternatives isn't really unfilled — downgrade or remove it.

## Current State

- 16,143 entries across 123 populated categories (124 in taxonomy) in 22 top-level groups
- ~1,551 curated + ~14,567 discovered entries + 25 forge ideas across 22 data files
- 67 tests passing (test_categorize, test_data, test_taxonomy)
- **View Tabs**: All / Catalog / Requests / Built by Forge — browse filled slots, unfilled slots, and built tools
- **Multi-dimensional filtering**: OS, pricing (free/freemium/paid/subscription), language, tags
- **Forge integration**: triage badges (impact/buildability/alternatives), validation info, priority sort
- **Header stats**: Apps, Categories, AI-Built, Requests (clickable to switch view)
- **Tag bar**: Top 12 tags shown contextually for current card list, clickable to filter
- Tree drill-down navigation (taxonomy.json → taxonomy.js)
- Dark/light mode toggle with `prefers-color-scheme` support + `matchMedia` listener
- Theme stored in localStorage as `thisminute_theme`
- Warm amber color scheme, category-colored card borders, green/blue forge card accents
- Cmd/Ctrl+K search shortcut, live result count, search highlighting, context-aware placeholder
- Search across names, descriptions, categories, tags
- Detail panel with triage section (for ideas), validation (for built), "See Also", "Copy Link", clickable tags
- Mobile: floating "Categories" button with bottom-sheet taxonomy panel (<=900px)
- API endpoint at api/v1/catalog.json, llms.txt for agent discovery
- JSON-LD structured data (schema.org SoftwareApplication, 1,542 sampled entries)
- Noscript fallback with full catalog HTML
- Live at https://thisminute.org/toolshed
- Cross-links to sister projects (Orchestration, Agent Forge) in header

## Deploying & Pushing

**Deploys and git pushes are handled by the ops steward** (see `~/projects/ops/agents/steward.md`). Do not deploy or push directly.

To request a deploy: add an entry to `~/projects/ops/DEPLOY_QUEUE.md` with scope (push/deploy/both), changed files, and any notes. The steward runs tests, pushes to GitHub, deploys via `bash deploy.sh`, cache-busts `?v=` on `data.js` and `taxonomy.js`, and verifies health — on a 60-minute cycle.

## Commands

- **Build**: `python build.py`
- **Build (strict)**: `python build.py --strict` (excludes Tier 3, unmatched, and category-disagreement discovered entries — 16,037 → 7,047)
- **Scrape**: `python -m scrape` (default: awesome,homebrew,cncf sources)
- **Dry-run scrape**: `python -m scrape --dry-run`
- **Test**: `python -m pytest tests/ -v` (67 tests)
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
