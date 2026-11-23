"""Build the apprenticeship database from the collected sources.

Inputs (all under apprenticeship-db/data/):
  sources/faa_vacancies.json   parsed GOV.UK Find an Apprenticeship vacancies (scrape_faa.py + parse_faa.py)
  sources/ausbildung_de.json   German dual-study listings (scrape_ausbildung.py)
  research/manual.jsonl        hand-researched schemes (employer sites, Gradcracker, Higherin, news)

Outputs (public, safe to commit; no personal data):
  data/employers.csv, data/programmes.csv   (the database as spreadsheets)
  apprenticeships.db                         (SQLite, built from schema/schema.sql)

With --personal, the student's profile (personal/my_profile.json: grades, home postcode) is applied
(grade_fit, commute_minutes, relocation_required) and the outputs go to the git-ignored personal/ folder:
  personal/apprenticeships.db, personal/programmes.csv, personal/employers.csv

Usage: python3 scripts/build_db.py [--personal] [--verified-on YYYY-MM-DD]
"""
import csv, json, re, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PERSONAL = ROOT / "personal"          # git-ignored: profile + personalised outputs
PERSONAL_BUILD = "--personal" in sys.argv
VERIFIED_ON = sys.argv[sys.argv.index("--verified-on") + 1] if "--verified-on" in sys.argv else "2026-11-12"
EUR_TO_GBP = 0.85  # approximate rate used for comparing pay; see docs/data-sources.md

TARGET_SECTORS = {"semiconductor", "energy_generation", "energy_nuclear", "energy_fusion", "energy_networks",
                  "energy_renewables", "energy_hydrogen", "mep", "automotive", "motorsport", "rail", "off_highway"}
MECH_DISCIPLINES = {"mechanical", "mechatronics", "manufacturing", "design", "building_services", "nuclear",
                    "process_chemical", "maintenance", "general_engineering"}

# Disciplines that count as "core" whatever the employer's sector (e.g. building services at AWE = MEP work)
CORE_ANYWHERE = {"building_services", "nuclear"}


def classify(sector, disc, lvl):
    if lvl <= 3:
        return "backup"
    if (sector in TARGET_SECTORS and disc in MECH_DISCIPLINES) or disc in CORE_ANYWHERE:
        return "core"
    return "related"


# ----------------------------------------------------------------------------- helpers
UCAS = {"A*": 56, "A": 48, "B": 40, "C": 32, "D": 24, "E": 16}


def ucas_from_grades(s):
    """'BBB' -> 120, 'ABB' -> 128, 'A*AA' -> 152."""
    toks = re.findall(r"A\*|[A-E]", s)
    return sum(UCAS[t] for t in toks) if 2 <= len(toks) <= 4 else None


def parse_alevels(text):
    """Return (min_ucas, min_maths_grade, min_physics_grade) from free-text A-level requirements."""
    if not text:
        return None, None, None
    t = text.replace("A-C", "").replace("A* - C", "C").replace("A*-C", "C")
    ucas = None
    m = re.search(r"(\d{2,3})\s*UCAS", t)
    if m:
        ucas = int(m.group(1))
    else:
        g = re.search(r"\b((?:A\*|[A-E]){2,4})\b", t)
        if g and not re.fullmatch(r"[A-E]", g.group(1)):
            ucas = ucas_from_grades(g.group(1))

    order = ["A*", "A", "B", "C", "D", "E"]

    def subj(name):
        # "B in Maths", "Maths (grade C)", "Maths (grade A/B)" -> lowest acceptable letter
        for pat in (rf"\b([A-E]\*?) in {name}", rf"{name}[^()]{{0,40}}\(grade ([A-E]\*?(?:/[A-E])?)"):
            m = re.search(pat, t, re.I)
            if m:
                return m.group(1).upper().split("/")[-1]
        return None
    maths = subj("Math\\w*")
    physics = subj("Physics")
    # A single overall grade string ("Maths plus 2 others (grade BBB)") sets the floor for Maths too
    overall = re.search(r"\b((?:A\*|[A-E]){2,4})\b", t)
    if maths is None and overall and re.search(r"math", t, re.I):
        maths = max(re.findall(r"A\*|[A-E]", overall.group(1)), key=order.index)
    return ucas, maths, physics


