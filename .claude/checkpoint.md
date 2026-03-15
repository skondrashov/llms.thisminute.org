# Checkpoint — 2026-03-15

## Architecture change

The top-level orchestrator now coordinates the entire repo. Sub-site agent files stay in place but the orchestrator spawns them directly. See `agents/orchestrator.md`.

Files updated: `AGENTS.md`, `agents/orchestrator.md`, `agents/builder.md`, `agents/skeptic.md`.

## What was done

### Session 5 (current)

Forge is actively developing — things are in flux. Reviewed and fixed what's stable.

- **Skeptic review** of all uncommitted changes: 1 security, 6 warning, 5 note — fixed 4 items:
  - Crucible: escaped `idea.id` in `data-id` attribute (defense-in-depth XSS prevention)
  - Crucible: added `aria-pressed` to filter toggle buttons
  - Toolshed schema: added `^[a-z0-9-]+$` pattern to `crucibleId` field
  - Note: `pipeline/bellows.py` with `os.system()` was removed by forge before fix was applied
- Verified: mermaid SRI hash valid, focus trap correct, highlightText XSS fix correct
- Verified: crucible build.py produces 8 ideas, 5 categories, 3 coordination models

### Session 4 (prior)
- 3 new executable tools: contrast_checker, cron_parser, license_checker (277 tests passing)
  - Skeptic review caught: hardcoded test paths, missing `__future__` import, undocumented AND semantics — all fixed
- Cross-site og: meta tags added (portal, forge, toolshed)
- CSS variable alignment: portal now has same base set as forge/toolshed (--bg-card, --accent, --radius-sm, etc.)
- Forge: --shadow CSS variable replaces hardcoded rgba hover shadows
- Forge: quick start warning now explains security pipeline, links to #security section
- Forge: version bump v0.3 → v0.4 (clone command + CLAUDE.md link + security_review.md)
- Forge: merged duplicate .header CSS rule
- Rhizome: overlay focus management (shortcuts + field notes — saves trigger, restores on close)
- Rhizome: popstate race fixed with async/await + finally block
- Toolshed: semantic `<header>` + `<main>` landmarks
- Toolshed: localStorage guarded in try/catch, detail panel gets role="dialog"
- Evolution.html: respects prefers-color-scheme when no saved theme
- Skeptic DRY pass: 2 security, 3 critical, 7 warning, 7 note — critical items fixed

### Session 3 (prior)
- Cross-site consistency: standardized breakpoint to 600px, `--radius` to 10px
- Forge: hover shadows for dark-mode visibility
- Rhizome: evolution cross-site nav, keyboard-accessible filters, sticky mobile search, popstate, theme-aware mermaid
- Skeptic review: 0 critical, 3 warnings fixed

### Session 2 (prior)
- Orchestrator authority expansion, builder/skeptic boundary fixes
- Forge page: 7 fixes (semantic header, nav, focus-visible, heading hierarchy, theme toggle)

### Session 1 (prior)
- Portal hub page, DRY pass, toolshed rename, domain fixes
- Forge role grid, pattern library links
- Rhizome evolution case link, field notes trigger
- Balatro scorer tool

## Uncommitted changes

Significant — forge is actively developing. Changes span:
- Portal: new vision statement, crucible card, 2-col grid, updated meta/tagline
- Forge: Plausible crossorigin
- Rhizome: mermaid SRI pinned to @10.9.1, highlightText XSS fix, similar-chip keyboard a11y
- Toolshed: focus trap, focus-visible styles, similar-item keyboard a11y, crucibleId schema field
- Evolution: Plausible crossorigin
- Crucible (new sub-site): 8 seed ideas, filterable UI, build script, schema

## In progress

- Forge is actively developing — pipeline/bellows.py and agents/bellows.md appeared and were removed during this session. Expect further changes.
- S38 worktree branch `worktree-agent-a9345a0f` no longer exists — results likely merged or abandoned.

## Deferred

### Skeptic S5 findings (not yet fixed)
- Crucible: missing sibling nav links (Rhizome, Toolshed, Agent Forge) — breaks cross-site nav pattern
- bellows.py: if it returns, needs `subprocess.run()` instead of `os.system()`, and schema validation on JSON input
- bellows.py: `--publish` writes TODO placeholders into source data

### DRY / code cleanliness (pre-existing)
- Toolshed: Fisher-Yates shuffle duplicated 3x — extract to helper
- Toolshed: getFilteredEntries/getSearchResults duplicate sort logic — extract shared sortResults()
- Cross-site: CSS variable naming — rhizome uses --bg-primary/--text-primary convention vs --bg/--text everywhere else
- Cross-site: theme toggle logic copy-pasted across 6 files (worse with crucible added)

### Catalog
- S38 miscategorization status unknown (worktree gone)
- Thin categories: Mobile IDE (11), Flashcards (14), Desktop App (15), HR & People (16)
