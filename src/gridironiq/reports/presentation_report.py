"""
Presentation-style report: slide-friendly bullets, key edges, visual references.

For downloadable report packets and internal briefings.
Output: JSON + optional PNG export later.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .matchup_report import build_matchup_report

logger = logging.getLogger(__name__)


def build_presentation_report(
    season: int,
    team_a: str,
    team_b: str,
    *,
    week: Optional[int] = None,
    matchup_data: Optional[Dict[str, Any]] = None,
    generate_heatmaps: bool = False,
) -> Dict[str, Any]:
    """
    Build presentation-style report: bold titles, concise bullets, key edges, visual refs.

    If matchup_data is provided, reuses it; otherwise calls build_matchup_report.
    """
    if matchup_data is None:
        matchup_data = build_matchup_report(
            season, team_a, team_b, week=week, generate_heatmaps=generate_heatmaps,
        )

    pred_winner = matchup_data.get("predicted_winner", "")
    win_pct = matchup_data.get("win_probability")
    score = matchup_data.get("projected_score") or {}

    slides: List[Dict[str, Any]] = []

    # Slide 1: Title / prediction
    slides.append({
        "title": f"{team_a} vs {team_b} — {season}" + (f" Week {week}" if week else ""),
        "bullets": [
            f"Projected winner: {pred_winner}",
            f"Win probability: {round(win_pct * 100, 1)}%" if win_pct is not None else "—",
            f"Projected score: {team_a} {score.get(team_a, 0)} – {team_b} {score.get(team_b, 0)}",
        ],
    })

    # Slide 2: Key edges
    key_edges = matchup_data.get("key_matchup_edges")
    if isinstance(key_edges, dict) and key_edges:
        edge_bullets = [f"{k}: {v}" if isinstance(v, (int, float)) else f"{k}: {v}" for k, v in key_edges.items()]
        slides.append({"title": "Key matchup edges", "bullets": edge_bullets})
    else:
        drivers = matchup_data.get("top_drivers") or []
        if drivers:
            slides.append({
                "title": "Top drivers",
                "bullets": [f"{k}: {v:.2f}" for k, v in drivers] if all(isinstance(d, (list, tuple)) and len(d) >= 2 for d in drivers) else [str(d) for d in drivers],
            })

    # Slide 3: Team strengths
    pa = matchup_data.get("team_a_profile") or {}
    pb = matchup_data.get("team_b_profile") or {}
    bullets = [f"{team_a}: " + "; ".join(pa.get("strengths", [])) or "—", f"{team_b}: " + "; ".join(pb.get("strengths", [])) or "—"]
    slides.append({"title": "Team strengths", "bullets": bullets})

    # Slide 4: Situational / visuals
    report_assets = matchup_data.get("report_assets") or []
    asset_refs = [a.get("path") or a.get("caption", "") for a in report_assets if a.get("path")]
    slides.append({
        "title": "Situational tendencies & visuals",
        "bullets": [
            "Run/pass tendency and success rate by down/distance and field position.",
            "Offense vs defense situational comparison available in full report.",
        ] + ([f"Generated assets: {len(asset_refs)} chart(s)."] if asset_refs else []),
        "visual_refs": asset_refs[:10],
    })

    return {
        "report_type": "presentation",
        "season": season,
        "week": week,
        "team_a": team_a,
        "team_b": team_b,
        "title": f"{team_a} vs {team_b} — Scouting report ({season})",
        "slides": slides,
        "report_assets": report_assets,
    }
