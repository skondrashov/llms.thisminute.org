import json, glob, os, re
from collections import defaultdict, Counter
from .config import DATA_DIR, VALID_CATEGORIES

# Direct keyword -> category mapping for common terms
KEYWORD_TO_CATEGORY = {
    "analytics": "Monitoring & Metrics",
    "cms": "Content Management Systems",
    "ci-cd": "CI/CD Tools",
    "continuous-integration": "CI/CD Tools",
    "docker": "Container Orchestration",
    "kubernetes": "Container Orchestration",
    "k8s": "Container Orchestration",
    "container": "Container Orchestration",
    "git": "Version Control",
    "vim": "Code Editors",
    "neovim": "Code Editors",
    "source-code-editor": "Code Editors",
    "ide": "Code Editors",
    "text-editor": "Code Editors",
    "code-editor": "Code Editors",
    "database": "Databases",
    "sql": "Databases",
    "orm": "ORMs",
    "proxy": "Networking",
    "vpn": "VPN",
    "networking": "Networking",
    "tcp": "Networking",
    "udp": "Networking",
    "dns": "Networking",
    "protocol": "Networking",
    "network-library": "Networking",
    "email": "Email",
    "smtp": "Email",
    "chat": "Communication",
    "messaging": "Communication",
    "password-manager": "Password Managers",
    "password": "Password Managers",
    "backup": "Backup & Sync",
    "sync": "Backup & Sync",
    "auth": "Auth & Identity",
    "authentication": "Auth & Identity",
    "oauth": "Auth & Identity",
    "testing": "Testing Frameworks",
    "test-framework": "Testing Frameworks",
    "monitoring": "Monitoring & Metrics",
    "metrics": "Monitoring & Metrics",
    "observability": "Monitoring & Metrics",
    "logging": "Log Management",
    "search-engine": "Search Engines",
    "image-processing": "Image Processing",
    "image-editor": "Image Editors",
    "video-editor": "Video Editing",
    "video": "Video Editing",
    "audio": "Music Production",
    "music": "Music Production",
    "game-engine": "Game Engines",
    "gamedev": "Game Engines",
    "note-taking": "Note Taking",
    "notes": "Note Taking",
    "wiki": "Documentation Tools",
    "documentation": "Documentation Tools",
    "docs": "Documentation Tools",
    "blog": "Blogging & Newsletter Platforms",
    "blogging": "Blogging & Newsletter Platforms",
    "rss": "RSS Readers",
    "feed-reader": "RSS Readers",
    "file-manager": "File Managers",
    "terminal": "Terminal Emulators",
    "terminal-emulator": "Terminal Emulators",
    "shell": "Shell Environments",
    "screenshot": "Screenshot & Annotation",
    "clipboard": "Clipboard Managers",
    "web-browser": "Browsers",
    "torrent": "Torrent Clients",
    "bittorrent": "Torrent Clients",
    "pdf": "PDF Tools",
    "calendar": "Calendar & Scheduling",
    "scheduling": "Calendar & Scheduling",
    "project-management": "Project Management",
    "task-management": "Project Management",
    "crm": "CRM & Sales",
    "accounting": "Accounting & Finance",
    "finance": "Accounting & Finance",
    "invoicing": "Accounting & Finance",
    "learning": "Learning Platforms",
    "education": "Learning Platforms",
    "flashcard": "Flashcards & Study",
    "api-client": "API Clients",
    "graphql": "GraphQL Tools",
    "static-site-generator": "Static Site Generators",
    "ssg": "Static Site Generators",
    "http-client": "HTTP Libraries",
    "scraper": "Web Scraping & Parsing",
    "web-scraping": "Web Scraping & Parsing",
    "crawler": "Web Scraping & Parsing",
    "websocket": "Real-time Communication",
    "realtime": "Real-time Communication",
    "react-native": "Cross-Platform Frameworks",
    "flutter": "Cross-Platform Frameworks",
    "xamarin": "Cross-Platform Frameworks",
    "cross-platform": "Cross-Platform Frameworks",
    "machine-learning": "AI/ML Libraries",
    "deep-learning": "AI/ML Libraries",
    "artificial-intelligence": "AI/ML Libraries",
    "ml": "AI/ML Libraries",
    "data-science": "Data Analysis",
    "data-analysis": "Data Analysis",
    "data-visualization": "Data Analysis",
    "validation": "Data Validation & Serialization",
    "serialization": "Data Validation & Serialization",
    "encryption": "Encryption & Privacy Tools",
    "privacy": "Encryption & Privacy Tools",
    "security": "Security Scanning",
    "vulnerability": "Security Scanning",
    "scanner": "Security Scanning",
    "secrets": "Secrets Management",
    "linter": "Linters",
    "formatter": "Formatters",
    "static-analysis": "Static Analysis",
    "code-analyzer": "Static Analysis",
    "code-quality": "Code Coverage & Quality",
    "load-testing": "Load & Performance Testing",
    "benchmark": "Load & Performance Testing",
    "cli": "CLI Frameworks",
    "command-line": "CLI Frameworks",
    "infrastructure-as-code": "Infrastructure as Code",
    "iac": "Infrastructure as Code",
    "terraform": "Infrastructure as Code",
    "ansible": "Infrastructure as Code",
    "package-manager": "Package Managers",
    "cloud-sdk": "Cloud SDKs & CLIs",
    "aws": "Cloud SDKs & CLIs",
    "gcp": "Cloud SDKs & CLIs",
    "azure": "Cloud SDKs & CLIs",
    "build-tool": "Build Tools",
    "bundler": "Build Tools",
    "iot": "Embedded & IoT",
    "embedded": "Embedded & IoT",
    "arduino": "Embedded & IoT",
    "raspberry-pi": "Embedded & IoT",
    "chess": "Chess",
    "3d": "3D & CAD",
    "cad": "3D & CAD",
    "modeling": "3D & CAD",
    "vector-database": "Vector Databases",
    "vector-search": "Vector Databases",
    "window-manager": "Window Managers",
    "tiling": "Window Managers",
    "app-launcher": "Launcher & Productivity Utils",
    "spotlight-alternative": "Launcher & Productivity Utils",
    "operating-system": "Operating Systems",
    "linux-distribution": "Operating Systems",
    "distro": "Operating Systems",
    "photo": "Photo Management",
    "gallery": "Photo Management",
    "font": "Fonts & Typography",
    "typography": "Fonts & Typography",
    "diagram": "Diagramming & Whiteboard",
    "whiteboard": "Diagramming & Whiteboard",
    "ui": "UI/UX Design Tools",
    "ux": "UI/UX Design Tools",
    "office": "Office Suites",
    "spreadsheet": "Office Suites",
    "streaming": "Screen Recording / Streaming",
    "screen-recording": "Screen Recording / Streaming",
    "media-player": "Media Players",
    "music-player": "Media Players",
    "video-player": "Media Players",
    "social-media": "Social Media Clients",
    "video-conferencing": "Video Conferencing",
    "virtualization": "Virtualization",
    "virtual-machine": "Virtualization",
    "vm": "Virtualization",
    "system-monitor": "System Utilities",
    "system-information": "System Utilities",
    "cloud-storage": "Cloud Storage",
    "file-sharing": "Backup & Sync",
    "illustration": "Vector & Illustration",
    "svg": "Vector & Illustration",
    "error-handling": "Error Handling",
    "async": "Async & Concurrency",
    "concurrency": "Async & Concurrency",
    "datetime": "Date & Time",
    "date-time": "Date & Time",
    "date-util": "Date & Time",
    "notebook": "Jupyter & Notebooks",
    "jupyter": "Jupyter & Notebooks",
    "scientific": "Scientific Computing",
    "statistics": "Statistical Tools",
    "e2e-testing": "UI Automation & E2E Testing",
    "selenium": "UI Automation & E2E Testing",
    "playwright": "UI Automation & E2E Testing",
    "hr": "HR & People",
    "data-pipeline": "Data Pipelines",
    "etl": "Data Pipelines",
    "streaming-data": "Data Pipelines",
    "document-converter": "Document Conversion",
    "converter": "Document Conversion",
    "programming-language": "Programming Languages",
    "compiler": "Programming Languages",
    # --- New categories ---
    "frontend-framework": "Frontend Frameworks",
    "react": "Frontend Frameworks",
    "vue": "Frontend Frameworks",
    "angular": "Frontend Frameworks",
    "svelte": "Frontend Frameworks",
    "backend-framework": "Backend Frameworks",
    "django": "Backend Frameworks",
    "rails": "Backend Frameworks",
    "expressjs": "Backend Frameworks",
    "fastapi": "Backend Frameworks",
    "template-engine": "Template Engines",
    "templating": "Template Engines",
    "jinja": "Template Engines",
    "handlebars": "Template Engines",
    "tui": "Terminal UI",
    "terminal-ui": "Terminal UI",
    "text-processing": "Text Processing",
    "string-manipulation": "Text Processing",
    "caching": "Caching",
    "cache": "Caching",
    "redis": "Caching",
    "memcached": "Caching",
    "database-driver": "Database Drivers",
    "jdbc": "Database Drivers",
    "database-migration": "Database Migrations",
    "blockchain": "Blockchain & Web3",
    "ethereum": "Blockchain & Web3",
    "web3": "Blockchain & Web3",
    "smart-contract": "Blockchain & Web3",
    "solidity": "Blockchain & Web3",
    "nlp": "NLP & Text AI",
    "natural-language-processing": "NLP & Text AI",
    "spacy": "NLP & Text AI",
    "nltk": "NLP & Text AI",
    "llm": "LLM Tools",
    "langchain": "LLM Tools",
    "ollama": "LLM Tools",
    "openai": "LLM Tools",
    "compression": "Compression & Archiving",
    "archiving": "Compression & Archiving",
    "config": "Configuration",
    "configuration": "Configuration",
    "dotenv": "Configuration",
    "math": "Math & Numerics",
    "numerics": "Math & Numerics",
    "linear-algebra": "Math & Numerics",
    "web-framework": "Backend Frameworks",
    "ai-assistant": "AI Assistants",
    "chatbot": "AI Assistants",
    "ai-copilot": "AI Assistants",
    "llm-client": "AI Assistants",
    "llm-interface": "AI Assistants",
    "task-runner": "Task Runners & Monorepos",
    "monorepo": "Task Runners & Monorepos",
    "build-automation": "Task Runners & Monorepos",
}


STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "are",
    "was", "were", "been", "have", "has", "had", "not", "but", "all",
    "can", "will", "one", "more", "also", "than", "them", "its", "into",
    "most", "other", "some", "such", "use", "her", "him", "how", "man",
    "new", "now", "old", "see", "way", "who", "did", "get", "let", "say",
    "she", "too", "any", "each", "which", "their", "there", "what", "about",
    "would", "make", "like", "just", "over", "these", "after", "could",
    "should", "when", "where", "being", "those", "then", "them", "been",
    "many", "very", "only", "come", "made", "find", "here", "thing",
    "give", "using", "used", "based", "open", "source", "free", "tool",
    "tools", "app", "apps", "library", "simple", "fast", "easy",
    "written", "built", "support", "supports", "lightweight", "powerful",
    "modern", "cross", "platform", "project", "application", "provides",
    "client", "server", "file", "files", "data", "code", "system",
    "line", "command", "framework", "plugin", "interface", "manager",
    "multiple", "management", "development", "high", "performance",
}


def build_category_index():
    """Build keyword frequency index from curated entries only."""
    cat_keywords = defaultdict(Counter)
    for path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        # Skip scraped data — only use curated files to avoid feedback loops
        if "discovered" in os.path.basename(path):
            continue
        with open(path, encoding="utf-8") as f:
            entries = json.load(f)
        for entry in entries:
            cat = entry.get("category")
            if not cat:
                continue
            for tag in entry.get("tags", []):
                t = tag.lower()
                if t not in STOP_WORDS:
                    cat_keywords[cat][t] += 1
            desc = entry.get("description", "")
            for word in re.findall(r'[a-z]{3,}', desc.lower()):
                if word not in STOP_WORDS:
                    cat_keywords[cat][word] += 1
    return cat_keywords


