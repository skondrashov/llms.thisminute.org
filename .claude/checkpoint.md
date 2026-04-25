# Checkpoint — 2026-04-20

## Current state

Agent consolidation (11 → 5 roles) complete. Code quality pass complete. All committed and pushed.

Last content commit: `0028177` (tone + sentence-case audit, 2026-04-15).

### Counts

- Orchestration: 277 patterns, 99 tests passing
- Tools: 16,150 entries across 135 categories, 67 tests passing
- Playwright e2e: 16 tests passing

### Session work (2026-04-20)

- **Agent consolidation**: 11 section-level roles → 5 top-level roles. Old agent files deleted, new curators created, memory files relocated to `memory/`.
- **Tools tests: 5 failures → 0.** Remapped 4 orphan categories, renamed "Dolphin" → "Dolphin Emulator", removed 36 duplicate-ID and 5 duplicate-URL entries.
- **Title tag consistency**: Standardized forge/ and tools/ titles to "Section · LLMs · thisminute.org" format.
- **Rebuilt tools**: `data.js`, `taxonomy.js`, API endpoints, llms.txt all regenerated.
- **Fixed orchestration filter bug**: `updateFilterDescriptionss` (typo) → `updateFilterDescriptions`.
- **Fixed domain tile counts**: Stale keys → current lens values.
- **Extracted orchestration JS**: 1,379 lines inline → `orchestration/app.js`.
- **Added ESLint**: `no-undef` rule, flat config (ESLint 9).
- **Added Playwright e2e tests**: 16 tests across 3 files.
- **Added Plausible analytics** to models/ and context/ (were missing).
- **Code quality pass**:
  - Removed dead `HIERARCHY_COLORS` constant (restored `HIERARCHY_LABELS` — still referenced)
  - Added 9 named constants, replaced all magic numbers
  - Consolidated panel header listeners (27 lines → 8 lines) and sort button listeners (7 lines → 3 lines)
  - Fixed duplicate theme toggle logic: two `t` key handlers used different code paths, now both delegate to forge theme button
  - Extracted mobile filter section header inline styles to `.mobile-section-label` CSS class
  - Extracted SW grid heading inline styles to `.sw-strengths` / `.sw-weaknesses` CSS classes
  - Removed duplicate `.site-label` / `.hero` CSS from context/index.html (already in forge.css)
  - Renamed stale "Agent Forge" → "the forge" in forge/index.html body text
  - Renamed stale "Toolshed" → "Tools" in tools/index.html heading and noscript
  - Standardized Plausible SRI comment across all pages
  - Updated stale "SITENAME FORGE" CSS comment

### Known issues

- Forge rename still pending user direction

## Deploy status

Deploy queued at `~/projects/ops/DEPLOY_QUEUE.md`. Major redesign + domain rename also queued (separate entry, predates this session).

## Deferred

- No `hashchange` listener in tools for same-page `#id` links (moot until entries use `crucibleId`)
- TimescaleDB URL redirect to tigerdata.com — curator should update when stable
- Cross-section nav: hub-and-spoke design is intentional, but no page has links to all 6 sections. Low priority.
