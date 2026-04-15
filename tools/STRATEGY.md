# Strategy

## Vision

Toolshed is the place you go to find software for anything. Chess apps, terminal emulators, DAWs, VPNs — all browsable in one place with honest descriptions, OS filtering, and direct links. No ads, no sponsored rankings, no bullshit.

**Primary audience**: AI agents and developers. Agents need verified URLs (they hallucinate), structured metadata (JSON with OS/tags/category), and current maintenance status. Humans benefit from honest curation without SEO spam.

**Secondary audience**: Power users and technical decision-makers who want to compare options without wading through SEO-optimized listicles.

**North star**: If an agent or human asks "what's the best X for Y?", Toolshed should have a useful, accurate answer with a working link.

## Core Principle: Task-First Categories

Categories describe **what a tool does**, not what language it's in. An agent thinks "I need to parse HTML" not "I need a Python library." Language is a tag/filter, not a category.

**Wrong:** Python Libraries, Rust Crates, Go Libraries, JavaScript Libraries
**Right:** HTTP Clients, Web Scraping, Image Processing, Data Validation, CLI Building

A single category page shows ALL options across ecosystems so you can compare (e.g., HTTP Clients shows requests, axios, reqwest, httpx, curl together).

### Task-Based Category Mapping (for library restructure)

| Task Category | Entries |
|---|---|
| HTTP Clients | requests, httpx, axios, reqwest, curl, wget |
| Web Scraping & Parsing | beautifulsoup4, cheerio |
| Data Analysis | pandas, numpy, polars, jq, duckdb |
| Image Processing | pillow, sharp, imagemagick, opencv |
| Media Processing | ffmpeg |
| Web Frameworks | flask, axum, gin, echo, fiber, go-chi (+ merge with existing Web Frameworks) |
| Database ORMs | sqlalchemy, prisma, gorm |
| Data Validation & Serialization | pydantic, zod, serde |
| CLI Building | click, clap, cobra |
| Async & Concurrency | tokio, rayon |
| Logging & Diagnostics | tracing, zap |
| Error Handling | anyhow |
| Real-time Communication | socket-io |
| Date & Time | date-fns |
| File Search & Navigation | fzf, ripgrep, fd, bat |
| Terminal & Shell | tmux |
| Document Conversion | pandoc |
| Utilities | lodash |

Categories that are already task-based (keep as-is): Testing Frameworks, Linters & Formatters, AI/ML Libraries, CI/CD Tools, Data Processing, Databases, APIs & Services

Language goes in `tags[]` for filtering (e.g., tags: ["python", "http"]).

---

## Long-Term Roadmap

### Phase 1: Foundation (Current — Target: 2 weeks)
**Theme: Make the existing site polished and agent-readable.**

#### 1A. Design Overhaul — Make It Sleek
The site is functional but visually flat. Every card looks the same. There is no visual hierarchy beyond the category sidebar. To make someone bookmark this and come back:

- **Card redesign**: Add subtle category-colored left borders or top accents to cards so they are visually scannable. Consider small software icons/favicons next to names.
- **Typography upgrade**: The system font stack is fine but the hierarchy is weak. Increase contrast between card names (bolder, slightly larger) and descriptions. Use a tighter line-height on card names.
- **Header refinement**: The stat row is good. Add a subtle gradient or animated accent on the "TOOLSHED" title. Consider a brief animated counter on page load.
- **Search UX**: Add keyboard shortcut (Cmd/Ctrl+K) to focus search. Show result count while typing. Add search highlighting in card text. Consider instant category/tag suggestions as you type.
- **Detail panel**: Add a proper software icon/logo placeholder. Show "Similar software" suggestions at the bottom. Add a "copy link" button. Improve the tag display with better spacing.
- **Dark/Light mode**: Add a toggle. The current dark theme is good; create a corresponding light theme with warm tones. Persist preference in localStorage.
- **Animations**: Add subtle staggered fade-in on cards when filtering. Smooth the detail panel slide-in. Add a skeleton loading state.
- **Mobile**: The mobile experience drops the sidebar entirely. The peek-bar is clever but undiscoverable. Add a visible "Filter" button. Test touch interactions.
- **Footer**: Add a minimal footer with: "Curated directory — no ads, no sponsored rankings", link count, last updated date, link to the data repository.
- **Favicon**: The current SVG favicon is functional. Consider a cleaner icon — a simple stylized "M" or hamburger menu icon.

