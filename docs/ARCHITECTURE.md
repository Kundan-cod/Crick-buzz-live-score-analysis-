# Architecture Document

## Project: Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics
- **System Architecture:** Layered Service-Oriented Monolith
- **Framework:** Streamlit (Multi-Page App) + Python 3.10+
- **Persistence:** Relational SQL Database (SQLite default with database-agnostic connector)
- **Status:** Draft / Awaiting User Approval (Gate 0)
- **Last Updated:** 2026-10-22

---

## 1. High-Level Architectural Overview

The **Cricbuzz LiveStats** platform follows a layered, decoupled architecture designed for high maintainability, testability, and strict separation of concerns. UI code is kept strictly isolated from data ingestion, business calculations, and database persistence.

```
+-----------------------------------------------------------------------------------+
|                                  PRESENTATION LAYER                               |
|                               (Streamlit Multi-Page UI)                           |
|  [Home]  [Live Matches]  [Top Players]  [SQL Analytics]  [CRUD Ops]  [Settings]   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                                   SERVICE LAYER                                   |
|   +-------------------+  +-------------------+  +-------------------------------+ |
|   |   MatchService    |  |   PlayerService   |  |        AnalyticsService       | |
|   +-------------------+  +-------------------+  +-------------------------------+ |
|   +------------------------------------------+  +-------------------------------+ |
|   |               CRUDService                |  |        RankingService         | |
|   +------------------------------------------+  +-------------------------------+ |
+----------------------+-----------------------------------+------------------------+
                       |                                   |
                       v                                   v
+------------------------------------------+  +-------------------------------------+
|              API LAYER                   |  |          ANALYTICS LAYER            |
|   +----------------------------------+   |  |   +-------------------------------+ |
|   | CricbuzzClient (requests + retry)|   |  |   | QueryRunner (Param SQL Engine)| |
|   +----------------------------------+   |  |   +-------------------------------+ |
|   | ResponseParser & Field Normalizer|   |  |   | 25 Parameterized SQL Files    | |
|   +----------------------------------+   |  |   +-------------------------------+ |
|   | Offline Fixture Fallback Engine  |   |  |   | Statistical & Pandas Aggregates| |
|   +----------------------------------+   |  |   +-------------------------------+ |
+----------------------+-------------------+  +--------------------+----------------+
                       |                                           |
                       v                                           v
+-----------------------------------------------------------------------------------+
|                                  PERSISTENCE LAYER                                |
|   +-----------------------------------------------------------------------------+ |
|   | DBConnectionManager (Connection pooling, PRAGMA foreign keys, Transactions) | |
|   +-----------------------------------------------------------------------------+ |
|   | Schema (Teams, Players, Venues, Series, Matches, Innings, Batting, Bowling) | |
|   +-----------------------------------------------------------------------------+ |
|   | Analytical Views (v_player_career, v_match_summary, v_partnerships)         | |
+-----------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             CROSS-CUTTING CONCERNS                                |
|   [Config & .env]  [Structured Logger]  [Data Validators]  [Pytest Test Suite]    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Component Breakdown & Responsibilities

### 2.1 Presentation Layer (`pages/`, `app.py`)
- **Technology:** Streamlit 1.30+
- **Responsibilities:**
  - Render rich, interactive web pages using a custom sports-analytics design system.
  - Manage session state and user interaction parameters (filters, pagination, date pickers).
  - Present data visually via KPI metric cards, interactive tables, and Plotly charts.
  - Collect user input via validated forms for CRUD operations and display confirmation modals for deletions.
  - Surface non-intrusive alerts for API latency, stale data, empty results, or connection diagnostics.
- **Isolation Rule:** Presentation components *never* execute direct SQL strings or invoke raw `requests` calls. They interact exclusively through the Service Layer.

### 2.2 Service Layer (`services/`)
- **Responsibilities:**
  - Act as the central mediator between UI components and underlying data engines.
  - `MatchService`: Coordinates fetching live scores from API/fixtures, cache synchronization, and match detail aggregation.
  - `PlayerService`: Computes cross-format aggregates, player profiles, and form tracking.
  - `AnalyticsService`: Loads, validates, and executes the 25 SQL queries with parameter injection and result caching.
  - `CRUDService`: Validates create/update/delete payloads, enforces business constraints, coordinates transactions, and handles soft-deletes.
  - `RankingService`: Implements the disambiguated composite scoring model for Q21.

### 2.3 API Ingestion Layer (`api/`)
- **Responsibilities:**
  - Interface with the designated Cricbuzz Cricket REST API via HTTP GET requests.
  - Enforce timeout policies (10s), headers (`x-rapidapi-key`, `x-rapidapi-host` or bearer tokens), and exponential backoff on transient errors (429, 502, 503).
  - **Offline Resilience:** If API credentials are not configured, network is unavailable, or quotas are exhausted, automatically load verified JSON fixtures from `data/fixtures/` with explicit UI status indication.
  - Normalize nested API responses into structured dictionaries matching relational database entity schemas.

### 2.4 Analytics Layer (`analytics/`, `sql/`)
- **Responsibilities:**
  - Maintain 25 distinct, version-controlled SQL files in `sql/queries/q01` through `q25`.
  - Provide `QueryRunner` utility to safely read, parameterize, and execute SQL scripts.
  - Execute database execution plans (`EXPLAIN QUERY PLAN` in SQLite) to document index usage and query performance.
  - Perform auxiliary statistical analysis (standard deviation, rolling averages, quarter-over-quarter percentage changes) in combination with SQL and pandas.

### 2.5 Persistence Layer (`database/`, `sql/`)
- **Engine:** SQLite by default (relational, file-based, zero-configuration); structured with a connection factory to permit seamless migration to PostgreSQL or MySQL.
- **Responsibilities:**
  - Connection management: single-source connection provider in `database/connection.py`.
  - Enforce referential integrity (`PRAGMA foreign_keys = ON;` in SQLite).
  - Transaction safety: atomic commits with automatic rollback upon exceptions.
  - Database schema initialization (`schema.sql`) and reusable analytical view definitions (`views.sql`).
  - Idempotent seeding mechanism (`data/seed_data.py`) providing guaranteed test records for all 25 queries.

### 2.6 Cross-Cutting Utilities (`utils/`, `config.py`)
- **`config.py`**: Centralized configuration reading environment variables via `python-dotenv` with sensible fallbacks and validation.
- **`utils/logger.py`**: Standardized logging with log level control, console output, and rotating file logging (`logs/app.log`). Credentials and secrets are automatically masked.
- **`utils/validators.py`**: Robust input validation functions ensuring positive numeric values, valid formats, date ranges, and safe strings.
- **`utils/formatters.py`**: Currency, run-rate, strike-rate, and timestamp formatting helpers for clean display across the UI.

---

## 3. Data Flow Architecture

### 3.1 Live Match Ingestion Flow
```
User navigates to Live Matches
            │
            ▼
