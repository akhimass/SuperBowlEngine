"""
Score prediction from 5 Keys margins: Ridge regression on historical POST games.

Predicts point differential and optional total points; outputs implied score with uncertainty.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from superbowlengine.features.keys import TeamKeys, compute_game_keys
from superbowlengine.models.professor_keys import TeamContext

# Feature names for margin model (team A - team B from A's perspective; TO: fewer giveaways = positive)
FEATURE_NAMES = ["margin_top", "margin_to", "margin_big", "margin_3d", "margin_rz", "sos_z"]


@dataclass
class ScoreModelArtifacts:
    """Fitted Ridge models and residual std for margin and total."""

    margin_coef: Dict[str, float] = field(default_factory=dict)
    margin_intercept: float = 0.0
    margin_std: float = 0.0
    total_coef: Optional[Dict[str, float]] = None
    total_intercept: float = 0.0
    total_std: float = 0.0
    feature_names: List[str] = field(default_factory=lambda: list(FEATURE_NAMES))
    n_samples: int = 0


def _keys_to_margin_row(keys_home: TeamKeys, keys_away: TeamKeys, sos_z_home: float = 0.0, sos_z_away: float = 0.0) -> Dict[str, float]:
    """One row of features: margins from home team perspective. TO margin = away_TO - home_TO (fewer giveaways = positive)."""
    return {
        "margin_top": keys_home.top_min - keys_away.top_min,
        "margin_to": float(keys_away.turnovers - keys_home.turnovers),
        "margin_big": float(keys_home.big_plays - keys_away.big_plays),
        "margin_3d": keys_home.third_down_pct - keys_away.third_down_pct,
        "margin_rz": keys_home.redzone_td_pct - keys_away.redzone_td_pct,
        "sos_z": sos_z_home - sos_z_away,
    }


def build_training_data(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    *,
    sos_z_map: Optional[Dict[str, float]] = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Build X (margins + sos_z), y_margin (point differential), y_total (total points) from POST games.

    Each row = one game. Features from home team perspective; y_margin = home_score - away_score.
    Uses schedule for final scores (home_score, away_score); falls back to PBP max if missing.
    """
    from superbowlengine.features.sos import build_game_results

    sos_z_map = sos_z_map or {}
    game_ids = pbp_post["game_id"].dropna().unique().tolist()
    rows = []
    for gid in game_ids:
        game_keys = compute_game_keys(pbp_post, gid)
        if len(game_keys) != 2:
            continue
        teams = list(game_keys.keys())
        home_row = pbp_post[pbp_post["game_id"] == gid].iloc[0]
        home_team = str(home_row["home_team"])
        away_team = str(home_row["away_team"])
        if home_team not in game_keys or away_team not in game_keys:
            continue
        keys_h = game_keys[home_team]
        keys_a = game_keys[away_team]
        row = _keys_to_margin_row(
            keys_h, keys_a,
            sos_z_home=sos_z_map.get(home_team, 0.0),
            sos_z_away=sos_z_map.get(away_team, 0.0),
        )
        # Scores: prefer schedule
        home_score = away_score = None
        if not schedules.empty and "game_id" in schedules.columns:
            sched = schedules[schedules["game_id"] == gid]
            if not sched.empty:
                c = sched.iloc[0]
                if "home_score" in c and "away_score" in c and pd.notna(c["home_score"]) and pd.notna(c["away_score"]):
                    home_score = int(c["home_score"])
                    away_score = int(c["away_score"])
        if home_score is None and "home_score" in pbp_post.columns:
            g = pbp_post[pbp_post["game_id"] == gid]
            home_score = int(g["home_score"].max())
            away_score = int(g["away_score"].max())
        if home_score is None:
            continue
        row["_home_score"] = home_score
        row["_away_score"] = away_score
        rows.append(row)
    if not rows:
        df = pd.DataFrame(columns=FEATURE_NAMES + ["_home_score", "_away_score"])
        return df[FEATURE_NAMES], pd.Series(dtype=float), pd.Series(dtype=float)
    df = pd.DataFrame(rows)
    X = df[FEATURE_NAMES]
    y_margin = df["_home_score"] - df["_away_score"]
    y_total = df["_home_score"] + df["_away_score"]
    return X, y_margin, y_total


def fit_score_model(
    pbp_years: List[int],
    *,
    pbp_post: Optional[pd.DataFrame] = None,
    schedules: Optional[pd.DataFrame] = None,
    sos_z_map: Optional[Dict[str, float]] = None,
    alpha: float = 1.0,
) -> ScoreModelArtifacts:
    """
    Fit Ridge regression for point differential and total points on POST games.

    If pbp_post/schedules are not provided, loads via get_pbp/get_schedules for pbp_years.
    Returns ScoreModelArtifacts with coefficients and residual std.
    """
    from sklearn.linear_model import Ridge

    if pbp_post is None or schedules is None:
        from superbowlengine.data import get_pbp, get_schedules
        from superbowlengine.config import DEFAULT_CONFIG
        pbp = get_pbp(pbp_years, season_type="ALL", columns=list(DEFAULT_CONFIG.pbp_columns))
        pbp_post = pbp[pbp["season_type"] == "POST"].copy()
        schedules = get_schedules(pbp_years)
    if pbp_post.empty:
        return ScoreModelArtifacts(n_samples=0)
    X, y_margin, y_total = build_training_data(pbp_post, schedules, sos_z_map=sos_z_map)
    if len(X) < 5:
        return ScoreModelArtifacts(n_samples=len(X))
    ridge = Ridge(alpha=alpha)
    ridge.fit(X, y_margin)
    pred_margin = ridge.predict(X)
    margin_std = float(pd.Series(y_margin - pred_margin).std())
    if margin_std != margin_std:
        margin_std = 0.0
    # Total model
    ridge_total = Ridge(alpha=alpha)
    ridge_total.fit(X, y_total)
    pred_total = ridge_total.predict(X)
    total_std = float(pd.Series(y_total - pred_total).std())
    if total_std != total_std:
        total_std = 0.0
    coef_margin = dict(zip(FEATURE_NAMES, ridge.coef_.tolist()))
    coef_total = dict(zip(FEATURE_NAMES, ridge_total.coef_.tolist()))
    return ScoreModelArtifacts(
        margin_coef=coef_margin,
        margin_intercept=float(ridge.intercept_),
        margin_std=margin_std,
        total_coef=coef_total,
        total_intercept=float(ridge_total.intercept_),
        total_std=total_std,
        feature_names=list(FEATURE_NAMES),
        n_samples=len(X),
    )