def months(s):
    if not s:
        return None
    y = re.search(r"(\d+)\s*year", s)
    mo = re.search(r"(\d+)\s*month", s)
    total = (int(y.group(1)) * 12 if y else 0) + (int(mo.group(1)) if mo else 0)
    return total or None


# UK postcode area -> region (areas present in the data plus common neighbours)
PC_REGION = {
    "north_east": "NE SR DH DL TS",
    "north_west": "M WA WN BL OL SK CW CH L PR FY LA BB CA CW",
    "yorkshire_humber": "YO HU LS BD HX HD WF S DN HG",
    "east_midlands": "DE NG LE LN NN",
    "west_midlands": "B CV WS WV DY ST TF WR HR",
    "east_of_england": "CB CO CM IP NR PE SG AL LU EN SS",
    "london": "E EC N NW SE SW W WC BR CR DA HA IG KT RM SM TW UB",
    "south_east": "RG OX HP MK SL GU RH BN TN ME CT PO SO",
    "south_west": "BS BA SN GL TA EX PL TQ TR DT BH SP",
    "wales": "CF NP SA LD LL SY",
    "scotland": "AB DD EH FK G KA KY PA PH IV ML",
    "northern_ireland": "BT",
}
PC_MAP = {a: r for r, areas in PC_REGION.items() for a in areas.split()}


def region_from_postcode(pc):
    if not pc:
        return None
    area = re.match(r"[A-Z]{1,2}", pc.upper())
    return PC_MAP.get(area.group(0)) if area else None


REGION_WORDS = [("yorkshire", "yorkshire_humber"), ("humber", "yorkshire_humber"), ("north west", "north_west"),
                ("north east", "north_east"), ("east midlands", "east_midlands"), ("west midlands", "west_midlands"),
                ("london", "london"), ("wales", "wales"), ("scotland", "scotland"), ("minworth", "west_midlands")]


def region_from_text(*texts):
    t = " ".join(x for x in texts if x).lower()
    for w, r in REGION_WORDS:
        if w in t:
            return r
    return None


# ----------------------------------------------------------------------------- GOV.UK FAA
FAA_EXCLUDE_COURSE = re.compile(
    r"Civil engineer|surveyor|surveying|site supervisor|site management|Brewer|Digital and technology|Machine learning|"
    r"Data analyst|DevOps|Network engineer|Vehicle damage|Business admin|Broadcast|Asset manager|Facilities manager|"
    r"Project controls|Supply chain|Artificial intelligence|Mineral products|Manufacturing manager", re.I)
FAA_EXCLUDE_TITLE = re.compile(r"Software", re.I)

COURSE_DISCIPLINE = [
    ("Electro-mechanical", "mechatronics"), ("Manufacturing engineer", "manufacturing"),
    ("Product design", "design"), ("Building services", "building_services"), ("Control systems", "control_automation"),
    ("process and plant", "process_chemical"), ("Nuclear", "nuclear"), ("Electrical and electronic", "electrical_electronic"),
    ("Embedded electronic", "electrical_electronic"), ("Engineering manufacturing technician", "manufacturing"),
    ("Rail engineering", "systems"), ("Automation and controls", "control_automation"),
    ("Maritime mechanical", "mechanical"), ("Heritage engineering", "mechanical"),
    ("maintenance technician", "maintenance"), ("support technician", "maintenance"),
]

