"""Query runner module for safe, monitored execution of approved SQL analytical queries.

Loads pre-approved, versioned SQL query files from disk, performs parameterized
execution against SQLite databases, gathers execution timing and plan metrics,
and converts results into structured dictionaries and Pandas DataFrames.
Arbitrary user-supplied SQL execution is strictly disallowed.
"""

from dataclasses import asdict, dataclass, field
import logging
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from config import settings
from database.connection import DBConnectionManager, db_manager

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Domain Exceptions
# ------------------------------------------------------------------------------

class QueryRunnerError(Exception):
    """Base exception for query runner operations."""


class QueryNotFoundError(QueryRunnerError):
    """Raised when a requested query ID is not found in the approved catalog."""


class QueryNotImplementedError(QueryRunnerError):
    """Raised when a query is registered in catalog but not yet approved/implemented."""


class QueryExecutionError(QueryRunnerError):
    """Raised when executing an approved SQL query fails at runtime."""


# ------------------------------------------------------------------------------
# Data Models
# ------------------------------------------------------------------------------

@dataclass
class QueryMetadata:
    """Metadata describing an approved SQL analytical query."""

    query_id: str
    title: str
    level: str  # Beginner, Intermediate, Advanced
    description: str
    sql_file: str
    is_implemented: bool = False
    params_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    """Structured result returned after executing an approved SQL query."""

    query_id: str
    title: str
    level: str
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    description: str
    error: Optional[str] = None

    def to_dataframe(self) -> pd.DataFrame:
        """Convert result rows into a Pandas DataFrame."""
        if not self.rows:
            return pd.DataFrame(columns=self.columns)
        return pd.DataFrame(self.rows)


# ------------------------------------------------------------------------------
# Master Catalog of 25 SQL Questions
# ------------------------------------------------------------------------------

