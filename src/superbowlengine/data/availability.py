"""
Data availability / readiness for 5 Keys pipeline.

Assesses whether the currently loaded PBP has the columns required to compute
each of the 5 Keys (TOP, Turnovers, Big Plays, 3rd Down, Red Zone). Used by
the Streamlit app and any other UI that needs a readiness badge.
"""

from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

# Column requirements per key (aligned with data/load.py validators)
_KEY_GROUPS = {
    "TOP": ["drive", "drive_time_of_possession", "game_id"],
    "Turnovers": ["interception", "fumble_lost"],
    "Big Plays": ["play_type", "yards_gained"],
    "3rd Down": ["down", "ydstogo"],  # plus first_down OR yards_gained
    "Red Zone": ["yardline_100", "drive", "game_id", "touchdown"],
}


@dataclass
class KeyAvailability:
    """Whether a single key can be computed and which columns are missing."""

    ok: bool
    missing: List[str]


@dataclass
class AvailabilityReport:
    """Overall data readiness for the 5 Keys pipeline."""

    overall_status: str  # "GREEN" | "YELLOW" | "RED"
    ok_keys: List[str]
    missing_by_key: Dict[str, List[str]]
    notes: List[str]


def _check_third_down(cols: List[str]) -> KeyAvailability:
    """3rd Down requires down, ydstogo, and (first_down OR yards_gained)."""
    base = _KEY_GROUPS["3rd Down"]
    missing_base = [c for c in base if c not in cols]
    if missing_base:
        return KeyAvailability(ok=False, missing=missing_base)
    if "first_down" in cols or "yards_gained" in cols:
        return KeyAvailability(ok=True, missing=[])
    return KeyAvailability(ok=False, missing=["first_down OR yards_gained"])


def assess_5keys_availability(pbp: pd.DataFrame) -> AvailabilityReport:
    """
    Assess whether the given PBP DataFrame has the columns needed to compute all 5 Keys.

    Returns an AvailabilityReport with overall_status (GREEN=all keys OK,
    YELLOW=some keys missing, RED=no data or critical missing), ok_keys,
    missing_by_key, and notes for the UI.
    """
    notes: List[str] = []
    missing_by_key: Dict[str, List[str]] = {}
    ok_keys: List[str] = []

    if pbp is None or pbp.empty:
        return AvailabilityReport(
            overall_status="RED",
            ok_keys=[],
            missing_by_key={k: v for k, v in _KEY_GROUPS.items()},
            notes=["No PBP data loaded."],
        )

    cols = list(pbp.columns)

    for key_name, required in _KEY_GROUPS.items():
        if key_name == "3rd Down":
            ka = _check_third_down(cols)
        else:
            missing = [c for c in required if c not in cols]
            ka = KeyAvailability(ok=len(missing) == 0, missing=missing)
        missing_by_key[key_name] = ka.missing
        if ka.ok:
            ok_keys.append(key_name)

    # Overall status
    n_ok = len(ok_keys)
    if n_ok == 5:
        overall_status = "GREEN"
        notes.append("All 5 Keys can be computed.")
    elif n_ok >= 1:
        overall_status = "YELLOW"
        missing_keys = [k for k in _KEY_GROUPS if k not in ok_keys]
        notes.append("Missing columns for: %s." % ", ".join(missing_keys))
    else:
        overall_status = "RED"
        notes.append("Cannot compute any key; add COLUMN_ALIASES in data/load.py if names differ.")

    return AvailabilityReport(
        overall_status=overall_status,
        ok_keys=ok_keys,
        missing_by_key=missing_by_key,
        notes=notes,
    )
