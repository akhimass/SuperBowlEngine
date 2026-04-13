"""
GridironIQ reports package: Python-native reporting layer for matchup and situational analysis.

Modules:
- report_assets: output paths and naming for report visuals
- situational: situational bucketing, run/pass tendency, success rate, offense vs defense
- heatmaps: run/pass and success heatmaps, matchup heatmaps, run direction, QB passing
- matchup_report: full matchup report (engine + situational + assets)
- broadcast_report: media-friendly headline and talking points
- presentation_report: slide-friendly bullets and key edges
- models / ai_content / renderer: draft room PDF reports (WeasyPrint + Jinja2)
"""

from . import report_assets
from . import situational
from . import heatmaps
from . import matchup_report
from . import broadcast_report
from . import presentation_report

__all__ = [
    "report_assets",
    "situational",
    "heatmaps",
    "matchup_report",
    "broadcast_report",
    "presentation_report",
]
