"""Unit and integration test suite for Analytics QueryRunner and Q01.

Validates query catalog integrity, safe SQL execution, DataFrame conversions,
execution plan analysis, and Q01 results against isolated temporary databases.
"""

from pathlib import Path
import pytest

from analytics.query_runner import (
    QUERY_CATALOG,
    QueryExecutionError,
    QueryNotFoundError,
    QueryNotImplementedError,
    QueryRunner,
)
from data.seed_data import seed_database
from database.init_db import init_database


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Fixture providing a fresh, seeded SQLite database in a temporary directory."""
    db_file = tmp_path / "test_analytics.db"
    init_database(db_file, force_recreate=True)
    seed_database(db_file)
    return db_file


@pytest.fixture
def runner() -> QueryRunner:
    """Fixture providing a QueryRunner instance."""
    return QueryRunner()


# ==============================================================================
# 1. CATALOG AND METADATA TESTS
# ==============================================================================

class TestQueryCatalog:
    """Tests for query catalog structure and integrity."""

    def test_catalog_contains_all_25_questions(self, runner: QueryRunner) -> None:
        """Verify catalog contains exactly 25 numbered analytical queries."""
        catalog = runner.get_catalog()
        assert len(catalog) == 25
        assert all(f"q{i:02d}" in QUERY_CATALOG for i in range(1, 26))

    def test_catalog_level_filtering(self, runner: QueryRunner) -> None:
        """Verify queries can be filtered by difficulty level."""
        beginner = runner.get_catalog(level="Beginner")
        intermediate = runner.get_catalog(level="Intermediate")
        advanced = runner.get_catalog(level="Advanced")

        assert len(beginner) == 8      # Q1-Q8
        assert len(intermediate) == 8  # Q9-Q16
        assert len(advanced) == 9      # Q17-Q25
        assert len(beginner) + len(intermediate) + len(advanced) == 25

    def test_all_25_queries_implemented(self, runner: QueryRunner) -> None:
        """Verify all 25 analytical queries are now registered and marked implemented."""
        for i in range(1, 26):
            meta = runner.get_query_metadata(f"q{i:02d}")
            assert meta.is_implemented is True

    def test_unknown_query_raises_not_found(self, runner: QueryRunner) -> None:
        """Verify invalid query ID raises QueryNotFoundError."""
        with pytest.raises(QueryNotFoundError) as exc:
            runner.get_query_metadata("q99")
        assert "not recognized" in str(exc.value)

    def test_unimplemented_query_raises_not_implemented(
        self, runner: QueryRunner, test_db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify requesting an unimplemented query raises QueryNotImplementedError."""
        meta = runner.get_query_metadata("q25")
        monkeypatch.setattr(meta, "is_implemented", False)
        with pytest.raises(QueryNotImplementedError) as exc:
            runner.execute_query("q25", db_path=test_db_path)
        assert "not yet implemented" in str(exc.value)

    def test_catalog_metadata_ascii_cleanliness_for_windows_cp1252(self, runner: QueryRunner) -> None:
        """Regression test: Ensure all query titles and descriptions encode cleanly in cp1252/ASCII."""
        for meta in runner.get_catalog():
            try:
                meta.title.encode("ascii")
                meta.description.encode("ascii")
            except UnicodeEncodeError as exc:
                pytest.fail(f"Query {meta.query_id} contains non-ASCII characters that break Windows console cp1252: {exc}")


# ==============================================================================
# 2. QUESTION 1 EXECUTION TESTS
# ==============================================================================

