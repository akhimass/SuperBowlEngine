"""
QB Production Score (Postseason Impact Index): non-duplicative of top-slide metrics.

- Drive Sustainability (40%): 3rd down conversion on QB plays, sack avoidance.
- Situational Execution (40%): RZ TD rate on QB-led drives, leverage TO avoidance (attributed).
- Off-Script Value (20%): Scramble rate/yards, pressure-to-sack proxy.

Uses PBP with graceful fallbacks when columns are missing. Opponent defense adjustment
and QB-fault vs non-QB-fault turnover attribution.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from superbowlengine.utils.math import safe_div

from superbowlengine.qb.validate import _qb_name_matches


@dataclass
class QBProdConfig:
    big_pass_yards: int = 15
    scramble_min_yards: int = 5
    eps: float = 1e-9
    w_drive: float = 0.40
    w_situational: float = 0.40
    w_offscript: float = 0.20
    w_def_adj: float = 0.25
    qb_fault_int_weight: float = 1.0
    non_qb_fault_int_weight: float = 0.35
    qb_fault_fum_weight: float = 0.75
    non_qb_fault_fum_weight: float = 0.25
    # Normalization ranges for 0-100 component scores (postseason-typical)
    third_down_pct_range: Tuple[float, float] = (25.0, 55.0)
    sack_avoid_range: Tuple[float, float] = (85.0, 98.0)  # 100 - sack_rate
    rz_td_pct_range: Tuple[float, float] = (30.0, 80.0)
    leverage_to_avoid_range: Tuple[float, float] = (0.0, 0.5)  # weighted TO per leverage play; lower better
    scramble_epa_proxy_range: Tuple[float, float] = (0.0, 25.0)  # scramble yds/g or similar
    pressure_to_sack_range: Tuple[float, float] = (0.05, 0.35)  # sacks/(qb_hits+sacks); lower better


def compute_opponent_def_strength(pbp_reg: pd.DataFrame) -> Dict[str, float]:
    """
    Defense strength index per team from REG season only.

    Requirements:
      - Use defteam if present; else infer defense as opponent of posteam using home_team/away_team.
      - Only real offensive plays: play_type in {run, pass, sack}
      - Exclude no_play==1 if present
      - Exclude qb_kneel==1, qb_spike==1 if present
      - Prefer epa if present; fallback to success
      - Toughness raw = -mean(epa_allowed) or -mean(success_allowed)
      - Z-score across teams: higher z = tougher
    """
    if pbp_reg.empty:
        return {}
    df = pbp_reg.copy()

    # Play filters
    if "play_type" in df.columns:
        df = df[df["play_type"].isin(["run", "pass", "sack"])]
    if "no_play" in df.columns:
        df = df[~df["no_play"].eq(1).fillna(False)]
    for col in ["qb_kneel", "qb_spike"]:
        if col in df.columns:
            df = df[df[col].ne(1)]

    # Determine defense team
    if "defteam" not in df.columns:
        if "posteam" in df.columns and "home_team" in df.columns and "away_team" in df.columns:
            def _infer_defteam(row: pd.Series) -> str:
                # defense = opponent of posteam
                if row["posteam"] == row["home_team"]:
                    return str(row["away_team"])
                return str(row["home_team"])

            df = df.copy()
            df["defteam"] = df.apply(_infer_defteam, axis=1)
        else:
            return {}

    df = df[df["defteam"].notna() & (df["defteam"].astype(str).str.len() > 0)]

    # Prefer EPA; fallback success
    metric = None
    if "epa" in df.columns:
        df = df.copy()
        df["epa"] = pd.to_numeric(df["epa"], errors="coerce")
        if df["epa"].notna().any():
            metric = "epa"
    if metric is None and "success" in df.columns:
        df = df.copy()
        df["success"] = pd.to_numeric(df["success"], errors="coerce")
        if df["success"].notna().any():
            metric = "success"
    if metric is None:
        return {}

    grouped = df.groupby("defteam")[metric].mean().reset_index(name="allowed")
    grouped["toughness_raw"] = -grouped["allowed"]  # lower allowed => tougher => higher toughness

    mu = float(grouped["toughness_raw"].mean())
    sd = float(grouped["toughness_raw"].std())
    if not (sd and sd > 0):
        return {str(r["defteam"]): 0.0 for _, r in grouped.iterrows()}
    grouped["def_z"] = (grouped["toughness_raw"] - mu) / sd
    return {str(r["defteam"]): round(float(r["def_z"]), 4) for _, r in grouped.iterrows()}


def validate_def_strength(def_z: Dict[str, float]) -> None:
    """
    Sanity checks for defense z-scores:
      - 20+ teams present
      - mean approx 0
      - std approx 1
    Raises ValueError with helpful diagnostics when violated.
    """
    if not def_z:
        raise ValueError("def_z is empty; cannot validate defense strength.")
    vals = [float(v) for v in def_z.values()]
    n = len(vals)
    if n < 20:
        raise ValueError(f"def_z has too few teams ({n}); expected 20+ (ideally 32).")
    s = pd.Series(vals)
    mu = float(s.mean())
    sd = float(s.std())
    if abs(mu) > 0.15:
        raise ValueError(f"def_z mean too far from 0 (mean={mu:.3f}); check toughness calculation.")
    if sd < 0.5 or sd > 1.5:
        raise ValueError(f"def_z std not ~1 (std={sd:.3f}); check z-scoring across teams.")


def _is_qb_play(row: pd.Series, team: str, qb: str) -> bool:
    """True if this play is a QB play for the given team (passer or rusher matches qb name/token)."""
    if row.get("posteam") != team:
        return False
    if "passer_player_name" in row.index and _qb_name_matches(row.get("passer_player_name", ""), qb):
        return True
    if "rusher_player_name" in row.index and _qb_name_matches(row.get("rusher_player_name", ""), qb):
        return True
    return False


def _team_has_qb_columns(pbp: pd.DataFrame) -> bool:
    return "passer_player_name" in pbp.columns or "rusher_player_name" in pbp.columns


def qb_turnover_attribution(pbp: pd.DataFrame, qb: str, team: str) -> Dict[str, float]:
    """
    Return counts for qb_fault_to and non_qb_fault_to using heuristics.
    Keys: qb_fault_int, non_qb_fault_int, qb_fault_fum, non_qb_fault_fum,
          qb_fault_to (weighted), non_qb_fault_to (weighted), weighted_turnovers,
          debug_counts (total_int, qb_fault_int, non_qb_fault_int, total_fum_lost_on_team, qb_fault_fum, non_qb_fault_fum),
          notes (list of fallbacks used).
    INT: only plays where interception==1 AND passer_player_name matches qb.
    Fumble: QB-fault = sack fumble or QB run fumble lost; non-QB = team fumble lost otherwise.
    """
    cfg = QBProdConfig()
    notes: List[str] = []
    team_pbp = pbp[(pbp["posteam"] == team)].copy()
    if team_pbp.empty:
        notes.append("No team plays in PBP for this team.")
        return {
            "qb_fault_int": 0.0, "non_qb_fault_int": 0.0,
            "qb_fault_fum": 0.0, "non_qb_fault_fum": 0.0,
            "qb_fault_to": 0.0, "non_qb_fault_to": 0.0, "weighted_turnovers": 0.0,
            "debug_counts": {"total_int": 0, "qb_fault_int": 0, "non_qb_fault_int": 0, "total_fum_lost_on_team": 0, "qb_fault_fum": 0, "non_qb_fault_fum": 0},
            "notes": notes,
        }
    # --- INT: only where passer is this QB
    total_int = int(team_pbp.get("interception", pd.Series(dtype=float)).fillna(0).sum())
    qb_fault_int = 0.0
    non_qb_fault_int = 0.0
    if "passer_player_name" not in team_pbp.columns:
        notes.append("INT attribution skipped: passer_player_name missing; cannot assign INT to QB.")
        if total_int > 0:
            notes.append(f"Team had {total_int} INT(s); counted as 0 for weighted TO (no passer id).")
    else:
        int_plays = team_pbp[team_pbp.get("interception", pd.Series(dtype=float)).fillna(0) == 1]
        int_plays_qb = int_plays[int_plays["passer_player_name"].apply(lambda x: _qb_name_matches(x, qb))]
        for _, row in int_plays_qb.iterrows():
            air_yds = row.get("air_yards")
            if pd.isna(air_yds):
                air_yds = -999
            _pd = row.get("pass_depth")
            pass_depth = "" if (pd.isna(_pd) or _pd is None) else str(_pd).lower()
            if air_yds >= 8 or pass_depth in ("deep", "intermediate"):
                qb_fault_int += 1.0
            else:
                tipped = row.get("tipped_pass", 0)
                if pd.isna(tipped):
                    tipped = 0
                _sg = row.get("shotgun", 1)
                _sc = row.get("screen", 0)
                screen = 1 if (not pd.isna(_sg) and _sg == 0 and str(_sc) == "1") else 0
                if tipped == 1 or (not pd.isna(_sg) and _sg == 0 and screen):
                    non_qb_fault_int += 1.0
                elif air_yds < 8 or pass_depth == "short":
                    non_qb_fault_int += 1.0
                else:
                    qb_fault_int += 1.0
        if total_int > 0 and (qb_fault_int + non_qb_fault_int) == 0:
            notes.append(f"Team had {total_int} INT(s) but none with passer_player_name matching QB; possible name mismatch.")
    # --- Fumble lost
    total_fum_lost_on_team = 0
    if "fumble_lost" in team_pbp.columns:
        total_fum_lost_on_team = int(team_pbp["fumble_lost"].fillna(0).sum())
    qb_fault_fum = 0.0
    non_qb_fault_fum = 0.0
    if "fumble_lost" in team_pbp.columns and total_fum_lost_on_team > 0:
        fum = team_pbp[team_pbp["fumble_lost"].eq(1).fillna(False)]
        for _, row in fum.iterrows():
            if _team_has_qb_columns(team_pbp) and not _is_qb_play(row, team, qb):
                non_qb_fault_fum += 1.0
                continue
            _qsf = row.get("qb_sack_fumble", 0)
            if "qb_sack_fumble" in row.index and not pd.isna(_qsf) and _qsf == 1:
                qb_fault_fum += 1.0
            elif str(row.get("play_type")) == "sack" and (not pd.isna(row.get("fumble_lost")) and row.get("fumble_lost") == 1):
                qb_fault_fum += 1.0
            elif _is_qb_play(row, team, qb) and str(row.get("play_type")) == "run":
                qb_fault_fum += 1.0
            else:
                non_qb_fault_fum += 1.0
    else:
        if total_fum_lost_on_team == 0 and "fumble_lost" not in team_pbp.columns:
            notes.append("Fumble attribution skipped: fumble_lost column missing.")
    if total_fum_lost_on_team > 0 and (qb_fault_fum + non_qb_fault_fum) == 0:
        notes.append(f"Team had {total_fum_lost_on_team} fumble(s) lost but attribution could not assign (check play_type/qb_sack_fumble).")

    qb_fault_to = cfg.qb_fault_int_weight * qb_fault_int + cfg.qb_fault_fum_weight * qb_fault_fum
    non_qb_fault_to = cfg.non_qb_fault_int_weight * non_qb_fault_int + cfg.non_qb_fault_fum_weight * non_qb_fault_fum
    weighted_turnovers = qb_fault_to + non_qb_fault_to
    return {
        "qb_fault_int": qb_fault_int,
        "non_qb_fault_int": non_qb_fault_int,
        "qb_fault_fum": qb_fault_fum,
        "non_qb_fault_fum": non_qb_fault_fum,
        "qb_fault_to": round(qb_fault_to, 3),
        "non_qb_fault_to": round(non_qb_fault_to, 3),
        "weighted_turnovers": round(weighted_turnovers, 3),
        "debug_counts": {
            "total_int": int(total_int),
            "qb_fault_int": int(qb_fault_int),
            "non_qb_fault_int": int(non_qb_fault_int),
            "total_fum_lost_on_team": int(total_fum_lost_on_team),
            "qb_fault_fum": int(qb_fault_fum),
            "non_qb_fault_fum": int(non_qb_fault_fum),
        },
        "notes": notes,
    }


def _opponent_for_game(schedules: pd.DataFrame, game_id: str, team: str) -> str:
    if schedules is None or schedules.empty:
        return ""
    row = schedules[schedules["game_id"] == game_id]
    if row.empty or "home_team" not in row.columns:
        return ""
    r = row.iloc[0]
    return str(r["away_team"]) if r.get("home_team") == team else str(r.get("home_team", ""))


def _game_round(schedules: pd.DataFrame, game_id: str) -> str:
    if schedules is None or "game_type" not in schedules.columns:
        return ""
    row = schedules[schedules["game_id"] == game_id]
    if row.empty:
        return ""
    return str(row.iloc[0].get("game_type", ""))


def qb_components_per_game(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    qb: str,
    team: str,
    def_strength: Dict[str, float],
    config: Optional[QBProdConfig] = None,
    game_ids: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Compute per-game component metrics (auditable). Returns DataFrame with columns:
    game_id, opp, is_home, round, third_down_att_qb, third_down_conv_qb, third_down_pct_qb,
    dropbacks, sacks, sack_rate, rz_trips_qb_led, rz_td_drives_qb_led, rz_td_pct,
    scrambles, scramble_yds, qb_fault_to_weighted, non_qb_fault_to_weighted, leverage_to_weighted, opp_def_z.
    """
    cfg = config or QBProdConfig()
    team_pbp = pbp_post[pbp_post["posteam"] == team].copy()
    if game_ids is not None:
        team_pbp = team_pbp[team_pbp["game_id"].isin(game_ids)]
    if team_pbp.empty:
        return pd.DataFrame()
    has_qb_names = _team_has_qb_columns(team_pbp)
    qb_mask = team_pbp.apply(lambda r: _is_qb_play(r, team, qb), axis=1) if has_qb_names else pd.Series(True, index=team_pbp.index)
    rows = []
    for gid in team_pbp["game_id"].dropna().unique().tolist():
        g = team_pbp[team_pbp["game_id"] == gid]
        gm = g[qb_mask.reindex(g.index, fill_value=False)] if has_qb_names else g
        opp = _opponent_for_game(schedules, gid, team)
        is_home = (g["home_team"].iloc[0] == team) if "home_team" in g.columns else None
        rnd = _game_round(schedules, gid)
        # 3rd down QB
        third = g[(g["down"] == 3) & (qb_mask.reindex(g.index, fill_value=False) if has_qb_names else True)]
        third_att = len(third)
        if third_att > 0 and "first_down" in third.columns:
            conv = ((third["first_down"].fillna(0) == 1) | (third.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1)).sum()
        else:
            conv = int((third.get("yards_gained", pd.Series(dtype=float)).fillna(0) >= third.get("ydstogo", pd.Series(dtype=float)).fillna(0)).sum()) if third_att else 0
        third_pct = 100.0 * safe_div(conv, third_att) if third_att else 0.0
        # Dropbacks / sacks
        db = gm[gm["play_type"].isin(["pass", "sack"])] if "play_type" in gm.columns else gm
        dropbacks = len(db)
        sacks = int(db["play_type"].eq("sack").sum()) if "play_type" in db.columns else 0
        sack_rate = 100.0 * safe_div(sacks, dropbacks) if dropbacks else 0.0
        # RZ QB-led
        drives = g.groupby(["game_id", "drive"])
        qb_led = set(drives.groups.keys()) if not has_qb_names else set()
        if has_qb_names:
            for (_, did), grp in drives:
                if grp.apply(lambda r: _is_qb_play(r, team, qb), axis=1).any():
                    qb_led.add((gid, did))
        rz_trips, rz_td = 0, 0
        for (_, did), grp in drives:
            if (gid, did) not in qb_led:
                continue
            if (grp["yardline_100"].fillna(999) <= 20).any():
                rz_trips += 1
                if (grp.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1).any():
                    rz_td += 1
        rz_pct = 100.0 * safe_div(rz_td, rz_trips) if rz_trips else 0.0
        # Scramble
        if "qb_scramble" in g.columns:
            scr = g[g["qb_scramble"].fillna(0) == 1]
        else:
            scr = g[(g["play_type"] == "run") & (g.get("rusher_player_name", pd.Series(dtype=str)).apply(lambda x: _qb_name_matches(x, qb)))] if has_qb_names else pd.DataFrame()
        scramble_yds = scr["yards_gained"].fillna(0).sum() if len(scr) else 0.0
        # TO attribution for this game only
        attr = qb_turnover_attribution(g, qb, team)
        qb_to = attr["qb_fault_to"]
        non_to = attr["non_qb_fault_to"]
        lev_to = qb_to + non_to
        opp_z = def_strength.get(str(opp), 0.0)
        rows.append({
            "game_id": gid,
            "opp": opp,
            "is_home": is_home,
            "round": rnd,
            "third_down_att_qb": third_att,
            "third_down_conv_qb": int(conv),
            "third_down_pct_qb": round(third_pct, 1),
            "dropbacks": dropbacks,
            "sacks": sacks,
            "sack_rate": round(sack_rate, 1),
            "rz_trips_qb_led": rz_trips,
            "rz_td_drives_qb_led": rz_td,
            "rz_td_pct": round(rz_pct, 1),
            "scrambles": len(scr),
            "scramble_yds": int(scramble_yds),
            "qb_fault_to_weighted": qb_to,
            "non_qb_fault_to_weighted": non_to,
            "leverage_to_weighted": lev_to,
            "opp_def_z": round(opp_z, 3),
        })
    return pd.DataFrame(rows)


