from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .cfb_client import fetch_cfbd_team_conferences, fetch_stats_for_schools
from .cfb_schools import cfbd_team_for_combine_school
from .positions import bucket_for_combine_pos

logger = logging.getLogger(__name__)

# CFBD conference → competition multiplier applied before within-class percentiling (audited on each prospect).
CONFERENCE_COMPETITION_WEIGHT: Dict[str, float] = {
    "SEC": 1.00,
    "Big Ten": 1.00,
    "Big 12": 0.95,
    "ACC": 0.93,
    "Pac-12": 0.90,
    "American Athletic": 0.80,
    "Mountain West": 0.78,
    "MAC": 0.75,
    "Sun Belt": 0.74,
    "Conference USA": 0.73,
    "Independent": 0.88,
}
DEFAULT_COMPETITION_WEIGHT = 0.82


def competition_weight_for_conference(conference: str) -> float:
    c = (conference or "").strip()
    if not c:
        return DEFAULT_COMPETITION_WEIGHT
    return float(CONFERENCE_COMPETITION_WEIGHT.get(c, DEFAULT_COMPETITION_WEIGHT))


def _parse_stat(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        parts = s.split("/")
        if len(parts) == 2:
            try:
                return float(parts[0]) / float(parts[1])
            except ValueError:
                return None
        return None


def aggregate_cfbd_rows(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    playerId -> {player, team, position, stats: {category: {statType: float}}}
    """
    by_pid: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        pid = r.get("playerId")
        if not pid:
            continue
        pid = str(pid)
        if pid not in by_pid:
            by_pid[pid] = {
                "player": r.get("player"),
                "team": r.get("team"),
                "position": r.get("position"),
                "stats": {},
            }
        cat = str(r.get("category") or "")
        st = str(r.get("statType") or "")
        v = _parse_stat(r.get("stat"))
        if not cat or not st or v is None:
            continue
        by_pid[pid]["stats"].setdefault(cat, {})[st] = v
    return by_pid


def normalize_person_name(name: str) -> str:
    s = (name or "").lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    s = re.sub(r"\b(jr|sr|iii|ii|iv)\b", "", s)
    return " ".join(s.split())


def _get_cat(stats: Dict[str, Dict[str, float]], *names: str) -> Dict[str, float]:
    for n in names:
        if n in stats:
            return stats[n]
    return {}


def _situational_raw(stats: Dict[str, Dict[str, float]]) -> Optional[float]:
    vals: List[float] = []
    for _cat, d in stats.items():
        for ty, val in d.items():
            t = str(ty).upper()
            if any(x in t for x in ("3RD", "THIRD", "RZ", "RED", "GOAL")):
                vals.append(float(val))
    if not vals:
        return None
    return sum(vals) / len(vals)


def raw_te_usage_efficiency(blob: Dict[str, Any]) -> Optional[float]:
    """
    College receiving usage / efficiency proxy from CFBD receiving bucket.
    Higher = more efficient / valuable receiving profile for TE.
    """
    st = blob["stats"]
    rec = _get_cat(st, "receiving")
    re = float(rec.get("REC") or 0.0)
    yd = float(rec.get("YDS") or 0.0)
    tg = float(rec.get("TGT") or rec.get("TARGETS") or rec.get("TAR") or 0.0)
    if re < 8 and yd < 120:
        return None
    ypr = yd / max(re, 1.0)
    if tg >= max(re, 1.0):
        catch_pct = re / max(tg, 1.0)
    else:
        catch_pct = 0.62
    return ypr * 10.0 + catch_pct * 28.0


def raw_explosiveness(pos_bucket: str, blob: Dict[str, Any]) -> Optional[float]:
    st = blob["stats"]
    if pos_bucket in {"WR", "TE"}:
        rec = _get_cat(st, "receiving")
        long = rec.get("LONG") or rec.get("LONGEST") or 0.0
        td = rec.get("TD") or 0.0
        yds = rec.get("YDS") or 0.0
        re = rec.get("REC") or 0.0
        if re < 5 and yds < 80:
            return None
        ypr = yds / max(re, 1.0)
        return float(long) + 6.0 * td + 1.5 * ypr
    if pos_bucket == "RB":
        ru = _get_cat(st, "rushing")
        long = ru.get("LONG") or ru.get("LONGEST") or 0.0
        yds = ru.get("YDS") or 0.0
        # "CAR" is CFBD rushing carries key, not an NFL team abbreviation.
        carries = ru.get("CAR") or ru.get("ATT") or 0.0
        if carries < 15:
            return None
        return float(long) + 0.08 * yds
    if pos_bucket == "QB":
        pa = _get_cat(st, "passing")
        yds = pa.get("YDS") or 0.0
        td = pa.get("TD") or 0.0
        att = pa.get("ATT") or 0.0
        if att < 30:
            return None
        return 0.04 * yds + 5.0 * td
    return None


def raw_pressure_proxy(blob: Dict[str, Any]) -> Optional[float]:
    d = _get_cat(blob["stats"], "defensive", "defense")
    sk = d.get("SACKS") or d.get("SACK") or 0.0
    tfl = d.get("TFL") or 0.0
    tot = d.get("TOT") or d.get("TACKLES") or 0.0
    if sk < 0.5 and tfl < 2 and tot < 15:
        return None
    return 12.0 * sk + 4.0 * tfl + 0.12 * tot


def raw_production_efficiency(pos_bucket: str, blob: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    Returns (production_raw, efficiency_raw) for percentile ranking within position bucket.
    """
    st = blob["stats"]
    pb = pos_bucket

    if pb == "QB":
        p = _get_cat(st, "passing")
        att = p.get("ATT") or p.get("ATTEMPTS") or 0.0
        yds = p.get("YDS") or 0.0
        td = p.get("TD") or 0.0
        ints = p.get("INT") or 0.0
        if att < 20 and yds < 200:
            return None
        prod = yds + 18.0 * td
        eff = (yds / max(att, 1.0)) - 2.2 * (ints / max(att, 1.0)) * 100.0
        return prod, eff

    if pb == "RB":
        ru = _get_cat(st, "rushing")
        rec = _get_cat(st, "receiving")
        carries = ru.get("CAR") or ru.get("ATT") or 0.0  # CFBD carries key
        ry = ru.get("YDS") or 0.0
        rtd = ru.get("TD") or 0.0
        recn = rec.get("REC") or 0.0
        recy = rec.get("YDS") or 0.0
        rectd = rec.get("TD") or 0.0
        if carries < 20 and recn < 8:
            return None
        prod = ry + 0.45 * recy + 10.0 * (rtd + 0.6 * rectd)
        eff = ry / max(carries, 1.0) + 0.12 * (recy / max(recn, 1.0))
        return prod, eff

    if pb in {"WR", "TE"}:
        rec = _get_cat(st, "receiving")
        recn = rec.get("REC") or 0.0
        recy = rec.get("YDS") or 0.0
        rectd = rec.get("TD") or 0.0
        if recn < 8 and recy < 120:
            return None
        prod = recy + 14.0 * rectd
        eff = recy / max(recn, 1.0)
        return prod, eff

    if pb in {"EDGE", "IDL", "LB", "CB", "SAF"}:
        d = _get_cat(st, "defensive", "defense")
        tot = d.get("TOT") or d.get("TACKLES") or 0.0
        solo = d.get("SOLO") or 0.0
        tfl = d.get("TFL") or 0.0
        sk = d.get("SACKS") or d.get("SACK") or 0.0
        pd = d.get("PD") or d.get("PBU") or 0.0
        ints = d.get("INT") or 0.0
        if tot < 8 and sk < 1 and ints < 1:
            return None
        prod = tot + 3.5 * tfl + 7.0 * sk + 5.0 * pd + 12.0 * ints + 0.5 * solo
        eff = prod
        return prod, eff

    return None


def _percentile_rank(values: List[float]) -> List[float]:
    if not values:
        return []
    s = pd.Series(values)
    return (s.rank(pct=True, method="average") * 100.0).tolist()


def build_cfbd_scores_for_combine_class(
    prospects: pd.DataFrame,
    cfb_season: int,
    api_key: str,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """
    prospects: combine frame with columns school, player_name, pos, cfb_id, player_id (optional).

    Returns:
      scores_by_player_id: gridiron player_id -> {production, efficiency, cfbd_player_id, season, ...}
      meta: fetch stats
    """
    schools = prospects["school"].dropna().astype(str).unique().tolist()
    teams = [cfbd_team_for_combine_school(s) for s in schools]
    team_rows = fetch_stats_for_schools(cfb_season, teams, api_key)

    conf_map: Dict[str, str] = {}
    try:
        conf_map = fetch_cfbd_team_conferences(cfb_season, api_key)
    except Exception as e:
        logger.warning("CFBD conference map unavailable: %s", e)
        conf_map = {}

    all_rows: List[Dict[str, Any]] = []
    for t, rows in team_rows.items():
        all_rows.extend(rows)

    by_pid = aggregate_cfbd_rows(all_rows)

    name_team_to_pid: Dict[Tuple[str, str], str] = {}
    for pid, meta in by_pid.items():
        team = str(meta.get("team") or "")
        pname = normalize_person_name(str(meta.get("player") or ""))
        if team and pname:
            name_team_to_pid[(team, pname)] = pid

    # First pass: match each prospect row -> cfbd pid (or None) + confidence
    match_pid: Dict[str, Optional[str]] = {}
    match_confidence: Dict[str, str] = {}
    unmatched_players: List[str] = []
    for _, row in prospects.iterrows():
        gid = str(row.get("player_id") or "")
        if not gid:
            continue
        cid = row.get("cfb_id")
        if cid is not None and str(cid).strip() and str(cid) in by_pid:
            match_pid[gid] = str(cid)
            match_confidence[gid] = "cfb_id_exact"
            continue
        team = cfbd_team_for_combine_school(str(row.get("school") or ""))
        nm = normalize_person_name(str(row.get("player_name") or ""))
        pid = name_team_to_pid.get((team, nm))
        match_pid[gid] = pid
        if pid:
            match_confidence[gid] = "name_school_fuzzy"
        else:
            unmatched_players.append(gid)

    # Build raw vectors per position bucket for matched players
    bucket_lists: Dict[str, List[Tuple[str, float, float]]] = {}
    ex_lists: Dict[str, List[Tuple[str, float]]] = {}
    pr_lists: Dict[str, List[Tuple[str, float]]] = {}
    sit_lists: Dict[str, List[Tuple[str, float]]] = {}
    te_use_data: List[Tuple[str, float, float, str, float]] = []

    for gid, pid in match_pid.items():
        if not pid or pid not in by_pid:
            continue
        sub = prospects.loc[prospects["player_id"] == gid]
        if sub.empty:
            continue
        row = sub.iloc[0]
        pos_b = str(row.get("pos_bucket") or bucket_for_combine_pos(str(row.get("pos") or "")))
        blob = by_pid[pid]
        raw = raw_production_efficiency(pos_b, blob)
        if raw is not None:
            pr, er = raw
            bucket_lists.setdefault(pos_b, []).append((gid, pr, er))
        ex = raw_explosiveness(pos_b, blob)
        if ex is not None:
            ex_lists.setdefault(pos_b, []).append((gid, ex))
        if pos_b == "EDGE":
            px = raw_pressure_proxy(blob)
            if px is not None:
                team_nm = str(blob.get("team") or "")
                conf = conf_map.get(team_nm, "")
                w = competition_weight_for_conference(conf)
                pr_lists.setdefault(pos_b, []).append((gid, px * w))
        sit = _situational_raw(blob["stats"])
        if sit is not None:
            sit_lists.setdefault(pos_b, []).append((gid, sit))
        if pos_b == "TE":
            tu = raw_te_usage_efficiency(blob)
            if tu is not None:
                team_nm = str(blob.get("team") or "")
                conf = conf_map.get(team_nm, "")
                w = competition_weight_for_conference(conf)
                te_use_data.append((gid, tu, tu * w, conf or "unknown", w))

    def _apply_bucket_lists(
        bucket_map: Dict[str, List[Tuple[str, float]]],
        key: str,
        target: Dict[str, Dict[str, Any]],
    ) -> None:
        for pos_b, pairs in bucket_map.items():
            gids = [p[0] for p in pairs]
            vals = [p[1] for p in pairs]
            pct = _percentile_rank(vals)
            for i, gid in enumerate(gids):
                target.setdefault(gid, {})
                target[gid][key] = round(float(pct[i]), 2)

    scores_by_player_id: Dict[str, Dict[str, Any]] = {}
    for pos_b, triples in bucket_lists.items():
        gids = [t[0] for t in triples]
        prs = [t[1] for t in triples]
        ers: List[float] = []
        for t in triples:
            gid = t[0]
            er = t[2]
            if pos_b == "WR":
                pid_m = match_pid.get(gid)
                if pid_m and pid_m in by_pid:
                    b = by_pid[pid_m]
                    conf = conf_map.get(str(b.get("team") or ""), "")
                    er = float(er) * competition_weight_for_conference(conf)
            ers.append(er)
        pp = _percentile_rank(prs)
        pe = _percentile_rank(ers)
        for i, gid in enumerate(gids):
            pid = match_pid.get(gid)
            prod_p = float(pp[i])
            eff_p = float(pe[i])
            scores_by_player_id[gid] = {
                "cfb_season": cfb_season,
                "cfbd_player_id": pid,
                "cfb_production_score": round(prod_p, 2),
                "cfb_efficiency_score": round(eff_p, 2),
                "cfb_consistency_score": round(100.0 - abs(prod_p - eff_p), 2),
                "production_source_detail": "cfbd_player_season_stats",
                "cfb_match_confidence": match_confidence.get(gid, "unknown"),
            }

    _apply_bucket_lists(ex_lists, "cfb_explosiveness_score", scores_by_player_id)
    _apply_bucket_lists(pr_lists, "cfb_pressure_proxy_score", scores_by_player_id)
    _apply_bucket_lists(sit_lists, "cfb_situational_score", scores_by_player_id)

    if te_use_data:
        gids_te = [t[0] for t in te_use_data]
        adj_te = [t[2] for t in te_use_data]
        pct_te = _percentile_rank(adj_te)
        for i, gid in enumerate(gids_te):
            raw_v, conf, w = te_use_data[i][1], te_use_data[i][3], te_use_data[i][4]
            scores_by_player_id.setdefault(gid, {})
            scores_by_player_id[gid]["cfb_te_usage_efficiency_score_raw"] = round(float(raw_v), 4)
            scores_by_player_id[gid]["cfb_te_usage_efficiency_adjusted_value"] = round(float(adj_te[i]), 4)
            scores_by_player_id[gid]["cfb_te_usage_efficiency_score"] = round(float(pct_te[i]), 2)
            scores_by_player_id[gid]["cfb_conference"] = conf
            scores_by_player_id[gid]["cfb_competition_weight"] = round(float(w), 4)

    for gid in scores_by_player_id:
        if "cfb_explosiveness_score" not in scores_by_player_id[gid]:
            scores_by_player_id[gid]["cfb_explosiveness_score"] = None
            scores_by_player_id[gid]["cfb_explosiveness_note"] = "no_cfbd_explosive_long_stat"
        if "cfb_pressure_proxy_score" not in scores_by_player_id[gid]:
            scores_by_player_id[gid]["cfb_pressure_proxy_score"] = None
        if "cfb_situational_score" not in scores_by_player_id[gid]:
            scores_by_player_id[gid]["cfb_situational_score"] = None
            scores_by_player_id[gid]["cfb_situational_note"] = "no_3rd_or_rz_stattypes_in_feed"

    for gid in scores_by_player_id:
        sub = prospects.loc[prospects["player_id"] == gid]
        if sub.empty or str(sub.iloc[0].get("pos_bucket")) != "TE":
            continue
        if "cfb_te_usage_efficiency_score" not in scores_by_player_id[gid]:
            scores_by_player_id[gid]["cfb_te_usage_efficiency_score"] = None
            scores_by_player_id[gid]["cfb_te_usage_efficiency_note"] = "no_cfbd_te_usage_signal"

    for gid in scores_by_player_id:
        pid_m = match_pid.get(gid)
        if not pid_m or pid_m not in by_pid:
            continue
        b = by_pid[pid_m]
        team_nm = str(b.get("team") or "")
        conf = conf_map.get(team_nm, "")
        cw = competition_weight_for_conference(conf)
        scores_by_player_id[gid].setdefault("cfb_conference", conf or "unknown")
        scores_by_player_id[gid].setdefault("cfb_competition_weight", round(cw, 4))

    matched = len(scores_by_player_id)
    total = len(prospects)
    meta = {
        "cfb_season": cfb_season,
        "cfbd_teams_fetched": len(team_rows),
        "cfbd_conference_map_size": len(conf_map),
        "cfbd_players_indexed": len(by_pid),
        "cfb_match_count": matched,
        "cfb_match_rate": round(matched / max(total, 1), 4),
        "cfb_unmatched_player_ids_sample": unmatched_players[:50],
        "cfb_unmatched_count": len(unmatched_players),
    }
    if unmatched_players:
        logger.info(
            "CFBD: %s combine prospects unmatched to CFBD rows (sample ids logged in meta)",
            len(unmatched_players),
        )
    return scores_by_player_id, meta
