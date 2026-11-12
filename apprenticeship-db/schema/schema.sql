-- Engineering apprenticeship tracker: SQLite schema (v2: international)
-- Field meanings and allowed values: docs/fields.md
-- Multi-value fields are stored as ';'-separated text.
PRAGMA foreign_keys = ON;

CREATE TABLE employers (
    employer_id             INTEGER PRIMARY KEY,
    employer_name           TEXT NOT NULL UNIQUE,
    parent_group            TEXT,
    primary_sector          TEXT NOT NULL CHECK (primary_sector IN (
        'semiconductor','energy_generation','energy_nuclear','energy_fusion',
        'energy_networks','energy_renewables','energy_hydrogen','mep',
        'automotive','motorsport','rail','off_highway','aerospace_defence','other')),
    secondary_sectors       TEXT,
    hq_country              TEXT,   -- ISO 3166-1 alpha-2, e.g. GB, IE, DE
    company_size            TEXT CHECK (company_size IN ('sme','large','major')),
    uk_sites                TEXT,
    careers_url             TEXT,
    glassdoor_or_rma_rating REAL CHECK (glassdoor_or_rma_rating BETWEEN 0 AND 5),
    notes                   TEXT
);

CREATE TABLE programmes (
    programme_id            INTEGER PRIMARY KEY,
    employer_id             INTEGER NOT NULL REFERENCES employers(employer_id),
    -- identity
    programme_title         TEXT NOT NULL,
    intake_year             INTEGER NOT NULL,
    sector                  TEXT NOT NULL CHECK (sector IN (
        'semiconductor','energy_generation','energy_nuclear','energy_fusion',
        'energy_networks','energy_renewables','energy_hydrogen','mep',
        'automotive','motorsport','rail','off_highway','aerospace_defence','other')),
    discipline              TEXT NOT NULL CHECK (discipline IN (
        'mechanical','mechatronics','manufacturing','electrical_electronic',
        'building_services','process_chemical','control_automation','design',
        'maintenance','systems','nuclear','general_engineering')),
    relevance               TEXT NOT NULL CHECK (relevance IN ('core','related','backup')),
    role_focus              TEXT,
    rotations               INTEGER CHECK (rotations IN (0,1)),
    -- qualification
    apprenticeship_type     TEXT NOT NULL CHECK (apprenticeship_type IN (
        'degree_apprenticeship','higher_apprenticeship','advanced_apprenticeship',
        'sponsored_degree','school_leaver_programme','dual_study')),
    level                   INTEGER NOT NULL CHECK (level BETWEEN 3 AND 7),  -- UK RQF level or nearest equivalent
    apprenticeship_standard TEXT,
    qualification_awarded   TEXT NOT NULL CHECK (qualification_awarded IN (
        'BEng_hons','MEng','BSc_hons','MSc','BEng_ordinary','BEng_intl','FdEng','FdSc',
        'HND','HNC','L3_diploma','other')),
    degree_subject          TEXT,
    university_partner      TEXT,
    university_location     TEXT,
    delivery_mode           TEXT NOT NULL DEFAULT 'unknown' CHECK (delivery_mode IN (
        'day_release','block_release','full_time_uni_then_work','distance_online','blended',
        'alternating_phases','unknown')),
    duration_months         INTEGER CHECK (duration_months > 0),
    accreditation           TEXT,   -- IMechE;IET;CIBSE;IChemE;EI;NI;RAeS;IMI;Engineers Ireland;none;unknown
    registration_target     TEXT CHECK (registration_target IN ('EngTech','IEng','CEng','none','unknown')),
    further_study_funded    INTEGER CHECK (further_study_funded IN (0,1)),
    -- location
    country                 TEXT NOT NULL DEFAULT 'GB',  -- ISO 3166-1 alpha-2
    work_location           TEXT NOT NULL,
    postcode                TEXT,
    region                  TEXT NOT NULL CHECK (region IN (
        'north_east','north_west','yorkshire_humber','east_midlands','west_midlands',
        'east_of_england','london','south_east','south_west','wales','scotland',
        'northern_ireland','multiple','remote','international')),
    state_province          TEXT,   -- for non-UK rows (e.g. Bayern, Munster)
    multiple_locations      INTEGER CHECK (multiple_locations IN (0,1)),
    commute_minutes         INTEGER CHECK (commute_minutes >= 0),       -- fill in yourself
    relocation_required     INTEGER CHECK (relocation_required IN (0,1)), -- fill in yourself
    relocation_support      TEXT,
    driving_licence_required INTEGER CHECK (driving_licence_required IN (0,1)),
    -- international eligibility (for a UK citizen)
    language_required       TEXT,   -- e.g. 'English', 'German B2-C1'
    uk_citizen_work_route   TEXT NOT NULL DEFAULT 'not_needed' CHECK (uk_citizen_work_route IN (
        'not_needed','cta_free','residence_permit','visa_hard','not_eligible','unknown')),
    -- entry requirements
    min_ucas_points         INTEGER CHECK (min_ucas_points >= 0),
    required_alevels        TEXT,
    min_maths_grade         TEXT CHECK (min_maths_grade IN ('A*','A','B','C','D','E','none')),
    min_physics_grade       TEXT CHECK (min_physics_grade IN ('A*','A','B','C','D','E','none')),
    physics_or_alt_accepted INTEGER CHECK (physics_or_alt_accepted IN (0,1)),
    further_maths_valued    TEXT CHECK (further_maths_valued IN (
        'required','preferred','counts_as_third','not_mentioned')),
    gcse_requirements       TEXT,
    min_age                 INTEGER,
    eligibility_restrictions TEXT,  -- uk_resident_3yrs;uk_resident_5yrs;uk_national_only;right_to_work;none
    security_clearance      TEXT CHECK (security_clearance IN ('none','BPSS','CTC','SC','DV','unknown')),
    medical_required        INTEGER CHECK (medical_required IN (0,1)),
    predicted_grades_accepted INTEGER CHECK (predicted_grades_accepted IN (0,1)),
    grade_fit               TEXT CHECK (grade_fit IN ('above','meets','borderline','below')),
    -- pay and benefits
    salary_year1            INTEGER CHECK (salary_year1 >= 0),         -- GBP per year (converted if needed)
    salary_year1_local      INTEGER CHECK (salary_year1_local >= 0),   -- in `currency`
    currency                TEXT DEFAULT 'GBP',
    salary_final_year       INTEGER CHECK (salary_final_year >= 0),
    salary_notes            TEXT,
    tuition_paid            INTEGER NOT NULL DEFAULT 1 CHECK (tuition_paid IN (0,1)),
    pension_employer_pct    REAL,
    holiday_days            INTEGER,
    extra_benefits          TEXT,
    job_on_completion       TEXT CHECK (job_on_completion IN ('guaranteed','expected','not_stated')),
    tie_in_clause           TEXT,
    -- application process
    opens_date              TEXT,   -- YYYY-MM-DD or YYYY-MM
    closes_date             TEXT,
    closes_early_if_full    INTEGER CHECK (closes_early_if_full IN (0,1)),
    start_date              TEXT,
    application_url         TEXT NOT NULL,
    stages                  TEXT,
    intake_size             INTEGER,
    applicants_per_place    INTEGER,
    open_days               TEXT,
    -- source and housekeeping
    source                  TEXT NOT NULL CHECK (source IN (
        'employer_site','gov_find_apprenticeship','gov_wales_apprenticeship','ucas','higherin',
        'gradcracker','amazing_apprenticeships','ausbildung_de','ibec','job_board',
        'school_careers','word_of_mouth','other')),
    source_url              TEXT NOT NULL,
    faa_ref                 TEXT,   -- GOV.UK Find an Apprenticeship reference (VAC...)
    data_quality            TEXT NOT NULL CHECK (data_quality IN (
        'live_listing','register_interest','previous_cycle','secondary_source')),
    date_last_verified      TEXT NOT NULL,
    listing_status          TEXT NOT NULL CHECK (listing_status IN (
        'rumoured','expected','open','closed','withdrawn')),
    notes                   TEXT
);

