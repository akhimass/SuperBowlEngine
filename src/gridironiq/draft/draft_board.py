from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .positions import POSITIONAL_VALUE


def positional_scarcity_multiplier(pos_bucket: str, board_buckets: List[str]) -> float:
    if not board_buckets:
        return 1.0
    c = sum(1 for b in board_buckets if b == pos_bucket)
    share = c / len(board_buckets)
    return max(0.92, min(1.06, 1.06 - 0.5 * share))


def position_dropoff_multiplier(
    pos_bucket: str,
    prospect_score: float,
    scores_by_position: Dict[str, List[float]],
    top_n: int = 5,
) -> float:
    """
    Scarcity: gap between this player and the Nth-best at position (higher dropoff -> premium).
    """
    arr = sorted(scores_by_position.get(pos_bucket, []), reverse=True)
    if len(arr) < 2:
        return 1.0
    top1 = arr[0]
    k = min(top_n, len(arr)) - 1
    anchor = arr[k] if k >= 0 else arr[-1]
    gap = max(0.0, top1 - anchor)
    if gap <= 1e-6:
        return 1.0
    edge = max(0.0, prospect_score - anchor) / gap
    # Up to +4% when near top of tier
    return max(0.96, min(1.04, 1.0 + 0.04 * min(1.0, edge)))


def replacement_level_adjustment(pos_bucket: str) -> float:
    base = POSITIONAL_VALUE.get(pos_bucket, 1.0)
    return 0.97 + 0.06 * min(1.2, base)


def dynamic_fusion_weights(
    pos_bucket: str,
    team_need_score: float,
    scheme_fit_score: float,
) -> Tuple[float, float, float, Dict[str, float]]:
    """
    Returns (w_prospect, w_need, w_fit) summing ~1 before scarcity multipliers.
    Need weight scales with team bucket need; fit scales when scheme alignment already strong.
    """
    imp = POSITIONAL_VALUE.get(pos_bucket, 1.0)
    need_n = team_need_score / 100.0
    fit_n = scheme_fit_score / 100.0

    w_need = 0.18 + 0.22 * need_n
    w_fit = 0.14 + 0.16 * fit_n
    w_prospect = 1.0 - w_need - w_fit
    # Premium positions keep slightly more weight on pure grade
    w_prospect += 0.04 * (imp - 1.0)
    w_prospect = max(0.35, min(0.72, w_prospect))
    w_need = max(0.12, min(0.45, w_need))
    w_fit = max(0.10, min(0.38, w_fit))
    s = w_prospect + w_need + w_fit
    w_prospect, w_need, w_fit = w_prospect / s, w_need / s, w_fit / s
    detail = {
        "w_prospect": round(w_prospect, 4),
        "w_need": round(w_need, 4),
        "w_fit": round(w_fit, 4),
        "position_importance": round(imp, 3),
    }
    return w_prospect, w_need, w_fit, detail


def final_draft_score(
    prospect_score: float,
    team_need_score: float,
    scheme_fit_score: float,
    pos_bucket: str,
    board_buckets: List[str],
    *,
    scores_by_position: Dict[str, List[float]] | None = None,
) -> Dict[str, Any]:
    wp, wn, wf, wdetail = dynamic_fusion_weights(pos_bucket, team_need_score, scheme_fit_score)
    base = prospect_score * wp + team_need_score * wn + scheme_fit_score * wf
    sm = positional_scarcity_multiplier(pos_bucket, board_buckets)
    dm = (
        position_dropoff_multiplier(pos_bucket, prospect_score, scores_by_position or {})
        if scores_by_position
        else 1.0
    )
    rm = replacement_level_adjustment(pos_bucket)
    raw = base * sm * dm * rm
    final = max(0.0, min(100.0, raw))
    return {
        "final_draft_score": round(final, 2),
        "fusion_base": round(base, 2),
        "scarcity_mult": round(sm, 4),
        "tier_dropoff_mult": round(dm, 4),
        "replacement_mult": round(rm, 4),
        "dynamic_weights": wdetail,
    }