FAA_EMPLOYERS = {  # FAA employer name (upper) prefix -> (display name, sector)
    "THALES": ("Thales UK", "aerospace_defence"),
    "DEVONPORT ROYAL DOCKYARD": ("Babcock - Devonport Royal Dockyard", "aerospace_defence"),
    "CAVENDISH NUCLEAR": ("Cavendish Nuclear (Babcock)", "energy_nuclear"),
    "BABCOCK INTEGRATED": ("Babcock Integrated Technology", "aerospace_defence"),
    "BABCOCK INTERNATIONAL": ("Babcock International", "aerospace_defence"),
    "AWE": ("AWE", "aerospace_defence"),
    "EDWARDS": ("Edwards (Atlas Copco) - Vacuum", "semiconductor"),
    "METHOD CONSULTING": ("Method Consulting", "mep"),
    "AMAZON": ("Amazon UK", "other"),
    "MOLSON COORS": ("Molson Coors", "other"),
    "TKMS ATLAS": ("TKMS Atlas UK", "aerospace_defence"),
    "ACTEMIUM": ("Actemium Design", "energy_generation"),
    "MASTERMOVER": ("MasterMover", "off_highway"),
    "DARVICK": ("Darvick", "other"),
    "GKN AEROSPACE": ("GKN Aerospace", "aerospace_defence"),
    "SIEMENS MOBILITY": ("Siemens Mobility", "rail"),
    "HOLCIM": ("Holcim UK", "other"),
    "ROYAL NAVY": ("Royal Navy", "aerospace_defence"),
    "TUTHILL": ("Tuthill Porsche", "motorsport"),
    "SB RACE": ("SB Race Engineering", "motorsport"),
}


def faa_employer(name):
    up = name.upper()
    for k, v in FAA_EMPLOYERS.items():
        if up.startswith(k):
            return v
    return (name.title(), "other")


def faa_rows():
    rows = []
    for r in json.load(open(DATA / "sources" / "faa_vacancies.json")):
        course = r.get("course") or ""
        if FAA_EXCLUDE_COURSE.search(course) or FAA_EXCLUDE_TITLE.search(r["title"]):
            continue
        emp, sector = faa_employer(r["employer"])
        lvl = int(re.search(r"level (\d)", course).group(1)) if re.search(r"level (\d)", course) else 6
        disc = next((d for k, d in COURSE_DISCIPLINE if k.lower() in course.lower()), "general_engineering")
        if re.search(r"\bMechanical\b", r["title"]) and disc not in ("building_services",):
            disc = "mechanical"
        if "Nuclear" in r["title"] or "Nuclear" in course:
            disc = "nuclear" if disc == "general_engineering" else disc
        sched = (r.get("training_schedule") or "") + " " + (r.get("summary") or "")
        qual = ("MEng" if re.search(r"\bMEng\b", sched) else "BSc_hons" if re.search(r"\bBSc\b", sched)
                else "BEng_hons") if lvl >= 6 else {5: "FdEng", 4: "HNC"}.get(lvl, "L3_diploma")
        deg = re.search(r"(B\s?Eng|BSc|MEng)\s*\(Hons\)[^.,;]{0,60}", sched)
        alevels = re.sub(r"\s*(Share if you have|T Level in:|BTEC in:).*$", "", r.get("alevels") or "").strip() or None
        ucas, maths, physics = parse_alevels(alevels)
        pc = r.get("postcode")
        region = region_from_postcode(pc) or region_from_text(r["title"], r.get("card_location"), r.get("where")) or "multiple"
        other = (r.get("other_requirements") or "") + " " + (r.get("essential") or "")
        elig = []
        if re.search(r"five years|5 years", other) and re.search(r"lived|resid", other, re.I):
            elig.append("uk_resident_5yrs")
        elif re.search(r"three years|3 years", other) and re.search(r"lived|resid", other, re.I):
            elig.append("uk_resident_3yrs")
        if re.search(r"British (citizen|national)|UK national", other, re.I):
            elig.append("uk_national_only")
        if re.search(r"right to work", other, re.I):
            elig.append("right_to_work")
        relevance = classify(sector, disc, lvl)
        closes = r.get("closes")
        rows.append(dict(
            employer=emp, sector=sector, programme_title=r["title"], intake_year=int((r.get("start") or "2027")[:4]),
            discipline=disc, relevance=relevance, role_focus=(r.get("work") or "")[:300] or None,
            apprenticeship_type="degree_apprenticeship" if lvl >= 6 else "higher_apprenticeship" if lvl >= 4 else "advanced_apprenticeship",
            level=lvl, apprenticeship_standard=course, qualification_awarded=qual,
            degree_subject=deg.group(0).strip() if deg else None, university_partner=(r.get("provider") or "").title() or None,
            delivery_mode=("block_release" if re.search(r"block", sched, re.I) else
                           "day_release" if re.search(r"day release|one day a week|1 day a week", sched, re.I) else "unknown"),
            duration_months=months(r.get("duration")),
            accreditation=";".join(r.get("accreditation") or []) or None,
            country="GB", work_location=(r.get("location_line") or r.get("card_location") or "UK"), postcode=pc,
            region=region, driving_licence_required=1 if r.get("driving") else None,
            language_required="English", uk_citizen_work_route="not_needed",
            min_ucas_points=ucas, required_alevels=alevels, min_maths_grade=maths, min_physics_grade=physics,
            gcse_requirements=r.get("gcse"), eligibility_restrictions=";".join(elig) or None,
            security_clearance=r.get("security"),
            salary_year1=r.get("salary"), salary_year1_local=r.get("salary"), currency="GBP",
            salary_notes=r.get("wage_text"), closes_date=closes, closes_early_if_full=1 if r.get("early_close") else None,
            start_date=r.get("start"), application_url=r["url"], source="gov_find_apprenticeship", source_url=r["url"],
            faa_ref=r["ref"], data_quality="live_listing", date_last_verified=VERIFIED_ON,
            listing_status="open" if (closes or "9999") >= VERIFIED_ON else "closed",
            intake_size=int(r["positions"]) if (r.get("positions") or "").isdigit() else None,
            stages=";".join(r.get("stages") or []) or None,
            notes=r.get("after")[:300] if r.get("after") else None,
            employer_url=r.get("employer_url"),
        ))
    return rows


