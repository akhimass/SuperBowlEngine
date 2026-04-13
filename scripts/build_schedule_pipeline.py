from __future__ import annotations

import argparse
import sys
from typing import Any, Dict

from gridironiq.schedule_engine import (
    Phase,
    run_schedule_predictions,
    run_schedule_reports,
)
from gridironiq.pipeline_cache import (
    save_game_report_cached,
    save_schedule_predictions,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build season-wide schedule predictions and reports for GridironIQ.")
    parser.add_argument("--season", type=int, required=True, help="Season year, e.g. 2024")
    parser.add_argument(
        "--phase",
        type=str,
        default="all",
        choices=["all", "regular", "postseason"],
        help="Which part of the schedule to build.",
    )
    parser.add_argument(
        "--build-reports",
        action="store_true",
        help="Also build full game reports for each matchup (slower).",
    )

    args = parser.parse_args(argv)
    season: int = args.season
    phase_raw: str = args.phase
    phase_typed: Phase = phase_raw  # type: ignore[assignment]

    print(f"Building schedule pipeline for season={season}, phase={phase_raw}...", flush=True)

    games = run_schedule_predictions(season=season, phase=phase_typed)
    save_schedule_predictions(season, phase_raw, games)
    print(f"- Predictions computed for {len(games)} games.", flush=True)

    reports_built = 0
    if args.build_reports:
        report_index: Dict[str, Dict[str, Any]] = run_schedule_reports(season=season, phase=phase_typed)
        for game_id, report in report_index.items():
            save_game_report_cached(season, game_id, report)
        reports_built = len(report_index)
        print(f"- Full reports built for {reports_built} games.", flush=True)

    print("Done.", flush=True)
    print(
        f"Summary: season={season}, phase={phase_raw}, games={len(games)}, reports={reports_built}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

