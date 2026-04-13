from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from superbowlengine.config import DEFAULT_CONFIG
from superbowlengine.data import get_pbp, get_schedules
from superbowlengine.features.sos import build_game_results, compute_sos, zscore_sos


@dataclass(frozen=True)
class TeamEfficiency:
    team: str
    # Offense
    off_epa_per_play: float
    off_success_rate: float
    off_explosive_rate: float
    off_early_down_success: float
    off_third_down_conv: float
    off_redzone_td_rate: float
    off_sack_rate_allowed: Optional[float]
    off_plays: int
    # Defense (allowed)
    def_epa_per_play_allowed: float
    def_success_rate_allowed: float
    def_explosive_rate_allowed: float
    def_early_down_success_allowed: float
    def_third_down_conv_allowed: float
    def_redzone_td_rate_allowed: float
    def_sack_rate_forced: Optional[float]
    def_plays: int
    # Context
    sos_z: float
    recent_off_epa_per_play: Optional[float] = None
    recent_def_epa_per_play_allowed: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_mean(s: pd.Series) -> float:
    s2 = pd.to_numeric(s, errors="coerce")
    if s2.dropna().empty:
        return 0.0
    return float(s2.mean())


def _safe_rate(mask: pd.Series) -> float:
    m = mask.fillna(False)
    if len(m) == 0:
        return 0.0
    return float(m.mean())


def _explosive_mask(df: pd.DataFrame) -> pd.Series:
    # NFL-ish explosive thresholds
    is_pass = df.get("play_type", pd.Series(index=df.index, dtype="object")).astype(str).str.lower().eq("pass")
    is_run = df.get("play_type", pd.Series(index=df.index, dtype="object")).astype(str).str.lower().eq("run")
    yg = pd.to_numeric(df.get("yards_gained", pd.Series(index=df.index, dtype="float")), errors="coerce").fillna(0.0)
    return (is_pass & (yg >= 15)) | (is_run & (yg >= 10))


def _success_mask(df: pd.DataFrame) -> pd.Series:
    if "success" in df.columns:
        return pd.to_numeric(df["success"], errors="coerce").fillna(0).astype(int).eq(1)
    # Fallback: touchdown OR gain >= ydstogo (rough proxy)
    td = pd.to_numeric(df.get("touchdown", 0), errors="coerce").fillna(0).astype(int).eq(1)
    yg = pd.to_numeric(df.get("yards_gained", 0), errors="coerce").fillna(0.0)
    togo = pd.to_numeric(df.get("ydstogo", 0), errors="coerce").fillna(0.0)
    return td | (yg >= togo)


def _third_down_conv_mask(df: pd.DataFrame) -> pd.Series:
    down = pd.to_numeric(df.get("down", pd.NA), errors="coerce")
    is_third = down.eq(3)
    if "first_down" in df.columns:
        fd = pd.to_numeric(df.get("first_down", 0), errors="coerce").fillna(0).astype(int).eq(1)
        return is_third & fd
    yg = pd.to_numeric(df.get("yards_gained", 0), errors="coerce").fillna(0.0)
    togo = pd.to_numeric(df.get("ydstogo", 0), errors="coerce").fillna(0.0)
    return is_third & (yg >= togo)


def _redzone_td_mask(df: pd.DataFrame) -> pd.Series:
    yl = pd.to_numeric(df.get("yardline_100", pd.NA), errors="coerce")
    in_rz = yl.le(20)
    td = pd.to_numeric(df.get("touchdown", 0), errors="coerce").fillna(0).astype(int).eq(1)
    return in_rz & td


def _sack_mask(df: pd.DataFrame) -> Optional[pd.Series]:
    if "sack" not in df.columns:
        return None
    return pd.to_numeric(df["sack"], errors="coerce").fillna(0).astype(int).eq(1)


def _filter_plays(df: pd.DataFrame) -> pd.DataFrame:
    # Focus on scrimmage plays where posteam/defteam exist and play_type is run/pass.
    pt = df.get("play_type", pd.Series(index=df.index, dtype="object")).astype(str).str.lower()
    ok = pt.isin(["run", "pass"])
    out = df[ok].copy()
    out = out[pd.notna(out.get("posteam")) & pd.notna(out.get("defteam"))].copy()
    return out


def _recent_game_ids(pbp: pd.DataFrame, team: str, n_games: int = 6) -> list[str]:
    if pbp.empty or "game_id" not in pbp.columns:
        return []
    df = pbp[pbp["posteam"].astype(str) == team]
    if df.empty:
        return []
    if "week" in df.columns:
        weeks = pd.to_numeric(df["week"], errors="coerce")
        df = df.assign(_week=weeks)
        gids = (
            df[["game_id", "_week"]]
            .dropna()
            .drop_duplicates()
            .sort_values("_week")
            .tail(n_games)["game_id"]
            .astype(str)
            .tolist()
        )
        return gids
    return df["game_id"].dropna().astype(str).drop_duplicates().tail(n_games).tolist()