# ----------------------------------------------------------------------------- manual research
MANUAL_QUAL = {"BEng_hons", "MEng", "BSc_hons", "MSc", "BEng_ordinary", "BEng_intl", "FdEng", "FdSc", "HND", "HNC", "L3_diploma", "other"}


def manual_rows():
    rows = []
    for line in open(DATA / "research" / "manual.jsonl"):
        if not line.strip():
            continue
        m = json.loads(line)
        country = {"UK": "GB"}.get(m.get("country", "UK"), m.get("country", "GB"))
        status = m.get("status", "expected")
        url = m["url"]
        source = ("gov_find_apprenticeship" if "findapprenticeship.service.gov.uk" in url else
                  "gov_wales_apprenticeship" if "service.gov.wales" in url else
                  "gradcracker" if "gradcracker" in url else "higherin" if "higherin" in url or "ratemy" in url else
                  "ibec" if "ibec.ie" in url else "ucas" if "ucas.com" in url else
                  "job_board" if re.search(r"jobs24|jobijoba|justapply|itjobswatch|ziprecruiter|grabjobs|irishtalents|flexa|formulacareers|grb\.uk", url) else
                  "employer_site")
        dq = ("live_listing" if status == "open" else
              "register_interest" if "register" in url.lower() or "register" in (m.get("notes") or "").lower() else
              "secondary_source" if source == "job_board" or status == "rumoured" else "previous_cycle")
        cur = m.get("currency", "GBP")
        sal_local = m.get("salary")
        sal_gbp = round(sal_local * EUR_TO_GBP) if sal_local and cur == "EUR" else sal_local
        intl = country != "GB"
        disc = m.get("discipline", "general_engineering")
        lvl = m.get("level", 6)
        sector = m["sector"]
        relevance = classify(sector, disc, lvl)
        if m.get("relevance"):
            relevance = m["relevance"]
        ucas, maths, physics = parse_alevels(m.get("alevels"))
        qual = m.get("qual", "BEng_hons")
        if qual not in MANUAL_QUAL:
            qual = "other"
        rows.append(dict(
            employer=m["employer"], sector=sector, programme_title=m["title"],
            intake_year=int(str(m.get("start") or "2027")[:4]), discipline=disc, relevance=relevance,
            apprenticeship_type=m.get("type", "degree_apprenticeship"), level=lvl, qualification_awarded=qual,
            degree_subject=m.get("degree"), university_partner=m.get("uni"), duration_months=m.get("months"),
            accreditation=m.get("accreditation"), country=country, work_location=m.get("location", "UK"),
            region="international" if intl else m.get("region", "multiple"),
            state_province=m.get("state"),
            language_required=m.get("language", "English"),
            uk_citizen_work_route=m.get("route", "cta_free" if country == "IE" else "residence_permit" if intl else "not_needed"),
            min_ucas_points=m.get("ucas") or ucas, required_alevels=m.get("alevels") or m.get("entry"),
            min_maths_grade=maths, min_physics_grade=physics, gcse_requirements=m.get("gcse"),
            eligibility_restrictions=m.get("eligibility"), security_clearance=m.get("security"),
            salary_year1=sal_gbp, salary_year1_local=sal_local, currency=cur,
            salary_notes=("Figure is from a previous intake" if sal_local and status != "open" else None),
            extra_benefits=m.get("extra"),
            opens_date=m.get("opens"), closes_date=m.get("closes"), start_date=m.get("start"),
            application_url=url, source=source, source_url=url, faa_ref=m.get("faa_ref"),
            data_quality=dq, date_last_verified=VERIFIED_ON, listing_status=status, notes=m.get("notes"),
            stages=m.get("stages"), intake_size=m.get("intake"),
        ))
    return rows


