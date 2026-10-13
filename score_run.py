"""Score a run_eval JSON dump against criteria.md, one line per try.

    python score_run.py results/run_<stamp>_before.json

Each check is the criterion exactly as written in criteria.md; the rule it
applies is in the function for that criterion.
"""
import json, re, sys
from collections import defaultdict

rows = json.load(open(sys.argv[1]))
by_crit = defaultdict(list)
for r in rows:
    by_crit[r["scenario"]["criterion"]].append(r)


def steps(trace):
    return re.findall(r"^\[\d+\] (.+)$", trace, re.M)


def c1(t):
    s, tr = t["session"], t["trace"]
    names = steps(tr)
    ok = (not t["crashed"] and not s.get("error") and bool((s.get("fit_card") or "").strip())
          and any(n.startswith("search_listings") for n in names)
          and "suggest_outfit" in names and "create_fit_card" in names and "failed" not in tr)
    return ok, f"error={s.get('error')!r:.60} card={len(s.get('fit_card') or '')}ch steps={names}"


def c2(t):
    s, tr = t["session"], t["trace"]
    err = s.get("error") or ""
    ok = (not t["crashed"] and bool(err) and s.get("outfit_suggestion") is None
          and s.get("fit_card") is None and "suggest_outfit" not in tr
          and all(w in err for w in ("price", "size", "words")))
    return ok, f"steps={steps(tr)} error={err!r:.80}"


def c3(t):
    s, tr = t["session"], t["trace"]
    if t["crashed"] or s.get("error"):
        return False, f"no full run: {t['crashed'] or s.get('error')!r:.80}"
    so = re.search(r"\] suggest_outfit\n\s+in:\s+\[(\w+)\]", tr)
    fc = re.search(r"\] create_fit_card\n\s+in:\s+.*?\[(\w+)\]", tr)
    ids = {"search_results[0]": s["search_results"][0]["id"], "selected_item": s["selected_item"]["id"],
           "trace suggest_outfit": so and so.group(1), "trace create_fit_card": fc and fc.group(1)}
    return len(set(ids.values())) == 1 and None not in ids.values(), str(ids)


def sentences(text):
    return len(re.findall(r"[.!?]+(?=\s|$)", text.strip()))


def first_sentence(text):
    return re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0].strip().lower()


def first_words(text, n=5):
    """Revised criterion 4: the opening is the first five words, case and
    punctuation ignored, so "I am" vs "I'm" later on can't make two openings
    count as different."""
    return " ".join(re.sub(r"[^\w\s$]", "", text.lower().replace("’", "")).split()[:n])


def c4_all(tries, revised=False):
    opening = first_words if revised else first_sentence
    firsts = [opening(t["session"].get("fit_card") or "") for t in tries]
    out = []
    for t, first in zip(tries, firsts):
        s = t["session"]
        card = s.get("fit_card") or ""
        if t["crashed"] or s.get("error") or not card:
            out.append((False, f"no card: {t['crashed'] or s.get('error')!r:.80}"))
            continue
        item = s["selected_item"]
        price = item["price"]
        p = f"{price:.0f}" if price == int(price) else f"{price:.2f}"
        n_price = len(re.findall(rf"\${re.escape(p)}(?:\.00?)?(?!\d)", card))
        n_plat = len(re.findall(rf"\b{re.escape(item['platform'])}\b", card, re.I))
        n_sent = sentences(card)
        unique = firsts.count(first) == 1
        ok = 2 <= n_sent <= 4 and n_price == 1 and n_plat == 1 and unique
        out.append((ok, f"sentences={n_sent} ${p}x{n_price} {item['platform']}x{n_plat} "
                        f"unique_opening={unique} opening={first[:70]!r}"))
    return out


def c5(t):
    s = t["session"]
    res = s.get("search_results") or []
    over = [(r["title"], r["price"]) for r in res if r["price"] > 30]
    return (not t["crashed"] and not over,
            f"parsed max_price={s.get('parsed', {}).get('max_price')} results={len(res)} "
            f"max=${max((r['price'] for r in res), default=0)} over={over}")


for crit in sorted(k for k in by_crit if k):
    print(f"\n===== Criterion {crit}")
    for r in by_crit[crit]:
        print(f"-- {r['scenario']['name']}  [{r['scenario']['query']}]")
        tries = r["tries"]
        if crit == 4:
            original = c4_all(tries)
            print("   original (whole first sentence):", " | ".join("PASS" if ok else "FAIL" for ok, _ in original))
            print("   revised in unit 4 (first five words):")
        results = c4_all(tries, revised=True) if crit == 4 else [{1: c1, 2: c2, 3: c3, 5: c5}[crit](t) for t in tries]
        for i, (ok, why) in enumerate(results, 1):
            print(f"   try {i}: {'PASS' if ok else 'FAIL'}  {why}")
        print("   row:", " | ".join("PASS" if ok else "FAIL" for ok, _ in results))

for r in by_crit.get(None, []):
    print(f"\n===== diagnostic: {r['scenario']['name']}")
    for i, t in enumerate(r["tries"], 1):
        s = t["session"]
        print(f"   try {i}: crashed={t['crashed']} error={s.get('error')!r:.60} "
              f"outfit={len(s.get('outfit_suggestion') or '')}ch card={len(s.get('fit_card') or '')}ch")
