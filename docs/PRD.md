# Project Requirements Document (PRD)

## Project Title: Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics
- **Domain:** Sports Analytics & Web Application Engineering
- **Organization / Program:** Innovexis Internship Project
- **Environment:** Antigravity AI-Assisted Development Environment
- **Status:** Draft / Awaiting User Approval (Gate 0)
- **Last Updated:** 2026-10-22

---

## 1. Executive Summary & Business Problem

Cricket is among the most popular sports globally, generating vast volumes of rich, multi-dimensional data across three major formats: Test matches, One Day Internationals (ODIs), and Twenty20 Internationals (T20Is), as well as domestic leagues (e.g., IPL). However, accessing, synthesizing, and extracting actionable intelligence from raw match streams remains a significant technical challenge for sports analysts, media broadcasters, fantasy sports managers, and data engineering students.

Most existing open-source solutions suffer from:
1. Fragmented data sources with fragile, unverified API scraping.
2. Poorly normalized databases lacking relational integrity for complex multi-innings cricket dynamics.
3. Limited analytical interfaces that either expose raw database consoles (risky) or rigid, non-interactive dashboards.
4. Absence of structured data management (CRUD) allowing administrative updates, correction of match statistics, or custom player entries.

**Cricbuzz LiveStats** bridges this gap by combining:
- A structured ingestion layer connecting to the Cricbuzz REST API (with offline synthetic fixture fallback).
- A normalized, relational SQL database supporting high-integrity sports analytics.
- An interactive, multi-page Streamlit web application providing live scores, leaderboards, 25 specialized SQL analytical queries, and form-based CRUD operations.

---

## 2. Business Objectives & Use Cases

### 2.1 Core Objectives
1. **Real-Time / Frequently Refreshed Insights:** Provide match state, scorecards, batting/bowling statistics, and venue data according to verified API capabilities.
2. **Standardized Relational Persistence:** Store cricket entities (teams, players, venues, series, matches, innings, batting and bowling scorecards) in a normalized relational schema.
3. **Structured Analytical Capability:** Implement and demonstrate 25 specific SQL analytical queries covering beginner, intermediate, and advanced data problems (aggregations, multi-table joins, window functions, and time-series trends).
4. **Governed Data Manipulation (CRUD):** Provide a secure, validated interface to create, read, update, and soft-delete/deactivate cricket records while strictly preserving relational integrity.
5. **Educational Excellence:** Build the system modularly from scratch, explaining architectural and SQL concepts before implementation at each phase gate.

### 2.2 Target Users & Contextual Use Cases
*Note: In accordance with project governance, sports betting/gambling use cases are excluded from implementation scope. They serve strictly as context for statistical analysis.*

| Target User Group | Primary Use Case | Required Capabilities |
| :--- | :--- | :--- |
| **Sports Media & Broadcasters** | Pre-match discussions, commentary feeds, historical head-to-head analysis | Live scorecard view, head-to-head statistics, venue bowling/batting averages |
| **Fantasy Cricket Platforms** | Player form tracking, momentum analysis, team selection insights | Last 10 matches form analysis, consistency score (standard deviation), strike-rate trends |
| **Cricket Analytics Firms** | Deep statistical modeling, player evaluation across formats | Cross-format batting averages, partnership analysis, weighted ranking index |
| **Educational & Academic Learners** | Database engineering and SQL practice on real-world datasets | Documented SQL execution plans, schema design, normalized data models, CRUD operations |

---

## 3. Scope of the System

### 3.1 In-Scope Deliverables
1. **Multi-Page Streamlit Web Application:**
   - **Page 1: Home:** Architecture overview, tech stack details, navigation instructions, and documentation links.
   - **Page 2: Live Matches:** Live and recent matches, scorecards, innings details, and venue information.
   - **Page 3: Top Player Stats:** Batting and bowling leaderboards (most runs, top wickets, highest individual scores, economy rates).
   - **Page 4: SQL Queries & Analytics:** Interactive, parameterized execution of the 25 specified SQL queries with execution plans and visual charts.
   - **Page 5: CRUD Operations:** Form-based validation for creating, updating, viewing, and safely deleting player and match records.
   - **Page 6: Settings (Confirmed):** Environment status, database connection diagnostics, cache management, and demo re-seeding (strictly no secret exposure).
