"""Tests for SOS (strength of schedule) module."""

import pandas as pd
import pytest

from superbowlengine.features.sos import (
    build_game_results,
    compute_sos,
    compute_team_sos,
    compute_team_win_pct,
    zscore_sos,
)


def test_build_game_results_max_scores() -> None:
    """Final scores are max home_score/away_score per game_id."""
    pbp = pd.DataFrame([
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score": 0, "away_score": 0},
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score": 7, "away_score": 0},
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score": 7, "away_score": 7},
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score": 14, "away_score": 7},
        {"game_id": "g2", "home_team": "B", "away_team": "C", "home_score": 10, "away_score": 3},
    ])
    out = build_game_results(pbp)
    assert len(out) == 2
    row1 = out[out["game_id"] == "g1"].iloc[0]
    assert row1["home_score_final"] == 14 and row1["away_score_final"] == 7
    row2 = out[out["game_id"] == "g2"].iloc[0]
    assert row2["home_score_final"] == 10 and row2["away_score_final"] == 3


def test_build_game_results_season_type_filter() -> None:
    """Optional season_type filters to REG/POST."""
    pbp = pd.DataFrame([
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score": 21, "away_score": 7, "season_type": "REG"},
        {"game_id": "g2", "home_team": "A", "away_team": "B", "home_score": 28, "away_score": 24, "season_type": "POST"},
    ])
    reg = build_game_results(pbp, season_type="REG")
    assert len(reg) == 1
    assert reg.iloc[0]["game_id"] == "g1"
    post = build_game_results(pbp, season_type="POST")
    assert len(post) == 1
    assert post.iloc[0]["game_id"] == "g2"


def test_compute_team_win_pct() -> None:
    """Win % from fabricated schedule: A 2-0, B 1-1, C 0-2."""
    gr = pd.DataFrame([
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score_final": 24, "away_score_final": 10},
        {"game_id": "g2", "home_team": "A", "away_team": "C", "home_score_final": 20, "away_score_final": 17},
        {"game_id": "g3", "home_team": "B", "away_team": "C", "home_score_final": 14, "away_score_final": 7},
    ])
    wp = compute_team_win_pct(gr)
    assert wp["A"] == 1.0
    assert wp["B"] == 0.5
    assert wp["C"] == 0.0


def test_compute_sos_fabricated() -> None:
    """SOS = average opponent win%. A plays B (1.0) and C (0.0) -> A's SOS = 0.5."""
    gr = pd.DataFrame([
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score_final": 21, "away_score_final": 7},
        {"game_id": "g2", "home_team": "C", "away_team": "A", "home_score_final": 3, "away_score_final": 17},
        {"game_id": "g3", "home_team": "B", "away_team": "C", "home_score_final": 28, "away_score_final": 0},
    ])
    # B is 1-0 (1.0), C is 0-1 (0.0). A played B and C -> SOS = (1.0 + 0.0) / 2 = 0.5
    assert compute_sos(gr, "A") == 0.5
    # B played A (0.5 from 1-1) and C (0.0) -> A's win% = 0.5, C's = 0.0 -> B's SOS = (0.5 + 0.0) / 2 = 0.25
    assert compute_sos(gr, "B") == 0.25
    # C played A (0.5) and B (1.0) -> SOS = (0.5 + 1.0) / 2 = 0.75
    assert compute_sos(gr, "C") == 0.75


def test_compute_sos_no_games() -> None:
    gr = pd.DataFrame([
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score_final": 10, "away_score_final": 7},
    ])
    assert compute_sos(gr, "Z") == 0.0


def test_zscore_sos() -> None:
    """Z-scores have mean 0 and std 1."""
    all_sos = {"A": 0.5, "B": 0.4, "C": 0.6, "D": 0.5}
    z = zscore_sos(all_sos)
    vals = list(z.values())
    mean = sum(vals) / len(vals)
    variance = sum((x - mean) ** 2 for x in vals) / (len(vals) - 1)
    std = variance ** 0.5
    assert abs(mean) < 1e-10
    assert abs(std - 1.0) < 1e-10


def test_zscore_sos_single_team() -> None:
    assert zscore_sos({"A": 0.6}) == {"A": 0.0}
    assert zscore_sos({}) == {}


def test_zscore_sos_two_teams() -> None:
    z = zscore_sos({"A": 0.0, "B": 1.0})
    assert z["A"] == -1.0
    assert z["B"] == 1.0


def test_compute_team_sos_backward_compat() -> None:
    """compute_team_sos works with home_score/away_score column names."""
    gr = pd.DataFrame([
        {"game_id": "g1", "home_team": "A", "away_team": "B", "home_score": 21, "away_score": 7},
        {"game_id": "g2", "home_team": "B", "away_team": "A", "home_score": 10, "away_score": 14},
    ])
    # A 1-1, B 1-1. A's only opponent is B with 0.5 -> SOS 0.5
    assert compute_team_sos(gr, "A") == 0.5
    assert compute_team_sos(gr, "B") == 0.5


def test_sos_no_external_api() -> None:
    """SOS is computed entirely from the passed DataFrame (no network)."""
    gr = pd.DataFrame([
        {"game_id": "g1", "home_team": "SEA", "away_team": "NE", "home_score_final": 24, "away_score_final": 21},
    ])
    wp = compute_team_win_pct(gr)
    assert wp["SEA"] == 1.0 and wp["NE"] == 0.0
    assert compute_sos(gr, "SEA") == 0.0  # only opponent NE has 0%
    assert compute_sos(gr, "NE") == 1.0   # only opponent SEA has 100%
