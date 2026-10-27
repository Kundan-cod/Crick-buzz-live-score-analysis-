"""Concrete API client implementation for Cricbuzz via RapidAPI.

Provides connectivity to RapidAPI's Cricbuzz endpoints for users who choose
to supply a RapidAPI key.
Features header management, TTL response caching, and quota protection.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request

from api.base_client import (
    APIAuthenticationError,
    APIConnectionError,
    BaseCricketClient,
    CricketAPIError,
    InvalidAPIResponseError,
    MissingAPIKeyError,
    RateLimitExceededError,
)

logger = logging.getLogger("cricbuzz.api.rapidapi")


class CricbuzzRapidAPIClient(BaseCricketClient):
    """Client for RapidAPI Cricbuzz endpoint (cricbuzz-cricket.p.rapidapi.com).
    
    Attributes:
        BASE_URL: 'https://cricbuzz-cricket.p.rapidapi.com'
        provider_name: 'RapidAPI Cricbuzz'
        is_direct_cricbuzz: True (Direct Cricbuzz feed via RapidAPI proxy)
    """

    BASE_URL = "https://cricbuzz-cricket.p.rapidapi.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_host: str = "cricbuzz-cricket.p.rapidapi.com",
        timeout_seconds: int = 10,
        cache_ttl_seconds: int = 60,
        offline_mode: bool = False,
    ) -> None:
        super().__init__(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            offline_mode=offline_mode,
        )
        self.api_host = api_host

    @property
    def provider_name(self) -> str:
        return "RapidAPI Cricbuzz"

    @property
    def is_direct_cricbuzz(self) -> bool:
        return True

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes an authenticated HTTP GET request with RapidAPI headers."""
        if self.offline_mode:
            raise CricketAPIError(
                "Live network requests are disabled because OFFLINE_MODE=True is active. "
                "To enable real network requests, set OFFLINE_MODE=False in your environment."
            )

        if not self.api_key or self.api_key.strip() in ("", "your_api_key_here", "PLACEHOLDER"):
            raise MissingAPIKeyError(
                "RapidAPI Cricbuzz key is missing. Note: RapidAPI Basic plans require a credit card on file. "
                "For a zero-cost option without payment details, configure CRICKETDATA_API_KEY instead."
            )

        query_str = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}{query_str}"

        req = urllib.request.Request(
            url,
            headers={
                "X-RapidAPI-Key": self.api_key.strip(),
                "X-RapidAPI-Host": self.api_host,
                "Accept": "application/json",
                "User-Agent": "Cricbuzz-LiveStats/1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw_bytes = response.read()
                raw_text = raw_bytes.decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise APIAuthenticationError(f"RapidAPI authentication failed: Invalid key or unauthorized access (HTTP {exc.code}).") from exc
            if exc.code == 429:
                raise RateLimitExceededError("RapidAPI rate limit or monthly quota exceeded (HTTP 429).") from exc
            raise APIConnectionError(f"HTTP error {exc.code} communicating with RapidAPI: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise APIConnectionError(f"Network error connecting to RapidAPI: {exc.reason}") from exc
        except Exception as exc:
            raise APIConnectionError(f"Unexpected RapidAPI connection failure: {exc}") from exc

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise InvalidAPIResponseError(f"Invalid JSON returned by RapidAPI: {exc}") from exc

    def get_live_matches(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch live matches list from RapidAPI."""
        cache_key = "rapidapi_live_matches"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        payload = self._make_request("matches/v1/live")
        matches = payload.get("typeMatches", [])
        self.cache.set(cache_key, matches)
        return matches

    def get_match_scorecard(self, external_match_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch detailed match scorecard from RapidAPI."""
        if not external_match_id:
            raise ValueError("external_match_id is required.")

        cache_key = f"rapidapi_scorecard_{external_match_id}"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        payload = self._make_request(f"mcenter/v1/{external_match_id}/scard")
        self.cache.set(cache_key, payload)
        return payload

    def get_series(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch series list from RapidAPI."""
        cache_key = "rapidapi_series"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        payload = self._make_request("series/v1/international")
        series_list = payload.get("seriesList", [])
        self.cache.set(cache_key, series_list)
        return series_list

    def test_connection(self) -> Dict[str, Any]:
        """Verifies RapidAPI connectivity."""
        try:
            matches = self.get_live_matches(force_refresh=True)
            return {
                "success": True,
                "provider": self.provider_name,
                "is_direct_cricbuzz": self.is_direct_cricbuzz,
                "message": f"Connection verified. Retrieved {len(matches)} match groupings.",
            }
        except CricketAPIError as exc:
            return {
                "success": False,
                "provider": self.provider_name,
                "is_direct_cricbuzz": self.is_direct_cricbuzz,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
            }
