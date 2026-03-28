# Checkpoint — 2026-03-22

## Architecture change

The top-level orchestrator now coordinates the entire repo. Sub-site agent files stay in place but the orchestrator spawns them directly. See `agents/orchestrator.md`.

Files updated: `AGENTS.md`, `agents/orchestrator.md`, `agents/builder.md`, `agents/skeptic.md`.

## What was done

### Session 9 (current)

Toolshed final thin-category expansion + Rhizome LLM agent orchestration research and UI.

- **Phase 1:** Health check across all 4 sites. All healthy — no critical bugs, shared CSS/JS working, all cross-links valid.

- **Phase 2:** Toolshed curator cycle 76 — final 3 thin categories expanded: HR & People (27→32), Chess (27→32), APIs & Services (27→34). +17 curated, -2 discovered. **No thin categories remain.**

- **Phase 3:** Rhizome steward researched 30+ real-world LLM agent orchestration frameworks (LangGraph, CrewAI, AutoGen, MetaGPT, ChatDev, OpenAI Swarm, Devin, Replit Agent, etc.). Tagged 24 existing patterns with `llm-agent`, created 9 new patterns in `structures/llm_agent_orchestration.json`. New patterns: graph-state-machine, role-play-dialogue-pair, sop-driven-software-team, conversational-group-chat, supervisor-router, agent-as-tool, skill-library-curriculum, plan-code-verify-loop, generative-agent-society.

- **Phase 4:** Skeptic review of steward's work. 0 bugs, 2 warnings, 5 notes:
  - WARNING: role-play-dialogue-pair had `adversarial` hierarchy type for cooperative pattern → fixed to `["mesh"]`
  - WARNING: agent-as-tool overlapped with tool-specialist-ring (duplicate LlamaIndex citation) → fixed tool-specialist-ring realWorldExample
  - NOTEs: minor imprecisions in framework attributions (ADK topology, MetaGPT benchmark specificity, AutoGen 0.4 framing, Voyager attribution, Anthropic internal system claim) — acceptable

- **Phase 5:** Builder added LLM Agent Orchestration toggle to rhizome UI (`index.html`). Pill-style toggle above filter panels, green accent when active, works with existing category/structure/search filters, mobile-responsive, accessible (`role="switch"`, `aria-checked`).

**Rhizome: 215 patterns (was 206), 33 tagged `documented`, 99 tests passing.**
**Toolshed: 16,052 entries (1,555 curated + 14,497 discovered), 67 tests passing. All categories ≥30.**

- **Phase 6:** Rhizome UI rework — replaced documented toggle with Origin/Structure/Field dropdown filters, side-by-side, collapsed by default, overlaying content. Origin has 4 domains: Agentic, Organizational, Computational, Natural. Descriptions appear under each dropdown when a filter is selected. "Category" renamed to "Field". Header simplified — removed "200 ways to organize", concise intro.

- **Phase 7:** Portal splash page updated with self-obsolescence sentiment.

- **Phase 8:** Massive toolshed expansion — 11 new categories, ~95 curated entries across 6 new data files:
  - `data/game_modding.json` — 23 entries (Balatro, Minecraft, Skyrim, Stardew Valley, Unity, Unreal, etc.)
  - `data/cli_data_tools.json` — 8 entries (fx, dasel, xsv, q, visidata, diff-so-fancy, delta, mkcert)
  - `data/specialized_engineering.json` — 26 entries (Reverse Engineering, Emulators, Robotics, Embedded)
  - `data/geospatial.json` — 16 entries (GIS & Mapping)
  - `data/creative_tech.json` — 29 entries (Creative Coding, Audio Programming, Graphics Programming, 3D Printing)
  - `data/observability.json` + `data/browser_automation.json` — 13 entries (Monitoring, Browser Automation, Extensions)
  - taxonomy.json updated with all new categories and groups

**Toolshed: 16,135 entries across 134 categories (was 124).**

### Session 8 (prior)

Cross-site DRY cleanup: theme toggle and CSS variable deduplication.

- **Phase 1:** Health check across all 4 sites + 5 HTML pages. Found: theme toggle duplication (5 files, 2 patterns), crucible link indirection in toolshed, missing og:image on 3 pages. Everything else healthy.

- **Phase 2:** Landing page DRY cleanup (`index.html`): added `shared/forge.css` + `shared/forge.js`, removed duplicated CSS reset, shared variables, body styles, icon-btn styles, and inline theme toggle JS. 244→167 lines.

- **Phase 3:** Forge page DRY cleanup (`forge/index.html`): removed duplicated shared CSS variables, reset, and body styles. Kept site-specific vars (`--bg-card`, `--accent-dim`, `--accent-text`).

- **Phase 4:** Fixed toolshed crucible link (`toolshed/index.html` line 1872): `/crucible/#id` → `/toolshed/#id` since crucible was merged into toolshed and the redirect doesn't preserve hash fragments.

- **Phase 5:** Skeptic review of all changes. 0 bugs, 2 warnings:
  - WARNING: Unused CSS vars on landing page → cleaned (removed `--bg-card`, `--bg-card-hover`, `--accent-dim`, `--accent-text`)
  - WARNING: No `hashchange` listener for same-page crucible origin links → pre-existing, moot (no entries use `crucibleId` yet)

**All 5 HTML pages now use `shared/forge.css` + `shared/forge.js` for theme toggle, reset, body styles, and shared variables. No more duplication.**

