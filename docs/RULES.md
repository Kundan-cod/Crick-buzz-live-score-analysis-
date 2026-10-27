# Engineering Standards & Governance Rules (RULES.md)

## Project: Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics
- **Standard:** Production-Grade Python, SQL, and Architecture Governance
- **Status:** Active / Non-Negotiable
- **Last Updated:** 2026-10-22

---

## 1. Code Style & Formatting (PEP 8)

1. **PEP 8 Compliance:** All Python source files must adhere strictly to PEP 8 standards:
   - Line length capped at 100 characters.
   - 4-space indentation; no tabs.
   - Two blank lines between top-level functions and classes; one blank line between methods.
   - Imports grouped in standard order: (1) Standard library, (2) Third-party packages, (3) Local modules.
2. **Naming Conventions:**
   - Modules / packages: `snake_case` (e.g., `match_service.py`, `query_runner.py`).
   - Classes: `PascalCase` (e.g., `CricbuzzClient`, `DBConnectionManager`, `PlayerService`).
   - Functions / methods / variables: `snake_case` (e.g., `get_live_matches`, `total_runs`).
   - Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT_SECONDS`, `MAX_RETRIES`).
   - Private methods / variables: Prefix with single underscore (e.g., `_execute_query`).
3. **Type Annotations:**
   - All function signatures, public methods, and service interfaces must include Python type hints (`str`, `int`, `float`, `Optional[T]`, `List[T]`, `Dict[str, Any]`, `pd.DataFrame`).
4. **Documentation & Docstrings:**
   - Every module, class, and public function must have a Google-style docstring explaining:
     - Short summary of intent.
     - `Args`: parameter names, types, and descriptions.
     - `Returns`: return type and description.
     - `Raises`: exceptions explicitly thrown.

---

## 2. Architecture & Modular Programming

1. **Separation of Concerns:**
   - **Never mix UI and Data:** Streamlit pages (`pages/*.py`, `app.py`) must *never* perform direct SQL queries or invoke raw `requests.get()`. All data acquisition flows through the `services/` layer.
   - **Never hardcode SQL in presentation code:** All SQL analytics statements reside in dedicated `.sql` files within `sql/queries/`.
2. **Object-Oriented & Functional Synergy:**
   - Use OOP for stateful, persistent, or lifecycle-managed components (e.g., `DBConnectionManager`, `CricbuzzClient`, `QueryRunner`).
   - Use pure functions and immutable data structures for formatting, mathematical scoring calculations, and stateless validators.
3. **DRY (Don't Repeat Yourself):**
   - Common queries, database helper routines, and chart generation pipelines must be centralized in utility or service modules.

---

## 3. Database Safety & Integrity

1. **100% Parameterized Queries:**
   - Under no circumstances shall raw user input or variable data be interpolated directly into SQL strings using Python f-strings, `%` formatting, or string concatenation.
   - Parameter placeholders (`?` for SQLite, `%s` for PostgreSQL) must always be used to eliminate SQL injection vulnerabilities.
2. **Foreign-Key Enforcement:**
   - For SQLite, every connection must explicitly execute `PRAGMA foreign_keys = ON;` upon opening.
3. **Transaction Management:**
   - All multi-statement write operations (e.g., match insertion with innings and player scorecards) must execute inside an explicit atomic transaction context.
   - In the event of any exception, an immediate `ROLLBACK` must occur before re-raising or logging the error.
4. **Integrity Preservation & Safe Deletion:**
   - Ingested records from source feeds (`source = 'API'`) are read-only and protected from accidental deletion.
   - Deletions are restricted to local/admin records (`source = 'LOCAL'`), require explicit user confirmation, and must verify that no dependent child records exist.

---

## 4. API Reliability & External Services

1. **Timeout Enforcement:**
   - Every outbound HTTP call via `requests` must include an explicit `timeout` parameter (default: 10 seconds). Bare `requests.get(url)` is prohibited.
2. **Rate Limit & Error Handling:**
   - Responses must be checked for HTTP status codes.
   - Transient failures (HTTP 429, 502, 503) must utilize a bounded retry strategy with exponential backoff (e.g., via `urllib3.util.retry.Retry`).
3. **Graceful Offline Fallback:**
   - If network connectivity is lost, credentials are unconfigured, or rate limits are exhausted, the API layer must fall back gracefully to verified offline fixtures located in `data/fixtures/`.
   - The application must clearly badge the UI to notify the user of fixture mode.

---

## 5. Security & Secrets Management

1. **Zero Secret Leakage:**
   - Under no circumstances shall API keys, passwords, database URLs, or authentication tokens be committed to Git.
   - All sensitive settings must be loaded from an ignored `.env` file via `config.py`.
2. **Version Control Exclusions:**
   - `.gitignore` must immediately be initialized and maintained to exclude:
     - `.env`
     - `*.db`, `*.sqlite`, `*.sqlite3`
     - `logs/`
     - `__pycache__/`, `*.pyc`, `.pytest_cache/`
     - Temporary scratch scripts
3. **Placeholder Templates:**
   - A `.env.example` file must be provided with descriptive placeholder values (e.g., `CRICBUZZ_API_KEY=your_api_key_here`).

---

## 6. Input Validation & Error Handling

1. **Defensive Validation:**
   - All inputs to CRUD operations must be validated before database submission (e.g., runs ≥ 0, overs ≥ 0, valid dates, valid non-empty names).
2. **User-Friendly Error Surfaces:**
   - Internal stack traces, raw database error dumps, and environment details must *never* be displayed to end users in the Streamlit UI.
   - Errors must be captured, logged with full detail to `logs/app.log`, and translated into friendly, actionable Streamlit notifications (`st.error()`, `st.warning()`).

---

## 7. Logging & Observability

1. **Structured Logging:**
   - Use Python's built-in `logging` module.
   - Log files must be placed in `logs/app.log` with size-based rotation (`RotatingFileHandler`, max 5MB, 3 backups).
2. **Log Levels:**
   - `DEBUG`: Query parameters, execution times, cache hit/miss details.
   - `INFO`: Application startup, page navigation, successful data ingestion batches, CRUD completions.
   - `WARNING`: API rate limits reached, fallback to fixtures triggered, missing optional fields.
   - `ERROR`: Database connection failures, transaction rollbacks, unhandled HTTP status codes.
3. **Sanitized Logs:**
   - Sensitive headers, passwords, and API keys must be scrubbed before logging.

---

## 8. Quality Assurance & Testing Standards

1. **Automated Testing Suite:**
   - Use `pytest` for all automated verification.
   - Tests are organized into:
     - `tests/test_database.py`: Schema creation, foreign keys, transaction rollbacks, connection management.
     - `tests/test_api_client.py`: Mocked HTTP responses, timeout handling, retry logic, fixture fallback.
     - `tests/test_crud.py`: Create, read, update, delete validation and constraint protection.
     - `tests/test_queries.py`: Verification that all 25 SQL queries run cleanly against seed data and return expected column schemas.
2. **Real Verification Evidence:**
   - Test outcomes must reflect actual commands executed in the shell.
   - No mock results may be claimed as passing without shell execution logs.

---

## 9. Strict Anti-Fabrication & Mentoring Gate Rules

1. **No Data Fabrication & Sample Data Labeling:**
   - Never invent mock values and claim they are live API feeds.
   - Never fabricate test logs, screenshots, or performance benchmarks.
   - Sample offline fixtures must always be explicitly labelled as `[SYNTHETIC TEST FIXTURE]`.
   - Never present fixture data as real-time cricket data in the UI or documentation.
2. **Phase Gate Enforcement:**
   - Development must proceed sequentially through the 11 agreed implementation stages.
   - No stage gate shall be crossed without explicit user review and approval.
3. **Q21 Formula Governance:**
   - The proposed Q21 bowling-points formula remains strictly **PENDING REVIEW**.
   - Do not silently finalize or modify the scoring rule without explicit user confirmation during Stage 6 Q21.
4. **SQL Analytics One-by-One Protocol:**
   - In Stage 6, each of the 25 SQL questions must be handled individually:
     1. Business problem.
     2. SQL concepts.
     3. Tables & relationships.
     4. Query logic & execution plan.
     5. Tested query implementation.
     6. Line-by-line explanation.
     7. Null handling & edge cases.
     8. Optimization & indexing.
     9. Verification.
     10. **STOP and wait for user to say "NEXT"**.
