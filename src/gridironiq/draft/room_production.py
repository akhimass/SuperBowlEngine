from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .loaders import load_player_stats_reg

_NEED_BUCKETS = ("QB", "RB", "WR", "TE", "OT", "IOL", "EDGE", "IDL", "LB", "CB", "SAF")

# One nflverse load per season; reused across all NEED_BUCKETS room calls.
_room_raw_cache: Dict[int, Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]] = {}


def clear_room_cache() -> None:
    """Clear cached room-production raw maps (for tests or hot reload)."""
    _room_raw_cache.clear()

# Max contribution per bucket from room layer (same raw scale as EPA/depth terms pre-normalize).
ROOM_BUCKET_WEIGHTS: Dict[str, float] = {
    "TE": 0.20,
    "WR": 0.15,
    "EDGE": 0.20,
}

# Columns to aggregate from nflverse player_stats (season sum by team + position).
_ROOM_SPECS: List[Tuple[str, List[str], List[str]]] = [
    ("TE", ["TE"], ["targets", "receptions", "receiving_yards", "receiving_tds"]),
    ("WR", ["WR"], ["targets", "receiving_yards", "receiving_air_yards"]),
    ("EDGE", ["DE", "OLB"], ["def_sacks", "def_qb_hits"]),
]


def _team_totals_by_positions(df: pd.DataFrame, positions: List[str], cols: List[str]) -> pd.DataFrame:
    sub = df[df["position"].astype(str).isin(positions)]
    if sub.empty:
        return pd.DataFrame()
    use = [c for c in cols if c in sub.columns]
    if not use:
        return pd.DataFrame()
    return sub.groupby("team", as_index=True)[use].sum()


def _mean_badness(z_row: pd.Series) -> float:
    """Average max(0, -z) across metrics: low room production vs league -> higher need."""
    parts: List[float] = []
    for v in z_row.astype(float):
        if np.isnan(v):
            continue
        parts.append(max(0.0, -float(v)))
    return float(sum(parts) / max(len(parts), 1))


def build_room_need_raw_by_team(season: int) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Any]]:
    """
    Per team, per NEED bucket, raw points to add before final need normalization.
    Grounded in nflverse player_stats only (no fabricated stats).
    """
    s = int(season)
    if s in _room_raw_cache:
        return _room_raw_cache[s]

    df = load_player_stats_reg(s)
    if df.empty or "team" not in df.columns:
        meta_skip: Dict[str, Any] = {
            "room_layer": "skipped",
            "reason": "empty_player_stats",
            "season": s,
        }
        skipped: Tuple[Dict[str, Dict[str, float]], Dict[str, Any]] = ({}, meta_skip)
        _room_raw_cache[s] = skipped
        return skipped

    teams = sorted(df["team"].dropna().astype(str).unique())
    out: Dict[str, Dict[str, float]] = {t: {b: 0.0 for b in _NEED_BUCKETS} for t in teams}
    meta: Dict[str, Any] = {"room_layer": "nflverse_player_stats", "season": s, "buckets": []}

    for bucket, positions, cols in _ROOM_SPECS:
        if bucket not in ROOM_BUCKET_WEIGHTS:
            continue
        tbl = _team_totals_by_positions(df, positions, cols)
        if tbl.empty:
            meta["buckets"].append({"bucket": bucket, "note": "no_rows"})
            continue
        z = tbl.astype(float)
        for c in z.columns:
            mu, sig = float(z[c].mean()), float(z[c].std(ddof=0) or 0.0)
            if sig <= 1e-9:
                z[c] = 0.0
            else:
                z[c] = (z[c] - mu) / sig
        w = ROOM_BUCKET_WEIGHTS[bucket]
        # Scale so a ~1 sigma weak room adds meaningful raw weight before normalize.
        scale = 52.0
        for team in teams:
            if team not in z.index:
                continue
            bad = _mean_badness(z.loc[team])
            out[team][bucket] += bad * scale * w
        meta["buckets"].append({"bucket": bucket, "positions": positions, "metrics": list(z.columns)})

    packed: Tuple[Dict[str, Dict[str, float]], Dict[str, Any]] = (out, meta)
    _room_raw_cache[s] = packed
    return packed