Page calls MatchService.get_live_matches()
            │
            ▼
MatchService checks local cache / TTL
            ├── Cache Valid? ──► Return cached match records to Page
            │
            └── Cache Stale / Miss
                    │
                    ▼
          API Client calls Cricbuzz API
                    │
                    ├── HTTP 200 OK ──► Parser normalizes JSON ──► Ingestion saves to DB
                    │                                                     │
                    └── HTTP 429 / Offline ──► Fallback to Fixtures ──────┘
                                                     │
                                                     ▼
                                      Return matches to UI with freshness badge
```

### 3.2 SQL Analytics Query Flow
```
User selects Question (Q1 - Q25) & Parameters on Analytics Page
            │
            ▼
Page calls AnalyticsService.execute_query(question_id, params)
            │
            ▼
Service loads `sql/queries/qXX.sql` via QueryRunner
            │
            ▼
QueryRunner executes parameterized SQL via DBConnectionManager
            │
            ▼
Database returns cursor records ──► Converted to pandas DataFrame
            │
            ▼
AnalyticsService computes statistical metrics & visualization mappings
            │
            ▼
Page renders KPI summary cards, interactive DataFrame, and Plotly chart
```

### 3.3 CRUD Operations Flow
```
User submits Player Update / Creation form
            │
            ▼
Page calls CRUDService.create_player(data)
            │
            ▼
Validators check types, boundaries, uniqueness, and constraints
            ├── Validation Failed? ──► Return friendly error message to UI
            │
            └── Validation Passed
                    │
                    ▼
          DBConnectionManager begins transaction
                    │
                    ├── Execute parameterized INSERT/UPDATE
                    ├── Check foreign key integrity
                    ├── Commit transaction
                    └── Return success confirmation & updated ID to UI
