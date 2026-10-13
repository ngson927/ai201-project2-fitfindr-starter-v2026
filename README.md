# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- Three or four sentences: what a user asks for, and what they get back. -->

FitFindr takes a plain-language request for a secondhand piece, like
`vintage graphic tee under $30` or `90s track jacket in size M`, and searches
40 thrift listings from Depop, thredUp and Poshmark for the best match within
the size and price limit. For the top match it suggests one or two outfits
using pieces the user already owns (or general styling advice if their
wardrobe is empty), then writes a short social-media caption about the find.
If nothing matches, it stops before calling the model and tells the user what
to change: raise the price limit, drop the size, or use broader words.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Finds listings in `data/listings.json` that match a keyword description, optionally filtered by size and a price ceiling, ranked best match first. It does not call the model.
- **Inputs:** `description` (str) — keywords like `"vintage graphic tee"`; `size` (str or None) — e.g. `"M"`, `"W30"`, `"8"`, None skips the size filter; `max_price` (float or None) — inclusive ceiling, None skips the price filter.
- **Returns:** A `list[dict]` of at most `config.SEARCH_RESULT_LIMIT` (10) listing dicts, sorted by score highest first (ties keep file order). Each dict is the full listing, unchanged: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand` (str or **None**), `platform`.
  - *Score:* the description is lowercased and split into words; each word scores 1 point if it appears as a whole word (not a substring — `tee` must not match `street`) in the listing's title, description, category, style_tags, colors, or brand (skipped when None). Listings scoring 0 are dropped.
  - *Size match:* both sizes are lowercased and split into tokens on spaces, `/`, and parentheses. A listing matches when every token of the requested size is a whole token of the listing's size. So `"M"` matches `M`, `S/M`, `M/L` but not `XL`; `"S"` does not match `US 9`; `"8"` matches `US 8` but not `US 8.5`. Listings whose size contains `one size` match any requested size.
- **When it has nothing:** Returns an empty list `[]` — never `None`, never an exception. This is what the loop branches on.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the thrifted item, using pieces the user already owns.
- **Inputs:** `new_item` (dict) — one listing dict from `search_listings`; `wardrobe` (dict) — `{"items": [...]}` where each item has `id`, `name`, `category`, `colors` (list), `style_tags` (list), `notes` (str or None). `items` may be an empty list.
- **Returns:** A non-empty `str` of plain text: one or two outfits, each naming the new item and the specific wardrobe pieces (by their `name`) it pairs with, plus a one-line reason why they work together.
- **When it has nothing:** If `wardrobe["items"]` is empty, it still returns a non-empty `str` — general styling advice for the item (what kinds of pieces to pair it with) instead of naming owned pieces. It never returns `""` and never raises for an empty wardrobe. If the model itself can't be reached, `generate()` raises `ModelUnavailable` and the tool lets it propagate to the loop.

### `create_fit_card`

- **What it does:** Asks the model to write a short, social-media-style caption about the find and how it's styled.
- **Inputs:** `outfit` (str) — the string returned by `suggest_outfit`; `new_item` (dict) — the same listing dict passed to `suggest_outfit`.
- **Returns:** A `str` caption of 2–4 sentences that reads like a real post, mentions the item's title, price (as `$NN`), and platform once each, and describes the vibe. The brand is mentioned only when it isn't None. With `TEMPERATURE = 0.9` the wording differs between runs.
- **When it has nothing:** If `outfit` is empty or only whitespace, it returns the string `"Can't write a fit card: no outfit suggestion was given."` without calling the model. It never raises for empty input.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that says what the user could change (raise the price ceiling, drop the size, or use fewer/different keywords), and return the session without calling `suggest_outfit` or `create_fit_card`. Otherwise, take the first result as `session["selected_item"]` and go to `suggest_outfit`, then `create_fit_card`.

**Second branch (stretch):** In the `select` step, if the first result is in `fair` condition and a later result in the same category is `good` or `excellent`, select that one instead and explain why in `session["selection_note"]`. Otherwise select the first result. See Stretch 2 below.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. A price pattern catches `under/below/less than/max/up to $N` and `$N or less`; a size pattern catches `size X` / `in size X`. Each match is cut out of the text, filler words (`looking`, `for`, `a`, …) are dropped, and what's left is the description.

**What moves through the session:** `query` → `parsed` (description, size, max_price) → `search_results` → [branch: empty sets `error` and stops] → `selected_item` (first result, or a better-condition one — second branch) → `price_check` (from `compare_prices`) → `outfit_suggestion` → `fit_card`. Each step reads its inputs back out of the session, not from a local variable. The loop is a `while` that picks `next_step` from what the last step left in the session, calling `trace.check_iterations` on every pass.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop (excellent)
  Price:    below typical — median $22 across 14 similar listings; cheapest similar: Mesh Long-Sleeve Top — Black at $15

  Outfit:   Outfit one: Pair the Y2K Baby Tee — Butterfly Print with your Baggy straight-leg jeans, dark wash. Layer the vintage black denim jacket on top and finish with the chunky white sneakers. The fitted baby tee balances the loose jeans, and the jacket ties the retro streetwear vibe together.

Outfit two: Combine the Y2K Baby Tee — Butterfly Print with your wide-leg khaki trousers and the brown leather belt. Step into your black combat boots to complete the look. The pastel butterfly print pops against the earthy khaki, creating a playful contrast between sweet Y2K style and grunge footwear.

  Fit card: scored this adorable little butterfly baby tee on depop for only $18 and I am so obsessed with how versatile it is. styling it with baggy denim gives me the ultimate retro streetwear energy, while pairing it with earth-toned trousers and chunky boots leans right into that sweet-meets-grunge aesthetic. honestly the best thrifted find for putting together effortless everyday looks!

0 model calls this session, 2 served from cache
```

