"""QB production engine: metrics and 0–100 production score from postseason stats."""

from superbowlengine.qb.model import (
    QBLine,
    compute_qb_metrics,
    qb_line_from_pbp,
    qb_production_score,
)
from superbowlengine.qb.production import (
    QBProdConfig,
    compute_opponent_def_strength,
    qb_production_components,
    qb_turnover_attribution,
)

__all__ = [
    "QBLine",
    "compute_qb_metrics",
    "qb_line_from_pbp",
    "qb_production_score",
    "QBProdConfig",
    "compute_opponent_def_strength",
    "qb_production_components",
    "qb_turnover_attribution",
]
