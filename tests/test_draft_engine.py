from __future__ import annotations

import numpy as np

from gridironiq.draft.decision_engine import recommend_pick
from gridironiq.draft.draft_board import final_draft_score
from gridironiq.draft.simulator import simulate_draft


def test_final_draft_score_in_range() -> None:
    out = final_draft_score(80.0, 70.0, 75.0, "WR", ["WR", "WR", "CB", "QB"])
    assert 0 <= out["final_draft_score"] <= 100


def test_simulate_returns_probabilities() -> None:
    board = [f"p{i}" for i in range(40)]
    rng = np.random.default_rng(42)
    sim = simulate_draft(
        list(range(1, 35)),
        board,
        pick_number=10,
        n_simulations=200,
        temperature=2.0,
        rng=rng,
    )
    avail = sim["availability"]
    for pid, p in avail.items():
        assert 0.0 <= p <= 1.0
        assert pid in board


def test_recommend_pick_orders_by_leverage() -> None:
    players = [
        {"player_id": "a", "final_draft_score": 90.0, "player_name": "A", "pos": "QB"},
        {"player_id": "b", "final_draft_score": 85.0, "player_name": "B", "pos": "WR"},
    ]
    avail = {"a": 0.9, "b": 0.2}
    ranked = recommend_pick("KC", 19, players, avail, availability_weight=0.4)
    assert ranked[0]["player_id"] == "b"
