"""Concrete API client implementation for CricketData.org (formerly CricAPI).

Connects to CricketData.org v1 REST endpoints to retrieve live scores,
match schedules, series information, and detailed scorecards under the free tier.
Features safe credential handling, in-memory caching, and quota protection.
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

logger = logging.getLogger("cricbuzz.api.cricketdata")


class CricketDataClient(BaseCricketClient):
    """Client for CricketData.org (api.cricapi.com).
    
    Attributes:
        BASE_URL: 'https://api.cricapi.com/v1'
        provider_name: 'CricketData.org'
        is_direct_cricbuzz: False (Independent aggregator, ~30-60s broadcast latency)
    """

    BASE_URL = "https://api.cricapi.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
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
        self.hits_today: Optional[int] = None
        self.hits_limit: Optional[int] = None

    @property
    def provider_name(self) -> str:
        return "CricketData.org"

    @property
    def is_direct_cricbuzz(self) -> bool:
        return False

    def get_quota_status(self) -> Dict[str, Any]:
        """Returns current daily API quota usage telemetry parsed from provider responses."""
        remaining = None
        if self.hits_limit is not None and self.hits_today is not None:
            remaining = max(0, self.hits_limit - self.hits_today)
        return {
            "hits_today": self.hits_today,
            "hits_limit": self.hits_limit,
            "hits_remaining": remaining,
        }

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes an authenticated HTTP GET request against the provider."""
        if self.offline_mode:
            raise CricketAPIError(
                "Live network requests are disabled because OFFLINE_MODE=True is active. "
                "To enable real network requests, set OFFLINE_MODE=False in your environment."
            )

        if not self.api_key or self.api_key.strip() in (
            "",
            "your_api_key_here",
            "your_cricketdata_api_key_here",
            "PLACEHOLDER",
            "your_rapidapi_key_here",
        ):
            raise MissingAPIKeyError(
                "CricketData.org API key is missing. Register a free account at "
                "https://cricketdata.org to obtain an API key (100 free hits/day, no credit card required)."
            )

        query_params = {"apikey": self.api_key.strip()}
        if params:
            query_params.update(params)

        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(query_params)}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Cricbuzz-LiveStats/1.0 (Educational/Student Project)",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                status_code = response.getcode()
                raw_bytes = response.read()
                raw_text = raw_bytes.decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise APIAuthenticationError(f"Authentication failed: Invalid CricketData API key (HTTP {exc.code}).") from exc
            if exc.code == 429:
                raise RateLimitExceededError("CricketData.org daily rate limit exceeded (HTTP 429).") from exc
            if exc.code == 500 and "match_scorecard" in endpoint:
                raise APIConnectionError(
                    f"Scorecard data is not currently available from CricketData.org for this match (HTTP 500). "
                    "This usually occurs when a match has not started yet or the provider has not published ball-by-ball commentary."
                ) from exc
            raise APIConnectionError(f"HTTP error {exc.code} communicating with CricketData.org: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise APIConnectionError(f"Network error connecting to CricketData.org: {exc.reason}") from exc
        except Exception as exc:
            raise APIConnectionError(f"Unexpected connection failure: {exc}") from exc

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise InvalidAPIResponseError(f"Invalid JSON returned by CricketData.org: {exc}") from exc

        # Check domain status indicator in CricketData.org responses
        if isinstance(data, dict):
            # Parse and store quota telemetry from provider info block
            info = data.get("info")
            if isinstance(info, dict):
                self.hits_today = info.get("hitsToday")
                self.hits_limit = info.get("hitsLimit")

            status = data.get("status", "").lower()
            if status == "failure":
                reason = data.get("reason", "").lower()
                if "limit" in reason or "quota" in reason or "hit" in reason or "exceeded" in reason:
                    raise RateLimitExceededError(f"CricketData quota exceeded: {data.get('reason')}")
                if "key" in reason or "auth" in reason:
                    raise APIAuthenticationError(f"CricketData auth failed: {data.get('reason')}")
                raise InvalidAPIResponseError(f"CricketData returned failure: {data.get('reason')}")

        return data

    def get_live_matches(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch ongoing and recently updated cricket fixtures with 60s caching."""
        cache_key = "current_matches"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Serving current matches from in-memory TTL cache.")
                return cached

        payload = self._make_request("currentMatches", {"offset": 0})
        matches = payload.get("data", [])
        self.cache.set(cache_key, matches)
        return matches

    def get_match_scorecard(self, external_match_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch detailed innings scorecards for a specific match with caching."""
        if not external_match_id:
            raise ValueError("external_match_id is required.")

        cache_key = f"scorecard_{external_match_id}"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Serving scorecard for %s from cache.", external_match_id)
                return cached

        payload = self._make_request("match_scorecard", {"id": external_match_id, "offset": 0})
        data = payload.get("data", {})
        self.cache.set(cache_key, data)
        return data

    def get_series(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch active series list with caching."""
        cache_key = "series_list"
        if not force_refresh:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        payload = self._make_request("series", {"offset": 0})
        series_list = payload.get("data", [])
        self.cache.set(cache_key, series_list)
        return series_list

    def test_connection(self) -> Dict[str, Any]:
        """Performs a non-destructive verification check against CricketData.org."""
        if self.offline_mode:
            return {
                "success": False,
                "provider": self.provider_name,
                "is_direct_cricbuzz": self.is_direct_cricbuzz,
                "error_type": "OfflineModeActive",
                "message": "Connection test blocked: OFFLINE_MODE=True is active. Network requests are safely disabled.",
                "cached_items": self.cache.size(),
                "quota": self.get_quota_status(),
            }

        try:
            matches = self.get_live_matches(force_refresh=True)
            return {
                "success": True,
                "provider": self.provider_name,
                "is_direct_cricbuzz": self.is_direct_cricbuzz,
                "message": f"Connection verified successfully. Retrieved {len(matches)} current fixtures.",
                "cached_items": self.cache.size(),
                "quota": self.get_quota_status(),
            }
        except CricketAPIError as exc:
            return {
                "success": False,
                "provider": self.provider_name,
                "is_direct_cricbuzz": self.is_direct_cricbuzz,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
                "quota": self.get_quota_status(),
            }
