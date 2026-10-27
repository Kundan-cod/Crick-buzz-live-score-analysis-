# Master Tasks & Implementation Roadmap (TASKS.md)

## Project: Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics
- **Status:** Phase 0 (Documentation-First Initialization) Completed; Awaiting User Approval to start Stage 1.
- **Implementation Strategy:** Offline-Fixture First; Real API Integration Deferred to Stage 11.
- **Workflow:** Sequential delivery with phase gates, educational explanations, and explicit user confirmation.
- **Last Updated:** 2026-10-22

---

## Status Legend
- `[ ]` **Unstarted:** Pending prior stage completion and user gate approval.
- `[-]` **In Progress:** Currently being executed within the approved scope.
- `[x]` **Completed:** Verified with actual shell execution / inspection evidence.
- `[!]` **Pending Review / Blocked:** Awaiting user decision or external dependency.

---

## Phase 0: Documentation-First Initialization & Reconciliation (Gate 0)

| Task ID | Task Description | Dependencies | Priority | Acceptance Criteria | Status | Blockers |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **T0.1** | Inspect workspace files (`Cricbuzz.docx`, `Prompt to be used in Claude.docx`) | None | High | Full text extracted, requirements identified | `[x]` | None |
| **T0.2** | Author & Reconcile `docs/PRD.md` | T0.1 | High | Comprehensive PRD covering scope, NFRs, deliverables, open questions | `[x]` | None |
| **T0.3** | Author & Reconcile `docs/ARCHITECTURE.md` | T0.1 | High | Layered architecture, component responsibilities, data flows, diagram | `[x]` | None |
| **T0.4** | Author & Reconcile `docs/DESIGN.md` | T0.1 | High | Page map (including Settings), visual tokens, KPI cards, tables, charts | `[x]` | None |
| **T0.5** | Author & Reconcile `docs/RULES.md` | T0.1 | High | PEP 8, OOP/modular rules, database safety, API rules, testing standards | `[x]` | None |
| **T0.6** | Author & Reconcile `docs/TASKS.md` | T0.1 | High | 11-stage master implementation roadmap aligned with confirmed workflow | `[x]` | None |
| **T0.7** | Author & Reconcile `docs/DECISIONS.md` | T0.1 | High | ADR format with confirmed SQLite, Settings, offline-first, Q21 pending | `[x]` | None |
| **T0.8** | Author & Reconcile `docs/MEMORY.md` | T0.1-T0.7 | High | Durable project context, active phase, next steps | `[x]` | None |
| **T0.9** | Review documentation consistency & present Phase 0 report | T0.1-T0.8 | High | All 7 documents verified; stop and wait for user approval | `[x]` | Awaiting User Approval |

---

## Master Implementation Sequence (Stages 1 to 11)

### Stage 1: Project Structure & Configuration Finalization
*Objective: Establish clean modular folders, dependency management, and configuration loading.*
- **Files to create/change:** `config.py`, `requirements.txt`, `.gitignore`, `.env.example`, `__init__.py` files in subpackages.
- **Concepts:** Environment configuration, dependency pinning, Git secret hygiene.
- **Acceptance Criteria:** Directory tree matches approved structure; `config.py` loads environment variables safely; no secrets committed.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T1.1** | Initialize modular folder hierarchy (`database/`, `services/`, `pages/`, `utils/`, `sql/`, `data/`, `tests/`) | `[x]` |
| **T1.2** | Create `requirements.txt` with pinned dependencies (`streamlit`, `pandas`, `pytest`, `python-dotenv`, `plotly`) | `[x]` |
| **T1.3** | Create `.env.example` and update `.gitignore` to protect databases, logs, and environments | `[x]` |
| **T1.4** | Implement `config.py` with typed configuration settings and SQLite path management | `[x]` |

---

### Stage 2: SQLite Database Schema & Connection Layer
*Objective: Build an ACID-compliant, normalized relational schema in SQLite with strict foreign keys.*
- **Files to create/change:** `database/connection.py`, `sql/schema.sql`, `sql/views.sql`.
- **Concepts:** 3NF relational modeling, foreign key pragma, transaction context managers.
- **Acceptance Criteria:** `connection.py` enforces `PRAGMA foreign_keys = ON;`; `schema.sql` creates all tables with constraints without errors.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T2.1** | Implement `database/connection.py` with thread-safe SQLite connection handling & transaction contexts | `[x]` |
| **T2.2** | Implement `sql/schema.sql` (Teams, Players, Venues, Series, Matches, Innings, Batting, Bowling, Fielding, Partnerships) | `[x]` |
| **T2.3** | Implement `sql/views.sql` for common analytical projections (match summaries, player career totals) | `[x]` |

