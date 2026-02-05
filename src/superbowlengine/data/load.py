"""
Load play-by-play and schedule data via nflreadpy (nflverse).

Column meanings and availability are defined by the nflreadr/nflverse PBP data
dictionary. If a required column is missing, we fail fast with a helpful error.

Uses nflreadpy's built-in caching (env: NFLREADPY_CACHE, NFLREADPY_CACHE_DIR).
Returns pandas DataFrames with column names expected by feature engineering.
"""

import logging
from typing import List, Optional

import pandas as pd

from superbowlengine.config import Config, DEFAULT_CONFIG
from superbowlengine.data.errors import MissingColumnsError, SeasonNotAvailableError

logger = logging.getLogger(__name__)

# Map alternate schema names to our expected names (nflverse/nflreadr data dictionary).
# Future-proofs against minor schema drifts without touching feature logic.
COLUMN_ALIASES: dict[str, str] = {
    "goal_to_go": "ydstogo",
    "total_home_score": "home_score",
    "total_away_score": "away_score",
}

# Columns required for 5 Keys + SOS. See nflreadr/nflverse PBP data dictionary.
# Missing any of these raises MissingColumnsError via validate_pbp_for_*.
REQUIRED_PBP_COLUMNS = [
    "game_id",
    "season_type",
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

# Optional: week, season, first_down; fill with NaN/0 if missing
OPTIONAL_PBP_COLUMNS = ["week", "season", "first_down"]


def _apply_aliases(df: pd.DataFrame, aliases: dict[str, str]) -> pd.DataFrame:
    """Rename columns using alias map; only renames if source exists and target missing."""
    renames = {}
    for src, tgt in aliases.items():
        if src in df.columns and tgt not in df.columns:
            renames[src] = tgt
    if renames:
        df = df.rename(columns=renames)
    return df


def ensure_nonempty(
    df: pd.DataFrame,
    years: List[int],
    season_type: str,
) -> None:
    """
    Raise SeasonNotAvailableError if the DataFrame is empty after filtering.
    Prevents silent all-zero predictions when data is not yet published.
    """
    if df.empty:
        raise SeasonNotAvailableError(
            f"Data may not be published yet for year(s) {years} and season_type={season_type!r}. "
            "No rows returned.",
            year=years[0] if years else None,
            season_type=season_type,
        )


def validate_pbp_for_top(df: pd.DataFrame) -> None:
    """TOP key requires drive, drive_time_of_possession, game_id."""
    required = ["drive", "drive_time_of_possession", "game_id"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise MissingColumnsError(
            f"TOP requires: {required}. Missing: {missing}.",
            missing_columns=missing,
            context="TOP",
        )


def validate_pbp_for_turnovers(df: pd.DataFrame) -> None:
    """Turnovers key requires interception, fumble_lost."""
    required = ["interception", "fumble_lost"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise MissingColumnsError(
            f"Turnovers requires: {required}. Missing: {missing}.",
            missing_columns=missing,
            context="Turnovers",
        )


def validate_pbp_for_third_down(df: pd.DataFrame) -> None:
    """3rd down key requires down, ydstogo, and either first_down OR yards_gained."""
    required = ["down", "ydstogo"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise MissingColumnsError(
            f"3rd down requires: down, ydstogo, and (first_down OR yards_gained). Missing base: {missing}.",
            missing_columns=missing,
            context="3rd down",
        )
    has_first_down = "first_down" in df.columns
    has_yards = "yards_gained" in df.columns
    if not (has_first_down or has_yards):
        raise MissingColumnsError(
            "3rd down requires either first_down OR yards_gained. Neither present.",
            missing_columns=[],
            context="3rd down",
        )


def validate_pbp_for_redzone(df: pd.DataFrame) -> None:
    """Red zone key requires yardline_100, drive, game_id, touchdown."""
    required = ["yardline_100", "drive", "game_id", "touchdown"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise MissingColumnsError(
            f"Red zone requires: {required}. Missing: {missing}.",
            missing_columns=missing,
            context="Red zone",
        )


def _validate_pbp_core(df: pd.DataFrame) -> None:
    """Core columns needed for SOS and keys (posteam, teams, scores, play_type, season_type)."""
    required = [
        "game_id",
        "season_type",
        "posteam",
        "defteam",
        "home_team",
        "away_team",
        "play_type",
        "home_score",
        "away_score",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise MissingColumnsError(
            f"PBP core requires: {required}. Missing: {missing}.",
            missing_columns=missing,
            context="core",
        )


def validate_pbp_for_keys(df: pd.DataFrame) -> None:
    """
    Validate that PBP has all key-critical columns for TOP, Turnovers, 3rd down, Red zone,
    plus core columns (posteam, teams, scores, etc.). Raises MissingColumnsError with
    targeted message per key if something is missing.
    """
    _validate_pbp_core(df)
    validate_pbp_for_top(df)
    validate_pbp_for_turnovers(df)
    validate_pbp_for_third_down(df)
    validate_pbp_for_redzone(df)


def get_pbp(
    years: List[int],
    *,
    season_type: str = "POST",
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Load PBP for the given years via nflreadpy; convert to pandas and filter.

    Caching is handled by nflreadpy (set NFLREADPY_CACHE=filesystem, NFLREADPY_CACHE_DIR).
    season_type: "REG", "POST", or "ALL".
    columns: subset to return; default is DEFAULT_CONFIG.pbp_columns.
    Applies COLUMN_ALIASES before validation. Raises MissingColumnsError or
    SeasonNotAvailableError if data is invalid or empty for the requested filter.
    """
    import nflreadpy as nfl  # noqa: PLC0415

    cols_use = columns or list(DEFAULT_CONFIG.pbp_columns)
    logger.info("Loading PBP for years=%s (season_type=%s) via nflreadpy", years, season_type)

    pl_pbp = nfl.load_pbp(seasons=years)
    df = pl_pbp.to_pandas()
    if df.empty:
        ensure_nonempty(df, years, season_type)

    df = _apply_aliases(df, COLUMN_ALIASES)

    # Filter by season_type if column exists
    if "season_type" in df.columns and season_type != "ALL":
        st = df["season_type"].astype(str).str.upper()
        if season_type == "REG":
            df = df[st == "REG"].copy()
        elif season_type == "POST":
            df = df[st == "POST"].copy()

    ensure_nonempty(df, years, season_type)
    validate_pbp_for_keys(df)

    # Return only requested columns that exist
    out_cols = [c for c in cols_use if c in df.columns]
    if out_cols != cols_use:
        missing = set(cols_use) - set(out_cols)
        logger.warning("Requested columns not in data (filled with NaN): %s", missing)
        for c in missing:
            df[c] = pd.NA
        out_cols = cols_use
    return df[out_cols].copy()


def get_schedules(years: List[int]) -> pd.DataFrame:
    """
    Load game schedules for the given years via nflreadpy; convert to pandas.

    Applies COLUMN_ALIASES for consistent naming. Returns at least: game_id,
    home_team, away_team; home_score/away_score if available.
    """
    import nflreadpy as nfl  # noqa: PLC0415

    logger.info("Loading schedules for years=%s via nflreadpy", years)
    pl_sched = nfl.load_schedules(seasons=years)
    df = pl_sched.to_pandas()
    if df.empty:
        return pd.DataFrame(columns=["game_id", "home_team", "away_team", "home_score", "away_score"])

    df = _apply_aliases(df, COLUMN_ALIASES)
    return df


def see_pbp_cols(
    years: Optional[List[int]] = None,
    print_: bool = True,
) -> List[str]:
    """
    Return available PBP column names (one year load via nflreadpy).
    Useful for building required_columns or debugging.
    """
    import nflreadpy as nfl  # noqa: PLC0415

    y = years or [DEFAULT_CONFIG.default_year]
    logger.info("Loading PBP for years=%s to list schema", y)
    pl_pbp = nfl.load_pbp(seasons=y)
    df = pl_pbp.to_pandas()
    cols = df.columns.tolist()
    if print_:
        print("Available PBP columns (%d):" % len(cols))
        for c in cols:
            print(" ", c)
    return cols


def load_pbp(
    years: Optional[List[int]] = None,
    columns: Optional[List[str]] = None,
    config: Optional[Config] = None,
) -> pd.DataFrame:
    """
    Backward-compatible: load PBP for given years and columns (season_type=ALL).
    Prefer get_pbp() for explicit season_type.
    """
    cfg = config or DEFAULT_CONFIG
    years = years or cfg.default_years
    columns = columns or cfg.pbp_columns
    return get_pbp(years, season_type="ALL", columns=columns)
