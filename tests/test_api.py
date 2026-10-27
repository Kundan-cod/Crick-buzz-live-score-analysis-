"""Comprehensive automated unit and integration tests for Stage 11 API layer.

All tests utilize mocked HTTP responses and temporary test databases.
ZERO real network calls are made. No live credentials required.
"""

from io import BytesIO
import json
from pathlib import Path
import time
import urllib.error
from unittest.mock import MagicMock, patch
import pytest

from api.base_client import (
    APIAuthenticationError,
    APIConnectionError,
    CricketAPIError,
    InvalidAPIResponseError,
    MissingAPIKeyError,
    RateLimitExceededError,
    SimpleTTLCache,
)
from api.cricketdata_client import CricketDataClient
from api.cricbuzz_client import CricbuzzRapidAPIClient
from api.factory import get_cricket_client
from api.parser import (
    CricketDataParser,
    normalize_dismissal,
    normalize_format,
    normalize_status,
    parse_match_outcome,
    parse_overs_to_balls,
)
from database.connection import DBConnectionManager
from database.init_db import init_database
from services.crud_service import CRUDService, ReadOnlyRecordError
from services.ingestion_service import IngestionService


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------

@pytest.fixture
def mock_client() -> CricketDataClient:
    """Provides a CricketDataClient configured with a mock API key."""
    return CricketDataClient(api_key="mock_test_key_12345", timeout_seconds=2, cache_ttl_seconds=1)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Provides a fresh temporary SQLite database initialized with schema."""
    db_file = tmp_path / "test_api_ingestion.db"
    init_database(db_file, force_recreate=True)
    return db_file


# ==============================================================================
# 1. TTL CACHE TESTS
# ==============================================================================

class TestTTLCache:
    """Verifies that the in-memory cache properly handles TTL and eviction."""

    def test_cache_set_and_get(self) -> None:
        cache = SimpleTTLCache(default_ttl_seconds=10)
        cache.set("key1", {"data": [1, 2, 3]})
        assert cache.get("key1") == {"data": [1, 2, 3]}
        assert cache.size() == 1

    def test_cache_miss_and_expiration(self) -> None:
        cache = SimpleTTLCache(default_ttl_seconds=1)
        cache.set("short_key", "val")
        assert cache.get("short_key") == "val"
        time.sleep(1.1)
        assert cache.get("short_key") is None
        assert cache.size() == 0

    def test_cache_clear(self) -> None:
        cache = SimpleTTLCache(default_ttl_seconds=10)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.size() == 2
        cache.clear()
        assert cache.size() == 0


# ==============================================================================
# 2. CLIENT AUTHENTICATION & ERROR HANDLING (MOCKED)
# ==============================================================================

class TestClientErrorHandling:
    """Verifies graceful error handling and exception hierarchy with mocked HTTP."""

    def test_missing_api_key_raises_error_without_network_call(self) -> None:
        client = CricketDataClient(api_key=None)
        with pytest.raises(MissingAPIKeyError) as exc:
            client.get_live_matches()
        assert "API key is missing" in str(exc.value)

    def test_empty_string_api_key_raises_error(self) -> None:
        client = CricketDataClient(api_key="   ")
        with pytest.raises(MissingAPIKeyError):
            client.get_live_matches()

    @patch("urllib.request.urlopen")
    def test_http_401_raises_authentication_error(self, mock_urlopen, mock_client: CricketDataClient) -> None:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.cricapi.com/v1/currentMatches",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=BytesIO(b'{"status": "failure", "reason": "Invalid API Key"}'),
        )
        with pytest.raises(APIAuthenticationError) as exc:
            mock_client.get_live_matches()
        assert "Invalid CricketData API key" in str(exc.value)

    @patch("urllib.request.urlopen")
    def test_http_429_raises_rate_limit_error(self, mock_urlopen, mock_client: CricketDataClient) -> None:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://api.cricapi.com/v1/currentMatches",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=BytesIO(b"Rate limit exceeded"),
        )
        with pytest.raises(RateLimitExceededError):
            mock_client.get_live_matches()

    @patch("urllib.request.urlopen")
    def test_domain_quota_failure_in_json_raises_rate_limit_error(self, mock_urlopen, mock_client: CricketDataClient) -> None:
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "status": "failure",
            "reason": "You have hit your daily limit of 100 hits. Please upgrade your plan."
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(RateLimitExceededError) as exc:
            mock_client.get_live_matches()
        assert "quota exceeded" in str(exc.value)

    @patch("urllib.request.urlopen")
    def test_successful_request_and_cache_hit(self, mock_urlopen, mock_client: CricketDataClient) -> None:
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "status": "success",
            "data": [
                {"id": "match_001", "name": "India vs Australia, 1st ODI", "matchType": "odi", "status": "Live"}
            ]
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # First call triggers mock HTTP
        matches1 = mock_client.get_live_matches()
        assert len(matches1) == 1
        assert matches1[0]["id"] == "match_001"
        assert mock_urlopen.call_count == 1

        # Second call within TTL hits cache: call_count MUST remain 1
        matches2 = mock_client.get_live_matches()
        assert len(matches2) == 1
        assert mock_urlopen.call_count == 1

        # Force refresh bypasses cache
        matches3 = mock_client.get_live_matches(force_refresh=True)
        assert len(matches3) == 1
        assert mock_urlopen.call_count == 2

    def test_placeholder_key_rejected_as_missing(self) -> None:
        client = CricketDataClient(api_key="your_cricketdata_api_key_here")
        with pytest.raises(MissingAPIKeyError) as exc:
            client.get_live_matches()
        assert "API key is missing" in str(exc.value)

    @patch("urllib.request.urlopen")
    def test_quota_telemetry_tracking_from_info_payload(self, mock_urlopen, mock_client: CricketDataClient) -> None:
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = json.dumps({
            "status": "success",
            "data": [],
            "info": {
                "hitsToday": 14,
                "hitsLimit": 100,
                "credits": 0,
                "server": 12,
            }
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Execute request
        mock_client.get_live_matches()
        assert mock_client.hits_today == 14
        assert mock_client.hits_limit == 100

        quota = mock_client.get_quota_status()
        assert quota["hits_today"] == 14
        assert quota["hits_limit"] == 100
        assert quota["hits_remaining"] == 86

        # Test connection reports quota correctly
        test_res = mock_client.test_connection()
        assert test_res["quota"]["hits_remaining"] == 86


# ==============================================================================
# 3. PARSER & DOMAIN TRANSFORMER TESTS
# ==============================================================================

class TestParserLogic:
    """Verifies that raw API JSON is cleanly normalized into relational schema formats."""

    def test_normalize_format(self) -> None:
        assert normalize_format("t20") == "T20I"
        assert normalize_format("t20i") == "T20I"
        assert normalize_format("odi") == "ODI"
        assert normalize_format("test") == "Test"
        assert normalize_format(None) == "ODI"

    def test_normalize_status(self) -> None:
        assert normalize_status("India won by 6 wickets") == "Completed"
        assert normalize_status("Match in progress") == "Live"
        assert normalize_status("Match abandoned due to rain") == "Abandoned"
        assert normalize_status("Match tied") == "Tied"
        assert normalize_status("Match not started") == "Upcoming"

    def test_normalize_dismissal(self) -> None:
        assert normalize_dismissal("c Smith b Starc") == "caught"
        assert normalize_dismissal("b Bumrah") == "bowled"
        assert normalize_dismissal("lbw b Cummins") == "lbw"
        assert normalize_dismissal("run out (Kohli)") == "run out"
        assert normalize_dismissal("stumped Carey") == "stumped"
        assert normalize_dismissal("not out") == "not out"
        assert normalize_dismissal(None) == "not out"

    def test_parse_overs_to_balls(self) -> None:
        # Dot notation: 4.2 overs = 26 balls, 4.3333 fractional overs
        balls, fractional = parse_overs_to_balls("4.2")
        assert balls == 26
        assert round(fractional, 2) == 4.33

        # Float 4.2 should also parse to 26 balls
        balls_float, frac_float = parse_overs_to_balls(4.2)
        assert balls_float == 26
        assert round(frac_float, 2) == 4.33

        # 4.6 overs rolls over to 5 completed overs (30 balls)
        balls_rollover, frac_rollover = parse_overs_to_balls("4.6")
        assert balls_rollover == 30
        assert frac_rollover == 5.0

        # Partial over (0.5 overs = 5 balls)
        balls_05, frac_05 = parse_overs_to_balls("0.5")
        assert balls_05 == 5
        assert round(frac_05, 2) == 0.83

        # Full 10 overs = 60 balls
        balls_10, frac_10 = parse_overs_to_balls(10)
        assert balls_10 == 60
        assert frac_10 == 10.0

        # Invalid/None/Negative input returns (0, 0.0)
        assert parse_overs_to_balls(None) == (0, 0.0)
        assert parse_overs_to_balls("invalid") == (0, 0.0)
        assert parse_overs_to_balls(-2.4) == (0, 0.0)

    def test_parse_cricketdata_match(self) -> None:
        raw_match = {
            "id": "abc-123",
            "name": "India vs South Africa, 3rd T20I",
            "matchType": "t20",
            "status": "India won by 28 runs",
            "dateTimeGMT": "2026-10-22T14:30:00",
            "teams": ["India", "South Africa"],
            "venue": "Wankhede Stadium, Mumbai",
        }
        parsed = CricketDataParser.parse_match(raw_match)
        assert parsed["external_id"] == "abc-123"
        assert parsed["match_format"] == "T20I"
        assert parsed["match_status"] == "Completed"
        assert parsed["match_date"] == "2026-10-22"
        assert parsed["team1_name"] == "India"
        assert parsed["team2_name"] == "South Africa"
        assert parsed["venue_name"] == "Wankhede Stadium, Mumbai"
        assert parsed["source"] == "API"

    def test_parse_cricketdata_scorecard_with_summary_and_field_variants(self) -> None:
        raw_scorecard = {
            "id": "scorecard-uuid-999",
            "score": [
                {"r": 185, "w": 4, "o": 20.0, "inning": "India Inning 1"},
                {"r": 160, "w": 10, "o": 19.2, "inning": "Australia Inning 1"},
            ],
            "scorecard": [
                {
                    "inning": "India Inning 1",
                    "batting": [
                        {"batsman": {"name": "Rohit Sharma"}, "runs": 65, "balls": 40, "4s": 6, "6s": 3, "dismissal": "c Smith b Starc"},
                        {"name": "Virat Kohli", "r": 50, "b": 35, "fours": 4, "sixes": 1, "dismissalText": "not out"},
                    ],
                    "bowling": [
                        {"bowler": {"name": "Mitchell Starc"}, "overs": 4.0, "maidens": 0, "runs": 35, "wickets": 1},
                        {"name": "Pat Cummins", "o": 4.0, "m": 0, "r": 30, "w": 2},
                    ],
                }
            ],
        }
        parsed = CricketDataParser.parse_scorecard(raw_scorecard)
        assert parsed["external_id"] == "scorecard-uuid-999"
        assert parsed["source"] == "API"
        assert len(parsed["innings"]) == 1

        inn = parsed["innings"][0]
        assert inn["batting_team"] == "India"
        assert inn["total_runs"] == 185
        assert inn["total_wickets"] == 4
        assert inn["overs_completed"] == 20.0
        assert len(inn["batting"]) == 2
        assert inn["batting"][0]["player_name"] == "Rohit Sharma"
        assert inn["batting"][0]["runs_scored"] == 65
        assert inn["batting"][0]["fours"] == 6
        assert inn["batting"][1]["player_name"] == "Virat Kohli"
        assert inn["batting"][1]["is_not_out"] == 1

        assert len(inn["bowling"]) == 2
        assert inn["bowling"][0]["player_name"] == "Mitchell Starc"
        assert inn["bowling"][0]["balls_bowled"] == 24
        assert inn["bowling"][1]["player_name"] == "Pat Cummins"
        assert inn["bowling"][1]["wickets_taken"] == 2


# ==============================================================================
# 4. INGESTION & ADR-006 SOURCE SEGREGATION TESTS
# ==============================================================================

class TestIngestionService:
    """Verifies that API records are ingested safely with source='API'."""

    def test_ingest_match_and_verify_source_protection(self, temp_db: Path) -> None:
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)
        crud = CRUDService(manager=mgr)

        match_payload = {
            "match_desc": "Live API Demonstration Match",
            "match_format": "ODI",
            "match_date": "2026-10-22",
            "match_status": "Completed",
            "team1_name": "New Zealand",
            "team2_name": "Pakistan",
            "venue_name": "Eden Park, Auckland",
            "source": "API",
        }

        # 1. Ingest match
        match_id = ingestion.ingest_match(match_payload, db_path=temp_db)
        assert match_id > 0

        # 2. Verify source is 'API' in database
        with mgr.get_connection(temp_db) as conn:
            row = conn.cursor().execute("SELECT source, match_format FROM matches WHERE match_id = ?", (match_id,)).fetchone()
            assert row["source"] == "API"
            assert row["match_format"] == "ODI"

        # 3. Verify ADR-006: User cannot delete API-sourced record via CRUDService
        with pytest.raises(ReadOnlyRecordError) as exc:
            crud.delete_match(match_id, force=True, db_path=temp_db)
        assert "API-sourced" in str(exc.value)

    def test_ingest_scorecard_transactional_success(self, temp_db: Path) -> None:
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)

        match_payload = {
            "match_desc": "India vs Australia, Final",
            "match_format": "ODI",
            "match_date": "2026-10-22",
            "match_status": "Completed",
            "team1_name": "India",
            "team2_name": "Australia",
            "venue_name": "Narendra Modi Stadium, Ahmedabad",
            "source": "API",
        }
        match_id = ingestion.ingest_match(match_payload, db_path=temp_db)

        raw_scorecard = {
            "id": "match-uuid-final",
            "score": [
                {"r": 280, "w": 6, "o": 50.0, "inning": "India Inning 1"},
            ],
            "scorecard": [
                {
                    "inning": "India Inning 1",
                    "batting": [
                        {"batsman": {"name": "Shubman Gill"}, "runs": 80, "balls": 75, "4s": 8, "6s": 2, "dismissal": "caught"},
                        {"batsman": {"name": "KL Rahul"}, "runs": 60, "balls": 65, "4s": 4, "6s": 1, "dismissal": "not out"},
                    ],
                    "bowling": [
                        {"bowler": {"name": "Josh Hazlewood"}, "overs": 10.0, "maidens": 1, "runs": 45, "wickets": 2},
                        {"bowler": {"name": "Adam Zampa"}, "overs": 10.0, "maidens": 0, "runs": 55, "wickets": 1},
                    ],
                }
            ],
        }
        parsed = CricketDataParser.parse_scorecard(raw_scorecard)
        innings_ids = ingestion.ingest_scorecard(match_id, parsed, db_path=temp_db)

        assert len(innings_ids) == 1
        inn_id = innings_ids[0]

        with mgr.get_connection(temp_db) as conn:
            cur = conn.cursor()
            # Verify innings row
            inn_row = cur.execute("SELECT total_runs, total_wickets, overs_completed FROM innings WHERE innings_id = ?", (inn_id,)).fetchone()
            assert inn_row["total_runs"] == 280
            assert inn_row["total_wickets"] == 6
            assert inn_row["overs_completed"] == 50.0

            # Verify batting rows
            bat_rows = cur.execute("SELECT runs_scored, balls_faced, fours, is_not_out FROM batting_performances WHERE innings_id = ? ORDER BY batting_position ASC", (inn_id,)).fetchall()
            assert len(bat_rows) == 2
            assert bat_rows[0]["runs_scored"] == 80
            assert bat_rows[0]["fours"] == 8
            assert bat_rows[1]["runs_scored"] == 60
            assert bat_rows[1]["is_not_out"] == 1

            # Verify bowling rows and balls math
            bowl_rows = cur.execute("SELECT balls_bowled, maidens, runs_conceded, wickets_taken, economy_rate FROM bowling_performances WHERE innings_id = ? ORDER BY wickets_taken DESC", (inn_id,)).fetchall()
            assert len(bowl_rows) == 2
            assert bowl_rows[0]["balls_bowled"] == 60
            assert bowl_rows[0]["wickets_taken"] == 2
            assert bowl_rows[0]["economy_rate"] == 4.5  # 45 runs / 10 ov = 4.5

    def test_ingest_scorecard_adr006_protection_on_local_match(self, temp_db: Path) -> None:
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)

        # Seed local match manually
        with mgr.transaction(temp_db) as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team Alpha', 'TA', 'AlphaLand')")
            t1 = cur.lastrowid
            cur.execute("INSERT INTO teams (team_name, short_name, country) VALUES ('Team Beta', 'TB', 'BetaLand')")
            t2 = cur.lastrowid
            cur.execute("INSERT INTO venues (venue_name, city, country, capacity) VALUES ('Alpha Stadium', 'Capital', 'AlphaLand', 30000)")
            v1 = cur.lastrowid
            cur.execute(
                """
                INSERT INTO matches (match_desc, match_format, match_date, team1_id, team2_id, venue_id, match_status, source)
                VALUES ('Local Demo Match', 'T20I', '2026-10-22', ?, ?, ?, 'Completed', 'LOCAL')
                """,
                (t1, t2, v1),
            )
            local_match_id = cur.lastrowid

        dummy_scorecard = {"innings": [{"innings_number": 1, "batting_team": "Team Alpha", "batting": [], "bowling": []}]}

        # Ingestion onto LOCAL match MUST raise PermissionError per ADR-006
        with pytest.raises(PermissionError) as exc:
            ingestion.ingest_scorecard(local_match_id, dummy_scorecard, db_path=temp_db)
        assert "ADR-006" in str(exc.value)

    def test_ingest_scorecard_transactional_rollback_on_failure(self, temp_db: Path) -> None:
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)

        match_payload = {
            "match_desc": "Rollback Test Match",
            "match_format": "T20I",
            "match_date": "2026-10-22",
            "match_status": "Completed",
            "team1_name": "England",
            "team2_name": "West Indies",
            "venue_name": "Kensington Oval, Bridgetown",
            "source": "API",
        }
        match_id = ingestion.ingest_match(match_payload, db_path=temp_db)

        # Scorecard with second inning having an illegal negative runs scored constraint violation
        corrupted_scorecard = {
            "innings": [
                {
                    "innings_number": 1,
                    "batting_team": "England",
                    "total_runs": 150,
                    "batting": [{"player_name": "Joe Root", "runs_scored": 50}],
                    "bowling": [],
                },
                {
                    "innings_number": 2,
                    "batting_team": "West Indies",
                    "total_runs": -50,  # Negative total runs violates CHECK (total_runs >= 0)
                    "batting": [],
                    "bowling": [],
                },
            ]
        }

        # Attempting ingestion should fail due to SQLite CHECK constraint
        with pytest.raises(Exception):
            ingestion.ingest_scorecard(match_id, corrupted_scorecard, db_path=temp_db)

        # Verify transaction rollback: zero innings must remain
        with mgr.get_connection(temp_db) as conn:
            count = conn.cursor().execute("SELECT COUNT(*) FROM innings WHERE match_id = ?", (match_id,)).fetchone()[0]
            assert count == 0

    def test_factory_returns_cricketdata_client_by_default(self) -> None:
        client = get_cricket_client()
        assert isinstance(client, CricketDataClient)
        assert client.provider_name == "CricketData.org"
        assert client.is_direct_cricbuzz is False

    def test_factory_returns_rapidapi_client_when_requested(self) -> None:
        client = get_cricket_client(provider="rapidapi")
        assert isinstance(client, CricbuzzRapidAPIClient)
        assert client.provider_name == "RapidAPI Cricbuzz"
        assert client.is_direct_cricbuzz is True


# ==============================================================================
# 5. STAGE 11C WORKFLOW VERIFICATION & IDEMPOTENCY REGRESSION TESTS
# ==============================================================================

class TestStage11CWorkflowVerification:
    """Verifies end-to-end workflow idempotency, incomplete response protections,
    offline enforcement, and schema outcome mapping."""

    def test_offline_mode_blocks_requests_safely(self) -> None:
        """Verifies that offline_mode=True blocks network requests before socket creation."""
        client = CricketDataClient(api_key="valid_looking_key", offline_mode=True)
        with pytest.raises(CricketAPIError) as exc:
            client.get_live_matches()
        assert "OFFLINE_MODE=True" in str(exc.value)

        with pytest.raises(CricketAPIError) as exc:
            client.get_match_scorecard("match-12345")
        assert "OFFLINE_MODE=True" in str(exc.value)

        # Connection test returns safe failure structure without raising
        res = client.test_connection()
        assert res["success"] is False
        assert res["error_type"] == "OfflineModeActive"
        assert "Network requests are safely disabled" in res["message"]

    def test_placeholder_and_empty_keys_fail_safely(self) -> None:
        """Verifies that missing or placeholder keys fail safely without network calls."""
        placeholders = ["", "   ", "your_cricketdata_api_key_here", "PLACEHOLDER", "your_rapidapi_key_here"]
        for key in placeholders:
            c = CricketDataClient(api_key=key)
            with pytest.raises(MissingAPIKeyError):
                c.get_live_matches()

    def test_repeated_polling_idempotency_zero_duplicates(self, temp_db: Path) -> None:
        """Verifies that repeated polling does not duplicate teams, players, matches,
        innings, batting records, or bowling records."""
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)

        match_payload = {
            "external_id": "poll-match-1",
            "match_desc": "South Africa vs New Zealand, 1st ODI",
            "match_format": "ODI",
            "match_date": "2026-10-23",
            "match_status": "Live",
            "team1_name": "South Africa",
            "team2_name": "New Zealand",
            "venue_name": "SuperSport Park, Centurion",
            "source": "API",
        }

        scorecard_payload = {
            "innings": [
                {
                    "innings_number": 1,
                    "batting_team": "South Africa",
                    "total_runs": 240,
                    "total_wickets": 4,
                    "overs_completed": 40.0,
                    "batting": [
                        {"player_name": "Quinton de Kock", "batting_position": 1, "runs_scored": 90, "balls_faced": 85, "fours": 9, "sixes": 2, "dismissal_type": "caught"},
                        {"player_name": "Temba Bavuma", "batting_position": 2, "runs_scored": 60, "balls_faced": 70, "fours": 5, "sixes": 1, "dismissal_type": "lbw"},
                    ],
                    "bowling": [
                        {"player_name": "Trent Boult", "overs_bowled": 10.0, "balls_bowled": 60, "maidens": 1, "runs_conceded": 45, "wickets_taken": 2},
                        {"player_name": "Matt Henry", "overs_bowled": 10.0, "balls_bowled": 60, "maidens": 0, "runs_conceded": 55, "wickets_taken": 1},
                    ],
                }
            ]
        }

        # Simulate 3 repeated poll cycles
        for _ in range(3):
            m_id = ingestion.ingest_match(match_payload, db_path=temp_db)
            inn_ids = ingestion.ingest_scorecard(m_id, scorecard_payload, db_path=temp_db)
            assert len(inn_ids) == 1

        with mgr.get_connection(temp_db) as conn:
            cur = conn.cursor()
            # Assert zero duplicate teams
            teams_count = cur.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
            assert teams_count == 2

            # Assert zero duplicate players
            players_count = cur.execute("SELECT COUNT(*) FROM players").fetchone()[0]
            assert players_count == 4

            # Assert zero duplicate matches
            matches_count = cur.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
            assert matches_count == 1

            # Assert zero duplicate innings
            innings_count = cur.execute("SELECT COUNT(*) FROM innings").fetchone()[0]
            assert innings_count == 1

            # Assert zero duplicate batting performances
            batting_count = cur.execute("SELECT COUNT(*) FROM batting_performances").fetchone()[0]
            assert batting_count == 2

            # Assert zero duplicate bowling performances
            bowling_count = cur.execute("SELECT COUNT(*) FROM bowling_performances").fetchone()[0]
            assert bowling_count == 2

    def test_batting_position_swap_handles_unique_constraint_cleanly(self, temp_db: Path) -> None:
        """Verifies that when batting order swaps between polling cycles,
        ingest_scorecard handles it without UNIQUE(innings_id, batting_position) violation."""
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)

        match_payload = {
            "match_desc": "Position Swap Test Match",
            "match_format": "T20I",
            "match_date": "2026-10-23",
            "match_status": "Live",
            "team1_name": "India",
            "team2_name": "Australia",
            "venue_name": "Wankhede Stadium, Mumbai",
            "source": "API",
        }
        m_id = ingestion.ingest_match(match_payload, db_path=temp_db)

        # Poll 1: Rohit Sharma at Pos 1, Shubman Gill at Pos 2
        sc1 = {
            "innings": [
                {
                    "innings_number": 1,
                    "batting_team": "India",
                    "total_runs": 40,
                    "total_wickets": 0,
                    "overs_completed": 4.0,
                    "batting": [
                        {"player_name": "Rohit Sharma", "batting_position": 1, "runs_scored": 25, "balls_faced": 14, "dismissal_type": "not out", "is_not_out": 1},
                        {"player_name": "Shubman Gill", "batting_position": 2, "runs_scored": 15, "balls_faced": 10, "dismissal_type": "not out", "is_not_out": 1},
                    ],
                    "bowling": [],
                }
            ]
        }
        ingestion.ingest_scorecard(m_id, sc1, db_path=temp_db)

        # Poll 2: Revised batting order swaps positions: Gill is Pos 1, Rohit is Pos 2
        sc2 = {
            "innings": [
                {
                    "innings_number": 1,
                    "batting_team": "India",
                    "total_runs": 60,
                    "total_wickets": 0,
                    "overs_completed": 6.0,
                    "batting": [
                        {"player_name": "Shubman Gill", "batting_position": 1, "runs_scored": 25, "balls_faced": 18, "dismissal_type": "not out", "is_not_out": 1},
                        {"player_name": "Rohit Sharma", "batting_position": 2, "runs_scored": 35, "balls_faced": 18, "dismissal_type": "not out", "is_not_out": 1},
                    ],
                    "bowling": [],
                }
            ]
        }
        # Ingestion must succeed without IntegrityError
        ingestion.ingest_scorecard(m_id, sc2, db_path=temp_db)

        with mgr.get_connection(temp_db) as conn:
            cur = conn.cursor()
            rows = cur.execute("SELECT p.full_name, bp.batting_position FROM batting_performances bp JOIN players p ON bp.player_id = p.player_id ORDER BY bp.batting_position ASC").fetchall()
            assert len(rows) == 2
            assert rows[0]["full_name"] == "Shubman Gill"
            assert rows[0]["batting_position"] == 1
            assert rows[1]["full_name"] == "Rohit Sharma"
            assert rows[1]["batting_position"] == 2

    def test_incomplete_payload_cannot_downgrade_completed_match(self, temp_db: Path) -> None:
        """Verifies that an incomplete API payload cannot revert a Completed match to Upcoming."""
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)

        complete_payload = {
            "match_desc": "India vs Australia, Final",
            "match_format": "ODI",
            "match_date": "2026-10-23",
            "match_status": "Completed",
            "team1_name": "India",
            "team2_name": "Australia",
            "venue_name": "Narendra Modi Stadium, Ahmedabad",
            "winning_team_name": "India",
            "win_margin": 6,
            "win_type": "wickets",
            "source": "API",
        }
        m_id = ingestion.ingest_match(complete_payload, db_path=temp_db)

        # Incomplete payload stub with Upcoming status and missing outcome
        incomplete_stub = {
            "match_desc": "India vs Australia, Final",
            "match_format": "ODI",
            "match_date": "2026-10-23",
            "match_status": "Upcoming",
            "team1_name": "India",
            "team2_name": "Australia",
            "venue_name": "Narendra Modi Stadium, Ahmedabad",
            "source": "API",
        }
        ingestion.ingest_match(incomplete_stub, db_path=temp_db)

        with mgr.get_connection(temp_db) as conn:
            cur = conn.cursor()
            m_row = cur.execute("SELECT match_status, winning_team_id, win_margin, win_type FROM matches WHERE match_id = ?", (m_id,)).fetchone()
            # Status must NOT be downgraded to Upcoming
            assert m_row["match_status"] == "Completed"
            # Outcome must NOT be cleared to None
            assert m_row["win_margin"] == 6
            assert m_row["win_type"] == "wickets"
            assert m_row["winning_team_id"] is not None

    def test_incomplete_scorecard_payload_cannot_overwrite_valid_innings(self, temp_db: Path) -> None:
        """Verifies that an empty/incomplete scorecard payload does not wipe valid existing innings."""
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)

        match_payload = {
            "match_desc": "Incomplete Payload Test",
            "match_format": "ODI",
            "match_date": "2026-10-23",
            "match_status": "Live",
            "team1_name": "England",
            "team2_name": "Pakistan",
            "venue_name": "Lord's, London",
            "source": "API",
        }
        m_id = ingestion.ingest_match(match_payload, db_path=temp_db)

        valid_scorecard = {
            "innings": [
                {
                    "innings_number": 1,
                    "batting_team": "England",
                    "total_runs": 280,
                    "total_wickets": 6,
                    "overs_completed": 50.0,
                    "batting": [{"player_name": "Ben Stokes", "batting_position": 1, "runs_scored": 80, "balls_faced": 75, "dismissal_type": "caught"}],
                    "bowling": [{"player_name": "Shaheen Afridi", "overs_bowled": 10.0, "balls_bowled": 60, "runs_conceded": 50, "wickets_taken": 2}],
                }
            ]
        }
        ingestion.ingest_scorecard(m_id, valid_scorecard, db_path=temp_db)

        # Incomplete/empty scorecard payload
        empty_stub = {
            "innings": [
                {
                    "innings_number": 1,
                    "batting_team": "England",
                    "total_runs": 0,
                    "total_wickets": 0,
                    "overs_completed": 0.0,
                    "batting": [],
                    "bowling": [],
                }
            ]
        }
        ingestion.ingest_scorecard(m_id, empty_stub, db_path=temp_db)

        with mgr.get_connection(temp_db) as conn:
            cur = conn.cursor()
            inn_row = cur.execute("SELECT total_runs, total_wickets, overs_completed FROM innings WHERE match_id = ?", (m_id,)).fetchone()
            # Verified: existing data preserved
            assert inn_row["total_runs"] == 280
            assert inn_row["total_wickets"] == 6
            assert inn_row["overs_completed"] == 50.0

            bat_count = cur.execute("SELECT COUNT(*) FROM batting_performances WHERE innings_id = (SELECT innings_id FROM innings WHERE match_id = ?)", (m_id,)).fetchone()[0]
            assert bat_count == 1

    def test_match_outcome_parsing_and_persistence(self, temp_db: Path) -> None:
        """Verifies parsing of match outcomes and persistence into winning_team_id, win_margin, win_type."""
        # 1. Wickets victory
        out1 = parse_match_outcome("India won by 6 wkts", "India", "Australia")
        assert out1["winning_team_name"] == "India"
        assert out1["win_margin"] == 6
        assert out1["win_type"] == "wickets"

        # 2. Runs victory
        out2 = parse_match_outcome("Australia won by 45 runs", "India", "Australia")
        assert out2["winning_team_name"] == "Australia"
        assert out2["win_margin"] == 45
        assert out2["win_type"] == "runs"

        # 3. Tied match
        out3 = parse_match_outcome("Match tied", "India", "Australia")
        assert out3["win_type"] == "tie"
        assert out3["win_margin"] is None

        # 4. Ingestion into SQLite
        mgr = DBConnectionManager(temp_db)
        ingestion = IngestionService(connection_manager=mgr)
        raw_match = {
            "name": "India vs Australia, 3rd ODI",
            "matchType": "odi",
            "dateTimeGMT": "2026-10-23T09:00:00",
            "status": "India won by 6 wkts",
            "teams": ["India", "Australia"],
            "venue": "Eden Gardens, Kolkata",
        }
        parsed = CricketDataParser.parse_match(raw_match)
        m_id = ingestion.ingest_match(parsed, db_path=temp_db)

        with mgr.get_connection(temp_db) as conn:
            cur = conn.cursor()
            row = cur.execute("SELECT m.win_margin, m.win_type, t.team_name FROM matches m JOIN teams t ON m.winning_team_id = t.team_id WHERE m.match_id = ?", (m_id,)).fetchone()
            assert row["win_margin"] == 6
            assert row["win_type"] == "wickets"
            assert row["team_name"] == "India"

