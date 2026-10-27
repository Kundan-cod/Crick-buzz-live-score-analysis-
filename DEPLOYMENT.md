# Cricbuzz LiveStats — Deployment Runbook & Operations Guide

This guide provides operational runbooks for deploying, configuring, troubleshooting, and maintaining **Cricbuzz LiveStats** in local development environments and hosted cloud platforms.

---

## 1. Environment Overview & Operational Modes

Cricbuzz LiveStats is designed with a **two-phase architecture**:
- **Current Mode (Offline Demo):** Uses a local, zero-maintenance SQLite database (`data/cricbuzz.db`) populated with 12 multi-format fixtures, 35 players, 10 venues, and authentic innings scorecards marked with `source = 'LOCAL'`. `OFFLINE_MODE=True` is active by default.
- **Future Mode (Live API Integration - Stage 11):** Integrates live Cricbuzz API streams via external data providers (e.g. RapidAPI). Ingests live scorecards into tables with `source = 'API'`.

> **Important Operational Notice:**  
> The current production build runs safely in **Offline Mode**. Do not attempt to call unverified third-party endpoints or expose private API keys in production until Stage 11 has been formally approved and implemented.

---

## 2. Local Development Deployment

### Prerequisites
- **Operating System:** Windows 10/11, macOS 12+, or Linux (Ubuntu 20.04+, Debian 11+, Fedora 38+)
- **Python Runtime:** Python 3.10 to 3.13 (Python 3.13.7 verified)
- **Git:** 2.30+ installed and configured on PATH

### Step-by-Step Local Deployment

#### 1. Repository Setup
```bash
# Clone the repository
git clone https://github.com/your-username/Cricbuzz.git
cd Cricbuzz
```

#### 2. Virtual Environment Configuration
Always run inside an isolated virtual environment to prevent package version conflicts:

```bash
# On Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# On macOS / Linux (bash/zsh)
python3 -m venv venv
source venv/bin/activate
```

#### 3. Dependency Installation
Install locked dependencies from `requirements.txt`:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Verify installed packages:
```bash
pip list
```

#### 4. Environment Variables Configuration
Copy the template configuration file:
```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Review default settings in `.env`:
```ini
# Application Operational Mode
OFFLINE_MODE=True
APP_ENV=development
DEBUG=True

# Database Configuration
DATABASE_PATH=data/cricbuzz.db
SQLITE_TIMEOUT=15.0

# Server Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
STREAMLIT_THEME_BASE=dark

# Stage 11 External API (Deferred - Leave empty)
RAPIDAPI_KEY=
RAPIDAPI_HOST=cricbuzz-cricket.p.rapidapi.com
```

#### 5. Database Initialization & Seeding
Run schema generation and fixture population:
```bash
# Fresh initialization (creates tables, views, and indexes)
python -m database.init_db

# Populate with offline demo fixtures (strictly idempotent)
python -m data.seed_data
```

Verify database health:
```bash
python -c "from database.init_db import validate_database; print(validate_database())"
```
Expected output:
```json
{"status": "valid", "file_exists": true, "integrity_check": "ok", "foreign_keys_enabled": true}
```

#### 6. Launching the Application
Launch the Streamlit dashboard:
```bash
streamlit run app.py
```
The application will open automatically at:
```text
Local URL: http://localhost:8501
Network URL: http://<your-local-ip>:8501
```

---

## 3. Cloud & Server Deployment Scenarios

### Scenario A: Streamlit Community Cloud (Recommended for Demos)

Streamlit Community Cloud provides free, instant deployment directly from GitHub.

1. **Repository Preparation:**
   - Ensure `requirements.txt` contains all runtime dependencies (`streamlit`, `pandas`, `plotly`, `python-dotenv`).
   - Ensure `.streamlit/config.toml` exists with server and theme settings.
   - Commit and push `data/cricbuzz.db` (or ensure `database/init_db.py` runs on startup).
2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io/).
   - Select your GitHub repository, branch (`main`), and main file path (`app.py`).
   - In **Advanced Settings**, configure Secrets if needed:
     ```toml
     OFFLINE_MODE = "True"
     APP_ENV = "production"
     ```
   - Click **Deploy**.

---

### Scenario B: Docker Container Deployment

For containerized environments (AWS ECS, Google Cloud Run, DigitalOcean App Platform, Render):

#### 1. Create `Dockerfile`
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Initialize and seed database inside container
RUN python -m database.init_db && python -m data.seed_data

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### 2. Create `docker-compose.yml`
```yaml
version: '3.8'

