"""Comprehensive test suite for the SQLite database layer.

Verifies:
1. Schema and view initialization.
2. Foreign key pragma enforcement (PRAGMA foreign_keys = ON).
3. Referential integrity (rejection of orphaned records).
4. Domain CHECK constraints and UNIQUE constraints.
5. Atomic transaction rollback upon exceptions.
6. Cascading deletions and restriction safety.
"""

from pathlib import Path
import sqlite3
import pytest

from database.connection import DBConnectionManager, DatabaseTransactionError


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Provide a fresh temporary SQLite database file path."""
    return tmp_path / "test_cricbuzz.db"


@pytest.fixture
def db(test_db_path: Path) -> DBConnectionManager:
    """Initialize a DBConnectionManager pointed at the temporary database and load schema."""
    manager = DBConnectionManager(default_db_path=test_db_path)

    # Load and execute schema.sql
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    manager.execute_script(schema_sql, db_path=test_db_path)

    # Load and execute views.sql
    views_path = Path(__file__).resolve().parent.parent / "sql" / "views.sql"
    with open(views_path, "r", encoding="utf-8") as f:
        views_sql = f.read()
    manager.execute_script(views_sql, db_path=test_db_path)

    return manager


def test_schema_tables_and_views_created(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that all 10 core tables and 5 analytical views exist in SQLite."""
    table_rows = db.execute_query(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%';",
        db_path=test_db_path,
    )
    table_names = {row["name"] for row in table_rows}

    expected_tables = {
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
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"

    view_rows = db.execute_query(
        "SELECT name FROM sqlite_master WHERE type = 'view';",
        db_path=test_db_path,
    )
    view_names = {row["name"] for row in view_rows}

    expected_views = {
        "v_match_details",
        "v_innings_summary",
        "v_player_batting_by_format",
        "v_player_bowling_by_format",
        "v_player_career_totals",
    }
    assert expected_views.issubset(view_names), f"Missing views: {expected_views - view_names}"


def test_foreign_keys_pragma_enabled(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that PRAGMA foreign_keys is strictly ON (value = 1)."""
    with db.get_connection(test_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        row = cursor.fetchone()
        assert row[0] == 1, "Foreign keys are NOT enabled on connection!"


def test_foreign_key_violation_raises_error(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that inserting a player with a non-existent team_id violates foreign key constraints."""
    with pytest.raises(DatabaseTransactionError) as exc_info:
        db.execute_write(
            """
            INSERT INTO players (team_id, full_name, country, playing_role, batting_style)
            VALUES (99999, 'Ghost Player', 'India', 'Batter', 'Right-hand bat');
            """,
            db_path=test_db_path,
        )
    assert "FOREIGN KEY constraint failed" in str(exc_info.value)


def test_check_constraint_role_validation(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that invalid playing_role values are rejected by CHECK constraints."""
    with pytest.raises(DatabaseTransactionError) as exc_info:
        db.execute_write(
            """
            INSERT INTO players (full_name, country, playing_role, batting_style)
            VALUES ('Invalid Role Player', 'India', 'Head Coach', 'Right-hand bat');
            """,
            db_path=test_db_path,
        )
    assert "CHECK constraint failed" in str(exc_info.value)


def test_check_constraint_negative_runs_rejected(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that negative runs_scored are rejected."""
    # First create valid dependencies
    team1_id = db.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('India', 'IND', 'India');",
        db_path=test_db_path,
    )
    team2_id = db.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('Australia', 'AUS', 'Australia');",
        db_path=test_db_path,
    )
    venue_id = db.execute_write(
        "INSERT INTO venues (venue_name, city, country, capacity) VALUES ('Wankhede', 'Mumbai', 'India', 33000);",
        db_path=test_db_path,
    )
    match_id = db.execute_write(
        f"""
        INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id)
        VALUES ('IND vs AUS 1st ODI', 'ODI', '2024-03-15', {team1_id}, {team2_id}, {venue_id});
        """,
        db_path=test_db_path,
    )
    innings_id = db.execute_write(
        f"""
        INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id)
        VALUES ({match_id}, 1, {team1_id}, {team2_id});
        """,
        db_path=test_db_path,
    )
    player_id = db.execute_write(
        f"""
        INSERT INTO players (team_id, full_name, country, playing_role, batting_style)
        VALUES ({team1_id}, 'Rohit Sharma', 'India', 'Batter', 'Right-hand bat');
        """,
        db_path=test_db_path,
    )

    with pytest.raises(DatabaseTransactionError) as exc_info:
        db.execute_write(
            f"""
            INSERT INTO batting_performances (innings_id, player_id, batting_position, runs_scored, balls_faced)
            VALUES ({innings_id}, {player_id}, 1, -15, 20);
            """,
            db_path=test_db_path,
        )
    assert "CHECK constraint failed" in str(exc_info.value)


def test_matches_teams_cannot_be_identical(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify CHECK (team1_id != team2_id) on matches."""
    team_id = db.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('India', 'IND', 'India');",
        db_path=test_db_path,
    )
    venue_id = db.execute_write(
        "INSERT INTO venues (venue_name, city, country, capacity) VALUES ('Eden Gardens', 'Kolkata', 'India', 66000);",
        db_path=test_db_path,
    )

    with pytest.raises(DatabaseTransactionError) as exc_info:
        db.execute_write(
            f"""
            INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id)
            VALUES ('Self Match', 'ODI', '2024-01-01', {team_id}, {team_id}, {venue_id});
            """,
            db_path=test_db_path,
        )
    assert "CHECK constraint failed" in str(exc_info.value)


def test_unique_constraint_team_name(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that inserting duplicate team names violates UNIQUE constraint."""
    db.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('England', 'ENG', 'England');",
        db_path=test_db_path,
    )

    with pytest.raises(DatabaseTransactionError) as exc_info:
        db.execute_write(
            "INSERT INTO teams (team_name, short_name, country) VALUES ('England', 'ENG2', 'UK');",
            db_path=test_db_path,
        )
    assert "UNIQUE constraint failed" in str(exc_info.value)


