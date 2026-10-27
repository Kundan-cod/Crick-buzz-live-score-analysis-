# Durable Project Context & State (MEMORY.md)

## Project: Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics
- **Role:** Senior Software Architect, Python Developer, Data Engineer, SQL Expert, Streamlit Developer, QA Engineer & Project Mentor
- **Current State:** Stage 11 Live API Integration Active (Key Verified, Live Feed & Scorecards Ingested, 139/139 Tests Passing, ADR-006 Preserved; Q21 Formula PENDING REVIEW)
- **Current System Date:** 2026-10-23
- **Last Updated:** 2026-10-23

---

## 1. Project Objective
Build a comprehensive, modular sports analytics web platform integrating:
- A normalized relational SQLite database (`data/cricbuzz.db`) with strict foreign key constraints and transaction safety.
- Clearly labelled offline test fixtures (`data/fixtures/` and `seed_data.py`) powering development, testing, and demo.
- Real Cricbuzz REST API integration added in Stage 11 after provider details, endpoints, and terms are verified.
- An interactive Streamlit multi-page web application featuring Home, Live Matches, Top Player Stats, SQL Analytics, CRUD Operations, and Settings.
- Complete, educational execution of 25 specified SQL analytical questions covering beginner, intermediate, and advanced levels.
- A 50-question technical viva preparation guide, deployment configuration, and demo recording checklist.

---

## 2. Current Phase & Mentoring Gate Status
- **Current Phase:** Stage 12B: First Real Match Synchronization (Completed; Live Feeds Active & Verified)
- **Gate Status:** Live matches feed synchronized once via existing `Sync Live Feed` workflow (`get_live_matches` + `ingest_match`). 25 fixtures received, 0 inserted, 25 updated, 0 skipped, 0 failed. Quota verified (15 used / 85 remaining of 100/day limit). All 12 LOCAL demo fixtures preserved under ADR-006. Database integrity verified (0 FK violations, integrity 'ok'). 139/139 automated tests passing.

---

## 3. Confirmed Decisions & Review Items

| ID | Title | Status | Summary |
| :--- | :--- | :---: | :--- |
| **ADR-001** | Documentation-First Governance | `Accepted` | Complete documentation suite verified before writing application code |
| **ADR-002** | Multi-Page Streamlit Structure | `Accepted` | Streamlit native `pages/` directory with separated `services/` backend |
| **ADR-003** | Database Engine Selection | `Accepted` | SQLite (`data/cricbuzz.db`) confirmed for local development |
| **ADR-004** | Phased API & Offline Fixtures | `Accepted` | Build offline-fixture mode first; integrate real API in Stage 11; sample data never presented as live |
| **ADR-005** | Q21 Formula Disambiguation | `Pending Review` | Bowling points formula held as PENDING REVIEW; will be formally reviewed in Stage 6 Q21 |
| **ADR-006** | CRUD Scope & Protection | `Accepted` | Source segregation (`'API'` read-only vs `'LOCAL'` editable) with FK checks |
| **ADR-007** | Settings Page Inclusion | `Accepted` | Include safe diagnostic & cache-monitoring page in `pages/5_Settings.py` |
| **ADR-008** | Execution Focus & Timeline | `Accepted` | Finish rapidly without sacrificing quality; eliminate deadline anxiety |

---

## 4. Current Workspace & Documentation Structure

```
e:/Cricbuzz/
├── Cricbuzz.docx                  # Primary project specification
├── Prompt to be used in Claude.docx # Primary mentoring instructions
├── Retail_Arcade.html             # Pre-existing workspace asset (unmodified)
└── docs/                          # Verified Documentation Suite
    ├── PRD.md                     # Business problem, requirements, 25 SQL questions, NFRs
    ├── ARCHITECTURE.md            # Decoupled layered architecture, components, ERD, data flow
    ├── DESIGN.md                  # Design system, visual tokens, layout, KPI cards, charts
    ├── RULES.md                   # Engineering standards, PEP 8, SQL safety, testing, anti-fabrication
    ├── TASKS.md                   # 11-stage master implementation roadmap with granular tasks
    ├── DECISIONS.md               # Architectural Decision Records (ADRs 001–008)
    └── MEMORY.md                  # Durable project state, active phase, next steps
```

