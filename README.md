# forge.thisminute.org

Portal and home for three interconnected sites about agent orchestration and software discovery.

| Site | Path | What it is |
|------|------|------------|
| **Portal** | `/` | Hub page linking to everything |
| **Agent Forge** | `/forge/` | Agent system manager landing page |
| **Rhizome** | `/rhizome/` | Catalog of 200 agent orchestration patterns |
| **Toolshed** | `/toolshed/` | Software directory (15K+ entries, 124 categories) |

Live at [forge.thisminute.org](https://forge.thisminute.org).

## Stack

Vanilla HTML/CSS/JS — no frameworks, no build step for the portal and forge pages. Rhizome and toolshed have Python build pipelines that aggregate source JSON into generated `.js` data files. All sites support dark/light mode and are mobile-responsive.

## Local dev

The portal and forge pages work as static files:

```bash
python -m http.server 8000
# open http://localhost:8000
```

Rhizome and toolshed need their data built first:

```bash
cd rhizome && python build.py    # generates data.js from structures/*.json
cd toolshed && python build.py   # generates data.js, taxonomy.js from data/*.json
```

Toolshed can also scrape fresh data from awesome lists, Homebrew, and CNCF:

```bash
cd toolshed && python -m scrape
```

## Tests

```bash
cd rhizome && python -m pytest tests/ -v   # 92 tests
cd toolshed && python -m pytest tests/ -v  # 67 tests
```

## Deployment

Hosted on Google Cloud Compute. Static files served by nginx; rhizome has an optional FastAPI backend for social features (votes, comments).

Deploy requests go through `~/projects/ops/DEPLOY_QUEUE.md` — the ops steward runs tests, pushes, and executes `deploy.sh` in each sub-site.

## Structure

```
index.html              Portal hub page
forge/index.html        Agent Forge landing page
rhizome/
  index.html            Pattern catalog frontend
  build.py              Aggregates structures/*.json → data.js
  deploy.sh             Deploys to GCP (--api for FastAPI service)
  api/                  FastAPI + SQLite social features (optional)
  structures/           Source pattern data (13 JSON files)
toolshed/
  index.html            Software directory frontend
  build.py              Aggregates data/*.json → data.js, taxonomy.js
  deploy.sh             Deploys to GCP
  scrape/               Scraping pipeline (awesome lists, Homebrew, CNCF)
  data/                 Source catalog data (22 JSON files)
  tools/                Standalone executable tools
agents/                 Agent role definitions (orchestrator, builder, skeptic)
```
