"""Tests for time utils."""

import pandas as pd
import pytest

from superbowlengine.utils.time import mmss_to_seconds


def test_mmss_to_seconds_normal() -> None:
    assert mmss_to_seconds("5:30") == 330
    assert mmss_to_seconds("0:00") == 0
    assert mmss_to_seconds("12:05") == 725


def test_mmss_to_seconds_nan() -> None:
    assert mmss_to_seconds(pd.NA) == 0
    assert mmss_to_seconds(float("nan")) == 0


def test_mmss_to_seconds_invalid() -> None:
    assert mmss_to_seconds("") == 0
    assert mmss_to_seconds("5") == 0
    assert mmss_to_seconds("5:30:00") == 0
