"""
Pipeline: build TeamKeys for two teams from POST PBP using aggregate, per_game, or opp_weighted mode.

Caller uses this then passes keys to predict(). REG PBP is used for win_pct when mode is opp_weighted.
"""

from typing import Dict, Optional, Tuple

import pandas as pd

from superbowlengine.features.aggregate_weighted import aggregate_weighted_keys
from superbowlengine.features.game_level import compute_team_keys_per_game
from superbowlengine.features.keys import TeamKeys, compute_team_keys
from superbowlengine.features.opponent_weights import combined_game_weights
from superbowlengine.features.sos import build_game_results, compute_team_win_pct


def prepare_keys_for_matchup(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    team_a: str,
    team_b: str,
    mode: str = "aggregate",
    reg_pbp: Optional[pd.DataFrame] = None,
    *,
    big_pass_yards: int = 15,
    big_rush_yards: int = 10,
    red_zone_yardline: int = 20,
) -> Tuple[TeamKeys, TeamKeys, Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Prepare keys for team_a and team_b according to mode.

    - aggregate: current behavior, sum keys over all POST games (keys_a, keys_b, None, None).
    - per_game: unweighted average per game (same as opp_weighted with weight=1 per game).
    - opp_weighted: weighted average by opponent REG win% and turnover-outlier dampener.

    Returns (keys_a, keys_b, per_game_df_a, per_game_df_b). per_game_dfs are None for aggregate;
    for per_game/opp_weighted they include a "weight" column when weights are computed.
    """
    if mode == "aggregate":
        keys_a = compute_team_keys(
            pbp_post, team_a,
            big_play_pass_yards=big_pass_yards,
            big_play_rush_yards=big_rush_yards,
            red_zone_yardline=red_zone_yardline,
        )
        keys_b = compute_team_keys(
            pbp_post, team_b,
            big_play_pass_yards=big_pass_yards,
            big_play_rush_yards=big_rush_yards,
            red_zone_yardline=red_zone_yardline,
        )
        return keys_a, keys_b, None, None

    # per_game or opp_weighted: build per-game DataFrames
    df_a = compute_team_keys_per_game(
        pbp_post, schedules, team_a,
        big_pass_yards=big_pass_yards,
        big_rush_yards=big_rush_yards,
        red_zone_yardline=red_zone_yardline,
    )
    df_b = compute_team_keys_per_game(
        pbp_post, schedules, team_b,
        big_pass_yards=big_pass_yards,
        big_rush_yards=big_rush_yards,
        red_zone_yardline=red_zone_yardline,
    )

    if mode == "per_game":
        weights_a = pd.Series(1.0, index=df_a.index) if not df_a.empty else pd.Series(dtype=float)
        weights_b = pd.Series(1.0, index=df_b.index) if not df_b.empty else pd.Series(dtype=float)
    else:
        # opp_weighted: REG win_pct and combined weights
        win_pct: Dict[str, float] = {}
        if reg_pbp is not None and not reg_pbp.empty:
            reg_results = build_game_results(reg_pbp, season_type="REG")
            if not reg_results.empty:
                wp_series = compute_team_win_pct(reg_results)
                win_pct = wp_series.to_dict()
        weights_a = combined_game_weights(df_a, win_pct, pbp_post) if not df_a.empty else pd.Series(dtype=float)
        weights_b = combined_game_weights(df_b, win_pct, pbp_post) if not df_b.empty else pd.Series(dtype=float)
        if weights_a.empty and not df_a.empty:
            weights_a = pd.Series(1.0, index=df_a.index)
        if weights_b.empty and not df_b.empty:
            weights_b = pd.Series(1.0, index=df_b.index)

    df_a = df_a.copy()
    df_b = df_b.copy()
    df_a["weight"] = weights_a.reindex(df_a.index).fillna(1.0).values
    df_b["weight"] = weights_b.reindex(df_b.index).fillna(1.0).values

    keys_a = aggregate_weighted_keys(df_a, weights_a) if not df_a.empty else TeamKeys(
        team=team_a, top_min=0.0, turnovers=0, big_plays=0, third_down_pct=0.0, redzone_td_pct=0.0,
    )
    keys_b = aggregate_weighted_keys(df_b, weights_b) if not df_b.empty else TeamKeys(
        team=team_b, top_min=0.0, turnovers=0, big_plays=0, third_down_pct=0.0, redzone_td_pct=0.0,
    )
    return keys_a, keys_b, df_a, df_b
