"""Look up coordinates for every UK programme location (postcodes.io) and cache them.

Usage: python3 scripts/geocode.py
Reads apprenticeships.db, writes data/sources/geocode_cache.json  {query: [lat, lon, label] | null}
(workplace locations only; safe to commit). If personal/my_profile.json exists, the home postcode is looked up
and saved to personal/home_geocode.json, which is git-ignored and never committed.
build_db.py --personal then estimates commute times from home (no network needed).
"""
import json, re, sqlite3, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "sources" / "geocode_cache.json"


# Site postcodes for locations whose town names are ambiguous or that are rural sites
OVERRIDE_PC = {
    "Broughton, Flintshire": "CH4 0DR", "Grove, Oxfordshire": "OX12 0DQ", "Newport, South Wales": "NP10 8YJ",
    "Wotton-under-Edge": "GL12 8JR", "Hinkley Point": "TA5 1UD", "Bridgwater": "TA6 4AA", "Gravity, near Bridgwater": "TA6 4FD",
    "Oakenshaw": "BD12 7EZ", "Miskin": "CF72 8YX", "Severn Beach": "BS35 4GG", "Sedgefield": "TS21 3FF",
    "Culham": "OX14 3DB", "Capenhurst": "CH1 6ER", "Rocester": "ST14 5JP", "Gaydon": "CV35 0RR", "Malmesbury": "SN16 0RP",
    "Dunton": "SS15 6EE", "Raynesway": "DE21 7BE", "Clevedon": "BS21 6TH", "Sellafield": "CA20 1PG", "Halewood": "L24 9BJ",
    "Barrow-in-Furness": "LA14 1AF", "Ellesmere Port": "CH65 1AL", "Yeovil": "BA20 2YB", "Crewe": "CW1 3PL",
    "Raheen, Limerick": None,
}


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return json.load(r)
    except Exception:
        return None


def lookup_postcode(pc):
    d = get("https://api.postcodes.io/postcodes/" + urllib.parse.quote(pc.replace(" ", "")))
    if d and d.get("result"):
        r = d["result"]
        return [r["latitude"], r["longitude"], r.get("admin_district")]
    return None


def lookup_place(name):
    d = get("https://api.postcodes.io/places?" + urllib.parse.urlencode({"q": name, "limit": 5}))
    res = (d or {}).get("result") or []
    # prefer towns/cities over hamlets or roads with the same name
    rank = {"City": 0, "Town": 1, "Suburban Area": 2, "Village": 3, "Other Settlement": 4, "Hamlet": 5}
    res.sort(key=lambda r: rank.get(r.get("local_type"), 9))
    if res:
        r = res[0]
        return [r["latitude"], r["longitude"], f"{r['name_1']} ({r.get('local_type')})"]
    return None


def place_candidates(loc):
    """'Raynesway, Derby' -> ['Derby', 'Raynesway'];  'Crawley (RH10 9HA)' handled by postcode."""
    loc = re.sub(r"\(.*?\)", "", loc or "")
    parts = re.split(r"[/,;]| - | or |\band\b", loc)
    parts = [p.strip(" .") for p in parts if p.strip(" .")]
    skip = re.compile(r"various|uk|england|multiple|nationwide|site|plant|hq|headquarters|campus|centre|world", re.I)
    clean = [re.sub(r"^(MINI Plant|Plant|Werk)\s+", "", p) for p in parts if not skip.fullmatch(p.split()[0] if p else "")]
    counties = re.compile(r"^(Cheshire|Wiltshire|Somerset|Devon|Essex|Cumbria|Oxfordshire|Gloucestershire|Flintshire|"
                          r"North Yorkshire|County Durham|South Wales|North Wales|Northants|Northamptonshire|England|Scotland)$", re.I)
    return list(dict.fromkeys(p for p in clean if not counties.match(p)))


def home(pc):
    return lookup_postcode(pc)


def main():
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    con = sqlite3.connect(ROOT / "apprenticeships.db")
    rows = con.execute("SELECT DISTINCT postcode, work_location FROM programmes WHERE country='GB'").fetchall()
    prof_p = ROOT / "personal" / "my_profile.json"
    profile = json.loads(prof_p.read_text()) if prof_p.exists() else {}
    if profile.get("home_postcode"):
        home = lookup_postcode(profile["home_postcode"])
        (ROOT / "personal" / "home_geocode.json").write_text(json.dumps(home))
        cache.pop("pc:" + profile["home_postcode"].upper().replace(" ", ""), None)  # keep home out of the shared cache
    for pc, loc in rows:
        if pc:
            key = "pc:" + pc.upper().replace(" ", "")
            if key not in cache:
                cache[key] = lookup_postcode(pc)
                time.sleep(0.1)
            if cache[key]:
                continue
        key = "loc:" + (loc or "")
        if key in cache:
            continue
        ov = next((pc for k, pc in OVERRIDE_PC.items() if k.lower() in (loc or "").lower() and pc), None)
        if ov:
            hit = lookup_postcode(ov)
            cache[key] = [hit + ["override " + ov]] if hit else None
            continue
        hits = []  # every candidate town; build_db picks the one nearest home
        for cand in place_candidates(loc):
            h = lookup_place(cand)
            time.sleep(0.1)
            if h:
                hits.append(h + [cand])
        cache[key] = hits or None
    CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True))
    print(len(cache), "cached;", sum(1 for v in cache.values() if v is None), "not found")
    for k, v in sorted(cache.items()):
        if v is None:
            print("  not found:", k)


if __name__ == "__main__":
    main()
