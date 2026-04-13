"""
Situational bucketing and tendency logic for matchup reports.

Uses nflverse-style PBP columns. Caller must supply PBP with at least:
  down, ydstogo, yardline_100, posteam, defteam, play_type
and for full metrics: pass_attempt, rush_attempt, qb_scramble, success, epa, yards_gained.
Optional: shotgun, run_location, pass_location, air_yards, complete_pass.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Order for down/distance situations (R: dist_order)
DIST_ORDER = [
    "1st & 10+",
    "1st & <10",
    "2nd Long",
    "2nd Medium",
    "2nd Short",
    "3rd Long",
    "3rd Medium",
    "3rd Short",
    "4th Long",
    "4th Medium",
    "4th Short",
]

# Order for field position (R: field_pos_order)
FIELD_POS_ORDER = [
    "Backed Up (Own 1-9)",
    "In the Field (Own 10-Opp 21)",
    "Upper Red Zone (Opp 20-11)",
    "Lower Red Zone (Opp 10-3)",
    "Goal Line (Opp 2-1)",
]


def _dist_bucket(down: int, ydstogo: int) -> str:
    """Map (down, ydstogo) to R-style dist_bucket label."""
    if down == 1:
        return "1st & 10+" if ydstogo >= 10 else "1st & <10"
    if down == 2:
        if ydstogo >= 7:
            return "2nd Long"
        if ydstogo >= 3:
            return "2nd Medium"
        return "2nd Short"
    if down == 3:
        if ydstogo >= 7:
            return "3rd Long"
        if ydstogo >= 3:
            return "3rd Medium"
        return "3rd Short"
    if down == 4:
        if ydstogo >= 7:
            return "4th Long"
        if ydstogo >= 3:
            return "4th Medium"
        return "4th Short"
    return "Other"


def _field_pos_bucket(yardline_100: float) -> str:
    """Map yardline_100 to R-style field_pos_bucket label."""
    y = int(yardline_100) if pd.notna(yardline_100) else 50
    if y >= 91:
        return "Backed Up (Own 1-9)"
    if y >= 21:
        return "In the Field (Own 10-Opp 21)"
    if y >= 11:
        return "Upper Red Zone (Opp 20-11)"
    if y >= 3:
        return "Lower Red Zone (Opp 10-3)"
    if y >= 1:
        return "Goal Line (Opp 2-1)"
    return "Other"


def build_situational_buckets(pbp: pd.DataFrame) -> pd.DataFrame:
    """
    Add dist_bucket and field_pos_bucket to PBP; filter to pass/rush and non-Other.

    Expects columns: down, ydstogo, yardline_100, and play_type or pass_attempt/rush_attempt/qb_scramble.
    Drops rows with NaN in down/ydstogo so int conversion does not fail.
    """
    df = pbp.copy()
    if "down" not in df.columns or "ydstogo" not in df.columns or "yardline_100" not in df.columns:
        raise ValueError("pbp must contain down, ydstogo, yardline_100")

    # Drop rows with NaN in required numeric columns to avoid "cannot convert float NaN to integer"
    df = df.dropna(subset=["down", "ydstogo"])
    if df.empty:
        return df

    df["dist_bucket"] = df.apply(lambda r: _dist_bucket(int(r["down"]), int(r["ydstogo"])), axis=1)
    df["field_pos_bucket"] = df["yardline_100"].map(_field_pos_bucket)

    # Play category: Pass (pass or scramble) vs Run
    if "pass_attempt" in df.columns and "rush_attempt" in df.columns and "qb_scramble" in df.columns:
        df["play_category"] = (
            df["pass_attempt"].fillna(0).astype(bool)
            | df["qb_scramble"].fillna(0).astype(bool)
        ).map({True: "Pass", False: "Run"})
        df.loc[df["rush_attempt"].fillna(0).astype(bool) & ~df["pass_attempt"].fillna(0).astype(bool) & ~df["qb_scramble"].fillna(0).astype(bool), "play_category"] = "Run"
    elif "play_type" in df.columns:
        df["play_category"] = df["play_type"].map(lambda x: "Pass" if str(x).lower() in ("pass", "pass_outcome_caught", "pass_outcome_incomplete", "qb_scramble") else "Run")
    else:
        df["play_category"] = "Run"

    # Filter: drop no_play, keep only rows with valid down and non-Other buckets
    if "play_type" in df.columns:
        df = df[df["play_type"].astype(str).str.lower() != "no_play"].copy()
    df = df[df["down"].notna()].copy()
    df = df[df["dist_bucket"] != "Other"].copy()
    df = df[df["field_pos_bucket"] != "Other"].copy()

    return df


def run_pass_tendency_by_situation(
    pbp: pd.DataFrame,
    team: str,
    *,
    team_col: str = "posteam",
) -> pd.DataFrame:
    """
    Run/pass rate and count by situation (dist_bucket × field_pos_bucket) for one team.

    pbp must already have dist_bucket, field_pos_bucket, play_category (use build_situational_buckets first).
    Returns DataFrame with columns: dist_bucket, field_pos_bucket, n_plays, run_pct, pass_pct, run_success, pass_success
    (run_success/pass_success only if 'success' in pbp).
    """
    df = pbp.loc[pbp[team_col] == team].copy()
    if df.empty:
        return pd.DataFrame(
            columns=[
                "dist_bucket", "field_pos_bucket", "n_plays", "run_pct", "pass_pct",
                "run_success", "pass_success",
            ]
        )

    has_success = "success" in df.columns
    df = df.copy()
    df["_n_run"] = (df["play_category"] == "Run").astype(int)
    df["_n_pass"] = (df["play_category"] == "Pass").astype(int)
    out = (
        df.groupby(["dist_bucket", "field_pos_bucket"], as_index=False)
        .agg(n_plays=("play_category", "count"), n_run=("_n_run", "sum"), n_pass=("_n_pass", "sum"))
    )
    out["run_pct"] = (out["n_run"] / out["n_plays"].replace(0, pd.NA)).round(3)
    out["pass_pct"] = (out["n_pass"] / out["n_plays"].replace(0, pd.NA)).round(3)

    if has_success:
        run_succ = df[df["play_category"] == "Run"].groupby(["dist_bucket", "field_pos_bucket"])["success"].mean().reset_index(name="run_success")
        pass_succ = df[df["play_category"] == "Pass"].groupby(["dist_bucket", "field_pos_bucket"])["success"].mean().reset_index(name="pass_success")
        out = out.merge(run_succ, on=["dist_bucket", "field_pos_bucket"], how="left")
        out = out.merge(pass_succ, on=["dist_bucket", "field_pos_bucket"], how="left")
        out["run_success"] = out["run_success"].round(3)
        out["pass_success"] = out["pass_success"].round(3)
    else:
        out["run_success"] = pd.NA
        out["pass_success"] = pd.NA

    return out


def success_rate_by_situation(
    pbp: pd.DataFrame,
    team: str,
    *,
    team_col: str = "posteam",
) -> pd.DataFrame:
    """
    Success rate by situation (dist_bucket × field_pos_bucket) for one team.

    pbp must have dist_bucket, field_pos_bucket, and success (0/1 or bool).
    """
    df = pbp.loc[pbp[team_col] == team]
    if df.empty or "success" not in df.columns:
        return pd.DataFrame(columns=["dist_bucket", "field_pos_bucket", "n_plays", "success_rate"])

    out = (
        df.groupby(["dist_bucket", "field_pos_bucket"], as_index=False)
        .agg(n_plays=("success", "count"), success_rate=("success", "mean"))
        .round({"success_rate": 3})
    )
    return out


def offense_vs_defense_situational(
    team_off_pbp: pd.DataFrame,
    team_def_pbp: pd.DataFrame,
    team_off_abbrev: str,
    team_def_abbrev: str,
) -> Dict[str, Any]:
    """
    Compare offense (team_off) tendency/success vs defense (team_def) in same situations.

    team_off_pbp: PBP where posteam == team_off_abbrev (that team's offensive plays).
    team_def_pbp: PBP where defteam == team_def_abbrev (plays against that defense).

    Returns a dict with offense tendency/success and defense tendency/success by situation,
    plus a simple edge summary (e.g. where offense runs more than defense allows).
    """
    off_tend = run_pass_tendency_by_situation(team_off_pbp, team_off_abbrev, team_col="posteam")
    def_tend = run_pass_tendency_by_situation(team_def_pbp, team_def_abbrev, team_col="defteam")
    off_succ = success_rate_by_situation(team_off_pbp, team_off_abbrev, team_col="posteam")
    def_succ = success_rate_by_situation(team_def_pbp, team_def_abbrev, team_col="defteam")

    def to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
        return df.replace({pd.NA: None}).to_dict(orient="records")

    return {
        "offense_team": team_off_abbrev,
        "defense_team": team_def_abbrev,
        "offense_tendency": to_records(off_tend),
        "defense_tendency_allowed": to_records(def_tend),
        "offense_success_by_situation": to_records(off_succ),
        "defense_success_allowed_by_situation": to_records(def_succ),
        "situations": list(FIELD_POS_ORDER),
        "dist_order": list(DIST_ORDER),
    }


def run_direction_summary(
    pbp: pd.DataFrame,
    team: str,
    *,
    team_col: str = "posteam",
) -> pd.DataFrame:
    """
    Run direction summary: left / middle / right with count, YPC, EPA/run.

    pbp must have run_location (or run_attempt + run_location), yards_gained, and optionally epa.
    """
    df = pbp.loc[(pbp[team_col] == team) & (pbp.get("play_category", pd.Series(dtype=object)) == "Run")].copy()
    if "run_location" not in df.columns:
        return pd.DataFrame(columns=["run_location", "n_runs", "ypc", "epa_per_run"])

    df = df[df["run_location"].notna() & (df["run_location"].astype(str).str.len() > 0)]
    if df.empty:
        return pd.DataFrame(columns=["run_location", "n_runs", "ypc", "epa_per_run"])

    grp = df.groupby("run_location", as_index=False)
    out = grp.agg(
        n_runs=("run_location", "count"),
        ypc=("yards_gained", "mean"),
    ).round({"ypc": 2})
    if "epa" in df.columns:
        epa_avg = grp["epa"].mean().round(3).reset_index()
        epa_avg = epa_avg.rename(columns={"epa": "epa_per_run"})
        out = out.merge(epa_avg, on="run_location", how="left")
    else:
        out["epa_per_run"] = None
    return out
