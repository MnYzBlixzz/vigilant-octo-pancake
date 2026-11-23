"""Parse GOV.UK Find an Apprenticeship vacancy pages into structured records.

Usage: python3 parse_faa.py RAW_DIR OUT_JSON
RAW_DIR is the output directory of scrape_faa.py.
"""
import html, json, re, sys
from datetime import datetime

SECTIONS = ["Summary", "Work", "Training", "Requirements", "About this employer", "After this apprenticeship"]


def page_text(raw):
    s = raw[raw.find("<main"):raw.find("</main>")]
    s = re.sub(r"<(script|style).*?</\1>", "", s, flags=re.S)
    s = re.sub(r"</(p|li|h\d|dt|dd|tr|div)>|<br\s*/?>", "\n", s)
    t = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return [" ".join(l.split()) for l in t.splitlines() if l.strip()]


def after(lines, label, n=1):
    """Value on the line(s) following an exact label line."""
    for i, l in enumerate(lines):
        if l == label and i + 1 < len(lines):
            return " ".join(lines[i + 1:i + 1 + n])
    return None


def block(lines, start, stops):
    """Lines between the first `start` line and the next line in `stops`."""
    try:
        i = lines.index(start)
    except ValueError:
        return []
    out = []
    for l in lines[i + 1:]:
        if l in stops:
            break
        out.append(l)
    return out