**Priority order for designer**: Search UX (Cmd+K, result count) > Card redesign (category accents) > Dark/light toggle > Detail panel improvements > Mobile filter button > Footer > Animations

#### 1B. Agent Discoverability — Make It Crawlable
The current site renders everything client-side from `data.js`. A crawler or agent hitting `index.html` sees empty divs. This is the single biggest problem for the stated primary audience.

- **Structured data (JSON-LD)**: Add schema.org `SoftwareApplication` markup for every entry, embedded in the HTML. Include name, url, operatingSystem, applicationCategory, offers (pricing). This is the highest-impact change for search engines and agents.
- **Semantic HTML**: Replace the generic `div.card` grid with `<article>` elements. Add `<main>`, `<nav>`, `<aside>` landmarks. Use `<h2>` for card names, `<p>` for descriptions.
- **Meta tags**: The current `<meta description>` is generic. Generate a dynamic description with entry/category counts. Add Open Graph and Twitter Card meta tags for social sharing.
- **Server-side rendering / static generation**: The ideal end state is that `index.html` contains all entries as visible HTML, not just loaded via JS. Options:
  - **Quick win**: Have `build.py` inject a `<noscript>` block or hidden semantic HTML section containing all entries as a structured list. Agents and crawlers see it; JS-capable browsers use the interactive version.
  - **Medium-term**: Generate static category pages (`/category/cli-tools/index.html`) with pre-rendered entry lists. Good for SEO, good for agents that want to browse by topic.
  - **Long-term**: If traffic justifies it, add a lightweight static site generator step to `build.py`.
- **`/api/` endpoint**: Serve the raw JSON at a stable URL. Options:
  - Simplest: Just make `data.js` also available as `api/v1/catalog.json` (pure JSON, no `window.SOFTWARE=` wrapper). `build.py` can generate both files.
  - Add `api/v1/categories.json` (list of categories with entry counts).
  - Add `api/v1/entry/{id}.json` (individual entry lookup — can be pre-generated static files).
- **`llms.txt`**: Create a manifest file at `/llms.txt` that describes the site purpose, data format, and how to access the catalog. Format:
  ```
  # Toolshed
  > Universal software directory. 15,000+ entries across 123 categories.

  ## API
  - Full catalog: /api/v1/catalog.json
  - Schema: /schema.json

  ## Categories
  [list of categories with counts]

  ## Entry Format
  Each entry has: id, name, description, url, category, os[], pricing, tags[], source (optional)
  ```
- **Sitemap**: Generate `sitemap.xml` from `build.py`. Include the main page and all category pages (once they exist). Low priority until we have actual category pages.

**Priority order for builder**: JSON-LD structured data > `api/v1/catalog.json` generation > `llms.txt` > Semantic HTML refactor > `<noscript>` fallback > Static category pages > Sitemap

### Phase 2: Scale (Weeks 3-6)
**Theme: Get to 500+ entries, improve metadata, harden quality.**

#### 2A. Catalog Expansion to 500+
Current: 290 entries across 42 categories. Path to 500+:

