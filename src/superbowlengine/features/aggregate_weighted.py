"""
Weighted per-game aggregation of 5 Keys for fair comparison across different game counts.

Averages are weighted by opponent strength and optionally dampened by turnover outliers.
Rates (third_down_pct, redzone_td_pct) are computed from weighted sums of attempts/conversions.
"""

import pandas as pd

from superbowlengine.features.keys import TeamKeys
from superbowlengine.utils.math import safe_div


def aggregate_weighted_keys(team_games_df: pd.DataFrame, weights: pd.Series) -> TeamKeys:
    """
    Aggregate per-game keys using weights. Returns a single TeamKeys for the team.

    - top_min, turnovers, big_plays: weighted average per game (sum(w*x)/sum(w)).
    - third_down_pct: 100 * (weighted sum of third_down_converted) / (weighted sum of third_down_attempts).
    - redzone_td_pct: 100 * (weighted sum of redzone_td_drives) / (weighted sum of redzone_trips).
    Preserves denominators (third_down_attempts, third_down_converted, redzone_trips, redzone_td_drives)
    as the weighted sums for debugging.
    """
    if team_games_df.empty:
        return TeamKeys(
            team="",
            top_min=0.0,
            turnovers=0,
            big_plays=0,
            third_down_pct=0.0,
            redzone_td_pct=0.0,
            third_down_attempts=0,
            third_down_converted=0,
            redzone_trips=0,
            redzone_td_drives=0,
        )
    team_name = team_games_df["team"].iloc[0]
    # Align weights to dataframe index
    w = weights.reindex(team_games_df.index).fillna(1.0)
    total_w = w.sum()
    if total_w == 0:
        total_w = 1.0
    # Weighted averages for count-like metrics (per game)
    top_min = (team_games_df["top_min"] * w).sum() / total_w
    turnovers = (team_games_df["turnovers"] * w).sum() / total_w
    big_plays = (team_games_df["big_plays"] * w).sum() / total_w
    # Rates from weighted sums of denominators
    third_attempts_w = (team_games_df["third_down_attempts"] * w).sum()
    third_converted_w = (team_games_df["third_down_converted"] * w).sum()
    rz_trips_w = (team_games_df["redzone_trips"] * w).sum()
    rz_td_drives_w = (team_games_df["redzone_td_drives"] * w).sum()
    third_down_pct = 100.0 * safe_div(third_converted_w, third_attempts_w)
    redzone_td_pct = 100.0 * safe_div(rz_td_drives_w, rz_trips_w)
    return TeamKeys(
        team=team_name,
        top_min=round(top_min, 2),
        turnovers=int(round(turnovers, 0)),
        big_plays=int(round(big_plays, 0)),
        third_down_pct=round(third_down_pct, 2),
        redzone_td_pct=round(redzone_td_pct, 2),
        third_down_attempts=int(round(third_attempts_w, 0)),
        third_down_converted=int(round(third_converted_w, 0)),
        redzone_trips=int(round(rz_trips_w, 0)),
        redzone_td_drives=int(round(rz_td_drives_w, 0)),
    )
