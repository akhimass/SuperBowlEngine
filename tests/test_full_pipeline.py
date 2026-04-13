"""End-to-end integration tests using real nflreadpy data.

These tests exercise the matchup engine, report generator, and backtest engine
against live nflverse PBP/schedules. They are marked as slow because they
invoke nflreadpy/network and do non-trivial computation.
"""

import pytest

from gridironiq.matchup_engine import run_matchup
from gridironiq.report_generator import generate_report
from gridironiq.backtest_engine import run_backtest


@pytest.mark.slow
def test_full_pipeline_matchup_and_report():
    season = 2024
    team_a = "GB"
    team_b = "DET"

    result = run_matchup(season, team_a, team_b)

    assert 0.0 <= result.win_probability <= 1.0
    assert isinstance(result.projected_score, dict) and result.projected_score
    assert result.predicted_winner in {team_a, team_b}
    assert result.keys_won

    report = generate_report(result)
    assert report.get("summary")
    assert isinstance(report.get("team_a_strengths"), list)
    assert isinstance(report.get("team_b_strengths"), list)
    assert report.get("prediction_explanation")


@pytest.mark.slow
def test_full_pipeline_backtest():
    season = 2024
    back = run_backtest(season=season)

    assert 0.0 <= back.accuracy <= 1.0
    assert back.calibration_data