**New categories to add (estimated 120+ entries):**
- Build Tools (8): webpack, Vite, esbuild, Rollup, Turbopack, Parcel, Gradle, Maven
- Container & DevOps (8): Kubernetes, Terraform, Ansible, Helm, Pulumi, Vagrant (move from Virtualization?), Docker Compose, Nomad
- Cloud SDKs (6): AWS SDK, Google Cloud SDK, Azure CLI, Cloudflare Workers, Vercel SDK, Netlify CLI
- API Tools (6): Postman, Insomnia, HTTPie, Bruno, Hoppscotch, Swagger/OpenAPI
- Privacy & Security Tools (8): Tor Browser, Signal, KeePassXC, Bitwarden CLI, GPG, age, Tails, Mullvad
- RSS Readers (6): Feedly, Inoreader, NewsBlur, Miniflux, FreshRSS, NetNewsWire
- Launcher & Productivity (6): Raycast, Alfred, Rofi, dmenu, Ulauncher, PowerToys
- Fonts & Design Systems (6): Google Fonts, Inter, JetBrains Mono, Nerd Fonts, Tailwind CSS, Bootstrap
- Monitoring & Observability (7): Prometheus, Grafana, Datadog, Sentry, PagerDuty, New Relic, Jaeger
- Static Site Generators (7): Hugo, Gatsby, Jekyll, Eleventy, Astro, Zola, Pelican
- Auth & Identity (6): Auth0, Clerk, NextAuth.js, Keycloak, Okta, Firebase Auth
- Shell & Terminal Tools (6): Oh My Zsh, Starship, zoxide, atuin, direnv, nushell
- Documentation Tools (6): Sphinx, MkDocs, Docusaurus, Storybook, Swagger UI, ReadTheDocs
- Diagramming & Whiteboard (6): Excalidraw, Mermaid, draw.io, Figma (FigJam), Miro, Lucidchart
- Embedded & IoT (5): Arduino, Raspberry Pi OS, PlatformIO, MicroPython, Zephyr

**Expand thin categories (estimated 30+ entries):**
- File Managers (4 -> 8): add Dolphin, Thunar, Double Commander, Midnight Commander
- Password Managers (4 -> 8): add Dashlane, NordPass, Enpass, KeePassXC
- Chess (5 -> 7): add Lichess mobile, chess24
- Cloud Storage (5 -> 8): add Mega, iCloud, Tresorit
- VPN (5 -> 8): add Tailscale, Wireguard, ZeroTier
- Database Tools (5 -> 7): add DataGrip, Beekeeper Studio

#### 2B. Enhanced Metadata
Add new optional fields to the schema to increase usefulness for agents:

- **`last_verified`** (date): When was this entry last checked for accuracy? Agents and users can trust recent entries more.
- **`maintenance_status`** (enum: active/maintenance/deprecated/archived): Critical signal. An agent should not recommend archived software.
- **`popularity`** (enum: niche/moderate/popular/dominant): Rough signal of adoption. "Popular" = most developers have heard of it. "Dominant" = category leader.
- **`license`** (string): SPDX identifier (MIT, Apache-2.0, GPL-3.0, proprietary, etc.). Agents need this to recommend software for commercial use.
- **`language`** (string): Primary programming language or ecosystem (python, javascript, rust, go, etc.). Enables queries like "find a Python HTTP library."
- **`alternatives`** (array of IDs): Cross-references to similar entries. Enables "see also" in the detail panel and agent recommendations.

These fields should be optional in schema.json and backfilled gradually. `last_verified` can be auto-set by the skeptic during verification cycles.

#### 2C. Quality Automation
- **URL health checker**: Script that hits every URL in the catalog and flags 404s, redirects, and timeouts. Run weekly.
- **Duplicate detection**: Check for entries with very similar names or URLs across data files.
- **Schema validation in CI**: If we add a GitHub repo, run `jsonschema` validation on every PR.
- **Freshness alerts**: Flag entries where `last_verified` is older than 90 days.

### Phase 3: Growth (Weeks 7-12)
**Theme: Get to 1000+ entries, community contributions, monetization.**

#### 3A. Catalog Expansion to 1000+
At 500+ entries with solid metadata, the catalog becomes genuinely useful as a reference. To reach 1000+:

- **Automated discovery**: Script that pulls trending repos from GitHub, top packages from PyPI/npm/crates.io, and suggests new entries for curator review.
- **Community submissions**: Simple GitHub issue template or Google Form where anyone can suggest entries. Curator reviews and adds.
- **Vertical deep-dives**: Pick 5-10 categories and go deep. For example, "Python Libraries" could have 50+ entries (web frameworks, data science, DevOps, testing, etc.). This makes Toolshed the definitive reference for that vertical.

#### 3B. Static Category Pages
Generate `/category/{slug}/index.html` for each category. Benefits:
- SEO: Each page ranks for "[category] tools" searches.
- Agent navigation: An agent can request `/category/python-libraries/` and get a focused list.
- Linkability: Users can share a direct link to a category.
- Pre-rendered: No JS required to see the content.

