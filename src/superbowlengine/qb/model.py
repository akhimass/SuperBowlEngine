"""
QB production score: completion %, YPA, TD/INT/sack rates, rush value, turnover rate.

Normalization ranges are configurable (playoff-typical). Returns 0–100 total + component scores.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from superbowlengine.utils.math import safe_div


@dataclass
class QBLine:
    """Raw stat line for a QB (postseason or segment)."""

    games: int
    cmp: int
    att: int
    yds: int
    td: int
    int_: int  # 'int' reserved
    sacks: int
    rush_att: int
    rush_yds: int
    rush_td: int
    fumbles: int

    def __post_init__(self) -> None:
        if self.games < 1:
            self.games = 1


def qb_line_from_pbp(
    pbp: pd.DataFrame,
    qb: str,
    team: str,
    game_ids: Optional[List[str]] = None,
) -> Optional[QBLine]:
    """
    Build QBLine (box-score stats) from PBP for the given QB and team.
    Uses passer_player_name / rusher_player_name with name matching; requires
    complete_pass, play_type, yards_gained, touchdown, interception, fumble_lost.
    Returns None if required columns missing or no QB plays.
    """
    from superbowlengine.qb.validate import _qb_name_matches

    df = pbp[pbp["posteam"] == team].copy()
    if game_ids is not None:
        df = df[df["game_id"].isin(game_ids)]
    if df.empty or "play_type" not in df.columns:
        return None
    has_passer = "passer_player_name" in df.columns
    has_rusher = "rusher_player_name" in df.columns
    if not (has_passer or has_rusher):
        return None
    games = df["game_id"].nunique() or 1
    # Pass plays (pass + sack) by QB
    pass_plays = df[df["play_type"].isin(["pass", "sack"])]
    if has_passer:
        pass_plays = pass_plays[pass_plays["passer_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
    att = len(pass_plays[pass_plays["play_type"] == "pass"]) if "play_type" in pass_plays.columns else 0
    sacks = int((pass_plays["play_type"] == "sack").sum()) if "play_type" in pass_plays.columns else 0
    comp = 0
    if att and "complete_pass" in df.columns:
        comp_plays = pass_plays[pass_plays["play_type"] == "pass"]
        comp = int((comp_plays["complete_pass"].fillna(0) == 1).sum())
    yds = int(pass_plays["yards_gained"].fillna(0).sum()) if "yards_gained" in pass_plays.columns else 0
    td = int((pass_plays.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1).sum())
    int_ = int((pass_plays.get("interception", pd.Series(dtype=float)).fillna(0) == 1).sum())
    # Rush by QB
    rush_plays = df[df["play_type"] == "run"]
    if has_rusher:
        rush_plays = rush_plays[rush_plays["rusher_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
    rush_att = len(rush_plays)
    rush_yds = int(rush_plays["yards_gained"].fillna(0).sum()) if "yards_gained" in rush_plays.columns else 0
    rush_td = int((rush_plays.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1).sum())
    # Fumbles: team fumbles lost (offense)
    fumbles = int(df.get("fumble_lost", pd.Series(dtype=float)).fillna(0).sum())
    return QBLine(
        games=int(games),
        cmp=comp,
        att=att,
        yds=yds,
        td=td,
        int_=int_,
        sacks=sacks,
        rush_att=rush_att,
        rush_yds=rush_yds,
        rush_td=rush_td,
        fumbles=fumbles,
    )


def compute_qb_metrics(qb: QBLine) -> Dict[str, float]:
    """
    Derive rates and per-game values from QBLine.

    Returns: comp_pct, ypa, td_rate, int_rate, sack_rate, rush_ypc, rush_td_pg,
             explosive_pass_pct (placeholder 0 if not from PBP), turnover_rate_pg.
    """
    dropbacks = qb.att + safe_div(qb.sacks, 1)
    comp_pct = 100.0 * safe_div(qb.cmp, qb.att) if qb.att else 0.0
    ypa = safe_div(qb.yds, qb.att) if qb.att else 0.0
    td_rate = 100.0 * safe_div(qb.td, qb.att) if qb.att else 0.0
    int_rate = 100.0 * safe_div(qb.int_, qb.att) if qb.att else 0.0
    sack_rate = 100.0 * safe_div(qb.sacks, dropbacks) if dropbacks else 0.0
    rush_ypc = safe_div(qb.rush_yds, qb.rush_att) if qb.rush_att else 0.0
    rush_td_pg = safe_div(qb.rush_td, qb.games)
    turnover_rate_pg = safe_div(qb.int_ + qb.fumbles, qb.games)
    return {
        "comp_pct": round(comp_pct, 1),
        "ypa": round(ypa, 2),
        "td_rate": round(td_rate, 2),
        "int_rate": round(int_rate, 2),
        "sack_rate": round(sack_rate, 2),
        "rush_ypc": round(rush_ypc, 2),
        "rush_td_pg": round(rush_td_pg, 2),
        "explosive_pass_pct": 0.0,  # optional PBP-derived
        "turnover_rate_pg": round(turnover_rate_pg, 2),
    }


# Default normalization ranges (playoff-typical) for 0–100 component scores
DEFAULT_RANGES = {
    "comp_pct": (50.0, 75.0),
    "ypa": (5.0, 9.0),
    "td_rate": (2.0, 8.0),
    "int_rate": (0.0, 4.0),  # lower better -> we invert
    "sack_rate": (2.0, 10.0),  # lower better -> we invert
    "rush_ypc": (0.0, 6.0),
    "rush_td_pg": (0.0, 0.5),
    "turnover_rate_pg": (0.0, 2.0),  # lower better
}

DEFAULT_WEIGHTS = {
    "passing_efficiency": 0.40,   # comp_pct, ypa, td_rate
    "ball_security": 0.30,        # int_rate, sack_rate, turnover_rate_pg (inverted)
    "added_value": 0.30,          # rush_ypc, rush_td_pg
}


def _clip_score(x: float) -> float:
    return max(0.0, min(100.0, x))


def _normalize(value: float, low: float, high: float, lower_is_better: bool = False) -> float:
    if high <= low:
        return 50.0
    pct = 100.0 * (value - low) / (high - low)
    if lower_is_better:
        pct = 100.0 - pct
    return _clip_score(pct)


def qb_production_score(
    metrics: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
    ranges: Optional[Dict[str, tuple]] = None,
) -> Dict[str, Any]:
    """
    Compute total production score 0–100 and component scores.

    Components:
      - Passing efficiency: comp_pct, ypa, td_rate (higher better)
      - Ball security: int_rate, sack_rate, turnover_rate_pg (lower better)
      - Added value: rush_ypc, rush_td_pg (higher better)

    Returns dict with: total, passing_efficiency, ball_security, added_value, metrics (input).
    """
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    r = dict(DEFAULT_RANGES)
    if ranges:
        r.update(ranges)
    # Passing efficiency (0–100)
    comp = _normalize(metrics.get("comp_pct", 0), r["comp_pct"][0], r["comp_pct"][1])
    ypa_s = _normalize(metrics.get("ypa", 0), r["ypa"][0], r["ypa"][1])
    td_s = _normalize(metrics.get("td_rate", 0), r["td_rate"][0], r["td_rate"][1])
    passing_efficiency = (comp + ypa_s + td_s) / 3.0
    # Ball security (lower is better for int, sack, turnover)
    int_s = _normalize(metrics.get("int_rate", 0), r["int_rate"][0], r["int_rate"][1], lower_is_better=True)
    sack_s = _normalize(metrics.get("sack_rate", 0), r["sack_rate"][0], r["sack_rate"][1], lower_is_better=True)
    to_s = _normalize(metrics.get("turnover_rate_pg", 0), r["turnover_rate_pg"][0], r["turnover_rate_pg"][1], lower_is_better=True)
    ball_security = (int_s + sack_s + to_s) / 3.0
    # Added value (rush_ypc, rush_td_pg)
    rush_ypc_s = _normalize(metrics.get("rush_ypc", 0), r["rush_ypc"][0], r["rush_ypc"][1])
    rush_td_s = _normalize(metrics.get("rush_td_pg", 0), r["rush_td_pg"][0], r["rush_td_pg"][1])
    added_value = rush_ypc_s * 0.6 + rush_td_s * 0.4
    added_value = _clip_score(added_value)
    total = (
        w["passing_efficiency"] * passing_efficiency
        + w["ball_security"] * ball_security
        + w["added_value"] * added_value
    )
    total = _clip_score(total)
    return {
        "total": round(total, 1),
        "passing_efficiency": round(passing_efficiency, 1),
        "ball_security": round(ball_security, 1),
        "added_value": round(added_value, 1),
        "metrics": metrics,
    }
