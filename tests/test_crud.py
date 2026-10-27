"""Unit and integration test suite for CRUD operations and input validators.

Validates Create, Read, Update, Delete methods, domain validation, foreign-key
protections, API source segregation, and transaction safety against temporary databases.
"""

from pathlib import Path
import pytest
import sqlite3

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
from utils.validators import (
    ValidationError,
    validate_match_data,
    validate_player_data,
    validate_venue_data,
)


@pytest.fixture
def test_db_path(tmp_path: Path) -> Path:
    """Fixture providing a fresh, seeded SQLite database in a temporary directory."""
    db_file = tmp_path / "test_crud.db"
    init_database(db_file, force_recreate=True)
    seed_database(db_file)
    return db_file


@pytest.fixture
def empty_db_path(tmp_path: Path) -> Path:
    """Fixture providing an initialized but unseeded SQLite database in a temporary directory."""
    db_file = tmp_path / "test_empty_crud.db"
    init_database(db_file, force_recreate=True)
    return db_file


@pytest.fixture
def crud() -> CRUDService:
    """Fixture providing a CRUDService instance."""
    return CRUDService()


# ==============================================================================
# 1. VALIDATOR UNIT TESTS
# ==============================================================================

class TestValidators:
    """Unit tests for entity input validators."""

    def test_validate_player_valid(self) -> None:
        """Verify valid player payload passes and is normalized."""
        payload = {
            "full_name": "  Sachin Tendulkar  ",
            "country": "India",
            "playing_role": "batter",
            "batting_style": "right-hand bat",
            "bowling_style": "Right-arm offbreak",
            "team_id": 1,
            "is_active": True,
        }
        cleaned = validate_player_data(payload)
        assert cleaned["full_name"] == "Sachin Tendulkar"
        assert cleaned["playing_role"] == "Batter"
        assert cleaned["batting_style"] == "Right-hand bat"
        assert cleaned["bowling_style"] == "Right-arm offbreak"
        assert cleaned["team_id"] == 1
        assert cleaned["is_active"] == 1
        assert cleaned["source"] == "LOCAL"

    def test_validate_player_missing_required_fields(self) -> None:
        """Verify missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validate_player_data({"full_name": "Test Player"})
        assert "country" in str(exc.value)

    def test_validate_player_invalid_role(self) -> None:
        """Verify invalid playing role raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validate_player_data({
                "full_name": "Test Player",
                "country": "India",
                "playing_role": "Cheerleader",
                "batting_style": "Right-hand bat",
            })
        assert "Invalid playing role" in str(exc.value)

    def test_validate_player_invalid_batting_style(self) -> None:
        """Verify invalid batting style raises ValidationError."""
        with pytest.raises(ValidationError) as exc:
            validate_player_data({
                "full_name": "Test Player",
                "country": "India",
                "playing_role": "Batter",
                "batting_style": "Ambidextrous bat",
            })
        assert "Invalid batting style" in str(exc.value)

    def test_validate_venue_valid(self) -> None:
        """Verify valid venue payload passes and is normalized."""
        payload = {
            "venue_name": "  Wanderers Stadium  ",
            "city": "Johannesburg",
            "country": "South Africa",
            "capacity": 34000,
        }
        cleaned = validate_venue_data(payload)
        assert cleaned["venue_name"] == "Wanderers Stadium"
        assert cleaned["city"] == "Johannesburg"
        assert cleaned["capacity"] == 34000

    def test_validate_venue_negative_capacity(self) -> None:
        """Verify negative venue capacity is rejected."""
        with pytest.raises(ValidationError) as exc:
            validate_venue_data({
                "venue_name": "Test Ground",
                "city": "Test City",
                "country": "Test Country",
                "capacity": -500,
            })
        assert "capacity" in str(exc.value)

    def test_validate_match_identical_teams(self) -> None:
        """Verify identical team1 and team2 are rejected."""
        with pytest.raises(ValidationError) as exc:
            validate_match_data({
                "match_desc": "Final",
                "match_format": "ODI",
                "match_date": "2026-10-22",
                "team1_id": 1,
                "team2_id": 1,
                "venue_id": 1,
            })
        assert "identical" in str(exc.value)

    def test_validate_match_invalid_date_format(self) -> None:
        """Verify non-ISO date formats are rejected."""
        with pytest.raises(ValidationError) as exc:
            validate_match_data({
                "match_desc": "1st T20I",
                "match_format": "T20I",
                "match_date": "22-10-2026",
                "team1_id": 1,
                "team2_id": 2,
                "venue_id": 1,
            })
        assert "YYYY-MM-DD" in str(exc.value)

    def test_validate_match_toss_winner_not_participating(self) -> None:
        """Verify toss winner must be one of the playing teams."""
        with pytest.raises(ValidationError) as exc:
            validate_match_data({
                "match_desc": "1st ODI",
                "match_format": "ODI",
                "match_date": "2026-10-22",
                "team1_id": 1,
                "team2_id": 2,
                "venue_id": 1,
                "toss_winner_id": 3,
            })
        assert "Toss winner must be one of the participating teams" in str(exc.value)


