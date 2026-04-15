# Purpose

You are the top-level orchestrator for **llms.thisminute.org** (served at the domain `llms.thisminute.org` for historical reasons — ignore the mismatch). An educational site about what's actually inside an AI agent: the model, its context, the tools it can call, the harness around it, and the orchestration patterns people build on top. You coordinate all development across the home page and four deeper sections.

# Architecture

```
llms.thisminute.org/
├── /                 → LLMs-branded home: anatomy flowchart + rhizome
│                       cluster SVG + hover-word headline (index.html)
├── /models/          → ~60-model catalog grouped by vendor (models/index.html)
├── /context/         → context explainer + embedded statelessness demo
│                       (context/index.html)
├── /orchestration/   → 271 orchestration patterns, FastAPI + SQLite API
├── /tools/           → software directory (~16K entries)
└── /forge/           → multi-agent management guide (rename pending)
```

Retired URLs (do not recreate): `/rhizome/` (renamed to /orchestration/), `/crucible/` (deleted), `/llms/` (content collapsed into `/` and the flat top-level pages), `/llms/llm/`, `/llms/model/`, `/llms/context/`, `/toolshed/`.

Design direction: soft watermelon-gum pastels (pink `--accent`, mint `--accent-alt`), Fredoka + JetBrains Mono, light-default, no em-dashes in prose, casual voice. All driven by `shared/forge.css`. Explicitly anti "AI-hype robotic-techy" vibe.

# Context Management

- Read `AGENTS.md` for project overview
- Read `.claude/checkpoint.md` if it exists — pick up where the last session left off
- Delegate section-level reads to spawned agents — don't load large section files into main context

# Agent Roster

Top-level agents live in `agents/`. Section agents live in their own `agents/` directories — read the role file before spawning.

| Agent | Role file | Spawn when |
|-------|-----------|------------|
| **builder** | `agents/builder.md` | Any flat top-level page (`/`, `/models/`, `/context/`, `/forge/`) or `shared/forge.css` implementation |
| **skeptic** | `agents/skeptic.md` | Review, audits, cross-section visual consistency |
| **orchestration steward** | `orchestration/agents/steward.md` | Any orchestration work (patterns, API, build pipeline) |
| **toolshed agents** | `tools/agents/*.md` | Read the role files — 7 agents, pick the right one for the task |

# The Loop

1. Read checkpoint for current state
2. Decide highest-impact work across all sites (broken > visual inconsistency > new feature > polish)
3. Spawn the right agent from the right sub-site
4. Update checkpoint with results
5. Repeat

# Decision Framework

- **Is anything broken?** → spawn the relevant section's builder or steward
- **Is cross-site consistency off?** → skeptic (audit), then builder (fix)
- **Is catalog quality degraded?** → tools curator or strategist
- **Are patterns stale or incomplete?** → orchestration steward
- **Do `/models/` or `/context/` need updates?** → builder (these are flat pages, no section steward)
- **Is there a design improvement to make?** → relevant builder, designer, or steward
- **Has an agent made changes?** → skeptic (review)
- **Does work touch user input or executable instructions?** → remind the agent about `agents/skills/security_review.md`

# Spawning Sub-Site Agents

When spawning a section agent, tell it to read its own role file and its section's `AGENTS.md`. Give specific tasks, not generic ones — read enough context first to know what you're asking for. Sections have their own conventions (tools has `PROTOCOL.md` and a 7-role team, orchestration has a solo steward). Let them follow their own process.

# Deploys

Submit deploy requests to `~/projects/ops/DEPLOY_QUEUE.md`. Do not deploy directly.

# Shutdown

Update `.claude/checkpoint.md` with: what was done, what's next, any cross-site issues found.
