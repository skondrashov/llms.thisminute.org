# Designer Memory

## Completed work (as of 2026-03-14)

### Already implemented (prior sessions)
- Cmd/Ctrl+K search shortcut
- Live result count
- Category-colored card borders (22 group colors from taxonomy)
- Dark/Light mode toggle with CSS custom properties, localStorage, SVG icons
- Light mode CSS variables (warm whites, subtle shadows)
- `prefers-color-scheme` support as default when no localStorage preference exists
- Light-mode overrides for detail panel elements (close btn, OS badges, tags, similar items, hover shadows)
- "See Also" section in detail panel: shows up to 4 entries from same category, shuffled, clickable
- "Copy Link" button in detail panel: copies fragment URL to clipboard, "Copied!" feedback for 1.5s

### Implemented this session (Designer Cycle 2)
- **Mobile category navigation**: Floating "Categories" button (bottom-right, <=900px only) + bottom-sheet panel with full taxonomy tree drill-down. Panel slides up, has scrim backdrop, back button, drill-down navigation. Button shows current category name + depth badge when navigated. Closes on scrim tap, close button, or Escape.
- **Search highlighting**: `<mark class="search-hl">` wraps matching substrings in card names and descriptions during search. Case-insensitive. Amber-tinted background in both themes. Only applied to rendered cards (performance safe). Uses `highlightText()` function that operates on HTML-escaped text to prevent XSS.

## Architecture notes

- `index.html` is ~79K lines (mostly noscript catalog). All CSS/JS is inline.
- The `openDetail(id)` function builds HTML string for the detail panel. All detail panel features go here.
- `CATEGORY_COLORS` maps category names to hex colors, built from `GROUP_COLORS` + taxonomy walk.
- `state.data` is the full SOFTWARE array. Filter same-category entries with `state.data.filter(s => s.category === e.category)`.
- Light mode uses `body.light-mode` class. Elements with hardcoded `rgba(255,255,255,...)` need `body.light-mode` overrides.
- Build: `python build.py` injects noscript catalog into index.html, so the file gets rebuilt.
- Mobile breakpoint: 900px. Detail panel goes to 100vw on mobile.
- Mobile category panel: `catPanelPath` is separate from `state.path` — the panel has its own drill-down state. On leaf selection, it writes to `state.path` and re-renders.
- `highlightText(text, query)`: escapes text first via `esc()`, then does case-insensitive indexOf loop to wrap matches in `<mark>` tags. Safe because HTML is escaped before highlight insertion.
- The `renderCards` function checks `state.query` to decide whether to call `highlightText` or plain `esc`.

### Implemented this session (Designer Cycle 3 -- forge polish)
- **Covered vs unique indicators**: `.forge-covered` class dims submitted cards with `alternatives: "covered"` to 72% opacity. "Alternatives now available" italic note below validation info.
- **Forge summary split**: "Built by Forge" stat shows "N unique / M covered" sub-line in green/gray.
- **Requests sparse message**: Contextual message when requests view has <=5 entries all tagged `forge-infra`.
- **Forge tag bar**: `TAG_EXCLUDE_FORGE` set excludes `cli` and `developer-tools` in forge views so domain-specific tags surface.
- **Banner description demoted**: Forge summary description text reduced to `0.78rem`/`--text-muted` (was `0.82rem`/`--text-secondary`).

## Architecture notes (forge views)

- `renderCards` adds `forge-covered` class and `coveredHtml` for submitted tools with `triage.alternatives === 'covered'`.
- `renderForgeSummary` computes `coveredCount` and `uniqueCount` from `getSubmitted()`.
- `TAG_EXCLUDE_FORGE` is a superset of `TAG_EXCLUDE` used only when `state.view` is `requests` or `built`.
- Sparse-view message logic checks `forgeEntries.every(e => e.tags.indexOf('forge-infra') !== -1)`.

### Implemented this session (Designer Cycle 4 -- forge search surfacing)
- **Forge sort boost**: `isForgeEntry(e)` helper added. In `sortResults()`, when sorting by category and searching in "All" view, forge entries are boosted to the top of results. No boost without a query or in scoped views.
- **Forge count in search results**: Search count now shows "X results (N from forge)" when forge matches exist in "All" view. Updated in both main search handler and detail-panel tag-click handler.
- **Forge-specific search highlight colors**: `mark.search-hl` on `.card.forge-idea` uses green (`rgba(52, 211, 153, 0.3)`), on `.card.forge-submitted` uses blue (`rgba(96, 165, 250, 0.3)`). Light-mode variants included.

## Architecture notes (forge search surfacing)

- `isForgeEntry(e)` is a standalone helper at module scope (line ~1492), reused by both `sortResults` and the search count display code.
- Sort boost only activates when `state.query && state.view === 'all'` -- this avoids disrupting taxonomy browsing and view-scoped results.
- Search count forge label uses `results.filter(isForgeEntry).length` -- computed from the already-filtered result set so it's always accurate with active filters.
- CSS highlight overrides use `.card.forge-idea mark.search-hl` and `.card.forge-submitted mark.search-hl` specificity -- inherits `color: inherit`, `border-radius`, `padding` from base rule.

## Known remaining UX tasks
- Semantic HTML improvements -- backlog
- Consider search highlighting in detail panel "About" section
- Consider adding category filter count to the mobile button (e.g., "3 active filters")
- S57: View switching resets language/tag but not os/pricing -- potential UX confusion
