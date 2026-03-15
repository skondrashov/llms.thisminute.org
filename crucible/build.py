"""Combines all idea JSON files into a single data.js for the UI."""
import json
import glob
import os


def load_ideas(data_dir):
    """Load all ideas from JSON files in a directory."""
    ideas = []
    seen_ids = set()
    file_count = 0
    for fpath in sorted(glob.glob(os.path.join(data_dir, "*.json"))):
        file_count += 1
        try:
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            items = data if isinstance(data, list) else [data]
            for item in items:
                pid = item.get("id")
                if not pid:
                    print(f"  WARNING: idea in {os.path.basename(fpath)} missing 'id', skipping")
                    continue
                if pid in seen_ids:
                    print(f"  WARNING: duplicate id '{pid}' in {os.path.basename(fpath)}, skipping")
                    continue
                seen_ids.add(pid)
                ideas.append(item)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ERROR reading {os.path.basename(fpath)}: {e}")
    return ideas, file_count


def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(root_dir, "data")

    ideas, file_count = load_ideas(data_dir)
    ideas.sort(key=lambda i: (i.get("category", ""), i.get("title", "")))

    out_path = os.path.join(root_dir, "data.js")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("window.CRUCIBLE_IDEAS = ")
        json.dump(ideas, f, indent=2, ensure_ascii=False)
        f.write(";\n")

    print(f"Built data.js with {len(ideas)} ideas from {file_count} files")

    # Category breakdown
    cats = {}
    for idea in ideas:
        cat = idea.get("category", "Uncategorized")
        cats[cat] = cats.get(cat, 0) + 1
    print("\nCategory breakdown:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Complexity breakdown
    complexities = {}
    for idea in ideas:
        c = idea.get("complexity", "unknown")
        complexities[c] = complexities.get(c, 0) + 1
    print("\nComplexity breakdown:")
    for c, count in sorted(complexities.items(), key=lambda x: -x[1]):
        print(f"  {c}: {count}")

    # Coordination model breakdown
    models = {}
    for idea in ideas:
        arch = idea.get("agentArchitecture", {})
        m = arch.get("coordinationModel", "unknown")
        models[m] = models.get(m, 0) + 1
    print("\nCoordination model breakdown:")
    for m, count in sorted(models.items(), key=lambda x: -x[1]):
        print(f"  {m}: {count}")


if __name__ == "__main__":
    main()