# ----------------------------------------------------------------------------- Germany (ausbildung.de)
DE_EXCLUDE = re.compile(r"Bauingenieur|Vermessung|Informatik|Informationstechnik 20|Bahningenieurwesen (IT|Informationstechnik|Bauwesen)|"
                        r"Masterstudium|Projektmanagement|Facility|Einkauf|Strategie|digitale Transformation|Computing|Software", re.I)
DE_DISCIPLINE = [  # first match wins
    ("Gebäude", "building_services"), ("Versorgungstechnik", "building_services"), ("Versorgungs-", "building_services"),
    ("Kälte", "building_services"), ("Klimatechnik", "building_services"),
    ("Wirtschaftsingenieur", "general_engineering"),
    ("Elektro", "electrical_electronic"), ("Energieversorgung", "electrical_electronic"), ("Bahnstrom", "electrical_electronic"),
    ("Leit- und Sicherung", "electrical_electronic"), ("Embedded", "electrical_electronic"),
    ("Mechatronik", "mechatronics"), ("Automatisierung", "control_automation"),
    ("Produktion", "manufacturing"), ("Fertigung", "manufacturing"),
    ("Maschinenbau", "mechanical"), ("Konstruktion", "design")]
DE_SECTOR_OVERRIDE = [(r"Infineon|GlobalFoundries|X-FAB|Zeiss SMT|Trumpf", "semiconductor"),
                      (r"Siemens Energy", "energy_generation"), (r"Siemens Mobility|Alstom|Stadler|Knorr|Deutsche Bahn|DB ", "rail"),
                      (r"Gamesa|Nordex|Enercon", "energy_renewables"), (r"E\.ON|TenneT|Amprion|50Hertz|TransnetBW|Netze", "energy_networks"),
                      (r"RWE|EnBW|Vattenfall|Uniper", "energy_generation"), (r"Viessmann|Vaillant|Stiebel|SPIE|Caverion|Imtech|Drees|Goldbeck", "mep"),
                      (r"Airbus|MTU Aero|Rheinmetall", "aerospace_defence"),
                      (r"Avacon|E\.DIS|Netze BW|Westnetz", "energy_networks"), (r"Liebherr|Claas|Rexroth", "off_highway"),
                      (r"BMW|Mercedes|Porsche|Volkswagen|Audi|ZF |ZF$|Continental|Schaeffler|MAN Truck|Daimler|Bosch", "automotive")]


