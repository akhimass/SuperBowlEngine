from __future__ import annotations

"""
Audit script to inspect score model distribution over a season.

Usage:
  uv run python scripts/audit_score_distribution.py --season 2024
"""

import argparse

import pandas as pd

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import get_pbp, get_schedules, validate_pbp_for_keys
from superbowlengine.features.keys_pipeline import prepare_keys_for_matchup
from superbowlengine.models.score_model import load_artifacts, predict_score


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()

    season = args.season
    columns = list(DEFAULT_CONFIG.pbp_columns)
    pbp = get_pbp([season], season_type="ALL", columns=columns)
    validate_pbp_for_keys(pbp)
    schedules = get_schedules([season])
    artifacts = load_artifacts()

    rows = []
    for _, row in schedules.iterrows():
        home = str(row["home_team"])
        away = str(row["away_team"])
        try:
            keys_a, keys_b, _, _ = prepare_keys_for_matchup(
                pbp,
                schedules,
                home,
                away,
                mode="opp_weighted",
                reg_pbp=None,
            )
            score = predict_score(keys_a, keys_b, artifacts=artifacts, team_a_name=home, team_b_name=away)
            rows.append(
                {
                    "home_team": home,
                    "away_team": away,
                    "pred_margin": score["predicted_margin"],
                    "pred_total": score["predicted_total"],
                    "home_score": score["predicted_score"][home],
                    "away_score": score["predicted_score"][away],
                    "score_clamped": score["score_ci"].get("score_clamped", False),
                }
            )
        except Exception:
            continue

    df = pd.DataFrame(rows)
    if df.empty:
        print("No games scored.")
        return 0

    print("=== Score distribution summary ===")
    print("Games:", len(df))
    print("Total points: mean", df["pred_total"].mean().round(1), "min", df["pred_total"].min(), "max", df["pred_total"].max())
    print("Margin: mean", df["pred_margin"].mean().round(1), "min", df["pred_margin"].min(), "max", df["pred_margin"].max())
    print("Home score: min", df["home_score"].min(), "max", df["home_score"].max())
    print("Away score: min", df["away_score"].min(), "max", df["away_score"].max())
    print("Clamped scores:", int(df["score_clamped"].sum()))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

