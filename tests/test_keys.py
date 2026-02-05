"""Tests for 5 Keys feature computation."""

import pandas as pd
import pytest

from superbowlengine.features.keys import (
    TeamKeys,
    aggregate_keys,
    compute_game_keys,
    compute_team_keys,
    compute_team_keys_from_pbp,
)


@pytest.fixture
def minimal_pbp() -> pd.DataFrame:
    """Minimal PBP with one drive, one team, for key computation."""
    return pd.DataFrame([
        {
            "game_id": "g1",
            "posteam": "SEA",
            "defteam": "NE",
            "down": 1,
            "ydstogo": 10,
            "yards_gained": 5,
            "play_type": "run",
            "touchdown": 0,
            "interception": 0,
            "fumble_lost": 0,
            "drive": 1,
            "drive_time_of_possession": "2:30",
            "yardline_100": 75,
        },
        {
            "game_id": "g1",
            "posteam": "SEA",
            "defteam": "NE",
            "down": 3,
            "ydstogo": 3,
            "yards_gained": 5,
            "play_type": "pass",
            "touchdown": 0,
            "interception": 0,
            "fumble_lost": 0,
            "drive": 1,
            "drive_time_of_possession": "2:30",
            "yardline_100": 70,
        },
    ])


def test_team_keys_dataclass() -> None:
    k = TeamKeys(team="SEA", top_min=30.0, turnovers=1, big_plays=3, third_down_pct=40.0, redzone_td_pct=50.0)
    assert k.team == "SEA"
    assert k.turnovers == 1
    assert k.third_down_attempts == 0  # default
    assert k.redzone_trips == 0


def test_compute_team_keys_from_pbp(minimal_pbp: pd.DataFrame) -> None:
    keys = compute_team_keys_from_pbp(minimal_pbp, "SEA")
    assert keys.team == "SEA"
    assert keys.top_min == 2.5  # 2:30 -> 150s -> 2.5 min
    assert keys.turnovers == 0
    assert keys.big_plays == 0
    assert keys.third_down_pct == 100.0  # 1 conversion on 3rd down
    assert keys.redzone_td_pct == 0.0


def test_compute_team_keys_empty_team() -> None:
    df = pd.DataFrame(columns=["game_id", "posteam", "drive", "drive_time_of_possession",
                               "down", "play_type", "yards_gained", "ydstogo", "touchdown", "yardline_100",
                               "interception", "fumble_lost"])
    df["posteam"] = df["posteam"].astype(object)
    keys = compute_team_keys_from_pbp(df, "SEA")
    assert keys.team == "SEA"
    assert keys.top_min == 0.0
    assert keys.turnovers == 0
    assert keys.big_plays == 0


# ---- MM:SS and TOP ----

def test_mmss_top_summed_in_keys() -> None:
    """TOP is sum of drive_time_of_possession per unique drive; MM:SS parsed correctly."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "2:30",
         "down": 1, "play_type": "run", "yards_gained": 0, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "SEA", "drive": 2, "drive_time_of_possession": "3:00",
         "down": 1, "play_type": "run", "yards_gained": 0, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50},
    ])
    keys = compute_team_keys(df, "SEA")
    # 2:30 = 2.5 min, 3:00 = 3 min -> total 5.5 min
    assert keys.top_min == 5.5


# ---- Red zone: trip = drive with any RZ play; TD = drive-level (one per drive) ----

def test_redzone_trip_and_td_drive_level() -> None:
    """One RZ trip with multiple TD plays counts as one RZ TD drive (no inflation)."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 1, "play_type": "run", "yards_gained": 5, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 15},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 2, "play_type": "pass", "yards_gained": 10, "ydstogo": 5, "touchdown": 1,
         "interception": 0, "fumble_lost": 0, "yardline_100": 5},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 3, "play_type": "run", "yards_gained": 0, "ydstogo": 10, "touchdown": 1,
         "interception": 0, "fumble_lost": 0, "yardline_100": 3},
    ])
    keys = compute_team_keys(df, "SEA", red_zone_yardline=20)
    assert keys.redzone_trips == 1
    assert keys.redzone_td_drives == 1  # one drive, one count
    assert keys.redzone_td_pct == 100.0  # 1/1, not inflated by 2 TD plays


def test_redzone_two_trips_one_td() -> None:
    """Two RZ trips, one ends in TD -> 50%."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 1, "play_type": "run", "yards_gained": 0, "ydstogo": 10, "touchdown": 1,
         "interception": 0, "fumble_lost": 0, "yardline_100": 10},
        {"game_id": "g1", "posteam": "SEA", "drive": 2, "drive_time_of_possession": "1:00",
         "down": 1, "play_type": "run", "yards_gained": 0, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 15},
    ])
    keys = compute_team_keys(df, "SEA", red_zone_yardline=20)
    assert keys.redzone_trips == 2
    assert keys.redzone_td_drives == 1
    assert keys.redzone_td_pct == 50.0


def test_redzone_no_trip_zero_pct() -> None:
    """No RZ play -> 0 trips, 0% (no divide by zero)."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "2:00",
         "down": 1, "play_type": "run", "yards_gained": 5, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 80},
    ])
    keys = compute_team_keys(df, "SEA", red_zone_yardline=20)
    assert keys.redzone_trips == 0
    assert keys.redzone_td_drives == 0
    assert keys.redzone_td_pct == 0.0


