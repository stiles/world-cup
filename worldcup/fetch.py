"""HTTP helpers with retry logic and FIFA-specific fetchers."""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from . import config


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "world-cup-data/0.1 (personal project)"})
    return session


def get_json(url: str, params: dict | None = None, timeout: int = 30):
    """GET a URL and return parsed JSON, raising on HTTP errors."""
    response = _session().get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_calendar_matches() -> list[dict]:
    """Return the full list of match records for the season.

    A single request with a large count returns all matches (104 in 2026), so
    no pagination is needed. We assert this to fail loudly if FIFA ever caps the
    page size and starts returning a ContinuationToken.
    """
    url = f"{config.API_BASE}/calendar/matches"
    params = {
        "language": config.LANGUAGE,
        "count": 1000,
        "idSeason": config.SEASON_ID,
    }
    data = get_json(url, params=params)
    results = data.get("Results", [])
    if not results:
        raise RuntimeError(f"No matches returned for season {config.SEASON_ID}")
    if data.get("ContinuationToken"):
        raise RuntimeError(
            "Calendar response was paginated (ContinuationToken present). "
            "Increase count or add pagination handling in fetch.get_calendar_matches()."
        )
    return results
