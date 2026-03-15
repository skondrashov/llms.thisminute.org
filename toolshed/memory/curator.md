# Curator Memory

## Last Session: Cycle 9 (2026-03-14)

### What I Did
- Added 16 new curated entries across 5 categories
- Fixed 5 miscategorized discovered entries by moving them to correct categories (not duplicating)
- Improved descriptions on 2 correctly-categorized discovered entries (zipkin, doxygen)

**New curated entries:**
- Monitoring & Metrics: PagerDuty, Grafana Tempo
- Auth & Identity: Authelia
- Documentation Tools: Docusaurus (docs context), Swagger UI (docs context), Mintlify (docs context), TypeDoc
- HR & People: Lattice, Greenhouse, Lever, Culture Amp, 15Five, Namely
- Mobile IDE & Tools: Genymotion, Appetize, Firebase App Distribution

**Recategorized discovered entries:**
- jaeger: ORMs -> Monitoring & Metrics
- bitrise: CI/CD Tools -> Mobile IDE & Tools
- codemagic: Operating Systems -> Mobile IDE & Tools
- proxyman: Networking -> Mobile IDE & Tools

**Categories skipped** (already well-populated): Static Site Generators (90), RSS Readers (81), Diagramming & Whiteboard (59), Encryption & Privacy Tools (191)

### Build State
- 15,601 entries, 123 categories
- 65/65 tests pass
- 0 duplicate ID warnings

### Critical Lesson: Duplicate Avoidance
- **NEVER create entries with suffixed IDs** (e.g., `ollama-llm` instead of `ollama`). This creates duplicate entries in the catalog.
- **When a discovered entry is miscategorized**: fix the category directly in `data/discovered_20260313.json` instead of adding a curated duplicate.
- **When a discovered entry has a poor description**: fix the description directly in `data/discovered_20260313.json`.
- **build.py processes files alphabetically**: `discovered_20260313.json` (d) comes before `mobile_desktop.json` (m), `monitoring.json` (m), `productivity.json` (p). So discovered entries take precedence when IDs collide.
- **Before adding any entry**: search ALL `data/*.json` files for the ID using grep.

### Data File Layout (Current)
| File | Categories |
|------|-----------|
| `data/development.json` | Code Editors, Terminal Emulators, Version Control, Database Tools, AI Assistants, Game Engines, Programming Languages, Web Frameworks |
| `data/creative_media.json` | Music Production, Video Editing, Image Editors, 3D & CAD, Media Players, Screen Recording / Streaming |
| `data/productivity.json` | Note Taking, Email, File Managers, Cloud Storage, Password Managers, PDF Tools, Office Suites, Calendar & Scheduling, Documentation Tools, Blogging & Newsletter Platforms |
| `data/internet_comms.json` | Browsers, Communication, VPN, Chess, Torrent Clients |
| `data/system_tools.json` | System Utilities, Virtualization, Backup & Sync, Package Managers |
| `data/cli_utilities.json` | CLI Frameworks, Terminal UI, File Search & Navigation, Async & Concurrency, Logging & Diagnostics, Error Handling, Date & Time, Document Conversion, Embedded & IoT, Utilities, Shell Environments |
| `data/ai_science.json` | AI/ML Libraries, Jupyter & Notebooks, Scientific Computing, Statistical Tools, NLP & Text AI, LLM Tools |
| `data/mobile_desktop.json` | Cross-Platform Frameworks, Mobile IDE & Tools, Desktop App Frameworks |
| `data/education.json` | Learning Platforms, Flashcards & Study |
| `data/devops_infra.json` | CI/CD Tools, Build Tools, Task Runners & Monorepos, Infrastructure as Code, Container Orchestration, Cloud SDKs & CLIs |
| `data/api_tools.json` | API Clients, API Documentation, GraphQL Tools |
| `data/web.json` | Frontend/Backend Frameworks, HTTP Libraries, Static Site Generators, Content Management Systems, etc. |
| `data/testing_quality.json` | Testing Frameworks, Static Analysis, Linters, etc. |
| `data/data_storage.json` | Databases, ORMs, Caching, etc. |
| `data/monitoring.json` | Monitoring & Metrics, Error & Exception Tracking, Log Management |
| `data/security.json` | Auth & Identity, Secrets Management, Security Scanning, Encryption & Privacy Tools |
| `data/networking.json` | RSS Readers, Social Media Clients, Video Conferencing, Networking |
| `data/system_desktop.json` | Window Managers, Launchers, Shell Environments, etc. |
| `data/design.json` | UI/UX Design Tools, Diagramming & Whiteboard, Fonts & Typography |
| `data/enterprise.json` | Project Management, CRM & Sales, Accounting & Finance, HR & People |

### Categories Still Needing Attention (as of 15,803 entries)
- Mobile IDE & Tools: 11 entries (regressed from 14 after Tier 3 threshold raise -- needs curated additions)
- Flashcards & Study: 14 entries
- Desktop App Frameworks: 15 entries
- HR & People: 16 entries
- Secrets Management: 18 entries
- Vector Databases: 18 entries (was 20, threshold affected)
- Task Runners & Monorepos: 20 entries
- Statistical Tools: 21 entries
- Error Handling: 21 entries

### Categories That Are Fully Populated Now
- Monitoring & Metrics: 194 (Prometheus, Grafana, Datadog, New Relic, Zabbix, Nagios, Uptime Kuma, Netdata, Checkmk, Jaeger, Zipkin, PagerDuty, Grafana Tempo)
- Auth & Identity: 144 (Auth0, Clerk, Keycloak, Firebase Auth, NextAuth.js, Okta, SuperTokens, Zitadel, WorkOS, Stytch, FusionAuth, Ory, Authelia)
- Documentation Tools: 148 (Sphinx, MkDocs, Storybook, ReadTheDocs, GitBook, VitePress, Confluence, BookStack, Outline, Docusaurus, Swagger UI, Mintlify, TypeDoc, Doxygen)
- Static Site Generators: 90 (Hugo, Gatsby, Jekyll, Eleventy, Astro, Zola, Pelican, Docusaurus, Bridgetown, Lume, Hexo)
- RSS Readers: 81
- Diagramming & Whiteboard: 59
- Encryption & Privacy Tools: 191