Each category page should include: category description, entry count, filterable list of entries, links to related categories.

#### 3C. Monetization (Careful)
The site's value proposition is honest curation. Monetization must not compromise this.

- **Affiliate links**: Where available (cloud services, paid tools), use affiliate URLs. Clearly mark them. Never let affiliate availability influence inclusion or ranking.
- **Sponsored listings**: Allow paid "featured" placement with a clear "Sponsored" label. Limit to 1 per category. Never in search results.
- **Donations**: Add a simple "Support this project" link (GitHub Sponsors, Buy Me a Coffee, Ko-fi). Low friction.
- **API access tiers**: If the API becomes popular, offer a free tier (rate-limited) and a paid tier for commercial use.

**Deprioritize**: Ads (ruins the aesthetic and trust), premium content (all data should be free), user accounts (complexity not justified yet).

#### 3D. Agent Integration Protocol
Define a standard way for agents to interact with Toolshed:

- **Discovery**: Agent reads `llms.txt` to understand the site.
- **Search**: Agent queries `api/v1/catalog.json` and filters locally, or uses `api/v1/search?q=...` if we add server-side search later.
- **Recommendation**: Agent uses `popularity`, `maintenance_status`, and `alternatives` fields to make informed suggestions.
- **Verification**: Agent checks `last_verified` date and `url` to ensure freshness.
- **Feedback loop**: Agents can report broken links or suggest entries via a simple API endpoint (future).

### Phase 4: Platform (Months 3-6)
**Theme: Become the reference that agents and humans default to.**

- **Comparison pages**: Auto-generated "X vs Y" pages for popular alternatives (e.g., "PostgreSQL vs MySQL").
- **Ecosystem maps**: Visual graphs showing how tools relate (e.g., "Python web stack: Django + PostgreSQL + Redis + Celery").
- **Version tracking**: Monitor release feeds for tracked software. Show "latest version" and "last release date."
- **User reviews/ratings**: Lightweight — maybe just thumbs up/down or a 1-5 rating. No text reviews (too hard to moderate).
- **Embeddable widgets**: Let blogs and docs embed a Toolshed card for any software entry.

---

## Current Priorities (Updated 2026-03-16)

**Context:** 16,156 entries across 124 populated categories (125 in taxonomy). 67 tests passing. Forge UI integration complete (view tabs, multi-dimensional filtering, forge pipeline visualization, covered/unique distinction). Thin categories addressed (Cycles 15-16, 20, 22, 28, 30, 38, 40, 43, 45, 48-49, 52, 55, 57, 60, 63, 65, 70, 73-75 curator). Harnesses category added (22 entries, Cycle 76). 3 forge ideas remaining, 22 built.

### Priority 0: Idea Triage Must Stay Current (CURATOR)

Every idea in `ideas.js` must have a `triage` object with `impact`, `buildability`, and `alternatives` scored. The forge reads these to decide what to build — untriaged ideas are invisible to it. When reviewing ideas, challenge stale scores: if a new product has launched that covers the need, downgrade `alternatives` to `covered`. See `schema.json` for field definitions.

**Proven pattern: precision CLI tools.** The forge's best cadence is shipping focused Python CLI tools (300-600 LOC, 300-500 tests) in 1-2 days. These are tools where **lookup beats reasoning** — combinatorics, spec compliance, format parsing, lookup tables. The pipeline has 20 such tools tagged `precision-tool`, including 3 forge-infra tools (forge-cli, forge-test-gen, forge-data) that accelerate the forge's own build cadence. Prioritize these over larger web-app or multi-agent ideas that take weeks.

### Priority 1: Thin Categories Need Attention (CURATOR)

| Category | Count | Notes |
|---|---|---|
| APIs & Services | 27 | |
| Chess | 27 | |
| HR & People | 27 | |

### Priority 2: Discovered Entry Quality (BUILDER/CURATOR -- ongoing)

- S38: Random sample shows ~50% miscategorization in discovered entries. **Mitigated**: `build.py --strict` excludes Tier 3, unmatched, and category-disagreement discovered entries (16,037 → 7,047). Default build unchanged. S72 fix implemented (tuple return with category agreement filter). S73 fix applied (Tier 2 best-match tracking aligned with `categorize()`).
- Options for further improvement: better section maps, LLM-assisted categorization, `get_confidence_tier()` category-agreement filtering.

