"""SQLite database connection and transaction management module.

Provides thread-safe connections, mandatory foreign key enforcement (PRAGMA foreign_keys = ON),
atomic transaction context managers, and parameterized query execution helpers.
"""

from contextlib import contextmanager
import logging
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from config import settings

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when establishing a connection to the database fails."""


class DatabaseTransactionError(Exception):
    """Raised when a transactional database operation fails."""


class DBConnectionManager:
    """Manages SQLite connections, pragmas, and transaction lifecycles."""

    def __init__(self, default_db_path: Optional[Union[Path, str]] = None) -> None:
        """Initialize connection manager with a default database file path.

        Args:
            default_db_path: Path to the SQLite database file.
                Defaults to settings.paths.db_path.
        """
        self._default_db_path = Path(default_db_path or settings.paths.db_path)

    @property
    def default_db_path(self) -> Path:
        """Return the configured default database path."""
        return self._default_db_path

    def _resolve_path(self, db_path: Optional[Union[Path, str]] = None) -> Path:
        """Resolve database path, falling back to default.

        Args:
            db_path: Optional override database path.

        Returns:
            Resolved Path object.
        """
        if db_path is not None:
            return Path(db_path)
        return self._default_db_path

    def create_connection(self, db_path: Optional[Union[Path, str]] = None) -> sqlite3.Connection:
        """Create and configure a new SQLite connection.

        Enforces:
        - PRAGMA foreign_keys = ON
        - PRAGMA journal_mode = WAL (Write-Ahead Logging)
        - Row factory = sqlite3.Row for dictionary-like column access

        Args:
            db_path: Path to database file. If None, default_db_path is used.

        Returns:
            Configured sqlite3.Connection object.

        Raises:
            DatabaseConnectionError: If connection creation or pragma execution fails.
        """
        target_path = self._resolve_path(db_path)
        try:
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            conn = sqlite3.connect(
                str(target_path),
                timeout=15.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row

            # Mandatory: Enforce foreign keys on every SQLite connection
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.close()

            return conn
        except sqlite3.Error as exc:
            logger.error("Failed to connect to SQLite database at %s: %s", target_path, exc)
            raise DatabaseConnectionError(f"Database connection error at {target_path}: {exc}") from exc

    @contextmanager
    def get_connection(
        self, db_path: Optional[Union[Path, str]] = None
    ) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding a configured SQLite connection and ensuring closure.

        Args:
            db_path: Optional database path override.

        Yields:
            Active sqlite3.Connection.
        """
        conn = self.create_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(
        self, db_path: Optional[Union[Path, str]] = None
    ) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an atomic ACID transaction.

        Automatically commits on successful block exit.
        Automatically rolls back on any exception before re-raising.

        Args:
            db_path: Optional database path override.

        Yields:
            Active sqlite3.Connection inside an active transaction.

        Raises:
            DatabaseTransactionError: Wrapped exception if a transaction failure occurs.
        """
        conn = self.create_connection(db_path)
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("Transaction rolled back due to error: %s", exc)
            raise DatabaseTransactionError(f"Transaction failed and rolled back: {exc}") from exc
        finally:
            conn.close()

    def execute_query(
        self,
        sql: str,
        params: Union[Tuple[Any, ...], Dict[str, Any]] = (),
        db_path: Optional[Union[Path, str]] = None,
    ) -> List[sqlite3.Row]:
        """Execute a read-only parameterized query and return all matching rows.

        Args:
            sql: Parameterized SQL query string.
            params: Query parameters (tuple or dict).
            db_path: Optional database path override.

        Returns:
            List of sqlite3.Row objects.
        """
        with self.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute_one(
        self,
        sql: str,
        params: Union[Tuple[Any, ...], Dict[str, Any]] = (),
        db_path: Optional[Union[Path, str]] = None,
    ) -> Optional[sqlite3.Row]:
        """Execute a parameterized query and return the first row or None.

        Args:
            sql: Parameterized SQL query string.
            params: Query parameters (tuple or dict).
            db_path: Optional database path override.

        Returns:
            Single sqlite3.Row or None if no result.
        """
        with self.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.fetchone()

    def execute_write(
        self,
        sql: str,
        params: Union[Tuple[Any, ...], Dict[str, Any]] = (),
        db_path: Optional[Union[Path, str]] = None,
    ) -> int:
        """Execute an INSERT, UPDATE, or DELETE statement within a transaction.

        Args:
            sql: Parameterized SQL statement.
            params: Bound parameters.
            db_path: Optional database path override.

        Returns:
            The lastrowid for INSERTs, or rowcount for UPDATEs/DELETEs.
        """
        with self.transaction(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.lastrowid if cursor.lastrowid else cursor.rowcount

    def execute_script(
        self,
        script_sql: str,
        db_path: Optional[Union[Path, str]] = None,
    ) -> None:
        """Execute multiple SQL statements in a script (e.g., DDL migrations).

        Args:
            script_sql: Multi-statement SQL text.
            db_path: Optional database path override.
        """
        with self.transaction(db_path) as conn:
            conn.executescript(script_sql)


# Global singleton connection manager
db_manager = DBConnectionManager()