services:
  cricbuzz:
    build: .
    ports:
      - "8501:8501"
    environment:
      - OFFLINE_MODE=True
      - APP_ENV=production
    volumes:
      - cricbuzz-data:/app/data
    restart: unless-stopped

volumes:
  cricbuzz-data:
```

#### 3. Build & Run
```bash
docker compose up --build -d
```

---

## 4. Secret Management & Git Hygiene

- **`.env` Exclusion:** Ensure `.env` is listed in `.gitignore` and is never committed to source control.
- **Zero Plaintext Tokens:** API keys (when added in Stage 11) must only be passed via environment variables or cloud secret managers (AWS Secrets Manager, GCP Secret Manager, or Streamlit Cloud Secrets).
- **Log Hygiene:** The logging utility ([`utils/logger.py`](file:///e:/Cricbuzz/utils/logger.py)) writes to `logs/app.log`. Logs must never output raw connection strings or authorization headers.
- **Git Status Check:**
  ```bash
  git status --ignored
  ```
  Ensure `.env`, `venv/`, and `__pycache__/` are ignored.

---

## 5. Troubleshooting Runbook

### Issue 1: `AttributeError: '_GeneratorContextManager' object has no attribute 'cursor'`
- **Cause:** Calling `db_manager.get_connection().cursor()` directly instead of using a Python context manager.
- **Solution:** Always invoke the connection manager with `with`:
  ```python
  # INCORRECT:
  # conn = db_manager.get_connection()
  # cur = conn.cursor()

  # CORRECT:
  with db_manager.get_connection() as conn:
      cur = conn.cursor()
      rows = cur.execute("SELECT ...").fetchall()
  ```

### Issue 2: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2265'`
- **Cause:** Console shells on Windows default to `cp1252` encoding, which cannot render non-ASCII mathematical symbols like `≥`.
- **Solution:** All metadata in `analytics/query_runner.py` uses standard ASCII `>=`. If encountered in external files, set the environment variable:
  ```powershell
  $env:PYTHONIOENCODING = "utf-8"
  ```

### Issue 3: `Port 8501 is already in use`
- **Cause:** Another instance of Streamlit or a background process is bound to port 8501.
- **Solution:** Specify an alternate port or terminate the existing process:
  ```bash
  # Launch on port 8502
  streamlit run app.py --server.port 8502

  # Or find and kill process on port 8501 (Windows PowerShell):
  Get-NetTCPConnection -LocalPort 8501 | Select-Object OwningProcess
  Stop-Process -Id <PID> -Force
  ```

### Issue 4: `sqlite3.OperationalError: no such table: matches`
- **Cause:** Database file has not been initialized.
- **Solution:** Execute initialization script:
  ```bash
  python -m database.init_db
  python -m data.seed_data
  ```

### Issue 5: Plotly Charts Display `undefined` in Title
- **Cause:** Passing `title=None` to Plotly layout configuration.
- **Solution:** The chart utility ([`utils/charts.py`](file:///e:/Cricbuzz/utils/charts.py)) sanitizes titles:
  ```python
  if title:
      fig.update_layout(title=f"<b>{title}</b>")
  else:
      fig.update_layout(title="")
  ```

---

## 6. Pre-Flight Deployment Checklist

Before submitting for grading or publishing to a live demo environment:

- [x] All 109 automated tests pass (`python -m pytest -v`).
- [x] SQLite database integrity check reports `ok` (`PRAGMA integrity_check`).
- [x] Foreign-key constraint enforcement verified (`PRAGMA foreign_key_check` returns 0).
- [x] `OFFLINE_MODE=True` is verified in `config.py` and `.env`.
- [x] All 25 analytical SQL questions execute without errors.
- [x] Q21 composite ranking formula is marked `PENDING REVIEW` per ADR-005.
- [x] Demonstration fixtures are labelled with `source = 'LOCAL'`.
- [x] `.env` is absent from git tracking (`.gitignore` verified).
- [x] All 6 multi-page interfaces compile and render cleanly via `streamlit run app.py`.
- [x] Logging is functional and writes to `logs/app.log`.
