from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Dict, Tuple

import numpy as np

from .loaders import load_pbp_reg
from .positions import bucket_for_combine_pos
from .room_production import build_team_pass_game_shares

if TYPE_CHECKING:
    from .team_context import TeamContext


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n <= 1e-9:
        return v * 0.0
    return v / n


def _lin01(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


TE_ARCHETYPE_PREFS: Dict[str, Tuple[float, float, float]] = {
    "receiving_weapon": (0.92, 0.88, 0.42),
    "inline_blocker": (0.38, 0.28, 0.58),
    "move_te_hybrid": (0.68, 0.58, 0.48),
}


def infer_te_archetype(player_profile: Dict[str, Any], team_raw: Dict[str, float] | None = None) -> str:
    """
    Prospect TE role from measurable inputs. Optional team pass-game shares resolve ties only.
    """
    manual = str(player_profile.get("te_scheme_archetype") or "").strip()
    if manual and manual in TE_ARCHETYPE_PREFS:
        return manual
    forty = player_profile.get("forty")
    wt = player_profile.get("weight_lb")
    try:
        f = float(forty) if forty is not None and not (isinstance(forty, float) and math.isnan(forty)) else None
    except (TypeError, ValueError):
        f = None
    try:
        w = float(wt) if wt is not None and not (isinstance(wt, float) and math.isnan(wt)) else None
    except (TypeError, ValueError):
        w = None
    arch = "move_te_hybrid"
    if f is not None and w is not None:
        if f <= 4.45 and w <= 245:
            arch = "receiving_weapon"
        elif f >= 4.71 or w >= 256:
            arch = "inline_blocker"
        else:
            arch = "move_te_hybrid"
    if team_raw is not None:
        te = float(team_raw.get("te_target_share", 0.15))
        air = float(team_raw.get("te_air_yards_share", 0.15))
        if te > 0.18 and air > 0.15 and arch == "move_te_hybrid":
            arch = "receiving_weapon"
        elif te < 0.12 and arch == "move_te_hybrid":
            arch = "inline_blocker"
    return arch


def te_share_fit_score(team_raw: Dict[str, float], archetype: str) -> float:
    """
    0–1 alignment between prospect TE archetype and team target/air-yards structure.
    High-TE-volume teams favor receiving profiles; low-TE teams favor inline.
    """
    te = float(team_raw.get("te_target_share", 0.15))
    air = float(team_raw.get("te_air_yards_share", 0.15))
    if archetype == "receiving_weapon":
        if te > 0.18 and air > 0.15:
            return 0.95
        return 0.35 + 0.40 * _lin01(te, 0.10, 0.22) + 0.25 * _lin01(air, 0.08, 0.24)
    if archetype == "inline_blocker":
        if te < 0.12:
            return 0.92
        return 0.38 + 0.52 * _lin01(1.0 - te, 0.0, 0.12)
    if 0.12 <= te <= 0.18:
        return 0.88
    return 0.50 + 0.35 * (1.0 - min(abs(te - 0.15) / 0.12, 1.0))


def edge_trend_fit_bonus(edge_pressure_trend: float) -> float:
    """0–0.10: reward EDGE fit when pass-rush output vs league is trending down."""
    return float(max(0.0, min(0.10, -edge_pressure_trend * 12.0)))


def ot_pass_rate_fit_bonus(pass_rate: float) -> float:
    """Small scheme lift for OT when offense is pass-heavy (PBP pass rate)."""
    if pass_rate <= 0.52:
        return 0.0
    return float(max(0.0, min(0.08, (pass_rate - 0.52) * 0.35)))


def wr_scheme_signals(team_raw: Dict[str, float]) -> Dict[str, float]:
    """
    WR fit proxies from nflverse skill-target/air shares (no separate slot/boundary charting).
    """
    wr_t = float(team_raw.get("wr_target_share_of_skill", 0.5))
    wr_air = float(team_raw.get("wr_air_yards_share", 0.5))
    boundary_proxy = min(1.0, 0.55 * wr_air + 0.45 * _lin01(wr_t, 0.35, 0.55))
    return {
        "wr_target_share": wr_t,
        "wr_air_yards_share": wr_air,
        "wr_boundary_usage_proxy": round(boundary_proxy, 4),
    }


def build_team_scheme_profile(team: str, season: int) -> Dict[str, Any]:
    team = str(team).upper()
    pbp = load_pbp_reg(season)
    off = pbp[pbp["posteam"] == team]
    deff = pbp[pbp["defteam"] == team]
    if off.empty or deff.empty:
        raise ValueError(f"Insufficient PBP rows for team={team} season={season}")

    pass_rate = float((off["play_type"] == "pass").mean())
    shotgun = float(off["shotgun"].fillna(0).mean()) if "shotgun" in off.columns else 0.0
    pass_epa = float(off.loc[off["play_type"] == "pass", "epa"].mean())
    rush_epa = float(off.loc[off["play_type"] == "run", "epa"].mean())

    opp_pass = float((deff["play_type"] == "pass").mean())
    def_pass_epa = float(deff.loc[deff["play_type"] == "pass", "epa"].mean())
    def_rush_epa = float(deff.loc[deff["play_type"] == "run", "epa"].mean())

    vec = np.array(
        [
            pass_rate,
            shotgun,
            pass_epa,
            rush_epa,
            opp_pass,
            def_pass_epa,
            def_rush_epa,
        ],
        dtype=float,
    )
    shares_tbl, shares_meta = build_team_pass_game_shares(season)
    te_tgt = te_air = wr_t = 0.5
    wr_air_share = 0.5
    if not shares_tbl.empty and team in shares_tbl.index:
        row = shares_tbl.loc[team]
        te_tgt = float(row.get("te_target_share", 0.5))
        te_air = float(row.get("te_air_yards_share", 0.5))
        wr_t = float(row.get("wr_target_share", 0.5))
        wr_air_share = float(row.get("wr_air_yards_share", 0.5))
    ext = np.array([te_tgt, te_air, wr_t], dtype=float)
    vec_full = np.concatenate([vec, ext])
    personnel_note = (
        "nflverse_pbp_has_no_personnel_column_in_this_build; "
        "using_player_stats_te_wr_target_and_air_shares_as_proxy"
    )
    return {
        "team": team,
        "season": season,
        "vector": vec_full.tolist(),
        "labels": [
            "off_pass_rate",
            "off_shotgun_rate",
            "off_pass_epa",
            "off_rush_epa",
            "def_opp_pass_rate",
            "def_pass_epa_allowed",
            "def_rush_epa_allowed",
            "te_target_share_skill",
            "te_air_yards_share_skill",
            "wr_target_share_skill",
        ],
        "raw": {
            "off_pass_rate": pass_rate,
            "off_shotgun_rate": shotgun,
            "off_pass_epa": pass_epa,
            "off_rush_epa": rush_epa,
            "def_opp_pass_rate": opp_pass,
            "def_pass_epa_allowed": def_pass_epa,
            "def_rush_epa_allowed": def_rush_epa,
            "te_target_share": te_tgt,
            "te_air_yards_share": te_air,
            "wr_target_share_of_skill": wr_t,
            "wr_air_yards_share": wr_air_share,
            "personnel_proxy_note": personnel_note,
            "pass_game_shares_meta": shares_meta,
        },
    }


def _player_pass_game_affinity(
    pos_bucket: str,
    player_profile: Dict[str, Any],
    team_raw: Dict[str, float] | None,
) -> Tuple[float, float, float]:
    if pos_bucket == "TE":
        arch = infer_te_archetype(player_profile, team_raw=team_raw)
        return TE_ARCHETYPE_PREFS.get(arch, TE_ARCHETYPE_PREFS["move_te_hybrid"])
    if pos_bucket == "WR":
        return (0.42, 0.38, 0.9)
    if pos_bucket == "RB":
        return (0.52, 0.45, 0.38)
    return (0.5, 0.5, 0.5)


def _player_archetype_vector(
    player_profile: Dict[str, Any],
    team_raw: Dict[str, float] | None = None,
) -> np.ndarray:
    pos_bucket = str(player_profile.get("pos_bucket") or bucket_for_combine_pos(str(player_profile.get("pos", ""))))
    height_in = float(player_profile.get("height_in", float("nan")))
    weight_lb = float(player_profile.get("weight_lb", float("nan")))
    pb = pos_bucket
    spread_affinity = 0.55
    vertical = 0.5
    inline = 0.5
    pass_rush = 0.5
    coverage = 0.5

    if pb in {"WR", "RB", "TE"}:
        spread_affinity = 0.72 if pb == "WR" else 0.62
        vertical = 0.75 if pb == "WR" else 0.45
        inline = 0.35 if pb == "TE" else 0.4
    if pb in {"QB"}:
        spread_affinity = 0.68
        vertical = 0.55
    if pb in {"OT", "IOL"}:
        spread_affinity = 0.5
        inline = 0.85
    if pb in {"EDGE", "IDL"}:
        pass_rush = 0.9
        inline = 0.65 if pb == "IDL" else 0.55
    if pb in {"CB", "SAF"}:
        coverage = 0.9
        vertical = 0.65 if pb == "CB" else 0.55
    if pb in {"LB"}:
        coverage = 0.55
        pass_rush = 0.45

    hn = (height_in - 70.0) / 8.0 if not math.isnan(height_in) else 0.0
    wn = (weight_lb - 240.0) / 120.0 if not math.isnan(weight_lb) else 0.0
    hn = max(-1.0, min(1.0, hn))
    wn = max(-1.0, min(1.0, wn))

    v7 = np.array(
        [
            spread_affinity + 0.08 * hn,
            0.55 + 0.1 * wn,
            0.02 * vertical + 0.01 * hn,
            0.02 * inline + 0.015 * wn,
            0.5 + 0.05 * coverage,
            -0.02 * pass_rush,
            -0.02 * coverage,
        ],
        dtype=float,
    )
    pg = _player_pass_game_affinity(pb, player_profile, team_raw)
    return np.concatenate([v7, np.array(pg, dtype=float)])


def compute_scheme_fit(
    player_profile: Dict[str, Any],
    team_profile: Dict[str, Any] | None = None,
    *,
    team_context: TeamContext | None = None,
) -> Dict[str, Any]:
    """
    Cosine similarity between team tendency vector (PBP + pass-game shares) and player archetype.
    Pass ``team_context`` to reuse a pre-built profile and apply trend-based bonuses without re-querying.
    """
    if team_context is not None:
        team_profile = team_context.scheme_profile
    if team_profile is None:
        raise ValueError("team_profile or team_context is required")

    team_vec = np.array(team_profile["vector"], dtype=float)
    raw = team_profile.get("raw") or {}
    pvec = _player_archetype_vector(player_profile, raw)
    m = min(len(team_vec), len(pvec))
    a = _unit(team_vec[:m])
    b = _unit(pvec[:m])
    sim = float(np.dot(a, b))
    score = max(0.0, min(100.0, (sim + 1.0) * 50.0))

    pos = str(player_profile.get("pos_bucket") or bucket_for_combine_pos(str(player_profile.get("pos", ""))))
    extra: Dict[str, Any] = {
        "te_scheme_archetype": None,
        "te_share_fit_score": None,
        "edge_pressure_trend_bonus": None,
        "ot_pass_rate_fit_bonus": None,
        "wr_scheme_signals": None,
    }

    edge_trend = float(team_context.edge_pressure_trend) if team_context is not None else 0.0

    if pos == "TE":
        arch = infer_te_archetype(player_profile, team_raw=raw)
        ts = te_share_fit_score(raw, arch)
        extra["te_scheme_archetype"] = arch
        extra["te_share_fit_score"] = round(ts, 4)
        score = min(100.0, max(0.0, score * max(0.38, ts)))

    if pos == "EDGE":
        eb = edge_trend_fit_bonus(edge_trend)
        extra["edge_pressure_trend_bonus"] = round(eb, 4)
        score = min(100.0, score + eb * 100.0)

    if pos in {"OT", "IOL"}:
        ob = ot_pass_rate_fit_bonus(float(raw.get("off_pass_rate", 0.5)))
        extra["ot_pass_rate_fit_bonus"] = round(ob, 4)
        score = min(100.0, score + ob * 100.0)

    if pos == "WR":
        extra["wr_scheme_signals"] = wr_scheme_signals(raw)

    return {
        "scheme_fit_score": round(score, 2),
        "cosine_similarity": round(sim, 4),
        "dimensions_used": m,
        "scheme_fit_detail_extra": extra,
    }
