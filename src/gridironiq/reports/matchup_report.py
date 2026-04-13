"""
Structured matchup report combining engine prediction, situational edges, and assets.

Input: season, week (optional), team_a, team_b.
Output: JSON with summary, team profiles, situational_edges, offense_vs_defense, report_assets.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..matchup_engine import run_matchup, MatchupResult
from ..report_generator import generate_report
from . import report_assets
from . import situational
from . import heatmaps

logger = logging.getLogger(__name__)

# Columns needed for report situational/heatmap logic (in addition to keys columns)
REPORT_PBP_EXTRA_COLUMNS = [
    "success", "epa", "pass_attempt", "rush_attempt", "qb_scramble",
    "shotgun", "run_location", "pass_location", "air_yards", "complete_pass", "yards_gained",
]


def get_pbp_for_reports(season: int, season_type: str = "REG") -> pd.DataFrame:
    """Load PBP with columns required for situational buckets and heatmaps."""
    from superbowlengine.config import DEFAULT_CONFIG
    from superbowlengine.data import get_pbp

    cols = list(DEFAULT_CONFIG.pbp_columns) + REPORT_PBP_EXTRA_COLUMNS
    return get_pbp([season], season_type=season_type, columns=cols)


def build_matchup_report(
    season: int,
    team_a: str,
    team_b: str,
    *,
    week: Optional[int] = None,
    mode: str = "opp_weighted",
    pbp: Optional[pd.DataFrame] = None,
    generate_heatmaps: bool = True,
) -> Dict[str, Any]:
    """
    Build full matchup report: prediction, situational edges, offense vs defense, optional assets.

    If pbp is None, loads PBP for season (REG) with report columns. If generate_heatmaps is True,
    renders run/pass and success heatmaps and records paths in report_assets.
    """
    # 1) Engine prediction
    try:
        result: MatchupResult = run_matchup(season, team_a, team_b, mode=mode)
    except Exception as e:
        logger.exception("Matchup engine failed")
        result = None
        engine_error = str(e)
    else:
        engine_error = None

    base_report = generate_report(result) if result else {
        "summary": f"Matchup {team_a} vs {team_b} ({season}). Engine unavailable: {engine_error}.",
        "team_a_strengths": [],
        "team_b_strengths": [],
        "offensive_profile": {},
        "defensive_profile": {},
        "prediction_explanation": "",
        "confidence_notes": [],
        "team_a": team_a,
        "team_b": team_b,
        "season": season,
        "win_probability": 0.5,
        "predicted_winner": team_a,
        "projected_score": {},
        "keys_won": {},
        "top_drivers": [],
    }

    # 2) Situational data (if we have PBP)
    situational_edges: Dict[str, Any] = {}
    offense_vs_defense: Dict[str, Any] = {}
    report_asset_list: List[Dict[str, Any]] = []

    if pbp is None:
        try:
            pbp = get_pbp_for_reports(season)
        except Exception as e:
            logger.warning("Could not load PBP for reports: %s", e)
            pbp = None

    if pbp is not None and not pbp.empty:
        try:
            pbp_bucketed = situational.build_situational_buckets(pbp)
        except Exception as e:
            logger.warning("Situational bucketing failed: %s", e)
            pbp_bucketed = None
        else:
            # Tendencies for both teams
            tend_a = situational.run_pass_tendency_by_situation(pbp_bucketed, team_a)
            tend_b = situational.run_pass_tendency_by_situation(pbp_bucketed, team_b)
            succ_a = situational.success_rate_by_situation(pbp_bucketed, team_a)
            succ_b = situational.success_rate_by_situation(pbp_bucketed, team_b)

            situational_edges = {
                "team_a_tendency": tend_a.replace({pd.NA: None}).to_dict(orient="records"),
                "team_b_tendency": tend_b.replace({pd.NA: None}).to_dict(orient="records"),
                "team_a_success": succ_a.replace({pd.NA: None}).to_dict(orient="records"),
                "team_b_success": succ_b.replace({pd.NA: None}).to_dict(orient="records"),
            }

            # Offense vs defense: A's offense vs B's defense, B's offense vs A's defense
            off_a = pbp_bucketed[pbp_bucketed["posteam"] == team_a]
            def_b = pbp_bucketed[pbp_bucketed["defteam"] == team_b]
            off_b = pbp_bucketed[pbp_bucketed["posteam"] == team_b]
            def_a = pbp_bucketed[pbp_bucketed["defteam"] == team_a]
            offense_vs_defense = {
                f"{team_a}_off_vs_{team_b}_def": situational.offense_vs_defense_situational(off_a, def_b, team_a, team_b),
                f"{team_b}_off_vs_{team_a}_def": situational.offense_vs_defense_situational(off_b, def_a, team_b, team_a),
            }

            # Optional heatmaps
            if generate_heatmaps:
                for team, tend, succ in [(team_a, tend_a, succ_a), (team_b, tend_b, succ_b)]:
                    if not tend.empty:
                        for kind in ("run", "pass"):
                            meta = heatmaps.render_run_pass_heatmap(tend, team, season, kind=kind)
                            if meta.get("path"):
                                p = Path(str(meta["path"]))
                                report_asset_list.append(
                                    {
                                        "type": f"heatmap_{kind}",
                                        "team": team,
                                        **meta,
                                        "url": f"/report-assets/{p.name}",
                                    }
                                )
                    if not succ.empty:
                        meta = heatmaps.render_success_rate_heatmap(succ, team, season)
                        if meta.get("path"):
                            p = Path(str(meta["path"]))
                            report_asset_list.append(
                                {"type": "heatmap_success", "team": team, **meta, "url": f"/report-assets/{p.name}"}
                            )
                # Matchup heatmaps: offense tendency vs defense tendency allowed
                def_tend_b = situational.run_pass_tendency_by_situation(pbp_bucketed, team_b, team_col="defteam")
                def_tend_a = situational.run_pass_tendency_by_situation(pbp_bucketed, team_a, team_col="defteam")
                if not tend_a.empty and not def_tend_b.empty:
                    meta = heatmaps.render_matchup_heatmap(tend_a, def_tend_b, team_a, team_b, season, metric="run_pct")
                    if meta.get("path"):
                        p = Path(str(meta["path"]))
                        report_asset_list.append({"type": "matchup_heatmap", **meta, "url": f"/report-assets/{p.name}"})
                if not tend_b.empty and not def_tend_a.empty:
                    meta = heatmaps.render_matchup_heatmap(tend_b, def_tend_a, team_b, team_a, season, metric="run_pct")
                    if meta.get("path"):
                        p = Path(str(meta["path"]))
                        report_asset_list.append({"type": "matchup_heatmap", **meta, "url": f"/report-assets/{p.name}"})
    else:
        situational_edges = {"note": "PBP not available for situational breakdown."}
        offense_vs_defense = {"note": "PBP not available."}

    key_matchup_edges = result.key_edges if result else {}

    return {
        "summary": base_report.get("summary", ""),
        "team_a_profile": {
            "team": team_a,
            "strengths": base_report.get("team_a_strengths", []),
            "offensive_profile": base_report.get("offensive_profile", {}).get(team_a, {}),
        },
        "team_b_profile": {
            "team": team_b,
            "strengths": base_report.get("team_b_strengths", []),
            "offensive_profile": base_report.get("offensive_profile", {}).get(team_b, {}),
        },
        "situational_edges": situational_edges,
        "key_matchup_edges": key_matchup_edges,
        "offense_vs_defense": offense_vs_defense,
        "report_assets": report_asset_list,
        "team_a": team_a,
        "team_b": team_b,
        "season": season,
        "week": week,
        "win_probability": base_report.get("win_probability"),
        "predicted_winner": base_report.get("predicted_winner"),
        "projected_score": base_report.get("projected_score"),
        "prediction_explanation": base_report.get("prediction_explanation"),
        "confidence_notes": base_report.get("confidence_notes", []),
    }
