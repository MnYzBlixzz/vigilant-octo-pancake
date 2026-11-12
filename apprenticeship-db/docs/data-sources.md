# How the database was built

Snapshot date: **12 November 2026**, for September 2027 intakes (Ireland: January/September 2027).

## Sources

| Source | How | Rows | Trust |
|---|---|---|---|
| GOV.UK **Find an Apprenticeship** | `scripts/scrape_faa.py` sweeps Level 3–7 vacancies in Engineering & Manufacturing, Construction and Transport, plus keyword searches for "engineer", "engineering" and "mechanical". `scripts/parse_faa.py` reads every vacancy page (pay, provider, A-level text, security vetting, accreditation). The build keeps engineering roles and drops civil, surveying, software, data and similar. | Live 2027 vacancies | `live_listing`: read directly from the official listing |
| Employer sites, Gradcracker, Higherin, UCAS, news | Hand-researched with web search and recorded in `data/research/manual.jsonl`. Covers big employers who recruit on their own sites, or who haven't posted 2027 vacancies yet (JLR, BMW, Rolls-Royce, BAE, EDF, Sellafield, National Grid, MEP consultancies, etc.). | Many are `expected` | `previous_cycle` / `register_interest` / `secondary_source`: dates and pay are often from the **2026** intake |
| **ausbildung.de** (Germany) | `scripts/scrape_ausbildung.py` searches dual-study programmes (Maschinenbau, Mechatronik, Elektrotechnik, Versorgungstechnik) at named target employers and reads each listing's JobPosting data. | Live 2027 listings | `live_listing` |
| Ireland (Ibec, ADI, ESB, Intel) | Hand-researched | Few | Mixed |

## Known gaps
- **Gradcracker** blocks automated access, so its listings appear only where a web search surfaced them.
- **Bosch, BAE, JLR, Rolls-Royce, Siemens UK** and other large employers often post 2027 vacancies between **January and March 2027**. They appear as `expected` rows with last year's details. Check them again then.
- Several schemes have **already closed** for 2027. They are marked `closed` and kept so you know to apply early next cycle: Airbus (closed 26 Oct 2026), GKN Aerospace (23 Oct 2026), and Hoare Lea (Sept–Nov 2026).
- Salaries: "Competitive" means the employer didn't publish a figure. Non-GBP pay is converted at **€1 = £0.85** for comparison only.
- `relevance` is decided by rules (sector + discipline + level) in `scripts/build_db.py`. Override it in a row if you disagree.
- Germany: only big-name employers were searched. There are thousands more on ausbildung.de and arbeitsagentur.de.

## Refreshing

```bash
cd apprenticeship-db
python3 scripts/scrape_faa.py /tmp/faa_raw            # ~2 min
python3 scripts/parse_faa.py /tmp/faa_raw data/sources/faa_vacancies.json
python3 scripts/scrape_ausbildung.py data/sources/ausbildung_de.json   # ~10 min
python3 scripts/build_db.py --verified-on $(date +%F)
```

Add or update hand-researched schemes in `data/research/manual.jsonl` (one JSON object per line), then rebuild.
These sites need network access to `www.findapprenticeship.service.gov.uk` and `www.ausbildung.de`.
