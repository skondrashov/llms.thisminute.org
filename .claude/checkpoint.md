# Checkpoint — 2026-03-15

## Architecture change

The top-level orchestrator now coordinates the entire repo. Sub-site agent files stay in place but the orchestrator spawns them directly. See `agents/orchestrator.md`.

Files updated: `AGENTS.md`, `agents/orchestrator.md`, `agents/builder.md`, `agents/skeptic.md`.

## What was done

### Session 3 (current)
- Cross-site consistency: standardized breakpoint to 600px (portal was 700px), `--radius` to 10px (portal/rhizome were 12px)
- Forge: added `box-shadow` to `.role-card:hover` and `a.pattern-item:hover` for dark-mode visibility
- Rhizome evolution.html: added `.other-projects` cross-site nav (matching all other pages), removed redundant page-footer
- Rhizome: filter panel headers now keyboard-accessible (`role="button"`, `tabindex="0"`, `aria-expanded`, keydown handlers)
- Rhizome: mobile search stays sticky (was `position: static`, now inherits `sticky`)
- Rhizome: popstate listener for browser back/forward with `pushState` on detail open
- Rhizome: mermaid initialization is now theme-aware (re-initializes on toggle)
- Skeptic review: 0 critical, 3 warnings fixed (aria-expanded, focus-visible, class naming)

### Session 2 (prior)
- Orchestrator authority expansion (portal → everything)
- Absorbed sub-site orchestrator memories and context
- Trimmed orchestrator file post-reflection (roster was aspirational, now lean with pointers)
- Fixed stale boundary language in builder.md and skeptic.md
- Forge page: 7 fixes (semantic `<header>`, portal nav link, focus-visible styles, heading hierarchy, tagline element, fixed theme toggle, summary focus)
- Skeptic review: portal clean, forge warnings all resolved

### Session 1 (prior)
- Portal hub page, DRY pass, toolshed rename, domain fixes
- Forge role grid, pattern library links, nav/theme upgrades
- Rhizome evolution case link, field notes trigger, 7 HTML tests
- Balatro scorer tool (rough draft in toolshed/tools/)

## Uncommitted changes

Session 3 changes need commit + push + deploy.

## Deferred

### Portal/Forge (minor polish)
- CSS variable naming divergence (portal has 6 vars, forge 8, rhizome 16+)
- Theme icon SVG duplication across 5 files (same paths, different IDs on evolution.html)
- Forge hover shadow is hardcoded `rgba(0,0,0,0.25)` — may be too heavy in light mode

### Rhizome (minor polish)
- Shortcuts overlay and field notes overlay: no initial focus management (have `role="dialog"` but no focus call on open)
- Popstate async race: `handlingPopstate` flag works now but fragile if `openDetail` is refactored to `await` before history call

### Toolshed
- S38: 50% miscategorization in discovered entries (systemic — biggest open issue)
- Thin categories: Mobile IDE (11), Flashcards (14), Desktop App (15), HR & People (16)
- No og: tags, non-semantic `<header>`, 5 dead links