class TestQuestion01:
    """Tests for Query 01: India Players."""

    def test_q01_executes_successfully(
        self, runner: QueryRunner, test_db_path: Path
    ) -> None:
        """Verify Q01 executes cleanly and returns structured QueryResult."""
        result = runner.execute_query("q01", db_path=test_db_path)

        assert result.query_id == "q01"
        assert result.level == "Beginner"
        assert result.row_count > 0
        assert result.execution_time_ms >= 0.0

        expected_columns = ["full_name", "playing_role", "batting_style", "bowling_style"]
        assert result.columns == expected_columns

    def test_q01_returns_correct_india_players(
        self, runner: QueryRunner, test_db_path: Path
    ) -> None:
        """Verify Q01 returns expected players representing India."""
        result = runner.execute_query("q01", db_path=test_db_path)

        # In seed data, 11 Indian players were seeded
        assert result.row_count == 11

        # Verify prominent Indian players are present
        player_names = [r["full_name"] for r in result.rows]
        assert "Virat Kohli" in player_names
        assert "Rohit Sharma" in player_names
        assert "Jasprit Bumrah" in player_names
        assert "Ravindra Jadeja" in player_names
        assert "Rishabh Pant" in player_names

        # Verify alphabetical ordering
        sorted_names = sorted(player_names)
        assert player_names == sorted_names

    def test_q01_dataframe_conversion(
        self, runner: QueryRunner, test_db_path: Path
    ) -> None:
        """Verify QueryResult.to_dataframe() produces a valid Pandas DataFrame."""
        result = runner.execute_query("q01", db_path=test_db_path)
        df = result.to_dataframe()

        assert len(df) == 11
        assert list(df.columns) == ["full_name", "playing_role", "batting_style", "bowling_style"]
        assert df["full_name"].iloc[0] == "Hardik Pandya"  # Alphabetically first in seed

    def test_q01_explain_query_plan(
        self, runner: QueryRunner, test_db_path: Path
    ) -> None:
        """Verify explain query plan returns SQLite index utilization."""
        plan = runner.explain_query_plan("q01", db_path=test_db_path)
        assert len(plan) > 0
        plan_details = " ".join(step.get("detail", "") for step in plan)
        # Should reference players table and index
        assert "players" in plan_details.lower()


# ==============================================================================
# 3. QUESTION 2 EXECUTION TESTS
# ==============================================================================

class TestQuestion02:
    """Tests for Query 02: Matches in the Last 30 Days."""

    def test_q02_executes_successfully(
        self, runner: QueryRunner, test_db_path: Path
    ) -> None:
        """Verify Q02 executes cleanly and returns structured QueryResult."""
        result = runner.execute_query("q02", db_path=test_db_path)

        assert result.query_id == "q02"
        assert result.level == "Beginner"
        assert result.execution_time_ms >= 0.0

        expected_columns = ["match_desc", "team1_name", "team2_name", "venue_city", "match_date"]
        assert result.columns == expected_columns

    def test_q02_date_boundary_filtering(
        self, runner: QueryRunner, tmp_path: Path
    ) -> None:
        """Verify date handling and boundary cases (today, exactly 30 days ago, 31 days ago, future)."""
        from database.connection import DBConnectionManager

        db_file = tmp_path / "test_q02_boundaries.db"
        init_database(db_file, force_recreate=True)
        seed_database(db_file)

        manager = DBConnectionManager(db_file)

        # Insert controlled boundary test fixtures:
        # Match A: Today (must be included)
        # Match B: Exactly 10 days ago (must be included)
        # Match C: Exactly 30 days ago (must be included by >= boundary)
        # Match D: Exactly 31 days ago (must be excluded)
        # Match E: Future match in 5 days (must be excluded by <= DATE('now'))
        boundary_matches = [
            ("Today Match", "DATE('now')"),
            ("Ten Days Ago Match", "DATE('now', '-10 days')"),
            ("Thirty Days Ago Match", "DATE('now', '-30 days')"),
            ("Thirty-One Days Ago Match", "DATE('now', '-31 days')"),
            ("Future Upcoming Match", "DATE('now', '+5 days')"),
        ]

        with manager.transaction(db_file) as conn:
            cursor = conn.cursor()
            for desc, date_expr in boundary_matches:
                cursor.execute(
                    f"""
                    INSERT INTO matches (
                        match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status
                    ) VALUES (
                        '{desc}', 'T20I', {date_expr}, 1, 2, 1, 'Completed'
                    );
                    """
                )

        result = runner.execute_query("q02", db_path=db_file)
        returned_descs = [r["match_desc"] for r in result.rows]

        # Verify in-bounds matches are present
        assert "Today Match" in returned_descs
        assert "Ten Days Ago Match" in returned_descs
        assert "Thirty Days Ago Match" in returned_descs

        # Verify boundary exclusions
        assert "Thirty-One Days Ago Match" not in returned_descs
        assert "Future Upcoming Match" not in returned_descs

        # Verify descending chronological sort
        dates = [r["match_date"] for r in result.rows]
        assert dates == sorted(dates, reverse=True)

    def test_q02_explain_query_plan(
        self, runner: QueryRunner, test_db_path: Path
    ) -> None:
        """Verify explain query plan uses idx_matches_date index for range scan."""
        plan = runner.explain_query_plan("q02", db_path=test_db_path)
        assert len(plan) > 0
        plan_details = " ".join(step.get("detail", "") for step in plan)
        assert "idx_matches_date" in plan_details

