"""Automated test suite for database initialization and schema validation (Stage 3).

Verifies:
1. Fresh database initialization on a new file.
2. Safe repeated initialization without data loss.
3. Force recreation behavior.
4. Validation reporting on missing or corrupted databases.
5. Accurate cricket bowling overs and economy rate calculations (no decimal math trap).
6. Prevention of join multiplication / inflated aggregates in v_player_career_totals.
"""

from pathlib import Path
import pytest

from database.connection import DBConnectionManager
from database.init_db import (
    EXPECTED_TABLES,
    EXPECTED_VIEWS,
    init_database,
    validate_database,
)


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Return a path to an isolated temporary database file."""
    return tmp_path / "temp_init_test.db"


def test_fresh_initialization(temp_db_path: Path) -> None:
    """Verify that init_database creates a fresh, fully valid database on a new path."""
    assert not temp_db_path.exists(), "Target database should not exist before fresh init"

    result = init_database(db_path=temp_db_path, force_recreate=False)

    assert result.action == "FRESH_INITIALIZATION"
    assert temp_db_path.exists()
    assert result.validation_report.is_valid
    assert result.validation_report.integrity_ok
    assert result.validation_report.foreign_keys_enabled
    assert len(result.validation_report.missing_tables) == 0
    assert len(result.validation_report.missing_views) == 0


def test_repeated_initialization_preserves_existing_data(temp_db_path: Path) -> None:
    """Verify that re-running init_database on an existing database preserves data (no silent wipe)."""
    # 1. Initial fresh creation
    init_database(db_path=temp_db_path, force_recreate=False)

    # 2. Insert test data
    mgr = DBConnectionManager(default_db_path=temp_db_path)
    team_id = mgr.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('India', 'IND', 'India');",
        db_path=temp_db_path,
    )
    player_id = mgr.execute_write(
        f"""
        INSERT INTO players (team_id, full_name, country, playing_role, batting_style)
        VALUES ({team_id}, 'Virat Kohli', 'India', 'Batter', 'Right-hand bat');
        """,
        db_path=temp_db_path,
    )

    # 3. Re-run init_database with force_recreate=False
    repeat_result = init_database(db_path=temp_db_path, force_recreate=False)

    assert repeat_result.action == "EXISTING_VALIDATED"
    assert repeat_result.validation_report.is_valid

    # 4. Verify existing records are completely intact
    team_count = mgr.execute_one("SELECT COUNT(*) AS c FROM teams;", db_path=temp_db_path)["c"]
    player_count = mgr.execute_one("SELECT COUNT(*) AS c FROM players;", db_path=temp_db_path)["c"]
    assert team_count == 1, "Existing team data was wiped during repeated init!"
    assert player_count == 1, "Existing player data was wiped during repeated init!"


def test_force_recreate_resets_database(temp_db_path: Path) -> None:
    """Verify that force_recreate=True cleanly deletes and rebuilds the database."""
    init_database(db_path=temp_db_path, force_recreate=False)
    mgr = DBConnectionManager(default_db_path=temp_db_path)
    mgr.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('Australia', 'AUS', 'Australia');",
        db_path=temp_db_path,
    )
    assert mgr.execute_one("SELECT COUNT(*) AS c FROM teams;", db_path=temp_db_path)["c"] == 1

    # Force recreate
    recreate_result = init_database(db_path=temp_db_path, force_recreate=True)
    assert recreate_result.action == "FORCE_RECREATED"
    assert recreate_result.validation_report.is_valid

    # Verify data was cleared
    count = mgr.execute_one("SELECT COUNT(*) AS c FROM teams;", db_path=temp_db_path)["c"]
    assert count == 0, "Database was not reset by force_recreate!"


def test_validation_reports_missing_file(tmp_path: Path) -> None:
    """Verify validate_database detects when a database file is missing."""
    missing_path = tmp_path / "non_existent.db"
    report = validate_database(db_path=missing_path)

    assert not report.file_exists
    assert not report.is_valid
    assert len(report.missing_tables) == len(EXPECTED_TABLES)
    assert len(report.missing_views) == len(EXPECTED_VIEWS)
    assert "Database file does not exist." in report.errors


def test_validation_reports_incomplete_schema(temp_db_path: Path) -> None:
    """Verify validate_database detects missing tables if database is partially constructed."""
    mgr = DBConnectionManager(default_db_path=temp_db_path)
    # Create only the teams table
    mgr.execute_script(
        "CREATE TABLE teams (team_id INTEGER PRIMARY KEY, team_name TEXT, short_name TEXT, country TEXT);",
        db_path=temp_db_path,
    )

    report = validate_database(db_path=temp_db_path)
    assert report.file_exists
    assert not report.is_valid
    assert "players" in report.missing_tables
    assert "matches" in report.missing_tables


def test_cricket_bowling_overs_calculation_not_decimal(temp_db_path: Path) -> None:
    """Verify that cricket overs are treated as 6 balls/over, NOT decimal math.

    Scenario:
    Innings 1: Bowler bowls 22 balls (3.4 overs in cricket), concedes 22 runs.
    Innings 2: Bowler bowls 16 balls (2.4 overs in cricket), concedes 16 runs.

    Decimal addition would yield: 3.4 + 2.4 = 5.8 (WRONG!)
    Cricket addition yields: 22 + 16 = 38 balls = 6 overs + 2 balls = 6.2 overs (CORRECT!)
    Economy rate: (38 runs * 6.0) / 38 balls = 6.00 runs/over (CORRECT!)
    """
    init_database(db_path=temp_db_path)
    mgr = DBConnectionManager(default_db_path=temp_db_path)

    # Setup base entities
    t1 = mgr.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('India', 'IND', 'India');",
        db_path=temp_db_path,
    )
    t2 = mgr.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('Australia', 'AUS', 'Australia');",
        db_path=temp_db_path,
    )
    ven = mgr.execute_write(
        "INSERT INTO venues (venue_name, city, country) VALUES ('Wankhede', 'Mumbai', 'India');",
        db_path=temp_db_path,
    )
    p = mgr.execute_write(
        f"INSERT INTO players (team_id, full_name, country, playing_role, batting_style, bowling_style) "
        f"VALUES ({t1}, 'Jasprit Bumrah', 'India', 'Bowler', 'Right-hand bat', 'Right-arm fast');",
        db_path=temp_db_path,
    )
    m = mgr.execute_write(
        f"INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id) "
        f"VALUES ('IND vs AUS 1st T20I', 'T20I', '2024-04-01', {t1}, {t2}, {ven});",
        db_path=temp_db_path,
    )

    # Innings 1: 3.4 overs = 22 balls, 22 runs, 2 wickets
    inn1 = mgr.execute_write(
        f"INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES ({m}, 1, {t2}, {t1});",
        db_path=temp_db_path,
    )
    mgr.execute_write(
        f"INSERT INTO bowling_performances (innings_id, player_id, overs_bowled, balls_bowled, runs_conceded, wickets_taken) "
        f"VALUES ({inn1}, {p}, 3.4, 22, 22, 2);",
        db_path=temp_db_path,
    )

    # Innings 2: 2.4 overs = 16 balls, 16 runs, 1 wicket
    m2 = mgr.execute_write(
        f"INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id) "
        f"VALUES ('IND vs AUS 2nd T20I', 'T20I', '2024-04-03', {t1}, {t2}, {ven});",
        db_path=temp_db_path,
    )
    inn2 = mgr.execute_write(
        f"INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES ({m2}, 1, {t2}, {t1});",
        db_path=temp_db_path,
    )
    mgr.execute_write(
        f"INSERT INTO bowling_performances (innings_id, player_id, overs_bowled, balls_bowled, runs_conceded, wickets_taken) "
        f"VALUES ({inn2}, {p}, 2.4, 16, 16, 1);",
        db_path=temp_db_path,
    )

    # Query v_player_bowling_by_format
    row = mgr.execute_one(
        f"SELECT * FROM v_player_bowling_by_format WHERE player_id = {p};",
        db_path=temp_db_path,
    )
    assert row is not None
    assert row["total_balls_bowled"] == 38
    # Assert overs string is 6.2 (6 overs + 2 balls), NOT 5.8!
    assert row["total_overs"] == "6.2", f"Expected '6.2' cricket overs, got {row['total_overs']}"
    # Assert true economy rate: (38 runs * 6.0) / 38 balls = 6.00
    assert row["economy_rate"] == 6.0, f"Expected economy 6.0, got {row['economy_rate']}"


def test_career_totals_view_no_join_multiplication(temp_db_path: Path) -> None:
    """Verify that v_player_career_totals does NOT suffer from Cartesian join multiplication.

    Scenario:
    Player bats in 3 innings: scores 50, 40, 30 runs = 120 runs.
    Player bowls in 2 innings: takes 2 and 3 wickets = 5 wickets.

    If joined improperly without pre-aggregation, 3 batting rows x 2 bowling rows = 6 rows,
    which would falsely inflate runs to 240 and wickets to 15!
    """
    init_database(db_path=temp_db_path)
    mgr = DBConnectionManager(default_db_path=temp_db_path)

    # Setup base entities
    t1 = mgr.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('India', 'IND', 'India');",
        db_path=temp_db_path,
    )
    t2 = mgr.execute_write(
        "INSERT INTO teams (team_name, short_name, country) VALUES ('England', 'ENG', 'England');",
        db_path=temp_db_path,
    )
    ven = mgr.execute_write(
        "INSERT INTO venues (venue_name, city, country) VALUES ('Lord''s', 'London', 'England');",
        db_path=temp_db_path,
    )
    p = mgr.execute_write(
        f"INSERT INTO players (team_id, full_name, country, playing_role, batting_style, bowling_style) "
        f"VALUES ({t1}, 'Hardik Pandya', 'India', 'All-rounder', 'Right-hand bat', 'Right-arm medium');",
        db_path=temp_db_path,
    )

    # Create 3 matches with innings
    for match_num, (runs, balls) in enumerate([(50, 40), (40, 30), (30, 20)], start=1):
        m = mgr.execute_write(
            f"INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id) "
            f"VALUES ('Match {match_num}', 'ODI', '2024-06-0{match_num}', {t1}, {t2}, {ven});",
            db_path=temp_db_path,
        )
        inn_bat = mgr.execute_write(
            f"INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES ({m}, 1, {t1}, {t2});",
            db_path=temp_db_path,
        )
        mgr.execute_write(
            f"INSERT INTO batting_performances (innings_id, player_id, batting_position, runs_scored, balls_faced) "
            f"VALUES ({inn_bat}, {p}, 6, {runs}, {balls});",
            db_path=temp_db_path,
        )

        # Bowl in only matches 1 and 2
        if match_num in (1, 2):
            inn_bowl = mgr.execute_write(
                f"INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES ({m}, 2, {t2}, {t1});",
                db_path=temp_db_path,
            )
            wickets = 2 if match_num == 1 else 3
            mgr.execute_write(
                f"INSERT INTO bowling_performances (innings_id, player_id, overs_bowled, balls_bowled, runs_conceded, wickets_taken) "
                f"VALUES ({inn_bowl}, {p}, 4.0, 24, 25, {wickets});",
                db_path=temp_db_path,
            )

    # Query v_player_career_totals
    row = mgr.execute_one(
        f"SELECT * FROM v_player_career_totals WHERE player_id = {p};",
        db_path=temp_db_path,
    )
    assert row is not None
    # Career runs must be exactly 120 (50 + 40 + 30), NOT inflated!
    assert row["career_runs"] == 120, f"Expected career runs 120, got {row['career_runs']}"
    assert row["career_innings_batted"] == 3, f"Expected 3 batting innings, got {row['career_innings_batted']}"

    # Career wickets must be exactly 5 (2 + 3), NOT inflated!
    assert row["career_wickets"] == 5, f"Expected career wickets 5, got {row['career_wickets']}"