QUERY_CATALOG: Dict[str, QueryMetadata] = {
    "q01": QueryMetadata(
        query_id="q01",
        title="India Players (Roles & Styles)",
        level="Beginner",
        description="Find all players who represent India with their playing role, batting style, and bowling style.",
        sql_file="q01.sql",
        is_implemented=True,
    ),
    "q02": QueryMetadata(
        query_id="q02",
        title="Matches in Last 30 Days",
        level="Beginner",
        description="Show matches played in the last 30 days including description, teams, venue city, and date.",
        sql_file="q02.sql",
        is_implemented=True,
    ),
    "q03": QueryMetadata(
        query_id="q03",
        title="Top 10 ODI Run Scorers",
        level="Beginner",
        description="List top 10 ODI run scorers with runs, batting average, and centuries, sorted descending.",
        sql_file="q03.sql",
        is_implemented=True,
    ),
    "q04": QueryMetadata(
        query_id="q04",
        title="Large Venues (>50,000 Capacity)",
        level="Beginner",
        description="Display venues with seating capacity > 50,000 with city, country, and capacity.",
        sql_file="q04.sql",
        is_implemented=True,
    ),
    "q05": QueryMetadata(
        query_id="q05",
        title="Team Wins Summary",
        level="Beginner",
        description="Calculate matches won per team, transparently handling tied and abandoned matches.",
        sql_file="q05.sql",
        is_implemented=True,
    ),
    "q06": QueryMetadata(
        query_id="q06",
        title="Player Counts by Role",
        level="Beginner",
        description="Count players in each playing role (Batter, Bowler, All-rounder, Wicket-keeper).",
        sql_file="q06.sql",
        is_implemented=True,
    ),
    "q07": QueryMetadata(
        query_id="q07",
        title="Highest Individual Score by Format",
        level="Beginner",
        description="Find the highest individual score achieved in Test, ODI, and T20I formats.",
        sql_file="q07.sql",
        is_implemented=True,
    ),
    "q08": QueryMetadata(
        query_id="q08",
        title="Series Started in 2024",
        level="Beginner",
        description="Show series started in 2024 with host country, format, start date, and total matches.",
        sql_file="q08.sql",
        is_implemented=True,
    ),
    "q09": QueryMetadata(
        query_id="q09",
        title="All-rounders (>1,000 Runs & >50 Wickets)",
        level="Intermediate",
        description="Find all-rounders with > 1,000 career runs AND > 50 career wickets.",
        sql_file="q09.sql",
        is_implemented=True,
    ),
    "q10": QueryMetadata(
        query_id="q10",
        title="Last 20 Completed Matches with Margins",
        level="Intermediate",
        description="Retrieve last 20 completed matches showing description, teams, winner, and victory margin.",
        sql_file="q10.sql",
        is_implemented=True,
    ),
    "q11": QueryMetadata(
        query_id="q11",
        title="Cross-Format Player Performance",
        level="Intermediate",
        description="For players with >= 2 formats, show Test, ODI, and T20I runs and combined batting average.",
        sql_file="q11.sql",
        is_implemented=True,
    ),
    "q12": QueryMetadata(
        query_id="q12",
        title="Home vs. Away Performance",
        level="Intermediate",
        description="For each team, count wins at home vs. away by comparing venue country with team country.",
        sql_file="q12.sql",
        is_implemented=True,
    ),
    "q13": QueryMetadata(
        query_id="q13",
        title="Consecutive Batting-Position Pairs (Sum >= 100)",
        level="Intermediate",
        description="Find pairs of consecutive batting positions whose individual scores sum to >= 100.",
        sql_file="q13.sql",
        is_implemented=True,
    ),
    "q14": QueryMetadata(
        query_id="q14",
        title="Venue Bowling Analysis",
        level="Intermediate",
        description="For bowlers with >= 3 matches at a venue, calculate average economy rate and wickets.",
        sql_file="q14.sql",
        is_implemented=True,
    ),
    "q15": QueryMetadata(
        query_id="q15",
        title="Players in Close Matches",
        level="Intermediate",
        description="Identify player performance in close matches (decided by < 50 runs or < 5 wickets).",
        sql_file="q15.sql",
        is_implemented=True,
    ),
    "q16": QueryMetadata(
        query_id="q16",
        title="Yearly Batting Trends Since 2020",
        level="Intermediate",
        description="Show average runs and strike rate per year for matches since 2020 (min 5 matches/year).",
        sql_file="q16.sql",
        is_implemented=True,
    ),
    "q17": QueryMetadata(
        query_id="q17",
        title="Toss Advantage Analysis",
        level="Advanced",
        description="Calculate win percentage of toss-winning teams segmented by decision to bat vs bowl.",
        sql_file="q17.sql",
        is_implemented=True,
    ),
    "q18": QueryMetadata(
        query_id="q18",
        title="Economical Limited-Overs Bowlers",
        level="Advanced",
        description="Calculate economy rate and wickets for bowlers with >= 10 limited-overs matches.",
        sql_file="q18.sql",
        is_implemented=True,
    ),
    "q19": QueryMetadata(
        query_id="q19",
        title="Batting Consistency (Standard Deviation)",
        level="Advanced",
        description="Calculate average runs and standard deviation of runs for players facing >= 10 balls.",
        sql_file="q19.sql",
        is_implemented=True,
    ),
    "q20": QueryMetadata(
        query_id="q20",
        title="Matches & Averages by Format",
        level="Advanced",
        description="Display Test, ODI, and T20 match counts and batting averages for players with >= 20 matches.",
        sql_file="q20.sql",
        is_implemented=True,
    ),
    "q21": QueryMetadata(
        query_id="q21",
        title="Weighted Player Ranking (PENDING REVIEW)",
        level="Advanced",
        description="Composite ranking combining batting, bowling, and fielding points (Scoring formula PENDING REVIEW).",
        sql_file="q21.sql",
        is_implemented=True,
    ),
    "q22": QueryMetadata(
        query_id="q22",
        title="Team Head-to-Head Analysis",
        level="Advanced",
        description="For team pairs with >= 5 matches in the last 3 years, calculate head-to-head records and win percentages.",
        sql_file="q22.sql",
        is_implemented=True,
    ),
    "q23": QueryMetadata(
        query_id="q23",
        title="Recent Player Form & Momentum",
        level="Advanced",
        description="Compare last 5 vs last 10 average runs, strike rate trend, and assign form tiers.",
        sql_file="q23.sql",
        is_implemented=True,
    ),
    "q24": QueryMetadata(
        query_id="q24",
        title="Batting Partnerships Analysis",
        level="Advanced",
        description="For batsman pairs partnering in >= 5 stands, calculate average runs, 50+ stands, and success rate.",
        sql_file="q24.sql",
        is_implemented=True,
    ),
    "q25": QueryMetadata(
        query_id="q25",
        title="Quarterly Career Trajectory",
        level="Advanced",
        description="Time-series analysis tracking quarterly runs and strike rates across career quarters.",
        sql_file="q25.sql",
        is_implemented=True,
    ),
}


# ------------------------------------------------------------------------------
# Query Runner Implementation
# ------------------------------------------------------------------------------