def qb_production_components(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    qb: str,
    team: str,
    def_strength: Dict[str, float],
    config: Optional[QBProdConfig] = None,
    game_ids: Optional[List[str]] = None,
) -> Dict[str, float]:
    """
    Compute component scores by aggregating from per-game table.
    Uses sum(conv)/sum(att) for 3rd down, sum(td_drives)/sum(trips) for RZ, 1 - sacks/dropbacks for sack avoidance.
    If game_ids provided, only those games are included (post validation).
    """
    cfg = config or QBProdConfig()
    per_game = qb_components_per_game(pbp_post, schedules, qb, team, def_strength, config, game_ids)
    if per_game.empty:
        return _empty_components(team, def_strength, cfg)
    # Aggregate: 3rd down pct = sum(conv)/sum(att)
    total_third_att = per_game["third_down_att_qb"].sum()
    total_third_conv = per_game["third_down_conv_qb"].sum()
    third_conv_pct = 100.0 * safe_div(total_third_conv, total_third_att) if total_third_att else 0.0
    total_dropbacks = per_game["dropbacks"].sum()
    total_sacks = per_game["sacks"].sum()
    sack_avoidance = 100.0 - (100.0 * safe_div(total_sacks, total_dropbacks) if total_dropbacks else 0.0)
    rz_trips = per_game["rz_trips_qb_led"].sum()
    rz_td_drives = per_game["rz_td_drives_qb_led"].sum()
    rz_td_pct = 100.0 * safe_div(rz_td_drives, rz_trips) if rz_trips else 0.0
    games = len(per_game)
    scramble_yds_per_game = safe_div(per_game["scramble_yds"].sum(), games)
    # Leverage TO: total weighted TO across games; leverage plays from full team_pbp for rate
    team_pbp = pbp_post[(pbp_post["posteam"] == team)]
    if game_ids is not None:
        team_pbp = team_pbp[team_pbp["game_id"].isin(game_ids)]
    leverage_plays = team_pbp[((team_pbp["down"] == 3) | (team_pbp["yardline_100"].fillna(999) <= 20))]
    n_leverage = len(leverage_plays)
    weighted_to = per_game["leverage_to_weighted"].sum()
    leverage_to_per_play = safe_div(weighted_to, n_leverage) if n_leverage else 0.0
    leverage_avoid_score = 100.0 - min(100.0, leverage_to_per_play * 200)
    attr = qb_turnover_attribution(team_pbp, qb, team)
    # Pressure-to-sack from full team_pbp
    if "qb_hit" in team_pbp.columns and "play_type" in team_pbp.columns:
        qb_hits = int(team_pbp["qb_hit"].fillna(0).sum())
        sack_count = int(team_pbp[team_pbp["play_type"] == "sack"].shape[0])
        pressure_to_sack = safe_div(sack_count, qb_hits + sack_count) if (qb_hits + sack_count) > 0 else 0.0
    else:
        pressure_to_sack = 0.0
    avg_def_z = per_game["opp_def_z"].mean() if "opp_def_z" in per_game.columns else 0.0
    # Normalize to 0-100
    lo_3d, hi_3d = cfg.third_down_pct_range
    lo_sack, hi_sack = cfg.sack_avoid_range
    drive_sustain = 100.0 * (third_conv_pct - lo_3d) / (hi_3d - lo_3d) if hi_3d > lo_3d else 50.0
    drive_sustain = (drive_sustain + 100.0 * (sack_avoidance - lo_sack) / (hi_sack - lo_sack)) / 2.0 if hi_sack > lo_sack else drive_sustain
    drive_sustain = max(0.0, min(100.0, drive_sustain))
    lo_rz, hi_rz = cfg.rz_td_pct_range
    situational_rz = 100.0 * (rz_td_pct - lo_rz) / (hi_rz - lo_rz) if hi_rz > lo_rz else 50.0
    situational_rz = max(0.0, min(100.0, situational_rz))
    situational_exec = 0.6 * situational_rz + 0.4 * leverage_avoid_score
    situational_exec = max(0.0, min(100.0, situational_exec))
    lo_sc, hi_sc = cfg.scramble_epa_proxy_range
    scramble_score = 100.0 * (scramble_yds_per_game - lo_sc) / (hi_sc - lo_sc) if hi_sc > lo_sc else 50.0
    scramble_score = max(0.0, min(100.0, scramble_score))
    lo_pt, hi_pt = cfg.pressure_to_sack_range
    pressure_score = 100.0 * (1.0 - (pressure_to_sack - lo_pt) / (hi_pt - lo_pt)) if hi_pt > lo_pt else 50.0
    pressure_score = max(0.0, min(100.0, pressure_score))
    offscript = (0.6 * scramble_score + 0.4 * pressure_score) if pressure_to_sack is not None and pressure_to_sack > 0 else scramble_score
    offscript = max(0.0, min(100.0, offscript))
    return {
        "drive_sustainability": round(drive_sustain, 1),
        "situational_execution": round(situational_exec, 1),
        "offscript_value": round(offscript, 1),
        "third_down_pct_qb": round(third_conv_pct, 1),
        "sack_avoidance_pct": round(sack_avoidance, 1),
        "rz_td_pct": round(rz_td_pct, 1),
        "rz_trips": int(rz_trips),
        "rz_td_drives": int(rz_td_drives),
        "leverage_to_per_play": round(leverage_to_per_play, 4),
        "scramble_yds_per_game": round(scramble_yds_per_game, 1),
        "pressure_to_sack": round(pressure_to_sack, 3) if pressure_to_sack is not None else 0.0,
        "qb_fault_int": attr["qb_fault_int"],
        "non_qb_fault_int": attr["non_qb_fault_int"],
        "qb_fault_fum": attr["qb_fault_fum"],
        "non_qb_fault_fum": attr["non_qb_fault_fum"],
        "qb_fault_to": attr["qb_fault_to"],
        "non_qb_fault_to": attr["non_qb_fault_to"],
        "weighted_turnovers": attr["weighted_turnovers"],
        "avg_def_z": round(avg_def_z, 3),
        "games": int(games),
    }