**The three tools, tested one at a time**

`search_listings` — a match, then the empty case:

```
$ python -c "from tools import search_listings; print([(r['title'], r['price'], r['size'], r['platform']) for r in search_listings('graphic tee', max_price=30)])"
[('Y2K Baby Tee — Butterfly Print', 18.0, 'S/M', 'depop'), ('Graphic Tee — 2003 Tour Bootleg Style', 24.0, 'L', 'depop'), ('Mesh Long-Sleeve Top — Black', 15.0, 'S/M', 'depop'), ('Vintage Band Tee — Faded Grey', 19.0, 'L', 'depop'), ('Low-Rise Cargo Pants — Khaki', 27.0, 'W29', 'poshmark'), ('Vintage Graphic Hoodie — Faded Black', 26.0, 'L', 'depop')]

$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

`suggest_outfit`:

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Outfit One
Pair the Vintage Levi's 501 Jeans — Medium Wash with the White ribbed tank top and the Vintage black denim jacket, finished with Chunky white sneakers. 
This look plays on classic denim-on-denim styling while the fitted tank balances the straight-leg cut for an effortless everyday streetwear vibe.

Outfit Two
Style the Vintage Levi's 501 Jeans — Medium Wash with the Oversized grey crewneck sweatshirt and the Black combat boots, pulling it together using the Brown leather belt. 
The mid-wash denim grounds the massive proportions of the grey sweatshirt, and the belt adds a polished vintage touch that anchors the grunge boots.
```

`create_fit_card`:

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[1]))"
Obsessed with how this Y2K butterfly baby tee fits with my favorite baggy jeans and white sneakers. Scored it for just $18 on depop and it brings the ultimate sweet, nostalgic cottagecore energy. Definitely my new go-to look for sunny weekend coffee runs!
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

I used Claude Code (in VS Code) for most of this unit. I pasted each
milestone into it, and it wrote the Tool Inventory spec, the three tools, the
planning loop, and the draft of criteria 3–5, testing each part from the
terminal as it went. The two moments below are where something came back
wrong or unclear and got changed, and who decided what.

**Moment 1**

- *What I asked for:* I pasted Milestone 4 and asked Claude to build the three
  tools from the `search_listings` spec in the Tool Inventory (one point per
  whole-word keyword match, token-based size match) and test each one.
- *What came back:* A tool that followed the spec: `[]` for
  `designer ballgown, size XXS, under $5`, `M` matching `S/M` but not `XL`,
  `8` matching `US 8` but not `US 8.5`. But `graphic tee` under $30 also
  returned **Low-Rise Cargo Pants**, because that listing's description
  contains the word "tee". Claude pointed this out after the test.
- *What I changed:* Nothing in the code yet. Claude's reasoning, which I agree
  with, is that the tool does what the spec says, so this is a weakness in the
  spec (every field scores the same), not a bug. It's left in on purpose as
  the first thing to check if criterion 1 or 4 misses in unit 4. The fix to
  try then is weighting `title` and `style_tags` above `description`.

**Moment 2**

- *What I asked for:* I asked Claude to write criteria 3–5 for me. The
  milestone says not to have a model write criteria, only to have it attack
  them. I skipped that advice, so these criteria are Claude's drafts, which I
  read and accepted rather than wrote.
- *What came back:* The first draft of criterion 4 (fit card) included
  "(c) names no brand when the item's brand is None." When Claude re-read it
  against the question "could someone check this without asking what I
  meant?", it didn't pass: deciding whether a word in a caption is a brand
  takes judgement.
- *What I changed:* Claude replaced (c) with "has a first sentence that no
  other card in the five starts with", which can be checked by comparing five
  strings, and updated the reason to match. What I take from this for unit 4:
  if a criterion turns out to be unmeasurable, I'll revise it underneath the
  original as `criteria.md` describes, and I'll write my own reasoning when I
  diagnose the results.

---

## Stretch Features

<!-- Declared here, and committed, BEFORE any of the three was built. -->

All three stretch items, declared before building. Each subsection says what I
plan to build; the **Result** lines are filled in after it's built.

### Stretch 1 — A fourth tool: `compare_prices`

- **What it does:** Checks whether the selected item is a good price by
  comparing it with similar listings in the data. It doesn't call the model.