def build_room_need_score(team: str, pos_bucket: str, season: int) -> float:
    """Raw room-production need contribution for one bucket (pre–final normalization)."""
    raw_map, _ = build_room_need_raw_by_team(season)
    t = str(team).upper()
    b = str(pos_bucket).upper()
    if not raw_map or t not in raw_map:
        return 0.0
    return float(raw_map[t].get(b, 0.0))


def _edge_pressure_ratio_for_team_season(team: str, season: int) -> float:
    """Team (DE+OLB) sacks+QB hits divided by league mean of same (nflverse player_stats)."""
    df = load_player_stats_reg(season)
    if df.empty:
        return 0.0
    sub = df[df["position"].astype(str).isin(["DE", "OLB"])]
    if sub.empty or "team" not in sub.columns:
        return 0.0
    g = sub.groupby("team", as_index=True)[["def_sacks", "def_qb_hits"]].sum()
    g["press"] = g["def_sacks"].astype(float) + g["def_qb_hits"].astype(float)
    league_mean = float(g["press"].mean()) or 1e-6
    t = str(team).upper()
    if t not in g.index:
        return 0.0
    return float(g.loc[t, "press"]) / league_mean


def compute_position_share_trend(team: str, position_bucket: str, seasons: List[int]) -> float:
    """
    Linear slope of share series over seasons (x = 0..n-1, y = share per season).
    TE/WR/RB: target share from build_team_pass_game_shares.
    EDGE: team pass-rush totals vs league mean (def_sacks + def_qb_hits, DE+OLB only).
    Returns 0.0 if fewer than 2 seasons with usable data.
    """
    team_u = str(team).upper()
    pb = str(position_bucket).upper()
    ys: List[float] = []
    for s in seasons:
        if pb == "EDGE":
            ys.append(_edge_pressure_ratio_for_team_season(team_u, int(s)))
            continue
        tbl, meta = build_team_pass_game_shares(int(s))
        if tbl.empty or team_u not in tbl.index or meta.get("error"):
            ys.append(float("nan"))
            continue
        row = tbl.loc[team_u]
        if pb == "TE":
            ys.append(float(row.get("te_target_share", float("nan"))))
        elif pb == "WR":
            ys.append(float(row.get("wr_target_share", float("nan"))))
        elif pb == "RB":
            ys.append(float(row.get("rb_target_share", float("nan"))))
        else:
            return 0.0
    clean = [y for y in ys if y == y and not np.isnan(y)]
    if len(clean) < 2:
        return 0.0
    x = np.arange(len(clean), dtype=float)
    y = np.array(clean, dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def build_team_pass_game_shares(season: int) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Team-level passing-game structure from nflverse player_stats (regular season).
    Used to extend scheme profile (TE usage vs WR usage). No PBP personnel column required.
    """
    df = load_player_stats_reg(season)
    meta: Dict[str, Any] = {"source": "nflverse_player_stats", "season": season}
    if df.empty or "team" not in df.columns:
        return pd.DataFrame(), {**meta, "error": "empty_stats"}

    skill_pos = {"WR", "TE", "RB"}
    sub = df[df["position"].astype(str).isin(skill_pos)]
    if sub.empty:
        return pd.DataFrame(), {**meta, "error": "no_skill_positions"}

    agg = sub.groupby(["team", "position"], as_index=False)[["targets", "receiving_air_yards"]].sum()
    rows = []
    for team, g in agg.groupby("team"):
        m = g.set_index("position")
        def _get(pos: str, col: str) -> float:
            if pos not in m.index or col not in m.columns:
                return 0.0
            return float(m.loc[pos, col] or 0.0)

        te_t = _get("TE", "targets")
        wr_t = _get("WR", "targets")
        rb_t = _get("RB", "targets")
        skill_t = te_t + wr_t + rb_t + 1e-6
        te_air = _get("TE", "receiving_air_yards")
        wr_air = _get("WR", "receiving_air_yards")
        rb_air = _get("RB", "receiving_air_yards")
        skill_air = te_air + wr_air + rb_air + 1e-6
        rows.append(
            {
                "team": str(team),
                "te_target_share": te_t / skill_t,
                "wr_target_share": wr_t / skill_t,
                "rb_target_share": rb_t / skill_t,
                "te_air_yards_share": te_air / skill_air,
                "wr_air_yards_share": wr_air / skill_air,
            }
        )
    out = pd.DataFrame(rows).set_index("team")
    return out, meta
