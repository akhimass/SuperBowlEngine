from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import SeasonNotAvailableError, get_pbp, get_schedules
from superbowlengine.qb.model import QBLine, compute_qb_metrics, qb_line_from_pbp, qb_production_score as qb_production_score_legacy
from superbowlengine.qb.production import (
    QBProdConfig,
    compute_opponent_def_strength,
    qb_components_per_game,
    qb_production_components,
    qb_production_score,
    validate_def_strength,
)
from superbowlengine.qb.validate import QBGameCheck, find_qb_games_post, qb_teams_in_post


@dataclass
class QBComparisonResult:
    qb_a: str
    team_a: str
    qb_b: str
    team_b: str
    season: int
    sustain_score: Dict[str, float]
    situational_score: Dict[str, float]
    offscript_score: Dict[str, float]
    total_score: Dict[str, float]
    avg_def_z: Dict[str, float]
    explanation: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_qb_pbp(season: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    columns = list(DEFAULT_CONFIG.pbp_columns)
    # Reuse the expanded column list from make_qb_prod_card
    extra_cols = [
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
    for c in extra_cols:
        if c not in columns:
            columns.append(c)

    try:
        pbp_reg = get_pbp([season], season_type="REG", columns=columns)
    except SeasonNotAvailableError as e:
        raise RuntimeError(f"REG data not available for season {season}: {e}") from e
    try:
        pbp_post = get_pbp([season], season_type="POST", columns=columns)
    except SeasonNotAvailableError as e:
        raise RuntimeError(f"POST data not available for season {season}: {e}") from e
    if pbp_post.empty:
        raise RuntimeError(f"No POST data for {season}; cannot compute postseason QB production.")

    schedules = get_schedules([season])
    if schedules.empty or "game_id" not in schedules.columns:
        raise RuntimeError("Schedules missing or empty; cannot validate QB games.")
    if "season" in schedules.columns:
        schedules = schedules[schedules["season"].astype(str) == str(season)]
    return pbp_reg, pbp_post, schedules


def _validate_qb_team(pbp_post: pd.DataFrame, qb: str, team: str, season: int) -> QBGameCheck:
    teams_with_qb = qb_teams_in_post(pbp_post, qb)
    if teams_with_qb and team not in teams_with_qb:
        raise RuntimeError(
            f"QB/team mismatch for {qb!r}: appears in POST PBP for teams {teams_with_qb}, not {team!r}."
        )
    return find_qb_games_post(pbp_post, get_schedules([season]), qb, team, season)


def compare_qbs(season: int, qb_a: str, team_a: str, qb_b: str, team_b: str) -> QBComparisonResult:
    """
    Thin wrapper around the existing QB production pipeline.

    - Uses REG + POST PBP and schedules via superbowlengine.data.
    - Validates that each QB played postseason games for the specified team.
    - Computes production components and scores for both QBs.
    - Returns compact scores + a JSON-friendly explanation dict.
    """
    pbp_reg, pbp_post, schedules = _load_qb_pbp(season)

    # Validation of QB/team combinations for POST
    try:
        check_a = find_qb_games_post(pbp_post, schedules, qb_a, team_a, season)
        check_b = find_qb_games_post(pbp_post, schedules, qb_b, team_b, season)
    except ValueError as e:
        raise RuntimeError(f"QB validation failed: {e}") from e

    config = QBProdConfig()
    def_strength = compute_opponent_def_strength(pbp_reg)
    validate_def_strength(def_strength)

    comp_a_df = qb_components_per_game(
        pbp_post,
        schedules,
        qb_a,
        team_a,
        def_strength,
        config,
        game_ids=check_a.game_ids,
    )
    comp_b_df = qb_components_per_game(
        pbp_post,
        schedules,
        qb_b,
        team_b,
        def_strength,
        config,
        game_ids=check_b.game_ids,
    )

    comp_a = qb_production_components(
        pbp_post,
        schedules,
        qb_a,
        team_a,
        def_strength,
        config,
        game_ids=check_a.game_ids,
    )
    comp_b = qb_production_components(
        pbp_post,
        schedules,
        qb_b,
        team_b,
        def_strength,
        config,
        game_ids=check_b.game_ids,
    )
    report_a = qb_production_score(comp_a, config)
    report_b = qb_production_score(comp_b, config)

    # Legacy box-score-based production score (for alignment with existing visuals)
    qb_line_a: Optional[QBLine] = qb_line_from_pbp(pbp_post, qb_a, team_a, check_a.game_ids)
    qb_line_b: Optional[QBLine] = qb_line_from_pbp(pbp_post, qb_b, team_b, check_b.game_ids)

    if qb_line_a:
        metrics_a = compute_qb_metrics(qb_line_a)
        legacy_a = qb_production_score_legacy(metrics_a)["total"]
        report_a["production_score"] = legacy_a
    if qb_line_b:
        metrics_b = compute_qb_metrics(qb_line_b)
        legacy_b = qb_production_score_legacy(metrics_b)["total"]
        report_b["production_score"] = legacy_b

    sustain_score = {qb_a: float(report_a.get("drive_sustain", 0)), qb_b: float(report_b.get("drive_sustain", 0))}
    situational_score = {qb_a: float(report_a.get("situational", 0)), qb_b: float(report_b.get("situational", 0))}
    offscript_score = {qb_a: float(report_a.get("offscript", 0)), qb_b: float(report_b.get("offscript", 0))}
    total_score = {qb_a: float(report_a.get("production_score", 0)), qb_b: float(report_b.get("production_score", 0))}
    avg_def_z = {qb_a: float(report_a.get("avg_def_z", 0)), qb_b: float(report_b.get("avg_def_z", 0))}

    explanation: Dict[str, Any] = {
        "qb_a": {
            "qb": qb_a,
            "team": team_a,
            "season": season,
            "components": comp_a,
            "per_game": comp_a_df.to_dict(orient="records") if not comp_a_df.empty else [],
        },
        "qb_b": {
            "qb": qb_b,
            "team": team_b,
            "season": season,
            "components": comp_b,
            "per_game": comp_b_df.to_dict(orient="records") if not comp_b_df.empty else [],
        },
    }

    return QBComparisonResult(
        qb_a=qb_a,
        team_a=team_a,
        qb_b=qb_b,
        team_b=team_b,
        season=season,
        sustain_score=sustain_score,
        situational_score=situational_score,
        offscript_score=offscript_score,
        total_score=total_score,
        avg_def_z=avg_def_z,
        explanation=explanation,
    )

