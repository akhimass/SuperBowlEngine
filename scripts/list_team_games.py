#!/usr/bin/env python3
"""
List games per team from PBP: who they played, how many games, game type (WC/DIV/CON/SB).

Use this to verify matchup validity: if NE has 3 postseason games and SEA has 2,
and NE won all 5 keys aggregated across their games while SEA lost or tied those keys,
the prediction result is valid.

Usage:
  python3 scripts/list_team_games.py --year 2025 --team-a NE --team-b SEA
"""

import argparse
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

from superbowlengine.data import get_pbp, get_schedules, SeasonNotAvailableError
from superbowlengine.data.games import list_team_games, team_games_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="List postseason games per team (who they played, count, game type)")
    parser.add_argument("--year", type=int, default=2025, help="Season year")
    parser.add_argument("--season-type", default="POST", choices=("POST", "REG", "ALL"), help="Season type")
    parser.add_argument("--team-a", default="NE", help="First team")
    parser.add_argument("--team-b", default="SEA", help="Second team")
    args = parser.parse_args()

    try:
        pbp = get_pbp([args.year], season_type=args.season_type)
    except SeasonNotAvailableError as e:
        print("Data not available:", e)
        return 1

    schedule = get_schedules([args.year])

    print("Games check for %s %s (year=%s)" % (args.season_type, args.year, args.year))
    print("-" * 50)
    print(team_games_summary(pbp, args.team_a, schedule))
    print()
    print(team_games_summary(pbp, args.team_b, schedule))
    print()
    print("If game counts and opponents look correct, aggregated 5 Keys and the prediction are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
