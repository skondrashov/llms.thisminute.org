# Checkpoint — 2026-04-11

## Architecture change (2026-04-09)

**Major reorganization**: forge.thisminute.org is now an agentic engineering education site with five sections: LLMs, Forge, Rhizome, Toolshed, and Portal. Previously it was a portal linking three sub-sites.

Key changes:
- `llms/` section added — interactive explainers on LLM fundamentals (copied from llms.thisminute.org, adapted paths)
- `llms/` gets its own steward agent (`llms/agents/steward.md`)
- Portal index.html redesigned: 2x2 grid with LLMs, Rhizome, Toolshed, Forge. Vision updated to "agentic engineering education."
- Toolshed "unfilled slots" concept formalized — ideas/requests renamed to "unfilled slots" in agent docs
- crucible/ fully absorbed (was already redirecting to toolshed; now conceptually replaced by unfilled slots)
- All agent files updated: AGENTS.md, orchestrator.md, builder.md, skeptic.md reflect unified site
- singularity-forge retired in the forge registry (premise was wrong — software gaps don't exist at scale)

Files created: `llms/index.html`, `llms/llm/index.html`, `llms/CLAUDE.md`, `llms/AGENTS.md`, `llms/agents/steward.md`
Files updated: `index.html`, `AGENTS.md`, `agents/orchestrator.md`, `agents/builder.md`, `agents/skeptic.md`, `toolshed/AGENTS.md`, `toolshed/agents/curator.md`

## Previous architecture change (2026-03-22)

The top-level orchestrator coordinates the entire repo. Sub-site agent files stay in place but the orchestrator spawns them directly. See `agents/orchestrator.md`.

## What was done

### Session 10

Site reorg + 2026 research pass + forge page polish.

- **Phase 1 — Forge page beginner's guide (2026-04-02, `b0d50b3`):** Added setup flow (spawn/create/ask workflow) above quick-start on `forge/index.html`.

- **Phase 2 — Forge readme link (2026-04-08, `238c4df`):** Readme link added above quick-start for first-time users (`forge/index.html`).

- **Phase 3 — 2026 research pass (2026-04-08, `cde8fd2`):**
  - Rhizome: 8 new patterns in `structures/round6_2026_update.json` — Protocol Split (A2A/MCP), Event-Driven Production Stack, Corporate Hierarchy with Budget Caps, Memory Distillation Pipeline, Metacognitive Self-Improvement Loop, Experiential Heuristic Library, Fractal Modularity, Diversity-Preserving Ensemble. `structural-classes.json` updated with new mappings.
  - Toolshed: 13 new entries in `data/2026_update.json` — OpenCode, Junie CLI, Gemini CLI, cmux, Ghostty, ty, uv, Octrafic, Clanker CLI, Devbox, Prowler, Termdock, Kilo Code CLI. `toolshed/index.html`, `llms.txt`, `llms-full.txt` regenerated.

- **Phase 4 — Site reorg (2026-04-09, `1954445`):** Portal redesigned as agentic engineering education site. See "Architecture change (2026-04-09)" note above for details. Adds `llms/` section with 2 pages live (`llms/index.html` Anatomy of an Agent, `llms/llm/index.html` token explainer) and a section steward. Portal 2x2 grid introduces LLMs/Rhizome/Toolshed/Forge. Toolshed "unfilled slots" concept formalized in agent docs.

**Rhizome: 269 patterns** (was 261 → +8 this session), counted from `rhizome/structures/*.json`. AGENTS.md and portal both say 269 ✓.
**Toolshed: ~16,050 entries** (was 16,037 per strategic docs; +13 from `data/2026_update.json`). Toolshed's own agent docs (`toolshed/AGENTS.md`, `STRATEGY.md`) still show 16,037 and should be updated on next curator pass.

### Session 9 (prior)

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

None. Git tree is clean as of 2026-04-11. Everything from sessions 7–10 is landed.

## In progress

- **llms section half-built**: 2 of 4 planned pages live. `/llms/` (Anatomy of an Agent) and `/llms/llm/` (token explainer) exist; `/llms/harness/` and `/llms/context/` still listed as *Planned* in `llms/AGENTS.md` with no folders.
- **llms visual split**: `llms/index.html` and `llms/llm/index.html` do not reference `shared/forge.css`. They use their own palette (deep blue `#07090e`) and fonts (Instrument Serif + JetBrains Mono), not the portal's warm orange. Skeptic policy (`agents/skeptic.md` line 36) is currently "flag inconsistencies but don't force adoption if the llms aesthetic works" — so this is intentional-for-now, but a navigation transition from `/` to `/llms/` feels like two different sites. Needs an explicit call: commit to the aesthetic split or plan an integration pass.
- **Toolshed entry count drift**: `cde8fd2` added 13 entries via `data/2026_update.json` but `toolshed/AGENTS.md` and `STRATEGY.md` still say 16,037. Curator should re-run `build.py` and update docs on next toolshed pass.

## Deferred

### DRY / code cleanliness (remaining)
- No `hashchange` listener in toolshed for same-page `#id` links (moot until entries use `crucibleId`)
- llms section theme split — see "In progress" above (promoted out of deferred; needs a direction call)

### Catalog
- TimescaleDB URL redirect to tigerdata.com — curator should update when stable
- ~~Remaining thin categories: APIs & Services (27), Chess (27), HR & People (27)~~ — RESOLVED in session 9 (all ≥30)

### Retired
- bellows: replaced by singularity-forge, which was itself retired 2026-04-09
- crucible: absorbed into toolshed as "unfilled slots"
