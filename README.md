# World Cup data

Collects teams, players, schedule, results and stats for the FIFA World Cup from public FIFA API endpoints. Built for the 2026 tournament (USA/Canada/Mexico), ported from a set of 2022 notebooks now kept in `archive/`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run every collector:

```bash
python -m worldcup
```

Run specific collectors (any subset, space separated):

```bash
python -m worldcup teams players
python -m worldcup schedule results
```

Each module is also runnable on its own:

```bash
python -m worldcup.teams
python -m worldcup.player_stats
```

Outputs land in `data/processed/` as both CSV and JSON. Raw API payloads (where saved) go to `data/raw/`.

## Targeting a different tournament

Edit `worldcup/config.py`:

- `SEASON_ID` - tournament season (2026 = `285023`, 2022 = `255711`)
- `COMPETITION_ID` - `17` for the men's World Cup

## Data sources

| Output | Endpoint |
|---|---|
| `teams` | `api.fifa.com/api/v3/competitions/teams/{season}` |
| `players` | `api.fifa.com/api/v3/teams/{idTeam}/squad` |
| `schedule`, `results` | `api.fifa.com/api/v3/calendar/matches` |
| `team_stats`, `team_stats_wide` | `fdh-api.fifa.com/v1/stats/season/{season}/team/{idTeam}.json` |
| `player_stats` | `fdh-api.fifa.com/v1/stats/season/{season}/players.json` |

## Outputs

- `teams` - one row per qualified team (id, confederation, names, flag URL)
- `players` - full squads with position, age, height, weight, jersey number
- `schedule` - fixtures with stage, group, kickoff times (UTC and venue-local)
- `results` - scores, winner, possession, tactics, attendance, weather, venue
- `team_stats` (long) and `team_stats_wide` (pivoted) - aggregate team metrics
- `player_stats` (long) - per-player metrics joined to player names and teams

Stats endpoints only return values once matches have been played, so those files grow as the tournament progresses.

## Layout

```
worldcup/
  config.py        tournament IDs, API bases, output paths
  fetch.py         HTTP with retry + calendar fetcher
  storage.py       CSV/JSON writers
  teams.py players.py schedule.py results.py team_stats.py player_stats.py
  __main__.py      orchestrator (python -m worldcup)
archive/           original 2022 notebooks
data/processed/    CSV + JSON outputs
```
