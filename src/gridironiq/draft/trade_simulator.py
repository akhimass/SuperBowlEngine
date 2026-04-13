from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from .simulator import simulate_draft


def expected_best_available_value(
    availability: Dict[str, float],
    prospects_by_id: Dict[str, Dict[str, Any]],
    *,
    value_key: str = "final_draft_score",
) -> float:
    """E[value] of selecting optimally from remaining pool given independence approx."""
    exp = 0.0
    for pid, p_avail in availability.items():
        p = prospects_by_id.get(pid)
        if not p:
            continue
        v = float(p.get(value_key, 0.0))
        exp += p_avail * v
    return exp


def analyze_trade_down(
    *,
    current_pick: int,
    target_pick: int,
    board_order: Sequence[str],
    prospects: List[Dict[str, Any]],
    target_player_ids: Optional[Sequence[str]] = None,
    n_simulations: int = 800,
    temperature: float = 2.0,
    top_k: int = 24,
    rng: Optional[np.random.Generator] = None,
) -> Dict[str, Any]:
    """
    Compare pick `current_pick` vs trading to `target_pick` (must be > current_pick).
    Uses same stochastic pick model as main simulator.
    """
    if target_pick <= current_pick:
        raise ValueError("target_pick must be greater than current_pick")
    order = [str(i) for i in range(1, int(target_pick) + 16)]
    board = [str(x) for x in board_order]
    rng = rng or np.random.default_rng()

    sim_cur = simulate_draft(
        order,
        board,
        int(current_pick),
        n_simulations=n_simulations,
        temperature=temperature,
        top_k=top_k,
        rng=rng,
    )
    sim_tgt = simulate_draft(
        order,
        board,
        int(target_pick),
        n_simulations=n_simulations,
        temperature=temperature,
        top_k=top_k,
        rng=np.random.default_rng(int(rng.integers(0, 2**31))),
    )

    by_id = {str(p["player_id"]): p for p in prospects}
    ev_cur = expected_best_available_value(sim_cur["availability"], by_id)
    ev_tgt = expected_best_available_value(sim_tgt["availability"], by_id)

    tgt_ids = [str(x) for x in target_player_ids] if target_player_ids else []
    target_probs = {pid: sim_tgt["availability"].get(pid) for pid in tgt_ids}

    return {
        "current_pick": int(current_pick),
        "target_pick": int(target_pick),
        "slots_gained": int(target_pick - current_pick),
        "expected_value_proxy_at_current": round(ev_cur, 3),
        "expected_value_proxy_at_target": round(ev_tgt, 3),
        "expected_value_delta": round(ev_tgt - ev_cur, 3),
        "target_availability_at_new_pick": target_probs,
        "note": "EV proxy assumes independent availability; use for relative trade-down screening only.",
        "simulation": {"current": sim_cur, "target": sim_tgt},
    }


def best_trade_down_ranges(
    *,
    current_pick: int,
    board_order: Sequence[str],
    prospects: List[Dict[str, Any]],
    max_target: int,
    target_player_ids: Optional[Sequence[str]] = None,
    n_simulations: int = 500,
) -> List[Dict[str, Any]]:
    """Scan target picks in (current_pick, max_target] for positive EV delta."""
    rows: List[Dict[str, Any]] = []
    for t in range(current_pick + 1, min(max_target + 1, current_pick + 40)):
        try:
            out = analyze_trade_down(
                current_pick=current_pick,
                target_pick=t,
                board_order=board_order,
                prospects=prospects,
                target_player_ids=target_player_ids,
                n_simulations=n_simulations,
            )
        except Exception:
            continue
        rows.append(
            {
                "target_pick": t,
                "ev_delta": out["expected_value_delta"],
                "targets_at_new_slot": out["target_availability_at_new_pick"],
            }
        )
    rows.sort(key=lambda r: -r["ev_delta"])
    return rows[:12]
