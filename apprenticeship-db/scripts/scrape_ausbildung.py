"""Collect German dual-study (duales Studium) listings from ausbildung.de for target employers.

Usage: python3 scrape_ausbildung.py OUT_JSON

For each target employer:
  1. find its ausbildung.de company slug (search by name -> open one of its listings -> /unternehmen/<slug>/ link)
  2. page through /ajax/job_postings_per_corporation_search/<slug>/ until no new listings appear
  3. keep dual-study / Bachelor engineering listings and read each one's JobPosting JSON-LD
Saves progress to OUT_JSON as it goes.
"""
import json, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (apprenticeship-research)", "X-Requested-With": "XMLHttpRequest"}
BASE = "https://www.ausbildung.de"

# search term -> sector
COMPANIES = {
    "Infineon": "semiconductor", "Carl Zeiss": "semiconductor", "Trumpf": "semiconductor",
    "GlobalFoundries": "semiconductor", "X-FAB": "semiconductor", "Robert Bosch": "automotive",
    "BMW": "automotive", "Mercedes-Benz": "automotive", "Porsche": "automotive", "Volkswagen": "automotive",
    "Audi": "automotive", "ZF": "automotive", "Continental": "automotive", "Schaeffler": "automotive",
    "MAN Truck": "automotive", "Daimler Truck": "automotive", "BorgWarner": "automotive",
    "Siemens Energy": "energy_generation", "Siemens": "other", "E.ON": "energy_networks", "RWE": "energy_generation",
    "EnBW": "energy_generation", "Vattenfall": "energy_generation", "Uniper": "energy_generation",
    "TenneT": "energy_networks", "Amprion": "energy_networks", "Westnetz": "energy_networks",
    "Nordex": "energy_renewables", "Enercon": "energy_renewables", "Maschinenfabrik Reinhausen": "energy_networks",
    "Deutsche Bahn": "rail", "Alstom": "rail", "Knorr-Bremse": "rail", "Stadler": "rail",
    "Airbus": "aerospace_defence", "MTU Aero Engines": "aerospace_defence", "Rheinmetall": "aerospace_defence",
    "Liebherr": "off_highway", "Claas": "off_highway", "Bosch Rexroth": "off_highway",
    "Viessmann": "mep", "Vaillant": "mep", "Stiebel Eltron": "mep", "ENGIE Deutschland": "mep",
    "SPIE": "mep", "Caverion": "mep", "Drees & Sommer": "mep",
}
ENGINEERING = re.compile(r"Maschinenbau|Mechatronik|Elektrotechnik|Energietechnik|Versorgungstechnik|Gebaeude|"
                         r"Fahrzeugtechnik|Automatisierung|Produktionstechnik|Fertigungstechnik|Verfahrenstechnik|"
                         r"Wirtschaftsingenieur|Engineering|Ingenieur|Mikrotechnik|Halbleiter|Luft|Mobilitaet", re.I)
STUDY = re.compile(r"duales?[- ]studium|dualer[- ]studiengang|b-eng|bachelor|praxisintegriert|studium", re.I)
MAX_PAGES = 40


def get(url, retries=2):
    for a in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(1 + a)
    return ""


def jobposting(html):
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            d = json.loads(m)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") == "JobPosting":
            return d
    return None


def norm(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def company_slug(name):
    """Search by name, open the first listing whose slug names the company, read its /unternehmen/<slug>/ link."""
    page = get(f"{BASE}/suche/?" + urllib.parse.urlencode({"search": name}))
    key = norm(name) if name in ("ZF", "MAN Truck", "E.ON", "SPIE", "RWE") else norm(name).split("-")[0]
    for href in dict.fromkeys(re.findall(r'href="(/stellen/[^"]+)"', page)):
        bei = href.split("-bei-")[-1] if "-bei-" in href else ""
        if bei.startswith(key) or f"-{key}-" in f"-{bei}":
            slugs = [x for x in re.findall(r'/unternehmen/([a-z0-9-]+)/', get(BASE + href)) if x != "alle"]
            if slugs:
                return slugs[0]
    return None


def company_listings(slug):
    seen = []
    for p in range(1, MAX_PAGES + 1):
        q = urllib.parse.urlencode({"form_job_postings_per_corporation_search[page]": p})
        html = get(f"{BASE}/ajax/job_postings_per_corporation_search/{slug}/?{q}")
        new = [h for h in dict.fromkeys(re.findall(r'(/stellen/[a-z0-9-]+/)', html)) if h not in seen]
        if not new:
            break
        seen += new
        time.sleep(0.2)
    return seen


def to_record(href, d, comp):
    addr = (d.get("jobLocation") or {}).get("address", {})
    sal = d.get("baseSalary") or {}
    desc = " ".join(re.sub(r"<[^>]+>", " ", d.get("description", "")).split())
    hs = re.search(r"((?:Duale Hochschule|DHBW|Technische Hochschule|Hochschule|Fachhochschule|TH|Universität)"
                   r"(?: [A-ZÄÖÜ][\w\-äöüß]+){1,3})", desc)
    start = re.search(r"(\d{1,2}\.\d{1,2}\.20\d\d)", (d.get("title") or "") + " " + desc)
    return {
        "url": BASE + href, "title": d.get("title"), "employer": (d.get("hiringOrganization") or {}).get("name"),
        "search_company": comp, "sector_hint": COMPANIES[comp], "city": addr.get("addressLocality"),
        "state": addr.get("addressRegion"), "postcode": addr.get("postalCode"),
        "posted": (d.get("datePosted") or "")[:10], "valid_through": (d.get("validThrough") or "")[:10],
        "education": d.get("educationRequirements"),
        "salary_min_month": sal.get("minValue"), "salary_max_month": sal.get("maxValue"), "currency": sal.get("currency"),
        "start_hint": start.group(1) if start else None, "hochschule": hs.group(1) if hs else None,
        "description": desc[:1200],
    }


def main(out):
    recs = []
    for comp in COMPANIES:
        slug = company_slug(comp)
        if not slug:
            print(comp, "no company page found", flush=True)
            continue
        hrefs = company_listings(slug)
        keep = [h for h in hrefs if STUDY.search(h) and ENGINEERING.search(h) and "2026" not in h.replace("2026-2027", "")]
        n0 = len(recs)
        for h in keep:
            d = jobposting(get(BASE + h))
            if d:
                recs.append(to_record(h, d, comp))
            time.sleep(0.2)
        print(comp, f"{slug}: {len(hrefs)} listings, {len(recs) - n0} engineering dual-study", flush=True)
        json.dump(recs, open(out, "w"), indent=1, ensure_ascii=False)
    print("done", len(recs), "records")


if __name__ == "__main__":
    main(sys.argv[1])
