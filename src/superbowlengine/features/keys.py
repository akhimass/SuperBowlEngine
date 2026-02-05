"""
5 Keys feature engineering from PBP: TOP, turnovers, big plays, 3rd down %, red zone TD %.

All functions are deterministic: same inputs produce same outputs.
Expects nflverse-style PBP columns (posteam, drive, drive_time_of_possession, etc.).
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from superbowlengine.config import Config, DEFAULT_CONFIG
from superbowlengine.utils.math import safe_div
from superbowlengine.utils.time import mmss_to_seconds

# Play types we count for big plays and 3rd down (exclude no_play, penalty, etc.)
_SCORING_PLAY_TYPES = {"pass", "run"}

# Default big-play thresholds: pass >= 15 yards, rush >= 10 yards
BIG_PLAY_PASS_YARDS = 15
BIG_PLAY_RUSH_YARDS = 10


@dataclass
class TeamKeys:
    """
    Five keys per team: TOP, turnovers, big plays, 3rd down %, red zone TD %.
    Optional count fields support correct aggregation across games (aggregate_keys).
    """

    team: str
    top_min: float
    turnovers: int
    big_plays: int
    third_down_pct: float
    redzone_td_pct: float
    # For aggregation across games (postseason):
    third_down_attempts: int = 0
    third_down_converted: int = 0
    redzone_trips: int = 0
    redzone_td_drives: int = 0


def compute_team_keys(
    pbp: pd.DataFrame,
    team: str,
    *,
    big_play_pass_yards: int = BIG_PLAY_PASS_YARDS,
    big_play_rush_yards: int = BIG_PLAY_RUSH_YARDS,
    red_zone_yardline: int = 20,
    third_down_number: int = 3,
) -> TeamKeys:
    """
    Compute 5 Keys for one team from play-by-play DataFrame.
    Deterministic. Uses only offensive plays (posteam == team).

    TOP: Sum of drive_time_of_possession over unique (game_id, drive). MM:SS parsed safely.
    Turnovers: interceptions + fumble_lost (offense giveaways).
    Big plays: pass with yards_gained >= big_play_pass_yards (default 15), or
              run with yards_gained >= big_play_rush_yards (default 10); excludes no_play if present.
    3rd down: conversion = first_down==1 (if present) else yards_gained >= ydstogo or touchdown==1.
    Red zone: RZ trip = drive with any play yardline_100 <= red_zone_yardline.
              RZ TD = drive that ended in a TD (one count per drive). RZ TD% = RZ TD drives / RZ trips.
    """
    tdf = pbp[pbp["posteam"] == team].copy()
    if tdf.empty:
        return _empty_team_keys(team)

    # --- 1) TOP: sum drive_time_of_possession over unique offensive drives
    drive_top = (
        tdf.dropna(subset=["game_id", "drive"])
        .drop_duplicates(subset=["game_id", "drive"])
    )
    top_seconds = drive_top["drive_time_of_possession"].apply(mmss_to_seconds).sum()
    top_min = top_seconds / 60.0

    # --- 2) Turnovers: interceptions + fumble_lost (nflverse uses fumble_lost)
    ints = int(tdf.get("interception", pd.Series(dtype=float)).fillna(0).sum())
    fum_lost = int(tdf.get("fumble_lost", pd.Series(dtype=float)).fillna(0).sum())
    turnovers = ints + fum_lost

    # --- 3) Big plays: pass >= 15 yards, run >= 10 yards; exclude no_play when column exists
    play_type_ok = tdf["play_type"].isin(_SCORING_PLAY_TYPES)
    if "no_play" in tdf.columns:
        play_type_ok = play_type_ok & (tdf["no_play"].fillna(0) != 1)
    elif (tdf["play_type"] == "no_play").any():
        play_type_ok = play_type_ok & (tdf["play_type"] != "no_play")
    yards = tdf["yards_gained"].fillna(0)
    big_play_mask = play_type_ok & (
        ((tdf["play_type"] == "pass") & (yards >= big_play_pass_yards))
        | ((tdf["play_type"] == "run") & (yards >= big_play_rush_yards))
    )
    big_plays = int(big_play_mask.sum())

    # --- 4) 3rd down efficiency: prefer first_down if present; else yards >= ydstogo or TD
    third = tdf[(tdf["down"] == third_down_number) & tdf["play_type"].isin(_SCORING_PLAY_TYPES)].copy()
    third_attempts = len(third)
    if third_attempts == 0:
        third_converted = 0
    else:
        if "first_down" in third.columns:
            converted = (third["first_down"].fillna(0) == 1) | (third.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1)
        else:
            converted = (
                (third["yards_gained"].fillna(0) >= third["ydstogo"].fillna(999))
                | (third.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1)
            )
        third_converted = int(converted.sum())
    third_down_pct = 100.0 * safe_div(third_converted, third_attempts)

    # --- 5) Red zone: trip = drive with any play in RZ; TD = drive that ended in a TD (one per drive)
    rz_plays = tdf[tdf["yardline_100"].fillna(999) <= red_zone_yardline]
    rz_drives_df = rz_plays.dropna(subset=["game_id", "drive"]).drop_duplicates(subset=["game_id", "drive"])
    rz_trips = len(rz_drives_df)
    if rz_trips == 0:
        redzone_td_drives = 0
        redzone_td_pct = 0.0
    else:
        # Drives that had at least one RZ play and at least one TD on the drive
        rz_drive_ids = set(zip(rz_drives_df["game_id"], rz_drives_df["drive"]))
        td_on_drive = tdf[tdf.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1]
        td_drive_ids = set()
        if not td_on_drive.empty and "game_id" in td_on_drive.columns and "drive" in td_on_drive.columns:
            td_drive_ids = set(zip(td_on_drive["game_id"], td_on_drive["drive"]))
        redzone_td_drives = len(rz_drive_ids & td_drive_ids)
        redzone_td_pct = 100.0 * safe_div(redzone_td_drives, rz_trips)

    return TeamKeys(
        team=team,
        top_min=round(top_min, 2),
        turnovers=turnovers,
        big_plays=big_plays,
        third_down_pct=round(third_down_pct, 2),
        redzone_td_pct=round(redzone_td_pct, 2),
        third_down_attempts=third_attempts,
        third_down_converted=third_converted,
        redzone_trips=rz_trips,
        redzone_td_drives=redzone_td_drives,
    )


def _empty_team_keys(team: str) -> TeamKeys:
    """Return zeroed TeamKeys for a team with no plays."""
    return TeamKeys(
        team=team,
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


def compute_game_keys(
    pbp: pd.DataFrame,
    game_id: str,
    *,
    big_play_pass_yards: int = BIG_PLAY_PASS_YARDS,
    big_play_rush_yards: int = BIG_PLAY_RUSH_YARDS,
    red_zone_yardline: int = 20,
    third_down_number: int = 3,
) -> dict[str, TeamKeys]:
    """
    Compute 5 Keys for each team that had possession in the given game.
    Returns dict mapping posteam -> TeamKeys. Deterministic.
    """
    game_pbp = pbp[pbp["game_id"] == game_id]
    if game_pbp.empty:
        return {}
    teams = game_pbp["posteam"].dropna().unique().tolist()
    teams = [t for t in teams if t and str(t).strip()]
    return {
        t: compute_team_keys(
            game_pbp, t,
            big_play_pass_yards=big_play_pass_yards,
            big_play_rush_yards=big_play_rush_yards,
            red_zone_yardline=red_zone_yardline,
            third_down_number=third_down_number,
        )
        for t in teams
    }


def aggregate_keys(keys_list: list[TeamKeys], team: str = "") -> TeamKeys:
    """
    Aggregate multiple TeamKeys (e.g. multi-game postseason) into one.
    Sums: top_min, turnovers, big_plays, third_down_attempts, third_down_converted,
          redzone_trips, redzone_td_drives. Recomputes third_down_pct and redzone_td_pct
    from summed attempts/conversions so rates are not inflated.
    If keys_list is empty, returns zeroed TeamKeys for team (or "").
    """
    if not keys_list:
        return _empty_team_keys(team)
    t = team or keys_list[0].team
    top_min = sum(k.top_min for k in keys_list)
    turnovers = sum(k.turnovers for k in keys_list)
    big_plays = sum(k.big_plays for k in keys_list)
    third_attempts = sum(k.third_down_attempts for k in keys_list)
    third_converted = sum(k.third_down_converted for k in keys_list)
    rz_trips = sum(k.redzone_trips for k in keys_list)
    rz_td_drives = sum(k.redzone_td_drives for k in keys_list)
    third_down_pct = 100.0 * safe_div(third_converted, third_attempts)
    redzone_td_pct = 100.0 * safe_div(rz_td_drives, rz_trips)
    return TeamKeys(
        team=t,
        top_min=round(top_min, 2),
        turnovers=turnovers,
        big_plays=big_plays,
        third_down_pct=round(third_down_pct, 2),
        redzone_td_pct=round(redzone_td_pct, 2),
        third_down_attempts=third_attempts,
        third_down_converted=third_converted,
        redzone_trips=rz_trips,
        redzone_td_drives=rz_td_drives,
    )


def compute_team_keys_from_pbp(
    pbp: pd.DataFrame,
    team: str,
    big_play_pass_yards: Optional[int] = None,
    big_play_rush_yards: Optional[int] = None,
    red_zone_yardline: Optional[int] = None,
    third_down_number: Optional[int] = None,
    config: Optional[Config] = None,
) -> TeamKeys:
    """
    Backward-compatible wrapper: compute 5 Keys for one team using config defaults.
    Prefer compute_team_keys() for direct control. Big plays use pass>=15, run>=10 by default.
    """
    cfg = config or DEFAULT_CONFIG
    pass_yd = big_play_pass_yards if big_play_pass_yards is not None else getattr(cfg, "big_play_pass_yards", BIG_PLAY_PASS_YARDS)
    rush_yd = big_play_rush_yards if big_play_rush_yards is not None else getattr(cfg, "big_play_rush_yards", BIG_PLAY_RUSH_YARDS)
    rz = red_zone_yardline if red_zone_yardline is not None else cfg.red_zone_yardline
    third = third_down_number if third_down_number is not None else cfg.third_down_number
    return compute_team_keys(
        pbp, team,
        big_play_pass_yards=pass_yd,
        big_play_rush_yards=rush_yd,
        red_zone_yardline=rz,
        third_down_number=third,
    )
