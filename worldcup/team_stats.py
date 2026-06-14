"""Fetch aggregate team statistics from the FIFA data hub (fdh-api)."""

import re

import pandas as pd
import requests

from . import config, storage, teams
from .fetch import get_json

_CAMEL = re.compile(r"(?<=[a-z0-9])([A-Z])")


def _snake(stat: str) -> str:
    return _CAMEL.sub(r"_\1", stat).lower()


def fetch_team(id_team: str) -> list | None:
    url = f"{config.FDH_BASE}/stats/season/{config.SEASON_ID}/team/{id_team}.json"
    try:
        return get_json(url)
    except requests.exceptions.HTTPError:
        return None


def transform(rows: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    long_df = pd.DataFrame(rows)
    wide = (
        long_df.pivot_table(
            index=["team_name", "id_team"], columns="stat", values="value"
        )
        .reset_index()
        .rename_axis(columns=None)
    )
    return long_df, wide


def run(teams_df: pd.DataFrame | None = None) -> pd.DataFrame:
    print("team stats:")
    if teams_df is None:
        teams_df = teams.run()

    rows: list[dict] = []
    for id_team, name in zip(teams_df["id_team"], teams_df["team_name"]):
        stats = fetch_team(str(id_team))
        if not stats:
            print(f"  {name}: no stats yet")
            continue
        for stat, value, *_ in stats:
            rows.append(
                {
                    "id_team": id_team,
                    "team_name": name,
                    "stat": _snake(stat),
                    "value": value,
                }
            )
        print(f"  {name}: {len(stats)} stats")

    if not rows:
        print("  no team stats available yet; skipping")
        return pd.DataFrame()

    long_df, wide = transform(rows)
    storage.save(long_df, "team_stats")
    storage.save(wide, "team_stats_wide")
    return long_df


if __name__ == "__main__":
    run()
