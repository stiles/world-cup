# World Cup data

Collects teams, players, schedule, results and stats for the FIFA World Cup from public FIFA API endpoints. Built for the 2026 tournament (USA/Canada/Mexico). 

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .          # or: pip install -r requirements.txt
```

Installing the package (`pip install -e .`) also adds the `worldcup-follow` and
`worldcup-collect` console scripts.

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

## Follow a match (play-by-play)

`worldcup-follow` browses the schedule, picks a match and either recaps a finished
game or streams a live one in the terminal, with goals, cards and VAR highlighted.

```bash
python -m worldcup.follow                 # today's matches, pick one
python -m worldcup.follow USA             # USA's live / last / next match
python -m worldcup.follow --match 1       # follow a specific match number
python -m worldcup.follow USA --recap     # full timeline of the last USA match
python -m worldcup.follow --list          # print the schedule and exit
```

After `pip install -e .` the same tool is available as `worldcup-follow`.

Key flags:

- `--recap` print the full timeline and exit (default for finished matches)
- `--scoring-only` goals, cards, VAR and key moments only
- `--from-start` when live, print all prior events before following
- `--list` print the schedule (optionally filtered by team) and exit
- `--interval N` live poll seconds (default 8)
- `--tz ZONE` IANA timezone for kickoff times (default: local)
- `--no-color` disable ANSI color

Data comes from the FIFA `timelines/{competition}/{season}/{stage}/{match}` endpoint,
keyed by the same IDs the collectors use, so no per-match configuration is needed.

## Examples

Analysis scripts that build on the collected data live in `examples/`:

```bash
python examples/team_profiles.py   # per-team average age, height, weight, squad size
```

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
  follow.py        play-by-play CLI (python -m worldcup.follow)
  __main__.py      collector orchestrator (python -m worldcup)
examples/          analysis scripts built on the collected data
data/processed/    CSV + JSON outputs
```
