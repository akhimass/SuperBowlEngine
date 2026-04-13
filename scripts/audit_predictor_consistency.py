from __future__ import annotations

"""
Audit script to compare original SuperBowlEngine predictor vs current GridironIQ wrapper.

Usage:
  uv run python scripts/audit_predictor_consistency.py --season 2024 --team-a SEA --team-b NE
"""

import argparse

from gridironiq.matchup_engine import run_matchup as run_matchup_gridironiq
from superbowlengine.features.keys_pipeline import prepare_keys_for_matchup
from superbowlengine.data import get_pbp, get_schedules, validate_pbp_for_keys
from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.models.professor_keys import predict as predict_professor
from superbowlengine.models.score_model import load_artifacts, predict_score


def run_original(season: int, team_a: str, team_b: str) -> dict:
    columns = list(DEFAULT_CONFIG.pbp_columns)
    pbp = get_pbp([season], season_type="ALL", columns=columns)
    validate_pbp_for_keys(pbp)
    schedules = get_schedules([season])
    keys_a, keys_b, _, _ = prepare_keys_for_matchup(
        pbp,
        schedules,
        team_a,
        team_b,
        mode="opp_weighted",
        reg_pbp=None,
    )
    pred = predict_professor(keys_a, keys_b, team_a_name=team_a, team_b_name=team_b)
    artifacts = load_artifacts()
    score = predict_score(
        keys_a,
        keys_b,
        context_a=None,
        context_b=None,
        artifacts=artifacts,
        team_a_name=team_a,
        team_b_name=team_b,
    )
    return {
        "win_prob_a": pred["p_team_a_win"],
        "predicted_winner": pred["predicted_winner"],
        "predicted_margin": score["predicted_margin"],
        "predicted_total": score["predicted_total"],
        "predicted_score": score["predicted_score"],
    }


def run_gridironiq(season: int, team_a: str, team_b: str) -> dict:
    res = run_matchup_gridironiq(season, team_a, team_b, mode="opp_weighted")
    return {
        "win_prob_a": res.win_probability,
        "predicted_winner": res.predicted_winner,
        "projected_score": res.projected_score,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--team-a", type=str, required=True)
    parser.add_argument("--team-b", type=str, required=True)
    args = parser.parse_args()

    original = run_original(args.season, args.team_a, args.team_b)
    current = run_gridironiq(args.season, args.team_a, args.team_b)

    print("=== Original SuperBowlEngine ===")
    print(original)
    print("\n=== Current GridironIQ wrapper ===")
    print(current)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

