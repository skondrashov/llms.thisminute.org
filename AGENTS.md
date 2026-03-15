# forge.thisminute.org

Portal site for the forge ecosystem. The agent-forge landing page serves as the root, with sub-sites at subpaths:

| Sub-site | Path | Source project | What it is |
|----------|------|---------------|------------|
| Portal | `/` | This repo (`index.html`) | Hub page linking to all three sub-sites |
| Forge | `/forge/` | This repo (`forge/index.html`) | Agent system manager landing page |
| Rhizome | `/rhizome/` | `rhizome/` | Agent orchestration pattern catalog (200 patterns) |
| Toolshed | `/toolshed/` | `toolshed/` | Software directory (15K+ entries) |

If told to go, start, or begin — you are the **orchestrator**. See `agents/orchestrator.md`.

## Scope

The orchestrator has authority over the entire repo — portal, forge, rhizome, and toolshed. Sub-sites keep their own agent definitions (`agents/`, `AGENTS.md`) but this orchestrator coordinates everything.

- `index.html` — portal hub page
- `forge/index.html` — agent-forge landing page
- `rhizome/` — pattern catalog (200 patterns, FastAPI + SQLite API)
- `toolshed/` — software directory (15K+ entries)
- Visual identity and consistency across the suite
- Deploys — submit requests to `~/projects/ops/DEPLOY_QUEUE.md`

## Stack

Vanilla HTML/CSS/JS. No frameworks, no build step. Dark/light mode. Mobile-responsive.

## Agents

| Agent | Scope |
|-------|-------|
| orchestrator | Coordinates all work across all sites |
| builder + skeptic | Portal/forge implementation and review |
| rhizome steward | All rhizome work (`rhizome/agents/steward.md`) |
| toolshed agents | 6 roles (`toolshed/agents/*.md`) — read before spawning |

## Key Files

```
index.html              # Portal hub page
forge/index.html        # Agent-forge landing page
agents/                 # Agent role files
agents/skills/          # Reusable checklists (security_review.md)
memory/                 # Persistent agent learnings
```
