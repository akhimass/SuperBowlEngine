"""
Slide 5: Super Bowl prediction visualization.
Produces a single PNG with win probability bars and a keys-won summary line.
"""

from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt

# Canonical key order for the summary line
KEY_ORDER = ["TOP", "TO", "BIG", "3D", "RZ"]

# Team primary colors (hex) for bar fills
TEAM_COLORS: Dict[str, str] = {
    "SEA": "#69BE28",   # Seattle Seahawks green
    "NE": "#C60C30",    # New England Patriots red
    "SF": "#AA0000",    # 49ers red
    "KC": "#E31837",    # Chiefs red
}
DEFAULT_COLOR_A = "#69BE28"  # green fallback
DEFAULT_COLOR_B = "#C60C30"  # red fallback


def _summary_line(pred: Dict[str, Any]) -> str:
    """Build summary: '{winner} wins {n}/5 keys (key1, key2, ...)' in KEY_ORDER."""
    winner = pred.get("predicted_winner", "SEA")
    key_winners = pred.get("key_winners") or {}
    keys_won_by_winner = [k for k in KEY_ORDER if key_winners.get(k) == winner]
    n = len(keys_won_by_winner)
    if not keys_won_by_winner:
        return f"{winner} wins {n}/5 keys"
    return f"{winner} wins {n}/5 keys ({', '.join(keys_won_by_winner)})"


def _probs_from_pred(pred: Dict[str, Any]) -> tuple[float, float, str, str]:
    """Get (p_a, p_b, label_a, label_b) for the two teams (SEA/NE or team_a/team_b)."""
    if "p_sea_win" in pred and "p_ne_win" in pred:
        return pred["p_sea_win"], pred["p_ne_win"], "SEA", "NE"
    p_a = pred.get("p_team_a_win", 0.5)
    p_b = pred.get("p_team_b_win", 0.5)
    keys_won = pred.get("keys_won") or {}
    names = list(keys_won.keys())
    if len(names) >= 2:
        return p_a, p_b, names[0], names[1]
    return p_a, p_b, "Team A", "Team B"


def render_slide5_prediction(
    pred: Dict[str, Any],
    outpath: str = "outputs/slide5_prediction.png",
) -> str:
    """
    Render a slide-ready PNG: title, horizontal win-probability bars, summary line.
    pred must contain win probabilities, predicted_winner, keys_won, key_winners.
    Creates the output directory if missing. Returns the absolute path saved.
    """
    path = Path(outpath)
    path.parent.mkdir(parents=True, exist_ok=True)

    p_a, p_b, label_a, label_b = _probs_from_pred(pred)
    summary = _summary_line(pred)

    color_a = TEAM_COLORS.get(str(label_a).upper(), DEFAULT_COLOR_A)
    color_b = TEAM_COLORS.get(str(label_b).upper(), DEFAULT_COLOR_B)

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.6, 1.4)

    # Two horizontal bars: team primary colors (Seattle green, NE red, etc.)
    y_a, y_b = 0.6, 0.2
    bar_height = 0.25
    ax.barh(y_a, p_a, height=bar_height, label=label_a, align="center", color=color_a)
    ax.barh(y_b, p_b, height=bar_height, label=label_b, align="center", color=color_b)

    # Probability labels: 1 decimal %; inside bar if wide enough, else outside
    def add_label(p: float, y: float) -> None:
        txt = f"{p * 100:.1f}%"
        if p >= 0.2:
            ax.text(p / 2, y, txt, ha="center", va="center", fontsize=12, fontweight="bold", color="white")
        else:
            ax.text(p + 0.02, y, txt, ha="left", va="center", fontsize=11, fontweight="bold")
    add_label(p_a, y_a)
    add_label(p_b, y_b)

    ax.set_xlabel("Win probability")
    ax.set_yticks([y_a, y_b])
    ax.set_yticklabels([label_a, label_b], fontsize=11)
    ax.set_title("Super Bowl LX Prediction", fontsize=14, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Summary line below the chart
    fig.text(0.5, 0.02, summary, ha="center", va="bottom", fontsize=12, fontweight="bold", wrap=True)

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return str(path.resolve())
