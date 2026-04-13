"""Tests for gridironiq.reports.matchup_report (full report builder)."""

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from gridironiq.reports.matchup_report import build_matchup_report, REPORT_PBP_EXTRA_COLUMNS


def test_report_pbp_extra_columns_defined():
    assert "success" in REPORT_PBP_EXTRA_COLUMNS
    assert "epa" in REPORT_PBP_EXTRA_COLUMNS
    assert "pass_attempt" in REPORT_PBP_EXTRA_COLUMNS
    assert "rush_attempt" in REPORT_PBP_EXTRA_COLUMNS


@patch("gridironiq.reports.matchup_report.run_matchup")
@patch("gridironiq.reports.matchup_report.get_pbp_for_reports")
def test_build_matchup_report_returns_required_fields(mock_get_pbp, mock_run_matchup):
    from gridironiq.matchup_engine import MatchupResult

    mock_run_matchup.return_value = MatchupResult(
        team_a="GB",
        team_b="DET",
        season=2024,
        mode="opp_weighted",
        win_probability=0.55,
        predicted_winner="GB",
        projected_score={"GB": 24, "DET": 21},
        keys_won={"GB": 3, "DET": 2},
        key_edges={"TOP": 0.2, "BIG": -0.1},
        top_drivers=(("TOP", 0.2), ("BIG", -0.1)),
        explanation={"key_winners": {}},
    )
    mock_get_pbp.return_value = pd.DataFrame()  # empty -> no situational data

    out = build_matchup_report(2024, "GB", "DET", generate_heatmaps=False)

    assert "summary" in out
    assert "team_a_profile" in out
    assert "team_b_profile" in out
    assert "situational_edges" in out
    assert "key_matchup_edges" in out
    assert "offense_vs_defense" in out
    assert "report_assets" in out
    assert out["team_a"] == "GB"
    assert out["team_b"] == "DET"
    assert out["season"] == 2024
    assert out["predicted_winner"] == "GB"
    assert isinstance(out["report_assets"], list)
