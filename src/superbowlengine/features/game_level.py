"""
Per-game 5 Keys: one row per team-game for fair aggregation across different game counts.

Uses existing compute_game_keys(pbp, game_id) and extracts the team's TeamKeys per game.
"""

from typing import List

import pandas as pd

from superbowlengine.features.keys import (
    BIG_PLAY_PASS_YARDS,
    BIG_PLAY_RUSH_YARDS,
    TeamKeys,
    compute_game_keys,
)


def team_game_ids(pbp_post: pd.DataFrame, team: str) -> List[str]:
    """Return list of game_id for games where the team had possession (posteam)."""
    if pbp_post.empty or "game_id" not in pbp_post.columns or "posteam" not in pbp_post.columns:
        return []
    team_games = pbp_post[pbp_post["posteam"] == team]["game_id"].dropna().unique()
    return sorted(team_games.tolist())


def compute_team_keys_per_game(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    team: str,
    *,
    big_pass_yards: int = BIG_PLAY_PASS_YARDS,
    big_rush_yards: int = BIG_PLAY_RUSH_YARDS,
    red_zone_yardline: int = 20,
) -> pd.DataFrame:
    """
    One row per game for the team: team, game_id, opp, is_home, round (if available),
    plus TeamKeys fields and denominators (third_down_attempts, third_down_converted,
    redzone_trips, redzone_td_drives).
    Uses compute_game_keys(pbp_post, game_id) and selects the team's TeamKeys.
    """
    gids = team_game_ids(pbp_post, team)
    if not gids:
        return pd.DataFrame(
            columns=[
                "team", "game_id", "opp", "is_home", "round",
                "top_min", "turnovers", "big_plays", "third_down_pct", "redzone_td_pct",
                "third_down_attempts", "third_down_converted", "redzone_trips", "redzone_td_drives",
            ]
        )

    rows = []
    for gid in gids:
        game_keys = compute_game_keys(
            pbp_post, gid,
            big_play_pass_yards=big_pass_yards,
            big_play_rush_yards=big_rush_yards,
            red_zone_yardline=red_zone_yardline,
        )
        if team not in game_keys:
            continue
        k = game_keys[team]
        # Opponent and is_home from PBP (one row per game)
        game_slice = pbp_post[pbp_post["game_id"] == gid]
        if game_slice.empty:
            continue
        home_team = game_slice["home_team"].iloc[0]
        away_team = game_slice["away_team"].iloc[0]
        is_home = (home_team == team)
        opp = away_team if is_home else home_team
        round_ = None
        if not schedules.empty and "game_id" in schedules.columns and "game_type" in schedules.columns:
            sched_row = schedules[schedules["game_id"] == gid]
            if not sched_row.empty:
                round_ = sched_row["game_type"].iloc[0]
        rows.append({
            "team": team,
            "game_id": gid,
            "opp": opp,
            "is_home": is_home,
            "round": round_,
            "top_min": k.top_min,
            "turnovers": k.turnovers,
            "big_plays": k.big_plays,
            "third_down_pct": k.third_down_pct,
            "redzone_td_pct": k.redzone_td_pct,
            "third_down_attempts": k.third_down_attempts,
            "third_down_converted": k.third_down_converted,
            "redzone_trips": k.redzone_trips,
            "redzone_td_drives": k.redzone_td_drives,
        })
    return pd.DataFrame(rows)
