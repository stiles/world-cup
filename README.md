# World Cup data

Collects teams, players, schedule, results and stats for the FIFA World Cup from public FIFA API endpoints, with a CLI for play-by-play of live matches in the terminal. 

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .          # or: pip install -r requirements.txt
```

Installing the package (`pip install -e .`) also adds the `nutmeg` and
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

Outputs land in `data/processed/` as both CSV and JSON. Raw API payloads (where saved) go to `data/raw/`. See [Data layout](#data-layout) for how the current tournament, per-edition and combined files are organized.

## Data layout

`data/processed/` holds three tiers of data:

| Location | What | Produced by |
|---|---|---|
| `data/processed/*.csv` (root) | The **current tournament** (2026). The only tier with stats (`team_stats`, `player_stats`). | `python -m worldcup` |
| `data/processed/<year>/` | One folder **per edition** (1930-2026) with the core datasets: `teams`, `players`, `schedule`, `results`. No stats. | `worldcup-backfill` |
| `data/processed/all/` | All editions **combined** into one table per dataset, with a `year` column, plus `coverage.csv`. | `worldcup-backfill` |

The root files and the `2026/` folder overlap for the core datasets, but the root is the live working set (and carries the stats), while `2026/` is just 2026's slice of the historical archive.

Raw API payloads (where saved) go to `data/raw/`.

## nutmeg: follow a match (play-by-play)

`nutmeg` browses the schedule, picks a match and either recaps a finished game or
streams a live one in the terminal, with goals, cards and VAR highlighted.

```bash
nutmeg                 # today's matches, pick one
nutmeg USA             # USA's live / last / next match
nutmeg --match 1       # follow a specific match number
nutmeg USA --recap     # full timeline of the last USA match
nutmeg --schedule          # print the schedule and exit
```

The `nutmeg` command is available after `pip install -e .`; without installing,
run it as `python -m worldcup.nutmeg ...`.

Key flags:

- `--recap` print the full timeline and exit (default for finished matches)
- `--scoring-only` goals, cards, VAR and key moments only
- `--recent` when live, show only the last few events instead of the full match so far
- `--schedule` print the schedule (optionally filtered by team) and exit
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

## Collect every edition (backfill)

`worldcup-backfill` collects the core datasets (teams, players, schedule, results)
for all World Cups, 1930-2026, discovered live from the FIFA seasons endpoint.

```bash
python -m worldcup.backfill              # all editions
python -m worldcup.backfill --from 1990  # 1990 onward
python -m worldcup.backfill 2018 2022     # specific years
python -m worldcup.backfill --refresh     # re-pull editions already on disk
```

Output:

- Per edition: `data/processed/<year>/{teams,players,schedule,results}.csv` (+ JSON)
- Combined, with a `year` column: `data/processed/all/{teams,players,schedule,results}.csv`
- `data/processed/all/coverage.csv` — row counts per dataset per edition

Past tournaments are static, so collected years are skipped unless `--refresh` is
passed; the run is resumable if a connection drops. Editions without a given
dataset are skipped gracefully (FIFA actually has squads back to 1930).

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
  seasons.py       discover all World Cup editions (year -> idSeason)
  backfill.py      collect every edition (the `worldcup-backfill` command)
  nutmeg.py        play-by-play CLI (the `nutmeg` command)
  __main__.py      collector orchestrator (python -m worldcup)
examples/          analysis scripts built on the collected data
data/processed/    CSV + JSON outputs
  *.csv            current tournament (2026), incl. stats — python -m worldcup
  <year>/          one folder per edition (1930-2026) — worldcup-backfill
  all/             every edition combined, with a year column + coverage.csv
```
