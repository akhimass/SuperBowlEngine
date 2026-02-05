"""
Integration contract tests for nflreadpy PBP loading.

Run only when RUN_NFLREADPY_TESTS=1 (or mark as slow and run with pytest -m slow).
Asserts get_pbp([2024], season_type="POST") returns non-empty DataFrame with
required columns and correct season/season_type values.
"""

import os

import pandas as pd
import pytest

from superbowlengine.data import get_pbp
from superbowlengine.data.load import REQUIRED_PBP_COLUMNS


def _nflreadpy_available() -> bool:
    return os.environ.get("RUN_NFLREADPY_TESTS", "") == "1"


@pytest.mark.skipif(not _nflreadpy_available(), reason="Set RUN_NFLREADPY_TESTS=1 to run")
@pytest.mark.slow
def test_get_pbp_2024_post_contract() -> None:
    """Contract: get_pbp([2024], season_type='POST') returns valid PBP."""
    df = get_pbp([2024], season_type="POST")
    assert isinstance(df, pd.DataFrame), "get_pbp must return a DataFrame"
    assert not df.empty, "PBP for 2024 POST must be non-empty"
    for col in REQUIRED_PBP_COLUMNS:
        assert col in df.columns, "Required column %r missing" % col
    if "season" in df.columns:
        assert 2024 in df["season"].unique(), "season must contain 2024"
    assert "season_type" in df.columns, "season_type column required"
    post_vals = df["season_type"].astype(str).str.upper()
    assert (post_vals == "POST").all(), "season_type must be POST"
