"""Discover World Cup editions (year -> idSeason) from the FIFA API."""

import json

from . import config
from .fetch import get_json

SEASONS_CACHE = config.RAW_DIR / "seasons.json"


def _description(value) -> str | None:
    if isinstance(value, list) and value:
        return value[0].get("Description")
    return None


def fetch_seasons() -> list[dict]:
    url = f"{config.API_BASE}/seasons"
    params = {"idCompetition": config.COMPETITION_ID, "language": config.LANGUAGE, "count": 100}
    return get_json(url, params=params)["Results"]


def season_table(refresh: bool = False) -> list[dict]:
    """Return [{year, id_season, name}, ...] sorted by year, cached to disk."""
    if SEASONS_CACHE.exists() and not refresh:
        with open(SEASONS_CACHE) as handle:
            raw = json.load(handle)
    else:
        raw = fetch_seasons()
        config.RAW_DIR.mkdir(parents=True, exist_ok=True)
        with open(SEASONS_CACHE, "w") as handle:
            json.dump(raw, handle, ensure_ascii=False, indent=2)

    rows = []
    for s in raw:
        start = (s.get("StartDate") or "")[:4]
        rows.append({
            "year": int(start) if start.isdigit() else None,
            "id_season": s.get("IdSeason"),
            "name": _description(s.get("Name")),
        })
    return sorted((r for r in rows if r["year"]), key=lambda r: r["year"])


if __name__ == "__main__":
    for r in season_table():
        print(f"{r['year']}  idSeason={r['id_season']:<8} {r['name']}")
