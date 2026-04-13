"""Tests for gridironiq.reports.heatmaps (metadata and path generation)."""

import pandas as pd
import pytest

from gridironiq.reports import heatmaps, report_assets, situational


@pytest.fixture
def tendency_df():
    """Minimal tendency DataFrame for heatmap (run_pct by situation)."""
    return pd.DataFrame([
        {"dist_bucket": "1st & 10+", "field_pos_bucket": "In the Field (Own 10-Opp 21)", "run_pct": 0.45, "pass_pct": 0.55, "run_success": 0.42, "pass_success": 0.52},
        {"dist_bucket": "2nd Long", "field_pos_bucket": "In the Field (Own 10-Opp 21)", "run_pct": 0.35, "pass_pct": 0.65, "run_success": 0.38, "pass_success": 0.48},
    ])


def test_run_pass_heatmap_returns_metadata(tendency_df):
    meta = heatmaps.render_run_pass_heatmap(tendency_df, "GB", 2024, kind="run")
    assert "path" in meta
    assert "caption" in meta
    assert meta.get("team") == "GB"
    assert meta.get("season") == 2024
    assert meta.get("kind") == "run"


def test_success_rate_heatmap_returns_metadata():
    succ = pd.DataFrame([
        {"dist_bucket": "1st & 10+", "field_pos_bucket": "In the Field (Own 10-Opp 21)", "n_plays": 100, "success_rate": 0.48},
    ])
    meta = heatmaps.render_success_rate_heatmap(succ, "GB", 2024)
    assert "path" in meta
    assert "caption" in meta


def test_report_assets_paths():
    p = report_assets.run_pass_heatmap_path("GB", 2024, "run")
    assert "GB" in str(p)
    assert "2024" in str(p)
    assert "run" in str(p)
    p2 = report_assets.success_rank_heatmap_path("DET", 2024)
    assert "DET" in str(p2)
    assert "success" in str(p2)
    p3 = report_assets.matchup_heatmap_path("GB", "DET", 2024, week=14)
    assert "GB" in str(p3)
    assert "DET" in str(p3)
    assert "14" in str(p3)
