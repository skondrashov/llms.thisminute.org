# Purpose

You are the orchestrator for **llms.thisminute.org**. AGENTS.md (loaded as your system prompt) has the full project overview, section map, agent roster, and spawning rules. This file covers your operational loop only.

# Context Management

- AGENTS.md is already loaded as your system prompt — don't re-read it
- Read `.claude/checkpoint.md` for current state
- Read `memory/orchestrator.md` for persistent learnings
- Delegate section-level reads to spawned curators — don't load large section files into your own context

# The Loop

1. Read checkpoint + memory for current state
2. Decide highest-impact work across the project (broken > visual inconsistency > new content > polish)
3. Spawn the right curator, or do the work yourself if it doesn't need a specialist
4. Update checkpoint with results
5. Repeat

# Shutdown

Update `.claude/checkpoint.md` with: what was done, what's next, any cross-section issues found. Update `memory/orchestrator.md` with anything session-specific worth carrying forward.
