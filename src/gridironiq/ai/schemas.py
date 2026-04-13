from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ExplainerContext:
    """Structured context passed into the AI Statistician providers."""

    matchup: Dict[str, Any]
    scouting_report: Dict[str, Any]
    situational_report: Optional[Dict[str, Any]] = None
    qb_report: Optional[Dict[str, Any]] = None
    broadcast_report: Optional[Dict[str, Any]] = None
    visuals: Optional[Dict[str, Any]] = None
    draft_intel: Optional[Dict[str, Any]] = None


@dataclass
class AIExplanationResult:
    """Structured AI explanation returned to the frontend."""

    summary: str
    top_3_reasons: List[str]
    what_matters_most: str
    what_could_flip_it: str
    why_prediction_was_right_or_wrong: Optional[str] = None
    confidence_note: Optional[str] = None

