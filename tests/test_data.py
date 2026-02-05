"""Tests for data layer: get_pbp, cache, column validation, DataSpec."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from superbowlengine.config import DataSpec, default_data_spec, DEFAULT_CONFIG
from superbowlengine.data.load import (
    get_pbp,
    see_pbp_cols,
    validate_pbp_for_keys,
    validate_pbp_for_top,
    validate_pbp_for_turnovers,
    validate_pbp_for_third_down,
    validate_pbp_for_redzone,
)
from superbowlengine.data.errors import MissingColumnsError
from superbowlengine.data.cache import read_cached_pbp, write_cached_pbp, _cache_path


def test_validate_pbp_for_top_pass() -> None:
    df = pd.DataFrame(columns=["drive", "drive_time_of_possession", "game_id"])
    validate_pbp_for_top(df)


def test_validate_pbp_for_top_missing() -> None:
    df = pd.DataFrame(columns=["drive", "game_id"])
    with pytest.raises(MissingColumnsError, match="TOP requires"):
        validate_pbp_for_top(df)


def test_validate_pbp_for_turnovers_missing() -> None:
    df = pd.DataFrame(columns=["interception"])
    with pytest.raises(MissingColumnsError, match="Turnovers requires"):
        validate_pbp_for_turnovers(df)


def test_validate_pbp_for_third_down_first_down_ok() -> None:
    df = pd.DataFrame(columns=["down", "ydstogo", "first_down"])
    validate_pbp_for_third_down(df)


def test_validate_pbp_for_third_down_yards_ok() -> None:
    df = pd.DataFrame(columns=["down", "ydstogo", "yards_gained"])
    validate_pbp_for_third_down(df)


def test_validate_pbp_for_third_down_missing() -> None:
    df = pd.DataFrame(columns=["down"])
    with pytest.raises(MissingColumnsError, match="3rd down"):
        validate_pbp_for_third_down(df)


def test_validate_pbp_for_redzone_missing() -> None:
    df = pd.DataFrame(columns=["yardline_100", "drive"])
    with pytest.raises(MissingColumnsError, match="Red zone requires"):
        validate_pbp_for_redzone(df)


def test_validate_pbp_for_keys_minimal_core_missing() -> None:
    """Core columns missing raises MissingColumnsError."""
    df = pd.DataFrame(columns=["game_id"])
    with pytest.raises(MissingColumnsError, match="core|Missing"):
        validate_pbp_for_keys(df)


def test_cache_path() -> None:
    p = _cache_path([2025], "/tmp/cache")
    assert "2025" in str(p)
    assert p.suffix == ".parquet"
    p2 = _cache_path([2024, 2025], "/tmp/cache")
    assert "2024" in str(p2) and "2025" in str(p2)


def test_get_pbp_returns_dataframe() -> None:
    """get_pbp returns a pandas DataFrame (integration: requires nflreadpy and network)."""
    try:
        out = get_pbp([2024], season_type="POST", columns=list(DEFAULT_CONFIG.pbp_columns))
    except Exception:
        pytest.skip("get_pbp requires nflreadpy and network")
    assert isinstance(out, pd.DataFrame)
    assert "game_id" in out.columns
    assert "season_type" in out.columns


def test_data_spec_defaults() -> None:
    spec = default_data_spec(cache_dir="/tmp/x")
    assert spec.years == [2025]
    assert spec.season_type == "POST"
    assert spec.cache_dir == "/tmp/x"
    assert "game_id" in spec.required_columns


def test_see_pbp_cols_return_type() -> None:
    """see_pbp_cols returns a list (requires nflreadpy and network)."""
    try:
        cols = see_pbp_cols(print_=False)
    except Exception:
        pytest.skip("see_pbp_cols requires nflreadpy and network")
    assert isinstance(cols, list)


def test_read_write_cached_pbp() -> None:
    """Manual cache read/write still works."""
    with tempfile.TemporaryDirectory() as d:
        df = pd.DataFrame({c: [] for c in DEFAULT_CONFIG.pbp_columns})
        write_cached_pbp(df, [2025], d)
        path = read_cached_pbp([2025], d)
        assert path is not None
        assert path.exists()
