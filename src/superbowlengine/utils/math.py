"""Math utilities for models (sigmoid, safe division)."""

import math


def sigmoid(x: float) -> float:
    """Logistic sigmoid: 1 / (1 + exp(-x))."""
    return 1.0 / (1.0 + math.exp(-x))


def safe_div(a: float, b: float) -> float:
    """Return a/b or 0.0 if b is zero."""
    return a / b if b else 0.0
