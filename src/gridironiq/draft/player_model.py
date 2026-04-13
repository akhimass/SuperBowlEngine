from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .positions import POSITIONAL_VALUE, bucket_for_combine_pos


def _parse_height_inches(ht: Any) -> float:
    if ht is None or (isinstance(ht, float) and math.isnan(ht)):
        return float("nan")
    s = str(ht).strip()
    if "-" in s:
        a, b = s.split("-", 1)
        try:
            return float(a) * 12.0 + float(b)
        except ValueError:
            return float("nan")
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _clip01(x: float) -> float:
    return max(0.0, min(100.0, x))


def _num(x: Any, default: float = 50.0) -> float:
    if x is None:
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _invert_good(series: pd.Series, lower_is_better: bool) -> pd.Series:
    """Map raw values to higher-is-better within group; NaN preserved."""
    s = series.astype(float)
    if not lower_is_better:
        return s
    valid = s.dropna()
    if valid.empty:
        return s
    hi, lo = valid.max(), valid.min()
    if hi == lo:
        return s.apply(lambda v: 50.0 if pd.notna(v) else float("nan"))
    return s.apply(lambda v: lo + hi - v if pd.notna(v) else float("nan"))


def _percentile_rank_within(group: pd.DataFrame, col: str, lower_is_better: bool) -> pd.Series:
    if col not in group.columns:
        return pd.Series([float("nan")] * len(group), index=group.index)
    adj = _invert_good(group[col], lower_is_better=lower_is_better)
    r = adj.rank(pct=True, method="average")
    return (r * 100.0).where(adj.notna())


def athletic_components_by_bucket() -> Dict[str, List[Tuple[str, bool, float]]]:
    """
    (column, lower_is_better, weight) per coarse bucket.
    Weights sum to ~1 within bucket for non-NaN columns present.
    """
    speed = [
        ("forty", True, 0.35),
        ("shuttle", True, 0.2),
        ("cone", True, 0.15),
        ("vertical", False, 0.2),
        ("broad_jump", False, 0.1),
    ]
    line = [
        ("bench", False, 0.35),
        ("forty", True, 0.15),
        ("vertical", False, 0.15),
        ("broad_jump", False, 0.15),
        ("shuttle", True, 0.2),
    ]
    qb = [
        ("forty", True, 0.35),
        ("shuttle", True, 0.25),
        ("vertical", False, 0.2),
        ("broad_jump", False, 0.2),
    ]
    return {
        "QB": qb,
        "RB": speed,
        "WR": speed,
        "TE": line,
        "OT": line,
        "IOL": line,
        "EDGE": speed,
        "IDL": line,
        "LB": speed,
        "CB": speed,
        "SAF": speed,
        "ST": speed,
        "UNK": speed,
    }


def compute_athletic_score_row(
    combine_row: pd.Series,
    group_df: pd.DataFrame,
) -> float:
    bucket = bucket_for_combine_pos(str(combine_row.get("pos", "")))
    spec = athletic_components_by_bucket().get(bucket, athletic_components_by_bucket()["UNK"])
    parts: List[float] = []
    wsum = 0.0
    for col, low_is_good, w in spec:
        if col not in group_df.columns:
            continue
        pr = _percentile_rank_within(group_df, col, lower_is_better=low_is_good)
        val = float(pr.loc[combine_row.name]) if combine_row.name in pr.index else float("nan")
        if not math.isnan(val):
            parts.append(val * w)
            wsum += w
    if wsum <= 0:
        return 50.0
    return _clip01(sum(parts) / wsum)


