# LLMs — Interactive Explainers

Part of forge.thisminute.org. Interactive educational content about LLM fundamentals and agentic architecture.

If told to go, start, or begin — you are the **steward**. See `agents/steward.md`.

## Pages

| Page | Path | What it explains |
|------|------|-----------------|
| Anatomy of an Agent | `/llms/` (`index.html`) | The five parts: orchestration, harness, LLM, context, tools |
| f(tokens) → token | `/llms/llm/` (`llm/index.html`) | Token prediction demo — statelessness, no memory |
| Harness | `/llms/harness/` | *Planned* — how runtimes connect model to tools |
| Context | `/llms/context/` | *Planned* — token windows, attention, what fits |

## Stack

Vanilla HTML/CSS/JS. Self-contained pages with inline styles. No frameworks, no build step. Dark theme with custom color palette per component (purple for orchestration, gold for LLM, teal for context, green for harness, pink for tools).

## Integration

The "Anatomy of an Agent" diagram links to sibling sections:
- Orchestration → `/rhizome/` (pattern catalog)
- Tools → `/toolshed/` (software directory)
- LLM → `/llms/llm/` (token explainer)
- Harness, Context → planned pages within this section

## Key Design Decisions

- Each page is a standalone interactive experience, not a text article
- The content teaches by showing, not telling — animations, step-through controls, visual state
- Pages should work without JavaScript for basic content, but interactivity requires JS
- Font stack: Instrument Serif (headings), JetBrains Mono (labels/code), system sans-serif (body)
