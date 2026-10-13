"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # Criterion 3 — state. Same query as criterion 1; what's checked is the
        # listing id in search_results[0], selected_item, and the ids the trace
        # shows going into suggest_outfit and create_fit_card.
        "name": "item id carried through the session",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4 — the fit card. The SAME item five times, so the five
        # cards can be compared with each other (first sentences must differ).
        "name": "fit card: sentences, price, platform, opening",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 4,
    },
    # Criterion 5 (revised in unit 4) — one scenario per phrasing of the same
    # $30 ceiling, on "vintage jacket": with no ceiling it matches 6 listings
    # over $30, so a missed phrasing shows. ("graphic tee" had none.) The
    # criterion counts phrasings, so each phrasing is one "try" in the README
    # row; the search doesn't call the model, so its five runs should agree.
    {
        "name": "price ceiling: 'under $30'",
        "query": "vintage jacket under $30",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "price ceiling: 'below $30'",
        "query": "vintage jacket below $30",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "price ceiling: 'less than 30 dollars'",
        "query": "vintage jacket less than 30 dollars",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "price ceiling: 'max $30'",
        "query": "vintage jacket max $30",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        "name": "price ceiling: '$30 or less'",
        "query": "vintage jacket $30 or less",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
