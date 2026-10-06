"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str
    compare_prices(item)                           → dict   (stretch: a fourth tool)

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re
import statistics

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = _words(description)
    wanted_size = _size_tokens(size) if size else None

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if wanted_size and not _size_matches(wanted_size, listing["size"]):
            continue

        score = len(keywords & _searchable_words(listing))
        if score > 0:
            scored.append((score, listing))

    # sorted() is stable, so ties keep the order they have in the file.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


def _words(text: str) -> set[str]:
    """Lowercase whole words. Whole words, so 'tee' doesn't match 'street'."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _searchable_words(listing: dict) -> set[str]:
    """Every word search_listings scores against. brand is skipped when None."""
    parts = [
        listing["title"],
        listing["description"],
        listing["category"],
        " ".join(listing["style_tags"]),
        " ".join(listing["colors"]),
        listing["brand"] or "",
    ]
    return _words(" ".join(parts))


def _size_tokens(size: str) -> list[str]:
    """'XL (oversized)' -> ['xl', 'oversized']; 'US 8.5' -> ['us', '8.5']."""
    return [t for t in re.split(r"[\s/()]+", size.lower()) if t]


def _size_matches(wanted: list[str], listing_size: str) -> bool:
    """Every requested token must be a whole token of the listing's size."""
    if "one size" in listing_size.lower():
        return True
    have = _size_tokens(listing_size)
    return all(token in have for token in wanted)


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item = _describe_item(new_item)
    items = wardrobe.get("items") or []

    if not items:
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item}\n\n"
            "They haven't told us anything about their wardrobe. Give general "
            "styling advice: one or two outfits built around this piece, naming "
            "the kinds of items to pair it with (e.g. 'straight-leg dark jeans'), "
            "and one line on why each works."
        )
    else:
        owned = "\n".join(_describe_wardrobe_item(w) for w in items)
        prompt = (
            f"Someone is thinking about buying this thrifted piece:\n{item}\n\n"
            f"Here is what they already own:\n{owned}\n\n"
            "Suggest one or two outfits built around the new piece. Each outfit "
            "must name specific pieces from their wardrobe, using the names "
            "exactly as listed, and end with one line on why they work together. "
            "Only use pieces from the list."
        )

    response = generate(prompt, system=_STYLIST).strip()
    # The spec promises a non-empty string. A blank reply from the model
    # shouldn't break that promise for the tools downstream.
    return response or f"Style the {new_item['title']} with simple basics in neutral colors."


_STYLIST = (
    "You are a stylist who knows secondhand fashion. Answer in plain text, no "
    "markdown headings, under 120 words."
)


def _describe_item(listing: dict) -> str:
    lines = [
        f"- title: {listing['title']}",
        f"- category: {listing['category']}",
        f"- colors: {', '.join(listing['colors'])}",
        f"- style: {', '.join(listing['style_tags'])}",
        f"- size: {listing['size']}",
        f"- condition: {listing['condition']}",
        f"- price: ${listing['price']:.0f} on {listing['platform']}",
    ]
    if listing.get("brand"):
        lines.append(f"- brand: {listing['brand']}")
    return "\n".join(lines)


def _describe_wardrobe_item(w: dict) -> str:
    line = f"- {w['name']} ({w['category']}; {', '.join(w['colors'])}; {', '.join(w['style_tags'])})"
    if w.get("notes"):
        line += f" — {w['notes']}"
    return line


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "Can't write a fit card: no outfit suggestion was given."

    brand_rule = (
        f"Mention the brand ({new_item['brand']}) once."
        if new_item.get("brand")
        else "There is no brand; don't mention or invent one."
    )
    prompt = (
        f"The thrifted find:\n{_describe_item(new_item)}\n\n"
        f"How it's being styled:\n{outfit}\n\n"
        "Write a 2 to 4 sentence caption for a social media post about this find. "
        "It should sound like a real person posting their outfit, not a product "
        "description. Mention the item, its price written as "
        f"${new_item['price']:.0f}, and the platform ({new_item['platform']}) "
        f"exactly once each. {brand_rule} Be specific about the vibe. "
        "Return only the caption."
    )
    return generate(prompt).strip()


# ── Tool 4 (stretch): compare_prices ──────────────────────────────────────────

def compare_prices(item: dict) -> dict:
    """
    Say whether the selected item is a good price, compared with similar
    listings: same category, sharing at least one style tag, not the item
    itself. Doesn't call the model.

    Returns a dict with item_price, comparable_count, median_price, verdict
    ("below typical" / "about typical" / "above typical", using ±15% of the
    median) and cheaper (up to 3 comparable listings that cost less, cheapest
    first). With no comparables: count 0, median None, cheaper [], verdict
    "no comparables". Never raises.
    """
    tags = set(item["style_tags"])
    comparables = [
        listing
        for listing in load_listings()
        if listing["id"] != item["id"]
        and listing["category"] == item["category"]
        and tags & set(listing["style_tags"])
    ]

    if not comparables:
        return {
            "item_price": item["price"],
            "comparable_count": 0,
            "median_price": None,
            "verdict": "no comparables",
            "cheaper": [],
        }

    median = statistics.median(listing["price"] for listing in comparables)
    if item["price"] < median * 0.85:
        verdict = "below typical"
    elif item["price"] > median * 1.15:
        verdict = "above typical"
    else:
        verdict = "about typical"

    cheaper = sorted(
        (listing for listing in comparables if listing["price"] < item["price"]),
        key=lambda listing: listing["price"],
    )[:3]

    return {
        "item_price": item["price"],
        "comparable_count": len(comparables),
        "median_price": median,
        "verdict": verdict,
        "cheaper": cheaper,
    }
