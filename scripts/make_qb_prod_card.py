#!/usr/bin/env python3
"""
Generate outputs/qb_prod_card.png and outputs/qb_prod_report_{qb}.json.

Loads PBP REG and POST separately, validates QB+team postseason games via find_qb_games_post,
computes per-game components and aggregates to production score (with def adjustment and
turnover attribution), then renders the card and writes full JSON reports.

If QB/team pairing is wrong (e.g. Darnold not on SEA for that year), fails fast with
a message listing which teams the QB appears for in POST PBP.

Usage:
  python scripts/make_qb_prod_card.py --year 2025 --qb-a "Drake Maye" --team-a NE --qb-b "Sam Darnold" --team-b SEA
"""

import argparse
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

try:
    import pandas as pd  # noqa: F401
except ModuleNotFoundError:
    print("Missing dependency: pandas. Install from repo root: pip install -e .")
    sys.exit(1)

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import get_pbp, get_schedules, SeasonNotAvailableError
from superbowlengine.qb.model import QBLine, compute_qb_metrics, qb_production_score as qb_production_score_legacy, qb_line_from_pbp
from superbowlengine.qb.production import (
    QBProdConfig,
    compute_opponent_def_strength,
    qb_components_per_game,
    qb_production_components,
    qb_production_score,
    qb_turnover_attribution,
    validate_def_strength,
)
from superbowlengine.qb.validate import find_qb_games_post, print_validation_table, qb_teams_in_post
from superbowlengine.viz.qb_prod_card import render_qb_prod_card

OUTPUTS_DIR = repo / "outputs"
QB_PROD_CARD_PATH = OUTPUTS_DIR / "qb_prod_card.png"

EXTRA_PBP_COLUMNS = [
    "passer_player_name",
    "rusher_player_name",
    "first_down",
    "air_yards",
    "qb_scramble",
    "qb_hit",
    "epa",
    "success",
    "pass_depth",
    "tipped_pass",
    "shotgun",
    "screen",
    "qb_sack_fumble",
    "no_play",
    "complete_pass",
]


