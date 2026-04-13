from dataclasses import dataclass, asdict
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import SeasonNotAvailableError, get_pbp, get_schedules, validate_pbp_for_keys
from superbowlengine.features.keys import TeamKeys
from superbowlengine.features.keys_pipeline import prepare_keys_for_matchup
from superbowlengine.features.sos import build_game_results, compute_sos, zscore_sos
from superbowlengine.models.professor_keys import TeamContext, predict
from superbowlengine.models.score_model import ScoreModelArtifacts, load_artifacts, predict_score

from gridironiq.models.matchup_features import build_matchup_features
from gridironiq.models.win_prob_model import load_artifacts as load_winprob_artifacts, predict_win_probability
from gridironiq.models.margin_model import load_artifacts as load_margin_artifacts, predict_margin
from gridironiq.models.total_model import load_artifacts as load_total_artifacts, predict_total


@dataclass
class MatchupResult:
    team_a: str
    team_b: str
    season: int
    mode: str
    win_probability: float  # probability team_a wins
    predicted_winner: str
    projected_score: Dict[str, int]
    keys_won: Dict[str, int]
    key_edges: Dict[str, float]
    top_drivers: Tuple[Tuple[str, float], ...]
    explanation: Dict[str, Any]
    # New v2 model fields (primary predictor)
    projected_margin: float | None = None
    projected_total: float | None = None
    team_efficiency_edges: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        # Ensure tuples are JSON-serialisable
        out["top_drivers"] = [list(p) for p in self.top_drivers]
        return out


@lru_cache(maxsize=16)
def _load_pbp_and_schedules(season: int) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load PBP and schedules for a season via nflreadpy-backed loaders."""
    columns = list(DEFAULT_CONFIG.pbp_columns)
    pbp = get_pbp([season], season_type="ALL", columns=columns)
    validate_pbp_for_keys(pbp)
    schedules = get_schedules([season])
    if "season" in schedules.columns:
        schedules = schedules[schedules["season"].astype(str) == str(season)]
    # Lightweight debug signal for audit/troubleshooting; relies on superbowlengine.data logging for details.
    if pbp.empty or schedules.empty:
        raise RuntimeError(f"PBP or schedules empty for season {season} (pbp_rows={len(pbp)}, sched_rows={len(schedules)})")
    return pbp, schedules


def _select_pbp_for_mode(pbp: pd.DataFrame, mode: str) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Returns (pbp_for_keys, pbp_reg_for_weights).

    - regular: keys from REG only, no REG weighting.
    - postseason: keys from POST only, no REG weighting.
    - opp_weighted: keys from POST, REG passed for opponent weights / SOS.
    """
    if "season_type" not in pbp.columns:
        raise RuntimeError("PBP missing 'season_type'; cannot separate REG/POST.")
    pbp_reg = pbp[pbp["season_type"] == "REG"].copy()
    pbp_post = pbp[pbp["season_type"] == "POST"].copy()

    if mode == "regular":
        return pbp_reg, None
    if mode in {"postseason", "opp_weighted"}:
        if pbp_post.empty:
            raise RuntimeError("No POST rows available for this season; cannot run postseason matchup.")
        reg_for_weights = pbp_reg if (mode == "opp_weighted") else None
        return pbp_post, reg_for_weights
    raise ValueError(f"Unsupported mode {mode!r} (expected 'regular', 'postseason', or 'opp_weighted').")


