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

## Known remaining UX tasks
- Semantic HTML improvements -- backlog
- Consider search highlighting in detail panel "About" section
- Consider adding category filter count to the mobile button (e.g., "3 active filters")
