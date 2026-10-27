"""Base abstract client and caching layer for external cricket data APIs.

Defines the provider-independent interface, standardized data access methods,
in-memory TTL response caching, and domain exception classes.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("cricbuzz.api")


# ------------------------------------------------------------------------------
# Custom API Exceptions
# ------------------------------------------------------------------------------

class CricketAPIError(Exception):
    """Base exception for all cricket API communication and ingestion errors."""


class MissingAPIKeyError(CricketAPIError):
    """Raised when an API request is attempted without a configured API key."""


class APIAuthenticationError(CricketAPIError):
    """Raised when the provider rejects credentials (HTTP 401 or 403)."""


class RateLimitExceededError(CricketAPIError):
    """Raised when daily quota or per-minute rate limits are exhausted (HTTP 429)."""


class APIConnectionError(CricketAPIError):
    """Raised when network connectivity fails or requests time out."""


class InvalidAPIResponseError(CricketAPIError):
    """Raised when the API returns malformed JSON or an error payload."""


# ------------------------------------------------------------------------------
# In-Memory TTL Response Cache
# ------------------------------------------------------------------------------

class SimpleTTLCache:
    """Thread-safe, lightweight in-memory cache with Time-To-Live (TTL) expiration.
    
    Prevents burning through limited daily quotas (e.g. 100 hits/day) during rapid
    page refreshes or multi-component dashboard renders.
    """

    def __init__(self, default_ttl_seconds: int = 60) -> None:
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Tuple[datetime, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value if present and not expired."""
        if key not in self._cache:
            return None
        timestamp, value = self._cache[key]
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        if age > self.default_ttl:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store value in cache with current timestamp."""
        self._cache[key] = (datetime.now(timezone.utc), value)

    def clear(self) -> None:
        """Purge all cached entries."""
        self._cache.clear()

    def size(self) -> int:
        """Return count of active entries."""
        return len(self._cache)


# ------------------------------------------------------------------------------
# Base Abstract Cricket Client
# ------------------------------------------------------------------------------

class BaseCricketClient(ABC):
    """Abstract base class defining the provider-independent cricket API contract."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout_seconds: int = 10,
        cache_ttl_seconds: int = 60,
        offline_mode: bool = False,
    ) -> None:
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.cache = SimpleTTLCache(default_ttl_seconds=cache_ttl_seconds)
        self.offline_mode = offline_mode

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier (e.g., 'CricketData.org', 'RapidAPI Cricbuzz')."""

    @property
    @abstractmethod
    def is_direct_cricbuzz(self) -> bool:
        """Indicates whether data originates directly from Cricbuzz or an independent aggregator."""

    @abstractmethod
    def get_live_matches(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch ongoing and recently completed matches."""

    @abstractmethod
    def get_match_scorecard(self, external_match_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Fetch granular innings scorecards for a specific fixture."""

    @abstractmethod
    def get_series(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch ongoing and recent tournaments/series."""

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Perform a non-destructive verification check against provider endpoints."""
