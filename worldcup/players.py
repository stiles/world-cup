"""Fetch squad rosters for every team."""

import pandas as pd

from . import config, storage, teams
from .fetch import get_json


def fetch_squad(id_team: str) -> list[dict]:
    url = f"{config.API_BASE}/teams/{id_team}/squad"
    params = {
        "idCompetition": config.COMPETITION_ID,
        "idSeason": config.SEASON_ID,
        "language": config.LANGUAGE,
    }
    return get_json(url, params=params).get("Players", [])


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


def transform(records: list[dict], teams_df: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(records)

    df["dob"] = pd.to_datetime(df["birth_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    today = pd.Timestamp("today").normalize()
    df["age"] = (
        (today - pd.to_datetime(df["dob"], errors="coerce")).dt.days / 365.25
    ).round(1)
    df = df.drop(columns=["birth_date"])

    df["position_desc"] = df["position"].map(config.POSITIONS)

    team_name = dict(zip(teams_df["id_team"].astype(str), teams_df["team_name"]))
    team_abbr = dict(zip(teams_df["id_team"].astype(str), teams_df["abbreviation"]))
    df["team_name"] = df["id_team"].astype(str).map(team_name)
    df["team_abbr"] = df["id_team"].astype(str).map(team_abbr)

    return df.sort_values(["team_name", "jersey_number"]).reset_index(drop=True)


def run(teams_df: pd.DataFrame | None = None) -> pd.DataFrame:
    print("players:")
    if teams_df is None:
        teams_df = teams.run()

    records: list[dict] = []
    for id_team, name in zip(teams_df["id_team"], teams_df["team_name"]):
        squad = fetch_squad(str(id_team))
        records.extend(_player_record(p) for p in squad)
        print(f"  {name}: {len(squad)} players")

    df = transform(records, teams_df)
    storage.save(df, "players")
    return df


if __name__ == "__main__":
    run()