class QueryRunner:
    """Safely manages, inspects, and executes approved SQL queries."""

    def __init__(
        self,
        queries_dir: Optional[Union[Path, str]] = None,
        manager: Optional[DBConnectionManager] = None,
    ) -> None:
        """Initialize QueryRunner.

        Args:
            queries_dir: Directory containing SQL query files.
                Defaults to settings.paths.sql_dir / 'queries'.
            manager: DBConnectionManager instance. Defaults to db_manager.
        """
        self.queries_dir = Path(queries_dir or (settings.paths.sql_dir / "queries"))
        self.db = manager or db_manager

    def get_catalog(self, level: Optional[str] = None) -> List[QueryMetadata]:
        """Return registered query metadata, optionally filtered by difficulty level.

        Args:
            level: Optional filter ('Beginner', 'Intermediate', 'Advanced').

        Returns:
            List of QueryMetadata objects.
        """
        queries = list(QUERY_CATALOG.values())
        if level:
            queries = [q for q in queries if q.level.lower() == level.lower()]
        return queries

    def get_query_metadata(self, query_id: str) -> QueryMetadata:
        """Retrieve metadata for a specific query ID.

        Args:
            query_id: Query identifier (e.g. 'q01').

        Returns:
            QueryMetadata for the requested ID.

        Raises:
            QueryNotFoundError: If query_id is not in catalog.
        """
        qid = query_id.strip().lower()
        if qid not in QUERY_CATALOG:
            raise QueryNotFoundError(
                f"Query '{query_id}' is not recognized in the approved analytics catalog."
            )
        return QUERY_CATALOG[qid]

    def get_query_sql(self, query_id: str) -> str:
        """Read and return the raw SQL content for an approved query.

        Args:
            query_id: Query identifier (e.g. 'q01').

        Returns:
            SQL statement text as string.

        Raises:
            QueryNotFoundError: If query ID is not in catalog.
            QueryNotImplementedError: If query file is not yet approved/implemented.
        """
        meta = self.get_query_metadata(query_id)
        if not meta.is_implemented:
            raise QueryNotImplementedError(
                f"Query '{query_id}' ({meta.title}) is scheduled for a future stage and not yet implemented."
            )

        sql_path = self.queries_dir / meta.sql_file
        if not sql_path.exists():
            raise QueryNotImplementedError(
                f"SQL file for query '{query_id}' not found at: {sql_path}"
            )

        return sql_path.read_text(encoding="utf-8")

    def execute_query(
        self,
        query_id: str,
        params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None,
        db_path: Optional[Union[Path, str]] = None,
    ) -> QueryResult:
        """Execute an approved analytical query by ID.

        Arbitrary SQL statements are forbidden. Only pre-registered, versioned
        SQL files from the catalog can be executed.

        Args:
            query_id: Query identifier (e.g. 'q01').
            params: Optional parameter bindings (dict or tuple).
            db_path: Optional database path override.

        Returns:
            QueryResult containing columns, rows, timing, and DataFrame conversion.

        Raises:
            QueryNotFoundError: If query is not in catalog.
            QueryNotImplementedError: If query is not yet implemented.
            QueryExecutionError: If SQLite execution encounters a syntax or runtime error.
        """
        meta = self.get_query_metadata(query_id)
        sql = self.get_query_sql(query_id)
        bound_params = params or ()

        start_time = time.perf_counter()
        try:
            with self.db.get_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, bound_params)
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                raw_rows = cursor.fetchall()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                rows = [dict(r) for r in raw_rows]
                return QueryResult(
                    query_id=meta.query_id,
                    title=meta.title,
                    level=meta.level,
                    sql=sql,
                    columns=column_names,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=round(elapsed_ms, 2),
                    description=meta.description,
                )
        except sqlite3.Error as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Failed to execute query %s: %s", query_id, exc)
            raise QueryExecutionError(
                f"Execution failed for query '{query_id}' ({meta.title}): {exc}"
            ) from exc

    def explain_query_plan(
        self,
        query_id: str,
        params: Optional[Union[Dict[str, Any], Tuple[Any, ...]]] = None,
        db_path: Optional[Union[Path, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve SQLite query execution plan via EXPLAIN QUERY PLAN.

        Provides educational visibility into index usage and table scans.

        Args:
            query_id: Query identifier.
            params: Optional query parameters.
            db_path: Optional database path override.

        Returns:
            List of plan step dictionaries (id, parent, notused, detail).
        """
        sql = self.get_query_sql(query_id)
        explain_sql = f"EXPLAIN QUERY PLAN {sql}"
        bound_params = params or ()

        with self.db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(explain_sql, bound_params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


# Global singleton instance
query_runner = QueryRunner()