def categorize(entry, category_index=None):
    """Determine the best category for an entry."""
    # If already has a valid category, keep it
    if entry.get("category") in VALID_CATEGORIES:
        return entry["category"]

    topics = [t.lower() for t in entry.get("tags", []) + entry.get("topics", [])]
    desc = (entry.get("description") or "").lower()
    name = (entry.get("name") or "").lower()

    # Tier 1: Direct keyword match from topics
    for topic in topics:
        if topic in KEYWORD_TO_CATEGORY:
            cat = KEYWORD_TO_CATEGORY[topic]
            if cat in VALID_CATEGORIES:
                return cat

    # Tier 2: Check description/name for keyword matches
    all_text = f"{name} {desc} {' '.join(topics)}"
    best_cat = None
    best_score = 0
    for keyword, cat in KEYWORD_TO_CATEGORY.items():
        if cat not in VALID_CATEGORIES:
            continue
        kw = keyword.replace("-", " ")
        # Use word-boundary matching for short keywords to avoid
        # false positives like "maintain" matching "ai"
        if len(kw) <= 3:
            if re.search(r'\b' + re.escape(kw) + r'\b', all_text):
                score = len(kw)
                if score > best_score:
                    best_score = score
                    best_cat = cat
        else:
            if kw in all_text:
                score = len(kw)  # longer matches = more specific
                if score > best_score:
                    best_score = score
                    best_cat = cat
    if best_cat:
        return best_cat

    # Categories that should NEVER be assigned via Tier 3 — too much overlap
    # with generic English words. Only section map or Tier 1/2 can assign these.
    TIER3_EXCLUDED = {
        "Desktop App Frameworks",  # "desktop" matches every macOS app
        "Mobile IDE & Tools",      # "ios"/"debugging" matches all iOS libs
        "Code Editors",            # "editor" matches WYSIWYG/music/molecule editors
        "Backend Frameworks",      # "web"/"server"/"http" attracts utility libs, routers, middleware
        "Frontend Frameworks",     # "component"/"ui"/"framework" attracts generic UI libs
    }

    # Tier 3: Score against category index (normalized by category size)
    if category_index:
        scores = {}
        tokens = set(topics + re.findall(r'[a-z]{3,}', all_text))
        for cat, keywords in category_index.items():
            if cat in TIER3_EXCLUDED:
                continue
            raw = sum(keywords.get(t, 0) for t in tokens)
            if raw > 0:
                # Normalize by total keyword count to prevent large categories
                # from dominating via sheer volume of common words
                total = sum(keywords.values())
                score = raw / (total ** 0.5) if total > 0 else raw
                # Penalize categories that attract junk via common words
                if cat in ("Utilities", "System Utilities"):
                    score *= 0.3
                elif cat in ("AI Assistants", "Cloud SDKs & CLIs",
                             "Task Runners & Monorepos"):
                    score *= 0.5
                elif cat in ("HR & People", "Chess", "Flashcards & Study",
                             "Error Handling", "Statistical Tools",
                             "Mobile IDE & Tools"):
                    score *= 0.3  # Small categories vulnerable to stop-word dominance
                elif cat in ("Desktop App Frameworks",):
                    score *= 0.3  # "desktop" keyword attracts generic apps
                elif cat in ("Data Analysis",):
                    score *= 0.3  # "data"/"visualization"/"chart" too broad
                elif cat in ("Date & Time", "Browsers"):
                    score *= 0.5  # Broad keywords attract junk
                scores[cat] = score
        if scores:
            best = max(scores, key=scores.get)
            # Require minimum confidence to avoid random assignment
            if scores[best] < 0.20:
                return None
            return best

    return None
