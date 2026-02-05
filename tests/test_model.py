"""Tests for professor_keys: unified engine, Explanation, drivers, 3+ keys rule."""

import pytest

from superbowlengine.features.keys import TeamKeys
from superbowlengine.models.professor_keys import (
    Explanation,
    TeamContext,
    predict,
    predict_from_keys,
)


def _keys(team: str, top: float, to: int, big: int, third: float, rz: float) -> TeamKeys:
    return TeamKeys(team=team, top_min=top, turnovers=to, big_plays=big, third_down_pct=third, redzone_td_pct=rz)


def test_predict_returns_unified_shape() -> None:
    """Engine returns predicted_winner, probs, keys_won, top_3_drivers, explanation."""
    sea = _keys("SEA", 30.0, 1, 4, 50.0, 50.0)
    ne = _keys("NE", 28.0, 2, 3, 45.0, 45.0)
    out = predict(sea, ne, team_a_name="SEA", team_b_name="NE")
    assert out["predicted_winner"] in ("SEA", "NE")
    assert "p_team_a_win" in out and "p_team_b_win" in out
    assert abs(out["p_team_a_win"] + out["p_team_b_win"] - 1.0) < 1e-6
    assert set(out["keys_won"].keys()) == {"SEA", "NE"}
    assert out["keys_won"]["SEA"] + out["keys_won"]["NE"] == 5
    assert len(out["top_3_drivers"]) <= 3
    assert isinstance(out["explanation"], Explanation)
    assert set(out["explanation"].key_winners.keys()) == {"TOP", "TO", "BIG", "3D", "RZ"}
    assert set(out["explanation"].margin_table.keys()) >= {"TOP", "TO", "BIG", "3D", "RZ"}
    assert "logit" in out
    assert set(out["explanation"].contributions.keys()) >= {"TOP", "TO", "BIG", "3D", "RZ", "rule_3_keys"}
    assert abs(out["explanation"].logit - out["logit"]) < 0.001
    # Probability must match predicted winner
    if out["predicted_winner"] == "SEA":
        assert out["p_team_a_win"] >= 0.5
    else:
        assert out["p_team_b_win"] >= 0.5


def test_predict_three_plus_keys_rule_bonus() -> None:
    """Team that wins 3+ keys gets rule bonus (discrete); drives logit."""
    # SEA wins all 5 keys -> gets rule bonus
    sea = _keys("SEA", 35.0, 0, 6, 60.0, 60.0)
    ne = _keys("NE", 25.0, 3, 2, 35.0, 35.0)
    out = predict(sea, ne, team_a_name="SEA", team_b_name="NE")
    assert out["keys_won"]["SEA"] == 5
    assert out["explanation"].contributions.get("rule_3_keys", 0) > 0
    assert out["predicted_winner"] == "SEA"
    assert out["p_team_a_win"] > 0.5


def test_predict_fixed_scenario_turnover_dominates() -> None:
    """When TO margin is large, TO is a top driver and drives outcome."""
    sea = _keys("SEA", 28.0, 0, 3, 45.0, 45.0)
    ne = _keys("NE", 30.0, 3, 4, 50.0, 50.0)  # NE more TOP/BIG/3D/RZ but 3 TO
    out = predict(sea, ne, team_a_name="SEA", team_b_name="NE")
    driver_names = [d[0] for d in out["top_3_drivers"]]
    assert "TO" in driver_names
    # SEA has fewer TO (wins TO key) and wins 1 key (TO); NE wins 4 keys but 3 TO hurt
    assert out["explanation"].margin_table["TO"] == 3.0  # NE 3 - SEA 0


