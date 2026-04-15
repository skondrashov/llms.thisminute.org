# Orchestration Rework — Three-Lens IA

Draft plan. First implementation pass landing alongside this doc. Expect the design to move once the user sees it.

## Why rework

Today `/orchestration/` is a single flat catalog of 271 patterns filtered by 20 categories (a mix of domains like "Medical & Emergency", topologies like "Network Topologies", and novelty tags like "Novel & Experimental"). "Technology & Engineering" alone holds 75 patterns and bundles industry-standard LLM agent patterns (supervisor-router, agent-as-tool, graph-state-machine) with org-inspired ones (NASA mission control, Toyota production) and experimental ones (agent-marketplace). The page is fun to browse but does not teach orchestration — a newcomer cannot tell which patterns are the ones they will actually meet in practice.

The rework adopts three educational lenses the user picks between on arrival, with the existing category / topology filters preserved as cross-cutting refinements inside each lens.

## Three lenses

### 1. Core (industry standard)

The ~15–20 patterns every agent developer will now meet in practice. This is the educational entry point. Each pattern shows a **Ships natively in** row enumerating the harnesses that implement it, so the pattern is never purely theoretical.

Tentative Core set (all exist in the catalog unless marked NEW):

| Pattern | Ships natively in |
|---------|-------------------|
| `harness-bundled-planner` (Plan mode) | Claude Code Plan mode, Cline Plan mode, OpenCode Plan, Aider Architect |
| `supervisor-router` | Claude Code Task tool, Roo Code Orchestrator, CrewAI Hierarchical, LangGraph Supervisor |
| `agent-as-tool` | Claude Code Task tool, OpenAI Agents SDK, LangChain agent executor |
| `peer-communicating-agent-team` (NEW) | Claude Code Agent Teams, Cursor 3 Agents Window |
| `plan-code-verify-loop` | Aider Architect, Cursor Composer, Devin |
| `multi-model-cascade` | Aider (reasoner + editor), Cursor best-of-N, Claude Code (Haiku explore → Sonnet plan) |
| `conversational-group-chat` | AutoGen GroupChat, Microsoft Agent Framework |
| `graph-state-machine` | LangGraph |
| `worktree-isolation` | Claude Code worktrees, Cursor 3 agents, Windsurf Arena |
| `hook-driven-agent-lifecycle` | Claude Code hooks (26 events), Goose MCP interceptors, Continue CI hooks |
| `tool-server-protocol` (MCP) | Claude Code, OpenAI Agents SDK, Goose, Continue, Kilo |
| `file-based-agent-memory` | CLAUDE.md, AGENTS.md, .cursorrules |
| `checkpoint-resume-across-sessions` | Claude Code /resume, LangGraph checkpoints, Cursor cloud agents |
| `guardrail-sandwich` | OpenAI moderation, Anthropic Constitutional, Cursor allow/block lists |
| `approval-gate-pipeline` | Claude Code PermissionRequest, Cline plan approval, Continue team allowlists |
| `context-window-relay` / `memory-distillation-pipeline` | Claude Code /compact, summarization across long sessions |
| `spec-gate-workflow` (NEW) | Devin, Kiro, Factory |
| `agent-handoff-chain` | OpenAI Swarm, CrewAI Sequential |
| `best-of-n-worktree-racing` (NEW) | Cursor 3 |

The exact set will tighten during implementation.

### 2. In the wild (real-world organizations)

Patterns drawn from how actual human organizations coordinate — aerospace, manufacturing, finance, emergency services, military, corporate. The "serious case study" layer for applying orchestration principles at scale. Target ~80 patterns. Pulled from existing categories:

- Corporate & Business (18)
- Historical & Traditional (13)
- Government & Political (11)
- Medical & Emergency (8)
- Sports & Competition (7)
- Maritime & Aviation (7)
- Legal & Judicial (7)
- Military & Defense (6)
- Intelligence & Espionage (6)
- Media & Communications (5)
- Plus the org-inspired half of Technology & Engineering (NASA mission control, Toyota, skunkworks, airline CRM, shuttle launch, etc.)

### 3. The garden (nature, philosophy, exotic)

The playful layer. Nature-inspired (ant colonies, stigmergy, mycelium), philosophical (consensus, anarchist collectives), religious, exotic / experimental. Still educational but lets the weirder patterns breathe without diluting the Core layer. Target ~80 patterns. Pulled from:

