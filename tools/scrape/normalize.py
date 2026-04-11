import re
from .config import VALID_OS, VALID_LANGUAGES, LANGUAGE_MAP


def make_id(name):
    s = name.lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'-+', '-', s)
    return s[:60]  # cap length


def map_language(lang):
    if not lang:
        return None
    mapped = LANGUAGE_MAP.get(lang.lower())
    return mapped if mapped in VALID_LANGUAGES else None


def truncate_desc(desc, limit=200):
    if not desc:
        return ""
    # Strip image/badge markdown: [![X][Y]](url), ![X][Y], ![X](url), [Icon]
    desc = re.sub(r'!\[[^\]]*\]\[[^\]]*\]', '', desc)       # ![X][Y]
    desc = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', desc)        # ![X](url)
    desc = re.sub(r'\[!\[[^\]]*\]\[[^\]]*\]\]\([^)]*\)', '', desc)  # [![X][Y]](url)
    desc = re.sub(r'\[(?:Freeware|OSS|Open-Source|Awesome)\s*Icon\]', '', desc, flags=re.IGNORECASE)
    # Clean markdown artifacts
    desc = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', desc)  # [text](url) -> text
    desc = re.sub(r'[`*_]', '', desc)  # strip markdown formatting
    desc = re.sub(r'\s+', ' ', desc).strip()
    desc = desc.rstrip('.')
    if len(desc) <= limit:
        return desc
    truncated = desc[:limit - 3]
    last_space = truncated.rfind(' ')
    if last_space > limit // 2:
        truncated = truncated[:last_space]
    return truncated + "..."


def infer_os(raw):
    """Infer OS from raw scraped entry metadata."""
    source_list = raw.get("source_list", "")
    topics = [t.lower() for t in raw.get("topics", [])]
    desc = (raw.get("description") or "").lower()

    if "awesome-mac" in source_list:
        return ["macos"]
    if "awesome-linux" in source_list:
        return ["linux"]
    if "awesome-selfhosted" in source_list:
        return ["web"]
    if "awesome-ios" in source_list or "awesome-swift" in source_list:
        return ["ios"]
    if "awesome-android" in source_list:
        return ["android"]

    os_set = set()
    os_keywords = {
        "macos": ["macos", "mac", "osx", "darwin", "apple"],
        "windows": ["windows", "win32", "win64"],
        "linux": ["linux", "unix"],
        "web": ["web", "webapp", "browser", "saas"],
        "ios": ["ios", "iphone", "ipad"],
        "android": ["android"],
    }
    for os_name, keywords in os_keywords.items():
        for kw in keywords:
            if kw in topics or kw in desc:
                os_set.add(os_name)

    # CLI tools and libraries default to cross-platform
    if not os_set:
        lang = (raw.get("language") or "").lower()
        if lang in ("python", "go", "rust", "java", "ruby", "javascript", "typescript", "c", "c++", "haskell", "scala"):
            return ["windows", "macos", "linux"]
        return ["windows", "macos", "linux"]

    return sorted(os_set, key=VALID_OS.index)


def infer_pricing(raw):
    """Most awesome-list and GitHub entries are open source = free."""
    return "free"


def normalize_entry(raw):
    """Convert raw scraped data into a schema-compliant entry."""
    name = (raw.get("name") or "").strip()
    if not name:
        return None

    entry = {
        "id": make_id(name),
        "name": name,
        "description": truncate_desc(raw.get("description", "")),
        "url": raw.get("homepage") or raw.get("url") or "",
        "category": raw.get("category"),  # may be None, filled by categorizer
        "os": infer_os(raw),
        "pricing": infer_pricing(raw),
        "tags": list(set(
            [t.lower().replace(" ", "-") for t in raw.get("topics", [])[:5]]
            + ["crawl-discovered"]
        )),
    }

    # Source (GitHub repo URL)
    source = raw.get("source_url") or raw.get("github_url")
    if source:
        entry["source"] = source
    elif "github.com/" in entry.get("url", ""):
        entry["source"] = entry["url"]

    # Language
    lang = map_language(raw.get("language"))
    if lang:
        entry["language"] = lang

    # Ensure URL exists
    if not entry["url"] and source:
        entry["url"] = source

    if not entry["url"] or not entry["id"]:
        return None

    return entry
