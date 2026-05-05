# Orchestrator Memory

Persistent learnings across sessions. Update after each session. Remove stale info.

## 2026-04-18: 11→5 agent consolidation

The project collapsed from 11 agent role files (3 top-level + 1 in orchestration/ + 7 in tools/) down to 5 top-level roles:

- `orchestrator` (you)
- `tools-curator` — catalog specialist for `tools/`
- `orchestration-curator` — pattern-catalog specialist for `orchestration/` (renamed from `steward`)
- `llms-curator` — content specialist for the four flat-page sections
- `skeptic` — project-wide reviewer (absorbed the tools-section skeptic)

Subsection `agents/`, `memory/`, `PROTOCOL.md`, `FORUM.md`, and `messages/` all went away. `tools/AGENTS.md` and `orchestration/AGENTS.md` are kept as technical references for the relevant curator. The builder role (top-level and tools) was removed — orchestrator does small code/CSS/layout fixes directly, tools-curator doesn't write pipeline code (flag to orchestrator when the pipeline needs changes).

Tone/voice-specific notes that used to live here have moved to `memory/llms-curator.md`.

## User preferences (stable)

- **Nuclear mode**: when the user says things like "go nuclear" or "I don't care about preserving old anything", they mean it. Don't hedge about backward compatibility or legacy URL preservation in those moments — they've already decided the cost is acceptable. Update the ops deploy queue with the migration steps afterward.
- **Deploys**: always route through `~/projects/ops/DEPLOY_QUEUE.md`. The user does not want this repo deploying directly.
- **Commits**: don't create commits unless explicitly asked. A fresh orchestrator session should not commit as part of ordinary work.

## Technical lessons (2026-04-20)

- **HIERARCHY_COLORS was dead, HIERARCHY_LABELS was not.** During the code quality pass I removed both as "dead constants" but HIERARCHY_LABELS is still referenced in two places: the field notes markdown builder and the search text matching. ESLint's `no-undef` rule caught this immediately. Lesson: always run lint after removing constants.
- **Theme toggle had two divergent code paths.** The `t` keyboard shortcut inside the detail drawer manually toggled `document.body.classList` and wrote to localStorage directly, while the `t` handler outside the drawer set `state.lightMode` and called a local `applyTheme()` that never actually toggled anything (it just read the current class). The outside-drawer handler was silently broken. Fix: both handlers now click the forge theme button (`#forge-theme-btn`), which delegates to llms.js's proper toggle (class + localStorage + sun/moon icons + MutationObserver fires mermaid reinit).
- **`updateFilterDescriptionss` typo** — the original filter bug was a function defined with a double 's' but called without it. Every filter click threw a silent ReferenceError. The ESLint `no-undef` rule was added specifically to prevent this class of bug from recurring.
- **Stale naming persists in body copy.** After domain/brand renames, grep for the old name in all `.html` files. This session found "Agent Forge" (2 instances in forge/index.html) and "Toolshed" (3 instances in tools/index.html) surviving a rename that touched titles, og:tags, and nav but missed prose and comments.
- **context/index.html had duplicate CSS** — `.site-label` and `.hero` rules copied verbatim from llms.css with only minor value differences (max-width 520 vs 560, margin 0.35rem vs 0.4rem). Replaced with a small override block. When adding shared CSS to llms.css, grep all pages for inline duplicates.
- **Playwright tests need filter-aware setup.** The orchestration page defaults to the "core" domain filter on first load, so a smoke test expecting >200 cards will fail unless it clears the filter first (press Escape).

## Philosophical direction: orchestration ↔ harness tie-ins

User framing (2026-04-11, just before restart): the forge (multi-agent system management template) is not special software. It is **context**. Role files, memory conventions, coordination protocols, pattern library — all of it is prompts and markdown that get fed into an LLM. The relevant consequence:

- If the forge pattern turns out to be durably useful, the major harness vendors (Anthropic, OpenAI, Microsoft, Google, etc.) will eventually ship their own version of the same idea bundled as default context in their harness. Claude Code has already shipped some of it (CLAUDE.md, memory files, agent roles, plan mode). Cursor has `.cursorrules`. Copilot has project instructions. Custom GPTs are another variant.
- That osmosis is a **good outcome**, not a threat. It means the pattern landed. The forge's job shifts to staying one step ahead of whatever harnesses ship natively.
- The orchestration catalog (`/orchestration/`) should explicitly track these tie-ins. When a harness ships a new native feature that is, underneath, a pattern the catalog already documents, add a realWorldExample pointing at the harness version. When the reverse happens — a new native harness mode introduces a pattern we haven't catalogued — add it as a new entry. See `orchestration/AGENTS.md` "In scope: orchestration that ships inside the harness" for the full framing.
- `harness-bundled-planner` and `harness-autopilot-mode` (added 2026-04-11) are the first two catalogue entries under this framing. More to come as harnesses keep shipping native orchestration features.

**When the orchestration-curator is spawned, remind them this tie-in is a focus area, not a footnote.** When they find a new harness mode (Cursor shipping a new agent profile, Copilot adding a new autopilot variant, etc.), the default action is "catalogue it or update an existing entry", not "leave it alone because it's a harness feature."

