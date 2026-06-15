"""Fetch squad rosters for every team."""

import pandas as pd
import requests

from . import config, seasons, storage, teams
from .fetch import get_json


def fetch_squad(id_team: str, season: str | None = None) -> list[dict]:
    season = season or config.SEASON_ID
    url = f"{config.API_BASE}/teams/{id_team}/squad"
    params = {
        "idCompetition": config.COMPETITION_ID,
        "idSeason": season,
        "language": config.LANGUAGE,
    }
    try:
        return get_json(url, params=params).get("Players", [])
    except requests.exceptions.HTTPError:
        # Older tournaments often have no squad data; treat as empty.
        return []


def _player_record(player: dict) -> dict:
    name = player.get("PlayerName") or [{}]
    picture = player.get("PlayerPicture") or {}
    return {
        "player_id": player.get("IdPlayer"),
        "name": (name[0].get("Description") or "").title(),
        "position": player.get("Position"),
        "jersey_number": player.get("JerseyNum"),
        "weight": player.get("Weight"),
        "height": player.get("Height"),
        "birth_date": player.get("BirthDate"),
        "country_code": player.get("IdCountry"),
        "id_team": player.get("IdTeam"),
        "picture_url": picture.get("PictureUrl"),
    }


def transform(records: list[dict], teams_df: pd.DataFrame,
              as_of: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(records)

    df["dob"] = pd.to_datetime(df["birth_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    # Age as of the tournament start (so historical editions aren't computed
    # against today's date); falls back to today if no reference is given.
    reference = pd.to_datetime(as_of) if as_of else pd.Timestamp("today").normalize()
    df["age"] = (
        (reference - pd.to_datetime(df["dob"], errors="coerce")).dt.days / 365.25
    ).round(1)
    df = df.drop(columns=["birth_date"])

    df["position_desc"] = df["position"].map(config.POSITIONS)

    team_name = dict(zip(teams_df["id_team"].astype(str), teams_df["team_name"]))
    team_abbr = dict(zip(teams_df["id_team"].astype(str), teams_df["abbreviation"]))
    df["team_name"] = df["id_team"].astype(str).map(team_name)
    df["team_abbr"] = df["id_team"].astype(str).map(team_abbr)

    return df.sort_values(["team_name", "jersey_number"]).reset_index(drop=True)


def run(teams_df: pd.DataFrame | None = None, season: str | None = None,
        subdir: str | None = None, as_of: str | None = None) -> pd.DataFrame:
    print("players:")
    season = season or config.SEASON_ID
    if as_of is None:
        as_of = seasons.season_start(season)
    if teams_df is None:
        teams_df = teams.run(season=season, subdir=subdir)

    records: list[dict] = []
    for id_team, name in zip(teams_df["id_team"], teams_df["team_name"]):
        squad = fetch_squad(str(id_team), season=season)
        records.extend(_player_record(p) for p in squad)
        print(f"  {name}: {len(squad)} players")

    if not records:
        print("  no squad data available for this season")
        return pd.DataFrame()

    df = transform(records, teams_df, as_of=as_of)
    storage.save(df, "players", subdir=subdir)
    return df


if __name__ == "__main__":
    run()
