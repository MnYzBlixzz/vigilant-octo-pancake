"""Scrape GOV.UK Find an Apprenticeship search results + vacancy pages.

Usage: python3 scrape_faa.py OUT_DIR
Writes OUT_DIR/faa_list.json (search cards) and OUT_DIR/vac/<ref>.html (detail pages).
"""
import html, json, os, re, sys, time, urllib.request, urllib.parse

BASE = "https://www.findapprenticeship.service.gov.uk"
UA = {"User-Agent": "Mozilla/5.0 (apprenticeship-research)"}
# (routeIds, levelIds) combinations to sweep
QUERIES = [
    {"routeIds": ["9"], "levelIds": ["4", "5", "6", "7"]},   # Engineering & manufacturing
    {"routeIds": ["5"], "levelIds": ["4", "5", "6", "7"]},   # Construction & building (MEP)
    {"routeIds": ["15"], "levelIds": ["4", "5", "6", "7"]},  # Transport (rail/vehicle)
    {"searchTerm": "engineer", "levelIds": ["4", "5", "6", "7"]},   # catches other routes
    {"searchTerm": "engineering", "levelIds": ["4", "5", "6", "7"]},
    {"searchTerm": "mechanical", "levelIds": ["3", "4", "5", "6", "7"]},
]

def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa
            time.sleep(2 ** attempt)
    raise RuntimeError(url)

def text(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).split() and " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())

def parse_cards(page):
    out = []
    for li in re.findall(r'<li class="das-search-results__list-item.*?</li>', page, re.S):
        m = re.search(r'href="/apprenticeship/(VAC\d+)".*?vacancy-title">(.*?)</span>', li, re.S)
        if not m:
            continue
        ps = [text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", li, re.S)]
        card = {"ref": m.group(1), "title": text(m.group(2)), "employer": ps[0] if ps else ""}
        for p in ps[1:]:
            for key, label in [("start", "Start date"), ("course", "Training course"), ("wage", "Wage")]:
                if p.startswith(label):
                    card[key] = p[len(label):].strip()
            if p.startswith("Closes"):
                card["closes"] = p
            elif p.startswith("Posted"):
                card["posted"] = p
            elif "location" not in card and not any(p.startswith(x) for x in ("Start", "Training", "Wage", "Closes", "Posted")):
                card["location"] = p
        out.append(card)
    return out

def expand(queries):
    """The site seems to honour only one levelIds value reliably, so query each level separately."""
    for q in queries:
        for lvl in q["levelIds"]:
            yield {**q, "levelIds": [lvl]}

def main(out):
    os.makedirs(f"{out}/vac", exist_ok=True)
    cards = {}
    for q in expand(QUERIES):
        n = 1
        while True:
            qs = urllib.parse.urlencode({**q, "pageNumber": n}, doseq=True)
            page = get(f"{BASE}/apprenticeships?{qs}")
            got = parse_cards(page)
            if not got:
                break
            for c in got:
                c["query"] = qs.split("&pageNumber")[0]
                cards.setdefault(c["ref"], c)
            n += 1
            time.sleep(0.5)
        print(q, "pages", n - 1, "total cards", len(cards), flush=True)
    json.dump(list(cards.values()), open(f"{out}/faa_list.json", "w"), indent=1)
    for i, ref in enumerate(cards):
        p = f"{out}/vac/{ref}.html"
        if not os.path.exists(p):
            open(p, "w").write(get(f"{BASE}/apprenticeship/{ref}"))
            time.sleep(0.4)
    print("details fetched", len(cards))

if __name__ == "__main__":
    main(sys.argv[1])