- **Inputs:** `item` (dict) — the selected listing dict.
- **Returns:** A `dict` with `item_price` (float), `comparable_count` (int,
  listings in the same `category` that share at least one `style_tag`, not
  counting the item itself), `median_price` (float or None), `verdict` (str:
  `"below typical"`, `"about typical"` or `"above typical"`, using ±15% of
  the median), and `cheaper` (list of up to 3 comparable listing dicts that
  cost less, cheapest first).
- **When it has nothing:** If no comparable listings exist,
  `comparable_count` is 0, `median_price` is None, `cheaper` is `[]`, and
  `verdict` is `"no comparables"`. It never raises.
- **Where the loop calls it:** `agent.py::run_agent`, after the item is
  selected and before `suggest_outfit`. The result goes in
  `session["price_check"]`.

**Result:** Built as declared: `tools.py::compare_prices`, called from `agent.py::run_agent` in the `compare_prices` step on every run that gets past the search. `app.py` prints the result on the `Price:` line. What it changed: every answer now says whether the find is a good price. Run where the agent called it (cache off):

```
$ python app.py ask '90s track jacket in size M'

  Found:    90s Track Jacket — Navy/White Stripe — $45.0 on poshmark (excellent)
  Price:    about typical — median $41 across 6 similar listings; cheapest similar: Denim Vest — Medium Wash, Studded at $27

  Outfit:   Outfit one: Pair the 90s Track Jacket — Navy/White Stripe with the White ribbed tank top, Baggy straight-leg jeans, dark wash, and Chunky white sneakers. 
This look leans into sporty 90s streetwear, where the fitted white tank balances the relaxed jacket and baggy denim while the sneakers tie the athletic vibe together.

Outfit two: Style the 90s Track Jacket — Navy/White Stripe over the White ribbed tank top with the Wide-leg khaki trousers and Chunky white sneakers. 
This outfit mixes athletic retro outerwear with tailored earth-toned trousers for a modern, effortless high-low streetwear aesthetic.

  Fit card: Still obsessed with how this vintage Champion track jacket turned out, especially since I managed to score it for just $45 on poshmark. It brings the ultimate 90s streetwear energy whether I'm dressing it down with baggy denim or leaning into that high-low mix with tailored trousers. Talk about a thrift win.

2 model calls this session, 674 prompt + 200 output tokens
```

Tested on its own:

```
$ python -c "from tools import compare_prices; from utils.data_loader import load_listings; c = compare_prices(load_listings()[1]); print({**c, 'cheaper': [(x['title'], x['price']) for x in c['cheaper']]})"
{'item_price': 18.0, 'comparable_count': 14, 'median_price': 21.5, 'verdict': 'below typical', 'cheaper': [('Mesh Long-Sleeve Top — Black', 15.0), ('Henley Long Sleeve — Washed Burgundy', 16.0), ('Tie-Dye Long Sleeve — Pastel', 17.0)]}
```

### Stretch 2 — A second branch: avoid a fair-condition pick

- **Condition:** The top search result has `condition == "fair"`, and another
  result in `session["search_results"]` is in the **same category** with
  condition `"good"` or `"excellent"`.
- **Path when it's true:** Select the first such better-condition listing
  instead of the top result, and record why in
  `session["selection_note"]`.
- **Path when it's false:** Select the top result, as before.
- **Why:** "Fair" listings in this data have visible wear (fading, pilling).
  If something similar in better shape matched the same search, that's the
  better suggestion.
- **Where it lives:** `agent.py::run_agent`, in the `select` step.

**Result:** Built as declared, in `agent.py::run_agent` (`select` step) with the check in `agent.py::_better_condition_alternative`. Run log where the branch was taken: the top match for `cargo pants` is the fair-condition Low-Rise Cargo Pants, so the agent picked the good-condition corduroys instead (cache off):

```
$ python app.py ask 'cargo pants under $40'

  Note:     Top match 'Low-Rise Cargo Pants — Khaki' is in fair condition, so I picked 'Corduroy Wide-Leg Pants — Rust' (good condition, also bottoms) instead.
  Found:    Corduroy Wide-Leg Pants — Rust — $32.0 on depop (good)
  Price:    about typical — median $30 across 7 similar listings; cheapest similar: High-Waisted Denim Shorts — Cutoff at $24

  Outfit:   Outfit 1: Pair the Corduroy Wide-Leg Pants — Rust with the white ribbed tank top tucked in, add the brown leather belt, and layer the oversized grey crewneck sweatshirt on top. Finish with the chunky white sneakers. 
Why it works: The cropped waist definition balances the slouchy sweatshirt while the earthy tones and textures lean into your vintage cottagecore aesthetic.

Outfit 2: Style the Corduroy Wide-Leg Pants — Rust with the white ribbed tank top, secure with the brown leather belt, and top with the vintage black denim jacket. Complete the look with the black combat boots.
Why it works: The rich rust shade grounds the edgy black outerwear and boots for a balanced, retro-inspired mix.

  Fit card: Scored these vintage rust corduroy wide-leg pants on depop for just $32 and I am never taking them off. They bring the ultimate 70s earth-tone cottagecore energy to my wardrobe. Can't decide if I love them more with a cozy oversized crewneck or styled edgy with a black denim jacket and boots!

2 model calls this session, 684 prompt + 219 output tokens
```

