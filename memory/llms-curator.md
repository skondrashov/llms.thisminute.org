# LLMs Curator Memory

Seeded 2026-04-18 during the 11→5 agent consolidation. Tone/voice notes extracted from the top-level orchestrator memory; flat-page and site-voice decisions live here going forward.

## Voice and tone (stable, extracted from orchestrator memory 2026-04-11 session)

- The site is a softly spoken educational tool, explicitly anti "AI-hype techy brutalist dashboard."
- **No em-dashes** in user-facing prose — the user has flagged these as an "LLM tell" and does not want them. Replace with commas, periods, or restructuring.
- Other LLM tells worth flagging:
  - Parallel short punchy sentences ("A X is Y. A P is Q. R does S.") when they feel robotic
  - "Not X but Y" rhetorical constructions
  - Bolded-then-defined paragraphs
- Casual lowercase and run-on sentences are intentional voice, not mistakes — don't "correct" them.
- The user has said repeatedly that they'll handle tone/copy themselves. Don't over-rewrite prose. Structural work (layout, accessibility, links, new content scaffolding) is fair game without tone fussiness.

## Aesthetic (stable)

- Warm watermelon-gum pastels: pink `--accent`, mint `--accent-alt`, coral for tools accents
- Fredoka typeface (Fredoka + JetBrains Mono loaded via `@import` at the top of `shared/llms.css`)
- Light-mode default; dark-mode via toggle (the `body.light-mode` class is the light state)
- Rounded 14px radius, feathered warm shadows
- Parchment-cream light / warm-plum-dusk dark

## Architecture of the four flat sections (as of 2026-04-11)

- `/` (home, `index.html`) — LLMs-branded anatomy flowchart (Model ↔ Context ↔ Tools inside a dashed HARNESS frame) with an SVG rhizome cluster of 8 interconnected context-window rectangles off to the right linking to `/orchestration/`. Hover-word headline picks one random plural per page load (not a cycle) from a curated list and formats it with the first L, last M, and closest L-before-M uppercased.
- `/models/` — ~60-model catalog grouped by vendor, card grid
- `/context/` — context explainer with embedded statelessness demo, "what's filling our context?" breakdown, vision transformers section
- `/forge/` — multi-agent management guide (rename pending; secondary section; `← LLMs` back link in the header)

## Retired URLs (do not resurrect)

`/rhizome/`, `/crucible/`, `/toolshed/`, `/llms/`, `/llms/llm/`, `/llms/harness/`, `/llms/model/`, `/llms/context/`. If internal links to these resurface, that's a regression from the pre-2026-04-11 era.

## Historical-regression watch

The old `/llms/` section used to have Instrument Serif + a standalone navy-black dark palette. If Instrument Serif or a standalone dark palette shows up in `models/` or `context/`, it's drift from that pre-rebrand era — flag and fix.
