"""
Style memory (stretch): remember items the agent found, between runs.

Opt-in only. `python app.py ask '...' --remember` adds what's saved here to the
wardrobe before the run and saves the item it finds afterwards. Without the
flag nothing is read or written, so run_eval.py and the criteria always run
against a fixed wardrobe.

Saved items use the wardrobe item shape from data/wardrobe_schema.json, so
suggest_outfit can't tell a remembered piece from one the user typed in.
"""

import json

import config

MEMORY_PATH = config.ROOT / "memory" / "wardrobe.json"


def load_memory() -> list[dict]:
    """Every remembered wardrobe item, or [] when nothing is saved yet."""
    if not MEMORY_PATH.exists():
        return []
    try:
        return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))["items"]
    except (json.JSONDecodeError, KeyError):
        return []


def remember_item(listing: dict) -> bool:
    """
    Save a found listing as a wardrobe item. Returns False when it was
    already saved, so the same find isn't added twice.
    """
    items = load_memory()
    item_id = f"mem_{listing['id']}"
    if any(item["id"] == item_id for item in items):
        return False

    items.append({
        "id": item_id,
        "name": listing["title"],
        "category": listing["category"],
        "colors": listing["colors"],
        "style_tags": listing["style_tags"],
        "notes": f"Found with FitFindr on {listing['platform']} for ${listing['price']:.0f}",
    })
    MEMORY_PATH.parent.mkdir(exist_ok=True)
    MEMORY_PATH.write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    return True


def clear_memory() -> int:
    """Forget everything. Returns how many items were removed."""
    count = len(load_memory())
    if MEMORY_PATH.exists():
        MEMORY_PATH.unlink()
    return count
