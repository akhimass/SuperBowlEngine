from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from .ai.explainer import build_explainer_context, generate_ai_explanation
from .matchup_engine import MatchupResult
from .qb_production_engine import QBComparisonResult

# Key names for readable labels
KEY_LABELS = {
    "TOP": "Time of Possession",
    "TO": "Turnover Margin",
    "BIG": "Explosive Plays",
    "3D": "Third-Down Conversion Rate",
    "RZ": "Red Zone Conversion Rate",
}


@dataclass
class ScoutingReport:
    """Compact, JSON-friendly scouting report object for the frontend."""

    matchup: Dict[str, Any]
    qb_comparison: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_report(
    matchup_result: MatchupResult,
    *,
    situational_report: Optional[Dict[str, Any]] = None,
    qb_report: Optional[Dict[str, Any]] = None,
    broadcast_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a structured scouting report from a MatchupResult.

    Returns JSON-ready dict with:
      summary, team_a_strengths, team_b_strengths, offensive_profile,
      defensive_profile, qb_impact, prediction_explanation, confidence_notes.
    """
    a, b = matchup_result.team_a, matchup_result.team_b
    win_pct = round(matchup_result.win_probability * 100, 1)
    winner = matchup_result.predicted_winner
    score = matchup_result.projected_score
    keys_won = matchup_result.keys_won
    edges = matchup_result.key_edges
    drivers = matchup_result.top_drivers
    expl = matchup_result.explanation or {}
    key_winners = expl.get("key_winners") or {}

    score_a = score.get(a, 0)
    score_b = score.get(b, 0)

    margin = score_b - score_a if winner == b else score_a - score_b
    projected_margin = matchup_result.projected_margin if matchup_result.projected_margin is not None else float(margin)
    projected_total = matchup_result.projected_total if matchup_result.projected_total is not None else float(score_a + score_b)
    summary = (
        f"{a} vs {b} ({matchup_result.season}): model favors {winner} with {win_pct}% win probability "
        f"(projected {score_a}–{score_b}). Keys won: {a} {keys_won.get(a, 0)}, {b} {keys_won.get(b, 0)}. "
        "Outcome is driven by the five core keys (Time of Possession, turnovers, explosive plays, 3rd down, red zone) "
        "and opponent-adjusted strength of schedule."
    )

    team_a_strengths: List[str] = []
    team_b_strengths: List[str] = []
    for key, label in KEY_LABELS.items():
        w = key_winners.get(key)
        m = edges.get(key)
        if w == a and m is not None:
            team_a_strengths.append(f"{label}: edge +{m:.2f}")
        elif w == b and m is not None:
            team_b_strengths.append(f"{label}: edge {m:.2f}")
        elif w == "TIE":
            pass

    if edges.get("SOS_z", 0) > 0:
        team_a_strengths.append("Strength of schedule (SOS) advantage")
    elif edges.get("SOS_z", 0) < 0:
        team_b_strengths.append("Strength of schedule (SOS) advantage")

    offensive_keys = ["TOP", "BIG", "3D", "RZ"]
    offensive_profile: Dict[str, Any] = {
        a: {k: round(edges.get(k, 0), 2) for k in offensive_keys if k in edges},
        b: {k: round(edges.get(k, 0), 2) for k in offensive_keys if k in edges},
    }
    defensive_profile: Dict[str, Any] = {
        "turnover_margin": round(edges.get("TO", 0), 2),
        "sos_z_diff": round(edges.get("SOS_z", 0), 2),
    }

    qb_impact: Dict[str, Any] = {
        "note": "QB production comparison available via /api/qb/compare for specific quarterbacks.",
    }

    prediction_explanation = (
        "Top drivers of the win probability: "
        + "; ".join(f"{KEY_LABELS.get(k, k)} (impact {v:.2f})" for k, v in drivers)
        if drivers
        else "No driver breakdown available."
    )

    confidence_notes: List[str] = [
        "Model uses opponent-weighted play-by-play splits with postseason emphasis when available.",
        "Turnovers are volatile; sustained success in success rate and EPA are treated as more stable edges.",
        "Score projection is from a separate regression; use for context, not certainty.",
    ]

    # --- Richer, sectioned report for frontend consumption ---

    executive_summary = {
        "headline": f"{winner} has a clear edge in the core efficiency keys.",
        "detail": summary,
        "projected_margin": projected_margin,
        "projected_total": projected_total,
    }

    offensive_outlook = {
        "team_a": a,
        "team_b": b,
        "keys": offensive_profile,
        "narrative": [
            f"{a} gains offensive leverage when it nudges TOP and explosive plays back toward even.",
            f"{b} can press its advantage by sustaining drives (3rd down) and converting red zone trips into touchdowns.",
        ],
    }

    defensive_outlook = {
        "turnover_margin": defensive_profile["turnover_margin"],
        "sos_z_diff": defensive_profile["sos_z_diff"],
        "narrative": [
            "Turnover margin is treated as a high-variance but high-impact factor.",
            "Schedule strength (SOS_z) adjusts the keys so dominant performances against soft schedules are not over-weighted.",
        ],
    }

    situational_edges = {
        "note": "Full situational heatmaps are available via /api/report/situational and /api/report/matchup.",
        "keys_emphasised": ["TOP", "3D", "RZ"],
    }

    qb_influence = {
        "summary": "QB production can tilt otherwise even matchups; use the QB comparison view for deeper context.",
        "note": qb_impact["note"],
    }

    risk_factors = [
        "High reliance on red zone execution can create wider variance in actual score than projected.",
        "If turnover margin swings against the favored team, the model's edge compresses quickly.",
    ]

    final_logic = (
        f"The model leans {winner} primarily because it controls more of the five keys with sustainable efficiency, "
        "after adjusting for opponent strength and game script."
    )

    visual_references = {
        "situational_report_endpoint": "/api/report/situational",
        "full_matchup_report_endpoint": "/api/report/matchup",
        "broadcast_report_endpoint": "/api/report/broadcast",
    }

    base_report: Dict[str, Any] = {
        "summary": summary,
        "team_a_strengths": team_a_strengths,
        "team_b_strengths": team_b_strengths,
        "offensive_profile": offensive_profile,
        "defensive_profile": defensive_profile,
        "qb_impact": qb_impact,
        "prediction_explanation": prediction_explanation,
        "confidence_notes": confidence_notes,
        "team_a": a,
        "team_b": b,
        "season": matchup_result.season,
        "win_probability": matchup_result.win_probability,
        "predicted_winner": winner,
        "projected_score": score,
        "projected_margin": projected_margin,
        "projected_total": projected_total,
        "team_efficiency_edges": matchup_result.team_efficiency_edges or {},
        "keys_won": keys_won,
        "top_drivers": [list(p) for p in drivers],
        # New, richer sections:
        "executive_summary": executive_summary,
        "offensive_outlook": offensive_outlook,
        "defensive_outlook": defensive_outlook,
        "situational_edges_section": situational_edges,
        "qb_influence": qb_influence,
        "risk_factors": risk_factors,
        "final_prediction_logic": final_logic,
        "visual_references": visual_references,
    }

    # Attach AI Statistician explanation (template or Phi-4, depending on config)
    ctx = build_explainer_context(
        matchup_result,
        base_report,
        situational_report=situational_report,
        qb_report=qb_report,
        broadcast_report=broadcast_report,
        visuals=None,
    )
    ai_result = generate_ai_explanation(ctx)
    base_report["ai_statistician"] = asdict(ai_result)

    return base_report


def build_scouting_report(matchup: MatchupResult, qb_comparison: QBComparisonResult) -> ScoutingReport:
    """
    Shape matchup + QB outputs into a single JSON payload suitable for UI cards/tables.

    This is intentionally lightweight in this phase; the goal is to keep a clear contract
    between the backend engines and the frontend.
    """
    matchup_section: Dict[str, Any] = {
        "team_a": matchup.team_a,
        "team_b": matchup.team_b,
        "season": matchup.season,
        "mode": matchup.mode,
        "win_probability": matchup.win_probability,
        "predicted_winner": matchup.predicted_winner,
        "projected_score": matchup.projected_score,
        "keys_won": matchup.keys_won,
        "key_edges": matchup.key_edges,
        "top_drivers": [list(p) for p in matchup.top_drivers],
    }

    qb_section: Dict[str, Any] = {
        "qb_a": qb_comparison.qb_a,
        "team_a": qb_comparison.team_a,
        "qb_b": qb_comparison.qb_b,
        "team_b": qb_comparison.team_b,
        "season": qb_comparison.season,
        "sustain_score": qb_comparison.sustain_score,
        "situational_score": qb_comparison.situational_score,
        "offscript_score": qb_comparison.offscript_score,
        "total_score": qb_comparison.total_score,
        "avg_def_z": qb_comparison.avg_def_z,
    }

    return ScoutingReport(matchup=matchup_section, qb_comparison=qb_section)

