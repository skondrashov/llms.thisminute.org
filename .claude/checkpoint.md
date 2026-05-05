# Checkpoint — 2026-05-04

## Current state

Portfolio polish session in progress. Major changes landed but uncommitted (10 files, ~81K lines net change mostly from removing tools noscript fallback).

### What's done

#### Navigation overhaul (A1 + A9)
- Added shared `.site-nav` component to `shared/forge.css` (mono font, uppercase, flex-wrap, aria-current)
- All pages now have consistent 7-link nav: LLMs / Models / Context / Tools / Harnesses / Orchestration / Forge
  - **EXCEPTION**: `tools/index.html` nav is missing the Harnesses link (edit failed twice due to file modification errors). Currently has 6 links.
- Removed footers from home, models, context
- Removed h1 back-links from forge, orchestration, tools (nav handles navigation now)
- Source link moved to top-right on homepage (fixed position, aligned with theme toggle)

#### Homepage restructure (A2)
- CSS Grid layout: `auto/auto/1fr/auto` rows for viewport-height constraint
- Explainer paragraph above diagram with bold linked keywords (harness, LLM, context, tools)
- Forge link pill at bottom: "Interested in orchestration for your project? Try the forge!"
- Mobile fallback allows scrolling (flex column for <=840px)
- `overflow: hidden` on desktop body to prevent scrollbar

#### Copy + naming fixes (A3 + A4)
- All "toolshed" → "tools" in tools/index.html and orchestration/evolution.html
- Meta descriptions updated (orchestration: "270+", tools: "16,000+" and "135 categories")
- Removed date qualifier from models page
- evolution.html: cache buster added, font preconnect added

#### Model data accuracy (A5)
- 13 new models added, 5 existing corrected (verified via web search)

#### SEO + meta (A7)
- OG tags added to models and context
- `robots.txt`, `sitemap.xml`, `404.html` created
- **sitemap.xml needs /harnesses/ added**

#### Performance (A8)
- Noscript fallback removed from tools/index.html (5.6MB → 789KB)
- Font preconnect added to all pages

#### Harnesses section created
- `harnesses/index.html` exists with full page skeleton, explainer sections, empty catalog
- Accent color: amber (#d4a574 dark / #b8864e light)
- Card render function wired up, groups by "setting" (CLI, IDE, Web, etc.)
- `HARNESSES = []` — **catalog data not yet populated**
- Harness research agent was running in background but context was lost; data needs to be gathered fresh

### What's NOT done

#### Homepage diagram copy updates (user's last request before restart)
User wants:
1. **HARNESS label**: higher contrast text + make it a clickable link to /harnesses/
2. **MODEL label** → "LARGE LANGUAGE MODEL" (or similar, more technical)
3. **Model node description**: replace current casual copy with: "The model itself only has one operation: Given a context, output a token. In a lot of ways, it is astonishing that this simple task has unlocked many secrets of language and of intelligence."
4. **Context node description**: needs update to match the more technical tone (user asked for my suggestions)
5. **Tools node description**: needs update to match the more technical tone (user asked for my suggestions)
6. **HARNESS blurb**: user also asked for a blurb on the harness label/section that matches the technical tone of the model description — "actually we should add a blurb for the HARNESS too that matches that tone, gimme something to start with"

Current diagram node copy (what to replace):
- Model: "You hand it a pile of tokens and it guesses the next one. That is the entire job. It also forgets everything the moment it's done, which is a bigger deal than it sounds."
- Context: "Everything the model actually gets to see on a given turn. If you want it to remember something, it has to live in here. There's nowhere else."
- Tools: "The model can't do anything on its own. It can't open files or go on the internet. You give it tools that can, and whatever the tool finds shows up in the context so the model sees what happened."
- Harness label: just says "harness" in --text-muted color, not clickable

#### tools/index.html: add Harnesses to nav
Current nav (line 1113-1120) has 6 links, missing Harnesses. Need to add `<a href="/harnesses/">Harnesses</a>` between Tools and Orchestration.

#### Harness catalog data
Need to research ~30-50 real harnesses and populate the HARNESSES array in harnesses/index.html. Group by setting: CLI, IDE extension, Web app, Desktop app, Embedded/SDK, Framework. Fields: name, vendor, setting, models, pricing, tags, summary, url.

#### sitemap.xml
Add `/harnesses/` URL.

#### Visual consistency (A6) — partially done
- Max-width standardization (some hardcoded values remain)
- Responsive testing at 375/768/1024/1440px not done

#### B-section review items (need user eyes)
- B3: Color contrast check (--text-muted borderline WCAG AA)
- B4: Forge naming/identity
- B5: Forge GitHub repo naming

#### C-section: evolution page
- Different color scheme (cyan/navy) vs site theme
- Title doesn't follow site pattern
- User hasn't decided if it should visually align

#### E-section: post-change verification
- All manual tests deferred until changes land

### Git status
- 10 files modified, nothing committed
- No new branch (working on main)
- New files: `harnesses/index.html`, `robots.txt`, `sitemap.xml`, `404.html`

### Files changed (for reference)
```
 AGENTS.md                    |     2 -
 context/index.html           |    31 +-
 forge/index.html             |    17 +-
 index.html                   |   127 +-
 memory/orchestrator.md       |     9 +
 models/index.html            |    67 +-
 orchestration/evolution.html |    40 +-
 orchestration/index.html     |    18 +-
 shared/forge.css             |    76 +-
 tools/index.html             | 80910 +---
```

## Execution order for next session

1. **Homepage diagram copy** — update all node descriptions + harness label (user's immediate request)
2. **tools/index.html nav** — add Harnesses link (quick fix)
3. **sitemap.xml** — add /harnesses/
4. **Harness catalog data** — research and populate (biggest remaining task)
5. **Visual consistency pass** — max-widths, responsive testing
6. **Surface B-items** for user review
7. **Commit** when user says so
