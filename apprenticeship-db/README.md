# Engineering Apprenticeship Tracker

A planned database of **degree apprenticeships and higher apprenticeships** for a
UK Year 13 student studying **A-level Maths, Further Maths and Physics** who wants
to go into **mechanical-related engineering**:

| Target sector | Typical roles |
|---|---|
| Semiconductor | Equipment / process / facilities engineer, vacuum & cleanroom systems |
| Energy | Generation, nuclear, fusion, networks, renewables, hydrogen |
| MEP / building services | Mechanical, electrical & public-health design and site engineering |
| Automotive | Manufacturing, product, powertrain / EV battery engineering |
| Vehicle (wider) | Rail, off-highway, motorsport, defence vehicles |

The aim is to answer three questions for every scheme:

1. **Can I get in?** Entry requirements against predicted grades.
2. **Is it worth it?** Degree awarded, chartership route, pay, location, job at the end.
3. **Where am I with it?** Deadlines and how far the application has got.

## Contents

| Path | Purpose |
|---|---|
| [`docs/fields.md`](docs/fields.md) | **Data dictionary:** every field, its type, allowed values and why it matters |
| [`docs/scoring.md`](docs/scoring.md) | How to rank schemes against each other |
| [`schema/schema.sql`](schema/schema.sql) | SQLite schema that enforces the allowed values |
| [`data/programmes_template.csv`](data/programmes_template.csv) | Blank spreadsheet with one column per programme field |
| [`data/applications_template.csv`](data/applications_template.csv) | Blank spreadsheet for tracking applications |
| [`data/seed_employers.csv`](data/seed_employers.csv) | Starting list of employers to research (**not verified**) |

## Structure (3 tables)

```
employers 1──* programmes 1──0..1 applications
```

- **employers**: facts about the company (sector, size, sites).
- **programmes**: one row per scheme/intake (e.g. "JLR Mechanical Engineering Degree Apprenticeship, Sept 2027, Gaydon").
- **applications**: your progress on a programme (status, dates, test results, notes).

Programme facts are kept apart from application progress, so the programme data
can be refreshed every year without losing your notes.

## Getting started

```bash
cd apprenticeship-db
sqlite3 apprenticeships.db < schema/schema.sql   # create the database
# or open the CSV templates in Excel / Google Sheets
```

## Where to find schemes

- GOV.UK *Find an apprenticeship* (official listings, filter by level 6)
- Employer early-careers pages (often list schemes before the GOV.UK site does)
- UCAS apprenticeship search
- RateMyApprenticeship, Amazing Apprenticeships, Higher Futures
- Professional bodies: IMechE, IET, CIBSE, Engineering UK

## Typical timeline for a September 2027 start

| When | What happens |
|---|---|
| Sep – Dec 2026 | Big employers open applications. Many close early or when full. |
| Jan – Mar 2027 | Online tests, video interviews, assessment centres |
| Mar – Jun 2027 | Offers. Smaller employers and MEP firms keep recruiting. |
| Aug 2027 | A-level results confirm conditional offers |
| Sep 2027 | Start |

Fill in `date_last_verified` every time you check a listing. Dates and pay change every year.
