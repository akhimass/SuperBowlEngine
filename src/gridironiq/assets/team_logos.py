"""
Team logo mapping: normalize filename stems and map to NFL team abbreviations.

Filename pattern: {city_and_team_name}_{suffix}.png (suffix often numeric or primary-YYYY).
Multi-word cities/teams use underscores; trailing numeric suffix is ignored for matching.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Normalized stem (lowercase, underscores) -> standard NFL abbreviation
TEAM_NAME_TO_ABBR: Dict[str, str] = {
    "arizona_cardinals": "ARI",
    "atlanta_falcons": "ATL",
    "baltimore_ravens": "BAL",
    "buffalo_bills": "BUF",
    "carolina_panthers": "CAR",
    "chicago_bears": "CHI",
    "cincinnati_bengals": "CIN",
    "cleveland_browns": "CLE",
    "dallas_cowboys": "DAL",
    "denver_broncos": "DEN",
    "detroit_lions": "DET",
    "green_bay_packers": "GB",
    "houston_texans": "HOU",
    "indianapolis_colts": "IND",
    "jacksonville_jaguars": "JAX",
    "kansas_city_chiefs": "KC",
    "las_vegas_raiders": "LV",
    "los_angeles_chargers": "LAC",
    "los_angeles_rams": "LA",
    "miami_dolphins": "MIA",
    "minnesota_vikings": "MIN",
    "new_england_patriots": "NE",
    "new_orleans_saints": "NO",
    "new_york_giants": "NYG",
    "new_york_jets": "NYJ",
    "philadelphia_eagles": "PHI",
    "pittsburgh_steelers": "PIT",
    "san_francisco_49ers": "SF",
    "seattle_seahawks": "SEA",
    "tampa_bay_buccaneers": "TB",
    "tennessee_titans": "TEN",
    "washington_commanders": "WAS",
}

# Abbreviation -> display name
ABBR_TO_DISPLAY_NAME: Dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

# Allowed image extensions
LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}


def normalize_logo_stem(filename: str) -> str:
    """
    Strip extension and remove trailing _<digits> from the stem.

    Example: san_francisco_49ers_456.png -> san_francisco_49ers
    """
    stem = Path(filename).stem
    stem = stem.lower().replace("-", "_")
    # Remove trailing _<digits> (one or more segments that are only digits)
    while True:
        m = re.match(r"^(.+)_(\d+)$", stem)
        if not m:
            break
        stem = m.group(1)
    return stem


def _stem_to_normalized_name(stem: str) -> str | None:
    """
    Map a full filename stem (after lower, - -> _) to a known normalized team name.
    Uses longest-prefix match so "san_francisco_49ers_primary_2009" -> san_francisco_49ers.
    """
    s = stem.lower().replace("-", "_")
    # Sort by length descending so we match longest first
    for key in sorted(TEAM_NAME_TO_ABBR.keys(), key=len, reverse=True):
        if s == key or s.startswith(key + "_"):
            return key
    return None


def scan_team_logo_dir(teamlogo_dir: str | Path) -> Dict[str, Any]:
    """
    Scan directory for logo files; map to abbreviations; return manifest-shaped dict.

    Returns:
        {
          "teams": { "GB": { "abbr", "display_name", "normalized_name", "filename", "path" }, ... },
          "unmatched": [ "filename1", ... ],
          "duplicates": { "GB": ["file1.png", "file2.png"] }  # only if multiple files matched same team
        }
    """
    teamlogo_dir = Path(teamlogo_dir)
    if not teamlogo_dir.is_dir():
        return {"teams": {}, "unmatched": [], "duplicates": {}}

    # Collect by normalized team name -> list of (filename, stem)
    by_team: Dict[str, List[tuple[str, str]]] = {}
    unmatched: List[str] = []

    for p in sorted(teamlogo_dir.iterdir()):
        if not p.is_file() or p.suffix.lower() not in LOGO_EXTENSIONS:
            continue
        if p.name.startswith("."):
            continue
        stem_full = p.stem.lower().replace("-", "_")
        normalized = _stem_to_normalized_name(stem_full)
        if normalized is None:
            unmatched.append(p.name)
            continue
        abbr = TEAM_NAME_TO_ABBR[normalized]
        by_team.setdefault(abbr, []).append((p.name, normalized))

    # Build teams dict: for each team, pick first alphabetical filename; record duplicates
    teams: Dict[str, Dict[str, Any]] = {}
    duplicates: Dict[str, List[str]] = {}

    for abbr in sorted(by_team.keys()):
        files = by_team[abbr]
        files.sort(key=lambda x: x[0])
        chosen_name = files[0][1]
        chosen_file = files[0][0]
        if len(files) > 1:
            duplicates[abbr] = [f[0] for f in files]
            logger.warning("Multiple logos for %s: using first alphabetically %r; others %r", abbr, chosen_file, [f[0] for f in files[1:]])
        path_str = f"teamlogo/{chosen_file}"
        teams[abbr] = {
            "abbr": abbr,
            "display_name": ABBR_TO_DISPLAY_NAME.get(abbr, abbr),
            "normalized_name": chosen_name,
            "filename": chosen_file,
            "path": path_str,
        }

    return {"teams": teams, "unmatched": unmatched, "duplicates": duplicates}


def write_logo_manifest(teamlogo_dir: str | Path, outpath: str | Path) -> Dict[str, Any]:
    """
    Scan teamlogo_dir, write JSON manifest to outpath, return the same dict.

    Frontend-facing paths use /teamlogo/... so the app can serve static files from there.
    """
    data = scan_team_logo_dir(teamlogo_dir)
    # Option: write paths with leading slash for frontend
    teams_with_slash_path = {}
    for abbr, info in data["teams"].items():
        info_copy = dict(info)
        info_copy["path"] = "/" + info_copy["path"].replace("\\", "/")
        teams_with_slash_path[abbr] = info_copy
    payload = {
        "teams": teams_with_slash_path,
        "unmatched": data["unmatched"],
        "duplicates": data["duplicates"],
    }
    outpath = Path(outpath)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload
