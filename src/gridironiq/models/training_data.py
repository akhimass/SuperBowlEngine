from __future__ import annotations

"""
Leakage-safe training row builder for GridironIQ v2 models.

Key principle: for each historical game, compute matchup features using ONLY games
played earlier in the same season (and optionally earlier playoff rounds).
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import get_pbp, get_schedules

from gridironiq.models.matchup_features import (
    MatchupFeatures,
    build_matchup_features,
    _load_pbp_and_schedules_for_efficiency,  # noqa: PLC2701
)


FEATURE_COLS = [
    "epa_edge",
    "success_edge",
    "explosive_edge",
    "early_down_success_edge",
    "third_down_edge",
    "redzone_edge",
    "sack_edge",
    "sos_edge",
    "recent_epa_edge",
]


def _season_games_sorted(schedules: pd.DataFrame) -> pd.DataFrame:
    df = schedules.copy()
    if "season_type" not in df.columns and "game_type" in df.columns:
        df = df.rename(columns={"game_type": "season_type"})
    df["season_type"] = df.get("season_type", "").astype(str).str.upper()
    # Week sometimes missing for postseason; keep stable ordering by week then game_id.
    w = pd.to_numeric(df.get("week", pd.NA), errors="coerce")
    df = df.assign(_week=w.fillna(99))
    df = df.sort_values(["season_type", "_week", "game_id"])
    return df


def _pbp_prior_for_game(pbp_all: pd.DataFrame, season_type: str, week: Any) -> pd.DataFrame:
    """
    Return PBP subset representing data available before the given game.

    - For REG games: only REG plays with week < current week.
    - For POST games: REG plays for the season + POST plays with week < current week (if week present).
      If postseason week is unavailable, falls back to all REG plays (no POST learning for that game).
    """
    pbp = pbp_all.copy()
    if "season_type" in pbp.columns:
        pbp["season_type"] = pbp["season_type"].astype(str).str.upper()
    if "week" in pbp.columns:
        pbp["_week"] = pd.to_numeric(pbp["week"], errors="coerce")
    else:
        pbp["_week"] = pd.NA

    st = str(season_type).upper()
    wk = pd.to_numeric(pd.Series([week]), errors="coerce").iloc[0]

    if st == "REG":
        reg = pbp[pbp["season_type"] == "REG"].copy() if "season_type" in pbp.columns else pbp
        if pd.isna(wk):
            return reg.iloc[0:0]
        return reg[reg["_week"] < wk].copy()

    # POST
    reg = pbp[pbp["season_type"] == "REG"].copy() if "season_type" in pbp.columns else pbp
    if pd.isna(wk):
        return reg
    post_prior = pbp[(pbp["season_type"] == "POST") & (pbp["_week"] < wk)].copy()
    return pd.concat([reg, post_prior], ignore_index=True)


def _build_matchup_features_from_pbp(
    season: int,
    team_a: str,
    team_b: str,
    *,
    mode: str,
    pbp_prior: pd.DataFrame,
    schedules: pd.DataFrame,
    sos_z: Dict[str, float],
) -> MatchupFeatures:
    # We reuse the internal efficiency computations by temporarily calling the same
    # code path but with a provided pbp subset.
    from gridironiq.models.matchup_features import _compute_team_efficiency  # noqa: PLC0415

    eff_a = _compute_team_efficiency(pbp_prior, schedules, team_a, sos_z_map=sos_z)
    eff_b = _compute_team_efficiency(pbp_prior, schedules, team_b, sos_z_map=sos_z)

    epa_edge = (eff_a.off_epa_per_play - eff_b.def_epa_per_play_allowed) - (eff_b.off_epa_per_play - eff_a.def_epa_per_play_allowed)
    success_edge = (eff_a.off_success_rate - eff_b.def_success_rate_allowed) - (eff_b.off_success_rate - eff_a.def_success_rate_allowed)
    explosive_edge = (eff_a.off_explosive_rate - eff_b.def_explosive_rate_allowed) - (eff_b.off_explosive_rate - eff_a.def_explosive_rate_allowed)
    early_edge = (eff_a.off_early_down_success - eff_b.def_early_down_success_allowed) - (eff_b.off_early_down_success - eff_a.def_early_down_success_allowed)
    third_edge = (eff_a.off_third_down_conv - eff_b.def_third_down_conv_allowed) - (eff_b.off_third_down_conv - eff_a.def_third_down_conv_allowed)
    rz_edge = (eff_a.off_redzone_td_rate - eff_b.def_redzone_td_rate_allowed) - (eff_b.off_redzone_td_rate - eff_a.def_redzone_td_rate_allowed)

    def _nz(x: Optional[float]) -> float:
        return float(x) if (x is not None and x == x) else 0.0

    sack_edge = (
        (-_nz(eff_a.off_sack_rate_allowed) + _nz(eff_a.def_sack_rate_forced))
        - (-_nz(eff_b.off_sack_rate_allowed) + _nz(eff_b.def_sack_rate_forced))
    )
    sos_edge = eff_a.sos_z - eff_b.sos_z

    recent_a = eff_a.recent_off_epa_per_play if eff_a.recent_off_epa_per_play is not None else eff_a.off_epa_per_play
    recent_b = eff_b.recent_off_epa_per_play if eff_b.recent_off_epa_per_play is not None else eff_b.off_epa_per_play
    recent_epa_edge = float(recent_a - recent_b)

    return MatchupFeatures(
        season=season,
        mode=mode,
        team_a=team_a,
        team_b=team_b,
        epa_edge=float(epa_edge),
        success_edge=float(success_edge),
        explosive_edge=float(explosive_edge),
        early_down_success_edge=float(early_edge),
        third_down_edge=float(third_edge),
        redzone_edge=float(rz_edge),
        sack_edge=float(sack_edge),
        sos_edge=float(sos_edge),
        recent_epa_edge=float(recent_epa_edge),
        team_a_eff=eff_a,
        team_b_eff=eff_b,
    )


def build_training_rows_for_season(season: int) -> pd.DataFrame:
    # Load PBP with efficiency columns
    extra_cols = ["epa", "success", "sack", "first_down", "season"]
    cols = list(dict.fromkeys(list(DEFAULT_CONFIG.pbp_columns) + extra_cols))
    pbp_all = get_pbp([season], season_type="ALL", columns=cols)
    schedules = get_schedules([season])
    games = _season_games_sorted(schedules)

    # Only completed games
    games = games[games["home_score"].notna() & games["away_score"].notna()].copy()
    if games.empty:
        return pd.DataFrame()

    # SOS z computed from REG results up to the season end is OK for training only if it does not leak.
    # To keep the pipeline simple and leakage-safe, we compute SOS from REG games only and do not use
    # future weeks SOS inside a given week's row; instead we rely on the current pbp_prior's derived SOS_z
    # which is computed from the same SOS_z_map passed in (can be 0 if unavailable).
    # Here we compute SOS_z_map from REG games in pbp_prior per row by recomputing from prior data.
    rows: List[Dict[str, Any]] = []

    for _, g in games.iterrows():
        home = str(g["home_team"])
        away = str(g["away_team"])
        week = g.get("week")
        season_type = str(g.get("season_type", "")).upper()

        # Pregame feature construction mode: use "regular" for REG; for POST we use "opp_weighted"
        mode = "regular" if season_type == "REG" else "opp_weighted"

        pbp_prior = _pbp_prior_for_game(pbp_all, season_type, week)
        # If no prior data (Week 1), skip row to avoid pure zeros dominating training.
        if pbp_prior.empty:
            continue

        # SOS_z map derived from prior REG game results only (leakage-safe)
        sos_z: Dict[str, float] = {}
        try:
            from superbowlengine.features.sos import build_game_results, compute_sos, zscore_sos  # noqa: PLC0415

            reg_prior = pbp_prior[pbp_prior["season_type"] == "REG"].copy() if "season_type" in pbp_prior.columns else pbp_prior
            gr = build_game_results(reg_prior, season_type="REG")
            if not gr.empty:
                teams = set(gr["home_team"]).union(set(gr["away_team"]))
                raw = {t: compute_sos(gr, t) for t in teams}
                sos_z = {k: float(v) for k, v in zscore_sos(raw).items()}
        except Exception:
            sos_z = {}

        feats = _build_matchup_features_from_pbp(
            season,
            home,
            away,
            mode=mode,
            pbp_prior=pbp_prior,
            schedules=schedules,
            sos_z=sos_z,
        )

        # Targets
        home_score = int(g["home_score"])
        away_score = int(g["away_score"])
        win_target = 1 if home_score > away_score else 0
        margin_target = home_score - away_score
        total_target = home_score + away_score

        r: Dict[str, Any] = {
            "season": season,
            "week": week,
            "season_type": season_type,
            "team_a": home,
            "team_b": away,
            "win_target": win_target,
            "margin_target": margin_target,
            "total_target": total_target,
        }
        for c in FEATURE_COLS:
            r[c] = getattr(feats, c)
        rows.append(r)

    return pd.DataFrame(rows)


def build_training_rows(seasons: List[int]) -> pd.DataFrame:
    parts = []
    for s in seasons:
        df = build_training_rows_for_season(int(s))
        if not df.empty:
            parts.append(df)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def save_training_rows_parquet(df: pd.DataFrame, path: str = "outputs/model_training/training_rows_2020_2025.parquet") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False)
    return p

