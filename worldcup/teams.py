"""Fetch the tournament's qualified teams."""

import pandas as pd

from . import config, storage
from .fetch import get_json


def fetch() -> list[dict]:
    url = f"{config.API_BASE}/competitions/teams/{config.SEASON_ID}"
    return get_json(url, params={"language": config.LANGUAGE})["Results"]


def _first_description(value) -> str | None:
    """Pull the Description from FIFA's [{'Locale':..,'Description':..}] lists."""
    if isinstance(value, list) and value:
        return value[0].get("Description")
    return None


def transform(results: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(results)
    out = pd.DataFrame(
        {
            "id_team": df["IdTeam"],
            "confederation": df["IdConfederation"],
            "team_name": df["Name"].apply(_first_description),
            "short_name": df["ShortClubName"],
            "abbreviation": df["Abbreviation"],
            "country_code": df["IdCountry"],
            "foundation_year": df.get("FoundationYear"),
        }
    )
    out["flag_url"] = (
        "https://api.fifa.com/api/v3/picture/flags-sq-4/" + out["abbreviation"]
    )
    return out.sort_values("team_name").reset_index(drop=True)


def run() -> pd.DataFrame:
    print("teams:")
    results = fetch()
    df = transform(results)
    storage.save(df, "teams", raw=results)
    return df


if __name__ == "__main__":
    run()
