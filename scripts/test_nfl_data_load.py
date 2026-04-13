"""Quick sanity test for nflreadpy/nflverse-backed loaders.

Loads 2024 play-by-play and schedules via superbowlengine.data.load and prints
basic stats. Exits with non-zero code if PBP/schedule are empty or required
columns are missing.
"""

from __future__ import annotations

import sys

import pandas as pd

from superbowlengine.data.load import REQUIRED_PBP_COLUMNS, get_pbp, get_schedules


def main() -> int:
    season = 2024
    print(f"Testing NFL data load for season={season}...", flush=True)

    try:
        pbp = get_pbp([season], season_type="ALL")
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: get_pbp failed: {e}", file=sys.stderr)
        return 1

    try:
        schedules = get_schedules([season])
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: get_schedules failed: {e}", file=sys.stderr)
        return 1

    print(f"PBP rows: {len(pbp)}")
    print(f"Schedule rows: {len(schedules)}")

    if pbp.empty or schedules.empty:
        print("ERROR: PBP or schedules are empty.", file=sys.stderr)
        return 1

    missing = [c for c in REQUIRED_PBP_COLUMNS if c not in pbp.columns]
    if missing:
        print(f"ERROR: PBP missing required columns: {missing}", file=sys.stderr)
        return 1

    print("PBP columns (sample):", sorted(pbp.columns)[:25])

    for team in ("GB", "DET"):
        team_pbp = pbp[(pbp["posteam"] == team) | (pbp["defteam"] == team)]
        print(f"Team {team}: {len(team_pbp)} PBP rows")
        if team_pbp.empty:
            print(f"WARNING: No PBP rows found for team {team} in {season}")

    print("NFL data load sanity check PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