---

### Stage 3: Schema Validation & Database Initialization
*Objective: Automate database bootstrapping, health checks, and migration-safe initialization.*
- **Files to create/change:** `database/init_db.py`, `tests/test_database.py`.
- **Concepts:** DDL execution pipelines, schema verification, programmatic constraint testing, cricket overs ball-math.
- **Acceptance Criteria:** `init_db.py` creates tables idempotently; automated tests verify primary keys, foreign keys, cascading behavior, and validation checks.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T3.1** | Implement `database/init_db.py` to bootstrap and validate SQLite database from SQL scripts safely | `[x]` |
| **T3.2** | Implement and execute `tests/test_init_db.py` verifying fresh init, repeated init, cricket overs math, and no join multiplication | `[x]` |

---

### Stage 4: Small, Clearly Labelled Offline Dataset
*Objective: Populate the database with verified, realistic, clearly labelled sample cricket data to power all 25 queries and CRUD operations.*
- **Files to create/change:** `data/seed_data.py`, `data/fixtures/sample_matches.json`.
- **Concepts:** Test fixture design, domain-accurate cricket scoring data, data labeling governance, idempotent seeding.
- **Acceptance Criteria:** Seed data populates test players, matches, innings, and performances; all data explicitly tagged with `source = 'LOCAL'`; zero fabricated claims of live data.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T4.1** | Create `data/seed_data.py` containing representative international teams, players, venues, and series | `[x]` |
| **T4.2** | Populate match scorecards across Test, ODI, and T20I formats supporting analytical query criteria | `[x]` |
| **T4.3** | Verify seeded records via database queries; verify referential integrity across all relationships | `[x]` |

---

### Stage 5: Database Operations & CRUD Functionality Verification
*Objective: Implement and test robust Create, Read, Update, and Delete operations with constraint safety.*
- **Files to create/change:** `services/crud_service.py`, `utils/validators.py`, `tests/test_crud.py`.
- **Concepts:** Parameterized SQL, validation rules, referential integrity preservation, soft deletion.
- **Acceptance Criteria:** Valid records can be created/updated; invalid records are rejected; players with existing match appearances cannot be destructively deleted.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T5.1** | Implement `utils/validators.py` for player, venue, and match input sanitization and domain rule checks | `[x]` |
| **T5.2** | Implement `services/crud_service.py` with parameterized CRUD methods, transaction safety, and FK protection | `[x]` |
| **T5.3** | Implement and execute `tests/test_crud.py` covering valid inputs, edge cases, duplicate rejection, and FK protection | `[x]` |

---

### Stage 6: The 25 SQL Analytics Questions (Batch Implementation Complete)
*Batch Implementation: All 25 queries implemented as modular SQL files in `sql/queries/q01.sql` through `q25.sql`, registered in `analytics/query_runner.py`, and verified with 85 automated tests. Q21 formula-dependent logic remains strictly marked as PENDING REVIEW.*
- **Files created/changed:** `sql/queries/q01.sql` through `q25.sql`, `analytics/query_runner.py`, `tests/test_query_runner.py`, `tests/test_queries.py`.
- **Status:** `[x] Completed (Q1–Q25 Implemented & Tested; Q21 Formula PENDING REVIEW)`

