"""DGI model (placeholder for future extension)."""

from typing import Any, Dict, Optional

import pandas as pd

from superbowlengine.features.keys import TeamKeys


def predict_dgi(
    _team_a_keys: TeamKeys,
    _team_b_keys: TeamKeys,
    _pbp: Optional["pd.DataFrame"] = None,
) -> Dict[str, Any]:
    """
    Placeholder: DGI or other advanced model.
    """
    return {"predicted_winner": None, "scores": {}}