What it changed, including a weakness: "same category" is coarse. For `graphic hoodie` the fair-condition hoodie gets swapped for the excellent-condition Y2K Baby Tee, because both are `tops`. That's the rule I declared, so I've left it, but requiring a shared `style_tag` or keyword would be a tighter rule to try. The query in my criteria (`vintage graphic tee under $30`) tops out with an excellent-condition item, so this branch doesn't change criterion 3.

### Stretch 3 — Style memory

- **What it remembers:** With `python app.py ask '...' --remember`, every
  item the agent successfully finds is saved to `memory/wardrobe.json` as a
  wardrobe item (same shape as `data/wardrobe_schema.json`).
- **How it shapes the next run:** On the next `--remember` run, the saved
  items are added to the wardrobe passed to `suggest_outfit`, so the outfit
  can name a piece found in an earlier run. `--forget` clears the file.
- **Why opt-in:** Without the flag nothing is read or written, so
  `run_eval.py` and my five criteria run against a fixed wardrobe.
- **Where it lives:** `memory.py` (`load_memory`, `remember_item`,
  `clear_memory`), used from `app.py`.

**Result:** Built as declared: `memory.py` plus `--remember` / `--forget` in `app.py`. `memory/` is in `.gitignore` because it's one user's data. Two runs with an **empty** wardrobe, so anything the second outfit names from the user's closet can only have come from memory. The first run saved the Y2K Baby Tee; the second run's outfit is built around it (cache off):

```
$ python app.py ask --forget
(style memory cleared: 0 item(s) forgotten)

$ python app.py ask 'vintage graphic tee under $30' --empty-wardrobe --remember
(running with an empty wardrobe)
(style memory: 0 saved item(s) added to the wardrobe)

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop (excellent)
  Price:    below typical — median $22 across 14 similar listings; cheapest similar: Mesh Long-Sleeve Top — Black at $15

  Outfit:   Grab this Y2K baby tee—it is a total steal for eighteen bucks. 

For a classic noughties look, pair it with low-rise baggy cargo pants and chunky platform sandals. The voluminous bottoms balance the tight crop of the shirt for that iconic off-duty pop star silhouette. 

Alternatively, lean into the cottagecore crossover by styling it under a denim overall dress with retro sneakers. The rugged denim tones down the sweetness of the pink butterfly graphic while keeping the nostalgic vibe intact.

  Fit card: scored this y2k baby tee for just $18 on depop and i’m obsessed with the butterfly print. it gives total noughties pop star off-duty energy when paired with low-rise cargo pants. such a lucky thrift find!

  Saved 'Y2K Baby Tee — Butterfly Print' to style memory (memory/wardrobe.json).

2 model calls this session, 416 prompt + 152 output tokens

$ python app.py ask 'denim jacket under $50' --empty-wardrobe --remember
(running with an empty wardrobe)
(style memory: 1 saved item(s) added to the wardrobe)

  Found:    Denim Jacket — Light Wash, Cropped — $42.0 on poshmark (excellent)
  Price:    about typical — median $40 across 7 similar listings; cheapest similar: Denim Vest — Medium Wash, Studded at $27

  Outfit:   Outfit One: Throw the Denim Jacket — Light Wash, Cropped right over the Y2K Baby Tee — Butterfly Print. 

Why they work together: The structured, light-wash vintage denim balances the playful Y2K energy of the baby tee for an effortless, throwback streetwear look.

  Fit card: Score this vintage Wrangler jacket on Poshmark for just $42 and honestly, it’s the ultimate Y2K throw-on-and-go piece. I layered it right over my favorite butterfly print baby tee, and the light wash denim gives it that perfectly worn-in streetwear edge. It’s giving effortless 90s nostalgia in the best way possible.

  Saved 'Denim Jacket — Light Wash, Cropped' to style memory (memory/wardrobe.json).

2 model calls this session, 408 prompt + 136 output tokens
```

What it changed: on the second run `suggest_outfit` received a wardrobe with one item instead of none, so it switched from general advice to a specific pairing ("over the Y2K Baby Tee — Butterfly Print"), and the fit card picked that up too.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

Run with `python run_eval.py --label before`: every scenario in `scenarios.py`, five tries each, cache off, `TEMPERATURE = 0.9`. It made 90 model calls and none crashed. The full report is in [results/run_2026-10-13_1847_before.md](results/run_2026-10-13_1847_before.md), with the raw sessions next to it in the `.json` file. Each try was marked by `python score_run.py results/run_2026-10-13_1847_before.json`. That script applies each criterion from `criteria.md` exactly as written:

1. **Criterion 1:** no error, a non-empty `fit_card`, and `search_listings`, `suggest_outfit` and `create_fit_card` all present in the trace.
2. **Criterion 2:** `error` set, `outfit_suggestion` and `fit_card` both None, no `suggest_outfit` in the trace, and the message names the price, the size and the words.
3. **Criterion 3:** four ids compared: `search_results[0]`, `selected_item`, and the `[id]` the trace shows going into `suggest_outfit` and into `create_fit_card`.
4. **Criterion 4:** sentences counted as `[.!?]` followed by a space or the end; `$18` and `depop` each counted, case-insensitive; whole first sentence compared across the five cards.
5. **Criterion 5:** every result in `search_results` has a price of 30 or less.

