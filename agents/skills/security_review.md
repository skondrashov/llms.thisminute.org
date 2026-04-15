# Security Review

Checklist for reviewing user-facing features across llms.thisminute.org and its sub-sites (orchestration, toolshed). Use this when building or reviewing any feature that accepts user input, renders user content, or asks visitors to run code.

---

## User-Generated Content (comments, names, text)

### XSS Prevention

- All user-submitted text must be escaped before rendering. Never insert raw user input into `innerHTML`, template literals inside `innerHTML`, or attribute values.
- Verify the escape path end-to-end: API stores raw → API returns raw → client escapes before display. If the API returns pre-escaped HTML, double-escaping will produce visible `&amp;` artifacts.
- The `esc()` function (textContent/innerHTML round-trip) is safe for body text. Confirm it's applied to every user-controlled field: display names, comment bodies, and any future fields.
- Links in user content: if you ever render user-provided URLs, validate the scheme (`https://` only — block `javascript:`, `data:`, `vbscript:`).

### Comment System

- **Honeypot field**: present (`.hp-field`). Verify the API rejects submissions where the honeypot is filled.
- **Rate limiting**: the API should enforce per-IP rate limits on comment submission. Check that rapid submissions from the same IP are throttled.
- **Length limits**: both display name and body should have max lengths enforced server-side, not just client-side.
- **Moderation**: the flag button exists. Verify flagged comments are actually hidden or queued for review, not just marked.
- **Empty/whitespace submissions**: the API should reject comments that are empty or whitespace-only after trimming.

### Vote System

- Votes are deduplicated client-side via `localStorage` — this is trivially bypassable (incognito, clearing storage, curl).
- The API should enforce its own dedup (IP-based or fingerprint-based) and rate limiting. Client-side dedup is UX, not security.
- Verify the vote endpoint doesn't accept negative values or arbitrary score manipulation.
- If vote counts are displayed, ensure they can't be inflated by scripted POST requests at scale.

---

## Quick-Start / Executable Instructions

Any time the site tells a visitor to clone a repo and run a command:

- **Warn before execution.** If the flow involves running an AI agent (`claude`, `cursor`, etc.) that will auto-execute code from the repo, say so explicitly. The visitor should know that running `claude` in a directory means the agent reads and executes instructions from that repo.
- **Pin to a tagged release.** Never point visitors at `main` — use a versioned tag. Already done (`v0.4`), keep enforcing.
- **Link to source.** The clone command should be near a link to the repo so visitors can inspect before running.
- **Scope the warning.** Something like: "This will clone a repo and start an AI agent that reads instructions from it. Review the repo's CLAUDE.md before running if you want to see what it does."

---

## API Endpoints

For any API endpoint that accepts input (`/api/vote/`, `/api/comments/`, etc.):

- **Input validation**: reject malformed IDs, oversized payloads, unexpected content types.
- **Rate limiting**: per-IP, with sensible limits (e.g., 10 comments/hour, 50 votes/hour).
- **CORS**: verify `Access-Control-Allow-Origin` is scoped to the site's domain, not `*`.
- **Error responses**: don't leak stack traces, file paths, or internal state in error messages.

---

## Static Site Basics

- **No secrets in source.** API keys, tokens, admin URLs — none of these belong in HTML/JS shipped to the browser.
- **Subresource integrity**: if loading any external scripts or stylesheets, use `integrity` attributes.
- **HTTPS only**: all links and API calls should use `https://`. No mixed content.
- **Content Security Policy**: consider adding a CSP header via the server config to restrict inline scripts and external resource loading.

---

## How to Use This Skill

**Skeptic**: reference this during any review that touches user-facing features. Flag issues as **Security** severity (above Critical — security issues block deploy).

**Builder / Steward**: reference this when implementing comment, vote, or any input-accepting feature. Check each applicable section before marking work complete.

**Orchestrator**: when spawning agents for user-facing work, remind them this skill exists at `agents/skills/security_review.md`.