def _compute_team_efficiency(pbp_all: pd.DataFrame, schedules: pd.DataFrame, team: str, *, sos_z_map: Dict[str, float]) -> TeamEfficiency:
    df = _filter_plays(pbp_all)
    # Offense plays
    off = df[df["posteam"].astype(str) == team]
    # Defense plays (allowed)
    dff = df[df["defteam"].astype(str) == team]

    # EPA
    off_epa = _safe_mean(off.get("epa", pd.Series(dtype="float")))
    def_epa_allowed = _safe_mean(dff.get("epa", pd.Series(dtype="float")))

    # Success/explosive
    off_success = _safe_rate(_success_mask(off))
    def_success_allowed = _safe_rate(_success_mask(dff))
    off_explosive = _safe_rate(_explosive_mask(off))
    def_explosive_allowed = _safe_rate(_explosive_mask(dff))

    # Early-down success (down <= 2)
    off_down = pd.to_numeric(off.get("down", pd.NA), errors="coerce")
    def_down = pd.to_numeric(dff.get("down", pd.NA), errors="coerce")
    off_early = off[off_down.le(2)]
    def_early = dff[def_down.le(2)]
    off_early_succ = _safe_rate(_success_mask(off_early))
    def_early_succ_allowed = _safe_rate(_success_mask(def_early))

    # Third down conversion
    off_third_total = int(pd.to_numeric(off.get("down", pd.NA), errors="coerce").eq(3).sum())
    def_third_total = int(pd.to_numeric(dff.get("down", pd.NA), errors="coerce").eq(3).sum())
    off_third_conv = float(_third_down_conv_mask(off).sum()) / off_third_total if off_third_total else 0.0
    def_third_conv_allowed = float(_third_down_conv_mask(dff).sum()) / def_third_total if def_third_total else 0.0

    # Red zone TD rate (proxy): TDs on plays with yardline_100 <= 20 / red zone plays
    off_rz_plays = int(pd.to_numeric(off.get("yardline_100", pd.NA), errors="coerce").le(20).sum())
    def_rz_plays = int(pd.to_numeric(dff.get("yardline_100", pd.NA), errors="coerce").le(20).sum())
    off_rz_td = float(_redzone_td_mask(off).sum()) / off_rz_plays if off_rz_plays else 0.0
    def_rz_td_allowed = float(_redzone_td_mask(dff).sum()) / def_rz_plays if def_rz_plays else 0.0

    # Sack rates
    sack_off_mask = _sack_mask(off)
    sack_def_mask = _sack_mask(dff)
    off_sack_allowed = None
    def_sack_forced = None
    # Use pass plays as dropbacks proxy
    off_pass = off[off.get("play_type", "").astype(str).str.lower().eq("pass")]
    def_pass = dff[dff.get("play_type", "").astype(str).str.lower().eq("pass")]
    if sack_off_mask is not None and len(off_pass) > 0:
        off_sack_allowed = float(sack_off_mask.loc[off_pass.index].mean())
    if sack_def_mask is not None and len(def_pass) > 0:
        def_sack_forced = float(sack_def_mask.loc[def_pass.index].mean())

    # Recent form (EPA/play)
    recent_gids = _recent_game_ids(pbp_all, team, n_games=6)
    recent_off = off[off["game_id"].astype(str).isin(recent_gids)] if recent_gids else off.iloc[0:0]
    recent_def = dff[dff["game_id"].astype(str).isin(recent_gids)] if recent_gids else dff.iloc[0:0]
    recent_off_epa = _safe_mean(recent_off.get("epa", pd.Series(dtype="float"))) if not recent_off.empty else None
    recent_def_epa = _safe_mean(recent_def.get("epa", pd.Series(dtype="float"))) if not recent_def.empty else None

    return TeamEfficiency(
        team=team,
        off_epa_per_play=off_epa,
        off_success_rate=off_success,
        off_explosive_rate=off_explosive,
        off_early_down_success=off_early_succ,
        off_third_down_conv=off_third_conv,
        off_redzone_td_rate=off_rz_td,
        off_sack_rate_allowed=off_sack_allowed,
        off_plays=int(len(off)),
        def_epa_per_play_allowed=def_epa_allowed,
        def_success_rate_allowed=def_success_allowed,
        def_explosive_rate_allowed=def_explosive_allowed,
        def_early_down_success_allowed=def_early_succ_allowed,
        def_third_down_conv_allowed=def_third_conv_allowed,
        def_redzone_td_rate_allowed=def_rz_td_allowed,
        def_sack_rate_forced=def_sack_forced,
        def_plays=int(len(dff)),
        sos_z=float(sos_z_map.get(team, 0.0)),
        recent_off_epa_per_play=recent_off_epa,
        recent_def_epa_per_play_allowed=recent_def_epa,
    )


