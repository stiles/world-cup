"""Profile each team's squad: average age, height, weight and size.

Reads data/processed/players.csv (run `python -m worldcup players` first)
and prints a per-team summary plus a few leaderboards.

    python examples/team_profiles.py
"""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAYERS_CSV = PROJECT_ROOT / "data" / "processed" / "players.csv"


def load_players() -> pd.DataFrame:
    if not PLAYERS_CSV.exists():
        raise SystemExit(
            f"Missing {PLAYERS_CSV}. Run `python -m worldcup players` first."
        )
    return pd.read_csv(PLAYERS_CSV)


POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Striker"]


def height_by_position(players: pd.DataFrame) -> pd.DataFrame:
    """Average height (cm) per team, split out by position."""
    pivot = (
        players.pivot_table(
            index="team_name",
            columns="position_desc",
            values="height",
            aggfunc="mean",
        )
        .round(1)
    )
    cols = [p for p in POSITION_ORDER if p in pivot.columns]
    return pivot[cols].rename_axis(columns=None).reset_index()


def team_profiles(players: pd.DataFrame) -> pd.DataFrame:
    profiles = (
        players.groupby("team_name")
        .agg(
            squad_size=("player_id", "count"),
            avg_age=("age", "mean"),
            avg_height=("height", "mean"),
            avg_weight=("weight", "mean"),
            youngest=("age", "min"),
            oldest=("age", "max"),
            tallest=("height", "max"),
        )
        .round(1)
        .reset_index()
    )
    return profiles.sort_values("avg_age", ascending=False).reset_index(drop=True)


def main() -> None:
    players = load_players()
    profiles = team_profiles(players)

    print(f"Squad profiles for {len(profiles)} teams\n")
    print(profiles.to_string(index=False))

    print("\nOldest squads (avg age):")
    print(profiles.nlargest(5, "avg_age")[["team_name", "avg_age"]].to_string(index=False))

    print("\nYoungest squads (avg age):")
    print(profiles.nsmallest(5, "avg_age")[["team_name", "avg_age"]].to_string(index=False))

    print("\nTallest squads (avg height, cm):")
    print(profiles.nlargest(5, "avg_height")[["team_name", "avg_height"]].to_string(index=False))

    by_position = height_by_position(players)
    print("\nAverage height by position (cm), tallest defenders first:")
    print(by_position.sort_values("Defender", ascending=False).to_string(index=False))

    print("\nLeague-wide average height by position (cm):")
    print(players.groupby("position_desc")["height"].mean().round(1).reindex(POSITION_ORDER).to_string())


if __name__ == "__main__":
    main()