### Priority 3: Script Quality Improvements (BUILDER -- low)

- ~~S40: `find_duplicates.py` Levenshtein check is O(n^2)~~ -- **FIXED** (SymSpell deletion neighborhoods, ~3s runtime)
- ~~S41: `check_urls.py` disables SSL verification~~ -- **FIXED** (`ssl.create_default_context()` with explicit error handling, `--no-verify-ssl` opt-in retained)
- ~~S43: `check_urls.py` no per-domain rate limiting~~ -- **FIXED** (per-domain tracking with 1s minimum; race condition noted as S63, low severity)

### Priority 4: Enhanced Metadata (BUILDER -- backlog)

- Schema fields: `maintenance_status`, `last_verified`, `license`, `popularity`, `alternatives`
- Individual entry pages at `api/v1/entry/{id}.json`
- Sitemap.xml (low priority until category pages exist)

### COMPLETED

**Categorization Quality (Cycles 5-7, 10, 13):**
- Tier 3 feedback loop, AI Assistants 579->33, Cloud SDKs 558->70, Task Runners 344->24, HR & People 220->9, VPN 274->58, CI/CD 275->196, Logging 274->207, Networking 0->285
- Code Editors 279->147 (S22), Data Analysis 159->92 (S23), Backend Frameworks 453->205 (S37)
- Tier 3 threshold raised 0.15->0.20, TIER3_EXCLUDED expanded

**Quality Automation (Cycle 11):**
- `scripts/find_duplicates.py` -- name, URL, similar-name detection (exit code fixed)
- `scripts/check_urls.py` -- URL health checker with concurrent workers
- Duplicate detection tests in `test_data.py`
- Fixed 4 duplicate entries, 5 URL collisions, 3 dead domains removed

**Agent Discoverability (Cycles 4, 14):**
- `api/v1/catalog.json` -- 15,979 entries
- `llms.txt` and `llms-full.txt`
- Noscript HTML fallback -- 15,979 entries
- JSON-LD structured data -- 1,464 sampled entries, 584.9 KB
- Tree drill-down navigation

**Design Polish (Cycles 1-2):**
- Search UX (Cmd/Ctrl+K, result count, highlighting), card borders, dark/light toggle, "See Also", "Copy Link", mobile taxonomy panel

**Forge UI Integration (Cycle 15):**
- View tabs: All / Catalog / Requests / Built by Forge
- Multi-dimensional filtering: OS + pricing + language + tags + priority sort
- Forge card styling: triage badges, validation info, green/blue accents
- Forge summary banner with pipeline stats and contextual descriptions
- Header forge stats (AI-Built, Requests) clickable to switch view
- Tag bar: contextual top-12 tags for current card list
- Detail panel: full triage section for ideas, clickable tags for search
- Context-aware search placeholders per view

**Accessibility & Polish (Cycles 15-16):**
- S50-S55 fixed: meta description, triage escaping, WCAG AA contrast in light mode, keyboard a11y on clickable stats, focus-visible on view-tab/tag-chip, curated count in docs
- Thin categories filled: Secrets Management 18->26, Vector Databases 18->26, Task Runners 17->24, Mobile IDE 20->25, Flashcards 20->25, Desktop App Frameworks 21->25, HR & People 20->27

**Forge Polish & Fixes (Cycles 17-20):**
- Designer: covered/unique card distinction, forge summary banner unique/covered split, sparse requests message, TAG_EXCLUDE_FORGE
- Builder: S40 fixed (find_duplicates.py SymSpell deletion neighborhoods, ~3s)
- Skeptic: S58-S62 found; S58-S60 fixed by orchestrator (sparse message filter, sub-unique contrast, covered-note contrast)
- Curator Cycle 12: Error Handling 21->34, Statistical Tools 21->32, 21 duplicate discovered entries cleaned
- Curator Cycle 13: Chess restored 11->27 (+16 curated, 2 discovered replaced)
- Builder: S41 fixed (SSL verification), S43 fixed (per-domain rate limiting), `--limit N` flag added
- Skeptic: S63-S66 found; S64/S65 flagged miscategorized discovered entries for curator

