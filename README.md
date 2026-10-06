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

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

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
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



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