---

## 5. Completed & Verified Work (Phase 0)

1. **Workspace Inspection:**
   - Extracted and verified full text of `Cricbuzz.docx` and `Prompt to be used in Claude.docx`.
   - Verified that `Retail_Arcade.html` is an unrelated existing asset and left it intact.
2. **Documentation Suite Creation & Reconciliation:**
   - Updated `DECISIONS.md` and `TASKS.md` to record confirmed decisions and the 11-stage sequence.
   - Reconciled `PRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `RULES.md`, and `MEMORY.md`.
   - Verified that all 25 SQL practice questions are cataloged.
   - Verified that all 6 Streamlit pages (Home, Live Matches, Top Players, SQL Analytics, CRUD, Settings) are documented.
   - Verified that sample data labeling rules are strict: never present fixture data as live cricket data.
   - Verified that Q21 bowling points formula is explicitly marked as **PENDING REVIEW**.
3. **Stage 1 (Project Structure & Configuration Finalization):**
   - Initialized modular directory tree: `database/`, `services/`, `pages/`, `utils/`, `sql/queries/`, `data/fixtures/`, `tests/`, `logs/`, `assets/`, `documentation/`, `api/`.
   - Created `requirements.txt` with pinned versions (`streamlit`, `pandas`, `plotly`, `requests`, `python-dotenv`, `pytest`).
   - Created `.env.example` template with default `OFFLINE_MODE=True` and clear placeholders.
   - Initialized `.gitignore` protecting `.env`, `*.db`, `logs/`, and caches.
   - Initialized Git repository and verified secrets/database exclusion.
   - Implemented `config.py` with typed configuration dataclasses and path helpers. Verified clean import and path resolution.
4. **Stage 2 (SQLite Database Schema & Connection Layer):**
   - Implemented `database/connection.py`: Thread-safe SQLite connection manager with connection and transaction context managers, enforcing `PRAGMA foreign_keys = ON;`, WAL mode, and `sqlite3.Row` factory.
   - Implemented `sql/schema.sql`: 3NF normalized schema for 10 core tables (`teams`, `players`, `venues`, `series`, `matches`, `innings`, `batting_performances`, `bowling_performances`, `fielding_performances`, `partnerships`) with CHECK constraints, foreign keys, and indexes.
   - Implemented `sql/views.sql`: 5 reusable analytical views (`v_match_details`, `v_innings_summary`, `v_player_batting_by_format`, `v_player_bowling_by_format`, `v_player_career_totals`).
   - Implemented and executed `tests/test_database.py`: 9 focused pytest tests verifying table/view creation, foreign key enforcement, CHECK constraints, UNIQUE constraints, transaction rollback on failure, and cascade deletion. 100% passed (9 of 9).
5. **Stage 3 (Schema Validation & Database Initialization):**
   - Implemented `database/init_db.py`: CLI and module supporting safe, idempotent database bootstrapping, structural validation, PRAGMA integrity_check, foreign keys check, and detailed health reporting.
   - Preserved existing data: Clearly distinguishes fresh initialization from validation of existing databases; never silently wipes data.
   - Fixed domain cricket overs math in `sql/schema.sql` and `sql/views.sql`: Added `balls_bowled` to prevent decimal notation trap (e.g. 3.4 overs is 22 balls, not 3.4 decimal float; 3.4 + 2.4 overs = 6.2 overs, not 5.8).
   - Validated analytical views: Pre-aggregation in `v_player_career_totals` verified to prevent Cartesian join multiplication and inflated statistics.
   - Implemented `tests/test_init_db.py`: 7 automated tests covering fresh init, repeated init, force recreation, missing file detection, cricket overs ball-math, and join multiplication checks.
    - Ran complete pytest suite across `test_database.py` and `test_init_db.py`: 16 tests passed out of 16 (100% pass rate).
6. **Stage 4 (Small, Clearly Labelled Offline Dataset):**
   - Designed documented fixture JSON structure in `data/fixtures/sample_matches.json` with metadata tags (`source: LOCAL`, synthetic disclaimer, format mapping).
   - Implemented `data/seed_data.py`: Idempotent seeder populating all 10 tables (`teams`, `players`, `venues`, `series`, `matches`, `innings`, `batting_performances`, `bowling_performances`, `fielding_performances`, `partnerships`) using `ON CONFLICT DO UPDATE` upserts within transactions without dropping or recreating the database.
   - Populated realistic, internally consistent records across Test, ODI, and T20I formats: 6 teams, 35 players, 10 venues, 10 series, 12 matches (spanning 2020–2026), 12 innings, 30 batting records, 18 bowling records, 8 fielding records, 5 partnerships.
   - Verified zero foreign-key integrity violations using SQLite `PRAGMA foreign_key_check`.
   - Verified strict idempotency: running `seed_database()` twice yields identical row counts.
   - Assessed analytics readiness across all 25 SQL queries, documenting query criteria coverage and noting queries that need additional historical records in Stage 6.
   - Implemented `tests/test_seed_data.py`: 4 automated tests verifying table population, zero FK violations, strict idempotency, and scenario coverage.
   - Total test suite: 20 passed out of 20 (100% pass rate).
7. **Stage 5 (Database Operations & CRUD Functionality Verification):**
   - Implemented `utils/validators.py`: Input validators for players, venues, and matches enforcing schema constraints (roles, styles, ISO dates, unique non-identical teams, non-negative capacity, toss/win conditions).
   - Implemented `services/crud_service.py`: Parameterized CRUD service for Players, Venues, and Matches with transactional safety, custom exceptions (`ValidationError`, `RecordNotFoundError`, `DuplicateRecordError`, `ProtectedRecordError`, `ReadOnlyRecordError`), foreign-key dependency verification, soft-delete via `is_active`, and API source segregation (ADR-006).
   - Implemented `tests/test_crud.py`: 30 unit and integration tests executing against isolated temporary databases (`tmp_path`), verifying valid operations, invalid inputs, duplicate rejection, soft-deletion, foreign-key protection, cascade deletion with confirmation, and transaction rollbacks.
   - Completed audit of Stage 4 data coverage for Stage 6: Identified exact historical sequence additions required for Q10 (20 matches), Q14 (≥3 matches at venue), Q19 (≥10 balls faced innings for stddev), Q22 (≥5 head-to-head matches), and Q23 (10 consecutive chronological innings for form curves). Recorded as pre-requisite subtasks in `docs/TASKS.md`.
   - Total test suite: 50 passed out of 50 (100% pass rate). Development database `data/cricbuzz.db` verified completely unmodified.
8. **Stage 6 (SQL Analytics — Batch Implementation of All 25 Questions):**
   - Implemented all 25 individual SQL query files (`sql/queries/q01.sql` through `q25.sql`) with student-friendly documentation, business context, execution plan notes, and safe division handling (`NULLIF`).
   - Implemented `analytics/query_runner.py`: Whitelisted query execution catalog, parameter validation, execution timing, Pandas DataFrame conversion, and `EXPLAIN QUERY PLAN` introspection.
   - Preserved ADR-005 governance for Q21: Structured underlying batting, bowling, and fielding metrics; explicitly held formula-dependent composite ranking as `PENDING REVIEW`.
   - Implemented `tests/test_queries.py`: 23 comprehensive tests covering all 23 new queries (Q03–Q25), join multiplication protection, standard deviation mathematical accuracy against `statistics.stdev`, overs formatting from balls bowled, boundary conditions, and isolated volume fixtures.
   - Total test suite: **85 passed out of 85 (100% pass rate)**.
   - All 25 queries executed against development database `data/cricbuzz.db` in 1.1ms to 4.5ms without a single error.
9. **Stage 7 (Streamlit Multi-Page UI Development):**
   - Configured `.streamlit/config.toml` with Midnight Cricket (`#0B1220`) + Electric Lime (`#B7F34A`) palette, dark cards (`#17243A`), and Inter typography.
   - Built shared theme & UI components in `utils/theme.py`: Custom CSS injection, brand header, KPI metric cards with subtitles/badges, status badges, offline warning banners, and sidebar brand block.
   - Built chart visualization library in `utils/charts.py`: Plotly helpers for bar, horizontal bar, donut, line, scatter, and grouped bar charts in consistent midnight-lime styling.
   - Implemented `app.py` (Home Dashboard): Real SQLite metrics (teams, players, matches, venues, analytics queries), quick links, recent matches, format & team distribution charts, architecture blueprint, and offline demo disclaimer.
   - Implemented `pages/1_Live_Matches.py` (Live Matches / Match Center): Filters for format, status, and team; styled match cards; collapsible scorecards with batting and bowling innings breakdowns.
   - Implemented `pages/2_Top_Players.py` (Top Players): Format tabs (All/Test/ODI/T20I), role/country filters, Batting leaderboard, Bowling leaderboard, and an interactive Player Spotlight card.
   - Implemented `pages/3_SQL_Analytics.py` (SQL Analytics): Grouped Q01–Q25 by difficulty, question selector with SQL metadata, 3 execution tabs (Results table + CSV download, Plotly chart, SQL code & `EXPLAIN QUERY PLAN`), data volume notes, and Q21 PENDING REVIEW banner.
   - Implemented `pages/4_CRUD_Operations.py` (CRUD Operations): Tabs for Players, Venues, and Matches with search/filter, validated Create forms, Update forms, and safe Delete with dependency checks and confirmation checkboxes.
   - Implemented `pages/5_Settings.py` (Settings & Diagnostics): SQLite engine telemetry (`PRAGMA integrity_check`, `PRAGMA foreign_keys = ON`), table row counts grid, environment configuration, cache clearing, sample database re-seeder, and Stage 11 API integration blueprint.
   - Implemented `tests/test_ui.py`: Automated UI testing suite using Streamlit's `AppTest` framework to verify compilation, rendering, zero-exception execution across all 6 pages, and theme/chart utility correctness.
   - Total test suite: **93 passed out of 93 (100% pass rate)**.
