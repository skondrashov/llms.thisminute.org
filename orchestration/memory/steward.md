# Steward Memory

Persistent learnings across sessions. Update after each section session. Remove stale info.

## Section renamed (2026-04-11)

This section was renamed from `rhizome/` to `orchestration/` at the orchestrator's direction ("rename rhizome to orchestration, I don't care about preserving old anything"). All `/rhizome/` URLs, `rhizome_*` localStorage keys, `/opt/rhizome` directories, `rhizome-api` systemd units, and API paths were updated. The deploy queue has a one-time VM migration block. Frontend label says "Orchestration" in the h1 but the underlying social UI still uses the "patterns" / "structures" internal vocabulary. SQLite DB file also renamed `rhizome.db` → `orchestration.db`.

## In scope: harness-built-in roles (2026-04-11)

Added two patterns on 2026-04-11 documenting a category the orchestrator flagged as meaningful: **harness-built-in roles are orchestration patterns, even though they look like harness features**. Specifically `harness-bundled-planner` (Claude Code's Shift-Tab planning mode with restricted read-only tools → executor swap) and `harness-autopilot-mode` (Copilot's autopilot, Cursor composer agent mode, ChatGPT agent mode — harness-managed loop with stopping conditions and a distinct system prompt). Both mapped to existing structural classes: planner to Assembly Pipeline, autopilot to Hub-and-Spoke. Key insight: orchestration doesn't require multiple LLM instances, it requires multiple context templates. Swapping templates on the same model at runtime = same coordination effect as spawning a second agent, at a fraction of the complexity. When new harnesses ship new built-in roles (copilot modes, new Claude Code phases, etc.), add them here. Scope note documented in `AGENTS.md`.

## Pattern count (as of 2026-04-11)

271 patterns total (was 261 before the 2026-04-11 pair). All 271 classified into structural classes, 0 uncategorized after `python build.py`.

## Session 2026-03-26e: Pattern expansion batch 4 — streaming, memory, multi-tenant, auth, and research patterns

### What was done
- Added 10 new patterns to `structures/agent_infrastructure.json` covering 5 categories:
  - **Streaming & Real-Time**: streaming-thought-display (pipeline/assembly-pipeline), real-time-collaboration-agent (mesh/peer-ensemble)
  - **Memory & Knowledge**: memory-consolidation-cycle (pipeline/cyclic-renewal), conversation-summarization-window (pipeline/assembly-pipeline), structured-output-enforcement (pipeline/assembly-pipeline)
  - **Multi-Tenant & Enterprise**: tenant-isolated-agent (federated/compartmented-cells), role-based-agent-permissions (chain-of-command/strict-hierarchy)
  - **Research & Frontier**: world-model-agent (orchestrated/hub-and-spoke), agent-compiler-target (pipeline/assembly-pipeline), adversarial-curriculum-learning (adversarial/adversarial-arena)
- Added structural class mappings for all 10 patterns in `structural-classes.json`
- Total pattern count: 261 (was 251)
- All 99 tests pass

### Pattern design decisions
- streaming-thought-display maps to assembly-pipeline (the reasoning-engine → stream-formatter → UI is a sequential pipeline)
- real-time-collaboration-agent maps to peer-ensemble (all participants including AI are peers in the CRDT layer)
- memory-consolidation-cycle maps to cyclic-renewal (the periodic scan → merge → reflect cycle is the defining structure)
- conversation-summarization-window maps to assembly-pipeline (context flows through manager → summarizer → primary agent)
- tenant-isolated-agent maps to compartmented-cells (strict data isolation between tenants is the defining feature)
- role-based-agent-permissions maps to strict-hierarchy (authority flows top-down from permission policy through enforcement to agents)
- world-model-agent is Novel & Experimental (research-stage, not production) — maps to hub-and-spoke (world model is the central hub)
- adversarial-curriculum-learning is Novel & Experimental (research-stage) — maps to adversarial-arena (the generator-student adversarial dynamic)
- agent-compiler-target covers DSPy, SGLang, and Salesforce Agentforce's declarative approach

### Observations
- The catalog now has strong coverage of production AI infrastructure patterns: memory management, streaming UX, multi-tenancy, access control
- Technology & Engineering is at 70 patterns, Novel & Experimental at 33
- The remaining gap areas: agent debugging/testing patterns, inter-agent negotiation protocols, long-horizon planning with backtracking
- Memory patterns are now well-represented: file-based-agent-memory, memory-consolidation-cycle, conversation-summarization-window, self-learning-memory-loop

