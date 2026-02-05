"""Data loading via nflreadpy (nflverse)."""

from superbowlengine.data.load import (
    get_pbp,
    get_schedules,
    load_pbp,
    see_pbp_cols,
    validate_pbp_for_keys,
    ensure_nonempty,
)
from superbowlengine.data.cache import read_cached_pbp, write_cached_pbp
from superbowlengine.data.errors import MissingColumnsError, SeasonNotAvailableError
from superbowlengine.data.availability import (
    assess_5keys_availability,
    AvailabilityReport,
    KeyAvailability,
)
from superbowlengine.data.games import list_team_games, team_games_summary


def get_cached_pbp(
    years: list,
    columns: list | None = None,
    cache_dir: str | None = None,
    config=None,
):
    """Backward compatibility: same as get_pbp (nflreadpy handles caching; cache_dir ignored)."""
    from superbowlengine.config import DEFAULT_CONFIG
    cfg = config or DEFAULT_CONFIG
    cols = columns or list(cfg.pbp_columns)
    return get_pbp(years, season_type="ALL", columns=cols)


__all__ = [
    "get_pbp",
    "get_schedules",
    "load_pbp",
    "see_pbp_cols",
    "validate_pbp_for_keys",
    "ensure_nonempty",
    "read_cached_pbp",
    "write_cached_pbp",
    "get_cached_pbp",
    "MissingColumnsError",
    "SeasonNotAvailableError",
    "assess_5keys_availability",
    "AvailabilityReport",
    "KeyAvailability",
    "list_team_games",
    "team_games_summary",
]
