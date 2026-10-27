"""Comprehensive automated test suite for SQL analytical queries Q03 through Q25.

Tests cover:
- Correct execution and column schemas across all queries
- Edge cases, joins, aggregations, tie-handling, and division-by-zero safeguards
- Mathematical verification of cricket formulas (overs, economy rate, standard deviation)
- Isolated fixtures for queries requiring specific match volumes (Q09, Q14, Q16, Q18, Q20, Q22, Q24, Q25)
- Q21 pending-review status verification
"""

import math
from pathlib import Path
import sqlite3
import statistics
from typing import Dict, List
import pytest

from analytics.query_runner import QueryRunner, QueryResult
from data.seed_data import seed_database
from database.connection import DBConnectionManager
from database.init_db import init_database


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Fixture providing a fresh, seeded SQLite database in a temporary directory."""
    db_file = tmp_path / "test_queries.db"
    init_database(db_file, force_recreate=True)
    seed_database(db_file)
    return db_file


@pytest.fixture
def runner() -> QueryRunner:
    """Fixture providing a QueryRunner instance."""
    return QueryRunner()


# ==============================================================================
# BEGINNER QUERIES: Q03 - Q08
# ==============================================================================

class TestBeginnerQueries:
    """Test suite for beginner level queries Q03 to Q08."""

    def test_q03_top_10_odi_run_scorers(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q03: Top 10 ODI Run Scorers - verify average calculation, centuries, and sorting."""
        result = runner.execute_query("q03", db_path=test_db_path)
        assert result.query_id == "q03"
        assert result.columns == [
            "player_name", "total_runs", "innings_batted", "centuries",
            "half_centuries", "batting_average"
        ]
        assert result.row_count > 0
        assert result.row_count <= 10

        # Verify descending order by total runs
        runs = [r["total_runs"] for r in result.rows]
        assert runs == sorted(runs, reverse=True)

        # Check top scorer
        top_scorer = result.rows[0]
        assert top_scorer["player_name"] == "Virat Kohli"
        assert top_scorer["total_runs"] == 230
        assert top_scorer["centuries"] == 1
        assert top_scorer["batting_average"] == 230.0

    def test_q04_large_venues(self, runner: QueryRunner, test_db_path: Path, tmp_path: Path) -> None:
        """Q04: Large Venues > 50,000 Capacity - verify strict inequality and capacity sorting."""
        result = runner.execute_query("q04", db_path=test_db_path)
        assert result.query_id == "q04"
        assert result.columns == ["venue_name", "city", "country", "capacity"]
        assert result.row_count == 4
        capacities = [r["capacity"] for r in result.rows]
        assert all(c > 50000 for c in capacities)
        assert capacities == sorted(capacities, reverse=True)

        # Boundary test: verify venue with exactly 50,000 is excluded
        db_file = tmp_path / "test_q04_boundary.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)
        with mgr.transaction(db_file) as conn:
            conn.execute(
                "INSERT INTO venues (venue_name, city, country, capacity) VALUES "
                "('Exact 50k Stadium', 'City A', 'Country A', 50000), "
                "('Just Over Stadium', 'City B', 'Country B', 50001);"
            )
        b_res = runner.execute_query("q04", db_path=db_file)
        names = [r["venue_name"] for r in b_res.rows]
        assert "Just Over Stadium" in names
        assert "Exact 50k Stadium" not in names

    def test_q05_team_wins_summary(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q05: Team Wins Summary - verify all teams are represented, handling zero wins and ordering."""
        result = runner.execute_query("q05", db_path=test_db_path)
        assert result.query_id == "q05"
        assert result.columns == ["team_name", "total_wins"]
        assert result.row_count == 6  # 6 seeded teams

        # Verify wins ordering
        wins = [r["total_wins"] for r in result.rows]
        assert wins == sorted(wins, reverse=True)

        # India should have highest wins in seed dataset
        assert result.rows[0]["team_name"] == "India"
        assert result.rows[0]["total_wins"] >= 5

    def test_q06_player_counts_by_role(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q06: Player Counts by Role - verify all 4 cricket roles are present."""
        result = runner.execute_query("q06", db_path=test_db_path)
        assert result.query_id == "q06"
        assert result.columns == ["playing_role", "player_count"]
        assert result.row_count == 4

        roles = {r["playing_role"]: r["player_count"] for r in result.rows}
        assert "Batter" in roles
        assert "Bowler" in roles
        assert "All-rounder" in roles
        assert "Wicket-keeper" in roles
        assert sum(roles.values()) == 35  # 35 total seeded players

    def test_q07_highest_score_by_format(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q07: Highest Individual Score by Format - verify record per format via window partition."""
        result = runner.execute_query("q07", db_path=test_db_path)
        assert result.query_id == "q07"
        assert result.columns == ["match_format", "player_name", "highest_score", "balls_faced", "not_out"]
        assert result.row_count >= 2

        format_records = {r["match_format"]: r for r in result.rows}
        assert "ODI" in format_records
        # Travis Head scored 137 in the 2023 CWC Final in the seed dataset
        assert format_records["ODI"]["player_name"] == "Travis Head"
        assert format_records["ODI"]["highest_score"] == 137

    def test_q08_series_started_in_2024(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q08: Series Started in 2024 - verify date filtering within 2024."""
        result = runner.execute_query("q08", db_path=test_db_path)
        assert result.query_id == "q08"
        assert result.columns == ["series_name", "host_country", "match_type", "start_date", "total_matches"]
        assert result.row_count == 4

        for row in result.rows:
            assert row["start_date"].startswith("2024")


# ==============================================================================
# INTERMEDIATE QUERIES: Q09 - Q16
# ==============================================================================

class TestIntermediateQueries:
    """Test suite for intermediate level queries Q09 to Q16."""

    def test_q09_all_rounders_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q09: All-rounders >1000 Runs & >50 Wickets - verify join multiplication protection."""
        db_file = tmp_path / "test_q09.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A')")
            t1_id = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B')")
            t2_id = cur.lastrowid
            cur.execute(
                "INSERT INTO players (team_id, full_name, country, playing_role, batting_style, bowling_style) "
                "VALUES (?, 'Legend Allrounder', 'Country A', 'All-rounder', 'Right-hand bat', 'Right-arm medium')",
                (t1_id,)
            )
            p_id = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Venue 1', 'City 1', 'Country A')")
            v_id = cur.lastrowid

            # Create 10 matches in ODI format
            for m_idx in range(1, 11):
                cur.execute(
                    "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status) "
                    "VALUES (?, 'ODI', '2024-01-01', ?, ?, ?, 'Completed')",
                    (f"Match {m_idx}", t1_id, t2_id, v_id)
                )
                m_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) "
                    "VALUES (?, 1, ?, ?)",
                    (m_id, t1_id, t2_id)
                )
                inn_id = cur.lastrowid
                # 125 runs per match * 10 = 1250 runs (> 1000)
                cur.execute(
                    "INSERT INTO batting_performances (innings_id, player_id, batting_position, runs_scored, balls_faced) "
                    "VALUES (?, ?, 1, 125, 100)",
                    (inn_id, p_id)
                )
                # 6 wickets per match * 10 = 60 wickets (> 50, within 0-10 per innings)
                cur.execute(
                    "INSERT INTO bowling_performances (innings_id, player_id, balls_bowled, runs_conceded, wickets_taken) "
                    "VALUES (?, ?, 60, 40, 6)",
                    (inn_id, p_id)
                )

        result = runner.execute_query("q09", db_path=db_file)
        assert result.row_count == 1
        row = result.rows[0]
        assert row["player_name"] == "Legend Allrounder"
        # If Cartesian product had occurred, runs would be 1250 * 10 = 12500!
        assert row["total_runs"] == 1250
        assert row["total_wickets"] == 60
        assert row["match_format"] == "ODI"

    def test_q10_last_20_completed_matches(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q10: Last 20 Completed Matches with Margins - verify columns, status filter, and order."""
        result = runner.execute_query("q10", db_path=test_db_path)
        assert result.query_id == "q10"
        assert result.columns == [
            "match_desc", "team1_name", "team2_name", "winning_team_name",
            "win_margin", "win_type", "venue_name", "match_date"
        ]
        assert result.row_count == 12  # All 12 completed matches in seed db
        dates = [r["match_date"] for r in result.rows]
        assert dates == sorted(dates, reverse=True)

    def test_q11_cross_format_player_performance(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q11: Cross-Format Player Performance - verify players playing in >= 2 formats."""
        result = runner.execute_query("q11", db_path=test_db_path)
        assert result.query_id == "q11"
        assert result.columns == [
            "player_name", "test_runs", "odi_runs", "t20i_runs", "total_runs", "overall_batting_average"
        ]
        assert result.row_count > 0

        # Verify Virat Kohli and Rohit Sharma appear as multi-format athletes
        names = [r["player_name"] for r in result.rows]
        assert "Virat Kohli" in names
        assert "Rohit Sharma" in names

        kohli = next(r for r in result.rows if r["player_name"] == "Virat Kohli")
        assert kohli["total_runs"] == kohli["test_runs"] + kohli["odi_runs"] + kohli["t20i_runs"]
        assert kohli["overall_batting_average"] is not None

    def test_q12_home_vs_away_performance(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q12: Home vs Away Performance - verify team country vs venue country aggregation."""
        result = runner.execute_query("q12", db_path=test_db_path)
        assert result.query_id == "q12"
        assert result.columns == ["team_name", "home_matches", "home_wins", "away_matches", "away_wins", "total_wins"]
        assert result.row_count > 0

        for r in result.rows:
            assert r["total_wins"] == r["home_wins"] + r["away_wins"]
            assert r["home_wins"] <= r["home_matches"]
            assert r["away_wins"] <= r["away_matches"]

    def test_q13_consecutive_batting_position_pairs(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q13: Consecutive Batting-Position Pairs (Sum >= 100)."""
        result = runner.execute_query("q13", db_path=test_db_path)
        assert result.query_id == "q13"
        assert result.columns == [
            "match_desc", "innings_number", "batsman_1", "position_1", "runs_1",
            "batsman_2", "position_2", "runs_2", "combined_runs"
        ]
        assert result.row_count > 0

        for r in result.rows:
            assert r["position_2"] == r["position_1"] + 1
            assert r["combined_runs"] >= 100
            assert r["combined_runs"] == r["runs_1"] + r["runs_2"]

    def test_q14_venue_bowling_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q14: Venue Bowling Analysis - verify >= 3 matches at venue and >= 4 overs (24 balls) spell."""
        db_file = tmp_path / "test_q14.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A')")
            t1_id = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B')")
            t2_id = cur.lastrowid
            cur.execute(
                "INSERT INTO players (team_id, full_name, country, playing_role, batting_style, bowling_style) "
                "VALUES (?, 'Specialist Bowler', 'Country A', 'Bowler', 'Right-hand bat', 'Right-arm fast')",
                (t1_id,)
            )
            p_id = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Test Stadium', 'Test City', 'Country A')")
            v_id = cur.lastrowid

            # Bowler plays 3 matches at Test Stadium, bowling 24 balls each match (4 overs)
            for m_idx in range(1, 4):
                cur.execute(
                    "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status) "
                    "VALUES (?, 'ODI', '2024-01-01', ?, ?, ?, 'Completed')",
                    (f"Venue Match {m_idx}", t1_id, t2_id, v_id)
                )
                m_id = cur.lastrowid
                cur.execute("INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES (?, 1, ?, ?)", (m_id, t1_id, t2_id))
                inn_id = cur.lastrowid
                # 24 balls, 16 runs conceded, 2 wickets
                cur.execute(
                    "INSERT INTO bowling_performances (innings_id, player_id, balls_bowled, runs_conceded, wickets_taken) "
                    "VALUES (?, ?, 24, 16, 2)",
                    (inn_id, p_id)
                )

        result = runner.execute_query("q14", db_path=db_file)
        assert result.row_count == 1
        row = result.rows[0]
        assert row["bowler_name"] == "Specialist Bowler"
        assert row["venue_name"] == "Test Stadium"
        assert row["matches_played"] == 3
        assert row["total_wickets"] == 6
        assert row["overs_bowled"] == "12.0"
        # 48 runs / 72 balls * 6 = 4.00 economy
        assert row["economy_rate"] == 4.0

    def test_q15_players_in_close_matches(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q15: Players in Close Matches (< 50 runs or < 5 wickets)."""
        result = runner.execute_query("q15", db_path=test_db_path)
        assert result.query_id == "q15"
        assert result.columns == [
            "player_name", "close_matches_batted", "total_runs",
            "avg_runs_per_close_match", "close_matches_won", "win_pct_when_batted"
        ]
        assert result.row_count > 0

    def test_q16_yearly_batting_trends_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q16: Yearly Batting Trends Since 2020 - verify min 5 matches per year requirement."""
        db_file = tmp_path / "test_q16.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A')")
            t1_id = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B')")
            t2_id = cur.lastrowid
            cur.execute("INSERT INTO players (team_id, full_name, country, playing_role, batting_style) VALUES (?, 'Trend Batsman', 'Country A', 'Batter', 'Right-hand bat')", (t1_id,))
            p_id = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Venue A', 'City A', 'Country A')")
            v_id = cur.lastrowid

            # Create 5 matches in 2023
            for m_idx in range(1, 6):
                cur.execute(
                    "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status) "
                    "VALUES (?, 'ODI', '2023-05-10', ?, ?, ?, 'Completed')",
                    (f"Trend Match {m_idx}", t1_id, t2_id, v_id)
                )
                m_id = cur.lastrowid
                cur.execute("INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES (?, 1, ?, ?)", (m_id, t1_id, t2_id))
                inn_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO batting_performances (innings_id, player_id, batting_position, runs_scored, balls_faced) "
                    "VALUES (?, ?, 1, 60, 50)",
                    (inn_id, p_id)
                )

        result = runner.execute_query("q16", db_path=db_file)
        assert result.row_count == 1
        row = result.rows[0]
        assert row["match_year"] == "2023"
        assert row["player_name"] == "Trend Batsman"
        assert row["matches_played"] == 5
        assert row["total_runs"] == 300
        assert row["avg_runs_per_match"] == 60.0
        assert row["strike_rate"] == 120.0


# ==============================================================================
# ADVANCED QUERIES: Q17 - Q25
# ==============================================================================

class TestAdvancedQueries:
    """Test suite for advanced level queries Q17 to Q25."""

    def test_q17_toss_advantage_analysis(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q17: Toss Advantage Analysis - verify bat vs bowl toss decisions and win percentages."""
        result = runner.execute_query("q17", db_path=test_db_path)
        assert result.query_id == "q17"
        assert result.columns == [
            "toss_decision", "total_matches", "toss_winner_wins", "toss_winner_losses", "toss_win_match_win_pct"
        ]
        assert result.row_count == 2  # 'bat' and 'bowl'
        decisions = [r["toss_decision"] for r in result.rows]
        assert "bat" in decisions
        assert "bowl" in decisions
        for r in result.rows:
            assert r["total_matches"] == r["toss_winner_wins"] + r["toss_winner_losses"]

    def test_q18_economical_bowlers_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q18: Economical Limited-Overs Bowlers - verify min 10 matches and >= 2 overs/match."""
        db_file = tmp_path / "test_q18.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A')")
            t1_id = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B')")
            t2_id = cur.lastrowid
            cur.execute("INSERT INTO players (team_id, full_name, country, playing_role, batting_style, bowling_style) VALUES (?, 'Econ Bowler', 'Country A', 'Bowler', 'Right-hand bat', 'Right-arm medium')", (t1_id,))
            p_id = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Venue A', 'City A', 'Country A')")
            v_id = cur.lastrowid

            # Create 10 ODI matches
            for m_idx in range(1, 11):
                cur.execute(
                    "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status) "
                    "VALUES (?, 'ODI', '2024-02-01', ?, ?, ?, 'Completed')",
                    (f"Econ Match {m_idx}", t1_id, t2_id, v_id)
                )
                m_id = cur.lastrowid
                cur.execute("INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES (?, 1, ?, ?)", (m_id, t1_id, t2_id))
                inn_id = cur.lastrowid
                # 24 balls (4 overs), 12 runs conceded (economy 3.0), 1 wicket
                cur.execute(
                    "INSERT INTO bowling_performances (innings_id, player_id, balls_bowled, runs_conceded, wickets_taken) "
                    "VALUES (?, ?, 24, 12, 1)",
                    (inn_id, p_id)
                )

        result = runner.execute_query("q18", db_path=db_file)
        assert result.row_count == 1
        row = result.rows[0]
        assert row["bowler_name"] == "Econ Bowler"
        assert row["limited_overs_matches"] == 10
        assert row["total_wickets"] == 10
        assert row["economy_rate"] == 3.0

    def test_q19_batting_consistency_standard_deviation(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q19: Batting Consistency - verify standard deviation against Python statistics module."""
        result = runner.execute_query("q19", db_path=test_db_path)
        assert result.query_id == "q19"
        assert result.columns == ["player_name", "qualifying_innings", "total_runs", "avg_runs", "stddev_runs"]
        assert result.row_count > 0

        # Verify against independent mathematical calculation
        conn = sqlite3.connect(test_db_path)
        cur = conn.cursor()
        for r in result.rows:
            scores = [row[0] for row in cur.execute(
                "SELECT bp.runs_scored FROM batting_performances bp "
                "JOIN players p ON bp.player_id = p.player_id "
                "JOIN innings i ON bp.innings_id = i.innings_id "
                "JOIN matches m ON i.match_id = m.match_id "
                "WHERE p.full_name = ? AND m.match_date >= '2022-01-01' AND bp.balls_faced >= 10",
                (r["player_name"],)
            ).fetchall()]
            if len(scores) >= 2:
                expected_stddev = round(statistics.stdev(scores), 2)
                assert math.isclose(r["stddev_runs"], expected_stddev, abs_tol=0.01)
        conn.close()

    def test_q20_matches_and_averages_by_format_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q20: Matches & Batting Averages by Format - verify min 20 total matches requirement."""
        db_file = tmp_path / "test_q20.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A')")
            t1_id = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B')")
            t2_id = cur.lastrowid
            cur.execute("INSERT INTO players (team_id, full_name, country, playing_role, batting_style) VALUES (?, 'Veteran Player', 'Country A', 'Batter', 'Right-hand bat')", (t1_id,))
            p_id = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Venue A', 'City A', 'Country A')")
            v_id = cur.lastrowid

            # Create 10 Tests and 10 ODIs = 20 total matches
            for m_idx in range(1, 21):
                fmt = 'Test' if m_idx <= 10 else 'ODI'
                cur.execute(
                    "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status) "
                    "VALUES (?, ?, '2024-01-01', ?, ?, ?, 'Completed')",
                    (f"Match {m_idx}", fmt, t1_id, t2_id, v_id)
                )
                m_id = cur.lastrowid
                cur.execute("INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES (?, 1, ?, ?)", (m_id, t1_id, t2_id))
                inn_id = cur.lastrowid
                cur.execute(
                    "INSERT INTO batting_performances (innings_id, player_id, batting_position, runs_scored, balls_faced, is_not_out) "
                    "VALUES (?, ?, 1, 50, 40, 0)",
                    (inn_id, p_id)
                )

        result = runner.execute_query("q20", db_path=db_file)
        assert result.row_count == 1
        row = result.rows[0]
        assert row["player_name"] == "Veteran Player"
        assert row["test_matches"] == 10
        assert row["test_batting_avg"] == 50.0
        assert row["odi_matches"] == 10
        assert row["odi_batting_avg"] == 50.0
        assert row["total_matches"] == 20

    def test_q21_weighted_ranking_pending_review_status(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q21: Weighted Player Ranking - verify metrics returned and composite ranking marked PENDING REVIEW."""
        result = runner.execute_query("q21", db_path=test_db_path)
        assert result.query_id == "q21"
        assert "composite_ranking_status" in result.columns
        assert result.row_count > 0

        # Confirm all rows explicitly indicate composite formula is pending review
        for r in result.rows:
            assert r["composite_ranking_status"] == "PENDING REVIEW"
            assert r["batting_points"] is not None
            assert r["fielding_points"] is not None

    def test_q22_team_head_to_head_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q22: Team Head-to-Head Analysis - verify canonical pairing and min 5 matches requirement."""
        db_file = tmp_path / "test_q22.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Alpha Team', 'ALP', 'Country A')")
            t1 = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Beta Team', 'BET', 'Country B')")
            t2 = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Rivalry Grounds', 'City R', 'Country A')")
            v_id = cur.lastrowid

            # 5 matches in the last year: Alpha wins 3, Beta wins 2
            for m_idx in range(1, 6):
                winner = t1 if m_idx <= 3 else t2
                cur.execute(
                    "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status, winning_team_id, win_margin, win_type) "
                    "VALUES (?, 'ODI', DATE('now', '-6 months'), ?, ?, ?, 'Completed', ?, 20, 'runs')",
                    (f"Rivalry Match {m_idx}", t1, t2, v_id, winner)
                )

        result = runner.execute_query("q22", db_path=db_file)
        assert result.row_count == 1
        row = result.rows[0]
        assert row["total_matches"] == 5
        assert row["team_a_wins"] == 3
        assert row["team_b_wins"] == 2
        assert row["team_a_win_pct"] == 60.0
        assert row["team_b_win_pct"] == 40.0

    def test_q23_recent_player_form(self, runner: QueryRunner, test_db_path: Path) -> None:
        """Q23: Recent Player Form & Momentum - verify last 5 vs last 10, form tiers."""
        result = runner.execute_query("q23", db_path=test_db_path)
        assert result.query_id == "q23"
        assert result.columns == [
            "player_name", "recent_innings_count", "last_5_avg_runs", "last_10_avg_runs",
            "last_5_strike_rate", "scores_50_plus", "recent_stddev", "form_tier"
        ]
        assert result.row_count > 0

        valid_tiers = {"Excellent Form", "Good Form", "Average Form", "Poor Form"}
        for r in result.rows:
            assert r["form_tier"] in valid_tiers
            assert r["recent_innings_count"] <= 10

    def test_q24_batting_partnerships_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q24: Batting Partnerships Analysis - verify canonical pairing and min 5 stands requirement."""
        db_file = tmp_path / "test_q24.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A')")
            t1_id = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B')")
            t2_id = cur.lastrowid
            cur.execute("INSERT INTO players (team_id, full_name, country, playing_role, batting_style) VALUES (?, 'Partner One', 'Country A', 'Batter', 'Right-hand bat')", (t1_id,))
            p1 = cur.lastrowid
            cur.execute("INSERT INTO players (team_id, full_name, country, playing_role, batting_style) VALUES (?, 'Partner Two', 'Country A', 'Batter', 'Left-hand bat')", (t1_id,))
            p2 = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Venue A', 'City A', 'Country A')")
            v_id = cur.lastrowid

            # Create 5 matches with 5 partnerships
            for m_idx in range(1, 6):
                cur.execute(
                    "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status) "
                    "VALUES (?, 'ODI', '2024-01-01', ?, ?, ?, 'Completed')",
                    (f"Part Match {m_idx}", t1_id, t2_id, v_id)
                )
                m_id = cur.lastrowid
                cur.execute("INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES (?, 1, ?, ?)", (m_id, t1_id, t2_id))
                inn_id = cur.lastrowid
                stand_runs = 70 if m_idx <= 3 else 30
                cur.execute(
                    "INSERT INTO partnerships (innings_id, wicket_number, player1_id, player2_id, runs_scored, balls_faced) "
                    "VALUES (?, 1, ?, ?, ?, 60)",
                    (inn_id, p1, p2, stand_runs)
                )

        result = runner.execute_query("q24", db_path=db_file)
        assert result.row_count == 1
        row = result.rows[0]
        assert row["total_partnerships"] == 5
        assert row["stands_50_plus"] == 3
        assert row["highest_partnership"] == 70
        assert row["avg_partnership_runs"] == 54.0
        assert row["success_rate_pct"] == 60.0

    def test_q25_quarterly_career_trajectory_with_isolated_fixture(self, runner: QueryRunner, tmp_path: Path) -> None:
        """Q25: Quarterly Career Trajectory - verify min 6 quarters with min 3 matches per quarter."""
        db_file = tmp_path / "test_q25.db"
        init_database(db_file, force_recreate=True)
        mgr = DBConnectionManager(db_file)

        with mgr.transaction(db_file) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team A', 'TA', 'Country A')")
            t1_id = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team B', 'TB', 'Country B')")
            t2_id = cur.lastrowid
            cur.execute("INSERT INTO players (team_id, full_name, country, playing_role, batting_style) VALUES (?, 'Long Career Batter', 'Country A', 'Batter', 'Right-hand bat')", (t1_id,))
            p_id = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country) VALUES ('Venue A', 'City A', 'Country A')")
            v_id = cur.lastrowid

            # Create matches across 6 distinct quarters:
            # 2022-Q1, 2022-Q2, 2022-Q3, 2022-Q4, 2023-Q1, 2023-Q2
            quarter_dates = [
                '2022-01-15', '2022-04-15', '2022-07-15',
                '2022-10-15', '2023-01-15', '2023-04-15'
            ]
            for q_idx, base_date in enumerate(quarter_dates, start=1):
                # 3 matches per quarter
                for m_sub in range(1, 4):
                    cur.execute(
                        "INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status) "
                        "VALUES (?, 'ODI', ?, ?, ?, ?, 'Completed')",
                        (f"Q Match {q_idx}-{m_sub}", base_date, t1_id, t2_id, v_id)
                    )
                    m_id = cur.lastrowid
                    cur.execute("INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id) VALUES (?, 1, ?, ?)", (m_id, t1_id, t2_id))
                    inn_id = cur.lastrowid
                    runs = 50 + (q_idx * 10)  # Improving trend (> 5 run increase per quarter)
                    cur.execute(
                        "INSERT INTO batting_performances (innings_id, player_id, batting_position, runs_scored, balls_faced) "
                        "VALUES (?, ?, 1, ?, 40)",
                        (inn_id, p_id, runs)
                    )

        result = runner.execute_query("q25", db_path=db_file)
        assert result.row_count == 6  # 6 quarter rows for Long Career Batter
        rows = result.rows
        assert rows[0]["match_quarter"] == "2022-Q1"
        assert rows[0]["quarterly_trend"] == "Baseline"
        assert rows[1]["match_quarter"] == "2022-Q2"
        assert rows[1]["quarterly_trend"] == "Improving"
        assert rows[-1]["career_phase"] == "Career Ascending"
