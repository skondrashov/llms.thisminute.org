# Checkpoint — 2026-03-15

## What was done

### Portal page
- New `index.html` at root — hub with three cards (Forge, Rhizome, Toolshed), each tinted with sub-site accent color
- Root is no longer a copy of `forge/index.html`
- Uses unified `thisminute_theme` localStorage key with system preference detection

### DRY pass across all sub-sites
- Unified localStorage key: `thisminute_theme` (was `forge_theme`, `rhizome_theme`, `mainmenu_theme`)
- Cross-site nav paths standardized to absolute (`/rhizome`, `/forge`, `/toolshed`) in rhizome and toolshed
- `<nav aria-label="Cross-site navigation">` landmark added to all three sub-sites
- `focus-visible` styles added for cross-site links on all three sub-sites
- Theme toggle button moved outside `<nav>` on all three sub-sites
- forge/index.html theme JS upgraded with system preference detection + try-catch

### Forge page improvements
- Role grid changed from 3-col auto-fill to 2x2 (fixes orphaned Keeper card)
- Pattern Library section now links 3 patterns to their rhizome entries (steward-bootstrap, protocol-forum-product-team, reflection-loop)
- Added intro text: "The forge scans against patterns from Rhizome"
- Linked pattern items have hover state

### Docs updated
- AGENTS.md reflects new portal architecture
- Builder agent doc updated with forge/index.html ownership
- Orchestrator agent doc was already accurate

## Skeptic review
- Pending — full cross-site review running

## Deploy
- Request submitted to ops queue (needs commit before push)

## What's next
- Address any skeptic findings
- Commit all changes
- "Reference Doc Splitting" and "Keeper Feedback Loop" patterns don't have rhizome entries yet — could be added to rhizome by its steward
- Consider adding a way to navigate back to portal from sub-sites
