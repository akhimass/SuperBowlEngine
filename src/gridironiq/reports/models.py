from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from gridironiq.draft.team_needs import NEED_BUCKETS

# All 32 NFL clubs — full names for draft reports (no external import).
TEAM_NAMES: Dict[str, str] = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LV": "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers",
    "SEA": "Seattle Seahawks",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _signal_policy_str(policy: Dict[str, Any]) -> str:
    manual = policy.get("manual_need_priors")
    src = policy.get("sources") or []
    base = "data_only"
    if manual:
        base += " | manual_need_priors=True"
    else:
        base += " | no_manual_priors"
    return f"{base} | sources={src}"


def _room_summaries_from_team_needs(team_needs: Dict[str, Any]) -> Dict[str, str]:
    layers = team_needs.get("signal_layers") or {}
    room = layers.get("room_production_normalized") or {}
    epa = layers.get("epa_need_normalized") or {}
    out: Dict[str, str] = {}
    for b in NEED_BUCKETS:
        rv = float(room.get(b, 0.0))
        ev = float(epa.get(b, 0.0))
        out[b] = (
            f"Room stress {rv:.0f}/100 vs class; EPA-need layer {ev:.0f}/100 "
            f"(nflverse player_stats + PBP signals)."
        )
    return out


def _scheme_summary_from_board(pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
    scheme = pipeline_result.get("team_scheme") or {}
    raw = scheme.get("raw") or {}
    summary = pipeline_result.get("team_context_summary") or {}
    highlights = summary.get("scheme_highlights") or {}
    out: Dict[str, Any] = {}
    mapping = (
        ("off_pass_rate", "pass_rate"),
        ("off_shotgun_rate", "shotgun_rate"),
        ("te_target_share", "te_target_share"),
        ("wr_target_share_of_skill", "wr_target_share"),
    )
    for src, dest in mapping:
        if src in raw and raw[src] is not None:
            try:
                out[dest] = float(raw[src])
            except (TypeError, ValueError):
                continue
    if "pass_rate" not in out and highlights.get("pass_rate") is not None:
        out["pass_rate"] = float(highlights["pass_rate"])
    if "shotgun_rate" not in out and highlights.get("shotgun_rate") is not None:
        out["shotgun_rate"] = float(highlights["shotgun_rate"])
    if highlights.get("te_target_share_trend") is not None:
        out["te_target_share_trend"] = float(highlights["te_target_share_trend"])
    if highlights.get("edge_pressure_trend") is not None:
        out["edge_pressure_trend"] = float(highlights["edge_pressure_trend"])
    return out


def _top_needs_from_scores(need_scores: Dict[str, Any]) -> List[Tuple[str, float]]:
    pairs: List[Tuple[str, float]] = []
    for k, v in need_scores.items():
        try:
            pairs.append((str(k), float(v)))
        except (TypeError, ValueError):
            continue
    pairs.sort(key=lambda x: -x[1])
    return pairs


def _parse_weight_to_int(weight: Any) -> int:
    if weight is None:
        return 0
    try:
        return int(round(float(weight)))
    except (TypeError, ValueError):
        return 0


def _height_display(ht: Any) -> str:
    if ht is None or (isinstance(ht, float) and str(ht) == "nan"):
        return "—"
    s = str(ht).strip()
    if not s or s.lower() == "nan":
        return "—"
    if "'" in s:
        return s
    m = re.match(r"^(\d+)-(\d+)$", s)
    if m:
        return f"{m.group(1)}'{m.group(2)}\""
    return s


@dataclass
class TeamNeedSnapshot:
    team: str
    team_full_name: str
    season: int
    pick_slots: List[int]
    top_needs: List[Tuple[str, float]]
    scheme_summary: Dict[str, Any]
    room_summaries: Dict[str, str]
    signal_policy: str
    generated_at: str
    signal_audit_rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ProspectCard:
    name: str
    position: str
    college: str
    conference: str
    height: str
    weight: int
    forty: Optional[float]
    vertical: Optional[float]
    broad_jump: Optional[float]
    bench_press: Optional[int]
    prospect_score: float
    athleticism_score: float
    production_score: float
    scheme_fit_score: float
    team_need_score: float
    final_draft_score: float
    availability_pct: Optional[float]
    strengths: List[str]
    weaknesses: List[str]
    comp: Optional[str]
    one_line: Optional[str]
    audit_trail: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def prospect_dict_to_card(
    row: Dict[str, Any],
    *,
    availability_pct: Optional[float] = None,
    strengths: Optional[List[str]] = None,
    weaknesses: Optional[List[str]] = None,
    comp: Optional[str] = None,
    one_line: Optional[str] = None,
) -> ProspectCard:
    radar = row.get("radar") or {}
    sb = row.get("score_breakdown") or {}
    prospect = sb.get("prospect") or {}
    cfb = sb.get("cfb") if isinstance(sb.get("cfb"), dict) else {}
    conf = str(cfb.get("cfb_conference") or cfb.get("conference") or "—")

    bench = row.get("bench")
    bench_i: Optional[int] = None
    if bench is not None and str(bench) != "nan":
        try:
            bench_i = int(round(float(bench)))
        except (TypeError, ValueError):
            bench_i = None

    def _f(key: str) -> Optional[float]:
        v = row.get(key)
        if v is None or (isinstance(v, float) and str(v) == "nan"):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    audit: Dict[str, Any] = dict(sb) if sb else {}
    audit["player_id"] = row.get("player_id")
    audit["model_rank"] = row.get("model_rank")
    audit["consensus_rank"] = row.get("consensus_rank")

    return ProspectCard(
        name=str(row.get("player_name") or ""),
        position=str(row.get("pos") or ""),
        college=str(row.get("school") or ""),
        conference=conf,
        height=_height_display(row.get("height")),
        weight=_parse_weight_to_int(row.get("weight_lb")),
        forty=_f("forty"),
        vertical=_f("vertical"),
        broad_jump=_f("broad_jump"),
        bench_press=bench_i,
        prospect_score=float(row.get("prospect_score") or 0.0),
        athleticism_score=float(radar.get("athleticism") or prospect.get("athletic_score") or 0.0),
        production_score=float(radar.get("production") or prospect.get("production_score") or 0.0),
        scheme_fit_score=float(radar.get("scheme_fit") or row.get("scheme_fit_score") or 0.0),
        team_need_score=float(radar.get("team_need") or row.get("team_need_score") or 0.0),
        final_draft_score=float(row.get("final_draft_score") or 0.0),
        availability_pct=availability_pct,
        strengths=list(strengths or []),
        weaknesses=list(weaknesses or []),
        comp=comp,
        one_line=one_line,
        audit_trail=audit,
    )


@dataclass
class DraftBoardReport:
    team_snapshot: TeamNeedSnapshot
    top_prospects: List[ProspectCard]
    pick_recommendations: Dict[int, ProspectCard]
    trade_scenarios: List[str]
    report_title: str
    generated_at: str


def _signal_audit_table(team_needs: Dict[str, Any]) -> List[Dict[str, Any]]:
    policy = team_needs.get("need_signal_policy") or {}
    weights = {
        "nflverse_pbp_epa": 0.35,
        "nflverse_snap_counts": 0.25,
        "nflverse_injury_reports": 0.20,
        "nflverse_player_stats_room_production": 0.20,
    }
    src_list = list(policy.get("sources") or [])
    rows: List[Dict[str, Any]] = []
    if not src_list:
        src_list = list(weights.keys())
    total_w = sum(weights.get(s, 0.15) for s in src_list) or 1.0
    for s in src_list:
        w = weights.get(s, 0.15)
        rows.append(
            {
                "signal_source": s,
                "weight": round(w / total_w, 3),
                "contribution": "Normalized per-position need stack; see team_needs.signal_layers.",
            }
        )
    return rows


def _availability_map_from_recs(recs: List[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for r in recs:
        pid = str(r.get("player_id") or "")
        if not pid:
            continue
        av = r.get("availability_at_pick")
        try:
            out[pid] = float(av) * 100.0 if av is not None else out.get(pid, 0.0)
        except (TypeError, ValueError):
            continue
    return out


def from_pipeline_output(
    pipeline_result: Dict[str, Any],
    team: str,
    season: int,
    pick_slots: Optional[List[int]] = None,
    *,
    top_n: int = 10,
) -> DraftBoardReport:
    """
    Converts ``build_draft_board`` output into a DraftBoardReport.

    Optional: ``recommendations_by_pick`` or ``recommendations`` + ``pick_number``
    for simulated pick recommendations. ``top_n`` caps ``top_prospects`` from
    full board rows sorted by ``final_draft_score`` descending.
    """
    team_u = str(team).upper()
    if "team" not in pipeline_result:
        raise ValueError("pipeline_result missing required key: team")
    if str(pipeline_result["team"]).upper() != team_u:
        raise ValueError(
            f"pipeline_result['team'] mismatch: expected {team_u!r}, got {pipeline_result['team']!r}"
        )
    if "eval_season" not in pipeline_result:
        raise ValueError("pipeline_result missing required key: eval_season")
    if int(pipeline_result["eval_season"]) != int(season):
        raise ValueError(
            f"pipeline_result['eval_season'] {pipeline_result['eval_season']!r} != season argument {season!r}"
        )
    if "prospects" not in pipeline_result:
        raise ValueError("Missing required key: prospects")
    prospects = pipeline_result["prospects"]
    if not isinstance(prospects, list):
        raise ValueError("pipeline_result missing or invalid required key: prospects (expected list)")
    if len(prospects) == 0:
        raise ValueError("pipeline_result.prospects is empty; need at least one prospect row")
    team_needs = pipeline_result.get("team_needs")
    if not isinstance(team_needs, dict):
        raise ValueError("pipeline_result missing or invalid required key: team_needs (expected dict)")
    need_scores = team_needs.get("need_scores")
    if not isinstance(need_scores, dict) or len(need_scores) == 0:
        raise ValueError("pipeline_result.team_needs missing required key: need_scores (non-empty dict)")
    summary = pipeline_result.get("team_context_summary")
    if not isinstance(summary, dict):
        raise ValueError(
            "pipeline_result missing or invalid required key: team_context_summary (expected dict)"
        )

    slots = list(pick_slots) if pick_slots is not None else list(summary.get("draft_pick_positions") or [])
    if not slots and pipeline_result.get("recommendations_by_pick"):
        slots = sorted(int(k) for k in pipeline_result["recommendations_by_pick"].keys())
    if not slots:
        slots = [1]

    top_needs = _top_needs_from_scores(need_scores)[:11]
    scheme_summary = _scheme_summary_from_board(pipeline_result)
    room_summaries = _room_summaries_from_team_needs(team_needs)
    policy = team_needs.get("need_signal_policy") or {}
    signal_policy = _signal_policy_str(policy)
    generated_at = _iso_now()

    snap = TeamNeedSnapshot(
        team=team_u,
        team_full_name=TEAM_NAMES.get(team_u, team_u),
        season=int(season),
        pick_slots=slots,
        top_needs=top_needs[:8],
        scheme_summary=scheme_summary,
        room_summaries=room_summaries,
        signal_policy=signal_policy,
        generated_at=generated_at,
        signal_audit_rows=_signal_audit_table(team_needs),
    )

    pick_recommendations: Dict[int, ProspectCard] = {}
    rec_by_pick = pipeline_result.get("recommendations_by_pick")
    avail_by_pid: Dict[str, float] = {}
    if isinstance(rec_by_pick, dict) and rec_by_pick:
        first_key = sorted(rec_by_pick.keys(), key=int)[0]
        avail_by_pid = _availability_map_from_recs(rec_by_pick[first_key] or [])
    if isinstance(rec_by_pick, dict):
        for pk, recs in rec_by_pick.items():
            if not isinstance(recs, list) or not recs:
                continue
            top = recs[0]
            avail = top.get("availability_at_pick")
            try:
                ap = float(avail) * 100.0 if avail is not None else None
            except (TypeError, ValueError):
                ap = None
            pick_recommendations[int(pk)] = prospect_dict_to_card(top, availability_pct=ap)
    elif pipeline_result.get("recommendations") and pipeline_result.get("pick_number") is not None:
        recs = pipeline_result["recommendations"]
        pk = int(pipeline_result["pick_number"])
        if isinstance(recs, list) and recs:
            avail_by_pid = _availability_map_from_recs(recs)
            top = recs[0]
            avail = top.get("availability_at_pick")
            try:
                ap = float(avail) * 100.0 if avail is not None else None
            except (TypeError, ValueError):
                ap = None
            pick_recommendations[pk] = prospect_dict_to_card(top, availability_pct=ap)

    ranked_rows = sorted(
        prospects,
        key=lambda r: (-float(r.get("final_draft_score") or 0), str(r.get("player_name"))),
    )
    n = max(1, min(int(top_n), len(ranked_rows)))
    top_prospect_cards: List[ProspectCard] = []
    for r in ranked_rows[:n]:
        pid = str(r.get("player_id") or "")
        ap = avail_by_pid.get(pid) if pid else None
        top_prospect_cards.append(
            prospect_dict_to_card(
                r,
                availability_pct=ap if ap is not None else None,
            )
        )

    title_team = TEAM_NAMES.get(team_u, team_u)
    return DraftBoardReport(
        team_snapshot=snap,
        top_prospects=top_prospect_cards,
        pick_recommendations=pick_recommendations,
        trade_scenarios=[],
        report_title=f"{title_team} — Draft Board ({season})",
        generated_at=generated_at,
    )
