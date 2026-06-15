"""Build detailed match results: scores, winner, possession, weather, venue."""

import pandas as pd

from . import storage
from .fetch import get_calendar_matches


def _description(value) -> str | None:
    if isinstance(value, list) and value:
        return value[0].get("Description")
    return None


def _row(match: dict) -> dict:
    home = match.get("Home") or {}
    away = match.get("Away") or {}
    weather = match.get("Weather") or {}
    stadium = match.get("Stadium") or {}
    possession = match.get("BallPossession") or {}

    winner_id = match.get("Winner")
    winner_abbr = None
    if winner_id == home.get("IdTeam"):
        winner_abbr = home.get("Abbreviation")
    elif winner_id == away.get("IdTeam"):
        winner_abbr = away.get("Abbreviation")

    date_utc = pd.to_datetime(match.get("Date"), errors="coerce", utc=True)

    return {
        "id_match": match.get("IdMatch"),
        "match_number": match.get("MatchNumber"),
        "stage": _description(match.get("StageName")),
        "group": _description(match.get("GroupName")),
        "date_utc": date_utc.strftime("%Y-%m-%d") if pd.notna(date_utc) else None,
        "match_status": match.get("MatchStatus"),
        "result_type": match.get("ResultType"),
        "home_team": home.get("Abbreviation"),
        "away_team": away.get("Abbreviation"),
        "home_name": home.get("ShortClubName"),
        "away_name": away.get("ShortClubName"),
        "home_score": home.get("Score"),
        "away_score": away.get("Score"),
        "home_penalties": match.get("HomeTeamPenaltyScore"),
        "away_penalties": match.get("AwayTeamPenaltyScore"),
        "winner": winner_abbr,
        "home_tactics": home.get("Tactics"),
        "away_tactics": away.get("Tactics"),
        "home_possession": possession.get("OverallHome"),
        "away_possession": possession.get("OverallAway"),
        "attendance": match.get("Attendance"),
        "stadium": _description(stadium.get("Name")),
        "humidity": weather.get("Humidity"),
        "temperature": weather.get("Temperature"),
        "wind_speed": weather.get("WindSpeed"),
        "weather": _description(weather.get("TypeLocalized")),
    }


def transform(matches: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame([_row(m) for m in matches])
    for col in ("home_possession", "away_possession"):
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)
    return df.sort_values("date_utc").reset_index(drop=True)


def run(season: str | None = None, subdir: str | None = None) -> pd.DataFrame:
    print("results:")
    matches = get_calendar_matches(season)
    df = transform(matches)
    storage.save(df, "results", subdir=subdir)
    return df


if __name__ == "__main__":
    run()
