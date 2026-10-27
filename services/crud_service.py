"""CRUD operations service for Cricbuzz LiveStats entities.

Provides safe, parameterized Create, Read, Update, and Delete operations for
Players, Venues, and Matches with transactional safety, input validation,
referential integrity protection, and API source segregation.
"""

from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

from database.connection import DBConnectionManager, DatabaseTransactionError, db_manager
from utils.validators import (
    ValidationError,
    validate_match_data,
    validate_player_data,
    validate_venue_data,
)


# ------------------------------------------------------------------------------
# Custom Domain Exceptions
# ------------------------------------------------------------------------------

class CRUDError(Exception):
    """Base exception for all CRUD service errors."""


class RecordNotFoundError(CRUDError):
    """Raised when a requested entity does not exist in the database."""


class DuplicateRecordError(CRUDError):
    """Raised when an operation violates a UNIQUE constraint."""


class ProtectedRecordError(CRUDError):
    """Raised when attempting to delete a record with active foreign-key dependencies."""


class ReadOnlyRecordError(CRUDError):
    """Raised when attempting to mutate or delete a protected API-sourced record."""


# ------------------------------------------------------------------------------
# Helper Utilities
# ------------------------------------------------------------------------------

def _extract_error_message(exc: Exception) -> str:
    """Extract innermost error message from an exception chain."""
    cause = getattr(exc, "__cause__", None)
    if cause is not None:
        return f"{str(cause)} {str(exc)}"
    return str(exc)


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Convert an sqlite3.Row object to a standard Python dictionary."""
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Convert a list of sqlite3.Row objects to a list of dictionaries."""
    return [dict(r) for r in rows]


# ------------------------------------------------------------------------------
# CRUD Service
# ------------------------------------------------------------------------------