## Session 2026-03-26d: Pattern expansion batch 2 — evaluation, observability, prompt engineering, collaboration, infrastructure

### What was done
- Added 12 new patterns to `structures/llm_agent_orchestration.json` covering evaluation/safety, prompt engineering, human-agent collaboration, and infrastructure:
  1. red-team-blue-team-loop (adversarial/adversarial-arena) — Iterative adversarial hardening: red team attacks, blue team defends (Anthropic, OpenAI Preparedness, Microsoft PyRIT, Haize Labs)
  2. guardrail-sandwich (pipeline/assembly-pipeline) — Input + output guardrails sandwiching a free-operating agent (NeMo Guardrails, Guardrails AI, OpenAI Agents SDK)
  3. agent-observability-pipeline (pipeline/assembly-pipeline) — End-to-end structured telemetry: traces, cost, latency, token usage (LangSmith, Braintrust, Arize Phoenix, Helicone)
  4. few-shot-exemplar-bank (orchestrated/hub-and-spoke) — Dynamic retrieval of relevant few-shot examples from a curated bank (DSPy, Amazon Bedrock, KATE)
  5. prompt-compiler (pipeline/assembly-pipeline) — Meta-system compiles task declarations into optimized prompts (DSPy, TextGrad, OPRO)
  6. pair-programming-copilot (mesh/peer-ensemble) — Real-time reactive inline suggestions for developers (GitHub Copilot, Cursor, Supermaven)
  7. approval-gate-pipeline (pipeline+orchestrated/dual-key-safeguard) — Autonomous phases with human approval gates at boundaries (Replit Agent, Devin, Claude Code permissions)
  8. prompt-cache-optimization (pipeline/assembly-pipeline) — Deliberate prompt ordering for LLM provider prefix caching (Anthropic 90% reduction, Google context caching)
  9. semantic-router (orchestrated/triage-and-dispatch) — Embedding-based intent routing, orders of magnitude faster than LLM routing (Aurelio AI, AWS Bedrock)
  10. multi-model-cascade (pipeline+chain-of-command/triage-and-dispatch) — Cheap models handle easy requests, escalate uncertain ones to expensive models (Martian, OpenRouter)
  11. agentic-rag (orchestrated+pipeline/hub-and-spoke) — Agent-directed retrieval: decides when/what/where to retrieve and whether results suffice (LlamaIndex, Perplexity, CRAG)
  12. code-generation-with-execution-feedback (pipeline/cyclic-renewal) — Generate code, execute in sandbox, read output/errors, iterate (Code Interpreter, Claude analysis, Jupyter AI)
- Added structural class mappings for all 12 patterns in `structural-classes.json`
- Total pattern count: 251 (was 239)
- All 99 tests pass

### Pattern design decisions
- red-team-blue-team-loop is distinct from debate-protocol (debate seeks truth, red/blue seeks hardening)
- guardrail-sandwich is distinct from constitutional-governance (constitution is self-imposed principles, guardrails are external enforcement layers)
- agent-observability-pipeline is a passive observer pattern — it reads agent behavior without modifying it
- few-shot-exemplar-bank is distinct from progressive-context-disclosure (exemplar bank is about example selection, not context management)
- pair-programming-copilot captures the dominant AI-assisted coding mode — reactive, not autonomous
- approval-gate-pipeline maps to dual-key-safeguard (the gate is the dual-key mechanism requiring both agent work and human approval)
- code-generation-with-execution-feedback maps to cyclic-renewal (the generate-execute-debug cycle is the defining iterative structure)
- multi-model-cascade and semantic-router both map to triage-and-dispatch (they classify and route, just with different mechanisms)

### Observations
- The catalog now covers the main gap areas identified in prior sessions: human-in-the-loop (approval-gate, pair-programming-copilot), cost optimization (prompt-cache, multi-model-cascade, semantic-router), evaluation/safety (red-team, guardrails, observability)
- Prompt engineering as architecture (few-shot-exemplar-bank, prompt-compiler, prompt-cache-optimization) is a distinct pattern family worth recognizing
- Technology & Engineering is now at 62 patterns — by far the largest category, appropriate for the audience
- Remaining potential gap areas: multi-agent debugging/testing patterns, agent-to-agent negotiation, long-horizon planning patterns