2. **Relational Database Engine:**
   - Database-agnostic architecture (SQLite default for zero-config portability; configurable for PostgreSQL / MySQL).
   - Normalized schema (`schema.sql`), views (`views.sql`), indexes, and foreign-key constraints.
   - Clearly labelled synthetic seed fixtures (`data/seed_data.py`) ensuring all 25 SQL queries can be executed and validated even when offline or API-limited.
3. **API Integration Layer:**
   - Robust Python client using `requests` with timeouts, backoff retries, header management, JSON validation, and error handling.
   - Offline fixture fallback to prevent application crashes during API outages or rate exhaustion.
4. **The 25 SQL Practice Questions:** Full SQL queries, optimization strategies, execution explanations, and Streamlit visualization.
5. **Quality Assurance & Verification:** Unit tests, database tests, mock API integration tests, and SQL verification tests via `pytest`.
6. **Documentation & Viva Preparation:** Technical documentation, README, setup guide, architecture blueprints, and a 50-question interview preparation guide.

### 3.2 Out-of-Scope (Exclusions)
- Real-money gambling, odds calculation engines, or sports betting placement workflows.
- Unrestricted arbitrary SQL consoles that accept unvalidated user queries (prevents injection and database corruption).
- Automated web scraping bypassing API terms of service.
- Destructive cascade deletion of historical source-ingested API records.

---

## 4. Functional Requirements

### FR1: API Integration & Data Ingestion
- **FR1.1:** The system shall authenticate requests to the designated Cricbuzz API using environment-configured API keys and headers.
- **FR1.2:** The API client shall enforce a 10-second timeout on all outbound HTTP calls.
- **FR1.3:** The system shall handle rate limits (HTTP 429), server errors (HTTP 5xx), and connectivity failures gracefully by falling back to cached responses or labelled offline fixtures.
- **FR1.4:** The ingestion pipeline shall parse and validate incoming JSON payloads before transforming them into relational records.
- **FR1.5:** Data ingestion shall be idempotent (e.g., using `INSERT OR REPLACE` or `ON CONFLICT DO UPDATE`) to prevent duplicate matches or player records.

### FR2: Relational Database Storage & Integrity
- **FR2.1:** The database must enforce primary keys, foreign keys, unique constraints, and check constraints across all core entities.
- **FR2.2:** Foreign keys must be enabled on every database connection (including `PRAGMA foreign_keys = ON;` in SQLite).
- **FR2.3:** Database migrations and initialization shall be managed through versioned SQL scripts (`schema.sql`, `views.sql`).
- **FR2.4:** Indexes must be created on frequently queried columns (e.g., `player_id`, `match_id`, `format`, `match_date`, `role`).

### FR3: The 25 SQL Analytical Queries
The system must support the execution and visualization of all 25 specified questions categorized into Beginner (Q1–Q8), Intermediate (Q9–Q16), and Advanced (Q17–Q25).

#### Beginner Level (Q1–Q8)
- **Q1 (India Players):** Find all players representing India. Display full name, playing role, batting style, and bowling style.
- **Q2 (Matches in Last 30 Days):** Show matches played in the last 30 days (relative to current date or max dataset date), including match description, team names, venue city, and date.
- **Q3 (Top ODI Run Scorers):** List top 10 ODI run scorers with player name, total runs, batting average, and centuries, sorted descending by runs.
- **Q4 (Large Venues):** Display venues with seating capacity > 50,000 with name, city, country, and capacity, sorted descending.
- **Q5 (Team Wins):** Calculate matches won per team, sorted by wins descending. Handle tied, abandoned, and no-result matches transparently.
- **Q6 (Player Roles):** Count players in each playing role (Batter, Bowler, All-rounder, Wicket-keeper).
- **Q7 (Highest Individual Score by Format):** Find highest individual score achieved in Test, ODI, and T20I formats.
- **Q8 (Series Started in 2024):** Show series started in 2024 with series name, host country, format, start date, and planned matches.

