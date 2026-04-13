"""
Centralized output paths and naming for GridironIQ report assets.

All generated visuals (heatmaps, matchup charts) use this module so the
frontend and API can reference assets by deterministic paths.
"""

from pathlib import Path
from typing import List, Optional

# Default base directory for report outputs (relative to repo root or cwd)
DEFAULT_OUTPUTS_DIR = Path("outputs")
REPORTS_SUBDIR = "reports"


def reports_dir(base: Optional[Path] = None) -> Path:
    """Directory for report-generated assets (heatmaps, matchup images)."""
    root = base or Path.cwd()
    out = root / DEFAULT_OUTPUTS_DIR / REPORTS_SUBDIR
    out.mkdir(parents=True, exist_ok=True)
    return out


def run_pass_heatmap_path(team: str, season: int, kind: str = "run") -> Path:
    """Path for run or pass tendency heatmap PNG. kind in ('run', 'pass')."""
    return reports_dir() / f"heatmap_{kind}_{team}_{season}.png"


def success_rank_heatmap_path(team: str, season: int) -> Path:
    """Path for success rank heatmap PNG."""
    return reports_dir() / f"heatmap_success_rank_{team}_{season}.png"


def run_direction_path(team: str, season: int) -> Path:
    """Path for run direction chart PNG."""
    return reports_dir() / f"run_direction_{team}_{season}.png"


def qb_passing_heatmap_path(qb_label: str, team: str, opponent: str, season: int) -> Path:
    """Path for QB passing heatmap PNG. qb_label should be filesystem-safe."""
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in qb_label).strip()[:40]
    return reports_dir() / f"qb_passing_{safe}_{team}_vs_{opponent}_{season}.png"


def matchup_heatmap_path(team_a: str, team_b: str, season: int, week: Optional[int] = None) -> Path:
    """Path for offense-vs-defense or matchup heatmap PNG."""
    w = f"_w{week}" if week is not None else ""
    return reports_dir() / f"matchup_{team_a}_vs_{team_b}_{season}{w}.png"


def broadcast_report_path(team_a: str, team_b: str, season: int) -> Path:
    """Path for broadcast-style report PNG (optional export)."""
    return reports_dir() / f"broadcast_{team_a}_vs_{team_b}_{season}.png"


def presentation_report_path(team_a: str, team_b: str, season: int) -> Path:
    """Path for presentation-style report PNG (optional export)."""
    return reports_dir() / f"presentation_{team_a}_vs_{team_b}_{season}.png"


def list_report_assets(team_a: Optional[str] = None, team_b: Optional[str] = None, season: Optional[int] = None) -> List[str]:
    """List relative paths of report assets under reports_dir(), optionally filtered."""
    base = reports_dir()
    if not base.exists():
        return []
    paths: List[str] = []
    for p in base.iterdir():
        if not p.is_file():
            continue
        name = p.name
        if team_a and team_a not in name:
            continue
        if team_b and team_b not in name:
            continue
        if season is not None and str(season) not in name:
            continue
        paths.append(f"{REPORTS_SUBDIR}/{name}")
    return sorted(paths)