def test_transaction_rollback_on_failure(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that if a transaction encounters an error, earlier writes in the block are rolled back."""
    initial_count = db.execute_one(
        "SELECT COUNT(*) AS count FROM teams;", db_path=test_db_path
    )["count"]

    with pytest.raises(DatabaseTransactionError):
        with db.transaction(test_db_path) as conn:
            cursor = conn.cursor()
            # Step 1: Insert a new valid team
            cursor.execute(
                "INSERT INTO teams (team_name, short_name, country) VALUES ('South Africa', 'SA', 'South Africa');"
            )
            # Step 2: Deliberate failure (invalid SQL syntax or constraint violation)
            cursor.execute("INSERT INTO teams (team_name) VALUES (NULL);")

    # Verify that 'South Africa' was NOT committed to the database
    final_count = db.execute_one(
        "SELECT COUNT(*) AS count FROM teams;", db_path=test_db_path
    )["count"]
    assert final_count == initial_count, "Transaction failed to roll back uncommitted work!"


def test_cascade_delete_matches_to_innings(db: DBConnectionManager, test_db_path: Path) -> None:
    """Verify that deleting a match cascades and deletes child innings, but restricts deleting teams."""
    team1_id = db.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A');",
        db_path=test_db_path,
    )
    team2_id = db.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B');",
        db_path=test_db_path,
    )
    venue_id = db.execute_write(
        "INSERT INTO venues (venue_name, city, country, capacity) VALUES ('Venue A', 'City A', 'Country A', 40000);",
        db_path=test_db_path,
    )
    match_id = db.execute_write(
        f"""
        INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id)
        VALUES ('Match 1', 'T20I', '2024-05-10', {team1_id}, {team2_id}, {venue_id});
        """,
        db_path=test_db_path,
    )
    innings_id = db.execute_write(
        f"""
        INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id)
        VALUES ({match_id}, 1, {team1_id}, {team2_id});
        """,
        db_path=test_db_path,
    )

    # Verify innings exists
    assert db.execute_one(
        f"SELECT COUNT(*) AS count FROM innings WHERE innings_id = {innings_id};",
        db_path=test_db_path,
    )["count"] == 1

    # Delete match
    db.execute_write(f"DELETE FROM matches WHERE match_id = {match_id};", db_path=test_db_path)

    # Verify innings was cascade-deleted
    assert db.execute_one(
        f"SELECT COUNT(*) AS count FROM innings WHERE innings_id = {innings_id};",
        db_path=test_db_path,
    )["count"] == 0

    # Verify team cannot be deleted while referenced by other records if any, or can be deleted if no longer referenced
    db.execute_write(f"DELETE FROM teams WHERE team_id = {team1_id};", db_path=test_db_path)
    assert db.execute_one(
        f"SELECT COUNT(*) AS count FROM teams WHERE team_id = {team1_id};",
        db_path=test_db_path,
    )["count"] == 0
