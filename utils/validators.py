"""Input validation and sanitization module for Cricbuzz LiveStats entities.

Provides comprehensive domain rule validation for players, venues, and matches,
ensuring data integrity before execution against database schema constraints.
"""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Set


class ValidationError(ValueError):
    """Raised when an entity input fails validation checks."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """Initialize ValidationError with an optional field identifier.

        Args:
            message: Descriptive error explanation.
            field: Name of the invalid field if applicable.
        """
        super().__init__(message)
        self.field = field
        self.message = message


# ------------------------------------------------------------------------------
# Domain Allowed Constants (aligned with sql/schema.sql CHECK constraints)
# ------------------------------------------------------------------------------

VALID_PLAYING_ROLES: Set[str] = {
    "Batter",
    "Bowler",
    "All-rounder",
    "Wicket-keeper",
}

VALID_BATTING_STYLES: Set[str] = {
    "Right-hand bat",
    "Left-hand bat",
}

VALID_BOWLING_STYLES: Set[str] = {
    "Right-arm fast",
    "Right-arm medium",
    "Right-arm offbreak",
    "Right-arm legbreak",
    "Left-arm fast",
    "Left-arm medium",
    "Left-arm orthodox",
    "Slow left-arm chinaman",
    "None",
}

VALID_MATCH_FORMATS: Set[str] = {
    "Test",
    "ODI",
    "T20I",
    "T20",
}

VALID_MATCH_STATUSES: Set[str] = {
    "Completed",
    "Live",
    "Upcoming",
    "Abandoned",
    "No Result",
    "Tied",
}

VALID_TOSS_DECISIONS: Set[str] = {
    "bat",
    "bowl",
}

VALID_WIN_TYPES: Set[str] = {
    "runs",
    "wickets",
    "tie",
    "no result",
    "abandoned",
}

VALID_SOURCES: Set[str] = {
    "API",
    "LOCAL",
}


# ------------------------------------------------------------------------------
# Player Validator
# ------------------------------------------------------------------------------

def validate_player_data(data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
    """Validate and sanitize player input dictionary.

    Args:
        data: Key-value dictionary of player attributes.
        is_update: If True, partial field updates are allowed.

    Returns:
        Cleaned and normalized dictionary ready for parameterized SQL execution.

    Raises:
        ValidationError: If any field violates business rules or schema constraints.
    """
    cleaned: Dict[str, Any] = {}

    # Required fields for creation
    if not is_update:
        required_fields = ["full_name", "country", "playing_role", "batting_style"]
        for field in required_fields:
            if field not in data or data[field] is None or str(data[field]).strip() == "":
                raise ValidationError(f"Missing required field: '{field}'", field=field)

    # Validate full_name
    if "full_name" in data and data["full_name"] is not None:
        name = str(data["full_name"]).strip()
        if len(name) < 2 or len(name) > 100:
            raise ValidationError(
                "Player full name must be between 2 and 100 characters.", field="full_name"
            )
        if re.search(r"[<>{}[\]\\]", name):
            raise ValidationError(
                "Player name contains invalid special characters.", field="full_name"
            )
        cleaned["full_name"] = name

    # Validate country
    if "country" in data and data["country"] is not None:
        country = str(data["country"]).strip()
        if len(country) < 2 or len(country) > 60:
            raise ValidationError(
                "Country must be between 2 and 60 characters.", field="country"
            )
        cleaned["country"] = country

    # Validate playing_role
    if "playing_role" in data and data["playing_role"] is not None:
        role = str(data["playing_role"]).strip()
        # Case-insensitive resolution
        matched_role = next((r for r in VALID_PLAYING_ROLES if r.lower() == role.lower()), None)
        if not matched_role:
            raise ValidationError(
                f"Invalid playing role '{role}'. Must be one of: {', '.join(sorted(VALID_PLAYING_ROLES))}",
                field="playing_role",
            )
        cleaned["playing_role"] = matched_role

    # Validate batting_style
    if "batting_style" in data and data["batting_style"] is not None:
        bat_style = str(data["batting_style"]).strip()
        matched_bat = next((s for s in VALID_BATTING_STYLES if s.lower() == bat_style.lower()), None)
        if not matched_bat:
            raise ValidationError(
                f"Invalid batting style '{bat_style}'. Must be one of: {', '.join(sorted(VALID_BATTING_STYLES))}",
                field="batting_style",
            )
        cleaned["batting_style"] = matched_bat

    # Validate bowling_style
    if "bowling_style" in data:
        val = data["bowling_style"]
        if val is None or str(val).strip() == "" or str(val).strip().lower() in ("none", "null"):
            cleaned["bowling_style"] = None
        else:
            bowl_style = str(val).strip()
            matched_bowl = next((s for s in VALID_BOWLING_STYLES if s.lower() == bowl_style.lower()), None)
            if not matched_bowl:
                raise ValidationError(
                    f"Invalid bowling style '{bowl_style}'. Must be one of: {', '.join(sorted(VALID_BOWLING_STYLES))} or None.",
                    field="bowling_style",
                )
            cleaned["bowling_style"] = matched_bowl

    # Validate team_id
    if "team_id" in data:
        tid = data["team_id"]
        if tid is not None and str(tid).strip() != "":
            try:
                tid_int = int(tid)
                if tid_int <= 0:
                    raise ValueError
                cleaned["team_id"] = tid_int
            except (ValueError, TypeError):
                raise ValidationError("team_id must be a positive integer or None.", field="team_id")
        else:
            cleaned["team_id"] = None

    # Validate is_active
    if "is_active" in data and data["is_active"] is not None:
        val = data["is_active"]
        if isinstance(val, bool):
            cleaned["is_active"] = 1 if val else 0
        elif str(val).strip() in ("1", "0"):
            cleaned["is_active"] = int(val)
        else:
            raise ValidationError("is_active must be 0, 1, or boolean.", field="is_active")

    # Validate source
    if "source" in data and data["source"] is not None:
        source_str = str(data["source"]).strip().upper()
        if source_str not in VALID_SOURCES:
            raise ValidationError(
                f"Invalid source '{source_str}'. Must be 'LOCAL' or 'API'.", field="source"
            )
        cleaned["source"] = source_str
    elif not is_update:
        cleaned["source"] = "LOCAL"

    return cleaned


# ------------------------------------------------------------------------------
# Venue Validator
# ------------------------------------------------------------------------------

def validate_venue_data(data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
    """Validate and sanitize venue input dictionary.

    Args:
        data: Key-value dictionary of venue attributes.
        is_update: If True, partial field updates are allowed.

    Returns:
        Cleaned and normalized dictionary ready for parameterized SQL execution.

    Raises:
        ValidationError: If any field violates business rules or schema constraints.
    """
    cleaned: Dict[str, Any] = {}

    # Required fields for creation
    if not is_update:
        required_fields = ["venue_name", "city", "country"]
        for field in required_fields:
            if field not in data or data[field] is None or str(data[field]).strip() == "":
                raise ValidationError(f"Missing required field: '{field}'", field=field)

    # Validate venue_name
    if "venue_name" in data and data["venue_name"] is not None:
        name = str(data["venue_name"]).strip()
        if len(name) < 2 or len(name) > 100:
            raise ValidationError("Venue name must be between 2 and 100 characters.", field="venue_name")
        cleaned["venue_name"] = name

    # Validate city
    if "city" in data and data["city"] is not None:
        city = str(data["city"]).strip()
        if len(city) < 2 or len(city) > 60:
            raise ValidationError("City must be between 2 and 60 characters.", field="city")
        cleaned["city"] = city

    # Validate country
    if "country" in data and data["country"] is not None:
        country = str(data["country"]).strip()
        if len(country) < 2 or len(country) > 60:
            raise ValidationError("Country must be between 2 and 60 characters.", field="country")
        cleaned["country"] = country

    # Validate capacity (optional, must be positive if supplied)
    if "capacity" in data:
        cap = data["capacity"]
        if cap is not None and str(cap).strip() != "":
            try:
                cap_int = int(cap)
                if cap_int <= 0:
                    raise ValueError
                cleaned["capacity"] = cap_int
            except (ValueError, TypeError):
                raise ValidationError("Venue capacity must be a positive integer.", field="capacity")
        else:
            cleaned["capacity"] = None

    return cleaned


# ------------------------------------------------------------------------------
# Match Validator
# ------------------------------------------------------------------------------

def validate_match_data(data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
    """Validate and sanitize match input dictionary.

    Args:
        data: Key-value dictionary of match attributes.
        is_update: If True, partial field updates are allowed.

    Returns:
        Cleaned and normalized dictionary ready for parameterized SQL execution.

    Raises:
        ValidationError: If any field violates business rules or schema constraints.
    """
    cleaned: Dict[str, Any] = {}

    # Required fields for creation
    if not is_update:
        required_fields = [
            "match_desc",
            "match_format",
            "match_date",
            "team1_id",
            "team2_id",
            "venue_id",
        ]
        for field in required_fields:
            if field not in data or data[field] is None or str(data[field]).strip() == "":
                raise ValidationError(f"Missing required field: '{field}'", field=field)

    # Validate match_desc
    if "match_desc" in data and data["match_desc"] is not None:
        desc = str(data["match_desc"]).strip()
        if len(desc) < 2 or len(desc) > 200:
            raise ValidationError("Match description must be between 2 and 200 characters.", field="match_desc")
        cleaned["match_desc"] = desc

    # Validate match_format
    if "match_format" in data and data["match_format"] is not None:
        fmt = str(data["match_format"]).strip()
        matched_fmt = next((f for f in VALID_MATCH_FORMATS if f.lower() == fmt.lower()), None)
        if not matched_fmt:
            raise ValidationError(
                f"Invalid match format '{fmt}'. Must be one of: {', '.join(sorted(VALID_MATCH_FORMATS))}",
                field="match_format",
            )
        cleaned["match_format"] = matched_fmt

    # Validate match_date (ISO 8601 YYYY-MM-DD)
    if "match_date" in data and data["match_date"] is not None:
        date_str = str(data["match_date"]).strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            cleaned["match_date"] = date_str
        except ValueError:
            raise ValidationError(
                f"Invalid match date '{date_str}'. Must be in YYYY-MM-DD format.", field="match_date"
            )

    # Validate team1_id and team2_id
    team1 = None
    team2 = None
    if "team1_id" in data and data["team1_id"] is not None:
        try:
            team1 = int(data["team1_id"])
            if team1 <= 0:
                raise ValueError
            cleaned["team1_id"] = team1
        except (ValueError, TypeError):
            raise ValidationError("team1_id must be a positive integer.", field="team1_id")

    if "team2_id" in data and data["team2_id"] is not None:
        try:
            team2 = int(data["team2_id"])
            if team2 <= 0:
                raise ValueError
            cleaned["team2_id"] = team2
        except (ValueError, TypeError):
            raise ValidationError("team2_id must be a positive integer.", field="team2_id")

    if team1 is not None and team2 is not None and team1 == team2:
        raise ValidationError("team1_id and team2_id cannot be identical.", field="team2_id")

    # Validate venue_id
    if "venue_id" in data and data["venue_id"] is not None:
        try:
            vid = int(data["venue_id"])
            if vid <= 0:
                raise ValueError
            cleaned["venue_id"] = vid
        except (ValueError, TypeError):
            raise ValidationError("venue_id must be a positive integer.", field="venue_id")

    # Validate series_id (optional)
    if "series_id" in data:
        sid = data["series_id"]
        if sid is not None and str(sid).strip() != "":
            try:
                sid_int = int(sid)
                if sid_int <= 0:
                    raise ValueError
                cleaned["series_id"] = sid_int
            except (ValueError, TypeError):
                raise ValidationError("series_id must be a positive integer or None.", field="series_id")
        else:
            cleaned["series_id"] = None

    # Validate toss_winner_id (optional)
    if "toss_winner_id" in data:
        tw = data["toss_winner_id"]
        if tw is not None and str(tw).strip() != "":
            try:
                tw_int = int(tw)
                if tw_int <= 0:
                    raise ValueError
                if team1 and team2 and tw_int not in (team1, team2):
                    raise ValidationError("Toss winner must be one of the participating teams.", field="toss_winner_id")
                cleaned["toss_winner_id"] = tw_int
            except (ValueError, TypeError) as exc:
                if isinstance(exc, ValidationError):
                    raise
                raise ValidationError("toss_winner_id must be a positive integer or None.", field="toss_winner_id")
        else:
            cleaned["toss_winner_id"] = None

    # Validate toss_decision (optional)
    if "toss_decision" in data:
        td = data["toss_decision"]
        if td is not None and str(td).strip() != "":
            td_str = str(td).strip().lower()
            if td_str not in VALID_TOSS_DECISIONS:
                raise ValidationError("toss_decision must be 'bat' or 'bowl'.", field="toss_decision")
            cleaned["toss_decision"] = td_str
        else:
            cleaned["toss_decision"] = None

    # Validate match_status
    if "match_status" in data and data["match_status"] is not None:
        stat = str(data["match_status"]).strip()
        matched_stat = next((s for s in VALID_MATCH_STATUSES if s.lower() == stat.lower()), None)
        if not matched_stat:
            raise ValidationError(
                f"Invalid match status '{stat}'. Must be one of: {', '.join(sorted(VALID_MATCH_STATUSES))}",
                field="match_status",
            )
        cleaned["match_status"] = matched_stat
    elif not is_update:
        cleaned["match_status"] = "Completed"

    # Validate winning_team_id (optional)
    if "winning_team_id" in data:
        wt = data["winning_team_id"]
        if wt is not None and str(wt).strip() != "":
            try:
                wt_int = int(wt)
                if wt_int <= 0:
                    raise ValueError
                if team1 and team2 and wt_int not in (team1, team2):
                    raise ValidationError("Winning team must be one of the participating teams.", field="winning_team_id")
                cleaned["winning_team_id"] = wt_int
            except (ValueError, TypeError) as exc:
                if isinstance(exc, ValidationError):
                    raise
                raise ValidationError("winning_team_id must be a positive integer or None.", field="winning_team_id")
        else:
            cleaned["winning_team_id"] = None

    # Validate win_margin (optional, non-negative integer)
    if "win_margin" in data:
        wm = data["win_margin"]
        if wm is not None and str(wm).strip() != "":
            try:
                wm_int = int(wm)
                if wm_int < 0:
                    raise ValueError
                cleaned["win_margin"] = wm_int
            except (ValueError, TypeError):
                raise ValidationError("win_margin must be a non-negative integer or None.", field="win_margin")
        else:
            cleaned["win_margin"] = None

    # Validate win_type (optional)
    if "win_type" in data:
        wt_type = data["win_type"]
        if wt_type is not None and str(wt_type).strip() != "":
            wt_str = str(wt_type).strip().lower()
            if wt_str not in VALID_WIN_TYPES:
                raise ValidationError(
                    f"Invalid win_type '{wt_type}'. Must be one of: {', '.join(sorted(VALID_WIN_TYPES))} or None.",
                    field="win_type",
                )
            cleaned["win_type"] = wt_str
        else:
            cleaned["win_type"] = None

    # Validate source
    if "source" in data and data["source"] is not None:
        source_str = str(data["source"]).strip().upper()
        if source_str not in VALID_SOURCES:
            raise ValidationError(f"Invalid source '{source_str}'. Must be 'LOCAL' or 'API'.", field="source")
        cleaned["source"] = source_str
    elif not is_update:
        cleaned["source"] = "LOCAL"

    return cleaned
