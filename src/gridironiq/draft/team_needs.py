from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .loaders import load_injuries, load_pbp_reg, load_snap_counts
from .positions import bucket_for_snap_pos
from .room_production import build_room_need_raw_by_team

NEED_BUCKETS: List[str] = ["QB", "RB", "WR", "TE", "OT", "IOL", "EDGE", "IDL", "LB", "CB", "SAF"]

# How much each team EPA weakness lifts need at a bucket (sums arbitrary; renormalized).
EPA_NEED_MAP: Dict[str, Dict[str, float]] = {
    "pass_off_epa_z": {"QB": 0.35, "WR": 0.25, "TE": 0.15, "OT": 0.15, "IOL": 0.1},
    "rush_off_epa_z": {"RB": 0.35, "IOL": 0.25, "TE": 0.15, "OT": 0.15, "WR": 0.1},
    "pass_def_epa_z": {"CB": 0.35, "SAF": 0.25, "LB": 0.2, "EDGE": 0.2},
    "rush_def_epa_z": {"IDL": 0.35, "LB": 0.25, "EDGE": 0.2, "SAF": 0.2},
}


def _normalize_need_dict(raw: Dict[str, float]) -> Dict[str, float]:
    mx = max(raw.values()) if raw else 1.0
    if mx <= 0:
        mx = 1.0
    return {b: max(0.0, min(100.0, 100.0 * raw.get(b, 0.0) / mx)) for b in NEED_BUCKETS}


def compute_team_epa_table(pbp: pd.DataFrame) -> pd.DataFrame:
    df = pbp
    off = df[df["play_type"] == "pass"].groupby("posteam")["epa"].mean()
    off_rush = df[df["play_type"] == "run"].groupby("posteam")["epa"].mean()
    def_pass = df[df["play_type"] == "pass"].groupby("defteam")["epa"].mean()
    def_rush = df[df["play_type"] == "run"].groupby("defteam")["epa"].mean()
    teams = sorted(set(df["posteam"].dropna().unique()) | set(df["defteam"].dropna().unique()))
    rows = []
    for t in teams:
        rows.append(
            {
                "team": t,
                "pass_off_epa": float(off.get(t, np.nan)),
                "rush_off_epa": float(off_rush.get(t, np.nan)),
                "pass_def_epa": float(def_pass.get(t, np.nan)),
                "rush_def_epa": float(def_rush.get(t, np.nan)),
            }
        )
    feat = pd.DataFrame(rows)
    for col in ["pass_off_epa", "rush_off_epa", "pass_def_epa", "rush_def_epa"]:
        s = feat[col].astype(float)
        mu, sig = s.mean(), s.std(ddof=0)
        zname = col + "_z"
        feat[zname] = (s - mu) / sig if sig and sig > 0 else 0.0
    return feat


