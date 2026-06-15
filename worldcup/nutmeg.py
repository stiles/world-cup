#!/usr/bin/env python3
"""nutmeg: follow a World Cup match in your terminal.

- Browse the schedule, pick a team or a match
- Recap a finished match or stream a live one play-by-play
- Rich, colorized output that makes goals, cards and VAR pop

Data: FIFA API calendar + per-match timelines endpoint.

    nutmeg                 # today's matches, pick one
    nutmeg USA             # USA's live/last/next match
    nutmeg --match 1       # follow match number 1
    nutmeg USA --recap     # full timeline of last USA match
    nutmeg --list          # print the schedule and exit

(or run via `python -m worldcup.nutmeg ...` without installing)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from . import config
from .fetch import get_calendar_matches, get_json

# Match window used to call a started-but-unfinished match "live".
LIVE_WINDOW = timedelta(hours=3)


# --- color -------------------------------------------------------------------

def colorize(enabled: bool, s: str, fg: str = "37", bold: bool = False) -> str:
    if not enabled:
        return s
    prefix = ("1;" if bold else "") + fg
    return f"\x1b[{prefix}m{s}\x1b[0m"


def warn(msg: str) -> None:
    print(colorize(True, f"! {msg}", "33"), file=sys.stderr)


def _reason(exc: Exception) -> str:
    """Collapse a noisy requests/urllib3 exception into a short, human cause."""
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return "connection timed out"
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return "server slow to respond"
    if isinstance(exc, requests.exceptions.ConnectionError):
        text = str(exc).lower()
        if "nodename nor servname" in text or "name or service not known" in text or "getaddrinfo" in text:
            return "computer asleep or offline"
        return "network unreachable"
    return exc.__class__.__name__


def local_tz_key(default: str = "America/Los_Angeles") -> str:
    try:
        key = getattr(datetime.now().astimezone().tzinfo, "key", None)
        if isinstance(key, str) and key:
            return key
    except Exception:
        pass
    return default


# --- schedule helpers --------------------------------------------------------

def _desc(value) -> str | None:
    if isinstance(value, list) and value:
        return value[0].get("Description")
    return None


def parse_match(m: dict) -> dict:
    home = m.get("Home") or {}
    away = m.get("Away") or {}
    stadium = m.get("Stadium") or {}
    kickoff = None
    raw = m.get("Date")
    if raw:
        try:
            kickoff = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            kickoff = None
    return {
        "id_match": m.get("IdMatch"),
        "id_stage": m.get("IdStage"),
        "number": m.get("MatchNumber"),
        "stage": _desc(m.get("StageName")),
        "group": _desc(m.get("GroupName")),
        "home_id": home.get("IdTeam"),
        "away_id": away.get("IdTeam"),
        "home_abbr": home.get("Abbreviation"),
        "away_abbr": away.get("Abbreviation"),
        "home_name": home.get("ShortClubName") or home.get("Abbreviation"),
        "away_name": away.get("ShortClubName") or away.get("Abbreviation"),
        "home_score": home.get("Score"),
        "away_score": away.get("Score"),
        "match_status": m.get("MatchStatus"),
        "winner": m.get("Winner"),
        "kickoff": kickoff,
        "venue": _desc(stadium.get("Name")),
    }


def status_of(match: dict, now: datetime) -> str:
    """Return one of: finished, live, upcoming."""
    if match["match_status"] == 0:
        return "finished"
    ko = match["kickoff"]
    if ko is None:
        return "upcoming"
    if ko <= now <= ko + LIVE_WINDOW:
        return "live"
    if ko > now:
        return "upcoming"
    # kicked off long ago but not flagged finished; treat as finished
    return "finished"


def team_matches(matches: list[dict], team: str) -> list[dict]:
    t = team.lower()
    out = []
    for m in matches:
        names = {
            (m["home_abbr"] or "").lower(),
            (m["away_abbr"] or "").lower(),
            (m["home_name"] or "").lower(),
            (m["away_name"] or "").lower(),
        }
        if t in names or any(t in n for n in names if n):
            out.append(m)
    return out


def pick_for_team(matches: list[dict], now: datetime) -> tuple[dict | None, dict | None, dict | None]:
    """Return (live, last_finished, next_upcoming) for a list of a team's matches."""
    matches = sorted(matches, key=lambda m: m["kickoff"] or now)
    live = next((m for m in matches if status_of(m, now) == "live"), None)
    last = None
    nxt = None
    for m in matches:
        if status_of(m, now) == "finished":
            last = m
    for m in matches:
        if status_of(m, now) == "upcoming":
            nxt = m
            break
    return live, last, nxt


