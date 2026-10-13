"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card, compare_prices
from mcp_client import call_tool, MCPError
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "selection_note": None,      # set when the fair-condition branch picked another item
        "price_check": None,         # what compare_prices returned
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # Each pass picks the next step from what the last one left in the
    # session. Every tool reads its inputs back out of the session, never
    # from a local variable, so the state stays visible.
    next_step = "parse"
    count = 0
    try:
        while next_step != "done":
            count += 1
            trace.check_iterations(count)

            if next_step == "parse":
                session["parsed"] = parse_query(session["query"])
                trace.step("parse_query", inputs=session["query"], returned=str(session["parsed"]))
                next_step = "search"

            elif next_step == "search":
                parsed = session["parsed"]
                # search_listings runs on the MCP server (mcp_server.py), not in-process.
                session["search_results"] = call_tool("search_listings", {
                    "description": parsed["description"],
                    "size": parsed["size"],
                    "max_price": parsed["max_price"],
                })
                # THE BRANCH: nothing found means stop here, before any model call.
                if not session["search_results"]:
                    session["error"] = _no_results_message(parsed)
                    next_step = "done"
                else:
                    next_step = "select"
                trace.step("search_listings (via MCP)", inputs=str(parsed),
                           returned=session["search_results"],
                           note="branch: empty, stopping" if next_step == "done" else "")

            elif next_step == "select":
                results = session["search_results"]
                # SECOND BRANCH: a fair-condition top match gives way to a
                # same-category result in better shape, when the search found one.
                better = _better_condition_alternative(results)
                if better:
                    session["selected_item"] = better
                    session["selection_note"] = (
                        f"Top match '{results[0]['title']}' is in fair condition, so I "
                        f"picked '{better['title']}' ({better['condition']} condition, "
                        f"also {better['category']}) instead."
                    )
                else:
                    session["selected_item"] = results[0]
                trace.step("select", inputs=f"{len(results)} results",
                           returned=session["selected_item"],
                           note="branch: fair-condition top match swapped" if better
                           else "first result")
                next_step = "compare_prices"

            elif next_step == "compare_prices":
                session["price_check"] = compare_prices(session["selected_item"])
                check = session["price_check"]
                trace.step("compare_prices", inputs=session["selected_item"],
                           returned=f"{check['verdict']}, median ${check['median_price']} "
                                    f"across {check['comparable_count']} comparable"
                           if check["comparable_count"] else "no comparable listings")
                next_step = "suggest_outfit"

            elif next_step == "suggest_outfit":
                session["outfit_suggestion"] = suggest_outfit(
                    session["selected_item"], session["wardrobe"]
                )
                trace.step("suggest_outfit",
                           inputs=f"{session['selected_item']['title']} + "
                                  f"{len(session['wardrobe']['items'])} wardrobe items",
                           returned=session["outfit_suggestion"])
                next_step = "create_fit_card"

            elif next_step == "create_fit_card":
                session["fit_card"] = create_fit_card(
                    session["outfit_suggestion"], session["selected_item"]
                )
                trace.step("create_fit_card",
                           inputs=f"outfit ({len(session['outfit_suggestion'])} chars) + "
                                  f"{session['selected_item']['title']}",
                           returned=session["fit_card"])
                next_step = "done"

    # Failures end the run with a message in session["error"], the same way the
    # empty search does, instead of escaping as a stack trace.
    except ModelUnavailable as exc:
        found = session["selected_item"]
        session["error"] = (
            f"The model couldn't be reached during {next_step}, so there's no "
            f"outfit or fit card this time. {exc}"
            + (f" (The search itself worked: it found '{found['title']}' for "
               f"${found['price']:.0f} on {found['platform']}.)" if found else "")
        )
        trace.step(next_step, note="failed: ModelUnavailable, stopping")
    except MCPError as exc:
        session["error"] = (
            f"The listing search couldn't run, because the MCP server for "
            f"search_listings didn't answer. Run `python mcp_server.py` on its own "
            f"to see why, then try again. Details: {exc}"
        )
        trace.step(next_step, note="failed: MCPError, stopping")

    return session


def _better_condition_alternative(results: list[dict]) -> dict | None:
    """
    If the top result is in fair condition, the first later result in the same
    category that's good or excellent. Otherwise None — keep the top result.
    """
    top = results[0]
    if top["condition"] != "fair":
        return None
    for listing in results[1:]:
        if listing["category"] == top["category"] and listing["condition"] in ("good", "excellent"):
            return listing
    return None


# ── query parsing (regex) ─────────────────────────────────────────────────────

# "under $30", "below $30", "less than 30 dollars", "max $30", "up to $30"
_PRICE_BEFORE = re.compile(
    r"\b(?:under|below|less than|max(?:imum)?|up to|at most)\s*\$?\s*(\d+(?:\.\d+)?)(?:\s*dollars?)?",
    re.IGNORECASE,
)
# "$30 or less", "30 dollars max", "$30 max"
_PRICE_AFTER = re.compile(
    r"\$?\s*(\d+(?:\.\d+)?)\s*(?:dollars?\s*)?(?:or less|or under|max(?:imum)?)\b",
    re.IGNORECASE,
)
# "size M", "in size XXS", "size 8.5", "size W30"
_SIZE = re.compile(r"\b(?:in\s+)?size\s+([a-z0-9./]+)", re.IGNORECASE)

# Words that say how someone is asking, not what they're asking for.
_FILLER = {
    "a", "an", "the", "i", "im", "i'm", "me", "my", "for", "in", "of", "and",
    "or", "with", "want", "need", "looking", "find", "show", "some",
    "something", "any", "please", "get", "buy", "to", "is", "that",
}


def parse_query(query: str) -> dict:
    """
    Pull description, size and max_price out of a plain-language query.

    Each part that's found is cut out of the text, so "under $30" doesn't end
    up as search keywords. Whatever is left, minus filler words, is the
    description.
    """
    text = query
    max_price = None
    for pattern in (_PRICE_BEFORE, _PRICE_AFTER):
        match = pattern.search(text)
        if match:
            max_price = float(match.group(1))
            text = text[: match.start()] + " " + text[match.end():]
            break

    size = None
    match = _SIZE.search(text)
    if match:
        size = match.group(1)
        text = text[: match.start()] + " " + text[match.end():]

    words = re.findall(r"[a-z0-9'-]+", text.lower())
    description = " ".join(w for w in words if w not in _FILLER)

    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict) -> str:
    """Say what was searched and what the user could change — not just 'No results'."""
    if not parsed["description"]:
        return (
            "I couldn't tell what kind of item you want. Name the piece, "
            "e.g. 'graphic tee' or 'denim jacket'."
        )

    searched = f"'{parsed['description']}'"
    if parsed["size"]:
        searched += f" in size {parsed['size']}"
    if parsed["max_price"] is not None:
        searched += f" under ${parsed['max_price']:.0f}"

    changes = []
    if parsed["max_price"] is not None:
        changes.append(f"raise your price limit above ${parsed['max_price']:.0f}")
    if parsed["size"]:
        changes.append(f"drop the size {parsed['size']}")
    changes.append("use fewer or more general words (e.g. 'dress' instead of the full phrase)")

    return f"Nothing matched {searched}. Try one of these: " + "; ".join(changes) + "."


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
