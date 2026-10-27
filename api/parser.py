"""Provider-independent response parser and schema transformer.

Converts nested third-party JSON payloads (from CricketData.org or RapidAPI)
into normalized dictionaries matching the SQLite schema:
- Teams, Venues, Matches, Innings, Batting, Bowling
- Normalizes cricket formats, dismissal types, and true overs math
- Enforces source='API' tag to guarantee ADR-006 immutability
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_format(format_raw: Optional[str]) -> str:
    """Normalizes API format strings to schema CHECK constraint values."""
    if not format_raw:
        return "ODI"
    cleaned = format_raw.strip().upper()
    if "T20" in cleaned:
        return "T20I"
    if "TEST" in cleaned:
        return "Test"
    if "ODI" in cleaned or "ONE DAY" in cleaned:
        return "ODI"
    return "T20I"


def normalize_status(status_raw: Optional[str]) -> str:
    """Normalizes match status strings to schema CHECK constraint values."""
    if not status_raw:
        return "Upcoming"
    cleaned = status_raw.strip().lower()
    if any(k in cleaned for k in ("won", "complete", "result", "finished")):
        return "Completed"
    if any(k in cleaned for k in ("live", "progress", "ongoing", "current", "opt to")):
        return "Live"
    if any(k in cleaned for k in ("abandoned", "cancelled")):
        return "Abandoned"
    if "tied" in cleaned:
        return "Tied"
    if "no result" in cleaned:
        return "No Result"
    return "Upcoming"


def parse_match_outcome(status_str: Optional[str], team1: str, team2: str) -> Dict[str, Any]:
    """Extracts winning team, margin, and win type from status text or structured attributes.
    
    Supports:
        'India won by 6 wkts' -> winner='India', margin=6, type='wickets'
        'Australia won by 45 runs' -> winner='Australia', margin=45, type='runs'
        'Match tied' -> winner=None, margin=None, type='tie'
        'Match abandoned' -> winner=None, margin=None, type='abandoned'
        'No result' -> winner=None, margin=None, type='no result'
    """
    if not status_str:
        return {"winning_team_name": None, "win_margin": None, "win_type": None}

    cleaned = status_str.strip().lower()

    if "tie" in cleaned or "tied" in cleaned:
        return {"winning_team_name": None, "win_margin": None, "win_type": "tie"}
    if "abandoned" in cleaned or "cancelled" in cleaned:
        return {"winning_team_name": None, "win_margin": None, "win_type": "abandoned"}
    if "no result" in cleaned:
        return {"winning_team_name": None, "win_margin": None, "win_type": "no result"}

    match = re.search(r"(.+?)\s+won\s+by\s+(\d+)\s*(run|runs|wicket|wickets|wkt|wkts)", cleaned, re.IGNORECASE)
    if match:
        winner_part = match.group(1).strip()
        margin = int(match.group(2))
        unit = match.group(3).lower()
        win_type = "wickets" if "w" in unit else "runs"

        winning_team_name = None
        if team1.lower() in winner_part.lower() or winner_part.lower() in team1.lower():
            winning_team_name = team1
        elif team2.lower() in winner_part.lower() or winner_part.lower() in team2.lower():
            winning_team_name = team2
        else:
            winning_team_name = winner_part.title()

        return {
            "winning_team_name": winning_team_name,
            "win_margin": margin,
            "win_type": win_type,
        }

    return {"winning_team_name": None, "win_margin": None, "win_type": None}


def parse_toss_info(
    status_str: Optional[str] = None,
    toss_winner_raw: Optional[str] = None,
    toss_choice_raw: Optional[str] = None,
    team1: str = "",
    team2: str = "",
) -> Dict[str, Optional[str]]:
    """Extracts toss winner team name and decision ('bat' or 'bowl') from API fields or status string."""
    winner_name = None
    decision = None

    # 1. Check explicit toss fields first
    if toss_choice_raw:
        choice = str(toss_choice_raw).strip().lower()
        if "bat" in choice:
            decision = "bat"
        elif "bowl" in choice or "field" in choice:
            decision = "bowl"

    if toss_winner_raw:
        t_raw = str(toss_winner_raw).strip().lower()
        if team1 and (team1.lower() in t_raw or t_raw in team1.lower()):
            winner_name = team1
        elif team2 and (team2.lower() in t_raw or t_raw in team2.lower()):
            winner_name = team2
        else:
            winner_name = str(toss_winner_raw).strip().title()

    # 2. If missing, parse from status string (e.g. "Zimbabwe opt to bowl", "India won toss & elected to bat")
    if status_str and (not winner_name or not decision):
        st_clean = status_str.strip()
        m1 = re.search(r"(.+?)\s+(?:opt|opted|elected|chose|decided)\s+(?:to\s+)?(bat|bowl|field)", st_clean, re.IGNORECASE)
        m2 = re.search(r"(.+?)\s+won\s+(?:the\s+)?toss(?:\s*(?:and|&)?\s*(?:elected|chose|opted)?\s*(?:to\s+)?(bat|bowl|field)?)?", st_clean, re.IGNORECASE)

        m = m1 or m2
        if m:
            matched_team = m.group(1).strip()
            if not winner_name:
                if team1 and (team1.lower() in matched_team.lower() or matched_team.lower() in team1.lower()):
                    winner_name = team1
                elif team2 and (team2.lower() in matched_team.lower() or matched_team.lower() in team2.lower()):
                    winner_name = team2
                else:
                    winner_name = matched_team.title()

            if not decision and len(m.groups()) >= 2 and m.group(2):
                choice = m.group(2).lower()
                if "bat" in choice:
                    decision = "bat"
                elif "bowl" in choice or "field" in choice:
                    decision = "bowl"

    return {
        "toss_winner_name": winner_name,
        "toss_decision": decision,
    }


def normalize_dismissal(dismissal_raw: Optional[str]) -> str:
    """Maps freeform dismissal strings into schema CHECK constraint enum."""
    if not dismissal_raw or dismissal_raw.strip().lower() in ("not out", "batting", "*", "n.o."):
        return "not out"
    cleaned = dismissal_raw.strip().lower()
    if "lbw" in cleaned:
        return "lbw"
    if "run out" in cleaned:
        return "run out"
    if "stump" in cleaned or "st " in cleaned:
        return "stumped"
    if "hit wicket" in cleaned:
        return "hit wicket"
    if "retired" in cleaned:
        return "retired hurt"
    if "c & b" in cleaned or "caught" in cleaned or "c " in cleaned:
        return "caught"
    if "b " in cleaned or "bowled" in cleaned:
        return "bowled"
    if "did not bat" in cleaned or "dnb" in cleaned:
        return "did not bat"
    return "caught"


def parse_overs_to_balls(overs_val: Any) -> Tuple[int, float]:
    """Converts cricket dot-notation overs into total legal balls bowled and true fractional overs.
    
    Examples:
        '4.2' -> 26 balls (4*6 + 2), 4.3333 fractional overs
        '4.6' -> 30 balls (5*6 + 0), 5.0 fractional overs (completed over rollover)
        '10.0' -> 60 balls, 10.0 fractional overs
        10 -> 60 balls, 10.0 fractional overs
    """
    if overs_val is None:
        return 0, 0.0

    try:
        overs_str = str(overs_val).strip()
        if "." in overs_str:
            parts = overs_str.split(".")
            completed_overs = int(parts[0])
            balls_part = int(parts[1]) if parts[1] else 0
        else:
            completed_overs = int(overs_str)
            balls_part = 0
    except (ValueError, TypeError):
        return 0, 0.0

    if completed_overs < 0 or balls_part < 0:
        return 0, 0.0

    # In cricket dot-notation, if balls_part >= 6 it rolls over into completed overs
    if balls_part >= 6:
        completed_overs += balls_part // 6
        balls_part = balls_part % 6

    total_balls = (completed_overs * 6) + balls_part
    fractional_overs = round(total_balls / 6.0, 4)
    return total_balls, fractional_overs


class CricketDataParser:
    """Transforms raw CricketData.org JSON structures into normalized schema entities."""

    @staticmethod
    def parse_match(raw_match: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts normalized match attributes from a CricketData.org match dictionary."""
        match_id_external = str(raw_match.get("id", ""))
        match_desc = raw_match.get("name", "Match")
        match_format = normalize_format(raw_match.get("matchType"))
        match_status = normalize_status(raw_match.get("status"))

        # Extract date
        raw_date = raw_match.get("dateTimeGMT") or raw_match.get("date")
        if raw_date:
            try:
                # Format: 2024-03-22T14:30:00 or 2024-03-22
                match_date = raw_date[:10]
            except Exception:
                match_date = datetime.now().strftime("%Y-%m-%d")
        else:
            match_date = datetime.now().strftime("%Y-%m-%d")

        # Extract team names
        teams = raw_match.get("teams", [])
        team1_name = teams[0] if len(teams) > 0 else "Team 1"
        team2_name = teams[1] if len(teams) > 1 else "Team 2"

        # Venue
        venue_name = raw_match.get("venue", "International Stadium")

        # Parse outcome details (winner, margin, win_type)
        raw_status = raw_match.get("status")
        outcome = parse_match_outcome(raw_status, team1_name, team2_name)

        # Parse toss details
        toss = parse_toss_info(
            status_str=raw_status,
            toss_winner_raw=raw_match.get("tossWinner"),
            toss_choice_raw=raw_match.get("tossChoice"),
            team1=team1_name,
            team2=team2_name,
        )

        return {
            "external_id": match_id_external,
            "match_desc": match_desc,
            "match_format": match_format,
            "match_date": match_date,
            "match_status": match_status,
            "team1_name": team1_name,
            "team2_name": team2_name,
            "venue_name": venue_name,
            "toss_winner_name": toss.get("toss_winner_name"),
            "toss_decision": toss.get("toss_decision"),
            "winning_team_name": outcome.get("winning_team_name"),
            "win_margin": outcome.get("win_margin"),
            "win_type": outcome.get("win_type"),
            "source": "API",
        }

    @staticmethod
    def parse_scorecard(raw_scorecard: Dict[str, Any]) -> Dict[str, Any]:
        """Parses batting and bowling innings arrays from CricketData.org scorecard data.
        
        Extracts innings totals (runs, wickets, overs) from 'score' block if present,
        or computes them from detailed batting/bowling statistics.
        """
        parsed_innings = []
        scorecard_list = raw_scorecard.get("scorecard", [])
        scores_summary = raw_scorecard.get("score", [])

        # Build lookup table for inning summary if score list exists
        summary_by_name = {}
        if isinstance(scores_summary, list):
            for s in scores_summary:
                if isinstance(s, dict) and "inning" in s:
                    summary_by_name[s["inning"].strip().lower()] = s

        for idx, inn in enumerate(scorecard_list, start=1):
            raw_inning_name = inn.get("inning", f"Innings {idx}").strip()
            # Clean up team name from strings like "India Inning 1" or "Team A 1st Innings"
            batting_team_name = re.sub(r"\s+(Innings?|Inning|\d+(st|nd|rd|th))\b.*$", "", raw_inning_name, flags=re.IGNORECASE).strip()
            if not batting_team_name:
                batting_team_name = raw_inning_name
            
            # Batting performances
            batting_rows = []
            batting_data = inn.get("batting", [])
            for b_idx, b in enumerate(batting_data, start=1):
                if isinstance(b.get("batsman"), dict):
                    p_name = b["batsman"].get("name")
                elif b.get("batsman"):
                    p_name = str(b.get("batsman"))
                elif b.get("name"):
                    p_name = str(b.get("name"))
                elif b.get("player"):
                    p_name = str(b.get("player"))
                else:
                    p_name = f"Batter {b_idx}"

                runs = int(b.get("r") if b.get("r") is not None else (b.get("runs") or 0))
                balls = int(b.get("b") if b.get("b") is not None else (b.get("balls") or 0))
                fours = int(b.get("4s") if b.get("4s") is not None else (b.get("fours") or 0))
                sixes = int(b.get("6s") if b.get("6s") is not None else (b.get("sixes") or 0))
                raw_dismissal = b.get("dismissal-text") or b.get("dismissal") or b.get("dismissalText") or b.get("status")
                dismissal = normalize_dismissal(raw_dismissal)
                is_not_out = 1 if dismissal == "not out" else 0

                batting_rows.append({
                    "player_name": p_name.strip() if p_name else f"Batter {b_idx}",
                    "batting_position": b_idx,
                    "runs_scored": runs,
                    "balls_faced": balls,
                    "fours": fours,
                    "sixes": sixes,
                    "dismissal_type": dismissal,
                    "is_not_out": is_not_out,
                })

            # Bowling performances
            bowling_rows = []
            bowling_data = inn.get("bowling", [])
            for bow in bowling_data:
                if isinstance(bow.get("bowler"), dict):
                    p_name = bow["bowler"].get("name")
                elif bow.get("bowler"):
                    p_name = str(bow.get("bowler"))
                elif bow.get("name"):
                    p_name = str(bow.get("name"))
                elif bow.get("player"):
                    p_name = str(bow.get("player"))
                else:
                    p_name = "Bowler"

                raw_overs = bow.get("o") if bow.get("o") is not None else (bow.get("overs") or 0)
                balls_bowled, fractional_overs = parse_overs_to_balls(raw_overs)
                maidens = int(bow.get("m") if bow.get("m") is not None else (bow.get("maidens") or 0))
                runs_conceded = int(bow.get("r") if bow.get("r") is not None else (bow.get("runs") or 0))
                wickets = min(int(bow.get("w") if bow.get("w") is not None else (bow.get("wickets") or 0)), 10)

                bowling_rows.append({
                    "player_name": p_name.strip() if p_name else "Bowler",
                    "overs_bowled": fractional_overs,
                    "balls_bowled": balls_bowled,
                    "maidens": maidens,
                    "runs_conceded": runs_conceded,
                    "wickets_taken": wickets,
                })

            # Resolve innings totals (runs, wickets, overs)
            # Try summary block first
            summary_match = summary_by_name.get(raw_inning_name.lower())
            if not summary_match and idx <= len(scores_summary):
                summary_match = scores_summary[idx - 1] if isinstance(scores_summary[idx - 1], dict) else None

            if summary_match:
                total_runs = int(summary_match.get("r", 0) or 0)
                total_wickets = min(int(summary_match.get("w", 0) or 0), 10)
                overs_raw = summary_match.get("o", 0.0)
                _, overs_completed = parse_overs_to_balls(overs_raw)
            else:
                # Calculate from individual performances if summary block absent
                total_runs = sum(b["runs_scored"] for b in batting_rows)
                total_wickets = min(sum(bow["wickets_taken"] for bow in bowling_rows), 10)
                total_balls = sum(bow["balls_bowled"] for bow in bowling_rows)
                overs_completed = round(total_balls / 6.0, 2)

            parsed_innings.append({
                "innings_number": idx,
                "batting_team": batting_team_name,
                "total_runs": total_runs,
                "total_wickets": total_wickets,
                "overs_completed": overs_completed,
                "batting": batting_rows,
                "bowling": bowling_rows,
            })

        toss = parse_toss_info(
            status_str=raw_scorecard.get("status"),
            toss_winner_raw=raw_scorecard.get("tossWinner"),
            toss_choice_raw=raw_scorecard.get("tossChoice"),
        )

        return {
            "external_id": str(raw_scorecard.get("id", "")),
            "innings": parsed_innings,
            "toss_winner_name": toss.get("toss_winner_name"),
            "toss_decision": toss.get("toss_decision"),
            "source": "API",
        }
