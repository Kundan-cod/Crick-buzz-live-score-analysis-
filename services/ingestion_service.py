"""Safe data ingestion service for external cricket API feeds.

Transforms and persists parsed match records and scorecards into the SQLite schema.
Enforces:
- Atomicity via db_manager.transaction()
- Tagging all records with source = 'API' (ADR-006 protection)
- Preservation of existing 'LOCAL' demo fixtures (zero overwrites)
- Idempotent resolution of teams, players, and venues
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from database.connection import DBConnectionManager, db_manager

logger = logging.getLogger("cricbuzz.services.ingestion")


class IngestionService:
    """Handles transactional insertion of API-sourced cricket records."""

    def __init__(self, connection_manager: Optional[DBConnectionManager] = None) -> None:
        self.db = connection_manager or db_manager

    def _get_or_create_team(self, conn, team_name: str, country: Optional[str] = None) -> int:
        """Finds existing team or inserts a new team."""
        cur = conn.cursor()
        clean_name = team_name.strip()
        row = cur.execute(
            "SELECT team_id FROM teams WHERE LOWER(TRIM(team_name)) = LOWER(?)",
            (clean_name,),
        ).fetchone()
        if row:
            return row["team_id"]
        
        words = clean_name.split()
        if len(words) >= 2:
            short_name = "".join(w[0] for w in words)[:4].upper()
        else:
            short_name = clean_name[:3].upper()

        cur.execute(
            "INSERT INTO teams (team_name, short_name, country) VALUES (?, ?, ?)",
            (clean_name, short_name, (country or clean_name).strip()),
        )
        return cur.lastrowid

    def _get_or_create_venue(self, conn, venue_name: str, city: str = "Host City", country: str = "Host Nation") -> int:
        """Finds existing venue or inserts a new venue."""
        cur = conn.cursor()
        clean_name = venue_name.strip()

        # Parse city out of composite string like "Wankhede Stadium, Mumbai"
        if "," in clean_name and (city == "Host City" or not city):
            parts = [p.strip() for p in clean_name.split(",", 1)]
            v_name = parts[0]
            v_city = parts[1]
        else:
            v_name = clean_name
            v_city = city.strip()

        row = cur.execute(
            """
            SELECT venue_id FROM venues 
            WHERE LOWER(TRIM(venue_name)) = LOWER(?) 
               OR (LOWER(TRIM(venue_name)) = LOWER(?) AND LOWER(TRIM(city)) = LOWER(?))
            """,
            (v_name, v_name, v_city),
        ).fetchone()
        if row:
            return row["venue_id"]

        cur.execute(
            "INSERT INTO venues (venue_name, city, country, capacity) VALUES (?, ?, ?, ?)",
            (v_name, v_city, country.strip(), 25000),
        )
        return cur.lastrowid

    def _get_or_create_player(self, conn, player_name: str, team_id: int) -> int:
        """Finds existing player or inserts a new player record."""
        cur = conn.cursor()
        clean_name = player_name.strip()
        row = cur.execute(
            "SELECT player_id FROM players WHERE LOWER(TRIM(full_name)) = LOWER(?)",
            (clean_name,),
        ).fetchone()
        if row:
            return row["player_id"]

        cur.execute(
            """
            INSERT INTO players (team_id, full_name, country, playing_role, batting_style, source)
            VALUES (?, ?, COALESCE((SELECT country FROM teams WHERE team_id = ?), 'International'), 'Batter', 'Right-hand bat', 'API')
            """,
            (team_id, clean_name, team_id),
        )
        return cur.lastrowid

    def ingest_match(self, match_data: Dict[str, Any], db_path: Optional[Path] = None) -> int:
        """Ingests a normalized match record into the database with source='API'.
        
        Returns:
            Inserted or existing match_id.
        """
        with self.db.transaction(db_path) as conn:
            cur = conn.cursor()

            # Resolve teams
            t1_id = self._get_or_create_team(conn, match_data["team1_name"])
            t2_id = self._get_or_create_team(conn, match_data["team2_name"])

            # Resolve venue
            v_id = self._get_or_create_venue(conn, match_data.get("venue_name", "International Stadium"))

            ext_id = match_data.get("external_id")

            # Check for existing match by external_id or date and teams
            if ext_id:
                existing = cur.execute(
                    """
                    SELECT match_id, source, match_status, winning_team_id, win_margin, win_type,
                           toss_winner_id, toss_decision, external_id 
                    FROM matches 
                    WHERE external_id = ? 
                       OR (match_date = ? AND ((team1_id = ? AND team2_id = ?) OR (team1_id = ? AND team2_id = ?)))
                    """,
                    (ext_id, match_data["match_date"], t1_id, t2_id, t2_id, t1_id),
                ).fetchone()
            else:
                existing = cur.execute(
                    """
                    SELECT match_id, source, match_status, winning_team_id, win_margin, win_type,
                           toss_winner_id, toss_decision, external_id 
                    FROM matches 
                    WHERE match_date = ? AND ((team1_id = ? AND team2_id = ?) OR (team1_id = ? AND team2_id = ?))
                    """,
                    (match_data["match_date"], t1_id, t2_id, t2_id, t1_id),
                ).fetchone()

            # Resolve winning team if present in payload
            winner_id = None
            if match_data.get("winning_team_name"):
                winner_id = self._get_or_create_team(conn, match_data["winning_team_name"])

            # Resolve toss info if present in payload
            toss_winner_id = None
            if match_data.get("toss_winner_name"):
                toss_winner_id = self._get_or_create_team(conn, match_data["toss_winner_name"])
            toss_decision = match_data.get("toss_decision")

            if existing:
                # If match already exists and is LOCAL, do NOT overwrite it (ADR-006)
                if existing["source"] == "LOCAL":
                    logger.info("Preserving existing LOCAL demo match %d.", existing["match_id"])
                    return existing["match_id"]
                
                # Incomplete payload protection:
                # Prevent downgrading terminal statuses (Completed/Abandoned/Tied/No Result) to Upcoming or Live
                existing_status = existing["match_status"]
                new_status = match_data.get("match_status", "Upcoming")

                final_status = existing_status
                if existing_status in ("Completed", "Abandoned", "Tied", "No Result"):
                    if new_status in ("Completed", "Abandoned", "Tied", "No Result"):
                        final_status = new_status
                elif existing_status == "Live":
                    if new_status != "Upcoming":
                        final_status = new_status
                else:
                    final_status = new_status

                # Preserve existing non-empty outcome fields if incoming payload lacks them
                final_winner = winner_id if winner_id is not None else existing["winning_team_id"]
                final_margin = match_data.get("win_margin") if match_data.get("win_margin") is not None else existing["win_margin"]
                final_win_type = match_data.get("win_type") if match_data.get("win_type") is not None else existing["win_type"]
                final_toss_winner = toss_winner_id if toss_winner_id is not None else existing["toss_winner_id"]
                final_toss_decision = toss_decision if toss_decision is not None else existing["toss_decision"]

                cur.execute(
                    """
                    UPDATE matches 
                    SET match_status = ?, winning_team_id = ?, win_margin = ?, win_type = ?,
                        toss_winner_id = ?, toss_decision = ?,
                        external_id = COALESCE(external_id, ?)
                    WHERE match_id = ?
                    """,
                    (final_status, final_winner, final_margin, final_win_type, final_toss_winner, final_toss_decision, ext_id, existing["match_id"]),
                )
                logger.info("Updated existing API match %d (status=%s, ext_id=%s).", existing["match_id"], final_status, ext_id)
                return existing["match_id"]

            # Insert new API match
            cur.execute(
                """
                INSERT INTO matches (
                    match_desc, match_format, match_date, team1_id, team2_id,
                    venue_id, toss_winner_id, toss_decision, match_status,
                    winning_team_id, win_margin, win_type, source, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'API', ?)
                """,
                (
                    match_data["match_desc"],
                    match_data["match_format"],
                    match_data["match_date"],
                    t1_id,
                    t2_id,
                    v_id,
                    toss_winner_id,
                    toss_decision,
                    match_data["match_status"],
                    winner_id,
                    match_data.get("win_margin"),
                    match_data.get("win_type"),
                    ext_id,
                ),
            )
            match_id = cur.lastrowid
            logger.info("Ingested new API match %d (%s, ext_id=%s).", match_id, match_data["match_desc"], ext_id)
            return match_id

    def ingest_scorecard(
        self,
        match_id: int,
        scorecard_data: Dict[str, Any],
        db_path: Optional[Path] = None,
    ) -> List[int]:
        """Ingests innings, batting scorecards, and bowling performances transactionally.
        
        Guarantees:
        - Atomic commit: Entire scorecard succeeds or entire transaction rolls back cleanly.
        - ADR-006 protection: Attempting to overwrite a LOCAL demo match raises PermissionError.
        - Accurate bowling economy and overs mapping.
        
        Args:
            match_id: Target match ID to attach scorecards to.
            scorecard_data: Output dictionary from CricketDataParser.parse_scorecard().
            db_path: Optional SQLite database file path.
            
        Returns:
            List of created or updated innings_ids.
        """
        # Verify target match exists and verify ADR-006 protection before transaction
        with self.db.get_connection(db_path) as conn:
            match_row = conn.cursor().execute(
                "SELECT match_id, team1_id, team2_id, source FROM matches WHERE match_id = ?",
                (match_id,),
            ).fetchone()

        if not match_row:
            raise ValueError(f"Target match ID {match_id} does not exist.")

        # ADR-006 Guard: API data ingestion must NEVER modify or overwrite LOCAL demo fixtures
        if match_row["source"] == "LOCAL":
            raise PermissionError(
                f"ADR-006 Protection Violation: Match ID {match_id} is a protected LOCAL demo fixture. "
                "API scorecards cannot overwrite local fixtures."
            )

        with self.db.transaction(db_path) as conn:
            cur = conn.cursor()

            if scorecard_data.get("external_id"):
                cur.execute(
                    "UPDATE matches SET external_id = COALESCE(external_id, ?) WHERE match_id = ?",
                    (scorecard_data["external_id"], match_id),
                )

            # Update toss details from scorecard if available
            if scorecard_data.get("toss_winner_name"):
                tw_id = self._get_or_create_team(conn, scorecard_data["toss_winner_name"])
                cur.execute(
                    """
                    UPDATE matches 
                    SET toss_winner_id = COALESCE(toss_winner_id, ?),
                        toss_decision = COALESCE(toss_decision, ?)
                    WHERE match_id = ?
                    """,
                    (tw_id, scorecard_data.get("toss_decision"), match_id),
                )

            # Retrieve team names for mapping innings batting team
            t1_name = cur.execute("SELECT team_name FROM teams WHERE team_id = ?", (match_row["team1_id"],)).fetchone()["team_name"]
            t2_name = cur.execute("SELECT team_name FROM teams WHERE team_id = ?", (match_row["team2_id"],)).fetchone()["team_name"]

            innings_ids = []
            innings_list = scorecard_data.get("innings", [])

            for inn in innings_list:
                inn_num = int(inn.get("innings_number", 1))

                # Resolve batting vs bowling teams
                batting_team_raw = str(inn.get("batting_team", "")).strip().lower()
                if t1_name.lower() in batting_team_raw:
                    bat_id = match_row["team1_id"]
                    bowl_id = match_row["team2_id"]
                elif t2_name.lower() in batting_team_raw:
                    bat_id = match_row["team2_id"]
                    bowl_id = match_row["team1_id"]
                else:
                    # Default: Odd innings team1 bats, even innings team2 bats
                    if inn_num % 2 == 1:
                        bat_id = match_row["team1_id"]
                        bowl_id = match_row["team2_id"]
                    else:
                        bat_id = match_row["team2_id"]
                        bowl_id = match_row["team1_id"]

                total_runs = int(inn.get("total_runs", 0) or 0)
                total_wickets = int(inn.get("total_wickets", 0) or 0)
                overs_completed = float(inn.get("overs_completed", 0.0) or 0.0)

                # Check if innings already exists
                existing_inn = cur.execute(
                    "SELECT innings_id, total_runs, total_wickets, overs_completed FROM innings WHERE match_id = ? AND innings_number = ?",
                    (match_id, inn_num),
                ).fetchone()

                batting_list = inn.get("batting", [])
                bowling_list = inn.get("bowling", [])

                # Incomplete payload protection:
                # If incoming payload is completely empty (0 runs, 0 wkts, no batsmen, no bowlers)
                # and existing innings already has recorded data, skip overwriting to protect valid records!
                if existing_inn:
                    if total_runs == 0 and total_wickets == 0 and len(batting_list) == 0 and len(bowling_list) == 0:
                        if existing_inn["total_runs"] > 0 or existing_inn["total_wickets"] > 0 or existing_inn["overs_completed"] > 0:
                            logger.warning(
                                "Skipping empty/incomplete scorecard payload for match %d innings %d to preserve existing data.",
                                match_id, inn_num,
                            )
                            innings_ids.append(existing_inn["innings_id"])
                            continue

                    innings_id = existing_inn["innings_id"]
                    cur.execute(
                        """
                        UPDATE innings
                        SET batting_team_id = ?, bowling_team_id = ?, total_runs = ?,
                            total_wickets = ?, overs_completed = ?
                        WHERE innings_id = ?
                        """,
                        (bat_id, bowl_id, total_runs, total_wickets, overs_completed, innings_id),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO innings (
                            match_id, innings_number, batting_team_id, bowling_team_id,
                            total_runs, total_wickets, overs_completed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (match_id, inn_num, bat_id, bowl_id, total_runs, total_wickets, overs_completed),
                    )
                    innings_id = cur.lastrowid

                innings_ids.append(innings_id)

                # Atomically refresh batting & bowling performances for this innings
                # Deleting previous performance rows for this innings inside the transaction
                # prevents UNIQUE(innings_id, batting_position) collisions on batting order changes,
                # prevents duplicate rows on repeated polling, and ensures exact sync with latest API state.
                cur.execute("DELETE FROM batting_performances WHERE innings_id = ?", (innings_id,))
                cur.execute("DELETE FROM bowling_performances WHERE innings_id = ?", (innings_id,))

                # Ingest Batting Performances
                used_positions = set()
                for b_idx, b in enumerate(batting_list, start=1):
                    p_id = self._get_or_create_player(conn, b["player_name"], bat_id)
                    pos = min(max(int(b.get("batting_position", b_idx) or b_idx), 1), 11)
                    while pos in used_positions and pos < 11:
                        pos += 1
                    used_positions.add(pos)

                    cur.execute(
                        """
                        INSERT INTO batting_performances (
                            innings_id, player_id, batting_position, runs_scored,
                            balls_faced, fours, sixes, dismissal_type, is_not_out
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            innings_id,
                            p_id,
                            pos,
                            b.get("runs_scored", 0),
                            b.get("balls_faced", 0),
                            b.get("fours", 0),
                            b.get("sixes", 0),
                            b.get("dismissal_type", "not out"),
                            b.get("is_not_out", 0),
                        ),
                    )

                # Ingest Bowling Performances
                for bow in bowling_list:
                    p_id = self._get_or_create_player(conn, bow["player_name"], bowl_id)
                    overs_bowled = float(bow.get("overs_bowled", 0.0) or 0.0)
                    balls_bowled = int(bow.get("balls_bowled", 0) or 0)
                    maidens = int(bow.get("maidens", 0) or 0)
                    runs_conceded = int(bow.get("runs_conceded", 0) or 0)
                    wickets = min(int(bow.get("wickets_taken", 0) or 0), 10)
                    economy = round((runs_conceded * 6.0) / balls_bowled, 2) if balls_bowled > 0 else 0.0

                    cur.execute(
                        """
                        INSERT INTO bowling_performances (
                            innings_id, player_id, overs_bowled, balls_bowled,
                            maidens, runs_conceded, wickets_taken, economy_rate
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (innings_id, p_id, overs_bowled, balls_bowled, maidens, runs_conceded, wickets, economy),
                    )

            logger.info("Successfully ingested %d innings for match %d.", len(innings_ids), match_id)
            return innings_ids