def _safe_qb_label(qb: str) -> str:
    """Safe filename segment from QB name (e.g. 'Drake Maye' -> 'Drake_Maye')."""
    return qb.replace(" ", "_").replace("/", "_")[:30]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate QB Production Score card and JSON reports")
    parser.add_argument("--year", type=int, default=2025, help="Season year")
    parser.add_argument("--qb-a", default="Drake Maye", help="First QB display name")
    parser.add_argument("--team-a", default="NE", help="First QB team abbr")
    parser.add_argument("--qb-b", default="Sam Darnold", help="Second QB display name")
    parser.add_argument("--team-b", default="SEA", help="Second QB team abbr")
    parser.add_argument("--out", default=None, help="Output PNG path (default outputs/qb_prod_card.png)")
    parser.add_argument("--debug-def", action="store_true", help="Print defense strength debug + write outputs/def_strength_{year}.csv")
    args = parser.parse_args()

    year = args.year
    columns = list(DEFAULT_CONFIG.pbp_columns) + [c for c in EXTRA_PBP_COLUMNS if c not in DEFAULT_CONFIG.pbp_columns]

    try:
        pbp_reg = get_pbp([year], season_type="REG", columns=columns)
    except SeasonNotAvailableError as e:
        print(f"REG data not available: {e}")
        sys.exit(1)
    try:
        pbp_post = get_pbp([year], season_type="POST", columns=columns)
    except SeasonNotAvailableError as e:
        print(f"POST data not available: {e}")
        sys.exit(1)
    if pbp_post.empty:
        print(f"No POST data for {year}. Cannot compute postseason production.")
        sys.exit(1)

    schedules = get_schedules([year])
    if schedules.empty or "game_id" not in schedules.columns:
        print("Schedules missing or empty; cannot validate QB games.")
        sys.exit(1)
    if "season" in schedules.columns:
        schedules = schedules[schedules["season"].astype(str) == str(year)]

    # Fail fast if QB/team mismatch: ensure QB appears for given team in POST
    for qb, team in [(args.qb_a, args.team_a), (args.qb_b, args.team_b)]:
        teams_with_qb = qb_teams_in_post(pbp_post, qb)
        if teams_with_qb and team not in teams_with_qb:
            print(f"QB/team mismatch: {qb!r} appears in POST PBP for teams {teams_with_qb}, not {team!r}.")
            print("Fix --team or --qb so they match, or confirm data (passer_player_name/rusher_player_name).")
            sys.exit(1)

    try:
        check_a = find_qb_games_post(pbp_post, schedules, args.qb_a, args.team_a, year)
        check_b = find_qb_games_post(pbp_post, schedules, args.qb_b, args.team_b, year)
    except ValueError as e:
        print(f"Validation failed: {e}")
        sys.exit(1)

    print("Postseason games and QB play counts (validation):")
    print_validation_table(check_a, schedules)
    print_validation_table(check_b, schedules)

    config = QBProdConfig()
    def_strength = compute_opponent_def_strength(pbp_reg)
    # Validate defense z-scores
    try:
        validate_def_strength(def_strength)
    except ValueError as e:
        print(f"Defense strength validation failed: {e}")
        sys.exit(1)

    if args.debug_def:
        ds = pd.DataFrame([{"defteam": k, "def_z": v} for k, v in def_strength.items()])
        ds = ds.sort_values("def_z", ascending=False).reset_index(drop=True)
        out_csv = OUTPUTS_DIR / f"def_strength_{year}.csv"
        ds.to_csv(out_csv, index=False)
        print("\nDefense strength (top 5 toughest):")
        print(ds.head(5).to_string(index=False))
        print("\nDefense strength (bottom 5 easiest):")
        print(ds.tail(5).to_string(index=False))
        print("\nWrote:", out_csv)

    per_game_a = qb_components_per_game(pbp_post, schedules, args.qb_a, args.team_a, def_strength, config, game_ids=check_a.game_ids)
    per_game_b = qb_components_per_game(pbp_post, schedules, args.qb_b, args.team_b, def_strength, config, game_ids=check_b.game_ids)

    if args.debug_def:
        print("\nOpponent defenses faced (QB A):")
        if not per_game_a.empty:
            print(per_game_a[["game_id", "opp", "opp_def_z"]].to_string(index=False))
        print("\nOpponent defenses faced (QB B):")
        if not per_game_b.empty:
            print(per_game_b[["game_id", "opp", "opp_def_z"]].to_string(index=False))

    print("\nPer-game component metrics (QB A):")
    if not per_game_a.empty:
        print(per_game_a.to_string(index=False))
    else:
        print("  (none)")
    print("\nPer-game component metrics (QB B):")
    if not per_game_b.empty:
        print(per_game_b.to_string(index=False))
    else:
        print("  (none)")

    comp_a = qb_production_components(pbp_post, schedules, args.qb_a, args.team_a, def_strength, config, game_ids=check_a.game_ids)
    comp_b = qb_production_components(pbp_post, schedules, args.qb_b, args.team_b, def_strength, config, game_ids=check_b.game_ids)
    report_a = qb_production_score(comp_a, config)
    report_b = qb_production_score(comp_b, config)

    # Legacy production score (same as qb_compare.png) from box-score QBLine
    team_pbp_a = pbp_post[(pbp_post["posteam"] == args.team_a) & (pbp_post["game_id"].isin(check_a.game_ids))]
    team_pbp_b = pbp_post[(pbp_post["posteam"] == args.team_b) & (pbp_post["game_id"].isin(check_b.game_ids))]
    qb_line_a = qb_line_from_pbp(pbp_post, args.qb_a, args.team_a, check_a.game_ids)
    qb_line_b = qb_line_from_pbp(pbp_post, args.qb_b, args.team_b, check_b.game_ids)
    legacy_score_a = None
    legacy_score_b = None
    if qb_line_a:
        metrics_a = compute_qb_metrics(qb_line_a)
        legacy_score_a = qb_production_score_legacy(metrics_a)["total"]
    if qb_line_b:
        metrics_b = compute_qb_metrics(qb_line_b)
        legacy_score_b = qb_production_score_legacy(metrics_b)["total"]
    # Use legacy score on card when available (same as qb_compare)
    report_a["production_score"] = legacy_score_a if legacy_score_a is not None else report_a["production_score"]
    report_b["production_score"] = legacy_score_b if legacy_score_b is not None else report_b["production_score"]

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    outpath = args.out or str(QB_PROD_CARD_PATH)
    saved = render_qb_prod_card(args.qb_a, args.qb_b, report_a, report_b, outpath=outpath)
    print("\nSaved:", saved)

    def _row_to_jsonable(r):
        return {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()}

    per_a_list = [_row_to_jsonable(r) for r in per_game_a.to_dict(orient="records")] if not per_game_a.empty else []
    per_b_list = [_row_to_jsonable(r) for r in per_game_b.to_dict(orient="records")] if not per_game_b.empty else []
    attr_a = qb_turnover_attribution(team_pbp_a, args.qb_a, args.team_a)
    attr_b = qb_turnover_attribution(team_pbp_b, args.qb_b, args.team_b)
    report_a_full = {**report_a, "per_game": per_a_list, "qb": args.qb_a, "team": args.team_a, "year": year, "debug_counts": attr_a.get("debug_counts"), "attribution_notes": attr_a.get("notes", [])}
    report_b_full = {**report_b, "per_game": per_b_list, "qb": args.qb_b, "team": args.team_b, "year": year, "debug_counts": attr_b.get("debug_counts"), "attribution_notes": attr_b.get("notes", [])}
    json_a = OUTPUTS_DIR / f"qb_prod_report_{_safe_qb_label(args.qb_a)}.json"
    json_b = OUTPUTS_DIR / f"qb_prod_report_{_safe_qb_label(args.qb_b)}.json"
    with open(json_a, "w") as f:
        json.dump(report_a_full, f, indent=2)
    with open(json_b, "w") as f:
        json.dump(report_b_full, f, indent=2)
    print("Saved:", json_a, json_b)

    print(f"  {args.qb_a}: score={report_a['production_score']}  drive={report_a['drive_sustain']}  sit={report_a['situational']}  offscript={report_a['offscript']}  avg_def_z={report_a['avg_def_z']}")
    print(f"  {args.qb_b}: score={report_b['production_score']}  drive={report_b['drive_sustain']}  sit={report_b['situational']}  offscript={report_b['offscript']}  avg_def_z={report_b['avg_def_z']}")


if __name__ == "__main__":
    main()
