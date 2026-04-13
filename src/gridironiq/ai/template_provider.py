from __future__ import annotations

from typing import List

from .provider import AIProvider
from .schemas import AIExplanationResult, ExplainerContext


class TemplateProvider(AIProvider):
    """Deterministic, template-driven AI Statistician (no model calls)."""

    def generate(self, context: ExplainerContext) -> AIExplanationResult:
        m = context.matchup
        r = context.scouting_report

        team_a = m.get("team_a") or r.get("team_a")
        team_b = m.get("team_b") or r.get("team_b")
        season = m.get("season") or r.get("season")
        win_prob = m.get("win_probability") or r.get("win_probability")
        predicted_winner = m.get("predicted_winner") or r.get("predicted_winner")
        projected_score = m.get("projected_score") or r.get("projected_score") or {}

        score_a = projected_score.get(team_a, 0)
        score_b = projected_score.get(team_b, 0)

        summary = (
            f"In {season}, {team_a} vs {team_b}, the model leans {predicted_winner} with "
            f"approximately {round(float(win_prob or 0) * 100, 1)}% win probability "
            f"and a projected score around {score_a}–{score_b}. "
            "The edge comes from the five keys (time of possession, turnovers, explosives, 3rd down, red zone) "
            "after adjusting for opponent strength."
        )

        strengths_a: List[str] = r.get("team_a_strengths") or []
        strengths_b: List[str] = r.get("team_b_strengths") or []

        top_reasons: List[str] = []
        if strengths_a or strengths_b:
            if strengths_b and predicted_winner == team_b:
                top_reasons.append(f"{team_b} holds clear advantages in: {', '.join(strengths_b[:3])}.")
            if strengths_a and predicted_winner == team_a:
                top_reasons.append(f"{team_a} holds clear advantages in: {', '.join(strengths_a[:3])}.")

        if not top_reasons:
            top_reasons.append("Core efficiency keys tilt slightly toward the favored side.")

        prediction_explanation = r.get("prediction_explanation") or ""
        if prediction_explanation:
            top_reasons.append(prediction_explanation)

        what_matters_most = (
            "Sustaining drives, finishing red zone trips, and avoiding short fields off turnovers."
        )

        what_could_flip_it = (
            f"If {team_a if predicted_winner == team_b else team_b} swings turnover margin and "
            "wins critical 3rd downs, the matchup could compress quickly."
        )

        why_right_or_wrong = None
        if context.situational_report is not None and "actual_score" in context.matchup:
            why_right_or_wrong = (
                "Post-game comparison between projected and actual scores shows where the model "
                "over- or under-weighted specific keys; use the full game report to inspect those gaps."
            )

        confidence_notes = r.get("confidence_notes") or []
        confidence_note = confidence_notes[0] if confidence_notes else None

        return AIExplanationResult(
            summary=summary,
            top_3_reasons=top_reasons[:3],
            what_matters_most=what_matters_most,
            what_could_flip_it=what_could_flip_it,
            why_prediction_was_right_or_wrong=why_right_or_wrong,
            confidence_note=confidence_note,
        )