CREATE TABLE applications (
    application_id          INTEGER PRIMARY KEY,
    programme_id            INTEGER NOT NULL UNIQUE REFERENCES programmes(programme_id),
    priority                INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    status                  TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN (
        'not_started','researching','in_progress','submitted','online_tests',
        'video_interview','assessment_centre','offer','accepted',
        'rejected','withdrawn','missed_deadline','declined')),
    date_started            TEXT,
    date_submitted          TEXT,
    next_action             TEXT,
    next_action_due         TEXT,
    test_results            TEXT,
    interview_date          TEXT,
    assessment_centre_date  TEXT,
    offer_type              TEXT CHECK (offer_type IN ('conditional','unconditional','none')),
    offer_conditions        TEXT,
    offer_deadline          TEXT,
    feedback                TEXT,
    contact_name            TEXT,
    contact_email           TEXT,
    fit_score               REAL CHECK (fit_score BETWEEN 0 AND 100),
    pros                    TEXT,
    cons                    TEXT
);

CREATE INDEX idx_prog_sector ON programmes(sector);
CREATE INDEX idx_prog_closes ON programmes(closes_date);
CREATE INDEX idx_prog_country ON programmes(country);

-- Live and expected schemes ordered by deadline (unknown deadlines last)
CREATE VIEW upcoming_deadlines AS
SELECT e.employer_name, p.programme_title, p.sector, p.relevance, p.country, p.work_location,
       p.closes_date, p.closes_early_if_full, p.listing_status,
       COALESCE(a.status,'not_started') AS status, a.priority, p.application_url
