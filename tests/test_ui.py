"""Automated test suite for Cricbuzz LiveStats Streamlit UI pages and components.

Tests headless rendering of all 6 multi-page application files via Streamlit's AppTest,
validates theme and chart utility functions against undefined labels,
and verifies database reads and filter operations.
"""

from pathlib import Path
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from database.connection import db_manager
from utils.charts import (
    apply_chart_theme,
    create_bar_chart,
    create_donut_chart,
    create_grouped_bar_chart,
    create_horizontal_bar_chart,
    create_line_chart,
    create_scatter_plot,
)
from utils.theme import (
    COLOR_ACCENT_LIME,
    COLOR_BG_MIDNIGHT,
    apply_custom_theme,
    render_badge,
    render_header,
    render_kpi_card,
)


# ==============================================================================
# 1. THEME & VISUALIZATION COMPONENT TESTS
# ==============================================================================

class TestUIComponents:
    """Tests for shared theme and charting helpers."""

    def test_render_badge_output(self) -> None:
        """Verify render_badge produces styled HTML snippet with class and content."""
        badge = render_badge("Test Badge", variant="lime")
        assert "cric-badge" in badge
        assert "cric-badge-lime" in badge
        assert "Test Badge" in badge

    def test_chart_creation_utilities_with_titles(self) -> None:
        """Verify Plotly chart helpers generate valid figures with explicit titles."""
        df = pd.DataFrame({
            "category": ["A", "B", "C"],
            "value": [10, 20, 30],
            "metric2": [5, 15, 25],
        })

        fig_bar = create_bar_chart(df, x_col="category", y_col="value", title="Test Bar", x_label="Cat", y_label="Val")
        assert fig_bar is not None
        assert fig_bar.layout.title.text == "<b>Test Bar</b>"
        assert fig_bar.layout.xaxis.title.text == "Cat"
        assert fig_bar.layout.yaxis.title.text == "Val"

        fig_hbar = create_horizontal_bar_chart(df, x_col="value", y_col="category", title="Test HBar")
        assert fig_hbar is not None
        assert fig_hbar.layout.title.text == "<b>Test HBar</b>"

        fig_donut = create_donut_chart(df, names_col="category", values_col="value", title="Test Donut")
        assert fig_donut is not None
        assert fig_donut.layout.title.text == "<b>Test Donut</b>"

        fig_line = create_line_chart(df, x_col="category", y_col="value", title="Test Line")
        assert fig_line is not None

        fig_scatter = create_scatter_plot(df, x_col="value", y_col="metric2", title="Test Scatter")
        assert fig_scatter is not None

        fig_grouped = create_grouped_bar_chart(df, x_col="category", y_cols=["value", "metric2"], labels=["V1", "V2"])
        assert fig_grouped is not None

    def test_chart_creation_with_omitted_or_none_title_never_renders_undefined(self) -> None:
        """Regression test for Bug 3: Verify omitted/None titles emit empty string, never 'undefined'."""
        df = pd.DataFrame({
            "format": ["Test", "ODI", "T20I"],
            "matches": [4, 5, 3],
        })

        # Test Donut Chart without title
        fig_donut = create_donut_chart(df, names_col="format", values_col="matches", title=None)
        title_json = fig_donut.layout.title.to_plotly_json()
        assert title_json.get("text") == ""
        assert "undefined" not in str(title_json)

        # Test Bar Chart without title
        fig_bar = create_bar_chart(df, x_col="format", y_col="matches", title=None)
        bar_title_json = fig_bar.layout.title.to_plotly_json()
        assert bar_title_json.get("text") == ""
        assert "undefined" not in str(bar_title_json)

        # Test empty string title
        fig_empty = create_bar_chart(df, x_col="format", y_col="matches", title="")
        assert fig_empty.layout.title.text == ""

    def test_trace_names_are_sanitized(self) -> None:
        """Ensure no trace has None or 'undefined' as its name."""
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        fig = create_line_chart(df, x_col="x", y_col="y")
        for trace in fig.data:
            assert trace.name != "undefined"
            assert trace.name != "None"


# ==============================================================================
# 2. DATABASE HELPER USAGE & QUERY TESTS
# ==============================================================================

