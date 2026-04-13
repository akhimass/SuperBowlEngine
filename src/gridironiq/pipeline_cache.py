from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
PRED_DIR = BASE_DIR / "outputs" / "schedule_predictions"
REPORT_DIR = BASE_DIR / "outputs" / "schedule_reports"


def _ensure_dirs() -> None:
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def schedule_pred_path(season: int, phase: str) -> Path:
    _ensure_dirs()
    return PRED_DIR / f"{season}_{phase}.json"


def game_report_path(season: int, game_id: str) -> Path:
    _ensure_dirs()
    safe = game_id.replace("/", "_")
    season_dir = REPORT_DIR / str(season)
    season_dir.mkdir(parents=True, exist_ok=True)
    return season_dir / f"{safe}.json"


def load_schedule_predictions(season: int, phase: str) -> Optional[List[Dict[str, Any]]]:
    path = schedule_pred_path(season, phase)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_schedule_predictions(season: int, phase: str, games: List[Dict[str, Any]]) -> Path:
    path = schedule_pred_path(season, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = [_json_serializable(g) for g in games]
    with path.open("w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    return path


def load_game_report_cached(season: int, game_id: str) -> Optional[Dict[str, Any]]:
    path = game_report_path(season, game_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _json_serializable(obj: Any) -> Any:
    """Recursively convert numpy/pandas scalars to native Python for json.dump."""
    if isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_serializable(v) for v in obj]
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if pd.isna(obj):
        return None
    return obj


def save_game_report_cached(season: int, game_id: str, report: Dict[str, Any]) -> Path:
    path = game_report_path(season, game_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = _json_serializable(report)
    with path.open("w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)
    return path

