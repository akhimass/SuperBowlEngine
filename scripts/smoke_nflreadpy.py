#!/usr/bin/env python3
"""
Smoke test for nflreadpy integration.

Loads PBP for --year 2024 --season-type POST by default, prints row/game counts,
first 10 columns, and confirms required column groups (TOP, TO, 3D, RZ) are present.
Exits 0 if validations pass, 1 otherwise.
"""

import argparse
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

try:
    import pandas  # noqa: F401
except ModuleNotFoundError:
    print("Missing dependency: pandas. Install with: pip install -e .")
    sys.exit(1)

from superbowlengine.data import get_pbp, validate_pbp_for_keys, SeasonNotAvailableError, MissingColumnsError


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test nflreadpy PBP load and validations")
    parser.add_argument("--year", type=int, default=2024, help="Season year")
    parser.add_argument("--season-type", default="POST", choices=("POST", "REG", "ALL"), help="Season type")
    args = parser.parse_args()

    try:
        df = get_pbp([args.year], season_type=args.season_type)
    except SeasonNotAvailableError as e:
        print("Data not published yet for %s %s: %s" % (args.year, args.season_type, e))
        return 1
    except MissingColumnsError as e:
        print("Missing columns: %s" % e)
        return 1

    try:
        validate_pbp_for_keys(df)
    except MissingColumnsError as e:
        print("Validation failed: %s" % e)
        return 1

    n_rows = len(df)
    n_games = df["game_id"].nunique() if "game_id" in df.columns else 0
    first_10 = list(df.columns[:10])

    print("Rows: %d" % n_rows)
    print("Games: %d" % n_games)
    print("First 10 columns: %s" % first_10)

    # Confirm column groups
    top_ok = all(c in df.columns for c in ["drive", "drive_time_of_possession", "game_id"])
    to_ok = all(c in df.columns for c in ["interception", "fumble_lost"])
    third_ok = "down" in df.columns and "ydstogo" in df.columns and ("first_down" in df.columns or "yards_gained" in df.columns)
    rz_ok = all(c in df.columns for c in ["yardline_100", "drive", "game_id", "touchdown"])

    print("TOP columns present: %s" % top_ok)
    print("Turnover columns present: %s" % to_ok)
    print("3rd down columns present: %s" % third_ok)
    print("Red zone columns present: %s" % rz_ok)

    if not (top_ok and to_ok and third_ok and rz_ok):
        print("One or more column groups missing.")
        return 1

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
