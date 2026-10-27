"""Automated test suite for Stage 4 database seeding and test fixtures.

Verifies:
1. Seeding creates non-zero records across all 10 relational tables.
2. Zero foreign key violations exist after seeding (PRAGMA foreign_key_check is empty).
3. Seeding is strictly idempotent: executing twice produces identical counts with zero duplicates.
4. Analytical scenarios for the 25 SQL queries are supported by the seeded records.
5. Fixtures JSON file exists and adheres to expected structure.
"""

import json
from pathlib import Path
import pytest

from database.connection import DBConnectionManager
from database.init_db import init_database
from data.seed_data import seed_database


@pytest.fixture
def temp_seed_db(tmp_path: Path) -> Path:
    """Initialize an isolated temporary database with schema and views."""
    db_file = tmp_path / "temp_seed_test.db"
    init_database(db_path=db_file)
    return db_file


def test_seeding_populates_all_tables_with_zero_fk_violations(temp_seed_db: Path) -> None:
    """Verify that seed_database populates all 10 tables and has zero foreign key violations."""
    mgr = DBConnectionManager(default_db_path=temp_seed_db)
    counts = seed_database(db_path=temp_seed_db, manager=mgr)

    expected_tables = [
        "teams", "venues", "series", "players", "matches",
        "innings", "batting_performances", "bowling_performances",
        "fielding_performances", "partnerships",
    ]
    for tbl in expected_tables:
        assert tbl in counts, f"Table {tbl} not in seeding summary"
        assert counts[tbl] > 0, f"Table {tbl} was not populated (0 rows)"

    # Strict SQLite check: verify zero foreign key integrity violations
    with mgr.get_connection(temp_seed_db) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        assert len(fk_violations) == 0, f"Foreign key check failed with violations: {fk_violations}"


def test_seeding_is_strictly_idempotent(temp_seed_db: Path) -> None:
    """Verify that running seed_database twice yields identical row counts (no duplicates)."""
    mgr = DBConnectionManager(default_db_path=temp_seed_db)

    # First run
    counts_run_1 = seed_database(db_path=temp_seed_db, manager=mgr)

    # Second run immediately after
    counts_run_2 = seed_database(db_path=temp_seed_db, manager=mgr)

    # Assert exact match across all tables
    assert counts_run_1 == counts_run_2, (
        f"Seeding is not idempotent! Run 1: {counts_run_1}, Run 2: {counts_run_2}"
    )


def test_seeded_data_supports_key_analytics_scenarios(temp_seed_db: Path) -> None:
    """Verify that seeded data supports essential SQL analytics requirements."""
    mgr = DBConnectionManager(default_db_path=temp_seed_db)
    seed_database(db_path=temp_seed_db, manager=mgr)

    # Scenario Q1: India players
    india_players = mgr.execute_query(
        "SELECT full_name, playing_role FROM players WHERE country = 'India';",
        db_path=temp_seed_db,
    )
    assert len(india_players) >= 5, "Insufficient India players for Q1"

    # Scenario Q4: Large venues with capacity > 50,000
    large_venues = mgr.execute_query(
        "SELECT venue_name, capacity FROM venues WHERE capacity > 50000;",
        db_path=temp_seed_db,
    )
    assert len(large_venues) >= 3, "Insufficient large venues for Q4"

    # Scenario Q8: Series started in 2024
    series_2024 = mgr.execute_query(
        "SELECT series_name FROM series WHERE strftime('%Y', start_date) = '2024';",
        db_path=temp_seed_db,
    )
    assert len(series_2024) >= 2, "Insufficient 2024 series for Q8"

    # Scenario Q13 & Q24: Partnerships >= 100 runs
    big_partnerships = mgr.execute_query(
        "SELECT runs_scored FROM partnerships WHERE runs_scored >= 100;",
        db_path=temp_seed_db,
    )
    assert len(big_partnerships) >= 2, "Insufficient 100+ run partnerships for Q13/Q24"

    # Scenario Q15: Close matches (margin < 50 runs OR < 5 wickets)
    close_matches = mgr.execute_query(
        """
        SELECT match_desc, win_margin, win_type FROM matches
        WHERE (win_type = 'runs' AND win_margin < 50)
           OR (win_type = 'wickets' AND win_margin < 5);
        """,
        db_path=temp_seed_db,
    )
    assert len(close_matches) >= 3, "Insufficient close matches for Q15"

    # Scenario: Views return valid records
    match_details = mgr.execute_query("SELECT * FROM v_match_details;", db_path=temp_seed_db)
    assert len(match_details) > 0, "v_match_details view returned 0 rows"

    batting_stats = mgr.execute_query("SELECT * FROM v_player_batting_by_format;", db_path=temp_seed_db)
    assert len(batting_stats) > 0, "v_player_batting_by_format returned 0 rows"


def test_fixtures_json_structure() -> None:
    """Verify that sample_matches.json exists, is valid JSON, and has required metadata."""
    fixture_path = Path(__file__).resolve().parent.parent / "data" / "fixtures" / "sample_matches.json"
    assert fixture_path.exists(), "sample_matches.json fixture file missing!"

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "_meta" in data
    assert "[SYNTHETIC TEST FIXTURE]" in data["_meta"]["disclaimer"]
    assert "matches" in data
    assert len(data["matches"]) >= 5

    # Check match structure
    first_match = data["matches"][0]
    assert "match_desc" in first_match
    assert "match_format" in first_match
    assert "venue" in first_match
    assert "team1" in first_match
    assert "team2" in first_match
    assert "result" in first_match
    assert "innings" in first_match
