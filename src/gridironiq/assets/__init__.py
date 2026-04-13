"""
GridironIQ assets: team logo manifest and helpers.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .team_logos import (
    ABBR_TO_DISPLAY_NAME,
    TEAM_NAME_TO_ABBR,
    scan_team_logo_dir,
    write_logo_manifest,
)

__all__ = [
    "ABBR_TO_DISPLAY_NAME",
    "TEAM_NAME_TO_ABBR",
    "load_logo_manifest",
    "get_team_logo",
    "scan_team_logo_dir",
    "write_logo_manifest",
]

# Default path relative to project root (or cwd)
DEFAULT_MANIFEST_PATH = Path("outputs/team_logo_manifest.json")


def load_logo_manifest(path: str | Path = DEFAULT_MANIFEST_PATH) -> Dict[str, Any]:
    """
    Load the team logo manifest JSON. Returns dict with "teams", "unmatched", "duplicates".

    If the file does not exist, returns {"teams": {}, "unmatched": [], "duplicates": {}}.
    """
    path = Path(path)
    if not path.is_file():
        return {"teams": {}, "unmatched": [], "duplicates": {}}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Some data sources use LAR for Rams; manifest uses LA
_ABBR_ALIAS: Dict[str, str] = {"LAR": "LA"}


def get_team_logo(team_abbr: str, manifest: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Return the logo path for a team abbreviation (e.g. "GB" -> "/teamlogo/green_bay_packers_3191.png").

    If manifest is None, loads from default path (outputs/team_logo_manifest.json).
    Returns None if team not found or manifest not loaded.
    """
    if manifest is None:
        manifest = load_logo_manifest()
    teams = manifest.get("teams") or {}
    abbr = team_abbr.upper()
    info = teams.get(abbr) or teams.get(_ABBR_ALIAS.get(abbr, ""))
    if info is None:
        return None
    return info.get("path")
