"""
Rank/percentile of 5 Keys among playoff (POST) teams.

Used by the Slide 5 explainer to show e.g. "SEA 82nd pct, NE 41st pct" per key.
TOP, BIG, 3D, RZ: higher is better. TO: lower is better.
"""

from typing import Dict, List, Optional

import pandas as pd

from superbowlengine.features.keys import TeamKeys
from superbowlengine.features.keys_pipeline import prepare_keys_for_matchup

KEY_NAMES = ["TOP", "TO", "BIG", "3D", "RZ"]
# TO: lower raw value = better, so we use inverse for percentile
LOWER_IS_BETTER_KEYS = {"TO"}


def _keys_to_row(k: TeamKeys) -> Dict[str, float]:
    """TeamKeys to dict of key name -> value for ranking."""
    return {
        "TOP": k.top_min,
        "TO": float(k.turnovers),
        "BIG": float(k.big_plays),
        "3D": k.third_down_pct,
        "RZ": k.redzone_td_pct,
    }


def _percentile_rank(value: float, values: List[float], lower_is_better: bool) -> float:
    """Return percentile 0-100: % of values that are <= value (or >= for TO)."""
    if not values:
        return 50.0
    n = len(values)
    if lower_is_better:
        # Higher rank when value is lower
        count_better = sum(1 for v in values if v > value)
        return 100.0 * (n - count_better) / n
    else:
        count_worse_or_eq = sum(1 for v in values if v <= value)
        return 100.0 * count_worse_or_eq / n


def get_ranks_meta(year: Optional[int] = None, mode: str = "opp_weighted") -> Dict[str, str]:
    """Return metadata for percentile interpretation: population and metric definition."""
    population = f"POST teams {year}" if year is not None else "POST teams"
    metric = "per-game, opponent-weighted" if mode == "opp_weighted" else ("per-game" if mode == "per_game" else "aggregate")
    return {"population": population, "metric_definition": metric}


def compute_ranks_for_matchup(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    team_a: str,
    team_b: str,
    mode: str = "opp_weighted",
    reg_pbp: Optional[pd.DataFrame] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Compute percentile (0-100) for each key for team_a and team_b among all POST teams.

    Returns ranks[team][key] = percentile. Uses same aggregation mode as matchup (opp_weighted
    recommended) so rankings are comparable. All teams that appear in pbp_post (posteam) are included.
    """
    post_teams = pbp_post["posteam"].dropna().unique().tolist()
    post_teams = [t for t in post_teams if t and str(t).strip()]
    if not post_teams:
        return {team_a: {k: 50.0 for k in KEY_NAMES}, team_b: {k: 50.0 for k in KEY_NAMES}}

    all_keys: Dict[str, TeamKeys] = {}
    for team in post_teams:
        ka, kb, _, _ = prepare_keys_for_matchup(
            pbp_post, schedules, team, team, mode=mode, reg_pbp=reg_pbp,
        )
        all_keys[team] = ka

    # Build value lists per key
    key_values: Dict[str, List[float]] = {k: [] for k in KEY_NAMES}
    for team, k in all_keys.items():
        row = _keys_to_row(k)
        for key in KEY_NAMES:
            key_values[key].append(row[key])

    result: Dict[str, Dict[str, float]] = {}
    for team in [team_a, team_b]:
        k = all_keys.get(team)
        if k is None:
            result[team] = {key: 50.0 for key in KEY_NAMES}
            continue
        row = _keys_to_row(k)
        result[team] = {}
        for key in KEY_NAMES:
            pct = _percentile_rank(
                row[key],
                key_values[key],
                lower_is_better=(key in LOWER_IS_BETTER_KEYS),
            )
            result[team][key] = round(pct, 1)
    return result