def de_rows():
    p = DATA / "sources" / "ausbildung_de.json"
    if not p.exists():
        return []
    rows = []
    for r in json.load(open(p)):
        title = r["title"] or ""
        if not re.search(r"dual|B\.?\s?Eng|Bachelor|Studium|praxisintegriert", title, re.I):
            continue
        if re.search(r"2026(?![/\-–]2027)", title) and "2027" not in title:
            continue
        if DE_EXCLUDE.search(title) and not re.search(r"Gebäudeausrüstung|TGA", title):
            continue
        disc = next((d for k, d in DE_DISCIPLINE if k.lower() in title.lower()), "general_engineering")
        sector = next((s for pat, s in DE_SECTOR_OVERRIDE if re.search(pat, r["employer"] or "")), r.get("sector_hint") or "other")
        if sector == "other" and r.get("sector_hint"):
            sector = r["sector_hint"]
        lo, hi = r.get("salary_min_month"), r.get("salary_max_month")
        lo = lo if lo and lo >= 300 else None   # some listings carry placeholder values like 1
        hi = hi if hi and hi >= 300 else None
        sal_local = round((lo or hi) * 12) if (lo or hi) else None
        relevance = classify(sector, disc, 6)
        if "Wirtschaftsingenieur" in title:  # engineering + management degree: useful, but not core mechanical
            relevance = "related"
        rows.append(dict(
            employer=r["employer"], sector=sector, programme_title=title, intake_year=2027,
            discipline=disc, relevance=relevance, apprenticeship_type="dual_study", level=6,
            qualification_awarded="BEng_intl", degree_subject=title, university_partner=r.get("hochschule"),
            delivery_mode="alternating_phases", country="DE", work_location=r.get("city") or "Germany",
            postcode=r.get("postcode"), region="international", state_province=r.get("state"),
            language_required="German (typically B2-C1)", uk_citizen_work_route="residence_permit",
            required_alevels=r.get("education"),
            salary_year1=round(sal_local * EUR_TO_GBP) if sal_local else None, salary_year1_local=sal_local, currency="EUR",
            salary_notes=(f"EUR {lo}-{hi} per month (training allowance)" if lo or hi else None),
            start_date=(lambda m: f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else "2027")(
                re.match(r"(\d{1,2})\.(\d{1,2})\.(2027)", r.get("start_hint") or "")),
            closes_date=r.get("valid_through") or None, application_url=r["url"], source="ausbildung_de",
            source_url=r["url"], data_quality="live_listing", date_last_verified=VERIFIED_ON, listing_status="open",
            notes="German dual study (duales Studium): paid contract + Bachelor at a partner Hochschule. "
                  "A-levels usually accepted as Abitur-equivalent via anabin/uni-assist; check with the Hochschule.",
        ))
    return rows


# ----------------------------------------------------------------------------- grade fit
GRADE_ORDER = ["A*", "A", "B", "C", "D", "E"]


def grade_fit(r, profile):
    """Compare a programme's entry requirements with the student's predicted A-levels.

    Returns (fit, note). fit is None when the listing states no academic requirement.
    'below' = a required subject is missing; 'borderline' = subject wording needs checking.
    """
    req = r.get("required_alevels")
    if not req:
        return None, None
    grades = profile["alevels"]
    subjects = {k.lower() for k in grades}
    ucas = sum(UCAS[g] for g in grades.values())
    if r["country"] == "DE":
        return "meets", "Needs recognition of A-levels as university entrance (anabin / the Hochschule)"
    if r["country"] == "IE":
        return "meets", None
    # a named subject the student doesn't take, required on its own (not as one option among several)
    for subj in ("Chemistry", "Biology", "Engineering"):
        if re.match(rf"\s*{subj} \(grade", req) and subj.lower() not in subjects:
            return "below", f"Requires A-level {subj}"
    if re.search(r"Biology, Chemistry, Computing", req) and "physics" in subjects:
        return "borderline", "Listed science subjects omit Physics - confirm Physics is accepted"
    need = r.get("min_ucas_points") or 0
    worst = max(grades.values(), key=GRADE_ORDER.index)
    floors = [g for g in (r.get("min_maths_grade"), r.get("min_physics_grade")) if g]
    if ucas >= need and all(GRADE_ORDER.index(worst) <= GRADE_ORDER.index(f) for f in floors):
        return "above", None
    return "meets", None


