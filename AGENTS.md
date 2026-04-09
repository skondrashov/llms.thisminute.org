# forge.thisminute.org

Agentic engineering education site. Learn how AI agents work — from token prediction to orchestration patterns — with interactive explainers, a software directory, and a pattern catalog. All connected.

| Section | Path | Source | What it is |
|---------|------|--------|------------|
| Portal | `/` | `index.html` | Hub page connecting all sections |
| LLMs | `/llms/` | `llms/` | Interactive explainers: agent anatomy, token mechanics |
| Forge | `/forge/` | `forge/index.html` | Multi-agent system management guide |
| Rhizome | `/rhizome/` | `rhizome/` | Agent orchestration pattern catalog (269 patterns) |
| Toolshed | `/toolshed/` | `toolshed/` | Software directory (16K+ entries, filled + unfilled slots) |

If told to go, start, or begin — you are the **orchestrator**. See `agents/orchestrator.md`.

## Scope

The orchestrator has authority over the entire repo — portal, llms, forge, rhizome, and toolshed. Sections keep their own agent definitions (`agents/`, `AGENTS.md`) but this orchestrator coordinates everything.

- `index.html` — portal hub page
- `llms/` — interactive LLM/agent fundamentals (steward-managed)
- `forge/index.html` — agent-forge landing page
- `rhizome/` — pattern catalog (269 patterns, FastAPI + SQLite API)
- `toolshed/` — software directory (16K+ entries)
- Visual identity and consistency across all sections
- Deploys — submit requests to `~/projects/ops/DEPLOY_QUEUE.md`

## Stack

Vanilla HTML/CSS/JS. No frameworks, no build step. Dark/light mode. Mobile-responsive.

## Agents

| Agent | Scope |
|-------|-------|
| orchestrator | Coordinates all work across all sections |
| builder + skeptic | Portal/forge implementation and review |
| llms steward | All llms section work (`llms/agents/steward.md`) |
| rhizome steward | All rhizome work (`rhizome/agents/steward.md`) |
| toolshed agents | 7 roles (`toolshed/agents/*.md`) — read before spawning |

## Key Files

```
index.html              # Portal hub page
llms/                   # LLM fundamentals section (steward-managed)
forge/index.html        # Agent-forge landing page
agents/                 # Portal agent role files
agents/skills/          # Reusable checklists (security_review.md)
memory/                 # Persistent agent learnings
```
