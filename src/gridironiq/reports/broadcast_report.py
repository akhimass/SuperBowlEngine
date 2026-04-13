"""
Broadcast-style report: short, media-friendly summary for TV/producer use.

Headline stats, matchup talking points, situational tendencies, top storylines.
Output: JSON for frontend cards; optional PNG export later.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .matchup_report import build_matchup_report

logger = logging.getLogger(__name__)


def build_broadcast_report(
    season: int,
    team_a: str,
    team_b: str,
    *,
    week: Optional[int] = None,
    matchup_data: Optional[Dict[str, Any]] = None,
    generate_heatmaps: bool = False,
) -> Dict[str, Any]:
    """
    Build broadcast-style report: headline stats, talking points, top 3 storylines.

    If matchup_data is provided, reuses it; otherwise calls build_matchup_report(..., generate_heatmaps=False).
    """
    if matchup_data is None:
        matchup_data = build_matchup_report(
            season, team_a, team_b, week=week, generate_heatmaps=generate_heatmaps,
        )

    summary = matchup_data.get("summary", "")
    pred_winner = matchup_data.get("predicted_winner", "")
    win_pct = matchup_data.get("win_probability")
    score = matchup_data.get("projected_score") or {}
    score_a = score.get(team_a, 0)
    score_b = score.get(team_b, 0)

    headline_stats: List[Dict[str, Any]] = [
        {"label": "Projected winner", "value": pred_winner},
        {"label": "Win probability", "value": f"{round(win_pct * 100, 1)}%" if win_pct is not None else "—"},
        {"label": "Projected score", "value": f"{team_a} {score_a} – {team_b} {score_b}"},
    ]

    keys_won = matchup_data.get("keys_won") or {}
    headline_stats.append({"label": "Keys won", "value": f"{team_a} {keys_won.get(team_a, 0)} – {team_b} {keys_won.get(team_b, 0)}"})

    talking_points: List[str] = []
    for s in matchup_data.get("team_a_strengths", matchup_data.get("team_a_profile", {}).get("strengths", [])):
        talking_points.append(f"{team_a}: {s}")
    for s in matchup_data.get("team_b_strengths", matchup_data.get("team_b_profile", {}).get("strengths", [])):
        talking_points.append(f"{team_b}: {s}")
    if not talking_points and matchup_data.get("prediction_explanation"):
        talking_points.append(matchup_data["prediction_explanation"])

    situational_note = ""
    if matchup_data.get("situational_edges") and "note" not in matchup_data["situational_edges"]:
        situational_note = "Situational run/pass tendencies and success rates by down/distance and field position are available in the full report."

    top_storylines: List[str] = []
    drivers = matchup_data.get("top_drivers") or matchup_data.get("key_matchup_edges")
    if isinstance(drivers, dict):
        drivers = drivers.get("top_drivers", drivers.get("key_edges", []))
    if isinstance(drivers, list) and drivers:
        for i, d in enumerate(drivers[:3]):
            if isinstance(d, (list, tuple)) and len(d) >= 2:
                top_storylines.append(f"{d[0]}: {d[1]:.2f}")
            else:
                top_storylines.append(str(d))
    if not top_storylines and pred_winner:
        top_storylines.append(f"Model favors {pred_winner} based on five keys (TOP, turnovers, big plays, 3rd down, red zone).")

    return {
        "report_type": "broadcast",
        "season": season,
        "week": week,
        "team_a": team_a,
        "team_b": team_b,
        "headline": f"{team_a} vs {team_b} — {season}" + (f" Week {week}" if week else ""),
        "summary": summary,
        "headline_stats": headline_stats,
        "talking_points": talking_points,
        "situational_tendencies_note": situational_note,
        "top_3_storylines": top_storylines,
        "confidence_notes": matchup_data.get("confidence_notes", []),
    }