# --- formatting --------------------------------------------------------------

def fmt_brief(match: dict, tz: str, color: bool, now: datetime) -> str:
    ko = match["kickoff"]
    when = ""
    if ko:
        when = ko.astimezone(ZoneInfo(tz)).strftime("%a %b %-d, %-I:%M %p %Z")
    st = status_of(match, now)
    hs, as_ = match["home_score"], match["away_score"]
    score = f"{hs}-{as_}" if hs is not None and as_ is not None and st != "upcoming" else "vs"
    line = (
        f"#{match['number']:>3}  "
        f"{colorize(color, match['home_abbr'] or '???', '36')} {score} "
        f"{colorize(color, match['away_abbr'] or '???', '35')}"
    )
    tags = " ".join(t for t in [match["stage"], match["group"]] if t)
    badge = {"live": colorize(color, "LIVE", "32", bold=True), "finished": "FT", "upcoming": when}[st]
    return f"{line}   {tags}   {badge}"


def scoreboard(match: dict, color: bool, hs=None, as_=None, minute: str | None = None) -> str:
    hs = match["home_score"] if hs is None else hs
    as_ = match["away_score"] if as_ is None else as_
    hs = "-" if hs is None else hs
    as_ = "-" if as_ is None else as_
    head = f"{match['home_name']}  {colorize(color, str(hs), '33', bold=True)} - " \
           f"{colorize(color, str(as_), '33', bold=True)}  {match['away_name']}"
    sub = " | ".join(t for t in [match["stage"], match["group"], match["venue"]] if t)
    minute_txt = colorize(color, f"  {minute}", "32", bold=True) if minute else ""
    return f"\n  {head}{minute_txt}\n  {colorize(color, sub, '90')}"


# Event labels (TypeLocalized) that deserve a callout, with an icon + style.
def event_style(label: str, text: str) -> tuple[str, str, bool, bool]:
    """Return (icon, fg_color, bold, is_highlight) for a timeline event."""
    l = (label or "").lower()
    t = (text or "").lower()
    if "attempt" in l:
        return "shot", "90", False, False
    if "goal" in l and "prevention" not in l and "kick" not in l:
        if "penalty" in t:
            return "GOAL (pen)", "32", True, True
        if "own goal" in t:
            return "OWN GOAL", "32", True, True
        return "GOAL", "32", True, True
    if "red card" in l:
        return "RED", "31", True, True
    if "yellow card" in l:
        return "YEL", "33", False, True
    if "substitution" in l:
        return "SUB", "36", False, False
    if "var" in l:
        return "VAR", "35", True, True
    if "penalty" in l:
        return "PEN", "35", True, True
    if l in {"start time", "resume"}:
        return ">>", "32", False, False
    if l in {"end time", "match end", "half time"}:
        return "==", "90", True, False
    if "offside" in l:
        return "off", "90", False, False
    if "corner" in l:
        return "cor", "90", False, False
    if "foul" in l:
        return "foul", "90", False, False
    if "attempt" in l:
        return "shot", "90", False, False
    return "-", "90", False, False


def team_tag(e: dict, match: dict, color: bool) -> str:
    """Colored 3-char team code: home in cyan, away in magenta."""
    tid = e.get("IdTeam")
    if tid and tid == match["home_id"]:
        return colorize(color, f"{(match['home_abbr'] or '???'):>3}", "36", bold=True)
    if tid and tid == match["away_id"]:
        return colorize(color, f"{(match['away_abbr'] or '???'):>3}", "35", bold=True)
    return "   "


def is_goal_event(e: dict) -> bool:
    label = (_desc(e.get("TypeLocalized")) or "").lower()
    if "attempt" in label or "prevention" in label or "kick" in label:
        return False
    return "goal" in label


def fmt_event(e: dict, match: dict, color: bool) -> str:
    label = _desc(e.get("TypeLocalized")) or str(e.get("Type"))
    text = _desc(e.get("EventDescription")) or label
    minute = e.get("MatchMinute") or ""
    icon, fg, bold, highlight = event_style(label, text)
    score = ""
    hg, ag = e.get("HomeGoals"), e.get("AwayGoals")
    if highlight and hg is not None and ag is not None:
        score = colorize(color, f"  [{hg}-{ag}]", "33", bold=True)
    tag = colorize(color, f"{icon:>4}", fg, bold=bold)
    minute_col = colorize(color, f"{minute:>5}", "37")
    body = colorize(color, text, fg, bold=bold) if highlight else colorize(color, text, "37")
    return f"{minute_col} {team_tag(e, match, color)} {tag}  {body}{score}"


