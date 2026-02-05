#!/usr/bin/env python3
"""
Generate outputs/qb_compare.png: Maye vs Darnold QB production comparison.

Hardcoded stat lines for now; run from repo root.
"""

import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo / "src"))

from superbowlengine.qb.model import QBLine, compute_qb_metrics, qb_production_score
from superbowlengine.viz.qb_compare import render_qb_comparison

# Hardcoded postseason-style lines (Maye vs Darnold)
MAYE = QBLine(
    games=2,
    cmp=45,
    att=75,
    yds=480,
    td=3,
    int_=2,
    sacks=5,
    rush_att=8,
    rush_yds=25,
    rush_td=0,
    fumbles=0,
)
DARNOLD = QBLine(
    games=3,
    cmp=72,
    att=105,
    yds=820,
    td=6,
    int_=0,
    sacks=4,
    rush_att=12,
    rush_yds=55,
    rush_td=1,
    fumbles=0,
)

SUBTITLE = "Darnold: accuracy, YPA, INT=0, lower sack rate."


def main() -> None:
    metrics_maye = compute_qb_metrics(MAYE)
    metrics_darnold = compute_qb_metrics(DARNOLD)
    out_maye = qb_production_score(metrics_maye)
    out_darnold = qb_production_score(metrics_darnold)
    outpath = repo / "outputs" / "qb_compare.png"
    path = render_qb_comparison(
        "Maye",
        "Darnold",
        metrics_maye,
        metrics_darnold,
        out_maye["total"],
        out_darnold["total"],
        outpath=str(outpath),
        subtitle=SUBTITLE,
    )
    print("Saved:", path)


if __name__ == "__main__":
    main()
