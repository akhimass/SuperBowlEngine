import json
from pathlib import Path

from gridironiq.models.win_prob_model import load_artifacts as load_win
from gridironiq.models.margin_model import load_artifacts as load_margin
from gridironiq.models.total_model import load_artifacts as load_total


def test_model_artifacts_load_from_custom_dir(tmp_path: Path, monkeypatch) -> None:
    d = tmp_path / "model_artifacts"
    d.mkdir(parents=True, exist_ok=True)

    (d / "win_prob_model.json").write_text(json.dumps({"intercept": 0.1, "coef": {"epa_edge": 1.0}}))
    (d / "margin_model.json").write_text(json.dumps({"intercept": 1.0, "coef": {"epa_edge": 10.0}}))
    (d / "total_model.json").write_text(json.dumps({"intercept": 45.0, "coef": {"success_edge": 2.0}}))

    monkeypatch.setenv("GRIDIRONIQ_MODEL_ARTIFACT_DIR", str(d))

    w = load_win()
    m = load_margin()
    t = load_total()

    assert w is not None and w.intercept == 0.1 and w.coef["epa_edge"] == 1.0
    assert m is not None and m.intercept == 1.0 and m.coef["epa_edge"] == 10.0
    assert t is not None and t.intercept == 45.0 and t.coef["success_edge"] == 2.0