#### Intermediate Level (Q9–Q16)
- **Q9 (All-rounders):** Find all-rounders with > 1,000 career runs AND > 50 career wickets, displaying name, runs, wickets, and format.
- **Q10 (Last 20 Completed Matches):** Retrieve last 20 completed matches showing description, teams, winner, victory margin, victory type, and venue.
- **Q11 (Cross-Format Player Performance):** For players with ≥ 2 formats, show Test, ODI, and T20I runs and combined batting average (total runs / total dismissals; never averaging averages).
- **Q12 (Home vs. Away Performance):** For each team, count wins at home vs. away by comparing venue country with team country.
- **Q13 (Consecutive Batting-Position Pairs):** Find pairs of consecutive batting positions whose individual scores sum to ≥ 100 in the same innings.
- **Q14 (Venue Bowling Analysis):** For bowlers with ≥ 3 matches at a venue, calculate average economy rate, wickets, and matches (filtering matches where bowler bowled ≥ 4 overs).
- **Q15 (Players in Close Matches):** Identify player performance in close matches (decided by < 50 runs OR < 5 wickets): calculate average runs, close matches played, and close matches won.
- **Q16 (Yearly Batting Trends Since 2020):** For matches since 2020, show each player's average runs and strike rate per year (minimum 5 matches per year).

#### Advanced Level (Q17–Q25)
- **Q17 (Toss Advantage Analysis):** Calculate win percentage of toss-winning teams, segmented by decision to bat first vs. bowl first.
- **Q18 (Economical Limited-Overs Bowlers):** For ODI and T20, calculate economy rate and wickets for bowlers with ≥ 10 matches and ≥ 2 overs/match average.
- **Q19 (Batting Consistency):** Calculate average runs and standard deviation of runs for players facing ≥ 10 balls per innings since 2022.
- **Q20 (Matches & Averages by Format):** Display Test, ODI, and T20 match counts and batting averages for players with ≥ 20 matches across formats.
- **Q21 (Weighted Player Ranking - Formula PENDING REVIEW):** Calculate composite ranking combining batting, bowling, and fielding points based on formula to be formally reviewed with user prior to implementation.
- **Q22 (Team Head-to-Head):** For team pairs with ≥ 5 matches in the last 3 years, calculate matches, wins, average victory margins, venue performance, and win percentages.
- **Q23 (Recent Player Form & Momentum):** For last 10 innings, compare last 5 vs. last 10 average runs, strike rate trend, 50+ scores, and standard deviation consistency; categorize into Excellent, Good, Average, or Poor Form.
- **Q24 (Batting Partnerships):** For consecutive batsman pairs partnering in ≥ 5 partnerships, calculate average partnership runs, 50+ partnerships, highest partnership, and success rate.
- **Q25 (Quarterly Career Trajectory):** Time-series analysis tracking quarterly runs and strike rate (minimum 6 quarters, ≥ 3 matches/quarter); categorize into Career Ascending, Career Declining, or Career Stable.

### FR4: Form-Based CRUD Data Management
- **FR4.1 (Create):** Provide validated forms to insert new players and match records with field-level constraint checks (e.g., positive integers for runs/wickets, valid date formats, valid enumerated roles).
- **FR4.2 (Read):** Provide paginated, searchable tables to inspect stored entities with real-time filtering by role, team, and country.
- **FR4.3 (Update):** Allow editing existing local/admin records with optimistic verification and audit logging.
- **FR4.4 (Delete):** Implement safe deletion (with confirmation modal). For referenced records, enforce foreign-key protection (disallow deletion if historical match scorecards depend on the player, or provide soft-delete / status flag).
- **FR4.5 (Source Data Segregation):** Ingested API records are marked `source = 'API'` (read-only for historical auditing), while locally added/modified records are marked `source = 'LOCAL'`.