Criterion 5 counts *phrasings*, so Try *n* in its row is phrasing *n* (`under $30`, `below $30`, `less than 30 dollars`, `max $30`, `$30 or less`). Each phrasing ran five times and gave the same result all five times, as expected, because the search doesn't call the model.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item id is the same from search to fit card | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card: 2–4 sentences, `$NN` and platform once each, unique opening | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search respects a $30 ceiling across five phrasings | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

The model-backed rows really were re-run: the 15 fit cards from criteria 1, 3 and 4 are all different texts. Criteria 4 and 5 turned out to be measuring the wrong thing, though. See Verdicts and Diagnoses below.

**Real output from one try**, pasted as text, naming the file and function that produced it:

**Criterion 1**, try 1. Trace from `trace.py::step`, called in `agent.py::run_agent`. Fit card from `tools.py::create_fit_card`.

```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
[3] select
      in:  10 results
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    first result
[4] compare_prices
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: below typical, median $21.5 across 14 comparable
[5] suggest_outfit
      in:  [lst_002] Y2K Baby Tee — Butterfly Print + 10 wardrobe items
      out: Outfit One: Pair the Y2K Baby Tee — Butterfly Print with your baggy straight-leg jeans, dark wash and vintage …
[6] create_fit_card
      in:  outfit (625 chars) + [lst_002] Y2K Baby Tee — Butterfly Print
      out: Scored this little butterfly baby tee on depop for just $18, and it’s officially my new favorite thing in my c…

fit_card: Scored this little butterfly baby tee on depop for just $18, and it’s officially my new favorite thing in my closet. I’ve been living in fitted tees paired with baggy denim for that ultimate nostalgic streetwear vibe, but it looks just as good dressed down with khaki trousers and chunky boots. Such a dreamy little vintage find!
```

**Criterion 2**, try 1. The branch in `agent.py::run_agent`; the message comes from `agent.py::_no_results_message`.

```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping

error: Nothing matched 'designer ballgown' in size XXS under $5. Try one of these: raise your price limit above $5; drop the size XXS; use fewer or more general words (e.g. 'dress' instead of the full phrase).
fit_card: None
```

**Criterion 3**, try 1. Ids read from the session returned by `agent.py::run_agent` and from its trace (`score_run.py::c3`).

```
[5] suggest_outfit
      in:  [lst_002] Y2K Baby Tee — Butterfly Print + 10 wardrobe items
[6] create_fit_card
      in:  outfit (669 chars) + [lst_002] Y2K Baby Tee — Butterfly Print

{'search_results[0]': 'lst_002', 'selected_item': 'lst_002', 'trace suggest_outfit': 'lst_002', 'trace create_fit_card': 'lst_002'}
```

**Criterion 4**, all five cards from `tools.py::create_fit_card`, because the uniqueness check compares them with each other. These are the scorer's lines (`score_run.py::c4_all`):

```
try 1: PASS  sentences=3 $18x1 depopx1 unique_opening=True opening='scored this little butterfly tee on depop for just $18 and i am so obs'
try 2: PASS  sentences=3 $18x1 depopx1 unique_opening=True opening='found this little y2k baby tee — butterfly print on depop for just $18'
try 3: PASS  sentences=3 $18x1 depopx1 unique_opening=True opening='score this dreamy little butterfly tee for just $18 on depop and i’m o'
try 4: PASS  sentences=2 $18x1 depopx1 unique_opening=True opening='scored this little butterfly tee on depop for just $18 and i’m so obse'
try 5: PASS  sentences=2 $18x1 depopx1 unique_opening=True opening='scored this adorable little butterfly baby tee on depop for just $18 a'
```

Try 2 in full: "Found this little Y2K Baby Tee — Butterfly Print on depop for just $18 and I am completely obsessed with the nostalgic pink and purple graphic. I love styling it with baggy denim for that ultimate 2000s streetwear vibe or dressing it down with structured trousers. It’s seriously the easiest way to add a little retro sweetness to any outfit."

**Criterion 5**, phrasing `below $30`, try 1. `agent.py::parse_query` followed by `search_listings` over MCP (`mcp_server.py::search_listings`).

