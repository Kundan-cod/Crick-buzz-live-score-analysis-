"""Synthetic demonstration dataset seeder for Cricbuzz LiveStats.

Populates the database with realistic, internally consistent cricket data across
Test, ODI, and T20I formats. Supports repeatable and idempotent execution:
running the script multiple times will not duplicate records.

DISCLAIMER: [SYNTHETIC TEST FIXTURE]
All match scorecards and player performance records in this module are explicitly
synthetic demonstration records created for development, testing, and SQL practice.
They must NEVER be presented as live cricket data or certified historical records.
"""

import argparse
from datetime import date
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from config import settings
from database.connection import DBConnectionManager, db_manager

logger = logging.getLogger(__name__)


def seed_database(
    db_path: Optional[Union[Path, str]] = None,
    manager: Optional[DBConnectionManager] = None,
) -> Dict[str, int]:
    """Populate the database with synthetic cricket test fixtures.

    Safe and idempotent: uses ON CONFLICT DO UPDATE to prevent duplicate rows.
    Executes entirely within an atomic transaction.

    Args:
        db_path: Path to target database. Defaults to settings.paths.db_path.
        manager: Optional DBConnectionManager instance.

    Returns:
        Dictionary mapping table name to seeded row count.
    """
    mgr = manager or db_manager
    target_path = Path(db_path or mgr.default_db_path)

    logger.info("Starting database seeding at %s...", target_path)

    with mgr.transaction(target_path) as conn:
        cursor = conn.cursor()

        # ----------------------------------------------------------------------
        # 1. TEAMS
        # ----------------------------------------------------------------------
        teams_data = [
            ("India", "IND", "India"),
            ("Australia", "AUS", "Australia"),
            ("England", "ENG", "England"),
            ("South Africa", "SA", "South Africa"),
            ("New Zealand", "NZ", "New Zealand"),
            ("Pakistan", "PAK", "Pakistan"),
        ]
        cursor.executemany(
            """
            INSERT INTO teams (team_name, short_name, country)
            VALUES (?, ?, ?)
            ON CONFLICT(team_name) DO UPDATE SET
                short_name = excluded.short_name,
                country = excluded.country;
            """,
            teams_data,
        )

        # Lookup team IDs
        cursor.execute("SELECT team_name, team_id FROM teams;")
        team_map = {row[0]: row[1] for row in cursor.fetchall()}

        # ----------------------------------------------------------------------
        # 2. VENUES
        # ----------------------------------------------------------------------
        venues_data = [
            ("Narendra Modi Stadium", "Ahmedabad", "India", 132000),
            ("Melbourne Cricket Ground", "Melbourne", "Australia", 100024),
            ("Eden Gardens", "Kolkata", "India", 66000),
            ("Perth Stadium", "Perth", "Australia", 60000),
            ("Lord's Cricket Ground", "London", "England", 31100),
            ("Wankhede Stadium", "Mumbai", "India", 33108),
            ("Newlands", "Cape Town", "South Africa", 25000),
            ("Sydney Cricket Ground", "Sydney", "Australia", 48000),
            ("Kennington Oval", "London", "England", 27500),
            ("Gaddafi Stadium", "Lahore", "Pakistan", 27000),
        ]
        cursor.executemany(
            """
            INSERT INTO venues (venue_name, city, country, capacity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(venue_name, city) DO UPDATE SET
                country = excluded.country,
                capacity = excluded.capacity;
            """,
            venues_data,
        )

        # Lookup venue IDs
        cursor.execute("SELECT venue_name, venue_id FROM venues;")
        venue_map = {row[0]: row[1] for row in cursor.fetchall()}

        # ----------------------------------------------------------------------
        # 3. SERIES
        # ----------------------------------------------------------------------
        series_data = [
            ("Border-Gavaskar Trophy 2024", "Australia", "Test", "2024-11-22", "2025-01-07", 5),
            ("T20 World Cup 2024", "USA & West Indies", "T20I", "2024-06-01", "2024-06-29", 55),
            ("Australia Tour of India 2024", "India", "ODI", "2024-03-15", "2024-03-26", 3),
            ("England Tour of India 2024", "India", "Test", "2024-01-25", "2024-03-11", 5),
            ("ICC Cricket World Cup 2023", "India", "ODI", "2023-10-05", "2023-11-19", 48),
            ("Asia Cup 2023", "Sri Lanka & Pakistan", "ODI", "2023-08-30", "2023-09-17", 13),
            ("The Ashes 2023", "England", "Test", "2023-06-16", "2023-07-31", 5),
            ("India Tour of South Africa 2023", "South Africa", "Multi-format", "2023-12-10", "2024-01-07", 8),
            ("ICC T20 World Cup 2022", "Australia", "T20I", "2022-10-16", "2022-11-13", 45),
            ("India Tour of England 2022", "England", "Multi-format", "2022-07-01", "2022-07-17", 7),
        ]
        cursor.executemany(
            """
            INSERT INTO series (series_name, host_country, match_type, start_date, end_date, total_matches)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(series_name, start_date) DO UPDATE SET
                host_country = excluded.host_country,
                match_type = excluded.match_type,
                end_date = excluded.end_date,
                total_matches = excluded.total_matches;
            """,
            series_data,
        )

        cursor.execute("SELECT series_name, series_id FROM series;")
        series_map = {row[0]: row[1] for row in cursor.fetchall()}

        # ----------------------------------------------------------------------
        # 4. PLAYERS
        # ----------------------------------------------------------------------
        players_data = [
            # India Players (Q1)
            (team_map["India"], "Rohit Sharma", "India", "Batter", "Right-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["India"], "Virat Kohli", "India", "Batter", "Right-hand bat", "Right-arm medium", "LOCAL"),
            (team_map["India"], "Shubman Gill", "India", "Batter", "Right-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["India"], "Rishabh Pant", "India", "Wicket-keeper", "Left-hand bat", "None", "LOCAL"),
            (team_map["India"], "Hardik Pandya", "India", "All-rounder", "Right-hand bat", "Right-arm medium", "LOCAL"),
            (team_map["India"], "Ravindra Jadeja", "India", "All-rounder", "Left-hand bat", "Left-arm orthodox", "LOCAL"),
            (team_map["India"], "Jasprit Bumrah", "India", "Bowler", "Right-hand bat", "Right-arm fast", "LOCAL"),
            (team_map["India"], "Mohammed Shami", "India", "Bowler", "Right-hand bat", "Right-arm fast", "LOCAL"),
            (team_map["India"], "Kuldeep Yadav", "India", "Bowler", "Left-hand bat", "Slow left-arm chinaman", "LOCAL"),
            (team_map["India"], "Suryakumar Yadav", "India", "Batter", "Right-hand bat", "Right-arm medium", "LOCAL"),
            (team_map["India"], "Shreyas Iyer", "India", "Batter", "Right-hand bat", "Right-arm legbreak", "LOCAL"),
            # Australia Players
            (team_map["Australia"], "David Warner", "Australia", "Batter", "Left-hand bat", "Right-arm legbreak", "LOCAL"),
            (team_map["Australia"], "Travis Head", "Australia", "Batter", "Left-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["Australia"], "Steve Smith", "Australia", "Batter", "Right-hand bat", "Right-arm legbreak", "LOCAL"),
            (team_map["Australia"], "Marnus Labuschagne", "Australia", "Batter", "Right-hand bat", "Right-arm legbreak", "LOCAL"),
            (team_map["Australia"], "Glenn Maxwell", "Australia", "All-rounder", "Right-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["Australia"], "Alex Carey", "Australia", "Wicket-keeper", "Left-hand bat", "None", "LOCAL"),
            (team_map["Australia"], "Pat Cummins", "Australia", "Bowler", "Right-hand bat", "Right-arm fast", "LOCAL"),
            (team_map["Australia"], "Mitchell Starc", "Australia", "Bowler", "Left-hand bat", "Left-arm fast", "LOCAL"),
            (team_map["Australia"], "Josh Hazlewood", "Australia", "Bowler", "Left-hand bat", "Right-arm fast", "LOCAL"),
            (team_map["Australia"], "Adam Zampa", "Australia", "Bowler", "Right-hand bat", "Right-arm legbreak", "LOCAL"),
            # England Players
            (team_map["England"], "Jos Buttler", "England", "Wicket-keeper", "Right-hand bat", "None", "LOCAL"),
            (team_map["England"], "Joe Root", "England", "Batter", "Right-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["England"], "Ben Stokes", "England", "All-rounder", "Left-hand bat", "Right-arm fast", "LOCAL"),
            (team_map["England"], "Harry Brook", "England", "Batter", "Right-hand bat", "Right-arm medium", "LOCAL"),
            (team_map["England"], "Jofra Archer", "England", "Bowler", "Right-hand bat", "Right-arm fast", "LOCAL"),
            (team_map["England"], "Adil Rashid", "England", "Bowler", "Right-hand bat", "Right-arm legbreak", "LOCAL"),
            # South Africa Players
            (team_map["South Africa"], "Quinton de Kock", "South Africa", "Wicket-keeper", "Left-hand bat", "None", "LOCAL"),
            (team_map["South Africa"], "Aiden Markram", "South Africa", "Batter", "Right-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["South Africa"], "Heinrich Klaasen", "South Africa", "Batter", "Right-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["South Africa"], "Kagiso Rabada", "South Africa", "Bowler", "Left-hand bat", "Right-arm fast", "LOCAL"),
            (team_map["South Africa"], "Keshav Maharaj", "South Africa", "Bowler", "Right-hand bat", "Left-arm orthodox", "LOCAL"),
            # Pakistan Players
            (team_map["Pakistan"], "Babar Azam", "Pakistan", "Batter", "Right-hand bat", "Right-arm offbreak", "LOCAL"),
            (team_map["Pakistan"], "Mohammad Rizwan", "Pakistan", "Wicket-keeper", "Right-hand bat", "None", "LOCAL"),
            (team_map["Pakistan"], "Shaheen Afridi", "Pakistan", "Bowler", "Left-hand bat", "Left-arm fast", "LOCAL"),
        ]
        cursor.executemany(
            """
            INSERT INTO players (team_id, full_name, country, playing_role, batting_style, bowling_style, source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(full_name, country) DO UPDATE SET
                team_id = excluded.team_id,
                playing_role = excluded.playing_role,
                batting_style = excluded.batting_style,
                bowling_style = excluded.bowling_style,
                source = excluded.source;
            """,
            players_data,
        )

        cursor.execute("SELECT full_name, player_id FROM players;")
        player_map = {row[0]: row[1] for row in cursor.fetchall()}

        # ----------------------------------------------------------------------
        # 5. MATCHES
        # ----------------------------------------------------------------------
        matches_specs = [
            # 1. IND vs AUS 1st Test 2024 (Perth)
            (
                series_map["Border-Gavaskar Trophy 2024"],
                "IND vs AUS 1st Test - Perth",
                "Test",
                "2024-11-22",
                team_map["India"],
                team_map["Australia"],
                venue_map["Perth Stadium"],
                team_map["India"],
                "bat",
                "Completed",
                team_map["India"],
                295,
                "runs",
            ),
            # 2. IND vs AUS 3rd ODI 2024 (Kolkata) - Close Match (won by 4 wickets)
            (
                series_map["Australia Tour of India 2024"],
                "IND vs AUS 3rd ODI - Kolkata",
                "ODI",
                "2024-03-24",
                team_map["India"],
                team_map["Australia"],
                venue_map["Eden Gardens"],
                team_map["Australia"],
                "bat",
                "Completed",
                team_map["India"],
                4,
                "wickets",
            ),
            # 3. IND vs SA Final T20 World Cup 2024 (Bridgetown/Barbados -> Newlands for local test) - Close Match (7 runs)
            (
                series_map["T20 World Cup 2024"],
                "IND vs SA Final T20I",
                "T20I",
                "2024-06-29",
                team_map["India"],
                team_map["South Africa"],
                venue_map["Newlands"],
                team_map["India"],
                "bat",
                "Completed",
                team_map["India"],
                7,
                "runs",
            ),
            # 4. IND vs ENG 1st Test 2024 (Ahmedabad)
            (
                series_map["England Tour of India 2024"],
                "IND vs ENG 1st Test - Ahmedabad",
                "Test",
                "2024-01-25",
                team_map["India"],
                team_map["England"],
                venue_map["Narendra Modi Stadium"],
                team_map["England"],
                "bat",
                "Completed",
                team_map["India"],
                106,
                "runs",
            ),
            # 5. IND vs PAK Asia Cup 2023 (Lahore/Colombo -> Gaddafi Stadium)
            (
                series_map["Asia Cup 2023"],
                "IND vs PAK Super Four ODI",
                "ODI",
                "2023-09-11",
                team_map["India"],
                team_map["Pakistan"],
                venue_map["Gaddafi Stadium"],
                team_map["Pakistan"],
                "bowl",
                "Completed",
                team_map["India"],
                228,
                "runs",
            ),
            # 6. AUS vs ENG Ashes 2nd Test 2023 (Lord's) - Close match (43 runs)
            (
                series_map["The Ashes 2023"],
                "ENG vs AUS 2nd Test - Lord's",
                "Test",
                "2023-06-28",
                team_map["England"],
                team_map["Australia"],
                venue_map["Lord's Cricket Ground"],
                team_map["England"],
                "bowl",
                "Completed",
                team_map["Australia"],
                43,
                "runs",
            ),
            # 7. IND vs AUS CWC 2023 Final (Ahmedabad)
            (
                series_map["ICC Cricket World Cup 2023"],
                "IND vs AUS CWC 2023 Final",
                "ODI",
                "2023-11-19",
                team_map["India"],
                team_map["Australia"],
                venue_map["Narendra Modi Stadium"],
                team_map["Australia"],
                "bowl",
                "Completed",
                team_map["Australia"],
                6,
                "wickets",
            ),
            # 8. IND vs SA 2nd Test 2024 (Cape Town)
            (
                series_map["India Tour of South Africa 2023"],
                "SA vs IND 2nd Test - Cape Town",
                "Test",
                "2024-01-03",
                team_map["South Africa"],
                team_map["India"],
                venue_map["Newlands"],
                team_map["South Africa"],
                "bat",
                "Completed",
                team_map["India"],
                7,
                "wickets",
            ),
            # 9. IND vs ENG 2nd ODI 2022 (Lord's)
            (
                series_map["India Tour of England 2022"],
                "ENG vs IND 2nd ODI - Lord's",
                "ODI",
                "2022-07-14",
                team_map["England"],
                team_map["India"],
                venue_map["Lord's Cricket Ground"],
                team_map["India"],
                "bowl",
                "Completed",
                team_map["England"],
                100,
                "runs",
            ),
            # 10. AUS vs PAK T20I 2022 (Sydney) - Close match (5 wickets)
            (
                series_map["ICC T20 World Cup 2022"],
                "AUS vs PAK Super 12 T20I",
                "T20I",
                "2022-10-23",
                team_map["Australia"],
                team_map["Pakistan"],
                venue_map["Sydney Cricket Ground"],
                team_map["Pakistan"],
                "bat",
                "Completed",
                team_map["Australia"],
                3,
                "wickets",
            ),
            # 11. IND vs AUS 1st ODI 2023 (Wankhede) - Close match (5 wickets)
            (
                series_map["ICC Cricket World Cup 2023"],
                "IND vs AUS CWC League Match",
                "ODI",
                "2023-10-08",
                team_map["India"],
                team_map["Australia"],
                venue_map["Wankhede Stadium"],
                team_map["Australia"],
                "bat",
                "Completed",
                team_map["India"],
                6,
                "wickets",
            ),
            # 12. IND vs ENG 3rd T20I 2024 (Wankhede)
            (
                series_map["T20 World Cup 2024"],
                "IND vs ENG Semi-Final T20I",
                "T20I",
                "2024-06-27",
                team_map["India"],
                team_map["England"],
                venue_map["Wankhede Stadium"],
                team_map["England"],
                "bowl",
                "Completed",
                team_map["India"],
                68,
                "runs",
            ),
        ]

        for spec in matches_specs:
            cursor.execute(
                """
                SELECT match_id FROM matches
                WHERE match_desc = ? AND match_date = ? AND team1_id = ? AND team2_id = ?;
                """,
                (spec[1], spec[3], spec[4], spec[5]),
            )
            existing = cursor.fetchone()
            if not existing:
                cursor.execute(
                    """
                    INSERT INTO matches (
                        series_id, match_desc, match_format, match_date, team1_id, team2_id,
                        venue_id, toss_winner_id, toss_decision, match_status,
                        winning_team_id, win_margin, win_type, source
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'LOCAL');
                    """,
                    spec,
                )

        cursor.execute("SELECT match_desc, match_id FROM matches;")
        match_map = {row[0]: row[1] for row in cursor.fetchall()}

        # ----------------------------------------------------------------------
        # 6. INNINGS & SCORECARDS
        # ----------------------------------------------------------------------

        # Helper to safely create innings
        def get_or_create_innings(
            match_name: str,
            innings_num: int,
            batting_team_name: str,
            bowling_team_name: str,
            total_runs: int,
            total_wickets: int,
            overs: float,
        ) -> int:
            m_id = match_map[match_name]
            bat_id = team_map[batting_team_name]
            bowl_id = team_map[bowling_team_name]
            cursor.execute(
                """
                INSERT INTO innings (match_id, innings_number, batting_team_id, bowling_team_id, total_runs, total_wickets, overs_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(match_id, innings_number) DO UPDATE SET
                    total_runs = excluded.total_runs,
                    total_wickets = excluded.total_wickets,
                    overs_completed = excluded.overs_completed;
                """,
                (m_id, innings_num, bat_id, bowl_id, total_runs, total_wickets, overs),
            )
            cursor.execute(
                "SELECT innings_id FROM innings WHERE match_id = ? AND innings_number = ?;",
                (m_id, innings_num),
            )
            return cursor.fetchone()[0]

        # Match 1: IND vs AUS Test (Perth)
        inn1_m1 = get_or_create_innings("IND vs AUS 1st Test - Perth", 1, "India", "Australia", 150, 10, 49.4)
        inn2_m1 = get_or_create_innings("IND vs AUS 1st Test - Perth", 2, "Australia", "India", 104, 10, 51.2)
        inn3_m1 = get_or_create_innings("IND vs AUS 1st Test - Perth", 3, "India", "Australia", 487, 6, 134.3)
        inn4_m1 = get_or_create_innings("IND vs AUS 1st Test - Perth", 4, "Australia", "India", 238, 10, 58.4)

        # Match 2: IND vs AUS 3rd ODI 2024 (Kolkata)
        inn1_m2 = get_or_create_innings("IND vs AUS 3rd ODI - Kolkata", 1, "Australia", "India", 284, 9, 50.0)
        inn2_m2 = get_or_create_innings("IND vs AUS 3rd ODI - Kolkata", 2, "India", "Australia", 285, 6, 48.0)

        # Match 3: IND vs SA Final T20I 2024
        inn1_m3 = get_or_create_innings("IND vs SA Final T20I", 1, "India", "South Africa", 176, 7, 20.0)
        inn2_m3 = get_or_create_innings("IND vs SA Final T20I", 2, "South Africa", "India", 169, 8, 20.0)

        # Match 5: IND vs PAK Super Four ODI 2023
        inn1_m5 = get_or_create_innings("IND vs PAK Super Four ODI", 1, "India", "Pakistan", 356, 2, 50.0)
        inn2_m5 = get_or_create_innings("IND vs PAK Super Four ODI", 2, "Pakistan", "India", 128, 10, 32.0)

        # Match 7: IND vs AUS CWC 2023 Final
        inn1_m7 = get_or_create_innings("IND vs AUS CWC 2023 Final", 1, "India", "Australia", 240, 10, 50.0)
        inn2_m7 = get_or_create_innings("IND vs AUS CWC 2023 Final", 2, "Australia", "India", 241, 4, 43.0)

        # ----------------------------------------------------------------------
        # 7. BATTING PERFORMANCES
        # ----------------------------------------------------------------------
        batting_records = [
            # Match 2 Innings 1 (Australia Batting in ODI)
            (inn1_m2, player_map["David Warner"], 1, 56, 61, 6, 1, "caught", 0),
            (inn1_m2, player_map["Travis Head"], 2, 89, 75, 10, 3, "bowled", 0),
            (inn1_m2, player_map["Steve Smith"], 3, 44, 52, 4, 0, "lbw", 0),
            (inn1_m2, player_map["Marnus Labuschagne"], 4, 28, 35, 2, 0, "caught", 0),
            (inn1_m2, player_map["Glenn Maxwell"], 5, 38, 24, 3, 2, "caught", 0),
            (inn1_m2, player_map["Alex Carey"], 6, 15, 18, 1, 0, "run out", 0),
            (inn1_m2, player_map["Pat Cummins"], 7, 8, 12, 0, 0, "not out", 1),
            # Match 2 Innings 2 (India Batting in ODI) - Rohit & Gill opening partnership (122 runs)
            (inn2_m2, player_map["Rohit Sharma"], 1, 104, 98, 11, 4, "caught", 0),  # Century
            (inn2_m2, player_map["Shubman Gill"], 2, 62, 58, 7, 2, "bowled", 0),    # Fifty
            (inn2_m2, player_map["Virat Kohli"], 3, 54, 52, 5, 1, "not out", 1),    # Fifty not out
            (inn2_m2, player_map["Shreyas Iyer"], 4, 32, 38, 3, 0, "caught", 0),
            (inn2_m2, player_map["Hardik Pandya"], 5, 21, 15, 2, 1, "not out", 1),
            # Match 3 Innings 1 (IND vs SA T20I Final - India Batting)
            (inn1_m3, player_map["Rohit Sharma"], 1, 9, 5, 2, 0, "caught", 0),
            (inn1_m3, player_map["Virat Kohli"], 2, 76, 59, 6, 2, "caught", 0),     # Match winning 76
            (inn1_m3, player_map["Rishabh Pant"], 3, 0, 2, 0, 0, "caught", 0),
            (inn1_m3, player_map["Suryakumar Yadav"], 4, 3, 4, 0, 0, "caught", 0),
            (inn1_m3, player_map["Hardik Pandya"], 5, 5, 2, 1, 0, "not out", 1),
            (inn1_m3, player_map["Ravindra Jadeja"], 6, 2, 2, 0, 0, "not out", 1),
            # Match 3 Innings 2 (South Africa Batting in T20I)
            (inn2_m3, player_map["Quinton de Kock"], 1, 39, 31, 4, 1, "caught", 0),
            (inn2_m3, player_map["Aiden Markram"], 2, 4, 5, 1, 0, "caught", 0),
            (inn2_m3, player_map["Heinrich Klaasen"], 3, 52, 27, 2, 5, "caught", 0), # 52 off 27
            # Match 5 Innings 1 (IND vs PAK ODI - Historic 122 & 111)
            (inn1_m5, player_map["Rohit Sharma"], 1, 56, 49, 6, 4, "caught", 0),
            (inn1_m5, player_map["Shubman Gill"], 2, 58, 52, 10, 0, "caught", 0),
            (inn1_m5, player_map["Virat Kohli"], 3, 122, 94, 9, 3, "not out", 1),    # Century 122*
            (inn1_m5, player_map["Shreyas Iyer"], 4, 111, 106, 12, 2, "not out", 1),  # Century 111*
            # Match 7 Innings 1 (CWC Final - India Batting)
            (inn1_m7, player_map["Rohit Sharma"], 1, 47, 31, 4, 3, "caught", 0),
            (inn1_m7, player_map["Virat Kohli"], 2, 54, 63, 4, 0, "bowled", 0),
            (inn1_m7, player_map["Ravindra Jadeja"], 3, 9, 22, 0, 0, "caught", 0),
            # Match 7 Innings 2 (CWC Final - Australia Batting)
            (inn2_m7, player_map["Travis Head"], 1, 137, 120, 15, 4, "caught", 0),   # Century 137
            (inn2_m7, player_map["Marnus Labuschagne"], 2, 58, 110, 4, 0, "not out", 1),
        ]

        cursor.executemany(
            """
            INSERT INTO batting_performances (
                innings_id, player_id, batting_position, runs_scored, balls_faced,
                fours, sixes, dismissal_type, is_not_out
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(innings_id, player_id) DO UPDATE SET
                batting_position = excluded.batting_position,
                runs_scored = excluded.runs_scored,
                balls_faced = excluded.balls_faced,
                fours = excluded.fours,
                sixes = excluded.sixes,
                dismissal_type = excluded.dismissal_type,
                is_not_out = excluded.is_not_out;
            """,
            batting_records,
        )

        # ----------------------------------------------------------------------
        # 8. BOWLING PERFORMANCES
        # ----------------------------------------------------------------------
        bowling_records = [
            # Match 2 Inn1: India bowling vs Australia (ODI)
            # (innings_id, player_id, overs, balls, maidens, runs, wickets, econ, wides, no_balls)
            (inn1_m2, player_map["Mohammed Shami"], 10.0, 60, 1, 51, 3, 5.10, 1, 0),
            (inn1_m2, player_map["Jasprit Bumrah"], 10.0, 60, 2, 38, 2, 3.80, 0, 0),
            (inn1_m2, player_map["Ravindra Jadeja"], 10.0, 60, 0, 44, 2, 4.40, 0, 0),
            (inn1_m2, player_map["Kuldeep Yadav"], 10.0, 60, 0, 56, 1, 5.60, 2, 0),
            (inn1_m2, player_map["Hardik Pandya"], 10.0, 60, 0, 62, 1, 6.20, 1, 0),
            # Match 2 Inn2: Australia bowling vs India (ODI)
            (inn2_m2, player_map["Mitchell Starc"], 9.0, 54, 0, 65, 2, 7.22, 2, 1),
            (inn2_m2, player_map["Pat Cummins"], 10.0, 60, 1, 48, 2, 4.80, 0, 0),
            (inn2_m2, player_map["Josh Hazlewood"], 10.0, 60, 0, 52, 1, 5.20, 1, 0),
            (inn2_m2, player_map["Adam Zampa"], 10.0, 60, 0, 59, 1, 5.90, 0, 0),
            (inn2_m2, player_map["Glenn Maxwell"], 9.0, 54, 0, 58, 0, 6.44, 0, 0),
            # Match 3 Inn1: South Africa bowling vs India (T20I Final)
            (inn1_m3, player_map["Kagiso Rabada"], 4.0, 24, 0, 36, 1, 9.00, 1, 0),
            (inn1_m3, player_map["Keshav Maharaj"], 3.0, 18, 0, 23, 2, 7.67, 0, 0),
            # Match 3 Inn2: India bowling vs South Africa (T20I Final)
            (inn2_m3, player_map["Jasprit Bumrah"], 4.0, 24, 0, 18, 2, 4.50, 0, 0),  # Incredible death bowling
            (inn2_m3, player_map["Hardik Pandya"], 3.0, 18, 0, 20, 3, 6.67, 0, 0),   # 3 wickets in death overs
            (inn2_m3, player_map["Kuldeep Yadav"], 4.0, 24, 0, 45, 2, 11.25, 1, 0),
            # Match 5 Inn2: India bowling vs Pakistan (ODI)
            (inn2_m5, player_map["Kuldeep Yadav"], 8.0, 48, 0, 25, 5, 3.12, 0, 0),   # 5-wicket haul
            (inn2_m5, player_map["Jasprit Bumrah"], 5.0, 30, 1, 18, 1, 3.60, 0, 0),
            (inn2_m5, player_map["Hardik Pandya"], 5.0, 30, 0, 17, 1, 3.40, 1, 0),
        ]

        cursor.executemany(
            """
            INSERT INTO bowling_performances (
                innings_id, player_id, overs_bowled, balls_bowled, maidens,
                runs_conceded, wickets_taken, economy_rate, wides, no_balls
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(innings_id, player_id) DO UPDATE SET
                overs_bowled = excluded.overs_bowled,
                balls_bowled = excluded.balls_bowled,
                maidens = excluded.maidens,
                runs_conceded = excluded.runs_conceded,
                wickets_taken = excluded.wickets_taken,
                economy_rate = excluded.economy_rate,
                wides = excluded.wides,
                no_balls = excluded.no_balls;
            """,
            bowling_records,
        )

        # ----------------------------------------------------------------------
        # 9. FIELDING PERFORMANCES (Required for Q21)
        # ----------------------------------------------------------------------
        fielding_records = [
            (inn1_m2, player_map["Ravindra Jadeja"], 2, 0, 1),
            (inn1_m2, player_map["Rishabh Pant"], 1, 0, 0),
            (inn2_m2, player_map["Alex Carey"], 2, 1, 0),
            (inn2_m2, player_map["Steve Smith"], 1, 0, 0),
            (inn1_m3, player_map["Quinton de Kock"], 1, 0, 0),
            (inn2_m3, player_map["Suryakumar Yadav"], 1, 0, 0),  # Iconic boundary catch
            (inn2_m3, player_map["Rishabh Pant"], 2, 0, 0),
            (inn2_m5, player_map["Virat Kohli"], 1, 0, 0),
        ]

        cursor.executemany(
            """
            INSERT INTO fielding_performances (innings_id, player_id, catches, stumpings, run_outs)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(innings_id, player_id) DO UPDATE SET
                catches = excluded.catches,
                stumpings = excluded.stumpings,
                run_outs = excluded.run_outs;
            """,
            fielding_records,
        )

        # ----------------------------------------------------------------------
        # 10. PARTNERSHIPS (Required for Q13, Q24)
        # ----------------------------------------------------------------------
        partnerships_records = [
            # Match 2 Innings 2: Rohit Sharma & Shubman Gill (1st wicket: 122 runs)
            (inn2_m2, 1, player_map["Rohit Sharma"], player_map["Shubman Gill"], 122, 110, 0),
            # Match 2 Innings 2: Rohit Sharma & Virat Kohli (2nd wicket: 85 runs)
            (inn2_m2, 2, player_map["Rohit Sharma"], player_map["Virat Kohli"], 85, 78, 0),
            # Match 5 Innings 1: Virat Kohli & Shreyas Iyer (3rd wicket: 233 runs unbroken!)
            (inn1_m5, 3, player_map["Virat Kohli"], player_map["Shreyas Iyer"], 233, 194, 1),
            # Match 2 Innings 1: David Warner & Travis Head (1st wicket: 105 runs)
            (inn1_m2, 1, player_map["David Warner"], player_map["Travis Head"], 105, 96, 0),
            # Match 3 Innings 1: Virat Kohli & Hardik Pandya (5th wicket: 55 runs)
            (inn1_m3, 5, player_map["Virat Kohli"], player_map["Hardik Pandya"], 55, 36, 0),
        ]

        cursor.executemany(
            """
            INSERT INTO partnerships (
                innings_id, wicket_number, player1_id, player2_id,
                runs_scored, balls_faced, is_unbroken
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(innings_id, wicket_number) DO UPDATE SET
                player1_id = excluded.player1_id,
                player2_id = excluded.player2_id,
                runs_scored = excluded.runs_scored,
                balls_faced = excluded.balls_faced,
                is_unbroken = excluded.is_unbroken;
            """,
            partnerships_records,
        )

        # ----------------------------------------------------------------------
        # 11. RECORD COUNT SUMMARY
        # ----------------------------------------------------------------------
        counts = {}
        for tbl in [
            "teams", "venues", "series", "players", "matches",
            "innings", "batting_performances", "bowling_performances",
            "fielding_performances", "partnerships",
        ]:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            counts[tbl] = cursor.fetchone()[0]

    logger.info("Database seeding completed successfully: %s", counts)
    return counts


def print_seeding_summary(counts: Dict[str, int], db_path: Path) -> None:
    """Print a clean summary of the seeded records."""
    print("=" * 70)
    print("Cricbuzz LiveStats - Database Seeding Completed")
    print("=" * 70)
    print(f"Target Database: {db_path}")
    print(f"Data Tag:        LOCAL (Explicitly synthetic demonstration fixtures)")
    print("-" * 70)
    for tbl, count in sorted(counts.items()):
        print(f"  - {tbl:<24} : {count} rows")
    print("=" * 70)


def main() -> None:
    """CLI entrypoint for running the database seeder."""
    parser = argparse.ArgumentParser(description="Seed Cricbuzz LiveStats Database with Test Fixtures")
    parser.add_argument("--db-path", type=str, default=None, help="Custom database path")
    args = parser.parse_args()

    custom_path = Path(args.db_path) if args.db_path else settings.paths.db_path
    counts = seed_database(db_path=custom_path)
    print_seeding_summary(counts, custom_path)


if __name__ == "__main__":
    main()
