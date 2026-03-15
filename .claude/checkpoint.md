# Checkpoint — 2026-03-15

## Architecture change

The top-level orchestrator now coordinates the entire repo. Sub-site agent files stay in place but the orchestrator spawns them directly. See `agents/orchestrator.md`.

Files updated: `AGENTS.md`, `agents/orchestrator.md`, `agents/builder.md`, `agents/skeptic.md`.

## What was done

### Session 2 (current)
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

All work from both sessions needs commit + push + deploy.

## Deferred

### Portal/Forge (minor polish)
- Dark-mode card hover shadow barely visible
- Breakpoint inconsistency: portal 700px vs forge 600px
- CSS variable naming divergence between portal and forge
- `--radius`: portal 12px vs forge 10px
- Theme icon SVG duplication across files

### Rhizome
- Mermaid diagrams hardcoded to dark theme
- No popstate listener, filter headers not keyboard-accessible
- Focus trap/initial focus missing
- Mobile search scrolls away
- evolution.html missing cross-site nav
- Large uncommitted diff from prior sessions

### Toolshed
- S38: 50% miscategorization in discovered entries (systemic — biggest open issue)
- Thin categories: Mobile IDE (11), Flashcards (14), Desktop App (15), HR & People (16)
- No og: tags, non-semantic `<header>`, 5 dead links
