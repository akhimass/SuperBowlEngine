"""Tests for turnover regression: expected_turnovers clamp/weighting, turnovers_in_losses_vs_wins."""

import pytest

from superbowlengine.models.turnover_regression import (
    expected_turnovers,
    turnovers_in_losses_vs_wins,
)


def test_expected_turnovers_weighting() -> None:
    """Blend = w_post * post_to_pg + w_season * season_to_pg."""
    # post=1.0, season=0.0 -> default weights 0.55*1 + 0.45*0 = 0.55
    assert expected_turnovers(0.0, 1.0) == 0.55
    # post=0.0, season=1.0 -> 0.45
    assert expected_turnovers(1.0, 0.0) == 0.45
    # 0.5 each -> 0.5
    assert expected_turnovers(0.5, 0.5) == 0.5
    # Custom weights 50/50
    assert expected_turnovers(0.0, 2.0, w_post=0.5, w_season=0.5) == 1.0


def test_expected_turnovers_clamp_floor() -> None:
    """Result is clamped to floor (default 0.4)."""
    # 0 post, 0 season -> blend 0, but floor 0.4
    assert expected_turnovers(0.0, 0.0) == 0.4
    assert expected_turnovers(0.0, 0.0, floor=0.5) == 0.5
    assert expected_turnovers(0.0, 0.0, floor=0.2) == 0.2


def test_expected_turnovers_clamp_ceil() -> None:
    """Result is clamped to ceil (default 2.2)."""
    # Very high rates -> cap at 2.2
    assert expected_turnovers(5.0, 5.0) == 2.2
    assert expected_turnovers(10.0, 10.0, ceil=3.0) == 3.0
    assert expected_turnovers(1.0, 1.0, ceil=1.5) == 1.5


def test_expected_turnovers_within_range() -> None:
    """When blend is inside [floor, ceil], no clamp."""
    x = expected_turnovers(1.0, 1.0)
    assert 0.4 <= x <= 2.2
    assert x == 1.0
    x = expected_turnovers(1.2, 0.8)
    assert x == pytest.approx(0.55 * 0.8 + 0.45 * 1.2)


def test_turnovers_in_losses_vs_wins() -> None:
    """Helper splits by win/loss and computes to_per_game."""
    game_keys = [
        {"turnovers": 2, "win": False},
        {"turnovers": 1, "win": False},
        {"turnovers": 0, "win": True},
        {"turnovers": 1, "win": True},
    ]
    out = turnovers_in_losses_vs_wins(game_keys)
    assert out["losses"]["games"] == 2
    assert out["losses"]["turnovers"] == 3
    assert out["losses"]["to_per_game"] == 1.5
    assert out["wins"]["games"] == 2
    assert out["wins"]["turnovers"] == 1
    assert out["wins"]["to_per_game"] == 0.5


def test_turnovers_in_losses_vs_wins_empty() -> None:
    out = turnovers_in_losses_vs_wins([])
    assert out["losses"]["games"] == 0 and out["losses"]["to_per_game"] == 0.0
    assert out["wins"]["games"] == 0 and out["wins"]["to_per_game"] == 0.0


def test_turnovers_in_losses_vs_wins_missing_keys() -> None:
    """Missing 'turnovers' or 'win' use defaults 0 and False."""
    out = turnovers_in_losses_vs_wins([{}, {"turnovers": 1}])
    assert out["losses"]["games"] == 2
    assert out["losses"]["turnovers"] == 1
