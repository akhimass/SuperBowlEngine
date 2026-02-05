"""
Regression tests: professor rule (3+ keys winner must have win probability >= 0.5).

Ensures we never output e.g. 'NE wins 2/5 keys but has 94.6% win probability'.
"""

import pytest

from superbowlengine.features.keys import TeamKeys
from superbowlengine.models.professor_keys import predict


def _keys(team: str, top: float, to: int, big: int, third: float, rz: float) -> TeamKeys:
    return TeamKeys(team=team, top_min=top, turnovers=to, big_plays=big, third_down_pct=third, redzone_td_pct=rz)


def test_team_a_wins_4_keys_has_majority_probability() -> None:
    """When team_a wins 4/5 keys with clear margins, p_team_a_win > 0.5 and predicted_winner == team_a."""
    # A wins TOP, TO (fewer), BIG, 3D; B wins only RZ
    team_a = _keys("A", 35.0, 0, 6, 55.0, 40.0)
    team_b = _keys("B", 25.0, 2, 2, 40.0, 55.0)
    out = predict(team_a, team_b, team_a_name="A", team_b_name="B")
    assert out["keys_won"]["A"] == 4
    assert out["keys_won"]["B"] == 1
    assert out["p_team_a_win"] > 0.5
    assert out["predicted_winner"] == "A"


def test_team_b_wins_3_keys_has_majority_probability() -> None:
    """When team_b wins 3/5 keys, p_team_b_win > 0.5 and predicted_winner == team_b."""
    # B wins BIG, 3D, RZ; A wins TOP and TO
    team_a = _keys("A", 32.0, 0, 2, 42.0, 40.0)
    team_b = _keys("B", 28.0, 1, 5, 52.0, 55.0)
    out = predict(team_a, team_b, team_a_name="A", team_b_name="B")
    assert out["keys_won"]["B"] == 3
    assert out["keys_won"]["A"] == 2
    assert out["p_team_b_win"] > 0.5
    assert out["predicted_winner"] == "B"


def test_team_a_wins_3_keys_never_loses_to_margins() -> None:
    """Even with margins favoring B, if A wins 3 keys, A is predicted winner (professor rule clamp)."""
    # A wins TOP, TO, BIG (3 keys); B wins 3D and RZ with huge margins so raw logit might favor B
    team_a = _keys("A", 31.0, 0, 4, 35.0, 35.0)
    team_b = _keys("B", 29.0, 2, 3, 65.0, 70.0)
    out = predict(team_a, team_b, team_a_name="A", team_b_name="B")
    assert out["keys_won"]["A"] == 3
    assert out["keys_won"]["B"] == 2
    assert out["p_team_a_win"] >= 0.5
    assert out["predicted_winner"] == "A"


def test_predicted_winner_matches_higher_probability() -> None:
    """predicted_winner is team_a iff p_team_a_win >= 0.5, else team_b."""
    team_a = _keys("KC", 30.0, 1, 4, 50.0, 50.0)
    team_b = _keys("SF", 30.0, 1, 4, 50.0, 50.0)
    out = predict(team_a, team_b, team_a_name="KC", team_b_name="SF")
    if out["predicted_winner"] == "KC":
        assert out["p_team_a_win"] >= 0.5
    else:
        assert out["p_team_b_win"] >= 0.5
    assert abs(out["p_team_a_win"] + out["p_team_b_win"] - 1.0) < 1e-6