def run_matchup(season: int, team_a: str, team_b: str, mode: str = "opp_weighted") -> MatchupResult:
    """
    High-level wrapper around existing SuperBowlEngine logic.

    Steps:
    1. Load PBP (ALL) and schedules via superbowlengine.data.
    2. Slice PBP based on mode (regular/postseason/opp_weighted).
    3. Compute TeamKeys for both teams via prepare_keys_for_matchup.
    4. Build simple TeamContext using REG-season SOS when available.
    5. Run professor_keys.predict for win probability and explanation.
    6. Run score_model.predict_score for projected score.
    """
    try:
        pbp_all, schedules = _load_pbp_and_schedules(season)
    except SeasonNotAvailableError as e:
        raise RuntimeError(f"PBP not available for season {season}: {e}") from e

    pbp_for_keys, pbp_reg_for_weights = _select_pbp_for_mode(pbp_all, mode)
    if schedules.empty:
        raise RuntimeError(f"Schedules empty for season {season}; cannot run matchup.")

    # Prepare keys; reuse existing aggregation logic.
    keys_a, keys_b, _, _ = prepare_keys_for_matchup(
        pbp_for_keys,
        schedules,
        team_a,
        team_b,
        mode="opp_weighted" if mode == "opp_weighted" else "aggregate",
        reg_pbp=pbp_reg_for_weights,
    )
    if not isinstance(keys_a, TeamKeys) or not isinstance(keys_b, TeamKeys):
        raise RuntimeError("prepare_keys_for_matchup did not return TeamKeys objects as expected.")

    # Build simple SOS context from REG games when available.
    ctx_a = TeamContext()
    ctx_b = TeamContext()
    if pbp_reg_for_weights is not None and not pbp_reg_for_weights.empty:
        game_results_reg = build_game_results(pbp_all, season_type="REG")
        if not game_results_reg.empty:
            # Compute raw SOS per team then convert to z-scores
            sos_raw = {}
            teams = set(game_results_reg["home_team"]).union(set(game_results_reg["away_team"]))
            for t in teams:
                sos_raw[t] = compute_sos(game_results_reg, t)
            sos_z = zscore_sos(sos_raw)
            ctx_a = TeamContext(sos_z=float(sos_z.get(team_a, 0.0)))
            ctx_b = TeamContext(sos_z=float(sos_z.get(team_b, 0.0)))

    # --- Explainability layer (legacy 5 Keys) ---
    # Keep professor-keys output for scouting reports and top driver explanations,
    # but do NOT use it as the primary win/score predictor.
    pred_5k = predict(
        keys_a,
        keys_b,
        team_a_name=team_a,
        team_b_name=team_b,
        context_a=ctx_a,
        context_b=ctx_b,
    )

    # --- Primary v2 predictor (efficiency + matchup features) ---
    feats = build_matchup_features(season, team_a, team_b, mode=mode)
    win_art = load_winprob_artifacts()
    margin_art = load_margin_artifacts()
    total_art = load_total_artifacts()

    win_out = predict_win_probability(feats, artifacts=win_art)
    margin_out = predict_margin(feats, artifacts=margin_art)
    total_out = predict_total(feats, artifacts=total_art)

    win_prob = float(win_out["win_probability"])
    predicted_winner = team_a if win_prob >= 0.5 else team_b

    # Reconstruct projected score from margin + total (team_a perspective)
    proj_margin = float(margin_out["predicted_margin"])
    proj_total = float(total_out["predicted_total"])
    a_score = max(0, round((proj_total + proj_margin) / 2.0))
    b_score = max(0, round((proj_total - proj_margin) / 2.0))
    score_out = {
        "predicted_margin": proj_margin,
        "predicted_total": proj_total,
        "predicted_score": {team_a: int(a_score), team_b: int(b_score)},
        "model_debug": {
            "win_prob": win_out,
            "margin": margin_out,
            "total": total_out,
        },
    }

    explanation = pred_5k.get("explanation")
    expl_dict: Dict[str, Any] = {}
    if explanation is not None:
        # Explanation is a dataclass; use vars() to convert to a plain dict.
        expl_dict = vars(explanation)

    result = MatchupResult(
        team_a=team_a,
        team_b=team_b,
        season=season,
        mode=mode,
        win_probability=round(win_prob, 3),
        predicted_winner=predicted_winner,
        projected_score=score_out.get("predicted_score", {}),
        keys_won=pred_5k.get("keys_won", {}),
        key_edges=expl_dict.get("margin_table", {}),
        top_drivers=tuple(expl_dict.get("driver_ranking", pred_5k.get("top_3_drivers", []))),
        explanation=expl_dict,
        projected_margin=proj_margin,
        projected_total=proj_total,
        team_efficiency_edges={
            "epa_edge": feats.epa_edge,
            "success_edge": feats.success_edge,
            "explosive_edge": feats.explosive_edge,
            "early_down_success_edge": feats.early_down_success_edge,
            "third_down_edge": feats.third_down_edge,
            "redzone_edge": feats.redzone_edge,
            "sack_edge": feats.sack_edge,
            "sos_edge": feats.sos_edge,
            "recent_epa_edge": feats.recent_epa_edge,
            "team_a_efficiency": feats.team_a_eff.to_dict(),
            "team_b_efficiency": feats.team_b_eff.to_dict(),
        },
    )
    return result

