from __future__ import annotations

import pytest

from gridironiq.draft.room_production import compute_position_share_trend
from gridironiq.draft.scheme_fit import compute_scheme_fit, infer_te_archetype, te_share_fit_score
from gridironiq.draft.team_context import TeamContext, build_team_context, team_context_summary
from gridironiq.draft.team_needs import NEED_BUCKETS, compute_team_needs


@pytest.mark.parametrize("team", ["KC", "BAL", "DET"])
def test_need_signal_policy_no_manual_priors(team: str) -> None:
    n = compute_team_needs(team, 2024)
    assert n["need_signal_policy"]["manual_need_priors"] is False
    assert set(n["need_scores"].keys()) == set(NEED_BUCKETS)
    assert all(0.0 <= v <= 100.0 for v in n["need_scores"].values())


@pytest.mark.parametrize("team", ["KC", "BAL", "GB"])
def test_build_team_context_smoke(team: str) -> None:
    ctx = build_team_context(team, 2024)
    assert isinstance(ctx, TeamContext)
    assert ctx.need_signal_policy["manual_need_priors"] is False
    assert len(ctx.needs) == len(NEED_BUCKETS)
    r = repr(ctx)
    assert ctx.team in r and str(ctx.season) in r
    summ = team_context_summary(ctx)
    assert summ["team"] == ctx.team
    assert "top_needs" in summ


def test_compute_position_share_trend_returns_float() -> None:
    s = compute_position_share_trend("KC", "TE", [2023, 2024, 2025])
    assert isinstance(s, float)
    assert s == 0.0 or s == s


def test_compute_position_share_trend_zero_with_one_season() -> None:
    assert compute_position_share_trend("KC", "TE", [2024]) == 0.0


def test_some_team_positive_te_target_trend() -> None:
    """At least one NFL team increased TE target share over 2022–2024 (nflverse)."""
    from gridironiq.draft.loaders import load_player_stats_reg

    teams = sorted(load_player_stats_reg(2024)["team"].dropna().astype(str).unique())
    seasons = [2022, 2023, 2024]
    found = any(compute_position_share_trend(t, "TE", seasons) > 0.0 for t in teams)
    assert found


def test_infer_te_archetype_physical_thresholds() -> None:
    assert infer_te_archetype({"pos_bucket": "TE", "forty": 4.39, "weight_lb": 241}) == "receiving_weapon"
    assert infer_te_archetype({"pos_bucket": "TE", "forty": 4.72, "weight_lb": 258}) == "inline_blocker"
    assert infer_te_archetype({"pos_bucket": "TE", "forty": 4.58, "weight_lb": 248}) == "move_te_hybrid"


def test_te_share_fit_high_volume_vs_low() -> None:
    high = {"te_target_share": 0.20, "te_air_yards_share": 0.18, "wr_target_share_of_skill": 0.45}
    low = {"te_target_share": 0.09, "te_air_yards_share": 0.10, "wr_target_share_of_skill": 0.55}
    assert te_share_fit_score(high, "receiving_weapon") > te_share_fit_score(low, "receiving_weapon")
    assert te_share_fit_score(low, "inline_blocker") > te_share_fit_score(high, "inline_blocker")


def test_scheme_fit_te_receiving_vs_team_volume() -> None:
    base_vec = [0.55, 0.62, 0.02, 0.0, 0.52, 0.0, 0.0]
    high_te = base_vec + [0.20, 0.18, 0.48]
    low_te = base_vec + [0.09, 0.10, 0.58]
    player = {
        "pos_bucket": "TE",
        "pos": "TE",
        "forty": 4.42,
        "weight_lb": 242,
        "height_in": 76.0,
    }
    hi_prof = {
        "vector": high_te,
        "raw": {
            "off_pass_rate": 0.58,
            "te_target_share": 0.20,
            "te_air_yards_share": 0.18,
            "wr_target_share_of_skill": 0.48,
            "wr_air_yards_share": 0.52,
        },
        "team": "SYN",
        "season": 2024,
        "labels": [],
    }
    lo_prof = {
        "vector": low_te,
        "raw": {
            "off_pass_rate": 0.52,
            "te_target_share": 0.09,
            "te_air_yards_share": 0.10,
            "wr_target_share_of_skill": 0.58,
            "wr_air_yards_share": 0.48,
        },
        "team": "SYN",
        "season": 2024,
        "labels": [],
    }
    hi = compute_scheme_fit(player, hi_prof)
    lo = compute_scheme_fit(player, lo_prof)
    assert hi["scheme_fit_score"] > lo["scheme_fit_score"]
    assert lo["scheme_fit_score"] < 55.0
