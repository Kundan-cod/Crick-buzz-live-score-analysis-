# Architectural Decision Records (DECISIONS.md)

## Project: Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics
- **Standard:** Lightweight Architecture Decision Records (ADR)
- **Status Legend:** `Proposed` | `Pending Review` | `Accepted` | `Rejected` | `Superseded`
- **Last Updated:** 2026-10-22

---

## ADR-001: Documentation-First Workflow and Phase Approval Gates
- **Status:** `Accepted`
- **Date:** 2026-10-22

### Context
Building a multi-faceted data engineering, SQL analytics, and web visualization platform requires clear alignment on business objectives, schema constraints, and technical boundaries before writing executable code. The project brief and mentoring guidelines mandate a documentation-first gate.

### Options Considered
1. *Code-First Rapid Prototyping:* Generate code immediately and document post-hoc.
2. *Documentation-First Governance (Selected):* Create a complete documentation suite (`PRD.md`, `ARCHITECTURE.md`, `DESIGN.md`, `RULES.md`, `TASKS.md`, `DECISIONS.md`, `MEMORY.md`), verify consistency, and hold for user approval before coding.

### Decision
Adopt Option 2. No substantial application code will be committed until the documentation suite is reviewed and approved by the user.

### Consequences
- **Positive:** Eliminates architectural rework, clarifies ambiguities early, guarantees alignment with the mentoring roadmap.
- **Negative:** Requires upfront time investment before initial runnable screens are produced.

---

## ADR-002: Modular Multi-Page Streamlit Architecture
- **Status:** `Accepted`
- **Date:** 2026-10-22

### Context
Streamlit applications can be built as a single monolithic script with multiple `if/else` page switches or structured using Streamlit's native `pages/` directory pattern.

### Options Considered
1. *Monolithic Single File (`app.py` with radio button routing):* All UI logic in one file.
2. *Native Multi-Page Directory Pattern (Selected):* `app.py` as Home, with discrete pages under `pages/` (`1_Live_Matches.py`, `2_Top_Players.py`, `3_SQL_Analytics.py`, `4_CRUD_Operations.py`, `5_Settings.py`), powered by isolated backend services in `services/`.

### Decision
Adopt Option 2. Native multi-page structure with clean decoupling between UI pages and service modules.

### Consequences
- **Positive:** Clean file organization, independent testing of pages, native Streamlit sidebar routing and URL hashing.
- **Negative:** Session state management across pages requires careful coordination via `st.session_state`.

---

## ADR-003: Database Engine Selection — SQLite for Local Development
- **Status:** `Accepted` (Confirmed by User)
- **Date:** 2026-10-22

### Context
The project requires an immediate, reliable, and easily deployable engine for local development, automated testing, and internship grading without requiring complex local server installations.

### Options Considered
1. *PostgreSQL / MySQL:* Highly scalable, but requires external service installation, credentials configuration, and connection daemon overhead.
2. *SQLite with Agnostic Connection Layer (Selected):* Built directly into Python standard library, zero external installation, instant file-based portability, fully ACID-compliant with foreign key enforcement (`PRAGMA foreign_keys = ON;`). Connection manager designed agnostically to allow toggling to PostgreSQL via `.env` if desired.

### Decision
Adopt Option 2: Use SQLite (`data/cricbuzz.db`) for all local development and demonstration, adhering to ANSI SQL and encapsulating connection logic in `database/connection.py`.

### Consequences
- **Positive:** Zero friction for grading and demo; completely reproducible across any operating system; embedded in version-controlled test workflows.
- **Implementation Note:** Foreign keys must be enabled on every connection via `PRAGMA foreign_keys = ON;`.

---

## ADR-004: Phased API Integration & Offline-Fixture Development Mode
- **Status:** `Accepted` (Confirmed by User)
- **Date:** 2026-10-22

### Context
The project requires integrating Cricbuzz data, but real API credentials, provider endpoint documentation, and rate limits will be verified and connected later. The development and testing must proceed immediately without blocking.