10. **Stage 7.1 (Runtime Bug Fixes & Live Browser UI Verification):**
    - Resolved Bug 1 & 2: Fixed `db_manager.get_connection()` context manager usage with `with` across `pages/1_Live_Matches.py` and `pages/2_Top_Players.py`.
    - Resolved Bug 3: Fixed Plotly `undefined` chart title rendering by returning an empty string when titles are `None` or omitted in `utils/charts.py`.
    - Resolved Bug 4: Normalized match status dropdown in `pages/1_Live_Matches.py` to match schema values (`All`, `Completed`, `Live`, `Upcoming`, `Abandoned`, `No Result`, `Tied`).
    - Verified all 6 pages live in headless Chromium browser; captured and archived visual screenshots.
    - Total test suite: 102 passed out of 102 (100% pass rate).
11. **Stage 8 (End-to-End Quality Assurance & Data Validation):**
    - Validated all 25 SQL queries against `Cricbuzz.docx`: syntax, joins, aggregations, anti-Cartesian safety, cricket math (overs/economy/strike rate), zero-row volume explanations, and strictly held Q21 `PENDING REVIEW` status.
    - Verified live development database `data/cricbuzz.db` integrity: `PRAGMA integrity_check` = "ok", `PRAGMA foreign_key_check` = 0 violations, all 10 core tables and 5 views intact.
    - Discovered & fixed defect: Non-ASCII mathematical characters (`≥`) in `analytics/query_runner.py` metadata caused `UnicodeEncodeError` in Windows cp1252 console shells. Replaced with standard ASCII `>=` and added a regression test (`test_catalog_metadata_ascii_cleanliness_for_windows_cp1252`).
    - Implemented `utils/logger.py`: Rotating file logger (`logs/app.log`, 5MB limit, 3 backups) with console output and credential masking.
    - Implemented `tests/test_workflows.py`: Automated realistic multi-step operational workflow test suite covering all 6 required workflows on an isolated temporary database.
    - Total test suite: **109 passed out of 109 (100% pass rate)** in 12.33s.