#### Stage 6 Data Limitations & Fixture Expansion Log:
| Query | Original Requirement Constraint | Current Dev DB Status | Isolated Test Status | Required Fixture Expansion for Dev DB |
| :--- | :--- | :--- | :--- | :--- |
| **Q02** | Matches in last 30 days | 0 rows (matches dated 2022–2024) | Tested (5 date boundary fixtures) | Add rolling fixtures matching runtime date |
| **Q09** | All-rounders >1000 runs & >50 wickets | 0 rows (highest runs ~230, wickets ~10) | Tested (10 matches, 1250 runs, 60 wkts) | Add high-volume career stats |
| **Q14** | Bowlers with ≥3 matches at same venue | 0 rows (12 matches spread across 10 venues) | Tested (3 matches at venue, 4 ov spells) | Add 3+ bowling spells at single venue |
| **Q16** | Yearly batting trends (≥5 matches/year) | 0 rows (max matches/year for player is 3) | Tested (5 matches in 2023) | Add ≥5 matches/player in a single year |
| **Q18** | Bowlers with ≥10 limited-overs matches | 0 rows (6 limited overs matches total) | Tested (10 ODI matches, 3.0 econ) | Add 10+ limited-overs bowling appearances |
| **Q20** | Players with ≥20 matches across formats | 0 rows (12 matches total in DB) | Tested (10 Tests + 10 ODIs = 20 matches) | Add 20+ matches for marquee players |
| **Q21** | Weighted player ranking | 22 rows returned (Batting/Fielding pts) | Tested (`PENDING REVIEW` status flag) | Formula review required before composite score |
| **Q22** | Team pairs with ≥5 matches in last 3 years | 0 rows (highest bilateral pair is 4 matches) | Tested (5 matches between Team A & B) | Add 5+ bilateral matches between rivalry pair |
| **Q24** | Batting partnerships with ≥5 stands | 0 rows (5 total partnerships in DB) | Tested (5 partnerships between 2 batsmen) | Add 5+ partnerships for specific pair |
| **Q25** | Quarterly career trajectory (≥6 quarters) | 0 rows (12 matches across 4 quarters) | Tested (6 quarters, 3 matches/quarter) | Add multi-year longitudinal quarterly data |

#### The 25 SQL Analytical Queries Sequence:

| Task ID | Question & Focus | Level | Status | Dev DB Rows | Execution Plan & Key Concepts |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **T6.1** | **Q1:** India players (full name, role, styles) | Beginner | `[x]` | 11 rows | Index scan `idx_players_country`, deterministic sort |
| **T6.2** | **Q2:** Matches in the last 30 days | Beginner | `[x]` | 0 rows* | Index range scan `idx_matches_date`, date boundaries |
| **T6.3** | **Q3:** Top 10 ODI run scorers (runs, avg, 100s) | Beginner | `[x]` | 10 rows | Covering index `idx_matches_format`, safe avg, NULLIF |
| **T6.4** | **Q4:** Large venues > 50,000 capacity | Beginner | `[x]` | 4 rows | Strict capacity filter (`> 50000`), sorted DESC |
| **T6.5** | **Q5:** Team wins count (handling ties/no-results) | Beginner | `[x]` | 6 rows | `LEFT JOIN` on completed matches, handles 0-win teams |
| **T6.6** | **Q6:** Player counts by playing role | Beginner | `[x]` | 4 rows | Covering index `idx_players_role`, role breakdown |
| **T6.7** | **Q7:** Highest individual score by format | Beginner | `[x]` | 2 rows | `ROW_NUMBER() OVER (PARTITION BY format)`, Head 137 |
| **T6.8** | **Q8:** Series started in 2024 | Beginner | `[x]` | 4 rows | Date filtering `2024-01-01` to `2024-12-31` |
| **T6.9** | **Q9:** All-rounders (>1,000 runs AND >50 wickets) | Intermediate | `[x]` | 0 rows* | CTE pre-aggregation prevents Cartesian multiplication |
| **T6.10** | **Q10:** Last 20 completed matches with margins | Intermediate | `[x]` | 12 rows | Index scan `idx_matches_date`, multiple team lookups |
| **T6.11** | **Q11:** Cross-format player performance (combined avg) | Intermediate | `[x]` | 4 rows | Conditional aggregation, multi-format `HAVING >= 2` |
| **T6.12** | **Q12:** Home vs. away performance comparison | Intermediate | `[x]` | 5 rows | Venue country vs team country comparison |
| **T6.13** | **Q13:** Consecutive batting-position pairs (sum ≥ 100) | Intermediate | `[x]` | 9 rows | Self-join on adjacency `bp2.position = bp1.position + 1` |
| **T6.14** | **Q14:** Venue bowling analysis (economy, wickets) | Intermediate | `[x]` | 0 rows* | True weighted economy, overs formatting from balls |
| **T6.15** | **Q15:** Players in close matches (<50 runs or <5 wkts) | Intermediate | `[x]` | 18 rows | Margin boolean filter, clutch batting performance |
| **T6.16** | **Q16:** Yearly batting trends since 2020 (avg, SR) | Intermediate | `[x]` | 0 rows* | Annual trend grouping `STRFTIME('%Y')`, min 5 matches |
| **T6.17** | **Q17:** Toss advantage analysis (bat vs bowl first) | Advanced | `[x]` | 2 rows | Segmented toss decision win rate percentages |
| **T6.18** | **Q18:** Economical limited-overs bowlers | Advanced | `[x]` | 0 rows* | Limited-overs filter, workload threshold (≥12 balls/m) |
| **T6.19** | **Q19:** Batting consistency (standard deviation) | Advanced | `[x]` | 6 rows | Pure SQL sample stddev `SQRT((SUM(x^2)-...)/(N-1))` |
| **T6.20** | **Q20:** Matches and averages by format | Advanced | `[x]` | 0 rows* | Pivot format averages, high appearance gate (≥20 m) |
| **T6.21** | **Q21:** Weighted player ranking *(Formula PENDING REVIEW)* | Advanced | `[!]` | 22 rows | Underlying metrics structured; composite PENDING REVIEW |
| **T6.22** | **Q22:** Team head-to-head match prediction | Advanced | `[x]` | 0 rows* | Canonical pairing `MIN(team1, team2)`, rolling 3-yr |
| **T6.23** | **Q23:** Recent player form (last 5 vs last 10, form tiers) | Advanced | `[x]` | 18 rows | Window function `ROW_NUMBER()`, momentum tiers |
| **T6.24** | **Q24:** Batting partnerships (averages, 50s, success rate) | Advanced | `[x]` | 0 rows* | Canonical batsman pairing, success rate percentage |
| **T6.25** | **Q25:** Quarterly career trajectory (time-series trends) | Advanced | `[x]` | 0 rows* | `LAG()` window function, quarter calculation, phase |

