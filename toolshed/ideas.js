/* Ideas from the former Crucible sub-site, merged into Toolshed.
 * These are tools/capabilities that need building, not existing software.
 * Appended to window.SOFTWARE so they appear alongside regular entries. */
(window.SOFTWARE = window.SOFTWARE || []).push(
  {
    "id": "lease-clause-comparator",
    "name": "Lease Clause Comparator",
    "description": "Compare two lease agreements by extracting clauses, normalizing them into a taxonomy, and producing a side-by-side diff with severity flags. Tenants and small landlords miss critical differences buried in 30+ pages of legalese.",
    "url": "",
    "category": "Accounting & Finance",
    "os": ["web"],
    "pricing": "free",
    "tags": ["idea", "legal", "documents", "comparison", "pdf"],
    "status": "submitted",
    "projectPath": "~/projects/singularity/lease-clause-comparator/",
    "language": "typescript",
    "validation": {
      "benchmarks": "TypeScript compiles cleanly. Client-side PDF parsing with PDF.js, Claude API for clause extraction and comparison. Vite-based static site.",
      "limitations": "Requires Claude API key for clause extraction. PDF parsing quality depends on PDF structure (scanned PDFs not supported)."
    },
    "complexity": "week",
    "capability": "Semantic document comparison with structured clause extraction",
    "approach": "Static site with client-side PDF parsing and API calls to Claude. Upload two PDFs, AI extracts and normalizes clauses, then diffs them.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "moderate",
      "alternatives": "partial",
      "alternatives_note": "LawGeex, Juro, and general contract review tools exist but none target lease-specific clause comparison for tenants/small landlords. The niche is underserved."
    }
  },
  {
    "id": "dependency-health-scorer",
    "name": "Open Source Dependency Health Scorer",
    "description": "Score every dependency in a project on maintainer health, security posture, and community activity. Takes a package manifest, resolves the full tree, pulls data from GitHub, registries, and CVE databases.",
    "url": "",
    "category": "Code Coverage & Quality",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "security", "dependencies", "open-source", "risk", "cli"],
    "status": "submitted",
    "projectPath": "~/projects/singularity/dependency-health-scorer/",
    "language": "typescript",
    "validation": {
      "benchmarks": "74 tests passing. Average health score 87 on own dependencies. Multi-signal risk synthesis from GitHub API, npm/PyPI registries, and CVE databases.",
      "limitations": "Requires GitHub API token for maintainer health data. CVE database queries require network access."
    },
    "complexity": "month",
    "capability": "Multi-signal risk synthesis from heterogeneous data sources",
    "approach": "CLI or web UI. Resolves dependency tree from package.json/requirements.txt/Cargo.toml, scores each dep, produces a risk-ranked dashboard.",
    "agentArchitecture": { "model": "checkpoint", "roles": ["orchestrator", "builder", "analyst", "skeptic"] },
    "triage": {
      "impact": "medium",
      "buildability": "moderate",
      "alternatives": "partial",
      "alternatives_note": "Snyk, Socket.dev, deps.dev, and npm audit cover vulnerability scanning. None synthesize maintainer health + community activity + security posture into a single score across ecosystems."
    }
  },
  {
    "id": "codebase-migration-planner",
    "name": "Codebase Migration Planner",
    "description": "Point it at a repo and a migration target (e.g. class components to hooks). AI scans all files, catalogs pattern instances, maps dependencies, and produces a sequenced migration plan with effort estimates per batch.",
    "url": "",
    "category": "Build Tools",
    "os": [],
    "pricing": "free",
    "tags": ["idea", "migration", "refactoring", "codebase", "planning", "automation"],
    "status": "idea",
    "complexity": "month",
    "capability": "Large-scale pattern recognition and dependency-aware transformation planning",
    "approach": "Scan repo, catalog old-pattern instances, map dependencies, sequence changes so nothing breaks mid-migration. Optional: generate the actual PRs.",
    "agentArchitecture": { "model": "protocol-forum", "roles": ["orchestrator", "builder", "strategist", "skeptic", "librarian"] },
    "triage": {
      "impact": "high",
      "buildability": "hard",
      "alternatives": "partial",
      "alternatives_note": "Codemods (jscodeshift, ast-grep) handle individual transforms. No tool does the full pipeline: scan, catalog instances, map dependencies, and produce a sequenced migration plan. Claude Code itself partially covers this for single-session work."
    }
  },
  {
    "id": "git-commit-archaeology",
    "name": "Git Commit Archaeology Tool",
    "description": "Select a code region, and AI traces its full history through commits, PRs, issues, and review comments to produce a narrative of why the code is the way it is. Turns hours of manual excavation into a 30-second query.",
    "url": "",
    "category": "Version Control",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "git", "history", "code-understanding", "cli", "editor-extension"],
    "status": "submitted",
    "projectPath": "~/projects/singularity/git-commit-archaeology/",
    "language": "typescript",
    "validation": {
      "benchmarks": "34 tests passing (narrator: 16, excavator: 10, CLI edge cases: 8). Handles file history tracing, line-range filtering, depth limiting, JSON and markdown output formats.",
      "limitations": "GitHub enrichment requires GITHUB_TOKEN. AI narrative synthesis requires ANTHROPIC_API_KEY. Core git-only mode works without external APIs."
    },
    "complexity": "week",
    "capability": "Historical narrative synthesis from fragmented version control data",
    "approach": "CLI or editor extension. Reads git log, finds associated PRs/issues via GitHub API, synthesizes a narrative.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "medium",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "git log/blame/bisect exist. GitHub has PR timeline views. No tool synthesizes a narrative across commits + PRs + issues + review comments for a selected code region. Straightforward to build as a CLI wrapping git + GitHub API + LLM."
    }
  },
  {
    "id": "research-paper-debate",
    "name": "Research Paper Debate Simulator",
    "description": "Upload a paper. AI spawns 3-5 agents with different expert perspectives who debate the claims, methodology, and conclusions. Watch the debate, ask follow-ups, get a structured critique with confidence levels.",
    "url": "",
    "category": "AI Assistants",
    "os": ["web"],
    "pricing": "free",
    "tags": ["idea", "papers", "peer-review", "debate", "multi-agent", "education"],
    "status": "submitted",
    "projectPath": "~/projects/singularity/research-paper-debate/",
    "language": "typescript",
    "validation": {
      "benchmarks": "35 tests passing (debate engine). Express server with Vite frontend. PDF parsing, multi-perspective expert debate with moderated turns, structured critique output with confidence levels.",
      "limitations": "Requires Claude API key for debate generation. PDF parsing quality varies with document structure. Debate quality depends on paper length and field specificity."
    },
    "complexity": "week",
    "capability": "Multi-perspective critical analysis with adversarial reasoning",
    "approach": "PDF upload, spawn expert agents, run moderated debate, compile structured critique.",
    "agentArchitecture": { "model": "checkpoint", "roles": ["orchestrator", "builder", "analyst", "skeptic"] },
    "triage": {
      "impact": "medium",
      "buildability": "moderate",
      "alternatives": "partial",
      "alternatives_note": "Elicit and Consensus do paper search and summarization. SciSpace explains papers. None run a multi-perspective adversarial debate on a paper's claims. The multi-agent architecture is the differentiator."
    }
  },
  {
    "id": "meeting-to-actions",
    "name": "Meeting Transcript to Action Items Pipeline",
    "description": "Audio file or live mic to Whisper transcription to Claude-extracted action items with owner, deadline, and confidence score. Pushes to task trackers (Linear, GitHub Issues, Todoist). The meeting already contained all the information — it just wasn't extracted.",
    "url": "",
    "category": "Productivity",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "meetings", "transcription", "automation", "task-management"],
    "status": "submitted",
    "projectPath": "~/projects/singularity/meeting-to-actions/",
    "language": "typescript",
    "validation": {
      "benchmarks": "74 tests passing. Audio ingestion, Whisper transcription, action item extraction with owner/deadline/confidence, task tracker integration (Linear, GitHub Issues, Todoist).",
      "limitations": "Requires Whisper for transcription and Claude API key for extraction. Real-time streaming mode is optional and not yet validated."
    },
    "complexity": "week",
    "capability": "Structured information extraction from unstructured conversation",
    "approach": "Audio upload or live mic, Whisper transcription, Claude extracts action items with owner/deadline/confidence, pushes to task tracker. Web app with simple upload flow.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "Otter.ai, Fireflies.ai, and Fellow do meeting transcription and action items but are SaaS-only, closed-source, and expensive. No local-first or open-source alternative extracts structured action items with confidence scores and pushes to multiple task trackers."
    }
  },
  {
    "id": "regex-explainer-tester",
    "name": "Regex Explainer & Tester",
    "description": "Parse a regex into its AST, explain each part in plain English, test against sample strings, and flag pitfalls like catastrophic backtracking, unescaped dots, or missing anchors. Regex is the #1 thing LLMs get wrong — this tool gets it right every time.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "regex", "validation", "developer-tools", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Regex AST parsing, explanation, validation, and pitfall detection via Python sre_parse",
    "approach": "Pure Python CLI. Uses sre_parse for AST, walks the tree to generate plain-English explanations, tests against user-provided strings, runs static analysis for common pitfalls.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "regex101.com is web-only and not agent-callable. Python's sre_parse gives the AST for free — this tool wraps it with explanation and validation. No CLI equivalent exists."
    }
  },
  {
    "id": "semver-range-resolver",
    "name": "Semver Range Resolver",
    "description": "Parse version ranges across ecosystems (npm ^1.2.3, Cargo ~1.2, pip >=1.0,<2.0, Maven [1.0,2.0)), test version membership, find range intersections, and explain what a range actually means. Agents generating package manifests need this for every dependency line.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "semver", "versioning", "package-management", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Multi-ecosystem version range parsing, membership testing, and intersection calculation",
    "approach": "Pure Python CLI. Parses range syntax for npm, Cargo, pip, and Maven. Tests whether a version satisfies a range, computes intersections of multiple ranges, explains semantics in plain English.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "semver (npm, JS-only) and packaging (pip-only) exist per-ecosystem. No multi-ecosystem CLI tool parses, explains, and intersects version ranges across npm, Cargo, pip, and Maven."
    }
  },
  {
    "id": "chmod-calculator",
    "name": "Chmod Calculator",
    "description": "Bidirectional conversion between octal (755), symbolic (rwxr-xr-x), and plain English. Supports setuid/setgid/sticky bits, umask calculation, and warns about dangerous permissions like 777 or world-writable files. Every deployment script and Dockerfile needs this.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "permissions", "unix", "security", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Bidirectional permission format conversion with security analysis",
    "approach": "Pure Python CLI. Converts between octal, symbolic, and English. Handles special bits (setuid/setgid/sticky). Computes effective permissions from umask. Flags dangerous patterns.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "none",
      "alternatives_note": "Web calculators exist but nothing is callable from CLI or by agents. True zero-alternative gap for a precision tool."
    }
  },
  {
    "id": "datetime-format-translator",
    "name": "Date/Time Format Translator",
    "description": "Translate format strings between syntaxes: Python strftime %Y-%m-%d, Java yyyy-MM-dd, Go 2006-01-02, moment.js YYYY-MM-DD, .NET yyyy-MM-dd. Also infer format from an example date string. LLMs confuse %m/%M, hallucinate Go tokens, and mix up ecosystem conventions.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "datetime", "formatting", "cross-language", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Cross-language date format translation and inference from example strings",
    "approach": "Pure Python CLI. Maps tokens between Python strftime, Java SimpleDateFormat, Go reference time, moment.js, and .NET format strings. Infers format by parsing example date strings against known patterns.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "moderate",
      "alternatives": "none",
      "alternatives_note": "Cheat sheet websites exist but no tool translates between syntaxes or infers format from example date strings. Go's reference-time system is especially error-prone for LLMs."
    }
  },
  {
    "id": "encoding-detective",
    "name": "Encoding Detective",
    "description": "Detect text encoding via heuristics and BOM, diagnose double-encoding chains (UTF-8 read as Latin-1 then saved as UTF-8 again), show byte-level diagnosis, and convert between encodings. Encoding bugs are the most frustrating 'works on my machine' class.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "encoding", "unicode", "text-processing", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Encoding detection, double-encoding diagnosis, and byte-level analysis",
    "approach": "Pure Python CLI. Detects encoding via BOM and heuristics, traces double-encoding chains by attempting decode/re-encode cycles, displays byte-level hex dumps with annotations, converts between encodings.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "chardet detects encoding but doesn't diagnose double-encoding. iconv converts but is a black box. No tool traces the encoding error chain or shows byte-level diagnosis."
    }
  },
  {
    "id": "env-validator",
    "name": ".env Validator",
    "description": "Compare .env.example against .env: missing vars, extra vars, placeholder values still present (your-api-key-here, changeme, xxx), type mismatches (port as string, boolean as yes/true inconsistency). Misconfigured env vars cause production outages and no tool validates against a template.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "env", "configuration", "validation", "devops", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Environment file validation against template with type and placeholder detection",
    "approach": "Pure Python CLI. Parses .env and .env.example, diffs keys, detects placeholder patterns via regex, infers expected types from example values, reports mismatches and missing vars.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "none",
      "alternatives_note": "dotenv libraries load env files but don't validate against a template. direnv manages env but doesn't validate. True gap — no tool does template-based .env validation."
    }
  },
  {
    "id": "timezone-converter",
    "name": "Timezone Converter & Overlap Calculator",
    "description": "Convert times between named zones, calculate meeting overlaps (when can SF, London, and Tokyo all meet?), handle DST transitions correctly, and explain ambiguous times during fall-back. Timezone math is the #2 thing LLMs get wrong after regex.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "timezone", "datetime", "scheduling", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Timezone conversion, multi-zone overlap calculation, and DST-aware time analysis",
    "approach": "Pure Python CLI. Uses Python 3.9+ zoneinfo (stdlib). Converts between named zones, finds overlapping business hours across multiple zones, flags DST transitions and ambiguous/non-existent times.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "moderate",
      "alternatives": "partial",
      "alternatives_note": "Python zoneinfo provides raw data. Web tools like worldtimebuddy.com exist. No CLI wraps timezone data with conversions, multi-zone overlap calculation, and DST transition explanations."
    }
  },
  {
    "id": "unicode-inspector",
    "name": "Unicode Inspector",
    "description": "Show every character's codepoint, name, category, script, and width. Detect invisible characters (zero-width spaces, soft hyphens, RTL marks), homoglyphs (Cyrillic a vs Latin a), and confusable strings. Normalize between NFC/NFD/NFKC/NFKD. Security-critical for homoglyph attacks and invisible character bugs.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "unicode", "text", "security", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Unicode character analysis, invisible character detection, and confusable string identification",
    "approach": "Pure Python CLI. Uses unicodedata for character metadata. Builds confusable detection from Unicode TR39 confusables.txt. Scans for invisible characters by category. Normalizes between NFC/NFD/NFKC/NFKD.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "medium",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "Python unicodedata provides raw character data. No CLI does confusable detection, invisible character scanning, or normalization comparison in one tool."
    }
  },
  {
    "id": "mime-type-oracle",
    "name": "MIME Type Oracle",
    "description": "Look up MIME types by extension, magic bytes, or name. Validate Content-Type headers. Map bidirectionally between MIME types and extensions using the full IANA registry (~2000 types). Agents hallucinate MIME types — wrong types break browser rendering and downloads.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "mime", "http", "web", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "MIME type lookup by extension, magic bytes, or name with full IANA registry coverage",
    "approach": "Pure Python CLI. Embeds the full IANA MIME type registry. Maps extensions to types and vice versa. Reads file magic bytes for detection. Validates Content-Type header syntax.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "medium",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "Python's mimetypes module is incomplete and system-dependent. file command does magic byte detection but not IANA registry lookup. No CLI combines the full registry with magic byte detection."
    }
  },
  {
    "id": "sql-type-mapper",
    "name": "SQL Type Mapper",
    "description": "Map column types across PostgreSQL, MySQL, SQLite, and SQL Server. Show equivalences (PostgreSQL SERIAL = MySQL AUTO_INCREMENT), size differences (VARCHAR(n) max varies), and migration warnings (SQLite has no native DATE). Every database migration needs this lookup.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "sql", "database", "migration", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Cross-database SQL type mapping with equivalences, size limits, and migration warnings",
    "approach": "Pure Python CLI. Embeds a type compatibility matrix across 4 databases. Maps types bidirectionally, flags lossy conversions, shows auto-increment and sequence equivalences, warns about NULL/default behavior differences.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "none",
      "alternatives_note": "Database docs cover their own types. No tool maps between databases or flags migration pitfalls. Agents generating migration scripts need this for every column."
    }
  },
  {
    "id": "escape-converter",
    "name": "Escape Sequence Converter",
    "description": "Convert between HTML entities (&amp;), URL encoding (%26), JSON escaping (\\u0026), Unicode escapes (\\x26), regex escaping, and shell escaping. Decode nested/double-escaped strings. LLMs get escaping wrong in every context — especially when escaping rules nest (JSON inside HTML inside shell).",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "escaping", "encoding", "web", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Multi-format escape/unescape conversion with double-encoding detection",
    "approach": "Pure Python CLI. Implements escape/unescape for HTML (all named entities), URL (percent encoding), JSON, Unicode (\\u, \\x, \\U), regex, and shell. Detects and unravels double-escaped strings.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "Individual language stdlib functions exist (html.escape, urllib.parse.quote) but no tool converts between all formats or detects double-escaping chains."
    }
  },
  {
    "id": "shell-escape-quoter",
    "name": "Shell Escape & Quoting Tool",
    "description": "Generate correctly quoted/escaped strings for bash, zsh, fish, PowerShell, and cmd.exe. Handle the hard cases: nested quotes, dollar signs in double quotes, glob characters, newlines in arguments. Show exactly which characters need escaping and why. Shell quoting rules differ wildly between shells and LLMs mix them up.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "shell", "escaping", "bash", "powershell", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Cross-shell string escaping with quoting strategy selection and explanation",
    "approach": "Pure Python CLI. Implements quoting rules for 5 shells. Takes a raw string + target shell, produces correctly quoted output. Explains which characters triggered escaping and which quoting style was chosen.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "none",
      "alternatives_note": "shlex.quote handles POSIX only. No tool covers PowerShell/cmd.exe or explains the quoting strategy. Agents generating shell commands for CI/CD need cross-shell correctness."
    }
  },
  {
    "id": "csv-dialect-detector",
    "name": "CSV Dialect Detector",
    "description": "Detect CSV dialect: delimiter (comma, tab, pipe, semicolon), quoting character, escape character, line endings, encoding, and whether a header row exists. Show a preview with detected columns. CSV is never 'just CSV' — every data pipeline hits a file that breaks the parser.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "csv", "data", "parsing", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "CSV format detection with delimiter, encoding, and header inference",
    "approach": "Pure Python CLI. Uses csv.Sniffer as starting point, adds encoding detection, line ending analysis, header inference via type consistency heuristics, and column count validation. Shows a formatted preview.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "Python csv.Sniffer exists but is unreliable and library-only. csvkit has some detection. No CLI combines dialect detection + encoding detection + header inference + preview."
    }
  },
  {
    "id": "dns-record-reference",
    "name": "DNS Record Reference & Validator",
    "description": "Look up DNS record types (A, AAAA, CNAME, MX, TXT, SRV, CAA, NS, SOA, PTR) with RFC meaning, syntax, and common use cases. Validate record values: SPF syntax, DKIM selectors, DMARC policies, MX priorities, SRV weight/port format. LLMs generate syntactically invalid DNS records that silently fail.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "dns", "networking", "email", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "DNS record type reference with value validation for SPF, DKIM, and DMARC",
    "approach": "Pure Python CLI. Embeds reference data for ~20 record types with RFC links. Validates SPF mechanisms, DKIM key syntax, DMARC policy tags, SRV format, and CNAME restrictions.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "high",
      "buildability": "moderate",
      "alternatives": "partial",
      "alternatives_note": "dig/nslookup query live DNS but don't explain record types or validate syntax. MXToolbox validates some records via web. No CLI validates SPF/DKIM/DMARC syntax offline."
    }
  },
  {
    "id": "locale-code-lookup",
    "name": "Locale & Country Code Lookup",
    "description": "Look up ISO 3166 country codes (US, USA, 840 all map to United States), ISO 639 language codes (en, eng), BCP 47 locale tags (en-US, zh-Hans-CN), and currency codes (USD, EUR). Convert between alpha-2, alpha-3, and numeric formats. Validate locale strings. LLMs confuse country codes with language codes and invent locale tags that don't exist.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "i18n", "locale", "iso", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "ISO 3166/639 code lookup, BCP 47 locale parsing, and format conversion",
    "approach": "Pure Python CLI. Embeds ISO 3166 (249 countries), ISO 639 (180+ languages), ISO 4217 (170 currencies). Parses and validates BCP 47 locale tags. Converts between alpha-2, alpha-3, and numeric codes.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "medium",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "pycountry (Python) provides data but is library-only. babel handles locales but is heavy. No CLI does cross-standard lookup + BCP 47 validation + format conversion."
    }
  },
  {
    "id": "glob-pattern-tester",
    "name": "Glob Pattern Tester & Explainer",
    "description": "Test glob patterns against file paths, explain what each part matches, and translate between glob flavors (shell, gitignore, Python fnmatch, Docker .dockerignore, GitHub Actions). Handle negation, double-star, brace expansion, and character classes. Glob syntax differs subtly between tools — ** means different things in bash vs gitignore.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "glob", "patterns", "gitignore", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Multi-flavor glob pattern testing, explanation, and cross-flavor translation",
    "approach": "Pure Python CLI. Implements glob matching for 5 flavors. Tests patterns against user-provided paths. Explains each pattern component. Translates between flavors, flagging behavioral differences.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "medium",
      "buildability": "moderate",
      "alternatives": "partial",
      "alternatives_note": "globtester.com is web-only. Python fnmatch and pathlib.Path.glob exist but differ from gitignore/docker glob rules. No tool explains or translates between flavors."
    }
  },
  {
    "id": "markdown-table-formatter",
    "name": "Markdown Table Formatter",
    "description": "Align markdown pipe tables, convert between markdown tables and CSV/TSV/HTML, auto-detect column alignment from content (numbers right-align, text left-aligns), and sort rows by any column. Every README and doc page has tables that agents and humans format inconsistently.",
    "url": "",
    "category": "CLI Tools",
    "os": ["windows", "macos", "linux"],
    "pricing": "free",
    "tags": ["idea", "cli", "markdown", "formatting", "tables", "precision-tool"],
    "status": "idea",
    "complexity": "weekend",
    "capability": "Markdown table alignment, format conversion, and content-aware column formatting",
    "approach": "Pure Python CLI. Parses pipe tables, aligns columns with padding, auto-detects alignment from content types, converts to/from CSV/TSV/HTML. Handles Unicode wide characters for correct alignment.",
    "agentArchitecture": { "model": "steward", "roles": ["steward"] },
    "triage": {
      "impact": "medium",
      "buildability": "straightforward",
      "alternatives": "partial",
      "alternatives_note": "VS Code and editor extensions auto-format tables but are not CLI-callable. prettytable (Python) generates tables but doesn't parse/reformat existing markdown. No CLI round-trips markdown tables with alignment."
    }
  }
);
