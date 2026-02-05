#!/usr/bin/env python3
"""
Train the score prediction model on POST games and save artifacts to outputs/score_model.json.

Usage:
  python scripts/train_score_model.py [--years 2010 2011 ... 2024] [--out outputs/score_model.json]
"""

import argparse
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import get_pbp, get_schedules, SeasonNotAvailableError
from superbowlengine.models.score_model import fit_score_model, save_artifacts

DEFAULT_YEARS = list(range(2010, 2026))  # through 2025 for 2025-2026 Super Bowl


def main() -> None:
    parser = argparse.ArgumentParser(description="Train score model on POST games; save artifacts.")
    parser.add_argument("--years", nargs="+", type=int, default=DEFAULT_YEARS,
                        help="Season years for training (default 2010..2025)")
    parser.add_argument("--out", default="outputs/score_model.json", help="Output JSON path")
    parser.add_argument("--alpha", type=float, default=1.0, help="Ridge alpha")
    args = parser.parse_args()
    years = args.years
    outpath = args.out
    try:
        pbp = get_pbp(years, season_type="ALL", columns=list(DEFAULT_CONFIG.pbp_columns))
    except SeasonNotAvailableError as e:
        print(f"Data not available: {e}")
        sys.exit(1)
    pbp_post = pbp[pbp["season_type"] == "POST"]
    if pbp_post.empty:
        print("No POST games in range.")
        sys.exit(1)
    schedules = get_schedules(years)
    artifacts = fit_score_model(
        years,
        pbp_post=pbp_post,
        schedules=schedules,
        sos_z_map=None,
        alpha=args.alpha,
    )
    save_artifacts(artifacts, outpath)
    print(f"Fitted on {artifacts.n_samples} POST games. Saved to {outpath}")


if __name__ == "__main__":
    main()
