"""
Your MCP server. ← UNIT 4, MILESTONE 1

Right now your tools only exist inside your own program. Nothing else can reach
them. MCP is an agreed shape you wrap a tool in so that anything speaking the
same protocol can call it — your agent today, a different agent tomorrow,
someone else's app after that.

**You're moving one tool. Not three.** The point is to see the seam.
`search_listings` is the one to move: it doesn't call the model, so nothing is
slow and nothing changes between runs while you're learning the shape.

    python mcp_server.py        starts the server (it will just sit there — that's right)
    python mcp_client.py        asks the server what it offers

─────────────────────────────────────────────────────────────────────────────
TODO — register one tool.

Uncomment the block below and fill it in. Three things matter:

  1. **The name.** Exactly what your agent will ask for.

  2. **The description.** This is the part that isn't code and matters most.
     Write it before you look at the example. You are not writing it for your
     agent — you're writing it for an agent someone else builds, that will
     never see your implementation. That isn't hypothetical; it's what every
     MCP server on the registry is.

     Two things to get right: name units and types ("price" is ambiguous,
     "max_price, in whole dollars" isn't), and state the empty case. Last unit
     the empty case was on your spec sheet for your loop's benefit. Here it's
     part of a published contract.

  3. **The typed inputs.** These come straight from your Tool Inventory. If the
     types here don't match your README, one of the two is wrong — fix it.

Then point your agent at it. In `run_agent()`, swap the direct call:

    results = search_listings(description, size, max_price)

for the MCP one:

    from mcp_client import call_tool
    results = call_tool("search_listings", {
        "description": description,
        "size": size,
        "max_price": max_price,
    })

**What comes back should not change.** If it does, that difference is your
first clue about what your tool was really returning before.

🛑 Stop rule: if this isn't connecting after 40 minutes, stop. Keep your direct
call, and write down in your README exactly where it broke — the error text and
the last thing that worked. Then carry on to Milestone 2. Everything after this
works with a direct call, and **a documented failure earns the point in full.**
─────────────────────────────────────────────────────────────────────────────
"""

from mcp.server.fastmcp import FastMCP

from tools import search_listings as _search_listings_impl
from tools import compare_prices as _compare_prices_impl

# log_level="WARNING" keeps the server from printing an INFO line for every
# request. Without it your terminal fills with "Processing request of type
# CallToolRequest" and the output you actually care about scrolls away.
mcp = FastMCP("fitfindr", log_level="WARNING")


@mcp.tool()
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search secondhand clothing listings (Depop, Poshmark, etc.) by keywords,
    optionally filtered by size and a price ceiling.

    Inputs: `description` — space-separated keywords, matched as whole words
    against title, description, category, style tags, colors and brand
    (e.g. "vintage graphic tee"). `size` — a size like "M", "W30" or "8";
    every token must appear as a whole token of the listing's size, so "M"
    matches "S/M" but not "XL"; "one size" listings always match; omit to skip.
    `max_price` — inclusive ceiling in US dollars (e.g. 30 or 24.5); omit to skip.

    Returns up to 10 listing objects, best keyword match first, each with: id,
    title, description, category, style_tags (list), size, condition, price
    (float, US dollars), colors (list), brand (string or null — usually null),
    platform. Returns an empty list [] when nothing matches; it never returns
    null and never errors on a no-match search.
    """
    return _search_listings_impl(description, size, max_price)


# ──────────────────────────────────────────────────────────────────────────────
#
# Two notes on the registration above.
#
# The registered name is the *function* name — so the block above registers
# "search_listings", which is exactly what call_tool("search_listings", ...)
# asks for. That is also why the import at the top of this file brings the real
# implementation in under an alias: without it, the registered function and the
# one it calls would be the same name, and the tool would call itself.
#
# FastMCP builds the input schema from your type hints, which is why the hints
# are not optional here. `description: str` becomes a required string;
# `max_price: float | None = None` becomes an optional number. Getting these
# wrong is the most common reason a call is rejected.


@mcp.tool()
def compare_prices(item: dict) -> dict:
    """
    Say whether one secondhand clothing listing is a good price, compared with
    similar listings in the same data: same category, at least one shared style
    tag, excluding the item itself. Does not call a model.

    Input: `item` — one listing object exactly as `search_listings` returns
    it; it must have id, price (US dollars), category and style_tags (list).

    Returns an object with: item_price (float, US dollars), comparable_count
    (int), median_price (float, US dollars, the median of the comparables),
    verdict ("below typical" / "about typical" / "above typical", i.e. more
    than 15% under, within 15% of, or more than 15% over the median) and
    cheaper (up to 3 comparable listing objects that cost less, cheapest first).
    When there are no comparables it returns comparable_count 0, median_price
    null, cheaper [] and verdict "no comparables" — never an error.
    """
    return _compare_prices_impl(item)


if __name__ == "__main__":
    mcp.run()
