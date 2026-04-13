from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import os

from gridironiq.models.matchup_features import MatchupFeatures


@dataclass(frozen=True)
class TotalArtifacts:
    intercept: float
    coef: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


DEFAULT_ARTIFACTS = TotalArtifacts(
    # Prior total around modern NFL scoring.
    intercept=45.5,
    # Totals respond to combined efficiency; use small weights.
    coef={
        # Higher epa_edge magnitude tends to increase volatility, but totals are more about combined offense.
        # We use absolute-ish proxies by feeding both teams via team efficiencies in the feature layer later;
        # here we keep a light dependence on features that correlate with pace/efficiency.
        "explosive_edge": 6.0,
        "success_edge": 4.0,
        "early_down_success_edge": 3.0,
        "redzone_edge": 2.0,
        "sack_edge": -2.0,
    },
)


def _artifact_path(filename: str) -> Path:
    base = os.getenv("GRIDIRONIQ_MODEL_ARTIFACT_DIR", "outputs/model_artifacts")
    return Path(base) / filename


def load_artifacts(path: Optional[str] = None) -> Optional[TotalArtifacts]:
    p = Path(path) if path else _artifact_path("total_model.json")
    if not p.exists():
        return None
    import json

    with open(p) as f:
        d = json.load(f)
    return TotalArtifacts(
        intercept=float(d.get("intercept", 45.5)),
        coef={k: float(v) for k, v in (d.get("coef", {}) or {}).items()},
    )


def predict_total(
    feats: MatchupFeatures,
    *,
    artifacts: Optional[TotalArtifacts] = None,
    safety_low: float = 24.0,
    safety_high: float = 62.0,
) -> Dict[str, Any]:
    a = artifacts or DEFAULT_ARTIFACTS
    x = feats.to_dict()
    raw = float(a.intercept) + sum(float(a.coef.get(k, 0.0)) * float(x.get(k, 0.0)) for k in a.coef.keys())
    clamped = max(safety_low, min(safety_high, raw))
    return {
        "predicted_total": float(clamped),
        "unclamped_total": float(raw),
        "clamped": bool(raw != clamped),
    }

