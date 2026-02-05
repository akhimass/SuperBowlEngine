"""
Turnover regression: stabilize turnover expectations for prediction.

Why turnovers are noisy
----------------------
Turnovers are high-variance events: a few bounces or referee calls change
counts a lot. In a tiny sample (e.g. 1–3 postseason games), raw turnover counts
are unreliable. A team with 0 postseason turnovers may have been lucky, not
"zero expected" in the next game. Using raw counts in a model over-rewards or
over-penalizes these extremes and hurts prediction stability.

Why regression is necessary
--------------------------
Regression (blending season and postseason rates, then clamping to a plausible
per-game range) shrinks extreme small-sample values toward a reasonable
expectation. That avoids projecting 0 postseason turnovers as literally 0
expected and keeps predictions stable (the "Seahawks argument": don't treat
small-sample extremes as if they will repeat).
"""

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from superbowlengine.features.keys import TeamKeys


def expected_turnovers(
    season_to_pg: float,
    post_to_pg: float,
    *,
    w_post: float = 0.55,
    w_season: float = 0.45,
    floor: float = 0.4,
    ceil: float = 2.2,
) -> float:
    """
    Expected turnovers per game as a weighted blend of season and postseason
    rates, clamped to [floor, ceil]. Avoids projecting 0 postseason turnovers
    as literally 0 expected.

    Weights default to slightly favoring postseason (w_post=0.55) while still
    regressing toward season (w_season=0.45). Clamp keeps the value in a
    plausible per-game range (e.g. 0.4–2.2) so predictions stay stable.
    """
    blend = w_post * post_to_pg + w_season * season_to_pg
    return max(floor, min(ceil, blend))


def turnovers_in_losses_vs_wins(game_keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Optional helper: split turnovers and games into losses vs wins from a list
    of per-game key dicts. Each dict should have "turnovers" (int) and "win"
    (bool). Returns aggregates for losses and wins (count, total turnovers, to per game).
    """
    losses_to = 0
    losses_n = 0
    wins_to = 0
    wins_n = 0
    for g in game_keys:
        to = g.get("turnovers", 0)
        win = g.get("win", False)
        if win:
            wins_to += to
            wins_n += 1
        else:
            losses_to += to
            losses_n += 1
    def _pg(total: int, n: int) -> float:
        return total / n if n else 0.0
    return {
        "losses": {"games": losses_n, "turnovers": losses_to, "to_per_game": _pg(losses_to, losses_n)},
        "wins": {"games": wins_n, "turnovers": wins_to, "to_per_game": _pg(wins_to, wins_n)},
    }


def predict_turnover_regression(
    _team_a_keys: "TeamKeys",
    _team_b_keys: "TeamKeys",
    _params: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    """
    Placeholder: turnover-focused regression predictor.
    Can use expected_turnovers() for each team's blended rate, then compare.
    """
    return {"predicted_winner": None, "p_team_a": 0.5, "p_team_b": 0.5}
