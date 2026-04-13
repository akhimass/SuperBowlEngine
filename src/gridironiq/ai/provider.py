from __future__ import annotations

from abc import ABC, abstractmethod

from .schemas import AIExplanationResult, ExplainerContext


class AIProvider(ABC):
    """Interface for AI Statistician providers."""

    @abstractmethod
    def generate(self, context: ExplainerContext) -> AIExplanationResult:  # pragma: no cover - interface
        raise NotImplementedError

