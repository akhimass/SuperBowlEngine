"""Tests for weighted per-game aggregation and opponent/dampener weights."""

import pandas as pd
import pytest

from superbowlengine.features.aggregate_weighted import aggregate_weighted_keys
from superbowlengine.features.opponent_weights import (
    opponent_win_pct_weights,
    turnover_outlier_dampener,
    combined_game_weights,
)


@pytest.fixture
def synthetic_team_games_df() -> pd.DataFrame:
    """Two games: different TOP, TO, big_plays, third_down and redzone rates."""
    return pd.DataFrame([
        {
            "team": "SEA",
            "game_id": "g1",
            "opp": "GB",
            "is_home": True,
            "top_min": 28.0,
            "turnovers": 1,
            "big_plays": 3,
            "third_down_pct": 40.0,
            "redzone_td_pct": 50.0,
            "third_down_attempts": 10,
            "third_down_converted": 4,
            "redzone_trips": 2,
            "redzone_td_drives": 1,
        },
        {
            "team": "SEA",
            "game_id": "g2",
            "opp": "TB",
            "is_home": False,
            "top_min": 32.0,
            "turnovers": 0,
            "big_plays": 5,
            "third_down_pct": 60.0,
            "redzone_td_pct": 100.0,
            "third_down_attempts": 10,
            "third_down_converted": 6,
            "redzone_trips": 1,
            "redzone_td_drives": 1,
        },
    ])


def test_aggregate_weighted_keys_weighted_averages(synthetic_team_games_df: pd.DataFrame) -> None:
    """Weighted averages: game1 weight 1, game2 weight 1 -> avg TOP = 30, TO ~0.5, BIG = 4."""
    weights = pd.Series([1.0, 1.0], index=synthetic_team_games_df.index)
    k = aggregate_weighted_keys(synthetic_team_games_df, weights)
    assert k.team == "SEA"
    assert k.top_min == 30.0  # (28+32)/2
    assert k.turnovers in (0, 1)  # (1+0)/2 = 0.5, round may be 0 or 1
    assert k.big_plays == 4   # (3+5)/2 rounded
    # third_down: (4+6)/(10+10)*100 = 50%
    assert k.third_down_pct == 50.0
    # redzone: (1+1)/(2+1)*100 = 66.67
    assert abs(k.redzone_td_pct - 66.67) < 0.1


def test_aggregate_weighted_keys_unequal_weights(synthetic_team_games_df: pd.DataFrame) -> None:
    """Heavier weight on first game: TOP should be closer to 28."""
    weights = pd.Series([2.0, 0.5], index=synthetic_team_games_df.index)
    k = aggregate_weighted_keys(synthetic_team_games_df, weights)
    total_w = 2.0 + 0.5
    expected_top = (28.0 * 2.0 + 32.0 * 0.5) / total_w  # 72/2.5 = 28.8
    assert abs(k.top_min - expected_top) < 0.01
    # third_down: weighted converted 4*2 + 6*0.5 = 11, attempts 10*2 + 10*0.5 = 25 -> 44%
    assert abs(k.third_down_pct - 44.0) < 1.0


def test_aggregate_weighted_keys_empty() -> None:
    """Empty DataFrame returns zeroed TeamKeys."""
    k = aggregate_weighted_keys(pd.DataFrame(), pd.Series(dtype=float))
    assert k.team == ""
    assert k.top_min == 0.0
    assert k.turnovers == 0
    assert k.third_down_pct == 0.0


def test_opponent_win_pct_weights() -> None:
    """Weights = base + scale * opp_win_pct; default 0.5 for missing team."""
    df = pd.DataFrame({"opp": ["A", "B", "C"]})
    win_pct = {"A": 1.0, "B": 0.0}
    w = opponent_win_pct_weights(df, win_pct, base=0.75, scale=0.5)
    assert len(w) == 3
    assert abs(w.iloc[0] - (0.75 + 0.5 * 1.0)) < 1e-6   # 1.25
    assert abs(w.iloc[1] - (0.75 + 0.5 * 0.0)) < 1e-6   # 0.75
    assert abs(w.iloc[2] - (0.75 + 0.5 * 0.5)) < 1e-6  # default 0.5 -> 1.0


def test_turnover_outlier_dampener() -> None:
    """When opponent has >= 4 turnovers in that game, weight becomes factor (0.8)."""
    df = pd.DataFrame([
        {"game_id": "g1", "opp": "BUF"},
        {"game_id": "g2", "opp": "KC"},
    ])
    # Mock PBP: we need compute_game_keys to return BUF with 5 TO in g1, KC with 1 TO in g2
    # So we need actual pbp for g1 and g2. Use minimal pbp that yields 5 TO for BUF in g1, 1 for KC in g2.
    pbp = pd.DataFrame([
        {"game_id": "g1", "posteam": "BUF", "home_team": "BUF", "away_team": "SEA", "interception": 1, "fumble_lost": 0, "drive": 1, "drive_time_of_possession": "5:00",
         "down": 1, "ydstogo": 10, "yards_gained": 5, "play_type": "pass", "touchdown": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "BUF", "home_team": "BUF", "away_team": "SEA", "interception": 1, "fumble_lost": 0, "drive": 2, "drive_time_of_possession": "3:00",
         "down": 1, "ydstogo": 10, "yards_gained": 5, "play_type": "pass", "touchdown": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "BUF", "home_team": "BUF", "away_team": "SEA", "interception": 1, "fumble_lost": 1, "drive": 3, "drive_time_of_possession": "2:00",
         "down": 1, "ydstogo": 10, "yards_gained": 5, "play_type": "pass", "touchdown": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "BUF", "home_team": "BUF", "away_team": "SEA", "interception": 1, "fumble_lost": 1, "drive": 4, "drive_time_of_possession": "2:00",
         "down": 1, "ydstogo": 10, "yards_gained": 5, "play_type": "pass", "touchdown": 0, "yardline_100": 50},
        {"game_id": "g2", "posteam": "KC", "home_team": "SEA", "away_team": "KC", "interception": 0, "fumble_lost": 1, "drive": 1, "drive_time_of_possession": "5:00",
         "down": 1, "ydstogo": 10, "yards_gained": 5, "play_type": "pass", "touchdown": 0, "yardline_100": 50},
    ])
    damp = turnover_outlier_dampener(df, pbp, threshold=4, factor=0.80)
    assert damp.iloc[0] == 0.80  # BUF has 5 TO in g1
    assert damp.iloc[1] == 1.0   # KC has 1 TO in g2
