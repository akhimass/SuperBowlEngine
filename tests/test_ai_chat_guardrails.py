import pytest
from fastapi.testclient import TestClient

from gridironiq.api import app


@pytest.mark.slow
def test_ai_chat_refuses_out_of_scope() -> None:
    client = TestClient(app)
    res = client.post(
        "/api/ai/chat",
        json={
            "question": "Who won the Super Bowl in 1998?",
            "context_type": "matchup",
            "season": 2024,
            "team_a": "GB",
            "team_b": "DET",
            "mode": "regular",
            "ai_mode": "template",
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "answer" in data
    assert "I can only answer" in data["answer"]