# ----------------------------------------------------------------------------- commute
def haversine_km(a, b):
    from math import radians, sin, cos, asin, sqrt
    la1, lo1, la2, lo2 = map(radians, (a[0], a[1], b[0], b[1]))
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def estimate_commute(km, rural):
    """Rough door-to-door public-transport minutes from a home in south-west London.

    <=25 km: London transport at ~23 km/h effective plus 10 min access.
    further: ~35 min to reach a London terminal / interchange, then rail at ~90 km/h straight-line, plus
    15 min for rural sites without a station nearby. Calibrated roughly against Reading (~75), Crawley
    (~50), Stevenage (~80), Bristol (~150). Treat as +/- 20 min.
    """
    m = 10 + km * 2.6 if km <= 25 else 35 + km / 1.5
    return int(round(m + (15 if rural and km > 25 else 0), -1))


def apply_commute(rows, profile):
    cache_p = DATA / "sources" / "geocode_cache.json"
    home_p = PERSONAL / "home_geocode.json"   # written by geocode.py; never committed
    if not (cache_p.exists() and home_p.exists()):
        return
    cache = json.loads(cache_p.read_text())
    home = json.loads(home_p.read_text())
    if not home:
        return
    for r in rows:
        if r["country"] != "GB":
            r["relocation_required"] = 1
            continue
        hits, rural = [], False
        if r.get("postcode") and cache.get("pc:" + r["postcode"].upper().replace(" ", "")):
            hits = [cache["pc:" + r["postcode"].upper().replace(" ", "")] + [r["postcode"]]]
        else:
            v = cache.get("loc:" + (r.get("work_location") or ""))
            hits = v or []
            rural = any(len(h) > 3 and str(h[-1]).startswith("override") for h in hits)
        if not hits:
            continue
        best = min(hits, key=lambda h: haversine_km(home, h))
        km = haversine_km(home, best)
        r["commute_minutes"] = estimate_commute(km, rural)
        r["relocation_required"] = 1 if r["commute_minutes"] > 90 else 0
        if len(hits) > 1:
            site = best[-1] if isinstance(best[-1], str) else best[2]
            note = f"Nearest listed site to home: {site}"
            r["notes"] = f"{note}. {r['notes']}" if r.get("notes") else note


# ----------------------------------------------------------------------------- selection stages
# Employer-level selection processes (researched Nov 2026; see docs/selection.md for sources).
# Applied when a listing doesn't state its own stages. Keys are matched against the employer name.
EMPLOYER_STAGES = {
    "Babcock": ("online_form;psychometric;video_interview;assessment_centre",
                "Window Oct-May, applications reviewed in order received and may close early; AC Nov-Mar "
                "(presentation, group task, interview)"),
    "Cavendish Nuclear": ("online_form;psychometric;video_interview;assessment_centre", "Babcock group process"),
    "Thales": ("online_form;cv;psychometric;assessment_centre",
               "Virtual AC with group exercises + competency interviews, Feb-May 2027"),
    "MBDA": ("online_form;psychometric;assessment_centre",
             "Online strengths assessment (personalised report) + job simulation; half-day virtual AC, strengths interview"),
    "AWE": ("online_form;cv;psychometric;assessment_centre", "Online aptitude test then on-site AC at Aldermaston; pre-AC webinars"),
    "Dyson": ("online_form;numerical_test;game_based;assessment_centre",
              "3 online activities (numerical, gamified HireVue, problem-solving/coding) then on-site assessment day"),
    "Jaguar Land Rover": ("online_form;sjt;psychometric;video_interview;assessment_centre",
                          "Motivation form (no CV); SJT + psychometrics; behavioural interview"),
    "Rolls-Royce": ("online_form;numerical_test;verbal_test;sjt;video_interview;assessment_centre",
                    "AC may include practical test, group exercise, technical/competency interview, 10-min presentation"),
    "Mott MacDonald": ("online_form;psychometric;phone_interview",
                       "Only ONE application allowed; strengths-based online test + single virtual strengths interview; no CV"),
    "Hoare Lea": ("online_form;phone_interview;assessment_centre", "Phone interviews Nov-Dec, selection event Jan-Feb"),
    "BAE Systems": ("online_form;psychometric;video_interview;assessment_centre", None),
}


