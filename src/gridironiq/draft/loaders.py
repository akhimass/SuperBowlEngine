from __future__ import annotations

from typing import Iterable

import pandas as pd


def load_combine(combine_seasons: Iterable[int]) -> pd.DataFrame:
    import nflreadpy as nfl  # noqa: PLC0415

    seasons = list(combine_seasons)
    df = nfl.load_combine(seasons=seasons).to_pandas()
    if df.empty:
        raise ValueError(f"No combine rows returned for seasons={seasons}")
    return df


def load_draft_picks(draft_seasons: Iterable[int]) -> pd.DataFrame:
    import nflreadpy as nfl  # noqa: PLC0415

    seasons = list(draft_seasons)
    df = nfl.load_draft_picks(seasons=seasons).to_pandas()
    return df


def load_snap_counts(nfl_season: int) -> pd.DataFrame:
    import nflreadpy as nfl  # noqa: PLC0415

    return nfl.load_snap_counts(seasons=[nfl_season]).to_pandas()


def load_injuries(nfl_season: int) -> pd.DataFrame:
    import nflreadpy as nfl  # noqa: PLC0415

    return nfl.load_injuries(seasons=[nfl_season]).to_pandas()


def load_rosters(nfl_season: int) -> pd.DataFrame:
    import nflreadpy as nfl  # noqa: PLC0415

    return nfl.load_rosters(seasons=[nfl_season]).to_pandas()


def load_players() -> pd.DataFrame:
    import nflreadpy as nfl  # noqa: PLC0415

    return nfl.load_players().to_pandas()


def load_player_stats_reg(nfl_season: int) -> pd.DataFrame:
    """Regular-season player stats (nflverse) for room production / scheme shares."""
    import nflreadpy as nfl  # noqa: PLC0415

    df = nfl.load_player_stats(seasons=[nfl_season]).to_pandas()
    if df.empty:
        return df
    st = df["season_type"].astype(str).str.upper()
    return df.loc[st == "REG"].copy()


def load_pbp_reg(nfl_season: int) -> pd.DataFrame:
    """
    Regular-season PBP for EPA / tendency features (nflverse).
    """
    import nflreadpy as nfl  # noqa: PLC0415

    df = nfl.load_pbp(seasons=[nfl_season]).to_pandas()
    if df.empty:
        raise ValueError(f"Empty PBP for season={nfl_season}")
    st = df["season_type"].astype(str).str.upper()
    df = df.loc[st == "REG"].copy()
    if "epa" not in df.columns:
        raise ValueError("PBP missing epa column")
    return df
