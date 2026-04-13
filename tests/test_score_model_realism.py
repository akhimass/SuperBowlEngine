from __future__ import annotations

from superbowlengine.models.score_model import ScoreModelArtifacts, predict_score
from superbowlengine.models.professor_keys import TeamContext
from superbowlengine.features.keys import TeamKeys


def test_score_never_negative_and_within_bounds() -> None:
    keys_a = TeamKeys(
        team="A",
        top_min=32.0,
        turnovers=1.0,
        big_plays=6.0,
        third_down_pct=45.0,
        redzone_td_pct=65.0,
    )
    keys_b = TeamKeys(
        team="B",
        top_min=28.0,
        turnovers=2.0,
        big_plays=3.0,
        third_down_pct=38.0,
        redzone_td_pct=52.0,
    )
    artifacts = ScoreModelArtifacts(
        margin_coef={"margin_top": 0.5, "margin_to": -0.3, "margin_big": 0.4, "margin_3d": 0.2, "margin_rz": 0.1, "sos_z": 0.0},
        margin_intercept=0.0,
        margin_std=7.0,
        total_coef={"margin_top": 0.2, "margin_to": 0.1, "margin_big": 0.1, "margin_3d": 0.1, "margin_rz": 0.1, "sos_z": 0.0},
        total_intercept=45.0,
        total_std=7.0,
        n_samples=100,
    )
    out = predict_score(keys_a, keys_b, context_a=TeamContext(), context_b=TeamContext(), artifacts=artifacts, team_a_name="A", team_b_name="B")
    a_score = out["predicted_score"]["A"]
    b_score = out["predicted_score"]["B"]
    total = out["predicted_total"]
    margin = out["predicted_margin"]
    assert a_score >= 0 and b_score >= 0
    assert 24.0 <= total <= 62.0
    assert -24.0 <= margin <= 24.0

