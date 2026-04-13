from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from ..matchup_engine import MatchupResult
from .phi4_provider import Phi4Provider
from .schemas import AIExplanationResult, ExplainerContext
from .template_provider import TemplateProvider

logger = logging.getLogger(__name__)


def build_explainer_context(
    matchup_result: MatchupResult,
    scouting_report: Dict[str, Any],
    situational_report: Optional[Dict[str, Any]] = None,
    qb_report: Optional[Dict[str, Any]] = None,
    broadcast_report: Optional[Dict[str, Any]] = None,
    visuals: Optional[Dict[str, Any]] = None,
) -> ExplainerContext:
    matchup_dict: Dict[str, Any] = {
        "team_a": matchup_result.team_a,
        "team_b": matchup_result.team_b,
        "season": matchup_result.season,
        "mode": matchup_result.mode,
        "win_probability": matchup_result.win_probability,
        "predicted_winner": matchup_result.predicted_winner,
        "projected_score": matchup_result.projected_score,
        "keys_won": matchup_result.keys_won,
        "key_edges": matchup_result.key_edges,
        "top_drivers": [list(p) for p in matchup_result.top_drivers],
    }
    return ExplainerContext(
        matchup=matchup_dict,
        scouting_report=scouting_report,
        situational_report=situational_report,
        qb_report=qb_report,
        broadcast_report=broadcast_report,
        visuals=visuals,
    )


def _select_provider(mode: str):
    if mode == "phi4":
        return Phi4Provider()
    return TemplateProvider()


def generate_ai_explanation(
    context: ExplainerContext,
    mode: Optional[str] = None,
) -> AIExplanationResult:
    """
    Generate an AI explanation using either the template provider or Phi-4.

    mode:
      - "template": always use TemplateProvider.
      - "phi4": try Phi4Provider and fall back to TemplateProvider on failure.
      - None: read GRIDIRONIQ_AI_MODE env var, default to "template".
    """
    resolved_mode = mode or os.getenv("GRIDIRONIQ_AI_MODE", "template").lower()
    provider = _select_provider(resolved_mode)
    try:
        return provider.generate(context)
    except Exception as e:  # noqa: BLE001
        logger.exception("AI explanation generation failed; falling back to template: %s", e)
        fallback = TemplateProvider()
        return fallback.generate(context)

