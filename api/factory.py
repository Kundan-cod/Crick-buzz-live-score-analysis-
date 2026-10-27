"""Factory module for instantiating the active cricket API client.

Inspects environment configuration and creates the configured client
(CricketDataClient or CricbuzzRapidAPIClient) with cached settings.
"""

import os
from typing import Optional

from api.base_client import BaseCricketClient
from api.cricketdata_client import CricketDataClient
from api.cricbuzz_client import CricbuzzRapidAPIClient
from config import settings


def get_cricket_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    offline_mode: Optional[bool] = None,
) -> BaseCricketClient:
    """Instantiates and returns the configured cricket API client.
    
    Args:
        provider: 'cricketdata' (recommended free tier) or 'rapidapi' / 'cricbuzz'.
                  Defaults to environment variable CRICKET_API_PROVIDER or 'cricketdata'.
        api_key: Optional override for the provider API key.
        offline_mode: Optional boolean flag to enforce offline behavior. Defaults to settings.api.offline_mode.
    """
    selected_provider = (provider or os.getenv("CRICKET_API_PROVIDER", "cricketdata")).strip().lower()
    is_offline = settings.api.offline_mode if offline_mode is None else offline_mode

    if selected_provider in ("rapidapi", "cricbuzz"):
        key = api_key or os.getenv("RAPIDAPI_KEY") or os.getenv("CRICBUZZ_API_KEY")
        host = os.getenv("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")
        return CricbuzzRapidAPIClient(
            api_key=key,
            api_host=host,
            timeout_seconds=settings.api.timeout_seconds,
            offline_mode=is_offline,
        )

    # Default: CricketData.org (free lifetime tier, zero payment details required)
    key = api_key or os.getenv("CRICKETDATA_API_KEY") or os.getenv("CRICBUZZ_API_KEY")
    return CricketDataClient(
        api_key=key,
        timeout_seconds=settings.api.timeout_seconds,
        offline_mode=is_offline,
    )
