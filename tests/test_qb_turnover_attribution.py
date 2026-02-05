"""
Tests for QB turnover attribution: QB-fault vs non-QB-fault INT and fumble heuristics.
"""

import pandas as pd
import pytest

from superbowlengine.qb.production import qb_turnover_attribution


def _pbp(rows: list) -> pd.DataFrame:
    """Build minimal PBP from list of dicts; fill missing columns with 0/empty."""
    df = pd.DataFrame(rows)
    defaults = {
        "interception": 0, "fumble_lost": 0, "tipped_pass": 0, "shotgun": 1, "screen": 0, "qb_sack_fumble": 0,
        "air_yards": 0.0, "pass_depth": "", "passer_player_name": "", "rusher_player_name": "",
        "posteam": "", "play_type": "",
    }
    for c, default in defaults.items():
        if c not in df.columns:
            df[c] = default
    return df


def test_deep_int_counted_as_qb_fault() -> None:
    """Deep INT (air_yards >= 8 or pass_depth deep/intermediate) is QB-fault."""
    pbp = _pbp([
        {"posteam": "NE", "interception": 1, "fumble_lost": 0, "play_type": "pass", "passer_player_name": "D.Maye", "rusher_player_name": "", "air_yards": 18, "pass_depth": "deep"},
    ])
    out = qb_turnover_attribution(pbp, "D.Maye", "NE")
    assert out["qb_fault_int"] == 1.0
    assert out["non_qb_fault_int"] == 0.0


def test_short_int_counted_as_discounted() -> None:
    """Short INT (air_yards < 8 or pass_depth short) is non-QB-fault (discounted)."""
    pbp = _pbp([
        {"posteam": "NE", "interception": 1, "fumble_lost": 0, "play_type": "pass", "passer_player_name": "D.Maye", "rusher_player_name": "", "air_yards": 3, "pass_depth": "short"},
    ])
    out = qb_turnover_attribution(pbp, "D.Maye", "NE")
    assert out["qb_fault_int"] == 0.0
    assert out["non_qb_fault_int"] == 1.0


def test_sack_fumble_counted_as_qb_fault() -> None:
    """Sack fumble (qb_sack_fumble==1 or play_type==sack and fumble_lost) is QB-fault."""
    pbp = _pbp([
        {"posteam": "NE", "interception": 0, "fumble_lost": 1, "play_type": "sack", "passer_player_name": "D.Maye", "rusher_player_name": "", "qb_sack_fumble": 1},
    ])
    out = qb_turnover_attribution(pbp, "D.Maye", "NE")
    assert out["qb_fault_fum"] == 1.0
    assert out["non_qb_fault_fum"] == 0.0


def test_non_qb_fumble_discounted() -> None:
    """Fumble lost not on sack (e.g. receiver fumble) is non-QB-fault."""
    pbp = _pbp([
        {"posteam": "NE", "interception": 0, "fumble_lost": 1, "play_type": "pass", "passer_player_name": "D.Maye", "rusher_player_name": "", "qb_sack_fumble": 0},
    ])
    out = qb_turnover_attribution(pbp, "D.Maye", "NE")
    assert out["qb_fault_fum"] == 0.0
    assert out["non_qb_fault_fum"] == 1.0


def test_weighted_turnovers_combine_weights() -> None:
    """weighted_turnovers = qb_fault_to + non_qb_fault_to with config weights."""
    pbp = _pbp([
        {"posteam": "NE", "interception": 1, "fumble_lost": 0, "play_type": "pass", "passer_player_name": "D.Maye", "rusher_player_name": "", "air_yards": 20, "pass_depth": "deep"},
        {"posteam": "NE", "interception": 1, "fumble_lost": 0, "play_type": "pass", "passer_player_name": "D.Maye", "rusher_player_name": "", "air_yards": 2, "pass_depth": "short"},
    ])
    out = qb_turnover_attribution(pbp, "D.Maye", "NE")
    assert out["qb_fault_int"] == 1.0
    assert out["non_qb_fault_int"] == 1.0
    assert out["weighted_turnovers"] == pytest.approx(1.0 * 1.0 + 1.0 * 0.35, abs=0.01)


def test_empty_team_returns_zeros() -> None:
    """When team has no plays, attribution is all zeros."""
    pbp = _pbp([{"posteam": "SEA", "interception": 0, "fumble_lost": 0, "play_type": "run"}])
    out = qb_turnover_attribution(pbp, "Maye", "NE")
    assert out["qb_fault_int"] == 0.0 and out["non_qb_fault_int"] == 0.0
    assert out["qb_fault_fum"] == 0.0 and out["non_qb_fault_fum"] == 0.0
    assert out["weighted_turnovers"] == 0.0
