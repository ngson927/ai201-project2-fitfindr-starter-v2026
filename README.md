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

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. A price pattern catches `under/below/less than/max/up to $N` and `$N or less`; a size pattern catches `size X` / `in size X`. Each match is cut out of the text, filler words (`looking`, `for`, `a`, …) are dropped, and what's left is the description.

**What moves through the session:** `query` → `parsed` (description, size, max_price) → `search_results` → [branch: empty sets `error` and stops] → `selected_item` (first result) → `outfit_suggestion` → `fit_card`. Each step reads its inputs back out of the session, not from a local variable. The loop is a `while` that picks `next_step` from what the last step left in the session, calling `trace.check_iterations` on every pass.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30'

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

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
