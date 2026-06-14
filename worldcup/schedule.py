"""Build the match schedule from the season calendar."""

import pandas as pd

from . import storage
from .fetch import get_calendar_matches


def _description(value) -> str | None:
    if isinstance(value, list) and value:
        return value[0].get("Description")
    return None


def _side_abbr(side) -> str | None:
    if isinstance(side, dict):
        return side.get("Abbreviation")
    return None


def transform(matches: list[dict]) -> pd.DataFrame:
    rows = []
    for match in matches:
        date_utc = pd.to_datetime(match.get("Date"), errors="coerce", utc=True)
        local = pd.to_datetime(match.get("LocalDate"), errors="coerce")
        rows.append(
            {
                "id_match": match.get("IdMatch"),
                "match_number": match.get("MatchNumber"),
                "stage": _description(match.get("StageName")),
                "group": _description(match.get("GroupName")),
                "home_team": _side_abbr(match.get("Home")),
                "away_team": _side_abbr(match.get("Away")),
                "date_utc": date_utc.strftime("%Y-%m-%d") if pd.notna(date_utc) else None,
                "time_utc": date_utc.strftime("%H:%M") if pd.notna(date_utc) else None,
                "local_date": local.strftime("%Y-%m-%d") if pd.notna(local) else None,
                "local_time": local.strftime("%H:%M") if pd.notna(local) else None,
            }
        )
    df = pd.DataFrame(rows)
    return df.sort_values("date_utc").reset_index(drop=True)


def run() -> pd.DataFrame:
    print("schedule:")
    matches = get_calendar_matches()
    df = transform(matches)
    storage.save(df, "schedule")
    return df


if __name__ == "__main__":
    run()
