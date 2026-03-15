import os, json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
SCHEMA_PATH = os.path.join(ROOT_DIR, "schema.json")
TAXONOMY_PATH = os.path.join(ROOT_DIR, "taxonomy.json")
BASELINE_PATH = os.path.join(ROOT_DIR, "baseline-ids.json")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# Rate limits (seconds between requests)
SEARCH_RATE_DELAY = 2.5  # GitHub search: 30/min authenticated
CORE_RATE_DELAY = 0.8    # GitHub core: 5000/hr authenticated
AWESOME_RATE_DELAY = 1.0  # Be nice to raw.githubusercontent.com

VALID_OS = ["windows", "macos", "linux", "web", "ios", "android"]
VALID_PRICING = ["free", "freemium", "paid", "subscription"]
VALID_LANGUAGES = [
    "python", "javascript", "typescript", "rust", "go", "c", "cpp", "java",
    "ruby", "php", "swift", "kotlin", "csharp", "dart", "elixir", "r",
    "julia", "lua", "zig", "haskell", "scala", "shell", "perl", "multi"
]

# Map GitHub language names to our schema enum
LANGUAGE_MAP = {
    "python": "python", "javascript": "javascript", "typescript": "typescript",
    "rust": "rust", "go": "go", "c": "c", "c++": "cpp", "c#": "csharp",
    "java": "java", "ruby": "ruby", "php": "php", "swift": "swift",
    "kotlin": "kotlin", "dart": "dart", "elixir": "elixir", "r": "r",
    "julia": "julia", "lua": "lua", "zig": "zig", "haskell": "haskell",
    "scala": "scala", "shell": "shell", "bash": "shell", "powershell": "shell",
    "perl": "perl",
}

def get_all_categories():
    """Extract all category names from taxonomy.json."""
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        tax = json.load(f)
    cats = set()
    def walk(node):
        if "categories" in node:
            cats.update(node["categories"])
        for child in node.get("children", []):
            walk(child)
    walk(tax)
    return cats

VALID_CATEGORIES = get_all_categories()