FROM programmes p
JOIN employers e USING (employer_id)
LEFT JOIN applications a USING (programme_id)
WHERE p.listing_status IN ('expected','open')
  AND COALESCE(a.status,'not_started') NOT IN ('rejected','withdrawn','declined','accepted')
ORDER BY p.closes_date IS NULL, p.closes_date;

-- Core UK degree apprenticeships that are open now
CREATE VIEW open_core_uk AS
SELECT e.employer_name, p.programme_title, p.sector, p.discipline, p.work_location, p.region,
       p.salary_year1, p.required_alevels, p.security_clearance, p.closes_date, p.application_url
FROM programmes p JOIN employers e USING (employer_id)
WHERE p.country = 'GB' AND p.relevance = 'core' AND p.listing_status = 'open' AND p.level >= 6
ORDER BY p.closes_date IS NULL, p.closes_date;

-- Options outside the UK, easiest to access first
CREATE VIEW international AS
SELECT e.employer_name, p.programme_title, p.country, p.work_location, p.uk_citizen_work_route,
       p.language_required, p.salary_year1, p.salary_year1_local, p.currency, p.listing_status, p.application_url
FROM programmes p JOIN employers e USING (employer_id)
WHERE p.country <> 'GB'
ORDER BY CASE p.uk_citizen_work_route WHEN 'cta_free' THEN 0 WHEN 'residence_permit' THEN 1 ELSE 2 END,
         p.country, e.employer_name;

-- Per-sector overview
CREATE VIEW sector_summary AS
SELECT sector, COUNT(*) AS programmes,
       SUM(listing_status='open') AS open_now,
       SUM(relevance='core') AS core,
       ROUND(AVG(salary_year1)) AS avg_salary_gbp
FROM programmes GROUP BY sector ORDER BY programmes DESC;

-- To-do list built from next_action
CREATE VIEW todo AS
SELECT a.next_action_due, a.next_action, e.employer_name, p.programme_title
FROM applications a
JOIN programmes p USING (programme_id)
JOIN employers e USING (employer_id)
WHERE a.next_action IS NOT NULL
ORDER BY a.next_action_due IS NULL, a.next_action_due;
