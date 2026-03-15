import json, glob, os, re
from .config import DATA_DIR, BASELINE_PATH


def normalize_url(url):
    if not url:
        return ""
    url = url.lower().rstrip("/")
    url = re.sub(r'^https?://(www\.)?', '', url)
    return url


def normalize_name(name):
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())


def build_dedup_index():
    known_ids = set()
    known_urls = set()
    known_names = set()

    if os.path.exists(BASELINE_PATH):
        with open(BASELINE_PATH, encoding="utf-8") as f:
            baseline = json.load(f)
        known_ids.update(baseline.get("ids", []))

    for path in glob.glob(os.path.join(DATA_DIR, "*.json")):
        with open(path, encoding="utf-8") as f:
            for entry in json.load(f):
                eid = entry.get("id", "")
                if eid:
                    known_ids.add(eid)
                known_urls.add(normalize_url(entry.get("url", "")))
                known_urls.add(normalize_url(entry.get("source", "")))
                known_names.add(normalize_name(entry.get("name", "")))

    known_urls.discard("")
    known_names.discard("")
    return known_ids, known_urls, known_names


def is_duplicate(entry, known_ids, known_urls, known_names):
    if entry.get("id", "") in known_ids:
        return True
    if normalize_url(entry.get("url", "")) in known_urls:
        return True
    if normalize_url(entry.get("source", "")) in known_urls:
        return True
    if normalize_name(entry.get("name", "")) in known_names:
        return True
    return False
