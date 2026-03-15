# Checkpoint — 2026-03-15

## What was done

### Portal page
- New `index.html` at root — hub with three cards (Forge, Rhizome, Toolshed)
- Uses semantic landmarks (`<main>`, `<header>`, `<nav>`)
- Focus-visible styles, unified theme key with system preference detection

### DRY pass across all sub-sites
- Unified localStorage key: `thisminute_theme` (was forge_theme, rhizome_theme, mainmenu_theme)
- Cross-site nav paths standardized to absolute with trailing slashes
- `<nav aria-label>` landmarks, focus-visible styles, theme toggle outside nav — all sites
- Consistent error handling: try-catch on all localStorage reads/writes
- System preference detection + change listener on all pages including evolution.html
- Icon button size standardized to 34px (was 36px in rhizome)

### Toolshed rename
- "Main Menu" → "Toolshed" across all user-facing text (title, h1, breadcrumbs, noscript, JSON-LD)
- JSON-LD URL fixed: thisminute.org/mainmenu → forge.thisminute.org/toolshed
- Cross-site nav labels updated in forge and rhizome

### Domain fixes
- Rhizome og:url and og:image: thisminute.org → forge.thisminute.org
- Evolution.html links: absolute URLs to thisminute.org → relative paths (/forge/, /rhizome/)
- Evolution.html: added Plausible analytics (was missing)

### Forge page improvements
- Role grid: 2x2 layout (fixes orphaned 4th card)
- Pattern Library links to rhizome entries (steward-bootstrap, protocol-forum-product-team, reflection-loop)
- Nav landmark, focus styles, theme JS upgraded

### Rhizome improvements
- Evolution case link fixed: href="evolution" → href="evolution.html"
- Field notes: added inline "Read the field notes →" trigger near intro blurb
- 7 new HTML tests (test_html.py): link resolution, trailing slashes, theme key, field notes

### First executable tool
- `toolshed/tools/balatro_scorer/` — Balatro first-blind hand evaluator + optimizer
- 31 tests, CLI + library interface
- Rough draft — to be refined by domain expert

### Docs updated
- AGENTS.md, builder.md reflect new portal architecture
- Toolshed librarian pass (docs, forum, memory cleanup)

## Deferred (not broken, just polish)
- Forge/toolshed use `<div class="header">` not semantic `<header>` — minor
- Mermaid diagrams in rhizome hardcoded to dark theme
- Theme icon SVG duplication across files (could extract to shared file)
- evolution.html missing cross-site "Also:" nav (has footer links instead)
- No og: tags on toolshed

## Deploy
- Needs commit + push, then deploy
