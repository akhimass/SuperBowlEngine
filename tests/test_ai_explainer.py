from __future__ import annotations

from gridironiq.ai.explainer import build_explainer_context, generate_ai_explanation
from gridironiq.ai.schemas import AIExplanationResult
from gridironiq.matchup_engine import MatchupResult


def _dummy_matchup() -> MatchupResult:
    return MatchupResult(
        team_a="GB",
        team_b="DET",
        season=2024,
        mode="opp_weighted",
        win_probability=0.62,
        predicted_winner="GB",
        projected_score={"GB": 27, "DET": 21},
        keys_won={"GB": 3, "DET": 2},
        key_edges={"TOP": 2.1, "BIG": 1.5},
        top_drivers=(("TOP", 1.2), ("BIG", 0.9)),
        explanation={"key_winners": {"TOP": "GB", "BIG": "GB"}},
    )


def test_template_provider_generates_structured_output() -> None:
    matchup = _dummy_matchup()
    scouting = {
        "team_a": "GB",
        "team_b": "DET",
        "season": 2024,
        "summary": "GB vs DET test summary.",
        "team_a_strengths": ["Time of Possession: edge +2.10"],
        "team_b_strengths": [],
        "offensive_profile": {"GB": {"TOP": 2.1}, "DET": {"TOP": -2.1}},
        "defensive_profile": {"turnover_margin": 0.0, "sos_z_diff": 0.0},
        "prediction_explanation": "TOP and BIG lean GB.",
        "confidence_notes": ["Template mode."],
        "win_probability": 0.62,
        "predicted_winner": "GB",
        "projected_score": {"GB": 27, "DET": 21},
        "keys_won": {"GB": 3, "DET": 2},
        "top_drivers": [["TOP", 1.2], ["BIG", 0.9]],
    }
    ctx = build_explainer_context(matchup, scouting)
    result = generate_ai_explanation(ctx, mode="template")
    assert isinstance(result, AIExplanationResult)
    assert result.summary
    assert result.top_3_reasons
    assert result.what_matters_most
    assert result.what_could_flip_it