# ==============================================================================
# 2. PLAYER CRUD OPERATIONS
# ==============================================================================

class TestPlayerCRUD:
    """Integration tests for Player CRUD operations."""

    def test_create_and_get_player_success(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify creating a valid player and retrieving it."""
        payload = {
            "full_name": "Yuvraj Singh",
            "country": "India",
            "playing_role": "All-rounder",
            "batting_style": "Left-hand bat",
            "bowling_style": "Slow left-arm chinaman",
            "team_id": 1,
        }
        player_id = crud.create_player(payload, db_path=test_db_path)
        assert player_id > 0

        player = crud.get_player_by_id(player_id, db_path=test_db_path)
        assert player is not None
        assert player["full_name"] == "Yuvraj Singh"
        assert player["team_name"] == "India"
        assert player["is_active"] == 1

    def test_create_duplicate_player_fails(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify creating a player with identical full_name and country raises DuplicateRecordError."""
        payload = {
            "full_name": "Virat Kohli",
            "country": "India",
            "playing_role": "Batter",
            "batting_style": "Right-hand bat",
            "team_id": 1,
        }
        with pytest.raises(DuplicateRecordError) as exc:
            crud.create_player(payload, db_path=test_db_path)
        assert "already exists" in str(exc.value)

    def test_update_player_success(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify updating a player's role and batting style."""
        payload = {
            "full_name": "Test Updatable",
            "country": "India",
            "playing_role": "Batter",
            "batting_style": "Right-hand bat",
        }
        pid = crud.create_player(payload, db_path=test_db_path)

        success = crud.update_player(
            pid,
            {"playing_role": "All-rounder", "bowling_style": "Right-arm offbreak"},
            db_path=test_db_path,
        )
        assert success is True

        updated = crud.get_player_by_id(pid, db_path=test_db_path)
        assert updated is not None
        assert updated["playing_role"] == "All-rounder"
        assert updated["bowling_style"] == "Right-arm offbreak"

    def test_update_nonexistent_player_fails(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify updating a nonexistent player raises RecordNotFoundError."""
        with pytest.raises(RecordNotFoundError):
            crud.update_player(99999, {"playing_role": "Bowler"}, db_path=test_db_path)

    def test_soft_delete_and_status_toggle(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify default player deletion is a non-destructive soft-delete (is_active = 0)."""
        payload = {
            "full_name": "Soft Delete Candidate",
            "country": "England",
            "playing_role": "Bowler",
            "batting_style": "Right-hand bat",
        }
        pid = crud.create_player(payload, db_path=test_db_path)

        # Soft delete
        result = crud.delete_player(pid, hard_delete=False, db_path=test_db_path)
        assert result is True

        player = crud.get_player_by_id(pid, db_path=test_db_path)
        assert player is not None
        assert player["is_active"] == 0

        # Toggle back to active
        new_status = crud.toggle_player_status(pid, db_path=test_db_path)
        assert new_status == 1
        player = crud.get_player_by_id(pid, db_path=test_db_path)
        assert player["is_active"] == 1

    def test_hard_delete_unreferenced_player_success(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify unreferenced player can be hard deleted."""
        payload = {
            "full_name": "Temporary Player",
            "country": "Australia",
            "playing_role": "Bowler",
            "batting_style": "Right-hand bat",
        }
        pid = crud.create_player(payload, db_path=test_db_path)

        # Hard delete
        result = crud.delete_player(pid, hard_delete=True, db_path=test_db_path)
        assert result is True

        assert crud.get_player_by_id(pid, db_path=test_db_path) is None

    def test_hard_delete_referenced_player_is_protected(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify player with linked scorecards cannot be hard-deleted."""
        # Player ID 1 (Virat Kohli) has batting performances
        with pytest.raises(ProtectedRecordError) as exc:
            crud.delete_player(1, hard_delete=True, db_path=test_db_path)
        assert "linked match scorecards exist" in str(exc.value)

    def test_api_sourced_player_is_protected(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify records with source = 'API' are protected against deletion and mutation."""
        # Create an API-sourced player
        pid = crud.create_player({
            "full_name": "API Feed Player",
            "country": "New Zealand",
            "playing_role": "Batter",
            "batting_style": "Right-hand bat",
            "source": "API",
        }, db_path=test_db_path)

        # Attempted mutation without override must fail
        with pytest.raises(ReadOnlyRecordError):
            crud.update_player(pid, {"country": "Australia"}, allow_api_mutation=False, db_path=test_db_path)

        # Attempted deletion without override must fail
        with pytest.raises(ReadOnlyRecordError):
            crud.delete_player(pid, allow_api_deletion=False, db_path=test_db_path)

    def test_get_players_filtering_and_pagination(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify player filtering by role, country, search, and pagination."""
        batters = crud.get_players(role="Batter", db_path=test_db_path)
        assert len(batters) > 0
        assert all(p["playing_role"] == "Batter" for p in batters)

        indians = crud.get_players(country="India", db_path=test_db_path)
        assert len(indians) > 0
        assert all(p["country"] == "India" for p in indians)

        search_results = crud.get_players(search="Kohli", db_path=test_db_path)
        assert len(search_results) == 1
        assert "Kohli" in search_results[0]["full_name"]

        # Pagination test
        page1 = crud.get_players(limit=5, offset=0, db_path=test_db_path)
        page2 = crud.get_players(limit=5, offset=5, db_path=test_db_path)
        assert len(page1) == 5
        assert len(page2) == 5
        assert page1[0]["player_id"] != page2[0]["player_id"]


# ==============================================================================
# 3. VENUE CRUD OPERATIONS
# ==============================================================================

class TestVenueCRUD:
    """Integration tests for Venue CRUD operations."""

    def test_create_and_get_venue_success(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify creating a valid venue and retrieving it."""
        payload = {
            "venue_name": "Newlands Cricket Ground",
            "city": "Cape Town",
            "country": "South Africa",
            "capacity": 25000,
        }
        vid = crud.create_venue(payload, db_path=test_db_path)
        assert vid > 0

        venue = crud.get_venue_by_id(vid, db_path=test_db_path)
        assert venue is not None
        assert venue["venue_name"] == "Newlands Cricket Ground"
        assert venue["city"] == "Cape Town"

    def test_create_duplicate_venue_fails(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify duplicate venue (same venue_name and city) raises DuplicateRecordError."""
        payload = {
            "venue_name": "Melbourne Cricket Ground",
            "city": "Melbourne",
            "country": "Australia",
        }
        with pytest.raises(DuplicateRecordError):
            crud.create_venue(payload, db_path=test_db_path)

    def test_update_venue_success(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify updating venue capacity."""
        payload = {
            "venue_name": "Updatable Stadium",
            "city": "Perth",
            "country": "Australia",
            "capacity": 30000,
        }
        vid = crud.create_venue(payload, db_path=test_db_path)

        crud.update_venue(vid, {"capacity": 35000}, db_path=test_db_path)
        venue = crud.get_venue_by_id(vid, db_path=test_db_path)
        assert venue is not None
        assert venue["capacity"] == 35000

    def test_delete_unreferenced_venue_success(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify unreferenced venue can be deleted."""
        payload = {
            "venue_name": "Unused Ground",
            "city": "Darwin",
            "country": "Australia",
        }
        vid = crud.create_venue(payload, db_path=test_db_path)
        deleted = crud.delete_venue(vid, db_path=test_db_path)
        assert deleted is True
        assert crud.get_venue_by_id(vid, db_path=test_db_path) is None

    def test_delete_referenced_venue_is_protected(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify venue referenced by existing matches cannot be deleted."""
        # Venue ID 1 (MCG) is referenced by match ID 1
        with pytest.raises(ProtectedRecordError) as exc:
            crud.delete_venue(1, db_path=test_db_path)
        assert "match(es) are scheduled or recorded" in str(exc.value)


# ==============================================================================
# 4. MATCH CRUD OPERATIONS
# ==============================================================================

class TestMatchCRUD:
    """Integration tests for Match CRUD operations."""

    def test_create_and_get_match_success(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify creating a valid match and retrieving details."""
        payload = {
            "match_desc": "1st T20I: India vs Australia",
            "match_format": "T20I",
            "match_date": "2026-10-25",
            "team1_id": 1,
            "team2_id": 2,
            "venue_id": 6,
            "series_id": 5,
            "toss_winner_id": 1,
            "toss_decision": "bat",
            "match_status": "Upcoming",
        }
        mid = crud.create_match(payload, db_path=test_db_path)
        assert mid > 0

        match = crud.get_match_by_id(mid, db_path=test_db_path)
        assert match is not None
        assert match["match_desc"] == "1st T20I: India vs Australia"
        assert match["team1_name"] == "India"
        assert match["team2_name"] == "Australia"
        assert match["venue_name"] == "Wankhede Stadium"
        assert match["match_status"] == "Upcoming"

    def test_create_match_invalid_team_fails(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify referencing a non-existent team raises RecordNotFoundError."""
        payload = {
            "match_desc": "Ghost Match",
            "match_format": "ODI",
            "match_date": "2026-10-25",
            "team1_id": 9999,
            "team2_id": 2,
            "venue_id": 1,
        }
        with pytest.raises(RecordNotFoundError):
            crud.create_match(payload, db_path=test_db_path)

    def test_delete_match_without_force_fails_if_has_scorecards(
        self, crud: CRUDService, test_db_path: Path
    ) -> None:
        """Verify deleting a match with innings requires force=True to protect scorecards."""
        # Match 1 has innings and performances
        with pytest.raises(ProtectedRecordError) as exc:
            crud.delete_match(1, force=False, db_path=test_db_path)
        assert "recorded innings with player scorecards" in str(exc.value)

    def test_delete_match_with_force_succeeds_and_cascades(
        self, crud: CRUDService, test_db_path: Path
    ) -> None:
        """Verify force deleting a match cascades safely to innings and child scorecards."""
        # Force delete match 1
        success = crud.delete_match(1, force=True, db_path=test_db_path)
        assert success is True
        assert crud.get_match_by_id(1, db_path=test_db_path) is None

        # Confirm innings for match 1 were cascade deleted
        manager = DBConnectionManager(test_db_path)
        innings = manager.execute_query(
            "SELECT COUNT(*) AS cnt FROM innings WHERE match_id = 1;",
            db_path=test_db_path,
        )
        assert innings[0]["cnt"] == 0

    def test_api_sourced_match_is_protected(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify API-sourced match is protected against deletion and mutation."""
        mid = crud.create_match({
            "match_desc": "Live API Feed Match",
            "match_format": "T20I",
            "match_date": "2026-10-22",
            "team1_id": 1,
            "team2_id": 2,
            "venue_id": 1,
            "source": "API",
        }, db_path=test_db_path)

        with pytest.raises(ReadOnlyRecordError):
            crud.update_match(mid, {"match_status": "Completed"}, db_path=test_db_path)

        with pytest.raises(ReadOnlyRecordError):
            crud.delete_match(mid, force=True, db_path=test_db_path)


# ==============================================================================
# 5. AUXILIARY LOOKUPS & TRANSACTION SAFETY
# ==============================================================================

class TestAuxiliaryAndTransactions:
    """Tests for reference lookups and transaction safety."""

    def test_get_teams_and_series(self, crud: CRUDService, test_db_path: Path) -> None:
        """Verify get_teams and get_series return seeded dropdown lists."""
        teams = crud.get_teams(db_path=test_db_path)
        assert len(teams) >= 6
        assert any(t["team_name"] == "India" for t in teams)

        series = crud.get_series(db_path=test_db_path)
        assert len(series) >= 10

    def test_transaction_atomic_rollback_on_failed_write(
        self, crud: CRUDService, test_db_path: Path
    ) -> None:
        """Verify transaction rollback prevents partial state changes upon error."""
        manager = DBConnectionManager(test_db_path)
        count_before = manager.execute_one(
            "SELECT COUNT(*) AS cnt FROM players;", db_path=test_db_path
        )["cnt"]

        # Attempt to insert valid player then force failure in same transaction
        try:
            with manager.transaction(test_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO players (full_name, country, playing_role, batting_style) "
                    "VALUES ('Temp Rollback Player', 'India', 'Batter', 'Right-hand bat');"
                )
                # Force violation
                cursor.execute("INSERT INTO players (player_id) VALUES (NULL);")
        except Exception:
            pass

        count_after = manager.execute_one(
            "SELECT COUNT(*) AS cnt FROM players;", db_path=test_db_path
        )["cnt"]
        assert count_before == count_after
