"""
Ultra-compact QB Production Score strip for slide: 1200×180, dark background.

Rendered as a single-row analytic banner with a fixed 6‑column grid so
it drops cleanly under the QB breakdown section without drifting columns.
"""

from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt


def render_qb_prod_card(
    qb_a: str,
    qb_b: str,
    report_a: Dict[str, float],
    report_b: Dict[str, float],
    outpath: str = "outputs/qb_prod_card.png",
) -> str:
    """
    Skinny horizontal stat strip (6 columns) with fixed edges/centers.
    Winner coloring based on Production Score.
    """
    path = Path(outpath)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 1200×180 banner
    fig = plt.figure(figsize=(12, 1.8), dpi=100)
    fig.patch.set_facecolor("#1a1a2e")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor("#1a1a2e")

    # Title (small, not dominating vertical space)
    ax.text(
        0.5,
        0.93,
        "QB Production Score (Postseason Impact Index)",
        ha="center",
        va="top",
        fontsize=13,
        color="#e0e0e0",
        fontweight="bold",
    )

    # Headers first; column edges must have len(headers)+1 so we have one center per header.
    # 6 columns: QB | Drive | Situational | Off-Script | Production Score | Defense Strength Faced
    headers = [
        "QB",
        "Drive\nSustain",
        "Situational",
        "Off-Script",
        "Production\nScore",
        "Defense Strength\nFaced (z)",
    ]
    n_cols = len(headers)
    # Fixed grid: 7 edges => 6 columns, biased a bit wider for Production Score + Defense Strength.
    col_edges: List[float] = [0.02, 0.20, 0.34, 0.48, 0.68, 0.84, 0.98]
    if len(col_edges) != n_cols + 1:
        # Fallback: evenly spaced edges so centers never out of range
        col_edges = [0.03 + (0.96 * i / n_cols) for i in range(n_cols + 1)]
    centers = [(col_edges[i] + col_edges[i + 1]) / 2 for i in range(n_cols)]

    # Row y positions (compact vertical stack)
    y_header = 0.72
    y_a = 0.48
    y_b = 0.24
    y_top = 0.80
    y_bottom = 0.10

    # Divider lines: table border + vertical column separators + header baseline
    for x in col_edges[1:-1]:
        ax.plot([x, x], [y_bottom, y_top], color="#ffffff", linewidth=1.0, alpha=0.35)
    # Top and bottom borders
    ax.plot([col_edges[0], col_edges[-1]], [y_top, y_top], color="#ffffff", linewidth=1.2, alpha=0.40)
    ax.plot([col_edges[0], col_edges[-1]], [y_bottom, y_bottom], color="#ffffff", linewidth=1.2, alpha=0.40)
    # Header underline
    ax.plot([col_edges[0], col_edges[-1]], [0.64, 0.64], color="#ffffff", linewidth=1.0, alpha=0.35)

    # Header row
    for i, h in enumerate(headers):
        ax.text(
            centers[i],
            y_header,
            h,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="#cfcfcf",
            linespacing=0.9,
        )

    # Winner coloring based on production_score
    score_a = float(report_a.get("production_score", 0) or 0)
    score_b = float(report_b.get("production_score", 0) or 0)
    win_color = "#7bc96f"
    lose_color = "#e57373"
    score_color_a = win_color if score_a >= score_b else lose_color
    score_color_b = win_color if score_b > score_a else lose_color

    # QB names (left aligned in first column)
    ax.text(col_edges[0] + 0.01, y_a, qb_a, ha="left", va="center", fontsize=16, fontweight="bold", color="#ffffff")
    ax.text(col_edges[0] + 0.01, y_b, qb_b, ha="left", va="center", fontsize=16, fontweight="bold", color="#ffffff")

    # Numeric cells (centers)
    def _cell(v, default=0) -> str:
        try:
            return str(int(round(float(v))))
        except Exception:
            return str(default)

    # Subscores
    sub_a_color = "#6ab7ff"
    sub_b_color = "#ff8a6a"
    for idx, key in [(1, "drive_sustain"), (2, "situational"), (3, "offscript")]:
        ax.text(centers[idx], y_a, _cell(report_a.get(key, 0)), ha="center", va="center", fontsize=18, color=sub_a_color)
        ax.text(centers[idx], y_b, _cell(report_b.get(key, 0)), ha="center", va="center", fontsize=18, color=sub_b_color)

    # Production score (visual focal point)
    ax.text(
        centers[4],
        y_a,
        _cell(score_a),
        ha="center",
        va="center",
        fontsize=24,
        fontweight="bold",
        color=score_color_a,
    )
    ax.text(
        centers[4],
        y_b,
        _cell(score_b),
        ha="center",
        va="center",
        fontsize=24,
        fontweight="bold",
        color=score_color_b,
    )

    # Defense strength faced (z)
    ax.text(
        centers[5],
        y_a,
        f"{float(report_a.get('avg_def_z', 0) or 0):+.2f}",
        ha="center",
        va="center",
        fontsize=16,
        color="#e0e0e0",
    )
    ax.text(
        centers[5],
        y_b,
        f"{float(report_b.get('avg_def_z', 0) or 0):+.2f}",
        ha="center",
        va="center",
        fontsize=16,
        color="#e0e0e0",
    )

    # One-line bold footnote, kept minimal for slide readability
    ax.text(
        0.5,
        0.05,
        "Subscores are 0–100; Defense Strength Faced uses REG defensive EPA allowed (z).",
        ha="center",
        va="center",
        fontsize=9,
        color="#b0b0b0",
        fontweight="bold",
    )
    plt.savefig(path, dpi=150, bbox_inches="tight", pad_inches=0.15, facecolor="#1a1a2e", edgecolor="none")
    plt.close(fig)
    return str(path.resolve())
