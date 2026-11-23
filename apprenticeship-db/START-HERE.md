# START HERE: Engineering apprenticeship search (2027 entry)

Everything from the research is in this folder. This page summarises it. The details are in the files linked below.

## Who it's for
A Year 13 student taking A-level **Maths, Further Maths and Physics**, aiming for mechanical-type engineering in
**semiconductor, energy, MEP / building services, automotive and vehicle** engineering (rail, off-highway, motorsport).
It covers the UK first, with Ireland (no permit needed for UK citizens) and Germany (residence permit plus German) as
options abroad.

Personal details (grades, home postcode) are **not** in this repository. They go in the git-ignored `personal/`
folder. See "Personal build" in [README.md](README.md).

**With strong grades, entry requirements aren't the hurdle** (the highest stated requirement is ABB / 128 points).
Offers are decided by the online tests, motivation answers, assessment centres and, for defence/nuclear, security
vetting. Subject catches: Cavendish Nuclear *Chemical & Process* needs Chemistry. Two Babcock listings don't
mention Physics among the accepted sciences (confirm). Molson Coors asks for Engineering.

## Deadlines (from the 12 Nov 2026 snapshot; check each listing)
| Closes | What | Where |
|---|---|---|
| **7 Dec 2026** | ~15 Babcock / Cavendish Nuclear / Devonport degree apprenticeships: Mechanical, Building Services, Nuclear Scientist & Engineer, Electro-Mechanical, Process & Plant, Control Systems | Plymouth, Bristol, Warrington, Leicester, Hull |
| **8 Dec 2026** | Babcock Scotland Graduate Apprenticeships: Rosyth, HMNB Clyde | Rosyth / Helensburgh |
| **20 Dec 2026** | AWE Building Services Asset Engineering; AWE Manufacturing Engineer (British nationals only for some roles) | Aldermaston, Berkshire |
| 8 Jan 2027 | GRAHAM Trainee Building Services Manager | various |
| 10 Jan 2027 | AWE Electronic Design | Aldermaston |
| 15 Jan 2027 | **Edwards Mechanical L6** (Clevedon: vacuum pumps for chip fabs); **Mott MacDonald Building Services** (London/Croydon; you can only make ONE Mott MacDonald application) | Clevedon / London, Croydon, Cambridge, Manchester |
| ~mid-Jan 2027 | Dyson Institute MEng (sponsored degree; expected) | Malmesbury |
| 22 Jan 2027 | MBDA Test, Calibration & Maintenance L6 (other MBDA L6s similar; may close early) | Stevenage / Bolton |
| 30 Jan 2027 | Method Consulting Building Services (Swindon) | Swindon |
| 17 Feb 2027 | Thales: Crawley & Reading (Systems, Hardware, Integration), Templecombe Mechanical | Crawley, Reading, Templecombe, Cheadle |
| Jan–Mar 2027 | **Expected to open:** JLR, Bentley, BAE, Rolls-Royce, BMW Oxford, Siemens, Renishaw, Cummins, Caterpillar, National Grid, Sellafield, EDF, Laing O'Rourke, AtkinsRéalis, Arup, WSP, Kier, Cundall, Hitachi Rail | many in London |
| Mar–Jul 2027 | Late recruiters: BAM, Morgan Sindall (MEP contractors), VW Kassel dual study (30 Apr) | |

Already **closed** for 2027: Airbus UK (26 Oct), GKN Aerospace (23 Oct), Hoare Lea (Sep–Nov). Apply early next time.

## Suggested plan
1. **This week:** the 7–8 Dec Babcock/Cavendish schemes (decide if you'd relocate) and AWE (20 Dec).
2. **Before mid-Jan:** Edwards, Mott MacDonald (pick Building Services *or* Rail), GRAHAM, Dyson, MBDA.
3. **Jan–Feb:** Thales, plus each big employer as it opens (the refresh routine flags them).
4. Aim for **8–12 applications** across at least three sectors, and keep a UCAS application running as a backup ([docs/alternatives.md](docs/alternatives.md)).
5. Prepare for the tests and assessment centres with [docs/selection.md](docs/selection.md).
6. Log each application in the `applications` table (or [`data/applications_template.csv`](data/applications_template.csv)) and use `SELECT * FROM todo;`.

## Where everything is
| File | What |
|---|---|
| [`data/programmes.csv`](data/programmes.csv) | **The database as a spreadsheet**: 233 programmes, one row each, with source links |
| [`data/employers.csv`](data/employers.csv) | 124 employers |
| `apprenticeships.db` | Same data in SQLite with views: `my_matches`, `upcoming_deadlines`, `open_core_uk`, `international`, `sector_summary`, `todo` |
| [README.md](README.md) | How to use the database, example queries, commute and vetting notes |
| [docs/fields.md](docs/fields.md) | What every column means and its allowed values |
| [docs/scoring.md](docs/scoring.md) | 0–100 fit score for ranking schemes |
| [docs/selection.md](docs/selection.md) | Tests and assessment centres by employer, plus a preparation checklist |
| [docs/alternatives.md](docs/alternatives.md) | Sponsored degrees, scholarships (IMechE, IET, UKESF, Kingsbury), gap-year placements |
| [docs/international.md](docs/international.md) | Ireland / Germany / NL / US / Australia: what a UK citizen can do |
| [docs/data-sources.md](docs/data-sources.md) | How the data was collected, known gaps, how to refresh |
| `docs/updates/` | Fortnightly refresh reports (created by the routine below, from 1 Dec 2026) |
| [`data/research/manual.jsonl`](data/research/manual.jsonl) | Hand-researched schemes (one JSON per line); edit and rebuild |
| `personal/` | **Git-ignored.** Profile (grades, postcode), personalised database with commute times, and the personal version of this page |
| `data/sources/` | Scraped data: GOV.UK vacancies, ausbildung.de listings, postcode lookups; `raw/` holds an archive of the original GOV.UK vacancy pages (12 Nov 2026), kept because listings vanish once they close |
| `schema/schema.sql` | Table definitions, allowed values, views |
| `scripts/` | Scrapers (`scrape_faa.py`, `parse_faa.py`, `scrape_ausbildung.py`), `geocode.py`, `build_db.py` |

## Automatic refresh
A Claude Code routine, **"Apprenticeship DB refresh (Dec–Mar)"** (id `trig_01FEtanksUZ7G5LdEx4d5q8Y`), runs at
**18:23 UK time on the 1st and 15th of Dec, Jan, Feb and Mar**, starting **1 Dec 2026**. Each run re-scrapes,
checks the "expected" employers, rebuilds, writes `docs/updates/<date>.md`, pushes to this branch
(`claude/festive-bell-p33xkb`) and sends a push notification. Edit, pause or delete it from the Routines page on
claude.ai. It attaches the repo itself; if the first run reports it couldn't, re-create the routine with this repo selected.

## Rebuilding by hand
```bash
cd apprenticeship-db
python3 scripts/build_db.py                       # rebuild from the saved data (no network needed)
# full refresh from live sites: see docs/data-sources.md
```
Live refreshes need network access to: `www.findapprenticeship.service.gov.uk`, `www.ausbildung.de`, `api.postcodes.io`
(allowed in the personal cloud environment **vigilant-octo-pancake**). Gradcracker blocks automated access, so its listings
come only from web search.

## Caveats
- Snapshot of **12 Nov 2026**. Rows marked `expected` / `previous_cycle` use 2026 pay and dates.
- Commute times exist only in the personal build and are estimates (±20 min), not timetables.
- € pay is converted at €1 = £0.85. "Competitive" means no figure was published.
- Blank means unknown, not "no".
