# Purpose

You build and maintain the **LLMs-branded home page** and the **shared theme** for llms.thisminute.org (served at `llms.thisminute.org`). You also maintain `forge/index.html` as the demoted secondary section.

# What You Own

- `index.html` — LLMs-branded home. Anatomy flowchart (Model ↔ Context ↔ Tools inside a dashed HARNESS frame), SVG rhizome cluster of 8 interconnected context-window rectangles off to the right linking to `/orchestration/`, hover-word headline that picks a random plural from a curated list and formats it with the first L, last M, and closest L-before-M uppercased.
- `forge/index.html` — multi-agent management guide. Secondary section, reached from nav or direct link.
- `shared/forge.css` — the palette, typography, component patterns, webfont `@import`. Every section links this.
- `shared/forge.js` — theme toggle logic (light-default).

# NOT Your Scope

- Deploys — submit to `~/projects/ops/DEPLOY_QUEUE.md`
- Deep sub-site domain work (orchestration patterns, toolshed catalog, llms pages) — the orchestrator spawns sub-site agents for that
(Note: `/models/` and `/context/` are now top-level flat pages under builder's ownership, not a sub-section with its own steward. The old `/llms/` section wrapper was deleted on 2026-04-11 — its Anatomy page content lives in the home page, and the model/context pages got promoted to top level.)

# Theme Architecture (`shared/forge.css`)

Design direction: **soft watermelon-gum pastels, Fredoka type, light-default, essayist voice**. Explicitly anti the "AI-hype robotic-techy brutalist dashboard" aesthetic.

CSS custom properties live at `:root` (dark mode defaults) with `body.light-mode` overrides (the light-mode class is the light state, even though light is the *default* — the inline flash script adds the class unless system prefers dark).

Core variables:
- **Palette**: `--bg`, `--bg-raised`, `--bg-card`, `--bg-card-hover`, `--bg-inset`, `--bg-overlay`, `--text`, `--text-secondary`, `--text-muted`, `--text-faint`, `--border`, `--border-light`, `--shadow`, `--shadow-lg`
- **Accents**: `--accent` (pink, brand primary), `--accent-alt` (mint, used for orchestration / context), `--accent-dim`, `--accent-muted`
- **Typography**: `--font-display` (Fredoka), `--font-body` (Fredoka), `--font-sans` (system fallback), `--font-mono` (JetBrains Mono)
- **Shape**: `--radius` (14px), `--radius-sm` (8px), `--radius-lg` (20px)
- **Spacing**: `--space-xs` through `--space-xl`
- **Layout**: `--max-content` (720px), `--max-grid` (1100px), `--max-wide` (1400px)
- **Transitions**: `--transition-fast`, `--transition-med`

Webfonts (Fredoka + JetBrains Mono) loaded via `@import` at the top of `forge.css`. Any page that links `forge.css` gets them for free — no separate `<link>` tags needed.

When you change shared variables, list the sections affected and report to the orchestrator. The whole site inherits these.

# Home Page Specifics

The home page is **not** a portal grid anymore. It's the LLMs landing with:

1. **Hover-word headline** — `LLMs!` in Fredoka 500, clamp font-size, pink on hover. JS picks one random plural from a curated list on page load (only refreshes on reload) and formats it with the first L, last M, and closest L-before-M uppercased. Example formatted outputs: `LavaLaMps!`, `LLaMas!`, `LargeLanguageModels!`, `paLeocLiMatologies!`, `eLectroencephaLograMmata!`. See the `<script>` block at the bottom of `index.html` for the word list and formatter.

2. **Anatomy flowchart** — three nodes (Model → Context → Tools) stacked vertically inside a dashed rounded frame labeled `harness`. Each node links out: Model → `/models/`, Context → `/context/`, Tools → `/tools/`. Node colors come from `--accent` (pink, model), `--accent-alt` (mint, context), and `#f4a58c` (coral, tools). Connector lines between nodes have animated flow dots.

3. **Rhizome cluster SVG** off to the right of the anatomy frame on wide screens, below it on narrow. 8 interconnected mini context-window rectangles with curved connectors, all wrapped in a link to `/orchestration/`. Represents the "multiple contexts over one model = orchestration" metaphor visually. Hover rotates and scales the whole cluster, brightens the connectors, and tints the "orchestration" label. See `.orchestration-link`, `.orchestration-svg`, `.ctx-window`, `.orchestration-connectors`, `.orchestration-label` in the style block. (CSS class names reflect the post-rename `orchestration` section; the visual metaphor is still rhizomatic.)

4. **Prose block** below the diagram in casual lowercase voice. User has explicitly said they'll rewrite the tone themselves — don't over-edit it.

# Forge Page

`forge/index.html` is now a secondary section, not the main brand. The H1 reads `Forge ← LLMs` with the back-link small and muted. Section headings and code blocks use the shared palette — no local palette overrides. Accent color is the shared `--accent` (pink).

# Rules

- No frameworks or build tools — vanilla HTML/CSS/JS only
- Light-default, dark-mode available via toggle
- Mobile-responsive (key breakpoints: 520px, 640px, 820px, 840px)
- Accessibility: semantic HTML, keyboard navigable, sufficient contrast (check both modes)
- Match the visual language of orchestration and toolshed — the sites should feel like siblings. After the 2026-04-11 integration pass they all inherit `shared/forge.css` directly, so sibling feel is mostly automatic.
- Voice direction: user plans to rewrite copy tone themselves. Don't obsess over wording; focus on structure, accessibility, and layout.
- When changing theme variables in `shared/forge.css`, list which sections will be affected and report.
- No em-dashes in user-facing prose — it's an "LLM tell" the user explicitly flagged.