12. **Stage 9 & Stage 10 (Project Documentation & 50-Question Technical Viva Preparation):**
    - Created comprehensive [`README.md`](file:///e:/Cricbuzz/README.md) featuring project overview, technology stack, directory structure, quickstart setup, database schema, 25 SQL queries catalog, UI screenshots, test suite results, and future API roadmap.
    - Created [`DEPLOYMENT.md`](file:///e:/Cricbuzz/DEPLOYMENT.md) and [`documentation/DEPLOYMENT.md`](file:///e:/Cricbuzz/documentation/DEPLOYMENT.md) containing local development, Streamlit Cloud, Docker containerization, secret hygiene, troubleshooting runbook, and pre-flight deployment checklist.
    - Created [`INTERVIEW_PREP.md`](file:///e:/Cricbuzz/INTERVIEW_PREP.md) and [`documentation/INTERVIEW_PREP.md`](file:///e:/Cricbuzz/documentation/INTERVIEW_PREP.md) with exactly 50 curated technical viva and interview questions organized across 8 categories, strictly adhering to the codebase.
    - Copied and archived 7 verified live UI screenshots into [`assets/screenshots/`](file:///e:/Cricbuzz/assets/screenshots).
    - Verified entire automated test suite: **109 passed out of 109 (100% pass rate)**.

---

13. **Stage 11A (Free Cricket API Investigation & Prepared Integration Layer):**
    - Investigated market providers: CricketData.org (cricapi.com) vs RapidAPI Cricbuzz vs Sportmonks.
    - Verified that RapidAPI requires a credit card even for $0 plans with overage risks, while CricketData.org offers a 100% lifetime free tier (100 hits/day, zero credit card or billing details required).
    - Recommended CricketData.org with transparent data provenance documentation (~30-60s latency, independent feed).
    - Implemented provider-independent API client layer:
      - `api/base_client.py`: `BaseCricketClient`, `SimpleTTLCache` (60s TTL), and custom domain exceptions.
      - `api/cricketdata_client.py`: Concrete client for CricketData.org with missing key safeguards and quota checking.
      - `api/cricbuzz_client.py`: Concrete client for RapidAPI Cricbuzz option.
      - `api/parser.py`: Schema normalizer converting match, innings, and scorecard payloads into schema dictionaries with `source = 'API'`.
      - `api/factory.py`: Factory instantiating the active provider from configuration.
      - `services/ingestion_service.py`: Transactional persistence layer preserving `'LOCAL'` fixtures and applying ADR-006 protection.
    - Implemented 17 automated unit and integration tests with mocked HTTP responses in `tests/test_api.py`.
    - Total test suite: 126 passed out of 126 (100% pass rate).
    - Created detailed investigation report in [`documentation/API_INVESTIGATION.md`](file:///e:/Cricbuzz/documentation/API_INVESTIGATION.md).
    - Preserved `OFFLINE_MODE = True` as default.

14. **Stage 11B (API Integration Readiness Audit):**
    - Verified official provider documentation: CricketData.org (`https://api.cricapi.com/v1/`), `apikey` query parameter, `currentMatches`, `match_scorecard`, and `series` endpoints. Confirmed 100 requests/day lifetime free ($0, no credit card required).
    - Audited full implementation and resolved 4 verified defects:
      1. Enhanced `parse_overs_to_balls` in `api/parser.py` to handle float/string notation, partial overs (`0.5` -> 5 balls), completed over rollovers (`4.6` -> 30 balls = 5.0 overs), and negative rejection.
      2. Enhanced `CricketDataParser.parse_scorecard` to extract innings totals (`total_runs`, `total_wickets`, `overs_completed`) from provider's `score` array or compute them from performances, supporting short/long key variants (`runs`/`r`, `balls`/`b`, `overs`/`o`, `maidens`/`m`, `wickets`/`w`, `economy`/`eco`).
      3. Implemented `ingest_scorecard()` in `services/ingestion_service.py` with atomic transaction commits, ADR-006 protection of LOCAL fixtures (raises `PermissionError`), and clean rollback on constraint violations leaving zero partial records.
      4. Added quota telemetry tracking (`hits_today`, `hits_limit`, `hits_remaining`) and placeholder key rejection to `CricketDataClient` in `api/cricketdata_client.py`.
      5. Enhanced UI in `pages/1_Live_Matches.py` with dynamic header badge, per-card source badge (`💾 LOCAL Demo` vs `📡 API Feed (~30-60s delay)`), and updated `pages/5_Settings.py` Section 5 with CricketData.org telemetry.
    - Added regression tests in `tests/test_api.py` (expanded from 17 to 23 tests).
    - Full test suite: **132 passed out of 132 (100% pass rate)** in 13.10s.

15. **Stage 11C (Final Live API Workflow Verification):**
    - Traced complete live data workflow from CricketData.org client through parsing, transactional ingestion, SQLite storage, and Live Matches UI.
    - Verified and enforced repeated polling idempotency: guaranteed **zero duplicate teams, players, matches, innings, or performance records** across multiple polling intervals.
    - Resolved batting order swap constraint collisions: replacing leaf performances atomically inside `self.db.transaction()` handles batting position permutations cleanly without `UNIQUE(innings_id, batting_position)` violations.
    - Implemented incomplete payload guards:
      - Status downgrade protection: prevented incomplete feed stubs from downgrading `"Completed"` or `"Live"` matches to `"Upcoming"`.
      - Outcome preservation: preserved existing non-null `winning_team_id`, `win_margin`, and `win_type` when incoming payloads omit outcome attributes.
      - Incomplete scorecard protection: prevented empty scorecard stubs (`total_runs=0`, `total_wickets=0`, `batting=[]`, `bowling=[]`) from wiping out populated existing innings.
    - Added structured match outcome parsing (`parse_match_outcome()`) extracting winners, margins, and win types into SQLite schema.
    - Wired UI actions in Streamlit dashboard:
      - Match Center (`pages/1_Live_Matches.py`): Added `🔄 Sync Live Feed` button and per-card `🔄 Sync Innings Feed` button.
      - Settings (`pages/5_Settings.py`): Added `🔌 Test Connection` diagnostic tool reporting daily quota telemetry.
      - Both pages safely block external network calls when `OFFLINE_MODE=True` with user-friendly informational banners.
    - Enhanced provenance display: `📡 API Feed` fixtures display `🕒 Synced: {created_at} UTC (~30-60s delay)` while local fixtures display `💾 LOCAL Demo • Static Sample Fixture`.
    - Added 7 regression tests in `tests/test_api.py` (30/30 API tests passing).
    - Full test suite: **139 passed out of 139 (100% pass rate)** in 13.66s.

16. **Live API Smoke Test (Active Live Mode Verification):**
    - Configured `.env` with user-provided CricketData.org key (`CRICKETDATA_API_KEY`), `OFFLINE_MODE=False`, and `CRICKET_API_PROVIDER=cricketdata`.
    - Executed live handshake with `client.test_connection()`: verified 200 OK status from CricketData.org, retrieved 25 global fixtures.
    - Live Quota Telemetry: 13 hits today / 100 limit (87 remaining).
    - Ingested live fixtures cleanly into SQLite database:
      - 12 `LOCAL` demo matches preserved untouched under ADR-006.
      - 25 live API matches stored with `source = 'API'` and UTC timestamps.
      - Ingested live detailed scorecard for Qatar vs Kuwait (Innings 1: 331/6 in 50 ov, Innings 2: 335/5 in 45.5 ov; 15 batting cards, 14 bowling figures).
    - Re-ran complete test suite: **139 passed out of 139 (100% pass rate)** in 17.27s.

---

## 6. Agreed 11-Stage Master Implementation Sequence

1. **Stage 1 (Completed):** Finalize the approved project structure and configuration (`config.py`, `requirements.txt`, `.env.example`, `.gitignore`).
2. **Stage 2 (Completed):** Implement SQLite database schema (`sql/schema.sql`, `sql/views.sql`) and connection layer (`database/connection.py`).
3. **Stage 3 (Completed):** Add schema validation and database initialization (`database/init_db.py`, `tests/test_init_db.py`).
4. **Stage 4 (Completed):** Create a small, clearly labelled offline dataset for development and testing (`data/seed_data.py`, `data/fixtures/`).
5. **Stage 5 (Completed):** Verify database operations and CRUD functionality (`services/crud_service.py`, `utils/validators.py`, `tests/test_crud.py`).
6. **Stage 6 (Completed):** Implement the 25 SQL analytics questions in batch (`sql/queries/q01.sql` through `q25.sql`, `tests/test_queries.py`; Q21 formula PENDING REVIEW).
7. **Stage 7 (Completed):** Build the Streamlit pages: Home, Live Matches, Top Players, SQL Analytics, CRUD, and Settings (`app.py`, `pages/`, `utils/theme.py`, `utils/charts.py`, `tests/test_ui.py`).
8. **Stage 7.1 (Completed):** Runtime bug fixes and live browser UI verification across all 6 pages.
9. **Stage 8 (Completed):** End-to-End Quality Assurance & Data Validation (all 25 SQL queries, DB integrity, 6 UI pages, realistic workflows, Windows cp1252 encoding fix, 109/109 tests passing).
10. **Stage 9 (Completed):** Comprehensive Application Testing & Verification (109 tests passing, workflows verified).
11. **Stage 10 (Completed):** Project Documentation (`README.md`, `DEPLOYMENT.md`) and Technical Viva/Interview Guide (`INTERVIEW_PREP.md`).
12. **Stage 11A (Completed):** Free Cricket API Investigation & Prepared Integration Layer (CricketData.org recommended, provider-independent clients, caching, parser, mocked tests, 126/126 passing).
13. **Stage 11B (Completed):** API Integration Readiness Audit (verified official docs, audited client/parser/service/schema/UI, resolved 4 defects, added regression tests, documented safe enablement steps; 132/132 tests passing).
14. **Stage 11C (Completed):** Final Live API Workflow Verification (idempotency, incomplete payload defense, UI actions, provenance timestamps, 139/139 tests passing).
15. **Stage 12A (Completed):** First CricketData.org API Smoke Test (single non-destructive `test_connection()` verified 200 OK, 25 live matches, quota 13 used / 87 remaining, credentials redacted, zero DB regressions).
16. **Stage 12B (Completed):** First Real Match Synchronization (synchronized 25 fixtures using existing `Sync Live Feed` workflow, 0 inserted, 25 updated, 0 skipped, 0 failed; quota 15 used / 85 remaining; 12 LOCAL demo fixtures preserved; 139/139 automated tests passing).
17. **Stage 12C (Completed):** Scorecard External ID Resolution & Provider HTTP 500 Handling:
    - Root cause: UI was passing local SQLite primary key (`match_id = 54`) instead of provider's external UUID (`1950e564-6c89-4a51-bd21-4b7413137434`) to `get_match_scorecard()`, causing CricketData.org to return HTTP 500.
    - Solution: Added `external_id TEXT` and `idx_matches_external_id` to `matches` table, persisted `external_id` in `IngestionService.ingest_match()`, updated `pages/1_Live_Matches.py` to pass `match['external_id']`, added user-friendly error wrapping in `CricketDataClient` for HTTP 500, and backfilled active matches. Verified real scorecard ingestion (Innings 15, 3 batting rows, 2 bowling figures) and 139/139 tests passing.

---

## 7. Remaining Uncertainties & Review Items
1. **Q21 Scoring Formula:** Left strictly as `PENDING REVIEW` until formally reviewed with the user per ADR-005.
2. **Fixture Data Expansion:** 9 questions currently return 0 rows on the 12-match development database due to historical sample size requirements (e.g. min 5, 10, or 20 matches, or 6 quarters). Fully verified with isolated test fixtures in `tests/test_queries.py` and transparently explained in UI callouts.

---

## 8. Exact Next Step
- **Stage 12B synchronization is completed.** All 25 live fixtures are synchronized in SQLite with `source='API'` alongside 12 protected `LOCAL` demo matches.
- Users can launch Streamlit (`streamlit run app.py`) to explore live matches in Match Center (`pages/1_Live_Matches.py`) and trigger on-demand detailed scorecard ingestion via `🔄 Sync Innings Feed` for specific fixtures.