def nfl_production_efficiency_scores(dp_row: Optional[pd.Series]) -> Tuple[float, float, str]:
    """
    Returns (production_0_100, efficiency_0_100, source_tag).
    Grounded in nflverse draft_picks career counting stats when present.
    """
    if dp_row is None:
        return 50.0, 50.0, "no_nflverse_draft_row"

    games = float(dp_row.get("games") or 0)
    pos = str(dp_row.get("position") or dp_row.get("pos") or "").upper()
    car_av = float(dp_row.get("car_av") or 0)

    if games <= 0:
        return 50.0, 50.0, "nflverse_draft_row_pre_rookie"

    av_per_g = car_av / max(games, 1.0)
    # Soft cap: ~0.15 AV/gm is excellent over a long career; scale to 0–100
    production = _clip01(av_per_g / 0.12 * 100.0)

    eff = 50.0
    if pos in {"QB"}:
        att = float(dp_row.get("pass_attempts") or 0)
        if att > 50:
            ypa = float(dp_row.get("pass_yards") or 0) / att
            tds = float(dp_row.get("pass_tds") or 0)
            ints = float(dp_row.get("pass_ints") or 0)
            td_rate = tds / att
            int_rate = ints / att
            eff = _clip01(50.0 + (ypa - 6.8) * 18.0 + (td_rate * 200.0) - (int_rate * 260.0))
    elif pos in {"RB"}:
        rush_att = float(dp_row.get("rush_atts") or dp_row.get("rush_attempts") or 0)
        if rush_att > 30:
            ypc = float(dp_row.get("rush_yards") or 0) / rush_att
            eff = _clip01(50.0 + (ypc - 4.2) * 35.0)
    elif pos in {"WR", "TE"}:
        tgt_proxy = float(dp_row.get("receptions") or 0) * 1.8
        if tgt_proxy > 30:
            ypr = float(dp_row.get("rec_yards") or 0) / max(float(dp_row.get("receptions") or 1), 1.0)
            td = float(dp_row.get("rec_tds") or 0)
            eff = _clip01(50.0 + (ypr - 11.0) * 6.0 + min(td, 40) * 0.6)
    elif pos in {"DE", "DT", "LB", "CB", "SAF", "EDGE", "OLB", "ILB", "DB", "S", "NT"}:
        solo = float(dp_row.get("def_solo_tackles") or 0)
        sk = float(dp_row.get("def_sacks") or 0)
        ints = float(dp_row.get("def_ints") or 0)
        if games > 0:
            eff = _clip01(45.0 + (solo / games) * 2.2 + (sk / max(games / 16.0, 1.0)) * 8.0 + ints * 3.0)

    return production, eff, "nflverse_draft_picks_career"


def age_adjustment_score(age: Optional[float], combine_season: int) -> float:
    """
    Slightly penalize older declare / rookie ages using combine season as reference.
    If age missing, neutral 50 -> maps to 0 adjustment in composite.
    """
    if age is None or (isinstance(age, float) and math.isnan(age)):
        return 50.0
    try:
        a = float(age)
    except (TypeError, ValueError):
        return 50.0
    # Typical rookie ~22; +1 year ~ -3 points on 0–100 scale
    delta = a - 22.0
    return _clip01(50.0 - delta * 3.0)


def combine_movement_efficiency_score(combine_row: pd.Series, pos_group: pd.DataFrame) -> float:
    """
    Measurable change-of-direction profile from combine (nflverse), within position.
    Used when nflverse career efficiency is not yet observable pre-rookie.
    """
    parts: List[float] = []
    for col, low_good in (("shuttle", True), ("cone", True)):
        if col not in pos_group.columns:
            continue
        pr = _percentile_rank_within(pos_group, col, lower_is_better=low_good)
        v = float(pr.loc[combine_row.name]) if combine_row.name in pr.index else float("nan")
        if not math.isnan(v):
            parts.append(v)
    if not parts:
        return 50.0
    return _clip01(sum(parts) / len(parts))


def _finish_prospect(
    wa: float,
    wp: float,
    we: float,
    wag: float,
    athletic: float,
    production: float,
    efficiency: float,
    age: float,
    pos: str,
    production_source: str,
    model_tag: str,
) -> Dict[str, Any]:
    pos_val = POSITIONAL_VALUE.get(pos, 1.0)
    wsum = wa + wp + we + wag
    if wsum <= 0:
        wsum = 1.0
    wa, wp, we, wag = wa / wsum, wp / wsum, we / wsum, wag / wsum
    base = wa * athletic + wp * production + we * efficiency + wag * age
    prospect = _clip01(base * (0.85 + 0.15 * pos_val))
    return {
        "prospect_score": round(prospect, 2),
        "athletic_score": round(athletic, 2),
        "production_score": round(production, 2),
        "efficiency_score": round(efficiency, 2),
        "age_adjustment": round(age, 2),
        "positional_value_mult": round(pos_val, 3),
        "production_source": production_source,
        "prospect_model": model_tag,
    }


