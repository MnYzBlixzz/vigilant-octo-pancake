# Engineering Apprenticeship Database

> **New here? Read [START-HERE.md](START-HERE.md)** for the summary, deadlines and plan.

A database of **degree, higher and dual-study apprenticeships** for a Year 13 student taking
**A-level Maths, Further Maths and Physics** who wants a **mechanical-related engineering** career in:

| Target sector | `sector` values | Typical roles |
|---|---|---|
| Semiconductor | `semiconductor` | Vacuum & fab equipment, process/manufacturing, metrology, cleanroom facilities |
| Energy | `energy_nuclear`, `energy_fusion`, `energy_generation`, `energy_networks`, `energy_renewables` | Nuclear plant & submarines, fusion, turbines, grid |
| MEP / building services | `mep` | Mechanical, electrical and public-health design and site engineering |
| Automotive | `automotive` | Manufacturing, product design, EV & battery |
| Vehicle (wider) | `motorsport`, `rail`, `off_highway` | Rolling stock, engines, off-highway machinery, racing |

Closely related options (aerospace & defence, which use the same mechanical skills) are kept with `relevance = related`.

Snapshot: **12 Nov 2026**, for **2027 intakes**. UK, plus Ireland and Germany. See [docs/international.md](docs/international.md).

**What's in it:** 233 programmes from 124 employers. 148 are UK, 77 Germany, 7 Ireland and 1 Netherlands. 145 are open now and 77 are expected to open. 82 are `core` matches.

> ⚠️ **Deadlines very soon:** About 15 Babcock / Cavendish Nuclear / Devonport Royal Dockyard degree apprenticeships close on **7 Dec 2026**, and the Babcock Scotland Graduate Apprenticeships close on **8 Dec 2026**, and AWE closes on **20 Dec 2026**. They include mechanical, building services, nuclear, electro-mechanical and process roles. Run `SELECT * FROM upcoming_deadlines;`.

## Use it

| You want… | Open |
|---|---|
| A spreadsheet | [`data/programmes.csv`](data/programmes.csv) (one row per scheme) and [`data/employers.csv`](data/employers.csv) |
| To query it | `apprenticeships.db` (SQLite: DB Browser for SQLite, or `sqlite3 apprenticeships.db`) |
| What each column means | [docs/fields.md](docs/fields.md) |
| How to rank schemes | [docs/scoring.md](docs/scoring.md) |
| Where the data came from | [docs/data-sources.md](docs/data-sources.md) |

### Useful views (already in the database)

```sql
SELECT * FROM near_home;             -- (personal build only) degree-level schemes within ~90 min of home
SELECT * FROM my_matches;            -- schemes worth applying to (uses grade_fit in the personal build), open first
SELECT * FROM open_core_uk;          -- core UK degree apprenticeships open right now, by deadline
SELECT * FROM upcoming_deadlines;    -- everything still open or expected, by deadline
SELECT * FROM international;         -- outside the UK, easiest-to-access first
SELECT * FROM sector_summary;        -- counts and average pay per sector
```

Example queries:

```sql
-- Mechanical-type schemes needing BBB or less, closing soonest
SELECT employer_name, programme_title, work_location, closes_date, min_ucas_points
FROM programmes JOIN employers USING (employer_id)
WHERE relevance='core' AND (min_ucas_points IS NULL OR min_ucas_points <= 120)
ORDER BY closes_date IS NULL, closes_date;

-- No security clearance needed (some nuclear/defence roles require 5 years' UK residence)
SELECT employer_name, programme_title FROM programmes JOIN employers USING (employer_id)
WHERE security_clearance IS NULL AND level >= 6;
```

### Personal build (kept off GitHub)
Grades and home postcode are **never committed**. They live in `personal/my_profile.json`, and the `personal/`
folder is git-ignored. To get the personalised columns (`grade_fit`, `commute_minutes`, `relocation_required`) and
the `near_home` view:

```bash
mkdir -p personal && cp data/my_profile.example.json personal/my_profile.json   # then fill in real values
python3 scripts/geocode.py              # looks up home + workplace locations (postcodes.io)
python3 scripts/build_db.py --personal  # writes personal/apprenticeships.db, personal/programmes.csv
```

`grade_fit`: `above` = beats every stated requirement; `meets` = Germany/Ireland, where A-levels must be recognised;
`borderline` = the listing's subject wording needs checking; `below` = a required subject isn't taken.
`commute_minutes` is a rough public-transport estimate from straight-line distance (±20 min); above 90 min,
`relocation_required = 1`.

### Security vetting and nationality
Many defence/nuclear schemes need **SC clearance**, which usually needs **5 years' continuous UK residence**. Thales,
Babcock, MBDA and Rolls-Royce Submarines all require it. Some AWE roles need **British nationality**. Check `security_clearance`
and `eligibility_restrictions` before applying if you've lived abroad recently or aren't a British national.

### More guides
- [docs/selection.md](docs/selection.md): tests and assessment centres by employer, plus a preparation checklist
- [docs/alternatives.md](docs/alternatives.md): sponsored degrees, scholarships (IMechE, IET, UKESF, Kingsbury), gap-year placements

### Tracking applications
Add a row to the `applications` table (or `data/applications_template.csv`) for each scheme you apply to.
`SELECT * FROM todo;` then lists your next actions by due date.

## How to read a row
- `listing_status`: `open` (applications open now), `expected` (ran in 2026, 2027 vacancy not yet posted), `closed`, `rumoured`.
- `data_quality`: `live_listing` (read from the actual 2027 vacancy) vs `previous_cycle` (pay and dates from 2026, so they will change).
- `relevance`: `core` / `related` / `backup` (Level 3 fallbacks).
- Blank means **unknown**, not "no".

## Rebuild
```bash
python3 scripts/build_db.py          # rebuild CSVs + SQLite from data/sources and data/research
```
For a full refresh from the live sites, see [docs/data-sources.md](docs/data-sources.md).

## Layout
```
apprenticeship-db/
  START-HERE.md                summary, deadlines, plan, file map, refresh routine
  apprenticeships.db           built SQLite database
  data/programmes.csv          built: all programmes
  data/employers.csv           built: all employers
  data/applications_template.csv
  data/sources/                raw scraped data (GOV.UK, ausbildung.de)
  data/research/manual.jsonl   hand-researched schemes
  data/sources/raw/            archive of the original GOV.UK vacancy pages
  schema/schema.sql            tables, allowed values, views
  scripts/                     scrapers + build script
  docs/                        field dictionary, scoring, sources, international guide
```

## Timeline for a September 2027 start
| When | What happens |
|---|---|
| **Now (Nov 2026)** | Many are open: Thales, Babcock/Devonport/Cavendish Nuclear, MBDA, Mott MacDonald, Edwards, AWE, GRAHAM… Several close in **December**. |
| Dec 2026 – Mar 2027 | Large employers open and close: JLR, Bentley, BAE, Rolls-Royce, BMW, Dyson (mid-Jan), Renishaw, Siemens. |
| Jan – Mar 2027 | Online tests, video interviews, assessment centres |
| Mar – Jun 2027 | Offers. Smaller firms and MEP contractors keep recruiting. |
| Aug 2027 | A-level results confirm conditional offers |