def _qb_production_components_legacy_team_pbp(
    pbp_post: pd.DataFrame,
    schedules: pd.DataFrame,
    qb: str,
    team: str,
    def_strength: Dict[str, float],
    config: Optional[QBProdConfig] = None,
) -> Dict[str, float]:
    """Legacy path: compute from full team_pbp without per-game table (used if per_game is empty)."""
    cfg = config or QBProdConfig()
    team_pbp = pbp_post[pbp_post["posteam"] == team].copy()
    if team_pbp.empty:
        return _empty_components(team, def_strength, cfg)
    has_qb_names = _team_has_qb_columns(team_pbp)
    qb_mask = team_pbp.apply(lambda r: _is_qb_play(r, team, qb), axis=1) if has_qb_names else pd.Series(True, index=team_pbp.index)

    # --- Drive Sustainability: 3rd down conversion on QB plays, sack avoidance
    third = team_pbp[(team_pbp["down"] == 3) & (qb_mask if has_qb_names else True)]
    if has_qb_names:
        third = third[qb_mask.reindex(third.index, fill_value=False)]
    third_attempts = len(third)
    if third_attempts > 0:
        if "first_down" in third.columns:
            converted = (third["first_down"].fillna(0) == 1) | (third.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1)
        else:
            converted = (third.get("yards_gained", pd.Series(dtype=float)).fillna(0) >= third.get("ydstogo", pd.Series(dtype=float)).fillna(0)) | (third.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1)
        third_conv_pct = 100.0 * converted.sum() / third_attempts
    else:
        third_conv_pct = 0.0

    dropbacks = team_pbp[(team_pbp["play_type"].isin(["pass", "sack"])) & (qb_mask if has_qb_names else True)]
    if has_qb_names:
        dropbacks = dropbacks[qb_mask.reindex(dropbacks.index, fill_value=False)]
    n_dropbacks = len(dropbacks)
    sacks = int(dropbacks.get("play_type", pd.Series(dtype=str)).eq("sack").sum()) if n_dropbacks else 0
    sack_rate = 100.0 * safe_div(sacks, n_dropbacks) if n_dropbacks else 0.0
    sack_avoidance = 100.0 - sack_rate  # higher better

    drive_sustain_raw = (third_conv_pct * 0.5 + sack_avoidance * 0.5)  # simple combo for raw; normalized later

    # --- Situational: RZ TD rate on QB-led drives, leverage TO avoidance
    drives = team_pbp.groupby(["game_id", "drive"])
    qb_led_drives = set(drives.groups.keys()) if not has_qb_names else set()
    if has_qb_names:
        for (gid, did), grp in drives:
            if grp.apply(lambda r: _is_qb_play(r, team, qb), axis=1).any():
                qb_led_drives.add((gid, did))
    rz_trips = 0
    rz_td_drives = 0
    for (gid, did), grp in drives:
        if (gid, did) not in qb_led_drives:
            continue
        in_rz = (grp["yardline_100"].fillna(999) <= 20).any()
        if not in_rz:
            continue
        rz_trips += 1
        if (grp.get("touchdown", pd.Series(dtype=float)).fillna(0) == 1).any():
            rz_td_drives += 1
    rz_td_pct = 100.0 * safe_div(rz_td_drives, rz_trips) if rz_trips else 0.0

    attr = qb_turnover_attribution(pbp_post, qb, team)
    leverage_plays = team_pbp[((team_pbp["down"] == 3) | (team_pbp["yardline_100"].fillna(999) <= 20))]
    n_leverage = len(leverage_plays)
    weighted_to = attr["weighted_turnovers"]
    leverage_to_per_play = safe_div(weighted_to, n_leverage) if n_leverage else 0.0
    leverage_avoid_score = 100.0 - min(100.0, leverage_to_per_play * 200)  # lower TO = higher score

    situational_raw = (rz_td_pct * 0.6 + leverage_avoid_score * 0.4)

    # --- Off-Script: scramble proxy, pressure-to-sack
    if "qb_scramble" in team_pbp.columns:
        scrambles = team_pbp[team_pbp["qb_scramble"].fillna(0) == 1]
    else:
        scrambles = team_pbp[(team_pbp["play_type"] == "run") & (team_pbp.get("rusher_player_name", pd.Series(dtype=str)).fillna("").str.upper() == str(qb).upper()) & (team_pbp["yards_gained"].fillna(0) >= cfg.scramble_min_yards)]
    scramble_yds = scrambles["yards_gained"].fillna(0).sum()
    scramble_plays = len(scrambles)
    games = team_pbp["game_id"].nunique() or 1
    scramble_yds_per_game = safe_div(scramble_yds, games)

    if "qb_hit" in team_pbp.columns:
        qb_hits = int(team_pbp["qb_hit"].fillna(0).sum())
        sack_count = int(team_pbp[team_pbp["play_type"] == "sack"].shape[0])
        pressure_to_sack = safe_div(sack_count, qb_hits + sack_count) if (qb_hits + sack_count) > 0 else 0.0
    else:
        pressure_to_sack = 0.0
        scramble_yds_per_game = scramble_yds_per_game * 1.2  # reweight: no pressure metric

    offscript_raw = scramble_yds_per_game - pressure_to_sack * 50  # higher scramble, lower pressure = better; normalized later

    # Normalize to 0-100
    lo_3d, hi_3d = cfg.third_down_pct_range
    lo_sack, hi_sack = cfg.sack_avoid_range
    drive_sustain = 100.0 * (third_conv_pct - lo_3d) / (hi_3d - lo_3d) if hi_3d > lo_3d else 50.0
    drive_sustain = (drive_sustain + 100.0 * (sack_avoidance - lo_sack) / (hi_sack - lo_sack)) / 2.0 if hi_sack > lo_sack else drive_sustain
    drive_sustain = max(0.0, min(100.0, drive_sustain))

    lo_rz, hi_rz = cfg.rz_td_pct_range
    situational_rz = 100.0 * (rz_td_pct - lo_rz) / (hi_rz - lo_rz) if hi_rz > lo_rz else 50.0
    situational_rz = max(0.0, min(100.0, situational_rz))
    situational_exec = 0.6 * situational_rz + 0.4 * leverage_avoid_score
    situational_exec = max(0.0, min(100.0, situational_exec))

    lo_sc, hi_sc = cfg.scramble_epa_proxy_range
    scramble_score = 100.0 * (scramble_yds_per_game - lo_sc) / (hi_sc - lo_sc) if hi_sc > lo_sc else 50.0
    scramble_score = max(0.0, min(100.0, scramble_score))
    lo_pt, hi_pt = cfg.pressure_to_sack_range
    pressure_score = 100.0 * (1.0 - (pressure_to_sack - lo_pt) / (hi_pt - lo_pt)) if hi_pt > lo_pt else 50.0
    pressure_score = max(0.0, min(100.0, pressure_score))
    if "qb_hit" not in team_pbp.columns:
        offscript = scramble_score
    else:
        offscript = 0.6 * scramble_score + 0.4 * pressure_score
    offscript = max(0.0, min(100.0, offscript))

    # Avg opponent def z (from schedules)
    avg_def_z = 0.0
    if "game_id" in team_pbp.columns and schedules is not None and not schedules.empty:
        game_ids = team_pbp["game_id"].unique()
        if "home_team" in schedules.columns and "away_team" in schedules.columns:
            opps = []
            for gid in game_ids:
                s = schedules[schedules["game_id"] == gid]
                if s.empty:
                    continue
                row = s.iloc[0]
                opp = row["away_team"] if row["home_team"] == team else row["home_team"]
                opps.append(def_strength.get(str(opp), 0.0))
            avg_def_z = sum(opps) / len(opps) if opps else 0.0

    return {
        "drive_sustainability": round(drive_sustain, 1),
        "situational_execution": round(situational_exec, 1),
        "offscript_value": round(offscript, 1),
        "third_down_pct_qb": round(third_conv_pct, 1),
        "sack_avoidance_pct": round(sack_avoidance, 1),
        "rz_td_pct": round(rz_td_pct, 1),
        "rz_trips": rz_trips,
        "rz_td_drives": rz_td_drives,
        "leverage_to_per_play": round(leverage_to_per_play, 4),
        "scramble_yds_per_game": round(scramble_yds_per_game, 1),
        "pressure_to_sack": round(pressure_to_sack, 3) if "qb_hit" in team_pbp.columns else 0.0,
        "qb_fault_int": attr["qb_fault_int"],
        "non_qb_fault_int": attr["non_qb_fault_int"],
        "qb_fault_fum": attr["qb_fault_fum"],
        "non_qb_fault_fum": attr["non_qb_fault_fum"],
        "qb_fault_to": attr["qb_fault_to"],
        "non_qb_fault_to": attr["non_qb_fault_to"],
        "weighted_turnovers": attr["weighted_turnovers"],
        "avg_def_z": round(avg_def_z, 3),
        "games": int(games),
    }


