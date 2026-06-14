"""Output helpers: write processed DataFrames to CSV and JSON."""

import json

import pandas as pd

from . import config


def save(df: pd.DataFrame, name: str, raw: dict | list | None = None) -> None:
    """Write a DataFrame to data/processed as both CSV and JSON.

    If ``raw`` is given, also dump it to data/raw/<name>.json for debugging.
    """
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = config.PROCESSED_DIR / f"{name}.csv"
    json_path = config.PROCESSED_DIR / f"{name}.json"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
    print(f"  wrote {len(df):>4} rows -> {csv_path.relative_to(config.PROJECT_ROOT)}")

    if raw is not None:
        config.RAW_DIR.mkdir(parents=True, exist_ok=True)
        with open(config.RAW_DIR / f"{name}.json", "w") as handle:
            json.dump(raw, handle, ensure_ascii=False, indent=2)
