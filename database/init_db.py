"""Database bootstrapping, schema initialization, and health validation module.

Supports safe, idempotent database initialization and comprehensive validation:
- Validates tables, views, indexes, and foreign-key constraints.
- Executes PRAGMA integrity_check and PRAGMA foreign_keys verification.
- Clearly distinguishes fresh initialization from validation of an existing database.
- Never silently deletes or overwrites existing data unless explicitly requested.
"""

import argparse
from dataclasses import dataclass, field
import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional, Union

from config import settings
from database.connection import DBConnectionManager, db_manager

logger = logging.getLogger(__name__)

# Expected canonical schema entities
EXPECTED_TABLES = [
    "teams",
    "players",
    "venues",
    "series",
    "matches",
    "innings",
    "batting_performances",
    "bowling_performances",
    "fielding_performances",
    "partnerships",
]

EXPECTED_VIEWS = [
    "v_match_details",
    "v_innings_summary",
    "v_player_batting_by_format",
    "v_player_bowling_by_format",
    "v_player_career_totals",
]

EXPECTED_INDEXES = [
    "idx_players_team_id",
    "idx_players_country",
    "idx_players_role",
    "idx_matches_date",
    "idx_matches_format",
    "idx_matches_teams",
    "idx_matches_venue",
    "idx_matches_winner",
    "idx_matches_external_id",
    "idx_innings_match",
    "idx_batting_player",
    "idx_batting_innings",
    "idx_batting_runs",
    "idx_bowling_player",
    "idx_bowling_innings",
    "idx_bowling_wickets",
    "idx_fielding_player",
    "idx_fielding_innings",
    "idx_partnerships_players",
    "idx_partnerships_innings",
]


