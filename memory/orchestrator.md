# Orchestrator Memory

Persistent learnings across sessions. Update after each session. Remove stale info.

## User preferences (stable)

- **Voice direction**: soft, essayist, anti "AI-hype techy brutalist dashboard" vibe. The site is meant to be a softly spoken educational tool. The user has explicitly flagged em-dashes as an "LLM tell" and does not want them in user-facing prose. Parallel short punchy sentences, "Not X but Y" constructions, and bolded-then-defined paragraphs are also in the tell bucket. When tone comes up, do not over-rewrite copy — the user has said they'll handle tone themselves. Structural work (layout, accessibility, links, new content) is fair game without tone fussiness.
- **Aesthetic**: warm watermelon-gum pastels (pink `--accent`, mint `--accent-alt`), Fredoka typeface, light-mode default, rounded 14px radius, feathered warm shadows. Lives in `shared/forge.css`.
- **Nuclear mode**: when the user says things like "go nuclear" or "I don't care about preserving old anything", they mean it. Don't hedge about backward compatibility or legacy URL preservation in those moments — they've already decided the cost is acceptable. Update the ops deploy queue with the migration steps afterward.
- **Deploys**: always route through `~/projects/ops/DEPLOY_QUEUE.md`. The user does not want this repo deploying directly.
- **Commits**: don't create commits unless explicitly asked. A fresh orchestrator session should not commit as part of ordinary work.

## Philosophical direction: orchestration ↔ harness tie-ins

User framing (2026-04-11, just before restart): the forge (multi-agent system management template) is not special software. It is **context**. Role files, memory conventions, coordination protocols, pattern library — all of it is prompts and markdown that get fed into an LLM. The relevant consequence:

- If the forge pattern turns out to be durably useful, the major harness vendors (Anthropic, OpenAI, Microsoft, Google, etc.) will eventually ship their own version of the same idea bundled as default context in their harness. Claude Code has already shipped some of it (CLAUDE.md, memory files, agent roles, plan mode). Cursor has `.cursorrules`. Copilot has project instructions. Custom GPTs are another variant.
- That osmosis is a **good outcome**, not a threat. It means the pattern landed. The forge's job shifts to staying one step ahead of whatever harnesses ship natively.
- The orchestration catalog (`/orchestration/`) should explicitly track these tie-ins. When a harness ships a new native feature that is, underneath, a pattern the catalog already documents, add a realWorldExample pointing at the harness version. When the reverse happens — a new native harness mode introduces a pattern we haven't catalogued — add it as a new entry. See `orchestration/AGENTS.md` "In scope: orchestration that ships inside the harness" for the full framing.
- `harness-bundled-planner` and `harness-autopilot-mode` (added 2026-04-11) are the first two catalogue entries under this framing. More to come as harnesses keep shipping native orchestration features.

**When the orchestration steward is spawned, remind them this tie-in is a focus area, not a footnote.** When they find a new harness mode (Cursor shipping a new agent profile, Copilot adding a new autopilot variant, etc.), the default action is "catalogue it or update an existing entry", not "leave it alone because it's a harness feature."

## Architecture cheat sheet (as of 2026-04-11)

The home page (`index.html`) is **LLMs-branded** with a big Fredoka headline that cycles through word expansions on hover. It's not a portal grid anymore — it's an anatomy flowchart (Model ↔ Context ↔ Tools inside a dashed HARNESS frame) with an SVG rhizome cluster of 8 interconnected context-window rectangles off to the right linking to `/orchestration/`.

Sections (flat top-level):
- `/` — LLMs-branded home, anatomy flowchart + rhizome cluster SVG
- `/models/` — flat page, ~60-model catalog grouped by vendor, builder-managed
- `/context/` — flat page, context explainer with embedded statelessness demo, builder-managed
- `/orchestration/` — 271 patterns + FastAPI/SQLite social layer, section steward
- `/tools/` — ~16K software entries, 7-role agent team
- `/forge/` — multi-agent management guide, flat page, rename pending

Dead URLs (do not resurrect): `/rhizome/`, `/crucible/`, `/toolshed/`, `/llms/`, `/llms/llm/`, `/llms/harness/`, `/llms/model/`, `/llms/context/`.

## Deploy state

As of 2026-04-11 late afternoon there's a large unfinished deploy in `~/projects/ops/DEPLOY_QUEUE.md` under "forge — Full redesign". The live site may still be in the pre-redesign state until ops runs the one-time VM migration. If a fresh session notices the live site doesn't match the repo, that's expected — do not try to fix it from this end.

## Session 11 retrospective (2026-04-11)

- Major integration pass + nuclear rename in one sitting. Palette rewrite, Fredoka, home rebuild, /models/ and /context/ built from scratch, rhizome→orchestration rename, crucible and /llms/llm/ deleted, role docs updated, deploy queued.
- Two new orchestration catalog patterns added: `harness-bundled-planner` (Claude Code's planning mode) and `harness-autopilot-mode` (Copilot autopilot). User insight: harness-built-in roles are orchestration patterns dressed as features. Scope note added to `orchestration/AGENTS.md`.
- Still pending: toolshed curator should add a `Harnesses` category so the anatomy page `/tools/#harnesses` hand-off lands somewhere specific. Non-blocking but worth doing on next toolshed pass.
