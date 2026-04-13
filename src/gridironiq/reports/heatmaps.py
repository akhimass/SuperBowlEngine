"""
Heatmap rendering for GridironIQ reports (run/pass tendency, success rank, matchup).

Uses matplotlib; saves to outputs via report_assets.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from . import report_assets
from . import situational

logger = logging.getLogger(__name__)


def _ensure_reports_dir() -> Path:
    return report_assets.reports_dir()


def render_run_pass_heatmap(
    tendency_df: pd.DataFrame,
    team: str,
    season: int,
    kind: str = "run",
    *,
    save_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Render run or pass tendency heatmap (down/distance × field position).

    tendency_df: from situational.run_pass_tendency_by_situation (must have
      dist_bucket, field_pos_bucket, run_pct, pass_pct, run_success, pass_success).
    kind: 'run' or 'pass'.
    Returns metadata dict with path, caption, and data summary.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless / test-safe backend
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not available; skipping heatmap render")
        return {"path": None, "caption": f"{kind.title()} tendency heatmap (not rendered)", "error": "matplotlib not installed"}

    path = save_path or report_assets.run_pass_heatmap_path(team, season, kind)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Pivot: rows = dist_bucket, cols = field_pos_bucket, values = run_pct or pass_pct
    val_col = "run_pct" if kind == "run" else "pass_pct"
    if val_col not in tendency_df.columns or tendency_df.empty:
        return {"path": str(path), "caption": f"No {kind} tendency data", "error": "empty or missing column"}

    pivot = tendency_df.pivot_table(
        index="dist_bucket",
        columns="field_pos_bucket",
        values=val_col,
        aggfunc="mean",
    )

    # Order axes like R
    dist_order = [d for d in situational.DIST_ORDER if d in pivot.index]
    field_order = [f for f in situational.FIELD_POS_ORDER if f in pivot.columns]
    pivot = pivot.reindex(index=dist_order, columns=field_order)

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(pivot.values, aspect="auto", cmap="Blues" if kind == "run" else "Oranges", vmin=0, vmax=1)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_xlabel("Field position")
    ax.set_ylabel("Down & distance")
    ax.set_title(f"{team} {kind.title()} tendency by situation ({season})")
    plt.colorbar(im, ax=ax, label=f"{kind.title()} %")
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()

    caption = f"{team} {kind} rate by down/distance and field position. Lighter = less {kind}, darker = more {kind}."
    return {"path": str(path), "caption": caption, "team": team, "season": season, "kind": kind}


def render_success_rate_heatmap(
    success_df: pd.DataFrame,
    team: str,
    season: int,
    *,
    save_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Render success rate heatmap (down/distance × field position).

    success_df: from situational.success_rate_by_situation.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"path": None, "caption": "Success rate heatmap (not rendered)", "error": "matplotlib not installed"}

    path = save_path or report_assets.success_rank_heatmap_path(team, season)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if success_df.empty or "success_rate" not in success_df.columns:
        return {"path": str(path), "caption": "No success rate data", "error": "empty"}

    pivot = success_df.pivot_table(
        index="dist_bucket",
        columns="field_pos_bucket",
        values="success_rate",
        aggfunc="mean",
    )
    dist_order = [d for d in situational.DIST_ORDER if d in pivot.index]
    field_order = [f for f in situational.FIELD_POS_ORDER if f in pivot.columns]
    pivot = pivot.reindex(index=dist_order, columns=field_order)

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_xlabel("Field position")
    ax.set_ylabel("Down & distance")
    ax.set_title(f"{team} success rate by situation ({season})")
    plt.colorbar(im, ax=ax, label="Success rate")
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()

    return {"path": str(path), "caption": f"{team} offensive success rate by situation. Green = higher success.", "team": team, "season": season}


def render_matchup_heatmap(
    off_tendency: pd.DataFrame,
    def_tendency: pd.DataFrame,
    team_off: str,
    team_def: str,
    season: int,
    *,
    metric: str = "run_pct",
    save_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Offense vs defense matchup heatmap: difference (offense - defense) by situation.

    off_tendency: run_pass_tendency for team_off (posteam).
    def_tendency: run_pass_tendency for team_def (defteam = plays allowed).
    metric: column to compare (e.g. run_pct, pass_pct).
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return {"path": None, "caption": "Matchup heatmap (not rendered)", "error": "matplotlib not installed"}

    path = save_path or report_assets.matchup_heatmap_path(team_off, team_def, season)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if metric not in off_tendency.columns or metric not in def_tendency.columns:
        return {"path": str(path), "caption": "Missing metric", "error": f"metric {metric} not in data"}

    pivot_off = off_tendency.pivot_table(index="dist_bucket", columns="field_pos_bucket", values=metric, aggfunc="mean")
    pivot_def = def_tendency.pivot_table(index="dist_bucket", columns="field_pos_bucket", values=metric, aggfunc="mean")
    dist_order = [d for d in situational.DIST_ORDER if d in pivot_off.index and d in pivot_def.index]
    field_order = [f for f in situational.FIELD_POS_ORDER if f in pivot_off.columns and f in pivot_def.columns]
    pivot_off = pivot_off.reindex(index=dist_order, columns=field_order).fillna(0)
    pivot_def = pivot_def.reindex(index=dist_order, columns=field_order).fillna(0)
    diff = pivot_off - pivot_def

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(diff.values, aspect="auto", cmap="RdBu_r", vmin=-0.3, vmax=0.3)
    ax.set_xticks(range(len(diff.columns)))
    ax.set_xticklabels(diff.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(diff.index)))
    ax.set_yticklabels(diff.index, fontsize=8)
    ax.set_xlabel("Field position")
    ax.set_ylabel("Down & distance")
    ax.set_title(f"{team_off} off vs {team_def} def — {metric} advantage ({season})")
    plt.colorbar(im, ax=ax, label=f"Δ {metric}")
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()

    return {"path": str(path), "caption": f"Red = {team_def} defense holds edge; blue = {team_off} offense edge.", "team_off": team_off, "team_def": team_def, "season": season}


def render_run_direction(
    run_dir_df: pd.DataFrame,
    team: str,
    season: int,
    *,
    save_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Bar chart: run direction (left/middle/right) with n_runs, ypc, epa_per_run."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"path": None, "caption": "Run direction chart (not rendered)", "error": "matplotlib not installed"}

    path = save_path or report_assets.run_direction_path(team, season)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if run_dir_df.empty:
        return {"path": str(path), "caption": "No run direction data", "error": "empty"}

    fig, ax = plt.subplots(figsize=(7, 4))
    x = run_dir_df["run_location"].astype(str)
    ax.bar(x, run_dir_df["n_runs"], color="steelblue", alpha=0.8)
    ax.set_ylabel("Number of runs")
    ax.set_xlabel("Run direction")
    ax.set_title(f"{team} run direction ({season})")
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()

    return {"path": str(path), "caption": f"{team} run distribution by direction.", "team": team, "season": season}


def render_qb_passing_heatmap(
    pbp: pd.DataFrame,
    team: str,
    opponent: str,
    season: int,
    qb_name: Optional[str] = None,
    *,
    save_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    QB completion % by pass_location × air_yards depth vs opponent.

    pbp: filtered to team's pass plays vs opponent; needs pass_location, air_yards, complete_pass.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return {"path": None, "caption": "QB passing heatmap (not rendered)", "error": "matplotlib not installed"}

    qb_label = qb_name or "QB"
    path = save_path or report_assets.qb_passing_heatmap_path(qb_label, team, opponent, season)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    for col in ["pass_location", "air_yards", "complete_pass"]:
        if col not in pbp.columns:
            return {"path": str(path), "caption": "Missing PBP columns for QB heatmap", "error": f"missing {col}"}

    df = pbp[(pbp["posteam"] == team) & (pbp["defteam"] == opponent)].copy()
    df = df[df["pass_attempt"].fillna(0).astype(bool) | df["qb_scramble"].fillna(0).astype(bool)]
    if df.empty:
        return {"path": str(path), "caption": "No pass plays vs this opponent", "error": "empty"}

    # Depth buckets
    def depth_bucket(ay: float) -> str:
        if pd.isna(ay) or ay < 0:
            return "Behind LOS"
        if ay < 5:
            return "Short (0-4)"
        if ay < 15:
            return "Intermediate (5-14)"
        return "Deep (15+)"

    df["depth"] = df["air_yards"].map(depth_bucket)
    df["loc"] = df["pass_location"].fillna("unknown").astype(str).str.strip().str.lower()
    df.loc[df["loc"] == "", "loc"] = "unknown"
    comp = df.groupby(["loc", "depth"], as_index=False).agg(
        comp=("complete_pass", "sum"),
        att=("complete_pass", "count"),
    )
    comp["pct"] = (comp["comp"] / comp["att"].replace(0, pd.NA)).round(3)

    pivot = comp.pivot_table(index="depth", columns="loc", values="pct", aggfunc="mean")
    order_depth = ["Behind LOS", "Short (0-4)", "Intermediate (5-14)", "Deep (15+)"]
    pivot = pivot.reindex(index=[d for d in order_depth if d in pivot.index])

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(pivot.values, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xlabel("Pass location")
    ax.set_ylabel("Depth (air yards)")
    ax.set_title(f"{qb_label} vs {opponent} — completion % ({season})")
    plt.colorbar(im, ax=ax, label="Completion %")
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()

    return {"path": str(path), "caption": f"Completion % by location and depth vs {opponent}.", "team": team, "opponent": opponent, "season": season}
