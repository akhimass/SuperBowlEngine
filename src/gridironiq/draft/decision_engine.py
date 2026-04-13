from __future__ import annotations

from typing import Any, Dict, List, Sequence


def recommend_pick(
    team: str,
    pick_number: int,
    available_players: Sequence[Dict[str, Any]],
    availability: Dict[str, float],
    *,
    availability_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    # NOTE: team parameter is stored as metadata only.
    # Need-adjusted ranking is pre-computed in final_draft_score
    # which already incorporates team_need_score. Adding
    # a second team filter here would double-count need.
    # If per-team filtering is needed in future, add a
    # team_filter: Optional[str] parameter distinct from
    # the metadata team field.
    team = str(team).upper()
    w = max(0.0, min(1.0, float(availability_weight)))
    ranked: List[Dict[str, Any]] = []
    for row in available_players:
        pid = str(row.get("player_id", ""))
        final = float(row.get("final_draft_score", 0.0))
        p_avail = float(availability.get(pid, 0.5))
        leverage = final * (1.0 - w * p_avail)
        item = dict(row)
        item["team_context"] = team
        item["pick_number"] = pick_number
        item["availability_at_pick"] = round(p_avail, 4)
        item["leverage_score"] = round(leverage, 3)
        ranked.append(item)
    ranked.sort(key=lambda x: (-x["leverage_score"], -x["final_draft_score"]))
    for i, r in enumerate(ranked, start=1):
        r["recommendation_rank"] = i
    return ranked


def _copy_ranked(pool: List[Dict[str, Any]], key: str, desc: str) -> List[Dict[str, Any]]:
    out = []
    for i, p in enumerate(sorted(pool, key=key, reverse=True), start=1):
        x = dict(p)
        x["mode_rank"] = i
        x["ranking_mode"] = desc
        out.append(x)
    return out


def four_ranking_modes(players: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    1) BPA — pure prospect_score
    2) Best fit — final_draft_score (team need + scheme already embedded)
    3) Upside — athletic + youth (age_adjustment) + prospect
    4) Safest — production + efficiency + market agreement when available
    """
    pool = [dict(p) for p in players]

    bpa = _copy_ranked(pool, lambda p: float(p.get("prospect_score", 0)), "best_player_available")

    fit = _copy_ranked(pool, lambda p: float(p.get("final_draft_score", 0)), "best_fit")

    def upside_key(p: Dict[str, Any]) -> float:
        ath = float(p.get("prospect_score", 0)) * 0.45
        mov = float(p.get("score_breakdown", {}).get("prospect", {}).get("athletic_score", 50)) * 0.35
        youth = float(p.get("score_breakdown", {}).get("prospect", {}).get("age_adjustment", 50)) * 0.20
        return ath + mov + youth

    upside = _copy_ranked(pool, upside_key, "highest_upside")

    def safe_key(p: Dict[str, Any]) -> float:
        pr = p.get("score_breakdown", {}).get("prospect", {})
        base = float(pr.get("production_score", 50)) * 0.45 + float(pr.get("efficiency_score", 50)) * 0.35
        mvs = p.get("market_value_score")
        rr = p.get("reach_risk")
        if mvs is not None:
            base += float(mvs) * 0.15
        if rr is not None:
            base -= min(20.0, abs(float(rr))) * 0.15
        return base

    safest = _copy_ranked(pool, safe_key, "safest_pick")

    return {
        "best_player_available": bpa[:50],
        "best_fit": fit[:50],
        "highest_upside": upside[:50],
        "safest_pick": safest[:50],
    }