class CRUDService:
    """Service providing safe, parameterized CRUD operations for cricket entities."""

    def __init__(self, manager: Optional[DBConnectionManager] = None) -> None:
        """Initialize CRUDService with a database connection manager.

        Args:
            manager: Optional DBConnectionManager instance. Defaults to global db_manager.
        """
        self.db = manager or db_manager

    # ==========================================================================
    # PLAYER CRUD OPERATIONS
    # ==========================================================================

    def create_player(
        self, data: Dict[str, Any], db_path: Optional[Union[Path, str]] = None
    ) -> int:
        """Create a new player record with domain validation and duplicate checking.

        Args:
            data: Raw player attributes dictionary.
            db_path: Optional database path override.

        Returns:
            The primary key (player_id) of the newly created player.

        Raises:
            ValidationError: If input fields violate validation rules.
            DuplicateRecordError: If a player with the same name and country already exists.
            RecordNotFoundError: If the specified team_id does not exist.
        """
        cleaned = validate_player_data(data, is_update=False)

        # Check team_id foreign key existence if specified
        if cleaned.get("team_id"):
            team = self.db.execute_one(
                "SELECT team_id FROM teams WHERE team_id = ?;",
                (cleaned["team_id"],),
                db_path=db_path,
            )
            if not team:
                raise RecordNotFoundError(
                    f"Team with team_id {cleaned['team_id']} does not exist."
                )

        sql = """
        INSERT INTO players (
            team_id, full_name, country, playing_role, batting_style,
            bowling_style, source, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            cleaned.get("team_id"),
            cleaned["full_name"],
            cleaned["country"],
            cleaned["playing_role"],
            cleaned["batting_style"],
            cleaned.get("bowling_style"),
            cleaned.get("source", "LOCAL"),
            cleaned.get("is_active", 1),
        )

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                new_id = cursor.lastrowid
                if new_id is None:
                    raise CRUDError("Failed to retrieve created player_id.")
                return new_id
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            err_msg = _extract_error_message(exc)
            if "UNIQUE constraint failed" in err_msg:
                raise DuplicateRecordError(
                    f"Player '{cleaned['full_name']}' from '{cleaned['country']}' already exists."
                ) from exc
            if "FOREIGN KEY constraint failed" in err_msg:
                raise RecordNotFoundError("Referenced team does not exist.") from exc
            raise CRUDError(f"Database integrity error: {exc}") from exc

    def get_player_by_id(
        self, player_id: int, db_path: Optional[Union[Path, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single player by primary key including team metadata.

        Args:
            player_id: Primary key ID of the player.
            db_path: Optional database path override.

        Returns:
            Player attributes dictionary, or None if not found.
        """
        sql = """
        SELECT p.*, t.team_name, t.short_name AS team_short_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE p.player_id = ?;
        """
        row = self.db.execute_one(sql, (player_id,), db_path=db_path)
        return _row_to_dict(row)

    def get_players(
        self,
        team_id: Optional[int] = None,
        role: Optional[str] = None,
        country: Optional[str] = None,
        is_active: Optional[int] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        db_path: Optional[Union[Path, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve a filtered and paginated list of players.

        Args:
            team_id: Filter by team ID.
            role: Filter by playing role.
            country: Filter by country.
            is_active: Filter by active status (1 for active, 0 for inactive).
            search: Substring search across full_name and country.
            limit: Maximum rows to return.
            offset: Number of rows to skip.
            db_path: Optional database path override.

        Returns:
            List of matching player dictionaries.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if team_id is not None:
            conditions.append("p.team_id = ?")
            params.append(team_id)

        if role is not None:
            conditions.append("p.playing_role = ?")
            params.append(role)

        if country is not None:
            conditions.append("p.country = ?")
            params.append(country)

        if is_active is not None:
            conditions.append("p.is_active = ?")
            params.append(is_active)

        if search:
            search_param = f"%{search.strip()}%"
            conditions.append("(p.full_name LIKE ? OR p.country LIKE ?)")
            params.extend([search_param, search_param])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit)
            if offset is not None:
                limit_clause += " OFFSET ?"
                params.append(offset)

        sql = f"""
        SELECT p.*, t.team_name, t.short_name AS team_short_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        {where_clause}
        ORDER BY p.full_name ASC
        {limit_clause};
        """
        rows = self.db.execute_query(sql, tuple(params), db_path=db_path)
        return _rows_to_list(rows)

    def update_player(
        self,
        player_id: int,
        data: Dict[str, Any],
        allow_api_mutation: bool = False,
        db_path: Optional[Union[Path, str]] = None,
    ) -> bool:
        """Update an existing player record with validation and source protection.

        Args:
            player_id: Primary key ID of player to update.
            data: Dictionary of fields to update.
            allow_api_mutation: If True, allows updating API-sourced records.
            db_path: Optional database path override.

        Returns:
            True if the record was successfully updated.

        Raises:
            RecordNotFoundError: If player does not exist.
            ReadOnlyRecordError: If player has source = 'API' and mutation not allowed.
            ValidationError: If input validation fails.
            DuplicateRecordError: If updated name/country collides with another player.
        """
        existing = self.get_player_by_id(player_id, db_path=db_path)
        if not existing:
            raise RecordNotFoundError(f"Player with ID {player_id} not found.")

        if existing.get("source") == "API" and not allow_api_mutation:
            raise ReadOnlyRecordError(
                f"Player {player_id} is an API-sourced record and cannot be modified."
            )

        cleaned = validate_player_data(data, is_update=True)
        if not cleaned:
            return True  # Nothing to update

        # Check team_id if updating team
        if "team_id" in cleaned and cleaned["team_id"] is not None:
            team = self.db.execute_one(
                "SELECT team_id FROM teams WHERE team_id = ?;",
                (cleaned["team_id"],),
                db_path=db_path,
            )
            if not team:
                raise RecordNotFoundError(
                    f"Team with team_id {cleaned['team_id']} does not exist."
                )

        set_clauses: List[str] = []
        params: List[Any] = []
        for key, value in cleaned.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)

        params.append(player_id)
        sql = f"UPDATE players SET {', '.join(set_clauses)} WHERE player_id = ?;"

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, tuple(params))
                return cursor.rowcount > 0
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            err_msg = _extract_error_message(exc)
            if "UNIQUE constraint failed" in err_msg:
                raise DuplicateRecordError(
                    "Update failed: Another player with this name and country already exists."
                ) from exc
            raise CRUDError(f"Database integrity error: {exc}") from exc

    def delete_player(
        self,
        player_id: int,
        hard_delete: bool = False,
        allow_api_deletion: bool = False,
        db_path: Optional[Union[Path, str]] = None,
    ) -> bool:
        """Delete or deactivate a player record with referential integrity protection.

        By default, performs a safe soft-delete (`is_active = 0`) preserving historical scorecards.
        If hard_delete is True, verifies that no foreign-key dependencies exist before deleting.

        Args:
            player_id: Primary key ID of player to delete.
            hard_delete: If True, physically removes row from database if unreferenced.
            allow_api_deletion: If True, allows deleting API-sourced records.
            db_path: Optional database path override.

        Returns:
            True if deletion or deactivation succeeded.

        Raises:
            RecordNotFoundError: If player does not exist.
            ReadOnlyRecordError: If player has source = 'API' and deletion not allowed.
            ProtectedRecordError: If hard_delete requested on a player with linked scorecards.
        """
        existing = self.get_player_by_id(player_id, db_path=db_path)
        if not existing:
            raise RecordNotFoundError(f"Player with ID {player_id} not found.")

        if existing.get("source") == "API" and not allow_api_deletion:
            raise ReadOnlyRecordError(
                f"Player {player_id} is an API-sourced record and cannot be deleted."
            )

        if not hard_delete:
            # Soft deletion: toggle is_active = 0
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE players SET is_active = 0 WHERE player_id = ?;", (player_id,))
                return cursor.rowcount > 0

        # Hard delete requested: verify foreign-key dependencies first
        batting_count = self.db.execute_one(
            "SELECT COUNT(*) AS cnt FROM batting_performances WHERE player_id = ?;",
            (player_id,),
            db_path=db_path,
        )["cnt"]

        bowling_count = self.db.execute_one(
            "SELECT COUNT(*) AS cnt FROM bowling_performances WHERE player_id = ?;",
            (player_id,),
            db_path=db_path,
        )["cnt"]

        fielding_count = self.db.execute_one(
            "SELECT COUNT(*) AS cnt FROM fielding_performances WHERE player_id = ?;",
            (player_id,),
            db_path=db_path,
        )["cnt"]

        partnership_count = self.db.execute_one(
            "SELECT COUNT(*) AS cnt FROM partnerships WHERE player1_id = ? OR player2_id = ?;",
            (player_id, player_id),
            db_path=db_path,
        )["cnt"]

        total_dependencies = batting_count + bowling_count + fielding_count + partnership_count
        if total_dependencies > 0:
            raise ProtectedRecordError(
                f"Cannot hard delete player {player_id} ('{existing['full_name']}'): "
                f"{total_dependencies} linked match scorecards exist "
                f"({batting_count} batting, {bowling_count} bowling, {fielding_count} fielding, "
                f"{partnership_count} partnerships). Use soft deletion (is_active = 0) instead."
            )

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM players WHERE player_id = ?;", (player_id,))
                return cursor.rowcount > 0
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            raise ProtectedRecordError(
                f"Cannot delete player {player_id} due to active database foreign-key constraints: {exc}"
            ) from exc

    def toggle_player_status(
        self,
        player_id: int,
        is_active: Optional[int] = None,
        db_path: Optional[Union[Path, str]] = None,
    ) -> int:
        """Toggle or explicitly set a player's is_active status.

        Args:
            player_id: Primary key ID of the player.
            is_active: Optional explicit target status (0 or 1). If None, inverts current status.
            db_path: Optional database path override.

        Returns:
            The new is_active status (0 or 1).

        Raises:
            RecordNotFoundError: If player does not exist.
        """
        existing = self.get_player_by_id(player_id, db_path=db_path)
        if not existing:
            raise RecordNotFoundError(f"Player with ID {player_id} not found.")

        new_status = 1 - existing["is_active"] if is_active is None else (1 if is_active else 0)

        with self.db.transaction(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE players SET is_active = ? WHERE player_id = ?;",
                (new_status, player_id),
            )
            return new_status

    # ==========================================================================
    # VENUE CRUD OPERATIONS
    # ==========================================================================

    def create_venue(
        self, data: Dict[str, Any], db_path: Optional[Union[Path, str]] = None
    ) -> int:
        """Create a new venue record with validation and uniqueness checks.

        Args:
            data: Venue attributes dictionary.
            db_path: Optional database path override.

        Returns:
            The primary key (venue_id) of the newly created venue.

        Raises:
            ValidationError: If input fields fail validation.
            DuplicateRecordError: If venue_name and city already exist.
        """
        cleaned = validate_venue_data(data, is_update=False)

        sql = """
        INSERT INTO venues (venue_name, city, country, capacity)
        VALUES (?, ?, ?, ?);
        """
        params = (
            cleaned["venue_name"],
            cleaned["city"],
            cleaned["country"],
            cleaned.get("capacity"),
        )

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                new_id = cursor.lastrowid
                if new_id is None:
                    raise CRUDError("Failed to retrieve created venue_id.")
                return new_id
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            err_msg = _extract_error_message(exc)
            if "UNIQUE constraint failed" in err_msg:
                raise DuplicateRecordError(
                    f"Venue '{cleaned['venue_name']}' in '{cleaned['city']}' already exists."
                ) from exc
            raise CRUDError(f"Database error creating venue: {exc}") from exc

    def get_venue_by_id(
        self, venue_id: int, db_path: Optional[Union[Path, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a single venue by primary key.

        Args:
            venue_id: Primary key ID of the venue.
            db_path: Optional database path override.

        Returns:
            Venue attributes dictionary, or None if not found.
        """
        sql = "SELECT * FROM venues WHERE venue_id = ?;"
        row = self.db.execute_one(sql, (venue_id,), db_path=db_path)
        return _row_to_dict(row)

    def get_venues(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        search: Optional[str] = None,
        min_capacity: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        db_path: Optional[Union[Path, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve a filtered and paginated list of venues.

        Args:
            country: Filter by country.
            city: Filter by city.
            search: Substring search across venue_name, city, and country.
            min_capacity: Filter venues with capacity >= min_capacity.
            limit: Maximum rows to return.
            offset: Number of rows to skip.
            db_path: Optional database path override.

        Returns:
            List of matching venue dictionaries.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if country is not None:
            conditions.append("country = ?")
            params.append(country)

        if city is not None:
            conditions.append("city = ?")
            params.append(city)

        if min_capacity is not None:
            conditions.append("capacity >= ?")
            params.append(min_capacity)

        if search:
            search_param = f"%{search.strip()}%"
            conditions.append("(venue_name LIKE ? OR city LIKE ? OR country LIKE ?)")
            params.extend([search_param, search_param, search_param])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit)
            if offset is not None:
                limit_clause += " OFFSET ?"
                params.append(offset)

        sql = f"""
        SELECT * FROM venues
        {where_clause}
        ORDER BY venue_name ASC
        {limit_clause};
        """
        rows = self.db.execute_query(sql, tuple(params), db_path=db_path)
        return _rows_to_list(rows)

    def update_venue(
        self,
        venue_id: int,
        data: Dict[str, Any],
        db_path: Optional[Union[Path, str]] = None,
    ) -> bool:
        """Update an existing venue record with validation.

        Args:
            venue_id: Primary key ID of venue to update.
            data: Dictionary of fields to update.
            db_path: Optional database path override.

        Returns:
            True if the venue was successfully updated.

        Raises:
            RecordNotFoundError: If venue does not exist.
            ValidationError: If input validation fails.
            DuplicateRecordError: If updated venue_name and city collide with another venue.
        """
        existing = self.get_venue_by_id(venue_id, db_path=db_path)
        if not existing:
            raise RecordNotFoundError(f"Venue with ID {venue_id} not found.")

        cleaned = validate_venue_data(data, is_update=True)
        if not cleaned:
            return True

        set_clauses: List[str] = []
        params: List[Any] = []
        for key, value in cleaned.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)

        params.append(venue_id)
        sql = f"UPDATE venues SET {', '.join(set_clauses)} WHERE venue_id = ?;"

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, tuple(params))
                return cursor.rowcount > 0
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            err_msg = _extract_error_message(exc)
            if "UNIQUE constraint failed" in err_msg:
                raise DuplicateRecordError(
                    "Update failed: Another venue with this name and city already exists."
                ) from exc
            raise CRUDError(f"Database error updating venue: {exc}") from exc

    def delete_venue(
        self, venue_id: int, db_path: Optional[Union[Path, str]] = None
    ) -> bool:
        """Delete a venue record with referential integrity protection.

        Args:
            venue_id: Primary key ID of venue to delete.
            db_path: Optional database path override.

        Returns:
            True if venue was deleted.

        Raises:
            RecordNotFoundError: If venue does not exist.
            ProtectedRecordError: If venue is referenced in one or more matches.
        """
        existing = self.get_venue_by_id(venue_id, db_path=db_path)
        if not existing:
            raise RecordNotFoundError(f"Venue with ID {venue_id} not found.")

        match_count = self.db.execute_one(
            "SELECT COUNT(*) AS cnt FROM matches WHERE venue_id = ?;",
            (venue_id,),
            db_path=db_path,
        )["cnt"]

        if match_count > 0:
            raise ProtectedRecordError(
                f"Cannot delete venue {venue_id} ('{existing['venue_name']}'): "
                f"{match_count} match(es) are scheduled or recorded at this venue."
            )

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM venues WHERE venue_id = ?;", (venue_id,))
                return cursor.rowcount > 0
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            raise ProtectedRecordError(
                f"Cannot delete venue {venue_id} due to active foreign-key constraint: {exc}"
            ) from exc

    # ==========================================================================
    # MATCH CRUD OPERATIONS
    # ==========================================================================

    def create_match(
        self, data: Dict[str, Any], db_path: Optional[Union[Path, str]] = None
    ) -> int:
        """Create a new match record with validation and entity existence verification.

        Args:
            data: Match attributes dictionary.
            db_path: Optional database path override.

        Returns:
            The primary key (match_id) of the newly created match.

        Raises:
            ValidationError: If input validation fails.
            RecordNotFoundError: If referenced team1, team2, venue, or series does not exist.
        """
        cleaned = validate_match_data(data, is_update=False)

        # Verify team1 and team2 exist
        t1 = self.db.execute_one(
            "SELECT team_id FROM teams WHERE team_id = ?;",
            (cleaned["team1_id"],),
            db_path=db_path,
        )
        if not t1:
            raise RecordNotFoundError(f"team1_id {cleaned['team1_id']} does not exist.")

        t2 = self.db.execute_one(
            "SELECT team_id FROM teams WHERE team_id = ?;",
            (cleaned["team2_id"],),
            db_path=db_path,
        )
        if not t2:
            raise RecordNotFoundError(f"team2_id {cleaned['team2_id']} does not exist.")

        # Verify venue exists
        ven = self.db.execute_one(
            "SELECT venue_id FROM venues WHERE venue_id = ?;",
            (cleaned["venue_id"],),
            db_path=db_path,
        )
        if not ven:
            raise RecordNotFoundError(f"venue_id {cleaned['venue_id']} does not exist.")

        # Verify series exists if provided
        if cleaned.get("series_id"):
            ser = self.db.execute_one(
                "SELECT series_id FROM series WHERE series_id = ?;",
                (cleaned["series_id"],),
                db_path=db_path,
            )
            if not ser:
                raise RecordNotFoundError(f"series_id {cleaned['series_id']} does not exist.")

        sql = """
        INSERT INTO matches (
            series_id, match_desc, match_format, match_date, team1_id,
            team2_id, venue_id, toss_winner_id, toss_decision, match_status,
            winning_team_id, win_margin, win_type, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        params = (
            cleaned.get("series_id"),
            cleaned["match_desc"],
            cleaned["match_format"],
            cleaned["match_date"],
            cleaned["team1_id"],
            cleaned["team2_id"],
            cleaned["venue_id"],
            cleaned.get("toss_winner_id"),
            cleaned.get("toss_decision"),
            cleaned.get("match_status", "Completed"),
            cleaned.get("winning_team_id"),
            cleaned.get("win_margin"),
            cleaned.get("win_type"),
            cleaned.get("source", "LOCAL"),
        )

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                new_id = cursor.lastrowid
                if new_id is None:
                    raise CRUDError("Failed to retrieve created match_id.")
                return new_id
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            raise CRUDError(f"Database error creating match: {exc}") from exc

    def get_match_by_id(
        self, match_id: int, db_path: Optional[Union[Path, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve match details including team names, venue name, and series name.

        Args:
            match_id: Primary key ID of the match.
            db_path: Optional database path override.

        Returns:
            Match attributes dictionary, or None if not found.
        """
        sql = """
        SELECT
            m.*,
            t1.team_name AS team1_name, t1.short_name AS team1_short,
            t2.team_name AS team2_name, t2.short_name AS team2_short,
            v.venue_name, v.city AS venue_city, v.country AS venue_country,
            tw.team_name AS toss_winner_name,
            wt.team_name AS winning_team_name,
            s.series_name
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.team_id
        JOIN teams t2 ON m.team2_id = t2.team_id
        JOIN venues v ON m.venue_id = v.venue_id
        LEFT JOIN teams tw ON m.toss_winner_id = tw.team_id
        LEFT JOIN teams wt ON m.winning_team_id = wt.team_id
        LEFT JOIN series s ON m.series_id = s.series_id
        WHERE m.match_id = ?;
        """
        row = self.db.execute_one(sql, (match_id,), db_path=db_path)
        return _row_to_dict(row)

    def get_matches(
        self,
        format: Optional[str] = None,
        status: Optional[str] = None,
        team_id: Optional[int] = None,
        venue_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        db_path: Optional[Union[Path, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve a filtered and paginated list of matches.

        Args:
            format: Filter by match format ('Test', 'ODI', 'T20I', 'T20').
            status: Filter by match status ('Completed', 'Live', 'Upcoming', etc.).
            team_id: Filter matches involving this team as team1 or team2.
            venue_id: Filter matches played at this venue.
            search: Substring search across match_desc, team names, or venue.
            limit: Maximum rows to return.
            offset: Number of rows to skip.
            db_path: Optional database path override.

        Returns:
            List of matching match dictionaries.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if format is not None:
            conditions.append("m.match_format = ?")
            params.append(format)

        if status is not None:
            conditions.append("m.match_status = ?")
            params.append(status)

        if team_id is not None:
            conditions.append("(m.team1_id = ? OR m.team2_id = ?)")
            params.extend([team_id, team_id])

        if venue_id is not None:
            conditions.append("m.venue_id = ?")
            params.append(venue_id)

        if search:
            search_param = f"%{search.strip()}%"
            conditions.append(
                "(m.match_desc LIKE ? OR t1.team_name LIKE ? OR t2.team_name LIKE ? OR v.venue_name LIKE ?)"
            )
            params.extend([search_param, search_param, search_param, search_param])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit)
            if offset is not None:
                limit_clause += " OFFSET ?"
                params.append(offset)

        sql = f"""
        SELECT
            m.*,
            t1.team_name AS team1_name, t1.short_name AS team1_short,
            t2.team_name AS team2_name, t2.short_name AS team2_short,
            v.venue_name, v.city AS venue_city, v.country AS venue_country,
            tw.team_name AS toss_winner_name,
            wt.team_name AS winning_team_name,
            s.series_name
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.team_id
        JOIN teams t2 ON m.team2_id = t2.team_id
        JOIN venues v ON m.venue_id = v.venue_id
        LEFT JOIN teams tw ON m.toss_winner_id = tw.team_id
        LEFT JOIN teams wt ON m.winning_team_id = wt.team_id
        LEFT JOIN series s ON m.series_id = s.series_id
        {where_clause}
        ORDER BY m.match_date DESC, m.match_id DESC
        {limit_clause};
        """
        rows = self.db.execute_query(sql, tuple(params), db_path=db_path)
        return _rows_to_list(rows)

    def update_match(
        self,
        match_id: int,
        data: Dict[str, Any],
        allow_api_mutation: bool = False,
        db_path: Optional[Union[Path, str]] = None,
    ) -> bool:
        """Update an existing match record with validation and source protection.

        Args:
            match_id: Primary key ID of match to update.
            data: Dictionary of fields to update.
            allow_api_mutation: If True, allows updating API-sourced records.
            db_path: Optional database path override.

        Returns:
            True if match was updated.

        Raises:
            RecordNotFoundError: If match does not exist.
            ReadOnlyRecordError: If match has source = 'API' and mutation not allowed.
            ValidationError: If input validation fails.
        """
        existing = self.get_match_by_id(match_id, db_path=db_path)
        if not existing:
            raise RecordNotFoundError(f"Match with ID {match_id} not found.")

        if existing.get("source") == "API" and not allow_api_mutation:
            raise ReadOnlyRecordError(
                f"Match {match_id} is an API-sourced record and cannot be modified."
            )

        cleaned = validate_match_data(data, is_update=True)
        if not cleaned:
            return True

        set_clauses: List[str] = []
        params: List[Any] = []
        for key, value in cleaned.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)

        params.append(match_id)
        sql = f"UPDATE matches SET {', '.join(set_clauses)} WHERE match_id = ?;"

        try:
            with self.db.transaction(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, tuple(params))
                return cursor.rowcount > 0
        except (sqlite3.IntegrityError, DatabaseTransactionError) as exc:
            raise CRUDError(f"Database error updating match: {exc}") from exc

    def delete_match(
        self,
        match_id: int,
        force: bool = False,
        allow_api_deletion: bool = False,
        db_path: Optional[Union[Path, str]] = None,
    ) -> bool:
        """Delete a match record with scorecard protection and API source checks.

        If the match contains recorded innings/scorecards, force=True must be specified
        to confirm cascade deletion of historical match scorecards.

        Args:
            match_id: Primary key ID of match to delete.
            force: If True, allows cascading deletion of innings and scorecards.
            allow_api_deletion: If True, allows deleting API-sourced records.
            db_path: Optional database path override.

        Returns:
            True if match was deleted.

        Raises:
            RecordNotFoundError: If match does not exist.
            ReadOnlyRecordError: If match has source = 'API' and deletion not allowed.
            ProtectedRecordError: If match has recorded scorecards and force=False.
        """
        existing = self.get_match_by_id(match_id, db_path=db_path)
        if not existing:
            raise RecordNotFoundError(f"Match with ID {match_id} not found.")

        if existing.get("source") == "API" and not allow_api_deletion:
            raise ReadOnlyRecordError(
                f"Match {match_id} is an API-sourced record and cannot be deleted."
            )

        # Check for recorded innings/scorecards
        innings_count = self.db.execute_one(
            "SELECT COUNT(*) AS cnt FROM innings WHERE match_id = ?;",
            (match_id,),
            db_path=db_path,
        )["cnt"]

        if innings_count > 0 and not force:
            raise ProtectedRecordError(
                f"Match {match_id} ('{existing['match_desc']}') has {innings_count} "
                "recorded innings with player scorecards. "
                "Set force=True to confirm deletion of match and all associated scorecards."
            )

        with self.db.transaction(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM matches WHERE match_id = ?;", (match_id,))
            return cursor.rowcount > 0

    # ==========================================================================
    # AUXILIARY REFERENCE LOOKUPS (FOR UI DROPDOWNS)
    # ==========================================================================

    def get_teams(
        self, db_path: Optional[Union[Path, str]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all participating teams for UI selection dropdowns.

        Args:
            db_path: Optional database path override.

        Returns:
            List of team dictionaries sorted alphabetically.
        """
        sql = "SELECT * FROM teams ORDER BY team_name ASC;"
        rows = self.db.execute_query(sql, db_path=db_path)
        return _rows_to_list(rows)

    def get_series(
        self, db_path: Optional[Union[Path, str]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all cricket series for UI selection dropdowns.

        Args:
            db_path: Optional database path override.

        Returns:
            List of series dictionaries sorted by start_date descending.
        """
        sql = "SELECT * FROM series ORDER BY start_date DESC;"
        rows = self.db.execute_query(sql, db_path=db_path)
        return _rows_to_list(rows)


# Global singleton instance
crud_service = CRUDService()
