"""
Output writer for scraped entries.
Writes to data/discovered_YYYYMMDD.json (dated batches) and/or data/discovered.json (append).
"""

import json
import os
from datetime import datetime
from .config import DATA_DIR


def write_entries(entries, filename=None, append=True):
    """
    Write entries to a JSON file in the data directory.

    If filename is None, generates a dated filename like discovered_20260312.json
    If append=True and the file exists, merges new entries with existing ones (dedup by id).
    """
    if not entries:
        print("  No entries to write.")
        return None

    if filename is None:
        date_str = datetime.now().strftime("%Y%m%d")
        filename = f"discovered_{date_str}.json"

    filepath = os.path.join(DATA_DIR, filename)

    existing = []
    if append and os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            existing = json.load(f)

    # Dedup by id
    existing_ids = {e["id"] for e in existing}
    new_entries = [e for e in entries if e["id"] not in existing_ids]

    merged = existing + new_entries

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"  Wrote {len(new_entries)} new entries to {filename} (total: {len(merged)})")
    return filepath
