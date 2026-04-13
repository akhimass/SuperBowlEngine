from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_draft_intelligence_report(
    board: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
    *,
    four_modes: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    trade_summary: Optional[Dict[str, Any]] = None,
    simulation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Structured front-office style snapshot (all fields grounded on passed objects).
    """
    team = board.get("team", "")
    pick = (simulation or {}).get("pick_number")
    top = recommendations[0] if recommendations else None
    alts = recommendations[1:5] if len(recommendations) > 1 else []

    risk_lines: List[str] = []
    if top:
        src = (top.get("score_breakdown") or {}).get("prospect", {}).get("production_source")
        if src:
            risk_lines.append(f"Grade anchor: {src}.")
        rr = top.get("reach_risk")
        if rr is not None:
            risk_lines.append(
                f"Reach vs market (model_rank - consensus_rank): {rr}. "
                "Positive implies model lower than external boards."
            )
        pa = top.get("availability_at_pick")
        if pa is not None:
            risk_lines.append(f"Simulated availability at pick {pick}: {round(float(pa) * 100, 1)}%.")

    pass_alts = [f"{a.get('player_name')} ({a.get('pos')})" for a in alts if a.get("player_name")]

    trade_line = None
    if trade_summary and isinstance(trade_summary, dict):
        trade_line = (
            f"Trade-down EV delta (proxy): {trade_summary.get('expected_value_delta')} "
            f"when sliding from pick {trade_summary.get('current_pick')} "
            f"to {trade_summary.get('target_pick')}."
        )

    return {
        "team": team,
        "pick_number": pick,
        "top_recommendation": top,
        "alternatives": alts,
        "risk_profile": risk_lines,
        "availability_note": (
            f"Based on {simulation.get('n_simulations')} simulations "
            f"(temp={simulation.get('temperature')})."
            if simulation
            else None
        ),
        "if_we_pass": (
            f"If {team} passes, next tier on levered board: {', '.join(pass_alts) or 'n/a'}."
        ),
        "trade_down_recommendation": trade_line,
        "four_ranking_modes": four_modes,
        "market_consensus_meta": board.get("meta", {}).get("consensus"),
    }