*\* Note: Queries marked with 0 rows* on the local development database represent genuine data volume limitations of the 12-match sample dataset. All such queries have been verified with isolated test fixtures in `tests/test_queries.py`.*

---

### Stage 7: Incremental Streamlit Page Development
*Objective: Build the multi-page web application page by page using the modern cricket design system.*
- **Files to create/change:** `app.py`, `pages/1_Live_Matches.py`, `pages/2_Top_Players.py`, `pages/3_SQL_Analytics.py`, `pages/4_CRUD_Operations.py`, `pages/5_Settings.py`, `.streamlit/config.toml`, `utils/theme.py`, `utils/charts.py`, `tests/test_ui.py`.
- **Status:** `[x] Completed (All 6 Pages, Dark Theme, 102/102 Tests Passing, UI Verified)`

| Task ID | Page Module | Components & Scope | Status |
| :--- | :--- | :--- | :---: |
| **T7.1** | **Home (`app.py`)** | Architecture blueprint, live SQLite metrics, recent match cards, breakdowns, quick links | `[x]` |
| **T7.2** | **Live Matches (`pages/1_Live_Matches.py`)** | Match center, format/status/team filters, match cards, full innings scorecards | `[x]` |
| **T7.3** | **Top Players (`pages/2_Top_Players.py`)** | Batting/bowling leaderboards, format tabs, player profile spotlight, search filters | `[x]` |
| **T7.4** | **SQL Analytics (`pages/3_SQL_Analytics.py`)** | 25 queries runner, difficulty filter, chart visualizer, EXPLAIN QUERY PLAN, Q21 review banner | `[x]` |
| **T7.5** | **CRUD Operations (`pages/4_CRUD_Operations.py`)** | Form-based CRUD for Players, Venues, and Matches with validation and safe deletion | `[x]` |
| **T7.6** | **Settings (`pages/5_Settings.py`)** | SQLite integrity & FK diagnostics, row counts grid, environment info, cache clear | `[x]` |
| **T7.7** | **Runtime Bug Fixes (Stage 7.1)** | Fixed `get_connection()` context manager in all pages, resolved `undefined` chart titles, verified live browser UI | `[x]` |

---

### Stage 8: End-to-End Quality Assurance & Data Validation
*Objective: Comprehensive quality audit of Cricbuzz LiveStats across all 25 SQL queries, database integrity, 6 UI pages, realistic workflows, and API readiness.*
- **Files created/changed:** `analytics/query_runner.py` (ASCII cp1252 fix), `tests/test_workflows.py`, `tests/test_query_runner.py`, `utils/logger.py`.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T8.1** | **Validate all 25 SQL Queries**: Checked query logic, joins, aggregations, anti-Cartesian safety, cricket math (overs/economy/strike rate), zero-row threshold callouts, and Q21 `PENDING REVIEW` status | `[x]` |
| **T8.2** | **Database Integrity & CRUD Validation**: Verified `PRAGMA integrity_check` (ok), `PRAGMA foreign_key_check` (0 violations), transaction rollbacks, API-source protections, and idempotent seeding | `[x]` |
| **T8.3** | **UI & Realistic Workflows**: Verified all 6 UI pages, added `tests/test_workflows.py` exercising 6 operational workflows on isolated temporary DB, added `utils/logger.py` with log rotation (`logs/app.log`) | `[x]` |
| **T8.4** | **Defect Remediation & Regression Testing**: Fixed Unicode mathematical symbols (`≥`) in `analytics/query_runner.py` for Windows cp1252 compatibility; added ASCII encode regression test; 109/109 tests passing | `[x]` |

---

### Stage 9: Comprehensive Application Testing & Verification
*Objective: Execute end-to-end test suite and document real verification evidence.*
- **Files created/changed:** `tests/test_workflows.py`, `tests/test_query_runner.py`, `tests/test_ui.py`.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T9.1** | Run full `pytest` suite across database, CRUD, services, queries, and workflows (109 passed in 12.33s); record shell output | `[x]` |
| **T9.2** | Conduct manual UI walkthrough of all 6 Streamlit pages; verify responsive layout, forms, charts, and save verified screenshots | `[x]` |

---

### Stage 10: Deployment Instructions & Technical Interview Preparation
*Objective: Provide complete deployment configuration, operations runbook, and the 50-question technical viva preparation guide.*
- **Files created/changed:** `README.md`, `DEPLOYMENT.md`, `documentation/DEPLOYMENT.md`, `INTERVIEW_PREP.md`, `documentation/INTERVIEW_PREP.md`, `assets/screenshots/`.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T10.1** | Create comprehensive `README.md` with setup, architecture, schema, query catalog, verified screenshots, and running instructions | `[x]` |
| **T10.2** | Create deployment guide (`DEPLOYMENT.md`) covering local venv, Streamlit Community Cloud, Docker, secret management, and troubleshooting | `[x]` |
| **T10.3** | Author 50-question technical viva and interview guide (`INTERVIEW_PREP.md`) matching actual code implementation across 8 distinct categories | `[x]` |

---

### Stage 11: API Investigation & Integration Layer
*Objective: Investigate free cricket APIs, build a provider-independent client architecture, audit implementation readiness, and prepare ingestion pipelines.*
- **Files created/changed:** `api/base_client.py`, `api/cricketdata_client.py`, `api/cricbuzz_client.py`, `api/parser.py`, `api/factory.py`, `services/ingestion_service.py`, `pages/1_Live_Matches.py`, `pages/5_Settings.py`, `tests/test_api.py`, `documentation/API_INVESTIGATION.md`.
- **Status:** `[x] Completed (Stage 11A Architecture, Stage 11B Readiness Audit, Stage 11C Final Workflow Verification Verified; 139/139 Tests Passing)`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T11.1** | **API Investigation & Evaluation**: Evaluated CricketData.org vs RapidAPI; recommended CricketData.org (100 hits/day, zero payment info) | `[x]` |
| **T11.2** | **Provider-Independent Client Layer**: Implemented `BaseCricketClient`, `SimpleTTLCache` (60s TTL), and custom exceptions (`MissingAPIKeyError`, `RateLimitExceededError`) | `[x]` |
| **T11.3** | **Concrete Provider Clients**: Built `CricketDataClient` (free endpoint integration, quota telemetry tracking) and `CricbuzzRapidAPIClient` | `[x]` |
| **T11.4** | **Response Parser & Overs Math**: Implemented `CricketDataParser` mapping matches, innings totals, batting, and bowling scores with true overs math (rollovers, 4.2=26 balls), outcome parsing (winner, margin, type), and `source='API'` | `[x]` |
| **T11.5** | **Transactional Ingestion Service**: Built `IngestionService` with `ingest_match()` and `ingest_scorecard()`, atomic transactions, and ADR-006 protection of LOCAL fixtures | `[x]` |
| **T11.6** | **Mocked Test Suite**: Implemented automated unit and integration tests with mocked HTTP responses in `tests/test_api.py` | `[x]` |
| **T11.7** | **API Readiness Audit (Stage 11B)**: Verified official docs, audited client/parser/service/schema/UI, resolved 4 defects, added regression tests, documented safe enablement steps | `[x]` |
| **T11.8** | **Final Workflow Verification (Stage 11C)**: Traced full workflow, verified schema mapping, added repeated-polling idempotency protections, added incomplete response guards (status downgrade defense, outcome persistence, non-empty innings protection), added UI sync actions (`🔄 Sync Live Feed`, `🔄 Sync Innings Feed`, `🔌 Test Connection`), rendered timestamps and source badges, added 7 regression tests (30/30 API tests, 139/139 full suite passing) | `[x]` |