### FR5: Streamlit User Interface & Visualizations
- **FR5.1:** Multi-page layout using Streamlit native pages (`pages/` directory).
- **FR5.2:** Rich aesthetics adhering to a sports-analytics theme (custom CSS, glassmorphism KPI cards, clear visual hierarchy).
- **FR5.3:** Interactive charts using Plotly / Streamlit native chart libraries (bar charts for comparisons, line charts for trends, scatter plots for correlation, donut charts for proportions).
- **FR5.4:** Responsive state feedback: skeleton loading spinners, clear empty-state notifications, stale-data warnings, and friendly error alerts.

---

## 5. Non-Functional Requirements (NFRs)

| Category | Requirement | Target Metric |
| :--- | :--- | :--- |
| **Performance** | SQL query execution time on local database | < 250 ms for 95% of queries |
| **Performance** | Streamlit page rendering time | < 1.5 seconds on page switch |
| **Reliability** | Graceful degradation on API timeout / HTTP 429 | 100% fallback to cached/fixture data; zero unhandled crash screens |
| **Security** | Secrets handling | 0 hardcoded secrets. All credentials read from `.env` |
| **Security** | Injection defense | 100% of SQL executions use parameterized queries; no raw string interpolation |
| **Maintainability**| Code cleanliness | PEP 8 compliance, modular architecture, full type hints, Google-style docstrings |
| **Data Integrity** | Foreign key and check constraints | `PRAGMA foreign_keys = ON;` enforced on every connection |
| **Auditability** | System operations logging | Structured logging to file (`logs/app.log`) and console with log rotation |

---

## 6. Deliverables Checklist

- [ ] Complete Source Code: Modular Python package with `app.py`, `config.py`, `api/`, `database/`, `services/`, `pages/`, `utils/`, `sql/`.
- [ ] Database Schema & Seed Data: `schema.sql`, `views.sql`, `seed_data.py`, and verified sample data.
- [ ] 25 SQL Analytics Solutions: Predefined, documented, and tested `.sql` files in `sql/queries/`.
- [ ] Documentation Suite in `docs/`: PRD, ARCHITECTURE, DESIGN, RULES, TASKS, DECISIONS, MEMORY.
- [ ] Setup & Operational Guide: Comprehensive `README.md` and `.env.example`.
- [ ] Automated Test Suite: `pytest` test suite covering models, database, API client, CRUD, and SQL queries.
- [ ] Working Live Demo & Video Recording Checklist.
- [ ] 50-Question Technical Viva & Interview Preparation Guide.

---

## 7. Confirmed Decisions & Review Items

### 7.1 Confirmed Architectural Baseline
1. **Database:** SQLite (`data/cricbuzz.db`) is confirmed as the primary local development database with `PRAGMA foreign_keys = ON;` enforced on every connection.
2. **Settings Page:** Confirmed for inclusion as Page 6 (`pages/5_Settings.py`) for system diagnostics, cache clearing, and demo re-seeding without secret exposure.
3. **Phased API Strategy:** Development proceeds immediately using clearly labelled offline test fixtures in `data/fixtures/` and `seed_data.py`. Real Cricbuzz API access will be integrated in Stage 11 after provider details, endpoints, and terms are verified. Sample fixtures will never be presented as real-time live data.
4. **Execution Focus:** Prioritize finishing rapidly without sacrificing engineering quality, eliminating deadline anxiety.
5. **Phase Gate Governance & Anti-Fabrication:** Work proceeds strictly in sequential stages. No phase gate is crossed without user approval. Test results, SQL outputs, and features are never fabricated or claimed complete without evidence.

### 7.2 Review Items (Explicitly Held for Stage Gate)
1. **Q21 Bowling Points Formula Disambiguation (PENDING REVIEW):**
   - The brief's formula contains an unmatched parenthesis: `(wickets_taken * 2) + (50 - bowling_average) * 0.5) + ((6 - economy_rate) * 2)`.
   - Proposed clean formula: `(wickets_taken * 2.0) + ((50.0 - bowling_average) * 0.5) + ((6.0 - economy_rate) * 2.0)`.
   - **Status:** Explicitly kept **PENDING REVIEW** until Stage 6 Question 21 is reached.
2. **Cricbuzz Live API Provider Details (Deferred to Stage 11):**
   - Live endpoints, headers, and rate limits will be verified prior to implementing Stage 11.
