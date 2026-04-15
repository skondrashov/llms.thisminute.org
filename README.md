# LLMs · thisminute.org

An educational site about what's actually inside an AI agent. The home page is a visual anatomy diagram (model → context → tools inside a harness frame, with a rhizomatic cluster of context windows linking to orchestration). Each part of the diagram hands off to a deeper section.

Live at [llms.thisminute.org](https://llms.thisminute.org) — the domain predates the rebrand and isn't worth changing.

| Section | Path | What it is |
|---------|------|------------|
| **Home** | `/` | LLMs-branded anatomy flowchart with hover-word headline |
| **Models** | `/models/` | Catalog of ~60 real models grouped by 11 vendors |
| **Context** | `/context/` | Context explainer with embedded statelessness demo, "what's filling our context?" breakdown, vision transformers |
| **Orchestration** | `/orchestration/` | Catalog of 271 agent orchestration patterns, FastAPI + SQLite social layer |
| **Tools** | `/tools/` | Software directory (~16K entries, filled + unfilled slots) |
| **Forge** | `/forge/` | Multi-agent system management guide |

## Stack

Vanilla HTML/CSS/JS — no frameworks, no build step for the flat pages. Orchestration and tools have Python build pipelines that aggregate source JSON into generated `.js` data files. Light-default theme with dark toggle. Mobile-responsive. Watermelon-gum pastel palette (pink + mint) on parchment-cream / warm-plum-dusk backgrounds. Fredoka + JetBrains Mono webfonts via `@import` in `shared/forge.css`.

## Local dev

The flat pages work as static files:

```bash
python -m http.server 8000
# open http://localhost:8000
```

Orchestration and tools need their data built first:

```bash
cd orchestration && python build.py    # generates data.js from structures/*.json
cd tools && python build.py             # generates data.js, taxonomy.js from data/*.json
```

Tools can also scrape fresh data from awesome lists, Homebrew, and CNCF:

```bash
cd tools && python -m scrape
```

## Tests

```bash
cd orchestration && python -m pytest tests/ -v   # 92 tests
cd tools && python -m pytest tests/ -v           # 67 tests
```

## Deployment

Hosted on Google Cloud Compute. Static files served by nginx; orchestration has an optional FastAPI backend for social features (votes, comments).

Deploy requests go through `~/projects/ops/DEPLOY_QUEUE.md` — the ops steward runs tests, pushes, and executes `deploy.sh` in each section that needs it.

## Structure

```
index.html              LLMs-branded home (anatomy flowchart + rhizome cluster SVG)
shared/forge.css        Palette, typography, shared components
shared/forge.js         Theme toggle (light-default)
models/index.html       Model catalog (flat page)
context/index.html      Context explainer (flat page)
orchestration/
  index.html            Pattern catalog SPA
  build.py              Aggregates structures/*.json → data.js
  deploy.sh             Deploys to GCP (--api for FastAPI service)
  api/                  FastAPI + SQLite social features (optional)
  structures/           Source pattern data (17 JSON files, 271 patterns)
tools/
  index.html            Software directory SPA
  build.py              Aggregates data/*.json → data.js, taxonomy.js
  deploy.sh             Deploys to GCP
  scrape/               Scraping pipeline (awesome lists, Homebrew, CNCF)
  data/                 Source catalog data (~27 JSON files)
  tools/                Standalone executable tools built from unfilled slots
forge/index.html        Multi-agent management guide (flat page)
agents/                 Top-level agent role files (orchestrator, builder, skeptic)
```
