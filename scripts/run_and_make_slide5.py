#!/usr/bin/env python3
"""
Produce outputs/slide5_prediction.png and outputs/prediction.json from real model output.

Loads PBP via nflreadpy (REG + POST), computes TeamKeys for the two teams,
builds contexts (SOS z from REG, expected TO from turnover regression, DGI=0),
calls predict(), then renders the slide and writes the prediction JSON.

Caching: use nflreadpy env vars (NFLREADPY_CACHE=filesystem, NFLREADPY_CACHE_DIR).
"""

import argparse
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

try:
    import pandas  # noqa: F401
except ModuleNotFoundError:
    print("Missing dependency: pandas. Install project deps from repo root:")
    print("  pip install -e .")
    sys.exit(1)

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import get_pbp, get_schedules, validate_pbp_for_keys, SeasonNotAvailableError
from superbowlengine.features.keys import compute_team_keys
from superbowlengine.features.keys_pipeline import prepare_keys_for_matchup
from superbowlengine.features.sos import (
    build_game_results,
    compute_sos,
    zscore_sos,
)
from superbowlengine.models.professor_keys import TeamContext, predict
from superbowlengine.models.score_model import load_artifacts, predict_score
from superbowlengine.models.turnover_regression import expected_turnovers
from superbowlengine.utils.math import safe_div
from superbowlengine.viz.slide5 import render_slide5_prediction
from superbowlengine.viz.slide5_explainer import render_slide5_explainer
from superbowlengine.analysis.rank_keys import compute_ranks_for_matchup

OUTPUTS_DIR = repo / "outputs"
SLIDE5_PATH = OUTPUTS_DIR / "slide5_prediction.png"
SLIDE5_EXPLAINER_PATH = OUTPUTS_DIR / "slide5_explainer.png"
PREDICTION_JSON_PATH = OUTPUTS_DIR / "prediction.json"

DGI_DEFAULT = 0.0