**Curation & Search Polish (Cycles 25-29):**
- Curator Cycle 14: Caching, Static Analysis, Configuration baselines (21 curated, 17 discovered removed)
- Designer Cycle 4: Forge search surfacing (sort boost, forge match count, highlight colors)
- Skeptic: S67-S68 found (double search call, stale counts)
- Curator Cycle 15: Blockchain & Web3, Template Engines, Math & Numerics baselines (21 curated, 10 discovered removed)
- Librarian: S68 fixed (counts rebuilt from scratch)
- Curator Cycle 16: Database Drivers baseline (7 curated, 2 discovered removed)
- Skeptic: S69-S70 found (Eigen URL redirect, OpenZeppelin language); both fixed

**S38 Mitigation & Quality (Cycles 33-39):**
- Builder: `--strict` flag for `build.py` excludes Tier 3/unmatched discovered entries
- Orchestrator: S72 fix (tuple return with category agreement filter, 15,939 -> 6,970 strict)
- S73 fixed (Tier 2 best-match tracking aligned with `categorize()` logic)
- Skeptic: S71 (tier function logic mismatch -- low), S72/S73 found and resolved
- Curator Cycle 38: Compression & Archiving baseline (7 curated, 1 discovered removed)
- Curator Cycle 40: Networking baseline (7 curated, 2 discovered removed)
- Curator Cycle 43: CLI Frameworks + Frontend Frameworks expansion (12 curated, 5 discovered removed)
- Curator Cycle 45: Text Processing + Game Engines expansion (13 curated, 4 discovered removed)
- Curator Cycle 48: Video Editing expansion (6 curated, 3 discovered removed)
- Curator Cycle 49: Backend Frameworks expansion (7 curated, 8 discovered removed)
- Curator Cycle 52: Image Processing + Cross-Platform Frameworks expansion (12 curated, 7 discovered removed)
- Curator Cycle 55: Databases expansion (7 curated, 3 discovered removed)
- Curator Cycle 57: ORMs + HTTP Libraries expansion (12 curated, 8 discovered removed)
- Curator Cycle 60: Testing Frameworks + Container Orchestration expansion (12 curated, 8 discovered removed)
- Curator Cycle 63: Security Scanning + Linters & Formatters expansion (12 curated, 7 discovered removed)
- Curator Cycle 65: Communication + Music Production expansion (13 curated, 8 discovered removed)
- Curator Cycle 67: Static Analysis + Data Validation expansion (12 curated, 12 discovered removed)
- Curator Cycle 70: Note Taking + Browsers expansion (12 curated, 9 discovered removed)

## Deprioritized

- User accounts / submissions (Phase 3 at earliest)
- Server-side search (not needed until 1000+ entries)
- Comparison pages and ecosystem maps (Phase 4)
- Version tracking (Phase 4)
- User reviews/ratings (Phase 4)
- Full static site generator migration (not needed while single-page works)

## Completed

### Category Gaps (Original List)
- ~~System Utilities~~ (8 entries)
- ~~Office Suites~~ (7 entries)
- ~~Screen Recording / Streaming~~ (6 entries)
- ~~PDF Tools~~ (6 entries)
- ~~Torrent Clients~~ (6 entries)
- ~~Backup & Sync~~ (7 entries)
- ~~Virtualization~~ (7 entries)
- ~~Programming Languages~~ (8 entries)
- ~~Web Frameworks~~ (8 entries)
- ~~Package Managers~~ (8 entries)
- ~~Python Libraries~~ (10 entries)
- ~~JavaScript Libraries~~ (8 entries)
- ~~Rust Crates~~ (8 entries)
- ~~CLI Tools~~ (11 entries)
- ~~APIs & Services~~ (8 entries)
- ~~Testing Frameworks~~ (8 entries)
- ~~CI/CD Tools~~ (7 entries)
- ~~Linters & Formatters~~ (8 entries)
- ~~Data Processing~~ (7 entries)
- ~~AI/ML Libraries~~ (8 entries)
- ~~Go Libraries~~ (7 entries)
- ~~Databases~~ (8 entries)
