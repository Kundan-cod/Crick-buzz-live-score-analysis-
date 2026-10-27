"""Stage 8 End-to-End Realistic Workflows Validation Suite.

Executes all 6 required realistic operational workflows against an isolated
temporary SQLite database:
1. Open the dashboard and inspect database metrics.
2. Filter matches by format, status, and team.
3. Filter player leaderboards and inspect a player profile.
4. Execute representative beginner, intermediate, and advanced SQL questions.
5. Create a test record, update it, validate an invalid input, and test safe deletion.
6. Check database diagnostics and verify data integrity afterward.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import pytest

from analytics.query_runner import QueryRunner
from data.seed_data import seed_database
from database.connection import DBConnectionManager
from database.init_db import init_database
from services.crud_service import (
    CRUDService,
    DuplicateRecordError,
    ProtectedRecordError,
    ReadOnlyRecordError,
    RecordNotFoundError,
)
from utils.validators import ValidationError


@pytest.fixture
def workflow_db(tmp_path: Path) -> Path:
    """Creates and seeds an isolated SQLite database for workflow testing."""
    db_file = tmp_path / "workflow_test.db"
    init_database(db_file, force_recreate=True)
    seed_database(db_file)
    return db_file


@pytest.fixture
def crud() -> CRUDService:
    """Fixture providing a CRUDService instance."""
    return CRUDService()


class TestRealisticWorkflows:
    """Test suite executing the 6 realistic workflows on an isolated database."""

    def test_workflow_1_inspect_dashboard_metrics(self, workflow_db: Path) -> None:
        """Workflow 1: Open the dashboard and inspect database metrics."""
        mgr = DBConnectionManager(workflow_db)
        with mgr.get_connection(workflow_db) as conn:
            cur = conn.cursor()
            
            # Metric 1: Total matches
            match_count = cur.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
            assert match_count == 12, f"Expected 12 matches, got {match_count}"

            # Metric 2: Total teams
            team_count = cur.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
            assert team_count == 6, f"Expected 6 teams, got {team_count}"

            # Metric 3: Total players
            player_count = cur.execute("SELECT COUNT(*) FROM players").fetchone()[0]
            assert player_count == 35, f"Expected 35 players, got {player_count}"

            # Metric 4: Total venues
            venue_count = cur.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
            assert venue_count == 10, f"Expected 10 venues, got {venue_count}"

            # Format distribution
            format_counts = dict(
                cur.execute(
                    "SELECT match_format, COUNT(*) FROM matches GROUP BY match_format"
                ).fetchall()
            )
            assert "ODI" in format_counts
            assert "T20I" in format_counts
            assert "Test" in format_counts

    def test_workflow_2_filter_matches(self, workflow_db: Path) -> None:
        """Workflow 2: Filter matches by format, status, and team."""
        mgr = DBConnectionManager(workflow_db)
        with mgr.get_connection(workflow_db) as conn:
            # Filter 1: Format = 'ODI'
            odi_matches = pd.read_sql_query(
                """
                SELECT m.match_id, m.match_format, m.match_status, t1.team_name AS team1, t2.team_name AS team2
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.team_id
                JOIN teams t2 ON m.team2_id = t2.team_id
                WHERE m.match_format = 'ODI'
                """,
                conn,
            )
            assert len(odi_matches) == 5
            assert all(odi_matches["match_format"] == "ODI")

            # Filter 2: Status = 'Completed'
            completed_matches = pd.read_sql_query(
                "SELECT match_id, match_status FROM matches WHERE match_status = 'Completed'",
                conn,
            )
            assert len(completed_matches) == 12

            # Filter 3: Team = 'India' (either team1 or team2)
            india_matches = pd.read_sql_query(
                """
                SELECT m.match_id, t1.team_name AS team1, t2.team_name AS team2
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.team_id
                JOIN teams t2 ON m.team2_id = t2.team_id
                WHERE t1.team_name = 'India' OR t2.team_name = 'India'
                """,
                conn,
            )
            assert len(india_matches) > 0
            for _, row in india_matches.iterrows():
                assert row["team1"] == "India" or row["team2"] == "India"

    def test_workflow_3_leaderboards_and_player_profile(self, workflow_db: Path) -> None:
        """Workflow 3: Filter player leaderboards and inspect a player profile."""
        mgr = DBConnectionManager(workflow_db)
        with mgr.get_connection(workflow_db) as conn:
            # Batting leaderboard: top 5 run scorers
            batting_df = pd.read_sql_query(
                """
                SELECT p.player_id, p.full_name, p.country,
                       COUNT(DISTINCT bp.innings_id) AS innings,
                       SUM(bp.runs_scored) AS total_runs,
                       ROUND(CAST(SUM(bp.runs_scored) AS REAL) / 
                             NULLIF(SUM(CASE WHEN bp.dismissal_type NOT IN ('not out', 'retired hurt') THEN 1 ELSE 0 END), 0), 2) AS batting_avg
                FROM batting_performances bp
                JOIN players p ON bp.player_id = p.player_id
                GROUP BY p.player_id
                ORDER BY total_runs DESC
                LIMIT 5;
                """,
                conn,
            )
            assert len(batting_df) == 5
            top_batsman_id = int(batting_df.iloc[0]["player_id"])
            top_batsman_name = batting_df.iloc[0]["full_name"]
            assert top_batsman_name == "Virat Kohli"

            # Inspect profile for top batsman
            profile_cur = conn.cursor()
            profile = profile_cur.execute(
                """
                SELECT p.player_id, p.full_name, p.country, p.playing_role, p.batting_style, p.bowling_style
                FROM players p
                WHERE p.player_id = ?;
                """,
                (top_batsman_id,),
            ).fetchone()
            assert profile is not None
            assert profile["full_name"] == "Virat Kohli"
            assert profile["playing_role"] == "Batter"
            assert profile["country"] == "India"

            # Bowling leaderboard: top wickets
            bowling_df = pd.read_sql_query(
                """
                SELECT p.player_id, p.full_name, SUM(bow.wickets_taken) AS total_wickets
                FROM bowling_performances bow
                JOIN players p ON bow.player_id = p.player_id
                GROUP BY p.player_id
                ORDER BY total_wickets DESC
                LIMIT 5;
                """,
                conn,
            )
            assert len(bowling_df) == 5
            assert bowling_df.iloc[0]["total_wickets"] > 0

    def test_workflow_4_execute_sql_questions(self, workflow_db: Path) -> None:
        """Workflow 4: Execute representative beginner, intermediate, and advanced SQL questions."""
        runner = QueryRunner()

        # Beginner: Q01 (India Players)
        res_q01 = runner.execute_query("q01", db_path=workflow_db)
        assert res_q01.error is None
        assert res_q01.row_count > 0
        names = [r["full_name"] for r in res_q01.rows]
        assert "Virat Kohli" in names

        # Beginner: Q03 (Top 10 ODI Run Scorers)
        res_q03 = runner.execute_query("q03", db_path=workflow_db)
        assert res_q03.error is None
        assert res_q03.row_count > 0
        assert res_q03.rows[0]["player_name"] == "Virat Kohli"

        # Intermediate: Q10 (Last 20 Completed Matches)
        res_q10 = runner.execute_query("q10", db_path=workflow_db)
        assert res_q10.error is None
        assert res_q10.row_count == 12

        # Intermediate: Q12 (Home vs Away Performance)
        res_q12 = runner.execute_query("q12", db_path=workflow_db)
        assert res_q12.error is None
        assert res_q12.row_count > 0

        # Advanced: Q17 (Toss Advantage Analysis)
        res_q17 = runner.execute_query("q17", db_path=workflow_db)
        assert res_q17.error is None
        assert res_q17.row_count > 0

        # Advanced: Q19 (Batting Consistency Standard Deviation)
        res_q19 = runner.execute_query("q19", db_path=workflow_db)
        assert res_q19.error is None
        assert res_q19.row_count > 0

        # Advanced: Q21 (Weighted Player Ranking - verify PENDING REVIEW status is honoured)
        res_q21 = runner.execute_query("q21", db_path=workflow_db)
        assert res_q21.error is None
        meta_q21 = runner.get_query_metadata("q21")
        assert "PENDING REVIEW" in meta_q21.title
        assert "PENDING REVIEW" in meta_q21.description

    def test_workflow_5_crud_lifecycle_validation_and_safe_delete(
        self, crud: CRUDService, workflow_db: Path
    ) -> None:
        """Workflow 5: Create a test record, update it, validate invalid input, and test safe deletion."""
        # 5a. Create a disposable test player
        player_data = {
            "team_id": 1,
            "full_name": "Test Workflow Batter",
            "country": "India",
            "playing_role": "Batter",
            "batting_style": "Right-hand bat",
            "bowling_style": "Right-arm medium",
            "is_active": 1,
            "source": "LOCAL",
        }
        test_player_id = crud.create_player(player_data, db_path=workflow_db)
        assert test_player_id > 0

        # 5b. Update the test record
        crud.update_player(
            test_player_id,
            {"playing_role": "All-rounder"},
            db_path=workflow_db,
        )
        retrieved = crud.get_player_by_id(test_player_id, db_path=workflow_db)
        assert retrieved["playing_role"] == "All-rounder"

        # 5c. Validate an invalid input (should be cleanly rejected by validators)
        with pytest.raises(ValidationError):
            crud.create_player(
                {
                    "team_id": 1,
                    "full_name": "",  # Empty name is invalid
                    "country": "India",
                    "playing_role": "InvalidRole",
                },
                db_path=workflow_db,
            )

        # 5d. Test safe soft-delete of disposable player (toggles is_active to 0)
        soft_success = crud.delete_player(test_player_id, hard_delete=False, db_path=workflow_db)
        assert soft_success is True
        soft_retrieved = crud.get_player_by_id(test_player_id, db_path=workflow_db)
        assert soft_retrieved["is_active"] == 0

        # 5e. Test hard-delete of unreferenced disposable test player
        hard_success = crud.delete_player(test_player_id, hard_delete=True, db_path=workflow_db)
        assert hard_success is True
        assert crud.get_player_by_id(test_player_id, db_path=workflow_db) is None

        # 5f. Test referential integrity: attempting to delete an active player with performances is protected
        kohli_id = 1
        with pytest.raises((ProtectedRecordError, ReadOnlyRecordError)):
            crud.delete_player(kohli_id, hard_delete=True, db_path=workflow_db)

    def test_workflow_6_database_diagnostics_and_integrity_check(self, workflow_db: Path) -> None:
        """Workflow 6: Check database diagnostics and verify data integrity afterward."""
        mgr = DBConnectionManager(workflow_db)
        with mgr.get_connection(workflow_db) as conn:
            cur = conn.cursor()

            # PRAGMA integrity_check
            integrity_row = cur.execute("PRAGMA integrity_check;").fetchone()
            assert integrity_row[0] == "ok", f"Integrity check failed: {integrity_row[0]}"

            # PRAGMA foreign_key_check
            fk_violations = cur.execute("PRAGMA foreign_key_check;").fetchall()
            assert len(fk_violations) == 0, f"Foreign key violations detected: {fk_violations}"

            # PRAGMA foreign_keys is ON
            fk_on = cur.execute("PRAGMA foreign_keys;").fetchone()[0]
            assert fk_on == 1, "Foreign keys are not enabled"
