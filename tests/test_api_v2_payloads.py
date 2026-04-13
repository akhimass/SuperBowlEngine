import pytest
from fastapi.testclient import TestClient

from gridironiq.api import app


@pytest.mark.slow
def test_api_matchup_run_includes_v2_fields() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/matchup/run",
        json={"season": 2024, "team_a": "GB", "team_b": "DET", "mode": "regular"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "projected_margin" in data
    assert "projected_total" in data
    assert "team_efficiency_edges" in data
    assert isinstance(data["team_efficiency_edges"], dict)


@pytest.mark.slow
def test_api_matchup_report_includes_v2_fields() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/matchup/report",
        json={"season": 2024, "team_a": "GB", "team_b": "DET", "mode": "regular"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "projected_margin" in data
    assert "projected_total" in data
    assert "team_efficiency_edges" in data
    assert isinstance(data["team_efficiency_edges"], dict)

