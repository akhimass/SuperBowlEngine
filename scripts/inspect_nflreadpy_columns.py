#!/usr/bin/env python3
"""
Developer utility: inspect and document nflreadpy columns for PBP and schedules.

Shows what columns our loader returns and which are missing vs required by the
5 Keys + SOS pipeline. Uses get_pbp() and get_schedules() (no direct nflreadpy).
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

try:
    import pandas as pd  # noqa: F401
except ModuleNotFoundError:
    print("Missing dependency: pandas. Install with: pip install -e .")
    sys.exit(1)

from superbowlengine.data import get_pbp, get_schedules, SeasonNotAvailableError, MissingColumnsError

# 5 Keys column requirements (aligned with data/load.py validators)
KEY_GROUPS = {
    "TOP": ["drive", "drive_time_of_possession", "game_id"],
    "Turnovers": ["interception", "fumble_lost"],
    "Big Plays": ["play_type", "yards_gained"],
    "3rd Down": ["down", "ydstogo"],  # plus first_down OR yards_gained (checked separately)
    "Red Zone": ["yardline_100", "drive", "game_id", "touchdown"],
}


def check_third_down_optional(cols: list[str]) -> tuple[bool, list[str]]:
    """3rd Down requires down AND (first_down OR (yards_gained AND ydstogo))."""
    missing_base = [c for c in KEY_GROUPS["3rd Down"] if c not in cols]
    if missing_base:
        return False, missing_base
    has_first_down = "first_down" in cols
    has_yards_ydstogo = "yards_gained" in cols and "ydstogo" in cols
    if has_first_down or has_yards_ydstogo:
        return True, []
    return False, ["first_down OR (yards_gained AND ydstogo)"]


def check_key_groups(pbp_columns: list[str]) -> dict[str, list[str]]:
    """Return missing_by_key: key name -> list of missing column names (empty = OK)."""
    missing_by_key: dict[str, list[str]] = {}
    cols = list(pbp_columns)

    for key_name, required in KEY_GROUPS.items():
        if key_name == "3rd Down":
            ok, missing = check_third_down_optional(cols)
            missing_by_key[key_name] = [] if ok else missing
        else:
            missing = [c for c in required if c not in cols]
            missing_by_key[key_name] = missing

    return missing_by_key


def run(
    year: int,
    season_type: str,
    limit: int | None,
    json_path: Path | None,
) -> int:
    """Load data, print inspection, optionally write JSON. Return 0 if all key groups OK else 1."""
    print("NFLREADPY COLUMN INSPECTION")
    print("-" * 50)
    print("Year: %s" % year)
    print("Season type: %s" % season_type)
    if limit is not None:
        print("Row limit: %s (applied after load)" % limit)
    print()

    try:
        pbp = get_pbp([year], season_type=season_type)
    except SeasonNotAvailableError as e:
        print("PBP not available: %s" % e)
        return 1
    except MissingColumnsError as e:
        print("PBP validation error: %s" % e)
        return 1

    if limit is not None and len(pbp) > limit:
        pbp = pbp.head(limit)

    sched = get_schedules([year])

    n_rows = len(pbp)
    n_games = pbp["game_id"].nunique() if "game_id" in pbp.columns else 0

    print("PBP: rows=%d, unique games=%d" % (n_rows, n_games))
    pbp_cols = sorted(pbp.columns.tolist())
    print("PBP columns (%d):" % len(pbp_cols))
    for c in pbp_cols:
        print("  %s" % c)
    print()

    print("Schedule columns (%d):" % len(sched.columns))
    sched_cols = sorted(sched.columns.tolist())
    for c in sched_cols:
        print("  %s" % c)
    print()

    print("5 Keys column check (required by pipeline):")
    print("-" * 50)
    missing_by_key = check_key_groups(pbp_cols)
    all_ok = True
    for key_name in KEY_GROUPS:
        missing = missing_by_key.get(key_name, [])
        if not missing:
            print("  %s: OK" % key_name)
        else:
            all_ok = False
            print("  %s: MISSING -> %s" % (key_name, missing))

    if not all_ok:
        print()
        print("If column names differ in your data, add mappings to COLUMN_ALIASES in data/load.py")
    print()

    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "year": year,
            "season_type": season_type,
            "pbp_columns": pbp_cols,
            "schedule_columns": sched_cols,
            "missing_by_key": missing_by_key,
            "pbp_row_count": n_rows,
            "pbp_game_count": int(n_games),
        }
        with open(json_path, "w") as f:
            json.dump(payload, f, indent=2)
        print("Wrote %s" % json_path)

    return 0 if all_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect nflreadpy PBP and schedule columns vs 5 Keys requirements",
    )
    parser.add_argument("--year", type=int, default=2024, help="Season year")
    parser.add_argument(
        "--season-type",
        default="POST",
        choices=("POST", "REG", "ALL"),
        help="Season type for PBP",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Use first N PBP rows after load (for faster inspection; default full)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write outputs/nflreadpy_columns_{year}_{season_type}.json",
    )
    args = parser.parse_args()

    json_path: Path | None = None
    if args.json:
        json_path = repo / "outputs" / ("nflreadpy_columns_%s_%s.json" % (args.year, args.season_type))

    return run(
        year=args.year,
        season_type=args.season_type,
        limit=args.limit,
        json_path=json_path,
    )


if __name__ == "__main__":
    sys.exit(main())
