"""NFL draft intelligence: prospect grades, team needs, scheme fit, simulation, recommendations."""

from typing import Any

__all__ = ["build_draft_board"]


def __getattr__(name: str) -> Any:
    if name == "build_draft_board":
        from .pipeline import build_draft_board

        return build_draft_board
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