```
[1] parse_query
      in:  graphic tee below $30
      out: {'description': 'graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'graphic tee', 'size': None, 'max_price': 30.0}
      out: 6 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Mesh Long-Sleeve Top — Black … +3 more

search_results prices: [('Y2K Baby Tee — Butterfly Print', 18.0), ('Graphic Tee — 2003 Tour Bootleg Style', 24.0), ('Mesh Long-Sleeve Top — Black', 15.0), ('Vintage Band Tee — Faded Grey', 19.0), ('Low-Rise Cargo Pants — Khaki', 27.0), ('Vintage Graphic Hoodie — Faded Black', 26.0)]
```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | A matching query completes all three tools | 4 of 5 | **MET (5/5)** | All five tries had no `error`, a non-empty `fit_card`, and `search_listings`, `suggest_outfit` and `create_fit_card` in the trace. |
| 2 | An impossible query stops before the second tool | 5 of 5 | **MET (5/5)** | All five traces end after `search_listings (via MCP)` with `[] (empty)` → `branch: empty, stopping`. `outfit_suggestion` and `fit_card` stayed None, and the message names the price, the size and the words. |
| 3 | Item id is the same from search to fit card | 5 of 5 | **MET (5/5)** | In every try, `search_results[0]`, `selected_item`, and the ids the trace shows going into `suggest_outfit` and `create_fit_card` were all `lst_002`. |
| 4 | Fit card: 2–4 sentences, `$NN` and platform once each, unique opening | 4 of 5 | As written: MET (5/5). **Revised: MISSED (3/5)** | (a) and (b) held on all five: 2–3 sentences, `$18` once, `depop` once. Under the original whole-sentence rule all five openings counted as unique. Under the revised five-word rule ([criteria.md](criteria.md) §4), tries 1 and 4 both open "scored this little butterfly tee", so both fail: FAIL, PASS, PASS, FAIL, PASS. |
| 5 | Search respects a $30 ceiling across five phrasings | 4 of 5 | As written: MET (5/5). **Revised: MET (5/5)** | Original (`graphic tee`): no result over $30 in any phrasing, but no `graphic tee` listing costs more than $30, so it couldn't have failed. Revised (`vintage jacket`, 6 of its 10 unfiltered matches over $30): every phrasing parsed `max_price=30.0` and returned 10 results with a top price of $30, in all five runs of each phrasing (output below). |

**Diagnoses**

**Criterion 4, the only real miss.** It happens in the **model's output**, and the cause is in the prompt in `tools.py::create_fit_card`. The prompt lists three things the caption must mention exactly once: the item, its price written as `$18`, and the platform. The model meets all three in the first sentence using one fixed frame: *"Scored this [little/cute/dreamy] butterfly tee on depop for just $18 and I'm obsessed…"*. Temperature 0.9 changes the adjective but not the frame. So whether two cards collide comes down to which adjective each one happens to draw, and in this run tries 1 and 4 both drew "little". The tool did what its spec says and the session passed the right item (criterion 3), so nothing upstream is wrong. The prompt gives the model a list of facts to fit in and no reason to open any other way.

**The pattern.** This is not one unlucky pair; it shows up in every fit card the run produced. The same query was used for criteria 1, 3 and 4, which gives 15 cards in total:
- **15 of 15** put both the price and the platform in sentence 1;
- **14 of 15** say "for just $18" or "for only $18";
- **10 of 15** open with "Score" or "Scored";
- three five-word openings appear twice each across the 15: "scored this little butterfly baby", "scored this cute little butterfly" and "scored this little butterfly tee".

Criteria 1 and 3 don't check the opening, so they passed anyway. It is one problem, in one place: the fit-card prompt sets the shape of the opening sentence.

Measured on the after-run, the fix should show as more varied first words and the price and platform moving out of sentence 1. Parts (a) and (b) must keep passing.

**Criterion 5, a broken measurement, not a miss.** With no listing over $30 among the `graphic tee` matches, the ceiling filter wasn't tested at all. The criterion was revised to a query that can fail (see [criteria.md](criteria.md) §5) and re-measured with the loop's own first two steps, `agent.py::parse_query` and then `search_listings` over MCP:

```
no ceiling: 10 results, 6 over $30, max $75
'vintage jacket under $30'                 parsed={'description': 'vintage jacket', 'size': None, 'max_price': 30.0} results=10 max=$30 over=[] -> PASS PASS PASS PASS PASS
'vintage jacket below $30'                 parsed={'description': 'vintage jacket', 'size': None, 'max_price': 30.0} results=10 max=$30 over=[] -> PASS PASS PASS PASS PASS
'vintage jacket less than 30 dollars'      parsed={'description': 'vintage jacket', 'size': None, 'max_price': 30.0} results=10 max=$30 over=[] -> PASS PASS PASS PASS PASS
'vintage jacket max $30'                   parsed={'description': 'vintage jacket', 'size': None, 'max_price': 30.0} results=10 max=$30 over=[] -> PASS PASS PASS PASS PASS
'vintage jacket $30 or less'               parsed={'description': 'vintage jacket', 'size': None, 'max_price': 30.0} results=10 max=$30 over=[] -> PASS PASS PASS PASS PASS
```

`scenarios.py` now uses these five queries, so the after-run measures the revised version. One thing this turned up, which the criterion allows: "under $30" returns a listing priced exactly $30, because the ceiling is inclusive for every phrasing.

**Were the other targets too low?** Partly, yes:
- **Criterion 1** allowed one failure "for a bad moment from the model service". Across 90 model calls there wasn't one, so 4 of 5 left room that wasn't needed.
- **Criterion 3** is the one I'd tighten. It compares `search_results[0]` against `selected_item`, and with this query that can't fail. The top result is in excellent condition, so the second branch (swap a fair-condition pick) never runs. Once that branch exists, `search_results[0]` is the wrong thing to compare: the selected item is *supposed* to differ from it when the swap fires. A tighter version would compare `selected_item["id"]` against the ids going into `suggest_outfit` and `create_fit_card`, and add a query whose top match is in fair condition, so the swap path is checked too.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path** — `python app.py ask 'vintage graphic tee under $30, size M' --trace`