---

### Stage 12: Live API Integration & Match Synchronization

#### Stage 12A: First CricketData.org API Smoke Test
*Objective: Safely verify live connectivity to CricketData.org using configured API credentials without exposing keys or triggering bulk sync.*
- **Files created/changed:** `documentation/API_INVESTIGATION.md`, `docs/TASKS.md`, `docs/MEMORY.md`.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T12A.1** | **Configuration & Credential Verification**: Checked `.env` existence and verified non-empty, non-placeholder API key without exposing/logging credentials | `[x]` |
| **T12A.2** | **Minimal Non-Destructive Connection Test**: Executed single `client.test_connection()` call against `GET https://api.cricapi.com/v1/currentMatches` | `[x]` |
| **T12A.3** | **Telemetry & Quota Reporting**: Verified HTTP 200 OK, confirmed 25 active fixtures returned, tracked provider quota (13 used / 100 limit, 87 remaining) | `[x]` |
| **T12A.4** | **Database & Fixture Safeguard Verification**: Confirmed SQLite schema unmodified, 12 LOCAL demo fixtures preserved under ADR-006, 139/139 automated tests passing | `[x]` |
| **T12A.5** | **Safe Documentation Update & Gate Stop**: Updated documentation with redacted credentials; halted before full match sync per Stage 12A requirements | `[x]` |

#### Stage 12B: User-Controlled Live Match Synchronization
*Objective: Execute controlled live match list synchronization through application's existing Live Matches UI workflow.*
- **Files created/changed:** `documentation/API_INVESTIGATION.md`, `docs/TASKS.md`, `docs/MEMORY.md`.
- **Status:** `[x] Completed`

| Task ID | Task Description | Status |
| :--- | :--- | :---: |
| **T12B.1** | **Safety & Implementation Inspection**: Inspected UI workflow in `pages/1_Live_Matches.py`, checked quota certainty (15 used, 85 remaining), verified ADR-006 protections | `[x]` |
| **T12B.2** | **Controlled Live Match Feed Synchronization**: Ran intended `Sync Live Feed` workflow once; received 25 fixtures, 0 inserted, 25 updated, 0 skipped, 0 failed; zero scorecards auto-fetched | `[x]` |
| **T12B.3** | **Source Segregation & Immutability Verification**: Verified 25 matches tagged `source='API'` with timestamps, 12 LOCAL demo fixtures preserved untouched | `[x]` |
| **T12B.4** | **Database & Constraint Integrity Check**: Executed `PRAGMA foreign_key_check` (0 violations) and `PRAGMA integrity_check` (ok); schema intact | `[x]` |
| **T12B.5** | **Live Matches UI Query & Label Verification**: Confirmed query accurately distinguishes and labels `📡 API Feed` vs `💾 LOCAL Demo` | `[x]` |
| **T12B.6** | **Test Suite Regression Check**: Verified 30/30 API tests and 139/139 full suite tests passing in 13.33s | `[x]` |
| **T12B.7** | **Documentation Update**: Updated `API_INVESTIGATION.md`, `TASKS.md`, and `MEMORY.md` with complete metrics, redacted credentials, and operational boundaries | `[x]` |