@dataclass
class ValidationReport:
    """Detailed health and schema validation report for an SQLite database."""

    db_path: Path
    file_exists: bool
    integrity_ok: bool
    foreign_keys_enabled: bool
    tables_found: List[str] = field(default_factory=list)
    missing_tables: List[str] = field(default_factory=list)
    views_found: List[str] = field(default_factory=list)
    missing_views: List[str] = field(default_factory=list)
    indexes_found: List[str] = field(default_factory=list)
    missing_indexes: List[str] = field(default_factory=list)
    foreign_key_count: int = 0
    row_counts: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return True if all critical integrity, schema, and configuration checks pass."""
        return (
            self.file_exists
            and self.integrity_ok
            and self.foreign_keys_enabled
            and len(self.missing_tables) == 0
            and len(self.missing_views) == 0
            and len(self.errors) == 0
        )


@dataclass
class InitResult:
    """Outcome of an initialization or validation operation."""

    action: str  # 'FRESH_INITIALIZATION', 'EXISTING_VALIDATED', 'FORCE_RECREATED', 'VALIDATION_FAILED'
    db_path: Path
    validation_report: ValidationReport
    message: str


def validate_database(
    db_path: Optional[Union[Path, str]] = None,
    manager: Optional[DBConnectionManager] = None,
) -> ValidationReport:
    """Perform comprehensive structural and integrity validation of the database.

    Args:
        db_path: Path to database file. Defaults to settings.paths.db_path.
        manager: Optional DBConnectionManager instance.

    Returns:
        ValidationReport instance containing detailed diagnostic information.
    """
    mgr = manager or db_manager
    target_path = Path(db_path or mgr.default_db_path)

    if not target_path.exists():
        return ValidationReport(
            db_path=target_path,
            file_exists=False,
            integrity_ok=False,
            foreign_keys_enabled=False,
            missing_tables=list(EXPECTED_TABLES),
            missing_views=list(EXPECTED_VIEWS),
            missing_indexes=list(EXPECTED_INDEXES),
            errors=["Database file does not exist."],
        )

    errors: List[str] = []
    tables_found: List[str] = []
    views_found: List[str] = []
    indexes_found: List[str] = []
    row_counts: Dict[str, int] = {}
    fk_count = 0
    integrity_ok = False
    fk_enabled = False

    try:
        with mgr.get_connection(target_path) as conn:
            cursor = conn.cursor()

            # 1. SQLite PRAGMA integrity_check
            cursor.execute("PRAGMA integrity_check;")
            integrity_rows = cursor.fetchall()
            if integrity_rows and integrity_rows[0][0] == "ok":
                integrity_ok = True
            else:
                err_msg = f"Integrity check failed: {[r[0] for r in integrity_rows]}"
                errors.append(err_msg)

            # 2. PRAGMA foreign_keys verification
            cursor.execute("PRAGMA foreign_keys;")
            fk_row = cursor.fetchone()
            if fk_row and fk_row[0] == 1:
                fk_enabled = True
            else:
                errors.append("Foreign keys PRAGMA is not enabled on connection.")

            # 3. Retrieve all existing tables and row counts
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            )
            tables_found = [row[0] for row in cursor.fetchall()]

            for tbl in tables_found:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tbl};")  # Table names verified from sqlite_master
                    count = cursor.fetchone()[0]
                    row_counts[tbl] = count
                except Exception as exc:
                    row_counts[tbl] = -1
                    errors.append(f"Could not count rows in {tbl}: {exc}")

                # Count foreign key definitions on this table
                cursor.execute(f"PRAGMA foreign_key_list({tbl});")
                fk_count += len(cursor.fetchall())

            # 4. Retrieve all existing views
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view';")
            views_found = [row[0] for row in cursor.fetchall()]

            # 5. Retrieve all existing indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
            indexes_found = [row[0] for row in cursor.fetchall()]

    except Exception as exc:
        errors.append(f"Connection or diagnostic execution error: {exc}")

    missing_tables = [t for t in EXPECTED_TABLES if t not in tables_found]
    missing_views = [v for v in EXPECTED_VIEWS if v not in views_found]
    missing_indexes = [idx for idx in EXPECTED_INDEXES if idx not in indexes_found]

    return ValidationReport(
        db_path=target_path,
        file_exists=True,
        integrity_ok=integrity_ok,
        foreign_keys_enabled=fk_enabled,
        tables_found=tables_found,
        missing_tables=missing_tables,
        views_found=views_found,
        missing_views=missing_views,
        indexes_found=indexes_found,
        missing_indexes=missing_indexes,
        foreign_key_count=fk_count,
        row_counts=row_counts,
        errors=errors,
    )


def init_database(
    db_path: Optional[Union[Path, str]] = None,
    force_recreate: bool = False,
    manager: Optional[DBConnectionManager] = None,
) -> InitResult:
    """Initialize or validate the database schema safely and idempotently.

    - If the database file does not exist, a fresh initialization is performed.
    - If the file exists and force_recreate is False, existing data is preserved,
      idempotent schema scripts are executed to ensure consistency, and validation is run.
    - If force_recreate is True, the file is unlinked and recreated from scratch.

    Args:
        db_path: Target database file path.
        force_recreate: Explicit flag to wipe and rebuild from scratch. Default False.
        manager: Optional DBConnectionManager instance.

    Returns:
        InitResult detailing the action taken and final validation status.
    """
    mgr = manager or db_manager
    target_path = Path(db_path or mgr.default_db_path)
    file_already_existed = target_path.exists()

    schema_file = settings.paths.sql_dir / "schema.sql"
    views_file = settings.paths.sql_dir / "views.sql"

    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found at {schema_file}")
    if not views_file.exists():
        raise FileNotFoundError(f"Views file not found at {views_file}")

    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with open(views_file, "r", encoding="utf-8") as f:
        views_sql = f.read()

    action = ""

    if file_already_existed and force_recreate:
        logger.warning("Force recreate requested: Removing existing database at %s", target_path)
        try:
            target_path.unlink()
            action = "FORCE_RECREATED"
        except Exception as exc:
            raise RuntimeError(f"Unable to delete existing database for recreation: {exc}") from exc
    elif file_already_existed:
        action = "EXISTING_VALIDATED"
    else:
        action = "FRESH_INITIALIZATION"

    # Execute DDL scripts (idempotent CREATE TABLE IF NOT EXISTS and CREATE VIEW IF NOT EXISTS)
    mgr.execute_script(schema_sql, db_path=target_path)
    mgr.execute_script(views_sql, db_path=target_path)

    # Validate the final state
    report = validate_database(db_path=target_path, manager=mgr)

    if not report.is_valid:
        action = "VALIDATION_FAILED"
        message = (
            f"Database initialization completed but validation failed with errors: {report.errors}, "
            f"missing tables: {report.missing_tables}, missing views: {report.missing_views}"
        )
        logger.error(message)
    else:
        if action == "FRESH_INITIALIZATION":
            message = f"Fresh database initialized successfully at {target_path}."
        elif action == "FORCE_RECREATED":
            message = f"Database wiped and cleanly recreated at {target_path}."
        else:
            message = f"Existing database validated and synchronized successfully at {target_path}."
        logger.info(message)

    return InitResult(
        action=action,
        db_path=target_path,
        validation_report=report,
        message=message,
    )


def print_validation_report(report: ValidationReport, action_title: str = "Validation Report") -> None:
    """Print a clean, human-readable summary of the validation report."""
    print("=" * 70)
    print(f"Cricbuzz LiveStats - {action_title}")
    print("=" * 70)
    print(f"Database File:          {report.db_path}")
    print(f"File Exists:            {report.file_exists}")
    print(f"Overall Status:         {'[VALID]' if report.is_valid else '[INVALID]'}")
    print(f"SQLite Integrity Check: {'PASS (ok)' if report.integrity_ok else 'FAIL'}")
    print(f"Foreign Keys Enforced:  {'YES (PRAGMA foreign_keys = 1)' if report.foreign_keys_enabled else 'NO'}")
    print(f"Tables Found ({len(report.tables_found)}/{len(EXPECTED_TABLES)}):   {', '.join(sorted(report.tables_found))}")
    if report.missing_tables:
        print(f"MISSING TABLES:         {', '.join(report.missing_tables)}")
    print(f"Views Found ({len(report.views_found)}/{len(EXPECTED_VIEWS)}):    {', '.join(sorted(report.views_found))}")
    if report.missing_views:
        print(f"MISSING VIEWS:          {', '.join(report.missing_views)}")
    print(f"Indexes Count:          {len(report.indexes_found)} defined")
    if report.missing_indexes:
        print(f"Missing Indexes:        {', '.join(report.missing_indexes)}")
    print(f"Foreign Key Refs Count: {report.foreign_key_count}")
    print("-" * 70)
    print("Row Counts per Table:")
    for tbl, count in sorted(report.row_counts.items()):
        print(f"  - {tbl:<24} : {count} rows")
    if report.errors:
        print("-" * 70)
        print("Validation Errors:")
        for err in report.errors:
            print(f"  [!] {err}")
    print("=" * 70)


def main() -> None:
    """CLI entrypoint for database initialization and validation."""
    parser = argparse.ArgumentParser(description="Cricbuzz LiveStats Database Initializer & Validator")
    parser.add_argument("--validate-only", action="store_true", help="Run validation without executing DDL scripts")
    parser.add_argument("--force-recreate", action="store_true", help="Delete and recreate database from scratch")
    parser.add_argument("--db-path", type=str, default=None, help="Custom database path")
    args = parser.parse_args()

    custom_path = Path(args.db_path) if args.db_path else None

    if args.validate_only:
        report = validate_database(db_path=custom_path)
        print_validation_report(report, action_title="Validation Check Only")
        sys.exit(0 if report.is_valid else 1)
    else:
        result = init_database(db_path=custom_path, force_recreate=args.force_recreate)
        print_validation_report(result.validation_report, action_title=f"Result: {result.action}")
        print(f"\n{result.message}")
        sys.exit(0 if result.validation_report.is_valid else 1)


if __name__ == "__main__":
    main()
