from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split

from gridironiq.models.training_data import FEATURE_COLS


@dataclass(frozen=True)
class WinProbFitResult:
    intercept: float
    coef: Dict[str, float]
    feature_cols: List[str]
    metrics: Dict[str, Any]


def fit_win_prob_model(df: pd.DataFrame, *, calibrate: bool = True, random_state: int = 7) -> WinProbFitResult:
    data = df.dropna(subset=["win_target"]).copy()
    X = data[FEATURE_COLS].astype(float).values
    y = data["win_target"].astype(int).values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=random_state, stratify=y)

    base = LogisticRegression(max_iter=2000, C=1.0, solver="lbfgs")
    if calibrate:
        clf = CalibratedClassifierCV(base, method="isotonic", cv=3)
        clf.fit(X_train, y_train)
        # For interpretability artifacts, store base LR coefficients (pre-calibration) as a reasonable approximation.
        base.fit(X_train, y_train)
        intercept = float(base.intercept_[0])
        coef = {FEATURE_COLS[i]: float(base.coef_[0, i]) for i in range(len(FEATURE_COLS))}
        proba = clf.predict_proba(X_test)[:, 1]
    else:
        base.fit(X_train, y_train)
        intercept = float(base.intercept_[0])
        coef = {FEATURE_COLS[i]: float(base.coef_[0, i]) for i in range(len(FEATURE_COLS))}
        proba = base.predict_proba(X_test)[:, 1]

    preds = (proba >= 0.5).astype(int)
    metrics = {
        "n_rows": int(len(data)),
        "log_loss": float(log_loss(y_test, proba)),
        "brier": float(brier_score_loss(y_test, proba)),
        "accuracy": float(accuracy_score(y_test, preds)),
        "p_mean": float(np.mean(proba)),
        "p_min": float(np.min(proba)),
        "p_max": float(np.max(proba)),
        "calibrated": bool(calibrate),
    }
    return WinProbFitResult(intercept=intercept, coef=coef, feature_cols=list(FEATURE_COLS), metrics=metrics)


def save_win_prob_artifact(fit: WinProbFitResult, path: str = "outputs/model_artifacts/win_prob_model.json") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "intercept": fit.intercept,
        "coef": fit.coef,
        "feature_cols": fit.feature_cols,
        "metrics": fit.metrics,
    }
    with p.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return p

