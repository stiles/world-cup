"""Output helpers: write processed DataFrames to CSV and JSON."""

import json

import pandas as pd

from . import config


def save(df: pd.DataFrame, name: str, subdir: str | None = None,
         raw: dict | list | None = None) -> None:
    """Write a DataFrame to data/processed as both CSV and JSON.

    ``subdir`` nests the output under data/processed/<subdir> (e.g. a year).
    If ``raw`` is given, also dump it to data/raw[/<subdir>]/<name>.json.
    """
    out_dir = config.PROCESSED_DIR / subdir if subdir else config.PROCESSED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{name}.csv"
    json_path = out_dir / f"{name}.json"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)
    print(f"  wrote {len(df):>4} rows -> {csv_path.relative_to(config.PROJECT_ROOT)}")

    if raw is not None:
        raw_dir = config.RAW_DIR / subdir if subdir else config.RAW_DIR
        raw_dir.mkdir(parents=True, exist_ok=True)
        with open(raw_dir / f"{name}.json", "w") as handle:
            json.dump(raw, handle, ensure_ascii=False, indent=2)
