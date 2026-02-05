"""Configuration with defaults for SuperBowlEngine."""

from dataclasses import dataclass, field
from typing import List


# Season type filter for PBP
SeasonType = str  # "REG" | "POST" | "ALL"


@dataclass(frozen=True)
class DataSpec:
    """
    Data loading specification: years, season filter, required columns, and cache.
    Used by get_pbp() to load/filter and optionally use disk cache.
    """

    years: List[int] = field(default_factory=lambda: [2025])
    season_type: SeasonType = "POST"  # "REG", "POST", or "ALL"
    required_columns: List[str] = field(default_factory=list)  # empty = use Config.pbp_columns
    cache_dir: str | None = None


@dataclass(frozen=True)
class Config:
    """Default config: year, thresholds, and model weights."""

    # Data
    default_year: int = 2025
    default_years: List[int] = field(default_factory=lambda: [2025])

    # Feature thresholds (big plays: pass >= 15, run >= 10)
    big_play_yards: int = 20  # legacy; use big_play_pass_yards / big_play_rush_yards
    big_play_pass_yards: int = 15
    big_play_rush_yards: int = 10
    red_zone_yardline: int = 20
    third_down_number: int = 3

    # Professor-keys model weights
    turnover_weight: float = 1.35
    key_weight: float = 0.55
    rule_bonus: float = 0.40

    # Scaling divisors used in logit (margins / divisor)
    top_divisor: float = 6.0
    turnover_divisor: float = 1.0
    big_play_divisor: float = 2.0
    third_down_divisor: float = 10.0
    redzone_divisor: float = 12.0

    # PBP columns needed for 5 Keys + SOS
    pbp_columns: List[str] = field(
        default_factory=lambda: [
            "game_id",
            "season_type",
            "week",
            "posteam",
            "defteam",
            "home_team",
            "away_team",
            "down",
            "ydstogo",
            "yards_gained",
            "play_type",
            "touchdown",
            "interception",
            "fumble_lost",
            "drive",
            "drive_time_of_possession",
            "yardline_100",
            "home_score",
            "away_score",
        ]
    )


# Singleton default config; override via env or explicit args in APIs
DEFAULT_CONFIG = Config()


def default_data_spec(cache_dir: str | None = None) -> DataSpec:
    """Build a DataSpec using DEFAULT_CONFIG defaults."""
    return DataSpec(
        years=DEFAULT_CONFIG.default_years.copy(),
        season_type="POST",
        required_columns=list(DEFAULT_CONFIG.pbp_columns),
        cache_dir=cache_dir,
    )