def _snap_depth_scores(snaps: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in snaps.iterrows():
        pos = bucket_for_snap_pos(str(r.get("position", "")))
        if pos not in NEED_BUCKETS:
            continue
        team = str(r.get("team", ""))
        off_pct = float(r.get("offense_pct") or 0.0)
        def_pct = float(r.get("defense_pct") or 0.0)
        side = "off" if off_pct >= def_pct else "def"
        pct = off_pct if side == "off" else def_pct
        rows.append(
            {
                "team": team,
                "bucket": pos,
                "side": side,
                "player": str(r.get("player", "")),
                "pct": pct,
            }
        )
    if not rows:
        return pd.DataFrame(columns=["team", "bucket", "depth_need"])
    g = pd.DataFrame(rows)
    mx = g.groupby(["team", "bucket", "player"], as_index=False)["pct"].max()
    scores = []
    for (team, bucket), sub in mx.groupby(["team", "bucket"]):
        tops = sub["pct"].sort_values(ascending=False).head(3).tolist()
        if not tops:
            continue
        top1 = tops[0]
        top2 = tops[1] if len(tops) > 1 else 0.0
        concentration = min(1.0, top1 + top2)
        depth_need = concentration * 100.0
        scores.append({"team": team, "bucket": bucket, "depth_need": depth_need})
    return pd.DataFrame(scores)


def _injury_pressure(inj: pd.DataFrame) -> pd.DataFrame:
    if inj.empty:
        return pd.DataFrame(columns=["team", "bucket", "injury_pressure"])
    df = inj.copy()
    df["report_status"] = df["report_status"].astype(str).str.lower()
    bad = df["report_status"].str.contains("out|ir|doubtful", na=False)
    df = df.loc[bad]
    if df.empty:
        return pd.DataFrame(columns=["team", "bucket", "injury_pressure"])
    rows = []
    for _, r in df.iterrows():
        b = bucket_for_snap_pos(str(r.get("position", "")))
        if b not in NEED_BUCKETS:
            continue
        rows.append({"team": str(r.get("team", "")), "bucket": b})
    if not rows:
        return pd.DataFrame(columns=["team", "bucket", "injury_pressure"])
    g = pd.DataFrame(rows)
    cnt = g.groupby(["team", "bucket"]).size().reset_index(name="n")
    cnt["injury_pressure"] = (cnt["n"].clip(upper=12) / 12.0) * 100.0
    return cnt[["team", "bucket", "injury_pressure"]]


def _empty_layer() -> Dict[str, float]:
    return {b: 0.0 for b in NEED_BUCKETS}


def _layer_from_depth(team: str, depth: pd.DataFrame) -> Dict[str, float]:
    out = _empty_layer()
    drow = depth.loc[depth["team"] == team]
    for _, dr in drow.iterrows():
        b = str(dr["bucket"])
        if b in out:
            out[b] = float(dr["depth_need"])
    return out


def _layer_from_injury(team: str, inj_p: pd.DataFrame) -> Dict[str, float]:
    out = _empty_layer()
    irow = inj_p.loc[inj_p["team"] == team]
    for _, ir in irow.iterrows():
        b = str(ir["bucket"])
        if b in out:
            out[b] = float(ir["injury_pressure"])
    return out


def compute_team_needs(team: str, season: int) -> Dict[str, Any]:
    """
    Position bucket -> need_score 0–100 using nflverse PBP EPA, snap concentration, injuries,
    and position-room production from player_stats (no manual team priors).
    """
    team = str(team).upper()
    pbp = load_pbp_reg(season)
    epa_tbl = compute_team_epa_table(pbp)
    row = epa_tbl.loc[epa_tbl["team"] == team]
    if row.empty:
        raise ValueError(f"Unknown team {team!r} in PBP for season {season}")

    snaps = load_snap_counts(season)
    inj = load_injuries(season)

    depth = _snap_depth_scores(snaps)
    inj_p = _injury_pressure(inj)

    epa_need = _empty_layer()
    r0 = row.iloc[0]

    pass_off_z = float(r0.get("pass_off_epa_z", 0.0))
    rush_off_z = float(r0.get("rush_off_epa_z", 0.0))
    pass_def_z = float(r0.get("pass_def_epa_z", 0.0))
    rush_def_z = float(r0.get("rush_def_epa_z", 0.0))

    epa_terms = {
        "pass_off_epa_z": max(0.0, -pass_off_z),
        "rush_off_epa_z": max(0.0, -rush_off_z),
        "pass_def_epa_z": max(0.0, pass_def_z),
        "rush_def_epa_z": max(0.0, rush_def_z),
    }

    for term, weight_map in EPA_NEED_MAP.items():
        mag = epa_terms.get(term, 0.0)
        mag_u = min(55.0, 18.0 * mag)
        for b, w in weight_map.items():
            if b in epa_need:
                epa_need[b] += mag_u * w

    snap_contrib = _empty_layer()
    drow = depth.loc[depth["team"] == team]
    for _, dr in drow.iterrows():
        b = str(dr["bucket"])
        if b in snap_contrib:
            snap_contrib[b] += float(dr["depth_need"]) * 0.35

    inj_contrib = _empty_layer()
    irow = inj_p.loc[inj_p["team"] == team]
    for _, ir in irow.iterrows():
        b = str(ir["bucket"])
        if b in inj_contrib:
            inj_contrib[b] += float(ir["injury_pressure"]) * 0.25

    room_by_team, room_meta = build_room_need_raw_by_team(season)
    room_contrib = _empty_layer()
    if room_by_team and team in room_by_team:
        for b, v in room_by_team[team].items():
            if b in room_contrib:
                room_contrib[b] += float(v)

    combined = _empty_layer()
    for b in NEED_BUCKETS:
        combined[b] = epa_need[b] + snap_contrib[b] + inj_contrib[b] + room_contrib[b]

    need_norm = _normalize_need_dict(combined)
    snap_depth_display = _normalize_need_dict(_layer_from_depth(team, depth))
    injury_display = _normalize_need_dict(_layer_from_injury(team, inj_p))
    room_display = _normalize_need_dict(dict(room_by_team.get(team, _empty_layer())))
    epa_display = _normalize_need_dict(epa_need)

    return {
        "team": team,
        "season": season,
        "need_scores": need_norm,
        "signal_layers": {
            "epa_need_normalized": epa_display,
            "snap_depth_normalized": snap_depth_display,
            "injury_pressure_normalized": injury_display,
            "room_production_normalized": room_display,
        },
        "room_production_meta": room_meta,
        "need_signal_policy": {
            "manual_need_priors": False,
            "sources": [
                "nflverse_pbp_epa",
                "nflverse_snap_counts",
                "nflverse_injury_reports",
                "nflverse_player_stats_room_production",
            ],
            "team": team,
            "season": season,
        },
        "epa_profile": {
            "pass_off_epa": float(r0.get("pass_off_epa", 0.0)),
            "rush_off_epa": float(r0.get("rush_off_epa", 0.0)),
            "pass_def_epa": float(r0.get("pass_def_epa", 0.0)),
            "rush_def_epa": float(r0.get("rush_def_epa", 0.0)),
            "pass_off_epa_z": pass_off_z,
            "rush_off_epa_z": rush_off_z,
            "pass_def_epa_z": pass_def_z,
            "rush_def_epa_z": rush_def_z,
        },
    }