def test_predict_fixed_scenario_near_tie() -> None:
    """When B wins 3 keys (BIG, 3D, RZ), professor rule ensures B is predicted winner; p_team_a_win <= 0.5."""
    # A wins TOP and TO; B wins BIG, 3D, RZ -> B has 3 keys, gets rule and must win
    a = _keys("A", 31.0, 0, 3, 48.0, 48.0)
    b = _keys("B", 29.0, 1, 4, 52.0, 52.0)
    out = predict(a, b, team_a_name="A", team_b_name="B")
    assert out["keys_won"]["A"] == 2 and out["keys_won"]["B"] == 3
    assert out["predicted_winner"] == "B"
    assert out["p_team_b_win"] >= 0.5
    assert 0.3 <= out["p_team_a_win"] <= 0.5


def test_predict_with_context_sos_and_expected_to() -> None:
    """Context SOS z and expected TO are used; show up in margin_table and drivers."""
    sea = _keys("SEA", 30.0, 0, 4, 50.0, 50.0)
    ne = _keys("NE", 30.0, 0, 4, 50.0, 50.0)
    ctx_a = TeamContext(sos_z=0.5, expected_turnovers_per_game=1.0, dgi=0.1)
    ctx_b = TeamContext(sos_z=-0.3, expected_turnovers_per_game=1.2, dgi=0.0)
    out = predict(sea, ne, team_a_name="SEA", team_b_name="NE", context_a=ctx_a, context_b=ctx_b)
    assert "SOS_z" in out["explanation"].margin_table
    assert out["explanation"].margin_table["SOS_z"] == 0.8  # 0.5 - (-0.3)
    assert out["explanation"].margin_table["TO"] == pytest.approx(0.2)  # 1.2 - 1.0 (expected)
    # DGI/SOS can appear in drivers if non-zero weight
    assert "DGI" in out["explanation"].margin_table


def test_predict_generic_team_names() -> None:
    """Engine works with any team names, not only SEA/NE."""
    a = _keys("KC", 32.0, 1, 5, 55.0, 55.0)
    b = _keys("SF", 28.0, 2, 3, 45.0, 45.0)
    out = predict(a, b, team_a_name="KC", team_b_name="SF")
    assert set(out["keys_won"].keys()) == {"KC", "SF"}
    assert out["predicted_winner"] in ("KC", "SF")
    assert all(out["explanation"].key_winners[k] in ("KC", "SF") for k in out["explanation"].key_winners)


def test_predict_from_keys_backward_compat() -> None:
    """Legacy predict_from_keys returns p_sea_win, p_ne_win, key_winners, margins_sea_minus_ne."""
    sea = TeamKeys(team="SEA", top_min=31.0, turnovers=0, big_plays=5, third_down_pct=55.0, redzone_td_pct=55.0)
    ne = TeamKeys(team="NE", top_min=30.0, turnovers=1, big_plays=4, third_down_pct=50.0, redzone_td_pct=50.0)
    out = predict_from_keys(sea, ne)
    assert "p_sea_win" in out
    assert "p_ne_win" in out
    assert out["predicted_winner"] in ("SEA", "NE")
    assert abs(out["p_sea_win"] + out["p_ne_win"] - 1.0) < 1e-6
    assert set(out["key_winners"].keys()) == {"TOP", "TO", "BIG", "3D", "RZ"}
    assert set(out["margins_sea_minus_ne"].keys()) == {"TOP", "TO", "BIG", "3D", "RZ"}
    assert out["keys_won"]["SEA"] + out["keys_won"]["NE"] == 5


def test_explanation_driver_ranking_absolute_contribution() -> None:
    """Driver ranking lists (component, contribution) by absolute contribution."""
    sea = _keys("SEA", 35.0, 0, 6, 60.0, 60.0)
    ne = _keys("NE", 25.0, 3, 2, 35.0, 35.0)
    out = predict(sea, ne, team_a_name="SEA", team_b_name="NE")
    ranking = out["explanation"].driver_ranking
    assert len(ranking) <= 3
    for name, contrib in ranking:
        assert isinstance(name, str)
        assert isinstance(contrib, (int, float))
    # Should be sorted by abs(contrib) descending
    abs_contribs = [abs(c) for _, c in ranking]
    assert abs_contribs == sorted(abs_contribs, reverse=True)
