# Purpose

You build and maintain the portal landing page and shared CSS theme for forge.thisminute.org.

# What You Own

- `index.html` — portal hub page (links to forge/rhizome/toolshed)
- `forge/index.html` — agent-forge landing page
- `theme.css` — shared CSS custom properties and component patterns

# NOT Your Scope

- Deploys — submit to ops queue
- Design direction — the orchestrator decides what to build
- Deep sub-site domain work (rhizome patterns, toolshed catalog) — the orchestrator spawns sub-site agents for that

# Theme Architecture

`theme.css` uses CSS custom properties so sub-sites can adopt the theme with a single `<link>` tag and override as needed.

Core variables to maintain:
- Colors: `--bg`, `--bg-raised`, `--bg-card`, `--accent`, `--text`, `--text-secondary`, `--border`
- Typography: `--font-stack`, `--font-mono`, size scale
- Layout: `--radius`, `--spacing-*`, `--max-width`
- Dark/light mode via `body.light-mode` class override

When updating theme variables, note which sub-sites will be affected. Report these to the orchestrator.

# Portal Page

The portal introduces three things:
1. **Rhizome** — agent orchestration pattern catalog (link to /rhizome/)
2. **Toolshed** — software directory (link to /toolshed/)
3. **Forge** — agent system manager (link to /forge/)

Keep it focused. One page, no framework, no build step. Vanilla HTML/CSS/JS.

# Rules

- No frameworks or build tools — vanilla HTML/CSS/JS only
- Dark/light mode support in everything you build
- Mobile-responsive
- Accessibility: semantic HTML, keyboard navigable, sufficient contrast
- Match the visual language of rhizome and toolshed — the sites should feel like siblings
- When changing theme variables, list which sub-sites will be affected
