from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import os

from gridironiq.models.matchup_features import MatchupFeatures


@dataclass(frozen=True)
class MarginArtifacts:
    intercept: float
    coef: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


DEFAULT_ARTIFACTS = MarginArtifacts(
    intercept=0.0,
    # Coefficients map stable feature edges to points.
    # These are conservative defaults designed to keep margins NFL-plausible.
    coef={
        "epa_edge": 28.0,
        "success_edge": 18.0,
        "explosive_edge": 14.0,
        "early_down_success_edge": 10.0,
        "third_down_edge": 6.0,
        "redzone_edge": 6.0,
        "sack_edge": 4.0,
        "sos_edge": 1.5,
        "recent_epa_edge": 6.0,
    },
)


def _artifact_path(filename: str) -> Path:
    base = os.getenv("GRIDIRONIQ_MODEL_ARTIFACT_DIR", "outputs/model_artifacts")
    return Path(base) / filename


def load_artifacts(path: Optional[str] = None) -> Optional[MarginArtifacts]:
    p = Path(path) if path else _artifact_path("margin_model.json")
    if not p.exists():
        return None
    import json

    with open(p) as f:
        d = json.load(f)
    return MarginArtifacts(
        intercept=float(d.get("intercept", 0.0)),
        coef={k: float(v) for k, v in (d.get("coef", {}) or {}).items()},
    )


def predict_margin(
    feats: MatchupFeatures,
    *,
    artifacts: Optional[MarginArtifacts] = None,
    safety_clamp: float = 24.0,
) -> Dict[str, Any]:
    a = artifacts or DEFAULT_ARTIFACTS
    x = feats.to_dict()
    raw = float(a.intercept) + sum(float(a.coef.get(k, 0.0)) * float(x.get(k, 0.0)) for k in a.coef.keys())
    clamped = max(-safety_clamp, min(safety_clamp, raw))
    return {
        "predicted_margin": float(clamped),
        "unclamped_margin": float(raw),
        "clamped": bool(raw != clamped),
    }