def predict_score(
    keys_a: TeamKeys,
    keys_b: TeamKeys,
    context_a: Optional[TeamContext] = None,
    context_b: Optional[TeamContext] = None,
    artifacts: Optional[ScoreModelArtifacts] = None,
    *,
    team_a_name: str = "SEA",
    team_b_name: str = "NE",
    neutral_site: bool = True,
) -> Dict[str, Any]:
    """
    Predict point differential and implied score from 5 Keys (and optional context).

    keys_a/keys_b are aggregated (e.g. opp_weighted) for the matchup.
    If artifacts is None, returns a no-model placeholder (margin 0, total 45, high uncertainty).
    """
    ctx_a = context_a or TeamContext()
    ctx_b = context_b or TeamContext()
    # Margins from team A perspective (A - B); TO = B.turnovers - A.turnovers
    margin_top = keys_a.top_min - keys_b.top_min
    margin_to = float(keys_b.turnovers - keys_a.turnovers)
    margin_big = float(keys_a.big_plays - keys_b.big_plays)
    margin_3d = keys_a.third_down_pct - keys_b.third_down_pct
    margin_rz = keys_a.redzone_td_pct - keys_b.redzone_td_pct
    sos_z = ctx_a.sos_z - ctx_b.sos_z
    x = {
        "margin_top": margin_top,
        "margin_to": margin_to,
        "margin_big": margin_big,
        "margin_3d": margin_3d,
        "margin_rz": margin_rz,
        "sos_z": sos_z,
    }
    if artifacts is None or artifacts.n_samples == 0:
        return {
            "predicted_margin": 0.0,
            "predicted_total": 45.0,
            "predicted_score": {team_a_name: 22, team_b_name: 23},
            "score_ci": {"margin_sd": 10.0, "total_sd": 10.0},
        }
    vec = [x[f] for f in FEATURE_NAMES]
    pred_margin = artifacts.margin_intercept + sum(artifacts.margin_coef[f] * vec[i] for i, f in enumerate(FEATURE_NAMES))
    pred_total = artifacts.total_intercept
    if artifacts.total_coef:
        pred_total += sum(artifacts.total_coef[f] * vec[i] for i, f in enumerate(FEATURE_NAMES))
    margin_sd = artifacts.margin_std
    total_sd = artifacts.total_std
    # Implied score: A_score + B_score = pred_total, A_score - B_score = pred_margin -> A = (total+margin)/2, B = (total-margin)/2
    a_score = (pred_total + pred_margin) / 2.0
    b_score = (pred_total - pred_margin) / 2.0
    a_score = max(0, round(a_score))
    b_score = max(0, round(b_score))
    return {
        "predicted_margin": round(pred_margin, 1),
        "predicted_total": round(pred_total, 1),
        "predicted_score": {team_a_name: int(a_score), team_b_name: int(b_score)},
        "score_ci": {"margin_sd": round(margin_sd, 2), "total_sd": round(total_sd, 2)},
    }


def load_artifacts(path: str = "outputs/score_model.json") -> Optional[ScoreModelArtifacts]:
    """Load ScoreModelArtifacts from JSON (e.g. outputs/score_model.json)."""
    p = Path(path)
    if not p.exists():
        return None
    import json
    with open(p) as f:
        d = json.load(f)
    return ScoreModelArtifacts(
        margin_coef=d.get("margin_coef", {}),
        margin_intercept=d.get("margin_intercept", 0.0),
        margin_std=d.get("margin_std", 0.0),
        total_coef=d.get("total_coef"),
        total_intercept=d.get("total_intercept", 0.0),
        total_std=d.get("total_std", 0.0),
        feature_names=d.get("feature_names", list(FEATURE_NAMES)),
        n_samples=d.get("n_samples", 0),
    )


def save_artifacts(artifacts: ScoreModelArtifacts, path: str = "outputs/score_model.json") -> None:
    """Save ScoreModelArtifacts to JSON."""
    import json
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    d = {
        "margin_coef": artifacts.margin_coef,
        "margin_intercept": artifacts.margin_intercept,
        "margin_std": artifacts.margin_std,
        "total_coef": artifacts.total_coef,
        "total_intercept": artifacts.total_intercept,
        "total_std": artifacts.total_std,
        "feature_names": artifacts.feature_names,
        "n_samples": artifacts.n_samples,
    }
    with open(p, "w") as f:
        json.dump(d, f, indent=2)
