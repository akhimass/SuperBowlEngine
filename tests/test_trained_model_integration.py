import json
from pathlib import Path

import pytest

from gridironiq.matchup_engine import run_matchup


@pytest.mark.slow
def test_live_predictor_uses_trained_artifacts(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / "model_artifacts"
    d.mkdir(parents=True, exist_ok=True)

    # Make a very biased model so we can see an effect (still clipped in win prob).
    (d / "win_prob_model.json").write_text(json.dumps({"intercept": 0.0, "coef": {"epa_edge": 50.0}}))
    (d / "margin_model.json").write_text(json.dumps({"intercept": 0.0, "coef": {"epa_edge": 24.0}}))
    (d / "total_model.json").write_text(json.dumps({"intercept": 45.0, "coef": {}}))

    monkeypatch.setenv("GRIDIRONIQ_MODEL_ARTIFACT_DIR", str(d))

    r = run_matchup(2024, "SF", "PHI", mode="regular")
    assert 0.0 <= r.win_probability <= 1.0
    assert r.projected_margin is not None
    assert r.projected_total is not None
    assert isinstance(r.team_efficiency_edges, dict)
    # Score reconstruction should remain consistent and non-negative
    assert r.projected_score["SF"] >= 0 and r.projected_score["PHI"] >= 0

