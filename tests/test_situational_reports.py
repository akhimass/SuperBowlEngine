"""Tests for gridironiq.reports.situational (bucketing and tendency logic)."""

import pandas as pd
import pytest

from gridironiq.reports import situational


@pytest.fixture
def minimal_pbp():
    """Minimal PBP with required columns for bucketing."""
    return pd.DataFrame({
        "down": [1, 1, 2, 2, 3, 3],
        "ydstogo": [10, 5, 8, 2, 7, 1],
        "yardline_100": [75, 15, 90, 50, 5, 2],
        "posteam": ["GB", "GB", "GB", "DET", "DET", "DET"],
        "defteam": ["DET", "DET", "DET", "GB", "GB", "GB"],
        "pass_attempt": [1, 0, 1, 0, 1, 0],
        "rush_attempt": [0, 1, 0, 1, 0, 1],
        "qb_scramble": [0, 0, 0, 0, 0, 0],
        "success": [1, 0, 1, 1, 0, 1],
        "epa": [0.5, -0.2, 0.8, 0.1, -0.5, 0.3],
    })


def test_build_situational_buckets(minimal_pbp):
    out = situational.build_situational_buckets(minimal_pbp)
    assert "dist_bucket" in out.columns
    assert "field_pos_bucket" in out.columns
    assert "play_category" in out.columns
    assert out["dist_bucket"].notna().all()
    assert (out["dist_bucket"] != "Other").all()
    assert (out["field_pos_bucket"] != "Other").all()


def test_dist_bucket_values():
    assert situational._dist_bucket(1, 10) == "1st & 10+"
    assert situational._dist_bucket(1, 5) == "1st & <10"
    assert situational._dist_bucket(2, 8) == "2nd Long"
    assert situational._dist_bucket(3, 4) == "3rd Medium"
    assert situational._dist_bucket(4, 1) == "4th Short"


def test_field_pos_bucket():
    assert situational._field_pos_bucket(95) == "Backed Up (Own 1-9)"
    assert situational._field_pos_bucket(50) == "In the Field (Own 10-Opp 21)"
    assert situational._field_pos_bucket(15) == "Upper Red Zone (Opp 20-11)"
    assert situational._field_pos_bucket(5) == "Lower Red Zone (Opp 10-3)"
    assert situational._field_pos_bucket(1) == "Goal Line (Opp 2-1)"


def test_run_pass_tendency_by_situation(minimal_pbp):
    bucketed = situational.build_situational_buckets(minimal_pbp)
    tend = situational.run_pass_tendency_by_situation(bucketed, "GB")
    assert "dist_bucket" in tend.columns
    assert "field_pos_bucket" in tend.columns
    assert "n_plays" in tend.columns
    assert "run_pct" in tend.columns
    assert "pass_pct" in tend.columns


def test_success_rate_by_situation(minimal_pbp):
    bucketed = situational.build_situational_buckets(minimal_pbp)
    succ = situational.success_rate_by_situation(bucketed, "GB")
    assert "success_rate" in succ.columns or succ.empty


def test_offense_vs_defense_situational(minimal_pbp):
    bucketed = situational.build_situational_buckets(minimal_pbp)
    out = situational.offense_vs_defense_situational(
        bucketed[bucketed["posteam"] == "GB"],
        bucketed[bucketed["defteam"] == "DET"],
        "GB",
        "DET",
    )
    assert out["offense_team"] == "GB"
    assert out["defense_team"] == "DET"
    assert "offense_tendency" in out
    assert "defense_tendency_allowed" in out
    assert "situations" in out
