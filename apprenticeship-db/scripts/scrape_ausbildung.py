"""Collect German dual-study (duales Studium) listings from ausbildung.de for target employers.

Usage: python3 scrape_ausbildung.py OUT_JSON
Searches "<programme> <company>" for each target company, keeps dual-study / Bachelor
listings, then reads the JobPosting JSON-LD on each listing page.
"""
import json, re, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (apprenticeship-research)"}
BASE = "https://www.ausbildung.de"

# company search term -> (sector, canonical employer name substring to match in JSON-LD)
COMPANIES = {
    "Infineon": "semiconductor", "Bosch": "automotive", "Siemens Energy": "energy_generation",
    "Siemens": "other", "ZF": "automotive", "Continental": "automotive", "BMW": "automotive",
    "Mercedes-Benz": "automotive", "Porsche": "automotive", "Volkswagen": "automotive",
    "Audi": "automotive", "Schaeffler": "automotive", "MAN": "automotive", "Daimler Truck": "automotive",
    "E.ON": "energy_networks", "RWE": "energy_generation", "EnBW": "energy_generation",
    "Vattenfall": "energy_generation", "Uniper": "energy_generation", "TenneT": "energy_networks",
    "Amprion": "energy_networks", "50Hertz": "energy_networks", "TransnetBW": "energy_networks",
    "Siemens Gamesa": "energy_renewables", "Nordex": "energy_renewables", "Enercon": "energy_renewables",
    "Carl Zeiss": "semiconductor", "Trumpf": "semiconductor", "GlobalFoundries": "semiconductor",
    "X-FAB": "semiconductor", "Bosch Rexroth": "off_highway", "Liebherr": "off_highway",
    "Claas": "off_highway", "Deutsche Bahn": "rail", "Alstom": "rail", "Stadler": "rail",
    "Knorr-Bremse": "rail", "Airbus": "aerospace_defence", "MTU Aero Engines": "aerospace_defence",
    "Viessmann": "mep", "Vaillant": "mep", "Stiebel Eltron": "mep", "Caverion": "mep",
    "SPIE": "mep", "Imtech": "mep", "Goldbeck": "mep", "Drees & Sommer": "mep",
}
PROGRAMMES = ["Duales Studium Maschinenbau", "Duales Studium Mechatronik", "Duales Studium Elektrotechnik",
              "Duales Studium Versorgungstechnik"]
KEEP = re.compile(r"duales-studium|dualer-studiengang|b-eng|bachelor|praxisintegriert|studium", re.I)
SKIP_YEAR = re.compile(r"2026(?!-2027)")


def get(url):
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2 ** a)
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


def main(out):
    links = {}
    for comp in COMPANIES:
        for prog in PROGRAMMES:
            q = urllib.parse.urlencode({"search": f"{prog} {comp}"})
            for href in set(re.findall(r'href="(/stellen/[^"]+)"', get(f"{BASE}/suche/?{q}"))):
                if KEEP.search(href) and not SKIP_YEAR.search(href):
                    links.setdefault(href, comp)
            time.sleep(0.3)
        print(comp, len(links), flush=True)
    recs = []
    for href, comp in links.items():
        d = jobposting(get(BASE + href))
        time.sleep(0.3)
        if not d:
            continue
        org = (d.get("hiringOrganization") or {}).get("name", "")
        # keep only listings actually posted by (a unit of) the searched company
        if comp.lower().split()[0] not in org.lower():
            continue
        addr = (d.get("jobLocation") or {}).get("address", {})
        sal = d.get("baseSalary") or {}
        desc = re.sub(r"<[^>]+>", " ", d.get("description", ""))
        desc = " ".join(desc.split())
        recs.append({
            "url": BASE + href, "title": d.get("title"), "employer": org, "search_company": comp,
            "sector_hint": COMPANIES[comp], "city": addr.get("addressLocality"),
            "state": addr.get("addressRegion"), "postcode": addr.get("postalCode"),
            "posted": (d.get("datePosted") or "")[:10], "valid_through": (d.get("validThrough") or "")[:10],
            "education": d.get("educationRequirements"),
            "salary_min_month": sal.get("minValue"), "salary_max_month": sal.get("maxValue"),
            "currency": sal.get("currency"), "industry": d.get("industry"),
            "start_hint": (re.search(r"(?:ab|zum|Start|Beginn)[^.]{0,30}?(\d{1,2}\.\d{1,2}\.20\d\d|20\d\d)", desc) or [None, None])[1],
            "hochschule": (re.search(r"((?:Duale )?Hochschule [A-ZÄÖÜ][\w\-]+(?: [A-ZÄÖÜ][\w\-]+)?|DHBW [A-ZÄÖÜ]\w+|TH [A-ZÄÖÜ]\w+|Fachhochschule [A-ZÄÖÜ][\w\-]+|Technische Hochschule [A-ZÄÖÜ]\w+|Universität [A-ZÄÖÜ]\w+)", desc) or [None, None])[1],
            "description": desc[:1200],
        })
    json.dump(recs, open(out, "w"), indent=1, ensure_ascii=False)
    print(len(links), "links;", len(recs), "kept")


if __name__ == "__main__":
    main(sys.argv[1])