class TestDatabaseHelperQueries:
    """Verify that with db_manager.get_connection() executes and returns populated data."""

    def test_teams_query_returns_data(self) -> None:
        """Verify teams list returns 6 squads."""
        with db_manager.get_connection() as conn:
            rows = conn.cursor().execute("SELECT team_name FROM teams ORDER BY team_name ASC").fetchall()
            teams = [r[0] for r in rows]
            assert len(teams) >= 6
            assert "India" in teams
            assert "Australia" in teams

    def test_matches_query_with_filters(self) -> None:
        """Verify matches query executes with format and team filters."""
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            rows = cur.execute(
                """
                SELECT m.match_id, m.match_format, t1.team_name, t2.team_name
                FROM matches m
                JOIN teams t1 ON m.team1_id = t1.team_id
                JOIN teams t2 ON m.team2_id = t2.team_id
                WHERE m.match_format = ?;
                """,
                ("ODI",),
            ).fetchall()
            assert len(rows) > 0
            for r in rows:
                assert r[1] == "ODI"

    def test_batting_leaderboard_query_returns_populated_records(self) -> None:
        """Verify batting leaderboard query returns populated statistics."""
        with db_manager.get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT p.full_name, SUM(bp.runs_scored) AS total_runs
                FROM batting_performances bp
                JOIN players p ON bp.player_id = p.player_id
                GROUP BY p.player_id
                ORDER BY total_runs DESC;
                """,
                conn,
            )
            assert not df.empty
            assert df.iloc[0]["total_runs"] > 0
            assert "Virat Kohli" in df["full_name"].values

    def test_bowling_leaderboard_query_returns_populated_records(self) -> None:
        """Verify bowling leaderboard query returns populated statistics."""
        with db_manager.get_connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT p.full_name, SUM(bow.wickets_taken) AS total_wickets
                FROM bowling_performances bow
                JOIN players p ON bow.player_id = p.player_id
                GROUP BY p.player_id
                ORDER BY total_wickets DESC;
                """,
                conn,
            )
            assert not df.empty
            assert df.iloc[0]["total_wickets"] > 0
            assert "Kuldeep Yadav" in df["full_name"].values

    def test_player_profile_query_for_known_player(self) -> None:
        """Verify player profile query retrieves details for Virat Kohli."""
        with db_manager.get_connection() as conn:
            cur = conn.cursor()
            p_row = cur.execute("SELECT player_id, full_name, country FROM players WHERE full_name = ?;", ("Virat Kohli",)).fetchone()
            assert p_row is not None
            assert p_row["full_name"] == "Virat Kohli"
            assert p_row["country"] == "India"


# ==============================================================================
# 3. HEADLESS STREAMLIT APPTEST EXECUTION
# ==============================================================================

class TestStreamlitPages:
    """Headless rendering tests verifying all 6 pages execute without exceptions."""

    def test_home_page_renders_cleanly(self) -> None:
        """Verify app.py (Home Dashboard) executes without exceptions."""
        at = AppTest.from_file("app.py")
        at.run(timeout=10)
        assert len(at.exception) == 0

    def test_live_matches_page_renders_cleanly(self) -> None:
        """Verify pages/1_Live_Matches.py executes without exceptions."""
        at = AppTest.from_file("pages/1_Live_Matches.py")
        at.run(timeout=10)
        assert len(at.exception) == 0

    def test_live_matches_filter_interaction(self) -> None:
        """Verify changing format filter on Live Matches page runs cleanly."""
        at = AppTest.from_file("pages/1_Live_Matches.py")
        at.run(timeout=10)
        assert len(at.exception) == 0
        if len(at.selectbox) > 0:
            at.selectbox[0].select("ODI")
            at.run(timeout=10)
            assert len(at.exception) == 0

    def test_top_players_page_renders_cleanly(self) -> None:
        """Verify pages/2_Top_Players.py executes without exceptions."""
        at = AppTest.from_file("pages/2_Top_Players.py")
        at.run(timeout=10)
        assert len(at.exception) == 0

    def test_top_players_filter_interaction(self) -> None:
        """Verify changing format filter on Top Players page runs cleanly."""
        at = AppTest.from_file("pages/2_Top_Players.py")
        at.run(timeout=10)
        assert len(at.exception) == 0
        if len(at.selectbox) > 0:
            at.selectbox[0].select("ODI")
            at.run(timeout=10)
            assert len(at.exception) == 0

    def test_sql_analytics_page_renders_cleanly(self) -> None:
        """Verify pages/3_SQL_Analytics.py executes without exceptions."""
        at = AppTest.from_file("pages/3_SQL_Analytics.py")
        at.run(timeout=10)
        assert len(at.exception) == 0

    def test_crud_operations_page_renders_cleanly(self) -> None:
        """Verify pages/4_CRUD_Operations.py executes without exceptions."""
        at = AppTest.from_file("pages/4_CRUD_Operations.py")
        at.run(timeout=10)
        assert len(at.exception) == 0

    def test_settings_page_renders_cleanly(self) -> None:
        """Verify pages/5_Settings.py executes without exceptions."""
        at = AppTest.from_file("pages/5_Settings.py")
        at.run(timeout=10)
        assert len(at.exception) == 0