- Nature-Inspired (13)
- Creative & Arts (10)
- Religious & Spiritual (6)
- Novel & Experimental (34)
- Social & Community (7)
- Network Topologies (8) — these are abstract topologies, belong here more than with the case studies
- Education & Training (7)
- Academic & Research (10)
- Plus the exotic half of Technology & Engineering

## Cross-cutting filters (unchanged)

- **Hierarchy type** — 8 topologies (adversarial, chain-of-command, orchestrated, swarm, mesh, pipeline, consensus, federated).
- **Field** — domain tag, now de-emphasized in favor of lens + topology.
- **Search** — full text.

## New patterns (from harness research)

Landing in `structures/round7_harness_native.json`:

1. **`peer-communicating-agent-team`** — agents in a team share a task list and a mailbox; members message each other directly and self-claim work. Distinct from supervisor-router in that there is no single router. Maps to Claude Code Agent Teams (experimental, v2.1.32+), Cursor 3 Agents Window.

2. **`best-of-n-worktree-racing`** — the same prompt runs in N isolated worktrees on different models; a selector picks the best result. Competitive, not collaborative (differs from ensemble). Maps to Cursor 3.

3. **`fleet-orchestration`** — primary agent dispatches work to a managed fleet of homogeneous peer agents; fleet size dynamic. Differs from supervisor-router by homogeneity of workers. Maps to Devin-of-Devins.

4. **`spec-gate-workflow`** — an approved spec document is the contract between planner and executor; no code until the spec is approved. Maps to Devin, Kiro, Factory.

5. **`cloud-local-agent-mobility`** — an agent session migrates between cloud and local execution with state preserved. Maps to Cursor 3, Devin.

6. **`mcp-elicitation`** — an MCP server asks the user a question mid-task; harness intercepts, routes to user, injects the answer. Two-way negotiation, not just tool call. Maps to Claude Code Elicitation hook.

7. **Expand `hook-driven-agent-lifecycle`** — current entry predates the full 26-event Claude Code hook system. Update description and realWorldExample to cover blocking vs observe-only semantics and team-specific events (TeammateIdle, TaskCreated, TaskCompleted).

## Harness-native mappings

New file: `harness_native.json`. Shape:

```json
{
  "supervisor-router": [
    { "harness": "Claude Code", "feature": "Task tool", "url": "https://code.claude.com/docs/en/sub-agents" },
    { "harness": "Roo Code", "feature": "Orchestrator mode", "url": "https://docs.roocode.com/basic-usage/using-modes" },
    { "harness": "CrewAI", "feature": "Hierarchical process", "url": "https://docs.crewai.com/" },
    { "harness": "LangGraph", "feature": "Supervisor agent", "url": "https://langchain-ai.github.io/langgraph/" }
  ],
  ...
}
```

Loaded by the frontend alongside `data.js`. Cards in the Core lens render a "Ships natively in" strip below the summary.

## Frontend changes

Minimal, layered on the existing `index.html`:

1. New lens selector at the top (three pills: Core / In the Wild / The Garden). Default = Core.
2. Each pattern tagged with its lens via `lenses.json` (derived from category with a small set of hand overrides).
3. Core pattern cards render the harness-native strip.
4. Existing category filter collapses into a secondary dropdown inside each lens (still available, less prominent).
5. Hierarchy type filter stays as-is.

## Execution phases

1. This doc.
2. `structures/round7_harness_native.json` — 6 new patterns + one update (~7 entries).
3. `lenses.json` — mapping from pattern id → `core` / `wild` / `garden`.
4. `harness_native.json` — Core pattern → harness feature mappings.
5. `build.py` extended to load and emit `data.js` with `lens` and `harnesses` fields on each pattern.
6. `index.html` — lens selector, harness-native strip, category filter demotion.
7. Tests updated, build green.
8. Commit. Update checkpoint. Flag for user review.

## Open questions

- **Naming** — "Core / In the wild / The garden" is a first guess. User will likely refine.
- **Core set size** — 20 is a first target; could tighten to 12 if coverage feels too broad.
- **Steward role** — the rework is big enough that a dedicated curator pass on harness-native mappings would benefit from reading the latest docs fresh. Deferring that to a follow-up.