@dataclass(frozen=True)
class MatchupFeatures:
    season: int
    mode: str
    team_a: str
    team_b: str
    # Primary stable edges (A minus B, already offense-vs-defense oriented)
    epa_edge: float
    success_edge: float
    explosive_edge: float
    early_down_success_edge: float
    third_down_edge: float
    redzone_edge: float
    sack_edge: float
    sos_edge: float
    recent_epa_edge: float
    # Diagnostics
    team_a_eff: TeamEfficiency
    team_b_eff: TeamEfficiency

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["team_a_eff"] = self.team_a_eff.to_dict()
        d["team_b_eff"] = self.team_b_eff.to_dict()
        return d


def _select_pbp_by_mode(pbp: pd.DataFrame, mode: str) -> pd.DataFrame:
    if "season_type" not in pbp.columns:
        return pbp
    st = pbp["season_type"].astype(str).str.upper()
    if mode == "regular":
        return pbp[st == "REG"].copy()
    if mode == "postseason":
        return pbp[st == "POST"].copy()
    return pbp.copy()


@lru_cache(maxsize=16)
def _load_pbp_and_schedules_for_efficiency(season: int) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
    # Pull additional columns needed for efficiency features without changing the existing 5 Keys pipelines.
    extra_cols = [
        "epa",
        "success",
        "sack",
        "first_down",
        "season",
    ]
    cols = list(dict.fromkeys(list(DEFAULT_CONFIG.pbp_columns) + extra_cols))
    pbp = get_pbp([season], season_type="ALL", columns=cols)
    schedules = get_schedules([season])

    # SOS z-score based on REG results where possible
    sos_z: Dict[str, float] = {}
    try:
        game_results_reg = build_game_results(pbp, season_type="REG")
        if not game_results_reg.empty:
            teams = set(game_results_reg["home_team"]).union(set(game_results_reg["away_team"]))
            sos_raw = {t: compute_sos(game_results_reg, t) for t in teams}
            sos_z = {k: float(v) for k, v in zscore_sos(sos_raw).items()}
    except Exception:
        sos_z = {}

    return pbp, schedules, sos_z


def build_matchup_features(season: int, team_a: str, team_b: str, *, mode: str = "opp_weighted") -> MatchupFeatures:
    pbp_all, schedules, sos_z = _load_pbp_and_schedules_for_efficiency(season)
    pbp = _select_pbp_by_mode(pbp_all, mode)

    eff_a = _compute_team_efficiency(pbp, schedules, team_a, sos_z_map=sos_z)
    eff_b = _compute_team_efficiency(pbp, schedules, team_b, sos_z_map=sos_z)

    # Offense A vs Defense B, minus Offense B vs Defense A (symmetrized)
    epa_edge = (eff_a.off_epa_per_play - eff_b.def_epa_per_play_allowed) - (eff_b.off_epa_per_play - eff_a.def_epa_per_play_allowed)
    success_edge = (eff_a.off_success_rate - eff_b.def_success_rate_allowed) - (eff_b.off_success_rate - eff_a.def_success_rate_allowed)
    explosive_edge = (eff_a.off_explosive_rate - eff_b.def_explosive_rate_allowed) - (eff_b.off_explosive_rate - eff_a.def_explosive_rate_allowed)
    early_edge = (eff_a.off_early_down_success - eff_b.def_early_down_success_allowed) - (eff_b.off_early_down_success - eff_a.def_early_down_success_allowed)
    third_edge = (eff_a.off_third_down_conv - eff_b.def_third_down_conv_allowed) - (eff_b.off_third_down_conv - eff_a.def_third_down_conv_allowed)
    rz_edge = (eff_a.off_redzone_td_rate - eff_b.def_redzone_td_rate_allowed) - (eff_b.off_redzone_td_rate - eff_a.def_redzone_td_rate_allowed)

    # Sack edge: lower sack rate allowed (off) + higher sack rate forced (def) is better
    def _nz(x: Optional[float]) -> float:
        return float(x) if (x is not None and x == x) else 0.0

    sack_edge = (
        (-_nz(eff_a.off_sack_rate_allowed) + _nz(eff_a.def_sack_rate_forced))
        - (-_nz(eff_b.off_sack_rate_allowed) + _nz(eff_b.def_sack_rate_forced))
    )

    sos_edge = eff_a.sos_z - eff_b.sos_z

    recent_a = eff_a.recent_off_epa_per_play if eff_a.recent_off_epa_per_play is not None else eff_a.off_epa_per_play
    recent_b = eff_b.recent_off_epa_per_play if eff_b.recent_off_epa_per_play is not None else eff_b.off_epa_per_play
    recent_epa_edge = float(recent_a - recent_b)

    return MatchupFeatures(
        season=season,
        mode=mode,
        team_a=team_a,
        team_b=team_b,
        epa_edge=float(epa_edge),
        success_edge=float(success_edge),
        explosive_edge=float(explosive_edge),
        early_down_success_edge=float(early_edge),
        third_down_edge=float(third_edge),
        redzone_edge=float(rz_edge),
        sack_edge=float(sack_edge),
        sos_edge=float(sos_edge),
        recent_epa_edge=float(recent_epa_edge),
        team_a_eff=eff_a,
        team_b_eff=eff_b,
    )

