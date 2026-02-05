"""
Single source of truth for 5 Keys comparison. Enforces explicit TIE when values are equal.

key_winners must be team_a, team_b, or "TIE". Tied keys do not increment keys_won.
"""

from dataclasses import dataclass
from typing import Dict, Literal

from superbowlengine.features.keys import TeamKeys

Winner = Literal["SEA", "NE", "TIE"]  # generic: any team name or "TIE"


@dataclass(frozen=True)
class KeyComparison:
    """Result of comparing one key between two teams."""

    winner: str  # team_a, team_b, or "TIE"
    margin: float  # team_a - team_b (raw)
    abs_margin: float


def compare_values(
    a: float,
    b: float,
    team_a: str,
    team_b: str,
    *,
    higher_is_better: bool = True,
    eps: float = 1e-9,
) -> KeyComparison:
    """
    Returns winner = team_a / team_b / "TIE" using eps.
    margin is always a - b (raw). If higher_is_better=False, winner is reversed (lower wins).
    """
    margin = a - b
    abs_margin = abs(margin)
    if abs_margin <= eps:
        return KeyComparison(winner="TIE", margin=margin, abs_margin=abs_margin)
    if higher_is_better:
        winner = team_a if a > b else team_b
    else:
        winner = team_a if a < b else team_b
    return KeyComparison(winner=winner, margin=margin, abs_margin=abs_margin)


def compare_5keys(
    keys_a: TeamKeys,
    keys_b: TeamKeys,
    team_a: str,
    team_b: str,
    *,
    eps: float = 1e-9,
) -> Dict[str, KeyComparison]:
    """
    Compare all 5 keys. TOP, BIG, 3D, RZ: higher is better. TO: lower is better.
    Returns dict key_name -> KeyComparison.
    """
    return {
        "TOP": compare_values(keys_a.top_min, keys_b.top_min, team_a, team_b, higher_is_better=True, eps=eps),
        "TO": compare_values(float(keys_a.turnovers), float(keys_b.turnovers), team_a, team_b, higher_is_better=False, eps=eps),
        "BIG": compare_values(float(keys_a.big_plays), float(keys_b.big_plays), team_a, team_b, higher_is_better=True, eps=eps),
        "3D": compare_values(keys_a.third_down_pct, keys_b.third_down_pct, team_a, team_b, higher_is_better=True, eps=eps),
        "RZ": compare_values(keys_a.redzone_td_pct, keys_b.redzone_td_pct, team_a, team_b, higher_is_better=True, eps=eps),
    }
