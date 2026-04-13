from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import math
import os

from gridironiq.models.matchup_features import MatchupFeatures


def _sigmoid(x: float) -> float:
    # Stable sigmoid
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


@dataclass(frozen=True)
class WinProbArtifacts:
    intercept: float
    coef: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


DEFAULT_ARTIFACTS = WinProbArtifacts(
    # Conservative intercept: slightly favors 50/50 prior.
    intercept=0.0,
    # Coefficients are tuned to keep probabilities reasonable from common ranges:
    # - epa_edge typically ~ [-0.3, 0.3]
    # - success_edge typically ~ [-0.15, 0.15]
    # - explosive_edge typically ~ [-0.08, 0.08]
    # - situational edges smaller
    coef={
        "epa_edge": 5.0,
        "success_edge": 3.0,
        "explosive_edge": 2.0,
        "early_down_success_edge": 1.5,
        "third_down_edge": 1.0,
        "redzone_edge": 1.0,
        "sack_edge": 1.0,
        "sos_edge": 0.4,
        "recent_epa_edge": 1.5,
    },
)


def _artifact_path(filename: str) -> Path:
    base = os.getenv("GRIDIRONIQ_MODEL_ARTIFACT_DIR", "outputs/model_artifacts")
    return Path(base) / filename


def load_artifacts(path: Optional[str] = None) -> Optional[WinProbArtifacts]:
    p = Path(path) if path else _artifact_path("win_prob_model.json")
    if not p.exists():
        return None
    import json

    with open(p) as f:
        d = json.load(f)
    return WinProbArtifacts(
        intercept=float(d.get("intercept", 0.0)),
        coef={k: float(v) for k, v in (d.get("coef", {}) or {}).items()},
    )


def predict_win_probability(
    feats: MatchupFeatures,
    *,
    artifacts: Optional[WinProbArtifacts] = None,
    clip_low: float = 0.03,
    clip_high: float = 0.97,
) -> Dict[str, Any]:
    a = artifacts or DEFAULT_ARTIFACTS
    # Linear logit
    x = feats.to_dict()
    logit = float(a.intercept)
    for k, w in a.coef.items():
        logit += w * float(x.get(k, 0.0))
    p = _sigmoid(logit)
    # Soft clip to avoid 0/1 unless extreme. This is not a "patch"; it is a calibration safety rail.
    p_clipped = max(clip_low, min(clip_high, p))
    return {
        "win_probability": float(p_clipped),
        "unclipped_win_probability": float(p),
        "logit": float(logit),
        "clipped": bool(p != p_clipped),
    }

