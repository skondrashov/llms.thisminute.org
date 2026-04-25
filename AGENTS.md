# LLMs · thisminute.org

An educational site about what's actually inside an AI agent. The home page is a visual anatomy diagram (model ↔ context ↔ tools inside a harness frame, with a rhizomatic cluster of context windows off to the side for orchestration). Each part hands off to a deeper section. Served at `llms.thisminute.org` (domain name predates the rebrand, not worth changing now).

| Section | Path | Source | What it is |
|---------|------|--------|------------|
| Home | `/` | `index.html` | LLMs-branded anatomy flowchart. Visual hand-offs to the other sections. |
| Models | `/models/` | `models/` | Catalog of ~60 real models grouped by vendor. Card grid, vendor jump nav. |
| Context | `/context/` | `context/` | Context explainer with embedded statelessness demo, "what's filling our context?" breakdown, vision transformers section. |
| Orchestration | `/orchestration/` | `orchestration/` | Catalog of 271+ orchestration patterns with a FastAPI + SQLite social layer. |
| Tools | `/tools/` | `tools/` | Software directory (~16K entries, filled + unfilled slots). |
| Forge | `/forge/` | `forge/index.html` | Multi-agent system management guide. (Naming TBD — user wants to rename, options pending.) |

If told to go, start, or begin, you are the **orchestrator**. See `agents/orchestrator.md`.

## Scope

The orchestrator has authority over the entire repo — home, models, context, orchestration, tools, forge. All agent roles live at the top level. Sections no longer have their own agents; the orchestrator spawns the relevant top-level curator for catalog/pattern/content work and reads the section's `AGENTS.md` for orientation.

- `index.html` — LLMs-branded home with anatomy flowchart + rhizome cluster SVG + hover-word headline
- `models/index.html` — flat page, model catalog
- `context/index.html` — flat page, context explainer
- `orchestration/` — pattern catalog, 271+ patterns, FastAPI + SQLite API (curator: `orchestration-curator`)
- `tools/` — software directory (curator: `tools-curator`)
- `forge/index.html` — multi-agent management landing, flat page
- `shared/forge.css` + `shared/forge.js` — the watermelon-gum pastel theme and light-default theme toggle, loaded by every page
- Visual identity and consistency across all sections
- Deploys — submit requests to `~/projects/ops/DEPLOY_QUEUE.md`. Do not deploy directly.

## Stack

Vanilla HTML/CSS/JS. No frameworks, no build step on the flat pages. Fredoka + JetBrains Mono webfonts loaded via `@import` in `shared/forge.css`. Light-default, dark available via toggle. Mobile-responsive. Favicons are emoji (💬 home, 🧠 model, 🪟 context, 🎶 orchestration, 🛠️ tools, 🔥 forge).

The orchestration and tools sections each have their own Python build pipeline (`python build.py`) and pytest suite; see the respective `AGENTS.md` in each section for details.

## Design direction

Soft, warm, essayist. Parchment-cream light / warm-plum-dusk dark. Watermelon-gum pastel accents: pink (`--accent`) and mint (`--accent-alt`). Rounded chunky sans (Fredoka). No em-dashes in prose. Casual, human voice. Explicitly anti "AI-hype techy brutalist dashboard" vibe. See `shared/forge.css` for the full palette + type system.

## Agent system

Five roles, all at the top level in `agents/`. Sections do **not** have their own agents — those directories were removed in the 2026-04-18 consolidation.

| Agent | Role file | Scope |
|-------|-----------|-------|
| **orchestrator** | `agents/orchestrator.md` | The only coordinator. Spawns curators by domain; does ad-hoc code/CSS/layout work directly. |
| **tools-curator** | `agents/tools-curator.md` | Catalog-maintenance specialist for `tools/` (data quality, dedup, new entries, category gaps) |
| **orchestration-curator** | `agents/orchestration-curator.md` | Pattern-catalog specialist for `orchestration/` (new patterns, three-lens IA, structural classes, harness mappings) |
| **llms-curator** | `agents/llms-curator.md` | Content specialist for the four flat-page sections (`home/`, `models/`, `context/`, `forge/`); owns voice/tone |
| **skeptic** | `agents/skeptic.md` | Project-wide reviewer: catalog data quality, pattern taxonomy, flat-page content, accessibility, cross-section consistency |

Orchestrator's spawning rules:
- Catalog or entry work in `tools/` → `tools-curator`
- Pattern work in `orchestration/` → `orchestration-curator`
- Flat-page content or voice/tone → `llms-curator`
- Review → `skeptic`
- Everything else (small code fixes, CSS tweaks, cross-section navigation, shared chrome, doc maintenance) → orchestrator does it directly

Each curator reads its role file plus the relevant section's `AGENTS.md` for orientation. `memory/*.md` holds each role's persistent learnings.

### Spawning specialists

Spawn a specialist by running a fresh Claude with the role file as its system prompt. The role file IS the identity — no read-the-role step at runtime, no embedded role briefing in the user message. Just dispatch the task.

```bash
# Bash
claude --dangerously-skip-permissions --system-prompt "$(cat agents/tools-curator.md)" -p "scan data/ for new entries from awesome-rust"
```

```powershell
# PowerShell
claude --dangerously-skip-permissions --system-prompt (Get-Content -Raw .\agents\tools-curator.md) -p "scan data/ for new entries from awesome-rust"
```

Capture the output, surface results back to the user or feed the next decision. Each spawn is a fresh process — no persistent subagent state.

When the meta-orchestrator at `~/projects/` dispatches into this project, it spawns *you* (the orchestrator) the same way using this AGENTS.md. The pattern is fractal.

## Key Files

```
index.html              # LLMs-branded home (anatomy flowchart + rhizome cluster)
shared/forge.css        # Palette, typography, shared components, webfont @imports
shared/forge.js         # Theme toggle (light-default)
models/index.html       # Model catalog (flat page)
context/index.html      # Context explainer (flat page)
orchestration/          # Pattern catalog, 271+ patterns, FastAPI + SQLite API
tools/                  # Software directory (~16K entries)
forge/index.html        # Multi-agent management guide (flat page)
agents/                 # Role files (5 roles)
agents/skills/          # Reusable checklists (security_review.md)
memory/                 # Per-role persistent learnings (+ memory/archive/ for retired roles)
.claude/checkpoint.md   # Session history — read before starting work
```

## Deploy status as of 2026-04-11

A major redesign + rename landed in this repo and is queued at `~/projects/ops/DEPLOY_QUEUE.md` ("forge — Full redesign" entry). The deploy has **not** happened yet. Until ops runs the one-time VM migration (see `orchestration/deploy.sh` header comment), the live site still has the pre-redesign structure. If anyone is confused about why the live site looks different from the repo, this is why.
