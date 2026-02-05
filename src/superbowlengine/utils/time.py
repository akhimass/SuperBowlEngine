"""Time utilities for drive TOP and similar fields."""

from typing import Union

import pandas as pd


def mmss_to_seconds(mmss: Union[str, float, pd.NA]) -> int:
    """
    Convert drive_time_of_possession "MM:SS" string to total seconds.
    Handles NaN and invalid formats.
    """
    if pd.isna(mmss):
        return 0
    parts = str(mmss).strip().split(":")
    if len(parts) != 2:
        return 0
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, TypeError):
        return 0
