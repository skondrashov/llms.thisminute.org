import re
from .config import VALID_OS, VALID_PRICING, VALID_LANGUAGES, VALID_CATEGORIES


def validate_entry(entry):
    errors = []
    for field in ("id", "name", "description", "url", "category", "os", "pricing"):
        if field not in entry or not entry[field]:
            errors.append(f"Missing: {field}")

    eid = entry.get("id", "")
    if eid and not re.match(r'^[a-z0-9-]+$', eid):
        errors.append(f"Bad id: {eid}")

    desc = entry.get("description", "")
    if len(desc) > 200:
        errors.append(f"Desc too long: {len(desc)}")

    for os_val in entry.get("os", []):
        if os_val not in VALID_OS:
            errors.append(f"Bad OS: {os_val}")

    pricing = entry.get("pricing")
    if pricing and pricing not in VALID_PRICING:
        errors.append(f"Bad pricing: {pricing}")

    lang = entry.get("language")
    if lang and lang not in VALID_LANGUAGES:
        errors.append(f"Bad language: {lang}")

    cat = entry.get("category")
    if cat and cat not in VALID_CATEGORIES:
        errors.append(f"Bad category: {cat}")

    return len(errors) == 0, errors
