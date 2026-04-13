"""
GridironIQ backend package.

This package wraps the existing `superbowlengine` analytics into a more general
NFL matchup intelligence backend that can be served via FastAPI.

Implementation guideline for this phase:
- Do not modify core `superbowlengine` logic.
- Keep wrappers thin and focused on shaping inputs/outputs for the API.
"""

__all__ = [
    "matchup_engine",
    "qb_production_engine",
    "report_generator",
    "backtest_engine",
]