## Session 2026-03-26c: Pattern expansion batch 3 — multi-modal, distributed, knowledge, emerging

### What was done
- Created new file `structures/agent_infrastructure.json` with 10 patterns covering 4 categories:
  - **Multi-Modal & Embodied**: vision-language-action-loop (pipeline/assembly-pipeline), multimodal-routing (orchestrated/triage-and-dispatch)
  - **Knowledge & Learning**: knowledge-graph-grounded-agent (orchestrated/hub-and-spoke), retrieval-augmented-fine-tuning (pipeline/assembly-pipeline)
  - **Distributed & Scale**: agent-mesh-network (mesh/peer-ensemble), event-driven-agent-bus (federated+swarm/swarm-stigmergy), rate-limit-aware-orchestrator (orchestrated/triage-and-dispatch)
  - **Emerging / Experimental**: agent-constitution (chain-of-command/strict-hierarchy), agent-marketplace (federated+mesh/market-ecosystem), simulated-environment-training (pipeline/cyclic-renewal)
- Added structural class mappings for all 10 patterns in `structural-classes.json`
- Total pattern count: 239 (was 229)
- All 99 tests pass

### Pattern design decisions
- All 10 patterns are Technology & Engineering — these are all production or near-production infrastructure patterns
- vision-language-action-loop maps to assembly-pipeline (the perceive→reason→act sequence is the defining structure)
- event-driven-agent-bus maps to swarm-stigmergy (agents coordinate indirectly through the environment/bus, not peer-to-peer)
- agent-constitution maps to strict-hierarchy (authority flows top-down from constitution to guardrails to operational agents)
- simulated-environment-training maps to cyclic-renewal (the train→evaluate→shadow→deploy→retrain cycle is the defining structure)
- agent-marketplace maps to market-ecosystem (competitive exchange mechanisms define the interaction pattern)

### Observations
- The catalog now covers the gap areas identified in session 2026-03-26b: multi-modal patterns and cost/budget optimization (rate-limit-aware-orchestrator)
- Human-in-the-loop patterns remain the main uncovered gap area
- The 16 source JSON files now span: seeds, gaps, rounds 3-5, exotic, corporate, military/gov, nature/networks, creative/social, professional ops, novel/experimental, forge-validated, LLM agent orchestration, and agent infrastructure
- Technology & Engineering is now the largest category at 50 patterns — appropriate given the catalog's audience

## Session 2026-03-26b: Major pattern expansion — creative agent architectures

### What was done
- Added 10 new patterns to `structures/llm_agent_orchestration.json` covering memory, tools, context engineering, evaluation, isolation, and self-improvement:
  1. evolutionary-self-modifier (Novel & Experimental) — Meta Hyperagents population-based code self-modification
  2. file-based-agent-memory (Tech & Eng) — Markdown file persistence with index (Claude Code, Cursor, Windsurf)
  3. tool-server-protocol (Tech & Eng) — Standardized tool discovery via protocol (Anthropic MCP, JSON-RPC)
  4. progressive-context-disclosure (Tech & Eng) — Lazy-load context, keep large data external (Azure SRE Agent)
  5. hook-driven-agent-lifecycle (Tech & Eng) — Shell commands on lifecycle events (Claude Code hooks)
  6. worktree-isolation (Tech & Eng) — Git worktree per subagent for parallel safe editing (Claude Code)
  7. llm-as-judge (Tech & Eng) — Separate LLM evaluates outputs with structured scoring (MT-Bench, ARK)
  8. agent-handoff-chain (Tech & Eng) — Direct context transfer between specialists (OpenAI Agents SDK)
  9. docker-sandboxed-execution (Tech & Eng) — Disposable containers for safe code execution (Code Interpreter, E2B)
  10. checkpoint-resume-across-sessions (Tech & Eng) — Structured checkpoint for multi-session continuity (forge.thisminute.org)
- Added structural class mappings for all 10 patterns in `structural-classes.json`
- Total pattern count: 229 (was 219)
- All 99 tests pass

