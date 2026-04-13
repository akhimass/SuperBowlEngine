from __future__ import annotations

from typing import Any, Dict, Sequence

import numpy as np


def simulate_draft(
    order: Sequence[str],
    board_player_ids: Sequence[str],
    pick_number: int,
    *,
    n_simulations: int = 1000,
    temperature: float = 2.0,
    top_k: int = 24,
    rng: np.random.Generator | None = None,
) -> Dict[str, Any]:
    """
    Monte Carlo: before `pick_number`, each slot stochastically removes a player from the pool.
    `order` length should be >= pick_number (teams or pick owners — only length matters).
    `board_player_ids` is consensus preference order (best first).

    Returns availability rates for every player id.
    """
    if pick_number < 1:
        raise ValueError("pick_number must be >= 1")
    if len(order) < pick_number:
        raise ValueError("order length must be >= pick_number")
    n_sim = int(n_simulations)
    if n_sim < 1:
        raise ValueError("n_simulations must be >= 1")

    rng = rng or np.random.default_rng()
    board = [str(x) for x in board_player_ids]
    if not board:
        return {"pick_number": pick_number, "n_simulations": n_sim, "availability": {}}

    avail_counts: Dict[str, int] = {pid: 0 for pid in board}

    picks_before = pick_number - 1
    temp = max(0.25, float(temperature))
    k = min(top_k, len(board))

    for _ in range(n_sim):
        pool = list(board)
        for _slot in range(picks_before):
            if not pool:
                break
            head = pool[:k]
            ranks = np.arange(len(head), dtype=float)
            logits = -ranks / temp
            logits = logits - np.max(logits)
            w = np.exp(logits)
            w = w / w.sum()
            j = int(rng.choice(len(head), p=w))
            taken = head[j]
            pool.remove(taken)
        for pid in board:
            if pid in pool:
                avail_counts[pid] += 1

    availability = {pid: round(avail_counts[pid] / n_sim, 4) for pid in board}
    return {
        "pick_number": pick_number,
        "n_simulations": n_sim,
        "temperature": temp,
        "top_k": k,
        "availability": availability,
    }