def to_date(s):
    m = re.search(r"(\d{1,2}) (\w+) (\d{4})", s or "")
    if not m:
        return None
    try:
        return datetime.strptime(" ".join(m.groups()), "%d %B %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def money(s):
    """First £ amount per year, as int; hourly wages converted at the stated weekly hours later."""
    m = re.search(r"£([\d,]+(?:\.\d+)?)\s*(?:to\s*£([\d,]+(?:\.\d+)?))?\s*a year", s or "")
    if m:
        return int(float(m.group(1).replace(",", "")))
    return None


GRADE = r"(A\*|A|B|C|D|E)"


STAGE_PATTERNS = [
    ("online_form", r"online application|application form"), ("cv", r"\bCV\b"), ("cover_letter", r"cover(ing)? letter"),
    ("motivation_questions", r"motivation(al)? question|competency question|supporting statement"),
    ("numerical_test", r"numerical (reasoning|test)|maths test|numeracy test"),
    ("verbal_test", r"verbal reasoning"), ("mechanical_reasoning", r"mechanical (reasoning|comprehension|aptitude)"),
    ("sjt", r"situational judg|SJT"), ("game_based", r"game[- ]based|gamified"),
    ("psychometric", r"psychometric|online test|aptitude test|online assessment"),
    ("video_interview", r"video interview|recorded interview|HireVue|Sonru"),
    ("phone_interview", r"telephone interview|phone interview|telephone screening"),
    ("assessment_centre", r"assessment (centre|center|day)|selection (day|event)|insight day"),
    ("technical_interview", r"technical interview|technical task|practical (task|test)"),
    ("site_visit", r"site visit|site tour"),
]


def parse(ref, raw):
    L = page_text(raw)
    if not L:
        return None
    full = "\n".join(L)
    req = block(L, "Essential qualifications", ["Skills", "Other requirements", "About this employer", "Desirable qualifications"])
    desirable = block(L, "Desirable qualifications", ["Skills", "Other requirements", "About this employer"])
    other_req = block(L, "Other requirements", ["About this employer"])
    alevel = None
    for i, l in enumerate(req):
        if l.startswith("A Level in"):
            alevel = " ".join(req[i + 1:i + 3]) if i + 1 < len(req) else None
            break
    gcse = None
    for i, l in enumerate(req):
        if l.startswith("GCSE in"):
            gcse = req[i + 1] if i + 1 < len(req) else None
            break
    sec = None
    sec_pats = {"DV": r"\bDV\b|Developed Vetting", "SC": r"\bSC\b|Security Check\b|SC clearance",
                "CTC": r"\bCTC\b|Counter[- ]Terrorist Check", "BPSS": r"\bBPSS\b|Baseline Personnel Security"}
    for lvl, pat in sec_pats.items():  # highest level mentioned wins
        if re.search(pat, full):
            sec = lvl
            break
    if sec is None and re.search(r"security clearance|security vetting|national security vetting", full, re.I):
        sec = "unknown"  # vetting mentioned but level not stated
    # Case-sensitive whole-word match: lowercase matching hits "notICE", "mINIMum" etc.
    acc_names = {
        "IMechE": r"\bIMechE\b|Institut\w* of Mechanical Engineers",
        "IET": r"\bIET\b|Institution of Engineering and Technology",
        "CIBSE": r"\bCIBSE\b|Chartered Institution of Building Services",
        "RAeS": r"\bRAeS\b|Royal Aeronautical Society",
        "IChemE": r"\bIChemE\b|Institution of Chemical Engineers",
        "EI": r"Energy Institute",
        "NI": r"Nuclear Institute",
        "IMI": r"\bIMI\b|Institute of the Motor Industry",
    }
    acc = sorted(k for k, pat in acc_names.items() if re.search(pat, full))
    employer_url = next((l.split(" (opens")[0] for l in block(L, "About this employer", ["Company benefits", "After this apprenticeship"])
                         if l.startswith("http")), None)
    rec = {
        "ref": ref,
        "url": f"https://www.findapprenticeship.service.gov.uk/apprenticeship/{ref}",
        "title": L[0],
        "employer": L[1] if len(L) > 1 else None,
        "location_line": L[2] if len(L) > 2 else None,
        "closes": to_date(next((l for l in L[:8] if l.startswith("Closes")), None)),
        "closes_text": next((l for l in L[:8] if l.startswith("Closes") or "early" in l.lower()), None),
        "posted": to_date(next((l for l in L[:8] if l.startswith("Posted")), None)),
        "wage_text": after(L, "Wage"),
        "salary": money(after(L, "Wage")),
        "course": after(L, "Training course"),
        "hours": after(L, "Hours"),
        "start": to_date(after(L, "Start date")),
        "duration": after(L, "Duration"),
        "positions": after(L, "Positions available"),
        "where": " ".join(block(L, "Where you'll work", ["Training"])) or None,
        "provider": after(L, "Training provider"),
        "summary": " ".join(block(L, "Summary", ["Wage"]))[:600],
        "work": " ".join(block(L, "What you'll do at work", ["Where you'll work"]))[:1500],
        "training_schedule": " ".join(block(L, "Training schedule", ["More training information", "Requirements"]))[:800],
        "alevels": alevel,
        "gcse": gcse,
        "essential": " | ".join(req)[:600],
        "desirable": " | ".join(desirable)[:300],
        "other_requirements": " ".join(other_req)[:700],
        "security": sec,
        "accreditation": acc,
        "driving": bool(re.search(r"driving licen[cs]e", full, re.I)),
        "employer_url": employer_url,
        "after": " ".join(block(L, "After this apprenticeship", ["Ask a question", "Apply now"]))[:400],
        "early_close": bool(re.search(r"close (this vacancy )?early|right to close", full, re.I)),
        "stages": [k for k, pat in STAGE_PATTERNS if re.search(pat, full, re.I)],
    }
    m = re.search(r"\b([A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2})\b", rec["location_line"] or "")
    rec["postcode"] = m.group(1) if m else None
    # Grades from A-level text, e.g. "Maths, Physics (grade BBB or equivalent)"
    g = re.search(r"grade\s+([A-E\*]{2,6})", alevel or "", re.I)
    rec["alevel_grades"] = g.group(1).upper() if g else None
    return rec


def main(raw_dir, out):
    import glob, os
    cards = {c["ref"]: c for c in json.load(open(f"{raw_dir}/faa_list.json"))}
    recs = []
    for p in sorted(glob.glob(f"{raw_dir}/vac/*.html")):
        ref = os.path.basename(p)[:-5]
        r = parse(ref, open(p).read())
        if r:
            r["card_location"] = cards.get(ref, {}).get("location")
            recs.append(r)
    json.dump(recs, open(out, "w"), indent=1)
    print(len(recs), "records")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