### Pattern design decisions
- evolutionary-self-modifier is Novel & Experimental (research-only, Meta FAIR 2026) — all others are Technology & Engineering (production patterns)
- worktree-isolation and docker-sandboxed-execution both map to compartmented-cells (isolation is the defining structural feature)
- checkpoint-resume-across-sessions maps to cyclic-renewal (the session cycle is the defining structural feature)
- agent-handoff-chain maps to assembly-pipeline even though it has mesh flexibility, because the dominant flow is sequential transfers
- These 10 patterns fill genuine gaps: the catalog had no patterns for memory architecture, tool protocols, context engineering, lifecycle extensibility, filesystem isolation, or evaluation-as-architecture

### Observations
- The catalog is now well-covered for LLM agent infrastructure patterns — memory, tools, context, evaluation, isolation, checkpointing
- The remaining gap areas are: human-in-the-loop patterns (approval workflows, HITL checkpoints), multi-modal agent patterns, and cost/budget optimization patterns
- Several of these patterns (file-based-agent-memory, hook-driven-agent-lifecycle, checkpoint-resume-across-sessions) are meta-patterns used by the forge itself

## Session 2026-03-26: Production case study enrichment + 3 new patterns

### What was done
- Integrated 22 real-world production case studies from company blogs into existing patterns
- Enriched 4 existing patterns with new citations:
  - checkpoint-and-branch: added Temporal + OpenAI durable execution (agents survive crashes/rate limits)
  - tool-specialist-ring: added Microsoft Azure SRE anti-lesson (100 narrow tools failed, generalist agents won)
  - constitutional-governance: added McKinsey/QuantumBlack ARK (Critic Agent with definition-of-done veto authority)
  - mixture-of-agents: added Google DeepMind research (180 configs, 80.9% improvement on parallel tasks, 39-70% degradation on sequential)
- Verified 6 patterns already had the requested citations from prior enrichment:
  - supervisor-router (already had Anthropic, Amazon Bedrock, Salesforce, Klarna, Bertelsmann, Exa, Komodor)
  - plan-code-verify-loop (already had Stripe Minions 1000+ PRs/week, Replit Agent v3 200-min sessions)
  - context-window-relay (already had Microsoft Azure SRE, Google ADK)
  - conversational-group-chat (already had Microsoft Agent Framework / AutoGen+SK merger, 10K+ orgs)
  - sop-driven-software-team (already had McKinsey/QuantumBlack ARK rule-based backbone)
  - critic-generator-loop (already had McKinsey/QuantumBlack Critic Agent, Elastic 0.8 quality threshold)
- Created 3 new patterns in `structures/llm_agent_orchestration.json`:
  - deterministic-agentic-hybrid (Stripe blueprints -- interleaves deterministic git/lint/CI nodes with LLM nodes)
  - single-agent-context-maximizer (Cognition/Devin anti-pattern -- single agent beats multi-agent for coding)
  - self-learning-memory-loop (Komodor -- 3 knowledge layers: blueprint, KB, auto-captured experience)
- Added structural class mappings for all 3 new patterns
- Total pattern count: 218 (was 215)
- All 99 tests pass

### Case study triage decisions
- 10 of 22 case studies mapped to patterns that were already enriched in the prior session
- 4 existing patterns needed new citations added
- 3 case studies warranted genuinely new patterns (not fits for existing ones):
  - Stripe's deterministic-agentic hybrid is distinct from graph-state-machine (which is all-LLM routing) and from sop-driven (which simulates human roles)
  - Cognition's single-agent stance is a legitimate anti-pattern worth documenting
  - Komodor's three-layer memory is distinct from skill-library-curriculum (which is about executable skills, not operational memory)

### Observations
- The production case studies largely validate the existing taxonomy -- most real-world systems map to patterns we already have
- Anti-patterns (Microsoft narrow-tool failure, Cognition anti-multi-agent) are as valuable as positive patterns for practitioners
- Google DeepMind's 180-config study is the strongest empirical evidence about when MoA helps vs hurts

## Session 2026-03-18: LLM agent orchestration research and pattern integration

