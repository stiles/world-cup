"""Fetch per-player statistics from the FIFA data hub (fdh-api)."""

import re

import pandas as pd

from . import config, players, storage
from .fetch import get_json

_CAMEL = re.compile(r"(?<=[a-z0-9])([A-Z])")


def _snake(stat: str) -> str:
    return _CAMEL.sub(r"_\1", stat).lower()


def fetch() -> dict:
    url = f"{config.FDH_BASE}/stats/season/{config.SEASON_ID}/players.json"
    return get_json(url)


def transform(data: dict, players_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for player_id, stats in data.items():
        for stat, value, *_ in stats:
            rows.append(
                {"player_id": player_id, "stat": _snake(stat), "value": value}
            )
    long_df = pd.DataFrame(rows)

    lookup = players_df[["player_id", "name", "team_name", "position_desc"]].copy()
    lookup["player_id"] = lookup["player_id"].astype(str)
    long_df["player_id"] = long_df["player_id"].astype(str)
    return long_df.merge(lookup, on="player_id", how="left")


def run(players_df: pd.DataFrame | None = None) -> pd.DataFrame:
    print("player stats:")
    if players_df is None:
        players_df = players.run()

    data = fetch()
    if not data:
        print("  no player stats available yet; skipping")
        return pd.DataFrame()

    long_df = transform(data, players_df)
    storage.save(long_df, "player_stats")
    print(f"  {long_df['player_id'].nunique()} players with stats")
    return long_df


if __name__ == "__main__":
    run()
