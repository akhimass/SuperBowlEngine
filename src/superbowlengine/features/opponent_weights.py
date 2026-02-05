"""
Opponent strength and turnover-outlier weights for per-game aggregation.

Weights games by opponent REG-season win% and optionally dampens games where
the opponent had a turnover meltdown (e.g. 5+ giveaways).
"""

from typing import Dict

import pandas as pd

from superbowlengine.features.keys import compute_game_keys


def opponent_win_pct_weights(
    team_games_df: pd.DataFrame,
    win_pct: Dict[str, float],
    *,
    base: float = 0.75,
    scale: float = 0.5,
) -> pd.Series:
    """
    Weight each game by opponent strength: weight = base + scale * opp_win_pct.
    Opponent win_pct defaults to 0.5 if missing from win_pct dict.
    Weights are roughly in [0.75, 1.25] for win_pct in [0, 1].
    team_games_df must have an "opp" column.
    """
    if team_games_df.empty or "opp" not in team_games_df.columns:
        return pd.Series(dtype=float)
    opp_wp = team_games_df["opp"].map(lambda t: win_pct.get(str(t), 0.5))
    return base + scale * opp_wp


def turnover_outlier_dampener(
    team_games_df: pd.DataFrame,
    pbp_post: pd.DataFrame,
    *,
    threshold: int = 4,
    factor: float = 0.80,
) -> pd.Series:
    """
    If the opponent committed >= threshold turnovers in that game, reduce weight by factor.
    Uses compute_game_keys(pbp_post, game_id) to get opponent's TeamKeys.turnovers.
    Returns a Series with index matching team_games_df; value factor where dampened, 1.0 otherwise.
    """
    if team_games_df.empty or pbp_post.empty or "game_id" not in team_games_df.columns or "opp" not in team_games_df.columns:
        return pd.Series(dtype=float)
    out = pd.Series(1.0, index=team_games_df.index)
    for idx, row in team_games_df.iterrows():
        gid = row["game_id"]
        opp = row["opp"]
        game_keys = compute_game_keys(pbp_post, gid)
        k_opp = game_keys.get(opp)
        opp_to = k_opp.turnovers if k_opp is not None else 0
        if opp_to >= threshold:
            out.loc[idx] = factor
    return out


def combined_game_weights(
    team_games_df: pd.DataFrame,
    win_pct: Dict[str, float],
    pbp_post: pd.DataFrame,
    *,
    base: float = 0.75,
    scale: float = 0.5,
    to_threshold: int = 4,
    to_factor: float = 0.80,
) -> pd.Series:
    """Final game weight = w_opp_strength * w_turnover_outlier."""
    w_opp = opponent_win_pct_weights(team_games_df, win_pct, base=base, scale=scale)
    w_to = turnover_outlier_dampener(team_games_df, pbp_post, threshold=to_threshold, factor=to_factor)
    if w_opp.empty:
        return w_to
    if w_to.empty:
        return w_opp
    return w_opp * w_to
