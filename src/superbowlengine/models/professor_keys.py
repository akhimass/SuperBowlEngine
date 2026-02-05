"""
Unified professor-style engine: 5 Keys + turnover emphasis + 3+ keys rule + optional SOS/DGI.

Single callable takes TeamKeys for two teams, optional team contexts (SOS z, expected TO, DGI),
and returns predicted winner, win probabilities, keys won, top 3 drivers, and an Explanation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from superbowlengine.config import Config, DEFAULT_CONFIG
from superbowlengine.core.key_compare import compare_5keys
from superbowlengine.features.keys import TeamKeys
from superbowlengine.utils.math import sigmoid


@dataclass
class TeamContext:
    """Optional context per team: SOS z-score, expected TO per game, DGI."""

    sos_z: float = 0.0
    expected_turnovers_per_game: Optional[float] = None  # use keys.turnovers if None
    dgi: float = 0.0


@dataclass
class Explanation:
    """Explainable output: key winners, margins, per-component contributions, driver ranking, logit."""

    key_winners: Dict[str, str] = field(default_factory=dict)
    margin_table: Dict[str, float] = field(default_factory=dict)
    contributions: Dict[str, float] = field(default_factory=dict)  # TOP, TO, BIG, 3D, RZ, SOS_z, DGI, rule_3_keys
    driver_ranking: List[Tuple[str, float]] = field(default_factory=list)
    logit: float = 0.0


# Default engine weights: turnover strongest, keys moderate, SOS/DGI mild
DEFAULT_WEIGHTS = {
    "turnover": 1.35,
    "key": 0.55,
    "sos": 0.15,
    "dgi": 0.12,
    "rule_bonus": 0.40,
}
DEFAULT_DIVISORS = {
    "top": 6.0,
    "turnover": 1.0,
    "big_play": 2.0,
    "third_down": 10.0,
    "redzone": 12.0,
}


# Key names for consistent ordering
KEY_NAMES = ["TOP", "TO", "BIG", "3D", "RZ"]


def predict(
    team_a_keys: TeamKeys,
    team_b_keys: TeamKeys,
    team_a_name: str = "SEA",
    team_b_name: str = "NE",
    context_a: Optional[TeamContext] = None,
    context_b: Optional[TeamContext] = None,
    config: Optional[Config] = None,
    weights: Optional[Dict[str, float]] = None,
    divisors: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Single callable engine: predicted winner, win probs, keys won, top 3 drivers, Explanation.

    Logistic score uses tunable weights: turnover strongest; TOP, big plays, 3rd down, red zone
    moderate; DGI and SOS mild. The professor "3+ keys wins" rule is a discrete bonus.
    When expected_turnovers_per_game is provided in context, it is used for the TO component
    instead of raw keys.turnovers (regression toward stability).
    """
    cfg = config or DEFAULT_CONFIG
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)
    else:
        w["turnover"] = cfg.turnover_weight
        w["key"] = cfg.key_weight
        w["rule_bonus"] = cfg.rule_bonus
    div = dict(DEFAULT_DIVISORS)
    if divisors:
        div.update(divisors)
    else:
        div["top"] = cfg.top_divisor
        div["turnover"] = cfg.turnover_divisor
        div["big_play"] = cfg.big_play_divisor
        div["third_down"] = cfg.third_down_divisor
        div["redzone"] = cfg.redzone_divisor

    a, b = team_a_keys, team_b_keys
    ctx_a = context_a or TeamContext()
    ctx_b = context_b or TeamContext()

    comparisons = compare_5keys(a, b, team_a_name, team_b_name)
    key_winners = {k: comp.winner for k, comp in comparisons.items()}
    keys_a = sum(1 for w in key_winners.values() if w == team_a_name)
    keys_b = sum(1 for w in key_winners.values() if w == team_b_name)
    tied_keys = [k for k, w in key_winners.items() if w == "TIE"]
    ties = len(tied_keys)
    counts: Dict[str, int] = {team_a_name: keys_a, team_b_name: keys_b}

    # Margins: (team_a - team_b); positive = A better. TO: fewer giveaways = better, so margin = team_b_to - team_a_to (positive favors A).
    m_top = a.top_min - b.top_min
    m_to_raw = b.turnovers - a.turnovers  # fewer TO for A => positive
    if ctx_a.expected_turnovers_per_game is not None and ctx_b.expected_turnovers_per_game is not None:
        m_to = ctx_b.expected_turnovers_per_game - ctx_a.expected_turnovers_per_game
    else:
        m_to = m_to_raw
    m_big = a.big_plays - b.big_plays
    m_3d = a.third_down_pct - b.third_down_pct
    m_rz = a.redzone_td_pct - b.redzone_td_pct
    m_sos = ctx_a.sos_z - ctx_b.sos_z
    m_dgi = (ctx_a.dgi - ctx_b.dgi) if (ctx_a.dgi or ctx_b.dgi) else 0.0

    margin_table = {
        "TOP": m_top,
        "TO": m_to,
        "BIG": m_big,
        "3D": m_3d,
        "RZ": m_rz,
        "SOS_z": m_sos,
        "DGI": m_dgi,
    }

    # Per-component contributions: weight * (margin / divisor). Positive = favors team A.
    contrib: Dict[str, float] = {
        "TOP": w["key"] * (m_top / div["top"]),
        "TO": w["turnover"] * (m_to / div["turnover"]),
        "BIG": w["key"] * (m_big / div["big_play"]),
        "3D": w["key"] * (m_3d / div["third_down"]),
        "RZ": w["key"] * (m_rz / div["redzone"]),
        "SOS_z": w["sos"] * m_sos,
        "DGI": w["dgi"] * m_dgi,
    }
    logit = sum(contrib.values())

    # Professor rule: only keys_won (non-ties) count. Team with >= 3 keys_won gets bonus; ties don't help either team.
    rule_bonus_val = w["rule_bonus"]
    rule_contrib = 0.0
    if keys_a >= 3 and keys_b < 3:
        logit += rule_bonus_val
        rule_contrib = rule_bonus_val
    elif keys_b >= 3 and keys_a < 3:
        logit -= rule_bonus_val
        rule_contrib = -rule_bonus_val
    contrib["rule_3_keys"] = rule_contrib

    # Professor rule enforcement: only clamp when one team has >= 3 keys_won (not 2-2-1).
    keys_winner: Optional[str] = None
    if keys_a >= 3:
        keys_winner = team_a_name
    elif keys_b >= 3:
        keys_winner = team_b_name
    p_a = sigmoid(logit)
    logit_based_winner = team_a_name if p_a >= 0.5 else team_b_name
    if keys_winner is not None and keys_winner != logit_based_winner:
        if keys_winner == team_a_name:
            logit = max(logit, 0.0)
        else:
            logit = min(logit, -0.01)
        p_a = sigmoid(logit)

    predicted_winner = team_a_name if p_a >= 0.5 else team_b_name
    assert (predicted_winner == team_a_name and p_a >= 0.5) or (predicted_winner == team_b_name and (1 - p_a) >= 0.5)

    # Driver ranking from contributions (top 3 by absolute contribution)
    driver_ranking = sorted(
        [(k, v) for k, v in contrib.items() if v != 0],
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:3]

    explanation = Explanation(
        key_winners=key_winners,
        margin_table=margin_table,
        contributions=dict(contrib),
        driver_ranking=driver_ranking,
        logit=logit,
    )

    return {
        "predicted_winner": predicted_winner,
        "p_team_a_win": round(p_a, 3),
        "p_team_b_win": round(1 - p_a, 3),
        "keys_won": counts,
        "ties": ties,
        "tied_keys": tied_keys,
        "top_3_drivers": driver_ranking,
        "explanation": explanation,
        "logit": round(logit, 4),
    }