def apply_stages(rows):
    for r in rows:
        if r.get("stages"):
            continue
        for key, (stages, note) in EMPLOYER_STAGES.items():
            if key.lower() in r["employer"].lower():
                r["stages"] = stages
                if note:
                    r["notes"] = f"Selection: {note}. {r['notes']}" if r.get("notes") else f"Selection: {note}"
                break


# ----------------------------------------------------------------------------- assemble
PROG_COLS = None  # filled from the schema


def main():
    rows = faa_rows()
    faa_refs = {r["faa_ref"] for r in rows}
    for m in manual_rows():  # prefer the live GOV.UK row when the manual note points at the same vacancy
        if m.get("faa_ref") and m["faa_ref"] in faa_refs:
            continue
        rows.append(m)
    rows += de_rows()

    # de-duplicate on (employer, title, location)
    seen, uniq = set(), []
    for r in rows:
        k = (r["employer"].lower(), r["programme_title"].lower(), (r.get("work_location") or "").lower())
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    rows = uniq
    apply_stages(rows)

    profile_path = PERSONAL / "my_profile.json"
    if PERSONAL_BUILD and not profile_path.exists():
        raise SystemExit(f"--personal needs {profile_path} (copy data/my_profile.example.json there)")
    if PERSONAL_BUILD:
        profile = json.load(open(profile_path))
        for r in rows:
            fit, note = grade_fit(r, profile)
            r["grade_fit"] = fit
            if note:
                r["notes"] = f"{note}. {r['notes']}" if r.get("notes") else note
        apply_commute(rows, profile)

    out_dir = PERSONAL if PERSONAL_BUILD else DATA
    db_path = (PERSONAL if PERSONAL_BUILD else ROOT) / "apprenticeships.db"
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript((ROOT / "schema" / "schema.sql").read_text())
    prog_cols = [c[1] for c in con.execute("PRAGMA table_info(programmes)")][2:]  # drop id, employer_id
    emp_cols = [c[1] for c in con.execute("PRAGMA table_info(employers)")][1:]

    employers = {}
    for r in rows:
        e = employers.setdefault(r["employer"], {"employer_name": r["employer"], "primary_sector": r["sector"],
                                                 "hq_country": r["country"], "careers_url": r.get("employer_url")})
        if not e.get("careers_url") and r.get("employer_url"):
            e["careers_url"] = r["employer_url"]
    for e in employers.values():
        cur = con.execute(f"INSERT INTO employers ({','.join(e)}) VALUES ({','.join('?' * len(e))})", list(e.values()))
        e["employer_id"] = cur.lastrowid

    for r in rows:
        vals = {c: r.get(c) for c in prog_cols if r.get(c) is not None}
        vals["employer_id"] = employers[r["employer"]]["employer_id"]
        try:
            con.execute(f"INSERT INTO programmes ({','.join(vals)}) VALUES ({','.join('?' * len(vals))})", list(vals.values()))
        except sqlite3.IntegrityError as ex:
            raise SystemExit(f"Row rejected by schema ({ex}): {r['employer']} - {r['programme_title']}")
    con.commit()

    # CSV exports (the spreadsheet version of the database)
    def dump(query, path):
        cur = con.execute(query)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([d[0] for d in cur.description])
            w.writerows(cur)
    dump("SELECT * FROM employers ORDER BY employer_name", out_dir / "employers.csv")
    dump("""SELECT e.employer_name, p.* FROM programmes p JOIN employers e USING (employer_id)
            ORDER BY p.country <> 'GB', p.relevance <> 'core', p.listing_status <> 'open',
                     p.closes_date IS NULL, p.closes_date, e.employer_name""", out_dir / "programmes.csv")

    n = con.execute("SELECT COUNT(*) FROM programmes").fetchone()[0]
    print(f"{len(employers)} employers, {n} programmes")
    for row in con.execute("SELECT * FROM sector_summary"):
        print("  ", row)
    print("by country:", con.execute("SELECT country, COUNT(*) FROM programmes GROUP BY country").fetchall())
    print("by status:", con.execute("SELECT listing_status, COUNT(*) FROM programmes GROUP BY listing_status").fetchall())
    con.close()


if __name__ == "__main__":
    main()
