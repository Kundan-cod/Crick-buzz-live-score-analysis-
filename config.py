"""Central configuration module for Cricbuzz LiveStats.

Loads environment variables, defines paths, and manages runtime settings
for the database, offline fixtures, Streamlit interface, and logging.
"""

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Base directory for the entire project
BASE_DIR = Path(__file__).resolve().parent

# Load local environment variables from .env if present
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)


@dataclass(frozen=True)
class PathConfig:
    """Project directory and file paths."""

    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    fixtures_dir: Path = BASE_DIR / "data" / "fixtures"
    sql_dir: Path = BASE_DIR / "sql"
    queries_dir: Path = BASE_DIR / "sql" / "queries"
    logs_dir: Path = BASE_DIR / "logs"
    docs_dir: Path = BASE_DIR / "docs"
    db_path: Path = BASE_DIR / "data" / "cricbuzz.db"
    log_file: Path = BASE_DIR / "logs" / "app.log"


@dataclass(frozen=True)
class DatabaseConfig:
    """Relational database connection parameters."""

    engine: str = field(
        default_factory=lambda: os.getenv("DB_ENGINE", "sqlite").lower()
    )
    db_name: str = field(
        default_factory=lambda: os.getenv("DB_NAME", "cricbuzz.db")
    )
    db_path: Path = field(
        default_factory=lambda: BASE_DIR / "data" / os.getenv("DB_NAME", "cricbuzz.db")
    )


@dataclass(frozen=True)
class APIConfig:
    """Cricket API integration settings (Stage 11)."""

    offline_mode: bool = field(
        default_factory=lambda: os.getenv("OFFLINE_MODE", "true").lower() in ("true", "1", "yes")
    )
    provider: str = field(
        default_factory=lambda: os.getenv("CRICKET_API_PROVIDER", "cricketdata").lower()
    )
    cricketdata_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("CRICKETDATA_API_KEY")
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("CRICBUZZ_API_KEY") or os.getenv("RAPIDAPI_KEY")
    )
    api_host: str = field(
        default_factory=lambda: os.getenv("CRICBUZZ_API_HOST", "cricbuzz-cricket.p.rapidapi.com")
    )
    timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("API_TIMEOUT_SECONDS", "10"))
    )
    cache_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("API_CACHE_TTL_SECONDS", "60"))
    )
    max_retries: int = 3


@dataclass(frozen=True)
class AppConfig:
    """Streamlit application appearance and runtime parameters."""

    app_title: str = "Cricbuzz LiveStats: Real-Time Cricket Insights & SQL-Based Analytics"
    app_short_title: str = "Cricbuzz LiveStats"
    page_icon: str = "🏏"
    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    debug: bool = field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper()
    )


class Settings:
    """Unified settings container providing access to all sub-configurations."""

    def __init__(self) -> None:
        """Initialize all sub-configurations and ensure directories exist."""
        self.paths = PathConfig()
        self.db = DatabaseConfig()
        self.api = APIConfig()
        self.app = AppConfig()
        self.ensure_directories()

    def ensure_directories(self) -> None:
        """Create essential application directories if they do not exist."""
        for directory in [
            self.paths.data_dir,
            self.paths.fixtures_dir,
            self.paths.sql_dir,
            self.paths.queries_dir,
            self.paths.logs_dir,
            self.paths.docs_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Global singleton settings instance
settings = Settings()