def fmt_goal_banner(e: dict, match: dict, color: bool) -> str:
    """A big, bold callout for goals."""
    minute = e.get("MatchMinute") or ""
    text = _desc(e.get("EventDescription")) or "Goal!"
    hg = e.get("HomeGoals")
    ag = e.get("AwayGoals")
    side = team_tag(e, match, color)
    score_line = f"{match['home_name']} {hg} - {ag} {match['away_name']}"

    def g(s: str) -> str:
        return colorize(color, s, "92", bold=True)

    return "\n".join([
        "",
        g("  ━━━━━━━━  G O A L !  ━━━━━━━━"),
        f"  {colorize(color, minute.strip(), '92', bold=True)}  {side}  {g(text)}",
        g(f"  {score_line}"),
        "",
    ])


def render_event(e: dict, match: dict, color: bool) -> str:
    return fmt_goal_banner(e, match, color) if is_goal_event(e) else fmt_event(e, match, color)


# --- timeline ----------------------------------------------------------------

def fetch_timeline(match: dict) -> list[dict]:
    url = (
        f"{config.API_BASE}/timelines/{config.COMPETITION_ID}/{config.SEASON_ID}"
        f"/{match['id_stage']}/{match['id_match']}?language={config.LANGUAGE}"
    )
    data = get_json(url)
    events = data.get("Event") or []
    events.sort(key=lambda x: x.get("Timestamp") or "")
    return events


def keep_event(e: dict, scoring_only: bool) -> bool:
    if not scoring_only:
        return True
    label = (_desc(e.get("TypeLocalized")) or "").lower()
    if "attempt" in label or "prevention" in label or "kick" in label:
        return False
    return any(k in label for k in ("goal", "card", "var", "penalty", "match end", "start time", "half time"))


def recap(match: dict, color: bool, scoring_only: bool) -> None:
    print(scoreboard(match, color))
    events = fetch_timeline(match)
    if not events:
        print(colorize(color, "\n  No timeline available for this match yet.", "90"))
        return
    print()
    for e in events:
        if keep_event(e, scoring_only):
            print(render_event(e, match, color))
    final = f"\n  Full time: {match['home_name']} {match['home_score']}-{match['away_score']} {match['away_name']}"
    print(colorize(color, final, "32", bold=True))


