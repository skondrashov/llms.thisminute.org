# forge.thisminute.org

Portal site for the forge ecosystem. The agent-forge landing page serves as the root, with sub-sites at subpaths:

| Sub-site | Path | Source project | What it is |
|----------|------|---------------|------------|
| Portal | `/` | This repo (`index.html`) | Hub page linking to all three sub-sites |
| Forge | `/forge/` | This repo (`forge/index.html`) | Agent system manager landing page |
| Rhizome | `/rhizome/` | `rhizome/` | Agent orchestration pattern catalog (200 patterns) |
| Toolshed | `/toolshed/` | `toolshed/` | Software directory (15K+ entries) |

If told to go, start, or begin — you are the **orchestrator**. See `agents/orchestrator.md`.

## What This Project Owns

- `index.html` — portal hub page (links to all three sub-sites)
- `forge/index.html` — agent-forge landing page
- Visual identity and consistency across the suite
- Deploys — submit requests to `~/projects/ops/DEPLOY_QUEUE.md`

## What This Project Does NOT Own

- Rhizome content, build pipeline, or API — managed by rhizome's steward
- Toolshed entries, scraping, or categorization — managed by toolshed's agents

## Stack

Vanilla HTML/CSS/JS. No frameworks, no build step. Dark/light mode. Mobile-responsive.

## Agents

| Agent | Scope |
|-------|-------|
| orchestrator | Coordinates work, checkpoint-based state |
| builder | Portal page implementation |
| skeptic | Review, accessibility, cross-site consistency |

## Key Files

```
index.html          # Portal hub page
forge/index.html    # Agent-forge landing page
agents/             # Agent role files
memory/             # Persistent agent learnings
```
