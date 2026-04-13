from __future__ import annotations

from typing import List

from .schemas import ExplainerContext


def build_phi4_prompt(context: ExplainerContext) -> str:
    """
    Build a grounded, football-native prompt for the AI Statistician.

    The model is instructed to ONLY use provided data and return a JSON object
    matching AIExplanationResult.
    """
    m = context.matchup
    r = context.scouting_report

    team_a = m.get("team_a") or r.get("team_a")
    team_b = m.get("team_b") or r.get("team_b")
    season = m.get("season") or r.get("season")

    lines: List[str] = []
    lines.append(
        "You are the GridironIQ AI Statistician, a concise NFL analyst who explains model outputs "
        "to coaches and front-office staff. You are NOT a chatbot."
    )
    lines.append("")
    lines.append("STRICT RULES:")
    lines.append("- Only use data explicitly provided in the context.")
    lines.append("- Do NOT invent stats, scores, or probabilities.")
    lines.append("- Use concise, football-native language.")
    lines.append("- No fantasy or gambling talk.")
    lines.append("- Output a single JSON object only, no extra prose.")
    lines.append("")
    lines.append(f"Matchup: {team_a} vs {team_b}, season {season}.")
    lines.append("")
    lines.append("=== MATCHUP RESULT ===")
    lines.append(str(m))
    lines.append("")
    lines.append("=== SCOUTING REPORT ===")
    lines.append(str(r))
    if context.situational_report is not None:
        lines.append("")
        lines.append("=== SITUATIONAL REPORT ===")
        lines.append(str(context.situational_report))
    if context.broadcast_report is not None:
        lines.append("")
        lines.append("=== BROADCAST REPORT ===")
        lines.append(str(context.broadcast_report))
    if context.qb_report is not None:
        lines.append("")
        lines.append("=== QB REPORT ===")
        lines.append(str(context.qb_report))
    if context.visuals is not None:
        lines.append("")
        lines.append("=== VISUAL REFERENCES ===")
        lines.append(str(context.visuals))

    lines.append("")
    lines.append(
        "Using ONLY this context, produce an explanation JSON with fields: "
        "`summary` (2–3 sentences), "
        "`top_3_reasons` (list of concise bullets), "
        "`what_matters_most` (single sentence), "
        "`what_could_flip_it` (single sentence from underdog perspective), "
        "`why_prediction_was_right_or_wrong` (optional, single sentence), "
        "`confidence_note` (optional, single sentence)."
    )

    lines.append("")
    lines.append("Return JSON only. Example shape (do not copy values):")
    lines.append(
        '{'
        '"summary": "...", '
        '"top_3_reasons": ["...", "...", "..."], '
        '"what_matters_most": "...", '
        '"what_could_flip_it": "...", '
        '"why_prediction_was_right_or_wrong": null, '
        '"confidence_note": "..."'
        "}"
    )

    return "\n".join(lines)

