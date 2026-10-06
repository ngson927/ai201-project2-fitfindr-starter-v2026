# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
The query has to pass through my regex parser and two model calls before a fit
card exists, and any one of those can fail on a single run: a reply that comes
back blank, a rate-limit retry that gives up, or a parse that drops a keyword.
5 of 5 would assume the model service never has a bad moment, which I can't
control from my code.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
Nothing on this path is random. `search_listings` doesn't call the model, the
cheapest listing in the data is $12, so "under $5" returns `[]` every time, and
the branch is an `if` in `agent.py::run_agent` that runs before any model call.
If this misses even once, the branch is broken, so anything below 5 of 5 would
be accepting a bug.

---

## 3. Something about state

<!-- YOU WRITE THIS ONE.

     How would you know that the item your search found is the same item the
     next tool received? Name something countable or observable.

     This is the criterion people find hardest, because state failure doesn't
     look like state failure — it looks like a tool problem. Something that
     compares session["selected_item"] against what actually reached
     suggest_outfit is the shape you're after. -->

For the query `vintage graphic tee under $30`, the listing `id` that the trace
shows going into `suggest_outfit`, the `id` going into `create_fit_card`,
`session["selected_item"]["id"]`, and `session["search_results"][0]["id"]` are
all the same value — in 5 of 5 tries.

**Why this target:**
Passing the item along is plain Python: no model sits between the search and
the next two tools, so there is no randomness that could change which item
moves on. A single mismatch would mean my loop reads the wrong field or
overwrites the session, which is a bug, not bad luck.

---

## 4. Something about the fit card

<!-- YOU WRITE THIS ONE.

     The fit card calls a model, so the same input can produce different words
     each time. That's not a bug — it's the nature of the tool. So what would
     make it acceptable?

     Think about what you'd actually be unhappy to see. A caption that never
     mentions the price? Two different items producing the same opening
     sentence? A card longer than a caption anyone would post? Any of those can
     be turned into a number. -->

For the query `vintage graphic tee under $30`, run 5 times with the cache off,
each fit card (a) has 2 to 4 sentences, counting sentences as text ending in
`.`, `!` or `?`; (b) contains the selected item's price written as `$NN` and
its platform name, case-insensitive, each exactly once; and (c) has a first
sentence that no other card in the five starts with. A card passes only if all
three hold, and at least 4 of 5 cards pass.

**Why this target:**
The card is written by the model at temperature 0.9, and my prompt only asks
for these things; nothing in my code enforces them. At that temperature the
model will sometimes repeat the price in a closing line or run to a fifth
sentence, and two of five cards could open the same way by chance. 5 of 5
would mean expecting a random process never to slip, and
lower than 4 would mean my prompt isn't really doing its job.

---

## 5. The search respects the price ceiling, however it's phrased

<!-- YOU WRITE THIS ONE TOO.

     Pick something you actually care about getting right. Speed, the empty
     wardrobe path, what happens when the model can't be reached, whether the
     search respects a price ceiling — anything, as long as it names a number
     or an observable outcome. -->
Across five phrasings of the same limit — `graphic tee under $30`,
`graphic tee below $30`, `graphic tee less than 30 dollars`,
`graphic tee max $30`, and `graphic tee $30 or less` — every listing in
`session["search_results"]` has a `price` of 30 or less, in at least 4 of the
5 phrasings.

**Why this target:**
The price filter in `search_listings` is exact, but it only works if my regex
parser pulls `max_price` out of the query first. If a phrasing slips past the
regex, `max_price` stays None, the search runs with no ceiling, and listings up
to $75 come back with no warning. I expect to cover the common forms but not
every way a person might say it, so 4 of 5 rather than 5 of 5.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
