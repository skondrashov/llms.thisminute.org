# LLMs · thisminute.org

An educational site about what's actually inside an AI agent. The home page is a visual anatomy diagram (model ↔ context ↔ tools inside a harness frame, with a rhizomatic cluster of context windows off to the side for orchestration). Each part hands off to a deeper section. Served at `llms.thisminute.org` (domain name predates the rebrand, not worth changing now).

| Section | Path | Source | What it is |
|---------|------|--------|------------|
| Home | `/` | `index.html` | LLMs-branded anatomy flowchart. Visual hand-offs to the other sections. |
| Models | `/models/` | `models/` | Catalog of ~60 real models grouped by vendor. Card grid, vendor jump nav. |
| Context | `/context/` | `context/` | Context explainer with embedded statelessness demo, "what's filling our context?" breakdown, vision transformers section. |
| Orchestration | `/orchestration/` | `orchestration/` | Catalog of 271 orchestration patterns with a FastAPI + SQLite social layer. |
| Tools | `/tools/` | `tools/` | Software directory (~16K entries, filled + unfilled slots). |
| Forge | `/forge/` | `forge/index.html` | Multi-agent system management guide. (Naming TBD — user wants to rename, options pending.) |

If told to go, start, or begin, you are the **orchestrator**. See `agents/orchestrator.md`.

## Scope

The orchestrator has authority over the entire repo — home, models, context, orchestration, tools, forge. Larger sections with their own internal structure (orchestration, tools) keep their own agent definitions; the flat top-level pages (home, models, context, forge) are handled by the top-level builder + skeptic.

- `index.html` — LLMs-branded home with anatomy flowchart + rhizome cluster SVG + hover-word headline
- `models/index.html` — flat page, model catalog, no sub-section agents
- `context/index.html` — flat page, context explainer, no sub-section agents
- `orchestration/` — pattern catalog, 271 patterns, FastAPI + SQLite API, section steward
- `tools/` — software directory, 7-role agent team
- `forge/index.html` — multi-agent management landing, flat page
- `shared/forge.css` + `shared/forge.js` — the watermelon-gum pastel theme and light-default theme toggle, loaded by every page
- Visual identity and consistency across all sections
- Deploys — submit requests to `~/projects/ops/DEPLOY_QUEUE.md`. Do not deploy directly.

## Stack

Vanilla HTML/CSS/JS. No frameworks, no build step. Fredoka + JetBrains Mono webfonts loaded via `@import` in `shared/forge.css`. Light-default, dark available via toggle. Mobile-responsive. Favicons are emoji (💬 home, 🧠 model, 🪟 context, 🎶 orchestration, 🛠️ toolshed, 🔥 forge).

## Design direction

Soft, warm, essayist. Parchment-cream light / warm-plum-dusk dark. Watermelon-gum pastel accents: pink (`--accent`) and mint (`--accent-alt`). Rounded chunky sans (Fredoka). No em-dashes in prose. Casual, human voice. Explicitly anti "AI-hype techy brutalist dashboard" vibe. See `shared/forge.css` for the full palette + type system.

## Agents

| Agent | Scope |
|-------|-------|
| orchestrator | Coordinates all work across all sections |
| builder + skeptic | Top-level flat pages (`/`, `/models/`, `/context/`, `/forge/`) and the shared theme |
| orchestration steward | All orchestration work (`orchestration/agents/steward.md`) |
| tools agents | 7 roles (`tools/agents/*.md`) — read before spawning |

## Key Files

```
index.html              # LLMs-branded home (anatomy flowchart + rhizome cluster)
shared/forge.css        # Palette, typography, shared components, webfont @imports
shared/forge.js         # Theme toggle (light-default)
models/index.html       # Model catalog (flat page, builder-managed)
context/index.html      # Context explainer (flat page, builder-managed)
orchestration/          # Pattern catalog, 271 patterns, FastAPI + SQLite API
tools/                  # Software directory
forge/index.html        # Multi-agent management guide (flat page)
agents/                 # Top-level agent role files
agents/skills/          # Reusable checklists (security_review.md)
.claude/checkpoint.md   # Session history — read before starting work
```

## Deploy status as of 2026-04-11

A major redesign + rename landed in this repo and is queued at `~/projects/ops/DEPLOY_QUEUE.md` ("forge — Full redesign" entry). The deploy has **not** happened yet. Until ops runs the one-time VM migration (see `orchestration/deploy.sh` header comment), the live site still has the pre-redesign structure. If anyone is confused about why the live site looks different from the repo, this is why.
