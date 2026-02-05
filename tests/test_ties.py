"""
Enforce explicit TIE logic: key_winners returns TIE for ties, keys_won counts only non-ties,
3+ keys rule uses keys_won only, and keys_won + ties == 5.
"""

import pytest

from superbowlengine.core.key_compare import compare_values, compare_5keys, KeyComparison
from superbowlengine.features.keys import TeamKeys
from superbowlengine.models.professor_keys import predict, KEY_NAMES


def _keys(team: str, top_min: float, turnovers: float, big_plays: float, third_down_pct: float, redzone_td_pct: float) -> TeamKeys:
    return TeamKeys(
        team=team,
        top_min=top_min,
        turnovers=int(turnovers) if turnovers == int(turnovers) else int(turnovers),
        big_plays=int(big_plays) if big_plays == int(big_plays) else int(big_plays),
        third_down_pct=third_down_pct,
        redzone_td_pct=redzone_td_pct,
    )


# --- 1) BIG tied: keys_a.big_plays = 8, keys_b.big_plays = 8 ---
def test_big_tied_key_winners_and_keys_won():
    keys_a = _keys("SEA", 28.0, 1.0, 8, 45.0, 60.0)
    keys_b = _keys("NE", 26.0, 1.0, 8, 44.0, 58.0)
    out = predict(keys_a, keys_b, team_a_name="SEA", team_b_name="NE")
    assert out["explanation"].key_winners["BIG"] == "TIE"
    assert "BIG" in out["tied_keys"]
    # TO is also 1 vs 1 => TIE, so ties >= 1. BIG must not increment either team's keys_won.
    assert out["ties"] >= 1
    assert out["keys_won"]["SEA"] + out["keys_won"]["NE"] + out["ties"] == 5
    assert "BIG" not in [k for k, w in out["explanation"].key_winners.items() if w == "SEA"]
    assert "BIG" not in [k for k, w in out["explanation"].key_winners.items() if w == "NE"]


# --- 2) Turnovers tie with 0.0 ---
def test_turnovers_tie_zero():
    keys_a = _keys("SEA", 28.0, 0, 6, 45.0, 60.0)
    keys_b = _keys("NE", 26.0, 0, 5, 44.0, 58.0)
    out = predict(keys_a, keys_b, team_a_name="SEA", team_b_name="NE")
    assert out["explanation"].key_winners["TO"] == "TIE"
    assert "TO" in out["tied_keys"]
    assert out["keys_won"]["SEA"] + out["keys_won"]["NE"] + out["ties"] == 5


# --- 3) eps behavior: a=8.0000000001, b=8.0 within eps => tie ---
def test_eps_tie():
    comp = compare_values(8.0000000001, 8.0, "SEA", "NE", higher_is_better=True, eps=1e-9)
    assert comp.winner == "TIE"
    comp2 = compare_values(8.0001, 8.0, "SEA", "NE", higher_is_better=True, eps=1e-9)
    assert comp2.winner == "SEA"


# --- 4) 3+ keys rule: team_a wins 2, team_b wins 2, 1 tie => no rule bonus ---
def test_three_keys_rule_no_bonus_when_two_two_one():
    # Construct so SEA wins 2, NE wins 2, 1 TIE (e.g. TOP, TO to SEA; BIG, 3D to NE; RZ TIE)
    # SEA: higher TOP, lower TO, lower 3D, lower RZ, lower BIG -> we need exact 2-2-1.
    # TOP: SEA 30 > NE 28 -> SEA. TO: SEA 1 < NE 2 (lower better) -> SEA. BIG: SEA 5 < NE 7 -> NE. 3D: SEA 40 < NE 45 -> NE. RZ: SEA 50 = NE 50 -> TIE.
    keys_a = _keys("SEA", 30.0, 1.0, 5, 40.0, 50.0)
    keys_b = _keys("NE", 28.0, 2.0, 7, 45.0, 50.0)
    out = predict(keys_a, keys_b, team_a_name="SEA", team_b_name="NE")
    assert out["keys_won"]["SEA"] == 2
    assert out["keys_won"]["NE"] == 2
    assert out["ties"] == 1
    assert out["keys_won"]["SEA"] + out["keys_won"]["NE"] + out["ties"] == 5
    # No team has >= 3 keys_won, so rule bonus should not force either side
    contrib = out["explanation"].contributions
    assert "rule_3_keys" in contrib
    assert contrib["rule_3_keys"] == 0.0


def test_exactly_one_tie_big():
    """Exactly one key tied (BIG); others all decided."""
    keys_a = _keys("SEA", 28.0, 1.0, 8, 45.0, 60.0)
    keys_b = _keys("NE", 26.0, 2.0, 8, 44.0, 58.0)  # TO 2 so NE loses TO; BIG 8=8 TIE
    out = predict(keys_a, keys_b, team_a_name="SEA", team_b_name="NE")
    assert out["explanation"].key_winners["BIG"] == "TIE"
    assert out["ties"] == 1
    assert out["tied_keys"] == ["BIG"]
    assert out["keys_won"]["SEA"] + out["keys_won"]["NE"] + out["ties"] == 5


def test_compare_5keys_big_tie():
    keys_a = _keys("SEA", 28.0, 1.0, 8, 45.0, 60.0)
    keys_b = _keys("NE", 26.0, 1.0, 8, 44.0, 58.0)
    comps = compare_5keys(keys_a, keys_b, "SEA", "NE")
    assert comps["BIG"].winner == "TIE"
    assert comps["BIG"].margin == 0.0
    assert comps["TOP"].winner == "SEA"
    assert comps["TO"].winner == "TIE"


def test_keys_won_plus_ties_equals_five():
    """keys_won[team_a] + keys_won[team_b] + ties == 5 always."""
    keys_a = _keys("SEA", 28.0, 2.0, 8, 45.0, 60.0)
    keys_b = _keys("NE", 30.0, 1.0, 6, 44.0, 55.0)
    out = predict(keys_a, keys_b, team_a_name="SEA", team_b_name="NE")
    assert out["keys_won"]["SEA"] + out["keys_won"]["NE"] + out["ties"] == 5