def predict_from_keys(
    sea: TeamKeys,
    ne: TeamKeys,
    turnover_weight: Optional[float] = None,
    key_weight: Optional[float] = None,
    rule_bonus: Optional[float] = None,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """
    Backward-compatible: same as p1.py. Calls predict() with SEA/NE and returns
    legacy shape (p_sea_win, p_ne_win, predicted_winner, keys_won, key_winners,
    margins_sea_minus_ne). Explanation and top_3_drivers are not in the legacy dict.
    """
    weights = None
    if turnover_weight is not None or key_weight is not None or rule_bonus is not None:
        weights = {**DEFAULT_WEIGHTS}
        if turnover_weight is not None:
            weights["turnover"] = turnover_weight
        if key_weight is not None:
            weights["key"] = key_weight
        if rule_bonus is not None:
            weights["rule_bonus"] = rule_bonus
    out = predict(
        sea, ne,
        team_a_name="SEA",
        team_b_name="NE",
        context_a=None,
        context_b=None,
        config=config,
        weights=weights,
    )
    return {
        "p_sea_win": out["p_team_a_win"],
        "p_ne_win": out["p_team_b_win"],
        "predicted_winner": out["predicted_winner"],
        "keys_won": out["keys_won"],
        "ties": out.get("ties", 0),
        "tied_keys": out.get("tied_keys", []),
        "key_winners": out["explanation"].key_winners,
        "margins_sea_minus_ne": {
            k: out["explanation"].margin_table[k]
            for k in ("TOP", "TO", "BIG", "3D", "RZ")
        },
    }
