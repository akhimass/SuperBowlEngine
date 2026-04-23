"""
Dual first-round classifiers per position: LogisticRegression (interpretable) + XGBoost (performance).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_lr_model(X_train: np.ndarray | pd.DataFrame, y_train: np.ndarray | pd.Series) -> Pipeline:
    pipe = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "lr",
                LogisticRegression(
                    C=0.5,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    pipe.fit(X_train, y_train)
    return pipe


def build_xgb_model(X_train: np.ndarray | pd.DataFrame, y_train: np.ndarray | pd.Series) -> Any:
    import xgboost as xgb

    y = np.asarray(y_train).astype(int).ravel()
    n_neg = int((y == 0).sum())
    n_pos = int((y == 1).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)

    # No early_stopping_rounds here: sklearn cross_val_score clones the estimator
    # and fits without eval_set, which breaks XGBoost 3.x early stopping.
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="auc",
        random_state=42,
    )

    X_tr, X_val, y_tr, y_val = train_test_split(
        X_train, y_train, test_size=0.15, random_state=42, stratify=y_train
    )
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)

    return model


def evaluate_model(model: Any, X: np.ndarray | pd.DataFrame, y: np.ndarray | pd.Series, label: str = "model") -> dict:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
    pr_scores = cross_val_score(model, X, y, cv=cv, scoring="average_precision")

    print(f"{label}:")
    print(f"  AUC:   {auc_scores.mean():.3f} ± {auc_scores.std():.3f}")
    print(f"  PRAUC: {pr_scores.mean():.3f} ± {pr_scores.std():.3f}")

    return {
        "auc_mean": float(auc_scores.mean()),
        "auc_std": float(auc_scores.std()),
        "prauc_mean": float(pr_scores.mean()),
        "prauc_std": float(pr_scores.std()),
    }


def get_feature_importance(
    lr_model: Pipeline,
    xgb_model: Any,
    feature_names: list[str],
    position: str,
) -> pd.DataFrame:
    coefs = lr_model.named_steps["lr"].coef_[0]
    lr_importance = pd.DataFrame(
        {
            "feature": feature_names,
            "lr_coef": coefs,
            "lr_abs": np.abs(coefs),
        }
    ).sort_values("lr_abs", ascending=False)

    xgb_importance = pd.DataFrame(
        {
            "feature": feature_names,
            "xgb_gain": xgb_model.feature_importances_,
        }
    ).sort_values("xgb_gain", ascending=False)

    merged = lr_importance.merge(xgb_importance, on="feature", how="outer")
    merged["rank_lr"] = merged["lr_abs"].rank(ascending=False, method="average")
    merged["rank_xgb"] = merged["xgb_gain"].rank(ascending=False, method="average")
    merged["avg_rank"] = (merged["rank_lr"] + merged["rank_xgb"]) / 2.0
    merged = merged.sort_values("avg_rank")

    print(f"\n=== {position} TOP FEATURES ===")
    show = merged[["feature", "lr_coef", "xgb_gain"]].head(8)
    print(show.to_string(index=False))

    return merged


def predict_first_round_prob(
    lr_model: Pipeline,
    xgb_model: Any,
    X_test: np.ndarray | pd.DataFrame,
    *,
    lr_weight: float = 0.40,
    xgb_weight: float = 0.60,
) -> np.ndarray:
    lr_probs = lr_model.predict_proba(X_test)[:, 1]
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
    return lr_weight * lr_probs + xgb_weight * xgb_probs
