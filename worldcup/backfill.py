"""Collect core data (teams, players, schedule, results) for every World Cup.

Writes per-edition files under data/processed/<year>/ and combined tables with a
`year` column under data/processed/all/. Past tournaments are static, so already
collected years are skipped unless --refresh is passed.

    python -m worldcup.backfill                 # all editions
    python -m worldcup.backfill --from 1990     # 1990 onward
    python -m worldcup.backfill 2018 2022        # specific years
    python -m worldcup.backfill --refresh        # re-pull even if on disk
"""

import argparse
import time

import pandas as pd

from . import config, players, results, schedule, seasons, teams

CORE = ["teams", "players", "schedule", "results"]


def collect_season(year: int, id_season: str) -> None:
    subdir = str(year)
    print(f"\n=== {year} (idSeason={id_season}) ===")
    teams_df = None
    try:
        teams_df = teams.run(season=id_season, subdir=subdir)
    except Exception as e:  # noqa: BLE001
        print(f"  teams failed: {e}")
    if teams_df is not None and not teams_df.empty:
        try:
            players.run(teams_df=teams_df, season=id_season, subdir=subdir)
        except Exception as e:  # noqa: BLE001
            print(f"  players failed: {e}")
    for mod in (schedule, results):
        try:
            mod.run(season=id_season, subdir=subdir)
        except Exception as e:  # noqa: BLE001
            print(f"  {mod.__name__.split('.')[-1]} failed: {e}")


def _year_dirs() -> list[int]:
    out = []
    for p in config.PROCESSED_DIR.iterdir() if config.PROCESSED_DIR.exists() else []:
        if p.is_dir() and p.name.isdigit():
            out.append(int(p.name))
    return sorted(out)


def build_combined() -> None:
    print("\n=== combined tables (data/processed/all) ===")
    coverage = {}
    for name in CORE:
        frames = []
        for year in _year_dirs():
            path = config.PROCESSED_DIR / str(year) / f"{name}.csv"
            if not path.exists():
                continue
            df = pd.read_csv(path)
            df.insert(0, "year", year)
            frames.append(df)
            coverage.setdefault(year, {})[name] = len(df)
        if frames:
            combined = pd.concat(frames, ignore_index=True)
            out = config.PROCESSED_DIR / "all" / f"{name}.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            combined.to_csv(out, index=False)
            combined.to_json(out.with_suffix(".json"), orient="records", indent=2, force_ascii=False)
            print(f"  {name}: {len(combined)} rows across {len(frames)} editions")

    if coverage:
        rows = [{"year": y, **{n: c.get(n, 0) for n in CORE}} for y, c in sorted(coverage.items())]
        cov = pd.DataFrame(rows)
        cov.to_csv(config.PROCESSED_DIR / "all" / "coverage.csv", index=False)
        print("\nCoverage (rows per dataset):")
        print(cov.to_string(index=False))


def main() -> None:
    ap = argparse.ArgumentParser(prog="worldcup-backfill",
                                 description="Collect core data for every World Cup edition")
    ap.add_argument("years", nargs="*", type=int, help="Specific years (default: all)")
    ap.add_argument("--from", dest="year_from", type=int, help="Earliest year to include")
    ap.add_argument("--to", dest="year_to", type=int, help="Latest year to include")
    ap.add_argument("--refresh", action="store_true", help="Re-pull editions already on disk")
    ap.add_argument("--no-combine", action="store_true", help="Skip building combined tables")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds to pause between editions")
    args = ap.parse_args()

    table = seasons.season_table()
    if args.years:
        table = [r for r in table if r["year"] in args.years]
    if args.year_from:
        table = [r for r in table if r["year"] >= args.year_from]
    if args.year_to:
        table = [r for r in table if r["year"] <= args.year_to]

    print(f"Collecting {len(table)} edition(s): {[r['year'] for r in table]}")
    for r in table:
        done = (config.PROCESSED_DIR / str(r["year"]) / "results.csv").exists()
        if done and not args.refresh:
            print(f"\n=== {r['year']} — already collected, skipping (use --refresh) ===")
            continue
        collect_season(r["year"], r["id_season"])
        time.sleep(args.delay)

    if not args.no_combine:
        build_combined()


if __name__ == "__main__":
    main()
