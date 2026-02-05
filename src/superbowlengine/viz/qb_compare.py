"""
Slide-ready QB comparison: two columns, key stats, production score, optional bar chart.
"""

from pathlib import Path
from typing import Dict, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


STAT_LABELS = {
    "comp_pct": "Comp %",
    "ypa": "YPA",
    "td_rate": "TD rate",
    "int_rate": "INT rate",
    "sack_rate": "Sack rate",
    "rush_ypc": "Rush YPC",
    "rush_td_pg": "Rush TD/g",
    "turnover_rate_pg": "TO/g",
}


def render_qb_comparison(
    qb_a_name: str,
    qb_b_name: str,
    metrics_a: Dict[str, float],
    metrics_b: Dict[str, float],
    score_a: float,
    score_b: float,
    outpath: str = "outputs/qb_compare.png",
    subtitle: Optional[str] = None,
    stat_keys: Optional[list] = None,
) -> str:
    """
    Render a two-column QB comparison PNG: key stats + Production Score each, optional bar chart.

    subtitle: e.g. "Darnold: accuracy, YPA, INT=0, sack rate."
    """
    path = Path(outpath)
    path.parent.mkdir(parents=True, exist_ok=True)
    stat_keys = stat_keys or ["comp_pct", "ypa", "td_rate", "int_rate", "sack_rate", "rush_ypc", "turnover_rate_pg"]
    fig = plt.figure(figsize=(12, 8), dpi=150)
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(2, 2, left=0.08, right=0.92, top=0.88, bottom=0.12, wspace=0.35, hspace=0.4)
    # Title
    ax_title = fig.add_subplot(gs[0, :])
    ax_title.axis("off")
    ax_title.text(0.5, 0.7, "QB Production Comparison (Postseason)", ha="center", va="center", fontsize=28, fontweight="bold", transform=ax_title.transAxes)
    if subtitle:
        ax_title.text(0.5, 0.35, subtitle, ha="center", va="center", fontsize=16, transform=ax_title.transAxes)
    # Left: QB A
    ax_a = fig.add_subplot(gs[1, 0])
    ax_a.set_xlim(0, 1)
    ax_a.set_ylim(0, 1)
    ax_a.axis("off")
    _draw_qb_column(ax_a, qb_a_name, metrics_a, score_a, stat_keys, "#1a5276")
    # Right: QB B
    ax_b = fig.add_subplot(gs[1, 1])
    ax_b.set_xlim(0, 1)
    ax_b.set_ylim(0, 1)
    ax_b.axis("off")
    _draw_qb_column(ax_b, qb_b_name, metrics_b, score_b, stat_keys, "#922b21")
    # Small bar chart: Production Score A vs B
    ax_bar = fig.add_axes([0.25, 0.02, 0.5, 0.08])
    ax_bar.barh([0], [score_a], height=0.4, color="#1a5276", label=qb_a_name)
    ax_bar.barh([0.5], [score_b], height=0.4, color="#922b21", label=qb_b_name)
    ax_bar.set_yticks([0, 0.5])
    ax_bar.set_yticklabels([qb_a_name, qb_b_name], fontsize=12)
    ax_bar.set_xlim(0, 100)
    ax_bar.set_xlabel("Production Score", fontsize=11)
    ax_bar.legend(loc="upper right", fontsize=9)
    ax_bar.spines["top"].set_visible(False)
    ax_bar.spines["right"].set_visible(False)
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path.resolve())


def _draw_qb_column(
    ax: plt.Axes,
    name: str,
    metrics: Dict[str, float],
    score: float,
    stat_keys: list,
    color: str,
) -> None:
    patch = mpatches.FancyBboxPatch(
        (0.02, 0.02), 0.96, 0.96,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        facecolor="#fafafa", edgecolor=color, linewidth=2,
        transform=ax.transAxes,
    )
    ax.add_patch(patch)
    ax.text(0.5, 0.92, name, ha="center", va="top", fontsize=22, fontweight="bold", color=color, transform=ax.transAxes)
    ax.text(0.5, 0.78, f"Production Score: {score:.1f}", ha="center", va="top", fontsize=20, fontweight="bold", transform=ax.transAxes)
    y = 0.66
    for k in stat_keys:
        if k not in metrics:
            continue
        val = metrics[k]
        if "pct" in k or "rate" in k:
            s = f"{STAT_LABELS.get(k, k)}: {val:.1f}%"
        elif "pg" in k:
            s = f"{STAT_LABELS.get(k, k)}: {val:.2f}"
        else:
            s = f"{STAT_LABELS.get(k, k)}: {val:.2f}"
        ax.text(0.5, y, s, ha="center", va="top", fontsize=14, transform=ax.transAxes)
        y -= 0.08