```
[1] parse_query
      in:  vintage graphic tee under $30, size M
      out: {'description': 'vintage graphic tee', 'size': 'M', 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': 'M', 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Mesh Long-Sleeve Top — Black, 90s Silk Slip Dress — Floral, Midi Length … +7 more
[3] select
      in:  10 results
      out: Y2K Baby Tee — Butterfly Print ($18.0, depop)
      →    first result
[4] compare_prices
      in:  Y2K Baby Tee — Butterfly Print ($18.0, depop)
      out: below typical, median $21.5 across 14 comparable
[5] suggest_outfit
      in:  Y2K Baby Tee — Butterfly Print + 10 wardrobe items
      out: Outfit one: Pair the Y2K Baby Tee — Butterfly Print with your Baggy straight-leg jeans, dark wash. Layer the v…
[6] create_fit_card
      in:  outfit (592 chars) + Y2K Baby Tee — Butterfly Print
      out: scored this adorable little butterfly baby tee on depop for only $18 and I am so obsessed with how versatile i…
```

(This query had been run before, so both model calls were served from the build cache. The steps and their order are the same either way.)

**Empty search** — `python app.py ask 'sequined astronaut ballgown size XXS under $5' --trace`

```
[1] parse_query
      in:  sequined astronaut ballgown size XXS under $5
      out: {'description': 'sequined astronaut ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'sequined astronaut ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, stopping
```

The empty run stops after two steps and makes 0 model calls. The happy path runs all six steps.

**On the MCP move:** `search_listings` is registered on a FastMCP server in `mcp_server.py`, under the same name and with the same typed inputs as in the Tool Inventory (`description: str`, `size: str | None`, `max_price: float | None`). `agent.py::run_agent` now calls it through `mcp_client.call_tool("search_listings", {...})` instead of importing it from `tools.py`. Nothing behaved differently afterwards. I ran four queries both the direct way and through MCP and the returns were exactly equal (`==`). That included the no-match case, which still comes back as `[]` and not `None`, and listings with `brand: None`, where the null survived the JSON round trip. The only visible cost is speed: every call starts the server process, asks, and stops it again.

### Failure modes

Each failure was triggered on purpose, one at a time. The output below is what the agent said.

**1. Empty search** — `python app.py ask 'sequined astronaut ballgown size XXS under $5'`

```
  Nothing matched 'sequined astronaut ballgown' in size XXS under $5. Try one of these: raise your price limit above $5; drop the size XXS; use fewer or more general words (e.g. 'dress' instead of the full phrase).

0 model calls this session
```

Already handled by the branch in `run_agent`. It stops before any model call and names each thing the user could change. No change needed.

**2. Empty wardrobe** — `python app.py ask 'black combat boots under $60' --empty-wardrobe`

```
(running with an empty wardrobe)

  Found:    Oversized Flannel Shirt — Plaid Red/Black — $22.0 on thredUp (good)
  Price:    about typical — median $20 across 12 similar listings; cheapest similar: Mesh Long-Sleeve Top — Black at $15

  Outfit:   Buy it. Woolrich is vintage quality that lasts forever, and $22 is a steal for that heritage.

Outfit one: Throw it open over a fitted white ribbed tank top, paired with relaxed light-wash distressed jeans and chunky black combat boots. This leans into classic nineties grunge, balancing the heavy oversized flannel with fitted elements underneath.

Outfit two: Belt it at the waist like a mini shirt-dress with sheer black tights and knee-high leather riding boots. ...
```

No crash and no empty string. `suggest_outfit` gives general pairing advice instead of naming owned pieces. No change needed. The run did show two other problems, though, which are not failures of the empty-wardrobe handling: a search for "combat boots" picked a flannel shirt, because "black" was the only word that matched, and the outfit text opened with a buy/skip verdict ("Buy it.") that the prompt doesn't ask for.

**3. Model unavailable** — one character of `GEMINI_API_KEY` changed in `.env`, then a query not asked before: `python app.py ask 'cropped denim jacket for a fall picnic size M'`

Before the fix:

```
ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.
```

That came back in under a second, with no hang and no stack trace. But that was only luck: `app.py`'s last-resort `except Exception` in `main()` caught it. `run_agent` didn't handle the error at all. The session was thrown away, so the listing it had already found was never shown, and the process exited with code 1. Called from `run_eval.py` or `serve.py`, the same error would have counted as a crash or returned a 500.