```

---

## 4. Database Schema Blueprint & Entity Relationships

The relational model is normalized to Third Normal Form (3NF) to balance relational rigor with query performance:

```
+---------------+        +----------------+        +---------------+
|     TEAMS     | 1    * |    MATCHES     | *    1 |    VENUES     |
|---------------|--------|----------------|--------|---------------|
| team_id (PK)  |        | match_id (PK)  |        | venue_id (PK) |
| team_name     |        | series_id (FK) |        | venue_name    |
| short_name    |        | team1_id (FK)  |        | city          |
| country       |        | team2_id (FK)  |        | country       |
+---------------+        | venue_id (FK)  |        | capacity      |
       | 1               | match_date     |        +---------------+
       |                 | match_format   |
       |                 | toss_winner_id |
       |                 | toss_decision  |
       |                 | match_result   |
       |                 | winning_team_id|
       |                 | win_margin     |
       |                 | win_type       |
       |                 +----------------+
       |                         | 1
       |                         |
       | *                       | *
+---------------+        +----------------+
|    PLAYERS    | 1    * |    INNINGS     |
|---------------|--------|----------------|
| player_id(PK) |        | innings_id(PK) |
| full_name     |        | match_id (FK)  |
| team_id (FK)  |        | innings_number |
| country       |        | batting_team_id|
| playing_role  |        | bowling_team_id|
| batting_style |        | total_runs     |
| bowling_style |        | total_wickets  |
| source        |        +----------------+
+---------------+           | 1          | 1
       | 1                  |            |
       |                    | *          | *
       | *            +--------------+  +--------------+
       +--------------|   BATTING    |  |   BOWLING    |
       |              | PERFORMANCES |  | PERFORMANCES |
       |              |--------------|  |--------------|
       |              | perf_id (PK) |  | bowl_id (PK) |
       |              | innings_id FK|  | innings_id FK|
       |              | player_id FK |  | player_id FK |
       |              | batting_pos  |  | overs_bowled |
       |              | runs_scored  |  | maidens      |
       |              | balls_faced  |  | runs_conceded|
       |              | fours        |  | wickets_taken|
       |              | sixes        |  | economy_rate |
       |              | dismissal    |  | no_balls     |
       |              +--------------+  | wides        |
       |                                +--------------+
       |                                       |
       +---------------------------------------+
```

---

## 5. Security Architecture & Secrets Governance

1. **Zero Secret Leakage:**
   - No API keys, database credentials, or secret tokens are ever committed to version control.
   - All credentials are read from `.env` via `config.py` using `python-dotenv`.
   - `.gitignore` explicitly excludes `.env`, `*.db`, `logs/`, and `__pycache__/`.
   - `.env.example` provides safe placeholder documentation.
2. **SQL Injection Defense:**
   - 100% of SQL statements executed against the database utilize parameter binding (`?` placeholders for SQLite, `%s` for PostgreSQL).
   - Dynamic table names or column identifiers, if ever needed, are strictly whitelisted against an internal enum; no direct user-supplied string interpolation is permitted.
3. **Data Protection & Soft Deletion:**
   - Ingested records from official feeds have `source = 'API'` and are protected from accidental destructive deletion.
   - Deletions are gated by confirmation modals and foreign-key checks.

---

## 6. Deployment Architecture

| Deployment Target | Database Strategy | Storage Persistence | Suitability |
| :--- | :--- | :--- | :--- |
| **Local Development** | SQLite (`data/cricbuzz.db`) | Local disk | Primary recommendation for development and testing |
| **Streamlit Community Cloud** | SQLite or Supabase (PostgreSQL) | Ephemeral git-backed / Remote SQL | Ideal for free internship project demo hosting |
| **Render / Railway** | PostgreSQL / SQLite with volume | Persistent disk or managed DB | Robust alternative for cloud deployment |
| **Docker Container** | SQLite inside container / External DB | Mounted volume | Standardized evaluation and grading |

---

## 7. Architectural Decisions Log Reference
All binding architectural choices are tracked in `docs/DECISIONS.md`. Status summary:
- **ADR-001 (Accepted):** Documentation-First Governance & Phase Gates.
- **ADR-002 (Accepted):** Modular Multi-Page Streamlit Architecture.
- **ADR-003 (Accepted):** SQLite (`data/cricbuzz.db`) confirmed for local development.
- **ADR-004 (Accepted):** Phased offline-fixture first; real API integration deferred to Stage 11.
- **ADR-005 (Pending Review):** Q21 parenthesized bowling formula held for explicit review in Stage 6.
- **ADR-006 (Accepted):** CRUD referential protection and source segregation.
- **ADR-007 (Accepted):** Settings Page (`pages/5_Settings.py`) confirmed for inclusion.
- **ADR-008 (Accepted):** Swift execution focus without deadline anxiety.
