from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split

from gridironiq.models.training_data import FEATURE_COLS


@dataclass(frozen=True)
class TotalFitResult:
    intercept: float
    coef: Dict[str, float]
    feature_cols: List[str]
    metrics: Dict[str, Any]


def fit_total_model(df: pd.DataFrame, *, alpha: float = 2.0, random_state: int = 7) -> TotalFitResult:
    data = df.dropna(subset=["total_target"]).copy()
    X = data[FEATURE_COLS].astype(float).values
    y = data["total_target"].astype(float).values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=random_state)
    model = Ridge(alpha=alpha)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, pred)))
    metrics = {
        "n_rows": int(len(data)),
        "mae": float(mean_absolute_error(y_test, pred)),
        "rmse": rmse,
        "pred_min": float(np.min(pred)),
        "pred_max": float(np.max(pred)),
        "alpha": float(alpha),
    }
    coef = {FEATURE_COLS[i]: float(model.coef_[i]) for i in range(len(FEATURE_COLS))}
    return TotalFitResult(intercept=float(model.intercept_), coef=coef, feature_cols=list(FEATURE_COLS), metrics=metrics)


def save_total_artifact(fit: TotalFitResult, path: str = "outputs/model_artifacts/total_model.json") -> Path:
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