### Options Considered
1. *Strict Online Only:* Block development until API credentials and documentation are obtained.
2. *Phased Offline-Fixture First, Real API Later (Selected):*
   - Prepare an offline-fixture mode using clearly labelled sample datasets (`data/fixtures/` and `data/seed_data.py`).
   - Never present fixture data as real-time cricket data in UI or documentation.
   - Design the API layer modularly so real Cricbuzz API endpoints can be plugged in later once verified.

### Decision
Adopt Option 2: Build the core database, CRUD, SQL analytics, and Streamlit UI using clearly labelled offline fixtures. Integrate real Cricbuzz API access in a dedicated later phase after endpoints and terms are confirmed.

### Consequences
- **Positive:** Unblocks immediate database, analytics, and frontend development; eliminates rate-limit failures during development.
- **Governance:** Sample data must always be marked as `[SYNTHETIC TEST FIXTURE]`.

---

## ADR-005: Q21 Bowling Points Formula Disambiguation
- **Status:** `Pending Review` (Explicitly Kept Pending Review per User Instruction)
- **Date:** 2026-10-22

### Context
The project brief provides the following formula for Question 21:
- Batting points: `(runs_scored * 0.01) + (batting_average * 0.5) + (strike_rate * 0.3)`
- Bowling points (verbatim from brief): `(wickets_taken * 2) + (50 - bowling_average) * 0.5) + ((6 - economy_rate) * 2)`
- Fielding points: `(catches * 3) + (stumpings * 5)`

Notice that the bowling formula has an unmatched closing parenthesis: `(50 - bowling_average) * 0.5)`.

### Options Considered
1. *Interpretation A (Outer bracket wrapping 50 - avg):*
   `Bowling Points = (wickets_taken * 2) + ((50 - bowling_average) * 0.5) + ((6 - economy_rate) * 2)`
2. *Interpretation B (No inner bracket):*
   `Bowling Points = (wickets_taken * 2) + (50 - bowling_average) * 0.5 + ((6 - economy_rate) * 2)`
3. *Interpretation C (Clamping against negative values):*
   `MAX(0, (50 - bowling_average) * 0.5)` to avoid negative contributions when average > 50.

### Current Status
**PENDING REVIEW**: This formula is explicitly held as Pending Review. It will NOT be silently finalized or modified until Phase 11 Question 21 is reached and formally reviewed with the user.

---

## ADR-006: CRUD Scope & Referential Integrity Segregation
- **Status:** `Accepted`
- **Date:** 2026-10-22

### Context
The project requires full CRUD operations on players and match records. Arbitrary deletion of entities linked to match scorecards can cause orphaned records or break the 25 analytical queries.

### Options Considered
1. *Unrestricted In-Place Mutation:* Users can edit or delete any row directly in the database.
2. *Source Tagging with Referential Protection (Selected):*
   - Records contain a `source` tag (`'API'` or `'LOCAL'`).
   - Ingested source records are protected from accidental deletion.
   - Users can create, update, and delete local/custom records.
   - Any deletion enforces foreign-key checks and requires explicit user confirmation.

### Decision
Adopt Option 2: Enforce strict referential protection and source segregation for all CRUD operations.

---

## ADR-007: Settings Page Inclusion
- **Status:** `Accepted` (Confirmed by User)
- **Date:** 2026-10-22

### Context
The mentoring prompt lists a 6th page: "Settings". The user has confirmed that this page must be included.

### Decision
Include `pages/5_Settings.py` in the Streamlit application. The page will display:
- System and database health (SQLite path, file size, connection status).
- Offline-fixture mode status vs API status.
- Cache management (clear cached query results).
- Demo data re-seeding button.
- Strictly no exposure of secrets or credentials.

### Consequences
- Provides transparency, diagnostics, and high professional polish for evaluation.

---

## ADR-008: Project Execution Timeline & Focus
- **Status:** `Accepted` (Confirmed by User)
- **Date:** 2026-10-22

### Context
The project brief mentions a 14-day completion period. The user instructed to avoid spending further time discussing or worrying about the submission deadline, focusing entirely on rapid, high-quality execution without sacrificing engineering standards.

### Decision
Execute the project sequentially through the agreed implementation sequence as swiftly as possible, maintaining uncompromising standards in architecture, testing, documentation, and code quality.
