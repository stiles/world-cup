"""Run collectors. Usage:

    python -m worldcup            # run everything
    python -m worldcup teams players schedule results team_stats player_stats
"""

import sys

from . import players, player_stats, results, schedule, team_stats, teams

ORDER = ["teams", "players", "schedule", "results", "team_stats", "player_stats"]


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    targets = argv or ORDER
    unknown = [t for t in targets if t not in ORDER]
    if unknown:
        raise SystemExit(f"Unknown target(s): {unknown}. Choose from {ORDER}")

    teams_df = None
    players_df = None

    if "teams" in targets:
        teams_df = teams.run()
    if "players" in targets:
        players_df = players.run(teams_df)
    if "schedule" in targets:
        schedule.run()
    if "results" in targets:
        results.run()
    if "team_stats" in targets:
        team_stats.run(teams_df)
    if "player_stats" in targets:
        player_stats.run(players_df)


if __name__ == "__main__":
    main()