### What was done
- Researched 30+ real-world LLM agent frameworks, company architectures, and research projects
- Tagged 24 existing patterns with `llm-agent` tag for UI filtering
- Enriched 16 existing patterns with framework-specific realWorldExample references
- Created 9 new patterns in `structures/llm_agent_orchestration.json`:
  - graph-state-machine (LangGraph)
  - role-play-dialogue-pair (CAMEL-AI, ChatDev)
  - sop-driven-software-team (MetaGPT, ChatDev)
  - conversational-group-chat (AutoGen, Semantic Kernel)
  - supervisor-router (Amazon Bedrock, Semantic Kernel Magentic)
  - agent-as-tool (LlamaIndex, CrewAI Flows, Google ADK)
  - skill-library-curriculum (Voyager)
  - plan-code-verify-loop (Replit Agent, Devin, GitHub Copilot)
  - generative-agent-society (Stanford Generative Agents, AgentVerse)
- Added structural class mappings for all 9 new patterns
- Total pattern count: 215 (was 206)
- All 99 tests pass

### Framework-to-pattern mapping summary
Mapped to EXISTING patterns (tagged + enriched):
- LangGraph sequential chains → prompt-chain-assembly-line
- CrewAI role-based teams → multi-persona-council
- OpenAI Swarm handoffs → tool-specialist-ring
- DSPy optimization → reflection-loop
- Anthropic subagent spawning → context-window-relay
- Devin checkpoints → checkpoint-and-branch
- AlphaCode sampling → temperature-gradient-ensemble
- Together AI MoA → mixture-of-agents
- LangChain MapReduce → hierarchical-summarization-tree

Needed NEW patterns (genuinely distinct approaches):
- LangGraph's graph-based conditional routing → graph-state-machine
- CAMEL/ChatDev role-play pairs → role-play-dialogue-pair
- MetaGPT/ChatDev SOP waterfall → sop-driven-software-team
- AutoGen group chat → conversational-group-chat
- Bedrock supervisor routing → supervisor-router
- LlamaIndex agent-as-tool → agent-as-tool
- Voyager skill library → skill-library-curriculum
- Replit/Devin plan-verify loop → plan-code-verify-loop
- Stanford generative agents → generative-agent-society

### Observations
- Many frameworks implement the same underlying patterns (hub-and-spoke, pipeline) with different APIs
- The genuinely novel LLM-native patterns are: graph-state-machine, role-play dialogue pairs, skill libraries, and generative agent societies
- Supervisor-router is a refined version of hub-and-spoke with dual-mode (fast route vs full orchestration)
- The llm-agent tag now covers 33 patterns (24 existing + 9 new)

## Session 2026-03-14: Audit, bug fixes, evolution page

### What was done
- Fixed localStorage reads crashing in private browsing (init reads now wrapped in try/catch)
- Fixed keyboard shortcuts (j/k/s) firing when detail drawer is open — now only detail-specific keys (arrows, h/l, t, Escape) work in drawer
- Fixed shortcuts overlay closing on modifier keys (Shift, Ctrl, Alt) — now only closes on non-modifier keys
- Enriched 3 short realWorldExample values (meta-learning-zoo, military-chain-of-command, holacracy)
- Removed duplicate left/right arrow handler (consolidated into detail-open guard block)
- Full data quality audit: all 200 patterns complete, no missing fields, no placeholders, no duplicates
- Refined about/intro copy for tone (cut thesis-statement opener, removed hedging from origin line)
- Created evolution.html — timeline of organizational evolution across 3 projects (agi, thisminute, orchestration)
- Added "case" link in header actions to evolution page
- Deploy queue updated, includes note about agent-forge gh-pages link needed

### Known remaining lower-priority items
- No `popstate` listener — hash routing is write-only (browser back/forward doesn't work)
- Filter panel headers (collapse/expand sections) are not keyboard-accessible
- Field notes and shortcuts overlays have `aria-modal="true"` but no focus trap / initial focus management
- Agent `count` field inconsistently present (83% of agents lack it — fine since 1 is the default)
- `history.replaceState` means detail-to-detail nav is not back-button traversable
- Mermaid SVG innerHTML injection relies on Mermaid v10's built-in DOMPurify
- Mobile: search input scrolls away with no replacement in mobile filter bar
- Agent-forge gh-pages needs link to evolution page added (separate deploy)

### Observations
- All 200 patterns structurally complete — no missing required fields
- 92 tests cover build, schema, API, classifier, and frontend smoke tests
- Large uncommitted diff spans multiple sessions: rebranding, 2-col detail layout, field notes overlay, accessibility, DRY refactors, data consolidation, evolution page