### Session 7 (prior)

Skeptic review of prior toolshed commit, then 3 curator cycles to fill thin categories, skeptic spot-check, and builder fixes.

- **Phase 1:** Skeptic reviewed commit b8bab62 (~2700 lines). Found 2 bugs, 3 warnings, 4 notes:
  - BUG: `tmp_indexdiff.txt` accidentally committed → removed, added to .gitignore
  - BUG: Stale counts in STRATEGY.md COMPLETED section → fixed
  - WARNING: Dead code in http_security_analyzer/analyzer.py → removed
  - WARNING: Permissions-Policy docstring overclaimed implementation → fixed
  - WARNING: TimescaleDB URL redirect to tigerdata.com (noted)

- **Phase 2:** Curator cycle 73 — Media Processing (23→33), Desktop App Frameworks (25→32), Statistical Tools (25→32). +24 curated, -5 discovered.

- **Phase 3:** Curator cycle 74 — Mobile IDE & Tools (25→36), Task Runners & Monorepos (25→35), Video Conferencing (25→37). +35 curated, -8 discovered.

- **Phase 4:** Skeptic spot-check of cycles 73-74 found S82-S89:
  - S82 (BUG): play-js URL defunct → updated to CodeSandbox iOS
  - S84 (BUG): wireit wrong repo → fixed to google/wireit
  - S85 (BUG): around.co defunct → removed
  - S87 (BUG): bluejeans defunct → removed
  - S83 (WARNING): cef-framework URL → updated to GitHub
  - S86 (WARNING): hopin acquired → updated to RingCentral Events
  - S88 (WARNING): rapidminer acquired → updated to Altair RapidMiner
  - S89 (WARNING): nw-js/pyqt duplicates → checked, none found

- **Phase 5:** Curator cycle 75 — Flashcards & Study (26→32), Secrets Management (26→30), Vector Databases (26→31). +21 curated, -6 discovered.

- **Phase 6:** Updated AGENTS.md, STRATEGY.md counts. Thin categories list reduced to 3 (APIs & Services 27, Chess 27, HR & People 27).

**Final state:** 16,037 entries (1,538 curated + 14,499 discovered), 67 tests passing. All categories ≥27.

### Session 6 (prior)

Cross-site polish, DRY cleanup, CSS normalization.

- Crucible sub-site, security fixes, cross-site a11y polish (144e6fa)
- Cross-site nav links to crucible (0a5b4cd)
- Toolshed DRY — shuffleArray() + sortResults() helpers (69a30d0)
- Rhizome CSS variables normalized (144414e)

### Session 5 (prior)

Skeptic review of uncommitted changes: 1 security, 6 warning, 5 note — fixed 4 items.

### Session 4 (prior)

3 new executable tools, cross-site og: meta tags, CSS variable alignment, forge v0.4, rhizome overlay focus, toolshed semantic HTML.

### Session 3 (prior)

Cross-site consistency, forge hover shadows, rhizome evolution features.

### Session 2 (prior)

Orchestrator authority expansion, forge page fixes.

### Session 1 (prior)

Portal hub page, DRY pass, toolshed rename, domain fixes.

## Uncommitted changes

Session 7+8+9 combined:
- .gitignore expanded (tmp_*.txt, __pycache__, .pytest_cache)
- tmp_indexdiff.txt removed
- Portal: `index.html` DRY cleanup (shared forge.css/forge.js, removed inline duplication)
- Forge: `forge/index.html` DRY cleanup (removed duplicated shared CSS vars, reset, body)
- Toolshed: 97 new curated entries across 12 categories, ~21 discovered removed
- Toolshed: 8 data quality fixes (S82-S89)
- Toolshed: http_security_analyzer dead code + docstring fixed
- Toolshed: crucible link fix (`/crucible/#id` → `/toolshed/#id`)
- Toolshed: AGENTS.md, STRATEGY.md, FORUM.md counts updated
- Toolshed: index.html, llms.txt, llms-full.txt regenerated by build.py
- Rhizome: 9 new LLM agent orchestration patterns in `structures/llm_agent_orchestration.json`
- Rhizome: 24 existing patterns tagged `documented` with enriched realWorldExamples
- Rhizome: structural-classes.json updated with 9 new mappings
- Rhizome: "Documented Implementations" toggle added to `index.html` (CSS, HTML, JS, mobile sync)
- Rhizome: data.js rebuilt (215 patterns, 33 documented)
- Rhizome: skeptic fixes (hierarchy type correction, citation dedup)

## In progress

- Forge is actively developing — pipeline and bellows work handled by thisminute-forge. Don't touch `pipeline/` or `agents/bellows.md`.

## Deferred

### bellows (forge's domain)
- bellows.py: if it returns, needs `subprocess.run()` instead of `os.system()`, and schema validation on JSON input

### DRY / code cleanliness (remaining)
- ~~Cross-site: theme toggle logic~~ — RESOLVED in session 8 (all pages use shared forge.css/forge.js)
- No `hashchange` listener in toolshed for same-page `#id` links (moot until entries use `crucibleId`)

### Catalog
- TimescaleDB URL redirect to tigerdata.com — curator should update when stable
- ~~Remaining thin categories: APIs & Services (27), Chess (27), HR & People (27)~~ — RESOLVED in session 9 (all ≥30)