def _games_played(game_results, team: str) -> int:
    """Number of games a team played in game_results (one row per game)."""
    if game_results.empty:
        return 0
    home = (game_results["home_team"] == team).sum()
    away = (game_results["away_team"] == team).sum()
    return int(home + away)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run model and generate Slide 5 PNG + prediction.json")
    parser.add_argument("--year", type=int, default=2024, help="Season year")
    parser.add_argument("--team-a", default="SEA", help="First team (e.g. SEA)")
    parser.add_argument("--team-b", default="NE", help="Second team (e.g. NE)")
    parser.add_argument("--season-type", default="POST", choices=("POST", "REG"), help="Season type for matchup keys")
    parser.add_argument("--mode", default="opp_weighted", choices=("aggregate", "per_game", "opp_weighted"),
                        help="Keys aggregation: aggregate (sum), per_game (avg), opp_weighted (avg by opponent strength + TO dampen)")
    parser.add_argument("--debug", action="store_true", help="Print key_winners, keys_won, margins, contributions, logit, probabilities; and per-game table when mode is per_game/opp_weighted")
    args = parser.parse_args()

    year = args.year
    team_a = args.team_a
    team_b = args.team_b
    season_type = args.season_type
    columns = list(DEFAULT_CONFIG.pbp_columns)

    try:
        # 1) Load PBP (REG + POST) via nflreadpy
        pbp = get_pbp([year], season_type="ALL", columns=columns)
    except SeasonNotAvailableError as e:
        print(f"Data not published yet for {year} {season_type}: {e}")
        sys.exit(1)

    validate_pbp_for_keys(pbp)

    if "season_type" not in pbp.columns:
        raise RuntimeError("PBP missing 'season_type'; cannot filter REG/POST.")

    pbp_reg = pbp[pbp["season_type"] == "REG"]
    pbp_post = pbp[pbp["season_type"] == "POST"]

    if pbp_post.empty:
        print(f"Data not published yet for {year} POST (no postseason rows).")
        sys.exit(1)

    # Data summary
    n_rows = len(pbp)
    n_games = pbp["game_id"].nunique() if "game_id" in pbp.columns else 0
    teams = set()
    if "posteam" in pbp.columns:
        teams = set(pbp["posteam"].dropna().unique()) - {""}
    print("Data summary: rows=%d, games=%d, season_type=ALL (REG+POST), teams=%s" % (
        n_rows, n_games, sorted(teams)[:20] if len(teams) <= 20 else "%d teams" % len(teams),
    ))

    # 2) TeamKeys for matchup (POST): aggregate, per_game, or opp_weighted
    schedules = get_schedules([year])
    keys_a, keys_b, per_game_a, per_game_b = prepare_keys_for_matchup(
        pbp_post, schedules, team_a, team_b,
        mode=args.mode,
        reg_pbp=pbp_reg,
    )

    # 3) Contexts: SOS z from REG, expected_turnovers_per_game, DGI=0
    game_results_reg = build_game_results(pbp, season_type="REG")
    game_results_post = build_game_results(pbp, season_type="POST")

    all_teams = set()
    if not game_results_reg.empty:
        all_teams = set(game_results_reg["home_team"].dropna()) | set(game_results_reg["away_team"].dropna())
    all_team_sos = {t: compute_sos(game_results_reg, t) for t in all_teams}
    sos_z_map = zscore_sos(all_team_sos)
    sos_z_a = sos_z_map.get(team_a, 0.0)
    sos_z_b = sos_z_map.get(team_b, 0.0)

    reg_keys_a = compute_team_keys(pbp_reg, team_a)
    reg_keys_b = compute_team_keys(pbp_reg, team_b)
    gp_reg_a = _games_played(game_results_reg, team_a)
    gp_reg_b = _games_played(game_results_reg, team_b)
    gp_post_a = _games_played(game_results_post, team_a)
    gp_post_b = _games_played(game_results_post, team_b)

    season_to_pg_a = safe_div(reg_keys_a.turnovers, gp_reg_a) if gp_reg_a else 0.0
    season_to_pg_b = safe_div(reg_keys_b.turnovers, gp_reg_b) if gp_reg_b else 0.0
    post_to_pg_a = safe_div(keys_a.turnovers, gp_post_a) if gp_post_a else 0.0
    post_to_pg_b = safe_div(keys_b.turnovers, gp_post_b) if gp_post_b else 0.0

    expected_to_a = expected_turnovers(season_to_pg_a, post_to_pg_a)
    expected_to_b = expected_turnovers(season_to_pg_b, post_to_pg_b)

    ctx_a = TeamContext(sos_z=sos_z_a, expected_turnovers_per_game=expected_to_a, dgi=DGI_DEFAULT)
    ctx_b = TeamContext(sos_z=sos_z_b, expected_turnovers_per_game=expected_to_b, dgi=DGI_DEFAULT)

    # 4) Unified predict (professor_keys only — no score model in calculations)
    out = predict(
        keys_a,
        keys_b,
        team_a_name=team_a,
        team_b_name=team_b,
        context_a=ctx_a,
        context_b=ctx_b,
    )

    # 4b) Score prediction for display only (scoreboard on slide; not used for win prob or winner)
    score_artifacts = load_artifacts(str(OUTPUTS_DIR / "score_model.json"))
    score_out = predict_score(
        keys_a, keys_b,
        context_a=ctx_a, context_b=ctx_b,
        artifacts=score_artifacts,
        team_a_name=team_a, team_b_name=team_b,
        neutral_site=True,
    )

    if args.debug:
        print("--- DEBUG ---")
        if per_game_a is not None and not per_game_a.empty:
            cols = ["game_id", "opp", "top_min", "turnovers", "big_plays", "third_down_pct", "redzone_td_pct", "weight"]
            print("Per-game keys", team_a + ":")
            print(per_game_a[[c for c in cols if c in per_game_a.columns]].to_string())
        if per_game_b is not None and not per_game_b.empty:
            cols = ["game_id", "opp", "top_min", "turnovers", "big_plays", "third_down_pct", "redzone_td_pct", "weight"]
            print("Per-game keys", team_b + ":")
            print(per_game_b[[c for c in cols if c in per_game_b.columns]].to_string())
        print("Aggregated keys:", team_a, "TOP=%.2f TO=%d BIG=%d 3D=%.2f RZ=%.2f" % (
            keys_a.top_min, keys_a.turnovers, keys_a.big_plays, keys_a.third_down_pct, keys_a.redzone_td_pct))
        print("Aggregated keys:", team_b, "TOP=%.2f TO=%d BIG=%d 3D=%.2f RZ=%.2f" % (
            keys_b.top_min, keys_b.turnovers, keys_b.big_plays, keys_b.third_down_pct, keys_b.redzone_td_pct))
        print("key_winners:", out["explanation"].key_winners)
        print("keys_won:", out["keys_won"])
        print("ties:", out["ties"], "tied_keys:", out["tied_keys"])
        print("margin_table:", out["explanation"].margin_table)
        print("contributions:", out["explanation"].contributions)
        print("logit:", out["logit"])
        print("p_team_a_win:", out["p_team_a_win"], "p_team_b_win:", out["p_team_b_win"])
        print("predicted_winner:", out["predicted_winner"])
        print("-------------")

    # 5) Schema for render_slide5_prediction
    pred_for_viz = {
        "p_team_a_win": out["p_team_a_win"],
        "p_team_b_win": out["p_team_b_win"],
        "predicted_winner": out["predicted_winner"],
        "keys_won": out["keys_won"],
        "key_winners": out["explanation"].key_winners,
    }
    if team_a == "SEA" and team_b == "NE":
        pred_for_viz["p_sea_win"] = out["p_team_a_win"]
        pred_for_viz["p_ne_win"] = out["p_team_b_win"]

    # 6) Ranks (percentiles among POST teams) and explainer
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    ranks = compute_ranks_for_matchup(pbp_post, schedules, team_a, team_b, mode=args.mode, reg_pbp=pbp_reg)
    pred_for_explainer = {
        "p_team_a_win": out["p_team_a_win"],
        "p_team_b_win": out["p_team_b_win"],
        "predicted_winner": out["predicted_winner"],
        "keys_won": out["keys_won"],
        "ties": out["ties"],
        "tied_keys": out["tied_keys"],
        "key_winners": out["explanation"].key_winners,
        "top_3_drivers": out["top_3_drivers"],
        "explanation": out["explanation"],
        "predicted_score": score_out["predicted_score"],
        "score_ci": score_out["score_ci"],
    }
    saved_explainer = render_slide5_explainer(
        pred_for_explainer,
        keys_a,
        keys_b,
        per_game_a=per_game_a,
        per_game_b=per_game_b,
        ranks=ranks,
        outpath=str(SLIDE5_EXPLAINER_PATH),
        year=year,
        mode=args.mode,
        logo_dir=repo,
    )
    print("Saved explainer PNG:", saved_explainer)
    saved_png = render_slide5_prediction(pred_for_viz, outpath=str(SLIDE5_PATH))
    print("Saved PNG:", saved_png)

    # 7) Full pred dict for JSON (prediction from professor_keys; score from score model for display only)
    full_pred = {
        "p_team_a_win": out["p_team_a_win"],
        "p_team_b_win": out["p_team_b_win"],
        "predicted_winner": out["predicted_winner"],
        "keys_won": out["keys_won"],
        "ties": out["ties"],
        "tied_keys": out["tied_keys"],
        "predicted_score": score_out["predicted_score"],
        "predicted_margin": score_out["predicted_margin"],
        "predicted_total": score_out["predicted_total"],
        "score_ci": score_out["score_ci"],
        "top_3_drivers": out["top_3_drivers"],
        "logit": out["logit"],
        "explanation": {
            "key_winners": out["explanation"].key_winners,
            "margin_table": out["explanation"].margin_table,
            "driver_ranking": out["explanation"].driver_ranking,
        },
    }
    if team_a == "SEA" and team_b == "NE":
        full_pred["p_sea_win"] = out["p_team_a_win"]
        full_pred["p_ne_win"] = out["p_team_b_win"]

    with open(PREDICTION_JSON_PATH, "w") as f:
        json.dump(full_pred, f, indent=2)
    print("Saved JSON:", PREDICTION_JSON_PATH)


if __name__ == "__main__":
    main()