def stream(match: dict, color: bool, scoring_only: bool, interval: float, from_start: bool) -> None:
    print(scoreboard(match, color, minute="LIVE"))
    seen: set[str] = set()
    last_score: tuple = ()
    backoff = interval
    first = True
    offline = False
    while True:
        try:
            events = fetch_timeline(match)
        except requests.exceptions.RequestException as e:
            if not offline:
                warn(f"Connection lost ({_reason(e)}). Reconnecting...")
                offline = True
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        except Exception as e:  # noqa: BLE001
            warn(f"Unexpected error: {e}. Retrying in {backoff:.0f}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        if offline:
            print(colorize(color, "  Reconnected.", "32", bold=True))
            offline = False
        backoff = interval

        new = [e for e in events if e.get("EventId") not in seen]
        if first and not from_start:
            # On first poll, prime 'seen' but still show the last few for context.
            for e in events:
                seen.add(e.get("EventId"))
            tail = [e for e in events if keep_event(e, scoring_only)][-6:]
            for e in tail:
                print(render_event(e, match, color))
            new = []
        for e in new:
            seen.add(e.get("EventId"))
            if keep_event(e, scoring_only):
                print(render_event(e, match, color))
                hg, ag = e.get("HomeGoals"), e.get("AwayGoals")
                if (hg, ag) != last_score and "goal" in (_desc(e.get("TypeLocalized")) or "").lower():
                    print(scoreboard(match, color, hs=hg, as_=ag, minute=e.get("MatchMinute")))
                    last_score = (hg, ag)
        first = False

        labels = {(_desc(e.get("TypeLocalized")) or "").lower() for e in events}
        if "match end" in labels:
            print(colorize(color, "\n  Match ended.", "32", bold=True))
            return
        time.sleep(interval)


# --- selection ---------------------------------------------------------------

def choose(options: list[dict], tz: str, color: bool, now: datetime) -> dict | None:
    if not options:
        return None
    if len(options) == 1:
        return options[0]
    print("Multiple matches. Choose one:")
    for i, m in enumerate(options, 1):
        print(f"  {i}) {fmt_brief(m, tz, color, now)}")
    while True:
        try:
            choice = input(f"Select [1-{len(options)}]: ").strip()
        except EOFError:
            return options[0]
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Invalid selection.")


def run_match(match: dict, args, now: datetime) -> None:
    color = not args.no_color
    st = status_of(match, now)
    if args.recap or (st == "finished" and not args.live):
        recap(match, color, args.scoring_only)
    elif st == "upcoming":
        print(scoreboard(match, color))
        ko = match["kickoff"]
        if ko:
            delta = ko - now
            hrs = delta.total_seconds() / 3600
            print(colorize(color, f"\n  Kicks off in {hrs:.1f} hours "
                                  f"({ko.astimezone(ZoneInfo(args.tz)):%a %b %-d, %-I:%M %p %Z}).", "90"))
    else:
        try:
            stream(match, color, args.scoring_only, args.interval, args.from_start)
        except KeyboardInterrupt:
            print("\nBye.")


# --- cli ---------------------------------------------------------------------

def main() -> None:
    tz_default = local_tz_key()
    ap = argparse.ArgumentParser(prog="nutmeg",
                                 description="Follow a World Cup match in your terminal")
    ap.add_argument("team", nargs="?", help="Team abbr or name (e.g., USA, Brazil)")
    ap.add_argument("--match", type=int, help="Follow a specific match number")
    ap.add_argument("--id", dest="id_match", help="Follow a specific IdMatch")
    ap.add_argument("--recap", action="store_true", help="Print the full timeline and exit")
    ap.add_argument("--live", action="store_true", help="Stream even if the match looks finished")
    ap.add_argument("--from-start", action="store_true", help="When live, print all prior events first")
    ap.add_argument("--scoring-only", action="store_true", help="Only goals, cards, VAR and key moments")
    ap.add_argument("--list", action="store_true", help="Print the schedule (optionally for a team) and exit")
    ap.add_argument("--interval", type=float, default=8.0, help="Live poll seconds (default 8)")
    ap.add_argument("--no-color", action="store_true", help="Disable ANSI color")
    ap.add_argument("--tz", default=tz_default, help="IANA timezone (default: local)")
    args = ap.parse_args()

    color = not args.no_color
    now = datetime.now(timezone.utc)
    matches = [parse_match(m) for m in get_calendar_matches()]

    pool = team_matches(matches, args.team) if args.team else matches

    if args.list:
        rows = sorted(pool, key=lambda m: m["kickoff"] or now)
        header = f"Schedule ({args.team})" if args.team else "Schedule"
        print(colorize(color, header, "37", bold=True))
        for m in rows:
            print("  " + fmt_brief(m, args.tz, color, now))
        return

    if args.id_match:
        match = next((m for m in matches if m["id_match"] == args.id_match), None)
        if not match:
            raise SystemExit(f"No match with IdMatch {args.id_match}")
        return run_match(match, args, now)

    if args.match:
        match = next((m for m in matches if m["number"] == args.match), None)
        if not match:
            raise SystemExit(f"No match number {args.match}")
        return run_match(match, args, now)

    if args.team:
        if not pool:
            raise SystemExit(f"No matches found for team: {args.team}")
        live, last, nxt = pick_for_team(pool, now)
        if live:
            return run_match(live, args, now)
        if last:
            print(colorize(color, "Most recent match:", "37", bold=True))
            run_match(last, args, now)
        if nxt:
            print(colorize(color, "\nNext match:", "37", bold=True))
            print("  " + fmt_brief(nxt, args.tz, color, now))
        if not last and nxt:
            return
        return

    # No team: prefer live matches, else today's matches by local date.
    live = [m for m in matches if status_of(m, now) == "live"]
    if live:
        match = choose(sorted(live, key=lambda m: m["kickoff"] or now), args.tz, color, now)
        return run_match(match, args, now) if match else None

    today = datetime.now(ZoneInfo(args.tz)).date()
    todays = [m for m in matches if m["kickoff"] and m["kickoff"].astimezone(ZoneInfo(args.tz)).date() == today]
    if todays:
        print(colorize(color, f"Matches today ({today}):", "37", bold=True))
        match = choose(sorted(todays, key=lambda m: m["kickoff"]), args.tz, color, now)
        return run_match(match, args, now) if match else None

    nxt = next((m for m in sorted(matches, key=lambda m: m["kickoff"] or now)
                if status_of(m, now) == "upcoming"), None)
    print("No live or scheduled matches today.")
    if nxt:
        print("Next match:")
        print("  " + fmt_brief(nxt, args.tz, color, now))


if __name__ == "__main__":
    main()
