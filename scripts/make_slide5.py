"""
Generate Slide 5 prediction PNG.
Uses predictor output if available (e.g. from a prior run), otherwise a sample pred dict.
Run from repo root: python scripts/make_slide5.py
"""

import json
import sys
from pathlib import Path

# Ensure package is on path
repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

from superbowlengine.viz.slide5 import render_slide5_prediction

OUTPUT_PATH = "outputs/slide5_prediction.png"

# Sample pred matching the schema (used if no saved output exists)
SAMPLE_PRED = {
    "p_sea_win": 0.62,
    "p_ne_win": 0.38,
    "predicted_winner": "SEA",
    "keys_won": {"SEA": 4, "NE": 1},
    "key_winners": {"TOP": "SEA", "TO": "SEA", "BIG": "SEA", "3D": "NE", "RZ": "SEA"},
}


def load_pred_if_available() -> dict:
    """Try to load prediction from outputs or a known path."""
    candidates = [
        repo / "outputs" / "prediction.json",
        repo / "outputs" / "pred.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
    return SAMPLE_PRED


def main() -> None:
    pred = load_pred_if_available()
    outpath = repo / OUTPUT_PATH
    saved = render_slide5_prediction(pred, outpath=str(outpath))
    print("Saved:", saved)


if __name__ == "__main__":
    main()