The fix: `run_agent` now catches `ModelUnavailable` (and `MCPError`, in case the search server doesn't answer). It puts a message in `session["error"]`, the same field the empty search uses, and returns the session normally. After the fix:

```
[5] suggest_outfit
      →    failed: ModelUnavailable, stopping

  The model couldn't be reached during suggest_outfit, so there's no outfit or fit card this time. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. (The search itself worked: it found '90s Track Jacket — Navy/White Stripe' for $45 on poshmark.)
```

It names the step that broke, says what to do (check or replace the key), and keeps what did work. The run now exits with code 0. The key was put back afterwards and `python test.py` passes again.

---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:** one prompt, in `tools.py::create_fit_card`. I added one sentence and left the rest of the prompt as it was:

```diff
         f"exactly once each. {brand_rule} Be specific about the vibe. "
+        "Open the first sentence with something specific from how it's being "
+        "styled above or how wearing it feels, not with buying or finding it; "
+        "keep the price and the platform out of the first sentence. "
         "Return only the caption."
```

Nothing else changed between the two runs: same scenarios, same tools, same loop, cache off for both, `TEMPERATURE = 0.9`.

**Which failure it was meant to fix:** criterion 4 (revised), MISSED at 3/5. The diagnosis said the prompt's must-mention list (item, `$18`, platform) gets packed into one fixed opening, "Scored this … on depop for just $18". That frame appeared in 15 of 15 cards, so whether two openings collide came down to which adjective each card drew. The fix gives the first sentence a different job and moves the price and platform out of it.

### Run Log — After

`python run_eval.py --label after`: 90 model calls, no crashes. Full report: [results/run_2026-10-13_1856_after.md](results/run_2026-10-13_1856_after.md), raw sessions in the `.json` next to it. Scored with `python score_run.py results/run_2026-10-13_1856_after.json`, using the criteria as revised in [criteria.md](criteria.md). For criterion 5, Try *n* is phrasing *n* on `vintage jacket`.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. A matching query completes all three tools | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. An impossible query stops before the second tool | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Item id is the same from search to fit card | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card: 2–4 sentences, `$NN` and platform once each, unique first five words *(revised)* | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Search respects a $30 ceiling across five phrasings, on `vintage jacket` *(revised)* | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

**Before and after, side by side**, both scored with the revised criteria. Before uses the run above, re-scored with the five-word rule for criterion 4 and re-measured on `vintage jacket` for criterion 5.

| Criterion | Target | Before | After |
|---|---|---|---|
| 1. Matching query completes | 4 of 5 | PASS PASS PASS PASS PASS — MET (5/5) | PASS PASS PASS PASS PASS — MET (5/5) |
| 2. Impossible query stops early | 5 of 5 | PASS PASS PASS PASS PASS — MET (5/5) | PASS PASS PASS PASS PASS — MET (5/5) |
| 3. Item id carried through | 5 of 5 | PASS PASS PASS PASS PASS — MET (5/5) | PASS PASS PASS PASS PASS — MET (5/5) |
| 4. Fit card *(revised)* | 4 of 5 | FAIL PASS PASS FAIL PASS — **MISSED (3/5)** | PASS PASS PASS PASS PASS — **MET (5/5)** |
| 5. Price ceiling *(revised)* | 4 of 5 | PASS PASS PASS PASS PASS — MET (5/5) | PASS PASS PASS PASS PASS — MET (5/5) |

**Real output, criterion 4 after the change.** All five cards from `tools.py::create_fit_card`, scored by `score_run.py::c4_all`:

```
try 1: PASS  sentences=2 $18x1 depopx1 unique_opening=True opening='balancing that ultraloose denim with'
try 2: PASS  sentences=3 $18x1 depopx1 unique_opening=True opening='balancing this fitted little butterfly'
try 3: PASS  sentences=3 $18x1 depopx1 unique_opening=True opening='balancing a fitted silhouette with'
try 4: PASS  sentences=3 $18x1 depopx1 unique_opening=True opening='balancing this sweet little butterfly'
try 5: PASS  sentences=3 $18x1 depopx1 unique_opening=True opening='balancing this pastel butterfly tee'
```

Try 4 in full: "Balancing this sweet little butterfly tee with baggy dark wash denim and chunky sneakers gives me all the nostalgic streetwear vibes. I scored this gem on depop for just $18, and the fit is honestly perfection. It's quickly becoming my go-to piece for effortless daily outfits."

**Did it help, and how do I know:** It helped the criterion: 3/5 became 5/5, and the other four rows stayed at 5/5. But it moved the template rather than removing it, and the criterion is too weak to see that.

Across the 15 cards each run produced for the `vintage graphic tee` query (criteria 1, 3 and 4):

| | Before | After |
|---|---|---|
| Price and platform both in sentence 1 | 15 / 15 | 0 / 15 |
| Says "for just/only $18" | 14 / 15 | 15 / 15 |
| Most common first word | "Score"/"Scored", 10 / 15 | "Balancing", 9 / 15 |
| Five-word openings that repeat | 3 pairs | none |

The new prompt tells the model to open with "something specific from how it's being styled above". Every one of the 15 outfit suggestions, in both runs, contains the word "balances" (e.g. "The fitted baby tee balances the loose jeans"). In the after-run, 9 of the cards built from those suggestions open with "Balancing". So the model swapped one stock opening for another, and the purchase frame "for just $18" just moved to sentence 2.

The five-word rule passes these because "balancing this fitted little butterfly" and "balancing this sweet little butterfly" differ in their fourth word. Comparing the first two words instead would fail most of them. The measured improvement is real, but the problem underneath, a caption with a fixed shape, is still there one sentence later.

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