# ---- 3rd down conversion ----

def test_third_down_conversion_yards() -> None:
    """Conversion when yards_gained >= ydstogo (no first_down column)."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 3, "ydstogo": 4, "yards_gained": 5, "play_type": "pass", "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 3, "ydstogo": 10, "yards_gained": 3, "play_type": "run", "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 45},
    ])
    keys = compute_team_keys(df, "SEA", third_down_number=3)
    assert keys.third_down_attempts == 2
    assert keys.third_down_converted == 1  # first play 5 >= 4
    assert keys.third_down_pct == 50.0


def test_third_down_conversion_first_down_column() -> None:
    """When first_down is present, use first_down==1 for conversion."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 3, "ydstogo": 10, "yards_gained": 2, "play_type": "pass", "touchdown": 0,
         "first_down": 1, "interception": 0, "fumble_lost": 0, "yardline_100": 50},
    ])
    keys = compute_team_keys(df, "SEA", third_down_number=3)
    assert keys.third_down_attempts == 1
    assert keys.third_down_converted == 1
    assert keys.third_down_pct == 100.0


def test_third_down_touchdown_counts() -> None:
    """TD on 3rd down counts as conversion."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 3, "ydstogo": 10, "yards_gained": 25, "play_type": "pass", "touchdown": 1,
         "interception": 0, "fumble_lost": 0, "yardline_100": 25},
    ])
    keys = compute_team_keys(df, "SEA", third_down_number=3)
    assert keys.third_down_converted == 1
    assert keys.third_down_pct == 100.0


# ---- compute_game_keys, aggregate_keys ----

def test_compute_game_keys() -> None:
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "2:00",
         "down": 1, "play_type": "run", "yards_gained": 0, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "NE", "drive": 2, "drive_time_of_possession": "1:30",
         "down": 1, "play_type": "run", "yards_gained": 0, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50},
    ])
    out = compute_game_keys(df, "g1")
    assert set(out) == {"SEA", "NE"}
    assert out["SEA"].top_min == 2.0
    assert out["NE"].top_min == 1.5


def test_aggregate_keys_sums_rates_correct() -> None:
    """Aggregated keys sum counts and recompute rates (no inflation)."""
    k1 = TeamKeys("SEA", 10.0, 1, 2, 50.0, 100.0, third_down_attempts=10, third_down_converted=5,
                  redzone_trips=2, redzone_td_drives=2)
    k2 = TeamKeys("SEA", 12.0, 0, 3, 33.33, 0.0, third_down_attempts=6, third_down_converted=2,
                  redzone_trips=1, redzone_td_drives=0)
    agg = aggregate_keys([k1, k2], team="SEA")
    assert agg.top_min == 22.0
    assert agg.turnovers == 1
    assert agg.big_plays == 5
    assert agg.third_down_attempts == 16
    assert agg.third_down_converted == 7
    assert agg.third_down_pct == 43.75  # 7/16
    assert agg.redzone_trips == 3
    assert agg.redzone_td_drives == 2
    assert abs(agg.redzone_td_pct - 66.67) < 0.1  # 2/3


def test_aggregate_keys_empty() -> None:
    out = aggregate_keys([], team="SEA")
    assert out.team == "SEA"
    assert out.top_min == 0.0
    assert out.turnovers == 0
    assert out.redzone_trips == 0


# ---- Big plays: pass >= 15, run >= 10 ----

def test_big_plays_pass_15_run_10() -> None:
    """Big plays: pass gain >= 15, run gain >= 10 (default thresholds)."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 1, "play_type": "pass", "yards_gained": 20, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 2, "play_type": "pass", "yards_gained": 14, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 45},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 3, "play_type": "run", "yards_gained": 12, "ydstogo": 5, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 40},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 4, "play_type": "run", "yards_gained": 9, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 35},
    ])
    keys = compute_team_keys(df, "SEA")
    # pass 20 >= 15 counts, pass 14 does not; run 12 >= 10 counts, run 9 does not -> 2 big plays
    assert keys.big_plays == 2


def test_big_plays_explicit_thresholds() -> None:
    """Custom pass 15 / rush 10 thresholds are applied."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 1, "play_type": "pass", "yards_gained": 15, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 2, "play_type": "run", "yards_gained": 10, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 45},
    ])
    keys = compute_team_keys(df, "SEA", big_play_pass_yards=15, big_play_rush_yards=10)
    assert keys.big_plays == 2
    keys2 = compute_team_keys(df, "SEA", big_play_pass_yards=20, big_play_rush_yards=15)
    assert keys2.big_plays == 0


def test_big_plays_no_play_excluded() -> None:
    """Plays with no_play==1 are excluded from big play count when column exists."""
    df = pd.DataFrame([
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 1, "play_type": "pass", "yards_gained": 25, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 50, "no_play": 0},
        {"game_id": "g1", "posteam": "SEA", "drive": 1, "drive_time_of_possession": "1:00",
         "down": 2, "play_type": "pass", "yards_gained": 20, "ydstogo": 10, "touchdown": 0,
         "interception": 0, "fumble_lost": 0, "yardline_100": 45, "no_play": 1},
    ])
    keys = compute_team_keys(df, "SEA")
    assert keys.big_plays == 1
