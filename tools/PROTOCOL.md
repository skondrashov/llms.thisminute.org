# Agent Protocol

How agents operate on Toolshed. For project overview, see `AGENTS.md`.

## Startup

1. You will be told your name (e.g., "you are the builder")
2. **Understand your role**: Read your agent file (`agents/{your-name}.md`)
3. **Get current time**: Run `powershell -Command "Get-Date -Format 'yyyy-MM-dd HH:mm'"` and record the output. You MUST use this exact timestamp in all forum posts and reports. NEVER guess or fabricate a timestamp.
4. **Understand the project**: Read `AGENTS.md` for architecture and quality signals
5. **Check the forum**: Read `FORUM.md` — vote on at least 2 posts before posting new ones
6. **Check messages**: Read `messages/{your-name}.md` if it exists. Handle messages, then clear the file.
7. **Execute your tasks**: Follow your agent file
8. **Report findings**: Post to `FORUM.md`
9. **Update memory**: Add learnings to `memory/{your-name}.md`
10. **Shutdown reflection**: The orchestrator will ask you to evaluate each context layer: its spawn prompt, your role file, AGENTS.md, PROTOCOL.md, memory files, and forum/messages. Be specific and honest — flag wrong info, missing context, and noise. Your feedback directly improves what the next agent gets.
11. **Exit** (unless you're the orchestrator)

## Communication

| Channel | Use for |
|---------|---------|
| `FORUM.md` | Proposals, findings, active discussions. Keep it concise. |
| `messages/{agent}.md` | Direct requests to one agent. Be specific. |
| `memory/{agent}.md` | What you need to remember between sessions. |
| `reports/{agent}.md` | Routine updates, verification logs. |
| `messages/human.md` | Messages to the person running the project. |

### Forum Voting

Every post: `**Author:** name | **Timestamp:** YYYY-MM-DD HH:MM | **Votes:** +N/-M`

- **+1**: Agree / Verified / Should prioritize
- **-1**: Disagree / Wrong / Deprioritize
- High-vote items (+3 or more) = group consensus

## Spawn Requests

If you think another agent should run, post to the forum:

```
REQUEST SPAWN: [agent-name]
REASON: [why]
```

## Guidelines

1. **Read before acting** — understand AGENTS.md, your agent file, and FORUM.md first
2. **One thing at a time** — finish and report before starting the next task
3. **Be specific** — file paths, entry counts, concrete details
4. **Don't modify CLAUDE.md** — unless a human asks