def build_qb_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """Efficiency-forward; blend explosive proxy into athletic bucket."""
    a = float(player_data.get("athletic_score", 50))
    p = float(player_data.get("production_score", 50))
    e = float(player_data.get("efficiency_score", 50))
    age = float(player_data.get("age_adjustment", 50))
    ex = _num(player_data.get("cfb_explosiveness_score"), 50.0)
    ath_blend = 0.75 * a + 0.25 * ex
    return _finish_prospect(0.2, 0.22, 0.50, 0.08, ath_blend, p, e, age, "QB", str(player_data.get("production_source", "")), "qb")


def build_te_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inline movement + CFBD receiving usage/efficiency when matched."""
    a = float(player_data.get("athletic_score", 50))
    p = float(player_data.get("production_score", 50))
    e = float(player_data.get("efficiency_score", 50))
    age = float(player_data.get("age_adjustment", 50))
    usage = _num(player_data.get("cfb_te_usage_efficiency_score"), 50.0)
    e_blend = 0.58 * e + 0.42 * usage
    ex = _num(player_data.get("cfb_explosiveness_score"), 50.0)
    ath_blend = 0.66 * a + 0.34 * ex
    return _finish_prospect(0.22, 0.26, 0.44, 0.08, ath_blend, p, e_blend, age, "TE", str(player_data.get("production_source", "")), "te")


def build_wr_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """Speed + separation efficiency + explosive receiving proxy."""
    a = float(player_data.get("athletic_score", 50))
    p = float(player_data.get("production_score", 50))
    e = float(player_data.get("efficiency_score", 50))
    age = float(player_data.get("age_adjustment", 50))
    ex = _num(player_data.get("cfb_explosiveness_score"), 50.0)
    ath_blend = 0.7 * a + 0.3 * ex
    return _finish_prospect(0.30, 0.28, 0.38, 0.04, ath_blend, p, e, age, "WR", str(player_data.get("production_source", "")), "wr")


def build_edge_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """Production + pressure proxy folded into athletic weight."""
    a = float(player_data.get("athletic_score", 50))
    p = float(player_data.get("production_score", 50))
    e = float(player_data.get("efficiency_score", 50))
    age = float(player_data.get("age_adjustment", 50))
    pr = _num(player_data.get("cfb_pressure_proxy_score"), 50.0)
    ath_blend = 0.65 * a + 0.35 * pr
    return _finish_prospect(0.26, 0.30, 0.38, 0.06, ath_blend, p, e, age, "EDGE", str(player_data.get("production_source", "")), "edge")


def build_cb_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """Coverage movement + ball production."""
    a = float(player_data.get("athletic_score", 50))
    p = float(player_data.get("production_score", 50))
    e = float(player_data.get("efficiency_score", 50))
    age = float(player_data.get("age_adjustment", 50))
    return _finish_prospect(0.32, 0.28, 0.32, 0.08, a, p, e, age, "CB", str(player_data.get("production_source", "")), "cb")


def build_ot_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """Movement + mass proxy + efficiency."""
    a = float(player_data.get("athletic_score", 50))
    p = float(player_data.get("production_score", 50))
    e = float(player_data.get("efficiency_score", 50))
    age = float(player_data.get("age_adjustment", 50))
    wt = _num(player_data.get("weight_percentile_proxy"), 50.0)
    ath_blend = 0.7 * a + 0.3 * wt
    return _finish_prospect(0.24, 0.24, 0.45, 0.07, ath_blend, p, e, age, "OT", str(player_data.get("production_source", "")), "ot")


def build_generic_prospect_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    athletic = float(player_data.get("athletic_score", 50))
    production = float(player_data.get("production_score", 50))
    efficiency = float(player_data.get("efficiency_score", 50))
    age = float(player_data.get("age_adjustment", 50))
    pos = str(player_data.get("pos_bucket", "UNK"))
    return _finish_prospect(0.22, 0.33, 0.33, 0.12, athletic, production, efficiency, age, pos, str(player_data.get("production_source", "")), "generic")


def build_prospect_score(player_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Position-aware composite 0–100. Dispatches to specialized models when applicable.
    """
    pos = str(player_data.get("pos_bucket", "UNK"))
    if pos == "QB":
        return build_qb_score(player_data)
    if pos == "TE":
        return build_te_score(player_data)
    if pos == "WR":
        return build_wr_score(player_data)
    if pos == "EDGE":
        return build_edge_score(player_data)
    if pos == "CB":
        return build_cb_score(player_data)
    if pos == "OT":
        return build_ot_score(player_data)
    return build_generic_prospect_score(player_data)