def _empty_components(team: str, def_strength: Dict[str, float], cfg: QBProdConfig) -> Dict[str, float]:
    return {
        "drive_sustainability": 0.0, "situational_execution": 0.0, "offscript_value": 0.0,
        "third_down_pct_qb": 0.0, "sack_avoidance_pct": 0.0, "rz_td_pct": 0.0,
        "rz_trips": 0, "rz_td_drives": 0, "leverage_to_per_play": 0.0,
        "scramble_yds_per_game": 0.0,         "pressure_to_sack": 0.0,
        "qb_fault_int": 0.0, "non_qb_fault_int": 0.0, "qb_fault_fum": 0.0, "non_qb_fault_fum": 0.0,
        "qb_fault_to": 0.0, "non_qb_fault_to": 0.0, "weighted_turnovers": 0.0,
        "avg_def_z": 0.0, "games": 0,
    }


def qb_production_score(components: Dict[str, float], config: Optional[QBProdConfig] = None) -> Dict[str, float]:
    """
    Combine components into 0-100 score; apply defense difficulty adjustment.
    Returns report with total, drive_sustain, situational, offscript, def_adj_points, avg_def_z, attribution.
    """
    cfg = config or QBProdConfig()
    base = (
        cfg.w_drive * components.get("drive_sustainability", 0)
        + cfg.w_situational * components.get("situational_execution", 0)
        + cfg.w_offscript * components.get("offscript_value", 0)
    )
    avg_def_z = components.get("avg_def_z", 0.0)
    def_adj_points = cfg.w_def_adj * avg_def_z * 10.0
    final = max(0.0, min(100.0, base + def_adj_points))
    return {
        "production_score": round(final, 1),
        "drive_sustain": round(components.get("drive_sustainability", 0), 1),
        "situational": round(components.get("situational_execution", 0), 1),
        "offscript": round(components.get("offscript_value", 0), 1),
        "avg_def_z": round(avg_def_z, 3),
        "def_adj_points": round(def_adj_points, 1),
        "qb_fault_to": components.get("qb_fault_to", 0),
        "non_qb_fault_to": components.get("non_qb_fault_to", 0),
        "weighted_turnovers": components.get("weighted_turnovers", 0),
        **{k: v for k, v in components.items() if k not in ("drive_sustainability", "situational_execution", "offscript_value")},
    }
